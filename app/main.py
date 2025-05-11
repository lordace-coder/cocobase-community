from fastapi import FastAPI
from app.api import user,collections,project
from app.core.middleware import BodySizeLimitMiddleware

app = FastAPI(
    title="CocoBase API",
    version="0.0.1",
    description="Api docs for COCOBASE",
    docs_url="/",
     redoc_url=None,  
)

# Include routers
app.include_router(user.router, tags=["Authentication"])
app.include_router(project.router, )
# Add middleware
app.add_middleware(BodySizeLimitMiddleware, max_body_size=1_000_000)  # ~1MB