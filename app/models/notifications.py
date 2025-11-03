from sqlalchemy import String, Integer, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False,index=True)
    message: Mapped[str] = mapped_column(String, nullable=False)
    created: Mapped[date] = mapped_column(default=date.today, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False)

