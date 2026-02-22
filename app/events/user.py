from sqlalchemy import event
from app.models.user import User
from app.services.email import send_email
import asyncio
import threading


async def send_welcome_email_async(email: str, name: str):
    """Send welcome email asynchronously"""
    try:
        await send_email(
            to=email,
            subject="Welcome to Cocobase! 🎉",
            template="1a94b9c6-c0d4-4fa1-9dcf-3c82bad4970f",
            context={"username": name},
        )
        print(f"Welcome email sent to {email}")
    except Exception as e:
        print(f"Failed to send welcome email to {email}: {str(e)}")


def trigger_welcome_email(email: str, name: str):
    """Trigger async email in a synchronous context"""
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_welcome_email_async(email, name))
        loop.close()
    except Exception as e:
        print(f"Error triggering welcome email: {str(e)}")


@event.listens_for(User, "after_insert")
def send_welcome_email_on_user_creation(mapper, connection, target: User):
    """Event listener that triggers after a user is inserted"""
    print("called user create event")
    thread = threading.Thread(
        target=trigger_welcome_email, args=(target.email, target.username or "User")
    )
    thread.daemon = True
    thread.start()
