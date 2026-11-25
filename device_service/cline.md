# Windows 设备服务启动说明

## 项目路径

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\device_service
```

## 项目类型

Python 出站设备任务 Worker，当前使用 MockAdapter。它主动轮询后端任务，不开放园区内网端口。

## 依赖安装

在项目根目录执行：

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan
.\.venv\Scripts\python.exe -m pip install -e ".\device_service[dev]"
```

## 启动

先启动后端 `8000` 端口，然后执行：

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\device_service
$env:WENQUAN_API_BASE="http://127.0.0.1:8000/api/v1"
$env:WENQUAN_DEVICE_TOKEN="dev-device-service-change-me"
$env:WENQUAN_WORKER_ID="windows-frontdesk-01"
$env:WENQUAN_READER_ID="mock-reader"
$env:WENQUAN_MOCK_RESULT="SUCCEEDED"
$env:WENQUAN_RESULT_JOURNAL=".\pending-device-result.json"
..\.venv\Scripts\python.exe -m wenquan_device_service.main
```

`WENQUAN_MOCK_RESULT` 可设为：

- `SUCCEEDED`
- `FAILED`
- `UNKNOWN`

## 测试

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\device_service
..\.venv\Scripts\python.exe -m pytest -q
```

## 重要限制

- 当前只有 MockAdapter，未连接真实 NFC 读写器或锁具。
- 写卡成功不等于门已打开。
- `UNKNOWN` 不自动重试设备动作，也不释放柜位。
- 已执行但回传失败时，只重试 HTTP 结果上报，使用同一任务号。
- 正式 SDK 接入前不得虚构 DLL 名称、函数签名或卡片密钥。
