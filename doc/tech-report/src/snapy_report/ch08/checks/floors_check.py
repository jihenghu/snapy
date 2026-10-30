"""Executable check of the equation-of-state limiter, its floors and the condensate
borrow (chapter 8, _eoslimiter.qmd, _borrow.qmd, _marks.qmd).

Ports, statement for statement, of EquationOfStateImpl::apply_conserved_limiter_
(src/eos/equation_of_state.cpp:192-322) and apply_primitive_limiter_ (:325-350) at
snapy@e894700ff7aee30b52882e5202b16461413780b0, with the YAML defaults at :65-72.

The claims test what the operator DOES to a state, not what its formula says: C1 reorders
the passes and measures the difference, C2 measures the mass and energy a floor invents,
and C3 compares the shipped repair against the one the code comment says it replaced. C8 ports the
multi-parent borrow and its normalised fractions (equation_of_state.cpp:136-160, 262-268) at
snapy@6fbb39750f62b83df096058a4746e77d0a634bc5.

Run: python3 floors_check.py   (numpy only; exits with the number of failed claims)
"""
import sys

import numpy as np

FAIL = []
DENSITY_FLOOR = 1.0e-6     # equation_of_state.cpp:65
PRESSURE_FLOOR = 1.0e-3    # :71
TEMPERATURE_FLOOR = 20.0   # :72
CV = 718.0                 # a dry-air heat capacity, for the energy floor only


def report(tag, ok, what, detail):
    print(f"[{tag}] {'PASS' if ok else 'FAIL'} {what}: {detail}")
    if not ok:
        FAIL.append(tag)


def conserved_limiter(dens, mom, etot, species, mark_interior=True):
    """apply_conserved_limiter_, :201-235, in the order the code runs it:
    NaN to zero, then the dry-density floor, then the energy floor built from the
    ALREADY floored density. Returns the state and the two marks."""
    patched = nan_seen = False
    for a in (dens, mom, etot, species):
        if np.isnan(a).any():
            nan_seen = True
            a[np.isnan(a)] = 0.                       # :203
    before = (dens.copy(), etot.copy())
    np.maximum(dens, DENSITY_FLOOR, out=dens)         # :209
    rho = dens + species.sum(0)                       # :229
    ke = 0.5 * (mom ** 2).sum(0) / rho                # :230
    min_ie = rho * CV * TEMPERATURE_FLOOR             # :231-232, "UT->I"
    np.maximum(etot, ke + min_ie, out=etot)           # :233
    if not np.array_equal(dens, before[0]) or not np.array_equal(etot, before[1]):
        patched = True
    return dens, mom, etot, species, (patched and mark_interior, nan_seen and mark_interior)


# --- C1: the order of the two floors is load-bearing ---------------------------
def check_C1():
    """The energy floor is built from rho AFTER the density floor (:229 reads cons[IDN],
    which :209 has already clamped). Reversing the two gives a different state."""
    rng = np.random.default_rng(1)
    worst = 0.
    hits = 0
    for _ in range(3000):
        n = 8
        dens = rng.uniform(0., 3e-6, n)          # straddles the density floor
        mom = rng.normal(0., 1e-3, (3, n))
        etot = rng.uniform(0., 1e-2, n)
        spec = np.zeros((1, n))
        a = conserved_limiter(dens.copy(), mom.copy(), etot.copy(), spec.copy())[2]
        # the same two statements in the other order
        d2, e2 = dens.copy(), etot.copy()
        rho2 = d2 + spec.sum(0)
        ke2 = 0.5 * (mom ** 2).sum(0) / np.maximum(rho2, 1e-300)
        np.maximum(e2, ke2 + rho2 * CV * TEMPERATURE_FLOOR, out=e2)
        np.maximum(d2, DENSITY_FLOOR, out=d2)
        d = np.max(np.abs(a - e2))
        if d > 0.:
            hits += 1
        worst = max(worst, d)
    report("C1", hits > 0 and worst > 1e-9,
           "the energy floor uses the already-floored density, so the two passes do not commute",
           f"reversing them changes the energy in {hits} of 3000 random states, by up to "
           f"{worst:.2e} in absolute energy; a cell below the density floor gets a different "
           f"minimum internal energy under each order")


# --- C2: the floors are not conservative ---------------------------------------
def check_C2():
    """A floor is a clamp: it invents whatever mass or energy the state was missing.
    Measure it rather than assert it."""
    rng = np.random.default_rng(2)
    n = 4000
    dens = rng.uniform(-1e-7, 5e-6, n)
    mom = np.zeros((3, n))
    etot = rng.uniform(-1e-3, 1e-2, n)
    spec = np.zeros((1, n))
    m0, e0 = dens.sum(), etot.sum()
    d1, _, e1, _, _ = conserved_limiter(dens.copy(), mom, etot.copy(), spec)
    dm, de = d1.sum() - m0, e1.sum() - e0
    report("C2", dm > 0. and de > 0.,
           "the floors invent mass and energy; they are repairs, not conservative operations",
           f"on 4000 cells straddling the floors they add {dm:.3e} of dry mass and "
           f"{de:.3e} of total energy, both strictly positive: a clamp can only add. "
           f"Nothing anywhere removes it again")


# --- C3: the condensate borrow against the repair it replaced ------------------
def check_C3():
    """:242-268. A negative condensate means a neighbour has the mass, so zeroing it
    invents mass. The shipped repair borrows the deficit from the parent vapour in the
    same cell, which moves mass between rows and creates none."""
    rng = np.random.default_rng(3)
    n = 2000
    vapour = rng.uniform(1e-3, 1e-2, n)
    cloud = rng.uniform(-2e-4, 1e-3, n)
    total0 = vapour + cloud
    # the repair the comment says was measured at 102% of the total-mass drift
    cloud_zeroed = np.maximum(cloud, 0.)
    drift_zero = (vapour + cloud_zeroed - total0).sum()
    # the shipped repair: borrow the deficit from the parent vapour, one parent, share 1
    deficit = np.minimum(cloud, 0.)                  # :264
    vap_b = vapour + deficit * 1.0                   # :266
    cloud_b = np.maximum(cloud, 0.)                  # :268
    drift_borrow = (vap_b + cloud_b - total0).sum()
    neg_vap = int((vap_b < 0.).sum())
    report("C3", abs(drift_borrow) < 1e-18 and drift_zero > 1e-6,
           "the condensate borrow conserves mass where a clamp to zero invents it",
           f"over {n} cells with negative condensate, clamping to zero adds {drift_zero:.3e} "
           f"of mass while the borrow changes the total by {drift_borrow:.1e}; "
           f"{neg_vap} cells went vapour-negative and are left to the column repair")


# --- C4: the marks ---------------------------------------------------------------
def check_C4():
    """:202 and :235. Mark 1 is set by a NaN, mark 0 by any density or energy repair,
    and only for the interior: a repair in a ghost cell must not force a redo."""
    rng = np.random.default_rng(4)
    clean = (np.full(6, 1.0), np.zeros((3, 6)), np.full(6, 1e5), np.zeros((1, 6)))
    _, _, _, _, marks_clean = conserved_limiter(*[a.copy() for a in clean])
    low = (np.full(6, 1e-9), np.zeros((3, 6)), np.full(6, 1e5), np.zeros((1, 6)))
    _, _, _, _, marks_low = conserved_limiter(*[a.copy() for a in low])
    nan = (np.full(6, 1.0), np.zeros((3, 6)), np.full(6, np.nan), np.zeros((1, 6)))
    _, _, _, _, marks_nan = conserved_limiter(*[a.copy() for a in nan])
    ghost = (np.full(6, 1e-9), np.zeros((3, 6)), np.full(6, 1e5), np.zeros((1, 6)))
    _, _, _, _, marks_ghost = conserved_limiter(*[a.copy() for a in ghost],
                                                mark_interior=False)
    ok = (marks_clean == (False, False) and marks_low[0] and marks_nan[1]
          and marks_ghost == (False, False))
    report("C4", ok,
           "a repair marks the block for a redo, and only from the interior",
           f"an untouched state marks nothing {marks_clean}; a density below the floor sets "
           f"the patch mark {marks_low}; a NaN sets the NaN mark {marks_nan}; the same "
           f"density repair outside the interior marks nothing {marks_ghost}")


# --- C5: the primitive pass floors a different set of rows ---------------------
def check_C5():
    """:325-350. The primitive pass floors rho and p and clamps species at zero. It does
    NOT floor temperature, and it has no energy row to repair: the two passes are not the
    same operation applied to different variables."""
    rho = np.array([1e-9, 1.0])
    p = np.array([1e-9, 1e5])
    y = np.array([[-1e-9, 0.2]])
    rho_f = np.maximum(rho.copy(), DENSITY_FLOOR)     # :333
    y_f = np.maximum(y.copy(), 0.)                    # :346
    p_f = np.maximum(p.copy(), PRESSURE_FLOOR)        # :349
    report("C5", rho_f[0] == DENSITY_FLOOR and p_f[0] == PRESSURE_FLOOR
           and y_f[0, 0] == 0. and rho_f[1] == 1.0,
           "the primitive pass floors density and pressure and clamps species, and floors "
           "no temperature",
           f"density {rho[0]:.0e} -> {rho_f[0]:.0e}, pressure {p[0]:.0e} -> {p_f[0]:.0e}, "
           f"a negative mass fraction -> {y_f[0, 0]:.0e}; an admissible cell is untouched. "
           f"The conserved pass instead floors energy through a temperature floor of "
           f"{TEMPERATURE_FLOOR:.0f} K, which has no primitive counterpart")


def check_C6():
    """_wbface.qmd: the non-positive face pressure falls back to the reference, which is positive."""
    rng = np.random.default_rng(86)
    p_ref = rng.uniform(1e2, 1e5, 200_000)          # the reference face pressure, positive by construction
    at_rest = p_ref + 0.0                           # at rest the perturbation is identically zero
    fires_at_rest = int(np.count_nonzero(at_rest <= 0.))
    untouched = int(np.count_nonzero(at_rest.view(np.int64) == p_ref.view(np.int64)))
    dp = rng.normal(0., 3e4, 200_000)               # a perturbation large enough to cross zero
    psf = p_ref + dp
    out = np.where(psf <= 0., p_ref, psf)           # hydro_forward.cpp:357-360
    fired = int(np.count_nonzero(psf <= 0.))
    report("C6", fires_at_rest == 0 and untouched == p_ref.size and bool((out > 0.).all()),
           "the face-pressure fallback cannot fire at rest and is positive whenever it does",
           f"at rest the face pressure is the reference bit for bit in {untouched} of "
           f"{p_ref.size} faces and never non-positive, so the well-balanced state is untouched; "
           f"with a perturbation the fallback fires at {fired} faces and the result is strictly "
           f"positive at all {out.size}. The density fallback is the adjacent cell's value, chosen "
           f"from a run rather than from theory, and is not checked here")


def check_C7():
    """_redo.qmd: a margin above the floor, not equality with it."""
    floored = DENSITY_FLOOR                          # a cell the limiter has just set to the floor
    nudges = [0.] + [10.0**-k for k in range(16, 2, -1)]
    nudged = [floored * (1. + d) for d in nudges]
    margin = [v <= 1.001 * DENSITY_FLOOR for v in nudged]      # meshblock.cpp:1199-1202
    equal = [v == DENSITY_FLOOR for v in nudged]               # the test the margin replaces
    lost = [d for d, m, e in zip(nudges, margin, equal) if m and not e]
    far = 1.002 * DENSITY_FLOOR                      # well above the floor: neither test may fire
    report("C7", all(margin) and len(lost) > 0 and not any(e for d, e in zip(nudges, equal) if d > 1e-15)
           and not (far <= 1.001 * DENSITY_FLOOR),
           "the redo detector tests a margin above the floor, so a nudged cell is still a hit",
           f"of {len(nudges)} nudges of a just-floored cell the 1.001 margin counts all "
           f"{sum(margin)} as hits; equality with the floor counts only {sum(equal)}, the "
           f"unnudged cell and the one nudge below machine epsilon. The {len(lost)} nudges from "
           f"{min(lost):.0e} to {max(lost):.0e} relative are the hits the margin keeps and "
           f"equality loses. A density 1.002 times the floor is a hit under neither test")


def check_C8():
    """_borrow.qmd. The parent fractions are cached normalised, f_k = nu_k mu_k / sum nu mu
    (equation_of_state.cpp:136-160), and the deficit d < 0 of a cloud is added as d f_k to each
    parent before the cloud is set to zero (:262-268). The cell total changes by d (sum f_k - 1)
    plus the rounding of the additions: zero because the fractions sum to one, for any number of
    parents. The same additions with un-normalised weights nu_k mu_k do not conserve."""
    from fractions import Fraction as Fr
    rng = np.random.default_rng(8)
    u = np.finfo(np.float64).eps / 2
    worst, raw_worst, n = 0., 0., 0
    for _ in range(2000):
        k = int(rng.integers(1, 5))                          # parents of the nucleation reaction
        nu = rng.integers(1, 4, k).astype(float)
        mu = rng.uniform(0.002, 0.2, k)                      # kg/mol
        mass = nu * mu                                        # :148
        total_mass = 0.
        for m in mass:                                        # :150, in order
            total_mass += m
        frac = mass / total_mass                              # :157-160
        vap = rng.uniform(1e-3, 1e-2, k)
        d = -rng.uniform(0., 2e-4)                            # the deficit, :264
        new = vap + d * frac                                  # :266
        change = sum(Fr(a) for a in new) - sum(Fr(a) for a in vap) - Fr(d)   # cloud d -> 0
        bound = u * ((k + 1) * abs(d) + float(new.sum()))
        worst = max(worst, float(abs(change)) / bound)
        raw = vap + d * mass                                  # the same additions, un-normalised
        raw_worst = max(raw_worst, abs(float(raw.sum() - vap.sum() - d)))
        n += 1
    report("C8", worst <= 1. and raw_worst > 1e-6,
           "the borrow conserves the cell total because the parent fractions are normalised",
           f"over {n} cells with 1 to 4 parents the total changes by at most {worst:.2f} of "
           f"eps_m/2 ((K + 1)|d| + sum of the parents); the same additions with the un-normalised "
           f"weights nu mu change it by up to {raw_worst:.2e}")


def check_C9():
    """_reconfloors.qmd. ReconstructOptionsImpl::from_yaml (reconstruct.cpp:14-38) at
    snapy@6fbb39750f62b83df096058a4746e77d0a634bc5 returns the C++ default, shock = true
    (reconstruct.hpp:51), unless the deck has dynamics/reconstruct/<section>; only then is
    shock read, with false as its default. The density and pressure face floors run only with
    shock false, so a deck without that section gets none of them; the species faces are clamped
    with the limiter on either way (ReconstructImpl::forward at
    snapy@c0c38593d3d3f37bebe204a590610fd7daa05a5f)."""
    CXX_DEFAULT = True                                    # reconstruct.hpp:51

    def shock(deck, section):
        dyn = deck.get("dynamics")
        if dyn is None or "reconstruct" not in dyn:      # :19-20
            return CXX_DEFAULT
        node = dyn["reconstruct"] or {}
        if section not in node:                          # :29
            return CXX_DEFAULT
        return bool((node[section] or {}).get("shock", False))   # :33

    decks = {
        "no dynamics block": {},
        "no reconstruct block": {"dynamics": {"equation-of-state": {"limiter": True}}},
        "vertical only": {"dynamics": {"reconstruct": {"vertical": {"type": "weno5"}}}},
        "both sections": {"dynamics": {"reconstruct": {"vertical": {"type": "weno5"},
                                                       "horizontal": {"type": "weno5"}}}},
        "shock set": {"dynamics": {"reconstruct": {"vertical": {"shock": True}}}},
    }
    got = {name: (shock(d, "vertical"), shock(d, "horizontal")) for name, d in decks.items()}
    want = {"no dynamics block": (True, True), "no reconstruct block": (True, True),
            "vertical only": (False, True), "both sections": (False, False),
            "shock set": (True, True)}
    # the statement "false by default from YAML" predicts False for every direction a deck
    # does not set explicitly
    old = {name: (False, False) for name in decks}
    old["shock set"] = (True, True)
    old_wrong = sorted(n for n in decks if old[n] != got[n])
    report("C9", got == want and len(old_wrong) > 0,
           "shock is false only where the deck has the reconstruct section of that direction; "
           "otherwise it keeps the C++ default, true, and the density and pressure face floors do not run",
           "; ".join(f"{n}: vertical {v}, horizontal {h}" for n, (v, h) in got.items()) +
           f". A reading of 'false by default from YAML' is wrong for {len(old_wrong)} of "
           f"{len(decks)} decks ({', '.join(old_wrong)})")


CHECKS = (check_C1, check_C2, check_C3, check_C4, check_C5, check_C6, check_C7, check_C8, check_C9)
for fn in CHECKS:
    fn()
print(f"{len(CHECKS) - len(FAIL)}/{len(CHECKS)} claims pass")
sys.exit(len(FAIL))
