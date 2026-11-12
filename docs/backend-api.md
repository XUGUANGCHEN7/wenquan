# 蜀南温泉一期后端接口文档

> 文档版本：v1.0（2026-11-02）  
> 适用后端：FastAPI 模块化单体，`/api/v1`  
> 机器可读规范：[`openapi.json`](./openapi.json)  
> 本文以当前代码实际路由为准；金额单位为整数分，时间以 ISO 8601 表示。微信支付、退款通知、正式微信登录和真实设备接口仍是待联调适配器。

## 1. 服务地址与协议

| 环境 | Base URL | 说明 |
|---|---|---|
| 本机开发 | `http://127.0.0.1:8000/api/v1` | 电脑模拟器、运营 Web |
| 局域网联调 | `http://<电脑局域网IP>:8000/api/v1` | 手机真机；后端需 `--host 0.0.0.0`，手机与电脑同网 |
| 生产 | 待部署确认 | 必须使用 HTTPS，替换开发鉴权、支付和设备适配器 |

- 请求和响应正文均使用 JSON；数组接口直接返回数组，不额外包 `data`。
- 除路径参数、查询参数外，POST/PATCH 请求使用 `Content-Type: application/json`。
- 开发 Web 允许跨域的来源由 `WEB_ORIGIN` 配置，生产不得放开为任意来源。
- 本版无分页参数：会员订单、流水最多 100 条，财务流水最多 200 条，审计最多 200 条。

## 2. 鉴权与角色

需要鉴权的接口使用：

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

| 角色 | `role` | 主要权限 |
|---|---|---|
| 会员 | `member` | 本人资料、订单、票券、私汤预约、钱包和支付 |
| 前台 | `frontdesk` | 人工验票、房态、分房、手牌柜位、点餐处理 |
| 商家 | `merchant` | 已付款且可送达的点餐队列、接单/制作/送达 |
| 财务 | `finance` | 会员账本、人工退款、日结与异常 |
| 管理员 | `admin` | 全部运营接口及配置/审计 |
| 设备服务 | `device` | 主动领取、执行和回传设备任务 |

无令牌的公开接口只包含：健康检查、开发登录、票价/活动、私汤场次/库存、房间/商家/菜单查询，以及访客点餐相关接口。带无效令牌调用可选鉴权接口同样返回 401。

### 2.1 开发登录与令牌

开发环境且 `DEV_AUTH_ENABLED=true` 时：

```http
POST /api/v1/auth/dev
```

```json
{"role":"member"}
```

`role` 可选 `member/frontdesk/merchant/finance/admin`。响应：

```json
{"access_token":"dev-member","token_type":"bearer","role":"member","member_id":"member-demo","mode":"development"}
```

开发默认令牌（以 `.env` 实际配置为准）：

| 角色 | 令牌 |
|---|---|
| 会员 | `dev-member` |
| 前台 | `dev-frontdesk` |
| 商家 | `dev-merchant` |
| 财务 | `dev-finance` |
| 管理员 | `dev-admin` |
| 设备服务 | `dev-device-service-change-me` |

**生产环境静态令牌失效，`POST /auth/dev` 也关闭。** 正式微信登录、OpenID/UnionID 映射、商户支付签名、设备独立凭据尚未接通。

## 3. 通用约定

### 3.1 金额、日期、时间

- 所有 `*_cents` 字段都是人民币**整数分**，例如 `2900 = 29.00 元`。
- 前端按元显示时，必须精确转为整数分，禁止浮点金额入库。
- `visit_date`、`report_date` 使用 `YYYY-MM-DD`。
- 日期时间使用 ISO 8601，例如 `2026-11-05T10:00:00+08:00`；服务端内部使用 UTC。
- 库存 `null` 表示不限制库存，不是 0。
- 可空字段返回 `null`，不要与空字符串混淆。

### 3.2 请求号与审计

客户端可传 `X-Request-ID`，允许字母、数字、`.`、`_`、`-`，最长 64 字符；不合法时服务端生成新值。响应始终包含同名响应头。

```http
X-Request-ID: web-20261102-0001
```

验票等人工操作另要求正文 `request_id`。配置、退款、设备任务使用业务唯一号和幂等逻辑，不以重复点击制造第二笔业务。

### 3.3 通用订单对象

```json
{
  "order_no":"TK202611020001",
  "order_type":"TICKET",
  "status":"PENDING",
  "business_id":"tba_xxx",
  "amount_cents":2900,
  "payment_method":null,
  "created_at":"2026-11-02T10:00:00",
  "paid_at":null
}
```

`order_type`：`TICKET` 门票、`PRIVATE` 私汤、`FOOD` 点餐、`RECHARGE` 充值、`DEPOSIT` 押金、`EXTENSION` 加钟。常见订单状态：`PENDING`、`PAID`、`EXCEPTION`、`REFUNDED`。预占超时和支付失败可能使业务记录进入 `EXPIRED/CANCELLED`，不可用客户端“支付成功页”代替服务端状态。

## 4. 错误响应

统一格式：

```json
{"code":"RESOURCE_FORBIDDEN","message":"This role cannot access the resource","request_id":"req-123"}
```

| HTTP | 含义 | 常见 `code` |
|---|---|---|
| 400 | 通用错误 | `HTTP_ERROR` |
| 401 | 未认证或令牌无效 | `AUTH_REQUIRED`、`AUTH_INVALID` |
| 403 | 角色/归属无权或开发适配器关闭 | `RESOURCE_FORBIDDEN`、`DEV_AUTH_DISABLED`、`MOCK_PAYMENT_DISABLED` |
| 404 | 资源不存在或已停用 | `ORDER_NOT_FOUND`、`ROOM_CODE_INVALID` |
| 409 | 状态/库存/幂等业务冲突 | `ORDER_NOT_PAYABLE`、`ASSIGNMENT_CONFLICT`、`MERCHANT_IN_USE` |
| 422 | 参数或配置校验失败 | `VALIDATION_ERROR`、`SLOT_INVALID`、`CONFIG_INVALID` |

`422 VALIDATION_ERROR` 不返回逐字段错误数组，客户端应检查 OpenAPI/Pydantic 字段约束。生产排查以响应头和正文的 `request_id` 关联审计日志。

## 5. 系统、身份与目录

### 5.1 `GET /api/v1/health`

公开健康检查，无请求体。

```json
{"status":"ok","version":"v1","environment":"development"}
```

### 5.2 `GET /api/v1/auth/me`

任意有效角色；返回令牌对应的上下文，不代表已经完成正式微信身份绑定。

```json
{"role":"member","member_id":"member-demo","appid":"dev-app"}
```

### 5.3 `GET /api/v1/members/{member_id}/profile`

仅 `member`，且路径 `member_id` 必须等于本人。当前是开发资料响应：

```json
{"member_id":"member-demo","nickname":"温泉旅人","mode":"development"}
```

### 5.4 `GET /api/v1/operations/status`

`frontdesk/merchant/finance/admin`。

```json
{"status":"ok","role":"admin","payment_mode":"mock","device_mode":"mock"}
```

### 5.5 `GET /api/v1/catalog/ticket-prices?visit_date=YYYY-MM-DD`

公开查询指定日期成人/儿童成交价。`visit_date` 必填；价格由后台规则决定，客户端不得自行计算节假日价。

```json
{"visit_date":"2026-11-05","adult_cents":2900,"child_cents":2900,"currency":"CNY"}
```

### 5.6 `GET /api/v1/catalog/recharge-activities`

公开查询启用中的充值活动，按实付本金升序。

```json
[{"id":"recharge-200","name":"轻享礼","principal_cents":20000,"gift_cents":2000}]
```

本金和赠送金分账；充值只能微信支付，不能用余额充值。

## 6. 会员钱包与充值

### 6.1 `GET /api/v1/wallet/balance`

`member`。仅返回本金+赠送金合计可用余额。

```json
{"available_cents":22000}
```

### 6.2 `GET /api/v1/wallet/entries`

`member`。按时间倒序返回本人最近 100 条追加式流水。

```json
[{
  "reference":"RC202611020001",
  "entry_type":"RECHARGE",
  "delta_cents":22000,
  "balance_after_cents":22000,
  "created_at":"2026-11-02T10:30:00"
}]
```

`delta_cents` 为总变化；本金/赠送拆分由财务接口查询。

### 6.3 `POST /api/v1/wallet/recharges`

`member`。按活动创建充值订单和微信支付单，HTTP 201。

请求：

```json
{"activity_id":"recharge-200"}
```

响应：

```json
{"order_no":"RC202611020001","payment_no":"PY202611020001","amount_cents":20000,"payment_method":"wechat","status":"pending","mode":"mock"}
```

活动不存在或停用时 `404 RECHARGE_ACTIVITY_NOT_FOUND`。开发环境随后调用 Mock 确认；真实微信预下单、支付签名和回调待接入。

## 7. 通用订单与支付

### 7.1 `GET /api/v1/orders`

`member`。返回本人最近 100 个订单，按创建时间倒序，每项为通用订单对象。

### 7.2 `GET /api/v1/orders/{order_no}`

可选鉴权。会员只能读取本人订单；访客点餐订单可按订单号读取。前台、财务、管理员、商家按业务权限读取。

```json
{"order_no":"FD202611020001","order_type":"FOOD","status":"PAID","business_id":"foo_xxx","amount_cents":7600,"payment_method":"WECHAT","created_at":"2026-11-02T11:00:00","paid_at":"2026-11-02T11:01:00"}
```

### 7.3 `POST /api/v1/orders/{order_no}/payments`

对 `PENDING` 订单创建或复用支付单，HTTP 201。

请求：

```json
{"method":"wechat"}
```

`method`：`wechat` 或 `balance`。响应：

```json
{"payment_no":"PY202611020001","order_no":"FD202611020001","status":"pending","amount_cents":7600,"payment_method":"wechat","mode":"mock"}
```

规则：

- 余额支付需要登录会员，服务端按“本金优先、赠送金后”扣款，成功立即分派业务。
- 充值和押金 `409 WECHAT_ONLY`，禁止余额支付。
- 非待支付订单 `409 ORDER_NOT_PAYABLE`。
- 同一订单更换支付方式 `409 PAYMENT_METHOD_CONFLICT`。
- 客户端不能传金额、支付成功状态或渠道交易号。

### 7.4 `POST /api/v1/payments/{payment_no}/mock-confirm`

**仅开发环境**的微信支付确认模拟。访客支付可不认证，本人支付需使用同一会话上下文。重复调用返回同一个 `SUCCESS` 支付单，不重复扣款/出票/出单。

```json
{"payment_no":"PY202611020001","status":"success","mode":"mock"}
```

只有开发鉴权开启、非生产且 `PAYMENT_PROVIDER=mock` 才可用，否则 `403 MOCK_PAYMENT_DISABLED`。这不是微信回调，也不能作为真实扣款证据。

## 8. 公共浴室票券

### 8.1 创建多人票订单

`POST /api/v1/tickets/orders`，`member`，HTTP 201。

请求字段：

| 字段 | 类型 | 约束 |
|---|---|---|
| `visit_date` | date | 入园日期 |
| `adult_count` | int | 0–20 |
| `child_count` | int | 0–20；总人数必须大于 0 |

```json
{"visit_date":"2026-11-05","adult_count":2,"child_count":1}
```

响应：

```json
{"order_no":"TK202611020001","batch_id":"tba_xxx","amount_cents":8700,"status":"PENDING","adult_unit_cents":2900,"child_unit_cents":2900}
```

服务端保存票价快照。支付确认后为每位实际游客生成独立 `ticket_no`，不能用私汤订单替代公共浴室票。

### 8.2 查询票券明细

`GET /api/v1/tickets/orders/{order_no}`，仅订单所属 `member`。

```json
{
  "order_no":"TK202611020001",
  "status":"PAID",
  "amount_cents":8700,
  "visit_date":"2026-11-05",
  "tickets":[
    {"ticket_no":"T-001","category":"ADULT","price_cents":2900,"status":"UNUSED"},
    {"ticket_no":"T-002","category":"ADULT","price_cents":2900,"status":"UNUSED"},
    {"ticket_no":"T-003","category":"CHILD","price_cents":2900,"status":"UNUSED"}
  ]
}
```

票状态：`UNUSED` 未使用、`USED` 已入园、`VOID` 已作废。

### 8.3 前台人工核验入园

`POST /api/v1/operations/tickets/admit`，`frontdesk/admin`。

请求：

```json
{"ticket_no":"T-001","request_id":"desk-20261102-001","reason":"前台核对订单和游客后放行"}
```

响应：

```json
{"admission_id":"adm_xxx","ticket_id":"tic_xxx","admitted_at":"2026-11-02T12:00:00","operator":"frontdesk"}
```

每张票只允许一次入园，同一 `request_id` 幂等。已用/作废票、票券未支付或重复请求返回 409。一期没有闸机自动核票；设备写卡成功不会自动消耗门票。

## 9. 私汤预约（会员端）

一期 17 间房，每日五场，每场使用 120 分钟，最后统一清洁 30 分钟：

| `slot_index` | 场次 |
|---|---|
| 0 | 10:00–12:00 |
| 1 | 12:30–14:30 |
| 2 | 15:00–17:00 |
| 3 | 17:30–19:30 |
| 4 | 20:00–22:00（清洁至 22:30） |

### 9.1 查询场次及单场可售量

`GET /api/v1/rooms/slots?visit_date=YYYY-MM-DD`，公开。

```json
{
  "visit_date":"2026-11-05",
  "unit_price_cents":12000,
  "slots":[{"slot_index":0,"start":"10:00","end":"12:00","available":16}]
}
```

`available` 是满足完整使用+清洁区间的真实房间数，不是固定 17。维修、人工占用、已售预约和实际未结束使用都会扣减。

### 9.2 查询连续场次库存与价格

`GET /api/v1/rooms/availability?visit_date=YYYY-MM-DD&slots=0,1`，公开。

```json
{"available":1,"amount_cents":24000,"slot_indices":[0,1]}
```

- `slots` 为逗号分隔整数，最多允许创建 1–5 个场次。
- 多相邻场次必须同一间房覆盖整个连续区间，禁止逐场分别有房就判定可售。
- 不相邻场次必须分别下单。
- 库存为 0 时 `amount_cents=0`，不能创建订单。

### 9.3 创建预约订单

`POST /api/v1/rooms/bookings`，`member`，HTTP 201。

请求：

```json
{"visit_date":"2026-11-05","slot_indices":[0,1],"expected_arrival_at":"2026-11-05T10:20:00+08:00"}
```

响应核心字段：

```json
{
  "order_no":"PB202611020001",
  "order_type":"PRIVATE",
  "status":"PENDING",
  "business_id":"pbo_xxx",
  "amount_cents":24000,
  "payment_method":null,
  "created_at":"2026-11-02T12:00:00",
  "paid_at":null,
  "booking_id":"pbo_xxx",
  "visit_date":"2026-11-05",
  "slot_indices":[0,1],
  "expected_arrival_at":"2026-11-05T10:20:00+08:00",
  "start_at":"2026-11-05T02:00:00",
  "end_at":"2026-11-05T06:00:00",
  "cleaning_end_at":"2026-11-05T06:30:00",
  "expires_at":"2026-11-02T12:15:00",
  "booking_status":"PENDING",
  "room_number":null
}
```

待支付预占保留 15 分钟；支付确认才确认预约。`room_number` 创建时不承诺，前台到店分房后才可能返回。

### 9.4 查询预约详情

`GET /api/v1/rooms/bookings/{booking_id}`，仅预约所属 `member`。响应同创建结果；已分房时 `room_number` 为实际房号，未分房为 `null`。

## 10. 独立房间点餐

### 10.1 查询可选择的房间

`GET /api/v1/dining/rooms`，公开。返回启用的房间码、房号和当前是否有有效使用记录。

```json
[{"room_code":"ROOM-01","room_number":"01","can_order":true}]
```

手动选房只是定位送餐房号，不证明点餐人在场；没有有效使用记录时 `can_order=false`，创建订单仍会被服务端拒绝。

### 10.2 查询营业商家

`GET /api/v1/dining/merchants`，公开。仅返回启用商家；`item_count` 为可售商品数。

```json
[{"id":"merchant-spring","name":"山泉食坊","item_count":3}]
```

### 10.3 查询房间上下文

`GET /api/v1/dining/room-context/{room_code}`，公开。

```json
{"room_code":"ROOM-01","room_number":"01","can_order":true,"message":null}
```

房间码不存在或停用返回 `404 ROOM_CODE_INVALID`；不可下单时 `message` 为提示文本。

### 10.4 查询菜单

`GET /api/v1/dining/menu?merchant_id=merchant-spring`，公开；`merchant_id` 可选，只返回营业商家的商品。

```json
[{
  "id":"menu-noodles",
  "merchant_id":"merchant-spring",
  "name":"暖汤荞麦面",
  "description":"山泉高汤 · 时蔬 · 溏心蛋",
  "category":"主食套餐",
  "image_url":"",
  "price_cents":3800,
  "stock":100,
  "available":true
}]
```

商品以服务端价格、库存和可售状态为准；下架/库存 0 不可加入有效订单。

### 10.5 创建点餐订单

`POST /api/v1/dining/orders`，访客可调用；带会员令牌时订单归属会员。HTTP 201。

请求：

```json
{"room_code":"ROOM-01","items":[{"menu_item_id":"menu-noodles","quantity":2}]}
```

`items` 至少一项，单项数量 1–50；同一订单只能包含一个商家的商品。响应是通用订单字段加：

```json
{
  "order_no":"FD202611020001",
  "order_type":"FOOD",
  "status":"PENDING",
  "business_id":"foo_xxx",
  "amount_cents":7600,
  "payment_method":null,
  "created_at":"2026-11-02T12:00:00",
  "paid_at":null,
  "food_order_id":"foo_xxx",
  "fulfillment_status":"NOT_READY",
  "delivered_at":null,
  "exception_reason":null,
  "room_id":"room-01",
  "room_number":"01",
  "items":[{"name_snapshot":"暖汤荞麦面","unit_price_cents":3800,"quantity":2}]
}
```

创建时绑定当次 `room_use_id` 和价格快照。房间空闲/清洁/维护、商家停用、商品缺货或跨商家购物车会被拒绝。

### 10.6 查询点餐订单

`GET /api/v1/dining/orders/{order_no}`，归属校验同通用订单。返回送餐房号、商品快照和履约状态。

`fulfillment_status`：`NOT_READY` 待支付，`QUEUED` 待接单，`ACCEPTED` 已接单，`PREPARING` 制作中，`DELIVERED` 已送达，`EXCEPTION` 前台人工处理。支付时再次校验原 `room_use_id`，不能因房间换客后重新处于使用中就错误送餐。已付款但不可送达进入异常，不自动退款。

### 10.7 商家出餐队列

`GET /api/v1/operations/dining/orders`，`merchant/frontdesk/admin`。返回 `QUEUED/ACCEPTED/PREPARING/DELIVERED` 订单，含 `id`（即 `food_order_id`）、房号、商品、金额、创建/送达时间。

### 10.8 更新履约状态

`POST /api/v1/operations/dining/orders/{food_order_id}/transition`，`merchant/frontdesk/admin`。

```json
{"status":"ACCEPTED","reason":"商家确认接单并更新状态"}
```

仅允许 `QUEUED → ACCEPTED → PREPARING → DELIVERED`。响应：

```json
{"id":"foo_xxx","fulfillment_status":"ACCEPTED","delivered_at":null}
```

非法跳转返回 `409 FULFILLMENT_TRANSITION_INVALID`，重复支付回调不会重复出单。

## 11. 前台房态、分房与加钟

本节均要求 `frontdesk/admin`。

### 11.1 房态看板

`GET /api/v1/operations/rooms/board`

```json
[{"id":"room-01","number":"01","status":"ACTIVE","room_use_id":"use_xxx","booking_id":"pbo_xxx","actual_end_at":"2026-11-02T14:00:00","cleaning_end_at":"2026-11-02T14:30:00"}]
```

`status`：`FREE` 空闲、`ACTIVE` 使用中、`PENDING_CLEANING` 待清洁、`CLEANING` 清洁中、`MAINTENANCE` 维护/人工占用。状态来自预约、实际使用、清洁和占用记录。

### 11.2 到店分房

`POST /api/v1/operations/rooms/bookings/{booking_id}/assign`

```json
{"actual_start":"2026-11-05T10:25:00+08:00","reason":"游客到店，前台复核后续预约","binding_id":"bin_xxx"}
```

`binding_id` 可选；传入时必须是 `BOUND` 手牌绑定，用于关联本次私汤使用。

```json
{"room_use_id":"use_xxx","room_number":"01","status":"ACTIVE","actual_end_at":"2026-11-05T12:25:00","cleaning_end_at":"2026-11-05T12:55:00"}
```

实际使用从分房时间起算购买总时长。晚到导致与下一笔预约冲突且无其他房时，返回 `409 ASSIGNMENT_CONFLICT`，不能强行分房或覆盖已售预约。

### 11.3 结束使用

`POST /api/v1/operations/rooms/uses/{room_use_id}/finish`

```json
{"reason":"前台确认游客使用结束"}
```

响应 `{"room_use_id":"use_xxx","status":"PENDING_CLEANING"}`。结束使用不等于房间立即可售。

### 11.4 开始/完成清洁

- `POST /api/v1/operations/rooms/uses/{room_use_id}/cleaning/start`
- `POST /api/v1/operations/rooms/uses/{room_use_id}/cleaning/complete`

均无请求体。开始清洁响应：

```json
{"room_use_id":"use_xxx","status":"CLEANING","started_at":"2026-11-02T14:01:00"}
```

完成响应：

```json
{"room_use_id":"use_xxx","status":"COMPLETED","completed_at":"2026-11-02T14:31:00"}
```

未确认清洁完成不得再次分房。

### 11.5 创建维修/人工占用

`POST /api/v1/operations/rooms/blocks`，HTTP 201。

```json
{"room_id":"room-03","start_at":"2026-11-05T09:00:00+08:00","end_at":"2026-11-05T12:00:00+08:00","kind":"MAINTENANCE","reason":"设备维护"}
```

`kind` 为 `MAINTENANCE` 或 `MANUAL`；结束时间必须晚于开始时间。响应 `{"id":"blk_xxx","status":"RECORDED"}`。

### 11.6 创建加钟订单

`POST /api/v1/operations/rooms/uses/{room_use_id}/extensions`，HTTP 201。

```json
{"binding_id":"bin_xxx"}
```

要求房间使用中、手牌 `BOUND` 且与本次 `room_use_id` 一致。价格/时长来自 `extension_price_cents`、`extension_minutes` 配置，并重新检查后续占用和清洁区间。

```json
{"extension_id":"ext_xxx","order_no":"EX202611020001","amount_cents":12000,"status":"PENDING","task":null}
```

支付确认后创建加钟占用和 `EXTEND_ROOM` 设备任务，响应中的 `task` 为任务对象。只有真实设备成功回传才将使用/清洁结束时间延长；UNKNOWN 不得重试写卡。加钟价格配置是开发值，正式规则待确认。

## 12. 手牌、押金与柜位

本节均要求 `frontdesk/admin`，普通商家/会员不能调用。

### 12.1 手牌柜位总览

`GET /api/v1/operations/access/overview`

```json
{
  "cards":[{"id":"card-01","physical_uid":"DEV-PHYSICAL-01","status":"AVAILABLE"}],
  "lockers":[{"id":"locker-001","number":"001","status":"FREE"}],
  "deposits":[{"id":"dep_xxx","ticket_id":"tic_xxx","amount_cents":10000,"status":"PAID","refund_id":null}],
  "bindings":[{"id":"bin_xxx","card_id":"card-01","locker_id":"locker-001","deposit_id":"dep_xxx","room_use_id":null,"status":"ISSUING"}],
  "device_tasks":[]
}
```

押金最近 100 条、绑定和设备任务最近 100 条。

### 12.2 创建逐枚押金订单

`POST /api/v1/operations/deposits/orders`，HTTP 201。

```json
{"payer_member_id":"member-demo","ticket_nos":["T-001","T-002"]}
```

一个微信押金订单可以代付多枚，但每枚手牌有独立押金责任和退款号。金额取服务端 `deposit_amount_cents` 快照，不能客户端指定。

```json
{"group_id":"dgr_xxx","order_no":"DP202611020001","amount_cents":20000,"deposit_ids":["dep_1","dep_2"]}
```

押金只能微信支付；支付确认前不能发牌。未退押金不是票款收入。

### 12.3 已收押金但未发牌退款

`POST /api/v1/operations/deposits/{deposit_id}/refund`

```json
{"reason":"已收押金但设备条件不满足，未发牌"}
```

```json
{"deposit_id":"dep_1","refund_no":"DR-dep_1","status":"ACCEPTED"}
```

同一押金重复调用复用同一退款单；原微信交易按该枚实际押金申请部分退款。累计退款不得超过原支付金额。

### 12.4 创建写卡发牌任务

`POST /api/v1/operations/cards/issue`，HTTP 201。

```json
{"deposit_id":"dep_1","card_id":"card-01"}
```

服务端先预占空柜，再创建写卡任务；必须确认该枚押金已支付。

```json
{"binding_id":"bin_xxx","locker_id":"locker-001","status":"ISSUING","task":{"id":"tsk_xxx","task_no":"DT202611020001","task_type":"ISSUE_CARD","status":"PENDING","binding_id":"bin_xxx","card_id":"card-01","locker_id":"locker-001","room_id":null,"payload":{},"raw_error":"","version":1}}
```

设备成功写卡后才正式 `BOUND`；UNKNOWN 不释放柜位、不自动重试。前台应通过设备服务回传结果。

### 12.5 归还手牌并触发逐枚退款

`POST /api/v1/operations/cards/{binding_id}/return`

```json
{"reason":"实物已回收并核对发放记录"}
```

```json
{"binding_id":"bin_xxx","status":"CLEARED","refund_no":"DR-dep_1","refund_status":"ACCEPTED","clear_task":{"id":"tsk_xxx","task_no":"DT202611020002","task_type":"CLEAR_CARD","status":"PENDING","binding_id":"bin_xxx","card_id":"card-01","locker_id":"locker-001","room_id":null,"payload":{},"raw_error":"","version":1}}
```

归还先记录并创建退款/清卡任务。清卡失败不剥夺应退押金，但卡片隔离，不能再发；`refund_status=SUCCESS` 只能由渠道结果证实。

### 12.6 柜位清理完成并释放

`POST /api/v1/operations/lockers/{locker_id}/cleaned`

```json
{"reason":"手牌已回收，柜内已清理"}
```

仅柜位 `CLEANING` 且绑定 `CLEARED/CLEAR_FAILED` 时允许；响应 `{"id":"locker-001","status":"FREE"}`。发卡后同一手牌再次使用仍绑定原柜，不重新分柜。

## 13. Windows 设备任务

所有 `/devices/tasks` 接口仅 `device` 角色。Windows 本地服务主动出站访问后端，Web 和云端不直接访问 USB、DLL 或园区私有端口。

任务对象：

```json
{"id":"tsk_xxx","task_no":"DT202611020001","task_type":"ISSUE_CARD","status":"PENDING","binding_id":"bin_xxx","card_id":"card-01","locker_id":"locker-001","room_id":null,"payload":{},"raw_error":"","version":1}
```

状态：`PENDING` 待领取、`CLAIMED` 已领取、`RUNNING` 执行中、`SUCCEEDED` 成功、`FAILED` 失败、`UNKNOWN` 结果未知。任务类型包括 `ISSUE_CARD`、`CLEAR_CARD`、`EXTEND_ROOM`，另有诊断任务类型。

### 13.1 领取前查询

`POST /api/v1/devices/tasks/poll`

```json
{"worker_id":"frontdesk-pc-01","reader_id":"reader-usb-01"}
```

返回最早的 `PENDING` 任务，无任务返回 `null`；**poll 不等于领取**，仍需调用 claim。

### 13.2 正式领取

`POST /api/v1/devices/tasks/{task_id}/claim`

```json
{"worker_id":"frontdesk-pc-01","reader_id":"reader-usb-01"}
```

同一 worker 重复领取返回原任务；其他 worker 抢占或状态不允许返回 409。

### 13.3 开始执行

`POST /api/v1/devices/tasks/{task_id}/start`

```json
{"worker_id":"frontdesk-pc-01"}
```

仅领取该任务的 worker 可执行，状态变为 `RUNNING`。

### 13.4 回传结果

`POST /api/v1/devices/tasks/{task_id}/result`

```json
{"worker_id":"frontdesk-pc-01","result":"SUCCEEDED","raw_error":""}
```

`result` 仅 `SUCCEEDED/FAILED/UNKNOWN`。相同 worker、相同终态和错误重复上报幂等返回；不同终态返回 `409 DEVICE_RESULT_CONFLICT`。

- 写卡/读回成功只代表适配器定义的操作成功，不能证明柜门或房门实际打开。
- `UNKNOWN` 是未解决终态，不得自动重试写卡、释放预占或重新发牌。
- 设备已动作但 HTTP 回传失败时，本地服务应以同一 `task_id` 重试上报，而不是创建新任务。
- 当前只有 Mock 适配器，真实 SDK/NFC/锁具行为待样机验收。

## 14. 财务、退款、日结与异常

### 14.1 人工订单退款

`POST /api/v1/operations/orders/{order_no}/refunds`，`finance/admin`。

```json
{"reason":"业务方签认的取消或异常退款"}
```

响应：

```json
{"refund_no":"RO-TK202611020001","status":"ACCEPTED","amount_cents":8700}
```

适用范围：门票、私汤的已支付或已付款异常订单；已使用门票、使用中/已完成私汤需另行人工审核。点餐、加钟、充值不走此通用接口；押金走逐枚退款接口。

余额原路退款会按原实际本金/赠送扣款分别冲回并直接 `SUCCESS`；微信退款先 `ACCEPTED`，渠道确认后才 `SUCCESS`。相同 `RO-{order_no}` 幂等复用。

### 14.2 开发退款结果模拟

`POST /api/v1/operations/refunds/{refund_no}/mock-result`，`finance/admin`，仅开发 Mock。

```json
{"status":"SUCCESS"}
```

`status` 可选 `SUCCESS/FAILED/UNKNOWN`。仅 `SUCCESS` 可显示退款成功；失败转异常，UNKNOWN 需继续查询/人工处理。正式微信退款通知和主动查询待接入。

### 14.3 查询会员完整账本

`GET /api/v1/operations/wallet/{member_id}`，`finance/admin`。

```json
{
  "member_id":"member-demo",
  "principal_cents":20000,
  "gift_cents":2000,
  "available_cents":22000,
  "entries":[{
    "id":"led_xxx","entry_type":"RECHARGE","reference":"RC202611020001",
    "principal_delta":20000,"gift_delta":2000,"principal_after":20000,"gift_after":2000,
    "original_entry_id":null,"created_at":"2026-11-02T10:30:00"
  }]
}
```

返回本金、赠送、合计及最近 200 条追加式流水。钱包不存在返回 `404 WALLET_NOT_FOUND`。

### 14.4 日结报表

`GET /api/v1/operations/reports/daily?report_date=YYYY-MM-DD`，`frontdesk/finance/admin`；省略日期时为当天。

```json
{"report_date":"2026-11-02","ticket_revenue_cents":8700,"private_revenue_cents":24000,"dining_revenue_cents":7600,"extension_revenue_cents":0,"recharge_principal_cents":20000,"recharge_gift_cents":2000,"unrefunded_deposit_cents":20000,"deposit_is_revenue":false}
```

充值本金/赠送金为负债，未退押金不是收入。当前尚未实现微信渠道账单下载和差异对账记录。

### 14.5 异常看板

`GET /api/v1/operations/exceptions`，`frontdesk/finance/admin`。

返回五个数组：`refunds`、`paid_exceptions`、`device_unknown`、`room_conflicts`、`food_delivery`。分别覆盖待处理退款、已付款异常订单、设备 UNKNOWN、预约冲突和点餐不可送达；不包含自动补偿/自动退款动作。

### 14.6 审计日志

`GET /api/v1/operations/audit`，仅 `admin`，最近 200 条倒序。

```json
[{"id":"aud_xxx","actor":"admin","action":"CONFIG_UPDATED","entity_type":"business_config","entity_id":"private_slot_price_cents","before_status":"12000","after_status":"13000","reason":"调价","request_id":"req-123","created_at":"2026-11-02T12:00:00"}]
```

记录操作人、动作、实体、前后状态、原因、请求号和时间；不提供修改审计原记录的接口。

## 15. 管理员：商家与商品

本节均要求 `admin`。

### 15.1 商家列表

`GET /api/v1/admin/merchants`，返回全部商家（含停用），按名称排序。

```json
[{"id":"merchant-spring","name":"山泉食坊","active":true,"item_count":3}]
```

`item_count` 为商品总数，与公开接口的可售商品数口径不同。

### 15.2 新增商家

`POST /api/v1/admin/merchants`，HTTP 201。

```json
{"name":"山泉食坊","active":true}
```

响应同商家对象，`item_count=0`。名称去除首尾空格后不能为空。

### 15.3 修改商家

`PATCH /api/v1/admin/merchants/{merchant_id}`，请求同新增；返回 `id/name/active`。停用后公开点餐接口不再返回该商家，且不能创建新订单。

### 15.4 删除商家

`DELETE /api/v1/admin/merchants/{merchant_id}`

```json
{"deleted":true,"id":"merchant_xxx"}
```

商家仍有商品或历史订单时返回 `409 MERCHANT_IN_USE`，应先下架商品并停用，不能破坏历史订单引用。

### 15.5 管理端商品列表

`GET /api/v1/admin/menu-items`，返回全部商品及所属商家，包含下架商品和停用商家的商品。

```json
[{"id":"menu-noodles","merchant_id":"merchant-spring","merchant_name":"山泉食坊","merchant_active":true,"name":"暖汤荞麦面","description":"山泉高汤","category":"主食套餐","image_url":"","price_cents":3800,"stock":100,"available":true}]
```

### 15.6 新增商品

`POST /api/v1/admin/menu-items`，HTTP 201。

```json
{"merchant_id":"merchant-spring","name":"温泉蛋牛肉饭","description":"现做简餐","category":"主食套餐","image_url":"https://cdn.example.com/beef.webp","price_cents":4600,"stock":100,"available":true}
```

| 字段 | 约束 |
|---|---|
| `merchant_id` | 必须存在的商家 |
| `name` | 1–100 字符，去空格后非空 |
| `category` | 默认“热销推荐”，1–50 字符 |
| `image_url` | 可空，最长 500 字符 |
| `price_cents` | 非负整数分 |
| `stock` | 非负整数或 `null`（不限库存） |
| `available` | 是否可售 |

返回完整商品字段。商家不存在返回 `404 MERCHANT_NOT_FOUND`。

### 15.7 修改商品（完整字段）

`PATCH /api/v1/admin/menu-items/{item_id}`，请求与新增相同，可修改商家、名称、分类、价格、库存、图片、描述和可售状态。

### 15.8 修改商品价格/库存（兼容接口）

`POST /api/v1/admin/menu-items/{item_id}`，仅修改部分字段：

```json
{"price_cents":3900,"stock":88,"available":true,"description":"调整后的价格"}
```

响应 `{"id":"menu-noodles","price_cents":3900,"stock":88,"available":true}`。

### 15.9 删除商品

`DELETE /api/v1/admin/menu-items/{item_id}`，返回 `{"deleted":true,"id":"menu_xxx"}`。已有历史订单时 `409 MENU_ITEM_IN_USE`，应改为 `available=false` 下架，不能删除历史快照引用。

## 16. 管理员：价格、活动、房间码与配置

### 16.1 维护指定日期票价

`POST /api/v1/admin/ticket-prices/{visit_date}`

```json
{"adult_cents":4900,"child_cents":2900,"is_holiday":true,"note":"节假日价格"}
```

返回 `visit_date/adult_cents/child_cents/is_holiday`。成交订单保留当时价格快照，后续调价不追溯。

### 16.2 新增或修改充值活动

`POST /api/v1/admin/recharge-activities`

```json
{"id":"recharge-200","name":"轻享礼","principal_cents":20000,"gift_cents":2000,"active":true}
```

`id` 传 `null` 或省略时生成新活动；`principal_cents` 必须大于 0，`gift_cents` 非负。只支持“充 X 赠 Y”，本金/赠送分账。

### 16.3 启用/停用或重印房间码

`POST /api/v1/admin/room-codes/{qr_id}`

```json
{"active":true,"reprint":true}
```

`reprint=true` 时 `version + 1` 并更新 `printed_at`；`active=false` 后房间码不可用于点餐。响应：

```json
{"id":"qr-01","code":"ROOM-01","active":true,"version":2,"printed_at":"2026-11-02T12:00:00"}
```

这里维护的是房间码元数据；正式微信小程序码仍需 AppID 和微信平台生成。

### 16.4 查询业务配置

`GET /api/v1/admin/config`

```json
[{"key":"private_slot_price_cents","value":12000,"description":"私汤单场基础价"}]
```

### 16.5 修改业务配置

`POST /api/v1/admin/config/{key}`

```json
{"value":12000,"description":"私汤单场基础价（开发配置）"}
```

| `key` | 含义 | `value` 单位 |
|---|---|---|
| `private_slot_price_cents` | 私汤单场基础价 | 整数分 |
| `deposit_amount_cents` | 每枚手牌押金 | 整数分；正式金额待确认 |
| `extension_price_cents` | 每次加钟价格 | 整数分；正式规则待确认 |
| `extension_minutes` | 每次加钟时长 | 分钟，必须大于 0 |

其他键或非法值返回 `422 CONFIG_INVALID`。配置变更写入审计，但押金/加钟政策未经业务确认时，开发种子值不能视为正式政策。

## 17. 典型联调流程

### 17.1 门票购买与人工入园

1. `GET /catalog/ticket-prices` 获取服务端价格。
2. `POST /tickets/orders` 创建逐人票订单。
3. `POST /orders/{order_no}/payments` 创建微信支付。
4. 开发环境调用 `POST /payments/{payment_no}/mock-confirm`；生产应由验签回调确认。
5. `GET /tickets/orders/{order_no}` 查询每张 `ticket_no`。
6. 前台逐人调用 `POST /operations/tickets/admit`，不能整单一次性核销。

### 17.2 私汤预约、分房、清洁

1. `GET /rooms/slots`、`GET /rooms/availability` 查询完整区间库存。
2. `POST /rooms/bookings` 创建 15 分钟预占订单。
3. 支付确认后 `GET /rooms/bookings/{booking_id}` 查看确认状态。
4. 到店后前台调用 `/operations/rooms/bookings/{booking_id}/assign`，重新检查实际使用+清洁。
5. 使用结束依次调用 `finish`、`cleaning/start`、`cleaning/complete`。
6. 分房冲突只记录异常，不能强制覆盖下一笔已售预约。

### 17.3 房间点餐

1. `GET /dining/rooms` 选择房间，或扫码获得 `room_code`。
2. `GET /dining/merchants` 选择商家，`GET /dining/menu?merchant_id=...` 加载商品。
3. `POST /dining/orders` 创建同商家订单。
4. 创建支付并等待服务端支付确认。
5. 商家轮询 `/operations/dining/orders`，按顺序接单、制作、送达。
6. 顾客通过 `/dining/orders/{order_no}` 查询；不可送达订单进入人工异常。

### 17.4 手牌押金与设备

1. `POST /operations/deposits/orders` 创建逐枚押金责任。
2. 微信支付确认后 `POST /operations/cards/issue` 预占柜位并创建任务。
3. 设备服务依次 `poll → claim → start → result`。
4. 实物归还调用 `/operations/cards/{binding_id}/return`。
5. 退款渠道确认后查询异常/退款状态；清卡完成后 `/operations/lockers/{locker_id}/cleaned`。

## 18. 常用错误码速查

| 错误码 | 触发场景 |
|---|---|
| `AUTH_REQUIRED` / `AUTH_INVALID` | 未带令牌或令牌无效 |
| `RESOURCE_FORBIDDEN` | 角色无权或访问他人资源 |
| `ORDER_NOT_PAYABLE` | 订单不是待支付状态 |
| `PAYMENT_METHOD_CONFLICT` | 更换订单已有支付方式或误用 Mock 确认 |
| `WECHAT_ONLY` | 充值/押金尝试余额支付 |
| `TICKET_ALREADY_USED` | 已使用门票进入人工退款 |
| `ASSIGNMENT_CONFLICT` | 晚到分房与后续预约/清洁冲突 |
| `ROOM_NOT_AVAILABLE` | 点餐房间无有效使用记录 |
| `SINGLE_MERCHANT_REQUIRED` | 点餐订单跨多个商家 |
| `MERCHANT_UNAVAILABLE` | 停用商家尝试接收新订单 |
| `MENU_ITEM_UNAVAILABLE` | 商品下架、缺货或库存不足 |
| `FULFILLMENT_TRANSITION_INVALID` | 出餐状态跳转不合法 |
| `ORIGINAL_PAYMENT_INVALID` | 原支付未确认或来源不匹配 |
| `REFUND_EXCEEDS_PAYMENT` | 累计退款超过原交易金额 |
| `DEVICE_RESULT_CONFLICT` | 同一任务上报不同终态 |
| `DEVICE_TASK_NOT_RUNNING` | 未开始执行就回传结果 |
| `MERCHANT_IN_USE` / `MENU_ITEM_IN_USE` | 有商品/历史订单仍尝试删除 |
| `CONFIG_INVALID` | 不支持的配置键或值 |

完整业务错误以实际响应 `code/message` 为准；遇到状态冲突不应在客户端自行改状态或创建第二笔交易。

## 19. 开发与生产边界

- 已实现并测试：角色鉴权骨架、会员订单、追加式账本、票券单次入园、完整私汤区间库存、支付幂等分派、点餐房间校验、逐枚押金、设备任务和审计。
- 仅开发模拟：`/auth/dev`、静态 Bearer Token、支付 Mock 确认、退款 Mock 结果、设备 Mock。
- 尚未实现：正式微信 `code2session`、UnionID 安全归并、支付预下单和 `wx.requestPayment` 参数、回调验签、微信退款通知/主动查询、正式 Windows SDK。
- 待业务确认：押金金额与损坏规则、门票/私汤/点餐取消规则、加钟政策、储值余额提现、部署位置。
- 测试环境 SQLite 通过不等同于 MySQL 生产并发验收；真实支付/设备也不能以 Mock 通过代替。

## 20. 开发调用示例

```powershell
$base = "http://127.0.0.1:8000/api/v1"
$headers = @{ Authorization = "Bearer dev-member" }

Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/catalog/ticket-prices?visit_date=2026-11-05"
Invoke-RestMethod "$base/orders" -Headers $headers
```

管理员示例：

```powershell
$admin = @{ Authorization = "Bearer dev-admin"; "Content-Type" = "application/json" }
Invoke-RestMethod "$base/admin/merchants" -Headers $admin
Invoke-RestMethod "$base/admin/merchants" -Method Post -Headers $admin -Body '{"name":"山泉食坊","active":true}'
```

调试时同时记录 HTTP 状态、响应 `code` 和 `X-Request-ID`，不要只记录 `message`。
