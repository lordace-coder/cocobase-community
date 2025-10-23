from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.cron.payments import auto_downgrade_expired_projects


router = APIRouter(prefix="/cron", tags=["Cron Jobs"])


@router.get("/check-subscription-status")
def check_subs(db=Depends(get_db)):
    auto_downgrade_expired_projects(db)
    pass
