import os
import subprocess
import sys
from pathlib import Path

import torch

BASE_DIR = Path(__file__).resolve().parent
WATCH_FOLDER = Path.home() / "Pictures" / "SmartGallery"
CHROMA_DB_DIR = BASE_DIR / "storage" / "chroma_data"

WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"

if torch.backends.mps.is_available():
    DEVICE = "mps"
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_graphclip_root() -> Path | None:
    env_root = os.environ.get("GRAPHCLIP_ROOT")
    candidates: list[Path] = []

    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())

    candidates.extend(
        [
            BASE_DIR,
            BASE_DIR.parent,
            BASE_DIR.parent.parent,
            Path.home() / "Desktop" / "codes",
            Path.home(),
        ]
    )

    seen: set[Path] = set()

    for root in candidates:
        root = root.resolve()
        if root in seen or not root.exists():
            continue
        seen.add(root)

        if root.name.lower() == "graphclip" and (root / "requirements.txt").exists():
            return root

        for candidate in root.rglob("GraphCLIP"):
            if candidate.is_dir() and (candidate / "requirements.txt").exists():
                return candidate

        for candidate in root.rglob("graphclip"):
            if candidate.is_dir() and (candidate / "requirements.txt").exists():
                return candidate

    return None


def ensure_graphclip_env(graphclip_root: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(graphclip_root / "requirements.txt")],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(graphclip_root)],
        check=True,
    )