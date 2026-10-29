from functools import lru_cache
from pathlib import Path

import joblib

from app.config import settings

@lru_cache(maxsize=8)
def _load(path: str, mtime: float):
    return joblib.load(path)


def load_artifact(file_name: str) -> dict:
    base = Path(settings.model_dir).resolve()
    path = (base / file_name).resolve()
    if base not in path.parents:
        raise ValueError("Model path escapes the model directory")
    if not path.is_file():
        raise FileNotFoundError(f"Model file missing on server: {file_name}")
    return _load(str(path), path.stat().st_mtime)