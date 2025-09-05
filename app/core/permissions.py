from app.models import Collection, AppUser
from fastapi import HTTPException, status
from app.core.dependencies import get_app_user


ACCESS_TYPES = ["create", "read", "update", "delete"]


def can_access_collection(collection: Collection, access_type: str, user: AppUser):
    if access_type not in ACCESS_TYPES:
        raise Exception(
            "Invalid access type, access type has to be ['create','read','update','delete']"
        )

    if collection.permissions == None:
        return

    permissions_needed: list = collection.permissions.get(access_type)
    if len(permissions_needed) == 0:
        return

    if user == None and len(permissions_needed) > 0:
        print("error from here")
        raise HTTPException(
            401,
            "This action can only be made by an authorized user,Try logging in first",
        )
    for perm in user.roles:
        if perm in permissions_needed:
            # grant user access
            return

    raise HTTPException(
        status.HTTP_403_FORBIDDEN, "This user doesnt have the access needed"
    )
