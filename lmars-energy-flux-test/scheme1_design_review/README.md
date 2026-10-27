# Review of Xinyue's agent's design-check report on ba2b28ce (thread ts 1793073074.858439)

This is a read-only review of the change: nothing was pushed to XinyueWang05/snapy, and nothing was posted on GitHub.

## Shas

Branch heads, from `git ls-remote https://github.com/XinyueWang05/snapy.git`:

- scheme1-donor-momentum: `ba2b28cee183d40a45c066b1d821b632f4b580e3`
- scheme1-design-checks: `3cd814e28f75c29a7f142040a54a7bfc74d82108`
- scheme1-roe-vt: `fb1baebfdc5e08b3a9ea46a03684b89028ffbede` (one commit on top of ba2b28ce)

Base is `a09cc256c3ab5c2a10315ab4bf32169740c2fd52`. The builds are CPU Release from source at base, ba2b28ce and fb1baebf
(gcc 13.3.1, torch 2.10.0, kintera 2.6.6, pyharp 2.7.6). Each is installed with `pip --target site-<base|fix2|roe>`.

## Code read (at ba2b28ce unless noted)

- **du_rho is the total mass increment: confirmed.** `fold_cell` sums `du[IDN]` and every species row
  (vic_assemble_partial_impl.h:201-202), with `ny = nhydro - ICY` (implicit_dispatch.cpp:32).
  `cons[IDN]` is the dry density `(1 - sum y) rho` and `cons[ICY..]` is `y rho` (ideal_moist.cpp:141-146).
- **x1 seams: confirmed N/A.** hydro.cpp:428-431 has
  `TORCH_CHECK(is_physical_boundary(0,0,-1) && is_physical_boundary(0,0,1), "... requires nb1 = 1 ...")`.
  `first_block = last_block = true` is hard-coded in every dispatcher (implicit_dispatch.cpp:33-34, 92-93,
  148-149; implicit_dispatch.cu:43-44, 101-102, 156-157).
- **Gravity work in the E row, including for the folded q_t mass flux: confirmed.** The face-work rows of the
  3x3 blocks are at vic_assemble_partial_impl.h:149-166. The same face-work terms (ApT/AmT mass rows times g)
  are applied to the m_t columns at :183-192.
- **roe-vt (fb1baebf):** each m_t column is split into the flux-Jacobian part (`aJ/bJ/cJ`, cell v_t) and
  the |A| part of each face (`aLo/aHi/bA/cA`). The |A| part, including its face-work rows and the
  wall-merged face, uses that face's Roe-averaged v_t (`vroe_lo/vroe_hi = prim[it]` after RoeAverage).
  The signs match ba2b28ce term by term, and in a uniform wind it reduces to ba2b28ce. The post-solve
  donor transfer from a74d4fb is unchanged.
  Note: the commit message says "dm_t = v drho + q holds for any v". That is a bookkeeping identity; choosing
  a different v in each term changes the implicit drag of m_t by drho, which is a modelling choice.

## Reruns with my own deck and driver

`chk_arm.py` (own deck builder, Gaussian isobaric T noise, seed 7, own budgets with rho_tot = dry + every
species). Physics follows the thread: H2-He 100 K, 450 km / 100 levels, dx 100 km, u0 400, cfl 0.3, 3 d.
Columns use nx2 = 4 with one noise draw copied to every column. The moist column uses the
test_tracer_dry_convention species, 32 km, 320 K.

```bash
run_chk.sh <workdir> base fix2 roe              # 16 arms per build
python chk_compare.py <workdir>/chkruns > chk_results.md
```

| claim (Xinyue: base -> ba2b28ce) | mine: base -> ba2b28ce (roe-vt) | verdict |
|---|---|---|
| shear column, 1e-6 K: s1-s9 mean-u gap / u0, 2.41e-9 -> 1.84e-11 | 1.84e-9 -> 1.33e-10 (1.33e-10) | same pattern; my residual is 7x theirs |
| uniform column, 1e-6 K: 2.48e-9 -> 0 | 3.32e-9 -> 0 (0) | confirmed |
| shear column, 1e-2 K: 2.57e-5 -> 1.99e-7 | 1.78e-5 -> 1.31e-6 (1.31e-6) | same pattern; my residual is 7x theirs |
| uniform column, 1e-2 K: under 5.3e-14 | 4.7e-14 (5.5e-14) | confirmed |
| shear box: base s1 +1.11/d; ba2b28ce s1 = s9 = -0.188/d | base s1 +0.95/d (band, R^2 0.53); s1 = s9 = -0.290/d (R^2 0.51) | same sign and pattern, different numbers |
| box rms-w gap s1 vs s9: shear 1.05e-3, uniform 1.4e-6 | shear 9.3e-4, uniform 1.5e-6 (roe-vt: 9.2e-4 / 1.2e-6) | confirmed |
| moist uniform column max abs(u-u0)/u0 at 3 d: 5.35e-6 -> 5.44e-13 (s9 5.41e-13) | 5.35e-6 -> 5.19e-13 (s9 5.60e-13) | confirmed |
| E+PE drift, uniform box: -1.48e-8 -> -5.49e-13 | -1.14e-8 -> -5.75e-13 (= s9) | confirmed |
| E+PE drift, shear box: -2.07e-11 -> -5.59e-13 | -2.21e-11 -> -5.88e-13 (= s9) | confirmed |
| scheme 9 bitwise across builds | 8/8 scheme-9 runs share one final-state sha256 across base/fix2/roe | confirmed |
| roe-vt changes nothing material | roe-vt equals ba2b28ce to 3 digits in every metric | confirmed |

The differences in the shear numbers are hypothesised to come from the deck: Gaussian (mine) vs uniform
(theirs) noise and a different draw. The qualitative result is the same.

## Loose ends

- **Moist E+PE drift of 1.95e-10: reproduced (1.95e-10 in s1 and s9, every build), and it is a
  diagnostic effect.** It is a one-time step during steps 2-4: 2.0e-10, even at rest with no noise.
  It comes from the initial 0.005 cloud evaporating in subsaturated air, which starts a vertical
  adjustment (rms w 2.3e-3 at step 2).
  - With no cloud: E+PE holds to 4e-15 and the column never moves.
  - Explicit scheme 0 shows the same (E+PE swings 5e-11 to 3e-10 while the column oscillates), so it
    is not the implicit solve. It is also independent of the EOS ftol (1e-6, 1e-8, 1e-10).
  - With `gravity-work: cell` (fixer on), E + rho_tot g z_c holds to 5e-15 through the same motion.
  So the cell-centred PE diagnostic differs from the energy form that face gravity work conserves
  whenever there is vertical mass flux. It is not a leak in the dynamics. Not checked: an exact
  face-form energy budget.
- **Base dx 200 km blow-up time: my earlier report was wrong.** Rerun with Xinyue's driver and seed, base
  blows up at **0.137 d** (303 steps). A repeat run is bitwise identical (sha256 d0eae492...). My earlier
  "0.04 d" was the end of the band fit window, not the blow-up time; it is corrected in
  ../scheme1_fix_review/README.md. Theirs is 0.135 d (295 steps). Hypothesis: the small step-count
  difference is the build (gcc 11.5 vs 13.3 code generation), since the deck, seed and cfl are
  identical. Not tested by building with gcc 11.5. My own deck (Gaussian noise) blows up at 0.146 d.
- **Xinyue's guess that the shear gap comes from m_t staying explicit in scheme 1:** the 1e-2 K shear
  column at ba2b28ce, s1 vs s9 gap / u0 at 3 d:
  - cfl 0.3 (dt 26.3 s): 1.31e-6
  - cfl 0.15 (dt 13.2 s): 2.30e-6
  - cfl 0.075 (dt 6.6 s): 3.26e-6

  The gap grows as dt shrinks, so it is not a splitting or time-integration error that vanishes with
  dt. That is evidence against reading "m_t explicit" as a timestep effect. Hypothesis: schemes 1 and 9
  differ in the semi-discrete vertical operator for m_t under shear, for example because scheme 9's
  |A| row acts on m_t itself. Untested.
