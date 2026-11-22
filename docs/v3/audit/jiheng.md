# V3 closing Audit 1, one place: homes in hydro, mesh, implicit, forcing, sedimentation, bc, chemistry, input (Jiheng)

Findings only: no source change. Target: UCzhangxi/snapy `v3/wave3` = `d3178f207b60663ff966b7c7ef20025821ef52fa`, pinned with `git ls-remote` at 2026-11-22T16:47:49Z. All file:line references are at d3178f20.

## Scope and method

- **Homes covered:** `src/hydro`, `src/mesh`, `src/implicit`, `src/forcing`, `src/sedimentation`, `src/bc`, `src/chemistry`, `src/input` (16,188 lines with `wc -l`). Copies were searched in all of `src/`.
- **Passes, in order:**
  1. Repeated floating-point literals in all of `src/` (constants, epsilons, defaults).
  2. Option defaults defined twice or three times: hand readers `node[...].as<T>(default)` against `ADD_ARG(...) = default`, and against the generated option tables in `src/options/*.yaml`.
  3. A content-based copy-paste detector over all of `src/` (`dupblocks.py`, below), with windows of 5 and 3 normalized code lines (comments, blank, brace-only, `#include` and `namespace` lines dropped). It reports a group only when one copy lies in my homes.
  4. Targeted formula searches: sound speed, kinetic and potential energy, gravity and gravity work, face area × flux divergence, `divergence(` callers (flux assembly outside the register), Stokes/Cunningham sedimentation velocity, metric sines.
  5. Same-name function definitions in more than one file.
- **Classification:** each hit was read by hand. Semantic near-duplicates (same shape, different meaning or operands) are listed separately and are **not** counted as findings.
- **Net lines:** counted as DESIGN.rst 6.1 defines the line budget (happysky19 v3-design/DESIGN 449636b3, section 6.1). That is `wc -l` over `.cpp/.hpp/.h/.cu/.cuh` under `src/`; changes to `src/options/*.yaml` are not counted. Each row's figure is lines removed minus lines added by the proposed form. These are estimates, not built.
- **Expected result:** "bitwise (hypothesis)" means the proposed form performs the same operations in the same order, by reading. No row was built or run in this audit.

## Findings (homes in my set)

| # | what | every site (file:line at d3178f20) | stays | the others become | expected result | net lines |
|---|---|---|---|---|---|---|
| 1 | Static face gauge `0.5 (p0 + p0 shifted one cell along the sweep axis)` from `perturb->pressure0` | `src/hydro/sweep.cpp:59-64` (horizontal FP64 path); `src/hydro/sweep.cpp:118-123` (static-gauge fallback in `riemann_solve`) | one static helper in sweep.cpp, `static_face_gauge(p0, axis)` | both blocks call it (1 line each) | bitwise (hypothesis: same ops, same order) | -4 (12 removed, 2 calls + 6-line helper) |
| 2 | Conservative face fluxes applied outside the flux register: the general diffusion path builds every row's face flux (energy included) and applies `du -= dt * coord->divergence(...)` itself. Cubed-sphere diffusion posts its energy rows to the register (A-ph3) but keeps a second, unposted route | `src/forcing/diffusion.cpp:698-700` (all rows, own divergence); `src/forcing/diffusion_cubed_sphere.cpp:392-397` (`posted ? posted_ : cubed_sphere_fluxes(...)`, own divergence when not posted) | the register route: `post_fluxes` adds the energy rows to `total(d)` as "diffusion" (A.rst 3.7) | general diffusion gets the same `post_fluxes`; the unposted cubed-sphere route is used only by direct `forward()` callers (tests) and can go once they post | not bitwise: du[IPR] becomes the divergence of the summed total, a round-off change like A-ph3's named one (under G8). Hypothesis; decks with non-cubed-sphere diffusion change. A-ph3 scoped its post to cubed sphere ("decks without cubed-sphere diffusion unchanged") | +8 (estimate: post_fluxes for the general path ~+10, one line removed; the unposted route is not removed here) |
| 3 | x1 face divergence `(A[is+1:ie+1] F[is+1:ie+1] - A[is:ie] F[is:ie]) / V[is:ie]` written by hand, twice, in the gravity energy correction; the same form as the x1 term of `CoordinateImpl::divergence` | `src/hydro/hydro_forward.cpp:1057-1061` (`vertical_mass_div`); `src/hydro/hydro_forward.cpp:1074-1078` (`potential_flux_div`); canonical x1 term `src/coord/coordinate.cpp:686-692` | a local lambda `x1div(F)` in that block. `coord->divergence(F, {}, {})` also fits but allocates the full array and adds the x1 term to zeros (0 + x is exact) | both expressions call the lambda | bitwise (hypothesis) | -3 (10 removed, 2 calls + 5-line lambda) |
| 4 | Option defaults repeated as literals in the const_gravity reader | reader `src/forcing/const_gravity.cpp:22-25, 30, 37` (`grav1/2/3` 0., `non-hydrostatic` 1., `gravity-work` "face", `gravity-work-fixer` false); `ADD_ARG` defaults `src/forcing/forcing.hpp:50, 55, 57-60` | the `ADD_ARG` defaults | the reader reads `node[k].as<T>(op->x())`, as `src/sedimentation/sed_options.cpp:96-99` already does | bitwise (checked by reading: the literals equal the `ADD_ARG` defaults, outputs below) | 0 |
| 5 | Option defaults repeated in the implicit reader | `src/implicit/implicit_hydro.cpp:50-51` ("auto", true); `src/implicit/implicit_hydro.hpp:49-50` | the `ADD_ARG` defaults | `.as<T>(op->x())` | bitwise (checked by reading) | 0 |
| 6 | Option defaults repeated in the MeshBlock reader | `src/mesh/meshblock_options.cpp:54-55` ("eager", false); `src/mesh/meshblock.hpp:94-95` | the `ADD_ARG` defaults | `.as<T>(op->x())` | bitwise (checked by reading) | 0 |
| 7 | `blocks_per_process` default 1 written three times, and the option held in two structs | `src/mesh/mesh.hpp:42` (`MeshOptions`); `src/mesh/mesh.cpp:244` (reader literal `1`); `src/layout/layout.hpp:131` (`LayoutOptions` mirror, copied from `MeshOptions` at `src/mesh/mesh.cpp:263, 276`) | `MeshOptions::blocks_per_process` (mesh.hpp:42), the one the deck reader fills | the reader uses `.as<int>(options->blocks_per_process())`. The `LayoutOptions` mirror is Linfeng's (layout home); listed there too | bitwise (checked by reading) | 0 (mesh side) |
| 8 | Internal-boundary options defined three times: table, `ADD_ARG` and hand reader | `src/options/internal_boundary.yaml:13-15` (rows-only table, defaults 5, 1.e3, 1.e9); `src/bc/internal_boundary.hpp:49-51` (`ADD_ARG` with the same defaults); `src/bc/internal_boundary.cpp:28-33` (`check_keys` + three `.as<T>(literal)` reads). Kept equal only by gate G-3 (`tests/test_options_table.cpp`) | the table, made a `struct:` table like the forcing tables (generated `_members.inc` and `_read.inc`) | the `ADD_ARG` lines go and the reader body becomes the generated read. `from_yaml(filename)` stays | bitwise (hypothesis; G-3 already asserts table = parser on every in-tree deck) | -6 (3 `ADD_ARG` + ~7 reader lines removed, ~4 include/call lines added; the yaml `struct:` line is not counted) |
| 9 | Verbose stage-timing report written seven times | `src/hydro/hydro_forward.cpp:383-387, 564-568, 809-813, 906-910, 969-973, 1132-1136, 1179-1183` (`end = now(); elapsed = end - start; SINFO(...)`, all against the one `start` at :301) | a local lambda `report_time(label)` | each block is one call | bitwise (logging only, no numerics) | -23 (35 removed, 7 calls + 5-line lambda) |
| 10 | Interior bounds and extents `si/ei, sj/ej, sk/ek, n1..n3` from `pg_->il()..ku()` written four times | `src/forcing/axial_momentum.cpp:71-74` (no `n1`), `112-115`, `138-141`, `197-200` | one private member returning the bounds struct | four structured bindings | bitwise (hypothesis) | -6 (16 removed, 4 + ~6 added) |
| 11 | Register part lookup written twice with the same body (key `part@dim`, TORCH_CHECK, `_parts.at`) | `src/hydro/flux_register.cpp:260-265` (`part_slot`); `src/hydro/flux_register.cpp:267-272` (`kept`) | `kept` | `part_slot` returns `kept(dim, part)` | bitwise (hypothesis; both return the same tensor handle) | -4 |
| 12 | CUDA sync-debug mode disabled and restored around a block, twice | `src/mesh/stage_executor.cpp:211-220`; `src/mesh/stage_executor.cpp:238-248` (get, set disabled, restore in catch, restore after) | one small RAII guard in stage_executor.cpp | both blocks declare the guard | bitwise (no numerics) | 0 (8 removed, 2 + ~6-line guard) |
| 13 | Centroid-shift and stencil setup (`centroid`, `ds`, `rho`, `dx1`) written twice | `src/hydro/hydro_forward.cpp:130-137` (`_flux_covariance`, :46); `src/hydro/hydro_forward.cpp:274-281` (`scalar_flux_covariance`, :225) | one helper returning `{centroid, ds, dx1}` | both functions call it | bitwise (hypothesis) | -4 (16 removed, 2 + ~10 added) |
| 14 | Wall-clamp predicates (`il`, `thin`, `fits`, `wall_in`, `wall_out`) written in two device functions | `src/hydro/hydro_ref_x1_impl.h:142-146`; `src/hydro/hydro_ref_x1_impl.h:164-171` | one inline DISPATCH_MACRO helper returning the flags | both call it | bitwise (hypothesis) | 0 (10 removed, 2 + ~8 added) |
| 15 | "Is this face reflecting" tested on the BC name string while a predicate on the BC function exists | name tests: `src/forcing/diffusion.cpp:421` (`names[0] == "reflecting_inner"`), `src/forcing/diffusion.cpp:441-442` and `src/mesh/meshblock_exchange.cpp:149` (`compare(0, 10, "reflecting")`); canonical `src/bc/bc_func.cpp:238` `is_reflecting(bcfunc_t)` | `is_reflecting` | `is_reflecting(bfuncs()[f])` | bitwise (hypothesis: only `reflecting_inner`/`reflecting_outer` carry the prefix, and the names and functions are paired one to one) | 0 |
| 16 | Face-area-by-dimension selector `dim == 1 ? face_area1 : dim == 2 ? face_area2 : face_area3` written three times | `src/hydro/flux_register.cpp:309-311`; `src/hydro/flux_register.cpp:549-551`; `src/hydro/flux_positivity.cpp:58-60` (range overloads) | a `face_area(dim)` accessor. Its natural home is coord (Linfeng's); a register-local helper also works | the three ternaries call it | bitwise (hypothesis) | 0 (9 removed, 3 calls + ~6-line accessor) |

**16 findings. Total net lines: -42** (sum of the column; rows 2, 8, 12, 13, 14 and 16 are estimates of the proposed form).

Largest items:
1. Row 2: diffusion outside the register (the one finding against "the register owns every conservative face flux").
2. Row 8: internal-boundary options defined three times.
3. Rows 4-7: literal defaults repeated in hand readers (11 literals).
4. Row 9: timing block x7 (-23).
5. Row 3: hand x1 divergence.

## Examined, near-duplicate, not counted (semantics differ)

- **Ideal-gas Roe average and sound speed.** `src/implicit/flux_decomposition_impl.h:17-19, 37-62` (`SoundSpeed`, `RoeAverage`) against `src/riemann/riemann_kernels.h:288-330` (Roe solver) and the EOS sound speed. The implicit linearization is ideal-gas by design (`gm1`, dry energy). The riemann Roe state is species-aware (qbar rows, EOS enthalpy). Not one quantity.
- **Metric sine.** `src/implicit/implicit_hydro.cpp:270-271` (`sin = sqrt(1 - cos^2)`) against `src/coord/gnomonic_equiangle.cpp:99` (`sine_cell_kj` from its own formula). They are mathematically equal but round differently, and `sine_cell_kj` exists only on the gnomonic grid while implicit needs it on every grid. Merging would change bits at round-off (hypothesis); it needs coord to own a sine for every grid (Linfeng).
- **Left/right face pressure difference.** `src/hydro/hydro_forward.cpp:679-684` has the shape of an x1 divergence, but the upper faces use `wlr1[ILT]` and the lower faces `wlr1[IRT]`: different operands, not row 3's form.
- **Weighted face differences.** `src/hydro/gravity_work.hpp:26-28` (potential-weighted face mass) and `src/implicit/implicit_hydro.cpp:697` (clamp work): differences of weighted face terms, not the divergence.
- **Gravity predicates.** `grav1() != 0` combined with different conditions at `src/hydro/hydro.cpp:96, 108, 120, 128, 327`, `src/hydro/hydro_forward.cpp:442, 542, 664, 1043`, `src/sedimentation/sed_hydro.cpp:106`, `src/diagnostics/budget.cpp:323`. Only `grav1 != 0 && gravity_work == "face"` repeats exactly (hydro.cpp:96, 108, inside 327), and a helper would add lines.
- **Bottom-layer selectors.** `part({0, 0, -1}, ...)` in `src/forcing/relax_bot_comp.cpp:68, 70`, `relax_bot_temp.cpp:32, 50`, `relax_bot_velo.cpp:24`: one call each, with depth and ndim varying. Not a definition; a helper would not save lines.
- **Two registers' views.** `src/hydro/hydro.cpp:243-245` and `src/scalar/scalar.cpp:70-72` (`register_buffer("F1", freg.totals()[0])`) bind views of two different registers (hydro's and scalar's), not one quantity.
- **FaceKind::wall.** `src/mesh/meshblock_options.cpp:200-202` includes `fixed_temperature_*`, so it is a different predicate from row 15's.
- **Epsilon clamps.** `src/hydro/hydro.cpp:385` (1.e-30) and `src/implicit/implicit_hydro.cpp:550` (1.e-300) are local guards with different purposes, not one named constant.

## Handed to Linfeng (home in layout/coord/output/eos/recon/riemann/diagnostics/scalar/utils/math)

- **`SQR` macro defined five times.** `src/implicit/flux_decomposition_impl.h:12` (my home's copy), `src/riemann/riemann_kernels.h:22, 184, 260`, `src/recon/recon_point.h:12` (`SNAP_SQR`). The home is a shared utility header; implicit's copy goes with it.
- **Kinetic energy `0.5 rho v^2` re-derived** outside the EOS `"U->K"`: `src/eos/aneos.cpp:55, 75`, `src/eos/equation_of_state.cpp:325`, `src/eos/ideal_gas.cpp:70`, `src/eos/ideal_gas_impl.h:29`, `src/eos/ideal_moist.cpp:131, 287`, `src/eos/moist_base.cpp:93, 123`, `src/eos/moist_mixture.cpp:124`, `src/diagnostics/budget.cpp:321`. My homes use `peos->compute("U->K")` (`src/mesh/meshblock_advance.cpp:307`).
- **`put_text`** defined in `src/output/netcdf.cpp:36` and `src/output/pnetcdf.cpp:44`.
- **Rows-only option tables `coord.yaml` and `layout.yaml`**: the same three-place pattern as row 8 (table + `ADD_ARG` + hand reader).
- **`LayoutOptions::blocks_per_process`** (`src/layout/layout.hpp:131`): the layout mirror in row 7.
- **`face_area(dim)` accessor** for row 16, if coord should own it.

## Not checked

- Python and YAML defaults outside `src/` (e.g. `python/snapy/*.pyi`, example decks). The brief limits the comparison to `src/`, where the only YAML is `src/options/*.yaml`, covered in rows 4-8.
- CUDA-only (`.cu`/`.cuh`) copies were in the detector's scope; the only hits are the expected CPU/CUDA dispatch twins (`sed_hydro_dispatch.cpp/.cu`).
- No row was built or run. Every "bitwise" except rows 4-7 (literal equality, checked by reading) is a hypothesis from reading.
- Semantic duplication under different names and shapes that neither the windowed detector nor the targeted searches catch.

## Commands and outputs

Trimmed where long; counts kept.

```
$ git ls-remote https://github.com/UCzhangxi/snapy.git refs/heads/v3/wave3    # 2026-11-22T16:47:49Z
d3178f207b60663ff966b7c7ef20025821ef52fa	refs/heads/v3/wave3

$ for d in hydro mesh implicit forcing sedimentation bc chemistry input; do (find src/$d ... | xargs cat | wc -l); done
hydro 22 files 5167 | mesh 19 3694 | implicit 14 2291 | forcing 17 3076 | sedimentation 7 640 | bc 10 1155 | chemistry 2 111 | input 2 54   (src total 35693)

# pass 1: float literals in src (non-comment sites of the interesting ones)
$ git grep -n -o -E '[^A-Za-z0-9_.]([0-9]+\.[0-9]*([eE][-+]?[0-9]+)?|[0-9]+[eE][-+]?[0-9]+)' -- 'src/*.cpp' 'src/*.hpp' 'src/*.h' 'src/*.cu' 'src/*.cuh' | ... | sort | uniq -c
distinct literals: 120, occurrences: 1218; with >= 3 uses: 0. 331, 1. 200, 0.5 164, 2. 75, ... 1.e-30 10, 1440. 7, 1.e9 8, 720. 4, 1.e-300 3, 1e-6 5
$ git grep -n -E '1\.e9' -- src
src/bc/internal_boundary.cpp:33:  op->solid_pressure() = node["solid-pressure"].as<double>(1.e9);
src/bc/internal_boundary.hpp:51:  ADD_ARG(double, solid_pressure) = 1.e9;
src/options/internal_boundary.yaml:15:  - {name: solid_pressure, key: solid-pressure, type: double, default: 1.e9, ...}
(1440./720. are one 6-point stencil in src/hydro/hydro_ref_x1_impl.h:179-200; 1e-6 is the WENO epsilon in recon only)

# pass 2: option tables and their consumers
$ for f in src/options/*.yaml; do ... struct= rows= used_by= ...; done
coord struct=0 rows=14 used_by: (rows-only, tests/test_options_table.cpp)
internal_boundary struct=0 rows=3 used_by: (rows-only, tests/test_options_table.cpp)
layout struct=0 rows=7 used_by: (rows-only)
forcing_* struct=1 (generated members + reader) ... hydro struct=1 rows=12 ... output struct=1
$ git grep -n -E '\.as<[^>]+>\([^)]' -- src/hydro src/mesh src/implicit src/forcing src/sedimentation src/bc src/chemistry src/input
src/forcing/const_gravity.cpp:22-25,30,37  (0., 0., 0., 1., "face", false)
src/sedimentation/sed_options.cpp:96-99    (.as<double>(op->x()) -- single source)
src/mesh/meshblock_options.cpp:48,54,55,114 ("verbose" from the caller's argument; "eager", false; "reflecting")
src/bc/internal_boundary.cpp:31-33        (5, 1.e3, 1.e9)
src/implicit/implicit_hydro.cpp:50-51      ("auto", true)
src/mesh/mesh.cpp:244                      (1)
$ git grep -n -E 'ADD_ARG\([^)]*\b(grav1|...|upper_limit)\)' -- src
src/bc/internal_boundary.hpp:49-51 = 5; 1.e3; 1.e9
src/forcing/forcing.hpp:50 non_hydrostatic = 1.; :55 gravity_work = "face"; :57 gravity_work_fixer = false; :58-60 grav1/2/3 = 0.
src/implicit/implicit_hydro.hpp:49 precision = "auto"; :50 fallback_fp64 = true
src/mesh/meshblock.hpp:94 execution = "eager"; :95 execution_strict = false
src/mesh/mesh.hpp:42 blocks_per_process = 1; src/layout/layout.hpp:131 blocks_per_process = 1
$ git grep -n -E 'blocks_per_process\(' -- src | grep -E 'mesh.cpp'
src/mesh/mesh.cpp:243:  options->blocks_per_process(
src/mesh/mesh.cpp:263:  base_layout->blocks_per_process(options->blocks_per_process());
src/mesh/mesh.cpp:276:    layout->blocks_per_process(options->blocks_per_process());
$ for n in <hydro.yaml rows>; do git grep -n "ADD_ARG(...$n)" -- src/hydro; done
(no output: the hydro table's 12 rows have no hand ADD_ARG copy in src/hydro)

# pass 3: copy-paste detector (script below)
$ python dupblocks.py <root> 5 hydro,mesh,implicit,forcing,sedimentation,bc,chemistry,input
GROUPS 6: flux_positivity.cpp/.hpp (decl/def); hydro_forward.cpp:133/277; hydro_ref_x1_impl.h:142/164;
          sweep.cpp:59/118; sed_hydro_dispatch.cpp/.hpp and .cpp/.cu (decl/def, dispatch twins)
$ python dupblocks.py <root> 3 ...
GROUPS 21, of interest: axial_momentum.cpp:113/139/198; relax_bot_temp.cpp:31 | relax_bot_velo.cpp:23;
          flux_register.cpp:261/268; hydro.cpp:243 | scalar.cpp:70; hydro_forward.cpp x7 (383,564,809,906,969,1132,1179);
          hydro_ref_x1_impl.h:144/169; stage_executor.cpp:211/238

# pass 4: formulas
$ git grep -n -E '\bsqrt\(|\.sqrt\(\)' -- <my homes>
diffusion_cubed_sphere.cpp:234,329 (basis-vector cosines, local); implicit/flux_decomposition_impl.h:18,39,40 (ideal-gas sound speed, Roe);
implicit_hydro.cpp:271 (sin from cos); sedimentation/sed_hydro_impl.h:69,73 (Chapman-Enskog viscosity; constants from kintera::constants::KBoltz)
$ git grep -n -E 'divergence\(' -- src
src/coord/coordinate.cpp:662,746 (definition); src/forcing/diffusion.cpp:699; src/forcing/diffusion_cubed_sphere.cpp:397;
src/output/load_diag_output_data.cpp:158,164 (diagnostic output); src/scalar/scalar.cpp:208
$ grep -n -E 'post|register|freg' src/forcing/diffusion.cpp
(no register post in the general diffusion path; only the cubed-sphere route at :561 forward_cubed_sphere)
$ git log -1 --format=%B ee0ce297 | tail -3
Results: decks without cubed-sphere diffusion unchanged. With it, du[IPR] is the divergence of the summed total in place of two divergences: round-off, under G8's tolerance.
$ git grep -n -E 'area1?\.slice\(-1, is \+ 1, ie \+ 1\)|...' -- src
src/hydro/gravity_work.hpp:26; src/hydro/hydro_forward.cpp:680, 1058, 1075; src/implicit/implicit_hydro.cpp:697
$ git grep -n -E '"reflecting"' -- src ; git grep -n 'is_reflecting' -- src
src/forcing/diffusion.cpp:441-442; src/mesh/meshblock_exchange.cpp:149; src/mesh/meshblock_options.cpp:114 (default name)
src/bc/bc_func.cpp:238 bool is_reflecting(bcfunc_t const& func); used at hydro.cpp:316,543; hydro_forward.cpp:326; balance_column.cpp:78-79
$ git grep -h -o -E 'BC_FUNCTION\([a-z_]+' -- src/bc | grep reflect
reflecting_inner
reflecting_outer
$ git grep -n -E 'sine_(cell|face[23])_kj *=' -- src
src/coord/gnomonic_equiangle.cpp:99,102,105 (sine from its own formula; gnomonic only)

# pass 5: same-name definitions in >1 file (beyond declaration + definition)
58 names, all decl/def pairs except put_text (src/output/netcdf.cpp:36, src/output/pnetcdf.cpp:44) -> Linfeng
```

The detector (`dupblocks.py`, run with Python 3 on the tree at d3178f20):

```python
# identical windows of W normalized code lines in src/, reported when one copy is under a HOME dir
import os, re, sys, collections
root, W, homes = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(",")
exts = (".cpp", ".hpp", ".h", ".cu", ".cuh")
files = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(root, "src")) for f in fs if f.endswith(exts)]
def norm(line): return re.sub(r"\s+", " ", re.sub(r"//.*", "", line).strip())
win = collections.defaultdict(list)
for f in files:
    rel, lines, inc = os.path.relpath(f, root), [], False
    for i, s in enumerate(open(f, errors="replace"), 1):
        if inc:
            if "*/" in s: s, inc = s.split("*/", 1)[1], False
            else: continue
        if "/*" in s and "*/" not in s: s, inc = s.split("/*", 1)[0], True
        n = norm(s)
        if not n or n in ("{", "}", "};", ");", "})", "});") or n.startswith(("#include", "namespace")): continue
        lines.append((i, n))
    for k in range(len(lines) - W + 1):
        key = "\n".join(n for _, n in lines[k:k + W])
        if len(key) >= 120: win[key].append((rel, lines[k][0], lines[k + W - 1][0]))
# groups with >= 2 sites and one site under src/<home>/, merged per file pair (25-line buckets)
```
