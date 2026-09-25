from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime

class AuthPayload(BaseModel):
    name: str = Field(default=None, min_length=2, max_length = 120)
    email: EmailStr
    password: str | None = Field(default = None, min_length=8, max_length=128)

class UserOut(BaseModel):
    email: EmailStr
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class InstallationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge = -90, le = 90)
    longitude: float = Field(ge = -180, le = 180)
    capacity: float = Field(gt=0)

class InstallationOut(InstallationCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class MeasurementCreate(BaseModel):
    measured_at: datetime | None = None
    energy_kwh: float = Field(ge = 0)
    power_kw: float = Field(ge = 0)

class MeasurementOut(MeasurementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    measured_at: datetime
    installation_id: int

class ImportResult(BaseModel):
    inserted: int
    skipped_duplicates: int
    rejected: int
    errors: list[str]

class WeatherOut(BaseModel):
    model_config = ConfigDict(from_attributes= True)
    id: int 
    installation_id: int
    observed_at: datetime
    temperature_c: float | None
    cloud_cover_pct: float | None
    precipitation_mm: float | None
    wind_speed_kmh: float | None
    shortwave_radiation_w_m2: float | None