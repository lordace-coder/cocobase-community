# GitHub Code Exchange Endpoint

Add this endpoint to `/home/patrick/Documents/COCOBASE/cocobase/app/api/auth_collection.py` after line 1080:

```python
# *GITHUB SIGN-IN (Code Exchange - Server-Side)
class GitHubCodeRequest(BaseModel):
    code: str
    redirect_uri: str
    platform: Optional[str] = None


@router.post("/github-code")
def exchange_github_code(
    payload: GitHubCodeRequest,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict:
    """
    Exchange GitHub authorization code for JWT token (server-side).

    This endpoint exchanges the code for an access_token using the
    client secret (which stays secure on the server).
    """
    project = proj[0]

    # Get integration settings
    integration = IntegrationService(db)
    GITHUB_INTEGRATION_ID = "github-oauth-integration-id"  # Replace with actual UUID

    project_integration: ProjectIntegration = integration.get_project_integration(
        project.id,
        GITHUB_INTEGRATION_ID,
    )

    if not project_integration or not project_integration.is_enabled:
        raise HTTPException(
            status_code=400,
            detail="GitHub Sign-In integration is not enabled for this project",
        )

    config = dict(project_integration.config)

    # Get required settings
    GITHUB_CLIENT_ID = config.get("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = config.get("GITHUB_CLIENT_SECRET")

    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="GitHub OAuth credentials are not configured",
        )

    try:
        # Exchange code for access token
        verifier = GitHubTokenVerifier(GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET)
        access_token = verifier.exchange_code_for_token(payload.code, payload.redirect_uri)

        # Get user info
        user_info = verifier.get_user_info(access_token)

        # Create/login user
        oauth_service = OAuthService(db, project.id)
        result = oauth_service.find_or_create_user(
            email=user_info["email"],
            oauth_id=user_info["oauth_id"],
            provider="github",
            name=user_info.get("name", ""),
            picture=user_info.get("picture", ""),
            additional_data={
                "username": user_info.get("username", ""),
                "bio": user_info.get("bio", ""),
                "location": user_info.get("location", ""),
                "company": user_info.get("company", ""),
            },
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred during authentication: {str(e)}"
        )
```

## Client-Side Usage

```javascript
const code = "c9a99c1b31664bc86504";

const response = await fetch('https://api.cocobase.buzz/auth-collections/github-code', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-project-api-key'
  },
  body: JSON.stringify({
    code: code,
    redirect_uri: 'http://localhost:3000'
  })
});

const { access_token, user } = await response.json();
// Done! User is logged in
```

**Configuration Required:**
- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`

Both secrets stay on server! ✅
