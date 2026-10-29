# 项目结构规划 / Project Structure Plan

本目录结构保留原有 Python Core，并补充 V0.3 React Web 与 FastAPI 演示服务。/ This layout preserves the existing Python Core and adds the V0.3 React Web and FastAPI demo service.

```text
.
├── AGENTS.md                         # 仓库级 Codex/Agent 工作规则 / Repository agent rules
├── README.md                         # 项目概览与边界 / Project overview and boundaries
├── config.yaml                       # 非敏感运行配置模板 / Non-secret runtime configuration
├── .env.example                      # 环境变量示例，不含密钥 / Environment example, no secrets
├── .gitignore                        # 忽略密钥、运行产物与临时文件 / Ignore secrets and runtime artifacts
├── requirements.txt                  # Python 运行依赖 / Python runtime dependencies
├── docs/
│   ├── specifications/               # 原始需求与规格版本 / Original requirements and versions
│   ├── architecture/                 # 架构、流程与接口说明 / Architecture, flow, and interfaces
│   └── records/                      # 决策、开发、验证与交接记录 / Decision, development, verification, handoff records
├── src/
│   ├── cli.py                        # 命令行入口 / CLI entry point
│   ├── config.py                     # 配置加载与校验 / Configuration loading and validation
│   ├── schemas.py                    # 输入输出结构 / Input and output schemas
│   ├── input_validation.py           # 只读输入契约验证 / Read-only input contract validation
│   ├── playbook.py                   # O1–O4 确定性规则 / Deterministic O1–O4 rules
│   ├── internal_analysis.py          # 内部探索性指标 / Internal exploratory metrics
│   ├── batching.py                   # 可配置批次构建 / Configurable batching
│   ├── prompt.py                     # 提示词与允许字段 / Prompt and field allowlist
│   ├── output_validation.py          # 模型响应校验 / Model response validation
│   ├── pipeline.py                   # 编排、恢复、完整发布 / Orchestration, recovery, publication
│   └── providers/                    # Provider 适配层 / Provider adapters
├── backend/
│   └── app.py                         # FastAPI 登录、校验、任务 API / Login, validation, task API
├── web/
│   └── src/ui/                        # React + TypeScript 页面 / React + TypeScript UI
├── deploy/cloudflare/                 # Pages API 路由 Worker 配置 / Pages API route Worker config
├── Dockerfile                         # FastAPI 容器 / FastAPI container
├── render.yaml                        # 独立后端与持久盘模板 / Standalone API and persistent disk template
├── tests/
│   ├── fixtures/                     # 合成数据与模拟响应 / Synthetic data and mock responses
│   └── ...                           # 单元与集成测试 / Unit and integration tests
├── data/
│   ├── input/                        # 输入 CSV（不提交真实课程数据）/ Input CSV (no real course data committed)
│   ├── output/                       # offers、分析和错误输出 / Offers, analysis, and error outputs
│   └── checkpoints/                  # 可恢复的批次检查点 / Resumable batch checkpoints
├── data/web_runtime/                 # Web 任务 SQLite、上传与检查点（忽略）/ Web SQLite, uploads and checkpoints (ignored)
└── evidence/                         # 可复核测试与演示证据 / Reviewable test and demo evidence
```

## 模块职责 / Module responsibilities

1. `config.py` 和 `cli.py` 读取运行选项、检查授权状态并提供 dry-run。/ Load run options, check authorization state, and provide dry-run.
2. `input_validation.py` 仅验证，不修复；有问题即生成诊断并停止交接。/ Validate without repairing; emit diagnostics and stop handoff on violations.
3. `playbook.py` 对每条有效记录按 O1 到 O4 生成确定性 Offer/Reason。/ Assign deterministic Offer/Reason in O1-to-O4 order.
4. `internal_analysis.py` 单独计算探索性 `risk_weighted_mrr_index`。/ Calculate the exploratory index separately.
5. `prompt.py`, `batching.py`, `providers/`, `output_validation.py` 负责最小化请求、批处理和受限消息生成。/ Handle minimized requests, batching, and constrained message generation.
6. `pipeline.py` 管理重试、检查点、错误记录，并且仅在所有有效客户成功后发布最终文件。/ Manage retries, checkpoints, errors, and publish only after every valid customer succeeds.

## 数据边界 / Data boundaries

真实课程输入数据、输出客户数据、API 凭据和含敏感内容的日志不得提交到版本库。/ Do not commit real course input/output data, API credentials, or logs containing sensitive content.
