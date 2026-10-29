"""Read-only validation for the upstream CSV contract."""

import csv
import io
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .schemas import Customer, INPUT_COLUMNS


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int | None
    customer_id: str
    field: str
    problem: str


@dataclass(frozen=True)
class ValidationResult:
    customers: tuple[Customer, ...]
    issues: tuple[ValidationIssue, ...]
    row_count: int

    @property
    def valid(self) -> bool:
        return not self.issues


def validate_csv(path: str | Path, valid_support_tiers: tuple[str, ...]) -> ValidationResult:
    """Validate without trimming, normalizing, or rewriting any source field."""
    csv_path = Path(path)
    try:
        handle = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        return ValidationResult((), (ValidationIssue(None, "", "file", str(exc)),), 0)

    with handle:
        return validate_csv_text(handle.read(), valid_support_tiers)


def validate_csv_text(text: str, valid_support_tiers: tuple[str, ...]) -> ValidationResult:
    """Validate CSV text in memory without modifying its source values."""
    issues: list[ValidationIssue] = []
    customers: list[Customer] = []
    seen: dict[str, int] = {}
    tier_lookup = {tier.strip().casefold() for tier in valid_support_tiers}
    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = reader.fieldnames
    if header is None:
        return ValidationResult((), (ValidationIssue(1, "", "header", "CSV is empty or has no header."),), 0)
    missing = [name for name in INPUT_COLUMNS if name not in header]
    extra = [name for name in header if name not in INPUT_COLUMNS]
    duplicate_headers = sorted({name for name in header if header.count(name) > 1})
    if missing or extra or duplicate_headers:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected columns: {', '.join(extra)}")
        if duplicate_headers:
            details.append(f"duplicate column names: {', '.join(duplicate_headers)}")
        return ValidationResult((), (ValidationIssue(1, "", "header", "; ".join(details)),), 0)

    row_count = 0
    for row_number, row in enumerate(reader, start=2):
        row_count += 1
        if None in row:
            issues.append(ValidationIssue(row_number, "", "row", "Row has more values than the header."))
            continue
        raw = {key: row.get(key) for key in INPUT_COLUMNS}
        customer_id = raw["customer_id"] or ""
        row_has_issue = False

        for field in ("customer_id", "industry", "region", "products", "support_tier"):
            value = raw[field]
            if value is None or not value.strip():
                issues.append(ValidationIssue(row_number, customer_id, field, "Required value is empty."))
                row_has_issue = True
        if customer_id:
            if customer_id in seen:
                issues.append(ValidationIssue(row_number, customer_id, "customer_id",
                                              f"Duplicate ID; first seen on row {seen[customer_id]}."))
                row_has_issue = True
            else:
                seen[customer_id] = row_number

        tier = raw["support_tier"] or ""
        if tier.strip() and tier.strip().casefold() not in tier_lookup:
            issues.append(ValidationIssue(row_number, customer_id, "support_tier",
                f"Unknown support tier {tier!r}; valid values are: {', '.join(valid_support_tiers)}. Confirm/correct upstream data."))
            row_has_issue = True

        tenure = _parse_integer(raw["tenure_months"])
        if tenure is None or tenure < 0:
            issues.append(ValidationIssue(row_number, customer_id, "tenure_months",
                                          "Must be an integer greater than or equal to 0."))
            row_has_issue = True
        mrr = _parse_decimal(raw["monthly_recurring_revenue"])
        if mrr is None or mrr < 0:
            issues.append(ValidationIssue(row_number, customer_id, "monthly_recurring_revenue",
                                          "Must be a finite decimal greater than or equal to 0."))
            row_has_issue = True
        probability = _parse_decimal(raw["churn_probability"])
        if probability is None or probability < 0 or probability > 1:
            issues.append(ValidationIssue(row_number, customer_id, "churn_probability",
                                          "Must be a finite number in [0, 1]."))
            row_has_issue = True

        if not row_has_issue:
            customers.append(Customer(row_number, raw, tenure, mrr, probability))

    return ValidationResult(tuple(customers), tuple(issues), row_count)


def _parse_integer(value: str | None) -> int | None:
    if value is None or not re.fullmatch(r"[+-]?\d+", value.strip()):
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None
