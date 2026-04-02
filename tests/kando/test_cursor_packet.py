from kando.cursor_packet import EXECUTION_TO_OUTCOME, map_execution_to_outcome


def test_map_execution_to_outcome_known():
    assert map_execution_to_outcome("patch_applied") == "applied"
    assert map_execution_to_outcome("no_change") == "applied"
    assert map_execution_to_outcome("blocked") == "blocked"
    assert map_execution_to_outcome("patch_failed") == "failed"
    assert map_execution_to_outcome("error") == "failed"


def test_map_execution_to_outcome_unknown():
    assert map_execution_to_outcome("pending_approval") == "unknown"
    assert map_execution_to_outcome("") == "unknown"


def test_execution_to_outcome_keys_match_map():
    assert set(EXECUTION_TO_OUTCOME) == {
        "patch_applied",
        "no_change",
        "blocked",
        "patch_failed",
        "error",
    }
