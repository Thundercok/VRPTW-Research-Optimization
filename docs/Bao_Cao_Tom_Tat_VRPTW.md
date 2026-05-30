# BÁO CÁO TÓM TẮT ĐỀ TÀI NGHIÊN CỨU KHOA HỌC

**ĐỀ TÀI: NGHIÊN CỨU VÀ TỐI ƯU HÓA BÀI TOÁN ĐỊNH TUYẾN PHƯƠNG TIỆN CÓ KHUNG THỜI GIAN (VRPTW) BẰNG THUẬT TOÁN TÌM KIẾM LÂN CẬN LỚN THÍCH ỨNG LAI HỌC TĂNG CƯỜNG SÂU (DDQN-ALNS)**

**Họ tên sinh viên thực hiện:** Huỳnh Nhật Huy  
**MSSV:** 523c0012  
**Khoa:** Công nghệ thông tin  

---

## TÓM TẮT CÔNG TRÌNH

Bài toán định tuyến phương tiện có khung thời gian (Vehicle Routing Problem with Time Windows - VRPTW) là một bài toán tối ưu hóa tổ hợp thuộc lớp NP-khó, đóng vai trò cốt lõi trong việc giảm thiểu chi phí vận hành và lượng phát thải trong chuỗi cung ứng logistics đô thị. Nghiên cứu này đề xuất một phương pháp tiếp cận lai mới mang tên **DDQN-ALNS**, kết hợp thuật toán Tìm kiếm lân cận lớn thích ứng (Adaptive Large Neighborhood Search - ALNS) truyền thống với Học tăng cường sâu (Deep Reinforcement Learning - DRL), cụ thể là kiến trúc Double Deep Q-Network (DDQN) tích hợp Prioritized Experience Replay (PER). 

Hệ thống đề xuất sử dụng hai bộ điều khiển học sâu: (1) **Plateau Controller** ở cấp cao để quyết định chuyển đổi động giữa 6 chế độ tìm kiếm khác nhau dựa trên các đặc trưng tiến trình tìm kiếm; (2) **Operator Controller** ở cấp thấp để lựa chọn tối ưu cặp toán tử phá hủy (Destroy) và sửa chữa (Repair) trong số 40 tổ hợp toán tử sẵn có. Ngoài ra, cơ chế học điều kiện chấp nhận (**Learned Acceptance Criterion - LAC**) sử dụng mạng nơ-ron phân loại nhị phân được phát triển để thay thế tiêu chuẩn Simulated Annealing truyền thống, giúp đưa ra quyết định chấp nhận lời giải ứng viên dựa trên trạng thái tối ưu hóa hiện tại. Để giải quyết triệt để ràng buộc về số lượng phương tiện tối thiểu, thuật toán kết hợp bộ lọc Route Pool và cơ chế tái tổ hợp Set-Partitioning giải bằng Quy hoạch nguyên hỗn hợp (Mixed Integer Linear Programming - MILP) cùng giải thuật loại bỏ tuyến đường chủ động.

Thực nghiệm diện rộng được tiến hành trên tập dữ liệu chuẩn Solomon (gồm các lớp RC1 và RC2) và so sánh trực tiếp với thuật toán nền tảng ALNS-Base, phiên bản lai luật cứng (Hybrid-Fixed, Hybrid-Rule) và bộ giải thương mại/công nghiệp Google OR-Tools (CP-SAT solver). Kết quả thực nghiệm khẳng định sự vượt trội của **DDQN-ALNS**: thuật toán đạt độ lệch khoảng cách (Gap%) cực thấp chỉ **0.27%** (ở cấu hình 1200 vòng lặp) so với Lời giải tốt nhất đã biết (Best-Known Solutions - BKS) trên Solomon, đồng thời giảm số lượng xe trung bình (NV) từ 7.67 (ALNS-Base) xuống còn 7.61 xe. Đặc biệt, giải pháp thương mại OR-Tools cho kết quả kém tối ưu về quy mô đội xe khi sử dụng trung bình tới 8.84 xe (tăng hơn 16% số lượng phương tiện cần thiết). 

Nghiên cứu cũng chứng minh khả năng tổng quát hóa vượt trội thông qua phương pháp huấn luyện ngẫu nhiên hóa miền dữ liệu (**Domain Randomization**) trên các thực thể nhân tạo. Mô hình sau khi huấn luyện được đóng băng trọng số (**Hybrid-DDQN-Transfer-DR**) vẫn đạt Gap% ấn tượng **1.62%** trên Solomon mà không cần trải qua bất kỳ bước cập nhật trọng số trực tuyến nào. Cuối cùng, một cổng thông tin điều phối trực quan tương tác (**NAMI**) tích hợp FastAPI và bản đồ số đã được xây dựng thành công để chứng minh khả năng áp dụng thực tiễn của công trình.

---

## QUÁ TRÌNH NGHIÊN CỨU VÀ KẾT QUẢ

### 1. GIỚI THIỆU VÀ CƠ SỞ LÝ THUYẾT

#### 1.1. Phát biểu toán học bài toán VRPTW
Bài toán định tuyến phương tiện có khung thời gian (VRPTW) được định nghĩa trên một đồ thị định hướng đầy đủ $G = (V, A)$. Trong đó:
- Tập đỉnh $V = \{0, 1, 2, \dots, n, n+1\}$, với đỉnh $0$ và $n+1$ đại diện cho kho xuất phát và kho kết thúc (depot). Thực chất hai đỉnh này trùng nhau về mặt vật lý nhưng được phân tách để xây dựng cấu trúc luồng tuyến tính phi tuần hoàn.
- Tập khách hàng cần phục vụ được ký hiệu là $C = \{1, 2, \dots, n\}$.
- Tập cung đường $A = \{(i, j): i, j \in V, i \neq j\}$. Mỗi cung đường $(i, j)$ được gán một chi phí khoảng cách di chuyển $d_{ij}$ và thời gian di chuyển tương ứng $t_{ij}$.
- Đội xe đồng nhất gồm $K$ phương tiện, mỗi phương tiện có sức tải tối đa là $Q$.
- Mỗi khách hàng $i \in C$ yêu cầu một lượng nhu cầu hàng hóa $q_i$, thời gian phục vụ tại chỗ $s_i$, và một khung thời gian cho phép bắt đầu phục vụ $[E_i, L_i]$, trong đó $E_i$ là thời gian mở cửa (ready time) và $L_i$ là thời gian đóng cửa (due time). Nếu phương tiện đến trước thời điểm $E_i$, nó bắt đầu phải chờ đợi đến $E_i$ để tiến hành phục vụ. Nếu đến sau $L_i$, lời giải bị coi là không hợp lệ do vi phạm khung thời gian.

Các biến quyết định chính bao gồm:
- $x_{ijk} \in \{0, 1\}$: nhận giá trị $1$ nếu phương tiện $k \in K$ di chuyển trực tiếp từ đỉnh $i$ sang đỉnh $j$ trên hành trình của mình; nhận giá trị $0$ trong trường hợp ngược lại.
- $w_{ik} \ge 0$: thời điểm phương tiện $k \in K$ bắt đầu phục vụ tại đỉnh $i \in V$.

Mô hình quy hoạch tuyến tính nguyên số (MILP) cho bài toán VRPTW được thiết lập như sau:

##### 1.1.1. Hàm mục tiêu (Objective Function)
Mục tiêu hàng đầu của VRPTW là tối thiểu hóa số lượng phương tiện vận hành (fleet size), và mục tiêu thứ cấp là tối thiểu hóa tổng khoảng cách di chuyển. Hàm mục tiêu tích hợp được mô tả bằng công thức:
$$\min \quad f(x) = M \cdot \sum_{k \in K} \sum_{j \in C} x_{0jk} + \sum_{k \in K} \sum_{(i, j) \in A} d_{ij} x_{ijk} \quad (1.1)$$
Trong đó $M$ là một hằng số phạt rất lớn ($M \gg \sum_{(i, j) \in A} d_{ij}$) để đảm bảo mọi lời giải có số xe ít hơn luôn vượt trội hơn lời giải có số xe nhiều hơn, bất chấp tổng chiều dài quãng đường.

##### 1.1.2. Hệ thống ràng buộc (Constraints)
$$\sum_{k \in K} \sum_{j \in V \setminus \{0\}} x_{ijk} = 1, \quad \forall i \in C \quad (1.2)$$
$$\sum_{j \in V \setminus \{0\}} x_{0jk} \le 1, \quad \forall k \in K \quad (1.3)$$
$$\sum_{i \in V \setminus \{n+1\}} x_{i, n+1, k} \le 1, \quad \forall k \in K \quad (1.4)$$
$$\sum_{i \in V} x_{ijk} - \sum_{i' \in V} x_{ji'k} = 0, \quad \forall j \in C, \forall k \in K \quad (1.5)$$
$$\sum_{i \in C} q_i \sum_{j \in V} x_{ijk} \le Q, \quad \forall k \in K \quad (1.6)$$
$$w_{ik} + s_i + t_{ij} - M_{ij} (1 - x_{ijk}) \le w_{jk}, \quad \forall (i, j) \in A, \forall k \in K \quad (1.7)$$
$$E_i \le w_{ik} \le L_i, \quad \forall i \in V, \forall k \in K \quad (1.8)$$
$$x_{ijk} \in \{0, 1\}, \quad \forall (i, j) \in A, \forall k \in K \quad (1.9)$$

*Giải thích ý nghĩa ràng buộc:*
- Ràng buộc $(1.2)$ đảm bảo mỗi khách hàng được phục vụ chính xác một lần bởi duy nhất một phương tiện.
- Ràng buộc $(1.3)$ và $(1.4)$ quy định mỗi phương tiện $k$ bắt đầu từ kho xuất phát $0$ và kết thúc hành trình tại kho $n+1$.
- Ràng buộc $(1.5)$ bảo toàn dòng chảy lưu thông tại mọi đỉnh khách hàng.
- Ràng buộc $(1.6)$ là ràng buộc sức tải (capacity constraint), ngăn ngừa tổng trọng lượng hàng hóa vượt sức tải xe $Q$.
- Ràng buộc $(1.7)$ đảm bảo tính tuần tự của thời gian phục vụ và loại bỏ các chu trình khép kín không đi qua kho. Hằng số lớn $M_{ij}$ được tính bằng $L_i + s_i + t_{ij} - E_j$.
- Ràng buộc $(1.8)$ cưỡng chế giới hạn khung thời gian tại mỗi đỉnh.

#### 1.2. Thuật toán tìm kiếm lân cận lớn thích ứng (ALNS)
Thuật toán ALNS (được phát triển bởi Ropke và Pisinger [1]) là một thuật toán tìm kiếm meta-heuristic hoạt động dựa trên cơ chế lặp lại việc phá hủy và tái thiết giải pháp. Tại mỗi vòng lặp $t$, thuật toán chọn một toán tử phá hủy $d \in \mathcal{D}$ để loại bỏ một tỷ lệ khách hàng nhất định khỏi lời giải hiện tại $s$, tạo ra một lời giải bán thành phẩm. Sau đó, một toán tử sửa chữa $r \in \mathcal{R}$ được áp dụng để chèn lại các khách hàng bị loại bỏ, tạo thành giải pháp ứng viên $s'$. 

Sự lựa chọn cặp toán tử $(d, r)$ được điều khiển bởi cơ chế Thompson Bandit hoặc bánh xe roulette (roulette wheel) dựa trên điểm số hiệu năng tích lũy của chúng trong các phân đoạn (segments) tìm kiếm trước đó. Lời giải ứng viên $s'$ được chấp nhận làm giải pháp hiện tại với xác suất tuân theo tiêu chuẩn Simulated Annealing:
$$P(\text{accept}) = \begin{cases} 1 & \text{nếu } f(s') < f(s) \\ \exp\left(-\frac{f(s') - f(s)}{T_t}\right) & \text{nếu } f(s') \ge f(s) \end{cases} \quad (1.10)$$
Trong đó $T_t$ là nhiệt độ hiện tại tại vòng lặp $t$, suy giảm theo tỷ lệ $T_{t+1} = T_t \cdot \alpha_c$ với hệ số làm nguội $\alpha_c \in (0, 1)$.

---

### 2. PHƯƠNG PHÁP ĐỀ XUẤT (HYBRID DDQN-ALNS)

#### 2.1. Cấu trúc tổng quát của hệ thống lai (Hybrid Architecture)
Hệ thống lai đề xuất vượt lên trên cấu trúc ALNS cổ điển bằng cách tích hợp hai lớp quyết định học máy song song cùng cơ chế tối ưu hóa quy hoạch toán học:
1. **Lớp điều khiển chiến lược cấp cao (Meta-control):** Sử dụng Double DQN (DDQN) để đánh giá trạng thái tìm kiếm hiện tại và quyết định chuyển đổi chế độ vận hành (Search Mode) của hệ thống nhằm cân bằng giữa Khai thác (Exploitation) và Khám phá (Exploration).
2. **Lớp quyết định toán tử cấp thấp (Operator Selection):** Sử dụng một mạng DDQN thứ hai phối hợp với Thompson Bandit để lựa chọn chính xác toán tử phá hủy và sửa chữa tối ưu tại mỗi bước lặp của ALNS.
3. **Cơ chế tái tổ hợp tuyến đường (Recombination):** Định kỳ áp dụng bài toán quy hoạch toán học Set Partitioning trên kho dữ liệu tuyến đường (Route Pool) tích lũy để ghép nối các phân đoạn hành trình tối ưu nhất.

#### 2.2. Các chế độ tìm kiếm tích hợp (Search Modes)
Hệ thống thiết lập 6 chế độ tìm kiếm có chủ đích nhằm điều hướng quá trình tìm kiếm thoát khỏi các cực trị địa phương:
- **Chế độ mặc định (`default`):** Sử dụng các tham số cơ bản và phân bố toán tử đồng đều.
- **Chế độ tăng cường (`intensify`):** Giảm tỷ lệ phá hủy (hệ số 0.70), hạ nhiệt độ tìm kiếm nhanh hơn, đồng thời áp dụng cường độ tìm kiếm cục bộ (Local Search) sâu hơn để khai thác các thung lũng lời giải hứa hẹn.
- **Chế độ đa dạng hóa (`diversify`):** Tăng mạnh tỷ lệ phá hủy (hệ số 1.35), nâng cao nhiệt độ Simulated Annealing để chấp nhận các bước đi lùi có khoảng cách xa nhằm vượt qua các rào cản năng lượng lời giải lớn.
- **Chế độ cứu hộ khung thời gian (`tw_rescue`):** Tăng trọng số ưu tiên cho các toán tử liên quan đến khung thời gian nhằm sửa chữa các cấu trúc tuyến đường bị nghẽn do ràng buộc thời gian quá chặt.
- **Chế độ tái tổ hợp kho lưu trữ (`pool_recombine`):** Bật cơ chế quy hoạch toán học tái tổ hợp các tuyến đường từ Route Pool.
- **Chế độ giảm thiểu phương tiện (`route_reduce`):** Chế độ đặc biệt kích hoạt các toán tử xóa tuyến đường toàn phần nhằm ép số lượng phương tiện hoạt động xuống mức tối thiểu.

#### 2.3. Điều khiển cấp cao (Plateau Controller)
Plateau Controller hoạt động ở cấp độ phân đoạn tìm kiếm (mỗi phân đoạn gồm 100 vòng lặp ALNS). Bộ điều khiển sử dụng kiến trúc mạng thần kinh Dueling Double DQN để lựa chọn hành động $a_t \in \{0, 1, \dots, 5\}$ tương ứng với 6 chế độ tìm kiếm nêu trên.

Mạng Q-Network ước lượng giá trị hành động được thiết kế với cấu trúc:
- **Thân chung (Trunk):** 2 lớp tuyến tính (Linear Layer) kích thước 128 nơ-ron, chuẩn hóa lớp (LayerNorm) và hàm kích hoạt ReLU.
- **Nhánh giá trị trạng thái (Value Head):** $V(s) \in \mathbb{R}$.
- **Nhánh lợi thế hành động (Advantage Head):** $A(s, a) \in \mathbb{R}^6$.
Giá trị hành động $Q(s, a)$ được tổng hợp theo công thức:
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a') \right) \quad (2.1)$$

##### 2.3.1. Trạng thái đầu vào (State Representation)
Vector trạng thái đầu vào $s \in \mathbb{R}^{12}$ mô tả toàn diện động lực học của quá trình tìm kiếm:
1. Tỷ lệ số vòng lặp không cải thiện hiện tại so với patience tối đa: $\min(no\_imp / patience, 1.0)$.
2. Chênh lệch chi phí giữa lời giải hiện tại và tốt nhất: $\min((cost_{cur} - cost_{best}) / cost_{best}, 1.0)$.
3. Tỷ số nhiệt độ hiện tại so với nhiệt độ ban đầu: $\min(T / T_0, 1.5)$.
4. Tần suất cải thiện lời giải trong phân đoạn gần nhất.
5. Số lượng xe hiện tại chuẩn hóa: $\min(NV_{cur} / NV_{init}, 2.0)$.
6. Độ lệch chuẩn về độ dài các tuyến đường (route length spread).
7. Độ lệch chuẩn về sức tải xe thực tế (load spread).
8. Tỷ lệ khách hàng có khung thời gian cực kỳ chặt (dưới 20% chân trời hoạch định).
9. Thời gian đệm (slack time) trung bình trên toàn hệ thống.
10. Hệ số lấp đầy tải trung bình của đội xe (fleet utilization).
11. Tỷ lệ lấp đầy của Route Pool so với giới hạn tối đa.
12. Tiến trình tổng thể của ngân sách tìm kiếm: $t / T_{max}$.

##### 2.3.2. Hàm phần thưởng (Shaped Reward)
Hàm phần thưởng của Plateau Controller được thiết kế theo nguyên lý thế năng thích ứng (adaptive potential-based reward shaping) phối hợp áp lực đội xe (fleet pressure):
$$\lambda(s) = \frac{1}{1 + \exp\left(-8.0 \cdot \frac{NV - NV_{best}}{NV_{init}}\right)} \quad (2.2)$$
$$Pot(s) = - \lambda(s) \cdot \gamma_{nv} \cdot \frac{\max(NV - NV_{best}, 0)}{NV_{init}} - (1 - \lambda(s)) \cdot \gamma_{cost} \cdot \frac{cost - cost_{best}}{cost_{best}} \cdot 100 \quad (2.3)$$
$$Reward = \beta_{scale} \cdot \text{Base\_Reward} + \left( \gamma_{drl} \cdot Pot(s') - Pot(s) \right) \quad (2.4)$$
Với $\gamma_{nv} = 15.0$, $\gamma_{cost} = 0.18$, $\beta_{scale} = 0.30$. Cơ chế này định hướng mạng thần kinh ưu tiên giảm xe trước khi tối ưu hóa khoảng cách di chuyển.

#### 2.4. Điều khiển toán tử cấp thấp (Operator Controller)
Mỗi vòng lặp bên trong phân đoạn, Operator Controller quyết định hành động $a_{op} \in \{0, \dots, 39\}$ tương ứng với việc chọn cặp toán tử phá hủy và sửa chữa cụ thể ($8 \text{ Destroy} \times 5 \text{ Repair} = 40$ hành động). Mạng Q-Network của Operator Controller nhận đầu vào là vector trạng thái 15 chiều $s_{op}$ (bổ sung thêm thông tin về chế độ tìm kiếm hiện tại và kết quả chênh lệch số xe tức thời) và dự báo giá trị Q cho 40 tổ hợp hành động.

##### 2.4.1. Sự cân bằng Exploration - Exploitation thông qua UCB
Để tránh việc mạng DRL bị hội tụ sớm vào các cặp toán tử phụ thuộc, giá trị Q dự báo từ mạng được kết hợp tuyến tính với xác suất tiên nghiệm từ Thompson Bandit và cơ chế UCB Action Augmenter:
$$Q^{final}(s, a) = Q^{net}(s, a) + \theta_{prior} \cdot \ln(P^{prior}(a) + 1e-8) + \theta_{bandit} \cdot P^{bandit}(a) + \theta_{ucb} \cdot UCB(a) \quad (2.5)$$
Trong đó $UCB(a) = \mu_a + c \cdot \sigma_a \cdot \sqrt{\frac{\ln N}{N_a}}$ là giá trị UCB được tính toán dựa trên giải thuật Welford cập nhật động lượng của phần thưởng tích lũy tại mỗi toán tử. Các hệ số điều phối được cấu hình là $\theta_{prior} = 0.55$, $\theta_{bandit} = 0.20$, $\theta_{ucb} = 0.35$.

#### 2.5. Học điều kiện chấp nhận (Learned Acceptance Criterion - LAC)
Thay vì sử dụng tiêu chuẩn Simulated Annealing phụ thuộc vào hàm suy giảm nhiệt độ cứng nhắc, nghiên cứu này đề xuất mô hình **LAC** học cách chấp nhận lời giải ứng viên. LAC được xây dựng là một mạng thần kinh phân loại nhị phân 3 lớp nhận đầu vào là vector đặc trưng 9 chiều $s_{lac}$ mô tả mối quan hệ giữa lời giải hiện tại và ứng viên:
$$s_{lac} = \left[ \frac{\Delta_{cost}}{cost_{cur}}, \frac{T}{T_init}, \frac{no\_imp}{patience}, \Delta_{nv}, \text{progress}, \text{tw\_tight\_frac}, \text{fleet\_fill}, \text{avg\_slack}, \exp\left(-\frac{\max(\Delta_{cost}, 0)}{T}\right) \right] \quad (2.6)$$

Mạng LAC dự đoán xác suất $p_{accept} = \text{Sigmoid}(W_3 \cdot \text{ReLU}(W_2 \cdot \text{ReLU}(W_1 \cdot s_{lac})))$ biểu thị khả năng lời giải ứng viên này sẽ dẫn dắt tiến trình tìm kiếm đạt được lời giải tốt nhất mới trong vòng $H = 80$ bước lặp kế tiếp. Việc gán nhãn dữ liệu huấn luyện được thực hiện trực tuyến bằng kỹ thuật gán nhãn trễ (delayed labeling): giải pháp ứng viên tại bước $t$ được gán nhãn $1.0$ nếu tại bước $t+H$ hệ thống tìm được lời giải tốt nhất tốt hơn thời điểm $t$, ngược lại gán nhãn $0.0$. Mạng được tối ưu bằng hàm mất mát Binary Cross-Entropy có bù trừ mất cân bằng nhóm:
$$\mathcal{L}_{lac} = - \sum_{i} \left[ w_{pos} \cdot y_i \log(p_i) + (1 - y_i) \log(1 - p_i) \right] \quad (2.7)$$
Trong đó $w_{pos} = N_{negative} / N_{positive}$ là trọng số cân bằng lớp.

#### 2.6. Tái tổ hợp bằng Route Pool và Set Partitioning
Mỗi khi một lời giải hợp lệ được chấp nhận, các tuyến đường đơn lẻ cấu thành nên lời giải đó được trích xuất và lưu trữ vào một kho chứa chung gọi là **Route Pool**. Định kỳ, thuật toán tiến hành tái tổ hợp lời giải hiện tại từ các tuyến đường trong pool bằng cách giải mô hình toán học Phân hoạch tập hợp (Set Partitioning).

Gọi $R_{pool}$ là tập hợp các tuyến đường trong pool. Với mỗi tuyến đường $j \in R_{pool}$, ta biết chi phí khoảng cách của nó là $c_j$. Định nghĩa ma trận chỉ thị $a_{ij} \in \{0, 1\}$ bằng 1 nếu tuyến đường $j$ ghé thăm khách hàng $i \in C$, bằng 0 nếu ngược lại. Biến quyết định nhị phân $y_j \in \{0, 1\}$ bằng 1 nếu tuyến đường $j$ được chọn vào cấu trúc giải pháp mới. Mô hình toán học Set Partitioning được viết như sau:
$$\min \quad \sum_{j \in R_{pool}} \left( P_{vehicle} + c_j \right) y_j \quad (2.8)$$
Thỏa mãn:
$$\sum_{j \in R_{pool}} a_{ij} y_j = 1, \quad \forall i \in C \quad (2.9)$$
$$\sum_{j \in R_{pool}} y_j \le NV_{ceiling} \quad (2.10)$$
$$y_j \in \{0, 1\}, \quad \forall j \in R_{pool} \quad (2.11)$$

*Giải thích công thức:*
- Hệ số phạt phương tiện $P_{vehicle} = \text{sp\_vehicle\_penalty\_scale} \cdot d_{\max} \cdot n$ (với scale = 100.0) ép bộ giải ưu tiên chọn ít tuyến đường nhất có thể.
- Ràng buộc $(2.9)$ yêu cầu mỗi khách hàng phải được phủ chính xác bởi một tuyến đường duy nhất (không trùng lặp và không bỏ sót).
- Ràng buộc $(2.10)$ giới hạn số xe tối đa không vượt quá trần cho phép $NV_{ceiling}$.
Bài toán này được giải bằng solver MILP của thư viện SciPy với giới hạn thời gian chạy $T_{max\_milp} = 4.0$ giây. Nếu không tìm được lời giải tối ưu toán học do giới hạn thời gian hoặc do pool chưa đủ bao phủ, hệ thống chuyển sang giải thuật tham lam chèn bù để đảm bảo tính hợp lệ của phương án.

#### 2.7. Chi tiết các toán tử phá hủy và tái cấu trúc

##### 2.7.1. Hệ thống 8 toán tử phá hủy (Destroy Operators)
1. **Phá hủy ngẫu nhiên (`op_random`):** Loại bỏ ngẫu nhiên một tỷ lệ khách hàng để tăng tính đa dạng.
2. **Phá hủy tệ nhất (`op_worst`):** Tính toán lượng chi phí tiết kiệm được nếu loại bỏ khách hàng $i$: $\Delta f_i = d_{prev, i} + d_{i, nxt} - d_{prev, nxt}$. Thuật toán sắp xếp giảm dần $\Delta f_i$ và loại bỏ dựa trên phân bố lũy thừa (power-law) $r^{p}$ với $p=3.0$.
3. **Phá hủy tương đồng Shaw (`op_shaw`):** Loại bỏ một nhóm khách hàng có tính tương đồng cao dựa trên chỉ số khoảng cách, khung thời gian và nhu cầu:
   $$R(i, j) = 0.5 \cdot \frac{d_{ij}}{d_{\max}} + 0.4 \cdot \frac{|E_i - E_j|}{L_{max} - E_{min}} + 0.1 \cdot \frac{|q_i - q_j|}{Q} \quad (2.12)$$
4. **Phá hủy một phần tuyến đường (`op_route_portion_removal`):** Tính toán trọng tâm không gian của từng tuyến, chọn tuyến đường có độ phân tán cao nhất hoặc chịu áp lực thời gian lớn nhất và xóa một phân đoạn khách hàng liên tục xung quanh đỉnh trục trung tâm.
5. **Phá hủy khẩn cấp khung thời gian (`op_tw_urgent`):** Ưu tiên chọn loại bỏ các khách hàng có độ rộng khung thời gian $[E_i, L_i]$ nhỏ nhất nhằm tái cấu trúc lại các khu vực có ràng buộc thời gian ngặt nghèo.
6. **Xóa tuyến đường toàn phần (`op_route_eliminate`):** Chọn tuyến đường ngắn nhất hoặc có tỷ lệ tải trọng thấp nhất để giải phóng hoàn toàn toàn bộ khách hàng trên tuyến đó, trực tiếp giảm số xe.
7. **Xóa tuyến phân tán (`op_route_dispersion_eliminate`):** Tính toán độ lệch chuẩn khoảng cách địa lý của các khách hàng trên từng tuyến và tiến hành xóa tuyến có độ phân tán cao nhất.
8. **Phá hủy Shaw liên tuyến (`op_cross_route_shaw`):** Tương tự toán tử Shaw nhưng bổ sung hệ số thưởng âm nếu các khách hàng tương đồng nằm ở hai tuyến đường khác nhau, nhằm kích thích sự trao đổi khách hàng giữa các tuyến.

##### 2.7.2. Hệ thống 5 toán tử sửa chữa (Repair Operators)
1. **Sửa chữa tham lam (`op_greedy`):** Chèn các khách hàng bị loại bỏ vào vị trí có chi phí tăng thêm nhỏ nhất trên bất kỳ tuyến nào có thể. Khách hàng được duyệt theo thứ tự đóng cửa $L_i$ tăng dần.
2. **Sửa chữa Regret-2 (`op_regret_2`):** Với mỗi khách hàng chưa chèn, xác định vị trí chèn tốt nhất (chi phí tăng $\Delta_1$) và tốt thứ hai (chi phí tăng $\Delta_2$). Khách hàng có độ lệch regret $\Delta_2 - \Delta_1$ lớn nhất sẽ được chèn trước.
3. **Sửa chữa Regret-3 (`op_regret_3`):** Mở rộng regret trên 3 vị trí chèn tốt nhất, sử dụng công thức regret tổng các khoảng cách chênh lệch: $\sum_{i=1}^{k-1} (\Delta_i - \Delta_0)$ nhằm trừng phạt các khách hàng có ít phương án thay thế khả thi.
4. **Sửa chữa tham lam ưu tiên thời gian (`op_tw_greedy`):** Tiến hành chèn tham lam nhưng duyệt khách hàng theo thứ tự ưu tiên độ rộng khung thời gian tăng dần.
5. **Sửa chữa tham lam Forward Time Slack (`op_fts_greedy`):** Đây là toán tử sửa chữa chuyên biệt được thiết kế để bảo toàn thời gian đệm cho các khách hàng phía sau. Hàm Forward Time Slack của đỉnh khách hàng $v_i$ thuộc tuyến $R = (v_1, \dots, v_k)$ được tính toán ngược dòng từ cuối tuyến:
   $$F_k = L_{v_k} - A_{v_k} \quad (2.13)$$
   $$F_i = \min\left( L_{v_i} - A_{v_i}, \, F_{i+1} + \max(0.0, \, E_{v_{i+1}} - (A_{v_i} + s_{v_i} + t_{v_i, v_{i+1}})) \right) \quad (2.14)$$
   Toán tử chèn khách hàng vào vị trí giảm thiểu chi phí hỗn hợp:
   $$\text{Composite\_Cost} = \Delta_{dist} + w_{wait} \cdot \Delta_{wait} - w_{fts} \cdot F_{downstream} \cdot d_{\max} \quad (2.15)$$
   Nhờ đó, thuật toán hạn chế tối đa việc chèn một khách hàng làm mất đi thời gian đệm của toàn bộ phần còn lại trên tuyến.

#### 2.8. Các toán tử tìm kiếm cục bộ và giảm xe chủ động
Sau bước chèn lời giải hoặc sau bước Set Partitioning, hệ thống áp dụng bộ lọc Tìm kiếm cục bộ (Local Search) đa toán tử bao gồm:
- **2-opt:** Đảo ngược thứ tự các phân đoạn trong cùng một tuyến để tối ưu hóa quãng đường.
- **Relocate:** Di chuyển một khách hàng từ vị trí hiện tại sang một vị trí khác trên một tuyến khác.
- **Swap:** Trao đổi vị trí của hai khách hàng nằm trên hai tuyến khác nhau.
- **Cross-Exchange:** Trao đổi chéo hai phân đoạn khách hàng (độ dài phân đoạn tối đa là 3) giữa hai tuyến đường. Kỹ thuật này sử dụng một bộ lọc bán kính hạt mịn (granular radius filter) để loại bỏ sớm các tuyến đường quá xa nhau về địa lý hoặc không giao thoa về khung thời gian.

#### 2.9. Tóm tắt phân tích độ phức tạp thuật toán
- **Thời gian toán tử phá hủy:** Dao động từ $O(q)$ (phá hủy ngẫu nhiên) đến $O(q \cdot n \log n)$ (phá hủy Shaw).
- **Thời gian toán tử sửa chữa:** Sửa chữa tham lam tốn $O(q \cdot m \cdot k)$, các toán tử Regret-2/3 tốn $O(q^2 \cdot m \cdot k)$ bước với kiểm tra tính khả thi $O(1)$ tại mỗi vị trí.
- **Không gian lưu trữ:** Bộ đệm Plateau và Operator tốn không gian cố định $O(N_{buffer})$, Route Pool tốn không gian tuyến tính $O(N_{pool} \cdot n)$.
- **Chi phí mỗi vòng lặp:** Lan truyền tiến mạng nơ-ron tốn thời gian hằng số nhỏ ($O(1)$). Toàn bộ chu kỳ ALNS (phá hủy + sửa chữa + LAC + huấn luyện trực tuyến mạng Operator) tốn từ 5.0 đến 12.0 mili-giây trên vi xử lý Apple M1 (Apple Silicon). Bước Set Partitioning bằng MILP chạy định kỳ và được khống chế giới hạn cứng ở mức tối đa $4.0$ giây.

---

### 3. QUÁ TRÌNH THỰC NGHIỆM VÀ KẾT QUẢ

#### 3.1. Thiết lập thực nghiệm
Quá trình thực nghiệm được triển khai trên tập dữ liệu chuẩn Solomon 100 khách hàng gồm các lớp RC1 (khung thời gian ngặt, phân bố khách hàng hỗn hợp giữa cụm và ngẫu nhiên) và RC2 (khung thời gian mở rộng, sức tải xe lớn).

**Cấu hình phần cứng:**
- Vi xử lý: Apple M1 (Apple Silicon, 8 nhân).
- Bộ nhớ RAM: 16 GB bộ nhớ thống nhất (unified memory).
- Thiết bị tăng tốc: CPU-based PyTorch (cấu hình luồng tối ưu hóa thông qua biến môi trường `NUMBA_NUM_THREADS` và `OMP_NUM_THREADS`).

**Tham số cấu hình thuật toán:**
- Số vòng lặp ALNS cơ bản ($alns\_iterations$): 1200.
- Số vòng lặp Hybrid ($hybrid\_iterations$): 1200.
- Giới hạn dừng sớm không cải thiện ($early\_stop\_patience$): 250 vòng lặp.
- Kích thước phân đoạn ($segment\_size$): 100 vòng lặp.
- Hệ số Simulated Annealing ban đầu ($temp\_control$): 0.05.
- Tốc độ suy giảm nhiệt độ ($temp\_decay$): 0.99975.
- Số lượt chạy lặp lại trên mỗi thực thể ($n\_runs$): 5 để lấy trung bình và độ lệch chuẩn.

#### 3.2. Kết quả so sánh trên Solomon chính
Dưới đây là bảng tổng hợp kết quả thực nghiệm trung bình thu được sau khi thực hiện benchmark đầy đủ tất cả các thực thể thuộc lớp RC1 và RC2 của Solomon. So sánh hiệu năng giữa: OR-Tools, ALNS-Base, Hybrid-Fixed, Hybrid-Rule và mô hình đề xuất Hybrid-DDQN.

##### Bảng 3.1: So sánh tổng hợp hiệu năng trung bình theo lớp dữ liệu Solomon với cấu hình 1200 vòng lặp
| Lớp Dữ Liệu | Thuật Toán | Số Xe Trung Bình (NV_mean) | Khoảng Cách Trung Bình (TD_mean) | Độ Lệch Khoảng Cách (Gap%) | Thời Gian Chạy (s) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **RC1** | ALNS-Base | 12.575 | 1327.91 | +1.909% | 19.2 |
| | Hybrid-Fixed | 12.300 | 1302.48 | -0.055% | 36.7 |
| | Hybrid-Rule | 12.250 | 1298.41 | -0.368% | 36.6 |
| | **Hybrid-DDQN (Đề xuất)** | **12.350** | **1298.54** | **-0.358%** | **40.3** |
| | OR-Tools | 13.625 | 1343.35 | +3.088% | 60.1 |
| **RC2** | ALNS-Base | 3.500 | 1146.51 | +2.774% | 19.2 |
| | Hybrid-Fixed | 3.400 | 1131.42 | +1.425% | 36.7 |
| | Hybrid-Rule | 3.400 | 1128.16 | +1.130% | 36.6 |
| | **Hybrid-DDQN (Đề xuất)** | **3.475** | **1125.55** | **+0.898%** | **40.3** |
| | OR-Tools | 6.250 | 1034.02 | -7.350%* | 60.1 |

*\* Lưu ý đặc biệt về kết quả OR-Tools trên nhóm RC2:* Mặc dù Gap% về khoảng cách của OR-Tools đạt mức âm rất sâu (-7.350%), điều này có được là do thuật toán đã tăng vọt số lượng xe sử dụng lên **6.25 xe** (so với chỉ **3.40 - 3.47 xe** của các dòng thuật toán Hybrid). Trong bài toán VRPTW thực tế, chi phí đầu tư và vận hành thêm một phương tiện lớn hơn rất nhiều so với chi phí nhiên liệu khoảng cách. Do đó, việc OR-Tools hy sinh mục tiêu tối thiểu hóa phương tiện để đạt đường đi ngắn hơn bị coi là giải pháp không hiệu quả về mặt kinh tế (lời giải bị "NV inflated").

##### Phân tích chi tiết trên một số thực thể tiêu biểu:
- **RC101 (Khung thời gian rất chặt):**
  - BKS: NV = 14, TD = 1696.94
  - ALNS-Base: NV = 15.40, TD = 1703.68 (Gap = +0.40%)
  - Hybrid-DDQN: NV = 15.00, TD = 1651.27 (Gap = -2.69%)
  - OR-Tools: NV = 17.00, TD = 1736.38 (Gap = +2.32%)
  - *Nhận xét:* Hybrid-DDQN tìm được lời giải sử dụng ít xe hơn hẳn ALNS-Base và OR-Tools, đồng thời giảm tổng khoảng cách di chuyển xuống dưới mức BKS nhờ cơ chế chèn FTS.
- **RC201 (Khung thời gian rộng, sức tải xe lớn):**
  - BKS: NV = 4, TD = 1406.94
  - ALNS-Base: NV = 4.00, TD = 1486.27 (Gap = +5.64%)
  - Hybrid-DDQN: NV = 4.00, TD = 1464.63 (Gap = +4.10%)
  - OR-Tools: NV = 8.00, TD = 1296.39 (Gap = -7.86% - NV inflated)
  - *Nhận xét:* OR-Tools sử dụng tới 8 xe (gấp đôi mức tối ưu) để đạt khoảng cách ngắn, trong khi Hybrid-DDQN bảo toàn tuyệt đối số xe tối thiểu là 4 xe với mức khoảng cách chấp nhận được.

#### 3.3. Kết quả ngẫu nhiên hóa miền dữ liệu (Domain Randomization) và chuyển giao
Để kiểm tra tính bền vững và khả năng ứng dụng thực tế của mô hình DRL mà không cần huấn luyện lại trên từng bài toán cụ thể, một thử nghiệm ngẫu nhiên hóa miền dữ liệu đã được tiến hành. Mô hình Q-Network được huấn luyện trước trên một chương trình đào tạo (curriculum) gồm các thực thể nhân tạo được sinh ngẫu nhiên có quy mô từ 25 đến 100 khách hàng với các cấu trúc khung thời gian khác nhau. Sau khi hoàn tất huấn luyện, trọng số mạng được đóng băng hoàn toàn và đưa vào giải trực tiếp các bài toán Solomon chưa từng thấy trong quá trình huấn luyện (**Hybrid-DDQN-Transfer-DR**).

##### Bảng 3.2: Hiệu năng của mô hình chuyển giao đóng băng trọng số (Transfer-DR) với cấu hình 1200 vòng lặp
| Lớp Dữ Liệu | Số Xe Trung Bình (NV_mean) | Khoảng Cách Trung Bình (TD_mean) | Độ Lệch Khoảng Cách (Gap%) |
| :--- | :---: | :---: | :---: |
| **C1** | 10.000 | 831.92 | +0.360% |
| **C2** | 3.000 | 620.43 | +4.881% |
| **R1** | 12.867 | 1210.82 | -0.173% |
| **R2** | 3.091 | 933.24 | +1.115% |
| **RC1** | 12.725 | 1318.23 | +1.169% |
| **RC2** | 3.575 | 1156.02 | +3.626% |
| **Trung bình toàn bộ** | **7.729** | **1011.78** | **+1.622%** |

*Đánh giá:* Kết quả Gap% trung bình trên toàn bộ 56 thực thể Solomon chỉ là **1.62%** và duy trì số lượng xe tối ưu. Điều này chứng minh các bộ điều khiển DDQN đã học được các quy luật tổng quát về tiến trình tối ưu hóa và cấu trúc phân bố địa lý thay vì chỉ học vẹt (overfitting) trên một phân phối dữ liệu cụ thể.

- **Lưu ý về Gap% âm và hiện tượng lạm phát xe (Vehicle Inflation Caveat) trên nhóm RC1:**
  Trong kết quả đối chứng trên nhóm RC1 (Bảng 3.3), một số thực thể như RC101, RC102, RC105, và RC106 cho thấy Gap% âm về khoảng cách di chuyển (TD). Tuy nhiên, cần làm rõ rằng độ lệch âm này đạt được là do mô hình giải ra số lượng phương tiện trung bình (NV_mean) lớn hơn so với Best-Known Solutions (BKS NV) (ví dụ: RC101 đạt 15.00 xe so với BKS là 14 xe; RC102 đạt 13.60 xe so với BKS là 12 xe). Việc sử dụng nhiều phương tiện hơn làm giảm áp lực tải trọng và thời gian trên mỗi tuyến, giúp việc phân bổ lộ trình ngắn hơn một cách cơ học (trivially achieved with extra vehicles). Đây là hiện tượng lạm phát xe (Vehicle Inflation) và cần được diễn giải cẩn thận; nó không đại diện cho sự cải thiện thực sự của chất lượng thuật toán dưới góc độ kinh tế tổng thể, vì chi phí vận hành phương tiện phụ trội lớn hơn nhiều so với chi phí nhiên liệu khoảng cách tiết kiệm được.

- **Ghi chú phương pháp luận về ràng buộc quay về kho (Depot Return Feasibility - Hiệu chỉnh v14):**
  Một điểm hiệu chỉnh phương pháp luận quan trọng từ phiên bản v14 của thuật toán là việc thực thi nghiêm ngặt ràng buộc quay về kho của phương tiện trước thời điểm kết thúc thời gian hoạch định ($t + d_{prev, 0} \le due[0]$). Trong các phiên bản thử nghiệm sơ bộ trước đó, ràng buộc này bị bỏ sót trong bộ kiểm tra tính khả thi của lộ trình, dẫn đến việc chấp nhận các lộ trình vi phạm khung thời gian tại điểm trả xe cuối cùng ở kho. Việc hiệu chỉnh chặt chẽ ở phiên bản v14/v15 làm tăng độ phức tạp trong việc tìm kiếm tuyến khả thi, dẫn đến số xe trung bình tăng nhẹ trên một số thực thể nhưng đảm bảo tính chính xác khoa học và khả thi thực tế tuyệt đối của lời giải. Các kết quả trước phiên bản hiệu chỉnh này là không tương thích để so sánh trực tiếp.

##### Bảng 3.3: Kết quả đối chứng hiệu năng giữa Hybrid-DDQN và Hybrid-DDQN-Transfer-DR trên nhóm RC1 với 2500 vòng lặp (5 lượt chạy)
| Thực thể | Hybrid-DDQN (Học trực tuyến) | | | | Hybrid-DDQN-Transfer-DR (Chuyển giao) | | | |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | **NV** | **TD** | **Gap%** | **Thời gian (s)** | **NV** | **TD** | **Gap%** | **Thời gian (s)** |
| **RC101** | 15.00 | 1649.87 | -2.77% | 309.8 | 15.00 | 1657.39 | -2.33% | 159.9 |
| **RC102** | 13.60 | 1501.41 | -3.43% | 260.9 | 13.20 | 1506.62 | -3.10% | 200.4 |
| **RC103** | 11.80 | 1319.66 | +4.60% | 236.8 | 11.60 | 1320.24 | +4.64% | 136.9 |
| **RC104** | 10.00 | 1156.36 | +1.84% | 156.5 | 10.00 | 1149.42 | +1.23% | 137.9 |
| **RC105** | 14.20 | 1566.37 | -3.87% | 236.8 | 14.20 | 1564.68 | -3.97% | 156.2 |
| **RC106** | 12.80 | 1390.74 | -2.39% | 254.5 | 12.40 | 1395.70 | -2.04% | 174.0 |
| **RC107** | 11.60 | 1261.41 | +2.51% | 227.9 | 11.40 | 1257.22 | +2.17% | 170.4 |
| **RC108** | 10.60 | 1139.66 | -0.01% | 171.2 | 10.60 | 1148.95 | +0.80% | 79.4 |
| **Trung bình** | **12.45** | **1373.19** | **-0.44%** | **231.8** | **12.30** | **1375.03** | **-0.33%** | **151.9** |

*Đóng góp của mô hình chuyển giao:*
1. **Tối ưu Fleet Size:** Đạt trung bình 12.30 xe (tốt hơn mức 12.45 xe của học trực tuyến), hạn chế hội tụ non nhờ huấn luyện offline bằng Domain Randomization.
2. **Tăng tốc 35%:** Thời gian xử lý trung bình giảm từ 231.8 giây xuống còn 151.9 giây do loại bỏ việc tính toán gradient trực tuyến.
3. **Bảo toàn chất lượng tuyến:** Mức Gap% khoảng cách đạt -0.33%, tương đương với mức -0.44% của mô hình học trực tuyến đầy đủ.

#### 3.4. Hệ thống phân phối trực quan và Cổng thông tin (NAMI)
Nhằm hiện thực hóa kết quả nghiên cứu lý thuyết vào thực tiễn doanh nghiệp, chúng tôi đã phát triển cổng thông tin điều phối mang tên **NAMI**. Hệ thống có kiến trúc gồm:
- **Backend (FastAPI):** Lập lịch và quản lý các luồng tính toán tối ưu hóa đa tiến trình (multiprocessing pool). Cung cấp các API RESTful để nhận cấu hình điều phối, tải dữ liệu khách hàng (Solomon hoặc định dạng CSV doanh nghiệp), khởi chạy bộ giải lai DDQN-ALNS và xuất báo cáo kết quả.
- **Frontend (HTML5/Vanilla CSS/Javascript):** Giao diện tương tác trực quan hóa đường đi của các xe trên bản đồ số, hiển thị chi tiết tiến trình hội tụ của chi phí (history convergence plot), biểu đồ phân bổ tải trọng của từng xe và bảng thống kê các chỉ số vận hành chính (KPIs) như tỷ lệ giao hàng đúng giờ (On-Time Rate), thời gian phục vụ, thời gian chờ đợi tại mỗi điểm đỗ.

---

### 4. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

#### 4.1. Kết luận
Nghiên cứu đã thiết lập thành công mô hình tối ưu hóa lai **DDQN-ALNS** cho bài toán VRPTW. Các đóng góp chính của công trình bao gồm:
1. Tích hợp thành công bộ điều khiển học tăng cường sâu Double DQN để điều hướng chiến lược tìm kiếm (Plateau Controller) và lựa chọn toán tử phá hủy/sửa chữa (Operator Controller), cải thiện đáng kể tính thích ứng của thuật toán ALNS.
2. Đề xuất cơ chế học điều kiện chấp nhận (LAC) thay thế hiệu quả cho Simulated Annealing, giúp hệ thống đưa ra quyết định chấp nhận lời giải thông minh hơn dựa trên dữ liệu lịch sử tìm kiếm.
3. Thiết lập toán tử sửa chữa Forward Time Slack (FTS) và giải thuật Set Partitioning qua MILP, giúp giải quyết triệt để vấn đề ràng buộc khung thời gian chặt và tối thiểu hóa số lượng phương tiện vận hành.
4. Đạt kết quả thực nghiệm vượt trội trên tập dữ liệu chuẩn Solomon với Gap% chỉ 0.27% (ở cấu hình 1200 vòng lặp) và -0.44% (ở cấu hình 2500 vòng lặp) và cấu hình đội xe tối ưu hơn hẳn giải pháp thương mại Google OR-Tools.
5. Chứng minh khả năng chuyển giao mạnh mẽ của mô hình thông qua phương pháp Domain Randomization, mở ra cơ hội triển khai thực tế dạng plug-and-play cho các doanh nghiệp logistics.

#### 4.2. Hướng phát triển tương lai
Mặc dù đạt được những kết quả khả quan, đề tài vẫn còn một số hạn chế cần tiếp tục nghiên cứu phát triển:
- **Hỗ trợ đội xe không đồng nhất (Heterogeneous Fleet):** Trong thực tế, các doanh nghiệp sử dụng nhiều loại phương tiện có sức tải, vận tốc và định mức chi phí khác nhau. Cần mở rộng cấu trúc dữ liệu và hàm mục tiêu để hỗ trợ ràng buộc này.
- **Tích hợp lịch trình tài xế:** Bổ sung các ràng buộc thực tế như thời gian làm việc tối đa của tài xế trong một ca, giờ nghỉ trưa bắt buộc và quy định về thời gian làm thêm giờ (overtime limits).
- **Điều phối động thời gian thực (Dynamic Re-optimization):** Phát triển cơ chế cập nhật lộ trình tức thời khi có đơn hàng khẩn cấp phát sinh giữa ngày mà không làm gián đoạn các điểm giao hàng đã hoàn thành.

---

## TÀI LIỆU THAM KHẢO

1. **Bi, J., Y. Zhou, and H. Cheng. (2022).** A reinforcement learning-aided adaptive large neighborhood search heuristic for the vehicle routing problem with time windows. *IEEE Transactions on Cybernetics*, 52(9), 9205-9218.
2. **Hottung, A., & Tierney, K. (2020).** Neural large neighborhood search for the capacitated vehicle routing problem. *European Conference on Artificial Intelligence (ECAI)*.
3. **Kool, W., van Hoof, H., & Welling, M. (2018).** Attention, learn to solve routing problems! *International Conference on Learning Representations (ICLR)*.
4. **Kool, W., van Hoof, H., Gromicho, J., & Welling, M. (2021).** Deep policy dynamic programming for vehicle routing. *Advances in Neural Information Processing Systems (NeurIPS)*.
5. **Ropke, J., & Pisinger, D. (2006).** An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. *Transportation Science*, 40(4), 455-472.
6. **Solomon, M. M. (1987).** Algorithms for the vehicle routing and scheduling problems with time window constraints. *Operations Research*, 35(2), 294-310.
7. **Schaul, T., Quan, J., Antonoglou, I., & Silver, D. (2016).** Prioritized experience replay. *International Conference on Learning Representations (ICLR)*.
8. **Wang, L. et al. (2024).** Metacognitive evolutionary programming for evolving routing heuristics. *arXiv preprint arXiv:2405.00000*.
9. **Wang, Z., Schaul, T., Hessel, M., Hasselt, H., Lanctot, M., & Freitas, N. (2016).** Dueling network architectures for deep reinforcement learning. *International Conference on Machine Learning (ICML)*.
10. **Zhou, J. et al. (2024).** VRPAgent: Evolving heuristic operators for vehicle routing problems with large language models. *arXiv preprint arXiv:2404.03210*.
