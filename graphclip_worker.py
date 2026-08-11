from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

from config import ALLOWED_EXTENSIONS, WATCH_FOLDER, ensure_graphclip_env, find_graphclip_root

_ENGINE = None


def _to_float(value) -> float | None:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except Exception:
            pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _predict_similarity(engine, image_path: Path, text: str) -> float | None:
    try:
        result = engine.predict(
            image=str(image_path),
            text=text,
        )
    except Exception:
        return None
    return _to_float(result.get("similarity"))


def iter_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return sorted(
        [
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
        ],
        key=lambda path: str(path),
    )


def get_graphclip_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    graphclip_root = find_graphclip_root()
    if graphclip_root is None:
        raise FileNotFoundError("GraphCLIP klasörü bulunamadı.")

    ensure_graphclip_env(graphclip_root)

    sys.path.insert(0, str(graphclip_root))

    from graphclip import GraphCLIPInference

    _ENGINE = GraphCLIPInference.from_pretrained(
        str(graphclip_root / "artifacts" / "graphclip-base")
    )
    return _ENGINE


def search_graphclip(
    text: str,
    image_folder: Path = WATCH_FOLDER,
    n_results: int = 8,
) -> list[dict]:
    engine = get_graphclip_engine()
    results: list[dict] = []

    for image_path in iter_images(image_folder):
        similarity = _predict_similarity(engine, image_path, text)
        if similarity is None:
            continue

        results.append(
            {
                "model": "graphclip",
                "image_path": str(image_path),
                "filename": image_path.name,
                "similarity": float(similarity),
            }
        )

    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results[:n_results]


def run_graphclip_scan(
    image_folder: Path = WATCH_FOLDER,
    text: str = "a flower next to a vase",
    on_result: Optional[Callable[[dict], None]] = None,
) -> list[dict]:
    engine = get_graphclip_engine()

    results: list[dict] = []
    for image_path in iter_images(image_folder):
        similarity = _predict_similarity(engine, image_path, text)
        if similarity is None:
            if on_result is not None:
                on_result(
                    {
                        "model": "graphclip",
                        "image": str(image_path),
                        "status": "skipped",
                    }
                )
            continue

        item = {
            "model": "graphclip",
            "image": str(image_path),
            "similarity": similarity,
            "status": "result",
        }
        results.append(item)

        if on_result is not None:
            on_result(item)

    return results
