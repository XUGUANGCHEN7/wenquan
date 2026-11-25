# 私汤点餐小程序启动说明

## 项目路径

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2
```

## 项目类型

uni-app + Vue 3，微信小程序编译目标为 `mp-weixin`。

## 首次安装

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2
npm install
```

## 开发启动

先确保后端运行在 `8000` 端口，然后执行：

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2
npm run dev:mp-weixin
```

保持该终端运行，等待：

```text
DONE Build complete.
```

微信开发者工具导入：

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2\dist\dev\mp-weixin
```

**不要导入 `frontend_2` 根目录。**

## 生产构建

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2
npm run build:mp-weixin
```

微信开发者工具导入：

```text
C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2\dist\build\mp-weixin
```

## 测试

```powershell
cd C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_2
npm test
```

## 环境配置

- 微信 AppID：`src/manifest.json` 的 `mp-weixin.appid`
- API 地址：`src/config.js`
- 开发者工具使用 `127.0.0.1`
- 真机使用 `lanApiBase`，当前为 `http://192.168.43.235:8000/api/v1`

电脑 IP 变化后，修改 `src/config.js` 的 `lanApiBase` 并重新编译。

## 页面

- `pages/room/index` 房间点餐（房间选择、左侧商家、右侧商品）
- `pages/orders/index` 点餐订单
- `pages/mine/index` 会员/余额

## 重要说明

- 房间码 scene 为 `ROOM-01` 至 `ROOM-17`。
- 真机需要与后端电脑同一局域网。
- 房间无有效使用记录时只能浏览菜单，不能下单。
- 当前微信支付、会员登录和设备均为开发 Mock。
