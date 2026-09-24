from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
from sqlalchemy import String, Float, ForeignKey

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