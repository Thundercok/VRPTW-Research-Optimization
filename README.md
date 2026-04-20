# VRPTW Research Optimization

- Backend : FastAPI
- Frontend : tĩnh được serve chung bởi backend.

## Yêu cầu

- Python 3.11+
- Môi trường ảo `.venv` trong thư mục gốc, hoặc một Python environment tương đương

## Chạy backend và frontend

Frontend không có server riêng. Khi backend chạy, bạn mở giao diện ở cùng địa chỉ đó:

- Backend API: `http://127.0.0.1:8000/api`
- Frontend UI: `http://127.0.0.1:8000/`

### Trên PowerShell/CMD

```powershell
cd C:\D\Github\VRPTW-Research-Optimization
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .\.venv\Scripts\Activate.ps1
cd web\backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Sau khi backend khởi động xong, mở trình duyệt và vào:

```text
http://127.0.0.1:8000/
```

## Hướng dẫn dùng web (ngắn gọn)

1. Đăng nhập vào hệ thống.
2. Chọn chế độ dữ liệu:
- `Sample`: tự động nạp dữ liệu mẫu Solomon.
- `Real Data`: dùng dữ liệu thật để import/paste.
3. Nhập dữ liệu khách hàng bằng một trong các cách:
- `Choose File` để chọn `.csv/.xlsx/.xls`.
- Kéo thả file vào vùng Import.
- Copy từ Excel và `Ctrl+V` trực tiếp vào trang (khi đang ở `Real Data`).
4. Kiểm tra bảng `Customer List` đã có đủ điểm.
5. Nhấn `Run Model` để chạy và xem kết quả DDQN vs ALNS.

## Input cần có

Mỗi dòng khách hàng nên có các cột sau:

- Tên: `Customer Name` hoặc `Name`
- Tọa độ: `Latitude/Longitude` (hoặc `Lat/Lon`, `Lat/Lng`)
- Nhu cầu: `Demand` (hoặc `Qty`, `Quantity`)
- Địa chỉ: `Address` (nếu không có tọa độ, hệ thống sẽ thử geocode)

Gợi ý CSV tối thiểu:

```csv
Customer Name,Address,Latitude,Longitude,Demand
Depot,1 Ben Nghe,10.776889,106.700806,0
Customer A,45 Le Loi District 1,10.773900,106.700100,12
Customer B,12 Nguyen Hue District 1,10.774300,106.703900,8
```

## Test nhanh

1. Chạy backend và mở UI.
2. Vào `Real Data`.
3. Import file test: `logs/results-v9.5/customers_import_test.csv`.
4. Nhấn `Run Model` và kiểm tra có kết quả ở tab Results.

