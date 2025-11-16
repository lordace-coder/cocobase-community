"""
Apple ID Token Verification Service

This module provides functionality to verify Apple ID tokens received from
client applications (web, mobile, iOS, etc.) using Apple's public keys.
"""

import jwt
import time
import requests
from typing import Dict, Optional
import logging
from jwt.algorithms import RSAAlgorithm

logger = logging.getLogger(__name__)


class AppleTokenVerifier:
    """Verify Apple ID tokens and extract user information."""

    APPLE_PUBLIC_KEYS_URL = "https://appleid.apple.com/auth/keys"
    APPLE_ISSUER = "https://appleid.apple.com"

    def __init__(self, client_id: str):
        """
        Initialize the Apple token verifier.

        Args:
            client_id: Apple Service ID (for web) or App Bundle ID (for iOS)
        """
        self.client_id = client_id
        self._public_keys = None
        self._keys_last_fetched = 0
        self._keys_cache_duration = 3600  # Cache keys for 1 hour

    def _get_apple_public_keys(self) -> Dict:
        """
        Fetch Apple's public keys for token verification.
        Implements caching to avoid excessive API calls.

        Returns:
            Dictionary of Apple's public keys
        """
        current_time = time.time()

        # Return cached keys if still valid
        if (self._public_keys and
            current_time - self._keys_last_fetched < self._keys_cache_duration):
            return self._public_keys

        try:
            response = requests.get(self.APPLE_PUBLIC_KEYS_URL, timeout=10)
            response.raise_for_status()
            self._public_keys = response.json()
            self._keys_last_fetched = current_time
            logger.info("Successfully fetched Apple public keys")
            return self._public_keys
        except Exception as e:
            logger.error(f"Failed to fetch Apple public keys: {str(e)}")
            if self._public_keys:
                # Return stale keys if available
                logger.warning("Using stale Apple public keys due to fetch failure")
                return self._public_keys
            raise ValueError("Unable to fetch Apple public keys for token verification")

    def _get_public_key(self, kid: str) -> str:
        """
        Get the public key matching the token's key ID.

        Args:
            kid: Key ID from token header

        Returns:
            Public key in PEM format
        """
        keys_data = self._get_apple_public_keys()

        # Find the key matching the kid
        for key in keys_data.get('keys', []):
            if key.get('kid') == kid:
                # Convert JWK to PEM format
                public_key = RSAAlgorithm.from_jwk(key)
                return public_key

        raise ValueError(f"Unable to find public key with kid: {kid}")

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify an Apple ID token and return user information.

        Args:
            token: The ID token from Apple Sign-In

        Returns:
            Dictionary containing user info if valid
            {
                'sub': Apple user ID (unique identifier),
                'email': User's email address,
                'email_verified': Boolean (string: 'true' or 'false'),
                'is_private_email': Boolean,
                'iss': Issuer (https://appleid.apple.com),
                'aud': Audience (your client_id),
                'exp': Expiration time,
                'iat': Issued at time
            }

        Raises:
            ValueError: If token is invalid or verification fails
        """
        try:
            # Decode header to get key ID (kid)
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')

            if not kid:
                raise ValueError("Token header missing 'kid' field")

            # Get the public key for this kid
            public_key = self._get_public_key(kid)

            # Verify and decode the token
            decoded_token = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=self.APPLE_ISSUER
            )

            logger.info(f"Successfully verified Apple token for user: {decoded_token.get('email', 'N/A')}")

            return decoded_token

        except jwt.ExpiredSignatureError:
            logger.error("Apple token has expired")
            raise ValueError("Apple ID token has expired")
        except jwt.InvalidAudienceError:
            logger.error(f"Invalid audience in Apple token. Expected: {self.client_id}")
            raise ValueError("Invalid Apple ID token audience")
        except jwt.InvalidIssuerError:
            logger.error("Invalid issuer in Apple token")
            raise ValueError("Invalid Apple ID token issuer")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Apple token: {str(e)}")
            raise ValueError(f"Invalid Apple ID token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Apple token verification: {str(e)}")
            raise ValueError(f"Token verification error: {str(e)}")

    def get_user_info(self, token: str, user_data: Optional[Dict] = None) -> Dict[str, str]:
        """
        Verify token and extract essential user information.

        Note: Apple only sends full user data (name) on first authentication.
        On subsequent logins, only the ID token is provided.

        Args:
            token: The ID token from Apple Sign-In
            user_data: Optional user object from first-time sign-in containing:
                      {'name': {'firstName': '...', 'lastName': '...'}}

        Returns:
            Dictionary with essential user info:
            {
                'oauth_id': Unique Apple user ID,
                'email': Email address (may be private relay),
                'name': Full name (if provided),
                'is_private_email': Boolean indicating private relay usage
            }
        """
        token_data = self.verify_token(token)

        # Extract name from user_data if provided (first-time sign-in)
        name = ''
        if user_data and 'name' in user_data:
            first_name = user_data['name'].get('firstName', '')
            last_name = user_data['name'].get('lastName', '')
            name = f"{first_name} {last_name}".strip()

        return {
            'oauth_id': token_data['sub'],
            'email': token_data['email'],
            'name': name,
            'is_private_email': token_data.get('is_private_email', False),
            'email_verified': token_data.get('email_verified', 'false') == 'true'
        }
