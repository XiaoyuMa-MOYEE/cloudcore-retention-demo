# Support Tier Update — 2026-10-31

## English

Person 2 confirmed the supported tiers are `Basic`, `Standard`, and `Enterprise`. Replaced active `Premium` values in `config.yaml`, the bundled synthetic customer CSV, test fixtures, Python tests, React tier styling, and README/architecture schema descriptions. Input validation still trims and case-folds for comparison while preserving the CSV source value. `Premium` is intentionally tested as an unknown tier and is not mapped to another value.

The ordered O1–O4 Playbook is unchanged: only Basic selects O1; Standard and Enterprise both continue through the existing MRR and Tenure decisions, then O4. Input and output schemas remain eight and seven fields respectively. Python remains responsible for Offer, Reason, and internal analysis; the LLM remains responsible only for Message.

Checked generated output/checkpoint directories and frontend public/build assets. No persisted offer result or checkpoint used the old tier. Rebuilt frontend assets to refresh the generated config and synthetic CSV copies. The original V0.2 specification remains unchanged; the dated pre-API record is marked as historical.

## 中文

Person 2 确认有效支持等级为 `Basic`、`Standard`、`Enterprise`。已更新 `config.yaml`、捆绑模拟客户 CSV、测试夹具、Python 测试、React 等级样式以及 README/架构文档中的 Schema 有效值描述。输入校验仍仅在比较时去除首尾空格并忽略大小写，同时保留 CSV 源值。测试明确确认 `Premium` 属于未知等级，不会被映射为其他值。

O1–O4 顺序规则未改变：只有 Basic 触发 O1；Standard 和 Enterprise 都继续按现有 MRR、Tenure 判断，最后匹配 O4。输入和输出结构仍分别为八字段和七字段。Python 仍负责 Offer、Reason 和内部分析；LLM 仍仅负责 Message。

已检查生成结果/检查点目录及前端 public/build 资源。未发现使用旧等级的持久化结果或检查点。已重建前端产物，刷新生成的配置和模拟 CSV 副本。原始 V0.2 规范未修改；带日期的 pre-API 记录已标记为历史记录。
