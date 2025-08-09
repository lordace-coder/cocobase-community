# ROUTES FOR COCO HOOKS SERVICE
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as redis
from app.services.redis_worker import instance, REDIS_URL

router = APIRouter(prefix="/coco-hooks", tags=["Coco Hooks"])


# Pydantic models for API responses
class WebhookURLResponse(BaseModel):
    """Response model for new webhook URL generation"""

    uuid: str
    webhook_url: str
    stream_url: str


class WebhookData(BaseModel):
    """Model representing webhook data structure"""

    timestamp: str
    method: str
    headers: Dict[str, str]
    body: Any
    content_type: Optional[str]
    query_params: Dict[str, str]


# Dependency to get Redis connection
async def get_redis() -> redis.Redis:
    """
    Dependency function to provide Redis connection instance.
    Uses the existing Redis instance from the worker service.
    """
    return instance # type: ignore


@router.get("/new-url", response_model=WebhookURLResponse)
async def generate_new_webhook_url(request: Request):
    """
    Generate a new unique webhook URL for testing.

    This endpoint creates a unique UUID that serves as both:
    - The webhook endpoint identifier
    - The Redis pub/sub channel name for real-time streaming

    Returns:
        WebhookURLResponse: Contains the UUID, webhook URL, and streaming URL
    """
    # Generate a unique UUID for this webhook mailbox
    webhook_uuid = str(uuid.uuid4())

    # Construct the base URL from the request
    base_url = f"{request.url.scheme}://{request.url.netloc}"

    # Build the webhook and streaming URLs
    webhook_url = f"{base_url}/coco-hooks/{webhook_uuid}"
    stream_url = f"{base_url}/coco-hooks/stream/{webhook_uuid}"

    return WebhookURLResponse(
        uuid=webhook_uuid, webhook_url=webhook_url, stream_url=stream_url
    )


@router.post("/{webhook_uuid}")
async def receive_webhook(
    webhook_uuid: str, request: Request, redis_client: redis.Redis = Depends(get_redis)
):
    """
    Receive webhook payloads and publish them to Redis pub/sub.

    This endpoint handles incoming webhooks from third-party services.
    It captures all relevant request data and publishes it to a Redis
    channel identified by the webhook UUID.

    Args:
        webhook_uuid: The unique identifier for this webhook endpoint
        request: FastAPI request object containing headers, body, etc.
        redis_client: Redis connection for publishing messages

    Returns:
        dict: Confirmation message with timestamp
    """
    try:
        # Read the request body
        body_bytes = await request.body()

        # Try to decode body as JSON if possible, otherwise keep as string
        try:
            if body_bytes:
                body_content = json.loads(body_bytes.decode("utf-8"))
            else:
                body_content = None
        except (json.JSONDecodeError, UnicodeDecodeError):
            # If JSON parsing fails, store as raw string
            body_content = (
                body_bytes.decode("utf-8", errors="replace") if body_bytes else None
            )

        # Extract request metadata
        webhook_data = WebhookData(
            timestamp=datetime.utcnow().isoformat() + "Z",
            method=request.method,
            headers=dict(request.headers),
            body=body_content,
            content_type=request.headers.get("content-type"),
            query_params=dict(request.query_params),
        )

        # Serialize the webhook data for Redis
        message_payload = webhook_data.json()

        try:
            # Publish to Redis pub/sub channel named after the UUID
            channel_name = f"webhook:{webhook_uuid}"
            publish_result = await redis_client.publish(channel_name, message_payload)

            if publish_result is None:
                raise HTTPException(
                    status_code=500, detail="Failed to publish message to Redis"
                )

            return {
                "status": "received",
                "timestamp": webhook_data.timestamp,
                "uuid": webhook_uuid,
                "message": "Webhook received and published successfully",
            }

        except redis.RedisError as redis_err:
            raise HTTPException(
                status_code=500, detail=f"Redis publish error: {str(redis_err)}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/stream/{webhook_uuid}")
async def stream_webhook_events(
    webhook_uuid: str, redis_client: redis.Redis = Depends(get_redis)
):
    """
    Stream webhook events in real-time using Server-Sent Events (SSE).

    This endpoint creates a persistent connection that streams webhook
    data as it arrives. It subscribes to a Redis pub/sub channel and
    forwards messages to the client using SSE format.

    Args:
        webhook_uuid: The unique identifier for the webhook channel
        redis_client: Redis connection for subscribing to messages

    Returns:
        EventSourceResponse: SSE stream of webhook events
    """

    async def event_stream():
        """
        Generator function that yields SSE events from Redis pub/sub.

        Yields:
            dict: SSE event data containing webhook information
        """
        # Create a new Redis connection for pub/sub using configured URL
        pubsub_redis = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = pubsub_redis.pubsub()

        try:
            # Subscribe to the specific channel for this webhook UUID
            channel_name = f"webhook:{webhook_uuid}"
            await pubsub.subscribe(channel_name)

            # Send initial connection confirmation
            yield {
                "event": "connected",
                "data": json.dumps(
                    {
                        "status": "connected",
                        "channel": channel_name,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                ),
            }

            # Listen for messages on the subscribed channel
            async for message in pubsub.listen():
                # Skip subscription confirmation messages
                if message["type"] == "subscribe":
                    continue

                if message["type"] == "message":
                    try:
                        # Parse the webhook data from Redis
                        webhook_data = json.loads(message["data"])

                        # Yield as SSE event
                        yield {"event": "webhook", "data": json.dumps(webhook_data)}

                    except json.JSONDecodeError:
                        # Handle malformed JSON gracefully
                        yield {
                            "event": "error",
                            "data": json.dumps(
                                {
                                    "error": "Failed to parse webhook data",
                                    "raw_data": message["data"],
                                }
                            ),
                        }

        except asyncio.CancelledError:
            # Handle client disconnection gracefully
            pass
        except Exception as e:
            # Send error event to client
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}
                ),
            }
        finally:
            # Clean up Redis connection
            await pubsub.unsubscribe(channel_name)
            await pubsub_redis.close()

    # Return SSE response with CORS headers for browser compatibility
    return EventSourceResponse(
        event_stream(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.get("/health")
async def health_check(redis_client: redis.Redis = Depends(get_redis)):
    """
    Health check endpoint to verify service and Redis connectivity.

    Returns:
        dict: Service status and Redis connection status
    """
    try:
        # Test Redis connection
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Additional utility endpoint to get webhook statistics (optional)
@router.get("/stats/{webhook_uuid}")
async def get_webhook_stats(
    webhook_uuid: str, redis_client: redis.Redis = Depends(get_redis)
):
    """
    Get statistics about a specific webhook endpoint.

    Note: This is a basic implementation. In production, you might want
    to store more detailed metrics in Redis or a separate database.

    Args:
        webhook_uuid: The unique identifier for the webhook
        redis_client: Redis connection

    Returns:
        dict: Basic webhook statistics
    """
    try:
        # Check if the webhook channel exists by looking for subscribers
        channel_name = f"webhook:{webhook_uuid}"
        subscriber_count = await redis_client.pubsub_numsub(channel_name)

        return {
            "webhook_uuid": webhook_uuid,
            "channel": channel_name,
            "active_subscribers": subscriber_count[0][1] if subscriber_count else 0,
            "status": (
                "active"
                if subscriber_count and subscriber_count[0][1] > 0
                else "inactive"
            ),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving webhook stats: {str(e)}"
        )
