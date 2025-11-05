"""
📚 Collections Analytics
=======================

Collection-specific analytics and time-series data.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access
from app.models.app_client import Project
from app.models.collections import Collection, Document

from .common import CollectionAnalytics, TimeSeriesData, TopCollections

router = APIRouter()


@router.get("/{project_id}/collections", response_model=List[CollectionAnalytics])
def get_collections_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Get analytics for all collections in the project.

    Includes:
    - Document counts
    - Growth metrics
    - Activity trends
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    collections = (
        db.query(Collection)
        .filter(Collection.project_id == project_id)
        .limit(limit)
        .all()
    )

    analytics_list = []

    for collection in collections:
        # Total documents
        total_docs = (
            db.query(func.count(Document.id))
            .filter(Document.collection_id == collection.id)
            .scalar()
            or 0
        )

        # Documents by time period
        docs_today = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= today_start,
            )
            .scalar()
            or 0
        )

        docs_this_week = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= week_start,
            )
            .scalar()
            or 0
        )

        docs_this_month = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        # Average per day
        avg_per_day = docs_this_month / 30.0 if docs_this_month > 0 else 0.0

        # Growth rate (this week vs last week)
        last_week_start = week_start - timedelta(days=7)
        docs_last_week = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= last_week_start,
                Document.created_at < week_start,
            )
            .scalar()
            or 0
        )

        growth_rate = 0.0
        if docs_last_week > 0:
            growth_rate = ((docs_this_week - docs_last_week) / docs_last_week) * 100
        elif docs_this_week > 0:
            growth_rate = 100.0

        # Most active day
        most_active = (
            db.query(
                func.date(Document.created_at).label("day"),
                func.count(Document.id).label("count"),
            )
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= month_start,
            )
            .group_by("day")
            .order_by(desc("count"))
            .first()
        )

        most_active_day = str(most_active[0]) if most_active else None

        # Last updated
        last_doc = (
            db.query(Document.created_at)
            .filter(Document.collection_id == collection.id)
            .order_by(desc(Document.created_at))
            .first()
        )

        last_updated = last_doc[0] if last_doc else None

        analytics_list.append(
            CollectionAnalytics(
                collection_id=collection.id,
                collection_name=collection.name,
                total_documents=total_docs,
                documents_today=docs_today,
                documents_this_week=docs_this_week,
                documents_this_month=docs_this_month,
                avg_documents_per_day=round(avg_per_day, 2),
                growth_rate_percentage=round(growth_rate, 2),
                most_active_day=most_active_day,
                last_updated=last_updated,
            )
        )

    return analytics_list


@router.get(
    "/{project_id}/collections/{collection_id}", response_model=CollectionAnalytics
)
def get_collection_analytics(
    project_id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """Get detailed analytics for a specific collection."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project_id)
        .first()
    )

    if not collection:
        raise HTTPException(404, "Collection not found")

    # Reuse list endpoint logic
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Total documents
    total_docs = (
        db.query(func.count(Document.id))
        .filter(Document.collection_id == collection.id)
        .scalar()
        or 0
    )

    # Documents by time period
    docs_today = (
        db.query(func.count(Document.id))
        .filter(
            Document.collection_id == collection.id,
            Document.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    docs_this_week = (
        db.query(func.count(Document.id))
        .filter(
            Document.collection_id == collection.id,
            Document.created_at >= week_start,
        )
        .scalar()
        or 0
    )

    docs_this_month = (
        db.query(func.count(Document.id))
        .filter(
            Document.collection_id == collection.id,
            Document.created_at >= month_start,
        )
        .scalar()
        or 0
    )

    avg_per_day = docs_this_month / 30.0 if docs_this_month > 0 else 0.0

    # Growth rate
    last_week_start = week_start - timedelta(days=7)
    docs_last_week = (
        db.query(func.count(Document.id))
        .filter(
            Document.collection_id == collection.id,
            Document.created_at >= last_week_start,
            Document.created_at < week_start,
        )
        .scalar()
        or 0
    )

    growth_rate = 0.0
    if docs_last_week > 0:
        growth_rate = ((docs_this_week - docs_last_week) / docs_last_week) * 100
    elif docs_this_week > 0:
        growth_rate = 100.0

    # Most active day
    most_active = (
        db.query(
            func.date(Document.created_at).label("day"),
            func.count(Document.id).label("count"),
        )
        .filter(
            Document.collection_id == collection.id,
            Document.created_at >= month_start,
        )
        .group_by("day")
        .order_by(desc("count"))
        .first()
    )

    most_active_day = str(most_active[0]) if most_active else None

    # Last updated
    last_doc = (
        db.query(Document.created_at)
        .filter(Document.collection_id == collection.id)
        .order_by(desc(Document.created_at))
        .first()
    )

    last_updated = last_doc[0] if last_doc else None

    return CollectionAnalytics(
        collection_id=collection.id,
        collection_name=collection.name,
        total_documents=total_docs,
        documents_today=docs_today,
        documents_this_week=docs_this_week,
        documents_this_month=docs_this_month,
        avg_documents_per_day=round(avg_per_day, 2),
        growth_rate_percentage=round(growth_rate, 2),
        most_active_day=most_active_day,
        last_updated=last_updated,
    )


@router.get("/{project_id}/timeseries/documents", response_model=List[TimeSeriesData])
def get_documents_timeseries(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    collection_id: Optional[str] = None,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get time-series data for document creation.

    Args:
    - days: Number of days to look back (default: 30)
    - collection_id: Filter by specific collection (optional)

    Returns daily document counts
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        db.query(
            func.date(Document.created_at).label("date"),
            func.count(Document.id).label("count"),
        )
        .join(Collection)
        .filter(Collection.project_id == project_id, Document.created_at >= start_date)
    )

    if collection_id:
        query = query.filter(Document.collection_id == collection_id)

    results = query.group_by("date").order_by("date").all()

    # Fill missing dates with 0
    date_map = {str(row.date): row.count for row in results}

    timeseries = []
    current_date = start_date.date()
    end_date = datetime.now(timezone.utc).date()

    while current_date <= end_date:
        date_str = str(current_date)
        timeseries.append(
            TimeSeriesData(date=date_str, value=date_map.get(date_str, 0))
        )
        current_date += timedelta(days=1)

    return timeseries


@router.get("/{project_id}/top-collections", response_model=List[TopCollections])
def get_top_collections(
    project_id: str,
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("total", regex="^(total|recent)$"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get top collections by activity.

    Args:
    - limit: Number of collections to return
    - sort_by: "total" (total documents) or "recent" (recent activity)
    """
    if sort_by == "total":
        # Sort by total document count
        results = (
            db.query(
                Collection.name,
                func.count(Document.id).label("document_count"),
                func.count(
                    case(
                        (
                            Document.created_at
                            >= datetime.now(timezone.utc) - timedelta(days=7),
                            1,
                        )
                    )
                ).label("recent_activity"),
            )
            .outerjoin(Document)
            .filter(Collection.project_id == project_id)
            .group_by(Collection.id, Collection.name)
            .order_by(desc("document_count"))
            .limit(limit)
            .all()
        )
    else:
        # Sort by recent activity
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        results = (
            db.query(
                Collection.name,
                func.count(Document.id).label("document_count"),
                func.count(case((Document.created_at >= week_ago, 1))).label(
                    "recent_activity"
                ),
            )
            .outerjoin(Document)
            .filter(Collection.project_id == project_id)
            .group_by(Collection.id, Collection.name)
            .order_by(desc("recent_activity"))
            .limit(limit)
            .all()
        )

    return [
        TopCollections(
            collection_name=row.name,
            document_count=row.document_count,
            recent_activity=row.recent_activity,
        )
        for row in results
    ]
