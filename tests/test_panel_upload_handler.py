"""PANEL-UPLOAD-HANDLER-01: /panel/upload v1 (attach) sözleşme kanıtları."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (_REPO_ROOT / "src", _REPO_ROOT / "packages" / "kando_bridge" / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from kando_bridge.panel_upload import (  # noqa: E402
    handle_panel_upload_request,
    sanitize_filename,
    upload_max_bytes,
    uploads_dir,
)

_BOUNDARY = "----lumostest"
_CT = f"multipart/form-data; boundary={_BOUNDARY}"


def _multipart(filename: str, data: bytes, field: str = "file") -> bytes:
    head = (
        f"--{_BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    return head + data + f"\r\n--{_BOUNDARY}--\r\n".encode()


def _post(repo: Path, filename: str, data: bytes, **kw):
    return handle_panel_upload_request(
        kw.pop("content_type", _CT), _multipart(filename, data, kw.pop("field", "file")),
        repo_root=repo, **kw
    )


def _stored_files(repo: Path) -> list[Path]:
    base = repo / "workspace" / "uploads"
    return sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []


# --- 2) mutlu yol ---


def test_valid_text_upload_is_stored_in_sandbox(tmp_path: Path) -> None:
    status, body = _post(tmp_path, "notlar.txt", b"merhaba lumos")

    assert status == 200
    assert body["ok"] is True and body["duplicate"] is False
    meta = body["file"]
    assert meta["name"] == "notlar.txt"
    assert meta["size"] == len(b"merhaba lumos")
    assert meta["mime"] == "text/plain"
    assert meta["sha256"] == hashlib.sha256(b"merhaba lumos").hexdigest()
    # Sandbox sink'i: workspace/uploads altında, repo-göreli yol
    assert meta["sandbox_path"].startswith("workspace/uploads/")
    assert not Path(meta["sandbox_path"]).is_absolute()
    files = _stored_files(tmp_path)
    assert len(files) == 1 and files[0].read_bytes() == b"merhaba lumos"


def test_upload_never_writes_outside_workspace(tmp_path: Path) -> None:
    _post(tmp_path, "x.txt", b"veri")
    # .lumos çekirdeği ve repo kökü kirlenmemeli
    assert not (tmp_path / ".lumos").exists()
    for item in tmp_path.iterdir():
        assert item.name == "workspace", f"beklenmeyen yazım: {item.name}"


# --- 3) boyut sınırı ---


def test_oversized_payload_is_rejected_without_partial_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_PANEL_UPLOAD_MAX_BYTES", "64")
    status, body = _post(tmp_path, "buyuk.txt", b"x" * 200)

    assert status == 413
    assert body["error"] == "file_too_large" and body["limit_bytes"] == 64
    assert _stored_files(tmp_path) == []  # kısmi dosya kalmaz


def test_declared_content_length_short_circuits_before_parsing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_PANEL_UPLOAD_MAX_BYTES", "32")
    status, body = _post(tmp_path, "a.txt", b"kucuk", content_length=10_000)
    assert status == 413 and _stored_files(tmp_path) == []


# --- 4/5) MIME allowlist + magic byte ---


def test_disallowed_extension_is_rejected(tmp_path: Path) -> None:
    status, body = _post(tmp_path, "kotu.exe", b"MZ\x90\x00")
    assert status == 415
    assert body["error"] == "unsupported_media_type"
    assert _stored_files(tmp_path) == []


def test_extension_lying_about_content_is_rejected(tmp_path: Path) -> None:
    # .png uzantısı ama içerik PNG değil → magic byte doğrulaması yakalar
    status, body = _post(tmp_path, "sahte.png", b"bu bir png degil")
    assert status == 415
    assert _stored_files(tmp_path) == []


def test_real_png_magic_bytes_pass(tmp_path: Path) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    status, body = _post(tmp_path, "gercek.png", png)
    assert status == 200 and body["file"]["mime"] == "image/png"


# --- 6) path traversal ---


@pytest.mark.parametrize(
    "raw,expected_absent",
    [("../../etc/passwd", ".."), ("/mutlak/yol.txt", "/"), ("a\x00b.txt", "\x00")],
)
def test_filename_sanitization(raw: str, expected_absent: str) -> None:
    safe = sanitize_filename(raw)
    assert expected_absent not in safe
    assert safe and not safe.startswith(".")


def test_traversal_filename_stays_inside_sandbox(tmp_path: Path) -> None:
    status, body = _post(tmp_path, "../../../escape.txt", b"veri")
    assert status == 200
    target = tmp_path / body["file"]["sandbox_path"]
    assert target.resolve().is_relative_to((tmp_path / "workspace").resolve())


# --- 10) SHA-256 duplicate: fiziksel kopya yok ---


def test_same_sha256_returns_existing_record_without_duplicate_file(tmp_path: Path) -> None:
    data = b"ayni icerik"
    first_status, first = _post(tmp_path, "bir.txt", data)
    second_status, second = _post(tmp_path, "iki.txt", data)

    assert first_status == 200 and first["duplicate"] is False
    assert second_status == 200 and second["duplicate"] is True
    assert second["file"]["sha256"] == first["file"]["sha256"]
    assert second["file"]["stored_as"] == first["file"]["stored_as"]
    assert len(_stored_files(tmp_path)) == 1  # fiziksel kopya oluşmaz


def test_different_content_creates_separate_files(tmp_path: Path) -> None:
    _post(tmp_path, "a.txt", b"birinci")
    _post(tmp_path, "b.txt", b"ikinci")
    assert len(_stored_files(tmp_path)) == 2


# --- 11) bozuk istek ---


def test_missing_file_field_is_rejected(tmp_path: Path) -> None:
    status, body = _post(tmp_path, "a.txt", b"veri", field="baska")
    assert status == 400 and body["error"] == "file_required"


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    status, body = _post(tmp_path, "bos.txt", b"")
    assert status == 400 and body["error"] == "empty_file"
    assert _stored_files(tmp_path) == []


def test_non_multipart_content_type_is_rejected(tmp_path: Path) -> None:
    status, body = handle_panel_upload_request(
        "application/json", b'{"file":"x"}', repo_root=tmp_path
    )
    assert status == 400 and body["error"] == "invalid_multipart"


# --- kapatma anahtarı ---


def test_upload_can_be_disabled_by_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LUMOS_PANEL_UPLOAD_ENABLED", "0")
    status, body = _post(tmp_path, "a.txt", b"veri")
    assert status == 403 and body["error"] == "upload_disabled"
    assert _stored_files(tmp_path) == []


def test_default_limit_is_ten_megabytes(monkeypatch) -> None:
    monkeypatch.delenv("LUMOS_PANEL_UPLOAD_MAX_BYTES", raising=False)
    assert upload_max_bytes() == 10 * 1024 * 1024


def test_uploads_dir_is_day_partitioned_under_workspace(tmp_path: Path) -> None:
    d = uploads_dir(tmp_path, day="2026-07-22")
    assert d.is_relative_to((tmp_path / "workspace").resolve())
    assert d.name == "2026-07-22" and d.parent.name == "uploads"


# --- v1 kapsam sınırı: analiz/özet yok ---


def test_v1_response_carries_no_analysis_or_summary(tmp_path: Path) -> None:
    _status, body = _post(tmp_path, "notlar.txt", b"ozetlenecek metin")
    assert set(body["file"]) == {
        "name", "size", "mime", "sha256", "stored_as", "sandbox_path"
    }
    assert body["approval"] is None
    assert "summary" not in body and "analysis" not in body
