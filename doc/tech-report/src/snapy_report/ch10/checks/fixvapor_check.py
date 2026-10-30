"""Executable check of the column vapour and cloud repair (chapter 10, _fixvapor.qmd).

What is checked: fix_vapor_impl (src/eos/fix_vapor_impl.h) at
snapy@c0c38593d3d3f37bebe204a590610fd7daa05a5f, ported line for line below: the downward branch borrows only
the deficit (negative cells to zero, each donor gives up D/Q of its vapour), the upward branch takes a bottom
deficit from the cells above. Claims C1-C9. C1-C3 replay the inputs of the eos_limiter gtests
(tests/test_eos.cpp at the same sha) through the port; C4, C5, C7 and C9 check the claims of the Derivation layer
on random and fixed columns; C6 replays the column of the snapy run in data/fixvapor_column.csv (written by
src/snapy_report/ch10/evidence/fixvapor_column_run.py against a build at the pin) through the port; C8 is the
window algebra in sympy.

Run: python3 fixvapor_check.py   (numpy and sympy only; exits with the number of failed claims)
"""
import os
import sys

import numpy as np
import sympy as sp

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the chapter directory


def report(tag, ok, label, numbers):
    print("[%s] %s %s: %s" % (tag, "PASS" if ok else "FAIL", label, numbers))
    return ok


def fix_vapor(vapor, major, vol):  # fix_vapor_impl; index 0 is the bottom cell
    nx1 = len(vapor)
    is_, ie = nx1 - 1, 0
    vol0 = vol[0]
    while is_ >= ie:
        if major[is_] <= 0.:
            return 1
        if vapor[is_] >= 0.:
            is_ -= 1
            continue
        i = is_
        sum_vapor = 0.
        sum_major = 0.
        while True:
            w = vol[i] / vol0
            sum_vapor += vapor[i] * w
            sum_major += major[i] * w
            i -= 1
            if not (sum_vapor < 0. and i >= ie):
                break
        if i < ie and sum_vapor < 0.:
            deficit = -sum_vapor
            above = 0.
            for j in range(is_ + 1, nx1):
                if major[j] <= 0.:
                    return 1
                above += vapor[j] * (vol[j] / vol0)
            if above < deficit:
                return 1
            for j in range(is_, ie - 1, -1):
                vapor[j] = 0.
            j = is_ + 1
            while j < nx1 and deficit > 0.:
                w = vol[j] / vol0
                need = deficit / w
                if vapor[j] <= need:
                    deficit -= vapor[j] * w
                    vapor[j] = 0.
                else:
                    vapor[j] -= need
                    deficit = 0.
                j += 1
            return 0
        # borrow only the deficit of (i, is_]: negative cells to zero, each donor gives up D / Q
        deficit = 0.
        donors = 0.
        for j in range(is_, i, -1):
            w = vol[j] / vol0
            if vapor[j] < 0.:
                deficit -= vapor[j] * w
            else:
                donors += vapor[j] * w
        share = deficit / donors if donors > 0. else 0.
        for j in range(is_, i, -1):
            vapor[j] = 0. if vapor[j] < 0. else vapor[j] - vapor[j] * share
        is_ = i
    return 0


def check_C1_downward_borrow():  # test_eos.cpp downward_branch_borrows_the_deficit, accepts_zero_vapor_column
    major = [1.00, 0.85, 0.72, 0.61]
    vapor = [0.2, -0.1, 0., 0.]
    err = fix_vapor(vapor, major, [1.] * 4)
    want0 = 0.2 - 0.2 * (0.1 / 0.2)
    flat = [0.2, -0.1, 0., 0.]
    errf = fix_vapor(flat, [1.] * 4, [1.] * 4)
    ok = (err == 0 and vapor == [want0, 0., 0., 0.] and errf == 0 and flat == [0.1, 0., 0., 0.])
    return report("C1", ok, "a deficit covered from below is borrowed from the donor, whatever the dry density",
                  "column %s (dry density 1, 0.85, 0.72, 0.61); %s (dry density 1)"
                  % (["%.6e" % v for v in vapor], ["%.6e" % v for v in flat]))


def check_C2_upward_fallback():  # test_eos.cpp repairs_bottom_cell_from_above
    major = [1.00, 0.85, 0.72, 0.61]
    vapor = [-1.7e-21, 4.4e-11, 1.0e-11, 1.0e-11]
    before = sum(vapor)
    err = fix_vapor(vapor, major, [1.] * 4)
    moved = 4.4e-11 - vapor[1]
    ok = (err == 0 and vapor[0] == 0. and abs(moved - 1.7e-21) <= 1e-25
          and vapor[2] == 1.0e-11 and abs(sum(vapor) - before) <= 1e-14 * abs(before))
    return report("C2", ok, "a bottom-cell deficit is taken from the first cell above, bounded by the deficit",
                  "transfer %.3e (deficit 1.7e-21); column sum change %.1e" % (moved, sum(vapor) - before))


def check_C3_net_deficit_untouched():  # test_eos.cpp rejects_column_in_net_deficit_without_writing
    vapor = [-0.3, 0.1, 0.1, 0.]
    want = list(vapor)
    err = fix_vapor(vapor, [1.] * 4, [1.] * 4)
    single = fix_vapor([-1e-30], [1.], [1.])
    return report("C3", err == 1 and vapor == want and single == 1,
                  "the upward branch writes nothing when it fails (net deficit, or a single negative cell)",
                  "return %d, column unchanged %s; single cell return %d" % (err, vapor == want, single))


def check_C4_volume_weighted_mass():
    rng = np.random.default_rng(10)
    worst, nfixed = 0., 0
    for _ in range(2000):
        n = int(rng.integers(2, 40))
        vol = list(rng.uniform(0.2, 5., n))
        major = list(rng.uniform(0.1, 2., n))
        vapor = list(rng.uniform(-0.2, 1., n) * np.asarray(major) * 1e-2)
        m0 = float(np.dot(vapor, vol))
        if fix_vapor(vapor, major, vol) == 0:
            nfixed += 1
            worst = max(worst, abs(float(np.dot(vapor, vol)) - m0) / max(abs(m0), 1e-300))
            if min(vapor) < 0.:
                worst = np.inf
    return report("C4", worst < 1e-13 and nfixed > 1000,
                  "a successful repair keeps sum_i V_i rho_{n,i} and leaves no negative cell",
                  "relative column-mass change below 1e-13 (the asserted bound) over %d repaired random columns "
                  "(non-uniform V), no cell negative" % nfixed)


def check_C5_failure_writes_nothing():
    rng = np.random.default_rng(11)
    bad, nfail = 0, 0
    for _ in range(2000):
        n = int(rng.integers(1, 20))
        vol = list(rng.uniform(0.2, 5., n))
        major = list(rng.uniform(0.1, 2., n))
        vapor = list(rng.uniform(-1., 0.3, n))
        copy = list(vapor)
        if fix_vapor(vapor, major, vol) == 1:
            nfail += 1
            # the downward branch may already have rewritten windows above the failing one
            if float(np.dot(copy, vol)) >= 0.:
                bad += 1
    return report("C5", bad == 0 and nfail > 100,
                  "every failure is a column whose total vapour is negative (no repairable column fails)",
                  "%d failures, %d of them on a column with non-negative total" % (nfail, bad))


def check_C6_matches_the_run():
    """data/fixvapor_column.csv is snapy's own repair of a 64-cell column with an interior (cell 40) and a bottom
    (cell 0) deficit, written by evidence/fixvapor_column_run.py against a build at the pin. The port, given the
    same column, dry density and volume weights, must give the same column to round-off."""
    cell, before, after, major, vol = np.loadtxt(os.path.join(HERE, "data", "fixvapor_column.csv"),
                                                 delimiter=",", unpack=True)
    port = list(before)
    err = fix_vapor(port, list(major), list(vol))
    diff = float(np.max(np.abs(np.asarray(port) - after)) / np.max(np.abs(before)))
    changed = [int(c) for c in cell[after != before]]
    m0 = float(np.dot(before, vol))
    rel = abs(float(np.dot(after, vol)) - m0) / m0
    ok = err == 0 and diff < 1e-15 and min(after) >= 0. and rel < 1e-14 and changed == [0, 1, 39, 40]
    return report("C6", ok, "the port reproduces snapy's repair of a column with an interior and a bottom deficit",
                  "return %d; cells changed %s; port and snapy agree to 1e-15 of max|vapour|; min after %.3e; "
                  "relative column-mass change below 1e-14" % (err, changed, min(after)))


def check_C7_failure_after_a_window():
    vapor = [-0.9, 0.1, 0.3, -0.1, 0.2]  # index 0 is the bottom cell
    copy = list(vapor)
    err = fix_vapor(vapor, [1.] * 5, [1.] * 5)
    rewritten = [j for j in range(5) if vapor[j] != copy[j]]
    kept = abs(sum(vapor) - sum(copy)) < 1e-15
    return report("C7", err == 1 and rewritten == [2, 3] and kept,
                  "a failure below an already repaired window leaves that window rewritten, mass kept",
                  "return %d; cells rewritten before the failure %s; column sum change below 1e-15"
                  % (err, rewritten))


def check_C8_window_algebra():  # fix_vapor_impl: deficit, donors, share with V_l/V_0 weights
    """A window of two negative and two donor cells: after the borrow the window keeps sum V rho_n, the donors
    give up D in total, and the V_l/V_0 weights give the same share D/Q as the volumes themselves."""
    V = sp.symbols("V0:4", positive=True)
    a, b = sp.symbols("a b", positive=True)        # the two negative cells hold -a, -b
    p, q = sp.symbols("p q", positive=True)        # the two donors hold p, q
    rho = [-a, -b, p, q]
    D = V[0] * a + V[1] * b
    Q = V[2] * p + V[3] * q
    new = [0, 0, p - p * D / Q, q - q * D / Q]
    keep = sp.simplify(sum(V[i] * new[i] for i in range(4)) - sum(V[i] * rho[i] for i in range(4)))
    given = sp.simplify(V[2] * (p - new[2]) + V[3] * (q - new[3]) - D)
    w = [V[i] / V[0] for i in range(4)]
    ratio = sp.simplify((w[0] * a + w[1] * b) / (w[2] * p + w[3] * q) - D / Q)
    ok = keep == 0 and given == 0 and ratio == 0
    return report("C8", ok, "the borrowed window keeps sum V rho_n, the donors give up D in total, "
                  "and the V_l/V_0 weights give the same share",
                  "three identities exact (sympy)")


def check_C9_independent_of_dry_density():
    """The downward branch does not read the dry density (it is only tested for > 0): the same vapour column
    under two unrelated dry-density profiles is repaired bit for bit the same, and every donor moves by its
    share of the deficit only."""
    rng = np.random.default_rng(12)
    differ, n, worst = 0, 0, 0.
    for _ in range(2000):
        m = int(rng.integers(2, 40))
        vol = list(rng.uniform(0.2, 5., m))
        vapor = list(rng.uniform(-0.2, 1., m) * 1e-2)
        if float(np.dot(vapor, vol)) < 0. or vapor[0] < 0.:
            continue  # the downward branch only: a repairable column whose bottom cell is not negative
        a, b = list(vapor), list(vapor)
        ea = fix_vapor(a, list(rng.uniform(0.1, 2., m)), vol)
        eb = fix_vapor(b, list(rng.uniform(0.1, 2., m)), vol)
        if ea or eb:
            continue
        n += 1
        differ += a != b
        d = sum(-v * vol[j] / vol[0] for j, v in enumerate(vapor) if v < 0.)
        moved = sum((vapor[j] - a[j]) * vol[j] / vol[0] for j in range(m) if vapor[j] >= 0.)
        if d > 0.:
            worst = max(worst, abs(moved - d) / d)
    return report("C9", differ == 0 and n > 500 and worst < 1e-12,
                  "the downward branch ignores the dry density, and the donors give up the deficit and no more",
                  "%d repaired columns, %d differ between two dry-density profiles; donors' loss equals the "
                  "deficit to 1e-12 relative" % (n, differ))


def main():
    checks = [check_C1_downward_borrow, check_C2_upward_fallback, check_C3_net_deficit_untouched,
              check_C4_volume_weighted_mass, check_C5_failure_writes_nothing, check_C6_matches_the_run,
              check_C7_failure_after_a_window,
              check_C8_window_algebra, check_C9_independent_of_dry_density]
    return sum(not c() for c in checks)


if __name__ == "__main__":
    sys.exit(main())
