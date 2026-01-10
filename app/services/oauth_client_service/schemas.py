# app/schemas/oauth.py
from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional
from datetime import datetime


# =========================
# CLIENT SCHEMAS
# =========================
class OAuthClientCreate(BaseModel):
    name: str
    description: Optional[str] = None
    redirect_uris: List[str]
    scopes: List[str] = ["openid", "email", "profile"]
    is_confidential: bool = True

    @validator('redirect_uris')
    def validate_redirect_uris(cls, v):
        if not v:
            raise ValueError('At least one redirect URI is required')
        for uri in v:
            if not uri.startswith(('http://', 'https://')):
                raise ValueError('Redirect URIs must use http or https')
        return v


class OAuthClientResponse(BaseModel):
    id: str
    client_id: str
    client_secret: str  # Only returned on creation
    name: str
    description: Optional[str]
    redirect_uris: List[str]
    scopes: List[str]
    is_confidential: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthClientInfo(BaseModel):
    """Public client info (no secret)"""
    id: str
    client_id: str
    name: str
    description: Optional[str]
    redirect_uris: List[str]
    scopes: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthClientUpdate(BaseModel):
    """Update OAuth client (all fields optional)"""
    name: Optional[str] = None
    description: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    scopes: Optional[List[str]] = None

    @validator('redirect_uris')
    def validate_redirect_uris(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError('At least one redirect URI is required')
        if v is not None:
            for uri in v:
                if not uri.startswith(('http://', 'https://')):
                    raise ValueError('Redirect URIs must use http or https')
        return v


# =========================
# AUTHORIZATION SCHEMAS
# =========================
class AuthorizationRequest(BaseModel):
    response_type: str  # "code" or "token"
    client_id: str
    redirect_uri: str
    scope: Optional[str] = "openid email profile"
    state: Optional[str] = None
    nonce: Optional[str] = None  # For OpenID Connect
    code_challenge: Optional[str] = None  # For PKCE
    code_challenge_method: Optional[str] = "S256"

    @validator('response_type')
    def validate_response_type(cls, v):
        if v not in ['code', 'token']:
            raise ValueError('response_type must be "code" or "token"')
        return v


class AuthorizationResponse(BaseModel):
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


# =========================
# TOKEN SCHEMAS
# =========================
class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    code_verifier: Optional[str] = None  # For PKCE

    @validator('grant_type')
    def validate_grant_type(cls, v):
        valid_types = ['authorization_code', 'refresh_token', 'client_credentials']
        if v not in valid_types:
            raise ValueError(f'grant_type must be one of {valid_types}')
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None  # OpenID Connect
    scope: Optional[str] = None


class TokenIntrospectionRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = None


class TokenIntrospectionResponse(BaseModel):
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[int] = None
    sub: Optional[str] = None


# =========================
# USERINFO SCHEMA (OpenID Connect)
# =========================
class UserInfoResponse(BaseModel):
    sub: str  # User ID
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    locale: Optional[str] = None


# =========================
# CONSENT SCHEMA
# =========================
class ConsentRequest(BaseModel):
    client_id: str
    scope: str
    approved: bool


class ConsentResponse(BaseModel):
    id: str
    user_id: str
    client_id: str
    scope: str
    created_at: datetime

    class Config:
        from_attributes = True