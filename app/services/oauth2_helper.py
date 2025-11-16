"""
OAuth2 helper for CocoBase platform user authentication.

This module is for platform users (developers who create projects),
NOT for app client users (end users of the BaaS).

For app client OAuth, see:
- app/services/google_token_verifier.py
- app/services/apple_token_verifier.py
- app/api/auth_collection.py
"""

import os
from urllib.parse import urlencode

# Google OAuth credentials for platform users
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# OAuth endpoints
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

# Redirect URI for platform users
REDIRECT_URI = "https://api.cocobase.buzz/auth/auth-google"

# Generate OAuth URL for platform users
params = {
    "client_id": GOOGLE_CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "openid email profile",
    "access_type": "offline",
    "prompt": "consent",
}

oauth_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
