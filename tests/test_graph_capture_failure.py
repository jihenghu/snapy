"""A capture that fails on one block of a Mesh never hangs the Mesh.

The six-panel cubed sphere of test_default_execution with 2 x 2 blocks per
panel (24 blocks): its stage segments hold panel-seam exchanges, so the blocks
of a capture meet at the same-process rendezvous. SNAP_TEST_CAPTURE_FAIL=5
makes block 5's capture throw the out-of-memory error a real capture can
throw (CUDAGraph::instantiate, the caching allocator). Each case runs in a
child process under a timeout, so a hang fails the test instead of stalling:

  default execution   the Mesh goes eager on all blocks together, 3 steps,
                      and equals an explicit-eager Mesh bitwise after every
                      step, with no capture kept
  execution cuda-graph the error reaches the caller

  python test_graph_capture_failure.py
"""
import json
import os
import subprocess
import sys

import torch

from cuda_build import build_has_cuda, skip

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 120
NSTEPS = 3


def child(mode):
    sys.path.insert(0, HERE)
    import test_default_execution as t

    execution = None if mode == "default" else "cuda-graph"
    mesh, blocks, mvars = t.cubed(2, execution)
    ref, _, evars = t.cubed(2, "eager")
    try:
        for n in range(NSTEPS):
            for s in range(3):
                mesh.forward(mvars, 1.0e-4, s)
                ref.forward(evars, 1.0e-4, s)
            for i in range(len(blocks)):
                assert torch.equal(mvars[i]["hydro_u"], evars[i]["hydro_u"]), (
                    "step", n, "block", i)
    except Exception as e:  # the explicit-graph case reports the error
        print("RAISED " + type(e).__name__ + ": " + str(e).splitlines()[0], flush=True)
        return
    print("REPORT " + json.dumps(mesh.execution_report()), flush=True)


def run(mode):
    env = dict(os.environ, SNAP_TEST_CAPTURE_FAIL="5")
    try:
        out = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", mode],
                             env=env, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise AssertionError(f"{mode}: the Mesh hung, no result within {TIMEOUT} s")
    lines = [l for l in out.stdout.splitlines() if l.startswith(("REPORT", "RAISED"))]
    assert out.returncode == 0 and lines, (mode, out.returncode, out.stdout[-2000:],
                                           out.stderr[-2000:])
    print(mode + ": " + lines[-1], flush=True)
    return lines[-1]


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2])
        return 0
    if not build_has_cuda():
        skip("CUDA unavailable")
    line = run("default")
    assert line.startswith("REPORT"), line
    report = json.loads(line[len("REPORT "):])
    assert report["eager"] > 0 and report["graphs"] == 0, report
    line = run("cuda-graph")
    assert line.startswith("RAISED") and "injected capture failure" in line, line
    print("PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
