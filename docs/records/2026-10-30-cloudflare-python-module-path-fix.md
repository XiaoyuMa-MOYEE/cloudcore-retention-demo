# Cloudflare Python Module Path Fix — 2026-10-30

## English

### Issue
The Cloudflare deployment successfully installed dependencies and used `uv run pywrangler deploy`, but Worker startup failed with `ModuleNotFoundError: No module named 'backend'`. The pre-bundle script copied the existing Python core (`src/`) into `python_modules/` but did not copy the FastAPI application package (`backend/`).

### Change
Updated `scripts/prepare-worker-python.mjs` to copy both `src/` and `backend/` into `python_modules/`, excluding Python cache files. The Worker entry point remains `backend/worker.py`; the existing backend import and application architecture are unchanged.

### Verification
- Python tests: `43 passed`.
- Frontend tests: `2 passed`.
- Frontend production build: passed.
- Wrangler dry-run from `web/`: passed; the prepared bundle contains 490 modules and 6 static assets.
- This verifies packaging only. Cloudflare deployment/runtime startup and live Azure calls still require a new Workers Build run.
- The provided Cloudflare log printed the Azure API key because it is configured as a plaintext remote variable. Rotate that key and replace the variable with a Worker Secret; the value is intentionally not recorded here.

## 中文

### 问题
Cloudflare 已成功安装依赖并使用 `uv run pywrangler deploy`，但 Worker 启动时报 `ModuleNotFoundError: No module named 'backend'`。打包前脚本将现有 Python 核心包 `src/` 复制进了 `python_modules/`，却未复制 FastAPI 应用包 `backend/`。

### 修改
更新 `scripts/prepare-worker-python.mjs`，将 `src/` 和 `backend/` 两个现有 Python 包都复制到 `python_modules/`，并排除 Python 缓存文件。Worker 入口仍是 `backend/worker.py`；现有导入和应用架构不变。

### 验证
- Python 测试：`43 passed`。
- 前端测试：`2 passed`。
- 前端生产构建：通过。
- 从 `web/` 运行 Wrangler dry-run：通过；打包内容为 490 个模块和 6 个静态资源。
- 该验证仅确认打包；Cloudflare 部署后的运行时启动和真实 Azure 调用仍需新的 Workers Build 验证。
- 用户提供的 Cloudflare 日志将 Azure API Key 作为普通远端变量打印。请轮换该 Key 并将普通变量替换为 Worker Secret；本文不记录密钥值。
