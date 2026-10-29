# CloudCore Person 3 — Codex Development Specification V0.2

## Project context
ISYS6014 Assessment 3, **Predict → Propose → Approve**. Person 2 produces Orange Random Forest customer-level churn scores and `high_risk_customers.csv`. Person 3 (this project) transforms validated high-risk customer records into policy-compliant retention offers and LLM-drafted customer messages, and exports `offers.csv` to Person 4 for human approval. This is a **local, command-line MVP**, not a production SaaS app or autonomous agent. Person 4 owns approval decisions/logging; Person 3 additionally supplies one-screen Figma design and a 90-second demo segment.

## NON-NEGOTIABLE REQUIREMENTS (do not silently change)
1. **Configurable batch size:** Set `batch_size` in a YAML or TOML config file, default **20 customers per LLM request**. No hardcoded batch-size constant in application logic. Validate it is positive. Handle the last partial batch.
2. **Configurable third-party API provider:** Use a provider adapter with configuration for provider, model name, base URL (where supported), timeout, maximum retries, and API key sourced from an environment variable. Default implementation may use OpenAI API. Allow another OpenAI-compatible provider adapter later without rewriting pipeline logic. Local-model adapter is a future extension, **not a claim that local inference is already implemented**. Never hardcode or log API keys; `.env` must be gitignored.
3. **Offer and Reason are DETERMINISTIC Python outputs:** Python applies the ordered four-row Playbook and writes exact `offer` and rule-based `reason`. **Never let LLM select the final offer or freely invent the reason.** LLM only drafts `message`. Preserve the team's exact seven-column output contract. Note in report that this is a reliability-oriented implementation refinement of the original team's plan (which proposed LLM selecting the offer).
4. **Data cleaning stays local/upstream:** Person 2 owns source cleaning, feature preprocessing, model evaluation and export. Person 3 only performs **read-only input contract validation**; it must reject invalid records and report their IDs/row numbers instead of filling values, deduplicating, changing churn scores, or modifying source data. All reading, policy logic, financial indicators, joining, validation, checkpointing and report files occur **locally**. API only receives a minimal allowlisted subset of data when explicitly permitted; never upload the raw CSV to a third-party API.
5. **Governance gate:** Before processing actual CloudCore course records with any external LLM provider, require explicit opt-in configuration (`allow_external_cloudcore_data: false` by default), plus a clear console warning about authorization. Synthetic test records can be used for API development. Do not assume that synthetic-looking course data is authorized for external processing. Keep a dry-run/template mode for testing when API use is not authorized.
6. Preserve the team handoff filenames and schemas. Do not add columns to `offers.csv`. Internal analysis and validation diagnostics go to separate files.

## Input data contract
File: `data/input/high_risk_customers.csv`, UTF-8 CSV, one row per customer, exact eight columns (column order need not be fixed, names must be):

| Field | Type | Validation |
|---|---|---|
| `customer_id` | string | required, nonempty, unique; retained only locally |
| `industry` | string | required, nonempty |
| `region` | string | required, nonempty; do not transmit to LLM by default |
| `tenure_months` | integer | required, >=0 |
| `products` | string | required, nonempty; may contain `+` delimiters |
| `monthly_recurring_revenue` | decimal | required, finite, >=0; do not transmit to LLM |
| `support_tier` | string | required, nonempty; validate known values or flag unknown for review rather than guessing |
| `churn_probability` | float | required, finite, in [0,1]; score for target `churn_flag=1`, not a validated future probability; do not transmit to LLM |

If Person 2's CSV differs, report mismatch, do not silently rename/coerce semantic meaning. No company names sent externally.

## The fixed ordered Playbook
Apply FIRST matching rule only. Store offer labels centrally as constants and output the agreed exact strings.

| Code | Condition | Exact offer label | Rule-based reason (template meaning) |
|---|---|---|---|
| O1 | `support_tier` equals `Basic` (normalise case only for matching, don't rewrite source) | `Free upgrade to Standard support for 3 months` | Customer is on Basic support; first playbook rule applies. |
| O2 | otherwise, `monthly_recurring_revenue < 2000` | `15% off the monthly fee for 3 months` | Customer's MRR is below $2,000 and the preceding rule did not apply. |
| O3 | otherwise, `tenure_months < 12` | `Free onboarding session` | Customer tenure is below 12 months and the preceding rules did not apply. |
| O4 | otherwise | `Account manager call within 5 business days` | None of the first three playbook conditions applies. |

Do not invent offers, discounts, lengths, support entitlements or outcomes. Rule choice does not depend on churn score or internal revenue index.

## Local analytical value
Calculate `risk_weighted_mrr_index = monthly_recurring_revenue * churn_probability` for internal *relative review context only*. Explicitly label as an exploratory index, **not expected loss, forecast revenue, ROI, intervention uplift or a calibrated probability**. Output `data/output/internal_analysis.csv`, not an extra `offers.csv` field. Do not alter Person 2's customer selection or Person 4's agreed queue ordering based on this index unless the team subsequently agrees.

## LLM request / response contract
Generate offer and reason in Python first. Construct compact per-batch LLM payload from **allowlisted fields only**: `industry`, `products`, `tenure_months`, `support_tier`, and `selected_offer` (encoded using offer code O1–O4 plus a single offer-code dictionary at the top of each request). Use batch-local integer `id` (1..N) rather than `customer_id`, and map IDs back locally. `selected_offer` is the fifth semantic element even when compressed to code. Do NOT transmit region, customer ID, MRR, churn score, risk-weighted index, company name or full input CSV.

LLM produces only structured JSON: `{ "results": [{ "id": 1, "message": "..." }, ...] }`, with exactly one message per batch-local id. Use provider structured-output capabilities if available; otherwise parse and validate JSON.

Message constraints:
- English, courteous professional B2B communication, <=80 words.
- Accurately describe the predetermined offer; do not change offer terms or make new promises.
- Use known product/industry/tenure context naturally when relevant, but do not awkwardly mention every input field.
- Do not invent complaints, service outages, financial distress, churn intention, or support benefits not established in supplied facts.
- No internal score/analytics/uncertainty disclosure to customer.
- Treat as an **approval-pending draft**; no automatic customer contact.

Python output fields `offer` and `reason` are not taken from model output under any circumstances.

## Output contract
File: `data/output/offers.csv` with exactly these seven ordered columns:
```
customer_id,support_tier,monthly_recurring_revenue,churn_probability,offer,message,reason
```
The first four fields come unchanged from validated input (aside from CSV serialization); `offer` and `reason` come from Python's rules; `message` comes from the validated LLM response. Preserve customer row identity without duplicates. Only publish the final file when **all valid input customers** have successful message outputs. If any customer fails, retain checkpoints and diagnostics and explicitly report incomplete status, rather than silently delivering a partial file.

## Validation and recovery — scoped to Person 3
- On input contract violation: fail the handoff and produce an actionable validation report for Person 2. **Do not clean upstream data**.
- On temporary API failure/timeout/rate limit: retry the affected batch at most **two additional times** with bounded exponential backoff; do not retry authorization/configuration errors blindly.
- On partial/bad LLM output: verify exact batch-local IDs and cardinality, nonempty message, <=80 words, JSON shape, and obvious offer-term violations. Preserve valid records; retry only invalid/missing individual records **once** using the same provider. Unresolved failures enter `data/output/errors.csv`.
- Automated text checks are incomplete: human review still checks unsupported claims, professionalism and business suitability.
- Save successful checkpoints after every completed batch, with input-file digest, prompt version, provider/model and record IDs; resume without duplicating prior successful calls only when those signatures match. Use atomic writes where practical.
- Keep basic event logs, without sensitive request bodies or credentials. Record number of input customers, batches, valid outputs, failed outputs and API usage metadata when exposed.

## Configuration
Prefer `config.yaml` (or TOML if it avoids unnecessary dependencies). Example:
```yaml
batch_size: 20
provider: openai
model: <set a currently accessible model ID in your local environment>
api_key_env: OPENAI_API_KEY
base_url: null
request_timeout_seconds: 60
batch_retry_count: 2
record_retry_count: 1
allow_external_cloudcore_data: false
input_path: data/input/high_risk_customers.csv
output_path: data/output/offers.csv
analysis_path: data/output/internal_analysis.csv
errors_path: data/output/errors.csv
prompt_version: v0.2
```
Also support CLI override `--input` and `--dry-run`. A placeholder model ID in sample config must never be treated as a real usable model. Add `.env.example`, never `.env` secrets to git.

## Tests and evaluation (default lightweight plan, configurable)
1. Use a self-created 16-record synthetic CSV covering O1–O4, overlapping conditions, MRR=2000, tenure=12, MRR=10000 and score=0.30; all 16 policy decisions must match expected outputs.
2. Validate input errors with tests for missing field, duplicate ID, negative MRR, score >1, noninteger tenure.
3. Test simulated provider outputs: missing ID, duplicate ID, malformed JSON, too-long message, wrong offer terms, transient API failure; confirm correct recovery and checkpoints.
4. On permitted official input, programmatically validate **all** rows and manually rate **8–10** varied generated messages on offer fidelity, factual grounding, personalisation and communication quality; report actual observations, no fabricated metrics.
5. Optional small baseline comparison: 3 customers with same offer but different backgrounds; compare a static template vs LLM on factual accuracy, personalisation and necessary edits. This is a proposed lightweight test, not a school-mandated requirement.
6. Produce `evidence/test_results.csv`, `evidence/prompt.txt`, `evidence/generation_log.json`, `evidence/baseline_comparison.csv` if done.

## Figma & demo handoff
One-screen Figma approval design: left queue (`customer_id`, support tier, churn score, sorted by churn score); right detail showing every Person 4 approval-log field (the seven offers.csv fields plus `approver_role`, `decision`, `decision_reason`, `date`) and visible Approve/Edit/Reject affordances. Use verified rows from real `offers.csv` in final screenshot, not synthetic examples represented as real. Person 4 owns actual approval decisions and audit log. Person 3 records `demo_P3.mp4` (~90s) showing customer input, genuine model message-generation step, rule/validation results and Figma screen. Disclose when showing a precomputed fallback instead of a live API call.

## Report contributions
- Section 2: Figma image.
- Section 3: LLM method, prompt, deterministic rules/reasons, input minimisation, model/provider and privacy limitations.
- Section 4: three real generated examples, tests/results and the limits of conclusions.
- Declare reused Assessment 2 work and all AI assistance according to team plan.
- Explicit limitations: churn scores are not established future probabilities; `MRR × score` is a review index only; intervention efficacy and retention uplift are not demonstrated; a locally hosted model would require new deployment and quality validation.

## Suggested project structure
```
cloudcore-person3/
  config.yaml
  .env.example
  .gitignore
  requirements.txt
  README.md
  src/
    config.py
    schemas.py
    input_validation.py
    playbook.py
    internal_analysis.py
    providers/base.py
    providers/openai_provider.py
    prompt.py
    batching.py
    output_validation.py
    pipeline.py
    cli.py
  tests/
    test_playbook.py
    test_schema.py
    test_batching.py
    test_failures.py
  data/input/
  data/output/
  data/checkpoints/
  evidence/
```
Implement minimal, readable code rather than framework-heavy abstractions; no UI/backend/database/server requirement for the Python pipeline.

## Codex implementation order
1. Inspect repository/files; do not overwrite existing work. Generate `README.md` and `config.yaml`/`.env.example`.
2. Implement typed input/output models, read-only input validation and Playbook tests.
3. Implement internal index and deterministic offer/reason generation.
4. Add provider adapter, compact 20-record batching, structured LLM messages, strict ID mapping and validations.
5. Implement retry, error log, checkpoint/resume and atomic final `offers.csv` publication.
6. Add synthetic test fixture and unit/integration tests with a mocked provider — **do not incur API cost in CI/tests**.
7. Provide a dry-run/template mode; make live external calls opt-in and safeguard actual course data.
8. Run tests, show actual results, provide exact commands for synthetic dry-run and authorized live run. Do not claim Figma or demo video have been created by the code unless genuinely created.

## Definition of done
- One command processes a valid CSV and generates exactly the required offers.csv columns when all rows succeed.
- Batch size and API provider/model configurable; default batch_size=20.
- API receives minimal permitted fields, never raw CSV or IDs.
- Playbook offer and reason are always deterministic Python outputs; LLM only writes `message`.
- Source cleaning is upstream/local; Person 3 only validates the incoming contract.
- Checkpoint, retry, and incomplete-output behavior pass mocked tests.
- Demonstration is reproducible; no false claims about commercial results, privacy authorization, local-model deployment, or model forecasting validity.
