"""sandbox_mode gerçek kaynak (env + CLI override) testleri."""

from main import _sandbox_mode_from_env


def test_sandbox_mode_from_env_unset(monkeypatch):
    """LUMOS_SANDBOX yoksa False."""
    monkeypatch.delenv("LUMOS_SANDBOX", raising=False)
    assert _sandbox_mode_from_env() is False


def test_sandbox_mode_from_env_empty(monkeypatch):
    """LUMOS_SANDBOX='' ise False."""
    monkeypatch.setenv("LUMOS_SANDBOX", "")
    assert _sandbox_mode_from_env() is False


def test_sandbox_mode_from_env_zero(monkeypatch):
    """LUMOS_SANDBOX='0' ise False."""
    monkeypatch.setenv("LUMOS_SANDBOX", "0")
    assert _sandbox_mode_from_env() is False


def test_sandbox_mode_from_env_one(monkeypatch):
    """LUMOS_SANDBOX='1' ise True."""
    monkeypatch.setenv("LUMOS_SANDBOX", "1")
    assert _sandbox_mode_from_env() is True


def test_sandbox_mode_from_env_true(monkeypatch):
    """LUMOS_SANDBOX='true' ise True."""
    monkeypatch.setenv("LUMOS_SANDBOX", "true")
    assert _sandbox_mode_from_env() is True


def test_sandbox_mode_from_env_true_uppercase(monkeypatch):
    """LUMOS_SANDBOX='TRUE' ise True."""
    monkeypatch.setenv("LUMOS_SANDBOX", "TRUE")
    assert _sandbox_mode_from_env() is True


def test_sandbox_mode_from_env_yes(monkeypatch):
    """LUMOS_SANDBOX='yes' ise True."""
    monkeypatch.setenv("LUMOS_SANDBOX", "yes")
    assert _sandbox_mode_from_env() is True


def test_sandbox_mode_from_env_no(monkeypatch):
    """LUMOS_SANDBOX='no' ise False."""
    monkeypatch.setenv("LUMOS_SANDBOX", "no")
    assert _sandbox_mode_from_env() is False


def test_sandbox_mode_from_env_whitespace_stripped(monkeypatch):
    """LUMOS_SANDBOX=' 1 ' ise True (strip)."""
    monkeypatch.setenv("LUMOS_SANDBOX", " 1 ")
    assert _sandbox_mode_from_env() is True
