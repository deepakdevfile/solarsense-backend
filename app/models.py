from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import String, Float, ForeignKey, UniqueConstraint, Index, DateTime, func, text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), server_default=text("'User'"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    installations: Mapped[list["Installation"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Installation(Base):
    __tablename__ = "installations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float, server_default=text("0.0"), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, server_default=text("0.0"), nullable=False)
    capacity: Mapped[float] = mapped_column(Float)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped[User] = relationship(back_populates="installations")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="installation", cascade="all, delete-orphan")
    weather: Mapped[list["WeatherObservation"]] = relationship(back_populates= "installation", cascade= "all, delete-orphan")

class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (UniqueConstraint("installation_id", "measured_at", name = "uq_measurement_installation_time"), 
                      Index("ix_measurement_installation_time", "installation_id", "measured_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default=func.now(), index=True)
    energy_kwh: Mapped[float] = mapped_column(Float)
    power_kw: Mapped[float] = mapped_column(Float)
    installation_id: Mapped[int] = mapped_column(ForeignKey("installations.id", ondelete="CASCADE"))
    installation: Mapped[Installation] = relationship(back_populates="measurements")

class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    __table_args__ = (UniqueConstraint("installation_id", "observed_at", name = "uq_weather_installation_time"), Index("ix_weather_installation_time", "installation_id", "observed_at"))
    id: Mapped[int] = mapped_column(primary_key= True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone= True), index = True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable= True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable= True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable= True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable= True)
    shortwave_radiation_w_m2: Mapped[float | None ] = mapped_column(Float, nullable= True)
    is_forecast: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    installation_id: Mapped[int] = mapped_column(ForeignKey("installations.id", ondelete="CASCADE"))
    installation: Mapped[Installation] = relationship(back_populates= "weather")

class ForecastModel(Base):
    __tablename__ = "forecast_models"
    __table_args__ = (UniqueConstraint("installation_id", "version", name="uq_forecast_model_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[int] = mapped_column(ForeignKey("installations.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(60))
    file_name: Mapped[str] = mapped_column(String(255))
    capacity_kw: Mapped[float] = mapped_column(Float)
    trained_start: Mapped[str | None] = mapped_column(String(10), nullable=True)
    trained_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    library_versions: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("installation_id", "target_time", "issued_at", name="uq_forecast_issue"),
        Index("ix_forecast_installation_target", "installation_id", "target_time"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[int] = mapped_column(ForeignKey("installations.id", ondelete="CASCADE"))
    model_id: Mapped[int] = mapped_column(ForeignKey("forecast_models.id", ondelete="CASCADE"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    target_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    power_kw: Mapped[float] = mapped_column(Float)
    is_daylight: Mapped[bool] = mapped_column(Boolean)