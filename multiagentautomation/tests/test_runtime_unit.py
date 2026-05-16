from src.agents.runtime import _strip_json_fences, _parse_reader_output, _parse_judge_output

def test_strip_json_fences():
    assert _strip_json_fences('```json\n{"a":1}\n```') == '{"a":1}'
    print("✓ fence stripping works")

def test_reader_parser_valid():
    out = _parse_reader_output('{"evidence_cards": []}')
    assert out["evidence_cards"] == []
    print("✓ reader parser handles valid JSON")

def test_reader_parser_invalid():
    out = _parse_reader_output("Sorry, I cannot comply.")
    assert out["evidence_cards"] == []
    print("✓ reader parser gracefully handles bad JSON")

def test_judge_parser_valid():
    out = _parse_judge_output('{"findings": []}')
    assert out["findings"] == []
    print("✓ judge parser handles valid JSON")

def test_judge_parser_invalid():
    out = _parse_judge_output("Not JSON at all.")
    assert out["findings"] == []
    print("✓ judge parser gracefully handles bad JSON")