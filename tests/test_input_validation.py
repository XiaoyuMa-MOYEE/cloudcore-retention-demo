import csv

import pytest

from src.input_validation import validate_csv
from conftest import customer_row, write_csv


TIERS = ("Basic", "Standard", "Premium", "Enterprise")


@pytest.mark.parametrize(("tier", "raw_value"), [
    ("Basic", "  bAsIc  "),
    ("Standard", " standard "),
    ("Premium", " PREMIUM "),
    ("Enterprise", " enterprise "),
])
def test_all_four_valid_tiers_match_and_preserve_raw_value(tmp_path, tier, raw_value):
    path = write_csv(tmp_path / "valid.csv", [customer_row(tier=raw_value)])
    result = validate_csv(path, TIERS)
    assert result.valid
    assert result.customers[0].raw["support_tier"] == raw_value


@pytest.mark.parametrize("tier", ["Gold", "Platinum"])
def test_unknown_tier_is_reported_not_guessed(tmp_path, tier):
    path = write_csv(tmp_path / "unknown.csv", [customer_row(tier=tier)])
    result = validate_csv(path, TIERS)
    assert not result.valid
    assert any(i.field == "support_tier" and tier in i.problem for i in result.issues)
    assert result.customers == ()


@pytest.mark.parametrize(("field", "value"), [
    ("tenure_months", "1.5"),
    ("monthly_recurring_revenue", "-0.01"),
    ("churn_probability", "1.01"),
])
def test_invalid_numeric_values_are_rejected_without_source_edits(tmp_path, field, value):
    row = customer_row()
    row[field] = value
    path = write_csv(tmp_path / "invalid.csv", [row])
    before = path.read_bytes()
    result = validate_csv(path, TIERS)
    assert not result.valid
    assert any(issue.field == field for issue in result.issues)
    assert path.read_bytes() == before


def test_duplicate_ids_and_missing_columns_are_reported(tmp_path):
    path = write_csv(tmp_path / "duplicate.csv", [customer_row("D1"), customer_row("D1")])
    result = validate_csv(path, TIERS)
    assert any(issue.field == "customer_id" and "Duplicate" in issue.problem for issue in result.issues)

    row_without_region = customer_row()
    row_without_region.pop("region")
    columns = list(row_without_region)
    missing = write_csv(tmp_path / "missing.csv", [row_without_region], columns=columns)
    result = validate_csv(missing, TIERS)
    assert result.issues[0].field == "header"
    assert "region" in result.issues[0].problem
