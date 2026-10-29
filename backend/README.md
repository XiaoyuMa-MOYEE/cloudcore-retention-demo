# Web API / Web 接口

FastAPI 服务包装现有 Python Core，不在此处复制 Playbook 或优惠决策。`app.py` 提供组内共享码登录、签名 Cookie、合成数据、只读 CSV 校验、后台任务状态、失败重试和七列 CSV 下载。/ This FastAPI service wraps the existing Python Core; it does not duplicate Playbook or offer decisions. `app.py` provides shared-code login, signed cookies, synthetic data, read-only CSV validation, background task status, failure retry, and seven-column CSV download.

Local run / 本地运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Set `GROUP_ACCESS_CODE`, `SESSION_SECRET`, and `AZURE_OPENAI_API_KEY` in the server environment. Runtime state belongs in the persistent `CLOUDCORE_RUNTIME_DIR`; never rely on a Worker filesystem. / 在服务端环境配置访问码、签名密钥和 Azure key。任务数据必须写入持久化 `CLOUDCORE_RUNTIME_DIR`，不可依赖 Worker 文件系统。
