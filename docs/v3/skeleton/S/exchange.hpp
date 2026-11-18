#pragma once
// V3 lane S skeleton: declarations only, in no build. Revision 2.3.
// Pin chengcli/snapy 9e5de2d4ce497d0b2d4da3295fc1fe969fe7e410. S owns the
// transport of every within-stage exchange (S.rst section 3 table); the
// rules for registered fluxes are R's (flux_register.hpp:62-65 at 4c59162a).
#include <cstdint>
#include <string>
#include <vector>
#include <torch/torch.h>

namespace snap {
class MeshBlockImpl;
class StateStore;                    // X's (state_store.hpp at 54ca5356)
enum class RegisterPhase : uint8_t;  // R's (flux_register.hpp:14-23)

//! what a block face is; replaces three wall predicates (hydro.cpp:296-301,
//! is_physical_boundary, bc_func.cpp:231-250) with one lookup
enum class FaceKind : uint8_t {
  interior,  // same-panel neighbour block
  seam_x1,   // x1 process or thread seam (pz > 1)
  panel,     // cubed-sphere panel seam, rotated
  periodic,  // seam to self (layout wrap, or the bc copy on slab x1)
  wall,      // reflecting / solid
  outflow,   // radiating
  custom,    // user callback
};

//! corners: diagonal neighbour on slab and cubed layouts; synthesized
//! 0.5*(edge+edge) only at cubed-sphere panel corners (layout.cpp:681-721)
enum class CornerRule : uint8_t { none, diagonal, synthesized, x1_full };

enum class Frame : uint8_t { raw, rotated_cell, rotated_face };

//! one row of the declared stage schedule (S.rst section 3.3)
struct ExchangeRow {
  int id;                 // row number in S.rst
  std::string name;       // e.g. "reconcile.x1"
  RegisterPhase phase;    // R's phase where the row is a register phase
  Frame frame;
  CornerRule corners;
  bool interpolate;       // cubed-sphere ghost interpolation (delta form)
  int rounds;             // sequential blocking rounds; X cuts at each
  bool fallback;          // 16i, 16l: in the schedule only if their gate fails
};

//! one stage's schedule, built at reset(); the last stage adds row 28's
//! second call. X reads it to place one cut per round
std::vector<ExchangeRow> const& stage_schedule(int stage, bool last_stage);

//! one transport for same-process boards and the process group (today two
//! paths: layout.cpp:312-500, 895-940 and 556-653)
class Channel {
 public:
  virtual ~Channel() = default;
  virtual void post(int block, torch::Tensor const& t, int tag) = 0;
  virtual torch::Tensor take(int block, torch::Tensor const& like,
                             int tag) = 0;
  virtual void wait_all() = 0;
};

//! S's transport API. Replaces the hand-written relays in hydro
//! (hydro.cpp:344-377, 622-776; hydro_forward.cpp:882-946)
class Exchange {
 public:
  explicit Exchange(MeshBlockImpl const* pmb);
  FaceKind kind(int face) const;  // face 0..5 as bfuncs()
  //! blocking conveniences: for each round r of the row, pack(r),
  //! host_wait(r), unpack(r). None allocates
  void ghosts(std::vector<torch::Tensor> fields, int type,
              bool interpolate);  // rows 0-3, 11-12, 17, 18, 20-21, 26-27
  void x1_rows(std::vector<torch::Tensor> fields, int m, bool faces,
               int tag);  // rows 4-5, 8, 10, 13-16, 19, 22-25 (R's D7)
  torch::Tensor seam_slab(int dim, torch::Tensor const& slab,
                          int tag);  // rows 9, 16r, 16i, 16l
  torch::Tensor gather_x1(torch::Tensor const& piece);  // row 28: a view
  torch::Tensor anchor_scan(torch::Tensor const& local_drop);  // M3
  //! X's kPack | kHost | kUnpack for round r in [0, ExchangeRow::rounds)
  //! (X stage_executor.hpp:27-29 at 7bed6980). pack writes, unpack reads
  //! only buffers registered at reset(). Synthesized corners (V3-4): unpack
  //! of each field set's last round, that set only, if skip_corner (pin)
  void pack_ghosts(int row, int round, std::vector<torch::Tensor> const& f);
  void unpack_ghosts(int row, int round, std::vector<torch::Tensor> f);
  void pack_x1_rows(int row, std::vector<torch::Tensor> const& f, int m,
                    bool faces);
  void unpack_x1_rows(int row, std::vector<torch::Tensor> f, int m,
                      bool faces);
  void pack_seam_slab(int row, int dim, torch::Tensor const& slab);
  torch::Tensor unpack_seam_slab(int row, int dim);  // view, receiver basis
  void pack_gather_x1(int round, torch::Tensor const& piece);  // row 28
  torch::Tensor unpack_gather_x1(int round);  // view of the column buffer
  //! rows 6-7, bitwise serial relay down the x1 column. Same-process
  //! top-down order under X's executor: hypothesis, untested
  torch::Tensor unpack_anchor();                // row 6, after its wait
  void pack_anchor(torch::Tensor const& face);  // row 7, before its wait
  //! kHost: post, progress and complete one round; never captured
  void host_wait(int row, int round);
  //! buffers per (row, round, shape, dtype, device), registered with
  //! StateStore::register_storage (X state_store.hpp:33-35); builds the
  //! stage schedules
  void reset(StateStore& store);
};

//! bc's outflow checks (bc_func.cpp:93-103, 132, 161, 185, 209-212, 221):
//! one bit each in a per-block int32 device word, no sync; joins X's
//! step-end read (meshblock.cpp:1566), which aborts with the check's message
struct BoundaryFlags {
  torch::Tensor outflow_bad;  // int32 [1], zeroed at step start
  static std::string message(int bit);
};

//! owner S, as X assigns (X meshblock_parts.hpp:18-20 at 54ca5356): now
//! meshblock.cpp:644-685, 1111-1205, 1846-1918, less 1198-1200 (X's divide)
struct BlockExchange {
  Exchange* ex;
  BoundaryFlags flags;
  void exchange_ghost_zones(std::vector<torch::Tensor> fields);  // rows 1-2
  void apply_boundaries(torch::Tensor hydro, torch::Tensor tracers,
                        bool primitive);  // sets flags, never reads them
};

}  // namespace snap
