"""Display-time chat body formatting.

Unsupported agent walkthrough markup (``TextReference``) must not reach the
user as raw tags. The human-readable ``alt`` text, or the tag's inner text,
is kept. Surrounding message text is not deleted.

This is a render/message-formatting step, not model generation.
"""

from __future__ import annotations

import re

_TEXT_REFERENCE_TAG = re.compile(
    r"(?:<|&lt;)TextReference\b(?P<attrs>.*?)"
    r"(?:"
    r"\s*/\s*(?:>|&gt;)"
    r"|"
    r"(?:>|&gt;)(?P<body>.*?)(?:</|&lt;/)TextReference\s*(?:>|&gt;)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

_ALT_ATTR = re.compile(
    r"""
    \balt\s*=\s*
    (?:
        "([^"]*)"
        | '([^']*)'
        | &quot;([^&]*)&quot;
        | \{\s*"([^"]*)"\s*\}
        | \{\s*'([^']*)'\s*\}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _alt_from_attrs(attrs: str) -> str:
    match = _ALT_ATTR.search(attrs or "")
    if not match:
        return ""
    for group in match.groups():
        if group:
            return group
    return ""


def _replace_text_reference(match: re.Match[str]) -> str:
    alt = _alt_from_attrs(match.group("attrs") or "")
    body = (match.group("body") or "").strip()
    return alt or body


def strip_unsupported_chat_markup(text: str | None) -> str:
    """Return chat body text with unsupported TextReference tags unfolded."""
    if text is None:
        return ""
    return _TEXT_REFERENCE_TAG.sub(_replace_text_reference, str(text))
