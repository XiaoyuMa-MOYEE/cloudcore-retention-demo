"""Local pre-API preparation pipeline."""

import csv
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from .batching import make_batches
from .config import AppConfig
from .input_validation import ValidationResult, validate_csv
from .internal_analysis import INTERPRETATION, risk_weighted_mrr_index
from .playbook import choose_offer
from .prompt import SYSTEM_PROMPT, build_request_payload
from .schemas import ANALYSIS_COLUMNS
from .schemas import OFFERS_COLUMNS
from .providers.base import ProviderResult
from .providers.openai_responses import OpenAIResponsesProvider, is_retryable_api_error
from .output_validation import validate_response


def run_pre_api(config: AppConfig, input_path: str | None = None) -> tuple[bool, str]:
    source_path = input_path or config.input_path
    try:
        input_digest = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    except OSError as exc:
        result = validate_csv(source_path, config.valid_support_tiers)
        _write_validation_report(config.validation_report_path, result)
        return False, f"Cannot read input file: {exc}; see {config.validation_report_path}."
    result = validate_csv(source_path, config.valid_support_tiers)
    _write_validation_report(config.validation_report_path, result)
    if not result.valid:
        return False, f"Input contract failed with {len(result.issues)} issue(s); see {config.validation_report_path}. No records were normalized or prepared."
    if not result.customers:
        return False, "Input contains no customer records; no requests were prepared."

    analysis_rows = []
    for customer in result.customers:
        index = risk_weighted_mrr_index(customer)
        analysis_rows.append({
            "customer_id": customer.customer_id,
            "risk_weighted_mrr_index": format(index, "f"),
            "interpretation": INTERPRETATION,
        })
    _atomic_csv(config.analysis_path, ANALYSIS_COLUMNS, analysis_rows)

    batches = []
    id_maps = []
    for batch_number, batch in enumerate(make_batches(result.customers, config.batch_size), start=1):
        payload, mapping = build_request_payload(batch)
        batches.append({"batch_number": batch_number, "payload": payload})
        id_maps.append({"batch_number": batch_number, "local_id_to_customer_id": mapping})

    requests_document = {
        "status": "prepared_not_sent",
        "input_sha256": input_digest,
        "prompt_version": config.prompt_version,
        "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "system_prompt": SYSTEM_PROMPT,
        "batch_count": len(batches),
        "batches": batches,
    }
    mapping_document = {
        "note": "LOCAL ONLY. Do not send this identity map to a provider.",
        "input_sha256": input_digest,
        "batches": id_maps,
    }
    _atomic_text(config.prepared_requests_path,
                 json.dumps(requests_document, ensure_ascii=False, indent=2) + "\n")
    _atomic_text(config.prepared_id_map_path,
                 json.dumps(mapping_document, ensure_ascii=False, indent=2) + "\n")

    counts: dict[str, int] = {code: 0 for code in ("O1", "O2", "O3", "O4")}
    for customer in result.customers:
        counts[choose_offer(customer).code] += 1
    return True, (
        f"Pre-API preparation complete: {result.row_count} input row(s), "
        f"{len(batches)} batch(es), offers {counts}. No API call was made and "
        f"offers.csv was not published. See {config.prepared_requests_path} and {config.analysis_path}."
    )


def run_live(config: AppConfig, input_path: str | None = None, *, synthetic_data: bool = False,
             smoke_test: bool = False, provider_override=None) -> tuple[bool, str]:
    """Call the configured provider only after explicit data-scope gating."""
    if not synthetic_data and not config.allow_external_cloudcore_data:
        return False, ("BLOCKED: external CloudCore data processing is disabled. Set "
                       "allow_external_cloudcore_data: true only after obtaining explicit authorization.")
    if not synthetic_data:
        print("WARNING: this run may transmit CloudCore course records to an external provider. "
              "Proceeding because allow_external_cloudcore_data is explicitly true.")
    if config.provider not in ("azure_openai", "openai"):
        return False, f"Unsupported provider {config.provider!r}; supported adapters are azure_openai and openai-compatible OpenAI Responses API."

    source_path = input_path or config.input_path
    ok, summary = run_pre_api(config, source_path)
    if not ok:
        return False, summary
    result = validate_csv(source_path, config.valid_support_tiers)
    digest = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    customers = result.customers[:1] if smoke_test else result.customers
    if smoke_test and not customers:
        return False, "Cannot run API smoke test: input contains no valid customer records."

    provider = provider_override or OpenAIResponsesProvider(
        config.api_key_env, config.base_url, config.request_timeout_seconds, max_retries=0,
    )
    if smoke_test:
        payload, _ = build_request_payload(tuple(customers))
        call, call_error = _call_with_retry(provider, payload, config, config.batch_retry_count)
        if call is None:
            _write_generation_log(config.generation_log_path, digest, config, [], [call_error or "API call failed"])
            return False, f"Azure API smoke test failed: {call_error}"
        expected = {1}
        code = choose_offer(customers[0]).code
        messages, errors = validate_response(call.output_text, expected, {1: code})
        _write_generation_log(config.generation_log_path, digest, config, [call], list(errors.values()))
        if errors:
            return False, f"Azure API smoke request succeeded, but message validation failed: {errors.get(1)}"
        return True, ("Azure API smoke test succeeded for one synthetic customer. "
                      f"Usage: input={call.input_tokens}, output={call.output_tokens}, total={call.total_tokens} tokens; "
                      f"request_id={call.request_id or 'unavailable'}. No offers.csv was written.")

    signature = {
        "input_sha256": digest,
        "prompt_version": config.prompt_version,
        "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "provider": config.provider,
        "model": config.model,
        "model_version": config.model_version,
        "customer_ids": [customer.customer_id for customer in customers],
    }
    signature_hash = hashlib.sha256(json.dumps(signature, sort_keys=True).encode("utf-8")).hexdigest()
    if not _invalidate_stale_output(config, signature):
        return False, (f"Cannot invalidate stale output at {config.output_path}; close any application "
                       "holding the file and rerun. No API request was sent for this batch run.")
    checkpoint = _load_checkpoint(config.checkpoint_path, signature_hash)
    messages: dict[str, str] = checkpoint.get("messages", {})
    log_calls: list[dict] = checkpoint.get("calls", [])
    errors_by_id: dict[str, dict] = {}

    for batch_number, batch in enumerate(make_batches(customers, config.batch_size), start=1):
        pending = tuple(customer for customer in batch if customer.customer_id not in messages)
        if pending:
            payload, id_map = build_request_payload(pending)
            id_to_customer = {local_id: customer for local_id, customer in zip(id_map, pending)}
            expected_ids = set(id_map)
            id_to_code = {local_id: choose_offer(customer).code for local_id, customer in id_to_customer.items()}
            response, call_error = _call_with_retry(provider, payload, config, config.batch_retry_count)
            calls: list[ProviderResult] = []
            valid_messages: dict[int, str] = {}
            invalid: dict[int, str] = {}
            if response is not None:
                calls.append(response)
                valid_messages, invalid = validate_response(response.output_text, expected_ids, id_to_code)
            else:
                invalid = {local_id: call_error or "Provider call failed." for local_id in expected_ids}

            # Recover invalid model output by record. Transport/auth failures are not
            # converted into individual retries after the batch retry policy ends.
            for local_id, issue in list(invalid.items()):
                customer = id_to_customer[local_id]
                if response is not None:
                    for _ in range(config.record_retry_count):
                        one_payload, _ = build_request_payload((customer,))
                        retry_response, retry_error = _call_with_retry(
                            provider, one_payload, config, config.batch_retry_count,
                        )
                        if retry_response is None:
                            issue = f"{issue}; record retry failed: {retry_error}"
                            continue
                        calls.append(retry_response)
                        retried, retry_issues = validate_response(
                            retry_response.output_text, {1}, {1: choose_offer(customer).code},
                        )
                        if 1 in retried:
                            valid_messages[local_id] = retried[1]
                            issue = ""
                            break
                        issue = retry_issues.get(1, issue)
                if issue:
                    errors_by_id[customer.customer_id] = {
                        "row_number": customer.source_row,
                        "customer_id": customer.customer_id,
                        "error": issue,
                    }

            for local_id, message in valid_messages.items():
                messages[id_to_customer[local_id].customer_id] = message
            for call in calls:
                log_calls.append(_call_metadata(call, batch_number))
            checkpoint = {
                "signature_hash": signature_hash,
                "signature": signature,
                "messages": messages,
                "calls": log_calls,
            }
            _atomic_text(config.checkpoint_path, json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n")

        # If a checkpoint was complete for this batch, no provider call is repeated.
        if not pending:
            continue

    for customer in customers:
        if customer.customer_id not in messages and customer.customer_id not in errors_by_id:
            errors_by_id[customer.customer_id] = {
                "row_number": customer.source_row,
                "customer_id": customer.customer_id,
                "error": "No validated message available after processing.",
            }
    error_rows = list(errors_by_id.values())
    _atomic_csv(config.errors_path, ("row_number", "customer_id", "error"), error_rows)
    _write_generation_log_from_metadata(config.generation_log_path, digest, config, log_calls, error_rows)
    if error_rows or len(messages) != len(customers):
        return False, (f"Batch run incomplete: {len(messages)}/{len(customers)} messages validated. "
                       f"Diagnostics: {config.errors_path}; successful messages retained in checkpoint.")

    customer_by_id = {customer.customer_id: customer for customer in customers}
    output_rows = []
    for customer in customers:
        decision = choose_offer(customer)
        output_rows.append({
            "customer_id": customer.raw["customer_id"],
            "support_tier": customer.raw["support_tier"],
            "monthly_recurring_revenue": customer.raw["monthly_recurring_revenue"],
            "churn_probability": customer.raw["churn_probability"],
            "offer": decision.offer,
            "message": messages[customer.customer_id],
            "reason": decision.reason,
        })
    _atomic_csv(config.output_path, OFFERS_COLUMNS, output_rows)
    token_totals = _token_totals(log_calls)
    return True, (f"Batch run complete: {len(output_rows)} validated messages; offers.csv published. "
                  f"Token usage: input={token_totals['input_tokens']}, output={token_totals['output_tokens']}, "
                  f"total={token_totals['total_tokens']}.")


def _call_with_retry(provider: OpenAIResponsesProvider, payload: dict, config: AppConfig,
                     max_retries: int) -> tuple[ProviderResult | None, str | None]:
    for attempt in range(max_retries + 1):
        try:
            return provider.generate(payload, SYSTEM_PROMPT, config.model), None
        except Exception as exc:
            if attempt < max_retries and is_retryable_api_error(exc):
                time.sleep(min(2 ** attempt, 4))
                continue
            status = getattr(exc, "status_code", None)
            detail = f" HTTP {status}" if status is not None else ""
            return None, f"{type(exc).__name__}{detail}"
    return None, "Retries exhausted."


def _load_checkpoint(path: str, signature_hash: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"messages": {}, "calls": []}
    if value.get("signature_hash") != signature_hash:
        return {"messages": {}, "calls": []}
    return {
        "messages": value.get("messages", {}) if isinstance(value.get("messages", {}), dict) else {},
        "calls": value.get("calls", []) if isinstance(value.get("calls", []), list) else [],
    }


def _invalidate_stale_output(config: AppConfig, signature: dict) -> bool:
    """Remove a prior offers file when its generation provenance is stale or unknown."""
    output_path = Path(config.output_path)
    if not output_path.exists():
        return True
    try:
        previous = json.loads(Path(config.generation_log_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    provenance_keys = (
        "input_sha256", "prompt_version", "prompt_sha256", "provider", "model", "model_version",
    )
    if any(previous.get(key) != signature.get(key) for key in provenance_keys):
        try:
            output_path.unlink()
        except OSError:
            return False
    return True


def _call_metadata(call: ProviderResult, batch_number: int) -> dict:
    return {
        "batch_number": batch_number,
        "request_id": call.request_id,
        "model": call.model,
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "total_tokens": call.total_tokens,
    }


def _token_totals(calls: list[dict]) -> dict[str, int | None]:
    totals = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        values = [call.get(key) for call in calls if call.get(key) is not None]
        totals[key] = sum(values) if values else None
    return totals


def _write_generation_log(path: str, digest: str, config: AppConfig,
                          calls: list[ProviderResult], errors: list[str]) -> None:
    metadata = [_call_metadata(call, 1) for call in calls]
    _write_generation_log_from_metadata(path, digest, config, metadata, errors)


def _write_generation_log_from_metadata(path: str, digest: str, config: AppConfig,
                                        calls: list[dict], errors: list) -> None:
    document = {
        "input_sha256": digest,
        "prompt_version": config.prompt_version,
        "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "provider": config.provider,
        "model": config.model,
        "model_version": config.model_version,
        "call_count": len(calls),
        "token_usage": _token_totals(calls),
        "calls": calls,
        "failed_records": len(errors),
    }
    _atomic_text(path, json.dumps(document, ensure_ascii=False, indent=2) + "\n")


def _write_validation_report(path: str, result: ValidationResult) -> None:
    rows = [{
        "row_number": "" if issue.row_number is None else issue.row_number,
        "customer_id": issue.customer_id,
        "field": issue.field,
        "problem": issue.problem,
    } for issue in result.issues]
    _atomic_csv(path, ("row_number", "customer_id", "field", "problem"), rows)


def _atomic_csv(path: str, columns: tuple[str, ...], rows: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _atomic_text(path: str, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
