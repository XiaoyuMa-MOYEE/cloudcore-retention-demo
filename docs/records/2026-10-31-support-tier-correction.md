# Support Tier Correction — 2026-10-31

## English

Person 2's final data dictionary confirms four valid support tiers: `Basic`, `Standard`, `Premium`, and `Enterprise`. `config.yaml` is the source of truth for the accepted values. The synthetic data and policy fixture include both Premium and Enterprise; input preserves each original CSV value without mapping either tier to the other.

Input validation tests cover all four tiers with whitespace/case variation and confirm that undefined tiers are rejected. The Playbook is unchanged: Basic → O1; otherwise MRR below 2000 → O2; otherwise tenure below 12 months → O3; otherwise O4. Standard, Premium, and Enterprise have identical downstream rules. Eight input fields, seven output fields, the API architecture, and Python/LLM responsibilities are unchanged.

The previous tier update record is marked superseded. The original V0.2 specification was not modified.

The existing ignored local `offers.csv`, prepared-request artifacts, and checkpoint were produced from the earlier input digest. Cloudflare does not read them; the CLI invalidates stale published output by comparing generation provenance, rejects checkpoints whose input signature differs, and does not reuse prepared requests. They were inspected and left in place as local artifacts, not committed.

## 中文

Person 2 最终数据字典确认四种有效支持等级：`Basic`、`Standard`、`Premium`、`Enterprise`。`config.yaml` 是有效值的唯一配置来源。模拟数据和策略夹具同时包含 Premium 与 Enterprise；输入保留 CSV 原始值，两者互不映射。

输入校验测试覆盖四种等级及大小写、首尾空格差异，并确认未定义等级会被拒绝。Playbook 未改变：Basic → O1；否则 MRR < 2000 → O2；否则 Tenure < 12 个月 → O3；否则 O4。Standard、Premium、Enterprise 使用相同的后续规则。八字段输入、七字段输出、API 架构及 Python/LLM 职责均保持不变。

此前的支持等级更新记录已标注为被后续更正取代。原始 V0.2 规范未修改。

现有被 Git 忽略的本地 `offers.csv`、预备请求文件和检查点来自旧输入摘要。Cloudflare 不读取它们；CLI 会根据生成来源摘要使过期输出失效，拒绝输入签名不匹配的检查点，且不会复用预备请求文件。已检查并保留为本地运行产物，没有提交。
