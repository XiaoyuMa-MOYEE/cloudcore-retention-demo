"""Stateless FastAPI API for the short-lived Cloudflare concept demo."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import yaml
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from src.batching import make_batches
from src.input_validation import validate_csv_text
from src.internal_analysis import risk_weighted_mrr_index
from src.output_validation import validate_response
from src.playbook import OFFER_LABELS, choose_offer
from src.prompt import SYSTEM_PROMPT, build_request_payload
from src.schemas import OFFERS_COLUMNS


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 2_000_000
MAX_ROWS = 500
app = FastAPI(title="CloudCore Person 3 Demo", version="0.3.0", docs_url=None, redoc_url=None)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False, encoding="utf-8-sig")
except ImportError:
    # python-dotenv is only a local-development convenience, not a Worker runtime dependency.
    pass


def _configuration() -> dict:
    try:
        return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        raise HTTPException(503, "Application configuration could not be loaded.") from None


async def _load_worker_config(request: Request) -> dict:
    env = request.scope.get("env")
    if env is not None and hasattr(env, "ASSETS"):
        response = await env.ASSETS.fetch("https://assets.local/cloudcore-config.yaml")
        if response.status != 200:
            raise HTTPException(503, "Worker configuration asset is missing.")
        config = yaml.safe_load(await response.text())
    else:
        config = _configuration()
    if config.get("provider") not in ("azure_openai", "openai"):
        raise HTTPException(503, f"Unsupported configured provider: {config.get('provider')}.")
    return config


async def _read_asset(request: Request, path: str) -> bytes:
    env = request.scope.get("env")
    if env is not None and hasattr(env, "ASSETS"):
        response = await env.ASSETS.fetch(f"https://assets.local/{path}")
        if response.status != 200:
            raise HTTPException(503, "Bundled synthetic dataset is missing.")
        return (await response.text()).encode("utf-8")
    try:
        return (ROOT / "data" / "input" / "模拟数据.csv").read_bytes()
    except OSError:
        raise HTTPException(503, "Bundled synthetic dataset is missing.") from None


async def _csv_content(file: UploadFile) -> bytes:
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "CSV must be 2 MB or smaller.")
    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8 encoded.") from None
    return content


def _validate(content: bytes, config: dict):
    text = content.decode("utf-8-sig")
    result = validate_csv_text(text, tuple(config["valid_support_tiers"]))
    if result.issues:
        raise HTTPException(422, {
            "message": "Input schema validation failed; the CSV was not modified.",
            "errors": [
                {"row_number": issue.row_number, "customer_id": issue.customer_id,
                 "field": issue.field, "problem": issue.problem}
                for issue in result.issues
            ],
        })
    if not result.customers:
        raise HTTPException(422, "CSV must contain at least one customer record.")
    if len(result.customers) > MAX_ROWS:
        raise HTTPException(413, "CSV is limited to 500 rows.")
    return result.customers


def _is_synthetic(content: bytes, customers, bundled: bytes) -> bool:
    if hashlib.sha256(content).digest() == hashlib.sha256(bundled).digest():
        return True
    return bool(customers) and all(
        customer.customer_id.strip().upper().startswith(("SIM", "SYN"))
        for customer in customers
    )


class CloudflareAzureResponsesProvider:
    """Responses API adapter using Workers fetch (Python sockets are unavailable)."""

    async def generate(self, payload: dict, system_prompt: str, model: str,
                       *, endpoint: str, api_key: str, timeout: int) -> dict:
        url = endpoint.rstrip("/") + "/responses"
        body = {
            "model": model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]},
            ],
            "text": {"format": {"type": "json_schema", "name": "customer_messages",
                       "strict": True, "schema": _message_schema()}},
            "store": False,
        }
        try:
            from js import AbortSignal, Object, fetch
            from pyodide.ffi import to_js
            options = to_js({
                "method": "POST",
                "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                "body": json.dumps(body, ensure_ascii=False),
                "signal": AbortSignal.timeout(timeout * 1000),
            }, dict_converter=Object.fromEntries)
            response = await fetch(url, options)
            text = await response.text()
            status = response.status
        except ImportError:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=endpoint, timeout=timeout, max_retries=0)
            response = await asyncio.to_thread(
                client.responses.create,
                model=model,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}]},
                ],
                text={"format": {"type": "json_schema", "name": "customer_messages",
                                 "strict": True, "schema": _message_schema()}},
                store=False,
            )
            usage = response.usage
            return {"output_text": response.output_text or "", "request_id": response.id,
                    "input_tokens": usage.input_tokens if usage else None,
                    "output_tokens": usage.output_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None}
        if status < 200 or status >= 300:
            raise ProviderCallError(status)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            raise ProviderCallError(status, "invalid_json") from None
        message_text = parsed.get("output_text")
        if not isinstance(message_text, str):
            fragments = []
            for item in parsed.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        fragments.append(content.get("text", ""))
            message_text = "".join(fragments)
        usage = parsed.get("usage") or {}
        return {
            "output_text": message_text,
            "request_id": parsed.get("id"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }


class ProviderCallError(Exception):
    def __init__(self, status: int, code: str = "api_error"):
        self.status = status
        self.code = code
        super().__init__(f"Azure Responses API returned HTTP {status}.")


def _message_schema() -> dict:
    return {
        "type": "object",
        "properties": {"results": {"type": "array", "items": {
            "type": "object", "properties": {
                "id": {"type": "integer"}, "message": {"type": "string"},
            }, "required": ["id", "message"], "additionalProperties": False,
        }}}, "required": ["results"], "additionalProperties": False,
    }


async def _generate_batch(provider, payload: dict, config: dict, api_key: str) -> dict:
    retries = int(config.get("batch_retry_count", 0))
    last_error = None
    for attempt in range(retries + 1):
        try:
            return await provider.generate(
                payload, SYSTEM_PROMPT, config["model"],
                endpoint=config["base_url"], api_key=api_key,
                timeout=int(config.get("request_timeout_seconds", 60)),
            )
        except ProviderCallError as exc:
            last_error = exc
            if attempt >= retries or (exc.status < 500 and exc.status != 429):
                break
            await asyncio.sleep(min(2 ** attempt, 4))
    raise HTTPException(502, f"Azure message generation failed ({last_error.code if last_error else 'provider_error'}).")


async def analyze_content(content: bytes, config: dict, api_key: str,
                          provider: CloudflareAzureResponsesProvider | None = None,
                          bundled: bytes | None = None) -> dict:
    """Run the existing Python business rules and return all output in memory."""
    customers = _validate(content, config)
    if bundled is None:
        bundled = (ROOT / "data" / "input" / "模拟数据.csv").read_bytes()
    exact_bundled = hashlib.sha256(content).digest() == hashlib.sha256(bundled).digest()
    uploaded_enabled = os.environ.get("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", "false").lower() == "true"
    if not exact_bundled and not (uploaded_enabled and _is_synthetic(content, customers, bundled)):
        raise HTTPException(403, "Only the bundled synthetic file is enabled by default; other SIM*/SYN* uploads need the server-side setting.")
    batch_size = int(config.get("batch_size", 20))
    if batch_size <= 0:
        raise HTTPException(503, "Configured batch_size must be positive.")
    provider = provider or CloudflareAzureResponsesProvider()
    messages: dict[str, str] = {}
    calls: list[dict] = []
    for batch in make_batches(customers, batch_size):
        payload, id_map = build_request_payload(batch)
        expected = set(id_map)
        codes = {local_id: choose_offer(customer).code
                 for local_id, customer in zip(id_map, batch)}
        response = await _generate_batch(provider, payload, config, api_key)
        valid, invalid = validate_response(response["output_text"], expected, codes)
        retries = int(config.get("record_retry_count", 0))
        for local_id, problem in list(invalid.items()):
            customer = batch[local_id - 1]
            for _ in range(retries):
                retry_payload, _ = build_request_payload((customer,))
                retry = await _generate_batch(provider, retry_payload, config, api_key)
                retry_valid, retry_errors = validate_response(
                    retry["output_text"], {1}, {1: choose_offer(customer).code},
                )
                calls.append(retry)
                if 1 in retry_valid:
                    valid[local_id] = retry_valid[1]
                    invalid.pop(local_id, None)
                    break
                problem = retry_errors.get(1, problem)
            if local_id in invalid:
                raise HTTPException(502, {
                    "message": "Message validation failed after retry; no result file was retained.",
                    "errors": [{"customer_id": id_map[local_id], "problem": problem}],
                })
        messages.update({id_map[local_id]: message for local_id, message in valid.items()})
        calls.append(response)

    results = []
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=OFFERS_COLUMNS, lineterminator="\n")
    writer.writeheader()
    distribution = {code: 0 for code in OFFER_LABELS}
    risk_index = Decimal(0)
    for customer in customers:
        decision = choose_offer(customer)
        distribution[decision.code] += 1
        risk_index += risk_weighted_mrr_index(customer)
        row = {
            "customer_id": customer.raw["customer_id"],
            "support_tier": customer.raw["support_tier"],
            "monthly_recurring_revenue": customer.raw["monthly_recurring_revenue"],
            "churn_probability": customer.raw["churn_probability"],
            "offer": decision.offer,
            "message": messages[customer.customer_id],
            "reason": decision.reason,
        }
        writer.writerow(row)
        results.append({**customer.raw, **row, "offer_code": decision.code,
                        "risk_weighted_mrr_index": str(risk_weighted_mrr_index(customer))})
    usage = {key: sum(call[key] or 0 for call in calls)
             for key in ("input_tokens", "output_tokens", "total_tokens")}
    return {
        "status": "completed", "total": len(results), "succeeded": len(results), "failed": 0,
        "results": results, "offer_distribution": distribution,
        "risk_weighted_mrr_index": float(risk_index),
        "risk_index_label": "Exploratory internal review index; not expected loss, forecast, ROI, or impact.",
        "synthetic_data": True, "human_approval_required": True,
        "token_usage": usage,
        "offers_csv": output.getvalue(),
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "cloudcore-person3-cloudflare"}


@app.get("/api/demo")
async def demo(request: Request):
    config = await _load_worker_config(request)
    content = await _read_asset(request, "simulated-data.csv")
    customers = _validate(content, config)
    return {"synthetic_data": True, "human_approval_required": True,
            "customers": [customer.raw for customer in customers]}


@app.post("/api/upload/validate")
async def upload_validate(request: Request, file: Annotated[UploadFile, File()]):
    config = await _load_worker_config(request)
    content = await _csv_content(file)
    customers = _validate(content, config)
    synthetic = _is_synthetic(content, customers, await _read_asset(request, "simulated-data.csv"))
    enabled = os.environ.get("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", "false").lower() == "true"
    can_analyze = synthetic and (content == await _read_asset(request, "simulated-data.csv") or enabled)
    return {"valid": True, "rows": len(customers), "customers": [c.raw for c in customers],
            "synthetic_data": synthetic, "analysis_allowed": can_analyze,
            "message": "Validated; ready for analysis." if can_analyze else
            "Validated only. Only the bundled synthetic file is enabled by default."}


@app.post("/api/analyze")
async def analyze(request: Request, file: Annotated[UploadFile | None, File()] = None):
    config = await _load_worker_config(request)
    content = (await _csv_content(file)) if file is not None else await _read_asset(request, "simulated-data.csv")
    key_name = config.get("api_key_env", "AZURE_OPENAI_API_KEY")
    api_key = getattr(request.scope.get("env"), key_name, "")
    if not api_key:
        api_key = os.environ.get(key_name, "")
    if not api_key:
        raise HTTPException(503, "Azure API key is not configured as a Cloudflare Worker Secret.")
    return await analyze_content(content, config, api_key, bundled=await _read_asset(request, "simulated-data.csv"))


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def frontend(path: str, request: Request):
    if request.url.path.startswith("/api/"):
        raise HTTPException(404, "API route not found.")
    env = request.scope.get("env")
    if env is None or not hasattr(env, "ASSETS"):
        raise HTTPException(404, "Static assets are served by the Cloudflare Worker.")
    asset_path = path or "index.html"
    response = await env.ASSETS.fetch(f"https://assets.local/{asset_path}")
    body = b"" if request.method == "HEAD" else bytes(await response.arrayBuffer())
    return Response(content=body, status_code=response.status,
                    media_type=response.headers.get("content-type", "application/octet-stream"))
