import csv
from dataclasses import replace

import pytest

from src.config import load_config


INPUT_COLUMNS = (
    "customer_id", "industry", "region", "tenure_months", "products",
    "monthly_recurring_revenue", "support_tier", "churn_probability",
)


def write_csv(path, rows, columns=INPUT_COLUMNS):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def customer_row(customer_id="T001", *, tier="Standard", mrr="2500", tenure="18", score="0.5"):
    return {
        "customer_id": customer_id,
        "industry": "Technology",
        "region": "WA",
        "tenure_months": tenure,
        "products": "Cloud Hosting",
        "monthly_recurring_revenue": mrr,
        "support_tier": tier,
        "churn_probability": score,
    }


@pytest.fixture
def app_config(tmp_path):
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    base = load_config(root / "config.yaml")
    return replace(
        base,
        input_path=str(tmp_path / "input.csv"),
        output_path=str(tmp_path / "offers.csv"),
        analysis_path=str(tmp_path / "internal_analysis.csv"),
        errors_path=str(tmp_path / "errors.csv"),
        generation_log_path=str(tmp_path / "generation_log.json"),
        validation_report_path=str(tmp_path / "validation.csv"),
        prepared_requests_path=str(tmp_path / "prepared.json"),
        prepared_id_map_path=str(tmp_path / "id-map.json"),
        checkpoint_path=str(tmp_path / "checkpoint.json"),
    )
