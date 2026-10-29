"""Deterministic ordered retention-offer rules."""

from .schemas import Customer, PlaybookDecision


OFFER_LABELS = {
    "O1": "Free upgrade to Standard support for 3 months",
    "O2": "15% off the monthly fee for 3 months",
    "O3": "Free onboarding session",
    "O4": "Account manager call within 5 business days",
}


def choose_offer(customer: Customer) -> PlaybookDecision:
    """Apply only the first matching Playbook rule."""
    tier = customer.raw["support_tier"].strip().casefold()
    if tier == "basic":
        return PlaybookDecision("O1", OFFER_LABELS["O1"],
                                "Customer is on Basic support; first playbook rule applies.")
    if customer.monthly_recurring_revenue < 2000:
        return PlaybookDecision("O2", OFFER_LABELS["O2"],
                                "Customer's MRR is below $2,000 and the preceding rule did not apply.")
    if customer.tenure_months < 12:
        return PlaybookDecision("O3", OFFER_LABELS["O3"],
                                "Customer tenure is below 12 months and the preceding rules did not apply.")
    return PlaybookDecision("O4", OFFER_LABELS["O4"],
                            "None of the first three playbook conditions applies.")
