from urllib.parse import urlencode
from dotenv import load_dotenv
import os

load_dotenv()


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

SCOPES = ["openid", "email", "profile"]
params = {
    "client_id": GOOGLE_CLIENT_ID,
    "response_type": "code",
    "redirect_uri": "https://futurebase.vercel.app/auth/auth-google",
    "scope": " ".join(SCOPES),
    "access_type": "offline",
    "prompt": "consent",
}

oauth_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
