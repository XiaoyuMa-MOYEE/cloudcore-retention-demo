# Agent Instructions — CloudCore Person 3

These rules apply to all work in this repository. Original V0.2 requirements are archived in `docs/specifications/CloudCore_Person3_Codex_Spec_V0.2.md`; the current V0.3 web demo scope is described in `docs/architecture/V0.3_WEB_DEMO.md` and the root README.

## Scope and ownership
- This is a lightweight group demo for Person 3, not a production SaaS or autonomous agent. The local CLI remains supported.
- Person 2 owns source cleaning, preprocessing, model evaluation, customer selection, and export. This project validates input read-only; never impute, deduplicate, rename semantically, change churn scores, or rewrite source records.
- Person 4 owns approval decisions and the approval audit log. Generated messages are drafts only; never contact customers.

## Non-negotiable implementation rules
- Implement the ordered O1–O4 Playbook exactly. First matching rule wins. Generate `offer` and `reason` in Python; never accept either from model output.
- Keep the handoff file `offers.csv` to exactly these ordered columns: `customer_id,support_tier,monthly_recurring_revenue,churn_probability,offer,message,reason`.
- Default `batch_size` to 20 in configuration, validate it is positive, and handle partial batches. Do not hardcode batch size in pipeline logic.
- Keep provider, model, supported base URL, timeout, retry limits, and API-key environment-variable name configurable. Never store or log secrets. Keep `.env` ignored by Git.
- External processing of CloudCore course data must be opt-in and default off (`allow_external_cloudcore_data: false`), with a clear authorization warning. Never send the raw CSV or disallowed fields to an API. Keep dry-run/template mode available.
- API payloads may contain only the approved allowlist: industry, products, tenure_months, support_tier, selected_offer code, and batch-local integer IDs. Do not transmit customer IDs, region, MRR, churn score, company name, or internal analysis.
- `risk_weighted_mrr_index` is an exploratory internal review index only. Never describe it as expected loss, forecast revenue, ROI, calibrated probability, or intervention impact; never reorder the handoff queue by it.
- Publish the final offers file only when every valid input customer has a validated message. Preserve diagnostics and checkpoints on incomplete runs.
- Keep documentation and user-facing project text bilingual (Chinese and English) where applicable. Keep the original specification under `docs/specifications/` without editing its requirements.
- Azure OpenAI Responses API integration is authorized for the user-supplied synthetic development CSV. Never send actual CloudCore course data unless `allow_external_cloudcore_data: true` is explicitly set after authorization and the CLI emits its warning.
- Keep data processing, Playbook decisions, Offer/Reason generation, output checks, and Azure provider execution in Python. React/TypeScript must not duplicate business logic.
- The browser must never receive or persist API keys, group access codes, or session signing secrets. All data and analysis APIs require a valid HttpOnly, Secure, SameSite session cookie in deployment.
- Web analysis may use only the bundled synthetic dataset by default. Uploaded CSV model calls require the server-side `ALLOW_UPLOADED_SYNTHETIC_ANALYSIS` setting; never offer a client-side data-scope override.
- Web task state, outputs, uploaded files, and checkpoints must live in a configured persistent runtime volume, not a Cloudflare Worker local filesystem. Isolate file paths per task.
- Do not modify the personal main site or its repository. Do not push to GitHub or deploy Cloudflare unless explicitly authorized in the current request.

## Engineering workflow
- Inspect existing files before changing them; preserve user work.
- Keep modules small and readable. React/Vite, FastAPI, a small SQLite task registry, and deployment files are authorized by V0.3; avoid unrelated expansion.
- Automated tests must use synthetic fixtures and mocked providers; they must not incur API costs or transmit course data. User-authorized manual live checks may use the supplied synthetic dataset.
- Do not claim that Figma, a demo video, live API runs, or quality evaluations exist unless actually produced and verified.
- Record material design decisions and verification results under `docs/records/`; do not fabricate results.
