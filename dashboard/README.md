VRPTW-Dashboard/
│
├── index.html                 # Màn hình chính (chỉ chứa khung Layout và các thẻ div rỗng cho 3 Tab)
├── css/
│   └── style.css              # Style chung (bạn có thể chia nhỏ thêm sau nếu CSS quá dài)
│
├── data/                      # Tách biệt hoàn toàn data ra khỏi source code
│   └── nexus_demo.json
│
├── assets/                    # Nơi chứa tài nguyên tĩnh
│   └── icons/                 # Marker bản đồ (icon Depot, icon xe tải, icon khách hàng...)
│
└── js/                        # Trái tim của ứng dụng
├── main.js                # File chạy đầu tiên: Khởi tạo app và gắn sự kiện
│
├── core/                  # Nhóm xử lý Dữ liệu & Logic ngầm (Không liên quan giao diện)
│   ├── Store.js           # "Single Source of Truth": Lưu trữ JSON, trạng thái đang chọn Tab nào, Route nào
│   ├── DataLoader.js      # Chuyên lo việc parse file từ máy tính hoặc fetch từ sample
│   └── Utils.js           # Các hàm xài chung (formatNumber, tính Gap, format HTML...)
│
├── components/            # Nhóm điều khiển UI dùng chung
│   └── TabController.js   # Quản lý logic click vào Sidebar để ẩn/hiện các Tab
│
└── views/                 # Nhóm giao diện chính (3 Workspaces)
├── DispatchView.js    # Tab 1: Khởi tạo Leaflet Map và điều phối animation xe chạy
├── AnalyticsView.js   # Tab 2: Vẽ biểu đồ hội tụ, heatmap (RL-ALNS stats)
└── InspectorView.js   # Tab 3: Bảng dữ liệu thô (tái sử dụng từ phần main.js cũ của bạn)