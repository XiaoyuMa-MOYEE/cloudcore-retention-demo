# Deployment Guide / 部署说明

This guide describes configuration and preflight only. No Cloudflare or API-host deployment is performed. / 本文说明配置和部署前检查，不执行 Cloudflare 或 API 主机部署。

## Architecture / 架构

A single Cloudflare Worker serves the Vite Static Assets and forwards `/api/*` to the independent FastAPI Docker service on a persistent disk. The current FastAPI app uses SQLite plus per-task source, checkpoint and result files. Although Python Workers support FastAPI, isolate-local files do not provide the durable storage this app requires. Moving it to Cloudflare storage would require a broader backend redesign, so Python Offer/Reason, validation, Azure Message generation, task status and recovery remain in the existing container. / 单个 Cloudflare Worker 同时托管 Vite 静态资源，并将 `/api/*` 转发至挂载持久盘的独立 FastAPI Docker 服务。当前 FastAPI 使用 SQLite 及逐任务输入、检查点和结果文件。虽然 Python Workers 支持 FastAPI，但隔离实例本地文件无法满足本项目的持久化要求。迁移到 Cloudflare 存储会扩大后端重构，因此 Python Offer/Reason、校验、Azure Message 生成、任务状态和恢复仍在现有容器运行。

## 1. API host / API 主机

1. Create the independent service from `render.yaml` / `Dockerfile` on a host with a persistent disk mounted at `/var/data`. / 使用 `render.yaml` 或 `Dockerfile` 创建独立服务，并将持久盘挂载到 `/var/data`。
2. Configure server-only Secrets `GROUP_ACCESS_CODE`, `SESSION_SECRET`, and `AZURE_OPENAI_API_KEY`. Set `PUBLIC_ORIGIN=https://cloudcore.moyee.uk`, `COOKIE_SECURE=true`, and `ALLOW_UPLOADED_SYNTHETIC_ANALYSIS=false`. / 在服务端配置 Secret：`GROUP_ACCESS_CODE`、`SESSION_SECRET`、`AZURE_OPENAI_API_KEY`；设置 `PUBLIC_ORIGIN=https://cloudcore.moyee.uk`、`COOKIE_SECURE=true`、`ALLOW_UPLOADED_SYNTHETIC_ANALYSIS=false`。
3. Keep the persistent disk enabled, then verify `/api/health`. Use synthetic data only. / 确保持久盘已启用，再验证 `/api/health`。仅使用模拟数据。

## 2. Cloudflare Workers Builds / Cloudflare Workers Builds 设置

For the connected Worker `cloudcore-retention-demo`, set:

- Root directory: `web`
- Build command: `npm run build`
- Deploy command: `npx wrangler deploy` (or `npm run deploy`)

The Vite output is `web/dist`; `web/wrangler.jsonc` declares `./dist` as Static Assets. This is a Workers project, not a Pages project, so do not set a Pages output directory. Replace the Hugo build command with the command above. / Vite 产物位于 `web/dist`；`web/wrangler.jsonc` 将相对 `web` 根目录的 `./dist` 声明为静态资源。本项目使用 Workers，不是 Pages 项目，因此不设置 Pages 输出目录。请将 Hugo 构建命令替换为上述命令。

Set the non-secret runtime variable `BACKEND_ORIGIN` in Worker Settings > Variables and Secrets to the FastAPI service's HTTPS origin without a trailing slash. `web/wrangler.jsonc` sets `keep_vars: true` so this dashboard-managed value survives Wrangler deployments. If it is missing, the proxy returns 503. Azure key, group access code, and session secret belong only in the FastAPI host's Secrets, never in Worker variables. / 在 Worker Settings > Variables and Secrets 将非敏感运行时变量 `BACKEND_ORIGIN` 设置为 FastAPI 服务的 HTTPS 根地址，末尾不加斜杠。`web/wrangler.jsonc` 设置 `keep_vars: true`，确保 Wrangler 部署保留此控制台变量；若未配置，代理返回 503。Azure key、组内访问码和会话密钥仅放在 FastAPI 主机 Secrets，不得放入 Worker variables。

`web/wrangler.jsonc` routes only `cloudcore.moyee.uk/*` in zone `moyee.uk`. It does not match `moyee.uk/*` or change the personal-site Worker. / `web/wrangler.jsonc` 仅路由 `moyee.uk` 区域下的 `cloudcore.moyee.uk/*`，不会匹配 `moyee.uk/*`，也不会修改个人主站 Worker。

## 3. Local checks / 本地检查

From `web`, run `npm ci`, `npm run build`, `npm test`, and `npm run deploy:check`. The last command is Wrangler's `--dry-run`; it bundles and validates without deploying. Do not run `npx wrangler deploy` until the API host and `BACKEND_ORIGIN` are configured and reviewed. / 在 `web` 目录执行 `npm ci`、`npm run build`、`npm test` 和 `npm run deploy:check`。最后一项使用 Wrangler `--dry-run`，只打包和校验，不部署。API 主机与 `BACKEND_ORIGIN` 配置并审查前，不要运行 `npx wrangler deploy`。

After a separately authorized deployment, verify the homepage, `/api/health`, login cookie attributes, unauthenticated API rejection, and that page load does not start analysis. / 单独授权部署后，验证首页、`/api/health`、登录 Cookie 属性、未认证 API 请求被拒，以及页面加载不会启动分析。

## 4. Synthetic-only acceptance / 模拟数据验收

The Azure end-to-end run is a separate billable action and may use only the bundled 45-row synthetic CSV. Confirm 45 completed rows, zero failures, and the exact seven output columns. Never send actual CloudCore customer/course data without separate authorization and service-side governance. / Azure 端到端运行是单独的计费操作，只能使用随项目提供的 45 行模拟 CSV。确认 45 条完成、失败数为 0、输出列严格为七列。未经单独授权和服务端治理，不得发送 CloudCore 真实客户/课程数据。

The persistent `/var/data` volume holds task state, source uploads, checkpoints and outputs. Follow the group's approved retention schedule for manual cleanup. / 持久卷 `/var/data` 保存任务状态、上传源文件、检查点和输出；按小组批准的保留计划手动清理。
