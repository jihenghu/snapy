// Closed decks, every step: mass, E + rho phi (gravity-work: cell + its fixer)
// and each tracer's mass close to round-off; the AAM about +z is logged only.
#include <gtest/gtest.h>
#include <yaml-cpp/yaml.h>

#include <snap/coord/cubed_sphere_utils.hpp>
#include <snap/mesh/mesh.hpp>

#include "cuda_test_gate.hpp"
using namespace snap;
using Case = std::tuple<char const*, char const*, int>;  // name, deck, scheme
double const C = 4., kEps = 1.e-15, g = 10.;  // |X_n - X_0| <= C n eps |X_0|
std::string card(Case const& c) {  // the in-tree deck, closed and small
  auto d = YAML::LoadFile(std::get<1>(c));
  d.remove("outputs");
  auto cells = d["geometry"]["cells"];
  if (cells["nx2"].as<int>() == 1) cells["nx2"] = cells["nx3"] = 4;
  for (auto f : {"x2-inner", "x2-outer", "x3-inner", "x3-outer"})
    if (!d["boundary-condition"]["external"][f])
      d["boundary-condition"]["external"][f] = "reflecting";
  d["forcing"]["const-gravity"]["grav1"] = -g;
  d["forcing"]["const-gravity"]["gravity-work"] = "cell";
  d["integration"] = YAML::Load("{type: rk3, cfl: 0.5}");
  d["integration"]["implicit-scheme"] = std::get<2>(c);
  std::string path = std::string("budget_") + std::get<0>(c) + ".yaml";
  std::ofstream(path) << d;
  return path;
}
struct Budget : testing::TestWithParam<Case> {};
TEST_P(Budget, closes_to_round_off) {
  auto c = GetParam();
  bool cuda = getenv("SNAP_BUDGET_CUDA");  // the _cuda entry
  if (cuda && !snapy_cuda_test_enabled()) GTEST_SKIP() << "no CUDA";
  auto mesh = Mesh(MeshOptionsImpl::from_yaml(card(c)));
  int nb = mesh->blocks.size(),
      ny = mesh->blocks[0]->phydro->peos->nvar() - ICY;
  MeshVariables vars(nb);
  std::vector<std::vector<torch::Tensor>> geo(nb);  // dV, phi, two lz arms
  for (int i = 0; i < nb; ++i) {
    auto b = mesh->blocks[i];
    auto co = b->pcoord;
    auto m = torch::meshgrid({co->x3v, co->x2v, co->x1v}, "ij");
    double x0 = co->options->x1min(), h = co->options->x1max() - x0;
    auto r = m[2], s = (r - x0) / h;
    double rho0 = ny ? 1.16 : 1.e5 / (g * h), u0 = std::sqrt(10. / rho0);
    auto w = r.new_zeros({ICY + ny, r.size(0), r.size(1), r.size(2)});
    w[IDN] = rho0 * (-(r - x0) * rho0 * g / 1.e5).exp() *
             (1. + 0.01 * (3. * m[1]).sin() * m[0].cos());
    w[IPR] = w[IDN] / rho0 * 1.e5;
    w[IVX] = u0 * (M_PI * s).sin() * (2. * m[1]).cos();
    w[IVY] = u0 * (M_PI * s).sin();
    for (int n = 0; n < ny; ++n)  // vapor subsaturated, first condensate empty
      w[ICY + n] = (n == 1 ? 0. : 0.01) * (1. + 0.5 * s);
    // lz = sum (arm2 u[IVY] + arm3 u[IVZ]) dV, arm_j = g^ji r (r^ x b_i).z
    auto arm = r.new_zeros({4, 3, r.size(0), r.size(1), r.size(2)});
    if (co->options->type() == "spherical-polar") arm[1][1] = r * m[1].sin();
    if (co->options->type() ==
        "gnomonic-equiangle") {  // arm[0]: the axis, arm[1-3]: the panel basis,
                                 // in (r, th, ph)
      int face =
          std::get<2>(b->get_layout()->loc_of(b->options->layout()->rank()));
      arm[0][0].fill_(1.);
      cs_cart_to_contra_(arm[0], m[1], m[0], face);
      for (int j = 0; j < 4; ++j) {
        if (j) arm[j][j - 1].fill_(1.);
        cs_contra_to_sph_(arm[j], m[1], m[0], face);
      }
      auto k = arm[0], c = co->cosine_cell_kj;
      auto a2 = r * (arm[2][1] * k[2] - arm[2][2] * k[1]);
      auto a3 = r * (arm[3][1] * k[2] - arm[3][2] * k[1]);
      arm[1][0] = (a2 - c * a3) / (1. - c * c);
      arm[1][1] = (a3 - c * a2) / (1. - c * c);
    }
    auto phi = g * (co->options->type() == "cartesian" ? r - x0 : r);
    geo[i] = {co->cell_volume(), phi, arm[1][0], arm[1][1]};
    if (cuda) b->to(torch::kCUDA);
    for (auto& t : geo[i]) t = t.to(co->x1v.device());
    vars[i]["hydro_w"] = w.to(co->x1v.device());
  }
  mesh->initialize(vars);
  auto P = PartOptions().exterior(false);
  auto in = mesh->blocks[0]->part({}, P),
       in3 = mesh->blocks[0]->part({}, P.ndim(3));
  auto totals = [&]() {  // mass, E + PE, lz, then each tracer
    std::vector<double> t(3 + ny, 0.);
    for (int i = 0; i < nb; ++i) {
      auto u = vars[i].at("hydro_u").index(in);
      auto dV = geo[i][0].index(in3);
      auto rho = u[IDN] + u.narrow(0, ICY, ny).sum(0);
      std::vector<torch::Tensor> x = {
          rho * dV, (u[IPR] + rho * geo[i][1].index(in3)) * dV,
          (u[IVY] * geo[i][2].index(in3) + u[IVZ] * geo[i][3].index(in3)) * dV};
      for (int n = 0; n < ny; ++n) x.push_back(u[ICY + n] * dV);
      for (int k = 0; k < 3 + ny; ++k) t[k] += x[k].sum().item<double>();
    }
    return t;
  };
  auto t0 = totals();
  for (int step = 1; step <= 20; ++step) {
    double dt = mesh->max_time_step(vars);
    for (int st = 0; st < 3; ++st) mesh->forward(vars, dt, st);
    auto t = totals();
    printf("budget %s step %2d lz %+.6e rel", std::get<0>(c), step, t[2]);
    for (int k = 0; k < 3 + ny; ++k) {
      if (k == 2) continue;  // angular momentum: logged only
      double rel = std::abs(t[k] - t0[k]) / std::abs(t0[k] ? t0[k] : t0[0]);
      printf(" %.2e", rel);
      EXPECT_LE(rel, C * step * kEps) << "total " << k << " step " << step;
    }
    printf("\n");
  }
}
Case const kDecks[] = {{"cartesian_s0", "test_gravity_energy.yaml", 0},
                       {"cartesian_s9", "test_gravity_energy.yaml", 9},
                       {"spherical_s0", "test_fix_vapor_volume.yaml", 0},
                       {"spherical_s9", "test_fix_vapor_volume.yaml", 9},
                       {"cubed_s0", "test_cubed_sphere_cell_volume.yaml", 0},
                       {"cubed_s9", "test_cubed_sphere_cell_volume.yaml", 9}};
INSTANTIATE_TEST_SUITE_P(Decks, Budget, testing::ValuesIn(kDecks),
                         [](auto const& p) { return std::get<0>(p.param); });
