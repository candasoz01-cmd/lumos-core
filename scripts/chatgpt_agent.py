#!/usr/bin/env python3
"""
ChatGPT (OpenAI Responses API, varsayılan streaming) → relay → bridge → Kando outbox özeti.

Çalıştırma: depo kökünden (bridge ve watcher ile aynı .lumos yolu için).
"""
from __future__ import annotations

import os
import sys
import time

from kando.relay_outbox_client import (
    env_float,
    expected_goal_inbox,
    mtime,
    outbox_paths,
    post_relay,
    print_summary,
    relay_url,
    repo_root_from_kando_file,
    wait_for_new_outbox,
)

_DEFAULT_MODEL = "gpt-4.1-mini"
_DEFAULT_WAIT_SEC = 600.0

_SYSTEM = """You convert user input into a single task sentence.

STRICT RULES:
- Output ONLY the task itself
- DO NOT include "goal:"
- DO NOT explain
- DO NOT ask questions
- DO NOT add extra text

Example:
Input: test
Output: Acknowledge the test input.
"""

# Responses stream event type strings (SDK / API)
_T_CREATED = "response.created"
_T_PROGRESS = "response.in_progress"
_T_OUT_DELTA = "response.output_text.delta"
_T_OUT_DONE = "response.output_text.done"
_REASON_DELTA_MARKERS = ("reasoning", "delta")

_ROOT = repo_root_from_kando_file()
_OUT_EXEC, _OUT_RESULT = outbox_paths(_ROOT)


def _stream_enabled() -> bool:
    v = (os.getenv("LUMOS_AGENT_STREAM") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _stream_style() -> str:
    return (os.getenv("LUMOS_AGENT_STREAM_STYLE") or "execution").strip().lower()


def _skip_relay() -> bool:
    return (os.getenv("LUMOS_AGENT_SKIP_BRIDGE") or "").strip().lower() in ("1", "true", "yes", "on")


def _extract_response_text(response: object) -> str:
    reply = getattr(response, "output_text", None)
    if reply is not None and str(reply).strip():
        return str(reply).strip()
    out = getattr(response, "output", None)
    if out and len(out) > 0:
        content = getattr(out[0], "content", None)
        if content and len(content) > 0:
            t = getattr(content[0], "text", None)
            if t is not None and str(t).strip():
                return str(t).strip()
    return ""


def _call_openai_sync(user_text: str) -> str:
    from openai import OpenAI

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        print("OPENAI_API_KEY tanımlı değil.", file=sys.stderr)
        sys.exit(2)
    model = (os.getenv("OPENAI_MODEL") or "").strip() or _DEFAULT_MODEL
    client = OpenAI(api_key=key)
    full_input = _SYSTEM + "\n\nUser:\n" + user_text
    print("[durum] analiz ediliyor …", flush=True)
    print("[durum] görev metni hazırlanıyor …", flush=True)
    try:
        try:
            response = client.responses.create(
                model=model,
                input=full_input,
                timeout=120,
            )
        except TypeError:
            response = client.responses.create(
                model=model,
                input=full_input,
            )
    except Exception as e:
        print(f"OpenAI API hatası: {e}", file=sys.stderr)
        sys.exit(3)

    text = _extract_response_text(response)
    if not text:
        print("Model boş yanıt döndü.", file=sys.stderr)
        sys.exit(3)
    return text


def _call_openai_stream(user_text: str) -> str:
    """Responses API streaming; execution modunda kısa durum satırları, verbose modda canlı akış."""
    from openai import OpenAI

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        print("OPENAI_API_KEY tanımlı değil.", file=sys.stderr)
        sys.exit(2)
    model = (os.getenv("OPENAI_MODEL") or "").strip() or _DEFAULT_MODEL
    client = OpenAI(api_key=key)
    full_input = _SYSTEM + "\n\nUser:\n" + user_text
    style = _stream_style()
    verbose = style in (
        "verbose",
        "chat",
        "analysis",
        "suggest",
        "self_improve",
        "full",
    )

    chunks: list[str] = []
    seen_status: set[str] = set()

    def _status_once(key: str, line: str) -> None:
        if key in seen_status:
            return
        seen_status.add(key)
        print(line, flush=True)

    print("… OpenAI Responses (streaming)", flush=True)
    if not verbose:
        print("(durum: analiz → görev metni → ardından Kando)", flush=True)

    try:
        try:
            cm = client.responses.stream(
                model=model,
                input=full_input,
                timeout=120,
            )
        except TypeError:
            cm = client.responses.stream(
                model=model,
                input=full_input,
            )
    except Exception as e:
        print(f"Streaming başlatılamadı: {e}", file=sys.stderr)
        sys.exit(3)

    try:
        with cm as stream:
            for event in stream:
                et = getattr(event, "type", "") or ""

                if not verbose:
                    if et == _T_CREATED:
                        _status_once("analiz", "[durum] analiz ediliyor …")
                    elif et == _T_PROGRESS:
                        _status_once("hazir", "[durum] görev metni hazırlanıyor …")
                    elif et == _T_OUT_DELTA:
                        _status_once("hazir", "[durum] görev metni hazırlanıyor …")
                    elif et == _T_OUT_DONE:
                        print(flush=True)

                if verbose and all(m in et for m in _REASON_DELTA_MARKERS):
                    d = getattr(event, "delta", None)
                    if d:
                        print(d, end="", flush=True, file=sys.stderr)

                if et == _T_OUT_DELTA:
                    d = getattr(event, "delta", "") or ""
                    chunks.append(d)
                    print(d, end="", flush=True)

            print(flush=True)
            final = stream.get_final_response()
    except Exception as e:
        print(f"OpenAI streaming hatası: {e}", file=sys.stderr)
        sys.exit(3)

    text = "".join(chunks).strip()
    if not text:
        text = _extract_response_text(final)
    if not text:
        print("Model boş yanıt döndü.", file=sys.stderr)
        sys.exit(3)
    return text


def _normalize_llm_goal(text: str) -> str:
    t = (text or "").strip()
    if t.lower().startswith("goal:"):
        t = t.split(":", 1)[1].strip()
    return t


def _call_openai(user_text: str) -> str:
    if _stream_enabled():
        return _call_openai_stream(user_text)
    print("… OpenAI Responses (streaming kapalı, senkron mod)", flush=True)
    return _call_openai_sync(user_text)


def _post_relay_or_exit(url: str, goal_text: str) -> None:
    try:
        post_relay(url, goal_text)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(4)


def main() -> None:
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        print("OPENAI_API_KEY tanımlı değil.", file=sys.stderr)
        sys.exit(2)

    relay = relay_url()
    wait_sec = env_float("KANDO_WAIT_TIMEOUT_SEC", _DEFAULT_WAIT_SEC)

    print("ChatGPT agent (çıkmak için boş satır veya Ctrl+D / Ctrl+C)")
    print(
        "Streaming: açık (varsayılan). Kapatmak: LUMOS_AGENT_STREAM=0. "
        "Öneri/analiz canlı akış: LUMOS_AGENT_STREAM_STYLE=verbose",
        flush=True,
    )
    print(f"Relay: {relay}", flush=True)
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue

        goal = _normalize_llm_goal(_call_openai(line))
        goal = f"{goal} [{int(time.time())}]"
        print("\n… Kando görev metni (relay JSON \"goal\" alanında; köprüde görev: öneki eklenir)\n")

        if _skip_relay():
            print("LUMOS_AGENT_SKIP_BRIDGE=1 → relay/Kando atlandı.\n")
            continue

        prev_e = mtime(_OUT_EXEC)
        prev_r = mtime(_OUT_RESULT)

        print("[durum] Kando'ya gönderiliyor …", flush=True)
        _post_relay_or_exit(relay, goal)

        print("[durum] sonuç bekleniyor …", flush=True)
        if not wait_for_new_outbox(prev_e, prev_r, goal, wait_sec, root=_ROOT):
            print(
                f"Zaman aşımı ({wait_sec:.0f}s): outbox bu istek için güncellenmedi veya "
                f"execution.goal beklenen ile eşleşmedi ({expected_goal_inbox(goal)}). "
                "kando_watch ve bridge çalışıyor mu? Aynı görev metni tekrar gönderilirse "
                "watcher dedup ile yeni çalıştırma yapmayabilir.",
                file=sys.stderr,
            )
            sys.exit(5)

        print_summary(root=_ROOT)


if __name__ == "__main__":
    main()
