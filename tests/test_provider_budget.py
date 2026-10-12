"""Provider usage ledger and pre-call token budget gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engine.model_client import PURPOSE_CYBER, CyberModelError, ModelClient
from engine.provider_budget import (
    LEDGER_NAME,
    RESERVATION_NAME,
    REASON_EXHAUSTED,
    REASON_RESERVED,
    BudgetDenied,
    reserve_for_call,
)

_REPO = Path(__file__).resolve().parents[1]
_WORKER = r"""
import json, os, sys, time
mode, base, budget = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ["LUMOS_BASE_DIR"] = base
if budget:
    os.environ["LUMOS_PROVIDER_BUDGET_TOKENS"] = budget
else:
    os.environ.pop("LUMOS_PROVIDER_BUDGET_TOKENS", None)
from engine.provider_budget import (
    REASON_EXHAUSTED,
    BudgetDenied,
    UsageSnapshot,
    commit_call,
    reserve_for_call,
)
try:
    if mode == "reserve":
        reservation = reserve_for_call(model="gpt-test", purpose="chat")
        print(json.dumps({"ok": True, "tokens": reservation.tokens, "id": reservation.id}))
    elif mode == "append":
        reservation = reserve_for_call(model="gpt-test", purpose="chat")
        commit_call(reservation, UsageSnapshot(True, 4, 6, 10))
        print(json.dumps({"ok": True, "id": reservation.id}))
    elif mode == "fill":
        for _ in range(40):
            try:
                reservation = reserve_for_call(model="gpt-test", purpose="chat")
            except BudgetDenied as exc:
                if exc.reason == REASON_EXHAUSTED:
                    print(json.dumps({"ok": False, "reason": exc.reason}))
                    break
                time.sleep(0.02)
                continue
            commit_call(reservation, UsageSnapshot(True, 5, 5, 10))
            print(json.dumps({"ok": True, "tokens": reservation.tokens, "id": reservation.id}))
            break
        else:
            print(json.dumps({"ok": False, "reason": "retry_exhausted"}))
    else:
        raise SystemExit("bad mode")
except BudgetDenied as exc:
    print(json.dumps({"ok": False, "reason": exc.reason}))
"""


def _child_env(base: Path, budget: str | None) -> dict[str, str]:
    env = os.environ.copy()
    env["LUMOS_BASE_DIR"] = str(base)
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(_REPO / "src"),
            str(_REPO / "packages" / "kando_runtime" / "src"),
            str(_REPO / "packages" / "kando_bridge" / "src"),
        ]
    )
    if budget is None:
        env.pop("LUMOS_PROVIDER_BUDGET_TOKENS", None)
    else:
        env["LUMOS_PROVIDER_BUDGET_TOKENS"] = budget
    return env


def _run_worker(base: Path, budget: str | None, mode: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _WORKER, mode, str(base), budget or ""],
        cwd=_REPO,
        env=_child_env(base, budget),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _spawn_workers(base: Path, budget: str | None, mode: str, count: int) -> list[dict]:
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", _WORKER, mode, str(base), budget or ""],
            cwd=_REPO,
            env=_child_env(base, budget),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(count)
    ]
    results = []
    for proc in procs:
        stdout, stderr = proc.communicate(timeout=30)
        assert proc.returncode == 0, stderr
        results.append(json.loads(stdout))
    return results


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


def test_two_processes_cannot_hold_the_same_remainder(tmp_path: Path) -> None:
    results = _spawn_workers(tmp_path, "80", "reserve", 2)
    admitted = [item for item in results if item["ok"]]
    denied = [item for item in results if not item["ok"]]
    assert len(admitted) == 1
    assert admitted[0]["tokens"] == 80
    assert len(denied) == 1
    assert denied[0]["reason"] == REASON_RESERVED
    payload = json.loads((tmp_path / RESERVATION_NAME).read_text(encoding="utf-8"))
    assert len(payload["reservations"]) == 1
    assert payload["reservations"][0]["tokens"] == 80


def test_dead_process_reservation_blocks_the_next_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    held = _run_worker(tmp_path, "50", "reserve")
    assert held["ok"] is True
    assert held["tokens"] == 50
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_PROVIDER_BUDGET_TOKENS", "50")
    with pytest.raises(BudgetDenied) as caught:
        reserve_for_call(model="gpt-test", purpose="chat")
    assert caught.value.reason == REASON_RESERVED
    assert _rows(tmp_path) == []
    assert (tmp_path / RESERVATION_NAME).is_file()


def test_restart_charges_abandoned_reservation_instead_of_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reservation_id = "dead-worker-reservation"
    (tmp_path / RESERVATION_NAME).write_text(
        json.dumps(
            {
                "reservations": [
                    {
                        "id": reservation_id,
                        "tokens": 30,
                        "created_unix": time.time() - 1000,
                        "provider": "openai",
                        "model": "gpt-test",
                        "purpose": "chat",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LUMOS_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("LUMOS_PROVIDER_BUDGET_TOKENS", "100")
    reservation = reserve_for_call(model="gpt-test", purpose="chat")
    assert reservation.tokens == 70
    rows = _rows(tmp_path)
    assert rows[0]["reservation_id"] == reservation_id
    assert rows[0]["usage_known"] is False
    assert rows[0]["charged_tokens"] == 30
    assert rows[0]["total_tokens"] is None


def test_parallel_ledger_appends_stay_valid_json(tmp_path: Path) -> None:
    results = _spawn_workers(tmp_path, None, "append", 8)
    assert all(item["ok"] for item in results)
    text = (tmp_path / LEDGER_NAME).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == 8
    rows = [json.loads(line) for line in lines]
    assert [row["charged_tokens"] for row in rows] == [10, 10, 10, 10, 10, 10, 10, 10]
    assert len({row["reservation_id"] for row in rows}) == 8


def test_parallel_workers_cannot_exceed_the_budget(tmp_path: Path) -> None:
    results = _spawn_workers(tmp_path, "40", "fill", 8)
    successes = [item for item in results if item["ok"]]
    assert len(successes) == 4
    text = (tmp_path / LEDGER_NAME).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    rows = [json.loads(line) for line in lines]
    assert len(rows) == 4
    assert sum(row["charged_tokens"] for row in rows) == 40
    denied = [item for item in results if not item["ok"]]
    assert denied
    assert {item["reason"] for item in denied} <= {REASON_EXHAUSTED, REASON_RESERVED}
