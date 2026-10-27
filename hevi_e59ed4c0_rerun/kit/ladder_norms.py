#!/usr/bin/env python3
"""Ladder errors under three normalisations (sensitivity check; analyze.py uses A).
A: ||q-q_ref|| / ||q_ref - q_init||   B: ||q-q_ref|| / ||q_ref - <q_ref>_x2||   C: ||q-q_ref|| / ||q_ref||
usage: ladder_norms.py <runs dir>"""
import glob, os, sys
import numpy as np
R = sys.argv[1]; NG = 3
ld = lambda p: np.load(p)[:, 0, NG:NG + 64, NG:NG + 100]
ref, ini = ld(R + "/base/ref_s0_d16.final_u.npy"), ld(R + "/base/lad_init.init_u.npy")
rows = {"rho": 0, "m1": 1, "m2": 2, "E": 4}
for f in sorted(glob.glob(R + "/*/lad_s9_d*.final_u.npy")):
    u = ld(f)
    out = []
    for nm, den in (("A", lambda i: ref[i] - ini[i]), ("B", lambda i: ref[i] - ref[i].mean(0, keepdims=True)), ("C", lambda i: ref[i])):
        out.append(nm + " " + " ".join("%.2e" % (np.linalg.norm(u[i] - ref[i]) / np.linalg.norm(den(i))) for i in rows.values()))
    print(f.split(R)[1], " | ".join(out))
