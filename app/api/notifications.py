from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.notifications import Notification
from app.models.user import User
from sqlalchemy.orm import Session

from app.schemas.notifications import NotificationSchema


router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/")
async def get_notifications(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[NotificationSchema]:
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created.desc())
        .all()
    )
    return notifications


@router.patch("/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    updated_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return {"message": "All notifications marked as read", "updated_count": updated_count}


@router.delete("/delete-all")
async def delete_all_notifications(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    deleted_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .delete()
    )
    db.commit()
    return {"message": "All notifications deleted", "deleted_count": deleted_count}