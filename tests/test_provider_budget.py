"""Provider usage ledger and pre-call token budget gate."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engine.model_client import PURPOSE_CYBER, CyberModelError, ModelClient
from engine.provider_budget import LEDGER_NAME, RESERVATION_NAME


def _client(monkeypatch: pytest.MonkeyPatch, base: Path, budget: str | None) -> ModelClient:
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    monkeypatch.setenv("LUMOS_SERVER_SIM", "0")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL_CHAT", raising=False)
    if budget is None:
        monkeypatch.delenv("LUMOS_PROVIDER_BUDGET_TOKENS", raising=False)
    else:
        monkeypatch.setenv("LUMOS_PROVIDER_BUDGET_TOKENS", budget)
    return ModelClient()


def _response(text: str, *, total: int | None, input_tokens: int = 3, output_tokens: int = 2) -> MagicMock:
    resp = MagicMock()
    resp.output_text = text
    resp.output = None
    if total is None:
        resp.usage = None
        resp.usage_metadata = None
        return resp
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.total_tokens = total
    resp.usage = usage
    return resp


def _rows(base: Path) -> list[dict]:
    path = base / LEDGER_NAME
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_unset_budget_keeps_reply_and_records_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, None)
    resp = _response("Cevap.", total=15, input_tokens=10, output_tokens=5)
    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = lambda **kw: resp
        openai_cls.return_value = mock_client
        out = client.generate("GIZLI-PROMPT", mode="—", presence="—", consent="—", lock="—")
    assert out == "Cevap."
    rows = _rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["usage_known"] is True
    assert row["total_tokens"] == 15
    assert row["charged_tokens"] == 15
    assert row["purpose"] == "chat"
    assert row["provider"] == "openai"
    blob = (tmp_path / LEDGER_NAME).read_text(encoding="utf-8")
    assert "GIZLI-PROMPT" not in blob
    assert "sk-test-secret" not in blob
    assert "Cevap." not in blob


def test_budget_is_checked_before_the_provider_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, "0")
    called = {"n": 0}

    def create(**kw):
        called["n"] += 1
        return _response("olmaz", total=1)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        out = client.generate("merhaba", mode="—", presence="—", consent="—", lock="—")
    assert called["n"] == 0
    assert out.startswith("provider_budget_exhausted:")
    assert _rows(tmp_path) == []


def test_known_usage_releases_the_unused_reservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, "100")
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        assert kw["max_output_tokens"] == (100 if calls["n"] == 1 else 90)
        return _response("tamam", total=10, input_tokens=6, output_tokens=4)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        first = client.generate("a", mode="—", presence="—", consent="—", lock="—")
        second = client.generate("b", mode="—", presence="—", consent="—", lock="—")
    assert first == "tamam"
    assert second == "tamam"
    assert calls["n"] == 2
    assert sum(row["charged_tokens"] for row in _rows(tmp_path)) == 20


def test_missing_usage_is_not_counted_as_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, "100")
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        return _response("gelsin", total=None)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        first = client.generate("a", mode="—", presence="—", consent="—", lock="—")
        second = client.generate("b", mode="—", presence="—", consent="—", lock="—")
    assert first == "gelsin"
    assert calls["n"] == 1
    assert second.startswith("provider_budget_exhausted:")
    rows = _rows(tmp_path)
    assert rows[0]["usage_known"] is False
    assert rows[0]["total_tokens"] is None
    assert rows[0]["charged_tokens"] == 100
    assert rows[0]["charged_tokens"] != 0


def test_concurrent_calls_cannot_share_one_remainder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, "50")
    entered = threading.Event()
    release = threading.Event()
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        entered.set()
        assert release.wait(2)
        return _response("bir", total=5)

    outcomes: list[str] = []

    def run() -> None:
        with patch("openai.OpenAI") as openai_cls:
            mock_client = MagicMock()
            mock_client.responses.create = create
            openai_cls.return_value = mock_client
            outcomes.append(client.generate("x", mode="—", presence="—", consent="—", lock="—"))

    first = threading.Thread(target=run)
    second = threading.Thread(target=run)
    first.start()
    assert entered.wait(2)
    second.start()
    second.join(2)
    release.set()
    first.join(2)
    assert calls["n"] == 1
    assert sum(item.startswith("provider_budget_reserved:") for item in outcomes) == 1
    assert sum(item == "bir" for item in outcomes) == 1
    assert not (tmp_path / RESERVATION_NAME).exists()


def test_invalid_budget_does_not_mean_unlimited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, "abc")
    called = {"n": 0}

    def create(**kw):
        called["n"] += 1
        return _response("yok", total=1)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        out = client.generate("a", mode="—", presence="—", consent="—", lock="—")
    assert called["n"] == 0
    assert out.startswith("provider_budget_config_invalid:")


def test_cyber_budget_blocks_before_the_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL_CYBER", "gpt-cyber")
    client = _client(monkeypatch, tmp_path, "0")
    called = {"n": 0}

    def create(**kw):
        called["n"] += 1
        return _response("yok", total=1)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        with pytest.raises(CyberModelError) as caught:
            client.generate("a", mode="—", presence="—", consent="—", lock="—", purpose=PURPOSE_CYBER)
    assert called["n"] == 0
    assert caught.value.status == "provider_budget_exhausted"


def test_real_zero_usage_does_not_block_the_next_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, tmp_path, "30")

    def create(**kw):
        return _response("sifir", total=0, input_tokens=0, output_tokens=0)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        first = client.generate("a", mode="—", presence="—", consent="—", lock="—")
        second = client.generate("b", mode="—", presence="—", consent="—", lock="—")
    assert first == "sifir"
    assert second == "sifir"
    assert [row["charged_tokens"] for row in _rows(tmp_path)] == [0, 0]


def test_provider_error_does_not_record_unknown_usage_as_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(monkeypatch, tmp_path, "40")
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("network")
        return _response("sonra", total=1)

    with patch("openai.OpenAI") as openai_cls:
        mock_client = MagicMock()
        mock_client.responses.create = create
        openai_cls.return_value = mock_client
        first = client.generate("a", mode="—", presence="—", consent="—", lock="—")
        second = client.generate("b", mode="—", presence="—", consent="—", lock="—")
    assert first == "Model yanıt vermedi"
    assert calls["n"] == 1
    assert second.startswith("provider_budget_exhausted:")
    assert _rows(tmp_path)[0]["usage_known"] is False
    assert _rows(tmp_path)[0]["charged_tokens"] == 40
