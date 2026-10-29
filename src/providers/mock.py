"""Deterministic local provider used for web UI and API regression checks."""

import json

from .base import ProviderResult


class MockProvider:
    def generate(self, payload: dict, system_prompt: str = "", model: str | None = None) -> ProviderResult:
        styles = {
            "O1": ("We’re pleased to offer a", "We’d like to extend a"),
            "O2": ("We’re pleased to offer", "You may consider"),
            "O3": ("We’re offering a", "We’d like to offer a"),
            "O4": ("We’d like to offer an", "One option is an"),
        }
        offer_phrases = {
            "O1": "free upgrade to Standard support for 3 months",
            "O2": "15% off the monthly fee for 3 months",
            "O3": "free onboarding session",
            "O4": "account manager call within 5 business days",
        }
        results = []
        for row in payload["customers"]:
            code = row["selected_offer"]
            subject = (row.get("products") or "your service").split("+")[0].strip()
            lead = styles[code][(row["id"] - 1) % 2]
            results.append({"id": row["id"], "message": f"{lead} {offer_phrases[code]} for your {subject} service."})
        return ProviderResult(json.dumps({"results": results}), f"mock-{id(payload)}", "mock-provider", 0, 0, 0)
