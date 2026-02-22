from app.models.app_client import Project
from app.models.notifications import Notification
from app.core.database import SessionLocal


def send_notification_to_project_users(project_id: str, message):
    """
    Send a notification message to all users associated with a project.
    Args:
        project_id (str): The project ID.
        message (str): The notification message to be sent.
    """
    # Fetch project and load relationships while still in session
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        if not project:
            raise ValueError(f"Project with id {project_id} not found")

        notification = f"Project '{project.name}': {message}"

        # Collect all user IDs (owner + shared users) BEFORE expunging
        user_ids = [project.owner.id]  # Start with project owner

        # Add all users the project is shared with
        for user in project.shared_with:
            user_ids.append(user.id)

        # Remove duplicates (in case owner is also in shared_with)
        user_ids = list(set(user_ids))

    # Now create notifications in a separate session
    # Prepare bulk notification data
    notifications_data = [
        {
            "message": notification,
            "user_id": user_id,
        }
        for user_id in user_ids
    ]

    # Bulk insert notifications
    with SessionLocal() as session:
        session.bulk_insert_mappings(Notification, notifications_data)
        session.commit()
