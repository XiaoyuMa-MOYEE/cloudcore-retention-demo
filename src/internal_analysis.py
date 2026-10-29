"""Exploratory, local-only review index."""

from decimal import Decimal

from .schemas import Customer


INTERPRETATION = (
    "Exploratory relative review index only; not expected loss, forecast revenue, ROI, "
    "intervention uplift, or a calibrated probability."
)


def risk_weighted_mrr_index(customer: Customer) -> Decimal:
    return customer.monthly_recurring_revenue * customer.churn_probability
