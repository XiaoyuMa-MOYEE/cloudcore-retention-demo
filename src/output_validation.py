"""Strict structured-output and message checks before local ID mapping."""

import json
import re

from .playbook import OFFER_LABELS


INTERNAL_WORKFLOW_PATTERNS = (
    re.compile(r"\bapprovals?\b", re.IGNORECASE),
    re.compile(r"\bapprover\b", re.IGNORECASE),
    re.compile(r"\bdrafts?\b", re.IGNORECASE),
    re.compile(r"\binternal\b", re.IGNORECASE),
    re.compile(r"\bdo not contact (?:the )?customer\b", re.IGNORECASE),
    re.compile(r"\bplease review\b", re.IGNORECASE),
    re.compile(r"\breview and approve\b", re.IGNORECASE),
    re.compile(r"\bawaiting (?:human )?approval\b", re.IGNORECASE),
    re.compile(r"\bpending (?:human )?approval\b", re.IGNORECASE),
    re.compile(r"\bfor (?:human )?approval\b", re.IGNORECASE),
)

UNSUPPORTED_PROCESS_PATTERNS = (
    re.compile(r"\b(?:please|kindly)\s+(?:reply|respond|contact|share|send|confirm|schedule|arrange|provide|tell)\b", re.IGNORECASE),
    re.compile(r"\b(?:reply|respond)\s+(?:to|with|and)\b", re.IGNORECASE),
    re.compile(r"\b(?:share|send)\s+(?:us|your|the|preferred|available|a|an)\b", re.IGNORECASE),
    re.compile(r"\bprovide\s+(?:us|your|the|preferred|available|contact|availability|attendee|a contact|a few)\b", re.IGNORECASE),
    re.compile(r"\b(?:i|we)(?:'ll| will| can| would)\s+(?:apply|activate|schedule|arrange|confirm|update|coordinate|extend|outline)\b", re.IGNORECASE),
    re.compile(r"\b(?:will be|is being)\s+(?:scheduled|arranged|activated|applied)\b", re.IGNORECASE),
    re.compile(r"\b(?:reply|respond|schedule|arrange|availability|next steps|contact us|contact number|preferred dates|preferred times|attendee details|tailored|customi[sz]ed)\b", re.IGNORECASE),
    re.compile(r"\b(?:billing|invoice|next billing cycle|upcoming invoices?)\b", re.IGNORECASE),
    re.compile(r"\b(?:qualify|eligible|eligibility)\b", re.IGNORECASE),
)

UNSUPPORTED_CONTEXT_PATTERNS = (
    re.compile(r"\b(?:seasonal demand|upcoming initiatives|next term|as you scale|your roadmap|your priorities)\b", re.IGNORECASE),
    re.compile(r"\b(?:ensure|improve|optimi[sz]e)\s+(?:your\s+)?(?:network\s+)?reliability\b", re.IGNORECASE),
    re.compile(r"\b(?:to speed|accelerate)\s+(?:your\s+)?adoption\b", re.IGNORECASE),
)

FORMULAIC_INTRO_PATTERNS = (
    re.compile(r"^\s*(?:for your records|please note (?:the )?available offer|your account offer is)\b", re.IGNORECASE),
    re.compile(r"\bas a .{0,70}\bcustomer using .{0,80}\b(?:for|on) .{0,40}\bsupport\b", re.IGNORECASE),
    re.compile(r"^\s*[^.!?]{1,70}:\s*(?:free upgrade|\d+% off|free onboarding|account manager call)\b", re.IGNORECASE),
)


def validate_response(output_text: str, expected_ids: set[int], id_to_offer_code: dict[int, str]) -> tuple[dict[int, str], dict[int, str]]:
    """Return valid messages and per-ID errors; malformed envelopes fail all IDs."""
    try:
        parsed = json.loads(output_text)
    except (json.JSONDecodeError, TypeError) as exc:
        return {}, {record_id: f"Malformed JSON response: {exc}" for record_id in expected_ids}
    if not isinstance(parsed, dict) or set(parsed) != {"results"} or not isinstance(parsed["results"], list):
        return {}, {record_id: "Response must be an object with exactly one results array." for record_id in expected_ids}

    messages: dict[int, str] = {}
    errors: dict[int, str] = {}
    seen: set[int] = set()
    unexpected_ids: set[int] = set()
    for row in parsed["results"]:
        if not isinstance(row, dict) or set(row) != {"id", "message"}:
            continue
        record_id, message = row["id"], row["message"]
        if not isinstance(record_id, int) or isinstance(record_id, bool):
            continue
        if record_id not in expected_ids:
            unexpected_ids.add(record_id)
            continue
        if record_id in seen:
            errors[record_id] = "Duplicate batch-local ID in response."
            messages.pop(record_id, None)
            continue
        seen.add(record_id)
        if not isinstance(message, str) or not message.strip():
            errors[record_id] = "Message is empty or not a string."
            continue
        if len(message.split()) > 80:
            errors[record_id] = "Message exceeds the 80-word limit."
            continue
        normalized = re.sub(r"\s+", " ", message.strip()).casefold()
        if any(pattern.search(normalized) for pattern in INTERNAL_WORKFLOW_PATTERNS):
            errors[record_id] = "Message contains internal approval or workflow language."
            continue
        if any(pattern.search(normalized) for pattern in UNSUPPORTED_PROCESS_PATTERNS):
            errors[record_id] = "Message adds an unconfirmed customer action or operational process."
            continue
        if any(pattern.search(normalized) for pattern in UNSUPPORTED_CONTEXT_PATTERNS):
            errors[record_id] = "Message assumes customer context that was not supplied."
            continue
        if any(pattern.search(message) for pattern in FORMULAIC_INTRO_PATTERNS):
            errors[record_id] = "Message uses a formulaic or label-style opening."
            continue
        if not _describes_offer(normalized, id_to_offer_code[record_id]):
            errors[record_id] = "Message does not accurately describe the selected offer terms."
            continue
        other_offers = [code for code in OFFER_LABELS
                        if code != id_to_offer_code[record_id] and _describes_offer(normalized, code)]
        if other_offers:
            errors[record_id] = "Message includes wording for a different Playbook offer."
            continue
        messages[record_id] = message.strip()

    for record_id in expected_ids:
        if record_id not in seen:
            errors[record_id] = "Missing batch-local ID in response."
    if unexpected_ids:
        errors = {record_id: f"Response included unexpected batch-local IDs: {sorted(unexpected_ids)}."
                  for record_id in expected_ids}
        messages = {}
    return messages, errors


def _describes_offer(message: str, code: str) -> bool:
    has_three_months = bool(re.search(r"\b(?:3|three)[ -]months?\b", message))
    has_five_business_days = bool(re.search(r"\b(?:5|five)[ -]business days?\b", message))
    is_free = bool(re.search(r"\b(?:free|complimentary)\b", message))
    if code == "O1":
        return all(("standard" in message, "support" in message,
                    bool(re.search(r"\bupgrade\w*\b", message)), is_free, has_three_months))
    if code == "O2":
        has_discount = bool(re.search(r"\b15\s*%|\bfifteen percent\b", message))
        has_reduction = bool(re.search(r"\b(?:off|discount|reduc\w*)\b", message))
        return all((has_discount, has_reduction, "monthly fee" in message, has_three_months))
    if code == "O3":
        return is_free and "onboarding" in message and "session" in message
    if code == "O4":
        return ("account manager" in message and "call" in message and has_five_business_days)
    return False
