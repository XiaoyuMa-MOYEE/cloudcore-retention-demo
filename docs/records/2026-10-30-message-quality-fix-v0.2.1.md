# Message Quality Fix V0.2.1 / Message 质量修复记录

- Date / 日期: 2026-10-30
- Scope / 范围: Updated only message prompt wording, local message validation, prompt-version/signature metadata, related regression tests, and test evidence. No web UI, database, or business-policy changes.
- 范围：仅调整 Message Prompt、本地 Message 校验、Prompt 版本/签名元数据、相关回归测试与测试证据；未增加 Web UI、数据库或业务规则改动。
- Prompt / 提示词: Removed internal approval-state instructions from the LLM prompt. Added customer-facing-only text guidance, natural product-context use, no mechanical attribute listing, no invented situations, no extra CTA/process claims, and grammatical offer phrasing.
- Validation / 校验: Added rejection for approval/draft/internal workflow terms, unsupported contact/scheduling/billing/eligibility instructions, known inferred-context phrases, formulaic label-style openings, offer mismatch, and >80-word output. Keyword checks remain partial; human review is still needed.
- Checkpoint safety / 检查点安全: Configuration prompt version is `v0.2.1`; checkpoint signature now includes SHA-256 of the system prompt content. A prompt edit invalidates old checkpoints even if the version label is unchanged. Stale output files are invalidated when provenance differs.
- Tests / 测试: `40 passed` using local mock providers. Tests cover forbidden workflow phrase variants, style labels, non-offer operational language, and checkpoint invalidation.
- Same-offer sample / 同 Offer 样例: Three distinct synthetic profiles receiving O1 produced three validated customer-facing messages. The messages refer to different supplied products and use two sentence structures; see `evidence/message_quality_examples.csv`.
- Full API regression / 完整 API 回归: Re-generated 45 synthetic records with Azure `gpt-5-mini`, three calls, 3,377 input / 4,441 output / 7,818 total tokens. All 45 passed automated message checks; no workflow-language hits and no message exceeded 80 words. Final default `data/output/offers.csv` was refreshed from the matching prompt-hash checkpoint after the previous file lock was released.
- Limitations / 限制: Automated phrase checks do not prove complete factual accuracy. Human review is still required. No real CloudCore course data was sent.
