V3 lane S: seams, coord, layout, exchange and boundaries
=========================================================

:Lane: S (cubed-sphere seams, coord, layout, exchange, bc)
:Owner: Jiheng Hu (from 17:59 EST, on Cheng's assignment; revisions up to
        1.1 by Xinyue Wang)
:Revision: 2.1 (from 2, ``c505fb87``): the PM's items 1-8 on rev 2,
           answered by number in section 11 ("Rev 2.1"). Rev 2 (from 1.1,
           ``d03e4888``): Cheng's six items of 16:37 EST and lane A's S-4
           to S-8 (A rev 4 final, ``4e0827b8``), re-cited to lane R rev
           2.2. The index is at the end of section 1.
:Pin: chengcli/snapy ``9e5de2d4ce497d0b2d4da3295fc1fe969fe7e410``
:Lane R header: happysky19/snapy ``docs/v3/skeleton/R/flux_register.hpp`` at
                ``4c59162ae37080d0ab307b2823742b44f46da7c3`` (frozen; header
                rev 4.2, 117 lines; R.rst rev 2.2). Its names and
                signatures are used here unchanged. Rev 1.1 cited
                ``3490d7e1``, rev 1 ``543ff84f``.

Every ``file:line`` is at the pin and relative to ``src/`` unless it names
another tree. Lines of R's header are written ``flux_register.hpp:N``. A
claim I have not tested is marked **hypothesis**. A change in results beyond
round-off is marked **FOR CHENG**. Nothing in this document was built or run.

.. contents::
   :local:
   :depth: 1


1. Scope and pins
-----------------

**Scope.** Lane S owns ``src/coord/*``, ``src/layout/*`` and ``src/bc/*``,
the transport of every within-stage exchange (section 3), the panel-seam
geometry and the one rotation (S-1). **S also owns ``BlockExchange``**, the
part X assigns it in the ``MeshBlock`` split (X skeleton
``meshblock_parts.hpp:18-20`` at UCzhangxi/snapy
``54ca53562c315cedc958af0799c2099546014b1f``): ``mesh/meshblock.cpp:644-685``
(the two-round exchange and its pack, host, unpack phases),
``:1111-1205`` (``exchange_ghost_zones`` with the x1 boundary-function
refresh) and ``:1846-1918`` (``apply_boundaries``), less ``:1198-1200``
(the ``scalar_r`` divide, X's). Those lines stay in X's ``meshblock.cpp``
split, outside S's section 9 baseline (proposal: X books any deletion
there under RULING V3-1). S reads but does not own the other exchange
call sites: ``hydro/hydro_forward.cpp``, ``hydro/hydro.cpp:344-377, 606-776``,
``scalar/scalar.cpp:100-181``, ``forcing/diffusion_cubed_sphere.cpp``,
``eos/equation_of_state.cpp:335-372`` and the rest of
``mesh/meshblock.cpp:611-1110``.

**Pins.**

- snapy ``9e5de2d4`` (checked with ``git rev-parse`` in a fresh clone).
- Lane R header and R.rst at ``4c59162a`` (fetched read-only). R.rst lines
  are written ``R.rst:N``.
- Lane A at JiachenLiu-Atmos/snapy ``4e0827b8`` (A.rst:N) and lane O at
  ``5a7b46fa`` (O.rst:N), both read-only.
- Rev 2.1 adds, all fetched read-only: lane A rev 4.1 part 2
  ``a0b006d29cf7c9c8147ebdc387ecddc672623b79``; lane X rev 3.13
  ``54ca53562c315cedc958af0799c2099546014b1f`` (UCzhangxi/snapy; X.rst:N);
  lane R rev 2.4 ``a15af81660f75b53f3e905b7ee15aa935ada855c``
  (happysky19/snapy, R.rst only; the header stays at ``4c59162a``); lane EF
  ``f5c8e9a76f2b06045b545cc692bff7262f13ac0d`` (zoeyzyhu/snapy; EF.rst:N).
  A cite to one of these names its sha.
- #370 (open; species enthalpy and donor velocity across seams) is used only
  through its PR text. It appears as the pending row 17p.

**The brief's numbers, checked at the pin.**

.. list-table::
   :header-rows: 1

   * - number
     - brief
     - at the pin
     - command
   * - lane baseline
     - 8,472
     - 8,472, confirmed: coord 4,008 + layout 3,316 + bc 1,155 = 8,479,
       less ``coord/cylindrical.cpp_`` (7 lines, never compiled)
     - ``wc -l src/coord/* src/layout/* src/bc/*``
   * - ceiling
     - 6,777 (at least -20%)
     - 8,472 x 0.8 = 6,777.6
     - arithmetic

That the brief's baseline is exactly this file set is my reconstruction: the
numbers match, but I did not see the brief's own file list.

**Settled before this revision** (lane S thread):

- S-1: coord owns the single rotation and its data. Lane A owns the Omega
  and mass-flux consumers. The non-z axis is a declared parameter that refuses
  non-z. That FOR CHENG item sits in lane A.
- S-2: register posts are in global components after coord's rotation
  (``flux_register.hpp:4-5``). This replaces my earlier panel-frame position.
  Any rounding or cost problem goes to the R header review, not back here.
- S-3: diffusion gets a face-slab row and keeps its own exchange until
  phase 3.
- EF: a solid cell is a column break in ``fix_vapor``, never a donor or
  receiver, and is excluded from theta, the hit census and the neighbour
  minimum (``phi``). Solid faces are not limited by EF: R's
  ``boundary.prescribed`` zeroes their mass, species, energy and scalar
  rows in ``reconcile``, before ``limit``, so theta already sees zero
  species flux there; normal momentum keeps the mirror-Riemann flux
  (EF.rst:696-704 at ``f5c8e9a7``). Tangential momentum is free-slip,
  accepted by EF (same lines; section 4).

**Rev 2: answers to Cheng's six items (16:37 EST), by number.**

1. Per-edge map in ``SeamEntry`` (``PanelEdge``: ``peer_dim``, ``reversed``,
   ``normal_sign``) for the 6 non-identity edges, and gate G-S13 anchored on
   2T:3T with a negative control: section 4.1 and section 5. The table cite
   is ``layout/cubed_sphere_layout.cpp:320-350``.
2. RULING V3-3: one sentence in section 4.
3. Section 9 on real counts: 8,472 -> 7,434 (-1,038, -12.3%; 7,445 at
   rev 2.1, section 9), with the 153
   AAM lines (V3-1), D7, H-S1..H-S7, lane O's 127 options lines (99 stay),
   the 16 ``coordinate.hpp`` AAM hook lines, ``rotation_geometry()`` (+4,
   estimate) and the overlap counted once.
4. The K7/J9 post-limit gate G-S-K7 (section 5; its row in the section 4
   shared-face table answers J9; lane A's G5 runs at the same point and
   depends on it) and the CPU-vs-GPU
   tolerance of row H18, a **hypothesis**.
5. ``set_prescribed`` on the hydro register and on each Scalar register
   (section 4, "boundary.prescribed").
6. Every R cite at ``4c59162a``; the 149 hydro lines are R's D7, D5 and D1
   (section 9).

Lane A's S-4 to S-8 (A.rst section 11.4 at ``4e0827b8``) are answered in
section 11, row A.

**Not checked.** The PM's own wording of the four failing identities
(section 5 uses the 919936da inventory and its cross-checks). Commit
``9c568b92`` (the first item-3 table, never pushed). Lane X's and lane C's
drafts.


2. Concepts and current sites
-----------------------------

**Layouts.** ``LayoutImpl`` (``layout/layout.hpp``) has three subclasses:
slab (``layout/slab_layout.cpp``, ``pz == 1`` only, ``:12-13``), cubed
(``layout/cubed_layout.cpp``) and cubed sphere
(``layout/cubed_sphere_layout.cpp``). One exchange is serialize, launch and
finalize (``mesh/meshblock.cpp:664-685``). On a subdivided cubed-sphere panel
an interpolating exchange runs twice, intra-panel and then cross-panel
(``mesh/meshblock.cpp:651-658``).

**Two transports.** A same-process neighbour goes through boards guarded by
a mutex and a condition variable (``layout/layout.cpp:312-500, 895-940``). A
remote one goes through the process group (``layout/layout.cpp:556-653``,
``layout/process_group.cpp:183-196``). Hydro writes its own x1 relays on top
of both (``hydro/hydro.cpp:344-377, 727-776``;
``hydro/hydro_forward.cpp:882-946``).

**Four rotation paths** (S-1):

#. the exchange's spherical frame matrices: ``cs_velocity_transform_matrix``
   (``coord/cubed_sphere_utils.cpp:259-298``), applied at
   ``layout/cubed_sphere_layout.cpp:685-698, 823-836``, cached per layout
   (``:161-191``). Its angle comes from ``torch::atan2``
   (``coord/cubed_sphere_utils.cpp:189``);
#. Coriolis' own frame (``forcing/coriolis.cpp:128-142``, the same matrices);
#. the AAM rotation field (``coord/gnomonic_equiangle.cpp:22-35``), which goes
   through Cartesian;
#. diffusion's Cartesian route (``forcing/diffusion_cubed_sphere.cpp:193,
   371``, using ``coord/cubed_sphere_utils.cpp:194-243``).

The face rotations the solver uses, ``prim2local*_``/``flux2global*_``
(``coord/gnomonic_equiangle.cpp:365-484``), are a fifth, per-face use. They
stay as they are. "Global components" in R's sense (``flux_register.hpp:4-5``)
is their output: each panel's own covariant components
(``coord/gnomonic_equiangle.cpp:427-455``).

**Seam geometry.** At the pin each panel already evaluates seam arcs with one
function of the unordered endpoint pair
(``coord/gnomonic_equiangle.cpp:114-123``). Ghost interpolation is already
in delta form (``coord/gnomonic_equiangle.cpp:767-771``). Both were the
proposed fixes for H6 and H12 (section 5).

**Corners.** ``skip_corner`` defaults to true (``layout/layout.hpp:152``).
Corners are synthesized as 0.5·(edge + edge) on every layout
(``layout/layout.cpp:681-721``), which is wrong for periodic corners on slab
and cubed layouts (section 5, identity P).

**Wall predicates.** There are three questions under one word: physical and
not periodic (``hydro/hydro.cpp:296-301``), physical
(``mesh/meshblock_options.cpp:235``), and outflow or reflecting
(``bc/bc_func.cpp:231-250``).

**Periodic, twice.** The layout wraps on cubed layouts, and the bc functions
copy (``bc/bc_func.cpp:36-50``). Slab x1 periodic exists only in the bc
copy, because the slab layout has no x1 wrap (``layout/slab_layout.cpp:12-13``).

**Solids.** ``InternalBoundaryImpl`` marks solid cells
(``bc/internal_boundary.cpp:47-60``) and mirrors face states into a solid
neighbour, negating the normal velocity (``bc/internal_boundary.cpp:70-95``).
The Riemann solver then gives the mirror flux. No mask is applied to the
flux.


3. Target design
----------------

3.1 Data flow
~~~~~~~~~~~~~

::

   coord (geometry, PanelRotation, PanelGeometry, AxialRotationData)
     |  rotation, metric, seam arcs, solid-face mask
     v
   Exchange (S) ----- Channel: local board | process group -----> peers
     |  ghosts()      x1_rows()      seam_slab()     gather_x1()
     |     |              |               |               |
     |  rows 0-3,17,   rows 4-5,8,     rows 9, 16r     rows 6-7 (scan),
     |  26-27          10,13-16,19,    (reconcile)     28
     |                 22-25              |
     v                                    v
   solver sweeps -- post --> FluxRegister (R) -- replace(d,faces,peer,rule)
                                  |  enter(RegisterPhase::reconcile)
                                  |  set_prescribed(d,mask,value) (from S)
                                  |  apply_prescribed(d): boundary.prescribed
                                  v
                            total(d) -> divergence

S moves bytes and rotates. R decides what a seam face's value is and keeps
it. Each stage exchange is one row of the declared schedule
(``stage_schedule()``, ``exchange.hpp``), and lane X cuts segments at its
rows.

**One rotation.** ``PanelRotation`` (``coord_rotation.hpp``) is the only
code that changes a vector's basis between panels. It goes through the
global Cartesian frame (contravariant A → Cartesian → contravariant B),
which needs no ``atan2``. Under AVX2 the cross-check measured its matrices
as strip-independent (0 of 8,640) and found it agrees with the spherical
route to 6.2e-16. Both numbers are at 919936da. That nb = 4 then becomes
bitwise end to end is a **hypothesis**. The spherical-frame code is deleted
(section 9).

**FaceKind.** Each block face has one kind (``exchange.hpp``). The three
wall predicates become one lookup. ``periodic`` is a seam to self: the layout
wraps where it can, and slab x1 keeps the bc copy as the declared fallback.
**The ``boundary(dim)`` face set (contract; R closed it in R rev 2.4,
R.rst:39-42, 632-657 at ``a15af816``).** R's
``RegisterMonitor::boundary(dim)`` sums two disjoint face sets, all rows,
outward from the fluid, and never an ``interior``, ``seam_x1``, ``panel``
or ``periodic`` face, which ``replace`` reconciles instead (lane O's L-3):

- **block faces**, selected by ``FaceKind``: a block face of kind
  ``wall``, ``outflow`` or ``custom`` whose interior cell is fluid.
  ``FaceKind`` is one value per block face (six per block), so it can only
  select faces on the block's outer boundary;
- **fluid-solid faces**, selected by the **solid mask**, not by
  ``FaceKind``: an immersed solid lies mostly inside a block, so its faces
  are interior faces of the block and no per-block-face kind can name them.
  S builds the set once from the cell mask (``solidl``/``solidr``,
  ``bc/internal_boundary.cpp:74-76``) as
  ``PrescribedFaces::solid_face_sign``: +1 where the solid cell is on the
  high side, -1 on the low side, 0 on fluid-fluid faces **and on
  solid-solid faces**. A face between two solid cells is not a boundary of
  the fluid domain, so whatever is posted on it stays out of
  ``boundary(dim)`` (R.rst:647-648 at ``a15af816``). R sums ``sign * A_f
  S_d`` over the nonzero entries.

Reason for the second set: the momentum
rows at a solid face keep the mirror flux ``p* n`` (section 4,
"Tangential momentum at solid faces"), which is not zero, and the solid
cell is overwritten every stage (``fill_cons_solid_``,
``bc/internal_boundary.cpp:62-68``, called at ``mesh/meshblock.cpp:936-938``),
while ``domain_total`` sums fluid cells only
(R.rst:417, 533-534 at ``4c59162a``). Without the faces, O's identity
(``residual = delta domain_total + sum_d boundary(d) - sum amounts``,
O.rst:808, 970 at ``4afdbf37``) leaves the wall pressure force in the
momentum residual. O.rst:2915-2917 (on the sphere ``boundary`` uses x1
faces only) then holds only without solids. Mass, species, energy and
scalar rows there are prescribed to zero, so they add nothing. No
``flux_register.hpp`` declaration changes (R.rst:41-42 at ``a15af816``).

**Corners.** ``CornerRule::diagonal`` on slab and cubed layouts, using the
diagonal neighbour that ``for_each_direction`` can already visit
(``layout/layout.cpp:189-202``). ``synthesized`` (today's average) only at
cubed-sphere panel corners, where no diagonal neighbour exists. ``x1_full``
for x1 rows.

3.2 What the schedule counts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One stage is ``MeshBlockImpl::forward`` (``mesh/meshblock.cpp:611-618``): the
stage-entry ghost sync, then ``advance_local`` (``mesh/meshblock.cpp:698-1007``),
which calls ``HydroImpl::forward`` (``hydro/hydro_forward.cpp:370``), the scalar
forward, the multi-stage averaging and the stage tail.

A row is one *exchange*: a point where a block reads data that another block
wrote in this stage (point-to-point message, same-process board, column gather
or global reduction). Physical boundary functions are block-local and are not
rows; they are named in the row they follow. The per-step ``dt`` reduction
(``mesh/meshblock.cpp:585-588``) is outside the stage and not a row.

Column meanings:

- **phase**: where in the stage the exchange sits (the step numbers are the
  code's own section comments).
- **interp/frame**: ``interp`` = cubed-sphere ghost interpolation
  (``layout/cubed_sphere_layout.cpp:818-820``); ``rot`` = the velocity is taken to
  the spherical frame on send and back on receive
  (``layout/cubed_sphere_layout.cpp:685-698``, ``:823-836``); ``raw`` = copied
  as is (``kScalar``, ``:699``, ``:837``, or a hand-written x1 relay).
- **corners**: ``skip_corner`` defaults to true (``layout/layout.hpp:152``) and
  ``for_each_direction`` then visits faces only (``layout/layout.cpp:189-202``).
  ``avg`` = corners synthesized as the mean of two edge strips
  (``layout/layout.cpp:681-721``) after an exchange that is neither half of a
  split sync (``layout/layout.cpp:736-741``, ``mesh/meshblock.cpp:657``).
  ``x1-full`` = x1 ghost rows sent over every x2/x3 column, ghosts included,
  so x1/x2 and x1/x3 corners come from the x1 neighbour
  (``hydro/hydro.cpp:344-377``).
- **rounds**: blocking rounds with the most options on (cubed sphere with a
  subdivided panel, ``pz > 1`` across processes). A two-phase cubed-sphere sync
  is two rounds (``mesh/meshblock.cpp:651-658``).
- **block/host**: where the wait is. ``finalize`` = ``work->wait()`` in
  ``LayoutImpl::finalize`` (``layout/layout.cpp:723-733``); ``recv`` = a
  blocking ``recv_from_block(...)->wait()``; ``host`` = a device-to-host read
  (``item``/``cpu``).

3.3 The schedule
~~~~~~~~~~~~~~~~

.. list-table:: Within-stage exchanges in execution order (pin 9e5de2d4)
   :header-rows: 1
   :widths: 4 14 14 10 10 10 7 5 10 16

   * - row
     - name
     - variables
     - peers
     - phase
     - interp/frame
     - corners
     - rounds
     - block/host
     - file:line
   * - 0
     - implicit-radial pre-step ghost sync (stage 0 only)
     - ``hydro_u``, ``scalar_s``
     - all face neighbours
     - before stage 0 (only with ``implicit_radial`` diffusion)
     - interp, rot (``hydro_u``); interp, raw (``scalar_s``)
     - avg
     - 4
     - finalize
     - ``mesh/meshblock.cpp:714-718`` -> ``:1111-1128``
   * - 1
     - stage-entry conserved ghost sync
     - ``hydro_u``
     - all face neighbours (x2, x3, and x1 when the layout has 27 buffers,
       ``layout/layout.cpp:123-127``)
     - stage entry
     - interp, rot (``kConserved``)
     - avg; x1 corners then refreshed by the x1 bfuncs
       (``mesh/meshblock.cpp:1130-1196``)
     - 2
     - finalize
     - ``mesh/meshblock.cpp:616``, ``:1117-1121``
   * - 2
     - stage-entry scalar ghost sync
     - ``scalar_s``
     - as row 1
     - stage entry
     - interp, raw (``kScalar``)
     - avg
     - 2
     - finalize
     - ``mesh/meshblock.cpp:1123-1128``
   * - 3
     - conversion-order-4 primitive ghost sync
     - ``hydro_w`` (converted)
     - as row 1
     - step (1) primitives
     - interp, rot (``kPrimitive``)
     - avg
     - 2
     - finalize
     - ``hydro/hydro_forward.cpp:489-490``
   * - 4
     - conversion-order-4 x1 ghost rows
     - ``hydro_w``, ``ng`` rows, tag ``0x772a``
     - x1 below/above
     - step (1) primitives
     - raw
     - x1-full; then bfuncs on every ghost layer (``:492-503``)
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:491``; ``hydro/hydro.cpp:344-377``
   * - 5
     - centroid plain-mean x1 seam rows
     - ``wx1`` (plain means), ``il`` rows, tag ``0x7724``
     - x1 below/above
     - step (2) x1 sweep, before the reference
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:653-667``
   * - 6
     - x1 reference anchor, receive
     - running seam-face pressure (1, 2 or 3 channels), tag ``0x7715``
     - x1 above only
     - step (2) inside ``_hydro_ref_x1``
     - raw
     - none (one face)
     - 1, serial over the column
     - recv; same-process board waits up to 5 min (``layout/layout.cpp:850-876``)
     - ``hydro/hydro.cpp:622-641``
   * - 7
     - x1 reference anchor, send
     - bottom-face pressure (+ split parts, + gauge in fp32)
     - x1 below only
     - step (2) inside ``_hydro_ref_x1``
     - raw
     - none
     - 1
     - send ``wait()`` for a remote peer (``layout/layout.cpp:878-882``)
     - ``hydro/hydro.cpp:704-713``
   * - 8
     - reference ghost rows
     - ``pref``, ``dref`` (+ ``cell0``, ``cell_delta`` when paired), tags
       ``0x7717``/``0x7718``
     - x1 below/above
     - step (2) inside ``_hydro_ref_x1``
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro.cpp:727-776``
   * - 9
     - **reconcile** (x1): R's ``replace(1, faces, peer, SeamRule::mean)``;
       at the pin, the x1 process-seam flux average. Rev 1.1 extends it to
       same-process seams (section 4)
     - ``_flux1`` slab, ``_face_pressure1``, ``bflux1``, ``pressure_base1``,
       tags ``0x7720``/``0x7721``
     - x1 below/above; at the pin process seams only (``:887-888``), in
       V3 every x1 seam
     - ``RegisterPhase::reconcile`` (pin: step (2), after the x1 Riemann
       solve and sedimentation)
     - raw transport (S), then R's rule: the mean of both sides
     - none (one face)
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:882-946``
   * - 10
     - centroid face-pressure seam rows
     - ``_face_pressure1``, ``min(2, il)`` faces, tag ``0x7722``
     - x1 below/above
     - step (2) end of the x1 sweep
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:949-955``
   * - 11
     - x2 face-state seam sync
     - ``hydro_wl:+``, ``hydro_wr:-`` (directional keys,
       ``layout/cubed_sphere_layout.cpp:81-90``)
     - cross-panel x2 neighbours
     - step (3.A)/(3.C)
     - no interp, rot (``kPrimitive``); strip widened over x1 ghosts
       (``layout/cubed_sphere_layout.cpp:92-112``)
     - none (``cross_panel_only``, ``layout/layout.cpp:736-741``)
     - 1 (shared with row 12)
     - finalize
     - ``hydro/hydro_forward.cpp:1005-1019``, ``:1033-1048``
   * - 12
     - x3 face-state seam sync
     - ``hydro_wl:+``, ``hydro_wr:-``
     - cross-panel x3 neighbours
     - step (3.B)/(3.C)
     - as row 11
     - none
     - shared with row 11
     - finalize
     - ``hydro/hydro_forward.cpp:1021-1031``, ``:1033-1048``
   * - 13
     - x2 covariance face states, left
     - ``wlr2[ILT]`` 1 row, tag ``0x7730``
     - x1 below/above
     - step (4.A)
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:1059-1065``, ``:1096``
   * - 14
     - x2 covariance face states, right
     - ``wlr2[IRT]``, tag ``0x7732``
     - x1 below/above
     - step (4.A)
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:1097``
   * - 15
     - x3 covariance face states, left
     - ``wlr3[ILT]``, tag ``0x7734``
     - x1 below/above
     - step (4.B)
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:1131``
   * - 16
     - x3 covariance face states, right
     - ``wlr3[IRT]``, tag ``0x7736``
     - x1 below/above
     - step (4.B)
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:1132``
   * - 16r
     - **reconcile** (x2/x3, not at the pin): R's ``replace(d, faces, peer,
       SeamRule::owner_copy)`` on panel seams, adopted by R (R.rst:183-184)
     - the owner's posted x2/x3 face flux slab, all rows; momentum rows
       rotated by coord (section 4)
     - cross-panel x2/x3 neighbours
     - ``RegisterPhase::reconcile``, after x2/x3 Riemann and covariance,
       before positivity (R's phases, ``flux_register.hpp:14-23``)
     - no interp; covariant(owner) to covariant(receiver) via one Cartesian
       rotation
     - none (one face)
     - +1
     - finalize
     - new; ``SeamRule::owner_copy`` (``flux_register.hpp:24, 62-64``)
   * - 16i
     - **fallback, only if G-R2 fails** (section 4 table): R's ``replace(d,
       faces, peer, SeamRule::owner_copy)`` on x2/x3 edges inside one panel
       (and on x2/x3 block edges of slab and cubed layouts)
     - the owner's posted x2/x3 face flux slab, all rows; raw copy, no
       rotation (same panel, same basis)
     - same-panel x2/x3 neighbours
     - ``RegisterPhase::reconcile``, at row 16r's position
     - no interp; raw
     - none (one face)
     - +1 when it runs; 0 extra on the cubed sphere if packed into row
       16r's round (**hypothesis**: one round can carry both peer sets)
     - finalize
     - new; not in the section 3.5 count unless G-R2 fails
   * - 17
     - hydro species theta sync
     - ``hydro_theta``
     - all face neighbours
     - step (4.C) positivity limiter
     - no interp, raw (``kScalar``)
     - avg; then bfuncs
     - 1
     - finalize
     - ``hydro/hydro_forward.cpp:1227``; ``hydro/flux_positivity.cpp:177-193``
   * - 17p
     - **pending #370**: species enthalpy and donor velocity (lane A's S-7;
       ``730b3500`` ``hydro_forward.cpp:1230, 1254-1271``)
     - ``hspec`` ghosts synced like theta; donor velocity synced as a face
       state, then taken to the face's covariant basis
     - as row 17
     - step (4.C), next to row 17
     - raw (as theta), per the PR text
     - as row 17
     - +1 or 0 if packed with row 17
     - finalize
     - not at the pin: ``hydro/hydro_forward.cpp:1224-1225`` says ``hspec`` is
       not exchanged (#238). Row from PR #370's description only
   * - 16l
     - **fallback, only if G-S-K7 fails** (section 5): a second R
       ``replace`` after the carry, ``SeamRule::mean`` on x1 seams and
       ``owner_copy`` on panel seams (mapped by the ``PanelEdge``, momentum
       rotated, as row 16r)
     - the post-carry face flux slab, all rows (x1 as row 9, x2/x3 as row
       16r)
     - x1 below/above and cross-panel x2/x3 neighbours
     - end of ``RegisterPhase::limit``, after row 17 (and 17p) and the
       carry (``hydro/hydro_forward.cpp:1234-1235``), before ``divergence``
       (``flux_register.hpp:17-18``)
     - as rows 9 and 16r
     - none (one face)
     - +1 when it runs
     - finalize
     - new; not in the section 3.5 count unless G-S-K7 fails; lanes X and
       EF decide
   * - 18
     - cubed-sphere diffusion flux seam
     - ``diffusion_flux`` (12 channels: area-weighted flux + trace), streamed
       as four sides
     - all face neighbours
     - step (6) forcings, inside ``f.forward`` (``hydro/hydro_forward.cpp:1378-1384``)
     - no interp, raw (``kScalar``, ``phyid 12``); Cartesian frame
       (``forcing/diffusion_cubed_sphere.cpp:190-195``)
     - avg
     - 4
     - finalize
     - ``forcing/diffusion_cubed_sphere.cpp:132-143``
   * - 19
     - potential-energy seam row
     - ``drho`` (x1 density change), 1 row, tag ``0x7726``
     - x1 below/above
     - step (6) face gravity work, radial-exact only
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:1483-1494``
   * - 20
     - scalar x2 face-state seam sync
     - ``scalar_wl:+``, ``scalar_wr:-``
     - cross-panel x2 neighbours
     - scalar forward (``mesh/meshblock.cpp:785``)
     - no interp, raw (``kScalar``)
     - none
     - 1 (shared with row 21)
     - finalize
     - ``scalar/scalar.cpp:109-122``, ``:136-147``
   * - 21
     - scalar x3 face-state seam sync
     - ``scalar_wl:+``, ``scalar_wr:-``
     - cross-panel x3 neighbours
     - scalar forward
     - as row 20
     - none
     - shared with row 20
     - finalize
     - ``scalar/scalar.cpp:124-132``, ``:136-147``
   * - 22
     - scalar x2 covariance rows, left
     - ``rl``, 1 row, tag ``0x7740``
     - x1 below/above
     - scalar forward, ``scalar_flux_covariance`` (``scalar/scalar.cpp:157``)
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:245-252``
   * - 23
     - scalar x2 covariance rows, right
     - ``rr``, tag ``0x7742``
     - x1 below/above
     - as row 22
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:253``
   * - 24
     - scalar x3 covariance rows, left
     - ``rl``, tag ``0x7744``
     - x1 below/above
     - as row 22
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:252``
   * - 25
     - scalar x3 covariance rows, right
     - ``rr``, tag ``0x7746``
     - x1 below/above
     - as row 22
     - raw
     - x1-full
     - 1
     - recv
     - ``hydro/hydro_forward.cpp:253``
   * - 26
     - scalar upper-bound theta sync
     - ``scalar_theta`` (upper bound)
     - all face neighbours
     - scalar forward, when ``upper_bound > 0``
     - no interp, raw
     - avg; then bfuncs
     - 1
     - finalize
     - ``scalar/scalar.cpp:178-181``, ``:205``
   * - 27
     - scalar theta sync
     - ``scalar_theta``
     - all face neighbours
     - scalar forward
     - no interp, raw
     - avg; then bfuncs
     - 1
     - finalize
     - ``scalar/scalar.cpp:178-181``, ``:239``
   * - 28
     - whole-column limiter gather
     - cloud (parentless) then vapor rows + dry total + volume, the whole x1
       column
     - every block of the x1 column (``pz`` pieces)
     - step (4) multi-stage averaging; again in step (6) on the last stage
       when the thermo has reactions
     - raw
     - interior only
     - 1-2 per call (two calls on the last stage with reactions)
     - all pieces waited (``layout/layout.cpp:792-802``); CUDA stream sync
       (``layout/layout.cpp:757-760``, ``:804-807``)
     - ``mesh/meshblock.cpp:908-909``, ``:952`` (last stage, before the
       saturation adjustment, ``:950-951``); ``eos/equation_of_state.cpp:335-372``;
       ``layout/layout.cpp:748-818``
   * - 29
     - axial-momentum closure reduction, with a process group
     - ``axial_closure_sums`` {R, I} (2 FP64 numbers)
     - all ranks (allreduce SUM)
     - stage tail, every stage
     - n/a
     - n/a
     - 1
     - pin: allreduce ``wait`` (``layout/process_group.cpp:184-195``) and a
       host read ``item`` (``mesh/meshblock.cpp:1017-1018``). V3: an
       in-stage device collective with no host read (section 7)
     - ``mesh/meshblock.cpp:983-990``

Gates (when a row runs at all):

- row 0: stage 0 and ``implicit_radial`` diffusion (``mesh/meshblock.cpp:713-718``);
- rows 3-4: ``conversion_order == 4`` and ``nc1 > 1``
  (``hydro/hydro_forward.cpp:419``); row 4 also needs an x1 neighbour
  (``hydro/hydro.cpp:346-347``);
- rows 5, 10: ``SNAP_X1_CENTROID_EXACT`` on a spherical-polar grid
  (``hydro/hydro_forward.cpp:654-655``, ``:950-951``). Not on the cubed sphere;
- rows 6-8: gravity in x1 (``wb_x1``, ``hydro/hydro_forward.cpp:645-646``) and
  ``pz > 1`` non-periodic (``hydro/hydro.cpp:630-631``);
- row 9: ``pz > 1`` with a process group, process seams only
  (``hydro/hydro_forward.cpp:882-888``);
- rows 11-12, 18, 20-21: cubed-sphere layout
  (``hydro/hydro_forward.cpp:1013``, ``:1032``; ``scalar/scalar.cpp:111``);
- rows 13-16: ``flux_covariance()``; rows 22-25 also need scalars;
- row 17: ``limiter || cov2 || cov3`` and species (``hydro/hydro_forward.cpp:1165``);
- row 19: x1 gravity and ``radial_exact_work()`` (``hydro/hydro_forward.cpp:1471``);
- row 28: ``pz > 1`` (``eos/equation_of_state.cpp:340-341``), and only when
  the limiter runs (``mesh/meshblock.cpp:907-909``); its second call
  (``:952``) only on the last stage with thermo reactions (``:950-951``);
- row 29: ``conserve_axial_momentum_closure`` with a process group
  (``mesh/meshblock.cpp:983-988``); on one rank the closure has no
  collective and is not a row;
- rows 16i and 16l: only if their gates fail (G-R2, G-S-K7).

The gravity-work fixer's reduction (row 30 up to rev 2,
``mesh/meshblock.cpp:997-1004``) is gone: the fixer is removed (Cheng's
ruling (b); X.rst:452-453 at ``54ca5356``; A.rst:501-505 at
``a0b006d2``), and with it merge M9.

Host reads in the stage that are not exchanges, but are blocking points for
lane X: the implicit solve's finiteness screen, ``item<double>()`` on every
stage with ``picorr`` (``implicit/implicit_hydro.cpp:476-487``), and the
same-process board waits behind rows 4-10, 13-16, 19 and 22-25
(``layout/layout.cpp:379-416``).

3.4 Lane C's four groups (Tianhao), checked at the pin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - lane C group, as cited
     - what is at the pin
     - rows
   * - ``hydro_forward.cpp:489-503`` (conversion-order-4 ghosts)
     - ``exchange`` of ``hydro_w`` at ``:490``, x1 rows ``0x772a`` at ``:491``,
       bfuncs at ``:492-503``. Matches.
     - 3, 4
   * - ``hydro.cpp:636, 712, 727-776`` (anchor relay, reference ghost rows)
     - ``take_x1_anchor`` at ``:636``, ``pass_x1_anchor`` at ``:712``,
       the ``pref``/``dref`` ghost-row exchange at ``:727-776``. Matches.
     - 6, 7, 8
   * - ``hydro.cpp:666, 953, 1059-1065`` (centroid and covariance seam rows)
     - ``hydro.cpp`` has 971 lines at the pin, so 1059 cannot be in it. The
       cited lines match ``hydro_forward.cpp``: plain-mean rows ``:666``,
       face-pressure rows ``:953``, ``x1_seam_rows`` ``:1059-1065`` (used
       at ``:1096-1097``, ``:1131-1132``). Read as ``hydro_forward.cpp``.
     - 5, 10, 13-16
   * - ``hydro_forward.cpp:1227``, ``flux_positivity.cpp:177-190``,
       ``scalar.cpp:179`` (theta sync)
     - hydro theta ``:1227``; the shared sync function
       ``flux_positivity_sync_theta_`` at ``flux_positivity.cpp:177-193``
       (exchange ``:184``, bfuncs ``:186-192``); scalar ``sync_theta`` at
       ``scalar.cpp:178-181``, called at ``:205`` and ``:239``. Matches.
     - 17, 26, 27

Rows not in either list: 0-2 (stage-entry syncs), 9 (seam flux averaging),
11-12 and 20-21 (face-state seam syncs), 18 (diffusion seam), 19
(potential-energy seam row), 22-25 (scalar covariance rows, a separate call
path at ``hydro_forward.cpp:245-253``), 28 (whole-column limiter gather),
29 (reduction).

3.5 Segment boundaries and merge proposals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lane X's contract: one segment boundary per blocking round. With the most
options on that can hold together on the cubed sphere (rows 1-4, 6-9, 11-29
except 16i, 16l and 17p; ``pz > 1`` across processes; a stage that is
neither stage 0 nor the last), the count is the sum of the ``rounds``
column:

2+2+2+1 (rows 1-4) + 1+1+1+1 (6-9) + 1 (11-12) + 4 (13-16) + 1 (17) + 4 (18)
+ 1 (19) + 1 (20-21) + 4 (22-25) + 1+1 (26-27) + 2 (28) + 1 (29) = **32**.

Rev 2 counted 33: row 30 (the gravity-work fixer's reduction) is gone with
the fixer (X.rst:452-453 at ``54ca5356``). Rows 5 and 10 are
spherical-polar only and do not add to this count. The proposed row 16r
adds one round on the cubed sphere (33). The last stage adds row 28's
second call at ``mesh/meshblock.cpp:952`` when the thermo has reactions:
+2 rounds (+1 with M8), so 34 on that stage (35 with 16r). The fallback
rows add +1 each only if their gates fail: 16l (G-S-K7), and 16i (G-R2;
0 if packed into 16r's round, **hypothesis**). The earlier local
commit 9c568b92 counted per exchange site and reported 23 points, with nine
merges to 12. That commit could not be fetched from here, so I could not
reconcile its count with this one. Counted per site, this table has 25 points
with the same options (rev 2's 26 less row 30). Both counts and both merge results are
**hypotheses**. Whether
the diffusion seam (row 18), radial-exact work (row 19) and the covariance
rows really run together in one cubed-sphere deck is a **hypothesis**. I did
not check the option validation for every pair.

Merge proposals. All are **hypotheses**: none was built or run. "Bitwise"
means the receiving block holds the same bits as before. For a pure copy this
is a property of the code. A changed summation order is not bitwise.

.. list-table::
   :header-rows: 1
   :widths: 6 34 12 12 36

   * - id
     - proposal
     - rows
     - rounds saved
     - bitwise?
   * - M1
     - one stage-entry sync carrying ``hydro_u`` and ``scalar_s`` with a
       per-variable type (rot vs raw)
     - 1+2
     - 2
     - yes, if the interpolation and corner averaging see the same inputs per
       variable (pure per-channel ops, ``layout/layout.cpp:681-721``)
   * - M2
     - fold the conversion-order-4 x1 rows into the primitive sync as the
       ``dz`` direction with x1-full extent
     - 3+4
     - 1
     - yes for the copied rows. The layout's ``dz`` strips skip corners
       (``layout/layout.cpp:197-199``), so x1-full extent needs a new strip
       shape
   * - M3
     - the anchor relay becomes one column all-gather of each block's local
       hydrostatic drop plus a prefix sum
     - 6+7
     - 1, and latency drops from ``pz - 1`` serial hops to 1 collective
     - **no**: the prefix sum changes the summation order of the scan
       (``hydro/hydro.cpp:614-622``)
   * - M4
     - pack the four covariance face-state rows into one x1 message
     - 13-16
     - 3
     - yes (pure copies)
   * - M5
     - pack the four scalar covariance rows into one x1 message
     - 22-25
     - 3
     - yes (pure copies)
   * - M6
     - send the four diffusion sides in one 48-channel round, as before the
       streaming change (``forcing/diffusion_cubed_sphere.cpp:132-136``)
     - 18
     - 3
     - yes per the code comment ("four completed rounds reproduce the old
       48-channel round"). Costs 4x the buffer. **Phase 3**, with S-3: it
       goes in when diffusion leaves its own exchange for
       ``Exchange::seam_slab`` (A.rst:160-161, 775 at ``a0b006d2``)
   * - M7
     - one theta sync for hydro and scalar species, by running the scalar
       lower-bound theta before row 17
     - 17+27
     - 1
     - yes for the copies. The reorder is safe only if the scalar theta reads
       no hydro flux that row 17's scaling changes: the scalar's mass flux is
       ``flux*()[IDN]`` (``scalar/scalar.cpp:166-170``), which
       ``flux_positivity_scale_`` does not scale. That this holds for the
       carry (``:1233-1236``) is a **hypothesis**
   * - M8
     - gather cloud and vapor in one column gather and repair both
     - 28
     - 1
     - yes if the cloud repair does not feed the vapor repair's inputs. The
       clamp at ``eos/equation_of_state.cpp:378`` lies between them, so this
       is a **hypothesis**
   * - M10
     - pack row 17p into row 17 when #370 lands
     - 17+17p
     - 1 (vs. #370 as written)
     - yes (pure copies)

With M1-M8: 32 - (2+1+1+3+3+3+1+1) = **17** blocking rounds, **18** with
row 16r (**hypothesis**; X.rst:456-458 at ``54ca5356``). M9 (one allreduce
for rows 29 and 30) is gone with row 30; the label is not reused. Of these
merges, only M3 is not bitwise.
Also proposed, with no change to the count: start rows 11-12 (and 20-21)
before the x1 sweep so they overlap it. The x2/x3 face states are
reconstructed from ``w`` (``hydro/hydro_forward.cpp:1011``, ``:1023``). The x1
sweep subtracts the reference from ``w`` in place when ``wx1`` aliases it
(``:703``, ``:705``) and restores the saved copies (``:696``, ``:765-767``).
That an earlier x2/x3 reconstruction therefore reads the same bits is a
**hypothesis**.


4. Flux-register contract
-------------------------

Lane S posts no physical flux. It owns the transport of the ``reconcile``
phase (``RegisterPhase::reconcile``, ``flux_register.hpp:16``), the rotation
that phase needs, and the wall and solid-face mask. R owns the rules:
``replace(dim, faces, peer, rule)`` with ``SeamRule::mean`` or
``SeamRule::owner_copy`` (``flux_register.hpp:24, 62-64``), and
``set_prescribed``/``apply_prescribed`` (``:45-47, 65``). Citations of R's
header are at ``4c59162a`` (header rev 4.2, R.rst rev 2.2).

**What changed in R since rev 1's ``543ff84f`` that affects S** (cited at
``4c59162a``).

- ``replace`` now takes the faces and the peer entry plus a ``SeamRule``,
  not a name and a seam tensor (``:62-64``). ``:62`` states that S maps
  the peer: dim swap, edge order, normal sign, basis. S supplies ``faces``
  and ``peer``; R applies the rule to the total, the kept parts and the
  companions (``riemann.pstar``, ``pressure_base1``).
- ``SeamRule {mean, owner_copy}`` (``:24``): ``mean`` is row 9,
  ``owner_copy`` is S's row 16r, adopted by R (R.rst:183-184, 712-732).
- ``boundary.prescribed`` (``:16, 21, 45-47, 65``) replaces S's
  ``bc.solid_face``. R calls it after ``reconcile`` and again after
  ``post_implicit``.
- ``bflux1`` is gone with the cell form (R.rst:216-217). Row 9's payload
  under R is therefore the total plus ``pressure_base1``, not ``bflux1``.
- The frame is the output of coord's ``flux2global<d>_``
  (``:4-5``; ``coord/coordinate.hpp:353-361``), as S-2 says.
- New phase ``after_combine`` (``:22``), ``begin_step()`` (``:48``) and
  ``begin_stage(stage, harp::IntegratorWeight)`` (``:49``). None touches
  S's rows.
- The replaced amount is a monitor amount named ``reconcile.x1`` or
  ``reconcile.panel`` (R.rst:727-729, 1023-1026). This answers S's rev 1
  question 3.

**RULING V3-3.** Under RULING V3-3, lane C's ``solve_faces`` runs FaceFloor,
the solid step and R's ``before_solve`` hook (the covariance from
post-solid, unrotated face states) before it calls S's ``prim2local_`` and
the solve, so S's face rotations ``prim2local_``/``flux2global_`` stay
functions the solver calls, unchanged in V3 (``coord_rotation.hpp``).

**Convention (adopted, S-2).** A post is per unit face area and time, in
the output frame of ``flux2global<d>_``. On the cubed sphere that is each
panel's covariant basis (``coord/gnomonic_equiangle.cpp:427-484``), so at a
panel seam the two sides' momentum rows are in different bases. Their
mass, energy, species and scalar rows are not.

**Row 9 is the existing x1 seam average.** ``replace(1, faces, peer,
SeamRule::mean)`` is the flux average at ``hydro/hydro_forward.cpp:868-946``
(comment ``:868-881``; exchange and mean ``:882-946``). Both sides hold
``0.5*(mine + theirs)`` (``:937, 942``), which is bitwise equal on both sides
because IEEE addition commutes.

**Row 9 and the implicit phase (J10): row 9 does not run again after
``implicit``.** The ``vic.*`` posts (``add(1, "vic.*", ...)`` in phase
``implicit``, ``flux_register.hpp:20`` at ``4c59162a``; R.rst:551-560 at
``a15af816``) never land on an x1 seam face, because under an implicit
scheme no x1 seam exists: the pin refuses an x1 split whenever the vertical
solve is active. ``HydroImpl::_apply_implicit_correction`` checks that both
x1 faces of the block are physical and throws otherwise ("implicit scheme
requires nb1 = 1 (no x1 decomposition): the vertical solve has no
cross-rank coupling", ``hydro/hydro.cpp:485-490``), and the solver's own
comments rely on it (``implicit/implicit_hydro.cpp:375-378, 576-577``).
Every column the solve sees is whole and inside one block, so each x1 face
it posts on is either a cell face inside the block (one value by
construction) or one of the column's two physical walls (in
``boundary(dim)``, not a seam). That is read from the pin, not run. V3
must keep the refusal as a precondition of ``implicit`` (proposal: the
check stays on the implicit path, lane I's). If a later design lifts it, the
fix is a second ``replace(1, faces, peer, SeamRule::mean)`` at the start of
``post_implicit``, before ``apply_prescribed(1)`` (+1 round), and that
would be a new row. **Hypothesis**, untested: on a slab with x1 periodic
(a seam to self through the bc copy, which ``is_physical_boundary`` counts
as physical, R.rst:643-645 at ``a15af816``) the solve treats both ends as
walls, so the two posts there are the wall's own and need no ``replace``.

**Same-process x1 seams (R's K6, requirement 5).** At the pin one process
can hold several blocks that are adjacent in x1. ``blocks_per_process``
(``layout/layout.hpp:128``) places blocks per process, and a mixed layout
(``pz > 1`` with several blocks per process) runs since #254 (commit
``5eeb9b6``; ``tests/test_pref_local_seam.cpp`` uses four blocks in one
process). Their shared x1 faces are computed independently by each block
from its own reconstruction. The average skips a same-process neighbour:
``if (above >= 0 && playout->is_local_block(above)) above = -1``
(``hydro/hydro_forward.cpp:887-888``; the comment at ``:880-881`` says so).
With no process group it does not run at all (``:882-883``). What makes the
two sides agree today is that their inputs agree: the stage-entry ghost
exchange (rows 1-3), the anchor relay through a board
(``layout/layout.cpp:850-893``) and the reference ghost rows sent to local
neighbours too (``hydro/hydro.cpp:716-776``). The code's own comment says
this makes the average "a no-op" (``hydro/hydro.cpp:722-726``). #254's test
bounds the 4-block-vs-1-block difference at 1e-12 after 200 steps (commit
message: rho 5.2e-15, p 1.2e-15, vx 5.4e-14). That compares against one
block, so it does not measure ``F_own - F_peer``.

So rev 1's rule (both sides keep the mean) **did not cover** same-process
seams: it described the pin's process seams only. Proposed rule:

- **Rule:** every x1 seam, process or same-process, is ``replace(1, faces,
  peer, SeamRule::mean)`` in phase ``reconcile``. S delivers the peer entry
  through ``Channel``: the board for a local peer, the process group for a
  remote one (``Exchange::seam_slab``). There is no owner; both sides keep
  the mean. One rule per shared x1 face, as requirement 5 asks. The
  ``has_process_group`` and ``is_local_block`` gates go.
- **Gate:** bitwise equality of the two sides after ``reconcile`` (``0.5*(a
  + b)`` is symmetric), on 2 and 4 blocks in one process and on a mixed
  layout. Before ``reconcile``, R's G-R10 records ``|F_own - F_peer|``.
- **Result change vs main:** where the two sides already agree bitwise, the
  mean returns the same bits (``0.5*(a + a) = a`` exactly, barring overflow),
  so nothing changes. Where they differ, the change is the size of that
  difference. **Hypothesis:** that is round-off, because the inputs are
  exchanged copies and only position-dependent kernels (``pow`` under AVX2,
  cross-check §3) can tell the two blocks apart. If G-R10 shows more than
  round-off, enabling the mean is a **FOR CHENG** result change.
- **Cost:** none for one block per process. For local blocks it adds one
  board round per stage, inside row 9's existing round.

**Two-sided entries for every shared face.** Declared in
``seam_register.hpp`` as ``SeamEntry``:

.. list-table::
   :header-rows: 1
   :widths: 16 18 30 36

   * - face
     - canonical owner
     - rule via ``replace``
     - gate
   * - x1 seam, process or same-process (row 9)
     - none: both keep the mean (``SeamOwner::both_mean``)
     - ``replace(1, faces, peer, SeamRule::mean)``, all rows, kept parts and
       companions
     - bitwise equal on both sides; G-R10 records the pre-``reconcile``
       difference
   * - x2/x3 edge inside one panel
     - both (``SeamOwner::self``)
     - no ``replace``. After rows 1-3 both blocks hold the same ghost bits,
       so each computes the same face flux
     - bitwise, checked in debug and CI (R's G-R2). **Hypothesis**: ``pow`` is
       position-dependent under AVX2 (492/5,462 in the cross-check), so the
       gate runs under AVX2 and the scalar setting. If it fails, the entry
       becomes ``owner_copy`` with a raw copy (bitwise by construction):
       fallback row 16i (section 3.3), in ``reconcile`` at row 16r's
       position, +1 round (0 if packed into 16r, **hypothesis**)
   * - cubed-sphere panel seam (row 16r)
     - the block with the smaller global rank (``SeamOwner::lower_rank``)
     - ``replace(d, faces, peer, SeamRule::owner_copy)``. S moves the owner's
       slab (``Exchange::seam_slab``). Mass, energy, species and scalar rows
       are mapped by the ``PanelEdge`` (4.1), then copied. Momentum rows go through
       ``PanelRotation::panel_to_panel_rows_(rows, edge, alpha, beta)``
       (owner covariant on its ``peer_dim`` face → Cartesian → receiver
       covariant on its ``dim`` face; the ``PanelEdge`` gives both)
     - non-momentum rows bitwise equal. Momentum rows rotated back to the
       owner's basis match to 1e-14 relative. Reason: two panels' covariant
       bases joined by one floating-point rotation (6.2e-16 between routes
       at 919936da, inventory I7b). **Hypothesis** until measured
   * - x1 split with a panel seam
     - row 9 first, then row 16r
     - the edge faces of a panel seam are x2/x3 faces, which row 9 never
       touches
     - as the two rows above
   * - every shared face after the carry: end of ``RegisterPhase::limit``,
       before ``divergence`` (K7, J9)
     - as the rows above
     - none at the pin (no second ``replace`` after the carry,
       R.rst:623-624). If the gate fails: a second ``replace`` in ``limit``,
       fallback row 16l (section 3.3: ``mean`` on x1, ``owner_copy`` on
       panel seams), at the end of ``limit`` after row 17 and the carry, +1
       round; lanes X and EF decide
     - **G-S-K7** (section 5), gate harness only, no schedule row: own vs
       mapped peer; x1 seams all rows
       bitwise; panel seams mass, species, scalars bitwise, momentum to the
       16r tolerance (**hypothesis**), energy an expected failure until #370
       (row 17p); lane A's G5 (seam A F·K_f, 1e-14 rel) runs at the same
       point and depends on it (A.rst:736-750 at ``c3ac77f3``, D22)

**What this buys.** Mass, energy, species and scalars telescope exactly
across every shared face. Today panel seams agree only to round-off
(inventory H15: mass drift -9.9e-16 over 20 steps at 919936da), and
same-process x1 seams to whatever G-R10 measures.

**Cost.** Row 16r is one more cross-panel face-slab round per stage (33
rounds with every option on, 18 after M1-M8, section 3.5).

**4.1 Panel-edge map (item 1).** R's ``replace`` takes the peer **already
mapped** by S into this block's face dim, edge order, normal sign and basis
(``flux_register.hpp:62``; R.rst:712-732). The map is read once from
``CS_FACE_EDGES`` (``layout/cubed_sphere_layout.cpp:320-350``: ``nface``,
``nside``, ``rev``). The two derived flags are computed in ``serialize``:
``trans_flag`` (an L/R side meets a B/T side, ``:659``, applied
``:723-728``) and ``flip_flag`` (same side parity, ``:660``, applied
``:713-721``). Sides are ``SIDE_L=0, SIDE_R=1, SIDE_B=2, SIDE_T=3``
(``layout/cubed_sphere_constants.h:11``); L/R are x2 faces and B/T are x3
faces (``layout/cubed_sphere_layout.cpp:365-377, 704-709``). So
``peer_dim != dim`` is ``trans_flag``, ``reversed`` is ``rev``, and
``normal_sign = -1`` is ``flip_flag``: both outward normals point out of
their own panels, so every flux row is multiplied by -1.

.. list-table:: Panel edges (entries at ``layout/cubed_sphere_layout.cpp``)
   :header-rows: 1

   * - edge
     - entries
     - dim
     - peer_dim
     - reversed
     - normal_sign
   * - 1B-5R
     - :329 / :348
     - 3
     - 2
     - 1
     - +1
   * - 1T-3R
     - :330 / :338
     - 3
     - 2
     - 0
     - -1
   * - 2B-5B
     - :334 / :349
     - 3
     - 3
     - 1
     - -1
   * - 2T-3T
     - :335 / :340
     - 3
     - 3
     - 1
     - -1
   * - 3L-4T
     - :337 / :345
     - 2
     - 3
     - 1
     - +1
   * - 4B-5L
     - :344 / :347
     - 3
     - 2
     - 0
     - -1

The other 6 edges (0L-4R, 0R-1L, 0B-5T, 0T-3B, 1R-2L, 2R-4L) are identity:
same dim, not reversed, +1. Of the 24 directed entries all are mutual with
the same ``rev``; swap 4, reverse 4, negate 4, and each non-identity edge
has exactly two of the three. Read with a parser of ``:320-350`` (no build);
it agrees with R.rst:712-719.

``reconcile_seams`` maps the owner's slab before ``replace``: transpose to
``peer_dim`` if it differs, reverse along the edge if ``reversed``, multiply
every row by ``normal_sign``, then rotate the momentum rows with
``PanelRotation::panel_to_panel_rows_``, which takes the ``PanelEdge``
(lane A's conflict 2). On the 4 swap edges (1B-5R, 1T-3R, 3L-4T, 4B-5L)
the owner's face is an x3 face and the receiver's an x2 face, or the
reverse, and the two covariant face bases use different metrics
(``flux2global2_`` uses ``cosine_face2_kj``,
``coord/gnomonic_equiangle.cpp:452-453``; ``flux2global3_`` uses
``cosine_face3_kj``, ``:481-482``), so one ``dim`` cannot name both. R
expects the peer mapped in basis as well (``flux_register.hpp:62`` at
``4c59162a``). ``owner_copy`` copies the mapped
slab, and ``reconcile.panel`` is computed after the mapping (R.rst:727-729).
The map is ``SeamEntry::edges`` (``seam_register.hpp``).

**K7, the carry's momentum frame on panel seams** (R's question). The carry
adds donor velocity times withheld mass to post-rotation face rows
(``hydro/hydro_forward.cpp:1233-1236``). It runs in ``limit``, after
``reconcile``. On a panel seam the donor ghost's velocity is in the
receiver's basis after rows 1-3, so each side's carry is in its own face
basis. The two sides then differ by the rotation, and the energy part
differs until #370 syncs ``hspec`` (row 17p). **Hypothesis:** after #370
the momentum rows agree to the 16r tolerance. If R's G-R12 or a
post-``limit`` single-valuedness check fails, the fix is a second
``owner_copy`` replace in ``limit`` (+1 round). That is for lane X and EF.
The check is the declared gate G-S-K7 (section 5).

**Walls and solid faces: boundary.prescribed.** S's ``bc.solid_face`` maps
onto R's ``boundary.prescribed``:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - item
     - mapping
   * - name
     - ``boundary.prescribed`` (R's). S's ``bc.solid_face`` is retired
   * - who posts
     - R calls ``apply_prescribed(d)`` (``flux_register.hpp:65``). S makes no
       ``add`` call. R books the change as the named correction
       ``boundary.prescribed`` (R.rst:407-417)
   * - phase
     - ``reconcile``, after ``replace``; and again after ``post_implicit``
       (``flux_register.hpp:16, 21``)
   * - when S supplies
     - ``set_prescribed(d, mask, value)`` (``:45-47``) on **every register
       instance**: the hydro register and each Scalar module's own register
       (``flux_register.hpp:41``; R.rst:339-341, 590-591). Once per instance
       and active dim, redone when the solid field or the wall set changes
       (R.rst:1395-1397), not per stage. ``PrescribedFaces::build`` writes
       into tensors allocated at ``reset()`` and registered with
       ``StateStore::register_storage`` (section 7). The mask is ``[nvar, faces...]`` at
       that instance's ``nvar`` (row dimension settled, ``:45``;
       R.rst:709-711). In a Scalar register every row is prescribed to 0 on
       wall and solid faces; in the hydro register mass, species and energy
       are, momentum is not
   * - mask
     - per direction ``d`` and per row: true where the row is prescribed on
       the face. A face is prescribed if it is a physical reflecting wall
       (``FaceKind::wall``) or either neighbour cell is solid
       (``InternalBoundaryImpl::forward``'s ``solidl``/``solidr``,
       ``bc/internal_boundary.cpp:74-76``). Rows set: mass, species, energy,
       scalars. Momentum rows: not set (below)
   * - value
     - zero on every set row
   * - normals
     - coord's face unit normal in the post frame (``face_normal(d)``,
       ``coord_rotation.hpp``). It is supplied with the mask but unused by
       the default rule, because no momentum row is prescribed. It is needed
       only if EF chooses to zero tangential momentum (below)
   * - what S also supplies
     - the cell mask: solid cells are column breaks, and are excluded from
       theta, the hit census and the neighbour minimum (EF)

**Tangential momentum at solid faces (settled).** EF accepted free-slip
(EF.rst:696-699 at ``f5c8e9a7``), and R records it (R.rst:593-597 at
``a15af816``). Free-slip is what the pin does. ``InternalBoundaryImpl::forward`` copies the
fluid side's face state into the solid side and negates only the normal
velocity component (``bc/internal_boundary.cpp:78-80, 84-91``), so the tangential
velocity is mirrored equal. Reflecting walls do the same with ghost cells
(``bc/bc_func.cpp:10-34``: only ``var[4 - dim]`` is negated). With symmetric
states the Riemann contact speed is zero. So the mass flux, and the
tangential momentum flux ``rho u* v_t``, vanish, and the momentum flux is
the pressure ``p*`` along the normal. **Hypothesis:** "zero" holds to
round-off, which is R's G-R9. Hence:

- momentum rows are **not** prescribed; they keep the mirror-Riemann flux,
  normal and tangential alike;
- zeroing the tangential covariant row would be wrong on the cubed sphere.
  On a non-orthogonal face (``g23 = cos theta``,
  ``coord/gnomonic_equiangle.cpp:336-362``) the pressure force ``p* n``
  has a component in both covariant rows (``flux2global2_``,
  ``:428-455``), and zeroing one row removes part of the pressure force;
- no-slip would need a wall stress. The inviscid solver has none, and
  diffusion owns viscous walls. That is out of scope for V3;
- caveat (**hypothesis**): on gnomonic x2/x3 faces the mirror negates the
  covariant ``IVY``/``IVZ`` component (``bc/internal_boundary.cpp:84-91``).
  ``prim2local2_`` mixes ``uu2`` into the local tangential velocity
  (``coord/gnomonic_equiangle.cpp:373-391``: ``IVZ = T32 uu2 + T33 uu3``),
  so the local tangential velocities on the two sides are not exactly
  equal there. The contact speed still vanishes by symmetry of the normal
  part. Whether the tangential flux is exactly zero there is for G-R9.

**Settled answers recorded here.**

- S-1: coord owns ``PanelRotation`` and ``AxialRotationData``
  (``coord_rotation.hpp``). Lane A reads them through
  ``CoordinateImpl::rotation_geometry()`` (null without an axis; the
  gnomonic grid overrides it), which replaces the hooks at
  ``coord/coordinate.hpp:375-392``, and owns the Coriolis rate, the
  closure, ``omega_local`` and the m1 weights. ``RotationAxis`` refuses
  anything but z (``check_supported``). The FOR CHENG item about other axes
  sits in lane A.
- Lane A's conflict 1: ``AxialRotationData`` carries every member A's read
  view lists (A ``rotation_geometry.hpp:16-27`` at ``c3ac77f3``). Added in
  rev 2, each checked at the pin and none derivable without coord's
  metric or a host read: covariant ``k`` at the centres,
  ``k_cell_lower`` (``aam_kl_c``, ``coord/gnomonic_equiangle.cpp:173-174``,
  read at ``:494, 522-523``; lowering needs coord's ``cosine_cell_kj``);
  ``cos^2(lat)`` on both face sets, ``cos2_face2``/``cos2_face3``
  (``aam_c2_f2``/``aam_c2_f3``, ``:194, 215-216``, read at ``:705, 714``;
  taken at the face mid-direction, so not ``k_face . k_face``, which
  carries the face-average factor ``2 sin(dth/2)/dth``); and
  ``has_on_axis_cell``, set once at reset from ``on_axis`` (the pin does a
  host ``.item()`` on every call, ``:506``). ``cos2_lat`` is ``aam_kk_c``
  (``:175``). All of them are already built in the rotation data that stays
  with S (``:169-221``), so section 9 does not change. Rev 2.1 drops
  ``k_face2``/``k_face3`` from the public struct: no lane reads them (A
  reads ``K_f2``/``K_f3``, ``s2`` and ``cos2_face2``/``cos2_face3``), and
  coord keeps whatever it needs to build ``K_f`` internally. Lane A's
  skeleton comment still lists them (A ``rotation_geometry.hpp:2-3`` at
  ``a0b006d2``); that comment is A's to update.
- Rev 2.1, Jiachen's nit: ``rotation_geometry()`` is a virtual member,
  ``CoordinateImpl::rotation_geometry() const``, as lane A reads it
  (A.rst:678-680 at ``a0b006d2``). Rev 2's skeleton declared a free
  function under a comment that said virtual; the free function is gone
  and the skeleton records the member in a comment, because
  ``CoordinateImpl`` is the pin's class (``coord/coordinate.hpp``).
- S-2: as the convention above.
- S-3: diffusion keeps its four-round seam exchange
  (``forcing/diffusion_cubed_sphere.cpp:132-143``, row 18) until phase 3. It
  then moves onto ``Exchange::seam_slab`` as a face-slab row.
- EF: solid cells are column breaks for ``fix_vapor``: never donor or
  receiver. They are excluded from theta, from the hit census
  (``hydro/hydro_forward.cpp:1195-1196``) and from the neighbour minimum. S
  supplies the cell mask with the face mask. The limiter's use of it is lane
  C's.

**Traceability to the register requirements** (names as in lane I's table):

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - requirement
     - where lane S meets it
   * - R1 one owner, frame, area weighting
     - S owns no physical flux. Frame: coord's rotation, one implementation
       (``PanelRotation``). The seam slab is moved per unit area, as posted
   * - R2 named increments, declared order
     - ``boundary.prescribed`` (R's name, from S's mask), and the replaced
       amounts ``reconcile.x1`` and ``reconcile.panel``
   * - R3 stage weights
     - N/A: S posts no stage transfer
   * - R4 divergence reads the register
     - the divergence reads ``total(d)`` after ``reconcile``. Nothing in S
       rebuilds a flux
   * - R5 seams, single-valuedness, rotation in coord
     - one rule per shared face, the table above, same-process x1 seams
       included. Rotation only in ``PanelRotation``
   * - R6 no host reads in a segment
     - section 7
   * - R7 fixers and floors register what they added
     - the wall and solid-face zero as ``boundary.prescribed``, booked by R
   * - R8 FP32 dtype, capturable storage
     - section 6. Fixed seam buffers per (shape, dtype, device)
   * - R9 no added full-field copy
     - row 16r moves one face slab per seam, not a field
   * - R10 rebuilt, not in restart
     - the masks, rotations and schedule are rebuilt from the grid and the
       solid field


5. Invariants and gates
-----------------------

**The four failing identities**, cited as the PM reported them from the
919936da coord/layout/parallel/bc inventory and Xinyue's cross-check at
919936da. Not rerun here.

.. list-table::
   :header-rows: 1
   :widths: 14 30 28 28

   * - identity
     - reported at 919936da
     - at the pin, by reading
     - V3 gate
   * - H6 seam areas bitwise across panels
     - 48/384 edge-sides (24/192 seam faces) not bitwise, max rel 3.8e-14.
       Cause measured: term order on mixed x2/x3 edges. The x2f
       antisymmetry is a centre-face artefact, not a cause
     - the canonical endpoint-pair arc is in
       (``coord/gnomonic_equiangle.cpp:114-123``). That H6 now passes is a
       **hypothesis**
     - T2: seam arcs bitwise at N = 16, 48, 96
   * - H12 uniform state through the exchange
     - 96/23,040 ghost entries off by 1 ULP, density only, on nb = 1, 2 and
       CUDA. Cause measured: ``x*b1 + (1-x)*b0``
     - delta form in (``coord/gnomonic_equiangle.cpp:767-771``). Passing is a
       **hypothesis**
     - T3: uniform state bitwise through rows 1-3, CPU and CUDA
   * - H16 nb = 4 equals nb = 1 bitwise
     - 8 + 28 of 6,144 entries after 20 steps, ≤ 2.5e-16. Cause measured:
       ``torch::atan2`` is position-dependent under AVX2, and the difference
       is gone with ``ATEN_CPU_CAPABILITY=default``
     - still open: ``coord/cubed_sphere_utils.cpp:189`` feeds the exchange
       matrices
     - T1: nb = 1 vs 4 bitwise under AVX2, default and CUDA, after the
       Cartesian route replaces the spherical one (**hypothesis**)
   * - H18 CPU equals GPU
     - GPU = ``std::fma`` on all outputs. CPU = unfused, so 16.9-18.5% of
       outputs differ, max 2.8e-14
     - unchanged: nvcc contracts by default (``coord/coord_dispatch.cu:14-40``)
     - tolerance gate in the default build, ``rtol = 1e-13, atol = 1e-12``
       in FP64 (**hypothesis**: from the 2.8e-14 above, not rerun, and the
       closest GPU-vs-host check at the pin,
       ``tests/test_diffusion_cubed_sphere_two_gpu.cpp:112``; no V3 CPU-GPU
       run exists); bitwise in the CI configuration (``--fmad=false``,
       ``-ffp-contract=off``). Lane X owns the build flag

**Further invariants S gates.**

- **P (periodic corners).** Corner ghosts are periodic images on slab and
  cubed layouts. Today they are synthesized: 36 of 36 and 144 of 144 were
  wrong at 919936da, max 0.11. Gate: a ghost-image test after
  ``initialize`` and after one stage.
- **Same-process x1 seams.** With 2 and 4 blocks in one process and on a
  mixed layout, the two sides of every x1 seam are bitwise equal after
  ``reconcile`` (the mean is symmetric). R's G-R10 records ``|F_own -
  F_peer|`` before it. If that is beyond round-off, enabling the mean is a
  **FOR CHENG** change (section 10).
- **Seam single-valuedness.** After ``reconcile``, every shared face has the
  same non-momentum rows on both sides (bitwise). Momentum rows meet the
  section 4 tolerance.
- **Rotation involution.** The panel edge table maps every seam vertex to the
  same point from both panels (inventory I5: 0/24 failures, 3.6e-16 at
  919936da). Gate: a structural test of ``CS_FACE_EDGES``
  (``layout/cubed_sphere_layout.cpp:320-350``).
- **G-S13, the panel-edge map, anchored on 2T:3T** (feeds R's G-R13).
  (1) Structural: a unit test reads ``CS_FACE_EDGES`` and checks all 24
  directed entries are mutual with the same ``rev`` and that
  ``seam_entries()`` holds the section 4.1 table exactly. (2) 2T:3T
  (``:335``/``:340``: same dim, reversed and negated, so a missing reversal
  or sign survives every transpose check): cubed sphere at N = 16 and 48, one
  block per panel; a tracer and density monotone along the edge
  (``1 + k/N``) with non-zero normal velocity. After ``reconcile``,
  ``own(2, k) == normal_sign * peer(3, N-1-k)`` bitwise on mass, energy,
  species and scalar rows; momentum to the 16r tolerance (1e-14 relative,
  **hypothesis**). (3) **Negative control:** the same test with the map
  turned off must fail with an O(1) error on 2T:3T (R.rst:720-722). (4) The
  same check on 1T-3R (swap + negate) and 3L-4T (swap + reverse), so the
  three edges cover every pair of properties.
- **G-S-K7, post-limit single-valuedness** (K7; R's Q-R-i and G-R12,
  R.rst:623-627, 1352-1356). **Gate harness only** (rev 2.1 choice): it
  runs in the debug and CI decks below, never in a production schedule, so
  it is not a row, adds no round and has no device flag (the peer compare
  needs its own exchange, which a production flag would add to every
  stage). At the end of ``RegisterPhase::limit``, before
  ``divergence`` (``flux_register.hpp:17-18``), on every shared face, own
  against the mapped peer: x1 seams all rows bitwise; panel seams mass,
  species and scalar rows bitwise, momentum to the 16r tolerance, energy an
  expected failure until #370 syncs ``hspec`` (row 17p). Decks: the G-R12
  cubed-sphere deck with the limiter on (all 12 edges process seams), and a
  ``pz = 2`` deck with 2 blocks in one process. That it fails today is a
  **hypothesis** (the pin does no second ``replace`` after the carry,
  R.rst:623-624). Fix if it fails: a second ``replace`` in ``limit``
  (``mean`` on x1, ``owner_copy`` on panel seams), fallback row 16l
  (section 3.3), one more round; lanes X and EF decide. This gate answers J9: its row is G-S-K7 in
  the section 4 shared-face table. Lane A took J9 option (b): its G5 (seam
  ``A F · K_f``, 1e-14 relative) runs at the same point, at the end of
  ``limit``, and depends on G-S-K7, because A builds ``A F · K_f`` from the
  post-carry rows (A.rst:736-750 at JiachenLiu-Atmos/snapy ``c3ac77f3``,
  D22; the carry is ``hydro/flux_positivity.cpp:150-152``, called at
  ``hydro/hydro_forward.cpp:1234-1235`` before the scale at ``:1237``). If
  G-S-K7 fails, G5 is not meaningful until row 16l exists. G5 stays in
  phase 2 and A's count does not change.
- **Transport-only rows are bitwise.** Rows that copy (4, 5, 8, 10, 13-16,
  19, 22-25 and merges M1, M2, M4, M5, M7, M10 in phase 1; M6 in phase 3,
  with S-3) must give the same bits as at the pin. Gate: an nb = 1 vs nb = 2 run, and a pz = 1 vs pz = 2 run, under the
  scalar CPU setting.
- **Solid faces.** Zero mass, species, energy and scalar flux through every
  solid face. The ``boundary.prescribed`` amount equals the flux the mask
  removed (R's G-R9).


6. FP32 contract
----------------

- Exchanged fields travel in their storage dtype, and V3 adds no cast in a
  stage row. The only FP32-to-FP64 cast near an exchange is in
  ``initialize_local`` (``mesh/meshblock.cpp:448``), outside the stage.
- Geometry arrays are ``Quantity::kReference``: FP64 masters with cached
  casts per use (X ``precision_policy.hpp:17``; X.rst:283 at
  ``54ca5356``). That covers ``PanelRotation``, ``PanelGeometry``,
  ``AxialRotationData`` and the ``PrescribedFaces`` normals. They are built
  in FP64 and cast once per (dtype, device), as the exchange matrices are
  cached today (``layout/cubed_sphere_layout.cpp:161-191``); masks and
  ``solid_face_sign`` are bool/int8 and need no cast. Building on the CPU and moving
  changes the CUDA bits relative to today's lazy build on the velocity's
  device (cross-check §3 at 919936da). That is a change at round-off.
- The reconcile slab is in the register's ``kFlux`` dtype
  (``flux_register.hpp:82``). The mean of row 9 and the raw copy of row 16r
  are exact in either precision. The momentum rotation is not, and its gate
  tolerance scales with the dtype's epsilon (**hypothesis**).
- The anchor scan (rows 6-7) stays in the reference's precision, FP64 under
  perturbation flux (``hydro/hydro.cpp:636-641``, which sizes the anchor
  with the fp32 gauge).


7. CUDA-graph contract
----------------------

Every row of section 3.3 is a segment boundary for lane X today. Their waits
are a process-group ``wait()`` (``layout/layout.cpp:723-733``), a board
condition variable (``layout/layout.cpp:379-416``) or a stream synchronize
(``layout/layout.cpp:757-760, 804-807``). None can be captured. S's
contract:

- **No host read inside a row.** Row 29, the axial closure, is a
  per-stage, in-stage device collective with no host read: {R, I} are two
  FP64 device numbers, reduced on the device, and ``Fixer::apply`` scales
  on the device (A.rst:478-499, 1057-1059 at ``a0b006d2``). The pin's
  ``.item`` pair (``mesh/meshblock.cpp:1017-1018``) goes; the stage weight
  ``wght2()`` (``:1027``) is a host double from ``begin_stage`` (A.rst:493-497
  at ``a0b006d2``).
  The gravity-work fixer's ``.cpu()`` (``:1058-1061``) goes with the fixer
  (X.rst:452-453 at ``54ca5356``). A.rst:507-508 at ``a0b006d2`` still
  says X reduces {R, I} "through the host"; that sentence is A's and X's
  to align (section 11, Rev 2.1 item 5).
- **bc's outflow checks become device flags.** ``bc/bc_func.cpp`` has 11
  lines with ``.item<bool>()`` (12 calls in 9 ``TORCH_CHECK`` calls) on the
  outflow path: ``:93-103`` (``check_background``, called at ``:131``),
  ``:132``, ``:161``, ``:185``, ``:209-212`` and ``:221``. They run on every
  outflow face call, i.e. every stage, from ``apply_boundaries``
  (``mesh/meshblock.cpp:1846-1918``, called at ``:1006``), each a device-to-host
  sync. In V3 each check sets one bit of a per-block int32 device word
  (``BoundaryFlags::outflow_bad``) with no sync, and that word joins X's
  step-end read (``mesh/meshblock.cpp:1566``; X.rst:215, 249 at
  ``54ca5356``) as one more stacked flag. A set bit aborts at step end
  with the pin's message for that check (abort, not a retry cause, as
  today). The background-only checks (``:93-103`` and the reference half
  of ``:209-212``) read the fixed reference and could instead run once at
  ``reset()`` (proposal).
- **Fixed buffers, allocated at** ``reset()``. Every pack and unpack op of
  every row (rows 0-29, and 16i and 16l if they run) works on send and
  receive buffers allocated once at ``reset()`` per (row, shape, dtype,
  device), replacing the lazy ``exchange_buffer_cache``
  (``layout/cubed_sphere_layout.cpp:571-574``), and registered with
  ``StateStore::register_storage`` (X ``state_store.hpp:33-35`` at
  ``54ca5356``). Row 16r's slab buffer is fixed per dim.
- **Registered geometry and masks.** ``PrescribedFaces::build`` (mask,
  value, normal, ``solid_cells``, ``solid_face_sign``) and the
  ``AxialRotationData`` members added in rev 2 (``k_cell_lower``,
  ``cos2_face2``/``cos2_face3``, ``K_f2``/``K_f3``, ``s2``, ``on_axis``)
  live in tensors allocated at ``reset()`` and registered the same way. A
  rebuild (a new solid field or wall set) either writes into the
  registered tensors with ``copy_``, so addresses and graphs stay valid, or
  bumps the configuration generation in ``GraphKey`` (X.rst:71-74, 83 at
  ``54ca5356``); it never rebinds a registered tensor silently.
- **Declared rounds.** ``ExchangeRow::rounds`` is the number of segment
  boundaries the row costs. X may merge rows only as section 3.5 lists. A
  merge that is not bitwise (M3) is flagged in section 10.
- **Boards.** Same-process boards wait on a condition variable. Under
  capture they become device events in the ``Channel`` implementation
  (**hypothesis**: one event per row and peer is enough).


8. Cross-repository interface changes and merge order
-----------------------------------------------------

- **Python bindings.** ``cs_contra_to_sph_``/``cs_sph_to_contra_`` and
  ``cs_ab_to_lonlat`` stay public (``python/csrc/pycoord.cpp``, used by
  tests and output). The test-only ``populate_cs_l2g_vel``
  (``tests/test_coordinate.cpp:297-298``) goes with its test row.
- **commux** (Zoey). ``Channel`` sits on ``ProcessGroupContext``. Moving the
  process-group wrapper (``layout/process_group*``, ``layout/distributed*``,
  446 lines) into commux is a proposal, not a decision (section 9, move C).
- **Lane R.** ``reconcile_seams`` calls ``FluxRegister::replace(d, faces,
  peer, rule)``, and ``supply_prescribed`` calls
  ``FluxRegister::set_prescribed(d, mask, value)``, exactly as declared at
  ``4c59162a``. R calls ``apply_prescribed``. A rename in R is a one-line
  change here.
- **Lane A.** Coriolis (``forcing/coriolis.cpp:85-151``) stops building
  frame matrices and calls coord's ``centre_frame`` (S-6). A owns
  ``rate_to_rows`` (S-4) and reads ``K_f`` and ``s2`` from coord (S-5).
  Coord's ``x1_mass_source_`` reads A's ``X1Momentum`` m1 (S-8).
- **Merge order.** (1) ``PanelRotation`` plus the Cartesian exchange route
  (T1). (2) FaceKind and corners (P, T4). (3) ``Exchange`` with the x1 relays
  moved out of hydro (bitwise gate). (4) Row 16r, the same-process x1 mean
  and ``boundary.prescribed``, after
  R's register lands. (5) The deletions of section 9.


9. Line budget
--------------

Baseline 8,472 (section 1). Lane S has no line ceiling any more (Cheng's
below-target decision in the lane S thread), so this section gives the real
count and no ceiling arithmetic. "Exact" means the lines exist at the pin and
were counted with ``git show 9e5de2d4:src/FILE | sed -n 'a,bp' | wc -l``;
the removal has no caller or is replaced as named. "Estimate" is a design
estimate for code that is not written. Rows marked "rev 1.1" are carried
from rev 1.1 unchanged and were not recounted, except the coordinate row.

**New in rev 2.**

- **V3-1, 153 gnomonic AAM lines (exact).** Under RULING V3-1 a deletion is
  counted by the lane that owns the file, so S counts the AAM physics that
  leaves coord for lane A's ``src/forcing`` (A.rst:261-263, 284-287 at
  ``4e0827b8``). A lists ``gnomonic_equiangle.hpp:84-108, 117-122`` (25 + 6)
  and ``.cpp:526-604, 664-719`` (79 + 56) = 166, less
  ``x1_mass_source_`` (``.cpp:664-674``, 11; ``.hpp:84-85``, 2), which stays
  in coord (J1): **153**. They are ``axial_x1_source_`` and
  ``conserve_axial_momentum_`` (``.cpp:526-604``), ``axial_coriolis_rate``
  (``.cpp:675-719``) and their declarations (``.hpp:86-108, 117-122``). The
  rotation data (``.cpp:18-36, 169-221, 485-525``; ``.hpp:22-35, 109-116``,
  135 lines) stays with S (S-1).
- **Options parsing to lane O, 127 lines (exact).** Lane O splits move A
  (226 lines) into 127 for O's schema and 99 that stay in S (O.rst:2326-2406
  at JiachenLiu-Atmos/snapy ``5a7b46fa``). Every range holds exactly at the
  pin. S deletes the 127 and counts them; O books none (O.rst:2333-2334,
  2401-2402).

  .. list-table:: Final options ranges (pin)
     :header-rows: 1

     * - range
       - lines
       - goes to
     * - ``coord/coordinate.cpp:62-114``
       - 53
       - O: ``geometry``, ``bounds`` (incl. ``*_pi``), global bounds
     * - ``coord/coordinate.cpp:125-149``
       - 25
       - O: ``cells/nx1..3``, ``x1rat``/``x1f`` and their cross-checks
     * - ``coord/coordinate.cpp:213-214``
       - 2
       - O: ``nghost``, ``interp_order``
     * - ``layout/layout.cpp:249-272``
       - 24
       - O: ``distribute/*``, ``BACKEND``/``DEVICE``
     * - ``bc/internal_boundary.cpp:14-36``
       - 23
       - O: ``boundary-condition/internal/*``
     * - **to O**
       - **127**
       -
     * - ``coord/coordinate.cpp:115-124, 150-178, 179-212, 215-240``
       - 10 + 29 + 34 + 26 = 99
       - stay in S as the post-parse grid resolver

- **Lane A's S-4 to S-6 (section 11).** S-4: ``axial_rate_to_rows_``
  (``coord/gnomonic_equiangle.cpp:485-525``, 41; ``.hpp:109-116``, 8) moves
  to lane A, -49 exact, counted by S under V3-1; coord keeps an on-axis mask
  and the ``nx2 >= 3`` check, +6 estimate. S-5: ``K_f`` with the radial
  factor and ``s2``, +8 estimate. S-6: ``centre_frame`` on every grid, +25
  estimate (lane A deletes ``forcing/coriolis.cpp:85-151`` and counts it).
  Net -10 (-49 exact, +39 estimate).
- **D7 (34, counted in R).** S takes ``hydro/hydro.cpp:344-377`` as
  ``Exchange::x1_rows`` (+30, estimate, inside the layout row). R counts the
  -34 (R.rst:1464-1466); S counts no hydro deletion.
- **H-S1..H-S7, repeated or dead code inside S.** H-S1 is exact. For H-S2 to
  H-S7 the removed spans are exact and the nets are estimates.

  .. list-table::
     :header-rows: 1
     :widths: 10 50 10 10 20

     * - item
       - site (pin)
       - removed
       - net
       - status
     * - H-S1
       - dead ``reset_coordinates`` family: ``coord/coordinate.cpp:471-494``,
         ``coord/coordinate.hpp:214, 432``, ``coord/cartesian.cpp:48-77``,
         ``coord/spherical_polar.cpp:111-156``, ``.hpp:23``
       - 103
       - -103
       - exact; ``git grep -n reset_coordinates 9e5de2d4`` finds no caller
     * - H-S2
       - partition computed twice, ``coord/coordinate.cpp:181-211``
       - 31
       - -25
       - estimate (+6, the divisibility checks move to ``repartition``)
     * - H-S3
       - normal-velocity index by ``if (dim==...)``,
         ``bc/internal_boundary.cpp:83-92``
       - 10
       - -7
       - estimate (+3, as ``bc/bc_func.cpp:32``)
     * - H-S4
       - face table inverted twice, ``coord/cubed_sphere_utils.cpp:54-76``,
         ``.hpp:68-73`` (with its doc comment)
       - 29
       - -21
       - estimate (+8)
     * - H-S5
       - widening rule repeated, ``coord/gnomonic_equiangle.cpp:320-332``
         (kept: ``layout/cubed_sphere_layout.cpp:103-110``)
       - 13
       - -6
       - estimate
     * - H-S6
       - radial volume three ways, ``coord/spherical_polar.cpp:80, 201-205``
         (kept: ``coord/gnomonic_equiangle.cpp:292-296``)
       - 6
       - -4
       - estimate
     * - H-S7
       - face frame built twice: rev 1.1's ``face_normal(d)`` (+10) reuses
         ``coord/coordinate.cpp:811-837``
       - 0
       - -10
       - estimate (an addition avoided)
     * - **all**
       -
       - 192
       - **-176**
       - -103 exact, -73 estimate

- **Lane O overlap, counted once.** H-S2 (``coordinate.cpp:181-211``) lies
  inside the 99 lines that stay (``:179-212``) and is disjoint from the 127.
  It is counted once, as S's H-S2.
- **Recount.** Rev 1.1's coordinate row said "measured -24"; at the pin it is
  25 (``coord/coordinate.cpp:687-705`` 19, ``coord/coordinate.hpp:19``,
  ``:327``, ``:329-332``).

.. list-table::
   :header-rows: 1
   :widths: 30 8 8 8 46

   * - file or group (pin)
     - now
     - after
     - delta
     - deletions named
   * - ``coord/cubed_sphere_utils_impl.h``
     - 83
     - 0
     - -83
     - rev 1.1: ``cs_lonlat_to_ab``, no caller; include at
       ``coord/coord_dispatch.cpp:11`` (exact)
   * - ``coord/coordgen.{hpp,cpp}``
     - 13
     - 0
     - -13
     - rev 1.1: ``UniformCoord``, no caller (exact)
   * - ``coord/coordinate.{cpp,hpp}``
     - 1,297
     - 1,154
     - -143
     - rev 1.1 -25 (recount, exact); H-S1 -26 (exact); O's options -80
       (exact); H-S2 -31 +6 (estimate); ``face_normal`` +10 cancelled by
       H-S7 -10 (estimate); S-6 ``centre_frame`` +25 (estimate); AAM hooks
       ``coordinate.hpp:375-380, 382-385, 387-392`` -16 (exact, non-blank;
       ``:370-373`` stays); ``rotation_geometry()`` +4 (**estimate**: the
       virtual and the gnomonic override, booked here)
   * - ``coord/coord_dispatch.{cpp,hpp,cu}``
     - 218
     - 132
     - -86
     - rev 1.1: MPS kernels, ``cs_matrix_vec`` kernels (exact)
   * - ``coord/cubed_sphere_utils.{cpp,hpp}``
     - 550
     - 411
     - -139
     - rev 1.1 -118 (spherical frame route, +15 for
       ``panel_to_panel_rows_``); H-S4 -29 +8 (estimate)
   * - ``coord/gnomonic_equiangle.{cpp,hpp}``
     - 939
     - 765
     - -174
     - rev 1.1 +20 (axis check, estimate); **V3-1 -153 (exact)**; H-S5 -13
       +7 (estimate); S-4 -49 (exact) +6 (estimate); S-5 +8 (estimate)
   * - ``coord/cartesian.cpp``
     - 78
     - 48
     - -30
     - H-S1 (exact)
   * - ``coord/spherical_polar.{cpp,hpp}``
     - 363
     - 312
     - -51
     - H-S1 -47 (exact); H-S6 -4 (estimate)
   * - ``layout/cubed_sphere_layout.{cpp,hpp}``
     - 1,006
     - 816
     - -190
     - rev 1.1: velocity-transform cache, test-only and dead helpers,
       repeated intra-panel loops (measured span, net of about +10)
   * - ``layout/layout.{cpp,hpp}``
     - 1,338
     - 1,304
     - -34
     - rev 1.1 -10 (estimate; includes D7's ``x1_rows`` +30); O's options
       -24 (exact)
   * - ``layout/connectivity.hpp``
     - 234
     - 220
     - -14
     - rev 1.1: ``is_edge_loc``, ``is_corner_loc`` (exact)
   * - ``bc/rectify_solid.cpp``
     - 170
     - 112
     - -58
     - rev 1.1: ``run_flip_dim1/2/3`` become one (estimate)
   * - ``bc/bc_func.cpp``, ``bc/bc_dispatch.cpp``
     - 320
     - 318
     - -2
     - rev 1.1 -13: wall predicates become a ``FaceKind`` lookup; rev 2.1
       +11 (**estimate**): the 9 outflow ``TORCH_CHECK`` calls become flag
       updates of about the same length, plus the bit-to-message table and
       the flag word (section 7)
   * - ``bc/internal_boundary.{cpp,hpp}``
     - 225
     - 215
     - -10
     - rev 1.1 +20 (``PrescribedFaces``, estimate); O's options -23
       (exact); H-S3 -10 +3 (estimate)
   * - all other files
     - 1,638
     - 1,638
     - 0
     - rev 1.1's 2,079 less ``cartesian.cpp`` and ``spherical_polar.*``,
       which now have rows
   * - **total within S**
     - **8,472**
     - **7,445**
     - **-1,027 (-12.1%)**
     -

Arithmetic: rev 1.1's 7,913 - 153 (V3-1) - 127 (O) - 103 (H-S1) - 73
(H-S2..H-S7) - 1 (recount) = 7,456 (rev 2 part 1), then - 49 + 39 (S-4 to
S-6) = 7,446, then - 16 (AAM hooks, exact) + 4 (``rotation_geometry()``,
estimate) = 7,434 (rev 2), then + 11 (bc outflow flags, rev 2.1,
estimate) = 7,445. Of the new deletions, 449 lines are exact (V3-1 153, O
127, H-S1 103, S-4 49, hooks 16, recount 1) plus the rev 1.1 rows marked exact; the rest
are estimates.

Lane A's conflicts 1-3 change no counted line: the new ``AxialRotationData``
members are buffers the pin already builds in the rotation data S keeps
(``coord/gnomonic_equiangle.cpp:169-221``) and ``has_on_axis_cell`` is set
with S-4's on-axis mask (+6, estimate); ``panel_to_panel_rows_`` taking a
``PanelEdge`` stays inside its +15 (estimate, cubed-sphere utils row); the
signed solid-face set is built with the ``PrescribedFaces`` mask from the
same ``solidl``/``solidr`` (+20, estimate, internal-boundary row). The total
stays 7,434 at rev 2.

Rev 2.1 changes one row: ``bc_func.cpp`` +11 (estimate, the outflow device
flags). Removing row 30 and M9, moving M6, the fallback rows 16i/16l, the
``reset()`` buffers and registration, dropping ``k_face2``/``k_face3`` from
the public struct and the virtual ``rotation_geometry()`` (already booked
as +4) change no counted line: the buffers and registration calls sit in
``BlockExchange`` (``mesh/meshblock.cpp``, outside the baseline) and the
dropped members are built by the rotation data S keeps. ``BlockExchange``
itself is outside the baseline (section 1). Total 7,445.

**Not counted.**

- Moves B (``coord/x1_centroid.{cpp,hpp}``, -283) and C (process-group
  wrapper, ``layout/process_group*``, ``layout/distributed*``, -446) are
  still not agreed with their receivers. With both, 6,716 (rev 2: 6,705).
- ``coord/coordinate.hpp:370-373`` (``x1_mass_source_``) stays and is not
  counted. The hooks ``:375-380`` (``conserve_axial_momentum_``),
  ``:382-385`` (``axial_rate_to_rows_``, S-4) and ``:387-392``
  (``axial_x1_source_``), 16 non-blank lines, are now counted in the
  coordinate row (A.rst:267 books ``coordinate.hpp:370-392`` to S); lane A
  reads ``rotation_geometry()`` instead. The blank lines ``:381`` and
  ``:386`` are not counted (with them, 7,443).

**S's 149 hydro lines are counted in R.** The lines leaving hydro for S's
transport (``hydro/hydro.cpp:344-377, 727-776``,
``hydro/hydro_forward.cpp:882-946``: 149 lines, replaced by about 60 in
``layout.cpp``) are R's D7 (34), D5's ``:882-946`` (65) and **R's D1**
``hydro.cpp:727-776`` (50), each counted once, in R (R.rst:1535-1539).
Under R-C2, C counts no deletion of ``hydro.cpp:727-776`` and neither does
S (R.rst:759-762).

**D7, ``hydro/hydro.cpp:344-377``: S takes it (yes, unconditionally).** It
is ``HydroImpl::_x1_ghost_rows`` (34 lines; declared ``hydro/hydro.hpp:402``),
the generic x1 ghost-row relay, over a board for a same-process block and
the process group otherwise (``:353-367``). Its callers are schedule rows 4,
5, 10, 13-16, 19 and 22-25 (``hydro/hydro_forward.cpp:249, 491, 666, 953,
1063, 1490``). S takes it as ``Exchange::x1_rows`` (``exchange.hpp``), which
also packs several fields in one message (merges M4, M5). R accepts it
unconditionally (R.rst:196-197, 733).


10. Migration
-------------

**Phase 1 (transport only, bitwise).** ``Exchange`` and ``Channel`` take
over the x1 relays and the schedule. Merges M1, M2, M4, M5, M7 and M10
(section 3.5) are copies. Gate: bitwise at nb = 1, 2 and pz = 1, 2 under the
scalar CPU setting. M8 goes in only if its bitwise **hypothesis** holds. M6
is not in phase 1: diffusion keeps its own exchange until phase 3 (S-3;
A.rst:160-161, 775 at ``a0b006d2``).

**Phase 2 (rotation and corners, round-off).** The Cartesian route replaces
the spherical one (T1), and diagonal corners replace synthesized ones on slab
and cubed layouts (P). Both change bits: at round-off for T1, and by up to
0.11 for wrong periodic corners, which is a correction. **FOR CHENG**: the
periodic-corner correction changes results beyond round-off on decks with
periodic x2 and x3. Affected decks are listed in the PR.

**Phase 3 (register).** Row 9 becomes ``replace(1, faces, peer,
SeamRule::mean)`` under R, now on every x1 seam: the
``is_local_block``/``has_process_group`` gates
(``hydro/hydro_forward.cpp:882-888``) go, so same-process seams are averaged
too. Where both sides already agree bitwise, nothing changes. Otherwise the
change is the G-R10 difference: round-off is the **hypothesis**, and beyond
round-off it is **FOR CHENG**. Row 16r and ``boundary.prescribed`` (R calls
``apply_prescribed``; S supplies ``set_prescribed``) start. Mass, energy, species and scalars telescope exactly
across panel seams (a round-off change). Zeroing the solid-face rows changes
results by the mirror flux's leak, which is round-off if the mirror is exact
(**hypothesis**). Otherwise **FOR CHENG**. Diffusion moves onto a face-slab
row (S-3), and merge M6 (one 48-channel round for row 18, a copy, gated
bitwise like phase 1's merges) goes in with it.

**Not bitwise, flagged.**

- **M3, the anchor scan.** Replacing the serial relay (rows 6-7,
  ``hydro/hydro.cpp:614-641, 704-713``) with one column gather and a prefix
  sum changes the summation order of the hydrostatic scan, so the reference
  pressure changes at round-off on every x1-split run. That is round-off.
  Anything beyond it is **FOR CHENG**. It stays a proposal for lane X.
- **The eight merges** (M1-M8) are a **hypothesis** for lane X. The earlier
  commit counted 23 → 12 blocking points per site. This table counts 32 → 17
  rounds per round, 18 with row 16r (section 3.5).


11. Open questions to other lanes
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 14 86

   * - lane, owner
     - question
   * - R, Tianhao
     - Settled by R rev 2.2: R calls ``apply_prescribed`` under the name
       ``boundary.prescribed``; panel seams use ``SeamRule::owner_copy`` on
       the peer S maps (section 4.1); the replaced amounts are
       ``reconcile.x1``/``reconcile.panel``; K6, the ``mean`` on every x1
       seam (R.rst:734-735); the mask's row dimension (``:45``;
       R.rst:709-711); D7 (R.rst:733). Settled by R rev 2.4 (R.rst:39-42,
       632-657 at ``a15af816``): the ``boundary(dim)`` face set, S's
       proposal as written (section 3.1). Open: K7, the G-S-K7 gate
       (section 5) and who adds row 16l if it fails. Lane O's L-3 text and
       O.rst:2915-2917 (x1 faces only on the sphere) should now name solid
       faces too; that is O's
   * - EF, Zoey
     - Settled: EF accepted free-slip (EF.rst:696-699 at ``f5c8e9a7``). No
       momentum row is prescribed (section 4). ``face_normal(d)`` stays
       supplied in case EF later wants the tangential projection zeroed.
       Open: G-S-K7's fallback row 16l (with X)
   * - X
     - Answered (X.rst:905-910 at ``54ca5356``): (1) yes, cuts at S's rows,
       merges as labelled (X.rst:453-458: M1, M2, M4-M7, M10 under X's
       golden, M8 once it passes, M3 Cheng's call); (2) the options parsing
       is not X's, X asks O (S already moved it to O, section 9); (3) yes,
       X owns the CI build for H18 (``--fmad=false``,
       ``-ffp-contract=off``) as capability-matrix row G0. Open: whether
       16i and 16l, if their gates fail, get their own segment cut or pack
       into 16r's
   * - C, Tianhao
     - The theta exclusion of solid cells uses S's cell mask. Does the hit
       census (``hydro/hydro_forward.cpp:1195-1196``) take the same mask?
   * - A, Jiachen
     - Answers to A.rst section 11.4 at ``4e0827b8``. **S-4:** agreed, lane
       A owns ``rate_to_rows`` with its on-axis rule
       (``coord/gnomonic_equiangle.cpp:485-525``, the share at ``:499-514``);
       coord keeps ``AxialRotationData`` with an on-axis mask and checks
       ``nx2 >= 3`` at reset when an on-axis cell exists (``:509-512``).
       **S-5:** agreed, coord provides ``s2`` and ``K_f2``/``K_f3``, the
       exact face averages of ``K = s k`` with the radial factor of
       ``:563-567``, next to ``k_cell`` (rev 2.1: ``k_face2``/``k_face3`` are no longer public). **S-6:**
       agreed, coord's ``centre_frame()`` is never null on Cartesian,
       spherical-polar and gnomonic grids (today ``forcing/coriolis.cpp:
       85-151``); a grid with no rule throws at reset, never returns null.
       Cylindrical has no compiled coord at the pin
       (``coord/cylindrical.cpp_``), so it throws until one exists.
       **S-7:** yes, all three are rows of the table (section 3.3): #370's
       syncs are row 17p (theta stays row 17;
       ``730b3500`` ``hydro_forward.cpp:1230, 1254-1271``); diffusion's
       ``phyid 12`` is row 18 until phase 3 (S-3); the radial split's
       exchange is row 0 (``mesh/meshblock.cpp:716-717``), after
       ``post_split`` at ``:715``, whose order R states (R-8). **S-8:**
       agreed: ``x1_mass_source_`` already takes ``m1`` as an argument
       (``coord/gnomonic_equiangle.cpp:664-667``), so coord reads whatever
       A's ``X1Momentum`` provides, with no Coriolis private; the call order
       is R's (R-7). The non-z axis stays FOR CHENG in A (settled).
       **J9:** option (b) taken, G5 depends on G-S-K7 (section 5).
       **Round 2 conflicts:** (1) the missing ``AxialRotationData`` members
       are added (section 4, settled answers); (2) ``panel_to_panel_rows_`` takes
       the ``PanelEdge`` (section 4.1); (3) solid faces in ``boundary(dim)``
       was a proposal to R and is now the contract (R rev 2.4, section
       3.1). **Rev 2.1:** ``rotation_geometry()`` is the virtual member A
       reads; ``k_face2``/``k_face3`` leave the public struct (section 4)
   * - commux, Zoey
     - Move C: would commux take the process-group wrapper?
   * - PM / Cheng
     - None open: lane S has no ceiling (section 9)


**Rev 2.1: the PM's items 1-8 on rev 2 (``c505fb87``), by number.** Lines
are this revision's ``S.rst`` lines; the skeleton changes are in section 12.

.. list-table::
   :header-rows: 1
   :widths: 6 10 18 66

   * - item
     - answer
     - S.rst line
     - what changed
   * - 1
     - agree
     - 873, 1451, 1868
     - M6 left phase 1 and the phase-1 bitwise list; it goes in with S-3 in
       phase 3 (section 3.5 M6 row, section 5, section 10), matching
       A.rst:160-161, 775 at ``a0b006d2``
   * - 2
     - agree
     - 34-46
     - S owns ``BlockExchange``: ``mesh/meshblock.cpp:644-685, 1111-1205,
       1846-1918`` less ``:1198-1200`` (X ``meshblock_parts.hpp:18-20`` at
       ``54ca5356``); declared in ``exchange.hpp``. Lines outside S's
       baseline (proposal: X books them)
   * - 3
     - agree
     - 1503-1516
     - bc's 11 ``.item<bool>()`` lines (12 calls) become bits of
       ``BoundaryFlags::outflow_bad``, joined to X's step-end read; section
       9 +11 (estimate)
   * - 4
     - agree
     - 243-265
     - block faces by ``FaceKind``; fluid-solid faces by the solid mask
       (``solid_face_sign``); solid-solid amounts stay out of
       ``boundary(dim)``. "Pending R" removed: R rev 2.4 (R.rst:39-42,
       632-657 at ``a15af816``)
   * - 5
     - agree
     - 803-806, 899-902, 1492-1502
     - row 29 is a per-stage device collective, no host read (A.rst:478-499,
       1057-1059 at ``a0b006d2``; pin ``mesh/meshblock.cpp:1017-1018,
       1027``). Row 30 and M9 removed (X.rst:452-453). Totals 32, 17 with
       M1-M8, 18 with 16r (X.rst:456-458). Note: A.rst:507-508 still says
       "through the host"; A and X to align
   * - 6
     - agree
     - 965-987
     - row 9 does not run again after ``implicit``: the pin refuses an x1
       split under an implicit scheme (``hydro/hydro.cpp:485-490``), so the
       ``vic.*`` posts never land on an x1 seam. Read, not run; the
       periodic-slab case is a **hypothesis**
   * - 7
     - agree
     - 535, 572, 1517-1532
     - pack/unpack buffers allocated at ``reset()`` and registered; rows
       16i (G-R2 fallback, ``reconcile``, +1 or 0 packed) and 16l (G-S-K7
       fallback, end of ``limit``, +1); ``PrescribedFaces::build`` and the
       new ``AxialRotationData`` members in registered storage, rebuilt by
       ``copy_`` or a configuration-generation bump (X.rst:71-74, 83)
   * - 8
     - agree
     - 98, 703, 707, 1060, 1237, 1289, 1295, 1427, 1465, 1934
     - geometry ``kReference`` FP64 (section 6); X's three answers (X row
       above); G-S-K7 gate harness only; panel rows "mapped by the
       ``PanelEdge`` (4.1), then copied"; row 28 cites ``:952``; row 29
       "with a process group"; EF bullet reworded to EF.rst:700-704 at
       ``f5c8e9a7`` (Zoey's note itself not seen here); free-slip settled;
       ``k_face2``/``k_face3`` out of the public struct; ``rotation_geometry()``
       a virtual member (Jiachen's nit)


12. Skeleton index
------------------

``docs/v3/skeleton/S/`` holds declarations and comments only, 291 lines
in all (``wc -l``; rev 2: 259). It is not part of any build. It uses R's names at ``4c59162a``
(``FluxRegister``, ``RegisterPhase::reconcile``, ``SeamRule``,
``replace(dim, faces, peer, rule)``, ``set_prescribed``,
``apply_prescribed``) and R's namespace ``snap``.

.. list-table::
   :header-rows: 1

   * - file
     - lines
     - declares
     - replaces (pin)
   * - ``coord_rotation.hpp``
     - 91
     - ``RotationAxis``, ``PanelRotation`` (``panel_to_panel_rows_`` takes a
       ``PanelEdge``), ``AxialRotationData`` (``k_cell``, ``k_cell_lower``,
       ``cos2_lat``, ``cos2_face2``/``cos2_face3``, ``K_f2``/``K_f3``,
       ``s2``, ``on_axis``, ``has_on_axis_cell``; no ``k_face2``/``k_face3``),
       ``CoordinateImpl::rotation_geometry()`` (virtual member, in a
       comment), ``centre_frame``,
       ``PanelGeometry``; ``face_normal``
     - ``cs_velocity_transform_matrix`` and its callers; the layout's
       ``_velocity_transform``; Coriolis' frame
   * - ``exchange.hpp``
     - 103
     - ``FaceKind``, ``CornerRule``, ``Frame``, ``ExchangeRow`` (with
       ``fallback``), ``stage_schedule``, ``Channel``, ``Exchange`` (with
       ``reset``), ``BoundaryFlags``, ``BlockExchange``
     - hydro's x1 relays (``hydro/hydro.cpp:344-377``, R's D7, as
       ``x1_rows``); the three wall predicates; the board/remote pair;
       ``mesh/meshblock.cpp:644-685, 1111-1205, 1846-1918`` less
       ``:1198-1200``; bc's 11 outflow ``.item<bool>()`` lines
   * - ``seam_register.hpp``
     - 97
     - ``SeamOwner``, ``SeamGate``, ``PanelEdge``, ``SeamEntry``,
       ``seam_entries``, ``reconcile_seams``, ``PrescribedFaces`` (with
       ``solid_face_sign``, R's contract since rev 2.4),
       ``supply_prescribed``, ``post_limit_single_valued``
     - ``hydro/hydro_forward.cpp:882-946`` (as transport, every x1 seam);
       the unmasked wall and solid-face flux
