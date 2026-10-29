import csv
import json
from dataclasses import replace

from src.pipeline import run_live
from src.playbook import OFFER_LABELS
from src.providers.base import ProviderResult
from conftest import customer_row, write_csv


class MockProvider:
    instances = []

    def __init__(self, *args, **kwargs):
        self.calls = 0
        self.instances.append(self)

    def generate(self, payload, system_prompt, model):
        self.calls += 1
        results = []
        for row in payload["customers"]:
            offer = OFFER_LABELS[row["selected_offer"]]
            if row["selected_offer"] == "O1":
                phrase = "a free upgrade to Standard support for 3 months"
            elif row["selected_offer"] == "O2":
                phrase = "15% off the monthly fee for 3 months"
            elif row["selected_offer"] == "O3":
                phrase = "a free onboarding session"
            else:
                phrase = "an account manager call within 5 business days"
            results.append({"id": row["id"], "message": f"We're offering {phrase} for your Cloud Hosting service."})
        return ProviderResult(json.dumps({"results": results}), f"mock-{self.calls}", model, 10, 12, 22)


def test_mock_pipeline_publishes_exact_schema_and_resumes_without_calls(tmp_path, app_config, monkeypatch):
    import src.pipeline as pipeline

    rows = [customer_row("A1", tier="Basic"), customer_row("A2", tier="Standard", mrr="1500"),
            customer_row("A3", tier="Premium", tenure="11")]
    input_path = write_csv(tmp_path / "input.csv", rows)
    config = app_config
    config = replace(config, input_path=str(input_path), batch_size=2)
    MockProvider.instances.clear()
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", MockProvider)

    ok, summary = run_live(config, synthetic_data=True)
    assert ok, summary
    assert MockProvider.instances[-1].calls == 2
    with open(config.output_path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        output = list(reader)
        assert reader.fieldnames == ["customer_id", "support_tier", "monthly_recurring_revenue",
                                     "churn_probability", "offer", "message", "reason"]
    assert len(output) == 3

    ok, summary = run_live(config, synthetic_data=True)
    assert ok, summary
    assert MockProvider.instances[-1].calls == 0

    monkeypatch.setattr(pipeline, "SYSTEM_PROMPT", pipeline.SYSTEM_PROMPT + " Add a distinct natural opening.")
    ok, summary = run_live(config, synthetic_data=True)
    assert ok, summary
    assert MockProvider.instances[-1].calls == 2  # Prompt hash invalidates the previous checkpoint.


def test_prompt_change_invalidates_stale_checkpoint_and_old_offers(tmp_path, app_config, monkeypatch):
    import src.pipeline as pipeline

    input_path = write_csv(tmp_path / "prompt-change.csv", [customer_row("V1"), customer_row("V2")])
    config = replace(app_config, input_path=str(input_path), batch_size=2)
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", MockProvider)
    ok, summary = run_live(config, synthetic_data=True)
    assert ok, summary
    assert __import__("pathlib").Path(config.output_path).exists()

    monkeypatch.setattr(pipeline, "SYSTEM_PROMPT", pipeline.SYSTEM_PROMPT + " Use a different natural structure.")
    fake = BadProvider()
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", lambda *args, **kwargs: fake)
    ok, summary = run_live(config, synthetic_data=True)
    assert not ok
    assert fake.calls == 3
    assert not __import__("pathlib").Path(config.output_path).exists()


class PartialThenValidProvider:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    def generate(self, payload, system_prompt, model):
        self.calls += 1
        rows = payload["customers"]
        if len(rows) > 1:
            rows = rows[:1]
        results = [{"id": row["id"], "message": OFFER_LABELS[row["selected_offer"]]} for row in rows]
        return ProviderResult(json.dumps({"results": results}), f"partial-{self.calls}", model, 3, 4, 7)


def test_partial_batch_output_retries_only_missing_record(tmp_path, app_config, monkeypatch):
    import src.pipeline as pipeline

    input_path = write_csv(tmp_path / "partial.csv", [customer_row("P1"), customer_row("P2")])
    config = replace(app_config, input_path=str(input_path), batch_size=2)
    fake = PartialThenValidProvider()
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", lambda *args, **kwargs: fake)
    ok, summary = run_live(config, synthetic_data=True)
    assert ok, summary
    assert fake.calls == 2  # One batch response, then only the missing customer's retry.
    with open(config.output_path, encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 2


class FlakyProvider:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    def generate(self, payload, system_prompt, model):
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("temporary service issue")
        results = [{"id": row["id"], "message": OFFER_LABELS[row["selected_offer"]]}
                   for row in payload["customers"]]
        return ProviderResult(json.dumps({"results": results}), "flaky-ok", model, 4, 5, 9)


def test_transient_batch_failure_uses_bounded_configured_retries(tmp_path, app_config, monkeypatch):
    import src.pipeline as pipeline

    input_path = write_csv(tmp_path / "flaky.csv", [customer_row("R1")])
    config = replace(app_config, input_path=str(input_path), batch_retry_count=2)
    fake = FlakyProvider()
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", lambda *args, **kwargs: fake)
    monkeypatch.setattr(pipeline, "is_retryable_api_error", lambda exc: True)
    monkeypatch.setattr(pipeline.time, "sleep", lambda _: None)
    ok, summary = run_live(config, synthetic_data=True)
    assert ok, summary
    assert fake.calls == 3


class BadProvider:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    def generate(self, payload, system_prompt, model):
        self.calls += 1
        results = [{"id": row["id"], "message": "This is a generic welcome."}
                   for row in payload["customers"]]
        return ProviderResult(json.dumps({"results": results}), f"bad-{self.calls}", model, 2, 2, 4)


def test_unresolved_messages_write_errors_without_partial_offers(tmp_path, app_config, monkeypatch):
    import src.pipeline as pipeline

    input_path = write_csv(tmp_path / "bad.csv", [customer_row("E1"), customer_row("E2")])
    config = replace(app_config, input_path=str(input_path), batch_size=2, record_retry_count=1)
    fake = BadProvider()
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", lambda *args, **kwargs: fake)
    ok, summary = run_live(config, synthetic_data=True)
    assert not ok
    assert "incomplete" in summary.lower()
    assert not __import__("pathlib").Path(config.output_path).exists()
    with open(config.errors_path, encoding="utf-8", newline="") as handle:
        errors = list(csv.DictReader(handle))
    assert {row["customer_id"] for row in errors} == {"E1", "E2"}
    assert fake.calls == 3  # Batch attempt plus one retry per invalid record.


def test_real_data_gate_blocks_without_explicit_opt_in(app_config, monkeypatch):
    import src.pipeline as pipeline

    def fail_if_constructed(*args, **kwargs):
        raise AssertionError("provider must not be constructed when governance gate is closed")
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", fail_if_constructed)
    ok, summary = run_live(app_config, synthetic_data=False)
    assert not ok
    assert "BLOCKED" in summary


def test_nontransient_api_failure_is_not_retried(tmp_path, app_config, monkeypatch):
    import src.pipeline as pipeline

    class UnauthorizedProvider:
        def __init__(self, *args, **kwargs):
            self.calls = 0

        def generate(self, payload, system_prompt, model):
            self.calls += 1
            raise RuntimeError("authorization/configuration error")

    input_path = write_csv(tmp_path / "unauthorized.csv", [customer_row("U1")])
    config = replace(app_config, input_path=str(input_path), batch_retry_count=2)
    fake = UnauthorizedProvider()
    monkeypatch.setattr(pipeline, "OpenAIResponsesProvider", lambda *args, **kwargs: fake)
    monkeypatch.setattr(pipeline, "is_retryable_api_error", lambda exc: False)
    ok, summary = run_live(config, synthetic_data=True)
    assert not ok
    assert fake.calls == 1
    assert "incomplete" in summary.lower()
