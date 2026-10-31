# Cloudflare Deployment / Cloudflare 部署

## Workers Builds values / Workers Builds 配置

- Root Directory: `.` (repository root) / 仓库根目录
- Build Command: `pip install uv && cd web && npm ci && npm run build`
- Deploy Command: `uv run pywrangler deploy`
- Vite output directory: `web/dist` (Workers Static Assets; not a Pages output setting) / Vite 输出目录（Workers Static Assets，不是 Pages 输出设置）

The root Wrangler config selects `backend/worker.py` and enables `python_workers`; it serves React assets and FastAPI from the same Worker. Pywrangler is required to vendor the Python dependencies from `pyproject.toml`; the configured pre-bundle script adds the existing Python core modules. No `BACKEND_ORIGIN`, Render service, extra database, or durable storage is used. / 根目录 Wrangler 配置选择 `backend/worker.py` 并启用 `python_workers`；React 静态资源和 FastAPI 由同一 Worker 提供。必须使用 Pywrangler 打包 `pyproject.toml` 中的 Python 依赖；打包前脚本会加入现有 Python 核心模块。无需配置 `BACKEND_ORIGIN`、Render 服务、数据库或持久化存储。

## Cloudflare variables and secrets / Cloudflare 变量和机密

1. In Cloudflare Dashboard → **Workers & Pages** → `cloudcore-retention-demo` → **Settings** → **Variables and Secrets**, add `AZURE_OPENAI_API_KEY` as a **Secret**. Do not add it to GitHub or any frontend `VITE_*` variable. / 在 Cloudflare Dashboard → **Workers & Pages** → `cloudcore-retention-demo` → **Settings** → **Variables and Secrets**，将 `AZURE_OPENAI_API_KEY` 添加为 **Secret**。不要提交到 GitHub，也不要设为前端 `VITE_*` 变量。
2. The Worker has no login or access code. Any visitor can upload a schema-valid CSV and click **Run AI Analysis**; use this only for data whose external processing is authorized. The initial page dataset remains the bundled synthetic CSV. / Worker 不设登录或访问码。任何访问者都可上传符合 Schema 的 CSV 并点击 **Run AI Analysis**；仅可对已获外部处理授权的数据使用此功能。页面初始数据仍为捆绑模拟 CSV。

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
