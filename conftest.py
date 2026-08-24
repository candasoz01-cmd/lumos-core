"""Test provenance: every verdict must be traceable to a deterministic decision.

A developer shell that exports a real provider credential turns LLM-gated code
paths into live network calls, so a test's verdict starts to depend on what a
remote model happens to answer. That is what made
tests/test_lumos_gate_execution_grant.py flaky: the substep validator called
gpt-4.1-mini for real, an occasional risk_hint=high blocked execution, and the
failure surfaced as "grant execute olmadi" -- pointing the reader at grant,
nonce and replay logic that were never involved.

So this layer does not only isolate; it reports. Three parts:

1. Isolation -- provider credentials are stripped and outbound egress to
   non-local hosts is refused, so the default posture is deterministic offline.
2. Provenance -- per test: was an external service reached, did an LLM decision
   point run on a real model answer or on its fallback, which host was involved.
3. Attribution -- when a test fails and provenance shows external influence, the
   failure report says so, instead of leaving the reader to misclassify it.

A test that needs a credential sets its own fake one (monkeypatch.setenv /
patch.dict); that still wins over the fixture here. To run against real
providers on purpose, set LUMOS_TEST_ALLOW_LIVE_PROVIDERS=1 -- which lifts both
the credential strip and the egress guard, and marks the run as non-hermetic.

Scope, so this file does not itself become the kind of hidden rule it exists to
expose. It changes no product behaviour and owns exactly three rules: the
credential list below, the local-address rule in _is_local, and the decision
points in _LLM_DECISION_POINTS. Each one is re-derivable from the tree, and the
command that regenerates the credential list sits next to it. Measured blast
radius on 2026-08-24, against a shell holding a real OPENAI_API_KEY: five tests
observe a different environment because of the strip -- all five were making
live model calls before -- and one test has an outbound connection refused.
Every other test reads only credentials it sets itself, so the strip is a no-op
for them. Known gap: the egress guard patches this process only, so the eight
test modules that spawn subprocesses are neither guarded nor recorded there.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from collections.abc import Iterator
from typing import Any

import pytest

# Outbound third-party credentials read by src/ and packages/. Re-derive with:
#   grep -rnoE '(os\.getenv|os\.environ\.get)\(\s*.[A-Z0-9_]*(API_KEY|TOKEN).' src packages
# Whatever that command finds must land in one of the two tuples below --
# tests/test_conftest_provider_isolation.py fails if a new credential appears in
# the tree and nobody classified it, so this rule cannot drift out of sight.
_PROVIDER_CREDENTIAL_ENV = (
    "OPENAI_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "BING_SEARCH_API_KEY",
    "GOOGLE_SEARCH_API_KEY",
    "REPLICATE_API_TOKEN",
    "RECALL_API_KEY",
    "LUMOS_SONOS_ACCESS_TOKEN",
)

# Read by src/ and packages/ but deliberately left in place: these authenticate
# local calls and reach no third party, and the LAN relay tests need theirs.
_LOCAL_CREDENTIAL_ENV = (
    "LUMOS_API_KEY",
    "LUMOS_RELAY_TOKEN",
)

# Decision points that ask a model and fall back to policy when it is absent.
# Wrapped so provenance can tell "model answered" from "fallback ran" without
# guessing from network traffic.
_LLM_DECISION_POINTS = (
    ("kando_runtime.lumos_gate", "validate_substep_with_llm"),
)

_ALLOW_LIVE_ENV = "LUMOS_TEST_ALLOW_LIVE_PROVIDERS"

_TRUTHY = ("1", "true", "yes")


def _live_providers_allowed() -> bool:
    return (os.environ.get(_ALLOW_LIVE_ENV) or "").strip().lower() in _TRUTHY


def _credentials_present() -> tuple[str, ...]:
    return tuple(
        name for name in _PROVIDER_CREDENTIAL_ENV if (os.environ.get(name) or "").strip()
    )


# --------------------------------------------------------------------------
# Provenance record
# --------------------------------------------------------------------------

# nodeid -> {"egress": [host, ...], "llm": [(name, "model"|"fallback"), ...]}
_PROVENANCE: dict[str, dict[str, list[Any]]] = {}
_CURRENT = {"nodeid": "<session>"}
# Credentials seen before the strip, kept for the header and for attribution.
_STARTUP_CREDENTIALS: tuple[str, ...] = ()


def _record(channel: str, value: Any) -> None:
    entry = _PROVENANCE.setdefault(_CURRENT["nodeid"], {"egress": [], "llm": []})
    entry[channel].append(value)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    _CURRENT["nodeid"] = item.nodeid
    return None


# --------------------------------------------------------------------------
# Isolation
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_ambient_provider_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    if _live_providers_allowed():
        return
    for name in _PROVIDER_CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)


def _is_local(address: Any) -> bool:
    """Loopback, LAN and link-local stay reachable: the bridge tests need them."""
    host = address[0] if isinstance(address, tuple) else str(address)
    if host in ("", "localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified


def _install_egress_guard() -> Any:
    """Refuse non-local connects and record the attempt against the running test.

    Counts are a floor, not a total: HTTP keep-alive lets a second request reuse
    an open socket, so an unguarded run under-reports. Presence, not volume, is
    the signal.
    """
    original = socket.socket.connect
    allow_live = _live_providers_allowed()

    def guarded(self: socket.socket, address: Any) -> Any:
        if self.family != socket.AF_UNIX and not _is_local(address):
            host = str(address[0]) if isinstance(address, tuple) else str(address)
            _record("egress", host)
            if not allow_live:
                raise OSError(
                    f"lumos test provenance: outbound connection to {host} refused. "
                    f"Tests run offline; set {_ALLOW_LIVE_ENV}=1 to allow live providers."
                )
        return original(self, address)

    socket.socket.connect = guarded  # type: ignore[method-assign]
    return original


def _wrap_llm_decision_points() -> None:
    """Record whether each model-gated decision used a real answer or its fallback."""
    import importlib

    for module_name, attr in _LLM_DECISION_POINTS:
        try:
            module = importlib.import_module(module_name)
            original = getattr(module, attr)
        except (ImportError, AttributeError):  # optional package layout
            continue

        def make(func: Any, name: str) -> Any:
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                result = func(*args, **kwargs)
                fell_back = isinstance(result, dict) and "fallback" in result.values()
                _record("llm", (name, "fallback" if fell_back else "model"))
                return result

            return wrapped

        setattr(module, attr, make(original, attr))


def pytest_configure(config: pytest.Config) -> None:
    global _STARTUP_CREDENTIALS
    _STARTUP_CREDENTIALS = _credentials_present()
    config._lumos_egress_original = _install_egress_guard()  # type: ignore[attr-defined]
    _wrap_llm_decision_points()


def pytest_unconfigure(config: pytest.Config) -> None:
    original = getattr(config, "_lumos_egress_original", None)
    if original is not None:
        socket.socket.connect = original  # type: ignore[method-assign]


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _credential_banner() -> list[str]:
    names = ", ".join(_STARTUP_CREDENTIALS)
    if _live_providers_allowed():
        return [
            "",
            "WARNING: External AI provider detected in test environment.",
            f"  Present: {names}",
            f"  {_ALLOW_LIVE_ENV}=1 -- live model calls are ALLOWED.",
            "  This run is NOT deterministic; assertion outcomes may depend on",
            "  a remote model answer. Do not treat a pass or a fail as evidence.",
            "",
        ]
    return [
        "",
        "NOTICE: External AI provider credentials detected in test environment.",
        f"  Present: {names}",
        "  Blocked for this run -- credentials stripped, non-local egress refused.",
        f"  Set {_ALLOW_LIVE_ENV}=1 to allow live provider access on purpose.",
        f"  Model-gated component: {_LLM_DECISION_POINTS[0][1]}()",
        "",
    ]


def pytest_report_header(config: pytest.Config) -> list[str]:
    # Quiet confirmation for a clean environment. The credential banner is not
    # returned here: pytest drops this header under -q, which is exactly the
    # mode the pre-commit hook runs in, so it is written out in sessionstart.
    if _STARTUP_CREDENTIALS:
        return []
    return ["test provenance: isolated (no provider credentials in environment)"]


def pytest_sessionstart(session: pytest.Session) -> None:
    if not _STARTUP_CREDENTIALS:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    for line in _credential_banner():
        reporter.write_line(line)


def _integrity_note(nodeid: str) -> str | None:
    """Text for a failure whose verdict may not be the code's own."""
    entry = _PROVENANCE.get(nodeid) or {"egress": [], "llm": []}
    egress: list[str] = entry["egress"]
    model_calls = [name for name, kind in entry["llm"] if kind == "model"]
    if not egress and not model_calls:
        return None

    lines = [
        "This failure may not be the code's verdict: the test's execution",
        "touched a nondeterministic external dependency.",
        "",
        "Detected:",
    ]
    if model_calls:
        lines.append(
            f"- LLM decision point ran on a real model answer: {', '.join(sorted(set(model_calls)))}"
        )
        lines.append("- A model response can change the assertion outcome")
    for host in sorted(set(egress)):
        verb = "reached" if _live_providers_allowed() else "attempted (refused)"
        lines.append(f"- Outbound connection {verb}: {host}")
    if _live_providers_allowed() and _STARTUP_CREDENTIALS:
        lines.append(
            f"- Provider isolation is OFF ({_ALLOW_LIVE_ENV}=1); "
            f"credentials live in the environment: {', '.join(_STARTUP_CREDENTIALS)}"
        )
    lines += ["", "Action:"]
    if _live_providers_allowed():
        lines += [
            f"- Re-run with provider isolation (unset {_ALLOW_LIVE_ENV}) to get a",
            "  deterministic verdict, then decide whether the failure is real.",
            "- If this test must never consult a model, pin the decision point in",
            "  the test itself so the dependency is explicit rather than ambient.",
        ]
    else:
        lines += [
            "- Isolation was already enforced, so this test reached for a remote",
            "  service it is not allowed to use. Stub that dependency in the test.",
            "- If it is a genuine integration test, mark it @pytest.mark.integration",
            f"  and run it deliberately with {_ALLOW_LIVE_ENV}=1.",
        ]
    return "\n".join(lines)


def pytest_terminal_summary(
    terminalreporter: Any, exitstatus: int, config: pytest.Config
) -> None:
    """A pass earned with outside help is not evidence either -- name those too."""
    touched = {
        nodeid: entry
        for nodeid, entry in _PROVENANCE.items()
        if entry["egress"] or any(kind == "model" for _, kind in entry["llm"])
    }
    if not touched:
        return
    live = _live_providers_allowed()
    terminalreporter.write_sep("-", "test provenance")
    verdict = (
        "verdict depended on a remote answer"
        if live
        else "reached for a remote service and was refused"
    )
    noun = "test" if len(touched) == 1 else "tests"
    terminalreporter.write_line(f"{len(touched)} {noun}: {verdict}")
    for nodeid, entry in sorted(touched.items()):
        marks = sorted({f"model:{n}" for n, kind in entry["llm"] if kind == "model"})
        # DNS round-robin makes one destination look like eight; name a few.
        hosts = sorted(set(entry["egress"]))
        marks += [f"egress:{host}" for host in hosts[:3]]
        if len(hosts) > 3:
            marks.append(f"+{len(hosts) - 3} more hosts")
        terminalreporter.write_line(f"  {nodeid}  [{', '.join(marks)}]")
    if live:
        terminalreporter.write_line(
            f"Unset {_ALLOW_LIVE_ENV} for a deterministic run."
        )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Iterator[pytest.TestReport]:
    report = yield
    if report.failed:
        note = _integrity_note(item.nodeid)
        if note is not None:
            report.sections.append(("TEST INTEGRITY", note))
    return report
