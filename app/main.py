from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.admin import *
from app.admin.backends import authentication_backend
from app.admin.project import ProjectModel
from app.admin.email_sender import EmailSenderView
from app.admin.analytics import (
    DashboardOverview,
    RevenueAnalyticsView,
    UserAnalyticsView,
    ProjectAnalyticsView,
    SystemHealthView
)
from app.admin.sql_console import SQLConsoleView
from app.admin.pricing import PaymentModel
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
    health,
    orm_api_keys,
    email_settup,
    webhooks,
    oauth,
    two_factor_auth,
    email_verification,
    phone_auth,
)
from app.api.email_verification import standalone_router as email_verification_standalone

from app.api.collections import collections
from app.core.config import SECRET_KEY
from app.cron import cron
from app.services.redis_worker import close_redis, init_redis, get_redis_instance
from app.websockets import documents
from app.core.database import engine
from app.core.scheduler import start_scheduler, stop_scheduler
import traceback
from app import events
from fastapi.responses import JSONResponse, FileResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqladmin import Admin
import logging
import os
from starlette.middleware.sessions import SessionMiddleware

logger = logging.getLogger(__name__)
# Configure root logger to WARNING by default to reduce noise, but enable INFO for project tracking
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# Ensure project tracking logs at INFO level are shown (e.g., 'Synced usage to DB')
logging.getLogger("app.services.project_tracking").setLevel(logging.INFO)

# Main app - Public API with collections and auth-collections at root
app = FastAPI(
    title="CocoBase Public API",
    version="1.5.0",
    description="Public API documentation for CocoBase Collections and Authentication",
    docs_url="/docs",  # Public docs
    redoc_url="/redoc",
)

# Dashboard/Admin API - separate docs (not used, just for creating openapi schema)
dashboard_app = FastAPI(
    title="CocoBase Dashboard API",
    version="1.5.0",
    description="Complete API docs for COCOBASE Dashboard and Admin",
)

admin = Admin(
    app,
    engine=engine,
    authentication_backend=authentication_backend,
    templates_dir="app/templates",
    base_url="/_/admin", 
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,  # Use env variable
    session_cookie="cocobase_session",  # Cookie name
    max_age=14 * 24 * 60 * 60,  # 14 days in seconds
    same_site="lax",  # CSRF protection
    https_only=False,  # Set to True in production with HTTPS
)
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
    logger.info("Redis connected!")

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
    logger.info("Redis closed!")

    # Stop background scheduler
    try:
        stop_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")


# Include public routes to main app (shown in public docs)
app.include_router(health.router)  # Health checks - available publicly
app.include_router(collections.router)
app.include_router(auth_collection.router)
app.include_router(email_verification_standalone)  # Standalone email verification page

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
app.include_router(orm_api_keys.router)
app.include_router(email_settup.router)
app.include_router(webhooks.router)
app.include_router(oauth.router)
app.include_router(two_factor_auth.router)
app.include_router(email_verification.router)
app.include_router(phone_auth.router)

# Create dashboard docs with all routes (for /_/docs)
dashboard_app.include_router(user.router, tags=["Authentication"])
dashboard_app.include_router(collections.router)
dashboard_app.include_router(auth_collection.router)
dashboard_app.include_router(project.router)
dashboard_app.include_router(api.router)
dashboard_app.include_router(email_settup.router)
dashboard_app.include_router(webhooks.router)

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
dashboard_app.include_router(orm_api_keys.router)
dashboard_app.include_router(oauth.router)
dashboard_app.include_router(two_factor_auth.router)
dashboard_app.include_router(email_verification.router)
dashboard_app.include_router(phone_auth.router)

@app.get("/")
def root():
    return {"status": "ok"}

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
admin.add_view(PaymentModel)
admin.add_view(ProjectModel)
admin.add_view(IntegrationsModel)
admin.add_view(ProjectIntegrationModel)
admin.add_view(ApiUsageCounterModel)
admin.add_view(EmailSenderView)
admin.add_view(DefaultEmailTemplateModel)

# Add analytics views
admin.add_view(DashboardOverview)
admin.add_view(RevenueAnalyticsView)
admin.add_view(UserAnalyticsView)
admin.add_view(ProjectAnalyticsView)
admin.add_view(SystemHealthView)

# Add SQL Console
admin.add_view(SQLConsoleView)


# ─── Dashboard UI (SvelteKit static build) ───────────────────────────────────
_DASHBOARD_BUILD = os.path.join(os.path.dirname(__file__), "..", "dashboard", "build")


@app.get("/_/ui", include_in_schema=False)
@app.get("/_/ui/{full_path:path}", include_in_schema=False)
async def serve_dashboard_ui(full_path: str = ""):
    """Serve the SvelteKit dashboard SPA from dashboard/build."""
    build_dir = os.path.abspath(_DASHBOARD_BUILD)

    if full_path:
        requested = os.path.normpath(os.path.join(build_dir, full_path))
        # Guard against path traversal
        if requested.startswith(build_dir) and os.path.isfile(requested):
            return FileResponse(requested)

    index = os.path.join(build_dir, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)

    return JSONResponse(
        {"error": "Dashboard not built. Run: cd dashboard && npm run build"},
        status_code=503,
    )