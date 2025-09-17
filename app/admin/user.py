from app.models import User
from sqladmin import ModelView


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email]
