from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

LIVE_RESULTS_FILE = STORAGE_DIR / "live_results.jsonl"
_LOCK = threading.Lock()


def publish_event(payload: dict[str, Any]) -> None:
    with _LOCK:
        with LIVE_RESULTS_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def publish_status(model: str, status: str, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"model": model, "status": status}
    if extra:
        payload.update(extra)
    publish_event(payload)


def read_live_results(limit: int = 20) -> list[dict[str, Any]]:
    if not LIVE_RESULTS_FILE.exists():
        return []

    with _LOCK:
        with LIVE_RESULTS_FILE.open("r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]

    results: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return results


def reset_live_results() -> None:
    with _LOCK:
        LIVE_RESULTS_FILE.write_text("", encoding="utf-8")
