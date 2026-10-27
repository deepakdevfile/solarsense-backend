from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime

def _check_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password must be at least 72 bytes")
    return value

class RegisterPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    _pw = field_validator("password")(_check_password_bytes)

class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

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

class InstallationSummary(BaseModel):
    measurement_count: int
    total_energy_kwh: float
    peak_power_kw: float
    first_measured_at: datetime | None
    last_measured_at: datetime | None
    weather_count: int

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
    is_forecast: bool

class WeatherSyncResult(BaseModel):
    upserted: int
    source: str