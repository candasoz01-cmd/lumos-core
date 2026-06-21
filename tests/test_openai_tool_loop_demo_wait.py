"""OpenAI tool-loop demo script — wait-approve timeout behavior."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "packages" / "kando_bridge" / "src"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from kando_bridge.openai_tool_adapter import ParsedToolCall  # noqa: E402

# Import after path setup
sys.path.insert(0, str(_REPO / "scripts"))
from openai_tool_loop_demo import _wait_for_manual_approve  # noqa: E402


def test_wait_for_manual_approve_timeout(monkeypatch) -> None:
    calls = [ParsedToolCall(name="pc_open_url", arguments={"url": "https://example.com"})]
    pending_results = [
        {
            "stage": "pending",
            "pending": {
                "approval_id": "pc_remote_test",
                "approval_token": "tok",
            },
        }
    ]

    def _never_accept(_aid: str, _tok: str) -> dict:
        return {"accepted": False, "error": "approval_not_approved"}

    monkeypatch.setattr("openai_tool_loop_demo.approve_pending", _never_accept)
    monkeypatch.setattr("openai_tool_loop_demo.time.sleep", lambda _s: None)

    final = _wait_for_manual_approve(calls, pending_results, timeout=0.01)
    assert len(final) == 1
    assert final[0].get("error") == "approval_timeout"
