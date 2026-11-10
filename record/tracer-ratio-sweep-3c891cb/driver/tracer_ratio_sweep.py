#!/usr/bin/env python3
"""Tracer/species ratio sweep: max |r/r0 - 1| per arm, gate <= 1e-13 on every arm.

Runs the two neutral #338 repros (tracer_ratio_2d_repro.py, tracer_ratio_limiter_repro.py)
unchanged, as subprocesses, over the cross product
    dim {2D, 3D} x covariance {on, off} x limiter {on, off} x scheme {0, 9}
    x settling {off, on} x grid {stretched, uniform}
Covariance is set through SNAP_FLUX_COVARIANCE (read once per process, so one process per arm).
Every combination a repro has no option for is written as a SKIP row with its reason in
<out>/tracer_ratio_skipped.csv; nothing is dropped. The limiter repro's own extra switches
(--dry, --relax) are swept on top for every combination it supports.

Plus one cubed-sphere C12 moist arm (six panels, 12x12 each, limiter on, 50 steps, CPU), built
from tests/test_flux_positivity_cubedsphere.yaml in the style of the repros: a neutral tracer at
a fixed ratio R0 to the dry density and a uniform vapour ratio, under a solid-body wind and a
pressure bump; max |r/r0 - 1| over all interior cells, all stages and all steps, for both.

usage: python tracer_ratio_sweep.py --repros DIR --snapy-src DIR [--out DIR]
exit 0 only if every run arm has max_dev <= 1e-13 (NaN fails), 1 otherwise.
"""
import argparse
import csv
import itertools
import math
import os
import re
import subprocess
import sys
import tempfile

TOL = 1e-13
R0 = 1e-3
COLS = ["arm", "repro", "dim", "covariance", "limiter", "scheme", "settling", "grid", "steps",
        "max_dev", "pass"]
FLOAT = r"([-+0-9.eE]+|nan|inf|-inf)"


def sh(cmd, cov, timeout=1800):
    env = dict(os.environ, SNAP_FLUX_COVARIANCE="1" if cov == "on" else "0")
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def skip_reason(repro, dim, lim, settling, grid):
    """Why a repro cannot run this combination as written (None: it can)."""
    why = []
    if dim == "3D":
        why.append("deck fixes nx3 = 1 and indexes x3 cell 0 (no 3-D option)")
    if grid == "uniform":
        why.append("deck fixes x1rat = 4^(1/(nx1-1)) (no uniform-grid option)")
    if settling == "on":
        why.append("deck has no sedimentation block (no settling option)")
    if repro == "2d" and lim == "on":
        why.append("deck fixes the EOS limiter off (no --limiter option)")
    return "; ".join(why) or None


def run_repros(rdir, rows, skipped):
    combos = itertools.product(("2D", "3D"), ("on", "off"), ("on", "off"), (0, 9),
                               ("off", "on"), ("stretched", "uniform"))
    for dim, cov, lim, scheme, settling, grid in combos:
        for repro in ("2d", "limiter"):
            base = dict(repro=repro, dim=dim, covariance=cov, limiter=lim, scheme=scheme,
                        settling=settling, grid=grid)
            tag = f"{repro}-{dim}-cov{cov}-lim{lim}-s{scheme}-set{settling}-{grid}"
            why = skip_reason(repro, dim, lim, settling, grid)
            if why:
                rows.append(dict(base, arm=tag, steps="", max_dev="", **{"pass": "SKIP"}))
                skipped.append((tag, why))
                continue
            if repro == "2d":
                rc, out = sh([sys.executable, os.path.join(rdir, "tracer_ratio_2d_repro.py"),
                              "--scheme", str(scheme)], cov)
                print(f"--- {tag} (rc {rc})\n{out.strip()}", flush=True)
                # the repro runs nx2 = 4 (the 2-D block) and nx2 = 1 (the single column)
                for nx2, dname in ((4, "2D"), (1, "1D-column")):
                    m = re.search(rf"nx2={nx2}: max\|r/r0-1\| = {FLOAT}", out)
                    dev = float(m.group(1)) if m else math.nan
                    rows.append(dict(base, arm=f"{tag}-nx2={nx2}", dim=dname,
                                     steps="1 (3 stages)", max_dev=f"{dev:.3e}",
                                     **{"pass": dev <= TOL}))
                continue
            for dry, relax in itertools.product((False, True), (False, True)):
                arm = tag + ("-dry" if dry else "-moist") + ("-relax" if relax else "")
                cmd = [sys.executable, os.path.join(rdir, "tracer_ratio_limiter_repro.py"),
                       "--limiter", lim, "--scheme", str(scheme)]
                cmd += ["--dry"] if dry else []
                cmd += ["--relax"] if relax else []
                rc, out = sh(cmd, cov)
                print(f"--- {arm} (rc {rc})\n{out.strip()}", flush=True)
                if "no step accepted" in out:
                    rows.append(dict(base, arm=arm, steps="0", max_dev="", **{"pass": "SKIP"}))
                    skipped.append((arm, "repro rejected it: check_redo accepted no step"))
                    continue
                m = re.search(rf"max\|r/r0-1\| = {FLOAT}", out)
                dev = float(m.group(1)) if m else math.nan
                nat = len(re.findall(r"^attempt \d+:", out, re.M))
                rows.append(dict(base, arm=arm, steps=f"1 accepted ({nat} attempts)",
                                 max_dev=f"{dev:.3e}", **{"pass": dev <= TOL}))


# ---------------------------------------------------------------- cubed sphere C12 moist
MOIST_SPECIES = [
    {"name": "vapor", "composition": {"H": 2, "O": 1}, "cv_R": 3.5},
    {"name": "cloud", "composition": {"H": 2, "O": 1}, "cv_R": 9.0, "u0_R": -3430.0},
]
MOIST_REACTIONS = [{"equation": "vapor <=> cloud", "type": "nucleation",
                    "rate-constant": {"formula": "h2o_ideal"}}]
PRES, QV, NSTEP = 1.1e6, 0.02, 50  # warm (~313 K at rho 1), unsaturated: cloud stays 0


def cs_arm(src):
    """Run the C12 moist deck; print max|r/r0-1| for the tracer and the vapour ratio."""
    import torch
    import yaml
    import snapy
    from snapy import Mesh, MeshOptions, kIDN, kIV1, kIV2, kIV3, kIPR, kICY

    torch.set_default_dtype(torch.float64)
    with open(os.path.join(src, "tests", "test_flux_positivity_cubedsphere.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["species"] = cfg["species"][:1] + MOIST_SPECIES
    cfg["reactions"] = MOIST_REACTIONS
    cfg["dynamics"]["equation-of-state"]["type"] = "ideal-moist"
    cfg["dynamics"]["equation-of-state"]["limiter"] = True
    cfg["integration"]["nlim"] = NSTEP
    cfg["scalar"] = {"nvar": 1, "names": ["tracer"],
                     "reconstruct": {"type": "weno5", "shock": False}}
    nx = cfg["geometry"]["cells"]["nx2"]
    assert nx == cfg["geometry"]["cells"]["nx3"] == 12, "expected C12"
    with tempfile.TemporaryDirectory() as wd:
        p = os.path.join(wd, "deck.yaml")
        with open(p, "w") as f:
            yaml.safe_dump(cfg, f)
        options = MeshOptions.from_yaml(p)
        options.blocks_per_process(6)
        options.set_local_horizontal_cells(nx, nx)
        mesh = Mesh(options)
    blocks = list(mesh.blocks)
    assert len(blocks) == 6
    mvars = []
    for ib, block in enumerate(blocks):
        coord = block.module("coord")
        beta, alpha = torch.meshgrid(coord.buffer("x3v"), coord.buffer("x2v"), indexing="ij")
        face = int(block.get_layout().loc_of(ib)[2])
        lon, lat = snapy.coord.cs_ab_to_lonlat(snapy.coord.get_cs_face_name(face), alpha, beta)
        bufs = dict(block.named_buffers())
        w = bufs["hydro.D"].clone().zero_()
        vel = torch.zeros((3,) + tuple(alpha.shape))
        vel[2] = 10.0 * torch.cos(lat)
        snapy.coord.cs_sph_to_contra_(vel, alpha, beta, face)
        dlon = torch.remainder(lon - math.radians(15.) + math.pi, 2 * math.pi) - math.pi
        bump = torch.exp(-(dlon ** 2 + lat ** 2) / (2 * math.radians(20.) ** 2))
        w[kIDN] = 1.0
        w[kIPR] = (PRES * (1. + 0.5 * bump)).unsqueeze(-1)
        w[kIV1], w[kIV2], w[kIV3] = (vel[k].unsqueeze(-1) for k in range(3))
        w[kICY] = QV
        mvars.append({"hydro_w": w, "scalar_r": torch.full((1,) + tuple(w.shape[1:]), R0)})
    mvars, _ = mesh.initialize(mvars)
    sls = [tuple(b.part((0, 0, 0), False)[1:]) for b in blocks]

    def ratios():
        out = []
        for ib in range(6):
            u, s = mvars[ib]["hydro_u"], mvars[ib]["scalar_s"]
            d = u[(kIDN,) + sls[ib]]
            out.append((s[(0,) + sls[ib]] / d, u[(kICY,) + sls[ib]] / d))
        return out

    init = ratios()
    q0 = float(torch.cat([q.flatten() for _, q in init]).mean())
    r0 = float(torch.cat([r.flatten() for r, _ in init]).mean())
    dr = dq = 0.

    def update():
        nonlocal dr, dq
        for r, q in ratios():
            dr = max(dr, float((r / R0 - 1).abs().max()))
            dq = max(dq, float((q / q0 - 1).abs().max()))

    update()
    intg = blocks[0].module("intg")
    redo = 0
    for cycle in range(1, NSTEP + 1):
        mesh.set_cycle(cycle)
        dt = mesh.max_time_step(mvars)
        for stage in range(len(intg.stages)):
            mesh.forward(mvars, dt, stage)
            update()
        redo += int(mesh.check_redo(mvars) != 0)
    hits = sum(int(dict(b.named_buffers())["hydro.positivity_hits"].item()) for b in blocks)
    print(f"cs: steps={NSTEP} redo={redo} hits={hits} tracer_r0_init={r0:.17g} "
          f"vapor_q0={q0:.17g}")
    print(f"cs tracer max|r/r0-1| = {dr:.3e}")
    print(f"cs vapor max|q/q0-1| = {dq:.3e}")
    return 0


def run_cs(src, rows):
    rc, out = sh([sys.executable, os.path.abspath(__file__), "--cs-arm", "--snapy-src", src], "on")
    print(f"--- cubed-sphere C12 moist (rc {rc})\n{out.strip()}", flush=True)
    m = re.search(r"redo=(\d+)", out)
    note = "" if m is None or m.group(1) == "0" else f" ({m.group(1)} rejected by check_redo)"
    for name, pat in (("tracer", r"cs tracer max\|r/r0-1\| = "), ("vapor", r"cs vapor max\|q/q0-1\| = ")):
        m = re.search(pat + FLOAT, out)
        dev = float(m.group(1)) if m and rc == 0 else math.nan
        rows.append(dict(arm=f"cs-C12-moist-{name}", repro="cubed_sphere_c12_moist", dim="CS-C12",
                         covariance="on", limiter="on", scheme=0, settling="off",
                         grid="uniform", steps=f"{NSTEP}{note}", max_dev=f"{dev:.3e}",
                         **{"pass": dev <= TOL}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repros", help="directory holding the two #338 repros")
    ap.add_argument("--snapy-src", required=True, help="snapy checkout (for the C12 test deck)")
    ap.add_argument("--out", default=".")
    ap.add_argument("--cs-arm", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.cs_arm:
        return cs_arm(a.snapy_src)
    rows, skipped = [], []
    run_repros(os.path.abspath(a.repros), rows, skipped)
    run_cs(os.path.abspath(a.snapy_src), rows)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "tracer_ratio_sweep.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(rows)
    with open(os.path.join(a.out, "tracer_ratio_skipped.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["arm", "reason"])
        wr.writerows(skipped)
    ran = [r for r in rows if r["pass"] != "SKIP"]
    bad = [r for r in ran if r["pass"] is not True]
    worst = max(ran, key=lambda r: math.inf if math.isnan(float(r["max_dev"]))
                else float(r["max_dev"]))
    print(f"arms: {len(ran)} run, {len(rows) - len(ran)} skipped; {len(bad)} failing; "
          f"worst {worst['arm']} = {worst['max_dev']}")
    for r in bad:
        print(f"FAIL {r['arm']}: {r['max_dev']}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
