from __future__ import annotations

from integrations.mail.connector import get_mail_connector
from integrations.mail.grants import MAIL_GRANT_READ
from integrations.mail.grants import session_from_payload, validate_mail_grants
from integrations.mail.models import MailConnectionStatus
from integrations.mail.vault_credential import get_vault_credential_bridge, mail_read_credential_ref
from integrations.models import IntegrationRequest, IntegrationResult

SUPPORTED_MAIL_ACTIONS = ("connection_status", "list_unread", "notify_check")

# Dar v1 — send_reply ve diğer dış etkili aksiyonlar desteklenmez.
UNSUPPORTED_DAR_V1_ACTIONS = frozenset(
    {"send_reply", "send", "delete", "archive", "label", "draft_prep"},
)


def _summary_to_dict(summary) -> dict[str, str]:
    return {
        "message_id": summary.message_id,
        "subject_preview": summary.subject_preview,
        "from_preview": summary.from_preview,
        "received_at": summary.received_at,
    }


def run_mail_action(request: IntegrationRequest) -> IntegrationResult:
    action = request.action.strip().lower()
    if action in UNSUPPORTED_DAR_V1_ACTIONS:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={"reason": "dar_v1_scope_excluded"},
            error="unsupported_mail_action",
        )
    if action not in SUPPORTED_MAIL_ACTIONS:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={},
            error="unsupported_mail_action",
        )

    session = session_from_payload(request.payload)
    vault = get_vault_credential_bridge()
    cred_ref = mail_read_credential_ref(session.account_id)
    vault_hint = vault.connection_hint(cred_ref)
    vault_ok = vault.is_configured(cred_ref)
    grants_include_read = MAIL_GRANT_READ in session.grants
    connector = get_mail_connector(
        account_id=session.account_id,
        vault_configured=vault_ok,
        grants_include_read=grants_include_read,
        vault_bridge=vault,
    )

    if action == "connection_status":
        status = MailConnectionStatus(
            provider=connector.provider,
            vault_configured=vault.is_configured(cred_ref),
            connector_ready=True,
            account_id=session.account_id,
        )
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "provider": status.provider,
                "vault_configured": status.vault_configured,
                "connector_ready": status.connector_ready,
                "account_id": status.account_id,
                "vault_hint": vault_hint,
                "dar_v1_grants": sorted(session.grants),
            },
        )

    grant_error = validate_mail_grants(
        session,
        require_notify=(action == "notify_check"),
    )
    if grant_error:
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={"grant_error": grant_error},
            error=grant_error,
        )

    if not vault.is_configured(cred_ref):
        return IntegrationResult(
            ok=False,
            provider=request.provider,
            action=request.action,
            data={
                "vault_hint": vault_hint,
                "account_id": session.account_id,
            },
            error="vault_credential_not_configured",
        )

    if action == "list_unread":
        limit_raw = request.payload.get("limit", 10)
        limit = int(limit_raw) if isinstance(limit_raw, int) else 10
        summaries = connector.list_unread_summaries(account_id=session.account_id, limit=limit)
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "account_id": session.account_id,
                "count": len(summaries),
                "messages": [_summary_to_dict(s) for s in summaries],
            },
        )

    if action == "notify_check":
        return IntegrationResult(
            ok=True,
            provider=request.provider,
            action=request.action,
            data={
                "account_id": session.account_id,
                "notify_eligible": True,
                "message": "notify_grant_valid_demo_stub",
            },
        )

    return IntegrationResult(
        ok=False,
        provider=request.provider,
        action=request.action,
        data={},
        error="unsupported_mail_action",
    )


def register_mail_provider(register) -> None:
    all_actions = set(SUPPORTED_MAIL_ACTIONS) | set(UNSUPPORTED_DAR_V1_ACTIONS)
    for mail_action in all_actions:
        register("mail", mail_action, run_mail_action)
