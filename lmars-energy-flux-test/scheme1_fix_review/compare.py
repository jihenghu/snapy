#!/usr/bin/env python3
"""Tables for the scheme-1 fix review. usage: compare.py <runs_dir> > review_results.md

Rate: Xinyue's method (analyze.py at 9825aba9): least squares of ln(rms w) vs t
over rms w in [1e-4, 1e-1] if >= 3 rows there ("band"), else over t >= 0.5 d
("run"); R^2 reported. Also the 0.5-3 d fit for every run. Drifts are
(S(end) - S(0)) / |S(0)| of the global sums. Bitwise: sha256 of the final
conserved state (from the driver) and of the full diagnostic CSV.
"""
import csv, hashlib, json, math, os, sys
import numpy as np
DAY = 86400.0
R = sys.argv[1]
builds = ["base", "fix1", "fix2"]
names = ["box_dx50_u400_s1", "box_dx100_u400_s1", "box_dx200_u400_s1",
         "box_dx100_u400_s9", "box_dx100_u0_s1_nonoise", "col_dx100_u400_s1"]


def load(b, n):
    p = os.path.join(R, b, n)
    if not os.path.exists(p + ".json"):
        return None
    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(p + ".csv"))]
    return json.load(open(p + ".json")), rows, hashlib.sha256(open(p + ".csv", "rb").read()).hexdigest()


def fit(t, y):
    p = np.polyfit(t, y, 1); yh = np.polyval(p, t)
    ss = ((y - y.mean()) ** 2).sum()
    return p[0], (1 - ((y - yh) ** 2).sum() / ss) if ss > 0 else float("nan")


def rates(rows):
    t = np.array([r["t"] for r in rows]) / DAY; w = np.array([r["rms_w"] for r in rows])
    ok = np.isfinite(w) & (w > 0)
    band = ok & (w >= 1e-4) & (w <= 1e-1)
    out = {}
    if band.sum() >= 3:
        s, r2 = fit(t[band], np.log(w[band])); out["x"] = (s, r2, "band", t[band][0], t[band][-1])
    sel = ok & (t >= 0.5)
    if sel.sum() >= 3:
        s, r2 = fit(t[sel], np.log(w[sel])); out["run"] = (s, r2, "run", t[sel][0], t[sel][-1])
        out.setdefault("x", out["run"])
    return out


print("| arm | build | status | steps | redos | dt median (s) | rate (1/d) | fit | R^2 | rate 0.5-3 d (1/d) | R^2 | rms w end | max w | drift rho | drift m2 | drift E+rho g z | lambda end (dx) |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
res = {}
for n in names:
    for b in builds:
        d = load(b, n)
        if d is None:
            print(f"| {n} | {b} | not finished | | | | | | | | | | | | | | |"); continue
        js, rows, csvsha = d; res[(b, n)] = d
        r = rates(rows)
        x = r.get("x"); ru = r.get("run")
        S0, S1 = rows[0], rows[-1]
        dr = lambda k: (S1[k] - S0[k]) / abs(S0[k]) if S0[k] != 0 else float("nan")
        xs = f"{x[0]:+.3f} | {x[2]} {x[3]:.2f}-{x[4]:.2f} d | {x[1]:.4f}" if x else "nan | none | "
        rs = f"{ru[0]:+.3f} | {ru[1]:.4f}" if ru else "nan | "
        print(f"| {n} | {b} | {js['status']} | {js['steps']} | {js['redos']} | {(js.get('dt_median') or float('nan')):.3f} | {xs} | {rs} | "
              f"{S1['rms_w']:.3e} | {max(rr['max_w'] for rr in rows):.3e} | {dr('S_rho'):.2e} | {dr('S_m2'):.2e} | {dr('S_Etot'):.2e} | {(js.get('lam_dx_end') or float('nan')):.3g} |")
print()
print("Uniform-wind column (nx2 = 4, same noise in every column), max|u-u0|/u0:\n")
print("| build | at 600 s | at 1 d | at 3 d | max over run |\n|---|---|---|---|---|")
for b in builds:
    d = res.get((b, "col_dx100_u400_s1"))
    if not d: continue
    rows = d[1]; t = np.array([r["t"] for r in rows]); m = np.array([r["max_du_rel"] for r in rows])
    at = lambda s: m[int(np.argmin(abs(t - s)))]
    print(f"| {b} | {at(600):.3e} | {at(DAY):.3e} | {m[-1]:.3e} | {m.max():.3e} |")
print()
print("Bitwise vs base (sha256 of the final conserved state; sha256 of the diagnostic CSV):\n")
print("| arm | build | state sha256 (16) | state == base | csv == base |\n|---|---|---|---|---|")
for n in names:
    if (("base", n)) not in res: continue
    sb = res[("base", n)][0].get("state_sha256"); cb = res[("base", n)][2]
    for b in builds:
        if (b, n) not in res: continue
        s = res[(b, n)][0].get("state_sha256"); c = res[(b, n)][2]
        print(f"| {n} | {b} | {s[:16]} | {s == sb} | {c == cb} |")
