"""Assertions for repo search tests when full search runs vs degrade (no repo_search feature signal)."""


def assert_repo_search_output_or_degrade(out: str) -> None:
    o = out.replace("\\", "/")
    lower = out.lower()
    assert (
        "src/" in o
        or "repo arama degrade" in lower
        or "repo arama şu anda devre dışı" in lower
    ), f"unexpected repo output: {out[:300]!r}"
