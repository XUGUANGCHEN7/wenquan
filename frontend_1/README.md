# 购票会员小程序（uni-app）

基于 uni-app + Vue 3 的微信小程序，包含首页、公共浴池门票、私汤连续场次预约、订单、会员中心与储值。

- 源码位于 `src/`，页面配置在 `src/pages.json`，微信 AppID 在 `src/manifest.json` 的 `mp-weixin.appid`。
- 票价、私汤价格、可售量和余额全部来自服务端。
- 预约不选择房号，到店后由前台分房。
- 园内点餐已移至独立 `frontend_2`，本项目不包含点餐页面。
- `src/config.js` 自动区分微信开发者工具与真机接口地址；真机需使用电脑局域网 IP。
- 开发环境明确启用开发令牌和 Mock 支付，生产必须替换。

```powershell
npm install
npm test
npm run dev:mp-weixin
npm run build:mp-weixin
```

开发构建后，在微信开发者工具导入 `dist/dev/mp-weixin`；生产构建导入 `dist/build/mp-weixin`。不要导入项目根目录（根目录是 uni-app 源码，不是微信原生目录）。

正式发布前必须实现正式微信登录、支付适配器和支付结果服务端查询，并关闭开发 Mock。uni-app 编译通过不等于真机业务验收。
