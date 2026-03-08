"""
Pre-route decision layer for ask/chat: run before AIRouter.

Single-shot only: run once per request and stop. No continuous loop, no retries,
no background work. Callers (e.g. ask/chat) invoke pre_route(ctx) once per message.

Reuses OfflineEngineV1 intent classification to detect:
- normal question -> send to provider
- command/tool request (not implemented in this flow) -> Lumos message
- unsupported (empty/too short) -> short Lumos explanation
"""
from __future__ import annotations

from pathlib import Path

from lumos_core.context.context import Context
from lumos_core.policy.decision import PreRouteResult
from lumos_core.policy.offline_engine import OfflineEngineV1
from lumos_core.tools.file_tools import try_handle_read_file
from lumos_core.tools.project_tools import try_handle_project_structure
from lumos_core.tools.system_tools import try_handle_readonly_tool

# Exact phrases that are CLI commands (lock/presence/alias/durum). Chat/ask do not run these.
_COMMAND_PHRASES = frozenset({
    "kilit", "kilit durumu", "kilit?", "lock", "lock status",
    "kilidi aç", "kilit aç", "unlock", "kilitac", "kilit açar mısın",
    "kilidi kapat", "kilit kapat", "kilitkapat",
    "kamera", "presence", "durum", "alias",
})
# Prefixes for multi-word commands (e.g. "kamera aç", "alias ekle")
_COMMAND_PREFIXES = ("kamera ", "alias ", "presence ")

# Relay/tell: birine mesaj iletme, söyleme, haber verme (tell X, relay to someone)
_RELAY_VERBS = ("ilet", "haber ver", "mesaj ilet", "de ki", "yazıver", "yazı ver")
# Recipient + "söyle" (order can be "X söyle" or "söyle X"; "kankime slm söyle" has both)
_RELAY_RECIPIENTS = (
    "kankime", "kankine", "arkadaşıma", "arkadaşına", "anneme", "annene",
    "babama", "babana", "birine", "ona", "buna", "şuna",
)
# Device/system: cihazdan okuma, kontrol, sistem işlemi
_DEVICE_SYSTEM_PHRASES = (
    "cihazın ", "cihaza ", "cihazı ", "cihaz ", "telefona bak", "telefonu aç",
    "telefonu kapat", "pil durum", "ekranı ", "sistemi kontrol", "ayara bak",
    "ayarı aç", "ayarı değiştir", "cihaza bak", "cihazı kontrol", "durumuna bak",
)

_USE_CLI_MSG = "Lumos: Bu komut için interaktif CLI kullanın: python -m lumos_core cli"
_RELAY_MSG = "Lumos: Birine mesaj iletme / söyleme bu modda desteklenmiyor."
# Short, clear message when device/system request is outside read-only tool set.
_DEVICE_MSG = "Lumos: Bu özellik desteklenmiyor. Sorabileceğiniz: hangi klasördeyim, burada ne var, Python sürümü, disk alanı, sistem bilgisi."


def _looks_like_relay(lower: str) -> bool:
    """True if request is to tell/relay something to someone (command, not a general question)."""
    for v in _RELAY_VERBS:
        if v in lower:
            return True
    # "X'e söyle" / "kankime slm söyle" etc.: recipient + imperative "söyle"
    if "söyle" in lower and any(r in lower for r in _RELAY_RECIPIENTS):
        return True
    return False


def _looks_like_device_or_system_action(lower: str) -> bool:
    """True if request is to read/control device or run a system action (not a general question)."""
    return any(p in lower for p in _DEVICE_SYSTEM_PHRASES)


def pre_route(ctx: Context) -> PreRouteResult:
    """
    Decide whether to send the request to the AI provider or return a Lumos message.
    Reuses OfflineEngineV1 intent classification; does not call the provider.
    """
    msg = (getattr(ctx, "message", "") or "").strip()
    lower = msg.lower()

    # Unsupported: empty or too short
    if not msg or len(msg) <= 2:
        return PreRouteResult(
            "unsupported",
            "Lumos: Çok kısa veya boş. Bir soru veya cümle yazın."
        )

    # Command/tool: exact CLI command phrase or prefix
    if lower in _COMMAND_PHRASES:
        return PreRouteResult("tool_not_implemented", _USE_CLI_MSG)
    if any(lower.startswith(p) for p in _COMMAND_PREFIXES):
        return PreRouteResult("tool_not_implemented", _USE_CLI_MSG)

    # Command/tool: natural Turkish relay (tell someone, message someone)
    if _looks_like_relay(lower):
        return PreRouteResult("tool_not_implemented", _RELAY_MSG)

    # Read-only system tools: cwd, list dir, python version, disk usage, system info
    tool_result = try_handle_readonly_tool(msg)
    if tool_result is not None:
        return PreRouteResult("tool", tool_result)
    # Read-only file tool: read text file (path in message or ctx.current_file)
    file_result = try_handle_read_file(msg, cwd=Path.cwd(), current_file=getattr(ctx, "current_file", None) or None)
    if file_result is not None:
        return PreRouteResult("tool", file_result)
    # Read-only project structure: scan project / show repo structure
    project_result = try_handle_project_structure(msg, cwd=Path.cwd())
    if project_result is not None:
        return PreRouteResult("tool", project_result)

    # Command/tool: device read/control or system action (not in our read-only set)
    if _looks_like_device_or_system_action(lower):
        return PreRouteResult("tool_not_implemented", _DEVICE_MSG)

    # Reuse offline engine intent (no callbacks needed for classify only)
    engine = OfflineEngineV1()
    intent = engine._classify(lower)

    # Command intents: time, perm — not runnable in chat/ask
    if intent == "DEVICE_TIME":
        return PreRouteResult(
            "tool_not_implemented",
            "Lumos: Saat ve tarih için interaktif CLI kullanın: python -m lumos_core cli"
        )
    if intent == "PERM_STATUS":
        return PreRouteResult(
            "tool_not_implemented",
            "Lumos: İzin durumu için interaktif CLI kullanın: python -m lumos_core cli"
        )

    # Tool intents: not implemented in this flow
    if intent == "NETWORK_REQUIRED_WEATHER":
        return PreRouteResult(
            "tool_not_implemented",
            "Lumos: Hava durumu bu modda desteklenmiyor."
        )
    if intent == "NETWORK_REQUIRED_FX":
        return PreRouteResult(
            "tool_not_implemented",
            "Lumos: Kur bilgisi bu modda desteklenmiyor."
        )
    if intent == "ACTION_SEND_SMS":
        return PreRouteResult(
            "tool_not_implemented",
            "Lumos: Mesaj gönderme bu modda desteklenmiyor."
        )
    if intent == "ACTION_DRAFT_ORDER":
        return PreRouteResult(
            "tool_not_implemented",
            "Lumos: Sipariş taslağı bu modda desteklenmiyor."
        )

    # GENERAL or anything else: normal question -> provider
    return PreRouteResult("provider", "")


if __name__ == "__main__":
    # Run once and stop: single pre_route invocation then exit (no loop).
    import sys
    from lumos_core.context.context import Context
    msg = sys.argv[1] if len(sys.argv) > 1 else "What is the time?"
    result = pre_route(Context(message=msg))
    print(f"destination={result.destination!r} message={result.message!r}")
    sys.exit(0)
