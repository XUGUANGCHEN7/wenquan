# Windows 本地设备服务

该进程只主动向 FastAPI 发起 HTTPS 请求，领取并回传设备任务；云端无需访问园区内网。当前只包含明确标注的 Mock 适配器。

```powershell
$env:WENQUAN_API_BASE="http://127.0.0.1:8000/api/v1"
$env:WENQUAN_DEVICE_TOKEN="dev-device-service-change-me"
$env:WENQUAN_WORKER_ID="windows-frontdesk-01"
$env:WENQUAN_READER_ID="mock-reader"
$env:WENQUAN_MOCK_RESULT="SUCCEEDED" # SUCCEEDED / FAILED / UNKNOWN
$env:WENQUAN_RESULT_JOURNAL=".\pending-device-result.json"
..\.venv\Scripts\python.exe -m wenquan_device_service.main
```

## 安全与未知结果

- `UNKNOWN` 或超时不会自动重试设备命令，后端任务、实体权限和柜位预占都不会被自动释放。
- 已完成设备动作但后端回传失败时，结果写入 `WENQUAN_RESULT_JOURNAL`，后续轮询周期重试同一唯一任务号。
- 适配器接口位于 `wenquan_device_service/worker.py` 的 `DeviceAdapter`。真实 Windows SDK 适配器必须在取得厂商 DLL、位数、ABI、驱动、许可和样机后实现。
- 本文不虚构 DLL 名、函数签名、端口、卡片扇区或密钥结构。

## 测试

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

## 待样机验证

同一张实体手牌能否同时持有柜锁与私汤锁权限、授权有效期、加钟是否需重新写卡、挂失撤销、清卡、断外网开锁和回传能力。模拟成功不能替代真实设备联调。
