from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("userId")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token missing userId"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return db.query(User).filter(User.id == user_id).first()


# async def get_current_user_client(request: Request, db: Session = Depends(get_db)):
#     auth_header = request.headers.get("Authorization")
#     print("Authorization Header:", auth_header)

#     if not auth_header:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authorization header missing",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     try:
#         scheme, token = auth_header.split(" ")
#     except ValueError:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid authorization header format",
#         )

#     if scheme.lower() == "bearer":
#         payload = decode_access_token(token)
#         if not payload:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid bearer token",
#             )
#         user_id = payload.get("userId")
#         if not user_id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Token missing userId",
#             )
#         user = db.query(User).filter(User.id == user_id).first()

#     elif scheme.lower() == "token":
#         token_instance: User = (
#             db.query(AccessToken).filter(AccessToken.token == int(token)).first()
#         )
#         if not token_instance:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Invalid token",
#             )
#         return token_instance.user

#     else:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Unsupported auth scheme '{scheme}'",
#         )

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found",
#         )

#     return user
