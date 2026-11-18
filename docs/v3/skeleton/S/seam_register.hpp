#pragma once
// V3 lane S skeleton: declarations only, in no build. Revision 2.1.
// The two-sided register entry for every shared face (S.rst section 4) and
// the wall/solid faces S supplies for R's "boundary.prescribed". Names are
// R's at happysky19/snapy 4c59162a (flux_register.hpp): FluxRegister,
// RegisterPhase::reconcile, SeamRule {mean, owner_copy} (:24),
// replace(dim, faces, peer, rule) (:62-64), set_prescribed(dim, mask,
// value) (:45-47); R itself calls apply_prescribed(dim) (:65).
#include <cstdint>
#include <string>
#include <vector>
#include <torch/torch.h>

namespace snap {
class FluxRegister;
class Exchange;
class PanelRotation;
enum class SeamRule : uint8_t;  // R's (flux_register.hpp:24)

//! who holds the canonical value of a shared face
enum class SeamOwner : uint8_t {
  both_mean,   // every x1 seam, process or same-process: SeamRule::mean
               // (pin: process seams only, hydro_forward.cpp:887-888)
  lower_rank,  // panel seam: SeamRule::owner_copy, momentum rotated (16r)
  self,        // intra-panel x2/x3 edge: same bits on both sides, no replace
};

//! the declared gate of one entry kind
struct SeamGate {
  bool bitwise;        // true: compared with ==
  double rel_tol;      // used only when !bitwise (panel momentum: 1e-14)
  std::string reason;  // e.g. "two panels' covariant bases, one rotation"
};

//! one directed panel edge, read once from CS_FACE_EDGES
//! (cubed_sphere_layout.cpp:320-350); 24 entries, 6 non-identity edges
struct PanelEdge {
  int8_t panel, side, peer_panel, peer_side;  // 0..5; SIDE_L/R/B/T
  int8_t dim, peer_dim;  // 2 for L/R, 3 for B/T; differ <=> trans_flag (:659)
  bool reversed;         // CS_FACE_EDGES[..].rev
  int8_t normal_sign;    // -1 if flip_flag (:660): every flux row x -1
};

struct SeamEntry {
  int dim;              // 1 = x1, 2 = x2, 3 = x3 (R's numbering)
  SeamOwner owner;
  SeamGate gate;
  std::vector<int> rotated_rows;  // momentum rows; empty when none
  std::vector<PanelEdge> edges;   // lower_rank only: the map before replace
};

//! the entries S declares (S.rst section 4 table)
std::vector<SeamEntry> const& seam_entries();

//! phase reconcile: per dim, S gathers the shared faces and the peer entry
//! (Exchange::seam_slab: board for a local peer, process group otherwise),
//! maps a panel peer by its PanelEdge (transpose, reverse, normal_sign),
//! rotates its momentum rows with coord's rotation, and calls R's
//! FluxRegister::replace(dim, faces, peer, rule)
void reconcile_seams(FluxRegister& reg, Exchange& ex,
                     PanelRotation const& rot);

//! wall and immersed-solid faces for R's "boundary.prescribed". A face is
//! prescribed if it is a reflecting wall or either neighbour cell is solid
//! (internal_boundary.cpp:74-76). Rows set: mass, species, energy, scalars,
//! value 0. Momentum rows are not set: they keep the mirror-Riemann flux
//! (free-slip, internal_boundary.cpp:78-80, 84-91). normal is coord's face
//! unit normal in the post frame, supplied for EF's tangential option only.
struct PrescribedFaces {
  torch::Tensor mask[3];    // bool [nvar, faces...]: row prescribed on face
  torch::Tensor value[3];   // [nvar, faces...]: 0 on every set row
  torch::Tensor normal[3];  // [3, faces...], unused by the default rule
  torch::Tensor solid_cells;  // EF: column breaks; out of theta and census
  //! fluid-solid faces for RegisterMonitor::boundary(dim), from the solid
  //! mask, not FaceKind (closed by R rev 2.4, R.rst:632-657 at a15af816).
  //! int8 [faces...]: +1 solid on the high side, -1 on the low side, 0 on
  //! fluid-fluid and solid-solid faces; R sums sign * A_f S_d, all rows
  torch::Tensor solid_face_sign[3];
  //! writes with copy_ into tensors allocated at reset() and registered
  //! with StateStore::register_storage; a new shape bumps the configuration
  //! generation instead (X.rst:71-74, 83 at 54ca5356)
  static void build(PrescribedFaces& into, torch::Tensor const& solid,
                    int nvar, std::vector<int> const& zero_rows);
};

//! S's only call into R for boundaries: set_prescribed(dim, mask, value)
//! per register instance (hydro and each Scalar module), per active dim,
//! redone when the solid field or wall set changes
void supply_prescribed(FluxRegister& reg, PrescribedFaces const& faces);

//! gate G-S-K7 (S.rst s5): end of RegisterPhase::limit, own vs mapped peer
//! on every shared face; gate harness only (debug and CI decks), no
//! schedule row, no device flag. If it fails: fallback row 16l
bool post_limit_single_valued(FluxRegister const& reg, Exchange& ex,
                              PanelRotation const& rot);

}  // namespace snap
