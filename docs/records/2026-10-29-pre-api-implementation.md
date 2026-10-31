# Pre-API Implementation Record / API 前实现记录

- Date / 日期: 2026-10-29
- Scope / 范围: Implemented YAML configuration loading, configurable support-tier validation, read-only CSV contract validation, deterministic O1–O4 decisions, local exploratory index, configurable batching, minimized request construction, and a CLI that stops before network access.
- 范围：实现 YAML 配置读取、可配置支持等级校验、只读 CSV 契约校验、确定性 O1–O4 决策、本地探索性指标、可配置批次、最小化请求构造，以及在网络访问前停止的 CLI。
- Support tiers / 支持等级: `Basic`, `Standard`, `Premium` are configured in `config.yaml`. Validation trims and case-folds only for comparison; original source values are retained. Only Basic selects O1.

> Historical snapshot / 历史记录：以上记录描述 2026-10-29 的初始配置。Person 2 后续确认的当前有效等级为 `Basic`, `Standard`, and `Enterprise`; see `docs/records/2026-10-31-support-tier-update.md`. The historical value `Premium` is not accepted by the current validator. / 以上记录描述 2026-10-29 的初始配置。Person 2 后续确认当前有效等级为 `Basic`、`Standard`、`Enterprise`；见 `docs/records/2026-10-31-support-tier-update.md`。历史值 `Premium` 不被当前校验器接受。
- Supported development input / 开发输入: Copied the user-supplied `模拟数据.csv` to `data/input/模拟数据.csv`; the file is excluded from Git by the existing data ignore rule.
- API status / API 状态: No provider/client was implemented and no request was sent. Prepared payloads and their local-only identity map are written separately. No final `offers.csv` or customer message is produced at this stage.
- Tests / 测试: No tests were added or run in this step.
