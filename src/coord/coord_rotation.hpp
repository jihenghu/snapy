#pragma once

// torch
#include <torch/torch.h>

namespace snap {

//! The one rotation between cubed-sphere panels (V3 lane S, step (1); S.rst
//! rev 2.4 section 3.1, "One rotation"). A vector goes from one panel's
//! contravariant components to the global Cartesian frame and from there to
//! another panel's contravariant components. That route needs no atan2, so
//! the matrices it builds depend on the point alone, not on where a strip
//! starts (the H16 identity, gate T1).
class PanelRotation {
 public:
  //! panel contravariant components -> global Cartesian, in place; vel is
  //! [3, ...] (radial, x2, x3) at the points (alpha, beta) of `panel`
  void contra_to_cart_(torch::Tensor vel, int panel, torch::Tensor alpha,
                       torch::Tensor beta) const;
  //! global Cartesian -> panel contravariant components, in place
  void cart_to_contra_(torch::Tensor vel, int panel, torch::Tensor alpha,
                       torch::Tensor beta) const;

  //! the pointwise [3, 3, ...] matrix the exchange caches: to_global maps the
  //! panel's components to Cartesian, else Cartesian to the panel's. With
  //! cosine defined (conserved momentum), the metric raise before (to_global)
  //! or the lower after (from global) is composed into the matrix
  torch::Tensor matrix(int panel, torch::Tensor alpha, torch::Tensor beta,
                       bool to_global,
                       torch::Tensor cosine = torch::Tensor()) const;
};

}  // namespace snap
