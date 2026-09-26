from pydantic import BaseModel
from typing import Any
class DocumentAnalysis(BaseModel):
    document_type:str; filename:str; provider:str|None=None; document_date:str|None=None
    due_date:str|None=None; amount:float|None=None; currency:str|None=None
    summary:str; actions:list[str]; confidence:float; extracted_fields:dict[str,Any]
    document_id:str|None=None
class QuestionRequest(BaseModel):
    document_id:str
    question:str
class QuestionAnswer(BaseModel):
    answer:str
    confidence:float
    grounded:bool
    evidence:list[str]
