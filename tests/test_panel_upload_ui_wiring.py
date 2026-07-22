"""Panel Dosyalar modülü canonical /panel/upload bağlantı kanıtları."""

from __future__ import annotations

from tests.test_panel_component_split import read_panel_source


def _source() -> str:
    return read_panel_source()


def _upload_click_block() -> str:
    text = _source().split("function wireDosyalarUpload()", 1)[1]
    return text.split('btn.addEventListener("click", async () => {', 1)[1].split(
        "renderDosyalarHistory();", 1
    )[0]


def test_panel_upload_uses_canonical_multipart_endpoint() -> None:
    text = _source()
    assert "async function uploadPanelFile(file)" in text
    assert "const form = new FormData();" in text
    assert 'form.append("file", file, file.name);' in text
    assert "fetch(UPLOAD_URL" in text
    assert 'headers["X-Kando-Token"] = kandoToken' in text


def test_dosyalar_click_no_longer_uses_controlled_file_rw() -> None:
    block = _upload_click_block()
    assert "await uploadPanelFile(file)" in block
    assert "controlledWriteFile" not in block
    assert "controlledReadFile" not in block
    assert "readBlobAsUtf8" not in block
    assert "dosyalarClientSummary" not in block


def test_upload_response_maps_metadata_without_summary_claim() -> None:
    block = _upload_click_block()
    assert "uploaded.data.file" in block
    assert 'summary: ""' in block
    assert 'info: ""' in block
    assert "uploaded.data.duplicate === true" in block
