import secrets
import bcrypt
import httpx
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def hash_password(raw_password):
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password, hashed_password):
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_api_key():
    return secrets.token_urlsafe(30)


async def handle_webhook_call(
    url: str,
    data: dict,
    isUpdate: bool = False,
    max_retries: int = 3,
    timeout: float = 10.0,
) -> bool:
    """
    Send webhook notification asynchronously with retry logic.

    Args:
        url: Webhook URL to send the request to
        data: Payload data to send (should include event_type, document_id, data, etc.)
        isUpdate: Whether this is an update operation (deprecated, use event_type in data)
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        bool: True if webhook succeeded, False otherwise
    """
    if not url:
        logger.warning("Webhook call attempted with empty URL")
        return False

    # The payload is already formatted with event_type from the event listener
    # Keep backwards compatibility by still supporting the old isUpdate flag
    payload = data if isinstance(data, dict) and "event_type" in data else {"data": data, "isUpdate": isUpdate}

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Cocobase-Webhook/1.0",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=payload, headers=headers)

                if response.is_success:
                    logger.info(f"Webhook sent successfully to {url}")
                    return True

                # Log non-success status codes
                logger.warning(
                    f"Webhook failed with status {response.status_code} to {url}. "
                    f"Attempt {attempt + 1}/{max_retries}"
                )

                # Don't retry on client errors (4xx), only on server errors (5xx)
                if 400 <= response.status_code < 500:
                    logger.error(
                        f"Webhook rejected by client (status {response.status_code}): {url}"
                    )
                    return False

            except httpx.TimeoutException:
                logger.warning(
                    f"Webhook timeout to {url}. Attempt {attempt + 1}/{max_retries}"
                )
            except httpx.RequestError as e:
                logger.error(
                    f"Webhook request error to {url}: {str(e)}. "
                    f"Attempt {attempt + 1}/{max_retries}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending webhook to {url}: {str(e)}. "
                    f"Attempt {attempt + 1}/{max_retries}"
                )

            # Exponential backoff before retry
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)

    logger.error(f"Webhook failed after {max_retries} attempts to {url}")
    return False



