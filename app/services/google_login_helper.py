from urllib.parse import urlencode



def generate_oauth_url(GOOGLE_CLIENT_ID: str, redirect_url):
    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

    SCOPES = ["openid", "email", "profile"]
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_url,
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }

    oauth_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    return oauth_url
