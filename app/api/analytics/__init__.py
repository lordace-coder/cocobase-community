"""
📊 Analytics Module
==================

Modular analytics system split into logical components:
- common: Shared utilities, cache, helpers, schemas
- overview: Project overview statistics
- collections: Collection analytics and trends
- users: User activity and growth analytics
- cloud_functions: Cloud function execution analytics and logs
- plans_payments: Subscription limits and payment analytics

All endpoints are combined in the main router.
"""

from fastapi import APIRouter
from .overview import router as overview_router
from .collections import router as collections_router
from .users import router as users_router
from .cloud_functions import router as cloud_functions_router
from .plans_payments import router as plans_payments_router

# Main analytics router that combines all sub-routers
router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Include all sub-routers
router.include_router(overview_router)
router.include_router(collections_router)
router.include_router(users_router)
router.include_router(cloud_functions_router)
router.include_router(plans_payments_router)

__all__ = ["router"]
