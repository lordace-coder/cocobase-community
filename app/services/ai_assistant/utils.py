from app.core.database import SessionLocal
from app.models.cloud_functions import CloudFunction, RuntimeEnum
from pydantic import BaseModel
from typing import Optional


def create_cloud_function(project: str, name: str, code: str, description: str) -> dict:
    """
    creates a cloud function for the user with the provided project id and returns valid json to the user

    Args:
        project (str): project the cloud function will belong to.

        name (str): The name of the cloud function, on the frontend it is displayed like a filename, should be sluggified befor being passed in.

        code (str): the cloud function code

        description (str): A short description to tell the user what the cloud function is all about
    """
    cloud_func = CloudFunction(
        project_id=project,
        name=name,
        code=code,
        description=description,
    )

    with SessionLocal() as db:
        db.add(cloud_func)
        db.commit()
        db.refresh(cloud_func)

        return {
            "id": cloud_func.id,
            "project_id": cloud_func.project_id,
            "name": cloud_func.name,
            "code": cloud_func.code,
            "description": cloud_func.description,
            "runtime": cloud_func.runtime,
            "is_active": cloud_func.is_active,
            "created_at": (
                cloud_func.created_at.isoformat() if cloud_func.created_at else None
            ),
        }


def update_cloud_function(
    function_id: str,
    project_id: str,
    code: Optional[str] = None,
    description: Optional[str] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> dict:
    """
    Update an existing cloud function.

    Args:
        function_id (str): The ID of the cloud function to update.
        project_id (str): The project ID (for security validation).
        code (str, optional): New code for the function.
        description (str, optional): New description.
        name (str, optional): New name for the function.
        is_active (bool, optional): Whether the function is active.

    Returns:
        dict: The updated cloud function as a dictionary.
    """
    with SessionLocal() as db:
        cloud_func = (
            db.query(CloudFunction)
            .filter(
                CloudFunction.id == function_id, CloudFunction.project_id == project_id
            )
            .first()
        )

        if not cloud_func:
            raise ValueError(
                f"Cloud function with id {function_id} not found or does not belong to project {project_id}"
            )

        # Update fields if provided
        if code is not None:
            cloud_func.code = code
        if description is not None:
            cloud_func.description = description
        if name is not None:
            cloud_func.name = name
        if is_active is not None:
            cloud_func.is_active = is_active

        db.commit()
        db.refresh(cloud_func)

        return {
            "id": cloud_func.id,
            "project_id": cloud_func.project_id,
            "name": cloud_func.name,
            "code": cloud_func.code,
            "description": cloud_func.description,
            "runtime": cloud_func.runtime,
            "is_active": cloud_func.is_active,
            "created_at": (
                cloud_func.created_at.isoformat() if cloud_func.created_at else None
            ),
        }


def get_cloud_function(function_id: str) -> dict:
    """
    Get a cloud function by ID.

    Args:
        function_id (str): The ID of the cloud function to retrieve.

    Returns:
        dict: The cloud function as a dictionary.
    """
    with SessionLocal() as db:
        cloud_func = (
            db.query(CloudFunction).filter(CloudFunction.id == function_id).first()
        )

        if not cloud_func:
            raise ValueError(f"Cloud function with id {function_id} not found")

        return {
            "id": cloud_func.id,
            "project_id": cloud_func.project_id,
            "name": cloud_func.name,
            "code": cloud_func.code,
            "description": cloud_func.description,
            "runtime": cloud_func.runtime,
            "is_active": cloud_func.is_active,
            "created_at": (
                cloud_func.created_at.isoformat() if cloud_func.created_at else None
            ),
        }


def list_cloud_functions(project: str) -> list[dict]:
    """
    List all cloud functions for a project.

    Args:
        project (str): The project ID.

    Returns:
        list[dict]: List of cloud functions as dictionaries.
    """
    with SessionLocal() as db:
        functions = (
            db.query(CloudFunction).filter(CloudFunction.project_id == project).all()
        )

        return [
            {
                "id": func.id,
                "project_id": func.project_id,
                "name": func.name,
                "code": func.code,
                "description": func.description,
                "runtime": func.runtime,
                "is_active": func.is_active,
                "created_at": func.created_at.isoformat() if func.created_at else None,
            }
            for func in functions
        ]


def delete_cloud_function(function_id: str) -> dict:
    """
    Delete a cloud function.

    Args:
        function_id (str): The ID of the cloud function to delete.

    Returns:
        dict: Success message.
    """
    with SessionLocal() as db:
        cloud_func = (
            db.query(CloudFunction).filter(CloudFunction.id == function_id).first()
        )

        if not cloud_func:
            raise ValueError(f"Cloud function with id {function_id} not found")

        db.delete(cloud_func)
        db.commit()

        return {
            "success": True,
            "message": f"Cloud function {function_id} deleted successfully",
        }
