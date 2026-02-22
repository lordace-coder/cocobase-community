from sqladmin import ModelView
from app.models.integrations import Integration, ProjectIntegration


class IntegrationsModel(ModelView, model=Integration):
    column_list = [Integration.id, Integration.display_name]


class ProjectIntegrationModel(ModelView, model=ProjectIntegration):
    pass
