#!/usr/bin/env python3
"""
Aynı kullanıcı mesajını /chat'e 3 kez ardışık gönderir; yanıtları loglar ve tutarlılık özeti üretir.

Tek değişken: mesaj metni (argv veya CHAT_TEST_MESSAGE).
Ortam: KANDO_BRIDGE_URL, isteğe bağlı KANDO_BRIDGE_TOKEN (X-Kando-Token).

Çıktı: logs/chat_repeatability_<timestamp>.log + stdout özeti.

Not: Sohbet yolu LLM kullanıyorsa yanıtlar doğası gereği değişebilir; bu betik
     "aynı mı?" sorusunu ölçüm + log ile görünür kılar.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _post_chat(base: str, token: str, message: str, history: list) -> tuple[int, str]:
    url = base.rstrip("/") + "/chat"
    body = json.dumps({"message": message, "history": history}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("X-Kando-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _safe_json(raw: str) -> dict | None:
    try:
        o = json.loads(raw)
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


def _reply_text(d: dict | None) -> str:
    if not d:
        return ""
    r = d.get("reply")
    if isinstance(r, str):
        return r.strip()
    return ""


def _mode(d: dict | None) -> str:
    if not d:
        return ""
    m = d.get("mode")
    return str(m) if m is not None else ""


def main() -> int:
    msg = (
        os.environ.get("CHAT_TEST_MESSAGE", "").strip()
        or (sys.argv[1].strip() if len(sys.argv) > 1 else "")
    )
    if not msg:
        print("Kullanım: CHAT_TEST_MESSAGE='metin' python3 chat_triple_repeatability.py", file=sys.stderr)
        print("   veya: python3 chat_triple_repeatability.py 'metin'", file=sys.stderr)
        return 2

    base = os.environ.get("KANDO_BRIDGE_URL", "http://127.0.0.1:8765").strip()
    token = os.environ.get("KANDO_BRIDGE_TOKEN", "").strip()

    repo_root = Path(__file__).resolve().parents[1]
    log_dir = repo_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    log_path = log_dir / f"chat_repeatability_{ts}.log"

    lines: list[str] = []
    lines.append(f"# Lumos /chat tekrarlanabilirlik — {ts} UTC")
    lines.append(f"# KANDO_BRIDGE_URL={base}")
    lines.append(f"# Token: {'ayarlı' if token else 'yok'}")
    lines.append(f"# Mesaj (tek input): {json.dumps(msg, ensure_ascii=False)}")
    lines.append("")

    results: list[tuple[int, str]] = []
    for i in range(1, 4):
        lines.append(f"--- İstek {i}/3 — {time.time():.3f} ---")
        t0 = time.perf_counter()
        code, raw = _post_chat(base, token, msg, [])
        dt = time.perf_counter() - t0
        lines.append(f"HTTP {code} ({dt:.2f}s)")
        lines.append(raw)
        lines.append("")
        results.append((code, raw))
        # Köprü ve istemci arasında kısa bekleme (aynı ortam, sıralı)
        time.sleep(0.15)

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    parsed = [_safe_json(r) for _, r in results]
    replies = [_reply_text(p) for p in parsed]
    modes = [_mode(p) for p in parsed]
    codes = [c for c, _ in results]

    same_http = len(set(codes)) == 1
    same_reply_text = len(set(replies)) == 1
    same_mode = len(set(modes)) <= 1

    print("=== Özet (stdout) ===")
    print(f"Log dosyası: {log_path}")
    print(f"HTTP kodları: {codes} → {'aynı' if same_http else 'farklı'}")
    print(f"mode alanları: {modes!r} → {'aynı' if same_mode else 'farklı'}")
    if same_reply_text and replies and replies[0] == "":
        reply_note = "evet (üçü de boş)"
    elif same_reply_text and replies and replies[0]:
        reply_note = "evet (3/3 aynı metin)"
    elif same_reply_text:
        reply_note = "evet (tek tekrarlı değer)"
    else:
        reply_note = "hayır (metinler farklı)"
    print(f"reply metinleri özdeş mi: {reply_note}")
    if replies and not same_reply_text:
        for i, t in enumerate(replies, 1):
            preview = (t[:200] + "…") if len(t) > 200 else t
            print(f"  #{i} reply ({len(t)} kar.): {preview!r}")

    print()
    print("Yorum (otomatik):")
    if same_http and same_mode and same_reply_text and replies and replies[0]:
        print("  Bu koşuda reply metinleri tam özdeş (sohbet/LLM yolu).")
    elif same_http and replies and not same_reply_text:
        print("  Aynı HTTP ve farklı reply: tipik LLM rastgeleliği veya sıcaklık farkı olabilir.")
    elif not same_http:
        print("  HTTP kodları farklı: ortam/kimlik/gateway dalgalanması veya hata.")
    else:
        print("  Karışık veya boş yanıt; log dosyasına bakın.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
