import csv
import inspect
import io
import json
from pathlib import Path

import yaml

from backend.cloudflare_app import analyze_content
from src.schemas import OFFERS_COLUMNS


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "input" / "模拟数据.csv"
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def run_inline(coroutine):
    """Drive immediate Mock-provider coroutines without opening a local socket loop."""
    send_value = None
    while True:
        try:
            yielded = coroutine.send(send_value)
            send_value = None
        except StopIteration as done:
            return done.value
        if inspect.iscoroutine(yielded):
            send_value = run_inline(yielded)
        elif yielded is not None:
            raise AssertionError("Mock coroutine unexpectedly awaited an external operation.")


class MockResponsesProvider:
    def __init__(self):
        self.calls = 0
        self.payloads = []

    async def generate(self, payload, system_prompt, model, **kwargs):
        self.calls += 1
        self.payloads.append(payload)
        descriptions = {
            "O1": "We are offering a free upgrade to Standard support for 3 months.",
            "O2": "We are offering 15% off the monthly fee for 3 months.",
            "O3": "We are offering a free onboarding session.",
            "O4": "We are offering an account manager call within 5 business days.",
        }
        return {
            "output_text": json.dumps({"results": [
                {"id": customer["id"], "message": descriptions[customer["selected_offer"]]}
                for customer in payload["customers"]
            ]}),
            "input_tokens": 12, "output_tokens": 20, "total_tokens": 32,
        }


def test_demo_is_processed_in_memory_in_batches_and_exports_exact_seven_columns():
    content = DEMO.read_bytes()
    provider = MockResponsesProvider()
    result = run_inline(analyze_content(content, CONFIG, "mock-key", provider, bundled=content))

    assert result["status"] == "completed"
    assert result["total"] == result["succeeded"] == 45
    assert result["failed"] == 0
    assert provider.calls == 3
    assert result["token_usage"] == {"input_tokens": 36, "output_tokens": 60, "total_tokens": 96}
    exported = list(csv.DictReader(io.StringIO(result["offers_csv"])))
    assert len(exported) == 45
    assert tuple(exported[0]) == OFFERS_COLUMNS
    assert all(len(row["message"].split()) <= 80 for row in exported)


def test_uploaded_customer_data_is_analyzed_without_sending_customer_identifiers():
    content = DEMO.read_bytes().replace(b"SIM001", b"CUS001", 1)
    provider = MockResponsesProvider()
    result = run_inline(analyze_content(content, CONFIG, "mock-key", provider, bundled=DEMO.read_bytes()))
    assert result["status"] == "completed"
    assert result["synthetic_data"] is False
    assert provider.calls == 3
    sent_customers = [customer for payload in provider.payloads for customer in payload["customers"]]
    assert all(set(customer) == {"id", "industry", "products", "tenure_months", "support_tier", "selected_offer"}
               for customer in sent_customers)
    assert "CUS001" not in json.dumps(provider.payloads)


def test_uploaded_csv_analysis_does_not_depend_on_synthetic_upload_flag(monkeypatch):
    content = DEMO.read_bytes().replace(b"SIM001", b"SIM901", 1)
    provider = MockResponsesProvider()
    monkeypatch.delenv("ALLOW_UPLOADED_SYNTHETIC_ANALYSIS", raising=False)
    result = run_inline(analyze_content(content, CONFIG, "mock-key", provider, bundled=DEMO.read_bytes()))
    assert result["succeeded"] == 45
