#!/usr/bin/env python3
"""Tables for the design-check review. usage: chk_compare.py <chkruns dir> > chk_results.md"""
import csv, json, os, sys
import numpy as np
R = sys.argv[1]; B = ["base", "fix2", "roe"]; DAY = 86400.0


def L(b, n):
    p = os.path.join(R, b, n)
    if not os.path.exists(p + ".json"):
        return None
    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(p + ".csv"))]
    return json.load(open(p + ".json")), rows, json.load(open(p + ".prof.json"))


def rate(rows):
    t = np.array([r["t"] for r in rows]) / DAY; w = np.array([r["rms_w"] for r in rows])
    ok = (w > 0) & np.isfinite(w); band = ok & (w >= 1e-4) & (w <= 1e-1)
    sel, kind = (band, "band") if band.sum() >= 3 else (ok & (t >= 0.5), "0.5-3 d")
    if sel.sum() < 3:
        return float("nan"), float("nan"), kind
    y = np.log(w[sel]); p = np.polyfit(t[sel], y, 1); yh = np.polyval(p, t[sel])
    return p[0], 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum(), kind


def drift(rows, k):
    return (rows[-1][k] - rows[0][k]) / abs(rows[0][k]) if rows[0][k] != 0 else float("nan")


print("## Scheme 1 vs scheme 9, x2-mean u profile gap max_z |<u>_1 - <u>_9| / u0 (at 1 / 2 / 3 d)\n")
print("| arm | " + " | ".join(B) + " |\n|---|---|---|---|")
for arm in ["colU", "colS", "colUn2", "colSn2"]:
    cells = []
    for b in B:
        a1, a9 = L(b, arm + "_s1"), L(b, arm + "_s9")
        if not (a1 and a9):
            cells.append("n/a"); continue
        g = [max(abs(x - y) for x, y in zip(a1[2][d]["u"], a9[2][d]["u"])) / 400.0 for d in ("1", "2", "3")]
        cells.append(" / ".join(f"{v:.2e}" for v in g))
    print(f"| {arm} | " + " | ".join(cells) + " |")
print("\nm2-profile gap max_z |<m2>_1 - <m2>_9| / max_z |<m2>_9| at 3 d:\n")
print("| arm | " + " | ".join(B) + " |\n|---|---|---|---|")
for arm in ["colU", "colS", "colUn2", "colSn2"]:
    cells = []
    for b in B:
        a1, a9 = L(b, arm + "_s1"), L(b, arm + "_s9")
        if not (a1 and a9):
            cells.append("n/a"); continue
        m1, m9 = np.array(a1[2]["3"]["m2"]), np.array(a9[2]["3"]["m2"])
        cells.append(f"{np.abs(m1 - m9).max() / np.abs(m9).max():.2e}")
    print(f"| {arm} | " + " | ".join(cells) + " |")

print("\n## Runs\n")
print("| run | build | status | steps | redos | dt med (s) | rate (1/d) | fit | R^2 | rms w end | max abs(u-uref)/u0 end | drift rho | drift m2 | drift E+PE |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
names = ["colU_s1", "colU_s9", "colS_s1", "colS_s9", "colUn2_s1", "colUn2_s9", "colSn2_s1", "colSn2_s9",
         "boxU_s1", "boxU_s9", "boxS_s1", "boxS_s9", "moist_s1", "moist_s9", "moistrest_s9", "box200_s1"]
for n in names:
    for b in B:
        d = L(b, n)
        if not d:
            print(f"| {n} | {b} | not run/finished | | | | | | | | | | | |"); continue
        js, rows, _ = d; s, r2, kind = rate(rows)
        tblow = rows[-1]["t"] / DAY
        print(f"| {n} | {b} | {js['status']} (t {tblow:.3f} d) | {js['steps']} | {js['redos']} | {js['dt_median']:.3f} | "
              f"{s:+.3f} | {kind} | {r2:.3f} | {rows[-1]['rms_w']:.3e} | {rows[-1]['du_rel']:.3e} | "
              f"{drift(rows,'S_rho'):.2e} | {drift(rows,'S_m2'):.2e} | {drift(rows,'S_EPE'):.2e} |")

print("\n## Box rms-w gap scheme 1 vs 9: max over rows |rms_w1 - rms_w9| / rms_w9\n")
print("| box | " + " | ".join(B) + " |\n|---|---|---|---|")
for arm in ["boxU", "boxS"]:
    cells = []
    for b in B:
        a1, a9 = L(b, arm + "_s1"), L(b, arm + "_s9")
        if not (a1 and a9):
            cells.append("n/a"); continue
        n = min(len(a1[1]), len(a9[1]))
        x = np.array([r["rms_w"] for r in a1[1][1:n]]); y = np.array([r["rms_w"] for r in a9[1][1:n]])
        cells.append(f"{np.max(np.abs(x - y) / y):.2e} (end {abs(x[-1]-y[-1])/y[-1]:.2e})")
    print(f"| {arm} | " + " | ".join(cells) + " |")

print("\n## Scheme 9 bitwise across builds (final-state sha256, first 16)\n")
print("| run | " + " | ".join(B) + " | all equal |\n|---|---|---|---|---|")
for n in [x for x in names if x.endswith("_s9")]:
    sh = [(L(b, n) or [{}])[0].get("state_sha256", "-") for b in B]
    print(f"| {n} | " + " | ".join(s[:16] for s in sh) + f" | {len(set(sh)) == 1 and '-' not in sh} |")
