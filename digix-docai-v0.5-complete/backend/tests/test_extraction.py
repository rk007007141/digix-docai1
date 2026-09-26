from app.document_service import analyze
from app.qa_service import answer_question

SAMPLE = """
GUJRANWALA ELECTRIC POWER COMPANY
Consumer Number: 916020050226267
Reference No: 12345678901234
Meter No: 778899
Bill Month: SEP 2026
Bill Date: 05-09-2026
Due Date: 25-09-2026
Units Consumed: 418
Previous Reading: 12000
Current Reading: 12418
Current Charges: Rs 6500
Taxes: Rs 780
Arrears: Rs 0
Amount Before Due Date: Rs 7280
Amount After Due Date: Rs 7600
"""

def test_bill_fields():
    result = analyze(
        "bill.png",
        "image/png",
        b"x",
        text_override=SAMPLE,
        words=[],
        ocr_quality=0.91,
    )
    f = result.extracted_fields
    assert result.document_type == "electricity_bill"
    assert f["provider"] == "Gujranwala Electric Power Company"
    assert f["consumer_number"] == "916020050226267"
    assert f["due_date"] == "25-09-2026"
    assert f["amount_before_due"] == 7280.0

def test_missing_field_does_not_hallucinate():
    result = analyze(
        "bill.png",
        "image/png",
        b"x",
        text_override="GUJRANWALA ELECTRIC POWER COMPANY",
        words=[],
        ocr_quality=0.70,
    )
    answer, confidence, grounded, evidence = answer_question(
        "What is the due date?",
        "GUJRANWALA ELECTRIC POWER COMPANY",
        result.extracted_fields,
        result.field_status,
    )
    assert grounded is False
    assert confidence == 0.0
    assert evidence == []
