# 后端项目启动说明

## 项目路径

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\backend
```

## 项目类型

FastAPI + SQLAlchemy 2 + Alembic 后端，默认 API 前缀为 `/api/v1`。

## 启动前检查

项目根目录虚拟环境：

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\.venv
```

如依赖缺失，在项目根目录执行：

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
```

## 方式一：SQLite 快速启动（当前最简单）

当前项目没有 `.env` 时会使用：

```text
backend/wenquan.sqlite3
```

开发环境会自动建表并写入演示数据。

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 方式二：MySQL 8 启动

### 1. 创建环境变量

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan
Copy-Item .env.example .env
```

### 2. 启动 MySQL

```powershell
docker compose up -d mysql
```

等待容器状态为 `healthy`。

### 3. 执行迁移

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

### 4. 启动后端

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 启动结果

- 健康检查：<http://127.0.0.1:8000/api/v1/health>
- Swagger：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>
- API：`http://127.0.0.1:8000/api/v1`

## 测试

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\backend
..\.venv\Scripts\python.exe -m pytest -q
```

MySQL 并发测试需要单独设置隔离数据库：

```powershell
$env:WENQUAN_TEST_MYSQL_URL="mysql+pymysql://user:password@127.0.0.1:3306/wenquan_test?charset=utf8mb4"
..\.venv\Scripts\python.exe -m pytest -m mysql -q
```

## 开发令牌

开发环境可用：

| 角色 | Bearer Token |
|---|---|
| 会员 | `dev-member` |
| 前台 | `dev-frontdesk` |
| 商家 | `dev-merchant` |
| 财务 | `dev-finance` |
| 管理员 | `dev-admin` |
| 设备服务 | `dev-device-service-change-me` |

这些令牌不是生产凭据。生产必须替换正式身份、支付和设备适配器。
