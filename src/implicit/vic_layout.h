#pragma once

#include <configure.h>

#include <Eigen/Dense>
#include <cstddef>
#include <cstdint>

namespace snap {

// The VIC workspace on CUDA stores neighbouring columns adjacent in memory
// (element e of level i at (i * R * C + e) * s, s = number of columns), so a
// warp's one-thread-per-column accesses coalesce. a[i] maps level i's R x C
// block with the same element order as the column-contiguous CPU layout.
template <typename T, int R, int C>
struct VicStrided {
  using Map = Eigen::Map<Eigen::Matrix<T, R, C>, 0, Eigen::InnerStride<>>;
  T* p;
  int64_t s;
  DISPATCH_MACRO Map operator[](int i) const {
    return Map(p + int64_t(i) * R * C * s, Eigen::InnerStride<>(s));
  }
  DISPATCH_MACRO VicStrided operator+(int i) const {
    return {p + int64_t(i) * R * C * s, s};
  }
  DISPATCH_MACRO bool operator!=(std::nullptr_t) const { return p != nullptr; }
};

}  // namespace snap
