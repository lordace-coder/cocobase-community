from sqladmin import ModelView
from app.models.app_client import Project


class ProjectModel(ModelView,model = Project):
    column_list = [Project.name, Project.created_at]