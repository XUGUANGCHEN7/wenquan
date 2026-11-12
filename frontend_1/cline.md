# 购票会员小程序启动说明

## 项目路径

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1
```

## 项目类型

uni-app + Vue 3，微信小程序编译目标为 `mp-weixin`。

## 首次安装

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1
npm install
```

## 开发启动

先确保后端运行在 `8000` 端口，然后执行：

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1
npm run dev:mp-weixin
```

保持该终端运行，等待出现：

```text
DONE Build complete.
```

微信开发者工具导入：

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1\dist\dev\mp-weixin
```

**不要导入 `frontend_1` 根目录。** 根目录是 uni-app 源码，不是微信小程序原生目录。

## 生产构建

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1
npm run build:mp-weixin
```

微信开发者工具导入：

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1\dist\build\mp-weixin
```

## 测试

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1
npm test
```

## 环境配置

- 微信 AppID：`src/manifest.json` 的 `mp-weixin.appid`
- API 地址：`src/config.js`
- 开发者工具自动使用 `127.0.0.1`，真机自动使用 `lanApiBase`
- 当前局域网后端地址：`http://192.168.43.235:8000/api/v1`

电脑 IP 变化后，需要修改 `src/config.js` 中的 `lanApiBase`，然后重新编译。

## 页面

- `pages/home/index` 首页
- `pages/tickets/index` 门票
- `pages/private-room/index` 私汤预约
- `pages/orders/index` 订单
- `pages/mine/index` 会员
- `pages/wallet/index` 储值

## 注意

- 当前是开发令牌 + Mock 支付，不是真实扣款。
- 真机需和后端电脑处于同一局域网，并允许防火墙入站。
- uni-app 编译成功不等于微信真机验收。
