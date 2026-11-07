#!/usr/bin/env python3
"""#280: on a stretched x1 (x1rat), 6 straight steps equal 3 steps, a restart
from the final dump and 3 more, bitwise; the restart resumes at cycle 3."""
import argparse
import math
import os
import tempfile
import torch
import snapy
from snapy import kIDN, kIPR, kIV2

DECK = """reference-state: {Tref: 0., Pref: 1.e5}
species: [{name: dry, composition: {O: 0.42, N: 1.56, Ar: 0.01}, cv_R: 2.5}]
dynamics:
  equation-of-state: {type: ideal-gas, limiter: false}
  reconstruct: {vertical: {type: weno5}, horizontal: {type: weno5}}
  riemann-solver: {type: lmars}
scalar: {nvar: 1, names: [q], reconstruct: {type: weno5}, riemann-solver: {type: upwind}}
geometry:
  type: cartesian
  cells: {nx1: 16, nx2: 8, nx3: 1, nghost: 3, x1rat: 1.05}
  bounds: {x1min: 0., x1max: 1.e4, x2min: 0., x2max: 2.e4, x3min: 0., x3max: 1.}
boundary-condition:
  external: {x1-inner: reflecting, x1-outer: reflecting, x2-inner: periodic, x2-outer: periodic}
forcing: {const-gravity: {grav1: -9.8}}
integration: {type: rk3, cfl: 0.8, tlim: 1.e12}
outputs: [{type: restart, dt: 1.e12}]
"""

def run(name, nlim, restart=None):
    os.makedirs(name)
    os.chdir(name)
    open("split.yaml", "w").write(DECK)
    mesh = snapy.Mesh(snapy.MeshOptions.from_yaml("split.yaml"))
    b = mesh.blocks[0]
    b.to(torch.device(device))
    if restart:
        state, t = mesh.initialize_from_restart(restart)
    else:
        w = dict(b.named_buffers())["hydro.D"].clone().zero_()
        x1 = b.module("coord").buffer("x1v").to(w).view(1, 1, -1)
        x2 = b.module("coord").buffer("x2v").to(w).view(1, -1, 1)
        w[kIPR] = 1.e5 * torch.exp(-x1 / 1.e4)
        w[kIDN] = w[kIPR] / (287. * (300. + 6. * torch.exp(-((x1 - 3.e3)**2 + (x2 - 1.e4)**2) / 2.e6)))
        w[kIV2] = 5. * torch.sin(2. * math.pi * x2 / 2.e4)
        q = dict(b.named_buffers())["scalar.D"].clone().fill_(.01) + .005 * torch.cos(x2 / 3.e3)
        state, t = mesh.initialize([{"hydro_w": w, "scalar_r": q}])
    start = cycle = b.cycle()
    while cycle < nlim:  # stop(cycle, t) of the example drivers
        dt = mesh.max_time_step(state)
        for stage in range(len(b.module("intg").stages)):
            mesh.forward(state, dt, stage)
        assert mesh.check_redo(state) == 0
        cycle += 1
        mesh.set_cycle(cycle)
        t += dt
    mesh.finalize(state, t)
    os.chdir("..")
    return start, t, state[0], b.module("coord").buffer("x1f")

p = argparse.ArgumentParser()
p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
device = os.environ["DEVICE"] = p.parse_args().device  # restart loads to DEVICE
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    _, t0, a, fa = run("straight", 6)
    run("half", 3)
    start, t1, b, fb = run("rest", 6, os.path.join(tmp, "half", "split.final.restart"))
assert start == 3 and t0 == t1, (start, t0, t1)
for key in ("hydro_u", "hydro_w", "scalar_s"):
    assert torch.equal(a[key], b[key]), (key, (a[key] - b[key]).abs().max().item())
assert torch.equal(fa, fb)
