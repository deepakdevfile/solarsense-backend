from pydantic import BaseModel, EmailStr, Field, ConfigDict


class AuthPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    email: EmailStr
    id: int
    model_config = ConfigDict(from_attributes=True)