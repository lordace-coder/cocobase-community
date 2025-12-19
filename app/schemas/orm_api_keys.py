from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ORMApiKeyCreate(BaseModel):
    """Schema for creating a new ORM API key."""
    name: str = Field(..., description="User-defined name for the API key", min_length=1, max_length=100)
    permissions: dict = Field(
        default_factory=lambda: {
            "collections": {"*": ["read"]},
            "admin": False,
            "auth": {
                "manage_users": False,
                "manage_roles": False
            }
        },
        description="Granular permissions for the API key"
    )
    expires_in_days: Optional[int] = Field(None, description="Number of days until the key expires", ge=1)
    rate_limit: Optional[int] = Field(None, description="Requests per minute (null = plan default)", ge=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Production API Key",
                "permissions": {
                    "collections": {
                        "*": ["read"],
                        "users": ["read", "write"],
                        "orders": ["read", "write", "delete"]
                    },
                    "admin": False,
                    "auth": {
                        "manage_users": True,
                        "manage_roles": False
                    }
                },
                "expires_in_days": 90,
                "rate_limit": 1000
            }
        }
    }


class ORMApiKeyResponse(BaseModel):
    """Schema for ORM API key responses."""
    id: str
    project_id: str
    name: str
    key_prefix: str = Field(..., description="First 16 characters of the key")
    permissions: dict
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_by: str
    rate_limit: Optional[int]

    model_config = {"from_attributes": True}


class ORMApiKeyCreateResponse(BaseModel):
    """Schema for the response when creating a new ORM API key (includes the full key)."""
    id: str
    project_id: str
    name: str
    key: str = Field(..., description="Full API key - SAVE THIS! It will not be shown again.")
    key_prefix: str
    permissions: dict
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    rate_limit: Optional[int]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "key-uuid",
                "project_id": "proj-uuid",
                "name": "Production API Key",
                "key": "coco_orm_901235c6-9564-4de0-bb40_8a7f3e9d2c1b4f6a8e5d7c9b3a1f2e4d",
                "key_prefix": "coco_orm_901235c6",
                "permissions": {
                    "collections": {"*": ["read"]},
                    "admin": False
                },
                "created_at": "2025-01-18T10:30:00Z",
                "expires_at": None,
                "is_active": True,
                "rate_limit": None
            }
        }
    }


class ORMApiKeyUpdate(BaseModel):
    """Schema for updating an ORM API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Key Name",
                "is_active": False
            }
        }
    }
