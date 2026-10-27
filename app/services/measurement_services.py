import csv
from datetime import datetime, timezone
from io import TextIOWrapper
from math import isfinite
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


from app.models import Installation, Measurement

REQUIRED = {"timestamp", "power_kw", "energy_kwh"}
BATCH_SIZE = 1000
MAX_ERRORS = 25

def import_measurements(db: Session, installation: Installation, file, tz_name: str = "UTC"):
    source_tz = ZoneInfo(tz_name)
    skipped = rejected = 0
    errors: list[str] = []
    unique: dict[datetime, dict] = {}

    try: 
        reader = csv.DictReader(TextIOWrapper(file, encoding="utf-8-sig"))
        if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
            return 0, 0, 1, ["CSV must contain: timestamp, power_kw, energy_kwh"]

        for n, row in enumerate(reader, start = 2):
            try: 
                raw = (row.get("timestamp") or "").strip()
                if not raw: 
                    raise ValueError("timestamp is empty")
                moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if moment.tzinfo is None: 
                    moment = moment.replace(tzinfo=source_tz)
                moment = moment.astimezone(timezone.utc)
                power = float(row["power_kw"])
                energy = float(row["energy_kwh"])
                if not (isfinite(power) and isfinite(energy)):
                    raise ValueError("power and energy must be finite numbers")
                if power < 0 or energy < 0:
                    raise ValueError("Power and energy must be non-negative")
                if power > 1.5 * installation.capacity:
                    raise ValueError("power is implausibly high for installation capacity")
                if moment in unique:
                    skipped += 1
                    continue
                unique[moment] = {
                    "installation_id": installation.id, "measured_at": moment, "power_kw": power, "energy_kwh": energy,
                }
            except(ValueError, TypeError, KeyError) as exc: 
                rejected += 1
                if len(errors) < MAX_ERRORS:
                    errors.append(f"Row {n}: {exc}")
    except (UnicodeDecodeError, csv.Error) as exc:
            return 0, 0, 1, [f"Could not read the sile as UTF-8 CSV: {exc}"]

    rows = list(unique.values())
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        stmt = (
            pg_insert(Measurement).values(rows[i:i + BATCH_SIZE]).on_conflict_do_nothing(constraint="uq_measurement_installation_time")
        )
        inserted += len(db.execute(stmt.returning(Measurement.id)).all())
    db.commit()
    skipped += len(rows) - inserted
    return inserted, skipped, rejected, errors