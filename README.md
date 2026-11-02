# 蜀南温泉运营系统一期

本仓库按 `.clinerules/project-rules.md` 交付一期可运行骨架：两个独立微信原生小程序、Vue 3 运营 Web、FastAPI/MySQL 模块化单体，以及只主动出站访问后端的 Windows 设备任务服务。

> 当前是开发/Mock 环境，不是生产验收。微信支付、微信登录、真实 Windows SDK、NFC 读写器、柜锁和私汤锁尚未接入；开发 Mock 的成功页面不代表真实扣款或硬件动作成功。

## 目录

| 目录 | 内容 |
| --- | --- |
| `frontend_1/` | 购票会员小程序：门票、私汤连续场次预约、统一余额、订单、充值 |
| `frontend_2/` | 独立私汤房点餐小程序：房间选择、左侧商家/右侧商品、访客微信/会员余额、商家状态 |
| `frontend_web/` | 前台、商家、财务、管理员工作台；管理员可维护商家和商品 |
| `backend/` | FastAPI、SQLAlchemy、Alembic、MySQL 权威业务事实与 API |
| `device_service/` | 主动轮询设备任务、可替换适配器、Mock 与本地结果日志 |
| `docs/superpowers/specs/` | 已批准设计 |
| `docs/superpowers/plans/` | 实施计划与执行选择记录 |
| `.clinerules/` | 项目持续约束 |

历史练习文件 `test.py`、`11`、`a-test.md`、`b-test.md` 保留未动，它们不属于本项目。原始未跟踪 `frontend_1` 中的 MCP 配置包含外部地图密钥，未复制到仓库；如这些密钥曾暴露，应轮换。

## 环境

- Python 3.12
- Node.js 24 / npm 11
- MySQL 8（推荐 Docker Compose）或测试 SQLite
- 微信开发者工具（两个小程序各自导入）
- Windows 10/11（仅设备服务；真实 SDK 待厂商提供）

## 后端启动

```powershell
Copy-Item .env.example .env
python -m venv .venv
uv pip install --python .venv\Scripts\python.exe -e ".\backend[dev]"
docker compose up -d mysql
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
```

开发环境启动时会自动写入演示会员、17 间房、演示房间使用记录、菜单、手牌、柜位和充值活动。生产环境不会自动建表或种子；必须显式运行迁移并替换所有开发适配器。

- API：<http://localhost:8000/api/v1>
- OpenAPI：<http://localhost:8000/docs>
- 健康检查：`GET /api/v1/health`
- 导出快照：`docs/openapi.json`

### 开发令牌

仅开发环境且 `DEV_AUTH_ENABLED=true` 时可用：

| 角色 | Bearer Token |
| --- | --- |
| 会员 | `dev-member` |
| 前台 | `dev-frontdesk` |
| 商家 | `dev-merchant` |
| 财务 | `dev-finance` |
| 管理员 | `dev-admin` |
| 设备服务 | `dev-device-service-change-me` |

这些值不是生产凭据。生产环境必须使用受控身份服务、角色授权和独立设备凭据。

## 运营 Web

```powershell
Set-Location frontend_web
Copy-Item .env.example .env
npm install
npm run dev
```

访问 <http://localhost:5173>，选择角色进入。商家账号只能进入出餐相关界面；财务不能执行实体卡操作；管理员拥有全部运营页面，并可在“商家商品”页增删改查商家及商品。

```powershell
npm run typecheck
npm test
npm run build
```

## 两个小程序

### 购票会员端

1. 微信开发者工具导入 `frontend_1/`。
2. 当前本机 AppID 若已由微信开发者工具写入真实值，请确认它属于购票端；不得与点餐端共用。AppSecret 不进入仓库。
3. `config.js` 的 `apiBase` 默认指向 `http://127.0.0.1:8000/api/v1`；开发阶段可关闭合法域名校验。
4. `config.js` 的 `development: true` 使用开发会员令牌和 Mock 支付；正式环境必须实现微信登录、`wx.requestPayment`、支付结果服务端查询，并关闭开发令牌。

```powershell
Set-Location frontend_1
npm test
```

### 独立房间点餐端

1. 微信开发者工具导入 `frontend_2/`。
2. AppID 当前为独立占位 `wx0000000000000002`，必须替换为该点餐小程序自己的正式 AppID，且与购票端不同。
3. 二维码 scene 建议为 `ROOM-01` 至 `ROOM-17`；也可用链接 `?scene=ROOM-01`。无参数时开发默认 `ROOM-01`，进入后也可在页面顶部直接选择送餐房间。
4. 真机预览时，`config.js` 的 `apiBase` 必须使用电脑局域网 IP（当前开发机为 `http://192.168.43.235:8000/api/v1`），不能使用 `127.0.0.1`；手机与电脑需在同一 Wi-Fi，后端用 `--host 0.0.0.0` 启动并允许防火墙入站。电脑 IP 改变后需同步修改 `apiBase`。
5. 点餐页左侧列出营业商家，右侧展示所选商家的商品；切换商家会清空当前购物车，订单只能包含同一商家的商品。
6. 访客默认可浏览和微信支付；只有点击“明确登录并绑定会员”后才附带会员令牌并使用共享余额。

```powershell
Set-Location frontend_2
npm test
```

WXML 渲染、真实微信登录和真实微信支付必须在微信开发者工具与已配置 AppID/商户号下另行验证，目前没有声称完成。

## 本地设备服务

```powershell
Set-Location device_service
$env:WENQUAN_API_BASE="http://127.0.0.1:8000/api/v1"
$env:WENQUAN_DEVICE_TOKEN="dev-device-service-change-me"
$env:WENQUAN_WORKER_ID="windows-frontdesk-01"
$env:WENQUAN_READER_ID="mock-reader"
$env:WENQUAN_MOCK_RESULT="SUCCEEDED"
..\.venv\Scripts\python.exe -m wenquan_device_service.main
```

`WENQUAN_MOCK_RESULT` 可设为 `SUCCEEDED`、`FAILED` 或 `UNKNOWN`。未知结果、超时和回传中断不会触发设备命令自动重试；已经执行但未回传的结果写入本地 journal，下个周期用同一任务号补传。详见 `device_service/README.md`。

## 已执行验证

| 范围 | 命令 | 结果 |
| --- | --- | --- |
| 后端基础、会员/账本、票务 | `pytest tests/test_foundation.py tests/test_wallet_identity.py tests/test_tickets.py -q` | 11 passed |
| 私汤库存、分房、清洁、加钟、前台 API | `pytest tests/test_rooms.py tests/test_room_transitions.py tests/test_frontdesk_api.py -q` | 11 passed |
| 点餐、手牌/押金、设备领域、会员 API | `pytest tests/test_dining.py tests/test_access.py tests/test_devices.py tests/test_member_api.py -q` | 9 passed |
| 运营 / 管理 / 商家商品 / 人工退款 API | `pytest tests/test_operations_api.py -q` | 6 passed |
| Alembic | `alembic upgrade head` → `downgrade base` → `upgrade head` | 通过（SQLite 迁移验证） |
| 购票会员小程序 | `cd frontend_1; npm test` | 4 passed |
| 点餐小程序 | `cd frontend_2; npm test` | 4 passed |
| 运营 Web | `cd frontend_web; npm test; npm run typecheck; npm run build` | 8 passed，类型检查与生产构建通过 |
| 设备服务 | `cd device_service; ..\.venv\Scripts\python.exe -m pytest -q` | 5 passed |

后端完整测试为 `37 passed, 2 skipped`：37 项领域/API 测试通过，2 项 MySQL 并发测试被跳过。所有已执行后端测试使用临时 SQLite 测试库，不等同于 MySQL 集成验证。

### 未执行 / 无法声称通过

- `backend/tests/test_mysql_concurrency.py` 已实现“最后一间房只售一次”和“同一充值引用只入账一次”两个 MySQL 并发测试，但本机 Docker 引擎未运行、本地 MySQL 5.7 无可用测试凭据，因此本次**未执行**。提供隔离 MySQL 8 和 `WENQUAN_TEST_MYSQL_URL` 后运行 `pytest -m mysql -q`。
- 微信开发者工具中的 WXML 渲染、真机登录、真实 AppID、UnionID、商户号和微信支付/退款通知均未验证。
- Windows SDK、NFC 读写器、柜锁、私汤锁、写卡回读、断网开锁和清卡未联调；设备服务只有 Mock。
- 浏览器 UI 已通过 TypeScript 与生产构建，但未执行真实浏览器自动化验收。

## 关键业务约束

- 金额全部为整数分；票价、房费、菜价、押金和活动保存成交快照。
- 会员储值先扣本金，再扣赠送金；退款按原扣款来源分别冲回。游客端只展示合计余额。
- 私汤订单检查至少一间具体房间能覆盖整个连续使用区间和最后一次清洁；待支付预占 15 分钟。
- 晚到分房重新计算实际使用满时长与清洁，冲突时进入人工处理，不覆盖下一单。
- 点餐创建和支付确认均验证原始 `room_use_id`；支付成功但不可送达只进入前台异常队列。
- 每张票一次入园；每枚手牌独立押金与退款号；清卡失败不阻止实物归还对应的应退款，但卡片隔离。
- 设备结果未知不自动重试、不释放柜位；本地服务只主动出站访问后端。

## 部署、备份与回滚

1. 开发、测试、生产使用独立数据库与密钥；生产设置 `APP_ENV=production`、`DEV_AUTH_ENABLED=false`，并替换静态令牌、Mock 支付和 Mock 设备适配器。
2. 部署前备份：`mysqldump --single-transaction --routines --triggers <db> > backup.sql`。
3. 恢复演练：在隔离数据库执行 `mysql <db> < backup.sql`，校验迁移版本、关键表行数和账本合计，再允许切换。
4. 升级：先备份，再 `alembic upgrade head`；应用发布保持两个小程序 API 版本兼容窗口。
5. 回滚：先回滚应用，再评估 `alembic downgrade <revision>`；涉及业务写入的新表不要在生产未备份时直接降级。OpenAPI 快照位于 `docs/openapi.json`。
6. 最终云端/园区本地部署位置、网络拓扑、外网故障前台应急流程仍待确认，不在代码中假定云厂商或服务器规格。

## 待确认事项

完整清单见 `docs/pending-confirmations.md`，包括真实 AppID/商户号/UnionID 绑定、固定场次与晚到满时长冲突政策、取消/部分退款、押金金额与损坏责任、微信退款次数能力、Windows SDK 与锁具能力、部署位置及离线流程。未确认项没有在前端或后端自行补成自动扣款、自动退款或自动重试规则。

## 安全

- 不提交 AppSecret、支付密钥、设备密钥和真实游客身份。
- 关键状态变更记录操作人/设备、前后状态、原因和请求号。
- 生产环境禁用开发登录与 Mock 确认；正式支付回调仍需实现验签、商户/金额核对与幂等查询。
- 前端客户端不决定价格、库存、余额或支付成功。
