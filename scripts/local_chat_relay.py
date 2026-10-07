#!/usr/bin/env python3
"""
ChatGPT → pano / stdin → relay (8766) → bridge → Kando → outbox özeti.

ChatGPT masaüstü veya web uygulaması yerel HTTP ile komut göndermez; doğrudan entegrasyon yoktur.
Panoyu izle (--watch) veya panodan tek sefer (--clipboard); görev satırı CORE>> ile başlar.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from kando.relay_outbox_client import (
    RelayResultError,
    env_float,
    expected_goal_inbox,
    macos_notify,
    mtime,
    outbox_bytes_mark,
    outbox_paths,
    post_relay,
    print_summary,
    relay_url,
    repo_root_from_kando_file,
    tag_request,
    wait_for_relay_result,
)

_DEFAULT_WAIT_SEC = 600.0
_DEFAULT_PREFIX = "CORE>>"
_MIN_GOAL_LEN = 8


def _read_pbpaste() -> str:
    import subprocess

    r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return ""
    return (r.stdout or "").strip()


def _strip_prefix(raw: str, prefix: str) -> str | None:
    t = (raw or "").strip()
    if not t:
        return None
    p = (prefix or "").strip()
    if not p:
        return None
    if not t.startswith(p):
        return None
    rest = t[len(p) :].strip()
    if len(rest) < _MIN_GOAL_LEN:
        return None
    return rest


def _run_pipeline(goal: str, *, root, relay: str, wait_sec: float, notify: bool) -> int:
    goal_tagged = tag_request(goal)
    oe, or_ = outbox_paths(root)
    prev_e = mtime(oe)
    prev_r = mtime(or_)
    mark_e = outbox_bytes_mark(oe)
    mark_r = outbox_bytes_mark(or_)
    print("[local_chat_relay] relay'e gönderiliyor …", flush=True)
    try:
        receipt = post_relay(relay, goal_tagged)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        if notify:
            macos_notify("Kando relay", f"Hata: {str(e)[:120]}")
        return 4
    print("[local_chat_relay] outbox bekleniyor …", flush=True)
    try:
        snapshot = wait_for_relay_result(
            receipt,
            prev_e,
            prev_r,
            goal_tagged,
            wait_sec,
            root=root,
            prev_exec_mark=mark_e,
            prev_res_mark=mark_r,
        )
    except RelayResultError as e:
        print(str(e), file=sys.stderr)
        if notify:
            macos_notify("Kando", str(e))
        return e.exit_code
    if snapshot is None:
        msg = (
            f"Zaman aşımı veya ilişkili sonuç yok ({expected_goal_inbox(goal_tagged)}). "
            "Teslim belirsiz; otomatik yeniden gönderilmedi. Yeniden göndermeden önce sonucu inceleyin."
        )
        print(msg, file=sys.stderr)
        if notify:
            macos_notify("Kando", "Zaman aşımı veya eşleşme yok")
        return 5
    print_summary(snapshot=snapshot)
    if not snapshot.succeeded:
        print("Sonuç alındı; görev başarıyla tamamlanmadı. Otomatik yeniden gönderilmedi.", file=sys.stderr)
        if notify:
            macos_notify("Kando", "Görev başarıyla tamamlanmadı; terminalde sonucu inceleyin.")
        return 6
    if notify:
        macos_notify("Kando", "Görev tamamlandı; terminalde özet var.")
    return 0


def main() -> int:
    if sys.platform != "darwin":
        print(
            "Bu script pano için macOS (pbpaste) kullanır. "
            "stdin modu: echo 'CORE>>...' | PYTHONPATH=src python scripts/local_chat_relay.py --stdin",
            file=sys.stderr,
        )

    ap = argparse.ArgumentParser(description="ChatGPT metnini relay'e ilet (pano veya stdin).")
    ap.add_argument(
        "--watch",
        action="store_true",
        help="Panoyu periyodik oku; CORE>> (veya LUMOS_CLIPBOARD_PREFIX) ile başlayan yeni içeriği gönder.",
    )
    ap.add_argument(
        "--clipboard",
        action="store_true",
        help="Tek sefer pbpaste oku ve gönder (CORE>> veya LUMOS_CLIPBOARD_PREFIX zorunlu).",
    )
    ap.add_argument(
        "--stdin",
        action="store_true",
        help="stdin'den tüm metni oku (CORE>> veya LUMOS_CLIPBOARD_PREFIX zorunlu).",
    )
    ap.add_argument(
        "--no-notify",
        action="store_true",
        help="macOS bildirimini kapat.",
    )
    args = ap.parse_args()

    root = repo_root_from_kando_file()
    relay = relay_url()
    wait_sec = env_float("KANDO_WAIT_TIMEOUT_SEC", _DEFAULT_WAIT_SEC)
    prefix = (os.getenv("LUMOS_CLIPBOARD_PREFIX") or _DEFAULT_PREFIX).strip() or _DEFAULT_PREFIX
    poll = env_float("KANDO_CLIPBOARD_POLL_SEC", 1.0)
    notify = not args.no_notify

    if args.watch:
        if sys.platform != "darwin":
            print("--watch yalnızca macOS'ta desteklenir.", file=sys.stderr)
            return 2
        print(
            f"[local_chat_relay] İzleme: pano her {poll:.1f}s; görev '{prefix}' ile başlamalı.\n"
            f"Relay: {relay}\n"
            f"ChatGPT yanıtını kopyalayın; ilk satıra {prefix} ekleyin, ardından görev metni.\n"
            "Durdurmak: Ctrl+C\n",
            flush=True,
        )
        seen_clip = ""
        while True:
            time.sleep(poll)
            raw = _read_pbpaste()
            if raw == seen_clip:
                continue
            seen_clip = raw
            goal = _strip_prefix(raw, prefix)
            if goal is None:
                continue
            print(f"\n[local_chat_relay] Yeni görev algılandı ({len(goal)} karakter)\n", flush=True)
            code = _run_pipeline(goal, root=root, relay=relay, wait_sec=wait_sec, notify=notify)
            if code:
                # Stop the watcher so copying the same uncertain request cannot resend it.
                return code

    elif args.clipboard:
        if sys.platform != "darwin":
            print("--clipboard macOS gerektirir.", file=sys.stderr)
            return 2
        raw = _read_pbpaste()
        goal = _strip_prefix(raw, prefix)
        if goal is None:
            print(
                f"Pano metni '{prefix}' ile başlamalı ve en az {_MIN_GOAL_LEN} karakter görev içermeli.",
                file=sys.stderr,
            )
            return 3
        return _run_pipeline(goal, root=root, relay=relay, wait_sec=wait_sec, notify=notify)

    elif args.stdin:
        raw = sys.stdin.read()
        goal = _strip_prefix(raw, prefix)
        if goal is None:
            print(
                f"stdin '{prefix}' ile başlamalı ve en az {_MIN_GOAL_LEN} karakter görev içermeli.",
                file=sys.stderr,
            )
            return 3
        return _run_pipeline(goal, root=root, relay=relay, wait_sec=wait_sec, notify=notify)

    else:
        ap.print_help()
        print(
            f"\nÖrnek: ChatGPT'den yanıtı kopyala (başına {prefix} ekle), sonra:\n"
            "  PYTHONPATH=src python scripts/local_chat_relay.py --clipboard\n",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
