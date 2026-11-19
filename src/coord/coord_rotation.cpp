#include "coord_rotation.hpp"

// C/C++
#include <vector>

// snap
#include "coord_utils.hpp"
#include "cubed_sphere_utils.hpp"

namespace snap {

void PanelRotation::contra_to_cart_(torch::Tensor vel, int panel,
                                    torch::Tensor alpha,
                                    torch::Tensor beta) const {
  cs_contra_to_cart_(vel, alpha, beta, panel);
}

void PanelRotation::cart_to_contra_(torch::Tensor vel, int panel,
                                    torch::Tensor alpha,
                                    torch::Tensor beta) const {
  cs_cart_to_contra_(vel, alpha, beta, panel);
}

torch::Tensor PanelRotation::matrix(int panel, torch::Tensor alpha,
                                    torch::Tensor beta, bool to_global,
                                    torch::Tensor cosine) const {
  TORCH_CHECK(alpha.sizes() == beta.sizes(),
              "PanelRotation: coordinates must have matching shapes");
  TORCH_CHECK(alpha.scalar_type() == beta.scalar_type() &&
                  alpha.device() == beta.device(),
              "PanelRotation: coordinates must match in dtype and device");
  if (cosine.defined()) {
    TORCH_CHECK(cosine.sizes() == alpha.sizes(),
                "PanelRotation: cosine has an incompatible shape");
    TORCH_CHECK(cosine.scalar_type() == alpha.scalar_type() &&
                    cosine.device() == alpha.device(),
                "PanelRotation: cosine must match the coordinates' dtype and "
                "device");
  }

  auto spatial = alpha.sizes().vec();
  auto vector_shape = spatial;
  vector_shape.insert(vector_shape.begin(), 3);
  auto matrix_shape = vector_shape;
  matrix_shape.insert(matrix_shape.begin() + 1, 3);
  auto m = torch::empty(matrix_shape, alpha.options());

  for (int input = 0; input < 3; ++input) {
    auto basis = torch::zeros(vector_shape, alpha.options());
    basis[input].fill_(1.);
    if (to_global) {
      if (cosine.defined()) coord_vec_raise_(basis, cosine);
      contra_to_cart_(basis, panel, alpha, beta);
    } else {
      cart_to_contra_(basis, panel, alpha, beta);
      if (cosine.defined()) coord_vec_lower_(basis, cosine);
    }
    m.select(1, input).copy_(basis);
  }
  return m;
}

}  // namespace snap
