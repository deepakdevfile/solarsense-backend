from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ml.features import WEATHER, make_features
from app.ml.model_store import load_artifact
from app.models import Installation, ForecastModel, Forecast, WeatherObservation
from app.services.weather_services import sync_weather

MIN_RERUN = timedelta(minutes=10)  
MAX_HORIZON_H = 72


class NoModelError(Exception): ...
class TooSoonError(Exception):
    def __init__(self, retry_after: int): self.retry_after = retry_after

def get_active_model(db: Session, installation_id: int) -> ForecastModel | None:
    return db.scalar(
        select(ForecastModel).where(ForecastModel.installation_id == installation_id, ForecastModel.is_active)
        .order_by(ForecastModel.created_at.desc()).limit(1))

def predict_hours(model_row: ForecastModel, installation: Installation, weather: pd.DataFrame) -> pd.DataFrame:
    art = load_artifact(model_row.file_name)
    feats = make_features(weather, installation.latitude, installation.longitude, art["tz"], art["orientation"])
    power = pd.Series(0.0, index=feats.index)  
    day = feats[feats.daylight]
    if len(day):
        cf = np.clip(art["model"].predict(day[art["features"]]), 0, None)
        power.loc[day.index] = cf * art["capacity_kw"]
    return pd.DataFrame({"power_kw": power, "is_daylight": feats.daylight})

def run_forecast(db: Session, installation: Installation, horizon_hours: int = 48, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    model_row = get_active_model(db, installation.id)
    if not model_row:
        raise NoModelError
    horizon_hours = min(max(horizon_hours, 1), MAX_HORIZON_H)

    last = db.scalar(select(Forecast.issued_at).where(Forecast.installation_id == installation.id).order_by(Forecast.issued_at.desc()).limit(1))
    if last and now - last < MIN_RERUN:
        raise TooSoonError(int((MIN_RERUN - (now - last)).total_seconds()) + 1)

    sync_weather(db, installation)  
    rows = db.scalars(
        select(WeatherObservation).where(
            WeatherObservation.installation_id == installation.id,
            WeatherObservation.observed_at > now,
            WeatherObservation.observed_at <= now + timedelta(hours=horizon_hours),
        ).order_by(WeatherObservation.observed_at)).all()
    weather = pd.DataFrame(
        [{c: getattr(r, c) for c in WEATHER} for r in rows],
        index=pd.DatetimeIndex([r.observed_at.astimezone(timezone.utc).replace(tzinfo=None) for r in rows]),
    ).dropna()
    if weather.empty:
        raise ValueError("No forecast weather available for this location right now")

    pred = predict_hours(model_row, installation, weather)
    records = [{
        "installation_id": installation.id, "model_id": model_row.id, "issued_at": now,
        "target_time": t.replace(tzinfo=timezone.utc), "power_kw": float(r.power_kw), "is_daylight": bool(r.is_daylight),
    } for t, r in pred.iterrows()]
    db.execute(pg_insert(Forecast).values(records).on_conflict_do_nothing(constraint="uq_forecast_issue"))
    db.commit()
    return model_row, records

def latest_forecast(db: Session, installation_id: int, hours: int, now: datetime | None = None):
    """Newest-issued prediction for every future hour."""
    now = now or datetime.now(timezone.utc)
    return db.scalars(
        select(Forecast).where(Forecast.installation_id == installation_id, Forecast.target_time > now,
                               Forecast.target_time <= now + timedelta(hours=hours))
        .distinct(Forecast.target_time).order_by(Forecast.target_time, Forecast.issued_at.desc())).all()