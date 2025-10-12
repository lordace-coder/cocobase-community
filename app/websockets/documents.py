from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import json
import asyncio
from app.core.database import get_db
from app.services.redis_worker import get_redis_instance, get_pubsub_redis
from app.models.app_client import Project
from app.models.collections import Collection, Document
from app.schemas.collections import DocumentSchema
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/realtime", tags=["RealTime"])

class RealtimeEvent:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


async def authenticate_websocket(
    websocket: WebSocket,
    db: Session
) -> Optional[Project]:
    """Authenticate WebSocket connection and return project"""
    try:
        # Wait for authentication message
        auth_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=10.0  # 10 second timeout
        )
        
        api_key = auth_data.get("api_key")
        if not api_key:
            await websocket.send_json({"error": "API key is required"})
            return None
        
        # Verify API key
        project = db.query(Project).filter(
            Project.api_key == api_key
        ).first()
        
        if not project:
            await websocket.send_json({
                "error": "Invalid API key",
                "error_detail": "Project not found"
            })
            return None
        
        return project
        
    except asyncio.TimeoutError:
        await websocket.send_json({"error": "Authentication timeout"})
        return None
    except Exception as e:
        await websocket.send_json({
            "error": "Authentication failed",
            "error_detail": str(e)
        })
        return None


async def subscribe_to_collection(
    collection_id: str,
    websocket: WebSocket
):
    """Subscribe to a collection's events and forward to WebSocket"""
    redis_conn = await get_pubsub_redis()
    pubsub = redis_conn.pubsub()
    channel = f"collection:{collection_id}"
    
    try:
        await pubsub.subscribe(channel)
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                # Decode the message data (since decode_responses=False for pubsub)
                data = json.loads(message["data"].decode('utf-8'))
                await websocket.send_json(data)
                
    except Exception as e:
        print(f"Error in subscription: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis_conn.close()


@router.websocket("/collections/{collection_id}")
async def watch_collection(
    websocket: WebSocket,
    collection_id: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for watching collection changes"""
    await websocket.accept()
    
    # Authenticate the connection
    project = await authenticate_websocket(websocket, db)
    if not project:
        await websocket.close(code=1008)  # Policy violation
        return
    
    # Verify collection exists and belongs to project
    collection = db.query(Collection).filter(
        Collection.name == collection_id,
        Collection.project_id == project.id  # Add authorization check
    ).first()
    
    if not collection:
        await websocket.send_json({
            "error": "Collection not found or access denied"
        })
        await websocket.close(code=1008)
        return
    
    # Send confirmation
    await websocket.send_json({
        "event": "connected",
        "collection_id": collection_id
    })
    
    # Create tasks for both listening to Redis and handling WebSocket messages
    redis_task = asyncio.create_task(
        subscribe_to_collection(collection_id, websocket)
    )
    
    async def handle_websocket_messages():
        """Handle incoming WebSocket messages (keepalive, etc.)"""
        try:
            while True:
                data = await websocket.receive_text()
                # Handle ping/pong or other client messages if needed
                if data == "ping":
                    await websocket.send_json({"event": "pong"})
        except WebSocketDisconnect:
            pass
    
    ws_task = asyncio.create_task(handle_websocket_messages())
    
    try:
        # Wait for either task to complete (disconnect or error)
        await asyncio.wait(
            [redis_task, ws_task],
            return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        # Clean up
        redis_task.cancel()
        ws_task.cancel()
        try:
            await websocket.close()
        except:
            pass


async def notify_collection_watchers(
    collection_id: str,
    document: Document,
    event: str
):
    """
    Publish a document event to all watchers of a collection.
    Call this function after creating/updating/deleting documents.
    
    Usage:
        await notify_collection_watchers(
            collection_id="123",
            document=document_instance,
            event=RealtimeEvent.CREATE
        )
    """
    redis_client = get_redis_instance()
    channel = f"collection:{collection_id}"
    
    payload = {
        "event": event,
        "data": jsonable_encoder(DocumentSchema.model_validate(document)),
        "collection_id": collection_id
    }
    
    await redis_client.publish(channel, json.dumps(payload))


# Example usage in your CRUD endpoints:
"""
from app.api.realtime import notify_collection_watchers, RealtimeEvent

@router.post("/collections/{collection_id}/documents")
async def create_document(
    collection_id: str,
    document_data: dict,
    db: Session = Depends(get_db)
):
    # Create document
    document = Document(**document_data)
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Notify watchers
    await notify_collection_watchers(
        collection_id=collection_id,
        document=document,
        event=RealtimeEvent.CREATE
    )
    
    return document

@router.put("/collections/{collection_id}/documents/{document_id}")
async def update_document(
    collection_id: str,
    document_id: str,
    document_data: dict,
    db: Session = Depends(get_db)
):
    # Update document
    document = db.query(Document).filter(Document.id == document_id).first()
    for key, value in document_data.items():
        setattr(document, key, value)
    db.commit()
    db.refresh(document)
    
    # Notify watchers
    await notify_collection_watchers(
        collection_id=collection_id,
        document=document,
        event=RealtimeEvent.UPDATE
    )
    
    return document

@router.delete("/collections/{collection_id}/documents/{document_id}")
async def delete_document(
    collection_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    # Get document before deleting (for notification)
    document = db.query(Document).filter(Document.id == document_id).first()
    
    # Delete document
    db.delete(document)
    db.commit()
    
    # Notify watchers
    await notify_collection_watchers(
        collection_id=collection_id,
        document=document,
        event=RealtimeEvent.DELETE
    )
    
    return {"message": "Document deleted"}
"""