# Independent rerun of e59ed4c0 (HEVI ARK2, 3 stage iterations)

Code: XinyueWang05/snapy `scheme9-hevi-ark2-bc` at e59ed4c0ad3415b07db50de183d22e5f689baf8b. ls-remote returned that sha at the start (16:39 UTC) and at the end (~18:00 UTC), so it did not move. The fork has a new branch `scheme9-hevi-ark2-iter3` at a73c862e8d9cb893217e99eb58eb2349fbd49d49 (leg 1). I did not look at it. Base is ba2b28cee183d40a45c066b1d821b632f4b580e3.

Builds (both from source, CPU, Release, fp64, one thread per run; torch 2.10.0+cu128, kintera 2.6.6, gcc-toolset-13):
- e59ed4c0: a fresh clone, built per the README (`cmake -B build -DCMAKE_BUILD_TYPE=Release -DNETCDF=ON`, `cmake --build build`, `pip install --target`). The first Eigen fetch failed because gitlab.com was overloaded, so I seeded snapy's own `.cache/eigen-3.4.0.tar.gz` with the same tarball the base build used (sha256 1476e3f0…). Nothing else changed.
- ba2b28ce: an existing CPU Release build of chengcli/snapy at ba2b28ce, already in the workspace and reused as is.
- No CUDA build, because it was not quick. No GPU numbers.

Results branch: jihenghu/snapy `hevi-e59ed4c0-rerun` (sha below). It holds the driver, the analysis scripts, every deck, per-arm CSV/JSON and the tables, in `hevi_e59ed4c0_rerun/`, on top of e59ed4c0.

## Setups and assumptions

The deck is rebuilt from Xinyue's `lmars_energy_flux_test/run_arm.py` at e59ed4c0: 2-D Cartesian, x1 vertical with 100 levels and reflecting walls, x2 periodic with 64 columns of width dx, x3 1 m. Dry H2-He (H 1.5, He 0.15, cv_R 2.5), ideal-moist EOS, weno5 in both directions, rk3, cfl 0.3, implicit-scheme 9. The column is balanced with `snapy.balance_column` (10-bar bottom), then gets 1e-6 K Gaussian isobaric T noise (seed 20261025) and a uniform x2 wind.
- 100 K: g 8.87, 450 km. Hot Jupiter: T0 1500 K, g 23, 2570 km.
- HEVI arms add `integration/implicit-integrator: hevi-ark2` and `integration/implicit-integrator-iterations: 3` to the deck (these are the real key names, implicit_hydro.cpp:32,65,75). Base arms leave both keys out, because ba2b28ce rejects them.
- Ladder: dx 5 km, u 400, **lmars** (assumed: the brief names no solver, and the study's dx 5 km deck is lmars). T = 3600 s. dt0 = T / ceil(T / dt_cfl(t=0)) = 1.31291 s (2742 steps), with dt0/k fixed. The reference is scheme 0 at dt0/16 (43 872 steps) on the base build.
- Error norm (assumed): B = ‖q − q_ref‖₂ / ‖q_ref − ⟨q_ref⟩ₓ₂‖₂ over the interior, i.e. relative to the eddy part of the reference. I chose it because it reproduces Xinyue's base numbers (0.026/0.28/0.032/0.065 against 0.028/0.41/0.043/0.095). Norm A (relative to q_ref − q_init) is in `tables.md`: it gives the same ratios, with values about 3× lower.
- Rates: least-squares slope of ln(rms w) against t in days over 0.5–3 d (62 hourly points), ± its standard error. Drift: max over t of |S(t)/S(0) − 1| for mass and for E + ρgz.
- "100 K dx 400 km hllc" was run at u 250 (my reading of Xi's "scheme 9 u250" arm set) and also at u 400.
- u = 0 box: dx 100 km, lmars (assumed), no noise, 3 d.
- Every arm ran the full span (3 d, or 3600 s for the ladder). No run was shortened.

## Table

| item | my number | Xinyue's | holds? |
|---|---|---|---|
| (a) HEVI-3it dt0 err rho/m1/m2/E | 1.44e-3 / 1.99e-3 / 1.04e-3 / 4.77e-3 | 1.8e-3 / 1.8e-3 / 1.8e-3 / 1.1e-2 | yes (same order; my E is 2.3× lower) |
| (a) base dt0 err | 0.026 / 0.283 / 0.032 / 0.065 | 0.028 / 0.413 / 0.043 / 0.095 | yes |
| (a) HEVI-3it dt0/2 err | 8.3e-4 / 3.5e-4 / 5.8e-4 / 4.57e-3 | not given | — |
| (a) base dt0/2 err | 0.0144 / 0.160 / 0.0187 / 0.0463 | not given | — |
| (a) order dt0→dt0/2, HEVI-3it | 0.80 / 2.49 / 0.85 / 0.06 | not given for 3 it | — |
| (a) order dt0→dt0/2, base | 0.86 / 0.82 / 0.77 / 0.49 | — | — |
| (a) HEVI/base error ratio at dt0 | 1/18, 1/142, 1/31, 1/14 | 1/16, 1/230, 1/24, 1/9 | yes |
| (b) HJ dx100 u3000 hllc, HEVI-3it | −0.414 ± 0.034 /d, 0 redos, mass 4.4e-16, E+PE 8.9e-16 | −0.41 /d, drift 6e-16..2e-14 | yes |
| (b) HJ base | +6.63 ± 0.26 /d, 0 redos | +6.75 ± 0.26 /d | yes |
| (c) 100 K dx400 hllc u250, HEVI-3it | −0.045 ± 0.020 /d, 0 redos, mass 2.2e-16, E+PE 1.2e-14 | −0.04 /d | yes |
| (c) same at u400 | −0.048 ± 0.020 /d, 0 redos, mass 3.3e-16 | — | — |
| (c) base u250 / u400 | −0.034 / −0.038 ± 0.020 /d | "like base" | yes |
| (d) u=0 dx100, HEVI-3it rms w | peak 9.4e-11 m/s at 0.29 d, 8.7e-13 at 3 d (max abs w 2.7e-10) | 2e-9 | decays, as she found; my level is ~20× lower |
| (d) mass drift | ≤ 2.4e-15 (E+PE 1.3e-15) | 1e-16..1e-14 | yes |

Other measurements:
- Ladder below dt0/2 with HEVI-3it: rho, m2 and E stay flat at 8.2e-4, 5.7e-4 and 4.6e-3 at dt0/4 and dt0/8, while m1 keeps converging (7.7e-5, 2.3e-5). I read this as a floor between the dt→0 limit of HEVI and the scheme-0 reference, and Xinyue also calls E a reference floor. Hypothesis, untested: it is a spatial/source difference between the scheme-9 and scheme-0 operators. Base is still above that floor at dt0/8 (5.2e-3 / 0.060 / 6.7e-3 / 0.030).
- The u = 0 box with base keeps rms w at about 1e-13. HEVI first moves about 1e-10 off the discrete balance, then decays.
- Cost on CPU: HEVI-3it is 2.35–2.45× base wall time per step (ladder dt0: 209 s against 89 s; HJ 3 d: 3766 s against 1537 s). The step dt is the same, and HEVI is still horizontal-CFL bound here.

## Code read (ba2b28ce..e59ed4c0, 3 commits, 10 files, +276/−6)

All file:line references are at e59ed4c0ad3415b07db50de183d22e5f689baf8b.
- **hevi-ark2 option**: `integration/implicit-integrator` is parsed at src/implicit/implicit_hydro.cpp:65-74. Only `rk` or `hevi-ark2` is accepted (:67). hevi-ark2 requires bit 3 of the scheme (:70). Since `type()` (:101-115) admits only 0, 1 and 9, that bit holds only for scheme 9. The default is `"rk"` (implicit_hydro.hpp:51). test_hevi_ark2_options passes and rejects scheme 1 and unknown names. Confirmed.
- **Default rk path unchanged**: MeshBlockImpl::advance_local diverts only when `integrator() == "hevi-ark2"` (src/mesh/meshblock.cpp:727-728). hydro_forward.cpp:1129 and :1192 keep the old dt_corr and the implicit correction under `hevi_mode == 0`, and hydro.hpp:238 defaults it to 0. Runtime check: the scheme-9 rk dt0 ladder arm on the e59ed4c0 build gives a final-state sha256 equal to ba2b28ce's (62fd3dea21c15c7c…), and the diagnostic CSV is identical apart from the wall-clock column. Confirmed.
- **Stage iterations**: the deck key is `integration/implicit-integrator-iterations`, whitelisted at implicit_hydro.cpp:32, parsed at :75-80 (n ≥ 1) and defaulted to **1** at implicit_hydro.hpp:55. It is used at meshblock.cpp:682-689 as D ← D + (I + gΔtJ)⁻¹(gΔt V(R+D) − D), with the offset subtracted at hydro_forward.cpp:1186-1190. Confirmed; the default is 1, as expected.
- **apply_boundaries on predictor and stage states**: `refresh_ghosts` (meshblock.cpp:671-674) runs exchange_ghost_zones and then apply_boundaries. It is applied to the predictor R before the first implicit forward (:677) and to every iterate R + D (:685). The stage state Q = R + D gets the limiter and then apply_boundaries (:695), and so does the final update (:720). The explicit forwards of stages 1 and 2 read those states after MeshBlock::forward's exchange (:556). Confirmed.
- ARS(2,3,2) tableau (:645, :710, :713-714, :717-718): γ = 1 − 1/√2, δ = −2√2/3, b = (0, 1−γ, γ). It matches Ascher–Ruuth–Spiteri 1997.

Flags (none of them changes the numbers above):
1. With `implicit-scheme` 0 or absent, from_yaml returns at implicit_hydro.cpp:35-42 before it reads the integrator keys. `implicit-integrator: hevi-ark2` is then silently ignored and the run is explicit. I checked this: scheme 0 + hevi-ark2 gives a state sha equal to plain scheme 0 after 8 steps. The scheme-1 case errors correctly.
2. `implicit-integrator-iterations` is accepted and silently ignored when the integrator is rk.
3. No test exercises iterations > 1. test_hevi_ark2_options and the two `_hevi` ctest entries run the default 1.
4. `explicit_split`'s `keep_v` argument is always false (meshblock.cpp:659,664), so it is dead code.

## Commands

```
git ls-remote https://github.com/XinyueWang05/snapy.git            # start and end
git clone -b scheme9-hevi-ark2-bc https://github.com/XinyueWang05/snapy.git src
hevi_e59ed4c0_rerun/kit/build.sh                                    # e59ed4c0 CPU build
LAD="--setup c100 --solver lmars --u 400 --dx 5e3 --tend 3600 --diag-dt 600"
H="--integrator hevi-ark2 --iters 3"
launch.sh base ref_s0_d16 $LAD --scheme 0 --dtdiv 16
launch.sh {base,hevi} lad_s9_d{1,2,4,8} $LAD --scheme 9 --dtdiv k [$H]
launch.sh {base,hevi} hj_hllc_u3000_dx100 --setup hj --solver hllc --u 3000 --dx 100e3 [$H]
launch.sh {base,hevi} c100_hllc_u{250,400}_dx400 --setup c100 --solver hllc --u {250,400} --dx 400e3 [$H]
launch.sh {base,hevi} u0_lmars_dx100_nonoise --setup c100 --solver lmars --u 0 --dx 100e3 --noise 0 [$H]
python analyze.py runs tables.md
python src/tests/test_hevi_ark2_options.py                          # PASSED
```

## Verdict

At 3 stage iterations set in the deck, Xinyue's e59ed4c0 numbers hold:
- the dx 5 km errors are at her level and 14–140× below base at dt0;
- hot Jupiter −0.414 ± 0.034/day against her −0.41 (base +6.63 against +6.75);
- 100 K dx 400 km −0.045 ± 0.020 against −0.04;
- 0 redos and round-off mass drift everywhere.

The only difference is the u = 0 rms w, which in my run is ~20× below her 2e-9 and decays in both.

Not covered here: GPU, the tall-column cubed-sphere test, ladder errors below dt0/2 compared against hers, and whether 3 iterations should be the default.

## Addendum: u = 0 box at 600 s sampling

`kit/hevi_arm_cadence.py` is a copy of `kit/hevi_arm.py` with a `--diag-steps` flag: it also samples at the listed step numbers, and the next sample time advances past t after each sample. The diagnostics never change dt, so the time stepping is the same. The rerun used the same e59ed4c0 build, the same deck (byte-identical yaml) and the original arguments, plus `--diag-dt 600 --diag-steps 164`:

```
kit/hevi_arm_cadence.py --out runs/cad600/u0_lmars_dx100_nonoise --setup c100 --solver lmars --u 0 --dx 100e3 \
  --noise 0 --integrator hevi-ark2 --iters 3 --diag-dt 600 --diag-steps 164
```

Results (`runs/cad600/`, 434 rows):
- Final conserved state sha256 equals the 3600 s run's (e2ecf32b...), with 6414 steps and 0 redos.
- All 74 rows of `runs/hevi/u0_lmars_dx100_nonoise.csv` reappear at the same steps with every printed digit equal, apart from the wall-clock column.
- Step 164 (t = 6627.83 s; also the first step past 6600 s): rms w = 2.2188e-10 m/s. This is the series maximum.
- At 3 d (step 6414): 8.6925e-13.
- At 600 s sampling, rms w oscillates between about 3e-11 and 2e-10 over the first hours. The 3600 s sampling's maximum was 9.37e-11 (step 624).
