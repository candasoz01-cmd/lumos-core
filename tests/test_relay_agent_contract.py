"""Offline bridge/relay contract fixtures; never bind sockets or start jobs."""
from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from kando import relay_outbox_client as client
from kando.agent_runner import _write_json
from kando_bridge import server
from kando_runtime import lumos_gate as gate
from kando_runtime.lumos_gate import build_result_payload

ROOT = Path(__file__).resolve().parents[1]
JOB_ID = "0123456789abcdef"
GOAL = "Görevi incele [relay:11111111111111111111111111111111]"


def load_script(name):
    spec = importlib.util.spec_from_file_location(f"fixture_{name}", ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_relay():
    return load_script("relay_agent")


def receipt(**changes):
    """Legacy direct-agent response; current /task uses current_plan_receipt below."""
    ctx = SimpleNamespace(policy_ok=True, reasoning_summary="fixture", execution_mode="agent", verification_summary="agent")
    payload = build_result_payload(ctx=ctx, execution_kind="agent", ex=None, job_id=JOB_ID)
    return server.merge_post_task_http_envelope(
        status=200, payload={**payload, **changes},
        envelope_meta={"raw": client.expected_goal_inbox(GOAL).encode(), "route": "agent"},
    )


def job(root, *, task=None, **changes):
    value = {"job_id": JOB_ID, "status": "completed", "phase": "done", "errors": [],
             "final_report": {"status": "ok", "verify": {"ok": True}, "errors": [],
                              "task": task if task is not None else client.expected_goal_inbox(GOAL)}, **changes}
    _write_json(root / ".lumos/outbox" / f"agent_status_{JOB_ID}.json", value)
    return value


def current_plan_receipt(root, monkeypatch, goal=GOAL):
    """Actual /task producers, including the wrapper that adds normalized_task."""
    raw = client.expected_goal_inbox(goal).encode()
    error, mode, payload, _ = server._resolve_task_routing("text/plain", raw)
    assert error is None and mode == "agent"
    normalized = gate.normalize_request(mode, payload)
    reasoning = {"ok": True, "llm_mode": "agent", "intent": "inspect module",
                 "reason": "offline fixture", "summary": "offline fixture"}
    plan = gate.build_execution_plan(normalized, reasoning, mode=mode)
    starts = []

    def start(task, auto):
        starts.append(task)
        job(root, task=task)  # Worker retains the rewritten plan goal, not raw input.
        return JOB_ID

    def forbidden(*args, **kwargs):
        raise AssertionError("No direct executor, worker, process or network in this fixture")

    import socket
    import subprocess
    import threading

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "bind", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(threading.Thread, "start", forbidden)
    monkeypatch.setattr(gate, "run_lumos_gate_substep", lambda *a, **kw: {
        "policy_ok": True, "_substep_gate_ok": True, "execution_mode": "run",
    })
    monkeypatch.setattr(gate, "validate_substep_with_llm", lambda *a, **kw: {"ok": True})
    kind, execution, jid = gate.execute_plan(
        plan, run_direct=forbidden, start_agent=start, run_agent_auto=None,
        repo_root=root, parent_task={"goal": goal},
    )
    assert kind == "plan" and starts == [plan["steps"][0]["goal"]]
    ctx = gate.GateContext(policy_ok=True, execution_mode="run", reasoning_summary="offline fixture")
    out = gate._build_result_after_execute(
        plan=plan, ctx=ctx, norm=normalized, reasoning=reasoning, risk="low", mode=mode,
        payload=payload, approval_granted=False, kind=kind, ex=execution, job_id=jid, repo_root=root,
    )
    response = server.merge_post_task_http_envelope(
        status=out["http_status"], payload=out["http_body"], envelope_meta={"raw": raw, "route": mode},
    )
    assert response["mode"] == "lumos_plan"
    assert response["step_results"] == [{"type": "agent", "job_id": JOB_ID, "ok": True}]
    assert response["normalized_task"]["raw_payload"] == payload
    return response


def wait(root, response):
    return client.wait_for_relay_result(response, None, None, GOAL, 1, root=root)


@pytest.fixture(autouse=True)
def virtual_clock(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(client.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(client.time, "sleep", lambda n: clock.__setitem__(0, clock[0] + n))


@pytest.mark.parametrize("url", [None, "http://localhost:8765", "http://localhost:8765/", "http://localhost:8765/task"])
def test_bridge_url_uses_supported_task_path(monkeypatch, url):
    monkeypatch.delenv("BRIDGE_URL", raising=False)
    if url:
        monkeypatch.setenv("BRIDGE_URL", url)
    relay = load_relay()
    assert relay.BRIDGE_URL == "http://localhost:8765/task"
    err, mode, payload, _ = server._resolve_task_routing("text/plain", client.expected_goal_inbox(GOAL).encode())
    assert err is None and mode == "agent"
    assert payload == client.expected_goal_inbox(GOAL)


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


def handler(relay):
    h = object.__new__(relay.Handler)
    body = json.dumps({"goal": GOAL}).encode()
    h.headers = {"Content-Length": str(len(body))}
    h.rfile, h.wfile = io.BytesIO(body), io.BytesIO()
    h.send_response = lambda status: setattr(h, "status", status)
    h.send_header = lambda *args: None
    h.end_headers = lambda: None
    return h


@pytest.mark.parametrize("payload", [receipt(), receipt(requires_approval=True), receipt(accepted=False, error="blocked")])
def test_relay_preserves_bridge_json_receipt(monkeypatch, payload):
    relay = load_relay()
    h = handler(relay)
    calls = []
    raw = json.dumps(payload).encode()

    def post(request, **kwargs):
        calls.append(request)
        return Response(raw)

    monkeypatch.setattr(relay, "urlopen", post)
    h.do_POST()
    assert h.status == 200 and h.wfile.getvalue() == raw
    assert len(calls) == 1
    assert calls[0].data == client.expected_goal_inbox(GOAL).encode()


def test_relay_preserves_bridge_http_failure_without_retry(monkeypatch):
    relay = load_relay()
    h = handler(relay)
    raw = b'{"accepted":false,"error":"blocked"}'
    calls = []

    def post(request, **kwargs):
        calls.append(request)
        raise HTTPError(request.full_url, 403, "blocked", {"Content-Type": "application/json"}, io.BytesIO(raw))

    monkeypatch.setattr(relay, "urlopen", post)
    h.do_POST()
    assert h.status == 403 and h.wfile.getvalue() == raw
    assert len(calls) == 1


def test_client_reads_bridge_receipt(monkeypatch):
    response = receipt()
    monkeypatch.setattr(client.urllib.request, "urlopen", lambda *args, **kw: Response(json.dumps(response).encode()))
    assert client.post_relay("http://relay.invalid", GOAL) == response


@pytest.mark.parametrize("changes,code", [
    ({"requires_approval": True}, 7), ({"requires_clarification": True}, 7),
    ({"accepted": False, "video_prompt_clarification": True}, 7),
    ({"accepted": False, "error": "blocked"}, 6), ({"outcome": "failed"}, 6),
    ({"job_id": None}, 8), ({"job_id": "../escape"}, 8),
    ({"mode": "lumos_plan", "outcome": "applied"}, 8),
    ({"mode": "direct_patch", "outcome": "applied", "execution": "patch_applied"}, 8),
])
def test_receipt_alone_never_completes(tmp_path, changes, code):
    job(tmp_path)  # Even a successful last job cannot complete a pending/unsupported receipt.
    with pytest.raises(client.RelayResultError) as error:
        wait(tmp_path, receipt(**changes))
    assert error.value.exit_code == code


@pytest.mark.parametrize("value", [None, {"job_id": "fedcba9876543210"}, {"status": "running", "final_report": None}])
def test_missing_wrong_or_running_job_stays_pending(tmp_path, value):
    if value:
        job(tmp_path, **value)
    with pytest.raises(client.RelayResultError) as error:
        wait(tmp_path, receipt())
    assert error.value.exit_code == 7


@pytest.mark.parametrize("raw", [b"{", b"[]", b"null", b"\xff"])
def test_unreadable_job_record_stays_pending(tmp_path, raw):
    job(tmp_path)
    (tmp_path / ".lumos/outbox" / f"agent_status_{JOB_ID}.json").write_bytes(raw)
    with pytest.raises(client.RelayResultError) as error:
        wait(tmp_path, receipt())
    assert error.value.exit_code == 7


def test_exact_job_terminal_snapshot_is_retained(tmp_path, capsys):
    job(tmp_path)
    snapshot = wait(tmp_path, receipt())
    assert snapshot.succeeded
    job(tmp_path, status="failed")
    client.print_summary(snapshot=snapshot)
    text = capsys.readouterr().out
    assert JOB_ID in text and "completed" in text
    assert snapshot.succeeded


@pytest.mark.parametrize("changes", [
    {"status": "failed"}, {"phase": "verify"}, {"errors": ["failure"]},
    {"final_report": None}, {"final_report": {"status": "failed"}},
    {"final_report": {"status": "partial"}},
    {"final_report": {"status": "ok", "verify": {"ok": False}, "errors": []}},
    {"final_report": {"status": "ok", "verify": {"ok": 1}, "errors": []}},
    {"final_report": {"status": "ok", "verify": {"ok": True}, "errors": ["failure"]}},
])
def test_completed_worker_is_not_necessarily_success(tmp_path, changes):
    job(tmp_path, **changes)
    assert not wait(tmp_path, receipt()).succeeded


def test_delayed_terminal_job_is_read_without_resubmission(tmp_path, monkeypatch):
    job(tmp_path, status="running", final_report=None)
    sleep = client.time.sleep

    def finish(seconds):
        job(tmp_path)
        sleep(seconds)

    monkeypatch.setattr(client.time, "sleep", finish)
    assert wait(tmp_path, receipt()).succeeded


def test_running_job_never_falls_back_to_global_success(tmp_path):
    job(tmp_path, status="running", final_report=None)
    exe, res = client.outbox_paths(tmp_path)
    _write_json(exe, {"goal": client.expected_goal_inbox(GOAL), "task_id": 17})
    _write_json(res, {"goal_preview": client.expected_goal_inbox(GOAL)[:500], "task_id": 17,
                      "outcome": "applied", "task_status": "tamamlandi", "brain_success": True})
    with pytest.raises(client.RelayResultError) as error:
        wait(tmp_path, receipt())
    assert error.value.exit_code == 7


@pytest.mark.parametrize("name", ["local_chat_relay", "chatgpt_agent"])
@pytest.mark.parametrize("producer", ["legacy", "current"])
@pytest.mark.parametrize("changes,code", [
    ({}, 0), ({"accepted": False, "error": "blocked"}, 6),
    ({"requires_approval": True}, 7), ({"job_id": None}, 8),
])
def test_both_clients_honor_bridge_result_without_retry(tmp_path, monkeypatch, name, producer, changes, code):
    module = load_script(name)
    job(tmp_path)
    calls = []

    def post(url, goal):
        calls.append(goal)
        if producer == "current":
            return {**current_plan_receipt(tmp_path, monkeypatch, goal), **changes}
        job(tmp_path, task=client.expected_goal_inbox(goal))
        return receipt(**changes)

    monkeypatch.setattr(module, "post_relay", post)
    if name == "local_chat_relay":
        actual = module._run_pipeline(GOAL, root=tmp_path, relay="http://relay.invalid", wait_sec=1, notify=False)
        assert actual == code
    else:
        monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
        monkeypatch.delenv("LUMOS_AGENT_SKIP_BRIDGE", raising=False)
        monkeypatch.setattr(module, "_ROOT", tmp_path)
        monkeypatch.setattr(module, "_OUT_EXEC", client.outbox_paths(tmp_path)[0])
        monkeypatch.setattr(module, "_OUT_RESULT", client.outbox_paths(tmp_path)[1])
        monkeypatch.setattr(module, "_call_openai", lambda text: GOAL)
        prompts = iter(["fixture request"])

        def prompt(_text):
            try:
                return next(prompts)
            except StopIteration:
                raise EOFError

        monkeypatch.setattr("builtins.input", prompt)
        if code:
            with pytest.raises(SystemExit) as error:
                module.main()
            assert error.value.code == code
        else:
            module.main()
    assert len(calls) == 1


@pytest.mark.parametrize("raw", [b"{", b"[]", b"null", b"\xff"])
def test_invalid_http_body_is_uncertain_without_retry(monkeypatch, raw):
    calls = []

    def post(*args, **kwargs):
        calls.append(args)
        return Response(raw)

    monkeypatch.setattr(client.urllib.request, "urlopen", post)
    with pytest.raises(RuntimeError, match="teslim belirsiz"):
        client.post_relay("http://relay.invalid", GOAL)
    assert len(calls) == 1


def test_legacy_plain_ok_keeps_strict_outbox_contract(monkeypatch):
    monkeypatch.setattr(client.urllib.request, "urlopen", lambda *args, **kw: Response(b"ok"))
    assert client.post_relay("http://relay.invalid", GOAL) is None


def test_relay_transport_timeout_is_uncertain_without_retry(monkeypatch):
    relay = load_relay()
    h = handler(relay)
    calls = []

    def post(request, **kwargs):
        calls.append(request)
        raise TimeoutError("fixture")

    monkeypatch.setattr(relay, "urlopen", post)
    h.do_POST()
    assert h.status == 502
    assert b"delivery uncertain, not retried" in h.wfile.getvalue()
    assert len(calls) == 1


def test_current_single_agent_plan_reaches_terminal_result(tmp_path, monkeypatch):
    response = current_plan_receipt(tmp_path, monkeypatch)
    snapshot = wait(tmp_path, response)
    assert snapshot.succeeded
    assert snapshot.record["final_report"]["task"].startswith("Lumos bridge (LLM plan)")
    assert GOAL not in snapshot.record["final_report"]["task"]


@pytest.mark.parametrize("old_goal", [
    "Görevi incele [relay:22222222222222222222222222222222]",
    "Completely different request [relay:33333333333333333333333333333333]",
])
def test_replayed_legacy_receipt_cannot_certify_new_request(tmp_path, old_goal):
    job(tmp_path, task=client.expected_goal_inbox(old_goal))
    path = tmp_path / ".lumos/outbox" / f"agent_status_{JOB_ID}.json"
    os.utime(path, (100, 100))
    assert not wait(tmp_path, receipt()).succeeded


def test_legacy_terminal_requires_request_task(tmp_path):
    job(tmp_path, task="")
    assert not wait(tmp_path, receipt()).succeeded


def test_replayed_plan_receipt_cannot_certify_new_request(tmp_path, monkeypatch):
    response = current_plan_receipt(tmp_path, monkeypatch, GOAL.replace("111111", "222222"))
    with pytest.raises(client.RelayResultError):
        wait(tmp_path, response)


@pytest.mark.parametrize("changed", [
    {"step_results": []}, {"step_results": None}, {"step_results": {}},
    {"step_results": [{"type": "agent", "job_id": JOB_ID, "ok": 1}]},
    {"step_results": [{"type": "agent", "job_id": "fedcba9876543210", "ok": True}]},
    {"step_results": [{"type": "agent", "job_id": JOB_ID, "ok": True}] * 2},
    {"step_results": [{"type": "patch", "ok": True}, {"type": "agent", "job_id": JOB_ID, "ok": True}]},
    {"step_results": [{"type": "agent_auto", "ok": True}]},
    {"step_results": [{"type": "agent", "job_id": JOB_ID, "ok": True, "steps": [{"type": "patch"}]}]},
    {"normalized_task": None}, {"normalized_task": {}},
    {"execution": "unknown"}, {"outcome": None},
])
def test_plan_with_missing_or_ambiguous_binding_is_unsupported(tmp_path, monkeypatch, changed):
    response = {**current_plan_receipt(tmp_path, monkeypatch), **changed}
    with pytest.raises(client.RelayResultError) as error:
        wait(tmp_path, response)
    assert error.value.exit_code == 8


@pytest.mark.parametrize("field", ["raw_payload", "agent_blob", "mode"])
def test_plan_normalized_request_mismatch_fails_closed(tmp_path, monkeypatch, field):
    response = current_plan_receipt(tmp_path, monkeypatch)
    response["normalized_task"][field] = "different request"
    with pytest.raises(client.RelayResultError):
        wait(tmp_path, response)


def test_current_plan_receipt_only_is_pending(tmp_path, monkeypatch):
    response = current_plan_receipt(tmp_path, monkeypatch)
    job(tmp_path, status="running", final_report=None)
    with pytest.raises(client.RelayResultError) as error:
        wait(tmp_path, response)
    assert error.value.exit_code == 7


def test_current_plan_failed_terminal_is_not_success(tmp_path, monkeypatch):
    response = current_plan_receipt(tmp_path, monkeypatch)
    job(tmp_path, final_report={"status": "failed", "errors": ["fixture"], "task": "plan goal"})
    assert not wait(tmp_path, response).succeeded
