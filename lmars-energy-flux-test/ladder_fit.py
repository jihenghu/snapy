#!/usr/bin/env python3
"""dt-ladder table and rate-vs-dt fits.

usage: ladder_fit.py --scheme9 runs/b runs/i ... --scheme1 runs/h ... [--extra runs/G0...]

Per arm: dt (median of logged steps), horizontal Courant u dt/dx, vertical
acoustic Courant cs dt/dz, growth rate from a least-squares fit of ln(rms w)
over the amplitude band [--lo, --hi] m/s (the linear regime: above the 2e-5
noise plateau, below nonlinear amplitudes), its R^2 and number of e-folds,
e-folding time, dominant k / wavelength (dx) of mid-height w at the end of the
band, and the first logged time with max|w| >= 50 m/s.
Then, per scheme: sigma(dt) = s0 + A dt (weighted LSQ, standard errors) and
the log-log slope of sigma vs dt (apparent order if s0 = 0).
"""
import argparse, json, math, os
import numpy as np

LATE = 86400.
CS = math.sqrt(1.4 * 8.31446261815324 / 2.3e-3 * 100.)  # 711.4 m/s


def load(d):
    rows = [json.loads(l) for l in open(os.path.join(d, "log.jsonl"))]
    return json.load(open(os.path.join(d, "meta.json"))), rows


def arm(d, lo, hi):
    meta, rows = load(d)
    t = np.array([r["t"] for r in rows]); rw = np.array([r["rms_w"] for r in rows])
    mw = np.array([r["max_w"] for r in rows])
    dts = np.array([r["dt"] for r in rows[1:-1] if "dt" in r])
    dt = float(np.median(dts))
    # band: from the first time rms_w >= lo to the first time rms_w >= hi
    i0 = int(np.argmax(rw >= lo)) if (rw >= lo).any() else None
    i1 = int(np.argmax(rw >= hi)) if (rw >= hi).any() else len(rw) - 1
    out = dict(run=os.path.basename(d.rstrip("/")), scheme=meta.get("implicit", 9),
               cfl=meta.get("cfl", 0.3), u=meta["u"], dx=meta["dx"], dz=meta["dz"],
               dt=dt, c_h=meta["u"] * dt / meta["dx"], c_v=CS * dt / meta["dz"],
               status=meta.get("status", "running"), t_end_d=float(t[-1] / 86400))
    j = np.where(mw >= 50.)[0]
    out["t50_d"] = float(t[j[0]] / 86400) if len(j) else None
    # late slope: ln(rms w) over the last --late-s seconds (upper bound = slope + 2 se)
    m = (t >= t[-1] - LATE) & (rw > 0)
    if m.sum() > 5:
        tl, yl = t[m], np.log(rw[m])
        Al = np.vstack([tl, np.ones_like(tl)]).T
        cl, *_ = np.linalg.lstsq(Al, yl, rcond=None)
        s2l = ((yl - Al @ cl) ** 2).sum() / max(len(tl) - 2, 1)
        sel = math.sqrt(s2l / ((tl - tl.mean()) ** 2).sum())
        out.update(late_rate=cl[0] * 86400, late_ub=(cl[0] + 2 * sel) * 86400,
                   late_win=[float(tl[0] / 86400), float(tl[-1] / 86400)])
    if i0 is None or i1 - i0 < 5:
        out.update(rate=None)
        return out, rows
    tt, yy = t[i0:i1 + 1], np.log(rw[i0:i1 + 1])
    A = np.vstack([tt, np.ones_like(tt)]).T
    c, *_ = np.linalg.lstsq(A, yy, rcond=None)
    r2 = 1 - ((yy - A @ c) ** 2).sum() / ((yy - yy.mean()) ** 2).sum()
    n = len(tt); s2 = ((yy - A @ c) ** 2).sum() / max(n - 2, 1)
    se = math.sqrt(s2 / ((tt - tt.mean()) ** 2).sum())
    f = np.abs(np.fft.rfft(np.array(rows[i1]["wmid"]) - np.mean(rows[i1]["wmid"]))); f[0] = 0
    k = int(np.argmax(f))
    out.update(rate=c[0] * 86400, rate_se=se * 86400, r2=float(r2),
               win=[float(tt[0] / 86400), float(tt[-1] / 86400)],
               efolds=float(yy[-1] - yy[0]), efold_h=24. / (c[0] * 86400) if c[0] > 0 else None,
               k=k, lam_dx=len(f) and (len(rows[i1]["wmid"]) / k if k else None))
    return out, rows


def fit_dt(arms, min_r2=0.97, min_efolds=3.0):
    a = [x for x in arms if x.get("rate") and x["r2"] >= min_r2 and x["efolds"] >= min_efolds]
    if len(a) < 2:
        return None
    dt = np.array([x["dt"] for x in a]); s = np.array([x["rate"] for x in a])
    se = np.array([max(x["rate_se"], 1e-3 * abs(x["rate"])) for x in a])
    W = 1 / se ** 2
    A = np.vstack([np.ones_like(dt), dt]).T
    cov = np.linalg.inv(A.T @ (A * W[:, None]))
    c = cov @ (A.T @ (W * s))
    res = s - A @ c
    dof = max(len(s) - 2, 1)
    chi2 = float((W * res ** 2).sum() / dof)
    scale = max(chi2, 1.0)  # inflate errors when the line does not fit within errors
    out = dict(n=len(s), s0=c[0], s0_se=math.sqrt(cov[0, 0] * scale), slope=c[1],
               slope_se=math.sqrt(cov[1, 1] * scale), chi2_dof=chi2)
    if (s > 0).all() and len(s) >= 2:
        p = np.polyfit(np.log(dt), np.log(s), 1)
        out["order"] = p[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scheme9", nargs="*", default=[])
    ap.add_argument("--scheme1", nargs="*", default=[])
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--lo", type=float, default=1e-4)
    ap.add_argument("--hi", type=float, default=1e-1)
    ap.add_argument("--every", type=float, default=8640.)
    ap.add_argument("--json", default="ladder_summary.json")
    ap.add_argument("--min-r2", type=float, default=0.97, help="band fits used in the dt fit")
    ap.add_argument("--late-s", type=float, default=86400., help="late-slope window, s")
    a = ap.parse_args()
    global LATE
    LATE = a.late_s
    allarms, fits, tables = [], {}, []
    print(f"Growth fits on the amplitude band rms w in [{a.lo:g}, {a.hi:g}] m/s; cs = {CS:.1f} m/s.\n")
    print("| arm | scheme | cfl | dt (s) | u dt/dx | cs dt/dz | rate (/day) | +- | R^2 | window (d) | e-folds | e-fold time (h) | k | lambda (dx) | t(max abs w >= 50) (d) | status |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for grp, runs in (("9", a.scheme9), ("1", a.scheme1), ("extra", a.extra)):
        arms = []
        for d in runs:
            x, rows = arm(d, a.lo, a.hi); arms.append(x); allarms.append(x); tables.append((x, rows))
            if x.get("rate") is not None:
                print(f"| {x['run']} | {x['scheme']} | {x['cfl']} | {x['dt']:.4f} | {x['c_h']:.4f} | {x['c_v']:.4f} | "
                      f"{x['rate']:.3f} | {x['rate_se']:.3f} | {x['r2']:.4f} | {x['win'][0]:.2f}-{x['win'][1]:.2f} | "
                      f"{x['efolds']:.1f} | {x['efold_h'] if x['efold_h'] else float('nan'):.2f} | {x['k']} | {x['lam_dx']:.1f} | "
                      f"{('%.3f' % x['t50_d']) if x['t50_d'] is not None else '-'} | {x['status']} (t_end {x['t_end_d']:.2f} d) |")
            else:
                print(f"| {x['run']} | {x['scheme']} | {x['cfl']} | {x['dt']:.4f} | {x['c_h']:.4f} | {x['c_v']:.4f} | "
                      f"no band crossing | | | | | | | | {('%.3f' % x['t50_d']) if x['t50_d'] is not None else '-'} | {x['status']} (t_end {x['t_end_d']:.2f} d) |")
        if grp != "extra":
            fits[grp] = fit_dt(arms, a.min_r2)
    print()
    print(f"Late slope (last {a.late_s/86400:g} d of each run; upper bound = slope + 2 se):\n")
    for x in allarms:
        if "late_rate" in x:
            print(f"- {x['run']}: {x['late_rate']:.3f} /day, upper bound {x['late_ub']:.3f} /day on "
                  f"[{x['late_win'][0]:.2f}, {x['late_win'][1]:.2f}] d")
    print(f"\nrate-vs-dt fits use band fits with R^2 >= {a.min_r2} and >= 3 e-folds only.\n")
    for g, f in fits.items():
        if not f:
            continue
        print(f"scheme {g}: sigma = s0 + A dt over {f['n']} arms: s0 = {f['s0']:.3f} +- {f['s0_se']:.3f} /day, "
              f"A = {f['slope']:.3f} +- {f['slope_se']:.3f} /day/s, chi2/dof {f['chi2_dof']:.2f}"
              + (f"; log-log slope d ln(sigma)/d ln(dt) = {f['order']:.3f}" if 'order' in f else ""))
    print()
    for x, rows in tables:
        print(f"#### {x['run']}: rms w every {a.every/86400:.1f} day\n\n| t (day) | rms w (m/s) | max abs w (m/s) |\n|---|---|---|")
        nxt = 0.
        for r in rows:
            if r["t"] >= nxt - 1e-6:
                print(f"| {r['t']/86400:.3f} | {r['rms_w']:.3e} | {r['max_w']:.3e} |"); nxt += a.every
        print()
    json.dump(dict(arms=allarms, fits=fits), open(a.json, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
