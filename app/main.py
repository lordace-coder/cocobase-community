from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import user, collections, project, api, auth_collection
from app.core.middleware import BodySizeLimitMiddleware

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
app.include_router(auth_collection.router)
# Add middleware
app.add_middleware(BodySizeLimitMiddleware, max_body_size=1_000_000)  # ~1MB
