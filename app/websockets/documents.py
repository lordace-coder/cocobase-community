from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
import asyncio
import logging
from app.core.database import get_db
from app.services.redis_worker import get_redis_instance, get_pubsub_redis
from app.models.app_client import Project
from app.models.collections import Collection, Document
from app.schemas.collections import DocumentSchema
from fastapi.encoders import jsonable_encoder
from app.api.collections.utilities import parse_filter_expression, extract_field_and_operator

router = APIRouter(prefix="/realtime", tags=["RealTime"])
logger = logging.getLogger(__name__)


class RealtimeEvent:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def matches_filters(document_data: Dict[str, Any], filters: Dict[str, str]) -> bool:
    """
    Check if a document matches the provided filters.

    Uses the same filtering logic as the REST API for consistency.

    Args:
        document_data: The document data to check
        filters: Dictionary of filters (e.g., {"status": "active", "age_gte": "18"})

    Returns:
        True if document matches all filters, False otherwise

    Examples:
        >>> matches_filters({"status": "active", "age": 25}, {"status": "active"})
        True
        >>> matches_filters({"status": "inactive", "age": 25}, {"status": "active"})
        False
        >>> matches_filters({"age": 25}, {"age_gte": "18"})
        True
        >>> matches_filters({"name": "John Doe"}, {"name_contains": "john"})
        True
    """
    if not filters:
        # No filters means match everything
        return True

    try:
        for key, value in filters.items():
            # Extract field name and operator
            field, operator = extract_field_and_operator(key)

            # Get the document field value
            doc_value = document_data.get(field)

            # Handle missing fields
            if doc_value is None:
                if operator == "isnull":
                    # Check if expecting null
                    expected_null = value.lower() in ("true", "1")
                    if not expected_null:
                        return False
                else:
                    # Field doesn't exist and we're not checking for null
                    return False
                continue

            # Convert document value to string for comparison
            doc_value_str = str(doc_value)

            # Apply operator logic
            if operator == "eq":
                if doc_value_str != str(value):
                    return False

            elif operator == "ne":
                if doc_value_str == str(value):
                    return False

            elif operator == "contains":
                if str(value).lower() not in doc_value_str.lower():
                    return False

            elif operator == "startswith":
                if not doc_value_str.lower().startswith(str(value).lower()):
                    return False

            elif operator == "endswith":
                if not doc_value_str.lower().endswith(str(value).lower()):
                    return False

            elif operator == "in":
                allowed_values = [v.strip() for v in str(value).split(",")]
                if doc_value_str not in allowed_values:
                    return False

            elif operator == "notin":
                disallowed_values = [v.strip() for v in str(value).split(",")]
                if doc_value_str in disallowed_values:
                    return False

            elif operator in ("lt", "lte", "gt", "gte"):
                # Numeric comparisons
                try:
                    doc_num = float(doc_value)
                    filter_num = float(value)

                    if operator == "lt" and not (doc_num < filter_num):
                        return False
                    elif operator == "lte" and not (doc_num <= filter_num):
                        return False
                    elif operator == "gt" and not (doc_num > filter_num):
                        return False
                    elif operator == "gte" and not (doc_num >= filter_num):
                        return False
                except (ValueError, TypeError):
                    # Can't compare non-numeric values
                    return False

            elif operator == "isnull":
                expected_null = value.lower() in ("true", "1")
                is_null = doc_value is None
                if is_null != expected_null:
                    return False

        # All filters passed
        return True

    except Exception as e:
        logger.error(f"Error matching filters: {e}")
        # On error, don't send the event
        return False


async def authenticate_websocket(
    websocket: WebSocket, db: Session
) -> Optional[tuple[Project, Dict[str, str]]]:
    """
    Authenticate WebSocket connection and return project with optional filters.

    Returns:
        Tuple of (Project, filters_dict) or None if authentication fails
    """
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

        # Extract optional filters from auth message
        filters = auth_data.get("filters", {})

        if filters:
            logger.info(f"WebSocket authenticated for project: {project.id} with filters: {filters}")
        else:
            logger.info(f"WebSocket authenticated for project: {project.id} (no filters)")

        return project, filters

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


async def subscribe_to_collection(
    collection_id: str, websocket: WebSocket, filters: Dict[str, str] = None
):
    """
    Subscribe to a collection's events and forward to WebSocket.

    Applies client-side filtering before sending events.

    Args:
        collection_id: The collection to watch
        websocket: The WebSocket connection
        filters: Optional filters to apply (e.g., {"status": "active", "age_gte": "18"})
    """
    redis_conn = None
    pubsub = None

    try:
        redis_conn = await get_pubsub_redis()
        pubsub = redis_conn.pubsub()
        channel = f"collection:{collection_id}"

        await pubsub.subscribe(channel)
        if filters:
            logger.info(f"Subscribed to channel: {channel} with filters: {filters}")
        else:
            logger.info(f"Subscribed to channel: {channel} (no filters)")

        # Keep listening for messages
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Decode the message data
                    data = json.loads(message["data"].decode("utf-8"))

                    # Apply filters if provided
                    if filters:
                        document_data = data.get("data", {})

                        # For DELETE events, we might not have full data
                        # so we should send it regardless
                        if data.get("event") == RealtimeEvent.DELETE:
                            await websocket.send_json(data)
                            logger.debug(f"Sent DELETE event (bypassed filters)")
                        else:
                            # Check if document matches filters
                            if matches_filters(document_data, filters):
                                await websocket.send_json(data)
                                logger.debug(f"Sent {data.get('event')} event (matched filters)")
                            else:
                                logger.debug(f"Skipped {data.get('event')} event (didn't match filters)")
                    else:
                        # No filters, send everything
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
    """
    WebSocket endpoint for watching collection changes with optional filtering.

    Client authentication message format:
    {
        "api_key": "your-api-key",
        "filters": {
            "status": "active",           // Exact match
            "age_gte": "18",              // Greater than or equal
            "name_contains": "john",      // Case-insensitive contains
            "role_in": "admin,moderator"  // In list
        }
    }

    Supported filter operators:
    - eq (default), ne, lt, gt, lte, gte
    - contains, startswith, endswith
    - in, notin, isnull

    Events sent to client:
    {
        "event": "create|update|delete",
        "collection_id": "collection_name",
        "data": { ... }  // Document data
    }
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for collection: {collection_id}")

    try:
        # Authenticate the connection and get filters
        auth_result = await authenticate_websocket(websocket, db)
        if not auth_result:
            logger.warning("Authentication failed, closing connection")
            await websocket.close(code=1008)
            return

        project, filters = auth_result

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

        # Send confirmation with filter info
        confirmation = {
            "event": "connected",
            "collection_id": collection_id,
        }
        if filters:
            confirmation["filters"] = filters
        await websocket.send_json(confirmation)
        logger.info(f"WebSocket connected to collection: {collection_id}")

        # Create tasks with filters
        redis_task = asyncio.create_task(
            subscribe_to_collection(collection_id, websocket, filters)
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
    collection_id: str, document: Document, event: str, old_data: dict = None
):
    """
    Publish a document event to all watchers of a collection.

    Args:
        collection_id: The collection name
        document: The document that changed
        event: Event type (create, update, delete)
        old_data: The previous document data (for UPDATE events)
    """
    try:
        redis_client = get_redis_instance()
        channel = f"collection:{collection_id}"

        payload = {
            "event": event,
            "data": jsonable_encoder(DocumentSchema.model_validate(document)),
            "collection_id": collection_id,
        }

        # Include old_data for UPDATE events to help with filtering
        if event == RealtimeEvent.UPDATE and old_data:
            payload["old_data"] = old_data

        await redis_client.publish(channel, json.dumps(payload))
        logger.debug(f"Published {event} event to {channel}")
    except Exception as e:
        logger.error(f"Error notifying collection watchers: {e}")


# ============================================
# GLOBAL PROJECT BROADCAST
# ============================================


async def subscribe_to_project_broadcast(project_id: str, websocket: WebSocket):
    """Subscribe to project-wide broadcast channel."""
    redis_conn = None
    pubsub = None

    try:
        redis_conn = await get_pubsub_redis()
        pubsub = redis_conn.pubsub()
        channel = f"project:{project_id}:broadcast"

        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to project broadcast: {channel}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"].decode("utf-8"))
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Error sending broadcast message: {e}")
                    break

    except asyncio.CancelledError:
        logger.info(f"Project broadcast subscription cancelled: {project_id}")
        raise
    except Exception as e:
        logger.error(f"Error in project broadcast: {e}")
        raise
    finally:
        if pubsub:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        if redis_conn:
            await redis_conn.close()


@router.websocket("/broadcast")
async def project_broadcast(
    websocket: WebSocket, db: Session = Depends(get_db)
):
    """
    Global project broadcast WebSocket.

    All clients connected to the same project receive messages sent by any client.

    STEP 1 - Client sends ONE authentication message with user info:
    {
        "api_key": "your-api-key",
        "user_id": "optional-user-id",  // For tracking who sent messages
        "user_name": "optional-name"
    }

    STEP 2 - Server responds with confirmation:
    {
        "event": "connected",
        "project_id": "project-id",
        "user_id": "your-user-id"
    }

    STEP 3 - Client sends messages (client to server):
    {
        "type": "message",
        "data": { ... }  // Any JSON data
    }

    STEP 4 - Server broadcasts to all clients (server to all clients):
    {
        "type": "message",
        "user_id": "sender-id",
        "user_name": "sender-name",
        "timestamp": "2024-01-01T12:00:00",
        "data": { ... }
    }
    """
    await websocket.accept()
    logger.info("Project broadcast connection accepted")

    user_id = "anonymous"
    user_name = "Anonymous"

    try:
        # Accept connection and get auth + user info in one message
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)

        api_key = auth_data.get("api_key")
        if not api_key:
            await websocket.send_json({"error": "API key is required"})
            await websocket.close(code=1008)
            return

        # Verify API key
        project = db.query(Project).filter(Project.api_key == api_key).first()
        if not project:
            await websocket.send_json({
                "error": "Invalid API key",
                "error_detail": "Project not found"
            })
            await websocket.close(code=1008)
            return

        # Get optional user info from same auth message
        user_id = auth_data.get("user_id", "anonymous")
        user_name = auth_data.get("user_name", "Anonymous")

        # Send confirmation
        await websocket.send_json({
            "event": "connected",
            "project_id": str(project.id),
            "user_id": user_id
        })
        logger.info(f"Client {user_id} connected to project broadcast: {project.id}")

        # Subscribe to broadcasts AFTER authentication
        redis_task = asyncio.create_task(
            subscribe_to_project_broadcast(str(project.id), websocket)
        )

        async def handle_client_messages():
            """Handle messages from client and broadcast to others"""
            try:
                while True:
                    message = await websocket.receive()

                    if message["type"] == "websocket.disconnect":
                        break
                    elif message["type"] == "websocket.receive":
                        if "text" in message:
                            try:
                                msg_data = json.loads(message["text"])

                                if msg_data.get("type") == "ping":
                                    await websocket.send_json({"type": "pong"})
                                    continue

                                # Broadcast to all clients in project
                                redis_client = get_redis_instance()
                                channel = f"project:{project.id}:broadcast"

                                from datetime import datetime
                                broadcast_payload = {
                                    "type": "message",
                                    "user_id": user_id,
                                    "user_name": user_name,
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "data": msg_data.get("data", msg_data)
                                }

                                await redis_client.publish(
                                    channel, json.dumps(broadcast_payload)
                                )
                                logger.debug(f"Broadcasted message from {user_id}")
                            except json.JSONDecodeError:
                                await websocket.send_json({
                                    "error": "Invalid JSON"
                                })
            except WebSocketDisconnect:
                logger.info("Client disconnected from broadcast")
            except Exception as e:
                logger.error(f"Error in client message handler: {e}")

        client_task = asyncio.create_task(handle_client_messages())

        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [redis_task, client_task], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Error in project broadcast: {e}")
    finally:
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing broadcast websocket: {e}")


# ============================================
# ROOM-BASED CHAT/MESSAGING
# ============================================


# In-memory room storage (consider moving to Redis for production across multiple machines)
active_rooms: Dict[str, Dict[str, Any]] = {}


from fastapi import HTTPException
from app.core.dependencies import require_api_access
from app.models.user import User


@router.get("/rooms")
async def list_rooms(
    proj: tuple[Project, User] = Depends(require_api_access),
):
    """
    List all active rooms for the current project.

    Returns:
        List of rooms with their details
    """
    project, _ = proj
    project_rooms = []

    for room_id, room_data in active_rooms.items():
        if room_data["project_id"] == str(project.id):
            project_rooms.append({
                "id": room_id,
                "title": room_data["title"],
                "created_by": room_data["created_by"],
                "participants": len(room_data["participants"]),
                "participant_list": [
                    {"id": uid, "name": udata["name"]}
                    for uid, udata in room_data["participants"].items()
                ],
                "created_at": room_data["created_at"]
            })

    return {
        "rooms": project_rooms,
        "total": len(project_rooms)
    }


async def subscribe_to_room(room_id: str, websocket: WebSocket):
    """Subscribe to a specific room's messages."""
    redis_conn = None
    pubsub = None

    try:
        redis_conn = await get_pubsub_redis()
        pubsub = redis_conn.pubsub()
        channel = f"room:{room_id}"

        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to room: {channel}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"].decode("utf-8"))
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Error sending room message: {e}")
                    break

    except asyncio.CancelledError:
        logger.info(f"Room subscription cancelled: {room_id}")
        raise
    except Exception as e:
        logger.error(f"Error in room subscription: {e}")
        raise
    finally:
        if pubsub:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        if redis_conn:
            await redis_conn.close()


@router.websocket("/rooms/{room_id}")
async def room_chat(
    websocket: WebSocket, room_id: str, db: Session = Depends(get_db)
):
    """
    Room-based messaging WebSocket.

    Users can create or join rooms by title. Messages sent in a room
    are received by all participants in that room.

    STEP 1 - Client sends ONE message with auth + room info:
    {
        "api_key": "your-api-key",
        "user_id": "optional-user-id",
        "user_name": "optional-name",
        "action": "create|join",  // "create" to create, "join" to join existing
        "room_title": "Optional room title (for create)"
    }

    STEP 2 - Server responds with confirmation:
    {
        "event": "joined",
        "room_id": "room-id",
        "room_title": "Room Title",
        "participants": 3,
        "user_id": "your-user-id"
    }

    STEP 3 - Client sends messages (client to server):
    {
        "type": "message",
        "content": "Hello everyone!"
    }

    STEP 4 - Room events (server to all room participants):
    {
        "type": "message|user_joined|user_left",
        "user_id": "sender-id",
        "user_name": "sender-name",
        "content": "message content",  // Only for "message" type
        "timestamp": "2024-01-01T12:00:00",
        "room_info": {
            "id": "room-id",
            "title": "Room Title",
            "participants": 5  // Current participant count
        }
    }
    """
    await websocket.accept()
    logger.info(f"Room connection accepted for: {room_id}")

    user_id = "anonymous"
    user_name = "Anonymous"

    try:
        # Get auth + room join info in one message
        join_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)

        api_key = join_data.get("api_key")
        if not api_key:
            await websocket.send_json({"error": "API key is required"})
            await websocket.close(code=1008)
            return

        # Verify API key
        project = db.query(Project).filter(Project.api_key == api_key).first()
        if not project:
            await websocket.send_json({
                "error": "Invalid API key",
                "error_detail": "Project not found"
            })
            await websocket.close(code=1008)
            return

        # Get room join info from same message
        user_id = join_data.get("user_id", "anonymous")
        user_name = join_data.get("user_name", "Anonymous")
        action = join_data.get("action", "join")
        room_title = join_data.get("room_title", room_id)

        # Create or join room
        if room_id not in active_rooms:
            if action == "create":
                active_rooms[room_id] = {
                    "title": room_title,
                    "project_id": str(project.id),
                    "created_by": user_id,
                    "participants": {},
                    "created_at": asyncio.get_event_loop().time()
                }
                logger.info(f"Room created: {room_id} by {user_id}")
            else:
                await websocket.send_json({
                    "error": "Room not found",
                    "room_id": room_id
                })
                await websocket.close(code=1008)
                return

        room = active_rooms[room_id]

        # Verify project access
        if room["project_id"] != str(project.id):
            await websocket.send_json({
                "error": "Room belongs to different project"
            })
            await websocket.close(code=1008)
            return

        # Add user to room
        room["participants"][user_id] = {
            "name": user_name,
            "joined_at": asyncio.get_event_loop().time()
        }

        # Send confirmation
        await websocket.send_json({
            "event": "joined",
            "room_id": room_id,
            "room_title": room["title"],
            "participants": len(room["participants"]),
            "user_id": user_id
        })

        # Notify others of new participant
        redis_client = get_redis_instance()
        channel = f"room:{room_id}"
        from datetime import datetime

        join_event = {
            "type": "user_joined",
            "user_id": user_id,
            "user_name": user_name,
            "timestamp": datetime.utcnow().isoformat(),
            "room_info": {
                "id": room_id,
                "title": room["title"],
                "participants": len(room["participants"])
            }
        }
        await redis_client.publish(channel, json.dumps(join_event))
        logger.info(f"User {user_id} joined room {room_id}")

        # Subscribe to room messages
        redis_task = asyncio.create_task(subscribe_to_room(room_id, websocket))

        async def handle_room_messages():
            """Handle messages from client and send to room"""
            try:
                while True:
                    message = await websocket.receive()

                    if message["type"] == "websocket.disconnect":
                        break
                    elif message["type"] == "websocket.receive":
                        if "text" in message:
                            try:
                                msg_data = json.loads(message["text"])

                                if msg_data.get("type") == "ping":
                                    await websocket.send_json({"type": "pong"})
                                    continue

                                # Send message to room
                                room_message = {
                                    "type": "message",
                                    "user_id": user_id,
                                    "user_name": user_name,
                                    "content": msg_data.get("content", ""),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "room_info": {
                                        "id": room_id,
                                        "title": room["title"]
                                    }
                                }

                                await redis_client.publish(
                                    channel, json.dumps(room_message)
                                )
                                logger.debug(f"Message sent in room {room_id} by {user_id}")
                            except json.JSONDecodeError:
                                await websocket.send_json({"error": "Invalid JSON"})
            except WebSocketDisconnect:
                logger.info(f"User {user_id} disconnected from room {room_id}")
            except Exception as e:
                logger.error(f"Error in room message handler: {e}")

        client_task = asyncio.create_task(handle_room_messages())

        # Wait for tasks
        done, pending = await asyncio.wait(
            [redis_task, client_task], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Error in room chat: {e}")
    finally:
        # Remove user from room
        if room_id in active_rooms and user_id in active_rooms[room_id]["participants"]:
            del active_rooms[room_id]["participants"][user_id]

            # Notify others of departure
            try:
                redis_client = get_redis_instance()
                channel = f"room:{room_id}"
                from datetime import datetime

                leave_event = {
                    "type": "user_left",
                    "user_id": user_id,
                    "user_name": user_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "room_info": {
                        "id": room_id,
                        "title": active_rooms[room_id]["title"],
                        "participants": len(active_rooms[room_id]["participants"])
                    }
                }
                await redis_client.publish(channel, json.dumps(leave_event))
            except Exception as e:
                logger.error(f"Error notifying room of departure: {e}")

            # Clean up empty rooms
            if not active_rooms[room_id]["participants"]:
                del active_rooms[room_id]
                logger.info(f"Room {room_id} deleted (no participants)")

        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing room websocket: {e}")
