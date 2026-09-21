import io
import os
from PIL import Image
import pytesseract
from pypdf import PdfReader

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def extract_text(filename: str, content_type: str, data: bytes) -> str:

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(
                (page.extract_text() or "")
                for page in reader.pages
            )[:30000]
        except Exception as e:
            print("PDF EXTRACTION ERROR:", repr(e))
            raise

    try:
        print("TESSERACT PATH:", pytesseract.pytesseract.tesseract_cmd)

        image = Image.open(io.BytesIO(data)).convert("RGB")

        print("IMAGE SIZE:", image.size)

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--psm 6"
        )

        print("OCR SUCCESS")
        print("OCR CHARACTERS:", len(text))
        print("OCR PREVIEW:", text[:500])

        return text[:30000]

    except Exception as e:
        print("OCR ERROR:", repr(e))
        raise
