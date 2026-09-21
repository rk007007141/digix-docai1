import io
import os
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pypdf import PdfReader

TESSERACT_CMD=os.getenv("TESSERACT_CMD",r"C:\Program Files\Tesseract-OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd=TESSERACT_CMD

def _variants(image):
    image=ImageOps.exif_transpose(image).convert("L")
    if image.width < 1800:
        scale=1800/image.width
        image=image.resize((int(image.width*scale),int(image.height*scale)),Image.Resampling.LANCZOS)
    base=ImageOps.autocontrast(image)
    contrast=ImageEnhance.Contrast(base).enhance(1.7).filter(ImageFilter.SHARPEN)
    threshold=contrast.point(lambda p:255 if p>170 else 0)
    return [base,contrast,threshold]

def _score(text):
    words=re.findall(r"[A-Za-z0-9]{2,}",text)
    useful=sum(c.isalnum() for c in text)
    return len(words)*5+useful

import re

def _ocr_best(image):
    candidates=[]
    for variant in _variants(image):
        for psm in (6,11,12):
            text=pytesseract.image_to_string(variant,lang="eng",config=f"--oem 3 --psm {psm}") or ""
            candidates.append(text)
    return max(candidates,key=_score)

def extract_text(filename,content_type,data):
    if content_type=="application/pdf" or filename.lower().endswith(".pdf"):
        try:
            reader=PdfReader(io.BytesIO(data))
            text="\n".join((p.extract_text() or "") for p in reader.pages)
            return text[:30000] if text.strip() else ""
        except Exception as e:
            print("PDF EXTRACTION ERROR:",repr(e)); raise
    try:
        print("TESSERACT PATH:",pytesseract.pytesseract.tesseract_cmd)
        original=Image.open(io.BytesIO(data))
        print("IMAGE SIZE:",original.size)
        text=_ocr_best(original)
        print("OCR SUCCESS")
        print("OCR CHARACTERS:",len(text))
        print("OCR PREVIEW:",text[:1500])
        return text[:30000]
    except Exception as e:
        print("OCR ERROR:",repr(e)); raise
