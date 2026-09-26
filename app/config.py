from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    cookie_secure: bool = False
    ALLOWED_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(env_file = ".env", extra="ignore")

settings = Settings()