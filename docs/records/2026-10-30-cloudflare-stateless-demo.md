# Cloudflare Stateless Demo Transition / Cloudflare 无状态演示改造

## Decision and scope / 决策与范围

- Replaced the external persistent FastAPI host and JavaScript reverse proxy with one Cloudflare Python Worker hosting both FastAPI and Vite Static Assets. / 将独立持久化 FastAPI 主机和 JavaScript 反向代理改为单个 Cloudflare Python Worker，同时承载 FastAPI 和 Vite 静态资源。
- Removed group-code login and session handling as requested for the public short-lived concept demo. / 按短期公开概念 Demo 的决定移除组内访问码登录和会话机制。
- Analysis is one synchronous request. CSV parsing, Python rules, Azure Message calls, result validation and CSV construction remain in memory; the server persists no uploads, tasks, checkpoints or results. / 分析为单次同步请求。CSV 解析、Python 规则、Azure Message 调用、结果校验和 CSV 生成均在内存中完成；服务端不持久化上传、任务、检查点或结果。
- Kept existing Python Offer/Reason, MRR × Churn Score, support-tier validation, batching and Message validation. The configured `batch_size` remains 20 by default. / 保留现有 Python Offer/Reason、MRR × Churn Score、Support Tier 校验、分批和 Message 校验；`batch_size` 仍由配置控制，默认 20。
- Worker Secret `AZURE_OPENAI_API_KEY` is the deployment key source. No key value was written into code or generated public assets. The demo remains synthetic-only for external model calls; non-exact synthetic uploads require the server-side flag and SIM*/SYN* IDs. / Worker Secret `AZURE_OPENAI_API_KEY` 是部署时的密钥来源；密钥值未写入代码或公开静态资源。外部模型调用仍限模拟数据；非捆绑原文件的模拟上传需要服务端开关及 SIM*/SYN* ID。

## Verification / 验证

- Python Mock regression suite: `43 passed` (run in the project-local isolated Python environment). / Python Mock 回归：`43 passed`（在项目隔离 Python 环境中运行）。
- Frontend tests: `2 passed`; TypeScript/Vite production build succeeded. / 前端测试：`2 passed`；TypeScript/Vite 正式构建成功。
- `uv run pywrangler deploy --dry-run`: passed. Bundle contains the Python worker, FastAPI dependencies, the existing Python core and 6 static assets; compressed upload estimate was about 2.5 MB. / Pywrangler dry-run 通过；打包包括 Python Worker、FastAPI 依赖、现有 Python 核心及 6 个静态资源；压缩上传估算约 2.5 MB。
- No live Azure API request or production deployment was performed in this local verification. Cloudflare requires `AZURE_OPENAI_API_KEY` as a Worker Secret before message generation can run. / 本地验证未发送真实 Azure API 请求，也未进行生产部署。Cloudflare 需先配置 `AZURE_OPENAI_API_KEY` Worker Secret 才能生成文案。

## Deployment handoff / 部署交接

Workers Builds Root Directory is `.`, build command is `pip install uv && cd web && npm ci && npm run build`, and deploy command is `uv run pywrangler deploy`. Add the Azure key in the Worker’s Variables and Secrets page; do not put it in the public repository. / Workers Builds 根目录为 `.`；构建命令为 `pip install uv && cd web && npm ci && npm run build`；部署命令为 `uv run pywrangler deploy`。在 Worker Variables and Secrets 页面添加 Azure Key，不得放入公开仓库。
