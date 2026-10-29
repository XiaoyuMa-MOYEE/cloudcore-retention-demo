import json
from types import SimpleNamespace

from src.providers.openai_responses import OpenAIResponsesProvider


def test_responses_adapter_uses_configured_endpoint_schema_and_no_private_fields(monkeypatch):
    import openai

    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                output_text='{"results":[{"id":1,"message":"draft"}]}',
                id="resp-test", model="gpt-5-mini",
                usage=SimpleNamespace(input_tokens=7, output_tokens=5, total_tokens=12),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-secret-never-logged")
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    provider = OpenAIResponsesProvider(
        "AZURE_OPENAI_API_KEY", "https://example.openai.azure.com/openai/v1/", 25,
    )
    payload = {
        "offer_code_dictionary": {"O1": "Free upgrade to Standard support for 3 months"},
        "customers": [{"id": 1, "industry": "Technology", "products": "Cloud Hosting",
                        "tenure_months": 8, "support_tier": "Basic", "selected_offer": "O1"}],
    }
    result = provider.generate(payload, "system prompt", "gpt-5-mini")
    request = captured["request"]
    client = captured["client"]
    assert client["base_url"] == "https://example.openai.azure.com/openai/v1/"
    assert client["timeout"] == 25 and client["max_retries"] == 0
    assert request["model"] == "gpt-5-mini" and request["store"] is False
    assert request["text"]["format"]["type"] == "json_schema"
    sent_user_text = request["input"][1]["content"][0]["text"]
    sent_payload = json.loads(sent_user_text)
    serialized_request = json.dumps(request)
    assert "customer_id" not in serialized_request and "monthly_recurring_revenue" not in serialized_request
    assert "churn_probability" not in serialized_request and "region" not in serialized_request
    assert sent_payload == payload
    assert result.input_tokens == 7 and result.output_tokens == 5 and result.total_tokens == 12
