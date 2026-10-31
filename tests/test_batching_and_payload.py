from src.batching import make_batches
from src.input_validation import validate_csv
from src.prompt import build_request_payload
from conftest import customer_row, write_csv


def test_partial_batch_and_minimal_allowlist_payload(tmp_path):
    rows = [customer_row(f"T{i}") for i in range(5)]
    path = write_csv(tmp_path / "five.csv", rows)
    records = validate_csv(path, ("Basic", "Standard", "Premium", "Enterprise")).customers
    batches = list(make_batches(records, 2))
    assert [len(batch) for batch in batches] == [2, 2, 1]

    payload, id_map = build_request_payload(batches[-1])
    record = payload["customers"][0]
    assert record == {
        "id": 1,
        "industry": "Technology",
        "products": "Cloud Hosting",
        "tenure_months": 18,
        "support_tier": "Standard",
        "selected_offer": "O4",
    }
    assert set(payload) == {"offer_code_dictionary", "customers"}
    assert id_map == {1: "T4"}
    assert make_batches(records, 20).__iter__().__next__() == records
