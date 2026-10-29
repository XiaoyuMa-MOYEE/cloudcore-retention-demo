# CloudCore Person 3 — V0.3 Demo

组内访问的留存分析演示。React 页面由 Cloudflare Pages 托管，API 由独立 FastAPI 容器运行，沿用现有 Python Playbook、Offer/Reason、分析、Azure Provider、检查点和七列 CSV 导出。

A group-access retention demo. Cloudflare Pages serves the React app and a standalone FastAPI container runs the API. The existing Python Playbook, Offer/Reason, analysis, Azure Provider, checkpoints, and seven-column CSV export are reused.

## Local startup / 本地启动

Requirements: Python 3.12+, Node.js 22.12+, npm. / 环境要求：Python 3.12+、Node.js 22.12+、npm。

```powershell
# Install Python dependencies / 安装 Python 依赖
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Create local secrets file; keep the existing Azure key if already present.
# 创建本地密钥文件；若已填 Azure key，请保留现有值。
# If .env does not exist, copy the example; otherwise append the listed settings without replacing its Azure key.
# 若 .env 不存在则复制示例；若已存在，只追加新设置，勿覆盖已有 Azure key。
if (!(Test-Path .env)) { Copy-Item .env.example .env }
# Set GROUP_ACCESS_CODE and SESSION_SECRET in .env. Add AZURE_OPENAI_API_KEY only if missing.
# 在 .env 设置 GROUP_ACCESS_CODE、SESSION_SECRET；仅在缺少时补充 AZURE_OPENAI_API_KEY。

# Terminal 1 — Python API / 终端 1 — Python API
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — React / 终端 2 — React
Set-Location web
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Local `.env.example` sets `COOKIE_SECURE=false` for HTTP development; production must use Secure cookies. A demo page load fetches synthetic rows only. Click **Run AI analysis** to call Azure; the bundled exact synthetic CSV is the only data allowed by default. / 访问 `http://127.0.0.1:5173`。示例 `.env` 在本地 HTTP 环境将 Cookie Secure 设为 false；生产必须启用 Secure。页面加载只读取模拟数据，点击 **Run AI analysis** 才会调用 Azure；默认仅允许随项目提供的原始模拟 CSV。

## Server secrets / 服务端密钥

- `AZURE_OPENAI_API_KEY`: Azure API secret. / Azure API 密钥。
- `GROUP_ACCESS_CODE`: one shared group access code. / 组内共享访问码。
- `SESSION_SECRET`: random signing secret; generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. / Cookie 签名随机密钥。
- `PUBLIC_ORIGIN`: production browser origin, `https://cloudcore.moyee.uk`. / 生产站点来源。
- `COOKIE_SECURE=true` in production. / 生产环境设置为 true。
- `ALLOW_UPLOADED_SYNTHETIC_ANALYSIS=false` by default. Uploaded files are validation-only unless the administrator enables this server-side. The browser cannot enable it. Do not enable on a service that may receive real customer data without separate authorization and server-side governance. / 默认关闭上传文件模型分析；只有管理员在服务端启用后才能处理上传文件，浏览器无法启用。若服务可能接收真实客户数据，未经单独授权及服务端治理不得开启。

Never put secrets in Vite variables, browser storage, checked-in files, or Cloudflare Pages build variables. API credentials belong only in the FastAPI host's secret manager. / 密钥不得放入 Vite 环境变量、浏览器存储、提交文件或 Pages 构建变量；仅放 FastAPI 主机的服务端 Secret。

## Run modes / 运行模式

- `config.yaml` is the source for provider, model, model version, batch size (default 20), endpoint and timeouts. Azure endpoint remains server-configured and cannot be supplied by a browser. / `config.yaml` 控制 Provider、模型、模型版本、batch size（默认 20）、Endpoint 和超时；Endpoint 由服务端配置，前端不能传入。
- Mock pipeline can be exercised through authenticated `POST /api/analysis?mode=mock` for tests only; the UI uses Azure by default. / 可通过已认证的 `POST /api/analysis?mode=mock` 执行 Mock 回归；界面默认调用 Azure。
- A completed export is available only after every valid input row has a validated Message. Failed/interrupted runs can be retried and reuse successful checkpointed rows. / 只有全部有效记录成功校验后才允许下载；失败或中断任务可重试并复用检查点中的成功记录。

## Tests / 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Set-Location web
npm test
npm run build
```

The Python web API regression suite uses the Mock Provider. The real Azure end-to-end test is a separate manual, billable action against the bundled synthetic CSV. / Python Web API 回归测试使用 Mock Provider。真实 Azure 端到端测试是单独的付费操作，且只使用随项目提供的模拟 CSV。

## Cloudflare deployment / Cloudflare 部署

Deployment is intentionally not performed by this repository workflow. Follow [`docs/deployment/README.md`](docs/deployment/README.md) after confirming the API hosting plan, setting Secrets, and reviewing the route. The planned subdomain route is limited to `cloudcore.moyee.uk`; no root-domain/main-site files are used. / 本项目不自动部署。确认 API 主机方案、配置 Secret 并审查路由后，按双语部署手册执行。目标仅为 `cloudcore.moyee.uk`，不使用根域/主站文件。

## Project rules / 项目规则

Read `AGENTS.md` before changing code. Original V0.2 requirements remain archived under `docs/specifications/`; V0.3 architecture and development records are under `docs/architecture/` and `docs/records/`. / 修改代码前阅读 `AGENTS.md`。V0.2 原始需求保存在 `docs/specifications/`；V0.3 架构与开发记录在 `docs/architecture/`、`docs/records/`。
