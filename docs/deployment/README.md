# Cloudflare Deployment / Cloudflare 部署

## Workers Builds values / Workers Builds 配置

- Root Directory: `.` (repository root) / 仓库根目录
- Build Command: `pip install uv && cd web && npm ci && npm run build`
- Deploy Command: `uv run pywrangler deploy`
- Vite output directory: `web/dist` (Workers Static Assets; not a Pages output setting) / Vite 输出目录（Workers Static Assets，不是 Pages 输出设置）

The root Wrangler config selects `backend/worker.py` and enables `python_workers`; it serves React assets and FastAPI from the same Worker. Pywrangler is required to vendor the Python dependencies from `pyproject.toml`; the configured pre-bundle script adds the existing Python core modules. No `BACKEND_ORIGIN`, Render service, extra database, or durable storage is used. / 根目录 Wrangler 配置选择 `backend/worker.py` 并启用 `python_workers`；React 静态资源和 FastAPI 由同一 Worker 提供。必须使用 Pywrangler 打包 `pyproject.toml` 中的 Python 依赖；打包前脚本会加入现有 Python 核心模块。无需配置 `BACKEND_ORIGIN`、Render 服务、数据库或持久化存储。

## Cloudflare variables and secrets / Cloudflare 变量和机密

1. In Cloudflare Dashboard → **Workers & Pages** → `cloudcore-retention-demo` → **Settings** → **Variables and Secrets**, add `AZURE_OPENAI_API_KEY` as a **Secret**. Do not add it to GitHub or any frontend `VITE_*` variable. / 在 Cloudflare Dashboard → **Workers & Pages** → `cloudcore-retention-demo` → **Settings** → **Variables and Secrets**，将 `AZURE_OPENAI_API_KEY` 添加为 **Secret**。不要提交到 GitHub，也不要设为前端 `VITE_*` 变量。
2. To enable uploaded synthetic CSV files beyond the bundled exact dataset, add non-secret variable `ALLOW_UPLOADED_SYNTHETIC_ANALYSIS=true`. Files with customer IDs outside the synthetic `SIM*`/`SYN*` pattern remain blocked. Default: off. / 如需启用捆绑原文件以外的模拟 CSV，添加非敏感变量 `ALLOW_UPLOADED_SYNTHETIC_ANALYSIS=true`。客户 ID 不符合 `SIM*`/`SYN*` 的文件仍会被拒绝。默认关闭。
3. The Worker has no login or access code because this is an intentionally public, short-term concept demo. Do not upload real CloudCore customer/course data. / 此项目为短期公开概念演示，不设登录和访问码。请勿上传 CloudCore 真实客户或课程数据。

After adding/changing a Secret or variable, trigger a new deployment so the new Worker version receives it. GitHub push may trigger the connected Workers Build automatically. / 添加或修改 Secret、变量后，触发一次新部署使新 Worker 版本生效。连接 GitHub 的 Workers Build 可由推送自动触发。

## Local preflight / 本地部署前检查

```powershell
.venv\Scripts\python.exe -m pytest tests --basetemp .pytest-tmp
cd web
npm test
npm run build
cd ..
uv run pywrangler deploy --dry-run
```

The preflight does not publish a deployment. Production deployment remains the connected Cloudflare Workers Build. / 前置检查不会发布部署；正式部署仍由 Cloudflare Workers Build 执行。
