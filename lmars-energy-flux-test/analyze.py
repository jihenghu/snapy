#!/usr/bin/env python3
"""Tables and growth fits for run_arm.py output.

usage: analyze.py runs/a runs/b ... > results.md
For each run: rms w(t) every --every s (about 30 rows over 3 days), max |w|,
a least-squares fit of ln(rms w) vs t over the whole run after --t0 and over
the steepest --win-s window, and the dominant x2 wavelength (in dx) of the
mid-height w row from an FFT at the end and at the time of peak rms w.
"""
import argparse, json, math, os
import numpy as np


def load(d):
    rows = [json.loads(l) for l in open(os.path.join(d, "log.jsonl"))]
    meta = json.load(open(os.path.join(d, "meta.json")))
    return meta, rows


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    c, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ c
    ss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - yhat) ** 2).sum() / ss if ss > 0 else float("nan")
    return c[0], r2


def dominant(wrow):
    f = np.abs(np.fft.rfft(np.asarray(wrow) - np.mean(wrow)))
    f[0] = 0.
    k = int(np.argmax(f))
    n = len(wrow)
    return k, (n / k if k else float("inf")), f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--every", type=float, default=8640.)
    ap.add_argument("--t0", type=float, default=21600., help="start of the whole-run fit, s")
    ap.add_argument("--win-s", type=float, default=43200., help="sliding fit window, s")
    a = ap.parse_args()
    summ = []
    for d in a.runs:
        meta, rows = load(d)
        t = np.array([r["t"] for r in rows])
        rw = np.array([r["rms_w"] for r in rows])
        mw = np.array([r["max_w"] for r in rows])
        name = os.path.basename(d.rstrip("/"))
        print(f"### {name}: {meta['solver']}, u = {meta['u']:g} m/s, dx = {meta['dx']/1e3:g} km, "
              f"nx2 = {meta['nx2']}, noise {meta['noise_T']:g} K, seed {meta['seed']}\n")
        print(f"status {meta.get('status')}, {meta.get('steps')} steps, t_end = {meta.get('t_end', 0)/86400:.4f} d, "
              f"wall {meta.get('wall_s', 0)/60:.1f} min, balance_column residual {meta['balance_residual']:.2e} "
              f"({meta['balance_sweeps']} sweeps)\n")
        print("| t (day) | rms w (m/s) | max abs w (m/s) | rms (u - U) (m/s) |\n|---|---|---|---|")
        nxt = 0.
        for r in rows:
            if r["t"] >= nxt - 1e-6:
                print(f"| {r['t']/86400:.3f} | {r['rms_w']:.3e} | {r['max_w']:.3e} | {r['rms_du']:.3e} |")
                nxt += a.every
        if rows[-1]["t"] < nxt - a.every - 1e-6 or True:
            pass
        pos = rw > 0
        m = (t >= a.t0) & pos
        s_all, r2_all = fit(t[m], np.log(rw[m])) if m.sum() > 2 else (float("nan"),) * 2
        best = (-1e99, None, None, None)
        for i in range(len(t)):
            j = np.searchsorted(t, t[i] + a.win_s)
            if j >= len(t) or t[i] < a.t0:
                continue
            sl = slice(i, j + 1)
            if not pos[sl].all():
                continue
            s, r2 = fit(t[sl], np.log(rw[sl]))
            if s > best[0]:
                best = (s, r2, t[i], t[j])
        imax = int(np.argmax(rw))
        k_end, lam_end, _ = dominant(rows[-1]["wmid"])
        k_pk, lam_pk, _ = dominant(rows[imax]["wmid"])
        print()
        print(f"max abs w over run {mw.max():.3e} m/s at t = {t[int(np.argmax(mw))]/86400:.3f} d; "
              f"rms w peak {rw[imax]:.3e} at t = {t[imax]/86400:.3f} d, end {rw[-1]:.3e}, ratio end/(t=0.25 d) "
              f"{rw[-1]/rw[np.searchsorted(t, a.t0)]:.3g}")
        print(f"fit ln(rms w) on [{a.t0/86400:.2f} d, end]: slope {s_all*86400:.3g} /day (R^2 {r2_all:.3f})")
        if best[2] is not None:
            print(f"steepest {a.win_s/86400:.2f}-day window [{best[2]/86400:.2f}, {best[3]/86400:.2f}] d: "
                  f"slope {best[0]*86400:.3g} /day (R^2 {best[1]:.3f})")
        print(f"dominant x2 wavelength of mid-height w: end {lam_end:.3g} dx (k={k_end}), "
              f"at rms peak {lam_pk:.3g} dx (k={k_pk})\n")
        summ.append(dict(run=name, solver=meta["solver"], u=meta["u"], status=meta.get("status"),
                         max_w=float(mw.max()), rms_end=float(rw[-1]), rms_peak=float(rw[imax]),
                         slope_all_per_day=float(s_all * 86400), r2_all=float(r2_all),
                         slope_win_per_day=float(best[0] * 86400) if best[2] is not None else None,
                         win=[best[2], best[3]], lam_end_dx=lam_end, lam_peak_dx=lam_pk))
    json.dump(summ, open("summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
