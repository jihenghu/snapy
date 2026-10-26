#!/usr/bin/env python3
"""rms w(t) for all arms on one log axis.  usage: plot.py runs/* -o rms_w.png"""
import argparse, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("runs", nargs="+")
ap.add_argument("-o", default="rms_w.png")
a = ap.parse_args()
fig, ax = plt.subplots(figsize=(8, 5))
for d in sorted(r for r in a.runs if os.path.isdir(r)):
    rows = [json.loads(l) for l in open(os.path.join(d, "log.jsonl"))][1:]
    ax.semilogy([r["t"] / 86400 for r in rows], [max(r["rms_w"], 1e-13) for r in rows],
                label=os.path.basename(d.rstrip("/")))
ax.set_xlabel("t (model day)"); ax.set_ylabel("rms w (m/s)")
ax.set_title("snapy 721a565, 2-D isothermal H2-He, dx = 5 km, 64 x 100")
ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(a.o, dpi=150)
