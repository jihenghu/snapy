#!/usr/bin/env python3
"""One arm of the LMARS energy-flux stability test.

Builds the isothermal column, projects it onto snapy's discrete hydrostatic
balance (snapy.balance_column), adds a uniform horizontal wind u and 1e-6 K
white noise in T at fixed p, then integrates for --days model days and logs
rms/max |w| and the mid-height w(x2) row every --dt-log seconds.

usage: run_arm.py --solver lmars --u 400 --dx 5e3 --nx2 64 --out runs/b
"""
import argparse, json, math, os, signal, sys, time

import numpy as np
import torch
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
RGAS = 8.31446261815324


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", default="lmars", choices=("lmars", "hllc"))
    ap.add_argument("--u", type=float, default=0.0, help="uniform x2 wind, m/s")
    ap.add_argument("--dx", type=float, default=5.e3, help="horizontal cell size, m")
    ap.add_argument("--nx2", type=int, default=64)
    ap.add_argument("--days", type=float, default=3.0)
    ap.add_argument("--dt-log", type=float, default=864.0, help="s between log rows")
    ap.add_argument("--noise", type=float, default=None, help="override noise_T (K)")
    ap.add_argument("--implicit", type=int, default=None, help="override implicit-scheme (0 = explicit)")
    ap.add_argument("--cfl", type=float, default=None, help="override integration/cfl")
    ap.add_argument("--grav0", action="store_true",
                    help="g = 0 control: grav1 = 0, uniform p = Ps and T = T0, no balance step")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--deck", default=os.path.join(HERE, "deck.yaml"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    torch.set_num_threads(a.threads)
    import snapy
    from snapy import MeshBlock, MeshBlockOptions, kIDN, kIPR, kIV1, kIV2

    os.makedirs(a.out, exist_ok=True)
    cfg = yaml.safe_load(open(a.deck))
    cfg["dynamics"]["riemann-solver"]["type"] = a.solver
    cfg["geometry"]["cells"]["nx2"] = a.nx2
    cfg["geometry"]["bounds"]["x2max"] = a.nx2 * a.dx
    if a.implicit is not None:
        cfg["integration"]["implicit-scheme"] = a.implicit
    if a.cfl is not None:
        cfg["integration"]["cfl"] = a.cfl
    if a.grav0:
        cfg["forcing"]["const-gravity"]["grav1"] = 0.0
    prob = cfg.pop("problem")
    noise = prob["noise_T"] if a.noise is None else a.noise
    deck = os.path.join(a.out, "deck.yaml")
    yaml.safe_dump(cfg, open(deck, "w"))

    block = MeshBlock(MeshBlockOptions.from_yaml(deck))
    block.to(torch.device("cpu"))

    g = -cfg["forcing"]["const-gravity"]["grav1"]
    rd = RGAS / cfg["dynamics"]["equation-of-state"]["weight"]
    T0, ps = prob["T0"], prob["Ps"]
    nz = cfg["geometry"]["cells"]["nx1"]
    zmax = cfg["geometry"]["bounds"]["x1max"]
    dz = zmax / nz
    ng = cfg["geometry"]["cells"]["nghost"]

    # isothermal column, then snapy's own discrete hydrostatic balance (T fixed)
    z = (torch.arange(nz, dtype=torch.float64) + 0.5) * dz
    p = ps * torch.exp(-g * z / (rd * T0))
    col = torch.zeros(kIPR + 1, 1, 1, nz, dtype=torch.float64)
    col[kIDN, 0, 0] = p / (rd * T0)
    col[kIPR, 0, 0] = p
    if g > 0.:
        wb, resid, sweeps = snapy.balance_column(
            col, torch.full((nz,), dz, dtype=torch.float64), g)
    else:  # g = 0: the uniform state is an exact rest state, nothing to balance
        wb, resid, sweeps = col, 0.0, 0

    w = dict(block.named_buffers())["hydro.D"].clone().zero_()
    for c in (kIDN, kIPR):
        w[c][..., ng:ng + nz] = wb[c, 0, 0]
        w[c][..., :ng] = w[c][..., ng:ng + 1]
        w[c][..., ng + nz:] = w[c][..., ng + nz - 1:ng + nz]
    nx2 = a.nx2
    js = slice(ng, ng + nx2)
    ks = slice(ng, ng + nz)

    # white noise in T at fixed p: rho -> rho * T0 / (T0 + dT); fixed seed
    gen = torch.Generator().manual_seed(int(prob["seed"]))
    dT = noise * torch.randn(1, nx2, nz, generator=gen, dtype=torch.float64)
    w[kIDN][:, js, ks] *= T0 / (T0 + dT)
    w[kIV2][:] = a.u

    bvars, _ = block.initialize({"hydro_w": w})
    nstage = len(block.module("intg").stages)
    mid = ng + nz // 2  # x1 index of the mid-height row (z = 227.25 km)

    def diag(t):
        hw = bvars["hydro_w"][:, 0, js, ks]
        wv = hw[kIV1]
        up = hw[kIV2] - a.u
        return dict(t=t, rms_w=wv.pow(2).mean().sqrt().item(),
                    max_w=wv.abs().max().item(),
                    rms_du=up.pow(2).mean().sqrt().item(),
                    wmid=bvars["hydro_w"][kIV1, 0, js, mid].tolist())

    meta = dict(solver=a.solver, u=a.u, implicit=cfg["integration"]["implicit-scheme"],
                cfl=cfg["integration"]["cfl"], dx=a.dx, nx2=nx2, nx1=nz, dz=dz,
                g=g, Rd=rd, T0=T0, Ps=ps, noise_T=noise, seed=int(prob["seed"]),
                balance_residual=resid, balance_sweeps=sweeps,
                z_mid=float((nz // 2 + 0.5) * dz), snapy_file=snapy.__file__,
                torch=torch.__version__,
                flux_covariance=os.environ.get("SNAP_FLUX_COVARIANCE", "default(on)"))
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)

    tlim = a.days * 86400.
    t, n, redo_n, wall0 = 0.0, 0, 0, time.time()
    log = open(os.path.join(a.out, "log.jsonl"), "w")
    log.write(json.dumps(diag(t)) + "\n")
    next_log = a.dt_log
    status = "ok"
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("flag", True))
    while t < tlim:
        if stop["flag"]:
            status = "stopped early (SIGTERM)"; break
        dt = min(block.max_time_step(bvars), tlim - t)
        for s in range(nstage):
            block.forward(bvars, dt, s)
        r = block.check_redo(bvars)
        if r == 1:
            redo_n += 1
            if redo_n > 100:
                status = "too many redos"; break
            continue
        if r < 0:
            status = "check_redo stop"; break
        block.inc_cycle()
        t += dt
        n += 1
        if not math.isfinite(bvars["hydro_w"][kIV1].abs().max().item()):
            status = "non-finite"; break
        if t >= next_log - 1e-9 or t >= tlim:
            d = diag(t); d["n"] = n; d["dt"] = dt
            log.write(json.dumps(d) + "\n"); log.flush()
            next_log += a.dt_log
            if d["max_w"] > 50.:
                status = "blew up (max|w|>50)"; break
    meta.update(status=status, steps=n, redos=redo_n, t_end=t,
                wall_s=time.time() - wall0)
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(json.dumps({k: meta[k] for k in ("solver", "u", "status", "steps", "t_end", "wall_s")}))


if __name__ == "__main__":
    sys.exit(main())
