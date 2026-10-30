"""A 64-cell column with an interior and a bottom vapour deficit, before and after fix_vapor.

Data: data/fixvapor_column.csv, written by evidence/fixvapor_column_run.py: snapy's own repair (the U->W
conversion of a spherical-polar MeshBlock with the EOS limiter on, so EquationOfStateImpl::apply_conserved_limiter_
and fix_vapor_impl) at snapy@c0c38593d3d3f37bebe204a590610fd7daa05a5f. fixvapor_check.py [C6] replays it through
the port.
"""
import os

import numpy as np

from snapy_report import figstyle as fs

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fixvapor_column.csv")


def make_fig():
    cell, before, after, major, _vol = np.loadtxt(DATA, delimiter=",", unpack=True)
    fig, ax = fs.new_figure(fs.SINGLE, 3.2)
    ax.plot(before / major * 1e3, cell, color=fs.VERMILLION, ls="--", marker="x", ms=3, label="before")
    ax.plot(after / major * 1e3, cell, color=fs.GREEN, marker="o", ms=2.5, label="after")
    ax.axvline(0., color=fs.BLACK, lw=0.8)
    ax.set_xlabel(r"$\rho_n/\rho_{\mathrm{d}}$ [$10^{-3}$]")
    ax.set_ylabel("cell index $i$ (0 = bottom)")
    ax.legend(frameon=False, loc="center left")
    return fig
