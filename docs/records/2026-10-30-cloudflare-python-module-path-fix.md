# Cloudflare Python Module Path Fix — 2026-10-30

## English

### Issue
The Cloudflare deployment successfully installed dependencies and used `uv run pywrangler deploy`, but Worker startup failed with `ModuleNotFoundError: No module named 'backend'`. The pre-bundle script copied the existing Python core (`src/`) into `python_modules/` but did not copy the FastAPI application package (`backend/`).

### Change
Updated `scripts/prepare-worker-python.mjs` to copy `src/` into `python_modules/src` and expose `backend/cloudflare_app.py` as the top-level Worker module `python_modules/cloudflare_app.py`. `backend/worker.py` imports `cloudflare_app` as a top-level module, matching the metadata-module layout used by Wrangler for Python Worker entrypoints.

### Verification
- Python tests: `43 passed`.
- Frontend tests: `2 passed`.
- Frontend production build: passed.
- Wrangler dry-run from `web/`: passed; the prepared bundle contains 491 modules and 6 static assets.
- Local Python Worker runtime launch was blocked because the sandbox could not reach PyPI to install the project's build dependency. Packaging and unit checks passed; the Cloudflare runtime still needs confirmation from a new deployment.
- This verifies packaging only. Cloudflare deployment/runtime startup and live Azure calls still require a new Workers Build run.
- The provided Cloudflare log printed the Azure API key because it is configured as a plaintext remote variable. Rotate that key and replace the variable with a Worker Secret; the value is intentionally not recorded here.

## 中文

### 问题
Cloudflare 已成功安装依赖并使用 `uv run pywrangler deploy`，但 Worker 启动时报 `ModuleNotFoundError: No module named 'backend'`。打包前脚本将现有 Python 核心包 `src/` 复制进了 `python_modules/`，却未复制 FastAPI 应用包 `backend/`。

### 修改
更新 `scripts/prepare-worker-python.mjs`，将 `src/` 复制到 `python_modules/src`，并把 `backend/cloudflare_app.py` 作为顶层 Worker 模块复制到 `python_modules/cloudflare_app.py`。`backend/worker.py` 改为按顶层模块导入 `cloudflare_app`，匹配 Wrangler 为 Python Worker 入口使用的元数据模块布局。

### 验证
- Python 测试：`43 passed`。
- 前端测试：`2 passed`。
- 前端生产构建：通过。
- 从 `web/` 运行 Wrangler dry-run：通过；打包内容为 491 个模块和 6 个静态资源。
- 本地 Python Worker runtime 因沙箱无法连接 PyPI 安装项目构建依赖而未能启动。打包与单元测试通过；仍需新的 Cloudflare 部署确认运行时。
- 用户提供的 Cloudflare 日志将 Azure API Key 作为普通远端变量打印。请轮换该 Key 并将普通变量替换为 Worker Secret；本文不记录密钥值。
