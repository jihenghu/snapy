#!/usr/bin/env python3
"""A uniform passive-tracer ratio r = scalar_s / rho_dry must stay uniform to round-off.
With the EOS limiter on it does not: at a large vertical Courant number the tracer outflow of a
donor cell is scaled by one factor on all its outgoing faces while the dry-air outflow is not.
Isothermal stratified column on a geometric x1 grid (nx1 32, ratio 4), projected with
snapy.balance_column, nx2 = 4 identical columns, wind (5 sin, 10 cos), vapour 0.02 below 12 km,
Gaussian pressure bump of amplitude 1. One accepted RK3 step: a step that check_redo rejects is
restored and redone at dt/2. Prints max|r/r0-1| and, at the first stage that departs, the
per-donor factor F_scalar/(r0 F_dry) on the outgoing faces of the worst cell (must be 1).
Exits 1 when max|r/r0-1| exceeds 1e-12.
usage: python tracer_ratio_limiter_repro.py [--limiter on|off] [--dry] [--relax] [--scheme 1] [--courant 30]
"""
import argparse, math, os, sys, tempfile
import torch, yaml
import snapy
from snapy import MeshBlock, MeshBlockOptions, kICY, kIDN, kIPR, kIV1

torch.set_default_dtype(torch.float64)
NX1, NX2, ZTOP, T0, RG, G, R0, TOL = 32, 4, 3.2e4, 320., 3900., 10., 1e-3, 1e-12


def deck(a):
    d = {
        "reference-state": {"Tref": 0., "Pref": 1.e5},
        "species": [{"name": "dry", "composition": {"H": 1.6667, "He": 0.16667}, "cv_R": 2.5},
                    {"name": "vapor", "composition": {"H": 2, "O": 1}, "cv_R": 2.5, "u0_R": 0.},
                    {"name": "cloud", "composition": {"H": 2, "O": 1}, "cv_R": 9.0, "u0_R": -3430.}],
        "reactions": [{"equation": "vapor <=> cloud", "type": "nucleation",
                       "rate-constant": {"formula": "h2o_ideal"}}],
        "geometry": {"type": "cartesian",
                     "bounds": {"x1min": 0., "x1max": ZTOP, "x2min": 0., "x2max": 4.e6,
                                "x3min": 0., "x3max": 1.e3},
                     "cells": {"nx1": NX1, "nx2": NX2, "nx3": 1, "nghost": 3,
                               "x1rat": 4. ** (1. / (NX1 - 1))}},
        "distribute": {"layout": "slab", "nb2": 1, "nb3": 1, "verbose": False},
        "dynamics": {"equation-of-state": {"type": "ideal-moist", "density-floor": 1.e-10,
                                           "pressure-floor": 1.e-10, "limiter": a.limiter == "on"},
                     "reconstruct": {"vertical": {"type": "weno5", "scale": True, "shock": True},
                                     "horizontal": {"type": "weno5", "scale": True, "shock": True}},
                     "riemann-solver": {"type": "lmars"}},
        "boundary-condition": {"external": {"x1-inner": "reflecting", "x1-outer": "reflecting",
                                            "x2-inner": "periodic", "x2-outer": "periodic",
                                            "x3-inner": "periodic", "x3-outer": "periodic"}},
        "integration": {"type": "rk3", "cfl": 0.9, "implicit-scheme": a.scheme, "nlim": -1,
                        "tlim": 1.e9, "ncycle_out": 0},
        "forcing": {"const-gravity": {"grav1": -G}},
        "scalar": {"nvar": 1, "names": ["tracer"], "reconstruct": {"type": "weno5", "shock": False}},
    }
    if a.relax:
        d["forcing"]["relax-bot-comp"] = {"tau": 3600., "species": ["vapor"], "xfrac": [0.2]}
    return d


def donor_factors(B, j, i):
    """F_scalar/(r0 F_dry) on the faces through which cell (x2 j, x1 i) loses dry air."""
    out = []
    for name, lo, hi in (("x1", (0, 3 + j, 3 + i), (0, 3 + j, 4 + i)),
                         ("x2", (0, 3 + j, 3 + i), (0, 4 + j, 3 + i))):
        Fd, Fs = B[f"hydro.F{name[1]}"][kIDN], B[f"scalar.F{name[1]}"][0]
        for side, ix, sgn in (("lo", lo, -1), ("hi", hi, 1)):
            if sgn * float(Fd[ix]) > 0:
                out.append(f"{name}{side} {float(Fs[ix] / (R0 * Fd[ix])):.6f}")
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limiter", choices=("on", "off"), default="on")
    ap.add_argument("--dry", action="store_true", help="vapour 0 everywhere")
    ap.add_argument("--relax", action="store_true", help="relax bottom vapour to 0.2 (tau 3600 s)")
    ap.add_argument("--scheme", type=int, default=1)
    ap.add_argument("--courant", type=float, default=30.)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as wd:
        p = os.path.join(wd, "deck.yaml")
        with open(p, "w") as f:
            yaml.safe_dump(deck(a), f)
        block = MeshBlock(MeshBlockOptions.from_yaml(p))
    coord = block.module("coord")
    f = coord.buffer("x1f").double()[3:3 + NX1 + 1]
    h, hs = f[1:] - f[:-1], RG * T0 / G
    pbar = 1.e5 * hs * (torch.exp(-f[:-1] / hs) - torch.exp(-f[1:] / hs)) / h  # exact cell means
    col = torch.zeros((5, 1, 1, NX1))
    col[0, 0, 0], col[4, 0, 0] = pbar / (RG * T0), pbar
    wb, _, _ = snapy.balance_column(col, h, G, wall_clamp=True, rtol=1.e-13, max_iter=400,
                                    stretched=True)
    w = dict(block.named_buffers())["hydro.D"].clone().zero_()
    for k, src in ((kIDN, 0), (kIPR, 4)):
        w[k][..., 3:3 + NX1] = wb[src]
        w[k][..., :3] = wb[src][..., :1]
        w[k][..., 3 + NX1:] = wb[src][..., -1:]
    z = coord.buffer("x1v").double()
    w[kICY] = 0. if a.dry else torch.where(z < 1.2e4, 0.02, 0.).view(1, 1, -1)
    w[kIPR] *= (1. + torch.exp(-((z - 0.5 * ZTOP) / 2.e3) ** 2 / 2)).view(1, 1, -1)
    w[kIV1] = (5. * torch.sin(math.pi * z / ZTOP)).view(1, 1, -1)
    w[kIV1 + 1] = (10. * torch.cos(math.pi * z / ZTOP)).view(1, 1, -1)
    v, _ = block.initialize({"hydro_w": w, "scalar_r": torch.full((1,) + tuple(w.shape[1:]), R0)})
    B = dict(block.named_buffers())
    save = {k: t.clone() for k, t in v.items()}
    dt = a.courant * float(h.min()) / math.sqrt(1.4 * RG * T0)
    for attempt in range(20):
        dev, first = 0., None
        for stage in range(3):
            block.forward(v, dt, stage)
            dd = (v["scalar_s"][0, 0, 3:-3, 3:-3] / v["hydro_u"][kIDN][0, 3:-3, 3:-3] / R0 - 1).abs()
            dev = max(dev, float(dd.max()))
            if first is None and dev > TOL:
                j, i = (int(x) for x in (dd == dd.max()).nonzero()[0])
                first = f"stage {stage}, cell x2 {j} x1 {i}: donor F_scalar/(r0 F_dry) = " + \
                    donor_factors(B, j, i)
        err = block.check_redo(v)
        print(f"attempt {attempt}: dt = {dt:.4g} s, check_redo = {err}", flush=True)
        if err == 0:
            break
        for k in v:
            v[k].copy_(save[k])
        dt *= 0.5
    else:
        print("no step accepted")
        return 2
    print(f"max|r/r0-1| = {dev:.3e}" + (f"; first departure at {first}" if first else ""))
    bad = dev > TOL
    print(f"{'FAIL' if bad else 'PASS'} (limiter {a.limiter}, {'dry' if a.dry else 'moist'}, "
          f"relax {a.relax}, implicit-scheme {a.scheme}, C {a.courant:g})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
