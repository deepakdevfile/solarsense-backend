from pydantic import BaseModel, EmailStr, Field, ConfigDict


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