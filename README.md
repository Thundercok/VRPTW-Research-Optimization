# VRPTW Research Optimization

- Backend : FastAPI
- Frontend : tĩnh được serve chung bởi backend.
# VRPTW Research Optimization

Hệ thống VRPTW gồm `FastAPI backend` và `frontend` tĩnh được serve chung một cổng. Dùng để nhập dữ liệu khách hàng, tính ma trận khoảng cách, chạy DDQN vs ALNS, và xem kết quả trên bảng/bản đồ.

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
3. Nạp khách hàng bằng 1 trong 3 cách:
- `Choose File` với `.csv/.xlsx/.xls`
- Kéo thả file vào vùng Import
- Copy từ Excel rồi `Ctrl+V` trực tiếp vào web
4. Kiểm tra bảng `Customer List`.
5. Nhấn `Run Model` để chạy.

## Input cần có

Hệ thống hỗ trợ tự map cột theo header. Nên có các cột sau:

- `Customer Name` hoặc `Name`
- `Address`
- `Latitude` / `Longitude` hoặc `Lat` / `Lng` / `Lon`
- `Demand` hoặc `Qty` / `Quantity`

Gợi ý CSV:

```csv
Customer Name,Address,Latitude,Longitude,Demand
Depot,1 Ben Nghe,10.776889,106.700806,0
Customer A,45 Le Loi District 1,10.773900,106.700100,12
Customer B,12 Nguyen Hue District 1,10.774300,106.703900,8
```

## Flow hệ thống

`Login -> nhập dữ liệu -> auto nhận depot/customer -> gọi API khoảng cách -> queue job -> solve DDQN/ALNS -> hiển thị kết quả`

Trạng thái job chạy theo: `queued -> processing -> matrix -> solving -> done`.

## Lỗi/ràng buộc chính

- Thiếu email/mật khẩu: báo lỗi ngay trên form.
- File sai định dạng: báo `Import Failed`.
- Thiếu depot hoặc customer: không cho chạy.
- Demand âm: bị chặn.
- Vượt tải trọng: backend trả lỗi kiểu `Infeasible` hoặc `exceeds vehicle capacity`; UI sẽ báo rõ để tăng `Vehicles` hoặc `Capacity`.

Ví dụ khi chạy model:

```javascript
try {
  const result = await this.request('/jobs', { method: 'POST', body: JSON.stringify(payload) });
  await this.pollJob(result.job_id);
} catch (error) {
  this.toast('Run Failed', this.parseApiError(error), 'error');
}
```

## Test nhanh

1. Mở `Real Data`.
2. Import file: `logs/results-v9.5/customers_import_test.csv`.
3. Xem `DEPOT` và các customer hiện trên bảng/bản đồ.
4. Nhấn `Run Model` và kiểm tra kết quả ở tab Results.

Lưu ý: `logs/results-v9.5/benchmark_clean.csv` là file benchmark, không phải file input khách hàng.
5. Backend tạo job và đưa vào queue.

6. Worker xử lý theo thứ tự: `queued -> processing -> matrix -> solving -> done`.
