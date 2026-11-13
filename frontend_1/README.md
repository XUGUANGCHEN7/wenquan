# 购票会员小程序（uni-app）

基于 uni-app + Vue 3 的微信小程序，包含首页、公共浴池门票、私汤连续场次预约、订单、会员中心与储值。

- 源码位于 `src/`，页面配置在 `src/pages.json`，微信 AppID 在 `src/manifest.json` 的 `mp-weixin.appid`。
- 票价、私汤价格、可售量和余额全部来自服务端。
- 预约不选择房号，到店后由前台分房。
- 园内点餐已移至独立 `frontend_2`，本项目不包含点餐页面。
- `src/config.js` 自动区分微信开发者工具与真机接口地址；真机需使用电脑局域网 IP。
- 会员登录使用微信手机号注册和业务会话，不自动使用演示会员；支付仍为 Mock。

## UI 与主题

- UI 组件库为 **Wot UI v2**：`@wot-ui/ui@2.x`，通过 `src/pages.json` 的 `easycom` 自动引入 `wd-*` 组件。
- 不要混用 v1 的 `wot-design-uni`、`wd-message-box`、`useMessage` 等包名和 API。
- 全局品牌 token 位于 `src/styles/theme.scss`，同时覆盖 Wot UI 的 `--wot-primary-*`、`--wot-text-*` 等语义变量。
- `--sn-gold` 只用于装饰和图形；浅色背景上的金色文字使用对比度更高的 `--sn-gold-ink`。
- 辅助文字使用 `--sn-muted`；小字号正文不要直接使用低对比度的装饰色。
- Sass 设计常量位于 `src/uni.scss`；页面和组件优先使用 `var(--sn-*)` 或这里定义的变量。
- 首页公共组件位于 `src/components/`：品牌轮播、入口卡、模块标题、私汤房卡片。
- 首页轮播图使用 `src/static/home-carousel/home-0x.jpg` 的压缩副本，源文件位于 `backend/media/home-carousel/`；这样轮播不依赖后端在线。
- 首页使用自定义导航栏，其他页面继续使用原生导航栏；底部仍是原生 `tabBar`，图标位于 `src/static/tabbar/`。

`Wot UI` 依赖 `sass`，请保持 `sass@^1.98` 以上。修改主题颜色时优先改 `src/styles/theme.scss` 中的语义变量，不要在业务页面大量使用 `!important`。

```powershell
npm install
npm test
npm run dev:mp-weixin
npm run build:mp-weixin
```

开发构建后，在微信开发者工具导入 `dist/dev/mp-weixin`；生产构建导入 `dist/build/mp-weixin`。不要导入项目根目录（根目录是 uni-app 源码，不是微信原生目录）。

微信登录代码已接入，须配置服务端 AppID/AppSecret、完成旧库迁移并真机验证；正式支付适配器和支付结果服务端查询仍待实现，发布前关闭开发 Mock。uni-app 编译通过不等于真机业务验收。

手机号注册、旧库备份迁移及新增接口见 [会员登录说明](../docs/member-login.md)。
