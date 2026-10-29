# Project Structure / 项目结构

The project keeps the original Python Core and CLI and adds one React/Vite + FastAPI Cloudflare Worker for the short-lived demo. The web API is stateless and does not need a database, separate API host, or persistent disk. / 项目保留原 Python Core 和 CLI，并新增一个由 React/Vite 与 FastAPI 组成的 Cloudflare Worker 短期演示站。网页 API 无状态，不需要数据库、独立 API 主机或持久磁盘。

```text
.
├── AGENTS.md                         # Project and agent rules / 项目与 Agent 规则
├── README.md                         # Project use and Cloudflare setup / 项目和 Cloudflare 使用说明
├── config.yaml                       # Non-secret provider/model/batch settings / 非敏感 Provider、模型、批次配置
├── .env.example                      # Local environment example / 本地环境变量示例
├── .gitignore                        # Secrets and generated output exclusions / 密钥和生成文件忽略规则
├── pyproject.toml                    # Cloudflare Python Worker dependencies / Worker Python 依赖
├── pylock.toml                       # Pywrangler-compatible dependency lock / Pywrangler 依赖锁定
├── uv.lock                           # Local Python dependency lock / 本地 Python 依赖锁定
├── requirements-local.txt            # Local CLI/API preview dependencies / 本地 CLI 和 API 预览依赖
├── wrangler.jsonc                    # Single Python + Static Assets Worker / Python 与静态资源 Worker 配置
├── backend/
│   ├── cloudflare_app.py             # Stateless FastAPI routes / 无状态 FastAPI 接口
│   └── worker.py                     # Cloudflare Python Worker and ASGI entry / Worker 与 ASGI 入口
├── scripts/prepare-worker-python.mjs # Copy existing core into generated modules / 复制现有核心模块
├── src/                              # Existing Python business core and CLI / 现有 Python 业务核心和 CLI
├── web/
│   ├── scripts/prepare-worker-assets.mjs # Copy public config and demo CSV / 复制公开配置与模拟 CSV
│   └── src/                          # React + TypeScript app / React + TypeScript 前端
├── docs/                             # Specifications, architecture, deployment, records / 规格、架构、部署与记录
├── tests/                            # Mock-only automated tests / 仅使用 Mock 的自动化测试
├── data/input/                       # Synthetic development data / 模拟开发数据
└── evidence/                         # Reviewable test and demo evidence / 可复核测试与演示证据
```

## Module responsibilities / 模块职责

1. `src/input_validation.py` validates source CSV without rewriting fields; `validate_csv_text` also enables in-memory Worker validation. / 验证源 CSV 且不改写字段；`validate_csv_text` 支持 Worker 内存校验。
2. `src/playbook.py` deterministically applies O1–O4 and owns Offer/Reason. / 确定性应用 O1–O4 并生成 Offer/Reason。
3. `src/internal_analysis.py` computes the exploratory risk-weighted MRR index. / 计算探索性风险加权 MRR 指标。
4. `src/prompt.py`, `src/batching.py`, and `src/output_validation.py` prepare minimal API requests, batch them, and validate generated Message. / 准备最小 API 请求、分批并校验生成文案。
5. `backend/cloudflare_app.py` validates, calls Azure via Worker fetch, and returns complete results/CSV without saving request data. / 校验输入，使用 Worker Fetch 调用 Azure，并在不落盘的前提下返回完整结果和 CSV。
6. `web/src` displays the synthetic demo, uploads CSV, starts analysis on click, and downloads the response. / 显示模拟数据、上传 CSV、由用户点击启动分析并下载结果。

Real customer/course data, API credentials, and sensitive logs must never be committed. / 不得提交真实客户/课程数据、API 凭据或含敏感内容的日志。
