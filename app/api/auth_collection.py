from datetime import datetime
from typing import Optional, List
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
    File,
    Form,
)
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.dependencies import get_app_user, get_project
from app.models.app_client import Project
from app.models.integrations import ProjectIntegration
from app.models.pricing import get_current_plan
from app.models.user import User
from app.models.app_client import AppUser
from app.services.email import notify_limit_reached, notify_limit_warning
from app.storage.storage import check_storage_limit, handle_file_upload
import json
from app.services.integrations import IntegrationService
from app.services.jwt import create_app_user_token, decode_app_user_token
from app.services.google_token_verifier import GoogleTokenVerifier
from app.services.apple_token_verifier import AppleTokenVerifier
from app.services.oauth_service import OAuthService
from app.schemas.auth_collection import (
    AppTokenResponse,
    AppUserSchema,
    AppUserResponse,
    AppUserUpdateSchema,
)


router = APIRouter(prefix="/auth-collections", tags=["App Client"])


@router.post("/login")
def user_login(
    payload: AppUserSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppTokenResponse:
    project = proj[0]
    try:
        user = (
            db.query(AppUser)
            .filter(AppUser.client_id == project.id, AppUser.email == payload.email)
            .first()
        )
        if not user:
            raise HTTPException(404, "Account with this email does not exist")
        # check if password is valid
        if user.compare_password(payload.password):
            # return api token
            return {"access_token": create_app_user_token(user)}
        else:
            raise HTTPException(400, "Invalid password value")

    except Exception as err:
        raise HTTPException(400, "An error occured " + str(err))


@router.post("/signup")
async def create_new_user(
    request: Request,
    bg: BackgroundTasks,
    data: str = Form(None, description="User data as JSON string"),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppTokenResponse:
    project = proj[0]

    # Parse user data - support both JSON body and multipart form
    user_data = {}
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        # Handle JSON request body
        try:
            user_data = await request.json()
        except Exception:
            raise HTTPException(400, "Invalid JSON in request body")
    elif data:
        # Handle multipart form data
        try:
            user_data = json.loads(data)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON in data field")

    if not user_data.get("email") or not user_data.get("password"):
        raise HTTPException(400, "Email and password are required")

    # Parse multipart form to get all file uploads (only if multipart request)
    form = None
    if "multipart/form-data" in content_type:
        form = await request.form()

    # Process all file uploads (simplified pattern)
    uploaded_files = {}  # {field_name: [urls]}

    if form:
        for field_name in form:
            if field_name in ("data",):
                continue

            field_value = form.get(field_name)

            # Check if it's a file
            if isinstance(field_value, StarletteUploadFile) and field_value.filename:
                # Read and upload file
                file_content = await field_value.read()
                file_size = len(file_content)

                check_storage_limit(project.id, file_size, db)

                file_url = await handle_file_upload(
                    file_content,
                    project.id,
                    field_value.filename,
                    subdirectory="users",
                    db=db,
                )

                # Store by field name
                if field_name not in uploaded_files:
                    uploaded_files[field_name] = []
                uploaded_files[field_name].append(file_url)

    # Add files to user data
    for field_name, urls in uploaded_files.items():
        if len(urls) == 1:
            user_data[field_name] = urls[0]
        else:
            user_data[field_name] = urls

    # check if limit has been reached
    plan = get_current_plan(project, db)

    # Check if user limit has been reached
    # max_users = 0 or None means unlimited users
    if plan.max_users is not None and plan.max_users > 0:
        current_user_count = (
            db.query(func.count(AppUser.id))
            .filter(AppUser.client_id == project.id)
            .scalar()
        )

        # Hard limit - deactivate project
        if current_user_count >= plan.max_users:
            project.is_active = False
            db.commit()

            # Notify user in background
            bg.add_task(notify_limit_reached, user, project, "users", plan.max_users)

            raise HTTPException(
                status_code=403,
                detail=f"User limit reached ({plan.max_users}). Project has been deactivated. Please upgrade your plan.",
            )

        # Soft limit - warning at 80% and 90%
        usage_percentage = (current_user_count / plan.max_users) * 100

        if usage_percentage >= 90:
            bg.add_task(
                notify_limit_warning,
                user,
                project,
                "users",
                current_user_count,
                plan.max_users,
                "critical",  # 90%+ is critical
            )
        elif usage_percentage >= 80:
            bg.add_task(
                notify_limit_warning,
                user,
                project,
                "users",
                current_user_count,
                plan.max_users,
                "warning",  # 80-89% is warning
            )

    if (
        db.query(AppUser)
        .filter(
            AppUser.client_id == project.id, AppUser.email == user_data.get("email")
        )
        .first()
    ):
        raise HTTPException(400, "User with this email already exists")
    else:
        # Extract password and remove from data (will be hashed separately)
        password = user_data.pop("password")

        # Create new user
        user = AppUser(**user_data)
        user.set_password(password)
        user.client_id = project.id
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"access_token": create_app_user_token(user)}


# list users with advanced querying
@router.get("/users")
def list_all_users(
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    limit: int = Query(50, ge=1, le=500),  # Reduced default and max for performance
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(
        None, description="Field to sort by (email, created_at, or data.field)"
    ),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    populate: Optional[list[str]] = Query(
        None, description="Relationships to populate"
    ),
) -> dict:
    """
    List AppUsers with advanced filtering, relationships, and JSONB querying.

    QUERY SYNTAX:
    =============

    1. FILTER STANDARD FIELDS:
       /users?email_contains=gmail
       /users?created_at_gte=2024-01-01

    2. FILTER JSONB DATA FIELDS:
       /users?data.username_contains=john
       /users?data.role=admin
       /users?data.age_gte=18

    3. OR CONDITIONS:
       /users?[or]data.role=admin&[or]data.role=moderator

    4. MULTI-FIELD SEARCH:
       /users?email__or__data.username_contains=john

    5. POPULATE SINGLE RELATIONSHIPS:
       /users?populate=profile_id
       → Fetches related document or user

    6. POPULATE MANY-TO-MANY RELATIONSHIPS:
       /users?populate=followers_ids&populate=following_ids
       → Fetches arrays of related users

    7. FILTER BY ARRAY CONTAINMENT:
       /users?data.followers_ids_array_contains=user-123
       → Find users who have user-123 in their followers array

    8. SORT BY JSONB FIELDS:
       /users?sort=data.username&order=asc

    OPERATORS: eq, ne, gt, gte, lt, lte, contains, startswith, endswith, in, notin, isnull, array_contains
    """
    from sqlalchemy import or_, and_, desc, asc, cast, String
    from app.api.user_relationship_helper import UserRelationshipHelper

    project = proj[0]

    # Start with base query
    query = db.query(AppUser).filter(AppUser.client_id == project.id)

    # Get query parameters
    query_params = dict(request.query_params)
    filter_params = {
        k: v
        for k, v in query_params.items()
        if k not in {"limit", "offset", "sort", "order", "populate"}
    }

    # Apply advanced filtering
    if filter_params:
        or_groups = {}
        and_conditions = []
        relationship_joins = {}  # Track joins to avoid duplicates

        for key, value in filter_params.items():
            # Check for OR conditions
            if key.startswith("[or"):
                import re

                match = re.match(r"\[or(?::(\w+))?\](.+)", key)
                if match:
                    group_name = match.group(1) or "default"
                    field_with_op = match.group(2)

                    if group_name not in or_groups:
                        or_groups[group_name] = []
                    or_groups[group_name].append((field_with_op, value))
                continue

            # Check for multi-field OR
            if "__or__" in key:
                or_conditions = []
                parts = key.split("__or__")
                for part in parts:
                    condition = _build_appuser_condition(part, value, AppUser)
                    if condition is not None:
                        or_conditions.append(condition)

                if or_conditions:
                    and_conditions.append(or_(*or_conditions))
                continue

            # Check for relationship filter (e.g., referred_by.email_eq)
            if "." in key and not key.startswith("data.") and not key.startswith("["):
                # Parse relationship filter
                rel_field, rest = key.split(".", 1)

                # Handle referred_by relationship
                if rel_field == "referred_by":
                    # Create alias for self-join if not already created
                    if "referred_by" not in relationship_joins:
                        from sqlalchemy.orm import aliased

                        ReferrerUser = aliased(AppUser)
                        relationship_joins["referred_by"] = ReferrerUser

                        # Join on the referred_by field in data (now JSONB)
                        query = query.outerjoin(
                            ReferrerUser,
                            AppUser.data["referred_by"].astext == ReferrerUser.id,
                        )

                    ReferrerUser = relationship_joins["referred_by"]

                    # Build condition on the joined referrer
                    condition = _build_appuser_condition(rest, value, ReferrerUser)
                    if condition is not None:
                        and_conditions.append(condition)
                    continue

            # Regular AND condition
            condition = _build_appuser_condition(key, value, AppUser)
            if condition is not None:
                and_conditions.append(condition)

        # Combine OR groups
        for group_conditions in or_groups.values():
            group_filters = []
            for field_with_op, value in group_conditions:
                condition = _build_appuser_condition(field_with_op, value, AppUser)
                if condition is not None:
                    group_filters.append(condition)

            if group_filters:
                and_conditions.append(or_(*group_filters))

        # Apply all conditions
        if and_conditions:
            query = query.filter(and_(*and_conditions))

    # Optimize COUNT: only count on first page OR if explicitly requested
    # Skip count entirely with ?count=false for maximum speed
    count_param = request.query_params.get("count", "auto").lower()
    if count_param == "false":
        total = -1  # Skip count
    elif count_param == "true" or (count_param == "auto" and offset == 0):
        total = query.count()
    else:
        total = -1  # Unknown count for pagination

    # Apply sorting
    if sort:
        if sort.startswith("data."):
            # Sort by JSONB field
            json_field = sort.replace("data.", "")
            sort_expr = AppUser.data[json_field].astext
            query = query.order_by(
                desc(sort_expr) if order == "desc" else asc(sort_expr)
            )
        else:
            # Sort by standard field
            sort_column = getattr(AppUser, sort, None)
            if sort_column is not None:
                query = query.order_by(
                    desc(sort_column) if order == "desc" else asc(sort_column)
                )
            else:
                query = query.order_by(desc(AppUser.created_at))
    else:
        query = query.order_by(desc(AppUser.created_at))

    # Apply pagination
    users = query.offset(offset).limit(limit).all()

    # Convert to dict format
    users_data = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "data": user.data or {},
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "oauth_id": user.oauth_id,
            "roles": user.roles or [],
        }
        users_data.append(user_dict)

    # Handle relationships if populate is specified
    if populate and users_data:
        helper = UserRelationshipHelper(db, project.id)
        users_data = helper.populate_user_relationships(users_data, populate)

    return {
        "data": users_data,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


def _build_appuser_condition(field_with_op: str, value: str, model):
    """Build SQLAlchemy condition for AppUser filtering (supports JSONB data field)"""
    from sqlalchemy import cast, String

    # Parse operator
    operators = [
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
        "startswith",
        "endswith",
        "in",
        "notin",
        "isnull",
        "array_contains",
    ]
    parts = field_with_op.split("_")

    operator = "eq"
    field_parts = parts

    # Check for array_contains (special case - two words)
    if len(parts) >= 3 and "_".join(parts[-2:]) == "array_contains":
        operator = "array_contains"
        field_parts = parts[:-2]
    elif len(parts) >= 2 and parts[-1] in operators:
        operator = parts[-1]
        field_parts = parts[:-1]

    field_name = "_".join(field_parts)

    # Check if it's a JSONB data field
    if field_name.startswith("data."):
        json_field = field_name.replace("data.", "")
        # model.data is now JSONB, access directly
        column = model.data[json_field].astext

        # Special handling for array_contains (check if value is in array)
        if operator == "array_contains":
            # Check if the JSONB array contains the value
            import json

            # Check if array contains the specific value
            return model.data[json_field].astext.contains(value)

        # Apply operator on JSONB field
        if operator == "eq":
            return column == value
        elif operator == "ne":
            return column != value
        elif operator == "gt":
            return cast(column, String) > value
        elif operator == "gte":
            return cast(column, String) >= value
        elif operator == "lt":
            return cast(column, String) < value
        elif operator == "lte":
            return cast(column, String) <= value
        elif operator == "contains":
            return column.ilike(f"%{value}%")
        elif operator == "startswith":
            return column.ilike(f"{value}%")
        elif operator == "endswith":
            return column.ilike(f"%{value}")
        elif operator == "in":
            values = [v.strip() for v in value.split(",")]
            return column.in_(values)
        elif operator == "notin":
            values = [v.strip() for v in value.split(",")]
            return ~column.in_(values)
        elif operator == "isnull":
            is_null = value.lower() in ["true", "1", "yes"]
            if is_null:
                # Field is null: either key doesn't exist OR value is null
                from sqlalchemy import or_

                return or_(
                    ~model.data.has_key(json_field),  # Key doesn't exist
                    model.data[json_field].astext.is_(
                        None
                    ),  # Key exists but value is null
                    model.data[json_field].astext
                    == "null",  # Key exists with JSON null value
                )
            else:
                # Field is not null: key exists AND has a non-null value
                from sqlalchemy import and_

                return and_(
                    model.data.has_key(json_field),  # Key exists
                    model.data[json_field].astext.isnot(None),  # Value is not null
                    model.data[json_field].astext != "null",  # Not JSON null
                )

    # Standard field (email, created_at, etc.)
    if not hasattr(model, field_name):
        return None

    column = getattr(model, field_name)

    # Apply operator on standard field
    if operator == "eq":
        return column == value
    elif operator == "ne":
        return column != value
    elif operator == "gt":
        return column > value
    elif operator == "gte":
        return column >= value
    elif operator == "lt":
        return column < value
    elif operator == "lte":
        return column <= value
    elif operator == "contains":
        return column.ilike(f"%{value}%")
    elif operator == "startswith":
        return column.ilike(f"{value}%")
    elif operator == "endswith":
        return column.ilike(f"%{value}")
    elif operator == "in":
        values = [v.strip() for v in value.split(",")]
        return column.in_(values)
    elif operator == "notin":
        values = [v.strip() for v in value.split(",")]
        return ~column.in_(values)
    elif operator == "isnull":
        is_null = value.lower() in ["true", "1", "yes"]
        return column.is_(None) if is_null else column.isnot(None)

    return None


# get user by id
@router.get("/users/{id}")
def get_all_users(
    id: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppUserResponse:
    users = (
        db.query(AppUser)
        .filter(AppUser.client_id == proj[0].id, AppUser.id == id)
        .first()
    )
    return users


# get current user
@router.get("/user")
def get_current_user_details(user: AppUser = Depends(get_app_user)) -> AppUserResponse:
    return user


# update user data
@router.patch("/user", response_model=AppUserResponse)
async def update_current_user_details(
    request: Request,
    data: str = Form(None, description="User data as JSON string"),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> AppUserResponse:
    if not user:
        raise HTTPException(401, "Not authenticated")
        raise HTTPException(401, "Not authenticated")

    # Get user's project for storage
    project = db.query(Project).filter(Project.id == user.client_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    # Parse update data - support both JSON body and multipart form
    update_data = {}
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        # Handle JSON request body
        try:
            update_data = await request.json()
        except Exception:
            raise HTTPException(400, "Invalid JSON in request body")
    elif data:
        # Handle multipart form data
        try:
            update_data = json.loads(data)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON in data field")

    # Parse multipart form to get all file uploads (only if multipart request)
    form = None
    if "multipart/form-data" in content_type:
        form = await request.form()

    # Process all file uploads (simplified pattern)
    uploaded_files = {}  # {field_name: [urls]}

    if form:
        for field_name in form:
            if field_name in ("data",):
                continue

            field_value = form.get(field_name)

            # Check if it's a file
            if isinstance(field_value, StarletteUploadFile) and field_value.filename:
                # Read and upload file
                file_content = await field_value.read()
                file_size = len(file_content)

                check_storage_limit(project.id, file_size, db)

                file_url = await handle_file_upload(
                    file_content,
                    project.id,
                    field_value.filename,
                    subdirectory="users",
                    db=db,
                )

                # Store by field name
                if field_name not in uploaded_files:
                    uploaded_files[field_name] = []
                uploaded_files[field_name].append(file_url)

    # Add files to update data
    for field_name, urls in uploaded_files.items():
        if len(urls) == 1:
            update_data[field_name] = urls[0]
        else:
            update_data[field_name] = urls

    # Update user fields
    if update_data:
        # Handle password separately (needs to be hashed)
        password = update_data.pop("password", None)

        # Update other fields
        for field, value in update_data.items():
            setattr(user, field, value)

        # Update password if provided
        if password:
            user.set_password(password)

        db.add(user)
        db.commit()
        db.refresh(user)

    return user


# *GOOGLE SIGN-IN (Token Verification)
class GoogleSignInRequest(BaseModel):
    id_token: str
    platform: Optional[str] = None  # 'web', 'mobile', 'ios', 'android' - for analytics


@router.post("/google-verify")
def verify_google_token(
    payload: GoogleSignInRequest,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verify Google ID token and authenticate user.

    This endpoint works for both web and mobile applications.
    Clients should use Google Sign-In SDK to obtain an ID token,
    then send it to this endpoint for verification.

    Args:
        payload: GoogleSignInRequest with id_token
        proj: Project tuple from dependency
        db: Database session

    Returns:
        {
            "access_token": "jwt_token",
            "user": {
                "id": "user_id",
                "email": "user@example.com",
                "data": {...},
                "oauth_provider": "google",
                "created_at": "timestamp"
            }
        }

    Raises:
        HTTPException 400: If integration not enabled or token invalid
        HTTPException 500: If server error occurs
    """
    project = proj[0]

    # Get integration settings
    integration = IntegrationService(db)
    project_integration: ProjectIntegration = integration.get_project_integration(
        project.id,
        "046deb41-47b3-403d-aee8-b80ccb80a87e",  # Google OAuth Integration ID
    )

    if not project_integration or not project_integration.is_enabled:
        raise HTTPException(
            status_code=400,
            detail="Google Sign-In integration is not enabled for this project"
        )

    config = dict(project_integration.config)

    # Get required settings from project config
    GOOGLE_CLIENT_ID = config.get("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_CLIENT_ID is not configured for this project"
        )

    try:
        # Verify the ID token
        verifier = GoogleTokenVerifier(GOOGLE_CLIENT_ID)
        user_info = verifier.get_user_info(payload.id_token)

        # Use OAuth service to find or create user
        oauth_service = OAuthService(db, project.id)
        result = oauth_service.find_or_create_user(
            email=user_info['email'],
            oauth_id=user_info['oauth_id'],
            provider='google',
            name=user_info.get('name', ''),
            picture=user_info.get('picture', ''),
            additional_data={
                'given_name': user_info.get('given_name', ''),
                'family_name': user_info.get('family_name', ''),
            }
        )

        return result

    except ValueError as e:
        # Token verification failed
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions from OAuth service
        raise
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during authentication: {str(e)}"
        )


# *APPLE SIGN-IN (Token Verification)
class AppleSignInRequest(BaseModel):
    id_token: str
    user: Optional[dict] = None  # Apple sends user data only on first auth
    platform: Optional[str] = None  # 'web', 'mobile', 'ios' - for analytics


@router.post("/apple-verify")
def verify_apple_token(
    payload: AppleSignInRequest,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verify Apple ID token and authenticate user.

    This endpoint works for both web and mobile applications.
    Clients should use Apple Sign-In SDK to obtain an ID token,
    then send it to this endpoint for verification.

    Note: Apple only sends user data (name) on first authentication.
    Store this information when received.

    Args:
        payload: AppleSignInRequest with id_token and optional user data
        proj: Project tuple from dependency
        db: Database session

    Returns:
        {
            "access_token": "jwt_token",
            "user": {
                "id": "user_id",
                "email": "user@example.com",
                "data": {...},
                "oauth_provider": "apple",
                "created_at": "timestamp"
            }
        }

    Raises:
        HTTPException 400: If integration not enabled or token invalid
        HTTPException 500: If server error occurs
    """
    project = proj[0]

    # Get integration settings
    # TODO: Create Apple Sign-In integration in database with a unique ID
    # For now, we'll create a placeholder - you need to insert this into your database
    APPLE_INTEGRATION_ID = "apple-signin-integration-id"  # Replace with actual UUID from database

    integration = IntegrationService(db)
    project_integration: ProjectIntegration = integration.get_project_integration(
        project.id,
        APPLE_INTEGRATION_ID,
    )

    if not project_integration or not project_integration.is_enabled:
        raise HTTPException(
            status_code=400,
            detail="Apple Sign-In integration is not enabled for this project"
        )

    config = dict(project_integration.config)

    # Get required settings from project config
    APPLE_CLIENT_ID = config.get("APPLE_CLIENT_ID")
    if not APPLE_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="APPLE_CLIENT_ID is not configured for this project"
        )

    try:
        # Verify the ID token
        verifier = AppleTokenVerifier(APPLE_CLIENT_ID)
        user_info = verifier.get_user_info(payload.id_token, payload.user)

        # Prepare additional data
        additional_data = {}
        if user_info.get('is_private_email'):
            additional_data['is_private_email'] = True

        # Use OAuth service to find or create user
        oauth_service = OAuthService(db, project.id)
        result = oauth_service.find_or_create_user(
            email=user_info['email'],
            oauth_id=user_info['oauth_id'],
            provider='apple',
            name=user_info.get('name', ''),
            picture='',  # Apple doesn't provide profile pictures
            additional_data=additional_data
        )

        return result

    except ValueError as e:
        # Token verification failed
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions from OAuth service
        raise
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during authentication: {str(e)}"
        )
