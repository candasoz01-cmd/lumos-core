"""CLI offline fixtures; every external side effect is replaced in-process."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest

from kando import relay_outbox_client as client

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def local():
    return script("local_chat_relay")


def result_writer(root, calls, **changes):
    def post(_url, goal):
        calls.append(goal)
        exe = {"goal": client.expected_goal_inbox(goal), "task_id": len(calls)}
        res = {"goal_preview": exe["goal"][:500], "task_id": len(calls),
               "outcome": "applied", "task_status": "tamamlandi", "brain_success": True,
               **changes}
        for path, data in zip(client.outbox_paths(root), (exe, res)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
    return post


@pytest.mark.parametrize("prefix", [None, "CUSTOM>>"])
def test_documented_stdin_prefix(local, tmp_path, monkeypatch, prefix):
    monkeypatch.delenv("LUMOS_CLIPBOARD_PREFIX", raising=False)
    if prefix:
        monkeypatch.setenv("LUMOS_CLIPBOARD_PREFIX", prefix)
    prefix = prefix or "CORE>>"
    monkeypatch.setattr(local.sys, "argv", ["local_chat_relay", "--stdin", "--no-notify"])
    monkeypatch.setattr(local.sys, "stdin", io.StringIO(prefix + " README dosyasını özetle"))
    monkeypatch.setattr(local, "repo_root_from_kando_file", lambda: tmp_path)
    calls = []
    monkeypatch.setattr(local, "post_relay", result_writer(tmp_path, calls))
    assert local.main() == 0
    assert len(calls) == 1
    assert "varsayılan `CORE>>`" in (ROOT / "scripts/README_local_chat_relay.md").read_text()


@pytest.mark.parametrize("change", [
    {"outcome": "failed"}, {"outcome": "blocked"}, {"outcome": "partial"},
    {"outcome": "simulation"}, {"outcome": None}, {"task_status": "hata"},
    {"task_status": "durdu"}, {"task_status": None}, {"brain_success": False},
    {"brain_success": "true"}, {"brain_success": 1},
])
def test_unsuccessful_result_never_claims_completion(local, tmp_path, monkeypatch, change):
    calls, notifications = [], []
    monkeypatch.setattr(local, "post_relay", result_writer(tmp_path, calls, **change))
    monkeypatch.setattr(local, "macos_notify", lambda *args: notifications.append(args))
    code = local._run_pipeline("README dosyasını özetle", root=tmp_path,
                               relay="http://relay.invalid", wait_sec=1, notify=True)
    assert code == 6
    assert len(calls) == 1
    assert all("Görev tamamlandı" not in text for _, text in notifications)


def test_same_task_submitted_twice_in_one_second_gets_distinct_ids(local, tmp_path, monkeypatch):
    monkeypatch.setattr(local.time, "time", lambda: 1000.0)
    calls = []
    monkeypatch.setattr(local, "post_relay", result_writer(tmp_path, calls))
    for _ in range(2):
        assert local._run_pipeline("README dosyasını özetle", root=tmp_path,
                                   relay="http://relay.invalid", wait_sec=1, notify=False) == 0
    assert len(set(calls)) == 2


@pytest.mark.parametrize("code", [4, 5, 6, 7, 8])
def test_watch_stops_after_uncertain_or_unsuccessful_delivery(local, monkeypatch, code):
    monkeypatch.setattr(local.sys, "platform", "darwin")
    monkeypatch.setattr(local.sys, "argv", ["local_chat_relay", "--watch", "--no-notify"])
    monkeypatch.setenv("LUMOS_CLIPBOARD_PREFIX", "CORE>>")
    reads = iter(["CORE>> README dosyasını özetle", "unrelated clipboard", "CORE>> README dosyasını özetle"])
    monkeypatch.setattr(local, "_read_pbpaste", lambda: next(reads))
    monkeypatch.setattr(local.time, "sleep", lambda _seconds: None)
    calls = []
    monkeypatch.setattr(local, "_run_pipeline", lambda *args, **kw: calls.append(args) or code)
    assert local.main() == code
    assert len(calls) == 1


def test_agent_rejects_failed_result_without_new_send(tmp_path, monkeypatch):
    agent = script("chatgpt_agent")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    monkeypatch.delenv("LUMOS_AGENT_SKIP_BRIDGE", raising=False)
    monkeypatch.setattr(agent, "_call_openai", lambda _text: "README dosyasını özetle")
    monkeypatch.setattr(agent, "_ROOT", tmp_path)
    monkeypatch.setattr(agent, "_OUT_EXEC", client.outbox_paths(tmp_path)[0])
    monkeypatch.setattr(agent, "_OUT_RESULT", client.outbox_paths(tmp_path)[1])
    prompts = iter(["summarize readme", EOFError()])

    def next_input(_prompt):
        value = next(prompts)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr("builtins.input", next_input)
    calls = []
    monkeypatch.setattr(agent, "post_relay", result_writer(tmp_path, calls, outcome="failed"))
    with pytest.raises(SystemExit) as error:
        agent.main()
    assert error.value.code == 6
    assert len(calls) == 1


def test_timeout_does_not_post_again(local, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(local, "post_relay", lambda url, goal: calls.append(goal))
    assert local._run_pipeline("README dosyasını özetle", root=tmp_path,
                               relay="http://relay.invalid", wait_sec=0, notify=False) == 5
    assert len(calls) == 1


def test_success_notifies_once(local, tmp_path, monkeypatch):
    calls, notifications = [], []
    monkeypatch.setattr(local, "post_relay", result_writer(tmp_path, calls))
    monkeypatch.setattr(local, "macos_notify", lambda *args: notifications.append(args))
    assert local._run_pipeline("README dosyasını özetle", root=tmp_path,
                               relay="http://relay.invalid", wait_sec=1, notify=True) == 0
    assert len(calls) == len(notifications) == 1
    assert "Görev tamamlandı" in notifications[0][1]


def test_agent_repeated_explicit_requests_are_unique(tmp_path, monkeypatch):
    agent = script("chatgpt_agent")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    monkeypatch.delenv("LUMOS_AGENT_SKIP_BRIDGE", raising=False)
    monkeypatch.setattr(agent, "_call_openai", lambda _text: "README dosyasını özetle")
    monkeypatch.setattr(client.time, "time", lambda: 1000.0)
    monkeypatch.setattr(agent, "_ROOT", tmp_path)
    monkeypatch.setattr(agent, "_OUT_EXEC", client.outbox_paths(tmp_path)[0])
    monkeypatch.setattr(agent, "_OUT_RESULT", client.outbox_paths(tmp_path)[1])
    prompts = iter(["same request", "same request"])

    def next_input(_prompt):
        try:
            return next(prompts)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", next_input)
    calls = []
    monkeypatch.setattr(agent, "post_relay", result_writer(tmp_path, calls))
    agent.main()
    assert len(calls) == len(set(calls)) == 2
