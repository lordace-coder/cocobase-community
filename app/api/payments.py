from fastapi import APIRouter, HTTPException, Depends, Request
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.pricing import PricingPlan
from app.models.user import User
from sqlalchemy.orm import Session
from app.schemas.payments import PricingPlanSchema
import httpx
import os
from dotenv import load_dotenv
import hmac
import hashlib

load_dotenv()

router = APIRouter(prefix="/plans", tags=["Plans and Payments"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_BASE_URL = "https://api.paystack.co"


@router.get("/", summary="Get available subscription plans")
async def get_subscription_plans(
    db: Session = Depends(get_db),
) -> list[PricingPlanSchema]:
    """
    Fetch available subscription plans from the external payment service.
    """
    plans = db.query(PricingPlan).all()
    return plans


@router.post("/initialize-subscription-payment/{plan_id}", summary="Initialize payment")
async def initialize_payment(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initialize a Paystack payment for a subscription plan.
    Returns authorization URL for the user to complete payment.
    """
    # Get the pricing plan
    plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Prepare payment data
    # Paystack amount is in kobo (smallest currency unit), multiply by 100
    amount_in_kobo = int(plan.price * 100)
    
    payload = {
        "email": user.email,
        "amount": amount_in_kobo,
        "currency": "NGN",  # Adjust based on your needs
        "metadata": {
            "user_id": user.id,
            "plan_id": plan.id,
            "plan_name": plan.name,
        },
        "callback_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/verify",
    }
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Payment initialization failed: {response.text}"
                )
            
            data = response.json()
            
            if not data.get("status"):
                raise HTTPException(
                    status_code=400,
                    detail="Payment initialization failed"
                )
            
            return {
                "status": "success",
                "authorization_url": data["data"]["authorization_url"],
                "access_code": data["data"]["access_code"],
                "reference": data["data"]["reference"],
            }
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to payment service: {str(e)}"
        )


@router.get("/verify-payment/{reference}", summary="Verify payment")
async def verify_payment(
    reference: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify a payment transaction with Paystack.
    This endpoint should be called after the user completes payment.
    """
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Payment verification failed: {response.text}"
                )
            
            data = response.json()
            
            if not data.get("status"):
                raise HTTPException(
                    status_code=400,
                    detail="Payment verification failed"
                )
            
            transaction_data = data["data"]
            
            # Check if payment was successful
            if transaction_data["status"] != "success":
                return {
                    "status": "failed",
                    "message": "Payment was not successful",
                    "transaction_status": transaction_data["status"]
                }
            
            # Extract metadata
            metadata = transaction_data.get("metadata", {})
            plan_id = metadata.get("plan_id")
            
            if not plan_id:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid payment metadata"
                )
            
            # Process subscription
            await process_subscription(user, plan_id, transaction_data, db)
            
            return {
                "status": "success",
                "message": "Payment verified and subscription activated",
                "transaction": {
                    "reference": transaction_data["reference"],
                    "amount": transaction_data["amount"] / 100,  # Convert from kobo
                    "currency": transaction_data["currency"],
                    "paid_at": transaction_data["paid_at"],
                }
            }
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to payment service: {str(e)}"
        )


@router.post("/webhook", summary="Paystack webhook")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Paystack webhook events.
    This is called by Paystack to notify about payment events.
    """
    # Verify webhook signature
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="No signature provided")
    
    body = await request.body()
    
    # Compute HMAC signature
    computed_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'),
        body,
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(signature, computed_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Parse webhook data
    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data", {})
    
    # Handle different event types
    if event == "charge.success":
        # Extract user and plan info from metadata
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan_id")
        
        if user_id and plan_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                await process_subscription(user, plan_id, data, db)
    
    return {"status": "success"}


async def process_subscription(
    user: User,
    plan_id: int,
    transaction_data: dict,
    db: Session
):
    """
    Process subscription after successful payment.
    Updates user subscription status and sends notification email.
    """
    from datetime import datetime, timedelta
    from app.services.email import send_subscription_email  # You'll need to create this
    
    # Get the plan
    plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Update user subscription
    user.subscription_plan_id = plan.id
    user.subscription_status = "active"
    user.subscription_start_date = datetime.utcnow()
    
    # Calculate end date based on plan duration (assuming monthly)
    user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
    
    # Store payment reference
    user.last_payment_reference = transaction_data.get("reference")
    
    db.commit()
    db.refresh(user)
    
    # Send confirmation email
    try:
        await send_subscription_email(
            to_email=user.email,
            user_name=user.name or user.email,
            plan_name=plan.name,
            amount=transaction_data["amount"] / 100,
            currency=transaction_data["currency"],
            subscription_end_date=user.subscription_end_date
        )
    except Exception as e:
        # Log the error but don't fail the subscription
        print(f"Failed to send email: {str(e)}")
    
    return user