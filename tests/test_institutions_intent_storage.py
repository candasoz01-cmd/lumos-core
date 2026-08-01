"""Kurum niyet formu yerel kayıt hata sözleşmesi."""

from pathlib import Path


PAGE = Path("ui/src/pages/institutions.astro")


def test_storage_failure_preserves_form_and_does_not_report_success():
    source = PAGE.read_text(encoding="utf-8")
    failure_start = source.index("} catch (_e) {")
    success_start = source.index('statusEl.dataset.state = "ok";')
    failure_block = source[failure_start:success_start]

    assert 'statusEl.dataset.state = "err";' in failure_block
    assert "Niyet bu tarayıcıya kaydedilemedi." in failure_block
    assert "return;" in failure_block
    assert "form.reset();" not in failure_block
    assert source.index("form.reset();") > success_start
