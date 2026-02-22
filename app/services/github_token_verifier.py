"""
GitHub OAuth Token Verification Service

This module provides functionality to verify GitHub OAuth access tokens received from
client applications (web, mobile, etc.) and fetch user information from GitHub's API.
"""

import requests
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GitHubTokenVerifier:
    """Verify GitHub OAuth tokens and extract user information."""

    def __init__(self, client_id: str, client_secret: Optional[str] = None):
        """
        Initialize the GitHub token verifier.

        Args:
            client_id: GitHub OAuth App Client ID
            client_secret: GitHub OAuth App Client Secret (optional, only needed for code exchange)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_base_url = "https://api.github.com"

    def verify_token(self, access_token: str) -> Optional[Dict]:
        """
        Verify a GitHub access token and return user information.

        Args:
            access_token: The access token from GitHub OAuth

        Returns:
            Dictionary containing user info if valid, None if invalid
            {
                'id': GitHub user ID (unique identifier),
                'login': GitHub username,
                'email': User's email address (may be None if private),
                'name': User's full name,
                'avatar_url': Profile picture URL,
                'bio': User bio,
                'location': User location,
                'company': User's company
            }

        Raises:
            ValueError: If token is invalid or verification fails
        """
        try:
            # Verify the token by making a request to GitHub API
            logger.info(f"Verifying GitHub token (first 10 chars): {access_token[:10]}...")

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }

            # Get user information
            user_response = requests.get(
                f'{self.api_base_url}/user',
                headers=headers,
                timeout=10
            )

            logger.info(f"GitHub API response status: {user_response.status_code}")

            if user_response.status_code != 200:
                # Log the error response for debugging
                try:
                    error_body = user_response.json()
                    logger.error(f"GitHub API error response: {error_body}")
                except:
                    logger.error(f"GitHub API error response (raw): {user_response.text}")
                raise ValueError(f'Failed to fetch user info: {user_response.status_code}')

            user_info = user_response.json()

            # Get user's email if not public
            if not user_info.get('email'):
                email_response = requests.get(
                    f'{self.api_base_url}/user/emails',
                    headers=headers,
                    timeout=10
                )

                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Find primary verified email
                    for email_obj in emails:
                        if email_obj.get('primary') and email_obj.get('verified'):
                            user_info['email'] = email_obj.get('email')
                            break

            # Ensure we have an email
            if not user_info.get('email'):
                raise ValueError('Unable to retrieve verified email from GitHub')

            logger.info(f"Successfully verified GitHub token for user: {user_info.get('login')}")

            return user_info

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {str(e)}")
            raise ValueError(f"Failed to communicate with GitHub API: {str(e)}")
        except ValueError as e:
            logger.error(f"GitHub token verification failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during GitHub token verification: {str(e)}")
            raise ValueError(f"Token verification error: {str(e)}")

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> str:
        """
        Exchange authorization code for access token.

        This is used when implementing the OAuth flow server-side.

        Args:
            code: Authorization code from GitHub OAuth callback
            redirect_uri: The redirect URI used in the OAuth flow

        Returns:
            Access token string

        Raises:
            ValueError: If code exchange fails or client_secret not provided
        """
        if not self.client_secret:
            raise ValueError("Client secret is required for code exchange")

        try:
            token_response = requests.post(
                'https://github.com/login/oauth/access_token',
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri
                },
                headers={'Accept': 'application/json'},
                timeout=10
            )

            if token_response.status_code != 200:
                raise ValueError(f'Failed to exchange code: {token_response.status_code}')

            token_data = token_response.json()

            if 'error' in token_data:
                raise ValueError(f"GitHub OAuth error: {token_data.get('error_description', token_data.get('error'))}")

            access_token = token_data.get('access_token')
            if not access_token:
                raise ValueError('No access token in response')

            return access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub token exchange failed: {str(e)}")
            raise ValueError(f"Failed to exchange code for token: {str(e)}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {str(e)}")
            raise ValueError(f"Token exchange error: {str(e)}")

    def get_user_info(self, access_token: str) -> Dict[str, str]:
        """
        Verify token and extract essential user information.

        Args:
            access_token: The access token from GitHub OAuth

        Returns:
            Dictionary with essential user info:
            {
                'oauth_id': Unique GitHub user ID,
                'email': Email address,
                'name': Full name,
                'picture': Profile picture URL,
                'username': GitHub username
            }
        """
        user_info = self.verify_token(access_token)

        return {
            'oauth_id': str(user_info['id']),
            'email': user_info['email'],
            'name': user_info.get('name', ''),
            'picture': user_info.get('avatar_url', ''),
            'username': user_info.get('login', ''),
            'bio': user_info.get('bio', ''),
            'location': user_info.get('location', ''),
            'company': user_info.get('company', ''),
        }
