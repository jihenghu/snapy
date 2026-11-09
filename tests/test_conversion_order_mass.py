#!/usr/bin/env python3
"""dynamics/conversion-order 4 conserves mass at reflecting x1 walls and at in-process x1 seams, and its
temporary point state does not trip the EOS limiter.

(a), (b) Two right-moving acoustic pulses, c = 1 + 0.03 exp(-((x - x0) / 0.07)^2), x0 = 0.08 (against the inner
    wall) and 0.45 (across the seam at 0.5), ideal gas, WENO5, LMARS, nx1 = 64 on [0, 1] between reflecting walls,
    as (a) one block and (b) two x1 blocks in one process: after 40 steps |M - M0| / M0 <= 1e-13, keys 2 and 4.
    (b') a 2:1 jump in rho and p exactly on that seam, two blocks, 40 steps, the same bound.
(c) The EOS limiter on (density floor 1e-3) and a 4-cell density dip of 0.0405 in rho = p = 1: u - L u is
    positive but below the floor at the dip's edges. 20 steps with the driver's redo loop must take no redo.
(d) A stable moist column (ideal-moist, limiter on, g = 10, isothermal, 10 km) with a vapor step to zero at 5 km,
    or a cloud band at 4-5 km: u - L u has negative species next to the zeros. 20 steps, no redo.

  python test_conversion_order_mass.py [--device cpu|cuda]
"""
import argparse
import os
import tempfile

import torch
import yaml
from snapy import Mesh, MeshOptions, kICY, kIDN, kIPR

G, NX, TOL = 1.4, 64, 1.e-13


def mesh(key, nb1, limiter=False, moist=False):
    bc = {f"x{d}-{s}": ("reflecting" if d == 1 else "periodic") for d in (1, 2, 3) for s in ("inner", "outer")}
    weno = {"type": "weno5", "scale": True, "shock": False}
    eos = {"type": "ideal-gas", "gammad": G, "limiter": limiter, "density-floor": 1.e-3, "pressure-floor": 1.e-3,
           "temperature-floor": 1.e-12}
    cfg = {"geometry": {"type": "cartesian", "cells": {"nx1": NX, "nx2": 1, "nx3": 1, "nghost": 3},
                        "bounds": {"x1min": 0., "x1max": 1., "x2min": 0., "x2max": 1., "x3min": 0., "x3max": 1.}},
           "boundary-condition": {"external": bc},
           "distribute": {"layout": "cubed" if nb1 > 1 else "slab", "nb1": nb1, "nb2": 1, "nb3": 1,
                          "blocks_per_process": nb1},
           "dynamics": {"equation-of-state": eos, "reconstruct": {"vertical": weno, "horizontal": weno},
                        "riemann-solver": {"type": "lmars"}, "conversion-order": key},
           "integration": {"type": "rk3", "cfl": 0.4, "implicit-scheme": 0, "nlim": -1, "tlim": 1.e9}}
    if moist:
        cfg["reference-state"] = {"Tref": 0., "Pref": 1.e5}
        cfg["species"] = [{"name": "dry", "composition": {"H": 1.6667, "He": 0.16667}, "cv_R": 2.5},
                          {"name": "vapor", "composition": {"H": 2, "O": 1}, "cv_R": 2.5, "u0_R": 0.},
                          {"name": "cloud", "composition": {"H": 2, "O": 1}, "cv_R": 9.0, "u0_R": -3430.}]
        cfg["reactions"] = [{"equation": "vapor <=> cloud", "type": "nucleation",
                             "rate-constant": {"formula": "h2o_ideal"}}]
        cfg["geometry"]["bounds"].update(x1max=1.e4)
        cfg["dynamics"]["equation-of-state"] = {"type": "ideal-moist", "density-floor": 1.e-10,
                                                "pressure-floor": 1.e-10, "limiter": True}
        cfg["forcing"] = {"const-gravity": {"grav1": -10.}}
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, dir=os.getcwd()) as f:
        yaml.safe_dump(cfg, f)
    try:
        options = MeshOptions.from_yaml(f.name)
        options.blocks_per_process(nb1)
        m = Mesh(options)
    finally:
        os.unlink(f.name)
    assert len(list(m.blocks)) == nb1
    return m


def run(m, init, nstep, device):
    """init(x1v) -> {w row: values}; returns (relative mass drift, redos, trips)"""
    blocks = list(m.blocks)
    state = []
    for b in blocks:
        b.to(torch.device(device), torch.float64)
        w = b.buffer("hydro.D").clone().zero_()
        for row, val in init(b.buffer("coord.x1v").double().cpu()).items():
            w[row] = val.to(w)
        state.append({"hydro_w": w})
    state, _ = m.initialize(state)
    parts = [b.part((0, 0, 0), False)[1:] for b in blocks]
    dx = [b.buffer("coord.dx1f").double().cpu()[sl[-1]] for b, sl in zip(blocks, parts)]
    mass = lambda: sum(float((s["hydro_u"][kIDN][sl].cpu() * h).sum()) for s, sl, h in zip(state, parts, dx))
    m0, redos, cycle = mass(), 0, 0
    while cycle < nstep:
        m.set_cycle(cycle + 1)
        dt = m.max_time_step(state)
        for st in range(len(blocks[0].module("intg").stages)):
            m.forward(state, dt, st)
        err = m.check_redo(state)
        assert err >= 0, f"terminated after {redos} redos at cycle {cycle}"
        redos, cycle = redos + (err > 0), cycle + (err == 0)
    assert all(torch.isfinite(s["hydro_u"]).all() for s in state)
    trips = sum(int(dict(b.named_buffers()).get("hydro.conversion_trips", torch.zeros(1)).sum()) for b in blocks)
    return abs(mass() - m0) / m0, redos, trips


def pulses(x):
    c = 1. + .03 * (torch.exp(-((x - .08) / .07) ** 2) + torch.exp(-((x - .45) / .07) ** 2))
    return {kIDN: c ** (2 / (G - 1)), 1: 2 / (G - 1) * (c - 1.), kIPR: c ** (2 * G / (G - 1)) / G}


def jump(x):
    rho = torch.where(x < .5, 1., .5).to(x.dtype)
    return {kIDN: rho, kIPR: rho}


def dip(x):
    return {kIDN: torch.where((x > .45) & (x < .45 + 4. / NX), .0405, 1.).to(x.dtype), kIPR: 1. + 0. * x}


def column(cloud):
    def init(z):
        p = 1.e5 * torch.exp(-z * 10. / (3900. * 320.))
        q = (1.e-3 + 0. * z, torch.where((z > 4.e3) & (z < 5.e3), 1.e-4, 0.)) if cloud else \
            (torch.where(z < 5.e3, 2.e-3, 0.), 0. * z)
        return {kIDN: p / (3900. * 320.), kIPR: p, kICY: q[0].to(z.dtype), kICY + 1: q[1].to(z.dtype)}
    return init


def main(device):
    bad = []
    for key in (2, 4):
        for name, nb1, init in (("pulses", 1, pulses), ("pulses", 2, pulses), ("seam jump", 2, jump)):
            drift, redos, trips = run(mesh(key, nb1), init, 40, device)
            print(f"mass {name} key {key} blocks {nb1}: |dM|/M {drift:.2e} redos {redos} trips {trips}")
            bad += [f"mass {name} key {key} blocks {nb1}"] if drift > TOL else []
        for name, m, init in (("dip", mesh(key, 1, limiter=True), dip),
                              ("moist vapor step", mesh(key, 1, moist=True), column(False)),
                              ("moist cloud band", mesh(key, 1, moist=True), column(True))):
            try:
                drift, redos, trips = run(m, init, 20, device)
            except AssertionError as e:
                drift, redos, trips = float("nan"), str(e), 0
            print(f"{name} key {key}: redos {redos} trips {trips} |dM|/M {drift:.2e}")
            bad += [f"{name} key {key}"] if redos else []
    assert not bad, bad


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    d = p.parse_args().device
    if d == "cuda" and not torch.cuda.is_available():
        raise SystemExit(125)
    main(d)
