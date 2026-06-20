import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integrations.mail.oauth_contract import (
    GMAIL_OAUTH_CALLBACK_PATH_PATTERN,
    GMAIL_OAUTH_SCOPE_READONLY,
    MAIL_READ_VAULT_REF_PREFIX,
    OAUTH_CALLBACK_ERROR_INVALID_STATE,
    OAUTH_CALLBACK_ERROR_MALFORMED_STATE,
    OAUTH_CALLBACK_ERROR_MISSING_CODE,
    OAUTH_CALLBACK_ERROR_PROVIDER_ERROR,
    OAUTH_CALLBACK_ERROR_UNKNOWN_ACCOUNT,
    OAuthCallbackPhase,
    OAuthCallbackQuery,
    OAuthCallbackResult,
    OAuthCallbackStatePayload,
    OAuthCallbackStatus,
    decode_oauth_state,
    encode_oauth_state,
    evaluate_oauth_callback,
    mail_read_vault_ref_id,
    parse_oauth_callback_query,
)
from integrations.mail.vault_credential import mail_read_credential_ref
from integrations.vault.purpose_codes import PURPOSE_MAIL_READ

# Demo-safe fixture değerleri — gerçek secret/token/client credential yok.
_FIXTURE_ACCOUNT = "user@example.invalid"
_FIXTURE_SESSION = "sess-demo-001"
_FIXTURE_NONCE = "nonce-demo-abc"
_FIXTURE_CODE = "auth-code-placeholder-not-real"


def _fixture_state_payload() -> OAuthCallbackStatePayload:
    return OAuthCallbackStatePayload(
        account_id=_FIXTURE_ACCOUNT,
        session_id=_FIXTURE_SESSION,
        nonce=_FIXTURE_NONCE,
    )


def _fixture_state() -> str:
    return encode_oauth_state(_fixture_state_payload())


def test_callback_path_pattern_public_safe():
    assert GMAIL_OAUTH_CALLBACK_PATH_PATTERN.startswith("/integrations/mail/oauth/")


def test_mail_read_vault_ref_format():
    ref_id = mail_read_vault_ref_id(_FIXTURE_ACCOUNT)
    assert ref_id == f"{MAIL_READ_VAULT_REF_PREFIX}{_FIXTURE_ACCOUNT}"
    ref = mail_read_credential_ref(_FIXTURE_ACCOUNT)
    assert ref.ref_id == ref_id
    assert ref.purpose_code == PURPOSE_MAIL_READ
    assert ref.account_id == _FIXTURE_ACCOUNT


def test_oauth_callback_result_success_vault_ref():
    result = OAuthCallbackResult.success(
        account_id=_FIXTURE_ACCOUNT,
        phase=OAuthCallbackPhase.VAULT_WRITE,
    )
    assert result.status == OAuthCallbackStatus.SUCCESS
    assert result.vault_ref is not None
    assert result.vault_ref.ref_id == mail_read_vault_ref_id(_FIXTURE_ACCOUNT)
    assert result.error_code is None
    assert GMAIL_OAUTH_SCOPE_READONLY in result.scopes


def test_evaluate_oauth_callback_happy_path():
    query = OAuthCallbackQuery(code=_FIXTURE_CODE, state=_fixture_state())
    result = evaluate_oauth_callback(
        query,
        expected_session_id=_FIXTURE_SESSION,
        known_account_ids=frozenset({_FIXTURE_ACCOUNT}),
    )
    assert result.status == OAuthCallbackStatus.SUCCESS
    assert result.phase == OAuthCallbackPhase.VAULT_WRITE
    assert result.vault_ref is not None
    assert result.vault_ref.ref_id.startswith(MAIL_READ_VAULT_REF_PREFIX)


def test_evaluate_oauth_callback_malformed_state():
    query = OAuthCallbackQuery(code=_FIXTURE_CODE, state="not-valid-base64!!!")
    result = evaluate_oauth_callback(query, expected_session_id=_FIXTURE_SESSION)
    assert result.status == OAuthCallbackStatus.ERROR
    assert result.error_code == OAUTH_CALLBACK_ERROR_MALFORMED_STATE


def test_evaluate_oauth_callback_invalid_state():
    query = OAuthCallbackQuery(code=_FIXTURE_CODE)
    result = evaluate_oauth_callback(query, expected_session_id=_FIXTURE_SESSION)
    assert result.error_code == OAUTH_CALLBACK_ERROR_INVALID_STATE


def test_evaluate_oauth_callback_session_mismatch():
    query = OAuthCallbackQuery(code=_FIXTURE_CODE, state=_fixture_state())
    result = evaluate_oauth_callback(query, expected_session_id="other-session")
    assert result.error_code == OAUTH_CALLBACK_ERROR_INVALID_STATE


def test_evaluate_oauth_callback_missing_code():
    query = OAuthCallbackQuery(state=_fixture_state())
    result = evaluate_oauth_callback(query, expected_session_id=_FIXTURE_SESSION)
    assert result.error_code == OAUTH_CALLBACK_ERROR_MISSING_CODE
    assert result.account_id == _FIXTURE_ACCOUNT


def test_evaluate_oauth_callback_unknown_account_id():
    query = OAuthCallbackQuery(code=_FIXTURE_CODE, state=_fixture_state())
    result = evaluate_oauth_callback(
        query,
        expected_session_id=_FIXTURE_SESSION,
        known_account_ids=frozenset({"other@example.invalid"}),
    )
    assert result.error_code == OAUTH_CALLBACK_ERROR_UNKNOWN_ACCOUNT
    assert result.account_id == _FIXTURE_ACCOUNT


def test_evaluate_oauth_callback_provider_error():
    query = OAuthCallbackQuery(error="access_denied", state=_fixture_state())
    result = evaluate_oauth_callback(query, expected_session_id=_FIXTURE_SESSION)
    assert result.error_code == OAUTH_CALLBACK_ERROR_PROVIDER_ERROR


def test_parse_oauth_callback_query():
    parsed = parse_oauth_callback_query(
        {"code": _FIXTURE_CODE, "state": _fixture_state(), "extra": "ignored"}
    )
    assert parsed.code == _FIXTURE_CODE
    assert parsed.state == _fixture_state()


def test_state_roundtrip_no_secrets_in_payload():
    encoded = _fixture_state()
    decoded = decode_oauth_state(encoded)
    assert decoded is not None
    assert decoded.account_id == _FIXTURE_ACCOUNT
    assert decoded.session_id == _FIXTURE_SESSION
    assert decoded.nonce == _FIXTURE_NONCE
    blob = encoded.lower()
    for forbidden in ("secret", "token", "password", "client_secret", "refresh_token"):
        assert forbidden not in blob
