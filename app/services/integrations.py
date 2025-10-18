import importlib.util
import sys
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session

from app.models import Integration, ProjectIntegration, Project


class IntegrationService:
    """Simple service for managing integrations"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Get Available Integrations ====================

    def get_all_integrations(self) -> List[Integration]:
        """Get all available integrations"""
        return self.db.query(Integration).filter(Integration.is_active == True).all()

    def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get specific integration"""
        return (
            self.db.query(Integration).filter(Integration.id == integration_id).first()
        )

    # ==================== Project Integration Management ====================

    def enable_integration_for_project(
        self,
        project_id: str,
        integration_id: str,
        config: Optional[Dict] = None,
    ) -> ProjectIntegration:
        """Enable an integration for a project"""
        # Check if already exists
        existing = (
            self.db.query(ProjectIntegration)
            .filter(
                ProjectIntegration.project_id == project_id,
                ProjectIntegration.integration_id == integration_id,
            )
            .first()
        )

        if existing:
            existing.is_enabled = True
            if config:
                existing.config = config
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new
        project_integration = ProjectIntegration(
            project_id=project_id,
            integration_id=integration_id,
            config=config or {},
            is_enabled=True,
        )
        self.db.add(project_integration)
        self.db.commit()
        self.db.refresh(project_integration)
        return project_integration

    def disable_integration_for_project(
        self, project_id: str, integration_id: str
    ) -> bool:
        """Disable an integration for a project"""
        project_integration = (
            self.db.query(ProjectIntegration)
            .filter(
                ProjectIntegration.project_id == project_id,
                ProjectIntegration.integration_id == integration_id,
            )
            .first()
        )

        if project_integration:
            project_integration.is_enabled = False
            self.db.commit()
            return True
        return False

    def update_integration_config(
        self, project_id: str, integration_id: str, config: Dict
    ) -> Optional[ProjectIntegration]:
        """Update config for a project integration"""
        project_integration = (
            self.db.query(ProjectIntegration)
            .filter(
                ProjectIntegration.project_id == project_id,
                ProjectIntegration.integration_id == integration_id,
            )
            .first()
        )

        if project_integration:
            project_integration.config = config
            self.db.commit()
            self.db.refresh(project_integration)
            return project_integration
        return None

    def get_project_integrations(
        self, project_id: str, enabled_only: bool = True
    ) -> List[ProjectIntegration]:
        """Get all integrations for a project"""
        query = self.db.query(ProjectIntegration).filter(
            ProjectIntegration.project_id == project_id
        )
        if enabled_only:
            query = query.filter(ProjectIntegration.is_enabled == True)
        return query.all()

    def get_project_integration(
        self, project_id: str, integration_id: str
    ) -> Optional[ProjectIntegration]:
        """Get specific project integration"""
        return (
            self.db.query(ProjectIntegration)
            .filter(
                ProjectIntegration.project_id == project_id,
                ProjectIntegration.integration_id == integration_id,
                ProjectIntegration.is_enabled == True,
            )
            .first()
        )

    # ==================== Module Execution ====================

    def load_integration_module(self, integration_id: str, config: Dict = None):
        """
        Load and return the Python module for an integration.

        Args:
            integration_id: The integration ID
            config: Optional config to pass to the module

        Returns:
            The loaded Python module
        """
        integration = self.get_integration(integration_id)
        if not integration or not integration.module_code:
            raise ValueError(f"Integration {integration_id} has no module code")

        # Create a unique module name
        module_name = f"integration_{integration.module_name or integration_id}"

        # Create module from code
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)

        # Execute the code in the module's namespace
        exec(integration.module_code, module.__dict__)

        # Add module to sys.modules so it can be imported
        sys.modules[module_name] = module

        return module

    def execute_integration(
        self,
        project_id: str,
        integration_id: str,
        function_name: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a function from a project's integration.

        Args:
            project_id: The project ID
            integration_id: The integration ID
            function_name: The function name to call
            *args, **kwargs: Arguments to pass to the function

        Returns:
            The result of the function call
        """
        # Get project integration
        project_integration = self.get_project_integration(project_id, integration_id)
        if not project_integration:
            raise ValueError(f"Integration not enabled for project {project_id}")

        # Load the module
        module = self.load_integration_module(
            integration_id, project_integration.config
        )

        # Get the function
        if not hasattr(module, function_name):
            raise AttributeError(
                f"Integration module has no function '{function_name}'"
            )

        func = getattr(module, function_name)

        # Merge config into kwargs if the function accepts a 'config' parameter
        import inspect

        sig = inspect.signature(func)
        if "config" in sig.parameters:
            kwargs["config"] = project_integration.config

        # Execute the function
        return func(*args, **kwargs)
