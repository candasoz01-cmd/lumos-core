"""Adversarial fixture — MUST NOT BE MERGED.

Exists only so this pull request touches a hard-excluded path
(``src/security/``). Paired with a tampered ``standing-class.yml`` that
would trivially report success if the orchestrator came from the pull
request. If the trust root works, the base branch workflow runs instead,
classifies this path, and the CheckRun goes red.
"""
