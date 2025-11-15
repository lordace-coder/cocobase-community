from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.admin import *
from app.admin.backends import authentication_backend
from app.admin.project import ProjectModel
from app.api import (
    ai_assistant,
    analytics,
    integrations,
    migrater,
    migrations,
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
from app.services.redis_worker import close_redis, init_redis, get_redis_instance
from app.websockets import documents
from app.core.database import engine, get_db
from app.core.sequence_manager import check_sequences_on_startup
from app.core.scheduler import start_scheduler, stop_scheduler
import traceback
from app import events
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqladmin import Admin
import logging

logger = logging.getLogger(__name__)

# Main app - Public API with collections and auth-collections at root
app = FastAPI(
    title="CocoBase Public API",
    version="1.2.1",
    description="Public API documentation for CocoBase Collections and Authentication",
    docs_url="/docs",  # Public docs
    redoc_url="/redoc",
)

# Dashboard/Admin API - separate docs (not used, just for creating openapi schema)
dashboard_app = FastAPI(
    title="CocoBase Dashboard API",
    version="1.2.1",
    description="Complete API docs for COCOBASE Dashboard and Admin",
)

admin = Admin(app, engine=engine, authentication_backend=authentication_backend)

# Configure CORS for main app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_redis()
    print("Redis connected!")

    # Check and fix database sequences to prevent duplicate key errors
    try:
        db = next(get_db())
        check_sequences_on_startup(db)
        db.close()
    except Exception as e:
        logger.error(f"Error checking sequences on startup: {e}")
        # Don't fail startup if sequence check fails
        pass

    # Start background scheduler for cron jobs
    try:
        start_scheduler()
        logger.info("Background scheduler started")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        # Don't fail startup if scheduler fails
        pass


@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()
    print("Redis closed!")

    # Stop background scheduler
    try:
        stop_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")


# Include public routes to main app (shown in public docs)
app.include_router(collections.router)
app.include_router(auth_collection.router)

# Include dashboard routes to main app (functional, NOT in public docs)
# We'll manually exclude these from the OpenAPI schema
app.include_router(user.router, tags=["Authentication"])
app.include_router(project.router)
app.include_router(api.router)
app.include_router(integrations.router)
app.include_router(documents.router)
app.include_router(payments.router)
app.include_router(coco_hooks.router)
app.include_router(collaborations.router)
app.include_router(storage.router)
app.include_router(cron.router)
app.include_router(migrater.router)
app.include_router(migrations.router)
app.include_router(ai_assistant.router)
app.include_router(analytics.router)

# Create dashboard docs with all routes (for /_/docs)
dashboard_app.include_router(user.router, tags=["Authentication"])
dashboard_app.include_router(collections.router)
dashboard_app.include_router(auth_collection.router)
dashboard_app.include_router(project.router)
dashboard_app.include_router(api.router)
dashboard_app.include_router(integrations.router)
dashboard_app.include_router(documents.router)
dashboard_app.include_router(payments.router)
dashboard_app.include_router(coco_hooks.router)
dashboard_app.include_router(collaborations.router)
dashboard_app.include_router(storage.router)
dashboard_app.include_router(cron.router)
dashboard_app.include_router(migrater.router)
dashboard_app.include_router(migrations.router)
dashboard_app.include_router(ai_assistant.router)
dashboard_app.include_router(analytics.router)


# Override OpenAPI schema for main app to only show public routes
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    # Get the full schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title="CocoBase Public API",
        version="1.2.1",
        description="Public API documentation for CocoBase Collections and Authentication",
        routes=app.routes,
    )

    # Filter paths to only include /collections and /auth-collections
    filtered_paths = {}
    for path, path_item in openapi_schema["paths"].items():
        if path.startswith("/collections") or path.startswith("/auth-collections"):
            filtered_paths[path] = path_item

    openapi_schema["paths"] = filtered_paths
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Serve dashboard docs at /_/
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse


@app.get("/_/docs", include_in_schema=False)
async def dashboard_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/_/openapi.json",
        title="CocoBase Dashboard API - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/_/redoc", include_in_schema=False)
async def dashboard_redoc():
    return get_redoc_html(
        openapi_url="/_/openapi.json",
        title="CocoBase Dashboard API - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


@app.get("/_/openapi.json", include_in_schema=False)
async def dashboard_openapi():
    return dashboard_app.openapi()


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


# add admin views
admin.add_view(UserAdmin)
admin.add_view(PricingPlanModel)
admin.add_view(ProjectSubscriptionModel)
admin.add_view(ProjectModel)
admin.add_view(IntegrationsModel)
admin.add_view(ProjectIntegrationModel)
admin.add_view(ApiUsageCounterModel)
