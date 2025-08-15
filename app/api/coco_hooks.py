# ROUTES FOR COCO HOOKS SERVICE
import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as redis
from app.services.redis_worker import instance, REDIS_URL

# Set up logging
logger = logging.getLogger(__name__)

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
    Creates a new connection if the instance is not available or not async.
    """
    try:
        # Check if the instance is an async Redis client
        if hasattr(instance, "publish") and asyncio.iscoroutinefunction(
            instance.publish
        ):
            return instance
        else:
            # Create a new async Redis client
            logger.warning("Creating new Redis connection as instance is not async")
            return redis.from_url(REDIS_URL, decode_responses=False)
    except Exception as e:
        logger.error(f"Error getting Redis client: {e}")
        # Fallback to creating a new connection
        return redis.from_url(REDIS_URL, decode_responses=False)


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
    temp_redis = None
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
        webhook_data_dict = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": request.method,
            "headers": dict(request.headers),
            "body": body_content,
            "content_type": request.headers.get("content-type"),
            "query_params": dict(request.query_params),
        }

        # Serialize the webhook data for Redis (avoid Pydantic model issues)
        message_payload = json.dumps(webhook_data_dict)

        # Publish to Redis pub/sub channel named after the UUID
        channel_name = f"webhook:{webhook_uuid}"

        try:
            # Try using the dependency-injected client first
            logger.debug(f"Publishing to channel: {channel_name}")
            publish_result = await redis_client.publish(channel_name, message_payload)
            logger.debug(f"Publish result: {publish_result}")

        except Exception as redis_err:
            logger.error(f"Error with dependency Redis client: {redis_err}")
            # Fallback: create a temporary Redis connection
            try:
                temp_redis = redis.from_url(REDIS_URL, decode_responses=False)
                logger.info("Created temporary Redis connection for publish")
                publish_result = await temp_redis.publish(channel_name, message_payload)
                logger.debug(f"Temporary Redis publish result: {publish_result}")
            except Exception as temp_err:
                logger.error(f"Temporary Redis connection failed: {temp_err}")
                raise HTTPException(
                    status_code=500, detail=f"Redis publish failed: {str(temp_err)}"
                )

        return {
            "status": "received",
            "timestamp": webhook_data_dict["timestamp"],
            "uuid": webhook_uuid,
            "subscribers_notified": publish_result,
            "message": "Webhook received and published successfully",
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in receive_webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing webhook: {str(e)}"
        )
    finally:
        # Clean up temporary Redis connection if created
        if temp_redis:
            try:
                await temp_redis.close()
            except Exception as cleanup_err:
                logger.error(f"Error closing temporary Redis connection: {cleanup_err}")


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
        # Create a dedicated Redis connection for pub/sub
        pubsub_redis = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = pubsub_redis.pubsub()

        try:
            # Subscribe to the specific channel for this webhook UUID
            channel_name = f"webhook:{webhook_uuid}"
            await pubsub.subscribe(channel_name)
            logger.info(f"Subscribed to channel: {channel_name}")

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

                    except json.JSONDecodeError as json_err:
                        logger.error(f"JSON decode error: {json_err}")
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
            logger.info(f"Client disconnected from webhook stream: {webhook_uuid}")
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
            # Send error event to client
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": str(e), "timestamp": datetime.utcnow().isoformat() + "Z"}
                ),
            }
        finally:
            # Clean up Redis connection
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub_redis.close()
                logger.info(f"Cleaned up Redis connection for webhook: {webhook_uuid}")
            except Exception as cleanup_err:
                logger.error(f"Error during cleanup: {cleanup_err}")

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
async def health_check():
    """
    Health check endpoint to verify service and Redis connectivity.

    Returns:
        dict: Service status and Redis connection status
    """
    redis_status = "unknown"
    temp_redis = None

    try:
        # Create a test Redis connection
        temp_redis = redis.from_url(REDIS_URL)
        await temp_redis.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
        logger.error(f"Redis health check failed: {e}")
    finally:
        if temp_redis:
            try:
                await temp_redis.close()
            except Exception:
                pass

    return {
        "status": "healthy" if redis_status == "connected" else "degraded",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Additional utility endpoint to get webhook statistics (optional)
@router.get("/stats/{webhook_uuid}")
async def get_webhook_stats(webhook_uuid: str):
    """
    Get statistics about a specific webhook endpoint.

    Note: This is a basic implementation. In production, you might want
    to store more detailed metrics in Redis or a separate database.

    Args:
        webhook_uuid: The unique identifier for the webhook

    Returns:
        dict: Basic webhook statistics
    """
    temp_redis = None
    try:
        # Create a temporary Redis connection for stats
        temp_redis = redis.from_url(REDIS_URL)

        # Check if the webhook channel exists by looking for subscribers
        channel_name = f"webhook:{webhook_uuid}"
        subscriber_count = await temp_redis.pubsub_numsub(channel_name)

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
        logger.error(f"Error getting webhook stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving webhook stats: {str(e)}"
        )
    finally:
        if temp_redis:
            try:
                await temp_redis.close()
            except Exception:
                pass
