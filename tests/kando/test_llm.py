from kando.llm import _response_text, llm

def test_llm_returns_invalid_when_response_empty_or_short():
    assert _response_text("") == ""
    assert _response_text("a") == "a"

def test_llm_returns_response_when_valid_format():
    assert _response_text("valid response") == "valid response"

def test_response_text_when_response_is_none():
    assert _response_text(None) == "None"

def test_response_text_when_expected_field_missing():
    class ResponseWithoutOutputText:
        def __str__(self):
            return "fallback text"

    assert _response_text(ResponseWithoutOutputText()) == "fallback text"

def test_response_text_with_very_long_output_text():
    class ResponseWithLongOutputText:
        output_text = " " + ("x" * 10000) + " "

    result = _response_text(ResponseWithLongOutputText())
    assert result == " " + ("x" * 10000) + " "
    assert len(result) == 10002

def test_response_text_handles_different_exception_types():
    class GetAttrRaisesRuntimeError:
        @property
        def output_text(self):
            raise RuntimeError("boom")

        def __str__(self):
            return "runtime fallback"

    class GetAttrRaisesValueErrorAndStrRaisesTypeError:
        @property
        def output_text(self):
            raise ValueError("bad value")

        def __str__(self):
            raise TypeError("cannot stringify")

    assert _response_text(GetAttrRaisesRuntimeError()) == "runtime fallback"
    assert _response_text(GetAttrRaisesValueErrorAndStrRaisesTypeError()) == ""


def test_basic_intents():
    assert llm("durum").startswith("Lumos Core aktif")
    assert llm("proje durum").startswith("Lumos Core aktif")
    assert llm("şişt") == (
        "Tam anlaşılmadı ama bir şey soruyorsun. 'yardım' yaz veya biraz netleştir."
    )
