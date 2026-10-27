#!/usr/bin/env python3
"""Own deck/driver for the review of Xinyue's ba2b28ce design checks.

Physics follows the thread's setups, but the deck, initial state, noise draw and
diagnostics are built here independently:
 - dry: H2-He ideal-moist (H 1.5, He 0.15, cv_R 2.5), 100 K isothermal, 10 bar at
   the bottom, 450 km / 100 levels, balanced with snapy.balance_column, g 8.87;
 - moist: dry + vapor + cloud (tests/test_tracer_dry_convention.yaml species),
   32 km / 32 levels, g 10, 320 K, 1e5 Pa, vapour 0.02 and cloud 0.005 of the
   total mass, continuous hydrostatic profile;
 - wind u0 uniform or linear shear u0*z/Lz; Gaussian isobaric T noise (std = --noise);
 - box: nx2 = 64; column: nx2 = 4 with one noise draw copied to every column.
Diagnostics every --diag-dt s: rms/max w, max |u - u_ref|/u0, global sums of the
total density, m2, E and E + rho_tot g z (rho_tot = dry + every species row).
x2-mean u and m2 profiles at 1, 2, 3 d. Writes <out>.csv, <out>.prof.json, <out>.json.
"""
import argparse, hashlib, json, math, os, sys, time
import numpy as np, torch, yaml

RGAS = 8.31446261815324


def build_deck(a, moist):
    lz, nz, g = (3.2e4, 32, 10.0) if moist else (450.0e3, 100, 8.87)
    d = {"reference-state": {"Tref": 0.0, "Pref": 1.0e5},
         "geometry": {"type": "cartesian",
                      "bounds": {"x1min": 0.0, "x1max": lz, "x2min": 0.0, "x2max": a.nx2 * a.dx,
                                 "x3min": 0.0, "x3max": a.dx},
                      "cells": {"nx1": nz, "nx2": a.nx2, "nx3": 1, "nghost": 3}},
         "dynamics": {"equation-of-state": {"type": "ideal-moist", "density-floor": 1.0e-10,
                                            "pressure-floor": 1.0e-10, "limiter": True,
                                            "max-iter": 10, "ftol": a.ftol},
                      "reconstruct": {"vertical": {"type": "weno5", "scale": True, "shock": True},
                                      "horizontal": {"type": "weno5", "scale": True, "shock": True}},
                      "riemann-solver": {"type": "lmars"}},
         "boundary-condition": {"external": {"x1-inner": "reflecting", "x1-outer": "reflecting",
                                             "x2-inner": "periodic", "x2-outer": "periodic",
                                             "x3-inner": "periodic", "x3-outer": "periodic"}},
         "integration": {"type": "rk3", "cfl": a.cfl, "implicit-scheme": a.scheme, "nlim": -1,
                         "tlim": a.days * 86400.0, "ncycle_out": 1000000},
         "forcing": {"const-gravity": {"grav1": -g}}}
    if moist:
        d["species"] = [{"name": "dry", "composition": {"H": 1.6667, "He": 0.16667}, "cv_R": 2.5},
                        {"name": "vapor", "composition": {"H": 2, "O": 1}, "cv_R": 2.5, "u0_R": 0.0},
                        {"name": "cloud", "composition": {"H": 2, "O": 1}, "cv_R": 9.0, "u0_R": -3430.0}]
        d["reactions"] = [{"equation": "vapor <=> cloud", "type": "nucleation",
                           "rate-constant": {"formula": "h2o_ideal"}}]
    else:
        d["species"] = [{"name": "dry", "composition": {"H": 1.5, "He": 0.15}, "cv_R": 2.5}]
    return d, lz, nz, g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scheme", type=int, default=1)
    ap.add_argument("--dx", type=float, default=100.0e3)
    ap.add_argument("--nx2", type=int, default=64)
    ap.add_argument("--u0", type=float, default=400.0)
    ap.add_argument("--shear", action="store_true")
    ap.add_argument("--moist", action="store_true")
    ap.add_argument("--column", action="store_true", help="one noise draw copied to every x2 column")
    ap.add_argument("--noise", type=float, default=1.0e-6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cfl", type=float, default=0.3)
    ap.add_argument("--days", type=float, default=3.0)
    ap.add_argument("--diag-dt", type=float, default=600.0)
    ap.add_argument("--gwork", default=None, help="const-gravity gravity-work override (face/cell)")
    ap.add_argument("--ftol", type=float, default=1.0e-6, help="EOS saturation-adjustment ftol")
    ap.add_argument("--cloud", type=float, default=0.005, help="moist: initial cloud mass fraction")
    ap.add_argument("--balance", action="store_true", help="moist: project the column with snapy.balance_column too")
    a = ap.parse_args()
    torch.set_num_threads(1)
    import snapy
    from snapy import MeshBlock, MeshBlockOptions, kIDN, kIPR, kIV1, kIV2, kICY

    cfg, lz, nz, g = build_deck(a, a.moist)
    if a.gwork:
        cfg["forcing"]["const-gravity"]["gravity-work"] = a.gwork
    yaml.safe_dump(cfg, open(a.out + ".yaml", "w"), sort_keys=False)
    blk = MeshBlock(MeshBlockOptions.from_yaml(a.out + ".yaml")); blk.to(torch.device("cpu"))
    ng, nx2, dz = 3, a.nx2, lz / nz
    if a.moist:
        T0, ps, rd = 320.0, 1.0e5, 3900.0
    else:
        T0, ps, rd = 100.0, 1.0e6, RGAS / (1.5 * 1.00794e-3 + 0.15 * 4.002602e-3)
    z = (torch.arange(nz, dtype=torch.float64) + 0.5) * dz
    p = ps * torch.exp(-g * z / (rd * T0))
    col = torch.zeros(kIPR + 1, 1, 1, nz, dtype=torch.float64)
    col[kIDN, 0, 0] = p / (rd * T0); col[kIPR, 0, 0] = p
    if not a.moist or a.balance:
        col, resid, _ = snapy.balance_column(col, torch.full((nz,), dz, dtype=torch.float64), g)
    w = dict(blk.named_buffers())["hydro.D"].clone().zero_()
    ks, js = slice(ng, ng + nz), slice(ng, ng + nx2)
    for c in (kIDN, kIPR):
        w[c][..., ks] = col[c, 0, 0]
    gen = torch.Generator().manual_seed(a.seed)
    if a.noise > 0:
        dT = a.noise * torch.randn(1, 1 if a.column else nx2, nz, generator=gen, dtype=torch.float64)
        w[kIDN][:, js, ks] = w[kIDN][:, js, ks] * T0 / (T0 + dT)
    for c in (kIDN, kIPR):
        w[c][..., :ng] = w[c][..., ng:ng + 1]; w[c][..., ng + nz:] = w[c][..., ng + nz - 1:ng + nz]
    if a.moist:
        w[kICY] = 0.02; w[kICY + 1] = a.cloud
    zf = (torch.arange(w.shape[-1], dtype=torch.float64) - ng + 0.5) * dz
    uprof = a.u0 * zf / lz if a.shear else torch.full_like(zf, a.u0)
    w[kIV2] = uprof.view(1, 1, -1)
    uref = uprof[ks].view(1, 1, nz)
    bv, _ = blk.initialize({"hydro_w": w})
    nst = len(blk.module("intg").stages)
    vol = a.dx * dz * a.dx
    zc = z.view(1, 1, nz)

    def diag(t):
        u = bv["hydro_u"][:, :, js, ks]; ww = bv["hydro_w"][:, :, js, ks]
        rho = u[kIDN] + (u[kICY:].sum(0) if u.shape[0] > kICY else 0)
        wv = ww[kIV1]; uv = ww[kIV2]
        return dict(t=t, rms_w=wv.pow(2).mean().sqrt().item(), max_w=wv.abs().max().item(),
                    du_rel=((uv - uref).abs().max() / max(a.u0, 1e-30)).item(),
                    S_rho=rho.sum().item() * vol, S_m2=u[kIV2].sum().item() * vol,
                    S_E=u[kIPR].sum().item() * vol, S_EPE=(u[kIPR] + rho * g * zc).sum().item() * vol,
                    S_rhodry=u[kIDN].sum().item() * vol)

    def prof():
        ww = bv["hydro_w"][:, :, js, ks]; u = bv["hydro_u"][:, :, js, ks]
        return dict(u=ww[kIV2].mean(dim=(0, 1)).tolist(), m2=u[kIV2].mean(dim=(0, 1)).tolist())

    out = open(a.out + ".csv", "w"); keys = list(diag(0).keys()) + ["dt", "step"]
    out.write(",".join(keys) + "\n")
    def wr(d, dt, n):
        out.write(",".join(repr(d[k]) for k in keys[:-2]) + f",{dt!r},{n}\n"); out.flush()
    wr(diag(0.0), 0.0, 0)
    profs = {"0": prof()}
    t, n, redo, nxt, pdays, status, dts, w0 = 0.0, 0, 0, a.diag_dt, [1, 2, 3], "finished", [], time.time()
    tlim = a.days * 86400.0
    while t < tlim - 1e-9:
        dt = min(blk.max_time_step(bv), tlim - t)
        for s in range(nst):
            blk.forward(bv, dt, s)
        r = blk.check_redo(bv)
        if r == 1:
            redo += 1
            if redo > 50: status = "blew_up(redo>50)"; break
            continue
        if r < 0: status = "stop"; break
        blk.inc_cycle(); t += dt; n += 1; dts.append(dt)
        if t >= nxt - 1e-9 or t >= tlim - 1e-9:
            d = diag(t); wr(d, dt, n); nxt += a.diag_dt
            if not math.isfinite(d["max_w"]) or d["max_w"] > 200: status = "blew_up(max_w)"; break
        while pdays and t >= pdays[0] * 86400.0 - 1e-6:
            profs[str(pdays.pop(0))] = prof()
    ufin = bv["hydro_u"].contiguous().numpy()
    json.dump(profs, open(a.out + ".prof.json", "w"))
    summ = dict(vars(a), status=status, t_end=t, steps=n, redos=redo,
                dt_median=float(np.median(dts)) if dts else None,
                state_sha256=hashlib.sha256(ufin.tobytes()).hexdigest(),
                snapy_file=snapy.__file__, wall_s=time.time() - w0)
    json.dump(summ, open(a.out + ".json", "w"), indent=1)
    print(json.dumps({k: summ[k] for k in ("status", "t_end", "steps", "redos")}))


if __name__ == "__main__":
    main()
