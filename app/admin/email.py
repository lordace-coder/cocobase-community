from sqladmin import ModelView
from app.models.email_models import DefaultEmailTemplate


class DefaultEmailTemplateModel(ModelView, model=DefaultEmailTemplate):
    column_list = [
        DefaultEmailTemplate.id,
        DefaultEmailTemplate.template_type,
        DefaultEmailTemplate.name,
        DefaultEmailTemplate.created_at,
        DefaultEmailTemplate.updated_at,
    ]