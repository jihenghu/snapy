#pragma once
// V3 lane S skeleton: declarations only, in no build. Revision 2.3. Lines
// at pin 9e5de2d4. S-1 (settled): coord owns ONE rotation and the rotation
// data; lane A owns the Omega and mass-flux consumers.
#include <array>
#include <torch/torch.h>

namespace snap {  // R's namespace (flux_register.hpp:12 at 4c59162a)
class CoordinateImpl;
struct PanelEdge;  // seam_register.hpp

//! declared rotation axis, hard-coded z today (gnomonic_equiangle.cpp:22-35);
//! anything else is refused at construction (FOR CHENG item, in lane A)
struct RotationAxis {
  std::array<double, 3> unit = {0., 0., 1.};
  void check_supported() const;  // throws unless unit == z
};

//! the one rotation; replaces cubed_sphere_utils.cpp:146-193, 259-334,
//! cubed_sphere_layout.cpp:132-191, coriolis.cpp:128-142 and
//! diffusion_cubed_sphere.cpp:193, 371. No atan2 (H16: utils.cpp:189)
class PanelRotation {
 public:
  //! panel contravariant <-> global Cartesian (cubed_sphere_utils.cpp:194-243)
  void contra_to_cart_(torch::Tensor vel, int panel, torch::Tensor alpha,
                       torch::Tensor beta) const;
  void cart_to_contra_(torch::Tensor vel, int panel, torch::Tensor alpha,
                       torch::Tensor beta) const;
  //! owner's covariant face vector (edge.peer_panel, edge.peer_dim) into
  //! this face's covariant basis (edge.panel, edge.dim): lower o cart_to_contra
  //! o contra_to_cart o raise, each side with its own face metric (:452-453,
  //! :481-482). Rows already mapped by the edge; alpha/beta are this face's.
  //! Covers the 4 swap edges 1B-5R, 1T-3R, 3L-4T, 4B-5L (row 16r)
  void panel_to_panel_rows_(torch::Tensor rows, PanelEdge const& edge,
                            torch::Tensor alpha, torch::Tensor beta) const;
  //! the face rotation the solver and the register use today
  //! (gnomonic_equiangle.cpp:365-484), unchanged in V3
  void prim2local_(torch::Tensor w, int dim) const;
  void flux2global_(torch::Tensor flux, int dim) const;
  //! face unit normal in the post frame, for boundary.prescribed (S.rst s4)
  torch::Tensor face_normal(int dim) const;
};

//! coord's rotation data (gnomonic_equiangle.cpp:18-36, 169-221); A's
//! rate_to_rows (:485-525, S-4) reads it (A rotation_geometry.hpp:16-27 at
//! c3ac77f3). kReference FP64 (X precision_policy.hpp:17 at 54ca5356);
//! registered at reset(), rebuilt by copy_ or a configuration-generation
//! bump. k_face2/k_face3 are not public (rev 2.1)
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

//! per-panel geometry built once (919936da owner G): seam arcs from one
//! function of the unordered endpoint pair (gnomonic_equiangle.cpp:114-123)
struct PanelGeometry {
  torch::Tensor seam_arc2, seam_arc3;
  static torch::Tensor arc(torch::Tensor const& e, torch::Tensor const& a,
                           torch::Tensor const& b);
};

}  // namespace snap
