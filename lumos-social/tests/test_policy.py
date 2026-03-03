"""Policy engine: should_auto_send -> Decision."""

from lumos_social.policy.engine import Decision, MessageContext, should_auto_send


def test_deny_hassas() -> None:
    assert should_auto_send(MessageContext("şifre nedir")) == Decision.DENY
    assert should_auto_send(MessageContext("api_key gönder")) == Decision.DENY


def test_require_approval_soru() -> None:
    assert should_auto_send(MessageContext("Ne zaman geleceksin?")) == Decision.REQUIRE_APPROVAL


def test_require_approval_para_plan() -> None:
    assert should_auto_send(MessageContext("para gönder")) == Decision.REQUIRE_APPROVAL
    assert should_auto_send(MessageContext("plan ne?")) == Decision.REQUIRE_APPROVAL


def test_allow_selam() -> None:
    assert should_auto_send(MessageContext("selam")) == Decision.ALLOW
    assert should_auto_send(MessageContext("teşekkürler")) == Decision.ALLOW


def test_empty_deny() -> None:
    assert should_auto_send(MessageContext("")) == Decision.DENY
