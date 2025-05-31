# models.py
from sqlalchemy import String, Integer, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from app.core.database import Base


class RouteHit(Base):
    __tablename__ = "route_hits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route: Mapped[str] = mapped_column(String, nullable=False)
    created: Mapped[date] = mapped_column(default=date.today, nullable=False)
    hits: Mapped[int] = mapped_column(default=0)

    __table_args__ = (UniqueConstraint("route", "created", name="uq_route_created"),)
