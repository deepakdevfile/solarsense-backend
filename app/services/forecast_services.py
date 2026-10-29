from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ml.features import WEATHER, make_features
from app.ml.model_store import load_artifact
from app.models import Installation, ForecastModel, Forecast, WeatherObservation, Measurement
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

def accuracy(db: Session, installation: Installation, days: int = 14, min_lead_hours: int = 12, now: datetime | None = None) -> dict:
    """Compare stored forecasts with what the plant really produced.

    For every past hour we use the newest forecast that was issued at least `min_lead_hours` earlier,
    so a forecast made minutes before the hour (which is nearly a measurement) cannot flatter the score."""
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    fc = db.scalars(
        select(Forecast).where(
            Forecast.installation_id == installation.id, Forecast.target_time > start, Forecast.target_time <= now,
            Forecast.issued_at <= Forecast.target_time - timedelta(hours=min_lead_hours))
        .distinct(Forecast.target_time).order_by(Forecast.target_time, Forecast.issued_at.desc())).all()
    empty = {"n_hours": 0, "mae_kw": None, "rmse_kw": None, "wape_pct": None, "bias_kw": None,
             "bias_pct": None, "min_lead_hours": min_lead_hours, "points": []}
    if not fc:
        return empty

    meas = db.execute(select(Measurement.measured_at, Measurement.power_kw).where(
        Measurement.installation_id == installation.id,
        Measurement.measured_at > start - timedelta(hours=1), Measurement.measured_at <= now)).all()
    actual = pd.Series(dtype=float)
    if meas:
        s = pd.Series([m.power_kw for m in meas], index=pd.DatetimeIndex([m.measured_at.astimezone(timezone.utc).replace(tzinfo=None) for m in meas])).sort_index()
        g = s.resample("1h", closed="right", label="right").agg(["mean", "count"])
        actual = g["mean"].where(g["count"] >= 3)

    points, f_list, a_list = [], [], []
    for f in fc:
        key = f.target_time.astimezone(timezone.utc).replace(tzinfo=None)
        a = actual.get(key)
        a = None if a is None or pd.isna(a) else float(a)
        points.append({"target_time": f.target_time, "forecast_kw": f.power_kw, "actual_kw": a, "issued_at": f.issued_at})
        if a is not None and f.is_daylight:
            f_list.append(f.power_kw)
            a_list.append(a)
    if not a_list:
        return {**empty, "points": points}
    f_arr = np.array(f_list)
    a_arr = np.array(a_list)
    return {
        "n_hours": len(a_arr), "mae_kw": float(np.abs(f_arr - a_arr).mean()),
        "rmse_kw": float(np.sqrt(((f_arr - a_arr) ** 2).mean())),
        "wape_pct": float(100 * np.abs(f_arr - a_arr).sum() / a_arr.sum()) if a_arr.sum() > 0 else None,
        "bias_kw": float((f_arr - a_arr).mean()),
        "bias_pct": float(100 * (f_arr - a_arr).sum() / a_arr.sum()) if a_arr.sum() > 0 else None,
        "min_lead_hours": min_lead_hours, 
        "points": points,
    }