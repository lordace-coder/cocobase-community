from app.models.app_client import Project
from app.models.notifications import Notification
from app.core.database import SessionLocal


def send_notification_to_project_users(project_id: str, message):
    """
    Send a notification message to all users associated with a project.
    Args:
        project (Project): The project instance containing associated users.
        message (str): The notification message to be sent.
    """
    project = None
    with SessionLocal() as session:
        proj = session.query(Project).filter(Project.id == project_id).first()
        session.expunge_all()
    notification = f"Project '{project.name}': {message}"

    # Collect all user IDs (owner + shared users)
    user_ids = [project.owner.id]  # Start with project owner

    # Add all users the project is shared with
    for user in project.shared_with:
        user_ids.append(user.id)

    # Remove duplicates (in case owner is also in shared_with)
    user_ids = list(set(user_ids))

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


send_notification_to_project_users(
    "bb3e92c8-86d6-4794-ba12-05825e511ee6", "This is a test notification."
)
