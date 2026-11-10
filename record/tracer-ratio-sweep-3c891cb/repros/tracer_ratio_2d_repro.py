#!/usr/bin/env python3
"""A uniform passive-tracer ratio r = scalar_s / rho_dry must stay uniform to round-off.
It does on a single column (nx2 = 1) but not on nx2 = 4 identical columns (x2-uniform, no wind).
Isothermal stratified column on a geometric x1 grid, projected with snapy.balance_column, plus a
Gaussian pressure bump; vapour 0 (dry), no forcing, EOS limiter off, one RK3 step.
Prints max|r/r0-1| for nx2 = 4 and nx2 = 1, and at stage 0 the implied x1 face ratio
F_scalar / (r0 F_rho) (must be 1). Exits 1 when nx2 = 4 exceeds 1e-12.
usage: python tracer_ratio_2d_repro.py [--scheme 1] [--courant 15]   (--scheme 0: explicit only)
"""
import argparse, math, os, sys, tempfile
import torch, yaml
import snapy
from snapy import MeshBlock, MeshBlockOptions, kICY, kIDN, kIPR

torch.set_default_dtype(torch.float64)
NX1, ZTOP, T0, RG, G, R0 = 8, 3.2e4, 320., 3900., 10., 1e-3


def deck(nx2, scheme):
    return {
        "reference-state": {"Tref": 0., "Pref": 1.e5},
        "species": [{"name": "dry", "composition": {"H": 1.6667, "He": 0.16667}, "cv_R": 2.5},
                    {"name": "vapor", "composition": {"H": 2, "O": 1}, "cv_R": 2.5, "u0_R": 0.},
                    {"name": "cloud", "composition": {"H": 2, "O": 1}, "cv_R": 9.0, "u0_R": -3430.}],
        "reactions": [{"equation": "vapor <=> cloud", "type": "nucleation",
                       "rate-constant": {"formula": "h2o_ideal"}}],
        "geometry": {"type": "cartesian",
                     "bounds": {"x1min": 0., "x1max": ZTOP, "x2min": 0., "x2max": 4.e6,
                                "x3min": 0., "x3max": 1.e3},
                     "cells": {"nx1": NX1, "nx2": nx2, "nx3": 1, "nghost": 3,
                               "x1rat": 4. ** (1. / (NX1 - 1))}},
        "distribute": {"layout": "slab", "nb2": 1, "nb3": 1, "verbose": False},
        "dynamics": {"equation-of-state": {"type": "ideal-moist", "density-floor": 1.e-10,
                                           "pressure-floor": 1.e-10, "limiter": False},
                     "reconstruct": {"vertical": {"type": "weno5", "scale": True, "shock": True},
                                     "horizontal": {"type": "weno5", "scale": True, "shock": True}},
                     "riemann-solver": {"type": "lmars"}},
        "boundary-condition": {"external": {"x1-inner": "reflecting", "x1-outer": "reflecting",
                                            "x2-inner": "periodic", "x2-outer": "periodic",
                                            "x3-inner": "periodic", "x3-outer": "periodic"}},
        "integration": {"type": "rk3", "cfl": 0.9, "implicit-scheme": scheme, "nlim": -1,
                        "tlim": 1.e9, "ncycle_out": 0},
        "forcing": {"const-gravity": {"grav1": -G}},
        "scalar": {"nvar": 1, "names": ["tracer"], "reconstruct": {"type": "weno5", "shock": False}},
    }


def run(nx2, scheme, courant):
    with tempfile.TemporaryDirectory() as wd:
        p = os.path.join(wd, "deck.yaml")
        with open(p, "w") as f:
            yaml.safe_dump(deck(nx2, scheme), f)
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
    w[kICY] = 0.
    z = coord.buffer("x1v").double()
    w[kIPR] *= (1. + torch.exp(-((z - 0.5 * ZTOP) / 2.e3) ** 2 / 2)).view(1, 1, -1)
    v, _ = block.initialize({"hydro_w": w, "scalar_r": torch.full((1,) + tuple(w.shape[1:]), R0)})
    B = dict(block.named_buffers())
    J = slice(3, -3) if nx2 > 1 else slice(None)
    dt = courant * float(h.min()) / math.sqrt(1.4 * RG * T0)
    dev, face = 0., None
    for stage in range(3):
        block.forward(v, dt, stage)
        if stage == 0:
            Fr, Fs = B["hydro.F1"][kIDN][0, J, 3:3 + NX1 + 1], B["scalar.F1"][0, 0, J, 3:3 + NX1 + 1]
            face = torch.where(Fr != 0, Fs / (R0 * Fr), torch.ones_like(Fr))[0]
        dev = max(dev, float((v["scalar_s"][0, 0, J, 3:-3] / v["hydro_u"][kIDN][0, J, 3:-3] / R0 - 1)
                             .abs().max()))
    return dev, face


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scheme", type=int, default=1)
    ap.add_argument("--courant", type=float, default=15.)
    a = ap.parse_args()
    out = {}
    for nx2 in (4, 1):
        dev, face = run(nx2, a.scheme, a.courant)
        out[nx2] = dev
        print(f"nx2={nx2}: max|r/r0-1| = {dev:.3e}; stage-0 x1 faces F_scalar/(r0 F_rho) =",
              " ".join(f"{float(x):.4f}" for x in face), flush=True)
    bad = out[4] > 1e-12
    print(f"{'FAIL' if bad else 'PASS'} (implicit-scheme {a.scheme}, C {a.courant:g})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
