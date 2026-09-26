from sqlalchemy.orm import Session
from app.models import Installation
from io import TextIOWrapper
import csv
from datetime import datetime, timezone
from app.models import Measurement
from sqlalchemy import select

def import_measurements(db: Session, installation: Installation, file):
    inserted = skipped = rejected = 0
    errors = []
    reader = csv.DictReader(TextIOWrapper(file, encoding = "utf-8-sig"))
    required = {"timestamp", "power_kw", "energy_kwh"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        return 0, 0, 1, ["CSV must contain: timestamp, power_kw, energy_kwh"]
    count = 0
    for n, row in enumerate(reader, start=2):
        try: 
            measured_at = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if measured_at.tzinfo is None: 
                measured_at = measured_at.replace(tzinfo= timezone.utc)
            power = float(row["power_kw"])
            energy = float(row["energy_kwh"])
            if power < 0 or energy < 0:
                raise ValueError("Power and energy must be non-negative")
            if power > 1.5 * installation.capacity:
                raise ValueError("power is implausibly high for installation capacity")
            exists = db.scalar(select(Measurement).where(Measurement.installation_id == installation.id, Measurement.measured_at == measured_at))
            if exists:
                skipped += 1
                continue
            db.add(Measurement(installation_id = installation.id, measured_at = measured_at, power_kw = power, energy_kwh = energy))
            inserted += 1
        except(ValueError, TypeError, KeyError) as exc: 
            rejected += 1
            if len(errors) < 25:
                errors.append(f"Row {n}: {exc}")
    db.commit()
    return inserted, skipped, rejected, errors