# app/services/oauth_service.py
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import secrets

from app.models.oauth import (
    OAuthClient,
    OAuthAuthorizationCode,
    OAuthAccessToken,
    OAuthRefreshToken,
    OAuthUserConsent,
)
from app.services.oauth_client_service.security import (
    generate_token,
    hash_secret,
    verify_secret,
    create_jwt_token,
    create_id_token,
    verify_pkce_challenge,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    AUTH_CODE_EXPIRE_MINUTES,
)
from app.services.oauth_client_service.schemas import (
    OAuthClientCreate,
    AuthorizationRequest,
    TokenRequest,
)


class OAuthService:
    def __init__(self, db: Session):
        self.db = db

    # =========================
    # CLIENT MANAGEMENT
    # =========================
    def create_client(
        self, client_data: OAuthClientCreate, owner_user_id: str
    ) -> tuple:
        """Create a new OAuth client application"""
        client_id = f"coco_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        hashed_secret = hash_secret(client_secret)

        client = OAuthClient(
            client_id=client_id,
            client_secret=hashed_secret,
            name=client_data.name,
            description=client_data.description,
            redirect_uris=client_data.redirect_uris,
            scopes=client_data.scopes,
            is_confidential=client_data.is_confidential,
            owner_user_id=owner_user_id,
        )

        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)

        return client, client_secret  # Return plaintext secret only once

    def get_client(self, client_id: str) -> Optional[OAuthClient]:
        """Get client by client_id"""
        return (
            self.db.query(OAuthClient)
            .filter(OAuthClient.client_id == client_id)
            .first()
        )

    def verify_client_secret(self, client_id: str, client_secret: str) -> bool:
        """Verify client credentials"""
        client = self.get_client(client_id)
        if not client:
            return False
        return verify_secret(client_secret, client.client_secret)

    def verify_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Verify redirect URI is registered for this client"""
        client = self.get_client(client_id)
        if not client:
            return False
        return redirect_uri in client.redirect_uris

    # =========================
    # AUTHORIZATION CODE FLOW
    # =========================
    def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: Optional[str] = None,
    ) -> str:
        """Create an authorization code"""
        code = generate_token(32)
        expires_at = datetime.utcnow() + timedelta(minutes=AUTH_CODE_EXPIRE_MINUTES)

        auth_code = OAuthAuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            expires_at=expires_at,
        )

        # Store PKCE challenge if provided
        if code_challenge:
            # You'd want to add a code_challenge column to the model
            # auth_code.code_challenge = code_challenge
            pass

        self.db.add(auth_code)
        self.db.commit()

        return code

    def verify_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> Optional[OAuthAuthorizationCode]:
        """Verify and consume an authorization code"""
        auth_code = (
            self.db.query(OAuthAuthorizationCode)
            .filter(
                OAuthAuthorizationCode.code == code,
                OAuthAuthorizationCode.client_id == client_id,
                OAuthAuthorizationCode.used == False,
            )
            .first()
        )

        if not auth_code:
            return None

        # Check expiration
        if datetime.utcnow() > auth_code.expires_at:
            return None

        # Verify redirect URI
        if auth_code.redirect_uri != redirect_uri:
            return None

        # Verify PKCE if challenge was used
        # if auth_code.code_challenge and code_verifier:
        #     if not verify_pkce_challenge(code_verifier, auth_code.code_challenge):
        #         return None

        # Mark as used
        auth_code.used = True
        self.db.commit()

        return auth_code

    # =========================
    # TOKEN MANAGEMENT
    # =========================
    def create_access_token(
        self,
        client_id: str,
        user_id: str,
        scope: str,
    ) -> tuple:
        """Create an access token and return token + expires_in"""
        token = generate_token(48)
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        access_token = OAuthAccessToken(
            token=token,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            expires_at=expires_at,
        )

        self.db.add(access_token)
        self.db.commit()

        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return token, expires_in

    def create_refresh_token(
        self,
        client_id: str,
        user_id: str,
    ) -> str:
        """Create a refresh token"""
        token = generate_token(48)
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_token = OAuthRefreshToken(
            token=token,
            client_id=client_id,
            user_id=user_id,
            expires_at=expires_at,
        )

        self.db.add(refresh_token)
        self.db.commit()

        return token

    def verify_access_token(self, token: str) -> Optional[OAuthAccessToken]:
        """Verify an access token"""
        access_token = (
            self.db.query(OAuthAccessToken)
            .filter(
                OAuthAccessToken.token == token,
                OAuthAccessToken.revoked == False,
            )
            .first()
        )

        if not access_token:
            return None

        # Check expiration
        if datetime.utcnow() > access_token.expires_at:
            return None

        return access_token

    def verify_refresh_token(self, token: str) -> Optional[OAuthRefreshToken]:
        """Verify a refresh token"""
        refresh_token = (
            self.db.query(OAuthRefreshToken)
            .filter(
                OAuthRefreshToken.token == token,
                OAuthRefreshToken.revoked == False,
            )
            .first()
        )

        if not refresh_token:
            return None

        # Check expiration
        if datetime.utcnow() > refresh_token.expires_at:
            return None

        return refresh_token

    def rotate_refresh_token(self, old_token: str) -> Optional[str]:
        """Rotate a refresh token (revoke old, create new)"""
        old_refresh = self.verify_refresh_token(old_token)
        if not old_refresh:
            return None

        # Revoke old token
        old_refresh.revoked = True

        # Create new token
        new_token = self.create_refresh_token(
            old_refresh.client_id,
            old_refresh.user_id,
        )

        self.db.commit()
        return new_token

    def revoke_token(self, token: str, token_type: str = "access"):
        """Revoke an access or refresh token"""
        if token_type == "access":
            token_obj = (
                self.db.query(OAuthAccessToken)
                .filter(OAuthAccessToken.token == token)
                .first()
            )
        else:
            token_obj = (
                self.db.query(OAuthRefreshToken)
                .filter(OAuthRefreshToken.token == token)
                .first()
            )

        if token_obj:
            token_obj.revoked = True
            self.db.commit()

    # =========================
    # USER CONSENT
    # =========================
    def check_user_consent(self, user_id: str, client_id: str, scope: str) -> bool:
        """Check if user has already consented to this scope"""
        consent = (
            self.db.query(OAuthUserConsent)
            .filter(
                OAuthUserConsent.user_id == user_id,
                OAuthUserConsent.client_id == client_id,
            )
            .first()
        )

        if not consent:
            return False

        # Check if all requested scopes are in the consent
        requested_scopes = set(scope.split())
        consented_scopes = set(consent.scope.split())

        return requested_scopes.issubset(consented_scopes)

    def save_user_consent(self, user_id: str, client_id: str, scope: str):
        """Save or update user consent"""
        consent = (
            self.db.query(OAuthUserConsent)
            .filter(
                OAuthUserConsent.user_id == user_id,
                OAuthUserConsent.client_id == client_id,
            )
            .first()
        )

        if consent:
            # Update existing consent with new scopes
            existing_scopes = set(consent.scope.split())
            new_scopes = set(scope.split())
            combined_scopes = existing_scopes.union(new_scopes)
            consent.scope = " ".join(combined_scopes)
            consent.updated_at = datetime.utcnow()
        else:
            # Create new consent
            consent = OAuthUserConsent(
                user_id=user_id,
                client_id=client_id,
                scope=scope,
            )
            self.db.add(consent)

        self.db.commit()

    def revoke_user_consent(self, user_id: str, client_id: str):
        """Revoke user consent for a client"""
        consent = (
            self.db.query(OAuthUserConsent)
            .filter(
                OAuthUserConsent.user_id == user_id,
                OAuthUserConsent.client_id == client_id,
            )
            .first()
        )

        if consent:
            self.db.delete(consent)
            self.db.commit()
