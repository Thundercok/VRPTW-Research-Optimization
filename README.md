# VRPTW Research Optimization

VRPTW Research Optimization là hệ thống tối ưu tuyến xe gồm `FastAPI backend` và `frontend` tĩnh được serve chung một cổng. Mục tiêu là nhập dữ liệu khách hàng, tính ma trận khoảng cách, chạy DDQN/ALNS, và xem kết quả trên bảng + bản đồ.

## Chạy ứng dụng

```powershell
cd C:\D\Github\VRPTW-Research-Optimization
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .\.venv\Scripts\Activate.ps1
cd web\backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Mở web tại: `http://127.0.0.1:8000/`

## Cách dùng nhanh

1. Đăng nhập.
2. Chọn mode:
- `Sample`: tự nạp dữ liệu mẫu Solomon.
- `Real Data`: nhập dữ liệu thật.
3. Nhập dữ liệu theo 1 trong 3 cách:
- `Choose File` với `.csv/.xlsx/.xls`
- Kéo thả file vào vùng Import
- Copy từ Excel rồi `Ctrl+V` trực tiếp vào web
4. Hoặc bấm trực tiếp lên bản đồ để thêm điểm mới, rồi chỉnh `Name`, `Address`, `Demand` trong bảng.
5. Kiểm tra bảng `Customer List` và nhấn `Run Model`.

## Input cần có

Hệ thống tự map cột theo header. Nên có các cột sau:

- `Customer Name` hoặc `Name`
- `Address`
- `Latitude` / `Longitude` hoặc `Lat` / `Lng` / `Lon`
- `Demand` hoặc `Qty` / `Quantity`

Ví dụ CSV:

```csv
Customer Name,Address,Latitude,Longitude,Demand
Depot,1 Ben Nghe,10.776889,106.700806,0
Customer A,45 Le Loi District 1,10.773900,106.700100,12
Customer B,12 Nguyen Hue District 1,10.774300,106.703900,8
```

Lưu ý:
- `Depot` nên để `Demand = 0`
- Nếu không có tọa độ, hệ thống sẽ thử geocode từ `Address`
## Tai khoan Admin (dùng để quản lý User Account,history login/logout)

- TK : tranlop72@gmail.com
- MK : 123456

## Flow hệ thống

`Login -> nhập dữ liệu -> auto nhận depot/customer -> gọi API khoảng cách -> queue job -> solve DDQN/ALNS -> hiển thị kết quả`

Trạng thái job: `queued -> processing -> matrix -> solving -> done`.

## Lỗi/ràng buộc chính

- Thiếu email/mật khẩu: báo lỗi ngay trên form.
- File sai định dạng: báo `Import Failed`.
- Thiếu depot hoặc customer: không cho chạy.
- Demand âm: bị chặn.
- Vượt tải trọng: backend trả lỗi kiểu `Infeasible` hoặc `exceeds vehicle capacity`; UI sẽ báo rõ để tăng `Vehicles` hoặc `Capacity`.

## Test nhanh

1. Mở `Real Data`.
2. Import file: `logs/results-v9.5/customers_import_test.csv`.
3. Xem `DEPOT` và các customer hiện trên bảng/bản đồ.
4. Nhấn `Run Model` và kiểm tra kết quả ở tab Results.

## Training Analysis dùng để làm gì

Phần `Training Analysis` dùng để xem lại dữ liệu benchmark/lịch sử mô hình trong `logs/results-vX`.

- `Version`: chọn bộ log/kết quả muốn xem.
- `Instance`: lọc theo bài toán cụ thể.
- `Deep Analysis`: mở màn hình phân tích chi tiết hơn, gồm biểu đồ hội tụ, heatmap operator, leaderboard và so sánh kết quả.

Tóm lại:
- Đây là phần để **xem lại và phân tích kết quả có sẵn**.
- Không phải phần để nhập dữ liệu chạy model mới.

Khi dùng `Training Analysis`:
- Muốn so sánh DDQN và ALNS trên một instance.
- Muốn xem version nào tốt hơn.
- Muốn kiểm tra xu hướng hội tụ hoặc policy operator.

Khi chỉ chạy dữ liệu mới:
- Chỉ cần dùng `Customer List` và `Run Model`.

