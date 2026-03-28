#!/usr/bin/env python3
"""
ChatGPT → pano / stdin → relay (8766) → bridge → watcher → Kando → outbox özeti.

ChatGPT masaüstü veya web uygulaması yerel HTTP ile komut göndermez; doğrudan entegrasyon yoktur.
Çalışan MVP: panoyu izle (--watch) veya panodan tek sefer (--clipboard); görev satırı KANDO>> ile başlar.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from kando.relay_outbox_client import (
    env_float,
    expected_goal_inbox,
    macos_notify,
    mtime,
    outbox_paths,
    post_relay,
    print_summary,
    relay_url,
    repo_root_from_kando_file,
    wait_for_new_outbox,
)

_DEFAULT_WAIT_SEC = 600.0
_DEFAULT_PREFIX = "KANDO>>"
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
    goal_tagged = f"{goal.strip()} [{int(time.time())}]"
    oe, or_ = outbox_paths(root)
    prev_e = mtime(oe)
    prev_r = mtime(or_)
    print("[local_chat_relay] relay'e gönderiliyor …", flush=True)
    try:
        post_relay(relay, goal_tagged)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        if notify:
            macos_notify("Kando relay", f"Hata: {str(e)[:120]}")
        return 4
    print("[local_chat_relay] outbox bekleniyor …", flush=True)
    if not wait_for_new_outbox(prev_e, prev_r, goal_tagged, wait_sec, root=root):
        msg = (
            f"Zaman aşımı veya goal eşleşmedi ({expected_goal_inbox(goal_tagged)[:80]}…)"
        )
        print(msg, file=sys.stderr)
        if notify:
            macos_notify("Kando", "Zaman aşımı veya eşleşme yok")
        return 5
    print_summary(root=root)
    if notify:
        macos_notify("Kando", "Görev tamamlandı; terminalde özet var.")
    return 0


def main() -> int:
    if sys.platform != "darwin":
        print(
            "Bu script pano için macOS (pbpaste) kullanır. "
            "stdin modu: echo 'KANDO>>...' | PYTHONPATH=src python scripts/local_chat_relay.py --stdin",
            file=sys.stderr,
        )

    ap = argparse.ArgumentParser(description="ChatGPT metnini relay'e ilet (pano veya stdin).")
    ap.add_argument(
        "--watch",
        action="store_true",
        help="Panoyu periyodik oku; KANDO>> ile başlayan yeni içerikte relay tetikle.",
    )
    ap.add_argument(
        "--clipboard",
        action="store_true",
        help="Tek sefer pbpaste oku ve gönder (KANDO>> zorunlu).",
    )
    ap.add_argument(
        "--stdin",
        action="store_true",
        help="stdin'den tüm metni oku (KANDO>> zorunlu).",
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
            "ChatGPT yanıtını kopyalayın; ilk satıra KANDO>> ekleyin, ardından görev metni.\n"
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
            _run_pipeline(goal, root=root, relay=relay, wait_sec=wait_sec, notify=notify)

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
            "\nÖrnek: ChatGPT'den yanıtı kopyala (başına KANDO>> ekle), sonra:\n"
            "  PYTHONPATH=src python scripts/local_chat_relay.py --clipboard\n",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
