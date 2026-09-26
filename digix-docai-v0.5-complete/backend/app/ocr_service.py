import io
import statistics
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pytesseract import Output
from pypdf import PdfReader

from .config import settings

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

@dataclass
class OCRResult:
    text: str
    words: list[dict[str, Any]]
    quality: float
    page_count: int = 1

def _normalize_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("L")
    if image.width < settings.ocr_max_width:
        scale = settings.ocr_max_width / max(image.width, 1)
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    return ImageOps.autocontrast(image)

def _variants(image: Image.Image) -> list[Image.Image]:
    base = _normalize_image(image)
    contrast = ImageEnhance.Contrast(base).enhance(1.7).filter(ImageFilter.SHARPEN)
    threshold = contrast.point(lambda p: 255 if p > 172 else 0)
    return [base, contrast, threshold]

def _ocr_variant(image: Image.Image, psm: int) -> OCRResult:
    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config=f"--oem 3 --psm {psm}",
        output_type=Output.DICT,
    )

    words = []
    confidences = []

    for i, raw in enumerate(data["text"]):
        token = (raw or "").strip()
        if not token:
            continue
        try:
            raw_conf = float(data["conf"][i])
        except (TypeError, ValueError):
            raw_conf = -1
        if raw_conf < 10:
            continue

        conf = max(0.0, min(1.0, raw_conf / 100.0))
        confidences.append(conf)
        words.append({
            "text": token,
            "confidence": conf,
            "left": int(data["left"][i]),
            "top": int(data["top"][i]),
            "width": int(data["width"][i]),
            "height": int(data["height"][i]),
            "block": int(data["block_num"][i]),
            "paragraph": int(data["par_num"][i]),
            "line": int(data["line_num"][i]),
        })

    groups = {}
    for w in words:
        key = (w["block"], w["paragraph"], w["line"])
        groups.setdefault(key, []).append(w)

    lines = []
    for group in groups.values():
        group.sort(key=lambda w: w["left"])
        text = " ".join(w["text"] for w in group).strip()
        if text:
            lines.append((min(w["top"] for w in group), min(w["left"] for w in group), text))

    lines.sort()
    text = "\n".join(x[2] for x in lines)
    mean_conf = statistics.fmean(confidences) if confidences else 0.0
    token_bonus = min(len(words), 250) / 250.0
    quality = max(0.0, min(1.0, mean_conf * 0.9 + token_bonus * 0.1))
    return OCRResult(text=text[:50000], words=words, quality=quality)

def _score(result: OCRResult) -> float:
    useful = sum(c.isalnum() for c in result.text)
    return result.quality * 1000 + min(useful, 5000) / 10

def _ocr_image(image: Image.Image) -> OCRResult:
    candidates = []
    for variant in _variants(image):
        for psm in (6, 11, 12):
            try:
                candidates.append(_ocr_variant(variant, psm))
            except Exception as exc:
                print("OCR PASS ERROR:", repr(exc))
    if not candidates:
        raise RuntimeError("No OCR pass completed successfully.")
    return max(candidates, key=_score)

def extract_document(filename: str, content_type: str, data: bytes) -> OCRResult:
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

    if is_pdf:
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)[:50000]
            if text.strip():
                return OCRResult(text=text, words=[], quality=0.98, page_count=len(reader.pages))
            return OCRResult(text="", words=[], quality=0.0, page_count=len(reader.pages))
        except Exception as exc:
            print("PDF EXTRACTION ERROR:", repr(exc))
            raise

    try:
        image = Image.open(io.BytesIO(data))
        print("TESSERACT PATH:", pytesseract.pytesseract.tesseract_cmd)
        print("IMAGE SIZE:", image.size)
        result = _ocr_image(image)
        print("OCR QUALITY:", round(result.quality, 3))
        print("OCR CHARACTERS:", len(result.text))
        print("OCR PREVIEW:", result.text[:1500])
        return result
    except Exception as exc:
        print("OCR ERROR:", repr(exc))
        raise
