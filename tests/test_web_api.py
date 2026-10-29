import csv
import time
from pathlib import Path

import pytest
from fastapi import HTTPException, Request, Response

from backend import app as web
from backend.app import LoginRequest


@pytest.fixture
def isolated_web_app(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "RUNTIME", tmp_path / "runtime")
    web.RUNTIME.mkdir()
    monkeypatch.setattr(web, "DB_PATH", web.RUNTIME / "tasks.sqlite3")
    monkeypatch.setenv("GROUP_ACCESS_CODE", "test-only-access")
    monkeypatch.setenv("SESSION_SECRET", "test-only-session-secret-that-is-long-enough")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", "false")
    web._init_db()
    return web.app


def request_with_cookie(cookie: str | None = None) -> Request:
    headers = [(b"origin", b"http://127.0.0.1:5173")]
    if cookie is not None:
        headers.append((b"cookie", f"{web.COOKIE_NAME}={cookie}".encode()))
    return Request({"type": "http", "method": "GET", "scheme": "https", "path": "/api/demo",
                    "query_string": b"", "headers": headers, "server": ("cloudcore.test", 443),
                    "client": ("127.0.0.1", 1234)})


def test_api_requires_session_and_login_sets_secure_cookie_attributes(isolated_web_app):
    with pytest.raises(HTTPException) as denied:
        web.demo(request_with_cookie())
    assert denied.value.status_code == 401

    response = Response()
    result = web.login(LoginRequest(access_code="test-only-access"), request_with_cookie(), response)
    assert result["authenticated"] is True
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "secure" in cookie
    token = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
    assert web.demo(request_with_cookie(token))["synthetic_data"] is True


def test_demo_load_does_not_start_model_task(isolated_web_app):
    expiry = str(int(time.time()) + 3600)
    token = f"{expiry}.{web._cookie_signature(expiry)}"
    response = web.demo(request_with_cookie(token))
    assert len(response["customers"]) == 45
    with web._db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0


def test_bad_csv_is_rejected_with_validation_detail(isolated_web_app):
    bad = b"customer_id,industry,region,tenure_months,products,monthly_recurring_revenue,support_tier,churn_probability\nX1,Tech,WA,2,Hosting,20,Unknown,0.5\n"
    with pytest.raises(HTTPException) as rejected:
        web._validate_bytes(bad)
    assert rejected.value.status_code == 422
    assert rejected.value.detail["errors"][0]["field"] == "support_tier"
    with pytest.raises(HTTPException) as empty:
        web._validate_bytes(b"customer_id,industry,region,tenure_months,products,monthly_recurring_revenue,support_tier,churn_probability\n")
    assert empty.value.status_code == 422


def test_valid_csv_is_preserved_and_uploaded_policy_requires_synthetic_ids(isolated_web_app, monkeypatch):
    original = web.SYNTHETIC_PATH.read_bytes()
    altered = original.replace(b"SIM001", b"CUS001", 1)
    saved_path, rows, _ = web._validate_bytes(altered)
    assert saved_path.read_bytes() == altered
    assert rows[0]["customer_id"] == "CUS001"
    saved_path.unlink()

    monkeypatch.setenv("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", "true")
    with pytest.raises(HTTPException) as blocked:
        web._create_task(altered, "uploaded_csv", "mock")
    assert blocked.value.status_code == 403


def test_only_bundled_dataset_runs_by_default_and_mock_pipeline_completes(isolated_web_app):
    altered = web.SYNTHETIC_PATH.read_bytes().replace(b"SIM001", b"SIMX01", 1)
    assert web._ensure_synthetic_bytes(altered) is False
    assert web._ensure_synthetic_bytes(web.SYNTHETIC_PATH.read_bytes()) is True
    with pytest.raises(HTTPException) as blocked:
        web._create_task(altered, "uploaded_csv", "mock")
    assert blocked.value.status_code == 403

    task_id = "mock-v03-test"
    paths = web._task_paths(task_id)
    Path(paths["input_path"]).write_bytes(web.SYNTHETIC_PATH.read_bytes())
    now = time.time()
    with web._db() as conn:
        conn.execute("INSERT INTO tasks(id,status,source,total,started_at,updated_at,provider_mode) VALUES(?,?,?,?,?,?,?)",
                     (task_id, "queued", "bundled_synthetic", 45, now, now, "mock"))
    web._run_task(task_id, "mock")
    task = web._task(task_id)
    assert task["status"] == "completed", task["error"]
    expiry = str(int(time.time() + 3600))
    status = web.analysis_status(task_id, request_with_cookie(f"{expiry}." + web._cookie_signature(expiry)))
    assert web.latest_analysis(request_with_cookie(f"{expiry}." + web._cookie_signature(expiry)))["task"]["task_id"] == task_id
    assert status["succeeded"] == 45
    assert status["failed"] == 0
    assert status["human_approval_required"] is True
    assert set(status["offer_distribution"]) <= {"O1", "O2", "O3", "O4"}
    assert len(status["results"]) == 45
    assert all(len(item["message"].split()) <= 80 for item in status["results"])
    assert all("approval" not in item["message"].lower() for item in status["results"])
    with open(paths["output_path"], "r", encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == ["customer_id", "support_tier", "monthly_recurring_revenue", "churn_probability", "offer", "message", "reason"]
