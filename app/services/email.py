import httpx
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("MAILER_API_KEY")
if not key:
    raise ValueError("MAILER_API_KEY is not set in the environment variables.")


async def send_email(
    to: str | list, subject: str, template: str, context: dict = None
) -> bool:
    """
    Send email asynchronously using httpx

    Args:
        to: Email address(es) - string or list
        subject: Email subject line
        template: Template key/identifier
        context: Dictionary of template variables (default: {"name": "John Doe"})

    Returns:
        bool: True if successful, False otherwise
    """
    if isinstance(to, str):
        to = [to]
    else:
        to = list(set(to))

    if context is None:
        context = {"name": "John Doe"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://coco-mailer-api.vercel.app/api/send-mail/{key}?template_key={template}",
                json={
                    "recipient_list": to,
                    "subject": subject,
                    "is_html": True,
                    "context": context,
                },
            )
            print(response.json(), "reponse")
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        print(f"Error sending email: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


async def send_subscription_email(
    to_email,
    user_name,
    plan_name,
    amount,
    currency,
    subscription_end_date,
):
    await send_email(
        to=to_email,
        subject="Successfull Subscription",
        context={
            "user_name": user_name,
            "plan_name": plan_name,
            "amount": amount,
            "currency": currency,
            "subscription_end_date": subscription_end_date,
        },
        template="98628178-1446-427f-88f5-aa4ac29ecce2",
    )
