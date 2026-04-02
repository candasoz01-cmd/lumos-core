"""kando.agent_runner: hedef seçimi ve güvenlik."""
import json

from kando.agent_runner import (
    EXECUTION_RESULT_PATCH_TRIPLET,
    MAX_CANDIDATE_FILES,
    _copy_cursor_bridge_snapshots_to_outbox,
    _cursor_bridge_source_dir,
    _is_risky_goal,
    _list_src_core_py_files,
    select_target_and_task,
)


def test_is_risky_goal():
    assert _is_risky_goal("please rm -rf /") is not None
    assert _is_risky_goal("fix imports in runtime_state") is None


def test_select_target_prefers_scored_file(tmp_path):
    root = tmp_path
    (root / "src" / "core").mkdir(parents=True)
    a = root / "src" / "core" / "aaa.py"
    b = root / "src" / "core" / "bbb.py"
    a.write_text("# aaa\n", encoding="utf-8")
    b.write_text("# runtime_state duplicateword duplicateword duplicateword\n", encoding="utf-8")
    rel, task, meta = select_target_and_task("duplicateword düzelt", root)
    assert rel == "src/core/bbb.py"
    assert "duplicateword" in task
    assert meta.get("top_scores")


def test_list_src_core_respects_limit(tmp_path):
    (tmp_path / "src" / "core").mkdir(parents=True)
    for i in range(5):
        (tmp_path / "src" / "core" / f"f{i}.py").write_text("x\n", encoding="utf-8")
    files = _list_src_core_py_files(tmp_path, limit_scan=3)
    assert len(files) == 3


def test_max_candidate_constant():
    assert MAX_CANDIDATE_FILES == 2


def test_execution_result_patch_triplet_documents_api_assert():
    assert EXECUTION_RESULT_PATCH_TRIPLET == ("patch_applied", "no_change", "blocked")
    assert "patch_applied" in EXECUTION_RESULT_PATCH_TRIPLET


def test_cursor_bridge_source_dir_respects_lumos_env(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    lumos = root / ".lumos"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos.resolve()))
    assert _cursor_bridge_source_dir(root) == (lumos / "cursor_bridge").resolve()


def test_cursor_bridge_source_dir_fallback_when_env_missing(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.delenv("LUMOS_BASE_DIR", raising=False)
    assert _cursor_bridge_source_dir(root) == (root / ".lumos" / "cursor_bridge").resolve()


def test_copy_cursor_bridge_snapshots_byte_identical_with_history(monkeypatch, tmp_path):
    """Outbox last_execution.json = bridge dosyasının aynı baytları (history/audit_id_chain kaybolmaz)."""
    root = tmp_path / "repo"
    lumos = root / ".lumos"
    bridge = lumos / "cursor_bridge"
    bridge.mkdir(parents=True)
    nested = {
        "schema_version": "kando.cursor.execution.v1",
        "constraints": {
            "execution": {
                "execution_result": "patch_applied",
                "detail": "x",
                "history": [
                    {"execution_result": "patch_applied", "audit_id": "run1"},
                    {"execution_result": "patch_applied", "audit_id": "run2"},
                ],
                "audit_id_chain": ["run1", "run2"],
            }
        },
    }
    raw_exec = json.dumps(nested, ensure_ascii=False, indent=2).encode("utf-8")
    (bridge / "last_execution.json").write_bytes(raw_exec)
    (bridge / "last_result.json").write_bytes(b"{}\n")
    outbox = tmp_path / "outbox"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos.resolve()))
    _copy_cursor_bridge_snapshots_to_outbox(root, outbox)
    assert (outbox / "last_execution.json").read_bytes() == raw_exec
    roundtrip = json.loads((outbox / "last_execution.json").read_text(encoding="utf-8"))
    ex = roundtrip["constraints"]["execution"]
    assert len(ex["history"]) == 2
    assert ex["audit_id_chain"] == ["run1", "run2"]


def test_copy_cursor_bridge_second_write_updates_outbox(monkeypatch, tmp_path):
    """İkinci bridge yazımı outbox'ı günceller (zincir büyür)."""
    root = tmp_path / "repo"
    lumos = root / ".lumos"
    bridge = lumos / "cursor_bridge"
    bridge.mkdir(parents=True)
    (bridge / "last_result.json").write_bytes(b"{}\n")
    outbox = tmp_path / "outbox"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(lumos.resolve()))

    for i in range(2):
        nested = {
            "constraints": {
                "execution": {
                    "execution_result": "patch_applied",
                    "history": [{"audit_id": f"id{j}"} for j in range(i + 1)],
                    "audit_id_chain": [f"id{j}" for j in range(i + 1)],
                }
            }
        }
        raw = json.dumps(nested, ensure_ascii=False, indent=2).encode("utf-8")
        (bridge / "last_execution.json").write_bytes(raw)
        _copy_cursor_bridge_snapshots_to_outbox(root, outbox)
        got = json.loads((outbox / "last_execution.json").read_text(encoding="utf-8"))
        assert len(got["constraints"]["execution"]["history"]) == i + 1
        assert len(got["constraints"]["execution"]["audit_id_chain"]) == i + 1
