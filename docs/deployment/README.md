# Deployment Guide / 部署说明

Local files only: no domain changes, GitHub push, Cloudflare deployment, or API hosting deployment have been performed. / 本文仅提供本地部署材料；目前未修改域名、未推送 GitHub、未部署 Cloudflare 或 API 主机。

## Architecture / 架构

Use Cloudflare Pages for the Vite static bundle, a Cloudflare Worker route for `/api/*`, and an independent FastAPI Docker service with a persistent disk. This keeps the tested Python Core and its checkpoint semantics. Do not configure a Python Worker as the API host: its local filesystem is ephemeral per isolate. / 使用 Cloudflare Pages 托管 Vite 静态文件，Cloudflare Worker 代理 `/api/*`，FastAPI Docker 服务运行于独立主机并挂载持久盘。这样可保留已测试 Python Core 和检查点机制。不要将 Python Worker 配成 API 主机，其本地文件系统按隔离实例易失。

## 1. Configure and deploy the API service / 配置并部署 API 服务

1. Create a new service from this project's independent repository; use `render.yaml` / `Dockerfile`. Pick a host/runtime with a persistent mounted disk. `/var/data` must survive container restarts. / 从本项目独立仓库新建服务，使用 `render.yaml` 或 `Dockerfile`，选择支持持久挂载盘的运行主机；`/var/data` 必须在容器重启后保留。
2. Set server-only Secrets in the API host: `GROUP_ACCESS_CODE`, `SESSION_SECRET`, `AZURE_OPENAI_API_KEY`. Generate a long random session value, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Do not place any of these in Pages variables. / 在 API 主机配置服务端 Secret：`GROUP_ACCESS_CODE`、`SESSION_SECRET`、`AZURE_OPENAI_API_KEY`。会话密钥用随机值生成；这些密钥不得放进 Pages 变量。
3. Set `PUBLIC_ORIGIN=https://cloudcore.moyee.uk`, `COOKIE_SECURE=true`, and keep `ALLOW_UPLOADED_SYNTHETIC_ANALYSIS=false`. / 设置 `PUBLIC_ORIGIN`、`COOKIE_SECURE=true`，保持上传分析关闭。
4. Confirm `config.yaml` contains the desired Azure provider, deployment name and batch size before building. Never configure a user-selectable model endpoint. / 构建前确认 `config.yaml` 中的 Azure Provider、部署名和 batch size。不要配置用户可选择的模型 Endpoint。
5. Confirm `/api/health` returns `{"status":"ok"}`. Do not use real CloudCore data for testing. / 确认 `/api/health` 返回成功；测试不得使用 CloudCore 真实数据。

## 2. Build Cloudflare Pages / 构建 Cloudflare Pages

Create a Pages project for the independent repository with root directory `web`, build command `npm ci && npm run build`, output directory `dist`. Do not add Azure keys, group access code, or session secrets to the build environment. Attach the custom domain `cloudcore.moyee.uk` in Pages. / 为独立仓库创建 Pages 项目，根目录 `web`，构建命令 `npm ci && npm run build`，输出目录 `dist`。构建环境不得配置 Azure key、访问码或会话 Secret。在 Pages 绑定自定义域 `cloudcore.moyee.uk`。

## 3. Configure API route proxy / 配置 API 路由代理

1. Edit `deploy/cloudflare/wrangler.jsonc` and replace `BACKEND_ORIGIN` with the API service origin, without a trailing slash. / 编辑 `deploy/cloudflare/wrangler.jsonc`，将 `BACKEND_ORIGIN` 替换为 API 主机来源，不加末尾斜线。
2. Verify the route is exactly `cloudcore.moyee.uk/api/*` and zone `moyee.uk`. It must not be widened to `moyee.uk/*` or another hostname. / 核对路由严格为 `cloudcore.moyee.uk/api/*`、zone 为 `moyee.uk`；不可扩展到 `moyee.uk/*` 或其他主机名。
3. Install/use Wrangler, review the exact config and then deploy from the project root: `npx wrangler deploy --config deploy/cloudflare/wrangler.jsonc`. This step is intentionally left to the project owner. / 安装或使用 Wrangler，审查配置后在项目根目录运行部署命令；此步骤由项目所有者自行执行。
4. Verify Pages home, `/api/health`, login Cookie attributes, unauthenticated API rejection, and that a page reload does not start an analysis. / 验证 Pages 首页、健康接口、登录 Cookie 属性、未认证接口拒绝，以及刷新页面不会触发模型调用。

The Worker forwards only same-origin `/api/*` traffic to the configured backend. It does not read or store API keys or customer data. Set `BACKEND_ORIGIN` as a non-secret Worker variable; never put access credentials there. / Worker 仅转发同源 `/api/*` 请求，不读取或保存 Azure 密钥或客户数据。`BACKEND_ORIGIN` 是非敏感 Worker 变量，不得将访问凭据写在此处。

## 4. Synthetic-only acceptance / 模拟数据验收

1. Log in using the group code. / 使用组内访问码登录。
2. Confirm the badge says Synthetic Data and Human Approval Required. / 确认页面显示 Synthetic Data 和 Human Approval Required。
3. Click Run AI analysis to send the bundled 45-row synthetic CSV to Azure. This can incur token charges. / 点击 Run AI analysis，才会将随项目提供的 45 条模拟记录发送 Azure；可能产生 token 费用。
4. Verify all 45 messages complete, failed count is zero, CSV has seven ordered output columns, and messages meet V0.2.1 constraints. / 检查 45 条全部完成、失败数为零、CSV 七列顺序正确且消息符合 V0.2.1 规则。
5. Never test this demo with actual CloudCore customer/course data unless separate authorization has been granted and service-side governance has been reviewed. / 未取得单独授权并完成服务端治理审查前，禁止用 CloudCore 真实客户/课程数据测试。

## 5. Operational storage / 运行存储

Mount the persistent disk at `/var/data`. It contains SQLite task state, per-task uploaded source, checkpoints and output files. Back it up using the hosting provider's approved method. No retention/deletion job is implemented yet; operators should remove completed task folders according to the group's approved retention schedule. / 持久盘挂载到 `/var/data`，其中保存任务 SQLite 状态、任务输入、检查点和结果。按主机提供的方式备份。当前未实现自动清理，运维人员应按小组批准的数据保留规则删除已完成任务目录。
