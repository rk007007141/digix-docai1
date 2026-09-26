import re
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Line:
    text: str
    left: int
    top: int
    right: int
    bottom: int
    confidence: float

    @property
    def width(self) -> int:
        return max(1, self.right - self.left)

    @property
    def height(self) -> int:
        return max(1, self.bottom - self.top)

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

@dataclass
class Candidate:
    value: Any
    confidence: float
    source: str
    evidence: str

def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def build_lines(words: list[dict[str, Any]]) -> list[Line]:
    if not words:
        return []

    groups = {}
    for word in words:
        key = (
            int(word.get("block", 0)),
            int(word.get("paragraph", 0)),
            int(word.get("line", 0)),
        )
        groups.setdefault(key, []).append(word)

    lines = []
    for group in groups.values():
        group.sort(key=lambda w: int(w["left"]))
        text = normalize_text(" ".join(str(w["text"]) for w in group))
        if not text:
            continue
        left = min(int(w["left"]) for w in group)
        top = min(int(w["top"]) for w in group)
        right = max(int(w["left"]) + int(w["width"]) for w in group)
        bottom = max(int(w["top"]) + int(w["height"]) for w in group)
        confs = [float(w.get("confidence", 0)) for w in group]
        lines.append(Line(text, left, top, right, bottom, sum(confs) / max(len(confs), 1)))

    lines.sort(key=lambda x: (x.top, x.left))
    return lines

def _label_match(line: Line, aliases: tuple[str, ...]):
    for alias in aliases:
        match = re.search(re.escape(alias), line.text, re.I)
        if match:
            return match
    return None

def _same_line(line, aliases, parser):
    match = _label_match(line, aliases)
    if not match:
        return None
    tail = re.sub(r"^[\s:#=\-|.]+", "", line.text[match.end():])
    value = parser(tail)
    if value is None:
        return None
    return Candidate(value, min(0.97, max(0.72, line.confidence)), "same_line", line.text)

def _nearby(label_line: Line, lines: list[Line]):
    found = []
    for line in lines:
        if line is label_line:
            continue
        y_gap = abs(line.center_y - label_line.center_y)
        if line.left > label_line.right - 10 and y_gap <= max(label_line.height, line.height) * 1.5:
            distance = max(0, line.left - label_line.right) + y_gap * 2
            found.append((distance, line))
            continue

        vertical_gap = line.top - label_line.bottom
        x_overlap = min(line.right, label_line.right) - max(line.left, label_line.left)
        if 0 <= vertical_gap <= max(label_line.height, line.height) * 3.5 and (
            x_overlap > 0 or abs(line.left - label_line.left) < label_line.width
        ):
            found.append((vertical_gap * 2 + abs(line.left - label_line.left) + 40, line))
    return sorted(found, key=lambda x: x[0])

def extract_near_label(
    lines: list[Line],
    aliases: tuple[str, ...],
    parser: Callable[[str], Any | None],
) -> Candidate | None:
    label_lines = [line for line in lines if _label_match(line, aliases)]

    direct = []
    for line in label_lines:
        candidate = _same_line(line, aliases, parser)
        if candidate:
            direct.append(candidate)
    if direct:
        return max(direct, key=lambda c: c.confidence)

    for label_line in label_lines:
        for distance, line in _nearby(label_line, lines)[:4]:
            value = parser(line.text)
            if value is None:
                continue
            penalty = min(0.22, distance / 1200)
            confidence = max(0.55, min(0.92, (label_line.confidence + line.confidence) / 2 - penalty))
            return Candidate(value, confidence, "nearby_line", f"{label_line.text} | {line.text}")

    return None
