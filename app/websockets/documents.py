from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import json
import asyncio
import logging
from app.core.database import get_db
from app.services.redis_worker import get_redis_instance, get_pubsub_redis
from app.models.app_client import Project
from app.models.collections import Collection, Document
from app.schemas.collections import DocumentSchema
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/realtime", tags=["RealTime"])
logger = logging.getLogger(__name__)


class RealtimeEvent:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


async def authenticate_websocket(
    websocket: WebSocket, db: Session
) -> Optional[Project]:
    """Authenticate WebSocket connection and return project"""
    try:
        # Wait for authentication message
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)

        api_key = auth_data.get("api_key")
        if not api_key:
            await websocket.send_json({"error": "API key is required"})
            return None

        # Verify API key
        project = db.query(Project).filter(Project.api_key == api_key).first()

        if not project:
            await websocket.send_json(
                {"error": "Invalid API key", "error_detail": "Project not found"}
            )
            return None

        logger.info(f"WebSocket authenticated for project: {project.id}")
        return project

    except asyncio.TimeoutError:
        logger.warning("WebSocket authentication timeout")
        await websocket.send_json({"error": "Authentication timeout"})
        return None
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.send_json(
            {"error": "Authentication failed", "error_detail": str(e)}
        )
        return None


async def subscribe_to_collection(collection_id: str, websocket: WebSocket):
    """Subscribe to a collection's events and forward to WebSocket"""
    redis_conn = None
    pubsub = None

    try:
        redis_conn = await get_pubsub_redis()
        pubsub = redis_conn.pubsub()
        channel = f"collection:{collection_id}"

        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")

        # Keep listening for messages
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Decode the message data
                    data = json.loads(message["data"].decode("utf-8"))
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")
                    break

    except asyncio.CancelledError:
        logger.info(f"Subscription task cancelled for collection: {collection_id}")
        raise
    except Exception as e:
        logger.error(f"Error in subscription: {e}")
        raise
    finally:
        if pubsub:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        if redis_conn:
            await redis_conn.close()


@router.websocket("/collections/{collection_id}")
async def watch_collection(
    websocket: WebSocket, collection_id: str, db: Session = Depends(get_db)
):
    """WebSocket endpoint for watching collection changes"""
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for collection: {collection_id}")

    try:
        # Authenticate the connection
        project = await authenticate_websocket(websocket, db)
        if not project:
            logger.warning("Authentication failed, closing connection")
            await websocket.close(code=1008)
            return

        # Verify collection exists and belongs to project
        collection = (
            db.query(Collection)
            .filter(
                Collection.name == collection_id, Collection.project_id == project.id
            )
            .first()
        )

        if not collection:
            logger.warning(f"Collection not found or access denied: {collection_id}")
            await websocket.send_json(
                {"error": "Collection not found or access denied"}
            )
            await websocket.close(code=1008)
            return

        # Send confirmation
        await websocket.send_json(
            {"event": "connected", "collection_id": collection_id}
        )
        logger.info(f"WebSocket connected to collection: {collection_id}")

        # Create tasks
        redis_task = asyncio.create_task(
            subscribe_to_collection(collection_id, websocket)
        )

        async def handle_websocket_messages():
            """Handle incoming WebSocket messages"""
            try:
                while True:
                    message = await websocket.receive()

                    # Handle different message types
                    if message["type"] == "websocket.disconnect":
                        logger.info("Client disconnected")
                        break
                    elif message["type"] == "websocket.receive":
                        if "text" in message:
                            data = message["text"]
                            if data == "ping":
                                await websocket.send_json({"event": "pong"})
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error handling websocket messages: {e}")

        ws_task = asyncio.create_task(handle_websocket_messages())

        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [redis_task, ws_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Unexpected error in watch_collection: {e}")
    finally:
        logger.info(f"Closing WebSocket connection for collection: {collection_id}")
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing websocket: {e}")


async def notify_collection_watchers(
    collection_id: str, document: Document, event: str
):
    """
    Publish a document event to all watchers of a collection.
    """
    try:
        redis_client = get_redis_instance()
        channel = f"collection:{collection_id}"

        payload = {
            "event": event,
            "data": jsonable_encoder(DocumentSchema.model_validate(document)),
            "collection_id": collection_id,
        }

        await redis_client.publish(channel, json.dumps(payload))
        logger.debug(f"Published {event} event to {channel}")
    except Exception as e:
        logger.error(f"Error notifying collection watchers: {e}")
