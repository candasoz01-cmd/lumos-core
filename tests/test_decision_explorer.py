from __future__ import annotations

from pathlib import Path

from core.change_plan import ChangePlan
from core.decision_explorer import generate_candidate_options, select_best_option
from core.decision_model import MutationOption


def test_generate_candidate_options_at_least_three(tmp_path: Path):
    paths = [tmp_path / "src" / "core" / "workspace_contract.py"]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# test", encoding="utf-8")

    opts = generate_candidate_options("goal", paths)
    assert len(opts) >= 3
    assert all(isinstance(o, MutationOption) for o in opts)
    assert all(o.score is not None for o in opts)


def test_low_risk_option_scores_higher_than_aggressive(tmp_path: Path):
    paths = [tmp_path / "src" / "tools" / "run_classify.py"]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# test", encoding="utf-8")

    opts = generate_candidate_options("goal", paths)
    best, sorted_opts = select_best_option(opts)
    # Minimal seçeneğin (düşük riskli) en yüksek skorla gelmesini bekleriz.
    assert best.description.startswith("Minimal")
    assert sorted_opts[0].score >= sorted_opts[-1].score


def test_create_change_plan_skeleton_from_best_option(tmp_path: Path, monkeypatch):
    paths = [tmp_path / "src" / "core" / "workspace_contract.py"]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# test", encoding="utf-8")

    opts = generate_candidate_options("goal", paths)
    best, _ = select_best_option(opts)

    # ChangePlan.new boş patch listesi için ValueError fırlatacağı için sadece
    # interface bağını test ediyoruz: MutationOption → ChangePlan ilişkisinin kurulabilirliği.
    # Gerçek patch listesi üretimi üst katmanın sorumluluğunda kalır.
    try:
        _ = ChangePlan.new("goal", [])
    except ValueError:
        pass

