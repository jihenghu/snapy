"""A Mesh whose block job failed can be stepped again: its same-process exchange starts clean (#320).

The 24-block cubed sphere of test_default_execution with 256 x 256 cells per block, eager execution. Two equal
Meshes A and D take one step. A's caching allocator is then capped 40 MiB above what stays, so some blocks of A
run out of memory in the next step while the others wait at the same-process exchange; the error reaches the
caller. With the cap lifted, A's state is restored from a copy taken before that step, and A and D take the same
step. A must not raise and must equal D bitwise.

A failed round once left its rendezvous state behind (arrival counts of the blocks that left), and the restored
Mesh's next exchange then raised "local exchange size mismatch" or copied before every block had packed, in about
two runs out of three. Each trial runs in its own child process under a timeout; the test fails if any of
TRIALS trials fails, so a stale state is caught every time.

  python test_mesh_restep_after_failure.py
"""
import os
import subprocess
import sys

import torch

from cuda_build import build_has_cuda, skip

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 120
TRIALS = 8


def child():
    sys.path.insert(0, HERE)
    import test_default_execution as t

    total = torch.cuda.get_device_properties(0).total_memory
    a, _, av = t.cubed(2, "eager", 256)
    d, _, dv = t.cubed(2, "eager", 256)
    for s in range(3):
        a.forward(av, 1.0e-6, s)
        d.forward(dv, 1.0e-6, s)
    torch.cuda.synchronize()
    saved = [{k: v.clone() for k, v in m.items()} for m in av]
    torch.cuda.empty_cache()
    torch.cuda.set_per_process_memory_fraction(
        (torch.cuda.memory_reserved() + 40 * 2**20) / total, 0)
    try:
        for s in range(3):
            a.forward(av, 1.0e-6, s)
        print("NOFAIL the capped step did not fail", flush=True)
        return
    except torch.OutOfMemoryError:
        pass
    torch.cuda.set_per_process_memory_fraction(1.0, 0)
    for m, kept in zip(av, saved):
        for k, v in kept.items():
            m[k].copy_(v)
    try:
        for s in range(3):
            a.forward(av, 1.0e-6, s)
            d.forward(dv, 1.0e-6, s)
        torch.cuda.synchronize()
    except Exception as e:
        print("RAISED " + type(e).__name__ + ": " + str(e).splitlines()[0], flush=True)
        return
    diff = [i for i, (x, y) in enumerate(zip(av, dv)) if not torch.equal(x["hydro_u"], y["hydro_u"])]
    print(("DIFF blocks %s" % diff) if diff else "RESTEP equal", flush=True)


def trial(n):
    try:
        out = subprocess.run([sys.executable, os.path.abspath(__file__), "--child"],
                             capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"trial {n}: hung, no result within {TIMEOUT} s"
    lines = [l for l in out.stdout.splitlines() if l.startswith(("RESTEP", "RAISED", "DIFF", "NOFAIL"))]
    if out.returncode != 0 or not lines:
        return f"trial {n}: child rc {out.returncode}: {out.stderr[-1000:]}"
    print(f"trial {n}: {lines[-1][:300]}", flush=True)
    return None if lines[-1] == "RESTEP equal" else f"trial {n}: {lines[-1][:300]}"


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child()
        return 0
    if not build_has_cuda():
        skip("CUDA unavailable")
    failures = [f for f in (trial(n) for n in range(TRIALS)) if f]
    assert not failures, failures
    print("PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
