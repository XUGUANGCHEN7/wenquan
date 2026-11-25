# 购票小程序手机号会员登录

本次只接入购票端 frontend_1，点餐端 frontend_2 及其游客微信支付规则保持现状。源码位于 `C:\Users\16861\.cline\worktrees\82ef6\wenquan`。

## 已接入的流程

首次打开小程序进入首页，可先浏览；登录/注册入口位于“我的”页。点击“微信登录 / 注册”后，已有已验证会员直接登录原账户；新用户或旧会员缺少手机号时，填写可选昵称、阅读手机号使用说明，再主动授权手机号完成注册。空昵称的新会员使用“会员＋手机号后四位”。会员中心展示真实昵称、脱敏手机号和本人余额，支持退出登录。

后端把微信身份映射到会员，创建唯一的零余额钱包；同一身份再次登录不重复开户。旧会员补手机号保留原会员ID和余额。手机号已属于另一会员时拒绝自动合并，转商家核验。点餐端正式跨应用身份关联不属于本次交付。

注册凭证有效期10分钟，只能完成注册；会员会话默认7天、可退出撤销，数据库仅存凭证哈希。购票端不再自动使用 dev-member。共享后端仍保留原开发入口供员工和未修改的点餐端演示使用，正式环境原有的开发令牌禁用规则继续生效。

## 本机微信配置

2026年11月12日检查当前后端配置时，购票端 AppID、AppSecret 均未配置。只在后端环境变量或项目根目录的本机 `.env` 填写：

```dotenv
WECHAT_TICKET_APPID=填写与frontend_1的manifest中mp-weixin.appid一致的值
WECHAT_TICKET_APPSECRET=仅在本机后端填写真实密钥
MEMBER_SESSION_SECONDS=604800
```

AppSecret 不放进 manifest、小程序包、Git 或聊天。微信公众平台需开通该 AppID 对应的手机号能力，并完成实际使用所需的隐私声明。真实环境为小程序配置后端 HTTPS 合法请求域名；现有局域网 HTTP 地址只供开发调试。修改配置后重启后端。没有配置时接口返回 WECHAT_NOT_CONFIGURED，不能成功注册为演示会员。

## 旧数据库升级

先停止正在运行的后端，再备份和迁移。不要删除数据库，也不要以重新建库代替迁移。

当前本地 `backend\wenquan.sqlite3` 的会员表仍为旧三列，未登记 Alembic 版本。只读对比发现原有34张表中，除新增的 member_sessions 表外，其余表的列结构均与初始迁移一致；member_sessions 可能由开发启动的 create_all 创建，新迁移会先校验并复用该表。

仅针对这份已核对的本地旧 SQLite 库，关闭后端后执行：

```powershell
Set-Location 'C:\Users\16861\.cline\worktrees\82ef6\wenquan\backend'
$memberBackup = 'wenquan.before-member-login-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.sqlite3'
Copy-Item -LiteralPath '.\wenquan.sqlite3' -Destination $memberBackup -ErrorAction Stop
..\.venv\Scripts\python.exe -m alembic stamp af3dbb89f3d4
..\.venv\Scripts\python.exe -m alembic upgrade head
```

`stamp` 只登记已核对的旧结构，不执行建表；不适用于其他未知结构数据库。新数据库或已正确登记版本的数据库只执行 `alembic upgrade head`。MySQL 上按既有流程先备份，再升级；本次未执行 MySQL 实库迁移。当前本地库没有被本次迁移命令修改，需按上述步骤升级后再启动应用；create_all 不会为已有表补列。

## 启动与联调

```powershell
Set-Location 'C:\Users\16861\.cline\worktrees\82ef6\wenquan\backend'
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
```

另开终端启动小程序构建：

```powershell
Set-Location 'C:\Users\16861\.cline\worktrees\82ef6\wenquan\frontend_1'
npm run dev:mp-weixin
```

微信开发者工具导入该目录下的 `dist\dev\mp-weixin`。生产编译命令为 `npm run build:mp-weixin`，产物为 `dist\build\mp-weixin`。本次已经生成生产构建包，但没有发布小程序。

## 新增接口

| 方法与地址 | 行为 |
| --- | --- |
| POST /api/v1/auth/wechat/login | code 换微信身份，返回会员会话或 REGISTER_REQUIRED 与注册凭证 |
| POST /api/v1/auth/wechat/register | 注册凭证＋手机号授权code＋选填昵称＋consent=true，注册或补全会员 |
| GET /api/v1/members/me | 从当前会话读取本人资料，返回脱敏手机号 |
| POST /api/v1/auth/logout | 撤销当前会员会话 |

登录 code 与手机号 code 不混用，均由后端调用微信验证；客户端不能指定会员ID或直接提交手机号建立身份。正式 OpenAPI 随服务生成，仓库文档快照同步更新。

## 验证边界

自动化测试覆盖注册、重复登录、零余额钱包、手机号冲突、注册凭证隔离、拒绝授权、退出/过期/停用、旧账户补手机号保留余额、真实会员购票、微信HTTP请求参数与错误脱敏、旧库迁移、会话失效及分享页面跳转。外部微信HTTP使用测试替身；这些结果不代表真实手机号授权已验证。

最后需要在配置后的真机核验：首次注册、再次进入原会员、拒绝手机号后重试、退出后停留登录页、分享直达返回原页面、会员中心展示本人资料。现有微信支付仍为开发 Mock，本次没有接入或改变真实支付。
