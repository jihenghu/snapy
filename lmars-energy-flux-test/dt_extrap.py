#!/usr/bin/env python3
"""Rate vs dt per scheme from ladder_fit.py's JSON.

usage: dt_extrap.py ladder_summary.json
Per arm, the rate used is the band fit if it is clean (R^2 >= 0.97 and >= 3
e-folds), else the last-day slope (flagged "late"). Fits per scheme:
  (1) sigma = s0 + A dt          weighted LSQ, s0 = the dt -> 0 extrapolation
  (2) sigma = s0 + A dt + B dt^2 (4 points), s0 with its standard error
  (3) ln sigma = ln C + p ln dt  apparent order p (assumes s0 = 0)
  (4) local orders p_i = ln(s_i/s_{i+1}) / ln(dt_i/dt_{i+1}) between neighbours
Standard errors are scaled by sqrt(chi2/dof) when chi2/dof > 1.
"""
import json, math, sys
import numpy as np


def wls(X, y, se):
    W = 1 / se ** 2
    cov = np.linalg.inv(X.T @ (X * W[:, None]))
    c = cov @ (X.T @ (W * y))
    dof = len(y) - X.shape[1]
    chi2 = float((W * (y - X @ c) ** 2).sum() / dof) if dof > 0 else float("nan")
    scale = max(chi2, 1.0) if dof > 0 else 1.0
    return c, np.sqrt(np.diag(cov) * scale), chi2


d = json.load(open(sys.argv[1]))
for sch in ("9", "1"):
    arms = [a for a in d["arms"] if str(a["scheme"]) == sch and a["run"] != "G0_u400_grav0"]
    pts = []
    for a in sorted(arms, key=lambda a: -a["dt"]):
        clean = a.get("rate") is not None and a["r2"] >= 0.97 and a["efolds"] >= 3
        if clean:
            pts.append((a["dt"], a["rate"], max(a["rate_se"], 0.01 * a["rate"]), "band", a["run"]))
        elif a.get("late_rate") is not None and a["late_rate"] > 0:
            se = (a["late_ub"] - a["late_rate"]) / 2
            pts.append((a["dt"], a["late_rate"], max(se, 0.01 * a["late_rate"]), "late", a["run"]))
    print(f"## scheme {sch}\n")
    for p in pts:
        print(f"- {p[4]}: dt {p[0]:.4f} s, rate {p[1]:.3f} +- {p[2]:.3f} /day ({p[3]})")
    dt = np.array([p[0] for p in pts]); s = np.array([p[1] for p in pts]); se = np.array([p[2] for p in pts])
    if len(pts) >= 2:
        c, e, chi2 = wls(np.vstack([np.ones_like(dt), dt]).T, s, se)
        print(f"\n(1) linear: s0 = {c[0]:.3f} +- {e[0]:.3f} /day, A = {c[1]:.3f} +- {e[1]:.3f} /day/s, chi2/dof {chi2:.2f}")
    if len(pts) >= 4:
        c, e, chi2 = wls(np.vstack([np.ones_like(dt), dt, dt ** 2]).T, s, se)
        print(f"(2) quadratic: s0 = {c[0]:.3f} +- {e[0]:.3f} /day, A = {c[1]:.3f}, B = {c[2]:.3f}, chi2/dof {chi2:.2f}")
    if len(pts) >= 2 and (s > 0).all():
        c, e, chi2 = wls(np.vstack([np.ones_like(dt), np.log(dt)]).T, np.log(s), se / s)
        print(f"(3) power law: p = {c[1]:.3f} +- {e[1]:.3f}, C = {math.exp(c[0]):.3f} /day/s^p, chi2/dof {chi2:.2f}")
        for i in range(len(pts) - 1):
            pi = math.log(s[i] / s[i + 1]) / math.log(dt[i] / dt[i + 1])
            print(f"(4) local order between dt {dt[i]:.3f} and {dt[i+1]:.3f} s: {pi:.3f}")
    print()
