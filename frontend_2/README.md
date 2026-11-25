# 独立私汤房点餐小程序（uni-app）

从每间私汤房二维码进入的独立 uni-app + Vue 3 微信小程序。AppID 占位 `wx0000000000000002`，不得与购票会员端共用。

- 源码位于 `src/`，页面配置在 `src/pages.json`，微信 AppID 在 `src/manifest.json` 的 `mp-weixin.appid`。
- 房间码 scene：`ROOM-01` 至 `ROOM-17`，或链接 `?scene=ROOM-01`；进入后也可在顶部选择送餐房间。
- 点餐页左侧为营业商家，右侧为该商家商品；切换商家会清空当前购物车。
- `src/config.js` 自动区分开发者工具/真机地址；真机需与电脑同一 Wi-Fi，并使用电脑局域网 IP。
- 加载失败会在页面保留错误原因和“重新加载”按钮。
- 任何扫码者可浏览菜单并使用本人微信支付；会员余额必须明确登录后才可选。
- 订单展示送达房号、商家接单/制作/已送达状态；无法送达时只显示前台人工处理。
- 开发环境使用 Mock 支付并清楚标注，不产生真实微信扣款。

```powershell
npm install
npm test
npm run dev:mp-weixin
npm run build:mp-weixin
```

开发构建后，在微信开发者工具导入 `dist/dev/mp-weixin`；生产构建导入 `dist/build/mp-weixin`。不要导入项目根目录。

真实微信登录、AppID/OpenID 绑定、UnionID 可用性、商户号和支付能力仍需甲方与微信平台确认并在开发者工具/真机联调。
