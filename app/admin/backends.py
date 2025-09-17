import os
from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from urllib.parse import quote_plus
from app.core.database import get_db
from app.models.user import User
from app.services.jwt import create_access_token


class AdminAuth(AuthenticationBackend):
    middlewares = []

    async def login(self, request: Request) -> RedirectResponse:
        form = await request.form()
        username, password = form["username"], form["password"]

        # Manually get the DB session from the generator
        db = next(get_db())

        try:
            user = db.query(User).filter(User.email == username).first()
            print(user.compare_password(password))
            if not user or not user.compare_password(password):
                return False

            token = create_access_token(data={"user": username, "userId": str(user.id)})
            request.session.update({"token": token})
            return True
        except Exception as e:
            print("error occured " + str(e))
        finally:
            # Ensure the session is always closed
            db.close()

        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False

        # In a real app, you would validate the token here
        return True


authentication_backend = AdminAuth(secret_key=os.getenv("SECRET"))
