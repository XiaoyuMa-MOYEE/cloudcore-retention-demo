# Mocked Test Suite Record / Mock 测试记录

- Date / 日期: 2026-10-29
- Scope / 范围: Added isolated tests for input validation, source immutability, Playbook priority, support-tier normalization, a separate 16-record policy fixture, Azure Responses request construction, partial batching, API field allowlist, response validation, mocked batch generation, invalid-record retry, transient and non-transient errors, checkpoint resume, output publication, and external-data governance gating.
- 范围：新增独立测试，覆盖输入校验、源文件不变、Playbook 优先级、支持等级匹配、末尾不完整批次、API 字段白名单、响应校验、Mock 批处理、无效记录重试、暂时性故障重试、检查点恢复、输出发布和外部数据授权门槛。
- Existing synthetic CSV / 现有模拟 CSV: No changes made to `data/input/模拟数据.csv`.
- Result / 结果: `23 passed` using `python -m pytest -q --basetemp=E:\\6014\\.pytest-tmp`. The project-local pytest temp path is ignored by `.gitignore` because the sandbox system temp directory is not writable in this environment.
- Network / 网络: These automated tests use mocked providers and made no API calls.
