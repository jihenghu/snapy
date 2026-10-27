#!/usr/bin/env python3
"""Tables for the e59ed4c0 rerun.

Ladder: L2 relative error of rho, m1, m2, E (interior cells) at T against the
explicit scheme-0 reference at dt0/16, in two norms:
    B (primary): err_q = ||q - q_ref||_2 / ||q_ref - <q_ref>_x2||_2  (eddy part of the reference)
    A:           err_q = ||q - q_ref||_2 / ||q_ref - q_init||_2      (change of the reference over the run)
For m1 both denominators are ~||m1_ref||. Order between dt0 and dt0/2:
p = log2(err(dt0) / err(dt0/2)).

Stability arms: growth rate = least-squares slope of ln(rms w) against t [d] over
the fit window (default 0.5 d to the end), with its standard error; redos;
mass drift = max_t |S_rho(t) / S_rho(0) - 1|, also for E + rho g z.

usage: analyze.py <runs dir> <out.md>
"""
import glob, json, math, os, sys

import numpy as np

R = sys.argv[1]
NG, NX1, NX2 = 3, 100, 64
rows = {"rho": 0, "m1": 1, "m2": 2, "E": 4}


def load(path):
    u = np.load(path)
    return u[:, 0, NG:NG + NX2, NG:NG + NX1]


def ladder(lines, norm):
    ref = os.path.join(R, "base/ref_s0_d16.final_u.npy")
    ini = os.path.join(R, "base/lad_init.init_u.npy")
    if not (os.path.exists(ref) and os.path.exists(ini)):
        lines.append("ladder: reference not ready\n")
        return {}
    uref, u0 = load(ref), load(ini)
    den = (lambda i: uref[i] - uref[i].mean(0, keepdims=True)) if norm == "B" else (lambda i: uref[i] - u0[i])
    out = {}
    lines.append("Norm %s." % norm)
    lines.append("")
    lines.append("| arm | dt / dt0 | steps | wall s | rho | m1 | m2 | E |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for b in ("hevi", "base"):
        for f in sorted(glob.glob(os.path.join(R, b, "lad_*_d*.json")), key=lambda p: int(p.split("_d")[-1][:-5])):
            s = json.load(open(f))
            if s["status"] != "finished":
                lines.append("| %s/%s | 1/%d | %s | | %s | | | |" % (b, os.path.basename(f)[:-5], s["dtdiv"], s["steps"], s["status"]))
                continue
            u = load(f[:-5] + ".final_u.npy")
            e = {k: float(np.linalg.norm(u[i] - uref[i]) / np.linalg.norm(den(i))) for k, i in rows.items()}
            name = b + "/" + os.path.basename(f)[:-5]
            out[name] = (s["dtdiv"], e)
            lines.append("| %s | 1/%d | %d | %.0f | %.3g | %.3g | %.3g | %.3g |" % (
                name, s["dtdiv"], s["steps"], s["wall_s"], e["rho"], e["m1"], e["m2"], e["E"]))
    lines.append("")
    lines.append("Order p = log2(err(dt0)/err(dt0/2)) (and dt0/2 -> dt0/4 where run):")
    lines.append("")
    lines.append("| tree | pair | rho | m1 | m2 | E |")
    lines.append("|---|---|---|---|---|---|")
    for b in ("hevi", "base"):
        arms = sorted([v for k, v in out.items() if k.startswith(b + "/")], key=lambda x: x[0])
        for (k1, e1), (k2, e2) in zip(arms, arms[1:]):
            lines.append("| %s | 1/%d -> 1/%d | %s |" % (b, k1, k2, " | ".join(
                "%.2f" % (math.log(e1[q] / e2[q]) / math.log(k2 / k1)) for q in rows)))
    lines.append("")
    return out


def fit(t, y, t0):
    m = (t >= t0) & np.isfinite(y) & (y > 0)
    if m.sum() < 3:
        return float("nan"), float("nan"), 0
    x, ly = t[m], np.log(y[m])
    A = np.vstack([x, np.ones_like(x)]).T
    c, res, *_ = np.linalg.lstsq(A, ly, rcond=None)
    r = ly - A @ c
    n = len(x)
    se = math.sqrt((r @ r) / (n - 2) / ((x - x.mean()) ** 2).sum())
    return c[0], se, n


def arms(lines):
    lines.append("| arm | status | t end (d) | steps | redos | dt median (s) | rate (1/d) +- se | fit | rms w start..end (m/s) | max rms w | mass drift | E+PE drift | wall s |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for f in sorted(glob.glob(os.path.join(R, "*", "*.json"))):
        nm = os.path.basename(f)[:-5]
        if nm.startswith("lad_") or nm.startswith("ref_"):
            continue
        s = json.load(open(f))
        d = np.genfromtxt(f[:-5] + ".csv", delimiter=",", names=True)
        t = d["t"] / 86400.0
        t0 = 0.5 if t[-1] > 1.0 else 0.25 * t[-1]
        k, se, n = fit(t, d["rms_w"], t0)
        md = np.abs(d["S_rho"] / d["S_rho"][0] - 1).max()
        ed = np.abs(d["S_Etot"] / d["S_Etot"][0] - 1).max()
        lines.append("| %s/%s | %s | %.3f | %d | %d | %.3f | %+.3f +- %.3f | %.2f-%.2f d, n %d | %.2e..%.2e | %.2e | %.1e | %.1e | %.0f |" % (
            os.path.basename(os.path.dirname(f)), nm, s["status"], s["t_end"] / 86400, s["steps"], s["redos"],
            s["dt_median"] or 0, k, se, t0, t[-1], n, d["rms_w"][1] if len(d) > 1 else 0, d["rms_w"][-1],
            d["rms_w"].max(), md, ed, s["wall_s"]))
    lines.append("")


lines = ["# e59ed4c0 rerun tables", "", "## dx 5 km u400 ladder (T = 3600 s)", ""]
ladder(lines, "B")
ladder(lines, "A")
lines += ["## Stability arms and u = 0 box", ""]
arms(lines)
open(sys.argv[2], "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
