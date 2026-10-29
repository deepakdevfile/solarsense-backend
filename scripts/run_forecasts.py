import sys

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models import ForecastModel, Installation
from app.services import forecast_services as fs

def main() -> int:
    failures = 0
    with SessionLocal() as db:
        ids = db.scalars(select(ForecastModel.installation_id).where(ForecastModel.is_active).distinct()).all()
        for installation_id in ids:
            installation = db.get(Installation, installation_id)
            try:
                _, records = fs.run_forecast(db, installation)
                print(f"installation {installation_id}: stored {len(records)} hourly forecasts")
            except fs.TooSoonError:
                print(f"installation {installation_id}: skipped, forecast is fresh")
            except (httpx.HTTPError, FileNotFoundError, ValueError) as exc:
                db.rollback()
                failures += 1
                print(f"installation {installation_id}: FAILED ({type(exc).__name__}: {exc})", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())