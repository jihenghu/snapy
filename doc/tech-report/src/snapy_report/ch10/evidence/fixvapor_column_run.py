"""The vapour column repair as snapy runs it, on the 64-cell column of @fig-ch10-fixvapor-column.

This is a RUN record, not a check: it needs snapy, built at the code pin, in the active Python. It builds the
MeshBlock of fixvapor_column.yaml (spherical-polar, 64 x1 cells, EOS limiter on), sets a smooth vapour profile with
a negative interior cell (40) and a negative bottom cell (0), and calls the equation of state's U->W conversion
once. That conversion runs EquationOfStateImpl::apply_conserved_limiter_ on the conserved state in place, and so
the column kernel fix_vapor_impl. The script writes the column before and after, the dry density and the radial
volume factor to data/fixvapor_column.csv, which fig_fixvapor_column.py draws and fixvapor_check.py [C6] replays
through its port.

  python3 src/snapy_report/ch10/evidence/fixvapor_column_run.py --snapy <snapy checkout at the code pin>

The checkout is only read for its HEAD, which must be the sha of code_pin.yml; the snapy imported must be built
from it. Prints the environment, the cells the repair changed and the column-mass change; exits nonzero when the
checkout is not at the pin, a cell is left negative, or the column mass moves by more than 1e-14 relative.
"""
import argparse
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]  # doc/tech-report
DATA = HERE.parent / "data" / "fixvapor_column.csv"
NX1, NG = 64, 2


def pin():
    text = (ROOT / "code_pin.yml").read_text()
    return re.search(r"^sha:\s*([0-9a-f]{40})\s*$", text, flags=re.M).group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapy", required=True, help="snapy checkout the imported build was made from")
    args = parser.parse_args()
    head = subprocess.check_output(["git", "-C", args.snapy, "rev-parse", "HEAD"], text=True).strip()
    if head != pin():
        print(f"checkout HEAD {head} is not the code pin {pin()}")
        return 2

    import snapy
    from snapy import MeshBlock, MeshBlockOptions, kICY, kIDN, kIPR

    torch.set_default_dtype(torch.float64)
    print(f"snapy@{head}; Python {platform.python_version()}, torch {torch.__version__}, numpy {np.__version__}, "
          f"CPU, double, 1 process")

    block = MeshBlock(MeshBlockOptions.from_yaml(str(HERE / "fixvapor_column.yaml")))
    eos = block.module("hydro.eos")
    x1f = dict(block.module("coord").named_buffers())["x1f"]
    assert x1f.numel() == NX1 + 2 * NG + 1

    # the profile of the figure: dry density exp(-i/30), vapour 4e-3 exp(-i/30) exp(-i/25), with a negative
    # interior cell and a negative bottom cell
    i = torch.arange(NX1, dtype=torch.float64)
    major = torch.exp(-i / 30.)
    vapor = 4e-3 * major * torch.exp(-i / 25.)
    vapor[40] = -6e-4 * major[40]
    vapor[0] = -1e-4

    cons = torch.zeros(eos.nvar(), 1, 1, NX1 + 2 * NG)
    cons[kIDN] = 1.
    cons[kIDN, 0, 0, NG:NG + NX1] = major
    cons[kIPR] = 2.5e5  # far above the energy floor, so no floor fires
    cons[kICY, 0, 0, NG:NG + NX1] = vapor
    before = cons[kICY, 0, 0, NG:NG + NX1].clone()

    eos.compute("U->W", [cons])  # runs apply_conserved_limiter_ on cons in place
    after = cons[kICY, 0, 0, NG:NG + NX1].clone()

    # SphericalPolarImpl::cell_volume is radial x polar x azimuthal; along one x1 column only the radial factor
    # varies, and fix_vapor_impl weights by V_l / V_0, so the radial factor is the weight
    r = x1f[NG:NG + NX1 + 1]
    vol = (r[1:] ** 3 - r[:-1] ** 3) / 3.

    m0 = float((before * vol).sum())
    rel = float(((after - before) * vol).sum()) / m0
    changed = (after != before).nonzero().flatten().tolist()
    print(f"cells changed by the repair: {changed}")
    for c in changed:
        print(f"  cell {c}: {float(before[c]):.10e} -> {float(after[c]):.10e}")
    print(f"min after {float(after.min()):.3e}; relative column-mass change {rel:.2e}; "
          f"V_63/V_0 = {float(vol[-1] / vol[0]):.3f}")

    np.savetxt(DATA, np.column_stack([i.numpy(), before.numpy(), after.numpy(), major.numpy(), vol.numpy()]),
               delimiter=",", fmt="%.17e",
               header=f"cell,vapor_before,vapor_after,major,vol (snapy@{head}, "
                      f"src/snapy_report/ch10/evidence/fixvapor_column_run.py)")
    ok = float(after.min()) >= 0. and abs(rel) < 1e-14
    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
