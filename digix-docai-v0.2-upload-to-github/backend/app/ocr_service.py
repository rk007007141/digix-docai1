import io, os, re
from PIL import Image,ImageEnhance,ImageFilter,ImageOps
import pytesseract
from pytesseract import Output
from pypdf import PdfReader
TESSERACT_CMD=os.getenv("TESSERACT_CMD",r"C:\Program Files\Tesseract-OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd=TESSERACT_CMD
def prep(im):
 im=ImageOps.exif_transpose(im).convert("L")
 if im.width<2200:
  s=2200/im.width;im=im.resize((int(im.width*s),int(im.height*s)),Image.Resampling.LANCZOS)
 return ImageEnhance.Contrast(ImageOps.autocontrast(im)).enhance(1.8).filter(ImageFilter.SHARPEN)
def image_ocr(data):
 im=prep(Image.open(io.BytesIO(data))); texts=[]
 for psm in (6,11,12):
  texts.append(pytesseract.image_to_string(im,lang="eng",config=f"--oem 3 --psm {psm}") or "")
 best=max(texts,key=lambda x:sum(c.isalnum() for c in x))
 d=pytesseract.image_to_data(im,lang="eng",config="--oem 3 --psm 11",output_type=Output.DICT)
 words=[]
 for i,w in enumerate(d["text"]):
  w=w.strip()
  try: conf=float(d["conf"][i])
  except: conf=-1
  if w and conf>=20: words.append({"text":w,"confidence":round(conf/100,2),"left":d["left"][i],"top":d["top"][i],"width":d["width"][i],"height":d["height"][i]})
 return best[:40000],words
def extract_document(filename,content_type,data):
 if content_type=="application/pdf" or filename.lower().endswith(".pdf"):
  reader=PdfReader(io.BytesIO(data));text="\n".join((p.extract_text() or "") for p in reader.pages)
  return text[:40000],[]
 return image_ocr(data)
def extract_text(filename,content_type,data): return extract_document(filename,content_type,data)[0]
