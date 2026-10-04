import re
from pathlib import Path

from .candidate_service import best_near_label, detect_candidates
from .layout_service import Candidate, build_lines, extract_near_label, normalize_text
from .schemas import DocumentAnalysis, FieldStatus

ELECTRICITY_TERMS = (
    "electricity", "electric power", "power company", "electric supply",
    "consumer number", "consumer no", "meter number", "meter no",
    "kwh", "units consumed", "gepco", "gujranwala", "msedcl", "msedc",
)

KNOWN_PROVIDERS = (
    ("Gujranwala Electric Power Company", ("gujranwala electric power company", "gepco")),
    ("MSEDCL", ("msedcl", "msedc", "maharashtra state electricity")),
    ("Adani Electricity", ("adani electricity",)),
    ("Tata Power", ("tata power",)),
    ("Torrent Power", ("torrent power",)),
    ("Reliance", ("reliance energy", "reliance electricity")),
)

TARGET_FIELDS = (
    "provider", "customer_name", "consumer_number", "reference_number", "meter_number",
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
    source = f"{filename} {text}".lower()
    hits = sum(term in source for term in ELECTRICITY_TERMS)
    if hits >= 2:
        return "electricity_bill", min(0.98, 0.84 + hits * 0.025)
    if hits == 1:
        return "electricity_bill", 0.78
    if any(x in source for x in ("tax invoice", "gst invoice", "invoice")):
        return "invoice", 0.90
    if any(x in source for x in ("receipt", "payment received")):
        return "receipt", 0.88
    if any(x in source for x in ("insurance", "policy number", "premium")):
        return "insurance_document", 0.88
    if any(x in source for x in ("bank statement", "account statement")):
        return "bank_statement", 0.88
    if "notice" in source:
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
        if any(x in low_line for x in ("power company", "electricity", "electric supply")) and len(clean.split()) >= 3:
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
    for pattern in patterns:
        match = re.search(pattern, value, re.I)
        if match:
            return _clean(match.group(1))
    return None

def _parse_month(value):
    match = re.search(
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\d{1,2}[/-]\d{4})\b",
        value,
        re.I,
    )
    return _clean(match.group(1)) if match else None

def _parse_number(value):
    for token in re.findall(r"\b\d[\d,]*(?:\.\d{1,3})?\b", value):
        try:
            number = float(token.replace(",", ""))
        except ValueError:
            continue
        if 0 <= number < 1_000_000_000:
            return number
    return None

def _parse_amount(value):
    value = re.sub(r"\b(?:PKR|INR|Rs\.?|Rupees?)\b|₹", " ", value, flags=re.I)
    value = re.sub(r"\b(\d{2,7})\s+(\d{2})\b", r"\1.\2", value)
    return _parse_number(value)

def _parse_text(value):
    value = _clean(value)
    if not value or len(value) < 2 or len(value) > 80:
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
    valid = [item for item in items if item is not None]
    return max(valid, key=lambda item: item.confidence) if valid else None

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

def _candidate_to_field(best, value_parser=None):
    if not best:
        return None
    score, detected, matched_label = best
    value = detected.value
    if value_parser:
        value = value_parser(str(value))
        if value is None:
            return None
    return Candidate(
        value=value,
        confidence=min(0.90, score),
        source="fuzzy_candidate",
        evidence=f"{matched_label} | {detected.evidence}"[:220],
    )

def analyze(filename, content_type, data, *, text_override, words, ocr_quality):
    text = text_override or ""
    lines = build_lines(words)
    document_type, type_confidence = _classify(filename, text)
    detected = detect_candidates(text)

    provider = _provider(text)

    customer_name = None
    if len(detected["names"]) == 1 and detected["names"][0].confidence >= 0.72:
        item = detected["names"][0]
        customer_name = Candidate(item.value, item.confidence, "name_candidate_unique", item.evidence)

    consumer = _field(
        lines, text,
        ("consumer number", "consumer no", "consumer id", "consumer", "account number", "account no"),
        _parse_identifier,
        (r"(?:consumer\s*(?:number|no|id)?|account\s*(?:number|no)?)\s*[:#=-]?\s*([A-Z0-9][A-Z0-9\-/]{3,29})",),
    )
    if consumer is None:
        consumer = _candidate_to_field(best_near_label(
            text, detected["identifiers"],
            ("consumer number", "consumer no", "consumer id", "account number"),
        ))

    reference = _field(
        lines, text,
        ("reference number", "reference no", "ref no", "reference"),
        _parse_identifier,
        (r"(?:reference\s*(?:number|no)?|ref\s*no)\s*[:#=-]?\s*([A-Z0-9][A-Z0-9\-/]{3,29})",),
    )
    if reference is None:
        reference = _candidate_to_field(best_near_label(
            text, detected["identifiers"], ("reference number", "reference no", "ref no"),
        ))

    meter = _field(
        lines, text,
        ("meter number", "meter no", "meter id"),
        _parse_identifier,
        (r"(?:meter\s*(?:number|no|id))\s*[:#=-]?\s*([A-Z0-9][A-Z0-9\-/]{3,29})",),
    )
    if meter is None:
        meter = _candidate_to_field(best_near_label(
            text, detected["identifiers"], ("meter number", "meter no", "meter id"),
        ))

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
    if document_date is None:
        document_date = _candidate_to_field(best_near_label(
            text, detected["dates"], ("bill date", "invoice date", "issue date", "date of issue"),
        ))

    due_date = _field(
        lines, text, ("due date", "pay by", "last date", "payment due"), _parse_date,
        (r"(?:due\s*date|pay\s*by|last\s*date|payment\s*due)\s*[:#=-]?\s*([A-Za-z0-9, ./-]{6,30})",),
    )
    if due_date is None:
        due_date = _candidate_to_field(best_near_label(
            text, detected["dates"], ("due date", "pay by", "last date", "payment due"),
        ))

    units = _field(
        lines, text, ("units consumed", "consumption", "units", "kwh"), _parse_number,
        (r"(?:units\s*consumed|consumption|units|kwh)\s*[:#=-]?\s*([0-9][0-9,.]*)",),
    )
    previous_reading = _field(
        lines, text, ("previous reading", "prev reading", "old reading"), _parse_number,
        (r"(?:previous|prev|old)\s*reading\s*[:#=-]?\s*([0-9][0-9,.]*)",),
    )
    current_reading = _field(
        lines, text, ("current reading", "present reading", "new reading"), _parse_number,
        (r"(?:current|present|new)\s*reading\s*[:#=-]?\s*([0-9][0-9,.]*)",),
    )

    amount_pattern_tail = r"([0-9][0-9,. ]*)"
    current_charges = _field(
        lines, text, ("current charges", "current bill", "energy charges"), _parse_amount,
        (rf"(?:current\s*charges|current\s*bill|energy\s*charges)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*{amount_pattern_tail}",),
    )
    taxes = _field(
        lines, text, ("taxes", "tax", "gst", "surcharge", "fuel surcharge"), _parse_amount,
        (rf"(?:taxes|tax|gst|surcharge|fuel\s*surcharge)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*{amount_pattern_tail}",),
    )
    arrears = _field(
        lines, text, ("arrears", "previous balance", "outstanding", "balance brought forward"), _parse_amount,
        (rf"(?:arrears|previous\s*balance|outstanding|balance\s*brought\s*forward)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*{amount_pattern_tail}",),
    )
    amount_before = _field(
        lines, text,
        ("amount before due date", "payable within due date", "amount due", "bill amount", "total amount", "net amount"),
        _parse_amount,
        (rf"(?:amount\s*before\s*due\s*date|payable\s*within\s*due\s*date|amount\s*due|bill\s*amount|total\s*amount|net\s*amount)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*{amount_pattern_tail}",),
    )
    if amount_before is None:
        amount_before = _candidate_to_field(best_near_label(
            text, detected["amounts"],
            ("amount before due date", "payable within due date", "amount due", "bill amount", "total amount"),
        ), lambda value: float(value))

    amount_after = _field(
        lines, text, ("amount after due date", "payable after due date", "late payment amount"), _parse_amount,
        (rf"(?:amount\s*after\s*due\s*date|payable\s*after\s*due\s*date|late\s*payment\s*amount)\s*[:#=-]?\s*(?:PKR|INR|Rs\.?|₹)?\s*{amount_pattern_tail}",),
    )
    if amount_after is None:
        amount_after = _candidate_to_field(best_near_label(
            text, detected["amounts"], ("amount after due date", "payable after due date", "late payment amount"),
        ), lambda value: float(value))

    currency = None
    if re.search(r"\bINR\b|₹", text, re.I):
        currency = Candidate("INR", 0.96, "currency_detection", "INR/₹")
    elif re.search(r"\bPKR\b", text, re.I):
        currency = Candidate("PKR", 0.96, "currency_detection", "PKR")
    elif re.search(r"\bRs\.?", text, re.I):
        if provider and provider.value == "Gujranwala Electric Power Company":
            currency = Candidate("PKR", 0.88, "provider_currency_mapping", "Rs + GEPCO")
        elif provider and provider.value in {"MSEDCL", "Adani Electricity", "Tata Power", "Torrent Power", "Reliance"}:
            currency = Candidate("INR", 0.88, "provider_currency_mapping", f"Rs + {provider.value}")
        else:
            currency = Candidate("RS", 0.70, "currency_detection", "Rs")

    mapped = {
        "provider": provider,
        "customer_name": customer_name,
        "consumer_number": consumer,
        "reference_number": reference,
        "meter_number": meter,
        "tariff": tariff,
        "bill_month": bill_month,
        "billing_period": billing_period,
        "document_date": document_date,
        "due_date": due_date,
        "units_consumed": units,
        "previous_reading": previous_reading,
        "current_reading": current_reading,
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
        "document_type": FieldStatus(status="extracted", confidence=type_confidence, source="classifier", evidence=document_type),
    }

    for key, candidate in mapped.items():
        field_status[key] = _status(candidate)
        if candidate is not None:
            extracted_fields[key] = candidate.value

    extracted_count = sum(1 for key in TARGET_FIELDS if field_status[key].status == "extracted")
    completeness = extracted_count / len(TARGET_FIELDS)
    candidate_count = sum(len(items) for items in detected.values())

    if text.strip():
        summary = (
            f"{document_type.replace('_', ' ').title()} detected. "
            f"{extracted_count} of {len(TARGET_FIELDS)} target fields were confidently mapped. "
            f"{candidate_count} OCR candidate value(s) were detected and are shown separately."
        )
    else:
        summary = "No reliable text could be extracted from the document."

    actions = [
        "Review mapped fields against the original document.",
        "Review Detected OCR Candidates for useful values that could not be safely mapped.",
    ]
    if due_date:
        actions.append(f"Take required action before {due_date.value}.")
    if amount_before:
        actions.append("Verify the payable amount before payment.")
    actions.append("Use Ask Your Document for mapped fields or candidate lists.")

    return DocumentAnalysis(
        document_type=document_type,
        filename=filename,
        provider=provider.value if provider else None,
        document_date=document_date.value if document_date else None,
        due_date=due_date.value if due_date else None,
        amount=amount_before.value if amount_before else None,
        currency=currency.value if currency else None,
        summary=summary,
        actions=actions,
        confidence=type_confidence,
        ocr_quality=ocr_quality,
        extraction_completeness=completeness,
        extracted_fields=extracted_fields,
        field_status=field_status,
        detected_candidates=detected,
        candidate_count=candidate_count,
    )
