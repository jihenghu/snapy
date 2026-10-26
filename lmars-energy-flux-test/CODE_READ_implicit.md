### Code read: `src/implicit/` at `721a5654ad3cf48543226a76ef8b0be6ad1fc7ad`

All paths are in chengcli/snapy at that sha (unchanged in ed6125d). The rk3 weights come from the
installed pyharp 2.7.6 (`harp/integrator/integrator.cpp`), not from snapy.

**Schemes.** `implicit_hydro.cpp:89-94` maps scheme 1 to `"vic-partial"` and scheme 9 to `"vic-full"`.
Bit 3 picks the block size: `if ((scheme() >> 3) & 1) { // full  return 5; } else { return 3; }`
(`implicit_hydro.hpp:34-40`). The dispatch is `implicit_hydro.cpp:403-414`:
`vic_assemble_full / vic_solve_full` vs `vic_assemble_partial / vic_solve_partial`.

**What the operator contains.** It is an x1-only, linearised, upwinded (Roe |A|) finite-volume
operator, block-tridiagonal per column. Rows are built in `vic_assemble_full_impl.h:94-99`:
```
a[i] = (Am * area_i + Ap * area_ip1 + (area_ip1 - area_i) * dfdq_curr) * half_inv_vol - Phi;
a[i].diagonal() += Dt;            // Dt = 1/dt
b[i] = -(Am + dfdq_prev) * area_i * half_inv_vol;
c[i] = -(Ap - dfdq_next) * area_ip1 * half_inv_vol;
```
- *Vertical acoustics, pressure, vertical advection:* `dfdq` is the full x1 Euler flux Jacobian
  (`flux_decomposition_impl.h:106-125`). `Am/Ap = R |Lambda| R^-1` uses Roe-averaged states with
  eigenvalues `|w-cs|, |w|, |w+cs|, |w|, |w|` (`:73`), so the operator contains the vertical acoustic
  and pressure terms and linearised vertical advection, plus their upwind dissipation.
- *Gravity:* `Phi(IVX+dir, IDN) = grav; Phi(IPR, IVX+dir) = grav;` (`vic_assemble_full_impl.h:39-40`)
  gives the rho g momentum source and the rho w g work in E. With the default `gravity-work: face` in a
  Cartesian box, the face-work rows are added to the energy row (`:101-108`).
- *Energy equation:* yes. E is a solved row (index IPR) in both schemes.
- *Horizontal velocity inside the vertical operator:* the Jacobian uses `s2 = v1*v1 + v2*v2 + v3*v3`
  (`flux_decomposition_impl.h:116`). It has entries `-gm1 * v2` in the vertical-momentum row (`:122`)
  and `c2 = ... + s2/2 - ...` in the energy row (`:119,124-125`). The eigenvectors use
  `h = hp + ke` with `ke = 0.5*(u*u + v*v + w*w)` (`:86-88`). So u = 400 m/s enters the matrix
  coefficients through the kinetic energy and the p(E, rho, rho u2) dependence. There are no x2 derivatives.
- *Scheme 9 vs 1:* scheme 9 solves 5 unknowns (rho, rho w, rho u2, rho u3, E), with RHS rows
  `rhs(0..4) = DU(IDN, IVX+dir, IVY, IVZ, IPR)/dt` (`forward_sweep_impl.h:44-48`). Scheme 1 solves the
  3x3 subset (rho, rho w, E): `rhs(1) = DU(IVX + dir, il) / dt; rhs(2) = DU(IPR, il) / dt;` (`:38-40`).
  Its blocks are the (IDN, IVX, IPR) rows and columns cut out of the same 5x5 Jacobian and |A|
  (`vic_assemble_partial_impl.h:66-68, 82-84`), with `Phi` at `:46-48`. On write-back
  (`vic_redistribute_impl.h:170-180`), scheme 1 replaces only `DU(IVX+dir)` and `DU(IPR)` (plus the
  mass correction on rho). The horizontal-momentum tendencies stay explicit. Scheme 9 also replaces
  `DU(IVY)` and `DU(IVZ)` with the solved delta.

**Does horizontal advection enter the vertical solve?** Not in the matrix: the operator has x1 fluxes
only (dir = 0). It enters **through the RHS**. The RHS handed to the solve is the full explicit
tendency: `du.index(interior) = -dt * _div.index(interior);` (`hydro_forward.cpp:935`), the divergence
of the x1, x2 and x3 fluxes from `pcoord->forward(w, _flux1, _flux2, _flux3, ...)` (`:904`), plus
forcings `for (auto& f : forcings) f.forward(du, w, temp, dt);` (`:942`). Then
`_apply_implicit_correction(du, w, dt_corr, other);` (`:1167`) runs
`picorr->forward_masked(du, wi, gamma, dt, ...)` (`hydro.cpp:451`), and the solve computes
delta = (I + dt_corr J)^-1 du. In addition, the matrix coefficients depend on the horizontal velocity,
as listed above.

**Where it sits in rk3.** Every stage calls `fut_hydro_du = phydro->forward(dt, hydro_u, vars);`
(`meshblock.cpp:679`), which ends with the implicit solve. The solve uses
`dt_corr = dt * stages[rk_stage].wght2()` (`hydro_forward.cpp:1128-1131`), that is dt, dt/4 and 2dt/3
for the three stages (pyharp `integrator.cpp:49-61`: wght2 = 1, 1/4, 2/3). The corrected du is then
combined by `hydro_u.set_(pintg->forward(stage, _hydro_u0, hydro_u, fut_hydro_du));`
(`meshblock.cpp:784`), i.e. `wght0*u0 + wght1*u + wght2*du` (pyharp `integrator.cpp:120`). So the
correction is applied once per stage, three times per step, each time to a stage tendency that already
contains the explicit horizontal fluxes. The Jacobian is frozen at that stage's state.

**Time step.** With bit 0 set, the x1 limit drops the sound speed:
`(!(icorr->scheme() & 1) || ...) ? (w[IVX].abs() + cs) : w[IVX].abs() * adv` (`hydro.cpp:349-353`).
x2 keeps `|u2| + cs` (`:357-359`). In this deck dt is therefore set by x2:
dt = cfl dx / (|u| + cs) = 0.3 * 5000 / 1111.4 = 1.350 s, which matches the logged dt.
The vertical acoustic Courant number is cs dt/dz = 0.21, below 1, so the implicit solve is not needed
for stability at any rung of this ladder.
