"""
Google ID Token Verification Service

This module provides functionality to verify Google ID tokens received from
client applications (web, mobile, etc.) using Google's public certificates.
"""

from google.oauth2 import id_token
from google.auth.transport import requests
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GoogleTokenVerifier:
    """Verify Google ID tokens and extract user information."""

    def __init__(self, client_id: str):
        """
        Initialize the Google token verifier.

        Args:
            client_id: Google OAuth 2.0 Client ID
        """
        self.client_id = client_id
        self.request = requests.Request()

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify a Google ID token and return user information.

        Args:
            token: The ID token from Google Sign-In

        Returns:
            Dictionary containing user info if valid, None if invalid
            {
                'sub': Google user ID (unique identifier),
                'email': User's email address,
                'email_verified': Boolean,
                'name': User's full name,
                'picture': Profile picture URL,
                'given_name': First name,
                'family_name': Last name,
                'locale': User's locale
            }

        Raises:
            ValueError: If token is invalid or verification fails
        """
        try:
            # Verify the token using Google's public keys
            idinfo = id_token.verify_oauth2_token(
                token,
                self.request,
                self.client_id
            )

            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid token issuer')

            # Ensure email is verified
            if not idinfo.get('email_verified', False):
                raise ValueError('Email not verified by Google')

            logger.info(f"Successfully verified Google token for user: {idinfo.get('email')}")

            return idinfo

        except ValueError as e:
            logger.error(f"Google token verification failed: {str(e)}")
            raise ValueError(f"Invalid Google ID token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Google token verification: {str(e)}")
            raise ValueError(f"Token verification error: {str(e)}")

    def get_user_info(self, token: str) -> Dict[str, str]:
        """
        Verify token and extract essential user information.

        Args:
            token: The ID token from Google Sign-In

        Returns:
            Dictionary with essential user info:
            {
                'oauth_id': Unique Google user ID,
                'email': Email address,
                'name': Full name,
                'picture': Profile picture URL
            }
        """
        idinfo = self.verify_token(token)

        return {
            'oauth_id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'given_name': idinfo.get('given_name', ''),
            'family_name': idinfo.get('family_name', ''),
        }
