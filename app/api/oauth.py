# app/api/routes/oauth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import urlencode
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.oauth_client_service.oauth import OAuthService
from app.services.oauth_client_service.schemas import (
    OAuthClientCreate,
    OAuthClientResponse,
    TokenRequest,
    TokenResponse,
    UserInfoResponse,
    TokenIntrospectionRequest,
    TokenIntrospectionResponse,
)
from app.services.oauth_client_service.security import create_id_token
from app.models.oauth import OAuthAccessToken

router = APIRouter(prefix="/oauth", tags=["OAuth 2.0"])

from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

# Setup templates
templates = Jinja2Templates(directory="app/templates")


# =========================
# DEPENDENCY: Get current user from session
# =========================


def get_current_user_optional(request: Request):
    """Get current user if logged in, None otherwise"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return {"id": user_id, "email": "user@example.com", "name": "User"}


# =========================
# CLIENT MANAGEMENT ENDPOINTS
# =========================
@router.post("/clients", response_model=OAuthClientResponse)
def create_oauth_client(
    client_data: OAuthClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new OAuth client application.
    Returns client_id and client_secret (save the secret, it's only shown once!)
    """
    oauth_service = OAuthService(db)
    client, client_secret = oauth_service.create_client(client_data, current_user.id)

    response_data = OAuthClientResponse.from_orm(client)
    response_data.client_secret = client_secret  # Only returned on creation

    return response_data


@router.get("/clients/{client_id}")
def get_oauth_client(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get OAuth client details (without secret)"""
    oauth_service = OAuthService(db)
    client = oauth_service.get_client(client_id)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.owner_user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    return client


# =========================
# CONSENT HANDLING ENDPOINT
# =========================
@router.post("/authorize/consent")
def handle_consent(
    request: Request,
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    state: Optional[str] = Form(None),
    response_type: str = Form(...),
    nonce: Optional[str] = Form(None),
    code_challenge: Optional[str] = Form(None),
    approved: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Handle user consent form submission
    """
    oauth_service = OAuthService(db)

    # Get current user
    current_user = get_current_user_optional(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # If user denied consent
    if approved != "true":
        params = {
            "error": "access_denied",
            "error_description": "User denied authorization",
        }
        if state:
            params["state"] = state
        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)

    # Save user consent
    oauth_service.save_user_consent(current_user["id"], client_id, scope)

    # Generate authorization code
    if response_type == "code":
        code = oauth_service.create_authorization_code(
            client_id=client_id,
            user_id=current_user["id"],
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
        )

        params = {"code": code}
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)

    # Implicit flow
    else:
        access_token, expires_in = oauth_service.create_access_token(
            client_id=client_id,
            user_id=current_user["id"],
            scope=scope,
        )

        params = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}#{urlencode(params)}"
        return RedirectResponse(url=redirect_url)


@router.get("/login")
def login_page(request: Request, next: str = "/dashboard"):
    """
    Show login page, pass along `next` URL so after login user is redirected.
    Default redirect is /dashboard
    """
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "next": next, "error": None},
    )

@router.post("/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard"),  # default fallback
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.compare_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password", "next": next},
            status_code=400,
        )

    # ✅ Create session
    request.session["user_id"] = str(user.id)
    request.session["email"] = user.email

    # Redirect to `next` URL after login
    return RedirectResponse(url=next, status_code=302)

# =========================
# AUTHORIZATION ENDPOINT
# =========================
@router.get("/authorize")
def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str = "openid email profile",
    state: Optional[str] = None,
    nonce: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = "S256",
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    OAuth 2.0 Authorization Endpoint

    This is where users are redirected to authorize an application.
    In production, this would show a consent screen.
    """
    oauth_service = OAuthService(db)

    # Validate client
    client = oauth_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Invalid client_id")

    # Validate redirect URI
    if not oauth_service.verify_redirect_uri(client_id, redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")

    # Validate response_type
    if response_type not in ["code", "token"]:
        raise HTTPException(status_code=400, detail="Invalid response_type")

    # Check if user is logged in
    current_user = get_current_user_optional(request)
    if not current_user:
        # Redirect to login page with return URL
        from urllib.parse import quote

        login_url = f"/oauth/login?next={quote('/oauth/authorize?' + request.url.query)}"
        return RedirectResponse(url=login_url)

    # Check if user has already consented
    has_consent = oauth_service.check_user_consent(current_user["id"], client_id, scope)

    if not has_consent:
        # Show consent screen
        scopes_list = scope.split() if scope else []
        return templates.TemplateResponse(
            "consent.html",
            {
                "request": request,
                "client_id": client_id,
                "app_name": client.name,
                "app_description": client.description,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "scopes": scopes_list,  # For iterating in template
                "state": state,
                "response_type": response_type,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "user_email": current_user.get("email", "Unknown"),
                "user_name": current_user.get("name", "User"),
            },
        )

    # Generate authorization code (only if user has already consented)
    if response_type == "code":
        code = oauth_service.create_authorization_code(
            client_id=client_id,
            user_id=current_user["id"],
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
        )

        # Redirect back to application with code
        params = {"code": code}
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)

    # Implicit flow (not recommended, but included for completeness)
    else:
        access_token, expires_in = oauth_service.create_access_token(
            client_id=client_id,
            user_id=current_user["id"],
            scope=scope,
        )

        params = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}#{urlencode(params)}"
        return RedirectResponse(url=redirect_url)


# =========================
# TOKEN ENDPOINT
# =========================
@router.post("/token", response_model=TokenResponse)
def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    OAuth 2.0 Token Endpoint

    Exchange authorization code for access token, or refresh an access token.
    """
    oauth_service = OAuthService(db)

    # Verify client credentials
    if client_secret:
        if not oauth_service.verify_client_secret(client_id, client_secret):
            raise HTTPException(
                status_code=401,
                detail="Invalid client credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

    # Authorization Code Grant
    if grant_type == "authorization_code":
        if not code or not redirect_uri:
            raise HTTPException(status_code=400, detail="Missing code or redirect_uri")

        # Verify authorization code
        auth_code = oauth_service.verify_authorization_code(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

        if not auth_code:
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        # Create tokens
        access_token, expires_in = oauth_service.create_access_token(
            client_id=client_id,
            user_id=auth_code.user_id,
            scope=auth_code.scope,
        )

        refresh_token = oauth_service.create_refresh_token(
            client_id=client_id,
            user_id=auth_code.user_id,
        )

        response = TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
            scope=auth_code.scope,
        )

        # Create ID token if openid scope is requested
        if "openid" in auth_code.scope:
            # Fetch user data (implement based on your user model)
            user_data = {
                "id": auth_code.user_id,
                "email": "user@example.com",
                "name": "User Name",
            }
            id_token = create_id_token(user_data, client_id)
            response.id_token = id_token

        return response

    # Refresh Token Grant
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh_token")

        # Verify refresh token
        refresh_token_obj = oauth_service.verify_refresh_token(refresh_token)
        if not refresh_token_obj:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        # Create new access token
        access_token, expires_in = oauth_service.create_access_token(
            client_id=refresh_token_obj.client_id,
            user_id=refresh_token_obj.user_id,
            scope="openid email profile",  # Use stored scope
        )

        # Optionally rotate refresh token
        new_refresh_token = oauth_service.rotate_refresh_token(refresh_token)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=new_refresh_token or refresh_token,
        )

    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")


# =========================
# TOKEN INTROSPECTION
# =========================
@router.post("/introspect", response_model=TokenIntrospectionResponse)
def introspect_token(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Token introspection endpoint (RFC 7662)

    Allows resource servers to validate tokens.
    """
    oauth_service = OAuthService(db)

    # Verify client credentials
    if not oauth_service.verify_client_secret(client_id, client_secret):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    # Verify token
    access_token = oauth_service.verify_access_token(token)

    if not access_token:
        return TokenIntrospectionResponse(active=False)

    return TokenIntrospectionResponse(
        active=True,
        scope=access_token.scope,
        client_id=access_token.client_id,
        sub=access_token.user_id,
        exp=int(access_token.expires_at.timestamp()),
    )


# =========================
# TOKEN REVOCATION
# =========================
@router.post("/revoke")
def revoke_token(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form("access_token"),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Token revocation endpoint (RFC 7009)
    """
    oauth_service = OAuthService(db)

    # Verify client credentials
    if not oauth_service.verify_client_secret(client_id, client_secret):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    # Revoke token
    oauth_service.revoke_token(token, token_type_hint)

    return {"status": "success"}


# =========================
# USERINFO ENDPOINT (OpenID Connect)
# =========================
@router.get("/userinfo", response_model=UserInfoResponse)
def userinfo(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    OpenID Connect UserInfo Endpoint

    Returns claims about the authenticated user.
    """
    # Extract bearer token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ")[1]

    # Verify access token
    oauth_service = OAuthService(db)
    access_token = oauth_service.verify_access_token(token)

    if not access_token:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch user data (implement based on your user model)
    # This is a placeholder - fetch real user data from database
    user_data = {
        "sub": access_token.user_id,
        "email": "user@example.com",
        "email_verified": True,
        "name": "User Name",
        "picture": "https://example.com/avatar.jpg",
    }

    # Filter claims based on requested scope
    scopes = access_token.scope.split() if access_token.scope else []
    response = {"sub": user_data["sub"]}

    if "email" in scopes:
        response["email"] = user_data["email"]
        response["email_verified"] = user_data["email_verified"]

    if "profile" in scopes:
        response["name"] = user_data.get("name")
        response["picture"] = user_data.get("picture")

    return UserInfoResponse(**response)


# =========================
# OPENID CONFIGURATION (Discovery)
# =========================
@router.get("/.well-known/openid-configuration")
def openid_configuration():
    """
    OpenID Connect Discovery endpoint

    Provides metadata about the OAuth/OIDC provider.
    """
    base_url = "https://cocobase.com"  # Replace with your actual domain

    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "userinfo_endpoint": f"{base_url}/oauth/userinfo",
        "jwks_uri": f"{base_url}/oauth/.well-known/jwks.json",
        "introspection_endpoint": f"{base_url}/oauth/introspect",
        "revocation_endpoint": f"{base_url}/oauth/revoke",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256", "RS256"],
        "scopes_supported": ["openid", "email", "profile"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
        ],
        "claims_supported": ["sub", "email", "email_verified", "name", "picture"],
        "code_challenge_methods_supported": ["S256"],
    }
