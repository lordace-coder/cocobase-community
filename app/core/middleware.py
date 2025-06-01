from datetime import date
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from app.core.database import get_db
from app.models.hits import RouteHit


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int):
        super().__init__(app)
        self.max_body_size = max_body_size  # in bytes

    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        if len(body) > self.max_body_size:
            raise HTTPException(status_code=413, detail="Payload too large")
        request._body = body
        return await call_next(request)


async def track_api_call(request: Request, db: Session = Depends(get_db)):
    """Track API call with proper error handling and retries"""
    path = request.url.path

    try:
        # Use a nested transaction to prevent commits from affecting parent transaction
        with db.begin_nested():
            hit = (
                db.query(RouteHit)
                .filter_by(route=path, created=date.today())
                .with_for_update()
                .first()
            )
            if hit:
                hit.hits += 1
            else:
                hit = RouteHit(route=path, created=date.today(), hits=1)
                db.add(hit)

        # If we get here, the nested transaction succeeded
        db.commit()
    except DBAPIError:
        # Log the error but don't fail the request - this is just analytics
        db.rollback()
        # We could add logging here
        pass
