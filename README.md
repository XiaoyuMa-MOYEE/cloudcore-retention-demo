# CloudCore Person 3 — Short-lived Demo / 短期演示

This is a public, short-term concept demo for a small project group. It runs as one Cloudflare Worker: React/Vite static assets plus a Python/FastAPI API. There is no login, task database, persistent upload storage, checkpoint store, or server-side result retention. / 本项目是供小组使用的短期公开概念演示。React/Vite 静态页面和 Python/FastAPI API 同属一个 Cloudflare Worker。不设置登录、任务数据库、上传文件持久化、检查点存储或服务端结果留存。

The Worker reuses the existing Python input validation, O1–O4 Playbook, Offer/Reason, internal analysis, batching, prompt and Message validation. Azure creates Message only. Uploads are held in request memory; users download the returned seven-column `offers.csv` to keep it. / Worker 复用现有 Python 输入校验、O1–O4 Playbook、Offer/Reason、内部分析、分批、Prompt 和 Message 校验。Azure 仅生成 Message。上传文件只在请求期间处理；用户下载七列 `offers.csv` 自行保存。

Valid support tiers are configured in `config.yaml`: `Basic`, `Standard`, `Premium`, and `Enterprise`. Only `Basic` triggers O1; the other tiers continue through the same MRR and Tenure rules. / `config.yaml` 配置四种有效支持等级：`Basic`、`Standard`、`Premium`、`Enterprise`。只有 `Basic` 触发 O1；其余等级均继续执行相同的 MRR 和 Tenure 规则。

## Local run / 本地运行

```powershell
cd web
npm ci
npm run build
cd ..
python -m pip install -r requirements-local.txt
uvicorn backend.cloudflare_app:app --reload
```

For local Azure calls, set `AZURE_OPENAI_API_KEY` in the ignored root `.env` or process environment. The production key belongs in Cloudflare Worker Secrets. / 本地调用 Azure 时，将 `AZURE_OPENAI_API_KEY` 放入根目录被 Git 忽略的 `.env` 或进程环境；线上 Key 配置为 Cloudflare Worker Secret。

## Cloudflare Workers Builds / 构建设置

- Root Directory: `.` (repository root) / 项目根目录
- Build Command: `pip install uv && cd web && npm ci && npm run build`
- Deploy Command: `uv run pywrangler deploy`
- Static build output: `web/dist` / 静态产物目录

The Python Worker entry is `backend/worker.py`, with the `python_workers` compatibility flag. The Wrangler pre-bundle command copies the unchanged Python core to Pywrangler's generated module directory. The Vite build copies non-secret `config.yaml` and the reviewed synthetic CSV to Worker static assets. Cloudflare serves the page and Python API from the same Worker; no `BACKEND_ORIGIN`, Render service, or separate API host is required. / Python Worker 入口为 `backend/worker.py`，配置 `python_workers` compatibility flag。Wrangler 打包前会将未改写的 Python 核心复制到 Pywrangler 生成的模块目录；Vite 构建将不含密钥的 `config.yaml` 和审核过的模拟 CSV 复制为 Worker 静态资源。页面和 Python API 由同一个 Worker 提供，无需 `BACKEND_ORIGIN`、Render 服务或独立 API 主机。

## Cloudflare settings / Cloudflare 设置

1. In Worker **Settings → Variables and Secrets**, add Secret `AZURE_OPENAI_API_KEY` using the Azure key value. Never put it in source or Vite configuration. / 在 Worker **Settings → Variables and Secrets** 中新增 Secret `AZURE_OPENAI_API_KEY` 并填写 Azure Key；不要写入源代码或 Vite 配置。
2. The page initially displays the bundled synthetic dataset. A user-uploaded CSV that passes input validation can be analyzed after **Run AI Analysis** is clicked. Uploading only validates and displays the CSV; it does not call Azure. / 页面初始显示捆绑模拟数据。用户上传的 CSV 通过输入校验后，可在点击 **Run AI Analysis** 时进行分析。上传操作仅校验并显示 CSV，不会调用 Azure。
3. Trigger a Workers build from the connected GitHub repository. No personal-site Astro Worker settings need to change. / 从已连接的 GitHub 仓库触发 Workers 构建；无需更改个人主站 Astro Worker。

## Data and limits / 数据与限制

- Page load displays only the bundled synthetic dataset; no Azure call occurs until **Run AI Analysis** is clicked. / 页面默认仅展示捆绑模拟数据；用户点击 **Run AI Analysis** 后才调用 Azure。
- Public demo has no access control. Any visitor can upload a schema-valid file and click **Run AI Analysis**. The API receives only its existing approved allowlist for message generation; other fields remain in Python and the browser. Use this capability only for data whose external processing is authorized. / 演示站不设访问控制。任何访问者都可上传符合 Schema 的文件并点击 **Run AI Analysis**。API 仅接收既有的文案生成允许字段；其余字段保留在 Python 和浏览器中。仅可对已获外部处理授权的数据使用此功能。
- Analysis is performed within one request. If it fails, submit again; no partial result is retained. A completed response stays in browser memory until refresh/close and can be downloaded as `offers.csv`. / 分析在单次请求中完成。失败时重新提交；服务端不保留部分结果。完成响应只留在浏览器内存，刷新或关闭页面即清除，可下载为 `offers.csv`。
- The message validator is a lightweight automated check, not factual verification. Every message needs human review. / Message 校验仅为轻量自动检查，不构成事实核验；每条文案都需要人工审核。

## Verification / 验证

```powershell
.venv\Scripts\python.exe -m pytest tests --basetemp .pytest-tmp
cd web
npm test
npm run build
npm run deploy:check
```

`deploy:check` bundles and validates without deploying. / `deploy:check` 只进行打包与部署前检查，不会正式部署。
