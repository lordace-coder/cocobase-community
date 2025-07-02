from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import user, collections, project, api, auth_collection
from app.websockets import documents
from app.core.middleware import BodySizeLimitMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
import traceback
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware


app = FastAPI(
    title="CocoBase API",
    version="0.0.1",
    description="Api docs for COCOBASE",
    docs_url="/",
    redoc_url=None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(user.router, tags=["Authentication"])
app.include_router(
    project.router,
)
app.include_router(
    collections.router,
)
app.include_router(api.router)
app.include_router(documents.router)
app.include_router(auth_collection.router)
# Add middleware
app.add_middleware(BodySizeLimitMiddleware, max_body_size=1_000_000)  # ~1MB

class FullErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            tb = traceback.format_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "error": str(exc),
                    "traceback": tb,
                },
            )

app.add_middleware(FullErrorMiddleware)

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")

