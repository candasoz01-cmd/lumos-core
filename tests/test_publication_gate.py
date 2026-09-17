"""Yayın kapısı regression testleri.

Sızıntı olayının (private karar metinlerinin public .astro sayfalarına
gömülmesi, 2026-07/08) tekrarını iki bağımsız katmanla engelleyen kapının
sözleşmesi. Tüm "özel" içerikler sentetiktir; gerçek özel belge gövdesi bu
dosyaya kopyalanmaz.

Bu test dosyası zorunlu `test` CI check'i içinde koşar: kapı gevşetilirse veya
public yüzeye kapısız gömülü belge girerse buradaki gerçek-repo taraması da
kırmızıya döner.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = REPO_ROOT / "ops" / "publication_gate" / "gate.py"

_spec = importlib.util.spec_from_file_location("publication_gate", GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


# --- sentetik içerik üreticileri -------------------------------------------

def synthetic_embedded_body() -> str:
    """Tek satıra kaçışlı \\n ile yazılmış sentetik 'iç belge' gövdesi."""
    chunk = "\\n## Sentetik bölüm\\n\\n| alan | değer |\\n| --- | --- |\\n" + ("x" * 80)
    body = "# Sentetik İç Belge" + chunk * 20
    return f'---\nconst BODY = "{body}";\n---\n<html><body><pre>{{BODY}}</pre></body></html>\n'


def synthetic_fake_secret_line() -> str:
    # Bilinçli sahte: gerçek token değil, yalnız desen eşleşmesi için.
    return 'const t = "ghp_' + "a" * 36 + '";\n'


def make_tree(tmp_path: Path, pages: dict[str, str],
              manifest_entries: list[dict] | None = None,
              baseline_entries: list[dict] | None = None) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "ui" / "src" / "pages").mkdir(parents=True)
    (root / "config" / "publication").mkdir(parents=True)
    for rel, content in pages.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    real_cfg = json.loads((REPO_ROOT / "config" / "publication" / "gate_config.json").read_text())
    cfg_path = root / "config" / "publication" / "gate_config.json"
    cfg_path.write_text(json.dumps(real_cfg), encoding="utf-8")

    (root / "config" / "publication" / "public_release_manifest.json").write_text(
        json.dumps({"version": 1, "default": "PRIVATE_NOT_APPROVED",
                    "entries": manifest_entries or []}), encoding="utf-8")
    (root / "config" / "publication" / "sensitive_boundary_baseline.json").write_text(
        json.dumps({"version": 1, "entries": baseline_entries or []}), encoding="utf-8")
    return root, cfg_path


def run(root: Path, cfg: Path) -> tuple[int, str]:
    code, lines = gate.run_gate(root, cfg)
    return code, "\n".join(lines)


def approved_entry(root: Path, rel: str) -> dict:
    return {
        "path": rel,
        "status": "approved",
        "public_release_approved": True,
        "content_sha256": gate.sha256_of(root / rel),
        "approved_by": "kurucu",
        "approved_date": "2026-09-17",
    }


# --- 1. private markdown → public astro embed bloklanır --------------------

def test_embedded_private_body_blocked(tmp_path):
    root, cfg = make_tree(tmp_path, {"ui/src/pages/deneme.astro": synthetic_embedded_body()})
    code, out = run(root, cfg)
    assert code == 1
    assert "embedded-document-body" in out
    assert gate.BLOCK_PREFIX in out


# --- 2. preview yüzeyi fail-closed: Vercel build kapıdan geçer -------------

def test_vercel_preview_build_runs_gate_first():
    vercel = json.loads((REPO_ROOT / "vercel.json").read_text())
    build = vercel["buildCommand"]
    assert build.startswith("python3 ops/publication_gate/gate.py && "), (
        "Vercel build (preview dahil) kapıyı ilk adım olarak koşmalı")
    assert "||" not in build and ";" not in build


# --- 3. açıkça onaylı içerik geçer ------------------------------------------

def test_approved_content_passes(tmp_path):
    page = "ui/src/pages/onayli.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()})
    entry = approved_entry(root, page)
    (root / "config/publication/public_release_manifest.json").write_text(
        json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 0, out


# --- 4. metadata'sız içerik bloklanır ---------------------------------------

def test_missing_approval_metadata_blocked(tmp_path):
    page = "ui/src/pages/eksik.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()})
    entry = approved_entry(root, page)
    entry["approved_by"] = None
    (root / "config/publication/public_release_manifest.json").write_text(
        json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "approval-metadata-incomplete" in out


def test_unknown_status_blocked(tmp_path):
    page = "ui/src/pages/garip.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()})
    entry = approved_entry(root, page)
    entry["status"] = "probably-fine"
    (root / "config/publication/public_release_manifest.json").write_text(
        json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "unknown-status" in out


# --- 5. "404 düzelt" gibi görev çerçevesi kapıyı etkilemez ------------------

def test_task_framing_is_irrelevant_content_decides(tmp_path):
    # Dosya adı/görev bağlamı ne olursa olsun (404 sayfası dahil) içerik esastır.
    root, cfg = make_tree(tmp_path, {"ui/src/pages/404.astro": synthetic_embedded_body()})
    code, out = run(root, cfg)
    assert code == 1
    assert "embedded-document-body" in out

    harmless = "---\n---\n<html><body><h1>404</h1><p>Sayfa bulunamadı.</p></body></html>\n"
    root2, cfg2 = make_tree(tmp_path / "b", {"ui/src/pages/404.astro": harmless})
    code2, _ = run(root2, cfg2)
    assert code2 == 0


# --- 6. "private fetch kaldır" gövde gömmeye dönüşemez; katmanlar bağımsız ---

def test_fetch_removal_cannot_inline_body_and_layers_are_independent(tmp_path):
    # fetch yok ama gövde gömülü + private repo referansı var.
    content = synthetic_embedded_body().replace(
        "</body>", '<a href="https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md">k</a></body>')
    page = "ui/src/pages/fetchsiz.astro"
    root, cfg = make_tree(tmp_path, {page: content})
    # Katman 1 onaylansa bile Katman 2 bağımsız durdurur.
    entry = approved_entry(root, page)
    (root / "config/publication/public_release_manifest.json").write_text(
        json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "2-sensitive-content-boundary" in out
    assert "private-source-reference" in out


# --- 7. public repo üzerindeki draft PR da public yüzeydir -------------------

def test_ci_gate_covers_all_pull_requests_including_drafts():
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "publication-gate:" in ci
    assert "python3 ops/publication_gate/gate.py" in ci
    # `pull_request:` tetikleyicisi daraltılmamış: draft'ları dışlayan types
    # filtresi veya paths filtresi yok.
    assert "\n  pull_request:\n" in ci
    assert "types:" not in ci
    gate_job = ci.split("publication-gate:")[1].split("\n  test:")[0]
    assert "if:" not in gate_job
    assert "continue-on-error" not in gate_job


# --- 8. PAT/token sahibi olmak kapıyı geçirmez ------------------------------

def test_env_and_tokens_cannot_bypass_gate(tmp_path, monkeypatch):
    for var, val in {
        "PUBLICATION_GATE_SKIP": "1", "FORCE": "1", "CI": "true",
        "GITHUB_TOKEN": "x", "WELOCKAI_CORE_TOKEN": "x", "VERCEL": "1",
    }.items():
        monkeypatch.setenv(var, val)
    root, cfg = make_tree(tmp_path, {"ui/src/pages/pat.astro": synthetic_embedded_body()})
    code, _ = run(root, cfg)
    assert code == 1
    source = GATE_PATH.read_text(encoding="utf-8")
    assert "environ" not in source and "getenv" not in source, (
        "gate.py ortam değişkeni okumamalı — env tabanlı bypass kapısı açılmış")


# --- 9. --force / kolay bypass yolu yoktur ----------------------------------

def test_no_force_flag_or_skip_paths():
    with pytest.raises(SystemExit) as exc:
        gate.main(["--force"])
    assert exc.value.code == 2
    source = GATE_PATH.read_text(encoding="utf-8")
    for banned in ("--force", "--skip", "--no-verify", "allow_failure"):
        assert banned not in source


def test_secret_cannot_be_baselined(tmp_path):
    page = "ui/src/pages/sizinti.astro"
    root, cfg = make_tree(tmp_path, {page: "---\n---\n" + synthetic_fake_secret_line()})
    baseline = [{"path": page, "content_sha256": gate.sha256_of(root / page),
                 "reasons": ["secret-material"]}]
    (root / "config/publication/sensitive_boundary_baseline.json").write_text(
        json.dumps({"version": 1, "entries": baseline}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "secret-material" in out


# --- 10. eski EMBED_REFRESH davranışı ve hash sürüklenmesi -------------------

def test_legacy_embed_refresh_shape_fails(tmp_path):
    # Eski davranışın yapısal kopyası (sentetik metinle): canonical belgeyi
    # kaçışlı gövde olarak .astro içine yazan çıktı bloklanır.
    root, cfg = make_tree(tmp_path, {"ui/src/pages/kararlar.astro": synthetic_embedded_body()})
    code, out = run(root, cfg)
    assert code == 1
    assert "embedded-document-body" in out


def test_legacy_status_does_not_pass_unapproved_content(tmp_path):
    """Regression: matching hash + legacy_baseline_review_required is not approval."""
    page = "ui/src/pages/eski.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()})
    entry = {"path": page, "status": "legacy_baseline_review_required",
             "public_release_approved": False,
             "content_sha256": gate.sha256_of(root / page)}
    manifest = root / "config/publication/public_release_manifest.json"
    manifest.write_text(json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "legacy-unapproved" in out
    assert gate.BLOCK_PREFIX in out


def test_legacy_baseline_blocks_on_any_content_change(tmp_path):
    page = "ui/src/pages/eski.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()})
    entry = {"path": page, "status": "legacy_baseline_review_required",
             "public_release_approved": False,
             "content_sha256": gate.sha256_of(root / page)}
    manifest = root / "config/publication/public_release_manifest.json"
    manifest.write_text(json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
    # Tek baytlık değişiklik hash sürüklenmesi olarak da durur.
    target = root / page
    target.write_text(target.read_text() + " ", encoding="utf-8")
    code2, out2 = run(root, cfg)
    assert code2 == 1
    assert "content-hash-drift" in out2 or "bayat" in out2


def test_layer2_hash_match_without_second_approval_is_blocked(tmp_path):
    """Regression: Katman 2 salt content_sha256 eşleşmesini yeterli saymaz."""
    page = "ui/src/pages/ozel-kaynak.astro"
    content = (
        '---\n---\n<html><body>'
        '<a href="https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md">k</a>'
        '</body></html>\n'
    )
    root, cfg = make_tree(tmp_path, {page: content})
    baseline = [{"path": page, "content_sha256": gate.sha256_of(root / page),
                 "reasons": ["private-source-reference"]}]
    (root / "config/publication/sensitive_boundary_baseline.json").write_text(
        json.dumps({"version": 1, "entries": baseline}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "baseline-approval-incomplete" in out
    assert "2-sensitive-content-boundary" in out


def test_layer2_second_approval_with_matching_hash_passes(tmp_path):
    page = "ui/src/pages/onayli-sinir.astro"
    content = (
        '---\n---\n<html><body>'
        '<a href="https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md">k</a>'
        '</body></html>\n'
    )
    root, cfg = make_tree(tmp_path, {page: content})
    baseline = [{
        "path": page,
        "content_sha256": gate.sha256_of(root / page),
        "reasons": ["private-source-reference"],
        "boundary_review_approved": True,
        "approved_by": "kurucu",
        "approved_date": "2026-09-17",
    }]
    (root / "config/publication/sensitive_boundary_baseline.json").write_text(
        json.dumps({"version": 1, "entries": baseline}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 0, out


def test_registry_entry_for_missing_file_blocks(tmp_path):
    root, cfg = make_tree(tmp_path, {"ui/src/pages/temiz.astro": "---\n---\n<html></html>\n"})
    manifest = root / "config/publication/public_release_manifest.json"
    manifest.write_text(json.dumps({"version": 1, "entries": [
        {"path": "ui/src/pages/silinmis.astro", "status": "approved",
         "public_release_approved": True, "content_sha256": "0" * 64,
         "approved_by": "kurucu", "approved_date": "2026-09-17"}]}), encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "olmayan dosyayı" in out


# --- gerçek repo: kapı yeşil, sızıntı geri gelmedi ---------------------------

def test_real_repo_passes_gate():
    code, lines = gate.run_gate(REPO_ROOT, gate.DEFAULT_CONFIG)
    assert code == 0, "\n".join(lines)


def test_kararlar_page_has_no_embedded_body():
    text = (REPO_ROOT / "ui" / "src" / "pages" / "kararlar.astro").read_text(encoding="utf-8")
    assert "const BODY" not in text
    assert gate.detect_embedded_document_body(
        text, {"min_embedded_chars": 1500}) == []
