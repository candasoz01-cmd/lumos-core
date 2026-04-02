from kando.cursor_packet import (
    EXECUTION_TO_OUTCOME,
    map_execution_to_outcome,
    packet_outcome_from_execution_result,
)


def test_map_execution_to_outcome_known():
    assert map_execution_to_outcome("patch_applied") == "applied"
    assert map_execution_to_outcome("no_change") == "applied"
    assert map_execution_to_outcome("approved_and_executed") == "applied"
    assert map_execution_to_outcome("blocked") == "blocked"
    assert map_execution_to_outcome("locked") == "blocked"
    assert map_execution_to_outcome("blocked_by_rollback") == "blocked"
    assert map_execution_to_outcome("blocked_repeated_failure") == "blocked"
    assert map_execution_to_outcome("target_required") == "blocked"
    assert map_execution_to_outcome("patch_failed") == "failed"
    assert map_execution_to_outcome("write_failed") == "failed"
    assert map_execution_to_outcome("parse_error") == "failed"
    assert map_execution_to_outcome("error") == "failed"


def test_map_execution_to_outcome_unknown():
    assert map_execution_to_outcome("pending_approval") == "unknown"
    assert map_execution_to_outcome("history_listed") == "unknown"
    assert map_execution_to_outcome("partial") == "unknown"
    assert map_execution_to_outcome("dry_run_success") == "unknown"
    assert map_execution_to_outcome("") == "unknown"


def test_packet_outcome_from_execution_result_coerces_unknown():
    assert packet_outcome_from_execution_result("patch_applied") == "applied"
    assert packet_outcome_from_execution_result("pending_approval") == "failed"
    assert packet_outcome_from_execution_result("parse_error") == "failed"
    assert packet_outcome_from_execution_result(None) == "failed"


def test_execution_to_outcome_keys_match_map():
    assert set(EXECUTION_TO_OUTCOME) == {
        "patch_applied",
        "no_change",
        "approved_and_executed",
        "blocked",
        "locked",
        "blocked_by_rollback",
        "blocked_repeated_failure",
        "target_required",
        "patch_failed",
        "write_failed",
        "parse_error",
        "error",
    }
