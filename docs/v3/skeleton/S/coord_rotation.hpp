#pragma once
// V3 lane S skeleton: declarations only, in no build. Revision 2.1.
// Pin chengcli/snapy 9e5de2d4ce497d0b2d4da3295fc1fe969fe7e410; lines at the
// pin. Untested claims: "hypothesis". S-1 (settled): coord owns ONE rotation
// and the rotation data; lane A owns the Omega and mass-flux consumers.
#include <array>
#include <torch/torch.h>

namespace snap {  // R's namespace (flux_register.hpp:12 at 4c59162a)
class CoordinateImpl;
struct PanelEdge;  // seam_register.hpp

//! declared rotation axis. Only z is supported; anything else is refused at
//! construction with a message (FOR CHENG item, kept in lane A). The axis is
//! hard-coded z today (gnomonic_equiangle.cpp:22-35).
struct RotationAxis {
  std::array<double, 3> unit = {0., 0., 1.};
  void check_supported() const;  // throws unless unit == z
};

//! the one rotation. Replaces the spherical frame matrices
//! (cubed_sphere_utils.cpp:146-193, 259-334; cubed_sphere_layout.cpp:132-191),
//! Coriolis' own frame (coriolis.cpp:128-142) and diffusion's calls
//! (diffusion_cubed_sphere.cpp:193, 371). The Cartesian route needs no atan2
//! (cubed_sphere_utils.cpp:189 is the H16 source).
class PanelRotation {
 public:
  //! panel contravariant <-> global Cartesian (cubed_sphere_utils.cpp:194-243)
  void contra_to_cart_(torch::Tensor vel, int panel, torch::Tensor alpha,
                       torch::Tensor beta) const;
  void cart_to_contra_(torch::Tensor vel, int panel, torch::Tensor alpha,
                       torch::Tensor beta) const;
  //! a covariant face vector of the owner's face (edge.peer_panel, face dim
  //! edge.peer_dim) into the covariant basis of this block's face
  //! (edge.panel, edge.dim) at the same seam face: lower o cart_to_contra
  //! o contra_to_cart o raise, each side with its own face metric
  //! (flux2global2_ uses cosine_face2_kj, :452-453; flux2global3_ uses
  //! cosine_face3_kj, :481-482). The rows are already transposed, reversed
  //! and signed by the edge; alpha/beta are this block's face coordinates,
  //! the owner's follow from the edge. Covers the 4 swap edges 1B-5R, 1T-3R,
  //! 3L-4T, 4B-5L, where dim != peer_dim (row 16r)
  void panel_to_panel_rows_(torch::Tensor rows, PanelEdge const& edge,
                            torch::Tensor alpha, torch::Tensor beta) const;
  //! the face rotation the solver and the register use today
  //! (gnomonic_equiangle.cpp:365-484), unchanged in V3
  void prim2local_(torch::Tensor w, int dim) const;
  void flux2global_(torch::Tensor flux, int dim) const;
  //! face unit normal in the post frame, for boundary.prescribed (S.rst s4)
  torch::Tensor face_normal(int dim) const;
};

//! the rotation data coord owns (gnomonic_equiangle.cpp:18-36, 169-221).
//! rate_to_rows (:485-525) is lane A's (S-4); A reads these, never casts.
//! Members A reads: A skeleton rotation_geometry.hpp:16-27 at c3ac77f3.
//! kReference: FP64 masters, cached casts per use (X precision_policy.hpp:17
//! at 54ca5356). Tensors allocated at reset() and registered with
//! StateStore::register_storage; a rebuild writes with copy_ or bumps the
//! configuration generation. k_face2/k_face3 are not public (rev 2.1).
struct AxialRotationData {
  RotationAxis axis;
  torch::Tensor k_cell;        // contravariant, unit radius, at centres
  torch::Tensor k_cell_lower;  // covariant k at centres (aam_kl_c, :173-174)
  torch::Tensor cos2_lat;      // k . k = cos^2(lat) at centres (aam_kk_c)
  torch::Tensor cos2_face2, cos2_face3;  // at the face mid-direction
                                         // (aam_c2_f2/f3, :194, :215-216)
  torch::Tensor K_f2, K_f3;  // S-5: exact face averages of K = s k (:563-567)
  torch::Tensor s2;          // S-5: s^2 = (r cos lat)^2 at the cell centres
  torch::Tensor on_axis;     // S-4: bool mask; reset checks nx2 >= 3 if any
  bool has_on_axis_cell;     // set at reset from on_axis; no per-call .item()
};

//! A's read of the rotation data: a virtual MEMBER of the pin's class
//! CoordinateImpl (coord/coordinate.hpp), not a free function (rev 2.1):
//!   virtual AxialRotationData const* rotation_geometry() const;
//! null without an axis; GnomonicEquiangle overrides. Replaces the hooks at
//! coordinate.hpp:375-392 (16 non-blank lines); +4 lines, an estimate

//! S-6: centre frame on every grid, never null (Cartesian, spherical-polar,
//! gnomonic; replaces coriolis.cpp:85-151). No rule: throws at reset
torch::Tensor centre_frame(CoordinateImpl const& coord);

//! per-panel derived geometry built once (owner G in the 919936da designs):
//! seam arcs from one function of the unordered endpoint pair (already at
//! the pin, gnomonic_equiangle.cpp:114-123)
struct PanelGeometry {
  torch::Tensor seam_arc2, seam_arc3;
  static torch::Tensor arc(torch::Tensor const& e, torch::Tensor const& a,
                           torch::Tensor const& b);
};

}  // namespace snap
