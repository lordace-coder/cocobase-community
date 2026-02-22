from fastapi import Request
from fastapi.responses import RedirectResponse
from app.models import User
from sqladmin import ModelView, action


# todo implement sending of email

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email]
    page_size = 100
