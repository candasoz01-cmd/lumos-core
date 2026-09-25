"""Shared Wall retention policy; evaluation never executes deletion.

Deployment profile is trusted configuration, never a request-body field.
Audit evidence and optional deleted-content copies are distinct record classes.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone


@dataclass(frozen=True)
class EvidencePolicy:
    profile: str = 'internal'
    capture_deleted_content: bool = True

    def __post_init__(self):
        if self.profile not in {'internal', 'customer'}:
            raise ValueError('Unknown deployment profile')
        if type(self.capture_deleted_content) is not bool:
            raise ValueError('capture_deleted_content must be boolean')
        if self.profile == 'internal' and not self.capture_deleted_content:
            raise ValueError('Internal retention cannot be disabled')

    def set_capture(self, enabled: bool):
        if self.profile == 'internal':
            raise ValueError('Internal retention is locked')
        return replace(self, capture_deleted_content=enabled)

    def view(self):
        return {'capture_deleted_content': self.capture_deleted_content,
                'toggle_visible': self.profile == 'customer',
                'audit_required': True, 'automatic_deletion': False}

    def record_terms(self, at: datetime, *, kind: str, severity: str):
        at = utc(at)
        if kind not in {'audit', 'deleted_content'}:
            raise ValueError('Unknown evidence kind')
        if severity not in {'ordinary', 'critical', 'unknown'}:
            raise ValueError('Unknown severity')
        if kind == 'deleted_content' and not self.capture_deleted_content:
            return None  # Only NEW optional copies; old evidence is untouched.
        # Calendar year, not 365 days (Feb 29 conservatively rolls to Mar 1).
        try:
            floor = at.replace(year=at.year + 1)
        except ValueError:
            floor = at.replace(year=at.year + 1, month=3, day=1)
        return {'schema': 'lumos.wall.retention.v1', 'kind': kind,
                'recorded_at': at.isoformat(), 'severity': severity,
                'retain_until': floor.isoformat(), 'default_retention': 'indefinite',
                'automatic_deletion': False,
                'classification_hold': severity != 'ordinary'}


def utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError('Timezone-aware timestamp required')
    return value.astimezone(timezone.utc)


def deletion_blockers(terms, *, at, exact_scope_approval_verified=False,
                      investigation_open=True):
    """Report prerequisites only; no permission token and no purge implementation.

    Approval must be verified by the existing human-authority gate, not accepted
    from an agent/user-supplied boolean at an HTTP boundary. Unknown severity is
    held until a separate, approved classification event establishes its floor.
    """
    if not isinstance(terms, dict) or terms.get('schema') != 'lumos.wall.retention.v1':
        return ['INVALID_RETENTION_RECORD']
    try:
        recorded = utc(datetime.fromisoformat(terms['recorded_at']))
        minimum = EvidencePolicy().record_terms(recorded, kind=terms['kind'],
                                                severity=terms['severity'])
        floor = utc(datetime.fromisoformat(terms['retain_until']))
        if floor < datetime.fromisoformat(minimum['retain_until']):
            return ['RETENTION_FLOOR_TAMPERED']
        at = utc(at)
    except (ValueError, KeyError, TypeError):
        return ['INVALID_RETENTION_RECORD']
    reasons = []
    if at < floor:
        reasons.append('MINIMUM_RETENTION_NOT_ELAPSED')
    if terms.get('classification_hold') is not False or terms['severity'] != 'ordinary':
        reasons.append('SEVERITY_RETENTION_UNRESOLVED')
    if investigation_open is not False:
        reasons.append('INVESTIGATION_HOLD')
    if exact_scope_approval_verified is not True:
        reasons.append('EXPLICIT_SCOPE_APPROVAL_REQUIRED')
    return reasons
