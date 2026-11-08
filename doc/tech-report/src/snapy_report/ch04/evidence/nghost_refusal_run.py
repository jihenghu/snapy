"""Which reconstruction and nghost pairs a MeshBlock refuses at setup, and with which message.

This is a RUN record, not a check: it needs snapy, built at the code pin, in the active Python. For each of
dc, plm, cp3, weno3, cp5 and weno5 as the vertical reconstruction of a 16-cell Cartesian column with reflecting
x1 walls, and nghost 1, 2 and 3, it builds MeshBlock(MeshBlockOptions.from_yaml(...)) and prints "built" or the
line of the refusal that names nghost (MeshBlockImpl::reset). Exits nonzero when a pair with
stencils() / 2 + 1 <= nghost is refused or a pair above it is built.

  python3 src/snapy_report/ch04/evidence/nghost_refusal_run.py
"""
import os
import sys
import tempfile

import snapy

DECK = """reference-state: {{Tref: 300., Pref: 1.e5}}
species: [{{name: dry, composition: {{O: 0.42, N: 1.56, Ar: 0.01}}, cv_R: 2.5}}]
geometry: {{type: cartesian, cells: {{nx1: 16, nghost: {ng}}}, bounds: {{x1min: 0., x1max: 16.}}}}
dynamics: {{equation-of-state: {{type: ideal-gas}}, reconstruct: {{vertical: {{type: {recon}, scale: false, shock: false}}}}}}
boundary-condition: {{external: {{x1-inner: reflecting, x1-outer: reflecting}}}}
"""
STENCILS = {"dc": 1, "plm": 3, "cp3": 3, "weno3": 3, "cp5": 5, "weno5": 5}


def main():
    print("snapy", snapy.__version__)
    bad = 0
    for recon, sten in STENCILS.items():
        for ng in (1, 2, 3):
            f = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
            f.write(DECK.format(recon=recon, ng=ng))
            f.close()
            try:
                snapy.MeshBlock(snapy.MeshBlockOptions.from_yaml(f.name))
                out, built = "built", True
            except RuntimeError as e:
                out = "refused: " + [l for l in str(e).splitlines() if "nghost" in l][0].strip()
                built = False
            finally:
                os.remove(f.name)
            bad += built != (sten // 2 + 1 <= ng)
            print(f"{recon:6s} nghost {ng}: {out}")
    sys.exit(bad)


if __name__ == "__main__":
    main()
