from fastapi import FastAPI
from app.api import user
from app.core.middleware import BodySizeLimitMiddleware

app = FastAPI()

# Include routers
app.include_router(user.router, tags=["Authentication"])
# Add middleware
app.add_middleware(BodySizeLimitMiddleware, max_body_size=1_000_000)  # ~1MB