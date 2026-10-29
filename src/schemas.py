"""Shared data structures and output contracts."""

from dataclasses import dataclass
from decimal import Decimal


INPUT_COLUMNS = (
    "customer_id",
    "industry",
    "region",
    "tenure_months",
    "products",
    "monthly_recurring_revenue",
    "support_tier",
    "churn_probability",
)

OFFERS_COLUMNS = (
    "customer_id",
    "support_tier",
    "monthly_recurring_revenue",
    "churn_probability",
    "offer",
    "message",
    "reason",
)

ANALYSIS_COLUMNS = (
    "customer_id",
    "risk_weighted_mrr_index",
    "interpretation",
)


@dataclass(frozen=True)
class Customer:
    """Validated record; raw field strings remain available for handoff fidelity."""

    source_row: int
    raw: dict[str, str]
    tenure_months: int
    monthly_recurring_revenue: Decimal
    churn_probability: Decimal

    @property
    def customer_id(self) -> str:
        return self.raw["customer_id"]


@dataclass(frozen=True)
class PlaybookDecision:
    code: str
    offer: str
    reason: str
