"""Yayın kapısı regression testleri.

Sızıntı olayının (private karar metinlerinin public .astro sayfalarına
gömülmesi, 2026-07/08) tekrarını iki bağımsız katmanla engelleyen kapının
sözleşmesi. Tüm "özel" içerikler ve anahtarlar sentetiktir; gerçek özel belge
gövdesi bu dosyaya kopyalanmaz.

Onay modeli: düz metin manifest alanları onay DEĞİLDİR — onay, kurucunun
private anahtarıyla üretilen SSH imzasıdır; ajan bu kaydı kendi başına
üretemez. Testler imzayı geçici (sentetik) bir anahtar çiftiyle prova eder.

Bu dosya zorunlu `test` CI check'i içinde koşar; #857'nin
`test_public_pages_no_private_embed.py` testi bağımsız ikinci ağdır.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = REPO_ROOT / "ops" / "publication_gate" / "gate.py"

_spec = importlib.util.spec_from_file_location("publication_gate", GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


# --- sentetik imza altyapısı ------------------------------------------------

@pytest.fixture(scope="session")
def signer(tmp_path_factory):
    """Sentetik 'kurucu' anahtar çifti + allowed_signers satırı."""
    keydir = tmp_path_factory.mktemp("signer")
    key = keydir / "id_test"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                   check=True)
    pub = (keydir / "id_test.pub").read_text().strip()
    key_type, key_blob = pub.split()[0], pub.split()[1]
    return {"key": key, "principal": "kurucu-test",
            "allowed_line": f"kurucu-test {key_type} {key_blob}\n",
            "dir": keydir}


def sign_payload(signer_info: dict, payload: bytes, key: Path | None = None) -> str:
    work = signer_info["dir"] / "payload.bin"
    work.write_bytes(payload)
    sig = work.with_suffix(".bin.sig")
    sig.unlink(missing_ok=True)
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key or signer_info["key"]),
                    "-n", gate.SIGN_NAMESPACE, str(work)],
                   check=True, capture_output=True)
    return sig.read_text()


# --- sentetik içerik üreticileri -------------------------------------------

def synthetic_embedded_body() -> str:
    """Tek satıra kaçışlı \\n ile yazılmış sentetik 'iç belge' gövdesi."""
    chunk = "\\n## Sentetik bölüm\\n\\n| alan | değer |\\n| --- | --- |\\n" + ("x" * 80)
    body = "# Sentetik İç Belge" + chunk * 20
    return f'---\nconst BODY = "{body}";\n---\n<html><body><pre>{{BODY}}</pre></body></html>\n'


def synthetic_fake_secret_line() -> str:
    # Bilinçli sahte: gerçek token değil, yalnız desen eşleşmesi için.
    return 'const t = "ghp_' + "a" * 36 + '";\n'


def make_tree(tmp_path: Path, pages: dict[str, str], signer_info: dict | None = None,
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

    (root / "config" / "publication" / "allowed_signers").write_text(
        signer_info["allowed_line"] if signer_info else "", encoding="utf-8")
    (root / "config" / "publication" / "public_release_manifest.json").write_text(
        json.dumps({"version": 2, "default": "PRIVATE_NOT_APPROVED",
                    "entries": manifest_entries or []}), encoding="utf-8")
    (root / "config" / "publication" / "sensitive_boundary_baseline.json").write_text(
        json.dumps({"version": 2, "entries": baseline_entries or []}), encoding="utf-8")
    return root, cfg_path


def run(root: Path, cfg: Path) -> tuple[int, str]:
    code, lines = gate.run_gate(root, cfg)
    return code, "\n".join(lines)


def signed_entry(root: Path, rel: str, signer_info: dict, layer_id: str,
                 key: Path | None = None) -> dict:
    sha = gate.sha256_of(root / rel)
    date = "2026-09-17"
    payload = gate.signature_payload(layer_id, rel, sha, date)
    return {
        "path": rel,
        "status": "approved",
        "public_release_approved": True,
        "content_sha256": sha,
        "approved_by": signer_info["principal"],
        "approved_date": date,
        "approval_signature": sign_payload(signer_info, payload, key=key),
    }


def write_manifest(root: Path, entries: list[dict]) -> None:
    (root / "config/publication/public_release_manifest.json").write_text(
        json.dumps({"version": 2, "entries": entries}), encoding="utf-8")


def write_baseline(root: Path, entries: list[dict]) -> None:
    (root / "config/publication/sensitive_boundary_baseline.json").write_text(
        json.dumps({"version": 2, "entries": entries}), encoding="utf-8")


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


# --- 3. kurucu imzalı onay geçer --------------------------------------------

def test_signed_approved_content_passes(tmp_path, signer):
    page = "ui/src/pages/onayli.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()}, signer_info=signer)
    write_manifest(root, [signed_entry(root, page, signer, gate.LAYER1_ID)])
    code, out = run(root, cfg)
    assert code == 0, out


# --- 4. imzasız / düz metin "onay" bloklanır (ajan onay üretemez) -----------

def test_plain_metadata_without_signature_is_not_approval(tmp_path, signer):
    page = "ui/src/pages/sahte-onay.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()}, signer_info=signer)
    entry = signed_entry(root, page, signer, gate.LAYER1_ID)
    del entry["approval_signature"]
    write_manifest(root, [entry])
    code, out = run(root, cfg)
    assert code == 1
    assert "approval-signature-invalid" in out


def test_unlisted_signer_cannot_approve(tmp_path, signer):
    # allowed_signers'ta olmayan bir anahtarla (ajanın kendi anahtarı gibi)
    # üretilen imza geçmez.
    rogue = signer["dir"] / "rogue_key"
    if not rogue.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(rogue)],
                       check=True)
    page = "ui/src/pages/korsan.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()}, signer_info=signer)
    write_manifest(root, [signed_entry(root, page, signer, gate.LAYER1_ID, key=rogue)])
    code, out = run(root, cfg)
    assert code == 1
    assert "approval-signature-invalid" in out


def test_pending_or_legacy_status_is_not_approval(tmp_path, signer):
    # "İnceleme bekliyor" türü ara statü yayın izni değildir.
    page = "ui/src/pages/bekleyen.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()}, signer_info=signer)
    entry = signed_entry(root, page, signer, gate.LAYER1_ID)
    entry["status"] = "legacy_baseline_review_required"
    entry["public_release_approved"] = False
    write_manifest(root, [entry])
    code, out = run(root, cfg)
    assert code == 1
    assert "not-approved" in out


# --- 5. "404 düzelt" gibi görev çerçevesi kapıyı etkilemez ------------------

def test_task_framing_is_irrelevant_content_decides(tmp_path):
    root, cfg = make_tree(tmp_path, {"ui/src/pages/404.astro": synthetic_embedded_body()})
    code, out = run(root, cfg)
    assert code == 1
    assert "embedded-document-body" in out

    harmless = "---\n---\n<html><body><h1>404</h1><p>Sayfa bulunamadı.</p></body></html>\n"
    root2, cfg2 = make_tree(tmp_path / "b", {"ui/src/pages/404.astro": harmless})
    code2, _ = run(root2, cfg2)
    assert code2 == 0


# --- 6. "private fetch kaldır" gövde gömmeye dönüşemez; katmanlar bağımsız ---

def test_fetch_removal_cannot_inline_body_and_layers_are_independent(tmp_path, signer):
    content = synthetic_embedded_body().replace(
        "</body>", '<a href="https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md">k</a></body>')
    page = "ui/src/pages/fetchsiz.astro"
    root, cfg = make_tree(tmp_path, {page: content}, signer_info=signer)
    # Katman 1 imzalı onaylansa bile Katman 2 bağımsız durdurur.
    write_manifest(root, [signed_entry(root, page, signer, gate.LAYER1_ID)])
    code, out = run(root, cfg)
    assert code == 1
    assert "2-sensitive-content-boundary" in out
    assert "private-source-reference" in out


def test_layer1_signature_cannot_ack_layer2(tmp_path, signer):
    # Katman imza yükleri ayrıdır: layer1 imzası layer2 baseline'ında geçmez.
    content = ('---\n---\n<a href="https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md">k</a>\n')
    page = "ui/src/pages/capraz.astro"
    root, cfg = make_tree(tmp_path, {page: content}, signer_info=signer)
    cross = signed_entry(root, page, signer, gate.LAYER1_ID)
    write_baseline(root, [cross])
    code, out = run(root, cfg)
    assert code == 1
    assert "private-source-reference" in out

    proper = signed_entry(root, page, signer, gate.LAYER2_ID)
    write_baseline(root, [proper])
    code2, out2 = run(root, cfg)
    assert code2 == 0, out2


# --- 7. public repo üzerindeki draft PR da public yüzeydir -------------------

def test_ci_gate_covers_all_pull_requests_including_drafts():
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "publication-gate:" in ci
    assert "python3 ops/publication_gate/gate.py" in ci
    assert "\n  pull_request:\n" in ci
    assert "types:" not in ci
    gate_job = ci.split("publication-gate:")[1].split("\n  test:")[0]
    assert "if:" not in gate_job
    assert "continue-on-error" not in gate_job


def test_pre_push_hook_runs_gate_before_publish():
    # Push anı = yayın; denetim push'tan önce koşmalı. CI ilk ifşayı geri alamaz.
    hook = REPO_ROOT / ".githooks" / "pre-push"
    text = hook.read_text(encoding="utf-8")
    assert "python3 ops/publication_gate/gate.py" in text
    assert hook.stat().st_mode & 0o111, "pre-push çalıştırılabilir olmalı"
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "core.hooksPath .githooks" in makefile


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


def test_secret_cannot_be_baselined_even_with_signature(tmp_path, signer):
    page = "ui/src/pages/sizinti.astro"
    root, cfg = make_tree(tmp_path, {page: "---\n---\n" + synthetic_fake_secret_line()},
                          signer_info=signer)
    write_baseline(root, [signed_entry(root, page, signer, gate.LAYER2_ID)])
    code, out = run(root, cfg)
    assert code == 1
    assert "secret-material" in out


# --- 10. eski embed davranışı ve hash sürüklenmesi ---------------------------

def test_legacy_embed_refresh_shape_fails(tmp_path):
    # Eski davranışın yapısal kopyası (sentetik metinle): canonical belgeyi
    # kaçışlı gövde olarak .astro içine yazan çıktı bloklanır.
    root, cfg = make_tree(tmp_path, {"ui/src/pages/kararlar.astro": synthetic_embedded_body()})
    code, out = run(root, cfg)
    assert code == 1
    assert "embedded-document-body" in out


def test_layer2_hash_only_without_signature_is_blocked(tmp_path, signer):
    """Regression: matching content_sha256 without a founder signature is not approval."""
    page = "ui/src/pages/ozel-kaynak.astro"
    content = (
        '---\n---\n<html><body>'
        '<a href="https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md">k</a>'
        '</body></html>\n'
    )
    root, cfg = make_tree(tmp_path, {page: content}, signer_info=signer)
    write_baseline(root, [{"path": page, "content_sha256": gate.sha256_of(root / page),
                           "reasons": ["private-source-reference"]}])
    code, out = run(root, cfg)
    assert code == 1
    assert "private-source-reference" in out
    assert "2-sensitive-content-boundary" in out


def test_layer2_private_source_match_is_case_insensitive(tmp_path):
    """GitHub treats owner/repo as case-insensitive; Layer 2 must too."""
    page = "ui/src/pages/kucuk-harf.astro"
    content = (
        '---\n---\n<html><body>'
        '<a href="https://github.com/CANDASOZ01-CMD/lumos/blob/main/docs/x.md">k</a>'
        '</body></html>\n'
    )
    root, cfg = make_tree(tmp_path, {page: content})
    code, out = run(root, cfg)
    assert code == 1
    assert "private-source-reference" in out
    assert "2-sensitive-content-boundary" in out


def test_layer2_does_not_flag_public_lumos_core(tmp_path):
    """Public lumos-core links must not be treated as the private Lumos repo."""
    page = "ui/src/pages/public-core.astro"
    content = (
        '---\n---\n<html><body>'
        '<a href="https://github.com/candasoz01-cmd/lumos-core/blob/main/docs/CONSTITUTION.md">k</a>'
        '</body></html>\n'
    )
    root, cfg = make_tree(tmp_path, {page: content})
    code, out = run(root, cfg)
    assert code == 0, out


def test_signature_is_bound_to_content(tmp_path, signer):
    # İmzalı onaydan sonra tek baytlık değişiklik bile yeniden onay ister.
    page = "ui/src/pages/imzali.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()}, signer_info=signer)
    write_manifest(root, [signed_entry(root, page, signer, gate.LAYER1_ID)])
    assert run(root, cfg)[0] == 0
    target = root / page
    target.write_text(target.read_text() + " ", encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "content-hash-drift" in out or "bayat" in out


def test_registry_entry_for_missing_file_blocks(tmp_path, signer):
    root, cfg = make_tree(tmp_path, {"ui/src/pages/temiz.astro": "---\n---\n<html></html>\n"},
                          signer_info=signer)
    write_manifest(root, [
        {"path": "ui/src/pages/silinmis.astro", "status": "approved",
         "public_release_approved": True, "content_sha256": "0" * 64,
         "approved_by": signer["principal"], "approved_date": "2026-09-17",
         "approval_signature": "yok"}])
    code, out = run(root, cfg)
    assert code == 1
    assert "olmayan dosyayı" in out


# --- güvenlik incelemesi bulgusu (2026-09-18): fail-open tarama boşluğu ------

def test_unknown_extension_is_scanned(tmp_path):
    # Uzantı allowlist'i yok: .log/.csv/.pem/uzantısız dosyalar da taranır.
    marker = "içerik https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md\n"
    for name in ("ui/public/notlar.log", "ui/public/veri.csv", "ui/public/aasa"):
        root, cfg = make_tree(tmp_path / name.replace("/", "_"), {name: marker})
        code, out = run(root, cfg)
        assert code == 1, name
        assert "private-source-reference" in out, name


def test_secret_in_unlisted_extension_blocked(tmp_path):
    root, cfg = make_tree(tmp_path, {"ui/public/yedek.pem": synthetic_fake_secret_line()})
    code, out = run(root, cfg)
    assert code == 1
    assert "secret-material" in out


def test_utf16_content_is_scanned(tmp_path):
    # UTF-16 kaydedilmiş dosya sessizce atlanmaz; çözülür ve taranır.
    marker = "belge https://github.com/candasoz01-cmd/Lumos/blob/main/docs/x.md\n"
    root, cfg = make_tree(tmp_path, {"ui/public/dummy.txt": "temiz\n"})
    (root / "ui/public/gizli.txt").write_bytes(marker.encode("utf-16"))
    code, out = run(root, cfg)
    assert code == 1
    assert "private-source-reference" in out and "gizli.txt" in out


def test_undecodable_file_is_a_finding_not_a_pass(tmp_path, signer):
    root, cfg = make_tree(tmp_path, {"ui/public/temiz.txt": "temiz\n"}, signer_info=signer)
    target = root / "ui/public/veri.bin"
    target.write_bytes(bytes([0, 159, 146, 150, 255, 254, 1]) * 40)
    code, out = run(root, cfg)
    assert code == 1
    assert "unscannable-file" in out

    entry = signed_entry(root, "ui/public/veri.bin", signer, gate.LAYER2_ID)
    write_baseline(root, [entry])
    code2, out2 = run(root, cfg)
    assert code2 == 0, out2


def test_binary_media_is_exempt(tmp_path):
    root, cfg = make_tree(tmp_path, {"ui/public/temiz.txt": "temiz\n"})
    (root / "ui/public/logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(64))
    code, out = run(root, cfg)
    assert code == 0, out


# --- kapalı varsayılan: güvenilir onay altyapısı kurulana kadar ret ----------

REVOKED_PUBKEY_LINE = (
    "kurucu ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAIH9upa6ZCJRPBJuxG4XrJAoj5bxaHGS68gOTFrIOC1Fq\n"
)


def test_revoked_key_cannot_be_reenrolled(tmp_path):
    # Ajan-erişilebilir bulunan anahtarın allowed_signers'a geri yazılması,
    # hiçbir kayıt olmasa bile kapıyı kırmızıya çevirir.
    root, cfg = make_tree(tmp_path, {"ui/src/pages/temiz.astro": "---\n---\n<html></html>\n"})
    (root / "config/publication/allowed_signers").write_text(
        REVOKED_PUBKEY_LINE, encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "iptal edilmiş imza anahtarı" in out


def test_no_enrolled_signer_rejects_every_approval(tmp_path, signer):
    # Kayıtlı kök yokken tam doldurulmuş, imzalı bir kayıt bile geçmez.
    page = "ui/src/pages/onaysiz.astro"
    root, cfg = make_tree(tmp_path, {page: synthetic_embedded_body()}, signer_info=signer)
    write_manifest(root, [signed_entry(root, page, signer, gate.LAYER1_ID)])
    (root / "config/publication/allowed_signers").write_text(
        "# kayitli kok yok\n", encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "approval-signature-invalid" in out


def test_real_repo_closed_default_no_enrolled_signer():
    # 2026-09-18 kapalı varsayılan: gerçek allowed_signers'ta kayıtlı kök yok.
    # Kurucu insan-kapılı yeni kökü kaydederken bu assertion'ı bilinçli olarak
    # güncelller; ajan güncellerse bu bir kapsam ihlalidir.
    signers = REPO_ROOT / "config" / "publication" / "allowed_signers"
    assert gate.enrolled_signer_lines(signers) == []


def test_options_field_cannot_hide_revoked_key(tmp_path, signer):
    # Delta güvenlik bulgusu (2026-09-18): options alanı (namespaces=...) +
    # dolgu satırı kombinasyonu iptal anahtarını parser'dan gizleyebiliyordu.
    revoked_blob = REVOKED_PUBKEY_LINE.split()[2]
    content = (
        signer["allowed_line"]
        + f'kurucu namespaces="lumos-publication" ssh-ed25519 {revoked_blob}\n'
    )
    root, cfg = make_tree(tmp_path, {"ui/src/pages/temiz.astro": "---\n---\n<html></html>\n"})
    (root / "config/publication/allowed_signers").write_text(content, encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "iptal edilmiş imza anahtarı" in out


def test_unparseable_signer_line_blocks(tmp_path, signer):
    # Çözümlenemeyen kayıt satırı sessizce atlanmaz; bulgudur.
    content = signer["allowed_line"] + "kurucu bozuk-veri daha-bozuk-veri\n"
    root, cfg = make_tree(tmp_path, {"ui/src/pages/temiz.astro": "---\n---\n<html></html>\n"})
    (root / "config/publication/allowed_signers").write_text(content, encoding="utf-8")
    code, out = run(root, cfg)
    assert code == 1
    assert "anahtar çözümlenemedi" in out


def test_revoked_fingerprint_pinned_in_gate():
    assert "SHA256:fCmMHAEP2k865znMPpzZdBZEdEVSLQVST9WT/hHhNHc" in (
        gate.REVOKED_SIGNER_FINGERPRINTS)


# --- gerçek repo: kapı yeşil, sızıntı geri gelmedi ---------------------------

def test_real_repo_passes_gate():
    code, lines = gate.run_gate(REPO_ROOT, gate.DEFAULT_CONFIG)
    assert code == 0, "\n".join(lines)


def test_kararlar_page_has_no_embedded_body():
    text = (REPO_ROOT / "ui" / "src" / "pages" / "kararlar.astro").read_text(encoding="utf-8")
    assert "const BODY" not in text
    assert gate.detect_embedded_document_body(
        text, {"min_embedded_chars": 1500}) == []
