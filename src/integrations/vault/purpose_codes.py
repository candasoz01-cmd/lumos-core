from __future__ import annotations

# Public-safe amaç kodları — gerçek token/secret yok; yalnızca scoped intent eşlemesi.
PURPOSE_MAIL_READ = "integration.mail.read"
PURPOSE_MAIL_NOTIFY = "integration.mail.notify"

# Amaç kodu → scoped token intent (Infisical RBAC / OAuth scope hedefi; gerçek token değil).
PURPOSE_TOKEN_INTENT: dict[str, str] = {
    PURPOSE_MAIL_READ: "gmail.readonly",
    PURPOSE_MAIL_NOTIFY: "gmail.readonly+notify.meta",
}

_ALL_PURPOSE_CODES = frozenset(PURPOSE_TOKEN_INTENT)


def is_known_purpose_code(purpose_code: str) -> bool:
    return purpose_code in _ALL_PURPOSE_CODES


def token_intent_for_purpose(purpose_code: str) -> str | None:
    """Amaç kodu için scoped token intent; bilinmeyen kodda None."""
    return PURPOSE_TOKEN_INTENT.get(purpose_code)
