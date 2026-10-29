
import argparse, json, shutil
from importlib.metadata import version as pkg_version
from pathlib import Path

import joblib
from sqlalchemy import update

from app.config import settings
from app.db import SessionLocal
from app.models import ForecastModel, Installation

def register(db, installation_id: int, model_path: str, version: str, metrics_path: str | None = None) -> ForecastModel:
    if not db.get(Installation, installation_id):
        raise SystemExit(f"Installation {installation_id} does not exist")
    art = joblib.load(model_path)
    missing = {"model", "features", "capacity_kw", "tz", "orientation"} - set(art)
    if missing:
        raise SystemExit(f"Model file is missing keys: {sorted(missing)}")

    metrics = {}
    if metrics_path:
        m = json.loads(Path(metrics_path).read_text())
        champ = m["champion"]
        metrics = {"test_period": m["test_period"], "model": champ, "metrics": m["results"][champ],
                   "baseline_7day": m["results"]["7-day same-hour mean (baseline)"]}
    start, _, end = art.get("trained_on", "..").partition("..")

    target_dir = Path(settings.model_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"installation_{installation_id}_{version}.joblib"
    shutil.copyfile(model_path, target_dir / file_name)

    db.execute(update(ForecastModel).where(ForecastModel.installation_id == installation_id).values(is_active=False))
    row = ForecastModel(
        installation_id=installation_id, version=version, file_name=file_name, capacity_kw=art["capacity_kw"],
        trained_start=start or None, trained_end=end or None, metrics=metrics, is_active=True,
        library_versions={p: pkg_version(p) for p in ("scikit-learn", "numpy", "pandas", "joblib")})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--installation-id", type=int, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--metrics")
    a = ap.parse_args()
    with SessionLocal() as db:
        row = register(db, a.installation_id, a.model, a.version, a.metrics)
    print(f"Registered model {row.version} (id {row.id}) for installation {row.installation_id} -> {row.file_name}")