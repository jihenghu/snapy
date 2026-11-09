#!/usr/bin/env python3
"""dynamics/conversion-order 4 on a radial x1, where a cell holds the r^2 dr average.

(a) The conversion itself, on a gnomonic-equiangle and a spherical-polar block, r in [1, 2], one cell in x2 and
    x3: u is set to the exact r^2-weighted averages of rho = 1 + 0.5 sin(4r) exp(-r/2), v1 = 0.1 cos(3r),
    p = 1 + 0.2 sin(2r), and one stage gives hydro_w. Its velocity row against the exact r^2 average of v1, away
    from the walls, at nx1 = 64, 128, 256: key 4's fitted order must be >= 3.8 (key 2's is printed). The point
    value sits at the coordinate's x1v: the volume centroid on spherical-polar, the midpoint on the cubed sphere.
(b) End to end on the spherical-polar shell: a right-moving isentropic pulse, c = 1 + 0.03 exp(-((r - 1.4)/0.07)^2),
    from the exact r^2 u averages, WENO5, LMARS, RK3 to t = 0.12, nx1 = 64, 128, 256 against 1024 on the nested
    faces, the L1 of the cell mass. With SNAP_X1_CENTROID_EXACT set (the r^2-exact radial pressure force) key 4's
    order must be >= 3.8; without it the plain pressure-gradient source is second order, so it is only printed.

  python test_conversion_order_radial.py [--device cpu|cuda]
"""
import argparse
import os
import tempfile

import numpy as np
import torch
import yaml
from snapy import MeshBlock, MeshBlockOptions, kIDN, kIPR

NG, G, T, NREF, NX = 3, 1.4, 0.12, 1024, (64, 128, 256)
X, WQ = (torch.from_numpy(v) for v in np.polynomial.legendre.leggauss(8))
ANGLES = {"spherical-polar": {"x2min": 1., "x2max": 2., "x3min": 0., "x3max": 1.},
          "gnomonic-equiangle": {"x2min": -.05, "x2max": .05, "x3min": -.05, "x3max": .05}}


def block(geo, nx, key, device):
    weno = {"type": "weno5", "scale": True, "shock": False}
    cfg = {"geometry": {"type": geo, "cells": {"nx1": nx, "nx2": 1, "nx3": 1, "nghost": NG},
                        "bounds": {"x1min": 1., "x1max": 2., **ANGLES[geo]}},
           "boundary-condition": {"external": {"x1-inner": "reflecting", "x1-outer": "reflecting"}},
           "dynamics": {"equation-of-state": {"type": "ideal-gas", "gammad": G, "limiter": False},
                        "reconstruct": {"vertical": weno, "horizontal": weno},
                        "riemann-solver": {"type": "lmars"}, "conversion-order": key},
           "integration": {"type": "rk3", "cfl": 0.4, "implicit-scheme": 0, "nlim": -1, "tlim": 1.e9}}
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, dir=os.getcwd()) as f:
        yaml.safe_dump(cfg, f)
    try:
        b = MeshBlock(MeshBlockOptions.from_yaml(f.name))
    finally:
        os.unlink(f.name)
    b.to(torch.device(device), torch.float64)
    x1f = b.buffer("coord.x1f").cpu().double()
    r = (x1f[:-1, None] + x1f[1:, None] + (x1f[1:, None] - x1f[:-1, None]) * X) / 2
    return b, x1f, r, WQ * r * r


def start(b, r, wr, rho, v, p):
    """initialise from the exact r^2 u averages: w = W(u)"""
    avg = lambda q: (q * wr).sum(-1) / wr.sum(-1)
    a, m, e = avg(rho), avg(rho * v), avg(p / (G - 1) + rho * v * v / 2)
    w = b.buffer("hydro.D").clone().zero_()
    w[kIDN], w[1], w[kIPR] = a.to(w), (m / a).to(w), ((G - 1) * (e - m * m / a / 2)).to(w)
    return b.initialize({"hydro_w": w})[0], avg(v)


def fit(err):
    return -np.polyfit(np.log(NX), np.log(err), 1)[0]


def conversion(geo, key, device):
    err = []
    for nx in NX:
        b, _, r, wr = block(geo, nx, key, device)
        rho = 1. + .5 * torch.sin(4. * r) * torch.exp(-r / 2.)
        bv, v = start(b, r, wr, rho, .1 * torch.cos(3. * r), 1. + .2 * torch.sin(2. * r))
        b.forward(bv, 1.e-12, 0)
        s = slice(2 * NG, -2 * NG)
        err.append(float((bv["hydro_w"][1, 0, 0].cpu()[s] - v[s]).abs().max()))
    print(f"{geo} conversion key {key}: max err {err} order {fit(err):.2f}")
    return fit(err)


def pulse(nx, key, dt, device):
    b, x1f, r, wr = block("spherical-polar", nx, key, device)
    c = 1. + .03 * torch.exp(-((r - 1.4) / .07) ** 2)
    bv, _ = start(b, r, wr, c ** (2 / (G - 1)), 2 / (G - 1) * (c - 1.), c ** (2 * G / (G - 1)) / G)
    for _ in range(round(T / dt)):
        b.inc_cycle()
        for st in range(len(b.intg.stages)):
            b.forward(bv, dt, st)
    vol = ((x1f[1:] ** 3 - x1f[:-1] ** 3) / 3)[NG:-NG]  # the r^2 dr cell measure
    return bv["hydro_u"][kIDN, 0, 0, NG:-NG].cpu() * vol


def end_to_end(key, device):
    dt = .25 / NREF
    ref = pulse(NREF, key, dt, device)
    err = [float((pulse(nx, key, dt, device) - ref.view(nx, NREF // nx).sum(1)).abs().sum()) for nx in NX]
    print(f"spherical pulse key {key} (SNAP_X1_CENTROID_EXACT={os.environ.get('SNAP_X1_CENTROID_EXACT', '')}): "
          f"L1 {err} order {fit(err):.2f}")
    return fit(err)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    d = ap.parse_args().device
    if d == "cuda" and not torch.cuda.is_available():
        raise SystemExit(125)
    bad = []
    for geo in ANGLES:
        conversion(geo, 2, d)
        bad += [f"{geo} conversion"] if conversion(geo, 4, d) < 3.8 else []
    end_to_end(2, d)
    p = end_to_end(4, d)
    bad += ["spherical pulse"] if os.environ.get("SNAP_X1_CENTROID_EXACT") and p < 3.8 else []
    assert not bad, bad
