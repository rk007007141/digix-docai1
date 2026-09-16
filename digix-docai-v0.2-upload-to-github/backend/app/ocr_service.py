import io
from PIL import Image
import pytesseract
from pypdf import PdfReader

def extract_text(filename:str,content_type:str,data:bytes)->str:
    if content_type=="application/pdf" or filename.lower().endswith(".pdf"):
        try:
            r=PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in r.pages)[:30000]
        except Exception:
            return ""
    try:
        image=Image.open(io.BytesIO(data)).convert("RGB")
        return pytesseract.image_to_string(image)[:30000]
    except Exception:
        return ""
