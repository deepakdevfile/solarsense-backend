from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
from sqlalchemy import String, Float, ForeignKey, UniqueConstraint, Index, DateTime, func
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    installations: Mapped[list["Installation"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Installation(Base):
    __tablename__ = "installations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[float] = mapped_column(Float)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped[User] = relationship(back_populates="installations")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="installation", cascade="all, delete-orphan")

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
