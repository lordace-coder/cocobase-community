from datetime import datetime
from pydantic import BaseModel


class PricingPlanSchema(BaseModel):
    id: int
    name: str
    description: str
    price: float
    currency: str
    created_at: datetime
    features: dict
    max_users: int
    max_storage_mb: int
    max_cloud_functions: int
    max_requests_per_month: int
