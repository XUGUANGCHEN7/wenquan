# 运营 Web 启动说明

## 项目路径

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_web
```

## 项目类型

Vue 3 + TypeScript + Vite + Pinia 运营工作台。

## 首次安装

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_web
Copy-Item .env.example .env
npm install
```

如 `.env` 已存在，不要覆盖。

默认接口配置：

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 启动开发服务

先确保后端已在 `8000` 端口运行，然后执行：

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_web
npm run dev
```

访问：

```text
http://localhost:5173
```

开发脚本已使用 `vite --host 0.0.0.0`，同一局域网设备也可通过电脑 IP 访问。

## 生产构建

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_web
npm run build
```

构建产物：

```text
frontend_web/dist
```

## 类型检查与测试

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_web
npm run typecheck
npm test
```

## 页面入口

| 路径 | 页面 |
|---|---|
| `/login` | 登录/选择角色 |
| `/` | 运营总览 |
| `/tickets` | 票券核验 |
| `/rooms` | 私汤房态 |
| `/dining` | 商家出餐 |
| `/access` | 手牌柜位 |
| `/wallet` | 会员账本 |
| `/exceptions` | 异常看板 |
| `/reports` | 日结报表 |
| `/merchants` | 商家商品 |
| `/settings` | 规则配置 |

## 注意事项

- 后端未开启时，页面会显示网络或鉴权错误。
- 当前登录是开发角色选择，不是正式身份认证。
- 真实微信支付、退款和设备联调尚未完成。
- 管理员才能访问“商家商品”和“规则配置”。
