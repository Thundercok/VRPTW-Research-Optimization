# Kế hoạch V2 — Nâng cấp Hybrid DDQN-ALNS và chạy lại toàn bộ benchmark

## Bối cảnh

Có hai yêu cầu cần khớp nhau:

- **`plan_estimated`** — brief nghiên cứu: đề xuất các cải tiến *tăng dần*, tương thích kiến trúc hiện có (không thay DDQN, không thay ALNS), xếp hạng theo ROI, kèm ablation và kiểm định thống kê.
- **`plan.md` cũ** — kế hoạch chạy lại sweep sản xuất ~16 h để sinh lại số liệu cho paper.

Hai cái này không mâu thuẫn, chúng **nối tiếp nhau**: sweep 16 h là chi phí phải trả *một lần*, nên nó phải chạy **sau** khi tập cải tiến đã chốt. Nếu chạy sweep trước rồi mới cải tiến thì phải trả 32 h.

Vì vậy kế hoạch V2 = **[sàng lọc rẻ trên bench] → [triển khai cái sống sót] → [sweep 16 h một lần] → [cập nhật paper]**.

### Ràng buộc bắt buộc giữ nguyên (theo `plan_estimated`)

Không thay DDQN bằng PPO/SAC/Rainbow, không thay ALNS bằng GA/HGS, giữ nguyên Hierarchical DDQN, Learned Acceptance Criterion, khung Adaptive Destroy/Repair, module Set Partitioning, khung Local Search và toàn bộ pipeline. Mọi mục dưới đây đều **mở rộng** một thành phần đã có, không thay thế.

### Bài học chi phối mọi quyết định

Bốn ý tưởng trước đây đã bị **đo đạc bác bỏ** (lọc kNN trong repair, số hạng slack của FTS, toán tử SISR, lịch destroy răng cưa). Trường hợp răng cưa là bài học đắt nhất: **thắng ở cùng số vòng lặp, thua ở cùng thời gian tường**. Do đó:

> Mọi thay đổi ảnh hưởng chất lượng đều phải được đánh giá ở **cùng thời gian tường**, không phải cùng số vòng lặp. Tỷ lệ trúng thực tế của dự án này cho các ý tưởng chất lượng là **0/4** — xếp hạng dưới đây phản ánh điều đó.

---

## Giao thức đánh giá (làm trước tiên — mọi mục đều dùng)

Đây là xương sống. Không có nó thì 20 mục ở dưới chỉ là phỏng đoán.

**Bench sàng lọc** — tái dùng `scripts/ab_compare.py` (đã có): 9 instance × 2 solver × 5 seed = 90 lần chạy ghép cặp, ~10 phút/nhánh sau tối ưu. Sàng cả 20 mục ≈ 3,5 h tổng.

Ba cổng, mục nào rớt cổng nào thì dừng ở đó:

| Cổng | Nội dung | Tiêu chí qua |
|---|---|---|
| **G1 — Đúng đắn** | `pytest tests/` + golden fingerprint `tests/golden/baseline.json` | 44/44 xanh. Mục "bit-identical" phải khớp golden **chính xác**; mục đổi quỹ đạo thì cập nhật golden có chủ đích |
| **G2 — Tốc độ** | `ab_compare` cùng số vòng lặp, đo tổng wall time | Không chậm đi. Mục Tầng A phải nhanh hơn đo được |
| **G3 — Chất lượng iso-time** | Nhánh cũ và mới chạy **cùng ngân sách thời gian**, nhánh nhanh hơn được tăng số vòng lặp tương ứng (`--iters`) | Wilcoxon NV (ưu tiên chính) và gap-BKS **ở cùng số xe** |

**G3 là cổng quyết định.** Mục nào chỉ thắng ở G2 mà không giữ được ở G3 thì lợi ích của nó là "nhanh hơn", không phải "tốt hơn" — ghi đúng như vậy.

### Hạ tầng còn thiếu, phải viết trước

| Việc | File | Lý do |
|---|---|---|
| Cờ `--time-limit` / `--no-time-limit` | `docs/run_benchmark.py` (argparse ~dòng 45–52) | Runner hiện **không có** cách bật/tắt `time_limit`, mặc định `time_limit_per_customer=0.6`. Không có cờ này thì không tách được hai giao thức và nhánh so-với-số-cũ sẽ bị chặn trần thời gian → sai |
| `scripts/compare_sweeps.py` | mới | So hai file kết quả theo `(Instance, Algorithm)`; Wilcoxon **tách theo họ** C1/C2/R1/R2/RC1/RC2; **TD ở cùng số xe** (phép kiểm đã lật ngược kết luận SISR); đếm số lần chạm đúng NV của BKS |
| `scripts/make_paper_tables.py` | mới | Hiện **không có** script sinh bảng LaTeX — 6 bảng trong paper làm tay. Không có nó thì "update full" = chép tay 6 bảng |
| Chế độ iso-time cho `ab_compare.py` | có sẵn `--iters` | Đủ dùng, chỉ cần quy ước: đo wall time nhánh gốc rồi chỉnh `--iters` nhánh mới cho khớp |

---

## Bảng xếp hạng ROI — 20 cải tiến

ROI = (mức cải thiện kỳ vọng × xác suất trúng) / chi phí triển khai. Cột **Chắc chắn** là điểm mấu chốt: phân biệt lợi ích *cơ học* (suy ra được từ cấu trúc mã, gần như không thể sai) với lợi ích *phỏng đoán* (phải đo mới biết).

### Tầng A — Lợi ích cơ học, rủi ro gần bằng 0 · **Đợt 1**

| # | Cải tiến | Thành phần mở rộng | Runtime | Chất lượng | Khó | Chắc chắn |
|---|---|---|---|---|---|---|
| A1 | Cache LS cập nhật tăng dần | `local_search.py:1044` | **Cao** | gián tiếp | TB | Rất cao |
| A2 | Bỏ Python `set` trong hot loop | `_PlanCache` `local_search.py:67–75` | Cao | gián tiếp | Dễ | Rất cao |
| A3 | Don't-look bits cho quét move | `_best_relocate/_best_swap/_best_or_opt` | **Cao** | phải đo | TB | Cao (tốc độ) |
| A4 | Sum-tree cho PER | `rl.py:55–80` | TB | không | Dễ | Rất cao |
| A5 | Pha đuôi biết deadline | `solvers.py:1940–2030` | — | **Có** (iso-time) | Dễ | Cao |
| A6 | Tái dùng timing khi chèn tuần tự trong greedy repair | `op_greedy`/`op_tw_greedy` → `_insert_into_cheapest_route` | **Cao** | gián tiếp | TB | Rất cao |
| A7 | Cache đặc trưng trạng thái RL theo `cur` | `_op_state`/`_state` `solvers.py:591–649, 1555` | TB-Cao | không | Dễ | Rất cao |
| A8 | Sửa oversubscription luồng trong sweep | `core.py:5–9` + `benchmark.py:434` | TB (sweep) | **độ tin cậy phép đo** | Dễ | Cao |

### Tầng B — Có căn cứ tài liệu, nhắm đúng số xe · **Đợt 1**

| # | Cải tiến | Thành phần mở rộng | Runtime | Chất lượng | Khó | Chắc chắn |
|---|---|---|---|---|---|---|
| B1 | **Guided Ejection Search** | `_try_buffered_route_elimination` `local_search.py:824` | chậm hơn | **NV — cao nhất** | Cao | TB-Cao |
| B2 | SREX crossover | `EliteArchive.crossover` `rl.py:190` | — | TB | TB | Cao |
| B3 | Chọn cột SP theo đối ngẫu + cache | `_milp_recombine` `pool.py:191` | TB | TB | TB | TB |

### Tầng C — Phỏng đoán, **chỉ sàng lọc, chưa cam kết**

| # | Cải tiến | Thành phần | Ghi chú |
|---|---|---|---|
| C1 | n-step returns (n=3) | cả 2 controller `rl.py` | Chuẩn Rainbow, không thay DDQN. Reward bị shaping nặng → credit assignment có thể lợi |
| C2 | Chuẩn hoá reward tách NV/TD | `WelfordRewardNormalizer` + `_iteration_reward` | Reward trộn cú nhảy NV (+15) với gain TD (~1); Welford vô hướng clip 8σ **nuốt mất** sự kiện NV |
| C3 | Số hạng nhiễu trong repair | `operators.py` `_regret`/`op_greedy` | Ropke & Pisinger chuẩn; repair hiện tất định hoàn toàn với removal set cho trước |
| C4 | Regret-k với k thích nghi | `_regret` `operators.py:523` | Hiện cố định regret_2/regret_3 |
| C5 | Tự hiệu chỉnh nhiệt độ ban đầu | `temp_control=0.05` `config.py:198` | Hằng số cố định qua mọi họ instance dù thang chi phí khác nhau rất xa |
| C6 | Ma trận khoảng cách float32 | `core.py` `Inst` | n=1000: 8 MB → 4 MB, vừa cache hơn. Rủi ro trôi số → đổi quỹ đạo |
| C7 | `prange` cho quét move | `numba_kernels.py` | Ở n≥600 số instance < 12 nhân → nhân rỗi ở đuôi sweep |
| C8 | `_MILP_MAX_COLS` thích nghi | `pool.py:191` | Hiện cắt cứng 400 cột bất kể instance |
| C9 | Trim route pool có tính đa dạng | `RoutePool._priority/_trim` `pool.py:59–64` | Hiện xếp theo chi phí → cột trùng lặp về phủ |
| C10 | Nhịp train thích nghi theo ngân sách | `solvers.py:1788` (`% 4`), `:1846` | Nhịp cố định, không biết còn bao nhiêu thời gian |
| C11 | Bandit trên kích thước destroy | `destroy_size` `operators.py:773` | **Cẩn trọng:** răng cưa đã thua iso-time. Chỉ chấp nhận nếu qua G3 |
| C12 | Bỏ forward pass thừa | `OperatorController.act` `rl.py:544` | Nhánh `except` chạy lại y hệt forward pass đã làm ở trên |

---

## Chi tiết Đợt 1 (8 mục Tầng A + B)

### A1 — Cache local search cập nhật tăng dần

**Hiện trạng.** `local_search()` gọi `_PlanCache.from_plan(best)` ở **`local_search.py:1044`, bên trong vòng `while moves < max_ls_moves`**. Mỗi move được chấp nhận là một lần dựng lại **toàn bộ** cache: `route_timings` cho mọi tuyến (O(n)), `centroids` (O(n)), `centroid_sqdist` (O(R²)), `route_sets` + `route_neighbors` (set Python, O(n·k)), `node_to_route` (O(n)).

**Vì sao cải thiện.** Một move relocate/swap/or-opt chỉ thay đổi **tối đa 2 tuyến**. Toàn bộ phần còn lại của cache vẫn đúng nguyên. Với `max_ls_moves=15` và LS chạy mỗi vòng lặp ALNS, đây là công việc lặp lại thuần tuý.

- **Runtime kỳ vọng:** cao — đây là hot loop rõ nhất còn lại sau đợt tối ưu trước.
- **Chất lượng kỳ vọng:** 0 trực tiếp; gián tiếp qua thêm vòng lặp trong cùng ngân sách.
- **Khó:** Trung bình. **Rủi ro:** cache cũ (stale) → sai kết quả im lặng. Golden test là lưới an toàn.
- **Thay đổi mã:** thêm `_PlanCache.update_routes(self, plan, changed_indices)`; các `_apply_*` trả về chỉ số tuyến đã đổi; `local_search` gọi update thay vì `from_plan`.
- **Thí nghiệm:** G1 phải **bit-identical** với golden. G2 đo tăng tốc.
- **Ablation:** on/off trên bench 9 instance.
- **Novelty:** thấp (kỹ thuật), nhưng là cái cho phép mọi thứ khác.

### A2 — Bỏ `set` Python khỏi `_PlanCache`

**Hiện trạng.** `local_search.py:67–75` dựng `route_sets = [set(r) for r in plan.routes]` và `route_neighbors` bằng hợp các set kNN cho **từng tuyến, mỗi lần dựng cache**.

**Vì sao cải thiện.** Set Python trên hot path là cấp phát + băm; thay bằng ma trận `uint8` `[R, n+1]` hoặc mảng `node_to_route` int + kiểm tra thành viên bằng mảng thì thành truy cập bộ nhớ liên tục, và dùng lại được trong kernel Numba.

- **Runtime:** cao. **Chất lượng:** 0. **Khó:** Dễ. **Rủi ro:** thấp.
- **Kiểm chứng:** bit-identical với golden.
- Nên làm **cùng lúc** với A1 (chạm cùng cấu trúc dữ liệu).

### A3 — Don't-look bits

**Hiện trạng.** Mỗi lần quét, `_best_relocate` duyệt lại **toàn bộ** node × tuyến ứng viên, kể cả node vừa bị quét hỏng ở lần trước mà lân cận không hề đổi.

**Vì sao cải thiện.** DLB là chuẩn trong tài liệu local search VRP: node bị đánh dấu "đã quét hỏng" chỉ được bật lại khi một lân cận của nó thay đổi. Thường cho 2–5× trên quét LS.

- **Runtime:** cao. **Chất lượng:** **phải đo** — DLB là cắt tỉa *heuristic*, có thể bỏ sót move.
- **Khó:** Trung bình. **Rủi ro:** trung bình — đây là mục Tầng A duy nhất **không** bit-identical.
- **Thí nghiệm:** bắt buộc qua **G3 iso-time**. Nếu G3 xấu đi thì bỏ, kể cả khi G2 rất đẹp — đúng bài học răng cưa.
- **Ablation:** DLB on/off, và biến thể "reset DLB mỗi N pass".

### A4 — Sum-tree cho Prioritized Replay Buffer

**Hiện trạng.** `PrioritizedReplayBuffer.sample` (`rl.py:57–59`) tính `probs = priorities[:n] ** alpha`, `probs /= sum`, rồi `np.random.choice(n, batch, p=probs)` — **O(buffer) mỗi lần lấy mẫu**, buffer 20 000 (plateau) / 30 000 (operator). Gọi mỗi 4 vòng lặp. `update_priorities` là vòng `for` Python.

**Vì sao cải thiện.** Sum-tree cho O(batch·log n) thay vì O(n). Đây là cách triển khai chuẩn của Schaul et al. mà mã hiện tại đang xấp xỉ bằng cách vét cạn.

- **Runtime:** trung bình (tỷ lệ chi phí RL trong tổng cần đo trước — thêm một mốc profiling nhỏ vào G2).
- **Chất lượng:** 0 kỳ vọng; **không** bit-identical (thứ tự lấy mẫu khác) nhưng tương đương về phân phối.
- **Khó:** Dễ. **Rủi ro:** thấp.

### A5 — Pha đuôi biết deadline

**Hiện trạng.** Đã đo: ở n=1000 **vượt ngân sách 8%** (648 s so với 600 s). Nguyên nhân xác định được trong mã: khối đuôi ở `solvers.py:1916` chỉ kiểm tra `_out_of_time()` **một lần lúc vào**, sau đó `_ejection_chain_eliminate` (:1940), `_buffered_route_elimination` (:1951), `_iterative_route_elimination` (:1957), `td_converge_polish` (:1987), `_local_search` (:1993) và `recombine_with_route_pool` (:2003) đều chạy **vô điều kiện**.

**Vì sao cải thiện.** Không sửa thì tuyên bố iso-time so với OR-Tools trong paper **không đứng vững** — phản biện sẽ bắt đúng chỗ này. Đồng thời dưới ngân sách cứng, việc phân bổ lại thời gian là thay đổi ảnh hưởng chất lượng thật.

- **Thay đổi mã:** chèn `if self._out_of_time(): ...` giữa các pha đuôi; truyền deadline xuống `td_converge_polish` để nó dừng giữa các pass.
- **Khó:** Dễ. **Rủi ro:** thấp (chỉ dừng sớm, không đổi logic).
- **Kiểm chứng:** chạy n=1000 với `--time-limit`, `Time_s` phải bám ngân sách trong ±2%.

### A6 — Tái dùng timing profile khi chèn tuần tự trong greedy repair

**Hiện trạng.** `op_greedy` và `op_tw_greedy` (`operators.py:510–525, 615–625`) chèn từng node qua `_insert_into_cheapest_route` (`heuristics.py:531`). Mỗi lần gọi lại `pack_routes` **toàn bộ** plan và `_best_insert_over_routes_numba` dựng lại `_route_timing_numba` cho **mọi tuyến** — trong khi giữa hai lần chèn liên tiếp chỉ **một tuyến** thay đổi. Với |removed| node, chi phí là O(|removed| × R × m) thay vì O(R × m + |removed| × m).

**Vì sao chắc chắn.** Chính `_regret` (`operators.py:523`) đã có sẵn khuôn mẫu đúng: dựng ma trận một lần bằng `_insert_costs_matrix_numba`, sau mỗi lần chèn chỉ refresh **một cột** bằng `_insert_costs_column_numba`. `op_greedy` chỉ cần tái dùng đúng bộ máy đó (chèn theo thứ tự cố định thay vì theo regret). Đây là lý do `_regret` đã đi từ 261 s → 12,6 s; `op_greedy`/`op_tw_greedy` là 2 trong 5 repair operator và chưa được hưởng gì.

- **Runtime:** cao — cùng bậc với cải tiến `_regret` trước đây. **Chất lượng:** 0 trực tiếp.
- **Khó:** Trung bình. **Rủi ro:** thấp — thứ tự chèn giữ nguyên → **bit-identical** với golden.
- **Kiểm chứng:** G1 bit-identical, G2 đo tăng tốc.

### A7 — Cache đặc trưng trạng thái RL theo danh tính `cur`

**Hiện trạng.** `_op_state` được gọi **mỗi vòng lặp** (`solvers.py:1555`, và lần hai cho `next_state` ở :1766) và mỗi lần gọi chạy 7 lượt quét toàn plan bằng Python thuần: `_gini_route_loads`, `_route_slack_stats`, `_fraction_at_capacity`, `_inter_route_dist_var` (vòng đôi O(R²)), `_plan_spread`, `_avg_slack`, `_fleet_fill`. Nhưng khi move bị **từ chối** — chiếm đa số vòng lặp — `cur` không đổi, chỉ các vô hướng (`it`, `temp`, `no_imp`) đổi. Toàn bộ 7 phép quét đó cho ra kết quả y hệt lần trước.

**Thay đổi mã:** cache tuple đặc trưng cấu trúc, khoá theo `id(cur)` (Plan bất biến sau khi gán vào `cur`); `_op_state`/`_state` chỉ lắp lại phần vô hướng.

- **Runtime:** trung bình-cao (tỷ lệ move bị từ chối càng cao càng lợi — đúng pha plateau vốn chiếm nhiều thời gian nhất). **Chất lượng:** 0 — giá trị đặc trưng **không đổi**, bit-identical.
- **Khó:** Dễ. **Rủi ro:** thấp; rủi ro duy nhất là dùng `id()` làm khoá khi object bị thu hồi — dùng thêm bộ đếm move đã chấp nhận làm khoá phụ.

### A8 — Sửa oversubscription luồng trong sweep sản xuất

**Hiện trạng.** `core.py:5–9` đặt `_N_PARALLEL = min(3, cpu//2)` → trên máy 12 nhân: `NUMBA_NUM_THREADS = OMP = MKL = 4`, torch = 2 luồng/worker (`rl.py:19`). Nhưng `benchmark.py:434` mặc định `os.cpu_count() - 1` = **11 worker**. Các worker spawn **kế thừa env của cha** (`setdefault` không ghi đè) → 11 worker × 4 luồng OMP/MKL + 11 × 2 luồng torch trên 12 nhân logic — oversubscription ~4× mỗi khi torch train hoặc BLAS chạy.

**Vì sao quan trọng cho cả hai mục tiêu.** (1) Tốc độ sweep: context-switch thay vì tính toán. (2) **Độ chính xác phép đo:** mọi `Time_s` trong sweep bị nhiễu bởi tranh chấp luồng không kiểm soát — ảnh hưởng trực tiếp tuyên bố iso-time và ngân sách anytime (deadline tính theo wall-clock nhưng tiến độ vòng lặp bị bóp méo).

**Thay đổi mã:** `run_benchmark.py` đặt tường minh `NUMBA_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` cho worker khi `max_workers > 1` (env truyền qua `mp_context`); kernel `@njit` ở đây đều tuần tự nên không mất gì.

- **Khó:** Dễ. **Rủi ro:** thấp. **Kiểm chứng:** chạy 2 instance H200 với cấu hình cũ/mới, so tổng wall và độ lệch chuẩn `Time_s` giữa các run cùng seed.

### B1 — Guided Ejection Search (⭐ ưu tiên chất lượng cao nhất)

**Hiện trạng.** `_try_buffered_route_elimination` (`local_search.py:824`) là beam search: sắp customer của tuyến mục tiêu, thử chèn, cho phép **một mức** ejection, dedup theo chữ ký, beam 8–16.

**Bốn thành phần của GES (Nagata & Bräysy 2009) đang thiếu hoàn toàn:**

1. **Ejection pool LIFO** — hiện dùng danh sách `pending` phẳng với heuristic chọn node cố định (`_select_buffered_pending_node`).
2. **Bộ đếm phạt `p[v]` theo từng customer** — hiện không có ký ức nào giữa các lần thử; customer khó luôn được xử lý y hệt.
3. **Chọn ejection cực tiểu hoá `Σp`** — hiện chọn theo `eject_score` dựa trên chi phí, không theo độ khó lịch sử.
4. **Pha nhiễu loạn (perturbation)** — hiện **không có**. Khi beam cạn thì bỏ cuộc. GES chèn các move relocate/exchange khả thi ngẫu nhiên rồi thử lại; đây chính là cơ chế giúp nó thoát chỗ mà beam search kẹt.

**Vì sao đây là mục đúng.** Dữ liệu của chính dự án nói rằng ALNS-Base và Hybrid-DDQN **hội tụ về cùng một sàn số xe** — nghĩa là dư địa còn lại nằm ở NV, và NV là mục tiêu từ vựng hạng nhất. GES là phương pháp cực tiểu số xe mạnh nhất trong tài liệu VRPTW. Nó **mở rộng** module route-elimination có sẵn, không thay ALNS.

- **Runtime:** **chậm hơn** — GES tốn thời gian. Vì vậy G3 iso-time là bắt buộc: phải chứng minh thời gian bỏ vào GES đáng giá hơn bỏ vào thêm vòng lặp ALNS.
- **Chất lượng:** cao nhất trong 20 mục, nhưng **chỉ trên NV**.
- **Khó:** Cao. **Rủi ro:** trung bình-cao (tốn thời gian, có thể thua iso-time).
- **Thay đổi mã:** hàm `_guided_ejection_search(plan, target_idx, ...)` mới trong `local_search.py`; gọi từ `_buffered_route_elimination` và từ `_committed_nv_search` (`solvers.py:1130`). Giữ nguyên đường cũ để ablation.
- **Ablation:** (a) không GES, (b) GES không perturbation, (c) GES không penalty counter, (d) GES đầy đủ. Bốn nhánh này tách bạch đóng góp của từng thành phần — chính là ablation mà paper cần.
- **Thống kê:** Wilcoxon trên NV, tách theo họ; báo cáo cả số lần chạm đúng NV của BKS.
- **Novelty:** trung bình như một *thành phần* (GES đã biết), nhưng **cao** ở đóng góp mới: *bộ điều khiển DDQN học khi nào nên gọi GES* — GES thành một mode/action trong khung có sẵn thay vì thủ tục cố định.

### B2 — SREX crossover thay crossover elite hiện tại

**Hiện trạng — gần như là lỗi.** `EliteArchive.crossover` (`rl.py:190–212`) lấy **nửa đầu** danh sách tuyến của p1 nguyên xi, quét p2 nhặt customer chưa dùng thành các tuyến rời rạc, rồi **dồn toàn bộ customer còn thiếu vào MỘT tuyến** sắp theo `ready_times` (dòng 206–207). Tuyến gộp đó gần như chắc chắn vi phạm tải trọng → `Plan` không khả thi → bị loại ở nơi gọi (`solvers.py:1682, 1686`). Nghĩa là crossover hiện **hầu như không bao giờ đóng góp gì**.

Đây đúng dạng lỗi đã bắt được ba lần trước (`op_fts_greedy` 0/60 khả thi, Homberger vắng mặt trong tập train GNN, GNN không chạy nổi n≥600): thành phần tồn tại trên giấy nhưng chưa từng chạy thật.

**Vì sao cải thiện.** SREX (Nagata) trao đổi *tập tuyến* giữa hai cha mẹ rồi sửa chữa bằng chèn lại có kiểm soát khả thi — thiết kế riêng cho VRPTW, giữ được cấu trúc tuyến thay vì phá nát.

- **Runtime:** trung tính. **Chất lượng:** trung bình. **Khó:** Trung bình. **Rủi ro:** thấp (hiện tại xấp xỉ bằng 0, khó tệ hơn).
- **Thí nghiệm bắt buộc trước tiên:** đếm số lần crossover trả về plan **khả thi** ở mã hiện tại. Nếu đúng ~0 thì con số đó tự nó là kết quả đáng báo cáo.
- **Ablation:** crossover cũ / SREX / tắt hẳn.

### B3 — Chọn cột SP theo đối ngẫu + cache lời giải

**Hiện trạng.** `_milp_recombine` (`pool.py:191`) cắt cứng `_MILP_MAX_COLS = 400`, lấy **400 bản ghi đầu** theo thứ tự ưu tiên tĩnh của `RoutePool._priority`. Không có tiêu chí đa dạng, không dùng thông tin đối ngẫu, và **không cache** — cùng một tập cột có thể được giải lại nhiều lần trong một lần chạy.

**Vì sao cải thiện.** Cắt theo chi phí giữ lại nhiều cột phủ gần trùng nhau; tập cột đa dạng hơn cho SP nhiều lựa chọn thật hơn ở cùng số cột. Giải nới lỏng LP một lần rồi xếp lại cột theo chi phí rút gọn là kỹ thuật chuẩn của generation cột và rất rẻ.

- **Runtime:** trung bình (cache tránh giải lại). **Chất lượng:** trung bình. **Khó:** Trung bình.
- **Thay đổi mã:** thêm cache theo hash tập cột trong `RoutePool`; thêm bước xếp hạng theo đối ngẫu trước khi cắt.
- **Thống kê:** so `sp_stats` (số lần gọi / timeout) và TD ở cùng số xe.

---

## Lộ trình thực thi

| Giai đoạn | Nội dung | Thời gian |
|---|---|---|
| **S0** | Hạ tầng: cờ `--time-limit`/`--no-time-limit`, `compare_sweeps.py`, `make_paper_tables.py`, mốc profiling cho G2 | ~2 h |
| **S1** | Tầng A (A1→A8). A1+A2 làm chung; A6 độc lập, có thể làm trước; A7, A8 rẻ nhất — làm đầu tiên. Sau mỗi mục: G1 → G2 → G3 | ~1,5 ngày |
| **S2** | Tầng B: B2 (rẻ, gần như lỗi) → B3 → B1 (đắt nhất, để cuối khi bench đã nhanh) | ~2–3 ngày |
| **S3** | Sàng Tầng C trên bench, **không cam kết**. Mục nào qua G3 mới đưa vào | ~4 h máy |
| **S4** | **Chốt tập cải tiến.** Chạy full test + golden, cập nhật golden có chủ đích | ~1 h |
| **S5** | Sweep giới hạn vòng lặp — Solomon (57 inst × 7 run × 5000 iter), H200 (60 × 5 × 800), H400 (24 × 3 × 600); 6 thuật toán `ALNS-Base ALNS-Base+ Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools`, OR-Tools ở 120 s, `--no-time-limit` → `results/rerun_iters/` | ~11 h |
| **S6** | Sweep giới hạn thời gian — H600/H800/H1000, ngân sách anytime mặc định (0,6 s × n) → `results/rerun_time/` | ~4,5 h |
| **S7** | Sinh 6 bảng LaTeX, cập nhật paper, `RERUN_CHECKLIST.md`, biên dịch PDF | ~3 h |

**Không dùng GNN trong sweep.** `run_full_production.sh` không truyền `--gnn-path`, và kiểm chứng cho thấy heatmap không cải thiện chất lượng (gap +0,22 pp, p=0,683). Báo cáo GNN riêng như kết quả **khả mở rộng** (1517 MB → 1,3 MB ở n=1000), không phải kết quả chất lượng.

**Tách giao thức theo shard là có chủ ý:** Solomon/H200/H400 giới hạn vòng lặp để so được với `results/ultimate-publication-suite/`; H600–1000 giới hạn thời gian vì đó là chỗ so iso-time với OR-Tools có ý nghĩa.

---

## Files sẽ sửa/tạo

| File | Nội dung |
|---|---|
| `src/vrptw/local_search.py` | A1 cache tăng dần, A2 bỏ set, A3 don't-look bits, B1 `_guided_ejection_search` |
| `src/vrptw/rl.py` | A4 sum-tree PER, B2 SREX crossover |
| `src/vrptw/solvers.py` | A5 pha đuôi biết deadline, A7 cache đặc trưng trạng thái, đấu nối B1 vào `_committed_nv_search` |
| `src/vrptw/operators.py` | A6 greedy repair dùng ma trận + refresh cột (tái dùng bộ máy của `_regret`) |
| `src/vrptw/pool.py` | B3 chọn cột theo đối ngẫu + cache |
| `docs/run_benchmark.py` | Cờ `--time-limit` / `--no-time-limit`; A8 pin 1 luồng/worker |
| `scripts/compare_sweeps.py` | **Mới** — Wilcoxon theo họ, TD-cùng-NV, đếm chạm sàn BKS |
| `scripts/make_paper_tables.py` | **Mới** — sinh LaTeX 6 bảng từ CSV |
| `docs/paper.tex` | 6 bảng (~672, 694, 729, 755, 780, 862), abstract (~80), runtime (~640), mô tả giao thức, mục GES mới |
| `docs/RERUN_CHECKLIST.md` | Đánh dấu hoàn thành + kết luận |
| `tests/golden/baseline.json` | Cập nhật có chủ đích sau S4 |

---

## Kiểm chứng

**Sau mỗi mục Tầng A/B:**
```powershell
python -m pytest tests/ -v --ignore=tests/e2e          # 44/44 xanh
python scripts/ab_compare.py run --out scratch/after.json
python scripts/ab_compare.py compare scratch/before.json scratch/after.json
```
A1, A2, A4, A6, A7 phải khớp golden **bit-identical**. A3, A5, B1, B2, B3 đổi quỹ đạo → bắt buộc qua G3 iso-time. A8 chỉ chạm cấu hình luồng của sweep, kiểm bằng độ lệch chuẩn `Time_s`.

**Trước sweep dài:**
```powershell
python docs\run_benchmark.py --instances R101 --runs 1 --algorithms Hybrid-DDQN --no-time-limit --hybrid-iters 500 --output-dir scratch\smoke_iters
python docs\run_benchmark.py --instances R101 --runs 1 --algorithms Hybrid-DDQN --time-limit 30 --output-dir scratch\smoke_time
```
`Time_s` trong `smoke_time` phải bám 30 s trong ±2% (đây chính là phép kiểm cho A5); `smoke_iters` không bị chặn.

**Sau mỗi sweep:** mọi shard hoàn thành (checkpoint đủ số combo), không dòng infeasible, H600/800/1000 có kết quả.

**Cuối cùng:** `pdflatex -interaction=nonstopmode -output-directory=docs docs/paper.tex` chạy sạch; bảng trong PDF khớp CSV do `make_paper_tables.py` sinh.

---

## Ràng buộc môi trường

- Máy: **12 nhân logic, 15,4 GB RAM**. `.venv/` là venv macOS — dùng `C:\Users\han\AppData\Local\Programs\Python\Python311\python.exe`.
- **Không có LaTeX** → sửa được `.tex` nhưng **không biên dịch được PDF**. Cần cài MiKTeX/TeX Live hoặc tự chạy `pdflatex`.
- `run_benchmark.py` có checkpoint/resume → ngắt giữa chừng an toàn.
- Không chạy sweep song song với đo bench: tranh CPU làm mọi số đo runtime vô nghĩa.

---

## Rủi ro đã biết

- **Tầng B có thể thua iso-time.** GES đắt; nếu thời gian bỏ vào GES kém hơn bỏ vào thêm vòng lặp ALNS thì nó rớt G3. Đó là kết quả hợp lệ và sẽ được báo cáo đúng như vậy, không chỉnh tham số cho tới khi ra số đẹp.
- **Tầng C nhiều khả năng rỗng.** Tỷ lệ trúng của dự án cho ý tưởng chất lượng đang là 0/4. Vì vậy Tầng C chỉ được sàng, không cam kết.
- **A1 rủi ro cache cũ** — lỗi im lặng, sai kết quả mà không báo. Golden fingerprint là lưới an toàn duy nhất; không được nới nó để "cho qua".
- **So với `results/ultimate-publication-suite/` là không ghép cặp** (seed/máy/thời điểm khác). Dùng để đối chiếu cho yên tâm. Khi tuyên bố mức cải thiện trong paper, **trích A/B ghép cặp**, không trích chênh lệch giữa hai sweep.
- **~16 h compute cho S5+S6**, ngắt được nhờ checkpoint nhưng cần máy chạy liên tục.

---

## Những gì đã chứng minh được (nền tảng, từ A/B ghép cặp 90 lần chạy)

| Cải tiến | Bằng chứng |
|---|---|
| **Nhanh 2,62×** | 1547,5 s → 590,2 s; nghiệm **giống hệt từng bit** nên không đánh đổi chất lượng |
| **Giảm số xe** | 13,400 → 13,289 khi tiêu tốc độ vào vòng lặp — **Wilcoxon p = 0,018** |
| **gap ở cùng số xe** | 3,55% → 3,12% (−0,43 pp) |
| **Bộ nhớ GNN n=1000** | 1517 MB → 1,3 MB; thời gian 3,96 s → 0,049 s |
| **3 lỗi thật đã sửa** | `op_fts_greedy` 0%→100% khả thi; Homberger vắng mặt trong tập train GNN; GNN không chạy nổi n≥600 |

Ở cùng số vòng lặp, chất lượng **không đổi** (gap 3,92% → 3,84%, p=0,419). Lợi ích chất lượng đến từ việc **tiêu tốc độ vào ngân sách tìm kiếm** — đó cũng là lý do Tầng A (thuần tốc độ) được xếp ưu tiên ngang Tầng B.
