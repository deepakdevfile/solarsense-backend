from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime

class AuthPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    email: EmailStr
    id: int
    model_config = ConfigDict(from_attributes=True)

class InstallationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=255)
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