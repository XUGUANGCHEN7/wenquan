# Backend

FastAPI modular monolith. All business facts, prices, balances, payment states, room inventory, and device tasks are server-owned.

```powershell
Copy-Item ..\.env.example ..\.env
uv pip install --python ..\.venv\Scripts\python.exe -e ".[dev]"
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
```

真机预览时手机必须能访问电脑局域网 IP 的 `8000` 端口；如 Windows 防火墙提示，请仅对专用网络/本地子网放行 Python 或 TCP 8000。不要把该开发端口直接暴露到公网。

Development payment confirmation is `/api/v1/payments/{payment_no}/mock-confirm` and is disabled in production. It never calls WeChat and must not be treated as payment evidence.

Tests:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

MySQL-only concurrency tests are marked `mysql` and require an isolated schema:

```powershell
$env:WENQUAN_TEST_MYSQL_URL="mysql+pymysql://user:password@127.0.0.1:3306/wenquan_test?charset=utf8mb4"
..\.venv\Scripts\python.exe -m pytest -m mysql -q
```

The fixture drops and recreates that test schema. Never point it at development or production data.

Important limitations: static development bearer tokens must be replaced, real WeChat login/payment notification verification is not implemented, and no model represents unconfirmed cancellation or deposit-deduction policies.
