from fastapi import APIRouter, HTTPException, Depends
import requests
from app.core.dependencies import get_current_user
from app.models.user import User


router = APIRouter(prefix="/payments", tags=["Payments"])


paystack_api_key = None


def initialize_payment(data: dict, email: str, amt) -> dict:
    req = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={
            "Authorization": f"Bearer {paystack_api_key}",
            "Content-Type": "application/json",
        },
        data={"email": email, "amount": amt},
    )
    return req.json()


@router.get("/initialize-subscription/{planId}")
def get_payment_url_for_subscription(user: User = Depends(get_current_user)): ...
