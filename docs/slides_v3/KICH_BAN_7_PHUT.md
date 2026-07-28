# Kịch bản thuyết trình 7 phút — Hybrid DDQN-ALNS cho VRPTW

Kèm: nhận xét deck Canva hiện tại (17 slide) và những chỗ **phải** sửa.

---

## 1. Chia phút — 11 slide, 7:00 tổng

| # | Slide | Thời lượng | Mốc | Câu chốt phải nói được |
|---|-------|-----------:|-----|------------------------|
| 1 | Bìa | 0:20 | 0:00 | Tên đề tài + tên phương pháp. Không đọc lại slide. |
| 2 | **Bức tranh lớn** | 0:45 | 0:20 | Vấn đề → đóng góp → kết quả, trong 3 câu. |
| 3 | Bài toán & 3 ràng buộc | 0:35 | 1:05 | `min(NV ≫ TD)` — thứ tự ưu tiên là chìa khoá của cả bài. |
| 4 | Khoảng trống nghiên cứu | 0:25 | 1:40 | Chúng tôi **nhúng** RL vào ALNS, không thay thế ALNS. |
| 5 | Kiến trúc 3 khối | 0:45 | 2:05 | Quyết định → tìm kiếm → học, vòng khép kín. |
| 6 | Ba tầng L1/L2/L3 | 0:35 | 2:50 | L1 chọn chế độ, L2 chọn toán tử, L3 phá bế tắc. |
| 7 | Huấn luyện zero-shot | 0:20 | 3:25 | Học trên dữ liệu giả lập, **không** fine-tune trên bộ chuẩn. |
| 8 | Kết quả Solomon | 0:45 | 3:45 | 0.089 xe dư — 1/6 của OR-Tools; cùng số xe thì đường ngắn hơn. |
| 9 | Mở rộng & giới hạn | 0:30 | 4:30 | Càng lớn khoảng cách càng rộng; và nói thẳng giới hạn. |
| 10 | **DEMO** | 1:20 | 5:00 | Nạp → solve → so sánh → kiểm toán một tuyến. |
| 11 | Kết luận & Q&A | 0:30 | 6:20 | 4 đóng góp, 1 câu kết. |
| — | Đệm | 0:10 | 6:50 | Dự phòng cho lag máy/demo. |

**Ngân sách chữ:** ~120 từ/phút khi nói tiếng Việt có kiểm soát → cả bài ≈ 700–750 từ nói. Nếu bản nháp lời của bạn dài hơn 800 từ, chắc chắn sẽ tràn giờ.

---

## 2. Lời dẫn từng slide (đọc thử bấm đồng hồ)

**S1 — 20 giây.**
"Chúng tôi nghiên cứu bài toán định tuyến vận tải có khung thời gian, và đề xuất một kiến trúc lai giữa học tăng cường sâu và metaheuristic ALNS, gọi là Hybrid DDQN-ALNS."

**S2 — 45 giây.** *(slide dành cho người ngoài ngành — chậm lại ở đây)*
"Hình dung một kho của chuỗi siêu thị phải giao cho vài trăm cửa hàng trong một ngày. Mỗi cửa hàng chỉ nhận hàng trong một khung giờ hẹp. Câu hỏi kinh doanh rất đơn giản: cần bao nhiêu xe, và mỗi xe đi theo lộ trình nào.
Thuật toán tốt nhất hiện nay cho lớp bài toán này là ALNS. Nhưng ALNS chọn nước đi kế tiếp bằng một cơ chế gần như bốc thăm có trọng số — nó không biết mình đang ở đâu trong quá trình tìm kiếm. Đóng góp của chúng tôi là thay cơ chế bốc thăm đó bằng một tác nhân học tăng cường, biết đọc trạng thái để chọn nước đi.
Kết quả: trên bộ chuẩn quốc tế Solomon, số xe dư so với lời giải tốt nhất đã biết chỉ còn 0.089 — bằng một phần sáu của Google OR-Tools. Và khi so sánh công bằng ở cùng số xe, độ lệch quãng đường của chúng tôi thấp hơn 65%."

**S3 — 35 giây.**
"Về hình thức, đây là bài toán trên đồ thị: đỉnh 0 là kho, các đỉnh còn lại là khách hàng. Ba ràng buộc cứng: khung giờ, tải trọng xe, và giờ đóng kho.
Điểm quan trọng nhất là hàm mục tiêu — nó **có thứ tự**: giảm số xe trước, giảm quãng đường sau. Vì trong thực tế một chiếc xe là một tài xế, một khoản khấu hao, một khoản bảo trì — lớn hơn tiền xăng của vài chục km rất nhiều."

**S4 — 25 giây.**
"Có hai hướng tiếp cận sẵn có. ALNS cổ điển đảm bảo khả thi cứng và kiểm toán được, nhưng cận thị và dễ mắc bẫy plateau. Mạng nơ-ron đầu-cuối thì nhanh và học được cấu trúc, nhưng không cưỡng chế được thứ tự ưu tiên, và là hộp đen.
Chúng tôi không chọn bên nào. Chúng tôi nhúng policy học được vào **trong** vòng lặp ALNS."

**S5 — 45 giây.**
"Kiến trúc gồm ba khối. Khối quyết định gồm hai tác nhân DDQN phối hợp: một tác nhân macro — Plateau Controller — chọn chế độ tìm kiếm; một tác nhân micro — Operator Controller — chọn cặp toán tử trong chế độ đó.
Khối tìm kiếm là ALNS, cộng thêm mạng Learned Acceptance thay cho Simulated Annealing, và một bước tái hợp bằng MILP.
Khối thứ ba đóng vòng học: Route Pool, Replay Buffer ưu tiên, và Welford chuẩn hoá reward trực tuyến — đây là thứ giúp huấn luyện ổn định qua ba giai đoạn giáo trình."

**S6 — 35 giây.**
"Đi vào chi tiết ba tầng. L1 có sáu chế độ, trong đó Route-Reduce là chế độ chuyên đi triệt tiêu xe. L2 có 13 toán tử phá huỷ nhân 5 toán tử khôi phục — 65 cặp hành động. L3 là phần phá bế tắc: chuỗi đẩy liên hoàn, đẩy khách từ tuyến này sang tuyến khác theo dây chuyền để xoá hẳn một tuyến — điều mà Relocate hay Swap đơn lẻ không làm được dưới khung giờ khắt khe.
Về GNN heatmap, chúng tôi báo cáo thẳng: nó giảm bộ nhớ 1160 lần nhưng **không** cải thiện chất lượng, nên mọi kết quả sau đây không dùng nó."

**S7 — 20 giây.**
"Toàn bộ trọng số được huấn luyện trên dữ liệu giả lập sinh ngẫu nhiên, và chưa từng được tinh chỉnh trên Solomon hay Gehring–Homberger. Đây là chuyển giao zero-shot trên 164 instance chuẩn."

**S8 — 45 giây.**
"Bảng trái: số xe dư so với lời giải tốt nhất. OR-Tools 0.536, ALNS cổ điển 0.258, chúng tôi 0.089 — giảm 65% so với ALNS và 83% so với OR-Tools, đều có ý nghĩa thống kê theo kiểm định Wilcoxon.
Bảng phải quan trọng hơn về mặt phương pháp. Khi cắt xe, quãng đường **tăng** — đó là số học, không phải mất chất lượng. Nên so sánh quãng đường chỉ hợp lệ khi cùng số xe. Trên tập giao chặt 40 instance mà mọi phương pháp đều đạt đúng số xe, độ lệch của chúng tôi là 0.575% so với 1.642% của ALNS."

**S9 — 30 giây.**
"Mở rộng quy mô: khoảng cách so với OR-Tools ở cùng ngân sách thời gian tăng đơn điệu — 1.34 xe ở 400 khách, lên 9.45 xe ở 1000 khách.
Nhưng chúng tôi cũng nói thẳng ba giới hạn: từ 400 khách trở lên cả hai thuật toán đều còn xa BKS, nên đóng góp ở quy mô đó là tương đối; chúng tôi chậm hơn ALNS 2 đến 100 lần trên các instance mà ALNS dừng sớm; và GNN guidance không có tác dụng."

**S10 — 80 giây. DEMO.** *(xem checklist ở mục 4)*

**S11 — 30 giây.**
"Tóm lại: bốn đóng góp — MDP phân cấp, ngưỡng chấp nhận học được, cơ chế phá bế tắc khả thi, và một quy trình thực nghiệm nghiêm ngặt có báo cáo cả kết quả âm.
Một câu kết: chúng tôi giữ nguyên tính kiểm toán của tối ưu hoá cổ điển, và thêm vào tính thích ứng của học tăng cường. Cảm ơn thầy cô, em xin nhận câu hỏi."

---

## 3. Nhận xét deck Canva hiện tại

### 3.1 Ba lỗi phải sửa trước khi trình bày

**① Lỗi công thức LaTeX hiển thị thô.** Nhiều slide còn nguyên ký hiệu `$...$`:

| Slide | Chỗ lỗi | Sửa thành |
|---|---|---|
| 8 | `$\rightarrow$` trong ô Research Gap | `→` |
| 10 | `13 Phá hủy ... $\times$ 5 Khôi phục` | `×` |
| 11 | `$H_{ij}$`, `$(i,j)$`, `$u_1$`, `$R_2$`, `$R_3$`, `$NV$` | chữ thường + chỉ số dưới thật |
| 12 | `$N = 20 + 100$`, `$(E_1)$`, `$(E_2)$`, `$(E_3)$` | `N = 20…120`, `(GĐ 1)`… |
| 16 | `$\text{CO}_2$` | `CO₂` |

Đây là loại lỗi giám khảo thấy ngay từ xa và trừ điểm trình bày.

**② Slide 13 có một tuyên bố sai về mặt khoa học.** Ô xanh dưới cùng ghi:

> *"Phá kỷ lục BKS ở các tập khó: −1.50% tại RC1, −0.37% tại R1."*

Không đúng, và chính paper của bạn đã cảnh báo điều này (`docs/paper.tex`: *"Negative TD gaps … reflect vehicle over-allocation, not lexicographic improvement"*). Kiểm tra bằng số của chính slide đó:

| Lớp | Mean NV trên slide | Mean NV của BKS | Kết luận |
|---|---:|---:|---|
| R1 (12 instance) | 12.26 | **11.92** | dùng **nhiều xe hơn** BKS |
| RC1 (8 instance) | 11.98 | **11.50** | dùng **nhiều xe hơn** BKS |

Khi dùng nhiều xe hơn, quãng đường ngắn hơn là hệ quả số học — không phải kỷ lục. Nếu giám khảo biết VRPTW, đây là câu hỏi khó nhất bạn sẽ nhận và bạn sẽ không có cách trả lời.

→ **Thay bằng:** so sánh ở cùng số xe (tập giao chặt N = 40): `+0.575%` của Hybrid-DDQN so với `+1.642%` của ALNS. Đó mới là con số bảo vệ được, và nó vẫn rất đẹp.

**③ Số liệu slide 13/14 không khớp paper.** Slide 14 ghi `p = 0.00161` và `p = 0.000415`; paper ghi `p = 1.78×10⁻³` (NV vs ALNS), `p = 2.96×10⁻⁵` (NV vs OR-Tools), `p = 0.064` (TD vs Hybrid-Rule). Chọn **một** bộ số, ghi rõ đang so với ai và dưới protocol nào, rồi dùng nhất quán ở cả slide, poster và paper. Bị hỏi "số này ở bảng nào trong bài" mà không chỉ ra được là mất điểm nặng.

### 3.2 Vấn đề cấu trúc

- **5 slide (3–7) chỉ để mô tả bài toán** trong bài 7 phút là quá nhiều. Gộp còn 1–2 slide.
- **Không có slide demo.** Yêu cầu đề bài có demo mà deck không dành chỗ cho nó → chắc chắn cháy giờ.
- **Không có slide kết quả so sánh trực quan** với ALNS/OR-Tools. Slide 13 là bảng theo lớp dữ liệu, không phải so sánh đối thủ — người nghe không thấy được "hơn ở điểm nào".
- **Thiếu hẳn kết quả mạnh nhất của bạn:** khả năng mở rộng 400→1000 khách, hơn OR-Tools tới 9.45 xe ở cùng ngân sách thời gian. Đây là con số ấn tượng nhất trong cả bài mà deck không có.
- **Mục lục hứa "6. Kết luận & Đóng góp"** nhưng deck không có slide đó — slide 16 chỉ là "Tầm nhìn" (future work).
- **Slide 9 bị tràn:** ba cột module chạy quá đáy slide.
- **Thứ tự tác giả trên bìa** khác thứ tự trong `paper.tex` (paper: Huỳnh Nhật Huy, Nguyễn Nhật Huy, Nguyễn Thị Bảo Trân). Nên đồng bộ.

### 3.3 Điểm mạnh nên giữ

- Ba slide ràng buộc (4/5/6) dùng chung một hình isometric có highlight khoanh đỏ — cách kể chuyện tăng dần rất tốt. Bộ mới của mình gộp lại để tiết kiệm giờ, nhưng nếu bạn có 10 phút thì cách cũ hay hơn.
- Slide 7 (hàm mục tiêu, ưu tiên 1/ưu tiên 2 gắn với chi phí cố định/biến đổi) là slide giải thích tốt nhất trong deck cũ. Mình đã giữ nguyên ý này.
- Slide 14 (kiểm định thống kê tách riêng NV và TD) là điểm cộng — rất ít bài NCKH sinh viên có kiểm định.

### 3.4 Bonus — hai lỗi trong `docs/paper.tex`

Không thuộc phần slide nhưng sẽ vào PDF nếu không xoá:

1. Dòng ~122: `...coordinated DDQN agents.ư` — còn ký tự `ư` lạc.
2. Trong mục Introduction có một block markdown lạc: danh sách `**Contributions.**` lặp lại phần `\begin{itemize}` phía trên, kèm một đoạn `**Quiz**: Đoạn cuối Contributions nói về...` — đây là ghi chú làm việc, phải xoá.
3. Bảng ablation (`+0.275 → +0.084`, N=62) và bảng nv_summary (`0.258 → 0.089`, N=56 Solomon) là hai tập khác nhau. Nên ghi rõ ngay trong caption để không ai tưởng là số vênh nhau.

---

## 4. Checklist demo (80 giây, đã tính cả rủi ro)

| Bước | Việc làm | Giây |
|---|---|---:|
| 0 | **Trước khi lên:** server đã chạy, R101 đã nạp sẵn, browser zoom 125%, tab 2 mở video dự phòng | — |
| 1 | Nạp R101 (100 khách) — chỉ vào bản đồ, nói "mỗi điểm là một cửa hàng" | 15 |
| 2 | Bấm Solve — **im lặng 5 giây** cho khán giả thấy số xe tụt | 25 |
| 3 | Bật lớp ALNS cổ điển: 15 xe so với 14 xe của mình | 25 |
| 4 | Mở một tuyến, chỉ khung giờ + tải trọng: "mọi nước đi đều kiểm toán được" | 15 |

**Quy tắc cứng:** nếu tới giây thứ 20 mà solver chưa chạy → chuyển sang video ngay, không chờ. Chuẩn bị sẵn một câu: *"Để tiết kiệm thời gian em dùng bản ghi đã chạy trước."*

---

## 5. Chuẩn bị Q&A (5 câu dễ bị hỏi nhất)

1. **"Cùng số xe thì quãng đường tăng — vậy có phải tệ hơn không?"**
   → Không. Hàm mục tiêu có thứ tự: cắt một xe luôn đáng giá hơn vài phần trăm quãng đường. Và ở cùng số xe, chúng em vẫn ngắn hơn (0.575% so với 1.642%).

2. **"Vì sao không so với các solver SOTA như LKH-3 / HGS?"**
   → Nói thật: phạm vi hiện tại là so với ALNS cổ điển và OR-Tools ở cùng ngân sách thời gian, cộng ablation 5 điều kiện. So với SOTA là hướng tiếp theo.

3. **"Chậm hơn 100 lần thì dùng được trong thực tế không?"**
   → Định tuyến ngày mai được chạy tối nay: ngân sách vài phút. Cắt một xe tiết kiệm hàng chục triệu/tháng, đổi lấy 2 phút CPU là đáng.

4. **"GNN để làm gì nếu không cải thiện gì?"**
   → Đóng góp của nó là khả năng mở rộng (bộ nhớ giảm 1160 lần ở n=1000), không phải chất lượng. Chúng em báo cáo kết quả âm này thẳng và mọi số liệu chính đều không dùng GNN.

5. **"Zero-shot thật không, hay đã tinh chỉnh trên benchmark?"**
   → Thật. Trọng số chỉ huấn luyện trên đồ thị giả lập. Mỗi thuật toán chạy khởi động lạnh độc lập, archive xoá sạch, cache rỗng.

---

## 6. Cách dùng bộ slide mới

- `VRPTW_deck_7min.pdf` — 11 trang 16:9, trình bày trực tiếp được.
- `p01.png … p11.png` — ảnh 3200×1800, kéo thẳng vào Canva nếu bạn muốn giữ deck ở đó.
- `deck.py` + `deckkit.py` — nguồn dựng slide; sửa chữ/số rồi chạy lại `python3 deck.py` là ra bản mới.
- `DESIGN_PHILOSOPHY.md` — hệ thống thị giác (bảng màu, ba tầng chữ, quy tắc canh lề) nếu bạn cần thêm slide mà vẫn muốn đồng bộ.

Bảng màu: nền ngà `#F4F1EA`, mực `#12191F`, xám `#677178`, đỏ tín hiệu `#BD3E19`, xanh kết quả `#166659`.
Font: **Big Shoulders** (tiêu đề), **Work Sans** (thân), **IBM Plex Mono** (nhãn kỹ thuật) — cả ba đều Google Fonts, có sẵn trong Canva.
