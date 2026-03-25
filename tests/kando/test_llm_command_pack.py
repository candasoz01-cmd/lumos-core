from kando.llm import llm


def test_help_pack():
    out = llm("yardım")
    assert "Komutlar:" in out
    assert "- repo: <arama>" in out
    assert "- durum" in out


def test_help_aliases():
    assert "Komutlar:" in llm("komut")
    assert "Komutlar:" in llm("help")


def test_version_intent():
    assert llm("version") == "Lumos Core 0.1.0-secure-core"
    assert llm("sürüm") == "Lumos Core 0.1.0-secure-core"


def test_health_intent():
    assert llm("health") == "OK"
    assert llm("sağlık") == "OK"


def test_status_pack():
    assert llm("durum") == "Lumos Core aktif. Sistem stabil."
    assert llm("proje durum") == "Lumos Core aktif. Sistem stabil."
