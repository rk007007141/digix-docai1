import re
from typing import Any

from .schemas import DetectedCandidate, FieldStatus

FIELD_ALIASES = {
    "provider": ("provider", "company", "issuer", "electricity company", "power company"),
    "customer_name": ("customer name", "consumer name", "owner name", "name"),
    "consumer_number": ("consumer number", "consumer id", "consumer", "account number"),
    "reference_number": ("reference number", "ref number", "reference"),
    "meter_number": ("meter number", "meter id", "meter"),
    "tariff": ("tariff", "category"),
    "bill_month": ("bill month", "billing month"),
    "billing_period": ("billing period", "bill period"),
    "document_date": ("bill date", "invoice date", "issue date", "document date"),
    "due_date": ("due date", "deadline", "last date", "pay by", "due"),
    "units_consumed": ("units consumed", "consumption", "kwh", "units"),
    "previous_reading": ("previous reading", "prev reading", "old reading"),
    "current_reading": ("current reading", "present reading", "new reading"),
    "current_charges": ("current charges", "energy charges", "current bill"),
    "taxes_surcharges": ("taxes", "tax", "gst", "surcharge"),
    "arrears": ("arrears", "outstanding", "previous balance"),
    "amount_before_due": ("amount before due", "bill amount", "amount due", "total", "payable", "amount"),
    "amount_after_due": ("amount after due", "after due", "late payment"),
    "currency": ("currency",),
}

STOP = {
    "what", "when", "where", "which", "who", "why", "how", "is", "are",
    "the", "a", "an", "of", "to", "for", "in", "on", "my", "this",
    "document", "bill", "please", "tell", "me",
}

def _mapped_field(question):
    q = question.lower()
    matches = []
    for key, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in q:
                matches.append((len(alias), key))
    return max(matches)[1] if matches else None

def _name(key):
    return key.replace("_", " ").title()

def _candidate_answer(title: str, items: list[DetectedCandidate]):
    if not items:
        return f"No reliable {title.lower()} candidates were detected.", 0.0, False, []

    values = []
    evidence = []
    for item in items[:12]:
        prefix = f"{item.currency} " if item.currency else ""
        values.append(f"{prefix}{item.value}")
        evidence.append(item.evidence)

    return (
        f"{title}: " + "; ".join(values),
        max(item.confidence for item in items[:12]),
        True,
        evidence[:6],
    )

def answer_question(
    question: str,
    text: str,
    fields: dict[str, Any],
    field_status: dict[str, FieldStatus],
    detected_candidates: dict[str, list[DetectedCandidate]] | None = None,
):
    q = question.strip()
    q_lower = q.lower()
    detected_candidates = detected_candidates or {}

    if "all date" in q_lower or "detected date" in q_lower or "dates found" in q_lower:
        return _candidate_answer("Detected dates", detected_candidates.get("dates", []))
    if "all amount" in q_lower or "detected amount" in q_lower or "amounts found" in q_lower or "all payment" in q_lower:
        return _candidate_answer("Detected amounts", detected_candidates.get("amounts", []))
    if "all id" in q_lower or "detected id" in q_lower or "identifiers" in q_lower:
        return _candidate_answer("Detected identifiers", detected_candidates.get("identifiers", []))
    if "detected name" in q_lower or "names found" in q_lower:
        return _candidate_answer("Detected names", detected_candidates.get("names", []))
    if "measurement" in q_lower or "all unit" in q_lower:
        return _candidate_answer("Detected measurements", detected_candidates.get("measurements", []))

    if len(q) < 2:
        return "Please enter a more specific question.", 0.0, False, []

    key = _mapped_field(q)
    if key:
        value = fields.get(key)
        status = field_status.get(key)

        if value not in (None, "") and status and status.status == "extracted":
            if key.startswith("amount_") or key in ("current_charges", "taxes_surcharges", "arrears"):
                currency = fields.get("currency")
                if currency:
                    value = f"{currency} {value}"
            evidence = [status.evidence] if status.evidence else []
            return f"{_name(key)}: {value}", status.confidence, True, evidence

        if key == "customer_name" and detected_candidates.get("names"):
            return _candidate_answer("Detected name candidates", detected_candidates["names"])

        return (
            f"I could not reliably map the {_name(key).lower()} from this document. "
            "Check Detected OCR Candidates for unmapped values.",
            0.0,
            False,
            [],
        )

    terms = [
        word for word in re.findall(r"[a-z0-9]+", q_lower)
        if len(word) > 2 and word not in STOP
    ]
    if len(terms) < 2:
        return "Please ask a more specific question about the document.", 0.0, False, []

    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if len(line.strip()) >= 4]
    scored = []
    for line in lines:
        low = line.lower()
        matched = sum(term in low for term in terms)
        coverage = matched / len(terms)
        if matched:
            scored.append((coverage, matched, len(line), line))

    if not scored:
        return "I could not find reliable evidence for that question in the document.", 0.0, False, []

    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    if scored[0][0] < 0.60:
        return "I could not find reliable evidence for that question in the document.", 0.0, False, []

    evidence = [scored[0][3]]
    for coverage, _, _, line in scored[1:]:
        if coverage >= 0.60 and line not in evidence:
            evidence.append(line)
        if len(evidence) == 2:
            break

    confidence = min(0.88, 0.58 + 0.25 * scored[0][0])
    return " ".join(evidence), confidence, True, evidence
