"""Execution dispatch: task_type + doğru executor kuyruğu (karar katmanından ayrı)."""

from pathlib import Path

from kando_runtime.lumos_gate import enrich_normalized_with_target_file
from kando_runtime.task_dispatch import (
    DISPATCH_PENDING_APPROVAL_SCHEMA,
    attach_execution_dispatch_to_out,
    build_dispatch_execution_plan,
    classify_file_shell_dispatch,
    dispatch_task,
    execute_approved_dispatch_pending,
    infer_task_type,
    resolve_task_type,
    validate_dispatch_pending_for_approval,
)


def test_infer_bare_pwd_is_shell():
    assert infer_task_type("pwd") == "shell"
    assert infer_task_type("echo merhaba") == "shell"


def test_dispatch_uses_normalized_task_in_http_body(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "low",
            "normalized_task": {"target_body": "test.txt oluştur"},
        },
    }
    d = dispatch_task({"text": "", "out": out, "repo_root": tmp_path})
    assert d["task_type"] == "file"
    pl = d["dispatch_execution_plan"]
    assert pl["ok"] is True
    assert pl["execution_permitted"] is True
    assert pl["action"] == "file_operation"
    assert pl["executor_type"] == "file_executor"
    assert d["system_execution"]["executed"] is True
    se = d["system_execution"]
    assert "test.txt" in str(se.get("path", ""))
    assert str(se.get("stdout", "")).endswith("test.txt")
    assert (tmp_path / "workspace" / "test.txt").is_file()


def test_infer_video_image_audio_file_shell():
    assert infer_task_type("720p video üret") == "video"
    assert infer_task_type("png logo üret") == "image"
    assert infer_task_type("podcast özeti mp3") == "audio"
    assert infer_task_type("tüm dosyaları sil") == "file"
    assert infer_task_type("test.txt oluştur") == "file"
    assert infer_task_type("komut çalıştır: pwd") == "shell"


def test_resolve_explicit_overrides_text():
    assert resolve_task_type("komut çalıştır: pwd", "file") == "file"
    assert resolve_task_type("test.txt oluştur", "shell") == "shell"


def test_resolve_media_maps_to_subtype():
    assert resolve_task_type("720p klip", "media") == "video"
    assert resolve_task_type("png logo üret", "media") == "image"
    assert resolve_task_type("podcast mp3 kes", "media") == "audio"


def test_resolve_system_ambiguous_text_no_executor():
    """TARGET + shell ipucu çakışınca güvenli neither → generic, system_execution yok."""
    text = "TARGET: x.txt\nkomut çalıştır: pwd"
    assert resolve_task_type(text, "system", {}) == "generic"
    d = dispatch_task(
        {
            "text": text,
            "out": {"execution_mode": "restricted", "http_body": {}},
            "repo_root": None,
        }
    )
    assert d["task_type"] == "generic"
    assert d["dispatch_execution_plan"]["ok"] is False
    assert d["dispatch_execution_plan"]["execution_permitted"] is False
    assert d["dispatch_execution_plan"]["action"] == "none"
    assert "system_execution" not in d


def test_dispatch_generic_plan_no_system_executor(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {"text": "sadece selamlaşma metni", "out": out, "repo_root": tmp_path}
    )
    assert d["task_type"] == "generic"
    assert d["dispatch_execution_plan"]["ok"] is False
    assert d["dispatch_execution_plan"]["execution_permitted"] is False
    assert "system_execution" not in d


def test_dispatch_high_risk_skips_file_executor(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "high",
            "normalized_task": {"target_body": "x.txt oluştur"},
        },
    }
    d = dispatch_task({"text": "", "out": out, "repo_root": tmp_path})
    assert d["task_type"] == "file"
    pl = d["dispatch_execution_plan"]
    assert pl["ok"] is True
    assert pl["execution_permitted"] is False
    assert pl["reason"] == "risk_enforcement"
    se = d["system_execution"]
    assert se["executed"] is False
    assert "Risk enforcement" in se["detail"]
    assert not (tmp_path / "workspace" / "x.txt").is_file()


def test_dispatch_risk_level_blocked_string_skips_executor(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "blocked",
            "normalized_task": {"target_body": "y.txt oluştur"},
        },
    }
    d = dispatch_task({"text": "", "out": out, "repo_root": tmp_path})
    assert d["dispatch_execution_plan"]["execution_permitted"] is False
    assert d["system_execution"]["executed"] is False


def test_dispatch_decision_kind_blocked_skips_executor(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "low",
            "decision_kind": "blocked",
            "normalized_task": {"target_body": "z.txt oluştur"},
        },
    }
    d = dispatch_task({"text": "", "out": out, "repo_root": tmp_path})
    assert d["dispatch_execution_plan"]["execution_permitted"] is False


def test_dispatch_medium_risk_file_no_sync_executor(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "medium",
            "normalized_task": {"target_body": "med.txt oluştur"},
        },
    }
    d = dispatch_task({"text": "", "out": out, "repo_root": tmp_path})
    pl = d["dispatch_execution_plan"]
    assert pl["execution_permitted"] is False
    assert pl["requires_dispatch_approval"] is True
    assert pl["reason"] == "medium_risk_requires_user_approval"
    assert "system_execution" not in d
    assert not (tmp_path / "workspace" / "med.txt").is_file()


def test_dispatch_medium_after_snapshot_approval_runs_executor(tmp_path: Path) -> None:
    hb = {
        "lumos_gate": {"execution_mode": "restricted", "risk_level": "medium"},
        "risk_level": "medium",
        "normalized_task": {"target_body": "apr.txt oluştur"},
    }
    out_med = {"execution_mode": "restricted", "http_body": hb}
    plan = build_dispatch_execution_plan(
        task_type="file",
        text="",
        out=out_med,
        executor="file_executor",
    )
    assert plan["risk"] == "medium"
    assert plan["requires_dispatch_approval"] is True
    loaded = {
        "schema_version": DISPATCH_PENDING_APPROVAL_SCHEMA,
        "policy_ok": True,
        "risk_level": "medium",
        "normalized_task": {"target_body": "apr.txt oluştur"},
        "original_payload": "apr.txt oluştur",
        "dispatch_snapshot": {"text": "", "explicit_task_type": None},
        "gate_http_body_snapshot": hb,
        "original_gate_execution_mode": "restricted",
        "dispatch_execution_plan_snapshot": plan,
        "task_type_snapshot": "file",
        "execution_dispatch_snapshot": {
            "queue": "file_executor_pending",
            "label_tr": "Dosya yürütücüsüne yönlendirildi",
            "executor": "file_executor",
        },
    }
    validate_dispatch_pending_for_approval(loaded)
    d = execute_approved_dispatch_pending(loaded, repo_root=tmp_path)
    assert d["dispatch_execution_plan"]["risk"] == "medium"
    assert d["dispatch_execution_plan"]["execution_permitted"] is True
    assert d["dispatch_execution_plan"]["reason"] == "user_approved"
    assert d["system_execution"]["executed"] is True
    assert (tmp_path / "workspace" / "apr.txt").is_file()


def test_attach_medium_risk_writes_pending_json(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "policy_ok": True,
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "medium",
            "normalized_task": {"target_body": "pend.txt oluştur"},
        },
    }
    attach_execution_dispatch_to_out(out, repo_root=tmp_path)
    assert out["execution_mode"] == "pending_approval"
    pr = out["pending_approval_record"]
    assert isinstance(pr, dict)
    assert pr["schema_version"] == DISPATCH_PENDING_APPROVAL_SCHEMA
    assert pr["task_type_snapshot"] == "file"
    assert isinstance(pr.get("dispatch_execution_plan_snapshot"), dict)
    assert pr["dispatch_execution_plan_snapshot"]["risk"] == "medium"
    rel = str(out.get("approval_file") or "")
    assert rel.startswith(".lumos/pending_approvals/")
    assert (tmp_path / rel).is_file()
    cid = str(pr.get("confirmation_id") or "")
    assert cid
    assert pr.get("confirmation_action_key") == "bridge_medium_dispatch"
    assert (tmp_path / ".lumos" / "pending_confirmations" / f"{cid}.json").is_file()


def test_resolve_system_reasoning_structured_patch_routes_file():
    out = {
        "pending_approval_record": {
            "reasoning_snapshot": {"intent": "structured_patch"},
            "normalized_task": {"mode": "direct_patch", "target_rel": "a.py"},
        }
    }
    assert resolve_task_type("", None, out) == "file"


def test_classify_file_shell_dispatch_plan_patch():
    out = {
        "http_body": {
            "execution_plan": {
                "steps": [{"type": "patch", "file": "z.md", "content": "x"}]
            }
        }
    }
    assert classify_file_shell_dispatch("rastgele", out) == "file"


def test_dispatch_video_queue():
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    # Dış kaynak (URL) olmadan saf üretim metni → need_source; kuyruk için kaynak eklenir
    d = dispatch_task(
        {
            "text": "720p video üret https://youtu.be/abc123",
            "out": out,
            "repo_root": Path("."),
        }
    )
    assert d["task_type"] == "video"
    assert d["dispatch_execution_plan"]["ok"] is True
    assert d["dispatch_execution_plan"]["execution_permitted"] is False
    assert d["dispatch_execution_plan"]["action"] == "media_video"
    assert d["execution_dispatch"]["queue"] == "video_executor_pending"
    assert d["execution_dispatch"]["executor"] == "video_executor"
    assert "system_execution" not in d


def test_dispatch_video_production_intent_bypasses_need_source():
    """video + üretim niyeti (video/üret) → need_source atlanır, kuyruğa gider."""
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {"text": "720p video üret", "out": out, "repo_root": Path(".")}
    )
    assert d["task_type"] == "video"
    assert d.get("status") != "need_source"
    assert d["execution_dispatch"]["queue"] == "video_executor_pending"


def test_dispatch_video_need_input_short_prompt():
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {"text": "kısa klip", "out": out, "repo_root": Path("."), "explicit_task_type": "video"}
    )
    assert d["status"] == "need_input"
    assert d["reason"] == "VIDEO_PROMPT_VAGUE"
    assert d["question"] == "Nasıl bir sahne istiyorsun?"
    assert d["dispatch_execution_plan"]["execution_permitted"] is False


def test_dispatch_video_need_input_vague_only():
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {
            "text": "garip farklı ilginç bilinmeyen şeyler",
            "out": out,
            "repo_root": Path("."),
            "explicit_task_type": "video",
        }
    )
    assert d["status"] == "need_input"
    assert d["reason"] == "VIDEO_PROMPT_VAGUE"


def test_dispatch_need_input_low_clarity_threshold():
    """clarity < 0.4 → LOW_CLARITY (video özel nedeni yoksa)."""
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {
            "text": "x",
            "out": out,
            "repo_root": Path("."),
            "explicit_task_type": "generic",
        }
    )
    assert d["status"] == "need_input"
    assert d["reason"] == "LOW_CLARITY"


def test_attach_execution_dispatch_need_input_on_http_body(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "message": "kısa",
        },
        "_client_task_type": "video",
    }
    attach_execution_dispatch_to_out(out, repo_root=tmp_path)
    hb = out["http_body"]
    assert hb.get("task_type") == "video"
    ni = hb["lumos_dispatch_need_input"]
    assert ni["status"] == "need_input"
    assert ni["reason"] == "VIDEO_PROMPT_VAGUE"
    assert ni["question"] == "Nasıl bir sahne istiyorsun?"


def test_dispatch_file_approval():
    out = {
        "execution_mode": "pending_approval",
        "http_body": {
            "lumos_gate": {"execution_mode": "pending_approval"},
            "risk_level": "low",
            "requires_clarification": False,
        },
    }
    d = dispatch_task({"text": "tüm dosyaları sil", "out": out, "repo_root": Path(".")})
    assert d["task_type"] == "file"
    assert d["dispatch_execution_plan"]["ok"] is True
    assert d["dispatch_execution_plan"]["execution_permitted"] is True
    assert d["execution_dispatch"]["queue"] == "file_approval_pending"
    assert d["execution_dispatch"]["executor"] == "file_executor"
    assert d["system_execution"]["outcome_tr"] == "reddedildi"
    assert d["system_execution"]["executed"] is False


def test_dispatch_shell_executes_whitelisted(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "low",
        },
    }
    d = dispatch_task(
        {"text": "komut çalıştır: echo hi", "out": out, "repo_root": tmp_path}
    )
    assert d["task_type"] == "shell"
    assert d["dispatch_execution_plan"]["ok"] is True
    assert d["dispatch_execution_plan"]["execution_permitted"] is True
    assert d["dispatch_execution_plan"]["action"] == "shell_command"
    assert d["execution_dispatch"]["queue"] == "shell_executor_pending"
    assert d["execution_dispatch"]["executor"] == "shell_executor"
    assert d["system_execution"]["executed"] is True
    assert d["system_execution"]["executor"] == "shell_executor"


def test_enrich_create_intent_skips_file_read(tmp_path: Path) -> None:
    """Yeni dosya oluşturma niyetinde gate hedef dosyayı okumaya çalışmasın."""
    norm = {
        "mode": "direct_patch",
        "target_rel": "yeni.md",
        "target_body": "yeni.md dosyasını oluştur",
    }
    out = enrich_normalized_with_target_file(norm, tmp_path)
    assert out["file_read_status"] == "create_intent"
    assert out["file_content_for_reasoning"] == ""


def test_enrich_create_intent_from_raw_payload_when_body_empty(tmp_path: Path) -> None:
    """Oluşturma fiili yalnızca raw_payload'da olsa bile okuma yapılmasın."""
    norm = {
        "mode": "direct_patch",
        "target_rel": "out.txt",
        "target_body": "",
        "raw_payload": "oluştur",
    }
    out = enrich_normalized_with_target_file(norm, tmp_path)
    assert out["file_read_status"] == "create_intent"


def test_reason_task_bypasses_precheck_for_create_intent(
    tmp_path: Path,
) -> None:
    from kando_runtime import lumos_gate as lg

    norm = {
        "mode": "direct_patch",
        "target_rel": "ghost.txt",
        "target_body": "ghost.txt oluştur",
        "raw_payload": "",
        "agent_blob": "",
    }
    norm = enrich_normalized_with_target_file(norm, tmp_path)
    assert norm["file_read_status"] == "create_intent"
    r = lg.reason_task(norm, tmp_path, payload="")
    assert r.get("intent") != "precheck_file"
    assert r.get("source") != "precheck"


def test_dispatch_explicit_task_type_json_path(tmp_path: Path) -> None:
    out = {
        "execution_mode": "restricted",
        "http_body": {
            "lumos_gate": {"execution_mode": "restricted"},
            "risk_level": "low",
        },
    }
    d = dispatch_task(
        {
            "text": "istediğim metin",
            "out": out,
            "repo_root": tmp_path,
            "explicit_task_type": "shell",
        }
    )
    assert d["task_type"] == "shell"
    assert d["system_execution"]["action"] == "unhandled"


def test_dispatch_content_watch_ready_to_watch():
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {
            "text": "sen seç bir şey izlemek istiyorum",
            "out": out,
            "repo_root": Path("."),
        }
    )
    assert d["status"] == "done"
    assert d["task_type"] == "content.watch"
    assert d["output"]["type"] == "video"
    assert d["output"]["source"] == "youtube"
    assert "youtube.com" in (d["output"].get("url") or "")
    assert d["execution_dispatch"]["executor"] == "content_executor"


def test_dispatch_content_watch_skipped_when_production_keyword():
    out = {
        "execution_mode": "restricted",
        "http_body": {"lumos_gate": {"execution_mode": "restricted"}},
    }
    d = dispatch_task(
        {
            "text": "720p video üret izlemek istiyorum",
            "out": out,
            "repo_root": Path("."),
        }
    )
    assert d["task_type"] == "video"
    assert d["task_type"] != "content.watch"
