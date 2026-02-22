"""
Unified OAuth Service

Handles common OAuth operations like finding/creating users,
preventing mixed authentication, and generating tokens.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta
from app.models.app_client import AppUser, Project
from app.models.two_factor_auth import TwoFactorCode, TwoFactorSettings
from app.services.jwt import create_app_user_token
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OAuthService:
    """Unified service for OAuth user management."""

    def __init__(self, db: Session, project_id: str):
        """
        Initialize OAuth service.

        Args:
            db: Database session
            project_id: Project ID for this authentication
        """
        self.db = db
        self.project_id = project_id
        self._project = None

    @property
    def project(self) -> Optional[Project]:
        """Lazy load project for config access."""
        if self._project is None:
            self._project = self.db.query(Project).filter(Project.id == self.project_id).first()
        return self._project

    def _check_2fa_required(self, user: AppUser) -> Optional[Dict]:
        """
        Check if 2FA is required for user and generate code if needed.

        Returns:
            Dict with requires_2fa=True if 2FA needed, None otherwise
        """
        project = self.project
        if not project or not project.configs:
            return None

        if not project.configs.get('ENABLE_2FA', False):
            return None

        # Check if user has 2FA enabled
        settings = self.db.query(TwoFactorSettings).filter(
            TwoFactorSettings.user_id == user.id,
            TwoFactorSettings.is_enabled == True
        ).first()

        if not settings:
            return None

        # Check if there's a recent valid 2FA verification
        recent_verification = settings.last_verified_at and \
            settings.last_verified_at >= datetime.utcnow() - timedelta(minutes=5)

        if recent_verification:
            # User has recently verified 2FA, allow login
            settings.last_verified_at = None
            self.db.commit()
            return None

        # Check for existing pending code
        existing_code = self.db.query(TwoFactorCode).filter(
            TwoFactorCode.user_id == user.id,
            TwoFactorCode.project_id == self.project_id,
            TwoFactorCode.is_used == False,
            TwoFactorCode.created_at >= datetime.utcnow() - timedelta(minutes=2)
        ).order_by(TwoFactorCode.created_at.desc()).first()

        if existing_code and existing_code.is_valid():
            return {
                "requires_2fa": True,
                "message": "2FA code already sent. Please check your email.",
                "user_email": user.email
            }

        # Generate new 2FA code
        otp_length = project.configs.get('OTP_LENGTH', 6)
        otp_length = max(4, min(10, otp_length))
        code = TwoFactorCode.generate_code(length=otp_length)
        expiry_minutes = 10

        twofa_code = TwoFactorCode(
            user_id=user.id,
            project_id=self.project_id,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes)
        )
        self.db.add(twofa_code)
        self.db.commit()

        # Return 2FA required response (caller should send email)
        return {
            "requires_2fa": True,
            "message": "2FA code sent to your email",
            "user_email": user.email,
            "_2fa_code": code,  # Internal: caller uses this to send email
            "_expiry_minutes": expiry_minutes
        }

    def find_or_create_user(
        self,
        email: str,
        oauth_id: str,
        provider: str,
        name: str = "",
        picture: str = "",
        additional_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Find existing user or create new user with OAuth credentials.

        Args:
            email: User's email address
            oauth_id: Unique OAuth ID from provider (Google's 'sub', Apple's 'sub', etc.)
            provider: OAuth provider name ('google', 'apple', etc.)
            name: User's full name
            picture: Profile picture URL
            additional_data: Additional user data to store in JSONB field

        Returns:
            Dictionary with access_token and user info

        Raises:
            HTTPException: If email exists with different auth method or other errors
        """
        try:
            # Check if user exists with this email
            existing_user = (
                self.db.query(AppUser)
                .filter(
                    AppUser.email == email,
                    AppUser.client_id == self.project_id
                )
                .first()
            )

            if existing_user:
                # User exists - validate authentication method
                if not existing_user.oauth_id:
                    # User registered with email/password
                    logger.warning(f"Login attempt with {provider} for password-registered account: {email}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"This email is already registered with password authentication. Please login with email and password instead."
                    )

                if existing_user.oauth_provider != provider:
                    # User registered with different OAuth provider
                    logger.warning(
                        f"Login attempt with {provider} for {existing_user.oauth_provider}-registered account: {email}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"This email is already registered with {existing_user.oauth_provider.title()} Sign-In. Please use {existing_user.oauth_provider.title()} to login."
                    )

                # User exists with same OAuth provider - check 2FA before login
                logger.info(f"Logging in existing {provider} user: {email}")

                # Check if 2FA is required
                twofa_response = self._check_2fa_required(existing_user)
                if twofa_response:
                    return twofa_response

                access_token = create_app_user_token(existing_user)

                return {
                    "access_token": access_token,
                    "user": {
                        "id": existing_user.id,
                        "email": existing_user.email,
                        "data": existing_user.data or {},
                        "oauth_provider": existing_user.oauth_provider,
                        "created_at": existing_user.created_at.isoformat() if existing_user.created_at else None,
                    }
                }

            else:
                # Create new user
                logger.info(f"Creating new {provider} user: {email}")

                # Prepare user data
                user_data = additional_data or {}

                # Generate username from name or email
                if name:
                    username = name.replace(" ", "").lower()
                else:
                    username = email.split("@")[0]

                # Add basic profile info to data
                user_data.update({
                    "username": username,
                    "name": name,
                    "picture": picture
                })

                # Create new user
                new_user = AppUser(
                    email=email,
                    client_id=self.project_id,
                    oauth_id=oauth_id,
                    oauth_provider=provider,
                    password=email,  # Placeholder password (user can't login with it)
                    data=user_data
                )

                self.db.add(new_user)
                self.db.commit()
                self.db.refresh(new_user)

                # Generate token
                access_token = create_app_user_token(new_user)

                logger.info(f"Successfully created new {provider} user: {email}")

                return {
                    "access_token": access_token,
                    "user": {
                        "id": new_user.id,
                        "email": new_user.email,
                        "data": new_user.data or {},
                        "oauth_provider": new_user.oauth_provider,
                        "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
                    }
                }

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error in OAuth user management: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred during authentication: {str(e)}"
            )

    def verify_oauth_user(self, email: str, oauth_id: str, provider: str) -> Optional[AppUser]:
        """
        Verify and retrieve an OAuth user by email and OAuth ID.

        Args:
            email: User's email address
            oauth_id: OAuth ID from provider
            provider: OAuth provider name

        Returns:
            AppUser if found and valid, None otherwise
        """
        user = (
            self.db.query(AppUser)
            .filter(
                AppUser.email == email,
                AppUser.client_id == self.project_id,
                AppUser.oauth_id == oauth_id,
                AppUser.oauth_provider == provider
            )
            .first()
        )

        return user
