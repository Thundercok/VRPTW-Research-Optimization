# VRPTW Research Optimization

Dự án này có backend FastAPI và frontend tĩnh được serve chung bởi backend.

## Yêu cầu

- Python 3.11+
- Môi trường ảo `.venv` trong thư mục gốc, hoặc một Python environment tương đương

## Chạy backend và frontend

Frontend không có server riêng. Khi backend chạy, bạn mở giao diện ở cùng địa chỉ đó:

- Backend API: `http://127.0.0.1:8000/api`
- Frontend UI: `http://127.0.0.1:8000/`

### Trên PowerShell

```powershell/cmd
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

