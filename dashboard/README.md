---
# Nexus Logistics VRPTW Dashboard

**Version:** 1.0.0-beta (Sprint 1 Completed)  
**Tech Stack:** Vanilla JS, Leaflet.js, OSRM API, Chart.js
---
## Project Overview

Hệ thống quản lý và mô phỏng lộ trình giao hàng tối ưu (Vehicle Routing Problem with Time Windows) dành cho doanh nghiệp. Hệ thống hỗ trợ so sánh thuật toán AI (DDQN) và thuật toán truyền thống (ALNS) trên nền bản đồ thực tế.

## Progress Report (Current Status)

### Sprint 0: Foundation & Core Simulation

- [X] Tích hợp bản đồ Leaflet (CartoDB Positron theme).
- [X] Tối ưu hóa API OSRM: Fetch toàn bộ route trong 1 request duy nhất (giảm tải nhìu).
- [X] Hệ thống mô phỏng di chuyển Lerp Animation.
- [X] Xây dựng cơ chế Store (Pub-Sub) để quản lý trạng thái ứng dụng đồng nhất.

### Sprint 1: Intelligent Input & UX (Current)

- [X] **UI Overhaul:** Giao diện chuyên nghiệp, không sử dụng emoji, thay thế bằng SVG icons.
- [X] **Live Fleet Status:** Bảng theo dõi tải trọng (Payload) và tiến độ giao hàng thời gian thực.
- [X] **Deep Focus Mode:** Click vào route/card để zoom cận cảnh và làm mờ các thành phần không liên quan.
- [X] **Setup Wizard:** - [x] Tab Cấu hình đội xe (Số lượng, tải trọng).
  - [X] Chế độ nhập liệu "Non-tech": Thả ghim trực tiếp lên Map (Map Pinning).
  - [X] Cấu trúc sẵn sàng cho Import Excel/CSV.

---

## Project Structure

```text
/
├── index.html           # Main UI Entry (Setup, Dispatch, Analytics, Inspector)
├── css/
│   └── style.css        # Glassmorphism UI & Layout
└── js/
    ├── main.js          # Khởi tạo App & Dependency Injection
    ├── core/
    │   ├── Store.js     # "Bộ não" quản lý State (activeRoute, data, v.v.)
    │   └── DataLoader.js# Xử lý nạp file JSON/Excel
    ├── components/
    │   ├── TabController.js # Quản lý chuyển đổi 4 màn hình chính
    │   └── AlgoSwitcher.js  # Chuyển đổi giữa kết quả DDQN/ALNS
    └── views/
        ├── SetupView.js     # Logic nhập liệu, thả ghim, cấu hình fleet
        ├── DispatchView.js  # Logic vẽ bản đồ, gọi OSRM & Animate xe
        ├── InspectorView.js # Bảng soi dữ liệu chi tiết
        └── AnalyticsView.js # Vẽ biểu đồ hội tụ (Convergence)
```

---

## Roadmap & Next Steps

### 1. Backend Integration (Python/FastAPI)

- [ ] Thiết lập môi trường Python bằng `uv`.
- [ ] Xây dựng API `POST /solve`: Nhận dữ liệu từ `SetupView` và đẩy vào hàng đợi (Queue).
- [ ] Tính toán **Distance Matrix** từ tọa độ khách hàng để làm đầu vào cho AI.

### 2. Advanced Features

- [ ] **Real-time Geocoding:** Tích hợp ô tìm kiếm địa chỉ (Search Bar) tự động cắm ghim.
- [ ] **Excel Parser:** Sử dụng `SheetJS` để đọc file `.xlsx` thực tế từ doanh nghiệp.
- [ ] **Split-map View:** Hiển thị so sánh song song 2 bản đồ ALNS và DDQN.

## Technical Notes

- **Coordinate Scaling:** Do dữ liệu Solomon dùng tọa độ XY đơn giản, hệ thống sử dụng `SCALE_FACTOR = 0.0005` và `REAL_DEPOT` (TDTU) làm gốc để ánh xạ lên bản đồ Quận 7.
- **Performance:** Tránh gọi `render()` liên tục. Sử dụng `applyFocus()` để thay đổi CSS Opacity thay vì vẽ lại toàn bộ Leaflet Layer.

---

*Last updated by Ông Năm Chèo - 13/04/2026*
--------------------------------------------
