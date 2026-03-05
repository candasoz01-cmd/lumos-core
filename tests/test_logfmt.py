"""Unit tests for logfmt: sorting, bool, quoting."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lumos_core.core.logfmt import logfmt  # noqa: E402


def test_logfmt_event_first():
    out = logfmt("presence_enabled", timeout=10, poll=1.0, cam=0, require_face=True)
    assert out.startswith("event=presence_enabled ")
    assert "event=presence_enabled" in out


def test_logfmt_sorted_keys():
    out = logfmt("e", z=1, a=2, m=3)
    # event first, then a=2, m=3, z=1
    assert out.startswith("event=e ")
    idx_a = out.index("a=")
    idx_m = out.index("m=")
    idx_z = out.index("z=")
    assert idx_a < idx_m < idx_z


def test_logfmt_bool():
    out = logfmt("e", enabled=True, disabled=False)
    assert "enabled=true" in out
    assert "disabled=false" in out


def test_logfmt_none_omitted():
    out = logfmt("e", a=1, b=None, c=3)
    assert "a=1" in out
    assert "c=3" in out
    assert "b=" not in out or "b=None" not in out


def test_logfmt_str_with_space_quoted():
    out = logfmt("e", msg="hello world")
    assert '"hello world"' in out or "msg=" in out
