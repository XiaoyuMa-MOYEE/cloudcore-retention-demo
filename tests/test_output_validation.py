import json

import pytest

from src.output_validation import validate_response
from src.prompt import SYSTEM_PROMPT


VALID_MESSAGES = {
    "O1": "We can provide a free upgrade to Standard support for 3 months.",
    "O2": "We can offer 15% off the monthly fee for 3 months.",
    "O3": "We can provide a free onboarding session.",
    "O4": "An account manager can call within 5 business days.",
}


def test_valid_messages_cover_each_offer():
    payload = {"results": [
        {"id": i, "message": VALID_MESSAGES[code]}
        for i, code in enumerate(VALID_MESSAGES, start=1)
    ]}
    valid, errors = validate_response(json.dumps(payload), {1, 2, 3, 4},
                                      {1: "O1", 2: "O2", 3: "O3", 4: "O4"})
    assert set(valid) == {1, 2, 3, 4}
    assert not errors


@pytest.mark.parametrize("response", [
    "not-json",
    '{"results":[{"id":1,"message":""}]}',
    '{"results":[{"id":1,"message":"good"},{"id":1,"message":"good"}]}',
    '{"results":[{"id":2,"message":"good"}]}',
])
def test_malformed_missing_duplicate_and_empty_outputs_rejected(response):
    valid, errors = validate_response(response, {1, 2}, {1: "O1", 2: "O2"})
    assert not valid
    assert errors


def test_too_long_and_wrong_offer_terms_rejected():
    too_long = "word " * 81
    wrong_offer = "We can offer 15% off the monthly fee for 3 months."
    response = json.dumps({"results": [
        {"id": 1, "message": too_long},
        {"id": 2, "message": wrong_offer},
    ]})
    valid, errors = validate_response(response, {1, 2}, {1: "O1", 2: "O4"})
    assert not valid
    assert "80-word" in errors[1]
    assert "selected offer" in errors[2]


@pytest.mark.parametrize("workflow_text", [
    "Approval-pending draft: ",
    "Draft for approval: ",
    "Do not contact the customer. ",
    "Please review and approve. ",
    "Internal use only. ",
    "Awaiting human approval. ",
])
def test_internal_workflow_language_is_rejected(workflow_text):
    response = json.dumps({"results": [{
        "id": 1,
        "message": workflow_text + "We can provide a Free upgrade to Standard support for 3 months.",
    }]})
    valid, errors = validate_response(response, {1}, {1: "O1"})
    assert not valid
    assert "workflow" in errors[1]


def test_prompt_is_customer_facing_and_encourages_natural_context():
    prompt = SYSTEM_PROMPT.casefold()
    assert "approval-pending" not in prompt
    assert "do not contact the customer" not in prompt
    assert "only text intended to be read by that customer" in prompt
    assert "do not mechanically list customer attributes" in prompt
    assert "vary how the offer is introduced across customers with the same offer" in prompt
    assert "do not add a call to action" in prompt
    assert "for your cloud hosting service" in prompt


@pytest.mark.parametrize("intro", [
    "For your records: ",
    "Please note the available offer: ",
    "Your account offer is: ",
    "As a Technology customer using Cloud Hosting for 8 months on Basic support: ",
])
def test_formulaic_or_label_style_openings_are_rejected(intro):
    response = json.dumps({"results": [{
        "id": 1,
        "message": intro + "Free upgrade to Standard support for 3 months.",
    }]})
    valid, errors = validate_response(response, {1}, {1: "O1"})
    assert not valid
    assert "formulaic" in errors[1]


@pytest.mark.parametrize("extra", [
    " Reply to confirm a start date.",
    " Please share your availability.",
    " We will apply the discount to your next invoice.",
    " You qualify for this promotion.",
    " To help with seasonal demand.",
])
def test_unconfirmed_actions_processes_and_context_are_rejected(extra):
    response = json.dumps({"results": [{
        "id": 1,
        "message": "We can provide a Free upgrade to Standard support for 3 months." + extra,
    }]})
    valid, errors = validate_response(response, {1}, {1: "O1"})
    assert not valid
    assert "unconfirmed" in errors[1] or "assumes customer context" in errors[1]
