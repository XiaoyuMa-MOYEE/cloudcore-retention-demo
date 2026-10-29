"""Authenticated FastAPI wrapper around the existing Python Person 3 pipeline."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import load_config
from src.input_validation import validate_csv
from src.internal_analysis import risk_weighted_mrr_index
from src.playbook import choose_offer
from src.schemas import INPUT_COLUMNS, OFFERS_COLUMNS
from src.pipeline import run_live
from src.providers.mock import MockProvider


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False, encoding="utf-8-sig")
CONFIG_PATH = Path(os.environ.get("CLOUDCORE_CONFIG", ROOT / "config.yaml")).resolve()
BASE_CONFIG = load_config(CONFIG_PATH)
RUNTIME = Path(os.environ.get("CLOUDCORE_RUNTIME_DIR", ROOT / "data" / "web_runtime")).resolve()
RUNTIME.mkdir(parents=True, exist_ok=True)
DB_PATH = RUNTIME / "tasks.sqlite3"
SYNTHETIC_PATH = ROOT / "data" / "input" / "模拟数据.csv"
SESSION_TTL = int(os.environ.get("SESSION_TTL_SECONDS", "28800"))
COOKIE_NAME = "cloudcore_session"
POOL = ThreadPoolExecutor(max_workers=max(1, int(os.environ.get("WEB_WORKERS", "2"))))
LOCK = threading.Lock()

app = FastAPI(title="CloudCore Person 3 Demo", version="0.3.0", docs_url=None, redoc_url=None)


class LoginRequest(BaseModel):
    access_code: str


class RetryRequest(BaseModel):
    failed_only: bool = True


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, source TEXT NOT NULL,
            total INTEGER NOT NULL, started_at REAL NOT NULL, updated_at REAL NOT NULL,
            error TEXT, attempt INTEGER NOT NULL DEFAULT 1, provider_mode TEXT NOT NULL DEFAULT 'azure'
        )""")
        conn.execute("UPDATE tasks SET status='interrupted', error='Server restarted during processing; retry to resume.' WHERE status='running'")


_init_db()


def _secret(name: str) -> str:
    return os.environ.get(name, "")


def _cookie_signature(expiry: str) -> str:
    secret = _secret("SESSION_SECRET")
    if len(secret) < 32:
        raise HTTPException(503, "Session signing secret must be configured with at least 32 characters.")
    return hmac.new(secret.encode(), expiry.encode(), hashlib.sha256).hexdigest()


def _session_ok(cookie: str | None) -> bool:
    if not cookie or "." not in cookie:
        return False
    expiry, signature = cookie.split(".", 1)
    if not expiry.isdigit() or int(expiry) < int(time.time()):
        return False
    expected = _cookie_signature(expiry)
    return hmac.compare_digest(signature, expected)


def _require_session(request: Request) -> None:
    if not _session_ok(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(401, "Please sign in to continue.")


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    expected = os.environ.get("PUBLIC_ORIGIN", "http://127.0.0.1:5173").rstrip("/")
    if not origin or origin.rstrip("/") != expected:
        raise HTTPException(403, "Cross-origin request rejected.")


def _write_task(task_id: str, **updates) -> None:
    allowed = {"status", "total", "updated_at", "error", "attempt"}
    updates = {key: value for key, value in updates.items() if key in allowed}
    updates["updated_at"] = time.time()
    fields = ", ".join(f"{key}=?" for key in updates)
    with _db() as conn:
        conn.execute(f"UPDATE tasks SET {fields} WHERE id=?", (*updates.values(), task_id))


def _task(task_id: str) -> sqlite3.Row:
    with _db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Analysis task not found.")
    return row


def _task_paths(task_id: str) -> dict[str, str]:
    folder = RUNTIME / task_id
    folder.mkdir(parents=True, exist_ok=True)
    return {
        "input_path": str(folder / "input.csv"), "output_path": str(folder / "offers.csv"),
        "analysis_path": str(folder / "analysis.csv"), "errors_path": str(folder / "errors.csv"),
        "generation_log_path": str(folder / "generation_log.json"),
        "validation_report_path": str(folder / "validation.csv"),
        "prepared_requests_path": str(folder / "prepared.json"),
        "prepared_id_map_path": str(folder / "id-map.json"),
        "checkpoint_path": str(folder / "checkpoint.json"),
    }


def _load_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _ensure_synthetic_bytes(content: bytes) -> bool:
    """Only the bundled, reviewed synthetic dataset is externally eligible by default."""
    try:
        digest = hashlib.sha256(SYNTHETIC_PATH.read_bytes()).digest()
    except OSError:
        return False
    return hmac.compare_digest(hashlib.sha256(content).digest(), digest)


def _validate_bytes(content: bytes) -> tuple[Path, list[dict], list[dict]]:
    if len(content) > 2_000_000:
        raise HTTPException(413, "CSV must be 2 MB or smaller.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8 encoded.") from None
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if (reader.fieldnames is None or set(reader.fieldnames) != set(INPUT_COLUMNS)
                or len(reader.fieldnames) != len(INPUT_COLUMNS)):
            raise HTTPException(400, {"message": "CSV must contain exactly the required eight input columns.", "expected_columns": INPUT_COLUMNS})
        if sum(1 for _ in reader) > 500:
            raise HTTPException(413, "CSV is limited to 500 rows.")
    except csv.Error as exc:
        raise HTTPException(400, f"Invalid CSV: {exc}") from None
    digest_name = uuid.uuid4().hex + ".csv"
    upload_path = RUNTIME / "validation" / digest_name
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)
    result = validate_csv(upload_path, BASE_CONFIG.valid_support_tiers)
    errors = [
        {"row_number": issue.row_number, "customer_id": issue.customer_id,
         "field": issue.field, "problem": issue.problem} for issue in result.issues
    ]
    if errors:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(422, {"message": "Input schema validation failed; the CSV was not modified.", "errors": errors})
    rows = _load_records(upload_path)
    if not rows:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(422, "CSV must contain at least one customer record.")
    return upload_path, rows, errors


def _enriched(rows: list[dict[str, str]]) -> list[dict]:
    # Build a transient validated CSV for reusing the exact Python validation and rules.
    import tempfile
    import csv as csv_module
    import os as os_module
    fd, name = tempfile.mkstemp(suffix=".csv", dir=RUNTIME)
    try:
        with os_module.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv_module.DictWriter(handle, fieldnames=INPUT_COLUMNS)
            writer.writeheader(); writer.writerows(rows)
        validated = validate_csv(name, BASE_CONFIG.valid_support_tiers)
        return [{
            **customer.raw,
            "offer_code": choose_offer(customer).code,
            "offer": choose_offer(customer).offer,
            "reason": choose_offer(customer).reason,
            "risk_weighted_mrr_index": str(risk_weighted_mrr_index(customer)),
        } for customer in validated.customers]
    finally:
        Path(name).unlink(missing_ok=True)


def _checkpoint_counts(task_id: str, total: int) -> tuple[int, int]:
    checkpoint = RUNTIME / task_id / "checkpoint.json"
    try:
        messages = json.loads(checkpoint.read_text(encoding="utf-8")).get("messages", {})
        success = len(messages)
    except (OSError, json.JSONDecodeError):
        success = 0
    errors_path = RUNTIME / task_id / "errors.csv"
    try:
        with errors_path.open("r", encoding="utf-8", newline="") as handle:
            failed = max(0, sum(1 for _ in csv.DictReader(handle)))
    except OSError:
        failed = max(0, total - success) if _task(task_id)["status"] in ("failed", "interrupted") else 0
    return min(success, total), min(failed, max(0, total - success))


def _run_task(task_id: str, mode: str) -> None:
    row = _task(task_id)
    paths = _task_paths(task_id)
    cfg = replace(BASE_CONFIG, **paths)
    _write_task(task_id, status="running", error=None)
    try:
        ok, summary = run_live(
            cfg, paths["input_path"], synthetic_data=True,
            provider_override=MockProvider() if mode == "mock" else None,
        )
        _write_task(task_id, status="completed" if ok else "failed", error=None if ok else summary)
    except Exception as exc:
        # Avoid returning exception text from third-party clients; it may contain request details.
        _write_task(task_id, status="failed", error=f"{type(exc).__name__}: processing failed. Check server logs.")


def _start_task(task_id: str, mode: str) -> None:
    with LOCK:
        _write_task(task_id, status="running", error=None)
        POOL.submit(_run_task, task_id, mode)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "cloudcore-person3"}


@app.post("/api/login")
def login(body: LoginRequest, request: Request, response: Response):
    _check_origin(request)
    expected = _secret("GROUP_ACCESS_CODE")
    if not expected or not _secret("SESSION_SECRET"):
        raise HTTPException(503, "Group access is not configured on the server.")
    if not hmac.compare_digest(body.access_code.encode(), expected.encode()):
        raise HTTPException(401, "The access code is not valid.")
    expiry = str(int(time.time()) + SESSION_TTL)
    response.set_cookie(COOKIE_NAME, f"{expiry}.{_cookie_signature(expiry)}", httponly=True,
                        secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
                        samesite="strict", max_age=SESSION_TTL, path="/")
    return {"authenticated": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    _require_session(request); _check_origin(request)
    response.delete_cookie(COOKIE_NAME, httponly=True,
                           secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
                           samesite="strict", path="/")
    return {"authenticated": False}


@app.get("/api/session")
def session(request: Request):
    return {"authenticated": _session_ok(request.cookies.get(COOKIE_NAME))}


@app.get("/api/demo")
def demo(request: Request):
    _require_session(request)
    rows = _load_records(SYNTHETIC_PATH)
    return {"synthetic_data": True, "human_approval_required": True, "customers": _enriched(rows)}


@app.post("/api/upload/validate")
async def upload_validate(request: Request, file: Annotated[UploadFile, File()]):
    _require_session(request); _check_origin(request)
    content = await file.read(2_000_001)
    path, rows, _ = _validate_bytes(content)
    exact_demo = _ensure_synthetic_bytes(content)
    uploaded_synthetic = (
        os.environ.get("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", "false").lower() == "true"
        and bool(rows)
        and all(row["customer_id"].strip().upper().startswith(("SIM", "SYN")) for row in rows)
    )
    path.unlink(missing_ok=True)
    can_analyze = exact_demo or uploaded_synthetic
    return {"valid": True, "rows": len(rows), "customers": rows,
            "synthetic_data": exact_demo or uploaded_synthetic,
            "analysis_allowed": can_analyze,
            "message": "Validated only. Uploaded files may be analyzed only when the server administrator enables uploaded synthetic data." if not can_analyze else "Validated; ready for analysis."}


def _create_task(content: bytes, source: str, mode: str) -> dict:
    if mode not in ("mock", "live"):
        raise HTTPException(400, "Unsupported analysis provider mode.")
    if mode == "live" and BASE_CONFIG.provider not in ("azure_openai", "openai"):
        raise HTTPException(503, f"Unsupported configured provider: {BASE_CONFIG.provider}.")
    validation_path, rows, _ = _validate_bytes(content)
    exact_demo = _ensure_synthetic_bytes(content)
    uploaded_enabled = os.environ.get("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", "false").lower() == "true"
    if not exact_demo and not uploaded_enabled:
        validation_path.unlink(missing_ok=True)
        raise HTTPException(403, "Only the bundled synthetic demo dataset is enabled for analysis by default.")
    if mode == "live" and not _secret(BASE_CONFIG.api_key_env):
        validation_path.unlink(missing_ok=True)
        raise HTTPException(503, f"{BASE_CONFIG.api_key_env} is not configured on the server.")
    if not exact_demo and uploaded_enabled:
        if any(not row["customer_id"].strip().upper().startswith(("SIM", "SYN")) for row in rows):
            validation_path.unlink(missing_ok=True)
            raise HTTPException(403, "Uploaded analysis is restricted to synthetic SIM*/SYN* customer IDs.")
    task_id = uuid.uuid4().hex
    paths = _task_paths(task_id)
    Path(paths["input_path"]).write_bytes(content)
    validation_path.unlink(missing_ok=True)
    now = time.time()
    with _db() as conn:
        conn.execute("INSERT INTO tasks(id,status,source,total,started_at,updated_at,provider_mode) VALUES(?,?,?,?,?,?,?)",
                     (task_id, "queued", source, len(rows), now, now, mode))
    _start_task(task_id, mode)
    return {"task_id": task_id, "status": "running", "total": len(rows), "provider_mode": mode,
            "synthetic_data": True, "human_approval_required": True}


@app.post("/api/analysis")
def start_analysis(request: Request, mode: str = "live"):
    _require_session(request); _check_origin(request)
    return _create_task(SYNTHETIC_PATH.read_bytes(), "bundled_synthetic", mode)


@app.post("/api/analysis/upload")
async def start_uploaded_analysis(request: Request, file: Annotated[UploadFile, File()], mode: str = "live"):
    _require_session(request); _check_origin(request)
    content = await file.read(2_000_001)
    return _create_task(content, "uploaded_csv", mode)


@app.post("/api/analysis/{task_id}/retry")
def retry_analysis(task_id: str, request: Request, body: RetryRequest):
    _require_session(request); _check_origin(request)
    task = _task(task_id)
    if task["status"] not in ("failed", "interrupted"):
        raise HTTPException(409, "Only failed or interrupted analysis tasks can be retried.")
    mode = task["provider_mode"]
    attempt = task["attempt"] + 1
    _write_task(task_id, attempt=attempt)
    _start_task(task_id, mode)
    return {"task_id": task_id, "status": "running", "attempt": attempt}


@app.get("/api/analysis/latest")
def latest_analysis(request: Request):
    _require_session(request)
    with _db() as conn:
        row = conn.execute("SELECT id FROM tasks ORDER BY started_at DESC LIMIT 1").fetchone()
    return {"task": analysis_status(row["id"], request) if row else None}


@app.get("/api/analysis/{task_id}")
def analysis_status(task_id: str, request: Request):
    _require_session(request)
    task = _task(task_id)
    succeeded, failed = _checkpoint_counts(task_id, task["total"])
    result = {"task_id": task_id, "status": task["status"], "total": task["total"],
              "succeeded": succeeded, "failed": failed, "error": task["error"], "attempt": task["attempt"]}
    if task["status"] in ("failed", "interrupted"):
        error_path = RUNTIME / task_id / "errors.csv"
        try:
            with error_path.open("r", encoding="utf-8", newline="") as handle:
                result["failed_records"] = list(csv.DictReader(handle))
        except OSError:
            result["failed_records"] = []
    if task["status"] == "completed":
        out = RUNTIME / task_id / "offers.csv"
        if not out.exists():
            raise HTTPException(500, "Task marked completed without a published result.")
        from src.playbook import OFFER_LABELS
        with out.open("r", encoding="utf-8", newline="") as handle:
            result["results"] = [
                {**item, "offer_code": next((code for code, label in OFFER_LABELS.items() if label == item.get("offer")), "")}
                for item in csv.DictReader(handle)
            ]
        result["synthetic_data"] = True
        result["human_approval_required"] = True
        result["offer_distribution"] = _offer_distribution(result["results"])
        analysis = RUNTIME / task_id / "analysis.csv"
        with analysis.open("r", encoding="utf-8", newline="") as handle:
            indices = [Decimal(item["risk_weighted_mrr_index"]) for item in csv.DictReader(handle)]
        result["risk_weighted_mrr_index"] = float(sum(indices, Decimal(0)))
        result["risk_index_label"] = "Exploratory internal review index; not expected loss, forecast, ROI, or impact."
    return result


def _offer_distribution(rows: list[dict]) -> dict[str, int]:
    from src.playbook import OFFER_LABELS
    labels = {label: code for code, label in OFFER_LABELS.items()}
    result: dict[str, int] = {}
    for row in rows:
        code = labels.get(row["offer"], "Unknown")
        result[code] = result.get(code, 0) + 1
    return result


@app.get("/api/analysis/{task_id}/download")
def download(task_id: str, request: Request):
    _require_session(request)
    if _task(task_id)["status"] != "completed":
        raise HTTPException(409, "Results are available only after all records have completed successfully.")
    path = RUNTIME / task_id / "offers.csv"
    if not path.is_file():
        raise HTTPException(404, "Result file not found.")
    content = path.read_bytes()
    return StreamingResponse(io.BytesIO(content), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="offers.csv"',
                                      "X-Output-Columns": ",".join(OFFERS_COLUMNS)})
