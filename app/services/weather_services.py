from sqlalchemy.orm import Session
from app.models import Installation, WeatherObservation
import httpx
from datetime import datetime, timezone
from sqlalchemy import select

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# url = https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m,precipitation,wind_speed_10m,cloud_cover,shortwave_radiation&timezone=GMT&past_days=7&forecast_days=3

def sync_weather(db: Session, installation_row: Installation):
    params = {"latitude": installation_row.latitude, "longitude": installation_row.longitude, "hourly": ["temperature_2m", "cloud_cover", "precipitation", "wind_speed_10m", "shortwave_radiation"], "timezone": "GMT", "past_days": 7, "forecast_days": 3}
    with httpx.Client(timeout= 20) as client:
        response = client.get(OPEN_METEO_URL, params= params)
        # print(response.url)
        response.raise_for_status()
        data = response.json()
    # print("I am invisible")
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    inserted = 0
    def val(name, i):
        values = hourly.get(name, [])
        if i < len(values):
            return values[i]  
        else:
            return None
    for i, raw in enumerate(times):
        observed_at = datetime.fromisoformat(raw).replace(tzinfo = timezone.utc)
        exists = db.scalar(select(WeatherObservation).where(WeatherObservation.installation_id == installation_row.id, WeatherObservation.observed_at == observed_at))
        if exists: 
            continue
        db.add(WeatherObservation(installation_id = installation_row.id, observed_at = observed_at, temperature_c = val("temperature_2m", i), cloud_cover_pct = val("cloud_cover", i), precipitation_mm = val("precipitation", i), wind_speed_kmh = val("wind_speed_10m", i), shortwave_radiation_w_m2 = val("shortwave_radiation", i)))
        inserted += 1
    db.commit()
    return inserted
