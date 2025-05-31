from datetime import date
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
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
    path = request.url.path

    hit = db.query(RouteHit).filter_by(route=path, created=date.today()).first()
    if hit:
        hit.hits += 1
    else:
        hit = RouteHit(route=path, created=date.today(), hits=1)
        db.add(hit)

    db.commit()
