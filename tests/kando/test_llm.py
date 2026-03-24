from kando.llm import _response_text

def test_llm_returns_invalid_when_response_empty_or_short():
    assert _response_text("") == ""
    assert _response_text("a") == "a"

def test_llm_returns_response_when_valid_format():
    assert _response_text("valid response") == "valid response"
