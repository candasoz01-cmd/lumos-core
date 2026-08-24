"""The credential list in conftest.py must not drift away from the tree.

conftest.py strips outbound provider credentials so tests cannot make live,
nondeterministic calls. That protection is only as good as its list, and a list
maintained by hand goes stale quietly -- which is the failure mode the
provenance layer exists to prevent. So derive the credentials from the source
and require every one of them to be classified.
"""
from __future__ import annotations

import re
from pathlib import Path

from conftest import _LOCAL_CREDENTIAL_ENV, _PROVIDER_CREDENTIAL_ENV

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCANNED = ("src", "packages")

# Same shape as the re-derivation command documented next to the list.
_CREDENTIAL_READ = re.compile(
    r"""os\.(?:getenv|environ\.get)\(\s*["']([A-Z0-9_]*(?:API_KEY|TOKEN))["']"""
)


def _credentials_read_in_tree() -> set[str]:
    found: set[str] = set()
    for top in _SCANNED:
        for path in (_REPO_ROOT / top).rglob("*.py"):
            found.update(_CREDENTIAL_READ.findall(path.read_text(encoding="utf-8")))
    return found


def test_every_credential_in_the_tree_is_classified() -> None:
    """A new provider key must be stripped or declared local, never neither."""
    classified = set(_PROVIDER_CREDENTIAL_ENV) | set(_LOCAL_CREDENTIAL_ENV)
    unclassified = _credentials_read_in_tree() - classified
    assert not unclassified, (
        f"unclassified credential(s) read by src/ or packages/: {sorted(unclassified)}. "
        "Add each to _PROVIDER_CREDENTIAL_ENV (stripped in tests) or to "
        "_LOCAL_CREDENTIAL_ENV (local auth, left in place) in conftest.py."
    )


def test_no_stale_entries_in_the_credential_lists() -> None:
    """A name nothing reads any more is dead weight that hides real coverage."""
    in_tree = _credentials_read_in_tree()
    stale = (set(_PROVIDER_CREDENTIAL_ENV) | set(_LOCAL_CREDENTIAL_ENV)) - in_tree
    assert not stale, (
        f"conftest.py lists credential(s) nothing reads any more: {sorted(stale)}. "
        "Drop them so the list keeps describing the tree."
    )


def test_the_two_lists_do_not_overlap() -> None:
    both = set(_PROVIDER_CREDENTIAL_ENV) & set(_LOCAL_CREDENTIAL_ENV)
    assert not both, f"credential(s) both stripped and declared local: {sorted(both)}"
