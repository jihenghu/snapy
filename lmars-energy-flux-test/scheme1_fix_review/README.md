# Review: scheme-1 donor-momentum fix (XinyueWang05/snapy, branch scheme1-donor-momentum)

This is a read-only review of the change: nothing was pushed to that fork, and nothing was posted on GitHub.

## Shas

- Fork: XinyueWang05/snapy (parent UCzhangxi/snapy). It was found with
  `gh api repos/chengcli/snapy/forks --paginate` and then the forks of those forks; this is the only fork
  carrying `scheme1-donor-momentum`.
- Branch head (`git ls-remote https://github.com/XinyueWang05/snapy.git refs/heads/scheme1-donor-momentum`):
  `ba2b28cee183d40a45c066b1d821b632f4b580e3`. This is the head that was named, and it had not moved.
- `9825aba9961d665dd72ddf54503ff5c68d24f08e` adds the box runs. Its parent
  `a74d4fbcd0faca643f6e1044692a239af024f58c` carries the code change.
- Merge base with chengcli/snapy main: `a09cc256c3ab5c2a10315ab4bf32169740c2fd52` ("base").
  base..85a3ce1 changes no file under src/ or python/; only study files change.

## Code read

**a74d4fbc (present in 9825aba9).** `vic_tangential_momentum_column`
(src/implicit/vic_redistribute_impl.h:172-186 at 9825aba9 and at ba2b28ce) runs after
`vic_constituent_column`, for `N == 3` only: CPU implicit_dispatch.cpp:217, CUDA implicit_dispatch.cu:227
at ba2b28ce. For each face it takes the total clamped transfer
`q = MASS(IVX+(dir+2)%3, i+1)`, the same quantity used for gravity work, in mass per step with positive
meaning upward. It picks the donor cell by the sign of q and moves `q * W(m, donor)` of both tangential
momenta from cell i to cell i+1: `DU(m,i) -= p/VOL(i); DU(m,i+1) += p/VOL(i+1)`. The column sum of each
tangential momentum is unchanged, and a zero transfer leaves DU bitwise untouched. The matrix itself is
unchanged: m_t is still frozen inside the solve. Only the post-solve mass transfer now carries
momentum, so this is the donor-momentum idea applied after the solve.

**ba2b28ce.** In `vic_assemble_partial_impl` (vic_assemble_partial_impl.h:173-213), with `du` and
`rhs_corr` passed, the 3x3 blocks gain the m_t columns of the same 5x5 flux Jacobian and |A|
(`fold` and `tcols`, :57-64). This covers both the face-work energy rows (:183-192) and the wall-mirror merge
(:194-197). The rho column of each block gets those columns times the v_t of the cell the block
multiplies (`fold_cell`, :199-213). The remainder `q_t = du_t - v_t du_rho` (explicit increments)
goes to the right-hand side as `aT q_i + bT q_{i-1} + cT q_{i+1}`. That value is stored in `delta[i]`
and subtracted by ForwardSweep before `delta[i]` is solved (forward_sweep_impl.h:32-40, 48, 104).
Solid cells zero `delta` (implicit_dispatch.cpp:65, .cu:76). The solve is called with
`rhs_in_delta = (N == 3)` (implicit_dispatch.cpp:166, .cu:172). So the partial solve now uses
dm_t = v_t drho + q_t instead of dm_t = 0. In a uniform wind this is the full 5x5 system restricted
to that ansatz.

**Scheme 0 and 9.** Every addition sits behind `N == 3`, or in the partial assembly or the partial-only
`rhs_in_delta`. The scheme-9 (N = 5) and scheme-0 paths are not touched in code. Scheme 9 is
confirmed bitwise below; scheme 0 was not run.

**Concerns (none blocking):**
1. Inside the solve, the matrix ansatz uses each cell's own v_t (:204). After the solve, a74d4fb moves
   momentum at the face donor's v_t. The two agree in a uniform wind and differ by O(dv_t drho)
   under vertical shear (hypothesis: small, untested).
2. The column residual R that `vic_constituent_column` removes pro rata
   (vic_redistribute_impl.h:99 at base and at ba2b28ce) is not a face transfer, so it carries no tangential momentum.
   Hypothesis: negligible while R is at round-off.
3. ForwardSweep's `rhs_in_delta` relies on the partial assembly having written `delta` for every
   cell just before. Both current call sites do this. A future caller that assembles without
   du/delta would subtract stale values; that is fragile, not a present bug.
4. The CUDA path is code-read only. I made no CUDA build.

Unit tests at ba2b28ce (CPU): `test_vic_partial_tangential` 2/2 passed, `test_backward_substitution` 8/8 passed.

## Runs

Setup: Xinyue's driver from 9825aba9 (`scheme1_donor_momentum/run_arm.py`, copied unchanged as
`run_arm_xw.py`). It is the 97d80e05 driver plus a perturbation-KE diagnostic and a sha256 of the final
state. Deck: 2-D H2-He ideal-moist, 100 K, 10 bar, 450 km / 100 levels, nx2 = 64, LMARS, weno5,
rk3, cfl 0.3, 1e-6 K uniform-random T noise, seed 20261026, 3 d. Builds are CPU Release from source at
base, 9825aba9 and ba2b28ce (gcc 13.3.1, torch 2.10.0, kintera 2.6.6, pyharp 2.7.6), each installed with
`pip install --no-build-isolation --no-deps --target site-<name> .`.

```bash
run_review.sh <workdir>            # 6 arms x {base, fix1 = 9825aba9, fix2 = ba2b28ce}
python compare.py <workdir>/runs > review_results.md
```

Rates follow Xinyue's analyze.py: ln(rms w) is fitted over rms w in [1e-4, 1e-1] if at least 3 rows
fall there ("band"), otherwise over 0.5-3 d. The 0.5-3 d fit is also listed. Full table:
`review_results.md`.

| run (scheme 1, u 400) | base | 9825aba9 | ba2b28ce |
|---|---|---|---|
| box dx 50 km | +1.77/d (0.5-3 d, R^2 0.94) | +2.92 band (1.59-3.00 d, R^2 0.97); +2.85 0.5-3 d (R^2 0.99) | -0.33 (R^2 0.75) |
| box dx 100 km | +31.44 band (0.17-0.38 d, R^2 0.985), rms w 0.49 at 3 d | +1.69 0.5-3 d (R^2 0.98); band only 2.96-3.00 d | -0.248 (R^2 0.60) |
| box dx 200 km | blew up at 0.137 d, 303 steps (+375 band over 0.03-0.04 d, R^2 0.999; correction: earlier text said 0.04 d, which was the end of the fit window) | +0.77 (R^2 0.94) | -0.113 (R^2 0.21) |
| column dx 100 km, max abs(u-u0)/u0 at 3 d | 2.49e-9 | 5.1e-13 | 4.9e-13 |
| scheme-9 box dx 100 km, for reference | -0.248 | -0.248 (bitwise = base) | -0.248 (bitwise = base) |

Relative 3-d drifts at ba2b28ce for scheme 1: rho -1.1e-12 / -5.5e-13 / -2.8e-13; m2 -1.1e-12 /
-5.7e-13 / -2.9e-13; E+rho g z -1.1e-12 / -5.5e-13 / -2.7e-13 (dx 50/100/200). At base, dx 100 gives
E+rho g z -1.5e-8.

At ba2b28ce, the scheme-1 dx 100 box tracks the scheme-9 box to 1.9e-6 relative in rms w over all
433 rows (5.2e-6 in max w). They are not bitwise equal.

Bitwise, by sha256 of the final state and of the diagnostic CSV: the scheme-9 dx 100 box and the
u = 0 no-noise scheme-1 box are identical at all three shas.
