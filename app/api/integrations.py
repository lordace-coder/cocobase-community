from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.services.integrations import IntegrationService
from app.models import Integration, ProjectIntegration

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ==================== Schemas ====================


class IntegrationResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    icon_url: Optional[str]
    config_schema: Optional[Dict]

    class Config:
        from_attributes = True


class ProjectIntegrationResponse(BaseModel):
    id: str
    project_id: str
    integration_id: str
    config: Dict
    is_enabled: bool
    integration: IntegrationResponse

    class Config:
        from_attributes = True


class EnableIntegrationRequest(BaseModel):
    integration_id: str
    config: Optional[Dict] = {}


class UpdateConfigRequest(BaseModel):
    config: Dict


# ==================== Routes ====================


@router.get("/", response_model=List[IntegrationResponse])
def get_all_integrations(db: Session = Depends(get_db)):
    """Get all available integrations"""
    service = IntegrationService(db)
    integrations = service.get_all_integrations()
    return integrations


@router.get("/project/{project_id}", response_model=List[ProjectIntegrationResponse])
def get_project_integrations(
    project_id: str,
    enabled_only: bool = True,
    db: Session = Depends(get_db),
):
    """Get integrations for a specific project"""
    service = IntegrationService(db)
    integrations = service.get_project_integrations(project_id, enabled_only)
    return integrations

def can_enable_integration(db: Session, integration_id: str) -> tuple[bool, str]:
    """Check if an integration can be enabled (e.g., no 2 email providers at once)"""
    email_providers = {
        "546013a6-ed93-426f-94b3-05302cf207f7": "cocomailer",
        "08e9ea54-0952-43bd-9ddf-e1a8da445b77": "resend",
        "6fd2ecf9-1334-46f6-88e2-dd0440550193": "emailjs",
    }
    
    if integration_id in email_providers.keys():
        # Check if an email integration is already active
        existing_email_integration = (
            db.query(ProjectIntegration)
            .filter(
                ProjectIntegration.integration_id.in_(email_providers.keys()),
                ProjectIntegration.is_enabled == True,
                ProjectIntegration.integration_id != integration_id,
            )
            .first()
        )
        
        if existing_email_integration:
            # Changed from .id to .integration_id
            existing_provider = email_providers[existing_email_integration.integration_id]
            new_provider = email_providers[integration_id]
            return (
                False,
                f"Cannot enable {new_provider}: {existing_provider} is already active. Only one email provider can be active at a time.",
            )
    
    return True, "Integration can be enabled"

@router.post("/project/{project_id}/enable")
def enable_integration(
    project_id: str,
    request: EnableIntegrationRequest,
    db: Session = Depends(get_db),
):
    """Enable an integration for a project"""
    service = IntegrationService(db)
    can_enable, reason = can_enable_integration(db, request.integration_id)
    if not can_enable:
        raise HTTPException(400, detail=reason)

    try:
        project_integration = service.enable_integration_for_project(
            project_id=project_id,
            integration_id=request.integration_id,
            config=request.config,
        )
        return {
            "message": "Integration enabled successfully",
            "integration": project_integration,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project/{project_id}/disable/{integration_id}")
def disable_integration(
    project_id: str,
    integration_id: str,
    db: Session = Depends(get_db),
):
    """Disable an integration for a project"""
    service = IntegrationService(db)

    success = service.disable_integration_for_project(project_id, integration_id)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {"message": "Integration disabled successfully"}


@router.put("/project/{project_id}/config/{integration_id}")
def update_integration_config(
    project_id: str,
    integration_id: str,
    request: UpdateConfigRequest,
    db: Session = Depends(get_db),
):
    """Update config for a project integration"""
    service = IntegrationService(db)

    project_integration = service.update_integration_config(
        project_id=project_id,
        integration_id=integration_id,
        config=request.config,
    )

    if not project_integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "message": "Config updated successfully",
        "integration": project_integration,
    }


@router.post("/project/{project_id}/execute/{integration_id}")
def execute_integration_function(
    project_id: str,
    integration_id: str,
    function_name: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Execute a function from an integration"""
    service = IntegrationService(db)

    try:
        result = service.execute_integration(
            project_id=project_id,
            integration_id=integration_id,
            function_name=function_name,
            **payload,
        )
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AttributeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


# Example Frontend Flow:
"""
1. GET /integrations/ 
   - Shows all available integrations to user

2. POST /integrations/project/{project_id}/enable
   - User clicks toggle to enable integration
   - If config_schema exists, show config form
   - If no config_schema, enable with empty config
   
   Body: {
       "integration_id": "openai-integration",
       "config": {"api_key": "sk-xxx"} // or {} if no config needed
   }

3. PUT /integrations/project/{project_id}/config/{integration_id}
   - User updates config later
   
   Body: {
       "config": {"api_key": "sk-yyy", "model": "gpt-4"}
   }

4. GET /integrations/project/{project_id}
   - Shows enabled integrations for project

5. POST /integrations/project/{project_id}/disable/{integration_id}
   - User toggles off integration
"""
