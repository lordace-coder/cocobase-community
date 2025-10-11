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
from app.services.redis_worker import get_redis_instance, get_pubsub_redis

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


# CRITICAL FIX: Use the SAME Redis instance for both publish and subscribe
# The issue is likely that get_redis_instance() and get_pubsub_redis()
# are returning different Redis connections


@router.post("/{webhook_uuid}")
async def receive_webhook(
    webhook_uuid: str,
    request: Request,
):
    """
    Receive webhook payloads and publish them to Redis pub/sub.
    """
    instance = get_redis_instance()
    if instance is None:
        raise HTTPException(status_code=503, detail="Redis connection not available")

    try:
        body_bytes = await request.body()

        try:
            if body_bytes:
                body_content = json.loads(body_bytes.decode("utf-8"))
            else:
                body_content = None
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_content = (
                body_bytes.decode("utf-8", errors="replace") if body_bytes else None
            )

        webhook_data_dict = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": request.method,
            "headers": dict(request.headers),
            "body": body_content,
            "content_type": request.headers.get("content-type"),
            "query_params": dict(request.query_params),
        }

        message_payload = json.dumps(webhook_data_dict)
        channel_name = f"webhook:{webhook_uuid}"

        logger.info(f"📤 Publishing to channel: {channel_name}")
        logger.info(
            f"📦 Message payload: {message_payload[:200]}..."
        )  # Log first 200 chars

        publish_result = await instance.publish(channel_name, message_payload)

        logger.info(f"✅ Publish result (subscribers notified): {publish_result}")

        # ADD WARNING if no subscribers
        if publish_result == 0:
            logger.warning(f"⚠️ No subscribers listening on channel: {channel_name}")

        return {
            "status": "received",
            "timestamp": webhook_data_dict["timestamp"],
            "uuid": webhook_uuid,
            "subscribers_notified": publish_result,
            "message": "Webhook received and published successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in receive_webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/stream/{webhook_uuid}")
async def stream_webhook_events(webhook_uuid: str):
    """
    Stream webhook events in real-time using Server-Sent Events (SSE).
    """
    instance = get_redis_instance()
    if instance is None:
        raise HTTPException(status_code=503, detail="Redis connection not available")

    async def event_stream():
        redis_client = None
        pubsub = None

        try:
            # CRITICAL: Use get_pubsub_redis() which should create a properly configured pubsub client
            redis_client = await get_pubsub_redis()

            # IMPORTANT: PubSub MUST have decode_responses=False (works with bytes)
            pubsub = redis_client.pubsub()

            channel_name = f"webhook:{webhook_uuid}"
            await pubsub.subscribe(channel_name)
            logger.info(f"🔔 Subscribed to channel: {channel_name}")

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

            # Send a heartbeat every 15 seconds to keep connection alive
            last_heartbeat = asyncio.get_event_loop().time()

            # Listen for messages
            while True:
                try:
                    # Wait for message with timeout to allow heartbeat
                    message = await asyncio.wait_for(
                        pubsub.get_message(
                            ignore_subscribe_messages=False, timeout=1.0
                        ),
                        timeout=15.0,
                    )

                    if message:
                        logger.info(f"📨 Received message type: {message['type']}")

                        if message["type"] == "subscribe":
                            logger.info(f"✅ Successfully subscribed to {channel_name}")
                            continue

                        if message["type"] == "message":
                            try:
                                message_data = message["data"]
                                if isinstance(message_data, bytes):
                                    message_data = message_data.decode("utf-8")

                                webhook_data = json.loads(message_data)
                                logger.info(f"📬 Sending webhook event to client")

                                yield {
                                    "event": "webhook",
                                    "data": json.dumps(webhook_data),
                                }
                                last_heartbeat = asyncio.get_event_loop().time()

                            except json.JSONDecodeError as json_err:
                                logger.error(f"❌ JSON decode error: {json_err}")
                                yield {
                                    "event": "error",
                                    "data": json.dumps(
                                        {
                                            "error": "Failed to parse webhook data",
                                            "raw_data": str(message.get("data", "")),
                                        }
                                    ),
                                }
                    else:
                        # No message received, check if heartbeat needed
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_heartbeat > 15:
                            yield {
                                "event": "heartbeat",
                                "data": json.dumps(
                                    {"timestamp": datetime.utcnow().isoformat() + "Z"}
                                ),
                            }
                            last_heartbeat = current_time

                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps(
                            {"timestamp": datetime.utcnow().isoformat() + "Z"}
                        ),
                    }
                    last_heartbeat = asyncio.get_event_loop().time()

        except asyncio.CancelledError:
            logger.info(f"👋 Client disconnected from webhook stream: {webhook_uuid}")
        except Exception as e:
            logger.error(f"❌ Error in event stream: {e}", exc_info=True)
            try:
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    ),
                }
            except:
                pass
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel_name)
                    await pubsub.close()
                    logger.info(f"🔌 Closed pubsub for webhook: {webhook_uuid}")
                except Exception as cleanup_err:
                    logger.error(f"Error closing pubsub: {cleanup_err}")

            if redis_client:
                try:
                    await redis_client.close()
                    logger.info(f"🔌 Closed Redis client for webhook: {webhook_uuid}")
                except Exception as cleanup_err:
                    logger.error(f"Error closing Redis client: {cleanup_err}")

    return EventSourceResponse(
        event_stream(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.get("/stream/{webhook_uuid}")
async def stream_webhook_events(
    webhook_uuid: str,
):
    """
    Stream webhook events in real-time using Server-Sent Events (SSE).

    This endpoint creates a persistent connection that streams webhook
    data as it arrives. It subscribes to a Redis pub/sub channel and
    forwards messages to the client using SSE format.

    Args:
        webhook_uuid: The unique identifier for the webhook channel

    Returns:
        EventSourceResponse: SSE stream of webhook events
    """
    # Check if Redis instance is available
    instance = get_redis_instance()
    if instance is None:
        raise HTTPException(status_code=503, detail="Redis connection not available")

    async def event_stream():
        """
        Generator function that yields SSE events from Redis pub/sub.

        Yields:
            dict: SSE event data containing webhook information
        """
        # Create a NEW Redis connection specifically for pubsub
        # PubSub requires decode_responses=False (binary mode)
        redis_client = None
        pubsub = None

        try:
            # Get a dedicated Redis client for pubsub
            redis_client = await get_pubsub_redis()

            pubsub = redis_client.pubsub()

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
                        # Decode the message data (it comes as bytes)
                        message_data = message["data"]
                        if isinstance(message_data, bytes):
                            message_data = message_data.decode("utf-8")

                        # Parse the webhook data from Redis
                        webhook_data = json.loads(message_data)

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
                                    "raw_data": str(message.get("data", "")),
                                }
                            ),
                        }
                    except Exception as parse_err:
                        logger.error(
                            f"Error parsing message: {parse_err}", exc_info=True
                        )

        except asyncio.CancelledError:
            # Handle client disconnection gracefully
            logger.info(f"Client disconnected from webhook stream: {webhook_uuid}")
        except Exception as e:
            logger.error(f"Error in event stream: {e}", exc_info=True)
            # Send error event to client
            try:
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    ),
                }
            except:
                pass
        finally:
            # Clean up pubsub and Redis connections
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel_name)
                    await pubsub.close()
                    logger.info(f"Closed pubsub for webhook: {webhook_uuid}")
                except Exception as cleanup_err:
                    logger.error(f"Error closing pubsub: {cleanup_err}")

            if redis_client:
                try:
                    await redis_client.close()
                    logger.info(f"Closed Redis client for webhook: {webhook_uuid}")
                except Exception as cleanup_err:
                    logger.error(f"Error closing Redis client: {cleanup_err}")

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
    instance = get_redis_instance()

    try:
        if instance is None:
            redis_status = "not initialized"
        else:
            await instance.ping()
            redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
        logger.error(f"Redis health check failed: {e}")

    return {
        "status": "healthy" if redis_status == "connected" else "degraded",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


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
    instance = get_redis_instance()
    if instance is None:
        raise HTTPException(status_code=503, detail="Redis connection not available")

    try:
        # Check if the webhook channel exists by looking for subscribers
        channel_name = f"webhook:{webhook_uuid}"
        subscriber_count = await instance.pubsub_numsub(channel_name)

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
