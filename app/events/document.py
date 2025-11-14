from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models.collections import Document, Collection
from app.services.utils import handle_webhook_call
from app.websockets.documents import RealtimeEvent, notify_collection_watchers
import asyncio
import threading
import logging

logger = logging.getLogger(__name__)


def run_async_in_thread(coro):
    """
    Run an async coroutine in a new thread with its own event loop.
    This is needed because SQLAlchemy events are synchronous.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
        loop.close()
    except Exception as e:
        logger.error(f"Error running async task in thread: {str(e)}")


async def handle_document_event_async(
    document: Document,
    collection: Collection,
    event_type: str,
    old_data: dict = None,
):
    """
    Handle document events asynchronously.
    Triggers webhooks and notifies WebSocket watchers.

    Args:
        document: The document that was modified
        collection: The collection the document belongs to
        event_type: 'CREATE', 'UPDATE', or 'DELETE'
        old_data: The previous data (only for UPDATE events)
    """
    try:
        # Notify WebSocket watchers
        await notify_collection_watchers(collection.name, document, event_type)

        # Call webhook if configured
        if collection.webhook_url:
            # Prepare webhook payload
            webhook_data = {
                "event_type": event_type,
                "document_id": str(document.id),
                "data": document.data,
                "created_at": document.created_at.isoformat() if document.created_at else None,
            }

            # Include old_data for UPDATE events
            if event_type == RealtimeEvent.UPDATE and old_data:
                webhook_data["old_data"] = old_data

            await handle_webhook_call(
                collection.webhook_url,
                webhook_data,
                isUpdate=(event_type == RealtimeEvent.UPDATE),
            )

        logger.info(
            f"Document event processed: {event_type} for document {document.id} in collection {collection.name}"
        )
    except Exception as e:
        logger.error(f"Error handling document event: {str(e)}")


def trigger_document_event(
    document: Document,
    collection: Collection,
    event_type: str,
    old_data: dict = None,
):
    """
    Trigger document event in a background thread.
    This allows the database transaction to complete without blocking.
    """
    thread = threading.Thread(
        target=run_async_in_thread,
        args=(handle_document_event_async(document, collection, event_type, old_data),),
    )
    thread.daemon = True
    thread.start()


@event.listens_for(Document, "after_insert")
def on_document_created(mapper, connection, target: Document):
    """
    Event listener triggered after a document is inserted.
    Sends CREATE event to webhooks and WebSocket watchers.
    """
    logger.debug(f"Document created event triggered for document {target.id}")

    # Get the collection from the session
    session = Session.object_session(target)
    if session:
        collection = session.query(Collection).get(target.collection_id)
        if collection:
            trigger_document_event(target, collection, RealtimeEvent.CREATE)
        else:
            logger.warning(f"Collection not found for document {target.id}")
    else:
        logger.warning(f"No session found for document {target.id}")


@event.listens_for(Document, "after_update")
def on_document_updated(mapper, connection, target: Document):
    """
    Event listener triggered after a document is updated.
    Sends UPDATE event to webhooks and WebSocket watchers with old_data.
    """
    logger.debug(f"Document updated event triggered for document {target.id}")

    # Get the collection and old data from the session
    session = Session.object_session(target)
    if session:
        collection = session.query(Collection).get(target.collection_id)
        if collection:
            # Get the old data from the session history
            old_data = None
            history = session.object_session(target).get_attribute_history(target, 'data')
            if history.deleted:
                old_data = history.deleted[0] if history.deleted else None

            trigger_document_event(target, collection, RealtimeEvent.UPDATE, old_data)
        else:
            logger.warning(f"Collection not found for document {target.id}")
    else:
        logger.warning(f"No session found for document {target.id}")


@event.listens_for(Document, "after_delete")
def on_document_deleted(mapper, connection, target: Document):
    """
    Event listener triggered after a document is deleted.
    Sends DELETE event to webhooks and WebSocket watchers.
    """
    logger.debug(f"Document deleted event triggered for document {target.id}")

    # For delete events, we need to get the collection before the document is fully removed
    # The collection_id is still available on the target
    session = Session(bind=connection)
    collection = session.query(Collection).get(target.collection_id)

    if collection:
        trigger_document_event(target, collection, RealtimeEvent.DELETE)
    else:
        logger.warning(f"Collection not found for document {target.id}")
