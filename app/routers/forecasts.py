import logging

import httpx
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.routers.installations import owned_installation
from app.schemas import ForecastOut, ForecastPoint, ForecastModelOut
from app.services import forecast_services as fs

router = APIRouter(tags=["Forecast"])
log = logging.getLogger("solarsense.forecast")

@router.get("/installation/{id}/forecast/model", response_model=ForecastModelOut)
def forecast_model(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_installation(db, id, user)
    model = fs.get_active_model(db, id)
    if not model:
        raise HTTPException(404, "No active forecast model for this installation")
    return model

@router.post("/installation/{id}/forecast/run", response_model=ForecastOut)
def run_forecast(id: int, hours: int = Query(48, ge=1, le=fs.MAX_HORIZON_H), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = owned_installation(db, id, user)
    try:
        model, records = fs.run_forecast(db, installation, hours)
    except fs.NoModelError:
        raise HTTPException(404, "No active forecast model for this installation")
    except fs.TooSoonError as exc:
        raise HTTPException(429, "A forecast was just generated. Try again in a few minutes.", headers={"Retry-After": str(exc.retry_after)})
    except httpx.HTTPError:
        db.rollback()
        raise HTTPException(502, "Weather provider request failed. Try again in a moment.")
    except FileNotFoundError:
        log.exception("model file missing")
        raise HTTPException(500, "The model file is missing on the server")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    
    return ForecastOut(model_version=model.version, points=[ForecastPoint(**r) for r in records])

