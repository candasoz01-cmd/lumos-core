"""Video executor: Replicate üzerinden video; yapılandırılmış çıktı."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

__all__ = ["run"]

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

POLL_MAX_ATTEMPTS = 30
POLL_INTERVAL_SEC = 2.0

VIDEO_CACHE_FILE = ".video_cache.json"


def _video_cache_path() -> Path:
    return Path(os.getcwd()) / VIDEO_CACHE_FILE


def _load_video_cache() -> dict[str, str]:
    p = _video_cache_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                out[k] = v.strip()
        return out
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def _write_cache_entry(prompt_hash: str, video_url: str) -> None:
    if not prompt_hash or not (video_url and str(video_url).strip()):
        return
    p = _video_cache_path()
    cache = _load_video_cache()
    cache[prompt_hash] = str(video_url).strip()
    try:
        p.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _done_video_payload(url: str) -> dict[str, Any]:
    return {
        "status": "done",
        "output": {
            "type": "video",
            "url": url,
            "provider": "replicate",
        },
    }


def _first_video_url_from_output(output: Any) -> str:
    """Replicate `output` alanından ilk video URL'ini döndürür (string, liste veya nesne)."""
    if output is None:
        return ""
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                u = item.get("url")
                if isinstance(u, str) and u.strip():
                    return u.strip()
        return ""
    if isinstance(output, dict):
        u = output.get("url")
        if isinstance(u, str) and u.strip():
            return u.strip()
    return ""


def _replicate_error_message(data: dict[str, Any], fallback: str) -> str:
    err = data.get("error")
    if isinstance(err, str) and err.strip():
        return err.strip()
    detail = data.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return fallback


def run(task_ctx: dict[str, Any]) -> dict[str, Any]:
    prompt = task_ctx.get("prompt", "")
    prompt_norm = prompt.strip().lower()
    prompt_norm = " ".join(prompt_norm.split())
    prompt_norm = prompt_norm.replace(".", "")
    prompt_norm = prompt_norm.replace(",", "")
    prompt_norm = prompt_norm.replace("!", "")
    prompt_norm = prompt_norm.replace("?", "")
    prompt_hash = hashlib.sha256(prompt_norm.encode()).hexdigest()

    cache = _load_video_cache()
    cached_url = cache.get(prompt_hash, "")
    if cached_url:
        return _done_video_payload(cached_url)

    if not REPLICATE_API_TOKEN:
        return {
            "status": "error",
            "output": {
                "type": "video",
                "url": "",
                "provider": "replicate",
                "error": "missing REPLICATE_API_TOKEN",
            },
        }

    response = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers={
            "Authorization": f"Token {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "version": "a40e1d8b0c...MODEL_ID...",
            "input": {
                "prompt": prompt_norm,
            },
        },
        timeout=120,
    )

    try:
        data = response.json()
    except Exception:
        return {
            "status": "error",
            "output": {
                "type": "video",
                "url": "",
                "provider": "replicate",
                "error": response.text[:500] if response.text else "invalid JSON from Replicate",
            },
        }

    if not response.ok:
        return {
            "status": "error",
            "output": {
                "type": "video",
                "url": "",
                "provider": "replicate",
                "error": _replicate_error_message(
                    data if isinstance(data, dict) else {},
                    response.text[:500] if response.text else f"HTTP {response.status_code}",
                ),
            },
        }

    pred_id = data.get("id") if isinstance(data, dict) else None
    poll_url = (
        data.get("urls", {}).get("get", "")
        if isinstance(data, dict)
        else ""
    )
    poll_url = str(poll_url or "").strip()
    if not poll_url and pred_id:
        poll_url = f"https://api.replicate.com/v1/predictions/{pred_id}"

    if not poll_url:
        return {
            "status": "error",
            "output": {
                "type": "video",
                "url": "",
                "provider": "replicate",
                "error": "missing prediction id and urls.get",
            },
        }

    initial_status = str(data.get("status") or "").lower()
    if initial_status == "succeeded":
        url_out = _first_video_url_from_output(data.get("output"))
        if url_out:
            _write_cache_entry(prompt_hash, url_out)
            return _done_video_payload(url_out)
        return {
            "status": "error",
            "output": {
                "type": "video",
                "url": "",
                "provider": "replicate",
                "error": _replicate_error_message(
                    data,
                    "replicate output missing video url",
                ),
            },
        }
    if initial_status in ("failed", "canceled"):
        return {
            "status": "error",
            "output": {
                "type": "video",
                "url": "",
                "provider": "replicate",
                "error": _replicate_error_message(data, initial_status),
            },
        }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    for _ in range(POLL_MAX_ATTEMPTS):
        time.sleep(POLL_INTERVAL_SEC)
        pr = requests.get(poll_url, headers=headers, timeout=120)
        try:
            pbody = pr.json()
        except Exception:
            return {
                "status": "error",
                "output": {
                    "type": "video",
                    "url": "",
                    "provider": "replicate",
                    "error": pr.text[:500] if pr.text else "invalid JSON polling prediction",
                },
            }

        if not isinstance(pbody, dict):
            return {
                "status": "error",
                "output": {
                    "type": "video",
                    "url": "",
                    "provider": "replicate",
                    "error": "invalid prediction response",
                },
            }

        status = str(pbody.get("status") or "").lower()

        if status == "succeeded":
            url_out = _first_video_url_from_output(pbody.get("output"))
            if url_out:
                _write_cache_entry(prompt_hash, url_out)
                return _done_video_payload(url_out)
            return {
                "status": "error",
                "output": {
                    "type": "video",
                    "url": "",
                    "provider": "replicate",
                    "error": _replicate_error_message(
                        pbody,
                        "replicate output missing video url",
                    ),
                },
            }

        if status in ("failed", "canceled"):
            return {
                "status": "error",
                "output": {
                    "type": "video",
                    "url": "",
                    "provider": "replicate",
                    "error": _replicate_error_message(
                        pbody,
                        status,
                    ),
                },
            }

    return {
        "status": "pending",
        "output": {
            "type": "video",
            "url": "",
            "provider": "replicate",
            "message": "video hazırlanıyor",
        },
    }
