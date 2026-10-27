#!/usr/bin/env python3
"""One arm of the independent e59ed4c0 (HEVI ARK2) rerun -- cadence copy of hevi_arm.py.

Identical to hevi_arm.py at fbd01b75 except for --diag-steps: the diagnostics are also
written at these exact step numbers. Diagnostics never touch dt (no clipping to sample
times), so the time stepping is bitwise that of hevi_arm.py for any --diag-dt/--diag-steps.


Deck and initial state follow XinyueWang05/snapy lmars_energy_flux_test/run_arm.py
(the study the scheme-9 arms come from): 2-D Cartesian, x1 vertical, reflecting
walls, x2 periodic (nx2 columns of width dx), x3 width 1 m, dry H2-He
(H 1.5, He 0.15, cv_R 2.5), ideal-moist EOS, weno5 both directions, rk3, isothermal
column projected onto the discrete balance with snapy.balance_column, Gaussian
isobaric T noise (seed 20261025), uniform x2 wind.

  --setup c100 : T0 100 K, g 8.87, 450 km / 100 levels (original set)
  --setup hj   : T0 1500 K, g 23, 2570 km / 100 levels (hot-Jupiter set)

HEVI: --integrator hevi-ark2 --iters N writes integration/implicit-integrator and
integration/implicit-integrator-iterations into the deck. With --integrator rk the
keys are left out, so the same deck runs on ba2b28ce (which rejects them).

Time stepping: cfl mode (dt = block.max_time_step, redos allowed), or ladder mode
(--tend T --dtdiv k): dt0 = T / ceil(T / dt_cfl(t = 0)), dt = dt0 / k, fixed.

Writes <out>.yaml (deck), <out>.csv (diagnostics), <out>.json (summary),
<out>.final_u.npy (final conserved state incl. ghosts).
"""
import argparse, hashlib, json, math, os, time

import numpy as np
import torch
import yaml

SETUPS = {"c100": dict(T0=100.0, grav=8.87, ztop=450.0e3),
          "hj": dict(T0=1500.0, grav=23.0, ztop=2570.0e3)}

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--setup", choices=SETUPS, default="c100")
ap.add_argument("--solver", choices=["lmars", "hllc"], default="lmars")
ap.add_argument("--u", type=float, default=0.0)
ap.add_argument("--dx", type=float, default=100.0e3)
ap.add_argument("--nx2", type=int, default=64)
ap.add_argument("--nx1", type=int, default=100)
ap.add_argument("--scheme", type=int, default=9)
ap.add_argument("--integrator", choices=["rk", "hevi-ark2"], default="rk")
ap.add_argument("--iters", type=int, default=0, help="implicit-integrator-iterations (0: key absent)")
ap.add_argument("--cfl", type=float, default=0.3)
ap.add_argument("--days", type=float, default=3.0)
ap.add_argument("--tend", type=float, default=0.0, help="ladder mode end time [s]")
ap.add_argument("--dtdiv", type=int, default=0, help="ladder mode: dt = dt0 / dtdiv")
ap.add_argument("--noise", type=float, default=1.0e-6)
ap.add_argument("--seed", type=int, default=20261025)
ap.add_argument("--ps", type=float, default=1.0e6)
ap.add_argument("--diag-dt", type=float, default=3600.0)
ap.add_argument("--wmax-stop", type=float, default=1.0e3)
ap.add_argument("--diag-steps", default="", help="comma-separated step numbers to sample as well")
ap.add_argument("--init-only", action="store_true", help="save the initial conserved state and stop")
a = ap.parse_args()
S = SETUPS[a.setup]

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)
import snapy
from snapy import MeshBlock, MeshBlockOptions, kIDN, kIPR, kIV1, kIV2

NG = 3
ladder = a.tend > 0 and a.dtdiv > 0
tend = a.tend if ladder else a.days * 86400.0
intg = {"type": "rk3", "cfl": a.cfl, "implicit-scheme": a.scheme, "nlim": -1, "tlim": tend}
if a.integrator != "rk":
    intg["implicit-integrator"] = a.integrator
if a.iters > 0:
    intg["implicit-integrator-iterations"] = a.iters
cfg = {
    "reference-state": {"Tref": 0.0, "Pref": 1.0e5},
    "species": [{"name": "dry", "composition": {"H": 1.5, "He": 0.15}, "cv_R": 2.5}],
    "geometry": {"type": "cartesian",
                 "bounds": {"x1min": 0.0, "x1max": S["ztop"], "x2min": 0.0, "x2max": a.nx2 * a.dx,
                            "x3min": -0.5, "x3max": 0.5},
                 "cells": {"nx1": a.nx1, "nx2": a.nx2, "nx3": 1, "nghost": NG}},
    "dynamics": {
        "equation-of-state": {"type": "ideal-moist", "density-floor": 1.0e-10,
                              "pressure-floor": 1.0e-10, "limiter": True,
                              "max-iter": 10, "ftol": 1.0e-6},
        "reconstruct": {"vertical": {"type": "weno5", "scale": True, "shock": True},
                        "horizontal": {"type": "weno5", "scale": True, "shock": True}},
        "riemann-solver": {"type": a.solver}},
    "boundary-condition": {"external": {
        "x1-inner": "reflecting", "x1-outer": "reflecting",
        "x2-inner": "periodic", "x2-outer": "periodic",
        "x3-inner": "periodic", "x3-outer": "periodic"}},
    "integration": intg,
    "forcing": {"const-gravity": {"grav1": -S["grav"]}},
}
yml = a.out + ".yaml"
os.makedirs(os.path.dirname(os.path.abspath(yml)), exist_ok=True)
with open(yml, "w") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)
block = MeshBlock(MeshBlockOptions.from_yaml(yml))
block.to(torch.device("cpu"), torch.float64)
eos = block.module("hydro.eos")

x1v = block.buffer("coord.x1v")
dx1f = block.buffer("coord.dx1f")
il, iu = NG, NG + a.nx1
w = block.buffer("hydro.D").clone().zero_()
nvar = w.shape[0]
probe = w.clone()
probe[kIDN], probe[kIPR] = 1.0, 1.0e5
Rd = 1.0e5 / eos.compute("W->T", [probe]).flatten()[0].item()
z = x1v[il:iu]
pcol = a.ps * torch.exp(-S["grav"] * (z - z[0]) / (Rd * S["T0"]))
wi = torch.zeros(nvar, 1, w.shape[2], a.nx1, dtype=torch.float64)
wi[kIPR] = pcol
wi[kIDN] = pcol / (Rd * S["T0"])
wb, resid, sweeps = snapy.balance_column(wi.contiguous(), dx1f[il:iu].contiguous(),
                                         S["grav"], True, 1.0e-12, 400, "cartesian")
w[..., il:iu] = wb
w[..., :il] = wb[..., :1]
w[..., iu:] = wb[..., -1:]
gen = torch.Generator().manual_seed(a.seed)
dT = a.noise * torch.randn((1, a.nx2, a.nx1), generator=gen, dtype=torch.float64)
w[kIDN, :, NG:NG + a.nx2, il:iu] *= S["T0"] / (S["T0"] + dT)
w[kIV2] = a.u
bv, t = block.initialize({"hydro_w": w})
if a.init_only:
    np.save(a.out + ".init_u.npy", bv["hydro_u"].detach().cpu().contiguous().numpy())
    raise SystemExit(0)

I = (slice(None), 0, slice(NG, NG + a.nx2), slice(il, iu))
zc = z.view(1, a.nx1)
vol = a.dx * dx1f[il:iu].view(1, a.nx1) * 1.0


def diag(t):
    u = bv["hydro_u"][I]
    wv = bv["hydro_w"][I][kIV1]
    rec = {"t": t, "rms_w": wv.square().mean().sqrt().item(), "max_w": wv.abs().max().item()}
    for k, row in (("S_rho", u[kIDN]), ("S_m1", u[kIV1]), ("S_m2", u[kIV2]), ("S_E", u[kIPR]),
                   ("S_Etot", u[kIPR] + u[kIDN] * S["grav"] * zc)):
        rec[k] = (row * vol).sum().item()
    return rec


rec0 = diag(0.0)
cols = ["t", "step", "dt", "wall"] + [k for k in rec0 if k != "t"]
fcsv = open(a.out + ".csv", "w")
fcsv.write(",".join(cols) + "\n")


def wrow(rec, step, dt, wall):
    fcsv.write(",".join(repr(x) for x in [rec["t"], step, dt, wall] + [rec[k] for k in cols[4:]]) + "\n")
    fcsv.flush()


wrow(rec0, 0, 0.0, 0.0)
nstage = len(block.module("intg").stages)
dt_cfl0 = block.max_time_step(bv)
if ladder:
    n0 = math.ceil(a.tend / dt_cfl0)
    nsteps = n0 * a.dtdiv
    dt_fixed = a.tend / nsteps
status, step, redos, dts = "finished", 0, 0, []
next_diag = a.diag_dt
diag_steps = {int(x) for x in a.diag_steps.split(",") if x.strip()}
w0 = time.time()
while (step < nsteps) if ladder else (t < tend * (1 - 1e-14)):
    dt = dt_fixed if ladder else min(block.max_time_step(bv), tend - t)
    for s in range(nstage):
        block.forward(bv, dt, s)
    e = block.check_redo(bv)
    if e > 0:
        redos += 1
        if ladder or redos > 50:
            status = "redo(%d)" % redos
            break
        continue
    if e < 0:
        status = "check_redo terminated"
        break
    t += dt
    step += 1
    dts.append(dt)
    if t >= next_diag * (1 - 1e-12) or (ladder and step == nsteps) or step in diag_steps:
        rec = diag(t)
        wrow(rec, step, dt, time.time() - w0)
        while next_diag <= t * (1 + 1e-12):
            next_diag += a.diag_dt
        if not math.isfinite(rec["rms_w"]):
            status = "non-finite"
            break
        if rec["max_w"] > a.wmax_stop:
            status = "max_w>%g" % a.wmax_stop
            break
wall = time.time() - w0
rec = diag(t)
wrow(rec, step, dts[-1] if dts else 0.0, wall)
fcsv.close()
ufin = bv["hydro_u"].detach().cpu().contiguous().numpy()
np.save(a.out + ".final_u.npy", ufin)
summ = dict(vars(a))
summ.update(status=status, t_end=t, steps=step, redos=redos, wall_s=wall,
            dt_cfl0=dt_cfl0, dt_fixed=dt_fixed if ladder else None,
            dt_median=float(np.median(dts)) if dts else None,
            Rd=Rd, balance_residual=float(resid) if not torch.is_tensor(resid) else resid.max().item(),
            state_sha256=hashlib.sha256(ufin.tobytes()).hexdigest(),
            snapy_file=snapy.__file__, torch=torch.__version__)
with open(a.out + ".json", "w") as f:
    json.dump(summ, f, indent=1)
print(json.dumps({k: summ[k] for k in ("status", "t_end", "steps", "redos", "wall_s", "dt_cfl0")}))
