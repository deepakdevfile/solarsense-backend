from datetime import date, datetime, timezone

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Installation, WeatherObservation

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"  # NEW: real history (the forecast API only has ~7 past days)
HOURLY = ["temperature_2m", "cloud_cover", "precipitation", "wind_speed_10m", "shortwave_radiation"]
MAX_RANGE_DAYS = 366


def sync_weather(db: Session, installation: Installation, start: date | None = None, end: date | None = None):
    """Fetch hourly weather and upsert it. Returns (rows_upserted, source)."""
    params: dict = {
        "latitude": installation.latitude, "longitude": installation.longitude,
        "hourly": HOURLY, "timezone": "GMT",
    }
    if start and end:
        if end < start:
            raise ValueError("end date must not be before start date")
        if (end - start).days > MAX_RANGE_DAYS:
            raise ValueError(f"date range must be at most {MAX_RANGE_DAYS} days")
        url, source = ARCHIVE_URL, "archive"
        params |= {"start_date": start.isoformat(), "end_date": end.isoformat()}
    else:
        url, source = FORECAST_URL, "forecast"
        params |= {"past_days": 7, "forecast_days": 3}

    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        hourly = response.json().get("hourly", {})

    now = datetime.now(timezone.utc)
    rows = []
    for i, raw in enumerate(hourly.get("time", [])):
        def val(name):
            values = hourly.get(name, [])
            return values[i] if i < len(values) else None

        observed_at = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        row = {
            "installation_id": installation.id, "observed_at": observed_at,
            "temperature_c": val("temperature_2m"), "cloud_cover_pct": val("cloud_cover"),
            "precipitation_mm": val("precipitation"), "wind_speed_kmh": val("wind_speed_10m"),
            "shortwave_radiation_w_m2": val("shortwave_radiation"),
            "is_forecast": observed_at > now,
        }
        if all(row[k] is None for k in ("temperature_c", "cloud_cover_pct", "shortwave_radiation_w_m2")):
            continue  # archive data lags a few days: skip hours with no values
        rows.append(row)

    if not rows:
        return 0, source

    # FIX: one-row-at-a-time SELECT/INSERT replaced by an upsert; forecast rows are refreshed
    # with newer values (and is_forecast flips to false) once their hour has passed.
    upserted = 0
    for i in range(0, len(rows), 1000):
        stmt = pg_insert(WeatherObservation).values(rows[i:i + 1000])
        stmt = stmt.on_conflict_do_update(
            constraint="uq_weather_installation_time",
            set_={c: stmt.excluded[c] for c in (
                "temperature_c", "cloud_cover_pct", "precipitation_mm",
                "wind_speed_kmh", "shortwave_radiation_w_m2", "is_forecast")},
        )
        upserted += len(db.execute(stmt.returning(WeatherObservation.id)).all())
    db.commit()
    return upserted, source
