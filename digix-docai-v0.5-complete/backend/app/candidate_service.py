import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Iterable

from .schemas import DetectedCandidate

AMOUNT_CONTEXT = (
    "amount", "payable", "payment", "bill", "total", "charges", "arrears",
    "balance", "due", "rs", "pkr", "inr",
)

NAME_STOP = (
    "POWER COMPANY", "ELECTRICITY", "BILL", "PAYMENT", "CHEQUE", "DATE",
    "PHONEPE", "UPI", "TARIFF", "METER", "CONSUMER", "REFERENCE", "TOTAL",
)

def _lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]

def _dedupe(items: list[DetectedCandidate]) -> list[DetectedCandidate]:
    seen = set()
    out = []
    for item in items:
        key = (item.normalized.lower(), item.line_no)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out

def _valid_date(raw: str):
    raw = raw.strip().replace(".", "-").replace("/", "-")
    raw = re.sub(r"\s+", "-", raw)
    match = re.fullmatch(r"(\d{1,3})-(\d{1,2})-(\d{2,4})", raw)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    if year < 100:
        year += 2000 if year < 70 else 1900
    if not 1900 <= year <= 2100:
        return None
    try:
        parsed = datetime(year, month, day)
    except ValueError:
        return None
    return parsed.strftime("%Y-%m-%d")

def detect_dates(text: str) -> list[DetectedCandidate]:
    found = []
    pattern = re.compile(r"(?<!\d)(\d{1,3}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{2,4})(?!\d)")
    for line_no, line in enumerate(_lines(text), start=1):
        for match in pattern.finditer(line):
            raw = re.sub(r"\s+", "", match.group(1))
            normalized = _valid_date(raw)
            if normalized:
                found.append(DetectedCandidate(
                    value=raw, normalized=normalized, confidence=0.88,
                    source="date_detector", evidence=line[:220], line_no=line_no,
                ))
    return _dedupe(found)

def _money_value(integer: str, decimals: str | None):
    cleaned = integer.replace(",", "")
    normalized = f"{cleaned}.{decimals}" if decimals is not None else cleaned
    try:
        return float(normalized)
    except ValueError:
        return None

def detect_amounts(text: str) -> list[DetectedCandidate]:
    found = []
    prefixed = re.compile(
        r"(?P<currency>Rs\.?|PKR|INR|₹)\s*(?P<int>\d{1,3}(?:,\d{3})+|\d{2,7})(?:[.\s](?P<dec>\d{2}))?",
        re.I,
    )
    contextual = re.compile(r"(?<!\d)(?P<int>\d{2,7})(?:[.\s](?P<dec>\d{2}))?(?!\d)")

    for line_no, line in enumerate(_lines(text), start=1):
        for match in prefixed.finditer(line):
            currency_raw = match.group("currency")
            currency = "INR" if currency_raw == "₹" or currency_raw.upper() == "INR" else (
                "PKR" if currency_raw.upper() == "PKR" else "RS"
            )
            value = _money_value(match.group("int"), match.group("dec"))
            if value is not None:
                found.append(DetectedCandidate(
                    value=value, normalized=f"{value:.2f}", confidence=0.91,
                    source="currency_amount_detector", evidence=line[:220],
                    line_no=line_no, currency=currency,
                ))

        lower = line.lower()
        if any(term in lower for term in AMOUNT_CONTEXT):
            for match in contextual.finditer(line):
                value = _money_value(match.group("int"), match.group("dec"))
                if value is None:
                    continue
                if match.group("dec") is None and 1900 <= value <= 2100:
                    continue
                found.append(DetectedCandidate(
                    value=value, normalized=f"{value:.2f}", confidence=0.67,
                    source="context_amount_detector", evidence=line[:220], line_no=line_no,
                ))

    found.sort(key=lambda item: (-item.confidence, item.line_no or 0))
    return _dedupe(found)

def detect_identifiers(text: str) -> list[DetectedCandidate]:
    found = []
    for line_no, line in enumerate(_lines(text), start=1):
        for match in re.finditer(r"(?<!\d)(\d{8,20})(?!\d)", line):
            raw = match.group(1)
            if len(raw) == 8 and raw.startswith(("19", "20")):
                continue
            found.append(DetectedCandidate(
                value=raw, normalized=raw,
                confidence=0.79 if len(raw) >= 10 else 0.70,
                source="identifier_detector", evidence=line[:220], line_no=line_no,
            ))
    return _dedupe(found)

def detect_names(text: str) -> list[DetectedCandidate]:
    found = []
    for line_no, line in enumerate(_lines(text), start=1):
        if not 8 <= len(line) <= 100:
            continue
        if any(stop in line.upper() for stop in NAME_STOP):
            continue
        letters = sum(ch.isalpha() for ch in line)
        digits = sum(ch.isdigit() for ch in line)
        if letters < 8 or digits > 2:
            continue
        words = re.findall(r"[A-Za-z]{2,}", line)
        if len(words) < 3:
            continue
        uppercase_words = sum(word.isupper() for word in words)
        ratio = uppercase_words / max(len(words), 1)
        if ratio < 0.60:
            continue
        found.append(DetectedCandidate(
            value=line, normalized=re.sub(r"\s+", " ", line).strip(),
            confidence=min(0.82, 0.62 + ratio * 0.20),
            source="name_candidate_detector", evidence=line[:220], line_no=line_no,
        ))
    return _dedupe(found)[:10]

def detect_measurements(text: str) -> list[DetectedCandidate]:
    found = []
    pattern = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*(kwh|kw|kva|kv|units?)\b", re.I)
    for line_no, line in enumerate(_lines(text), start=1):
        for match in pattern.finditer(line):
            value = f"{match.group(1)} {match.group(2).upper()}"
            found.append(DetectedCandidate(
                value=value, normalized=value, confidence=0.80,
                source="measurement_detector", evidence=line[:220], line_no=line_no,
            ))
    return _dedupe(found)

def detect_candidates(text: str) -> dict[str, list[DetectedCandidate]]:
    return {
        "dates": detect_dates(text),
        "amounts": detect_amounts(text),
        "identifiers": detect_identifiers(text),
        "names": detect_names(text),
        "measurements": detect_measurements(text),
    }

def _normalize_label(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()

def _label_similarity(line: str, aliases: Iterable[str]) -> float:
    line_n = _normalize_label(line)
    if not line_n:
        return 0.0
    best = 0.0
    for alias in aliases:
        alias_n = _normalize_label(alias)
        if alias_n in line_n:
            return 1.0
        words = line_n.split()
        width = max(1, len(alias_n.split()))
        windows = [" ".join(words[i:i + width + 1]) for i in range(max(1, len(words) - width + 1))]
        windows.append(line_n)
        for window in windows:
            best = max(best, SequenceMatcher(None, alias_n, window).ratio())
    return best

def best_near_label(
    text: str,
    candidates: list[DetectedCandidate],
    aliases: tuple[str, ...],
    *,
    minimum_score: float = 0.78,
    max_line_distance: int = 2,
):
    if not candidates:
        return None
    lines = _lines(text)
    best = None
    for candidate in candidates:
        if not candidate.line_no:
            continue
        start = max(1, candidate.line_no - max_line_distance)
        end = min(len(lines), candidate.line_no + max_line_distance)
        for line_no in range(start, end + 1):
            similarity = _label_similarity(lines[line_no - 1], aliases)
            if similarity < 0.60:
                continue
            distance = abs(line_no - candidate.line_no)
            score = similarity * 0.58 + candidate.confidence * 0.42 - distance * 0.06
            if score >= minimum_score and (best is None or score > best[0]):
                best = (score, candidate, lines[line_no - 1])
    return best
