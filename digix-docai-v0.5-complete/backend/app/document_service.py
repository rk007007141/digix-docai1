import re
from pathlib import Path
from typing import Any

from .layout_service import Candidate, build_lines, extract_near_label, normalize_text
from .schemas import DocumentAnalysis, FieldStatus

ELECTRICITY_TERMS = (
    "electricity", "electric power", "power company", "electric supply",
    "consumer number", "consumer no", "meter number", "meter no",
    "kwh", "units consumed", "gepco", "gujranwala",
)

KNOWN_PROVIDERS = (
    ("Gujranwala Electric Power Company", ("gujranwala electric power company", "gepco")),
    ("MSEDCL", ("msedcl", "maharashtra state electricity")),
    ("Adani Electricity", ("adani electricity",)),
    ("Tata Power", ("tata power",)),
    ("Torrent Power", ("torrent power",)),
    ("Reliance", ("reliance energy", "reliance electricity")),
)

TARGET_FIELDS = (
    "provider", "consumer_number", "reference_number", "meter_number",
    "tariff", "bill_month", "billing_period", "document_date", "due_date",
    "units_consumed", "previous_reading", "current_reading", "current_charges",
    "taxes_surcharges", "arrears", "amount_before_due", "amount_after_due", "currency",
)

BAD_ID_WORDS = {
    "bill", "consumer", "number", "meter", "reference", "account",
    "date", "amount", "reading", "units", "month", "due", "payable",
    "current", "previous", "total", "case",
}

def _clean(value):
    if not value:
        return None
    value = normalize_text(value).strip(" :|-")
    return value or None

def _classify(filename, text):
    s = f"{filename} {text}".lower()
    hits = sum(term in s for term in ELECTRICITY_TERMS)
    if hits >= 2:
        return "electricity_bill", min(0.98, 0.84 + hits * 0.025)
    if hits == 1:
        return "electricity_bill", 0.78
    if any(x in s for x in ("tax invoice", "gst invoice", "invoice")):
        return "invoice", 0.90
    if any(x in s for x in ("receipt", "payment received")):
        return "receipt", 0.88
    if any(x in s for x in ("insurance", "policy number", "premium")):
        return "insurance_document", 0.88
    if any(x in s for x in ("bank statement", "account statement")):
        return "bank_statement", 0.88
    if "notice" in s:
        return "notice", 0.78
    return "generic_document", 0.62

def _provider(text):
    low = text.lower()
    for canonical, aliases in KNOWN_PROVIDERS:
        for alias in aliases:
            if alias in low:
                return Candidate(canonical, 0.97, "provider_dictionary", alias)
    for line in text.splitlines():
        clean = _clean(line)
        if not clean or len(clean) > 100:
            continue
        low_line = clean.lower()
        if (
            "power company" in low_line or "electricity" in low_line or "electric supply" in low_line
        ) and len(clean.split()) >= 3:
            return Candidate(clean, 0.75, "provider_line", clean)
    return None

def _parse_identifier(value):
    if not value:
        return None
    tokens = re.findall(r"[A-Z0-9][A-Z0-9\-/]{3,29}", value.upper())
    for token in tokens:
        low = token.lower()
        digits = sum(c.isdigit() for c in token)
        alnum = sum(c.isalnum() for c in token)
        if digits < 4 or not alnum or digits / alnum < 0.50:
            continue
        if any(word in low for word in BAD_ID_WORDS):
            continue
        if re.fullmatch(r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", token):
            continue
        return token
    return None

def _parse_date(value):
    patterns = (
        r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b",
        r"\b(\d{4}-\d{1,2}-\d{1,2})\b",
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
    )
    for p in patterns:
        m = re.search(p, value, re.I)
        if m:
            return _clean(m.group(1))
    return None

def _parse_month(value):
    m = re.search(
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\d{1,2}[/-]\d{4})\b",
        value,
        re.I,
    )
    return _clean(m.group(1)) if m else None

def _parse_number(value):
    for token in re.findall(r"\b\d[\d,]*(?:\.\d{1,3})?\b", value):
        try:
            n = float(token.replace(",", ""))
        except ValueError:
            continue
        if 0 <= n < 1_000_000_000:
            return n
    return None

def _parse_amount(value):
    value = re.sub(r"\b(?:PKR|INR|Rs\.?|Rupees?)\b|₹", " ", value, flags=re.I)
    return _parse_number(value)

def _parse_text(value):
    value = _clean(value)
    if not value or len(value) < 2 or len(value) > 50:
        return None
    return value

def _regex_candidate(text, patterns, parser, confidence=0.68):
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I | re.M):
            value = parser(match.group(1))
            if value is not None:
                return Candidate(value, confidence, "text_fallback", normalize_text(match.group(0))[:180])
    return None

def _best(*items):
    valid = [x for x in items if x is not None]
    return max(valid, key=lambda x: x.confidence) if valid else None

def _field(lines, text, aliases, parser, patterns=()):
    layout = extract_near_label(lines, aliases, parser) if lines else None
    fallback = _regex_candidate(text, patterns, parser) if patterns else None
    return _best(layout, fallback)

def _status(candidate):
    if candidate is None:
        return FieldStatus(status="not_reliably_read", confidence=0.0, source="none", evidence=None)
    return FieldStatus(
        status="extracted",
        confidence=max(0.0, min(1.0, candidate.confidence)),
        source=candidate.source,
        evidence=candidate.evidence[:220] if candidate.evidence else None,
    )

def analyze(filename, content_type, data, *, text_override, words, ocr_quality):
    text = text_override or ""
    lines = build_lines(words)
    document_type, type_conf = _classify(filename, text)

    provider = _provider(text)

    consumer = _field(
        lines, text,
        ("consumer number", "consumer no", "consumer id", "consumer", "account number", "account no"),
        _parse_identifier,
        (r"(?:consumer\s*(?:number|no|id)?|account\s*(?:number|no)?)\s*[:#=-]?\s*([A-Z0-9][A-Z0-9\-/]{3,29})",),
    )
    reference = _field(
        lines, text,
        ("reference number", "reference no", "ref no", "reference"),
        _parse_identifier,
        (r"(?:reference\s*(?:number|no)?|ref\s*no)\s*[:#=-]?\s*([A-Z0-9][A-Z0-9\-/]{3,29})",),
    )
    meter = _field(
        lines, text,
        ("meter number", "meter no", "meter id"),
        _parse_identifier,
        (r"(?:meter\s*(?:number|no|id))\s*[:#=-]?\s*([A-Z0-9][A-Z0-9\-/]{3,29})",),
    )
    tariff = _field(
        lines, text, ("tariff", "tariff category", "category"), _parse_text,
        (r"(?:tariff(?:\s*category)?|category)\s*[:#=-]?\s*([A-Z0-9][A-Z0-9 ./_-]{1,30})",),
    )
    bill_month = _field(
        lines, text, ("bill month", "billing month", "month"), _parse_month,
        (r"(?:bill(?:ing)?\s*month|month)\s*[:#=-]?\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\d{1,2}[/-]\d{4})",),
    )
    billing_period = _field(
        lines, text, ("billing period", "bill period", "period"), _parse_text,
        (r"(?:billing\s*period|bill\s*period)\s*[:#=-]?\s*([A-Za-z0-9 ./-]{4,40})",),
    )
    document_date = _field(
        lines, text, ("bill date", "invoice date", "issue date", "date of issue"), _parse_date,
        (r"(?:bill\s*date|invoice\s*date|issue\s*date|date\s*of\s*issue)\s*[:#=-]?\s*([A-Za-z0-9, ./-]{6,30})",),
    )
    due_date = _field(
        lines, text, ("due date", "pay by", "last date", "payment due"), _parse_date,
        (r"(?:due\s*date|pay\s*by|last\s*date|payment\s*due)\s*[:#=-]?\s*([A-Za-z0-9, ./-]{6,30})",),
    )
    units = _field(
        lines, text, ("units consumed", "consumption", "units", "kwh"), _parse_number,
        (r"(?:units\s*consumed|consumption|units|kwh)\s*[:#=-]?\s*([0-9][0-9,.]*)",),
    )
    prev = _field(
        lines, text, ("previous reading", "prev reading", "old reading"), _parse_number,
        (r"(?:previous|prev|old)\s*reading\s*[:#=-]?\s*([0-9][0-9,.]*)",),
    )
    current = _field(
        lines, text, ("current reading", "present reading", "new reading"), _parse_number,
        (r"(?:current|present|new)\s*reading\s*[:#=-]?\s*([0-9][0-9,.]*)",),
    )
    current_charges = _field(
        lines, text, ("current charges", "current bill", "energy charges"), _parse_amount,
        (r"(?:current\s*charges|current\s*bill|energy\s*charges)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*([0-9][0-9,.]*)",),
    )
    taxes = _field(
        lines, text, ("taxes", "tax", "gst", "surcharge", "fuel surcharge"), _parse_amount,
        (r"(?:taxes|tax|gst|surcharge|fuel\s*surcharge)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*([0-9][0-9,.]*)",),
    )
    arrears = _field(
        lines, text, ("arrears", "previous balance", "outstanding", "balance brought forward"), _parse_amount,
        (r"(?:arrears|previous\s*balance|outstanding|balance\s*brought\s*forward)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*([0-9][0-9,.]*)",),
    )
    amount_before = _field(
        lines, text,
        ("amount before due date", "payable within due date", "amount due", "bill amount", "total amount", "net amount"),
        _parse_amount,
        (r"(?:amount\s*before\s*due\s*date|payable\s*within\s*due\s*date|amount\s*due|bill\s*amount|total\s*amount|net\s*amount)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*([0-9][0-9,.]*)",),
    )
    amount_after = _field(
        lines, text, ("amount after due date", "payable after due date", "late payment amount"), _parse_amount,
        (r"(?:amount\s*after\s*due\s*date|payable\s*after\s*due\s*date|late\s*payment\s*amount)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*([0-9][0-9,.]*)",),
    )

    currency = None
    if re.search(r"\bINR\b|₹", text, re.I):
        currency = Candidate("INR", 0.96, "currency_detection", "INR/₹")
    elif re.search(r"\bPKR\b|\bRs\.?", text, re.I):
        currency = Candidate("PKR", 0.92, "currency_detection", "PKR/Rs")
    elif provider and provider.value == "Gujranwala Electric Power Company":
        currency = Candidate("PKR", 0.82, "provider_currency_mapping", provider.value)

    candidates = {
        "provider": provider,
        "consumer_number": consumer,
        "reference_number": reference,
        "meter_number": meter,
        "tariff": tariff,
        "bill_month": bill_month,
        "billing_period": billing_period,
        "document_date": document_date,
        "due_date": due_date,
        "units_consumed": units,
        "previous_reading": prev,
        "current_reading": current,
        "current_charges": current_charges,
        "taxes_surcharges": taxes,
        "arrears": arrears,
        "amount_before_due": amount_before,
        "amount_after_due": amount_after,
        "currency": currency,
    }

    extracted_fields = {"filename": filename, "document_type": document_type}
    field_status = {
        "filename": FieldStatus(status="extracted", confidence=1.0, source="upload", evidence=Path(filename).name),
        "document_type": FieldStatus(status="extracted", confidence=type_conf, source="classifier", evidence=document_type),
    }

    for key, candidate in candidates.items():
        field_status[key] = _status(candidate)
        if candidate is not None:
            extracted_fields[key] = candidate.value

    extracted_count = sum(1 for key in TARGET_FIELDS if field_status[key].status == "extracted")
    completeness = extracted_count / len(TARGET_FIELDS)

    provider_value = provider.value if provider else None
    document_date_value = document_date.value if document_date else None
    due_date_value = due_date.value if due_date else None
    amount_value = amount_before.value if amount_before else None
    currency_value = currency.value if currency else None

    if text.strip():
        summary = (
            f"{document_type.replace('_', ' ').title()} detected. "
            f"{extracted_count} of {len(TARGET_FIELDS)} target fields were reliably extracted. "
            "Unreadable fields are marked instead of guessed."
        )
    else:
        summary = "No reliable text could be extracted from the document."

    actions = ["Review extracted values against the original document."]
    if due_date_value:
        actions.append(f"Take required action before {due_date_value}.")
    if amount_value is not None:
        actions.append("Verify the payable amount before payment.")
    actions.append("Use Ask Your Document for questions grounded in extracted fields.")

    return DocumentAnalysis(
        document_type=document_type,
        filename=filename,
        provider=provider_value,
        document_date=document_date_value,
        due_date=due_date_value,
        amount=amount_value,
        currency=currency_value,
        summary=summary,
        actions=actions,
        confidence=type_conf,
        ocr_quality=ocr_quality,
        extraction_completeness=completeness,
        extracted_fields=extracted_fields,
        field_status=field_status,
    )
