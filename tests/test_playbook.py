from decimal import Decimal
from pathlib import Path

from src.input_validation import validate_csv
from src.playbook import OFFER_LABELS, choose_offer
from src.schemas import Customer


def make_customer(tier, mrr, tenure):
    return Customer(
        source_row=2,
        raw={"customer_id": "T1", "industry": "Tech", "region": "WA",
             "tenure_months": str(tenure), "products": "Cloud", "monthly_recurring_revenue": str(mrr),
             "support_tier": tier, "churn_probability": "0.5"},
        tenure_months=tenure,
        monthly_recurring_revenue=Decimal(str(mrr)),
        churn_probability=Decimal("0.5"),
    )


def test_first_matching_playbook_rule_wins():
    assert choose_offer(make_customer("Basic", 100, 1)).code == "O1"
    assert choose_offer(make_customer("Standard", 1999.99, 1)).code == "O2"
    assert choose_offer(make_customer("Premium", 2000, 11)).code == "O3"
    assert choose_offer(make_customer("Premium", 2000, 12)).code == "O4"
    assert set(OFFER_LABELS) == {"O1", "O2", "O3", "O4"}


def test_basic_matching_trims_and_ignores_case_but_preserves_input(tmp_path):
    from conftest import customer_row, write_csv

    path = write_csv(tmp_path / "tier.csv", [customer_row(tier="  bAsIc  ", mrr="100")])
    result = validate_csv(path, ("Basic", "Standard", "Premium"))
    assert result.valid
    assert result.customers[0].raw["support_tier"] == "  bAsIc  "
    assert choose_offer(result.customers[0]).code == "O1"


def test_all_sixteen_synthetic_policy_cases_match_expected_codes():
    from src.input_validation import validate_csv

    fixture = Path(__file__).parent / "fixtures" / "synthetic_policy_16.csv"
    records = validate_csv(fixture, ("Basic", "Standard", "Premium"))
    assert records.valid
    expected = ["O1", "O1", "O2", "O2", "O2", "O2", "O3", "O3",
                "O4", "O4", "O4", "O1", "O1", "O3", "O4", "O2"]
    assert [choose_offer(record).code for record in records.customers] == expected
