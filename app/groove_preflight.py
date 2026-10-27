"""Check whether the optional privately trained Groove23 reference is installed.

The public Music Studio source release excludes personal training checkpoints,
third-party sample libraries and private training runs. Missing those OPTIONAL
assets must not break ordinary ACE-Step music generation or silently invent a
"trained" rhythm. This module imports only Python standard-library modules.
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_ROOT = Path.home() / "Music Studio"


class GrooveReferenceUnavailable(RuntimeError):
    """The optional experimental 808 groove cannot be rendered locally."""


def availability(root: Path | str | None = None) -> dict:
    root = Path(root) if root is not None else DEFAULT_ROOT
    model_dir = root / "Training Runs" / "groove23"
    library = root / "Sound Library"
    checks = {
        "groove23 checkpoint": model_dir / "best_groove_model.pt",
        "groove23 model architecture": model_dir / "groove_model23.py",
        "licensed sample catalog": library / "catalog20.json",
        "local sample packs": library / "packs",
        "ACE-Step Python": root / "ACE-Step-1.5" / ".venv" / "Scripts" / "python.exe",
    }
    missing = []
    for label, path in checks.items():
        try:
            if path.is_dir():
                if not any(path.iterdir()):
                    missing.append(label)
            elif not path.is_file() or not path.stat().st_size:
                missing.append(label)
        except OSError:
            missing.append(label)
    # A partial download of the audio catalog should not be presented
    # as a functional sample collection; actual individual sample
    # integrity is validated by the renderer if the optional model runs.
    present = not missing
    return {
        "available": present,
        "missing": missing,
        "message": (
            "Экспериментальный обученный 808-грув доступен."
            if present else
            "Дополнительная модель ритма groove23 недоступна: "
            + ", ".join(missing)
            + ". Генерация через ACE-Step продолжится без этой обученной ритм-подложки."
        ),
        "optional": True,
        "requires_private_training_files": True,
    }


def ensure_available(root: Path | str | None = None) -> dict:
    state = availability(root)
    if not state["available"]:
        raise GrooveReferenceUnavailable(state["message"])
    return state
