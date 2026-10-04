from app.candidate_service import detect_candidates

SAMPLE = """
SAMPLE CUSTOMER ONE & SAMPLE CUSTOMER TWO
Consumer Number 916020050226267
Bill Date 03-12-2019
Due Date 19-12-2019
Bad OCR Date 32-12-2019
Rs 1720 00
Rs 1750.00
Rs 1730 00
300 KV
"""

def test_candidate_extraction_keeps_valid_values():
    found = detect_candidates(SAMPLE)

    dates = [item.normalized for item in found["dates"]]
    amounts = [item.normalized for item in found["amounts"]]
    ids = [item.normalized for item in found["identifiers"]]
    measurements = [item.normalized for item in found["measurements"]]

    assert "2019-12-03" in dates
    assert "2019-12-19" in dates
    assert all("32" not in item for item in dates)
    assert "1720.00" in amounts
    assert "1750.00" in amounts
    assert "1730.00" in amounts
    assert "916020050226267" in ids
    assert "300 KV" in measurements
