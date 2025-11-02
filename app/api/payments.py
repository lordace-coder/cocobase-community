from fastapi import APIRouter, HTTPException, Depends, Request
from app.api.project import get_project_with_access
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.pricing import PricingPlan, ProjectSubscription, Payment, get_current_plan
from app.models.user import User
from app.models.app_client import Project
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.schemas.payments import PricingPlanSchema
import httpx
import os
from dotenv import load_dotenv
import hmac
import hashlib
from datetime import datetime, timedelta

load_dotenv()

router = APIRouter(prefix="/plans", tags=["Plans and Payments"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_BASE_URL = "https://api.paystack.co"


@router.get("/", summary="Get available subscription plans")
async def get_subscription_plans(
    db: Session = Depends(get_db),
) -> list[PricingPlanSchema]:
    """
    Fetch available subscription plans.
    """
    plans = db.query(PricingPlan).filter(PricingPlan.is_active == True).all()
    return plans


@router.get("/project/{project_id}/current", summary="Get project's current plan")
async def get_project_current_plan(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
)->PricingPlanSchema:
    """
    Get the current active subscription plan for a project.
    """
    # Verify user has access to project
    project = get_project_with_access(project_id, user, db)

    # Get active subscription
    subscription =get_current_plan(project_id, db)

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")


    return subscription


@router.post("/initialize-subscription-payment/{plan_id}", summary="Initialize payment")
async def initialize_payment(
    plan_id: int,
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initialize a Paystack payment for a project subscription plan.
    Returns authorization URL for the user to complete payment.
    Anyone can pay for any project.
    """
    # Verify project exists (no ownership check)
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the pricing plan
    plan = (
        db.query(PricingPlan)
        .filter(and_(PricingPlan.id == plan_id, PricingPlan.is_active == True))
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")

    if plan.is_free:
        raise HTTPException(
            status_code=400, detail="Cannot initialize payment for free plan"
        )

    # Create payment record
    payment = Payment(
        reference=f"PAY-{project_id}-{plan_id}-{int(datetime.utcnow().timestamp())}",
        provider="paystack",
        amount=plan.price,
        currency=plan.currency,
        status="pending",
        project_id=project_id,
        user_id=user.id,
        plan_id=plan_id,
        payment_metadata={
            "project_name": project.name,
            "plan_name": plan.name,
            "user_email": user.email,
        },
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Prepare Paystack payment data
    amount_in_kobo = int(plan.price * 100)

    payload = {
        "email": user.email,
        "amount": amount_in_kobo,
        "currency": plan.currency,
        "reference": payment.reference,
        "metadata": {
            "payment_id": payment.id,
            "user_id": user.id,
            "project_id": project_id,
            "plan_id": plan.id,
            "project_name": project.name,
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
                timeout=30.0,
            )

            if response.status_code != 200:
                payment.status = "failed"
                db.commit()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Payment initialization failed: {response.text}",
                )

            data = response.json()

            if not data.get("status"):
                payment.status = "failed"
                db.commit()
                raise HTTPException(
                    status_code=400, detail="Payment initialization failed"
                )

            # Store provider response
            payment.provider_response = data
            db.commit()

            return {
                "status": "success",
                "payment_id": payment.id,
                "authorization_url": data["data"]["authorization_url"],
                "access_code": data["data"]["access_code"],
                "reference": payment.reference,
            }

    except httpx.HTTPError as e:
        payment.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500, detail=f"Error connecting to payment service: {str(e)}"
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
    Only processes if webhook hasn't already processed it.
    Anyone can verify any payment.
    """
    # Get payment record
    payment = db.query(Payment).filter(Payment.reference == reference).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # If webhook already processed, return existing status
    if payment.webhook_received and payment.status == "success":
        return {
            "status": "success",
            "message": "Payment already verified and subscription activated",
            "already_processed": True,
            "payment": {
                "reference": payment.reference,
                "amount": payment.amount,
                "currency": payment.currency,
                "paid_at": payment.paid_at,
            },
        }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                headers=headers,
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Payment verification failed: {response.text}",
                )

            data = response.json()

            if not data.get("status"):
                raise HTTPException(
                    status_code=400, detail="Payment verification failed"
                )

            transaction_data = data["data"]

            # Check if payment was successful
            if transaction_data["status"] != "success":
                payment.status = "failed"
                db.commit()
                return {
                    "status": "failed",
                    "message": "Payment was not successful",
                    "transaction_status": transaction_data["status"],
                }

            # Only process if not already processed by webhook
            if not payment.webhook_received:
                await process_subscription(payment, transaction_data, db)

            return {
                "status": "success",
                "message": "Payment verified and subscription activated",
                "payment": {
                    "reference": payment.reference,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "paid_at": payment.paid_at,
                },
            }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500, detail=f"Error connecting to payment service: {str(e)}"
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
        PAYSTACK_SECRET_KEY.encode("utf-8"), body, hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(signature, computed_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Parse webhook data
    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data", {})

    # Handle charge.success event
    if event == "charge.success":
        reference = data.get("reference")

        if not reference:
            return {"status": "ignored", "reason": "No reference"}

        # Find payment record
        payment = db.query(Payment).filter(Payment.reference == reference).first()

        if not payment:
            return {"status": "ignored", "reason": "Payment not found"}

        # Check if already processed
        if payment.webhook_received and payment.status == "success":
            return {"status": "already_processed"}

        # Mark webhook as received
        payment.webhook_received = True
        payment.webhook_received_at = datetime.utcnow()
        db.commit()

        # Process subscription
        await process_subscription(payment, data, db)

    return {"status": "success"}


@router.get(
    "/project/{project_id}/payment-history", summary="Get project payment history"
)
async def get_project_payment_history(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """
    Get payment history for a project.
    """
    # Verify user has access to project
    project = get_project_with_access(project_id, user, db)

    # Get payments
    payments = (
        db.query(Payment)
        .filter(Payment.project_id == project_id)
        .order_by(desc(Payment.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    total = db.query(Payment).filter(Payment.project_id == project_id).count()

    return {
        "payments": [
            {
                "id": p.id,
                "reference": p.reference,
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status,
                "provider": p.provider,
                "plan_name": p.plan.name if p.plan else None,
                "paid_at": p.paid_at,
                "created_at": p.created_at,
            }
            for p in payments
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def process_subscription(payment: Payment, transaction_data: dict, db: Session):
    """
    Process subscription after successful payment.
    Updates payment and project subscription status.
    """
    from app.services.email import send_subscription_email

    try:
        # Update payment status
        payment.status = "success"
        payment.paid_at = datetime.utcnow()
        payment.provider_response = transaction_data

        # Get or create project subscription
        subscription = (
            db.query(ProjectSubscription)
            .filter(
                and_(
                    ProjectSubscription.project_id == payment.project_id,
                    ProjectSubscription.is_active == True,
                )
            )
            .first()
        )

        plan = db.query(PricingPlan).filter(PricingPlan.id == payment.plan_id).first()

        if not plan:
            raise Exception("Plan not found")

        now = datetime.utcnow()

        if subscription:
            # Upgrade/renew existing subscription
            subscription.plan_id = plan.id
            subscription.start_date = now
            subscription.end_date = now + timedelta(days=plan.duration_days or 30)
            subscription.is_active = True
        else:
            # Create new subscription
            subscription = ProjectSubscription(
                project_id=payment.project_id,
                plan_id=plan.id,
                start_date=now,
                end_date=now + timedelta(days=plan.duration_days or 30),
                is_active=True,
                auto_renew=True,
            )
            db.add(subscription)

        db.flush()

        # Link payment to subscription
        payment.subscription_id = subscription.id

        db.commit()
        db.refresh(payment)
        db.refresh(subscription)

        # Send confirmation email
        try:
            user = db.query(User).filter(User.id == payment.user_id).first()
            project = db.query(Project).filter(Project.id == payment.project_id).first()

            if user and project:
                await send_subscription_email(
                    to_email=user.email,
                    user_name=user.full_name or user.email,
                    project_name=project.name,
                    plan_name=plan.name,
                    amount=payment.amount,
                    currency=payment.currency,
                    subscription_end_date=subscription.end_date,
                )
        except Exception as e:
            print(f"Failed to send email: {str(e)}")

        return subscription

    except Exception as e:
        payment.status = "failed"
        db.commit()
        raise e
