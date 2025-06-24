from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Dict, List
import json

from fastapi.encoders import jsonable_encoder
from fastapi.params import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.app_client import Project
from app.models.collections import Collection, Document
from app.schemas.collections import CollectionSchema, DocumentSchema

collection_watchers: Dict[str, List[WebSocket]] = {}

router = APIRouter(prefix="/realtime", tags=["RealTime"])


class RealtimeEvent:
    create = "create event"
    update = "update event"
    delete = "delete event"


async def add_watcher(collection_id: str, websocket: WebSocket, db: Session):
    await websocket.accept()

    # get token from first message
    try:
        token = await websocket.receive_json()
        token = token.get("api_key", None)
        if not token:
            await websocket.send_json({"error": "API key is required"})
            await websocket.close()
            return
        # get project from api key
        project = (
            db.query(Project)
            .filter(
                Project.api_key == token,
            )
            .first()
        )
        collection = db.query(Collection).get(collection_id)
        if not project:
            await websocket.send_json(
                {"error": "Invalid API key", "error_detail": "Project not found"}
            )
            await websocket.close()
            return
    except Exception as e:
        print("error receiving token", e)
        await websocket.send_json(
            {"error": "Invalid token format", "error_detail": str(e)}
        )
        await websocket.close()

    if collection_id not in collection_watchers:
        collection_watchers[collection_id] = []
    collection_watchers[collection_id].append(websocket)
    print(collection_watchers)


def remove_watcher(collection_id: str, websocket: WebSocket):
    if collection_id in collection_watchers:
        collection_watchers[collection_id].remove(websocket)
        if not collection_watchers[collection_id]:
            del collection_watchers[collection_id]


async def notify_collection_watchers(
    collection_id: str, document: Document, event: RealtimeEvent
):
    print(collection_id, document, event, collection_watchers)
    watchers = collection_watchers.get(collection_id, [])
    payload = {
        "event": "collection_created",
        "data": jsonable_encoder(DocumentSchema.model_validate(document)),
    }
    for ws in watchers:
        try:
            await ws.send_json(payload)
            print("sent message")
        except Exception as e:
            print("err sending response ", e)
            continue


@router.websocket("/collections/{collection_id}")
async def watch_collection(
    websocket: WebSocket, collection_id: str, db: Session = Depends(get_db)
):
    await add_watcher(collection_id, websocket, db)
    try:
        while True:
            await websocket.receive_text()  # optional keepalive
    except WebSocketDisconnect:
        remove_watcher(collection_id, websocket)
