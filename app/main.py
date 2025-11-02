from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.admin import *
from app.admin.backends import authentication_backend
from app.admin.project import ProjectModel
from app.api import (
    ai_assistant,
    integrations,
    migrater,
    user,
    coco_hooks,
    project,
    api,
    auth_collection,
    payments,
    collaborations,
    storage,
)

from app.api.collections import collections
from app.cron import cron
from app.services.redis_worker import close_redis, init_redis
from app.websockets import documents
from app.core.database import engine
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
import traceback
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqladmin import Admin

app = FastAPI(
    title="CocoBase API",
    version="1.0.0",
    description="Api docs for COCOBASE",
    docs_url="/_/",
    redoc_url=None,
)

admin = Admin(app, engine=engine, authentication_backend=authentication_backend)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
# app.add_middleware(BodySizeLimitMiddleware, max_body_size=2_000_000)  # ~1MB


@app.on_event("startup")
async def startup_event():
    await init_redis()
    print("Redis connected!")


@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()
    print("Redis closed!")


# Include routers
app.include_router(user.router, tags=["Authentication"])
app.include_router(collections.router)
app.include_router(project.router)
app.include_router(api.router)
app.include_router(integrations.router)
app.include_router(documents.router)
app.include_router(auth_collection.router)
app.include_router(payments.router)
app.include_router(coco_hooks.router)
app.include_router(collaborations.router)
app.include_router(storage.router)
app.include_router(cron.router)
app.include_router(migrater.router)
app.include_router(ai_assistant.router)
# Add middleware


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


@app.middleware("http")
async def ensure_cache_init(request, call_next):
    if FastAPICache._backend is None:
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    response = await call_next(request)
    return response


# add admin views
admin.add_view(UserAdmin)
admin.add_view(PricingPlanModel)
admin.add_view(ProjectSubscriptionModel)
admin.add_view(ProjectModel)
admin.add_view(IntegrationsModel)
admin.add_view(ProjectIntegrationModel)
