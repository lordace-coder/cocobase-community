from fastapi import APIRouter, Depends, HTTPException, Request
from dotenv import load_dotenv
import resend
import os

from app.services.email import send_email

load_dotenv()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SIGNING_SECRET = os.getenv("RESEND_WEBHOOK_SIGNING_SECRET")

resend.api_key = os.getenv("RESEND_API_KEY")
if not resend.api_key:
    raise ValueError("RESEND_API_KEY is not set in the environment variables.")


@router.post("/resend-forward")
async def resend_webhook_forward(req: Request):
    """Endpoint to forward Resend emails to cocomailer email"""
    data = await req.json()

    msg_id = data.get("data").get("message_id")
    msg_title = data.get("data").get("subject")
    email_detail = resend.Emails.Receiving.get(email_id=msg_id)

    send_email(
        to="cocomailer85@gmail.com",
        subject=f"FWD: {msg_title} from {email_detail.get('from')}",
        html_content=email_detail.get("html"),
    )
    return
