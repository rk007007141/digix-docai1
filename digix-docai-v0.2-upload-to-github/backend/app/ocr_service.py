import io
import os
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pypdf import PdfReader

TESSERACT_CMD=os.getenv("TESSERACT_CMD",r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd=TESSERACT_CMD

def _preprocess(image):
    image=ImageOps.exif_transpose(image).convert("L")
    if image.width < 1400:
        scale=1400/image.width
        image=image.resize((int(image.width*scale),int(image.height*scale)),Image.Resampling.LANCZOS)
    image=ImageOps.autocontrast(image)
    image=ImageEnhance.Contrast(image).enhance(1.8)
    image=image.filter(ImageFilter.SHARPEN)
    return image.point(lambda p: 255 if p > 175 else 0)

def _ocr(image):
    results=[]
    for psm in (6,11):
        results.append(pytesseract.image_to_string(image,lang="eng",config=f"--oem 3 --psm {psm}") or "")
    return max(results,key=lambda x:len(x.strip()))

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
        processed=_preprocess(original)
        print("OCR IMAGE SIZE:",processed.size)
        text=_ocr(processed)
        print("OCR SUCCESS")
        print("OCR CHARACTERS:",len(text))
        print("OCR PREVIEW:",text[:1000])
        return text[:30000]
    except Exception as e:
        print("OCR ERROR:",repr(e)); raise
