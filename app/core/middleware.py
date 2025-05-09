from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException

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


