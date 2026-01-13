# How Developers Integrate "Sign in with CocoBase"

## Step 1: Register Your Application

First, the developer needs to register their app with CocoBase to get credentials.

### Via API:

```bash
curl -X POST https://cocobase.com/oauth/clients \
  -H "Authorization: Bearer YOUR_COCOBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Awesome App",
    "description": "A cool todo app",
    "redirect_uris": ["https://myapp.com/auth/callback"],
    "scopes": ["openid", "email", "profile"]
  }'
```

### Response:

```json
{
  "client_id": "coco_abc123xyz",
  "client_secret": "secret_very_secret_string_save_this",
  "name": "My Awesome App",
  ...
}
```

**IMPORTANT:** Save the `client_secret` - it's only shown once!

---

## Step 2: Add "Sign in with CocoBase" Button

The developer adds a button to their login page:

### HTML:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>My App - Login</title>
    <style>
      .cocobase-btn {
        background: #667eea;
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .cocobase-btn:hover {
        background: #5568d3;
      }
    </style>
  </head>
  <body>
    <h1>Welcome to My App</h1>

    <!-- Traditional login form -->
    <form action="/login" method="POST">
      <input type="email" name="email" placeholder="Email" />
      <input type="password" name="password" placeholder="Password" />
      <button type="submit">Login</button>
    </form>

    <p>OR</p>

    <!-- Sign in with CocoBase button -->
    <button class="cocobase-btn" onclick="signInWithCocoBase()">
      🥥 Sign in with CocoBase
    </button>

    <script>
      function signInWithCocoBase() {
        // Generate random state for CSRF protection
        const state = generateRandomString(32);
        sessionStorage.setItem("oauth_state", state);

        // Build authorization URL
        const params = new URLSearchParams({
          response_type: "code",
          client_id: "coco_abc123xyz", // From Step 1
          redirect_uri: "https://myapp.com/auth/callback",
          scope: "openid email profile",
          state: state,
        });

        // Redirect to CocoBase
        window.location.href = `https://cocobase.com/oauth/authorize?${params}`;
      }

      function generateRandomString(length) {
        const chars =
          "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        let result = "";
        for (let i = 0; i < length; i++) {
          result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
      }
    </script>
  </body>
</html>
```

---

## Step 3: Handle the Callback

When user approves, CocoBase redirects back to `https://myapp.com/auth/callback?code=xxx&state=yyy`

The developer needs to handle this callback:

### Backend Examples:

#### Option A: Node.js/Express

```javascript
// server.js
const express = require("express");
const axios = require("axios");
const session = require("express-session");

const app = express();
app.use(
  session({ secret: "your-secret", resave: false, saveUninitialized: true })
);

const CLIENT_ID = "coco_abc123xyz";
const CLIENT_SECRET = "secret_very_secret_string_save_this";
const REDIRECT_URI = "https://myapp.com/auth/callback";

// Callback endpoint
app.get("/auth/callback", async (req, res) => {
  const { code, state } = req.query;

  // Verify state (CSRF protection)
  const savedState = req.session.oauth_state;
  if (state !== savedState) {
    return res.status(400).send("Invalid state");
  }

  try {
    // Exchange code for tokens
    const tokenResponse = await axios.post(
      "https://cocobase.com/oauth/token",
      new URLSearchParams({
        grant_type: "authorization_code",
        code: code,
        redirect_uri: REDIRECT_URI,
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
      }),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );

    const { access_token, id_token, refresh_token } = tokenResponse.data;

    // Get user info
    const userResponse = await axios.get(
      "https://cocobase.com/oauth/userinfo",
      {
        headers: { Authorization: `Bearer ${access_token}` },
      }
    );

    const user = userResponse.data;
    // user = { sub: '123', email: 'user@example.com', name: 'John Doe' }

    // Create or update user in your database
    const localUser = await findOrCreateUser({
      cocobase_id: user.sub,
      email: user.email,
      name: user.name,
      email_verified: user.email_verified,
    });

    // Log the user in
    req.session.user_id = localUser.id;

    // Redirect to app
    res.redirect("/dashboard");
  } catch (error) {
    console.error("OAuth error:", error);
    res.redirect("/login?error=oauth_failed");
  }
});

async function findOrCreateUser(userData) {
  // Check if user exists
  let user = await db.users.findOne({ cocobase_id: userData.cocobase_id });

  if (!user) {
    // Create new user
    user = await db.users.create({
      cocobase_id: userData.cocobase_id,
      email: userData.email,
      name: userData.name,
      email_verified: userData.email_verified,
      created_at: new Date(),
    });
  } else {
    // Update existing user
    await db.users.update(user.id, {
      email: userData.email,
      name: userData.name,
      email_verified: userData.email_verified,
    });
  }

  return user;
}

app.listen(3000);
```

#### Option B: Python/Flask

```python
# app.py
from flask import Flask, redirect, request, session, url_for
import requests
import secrets

app = Flask(__name__)
app.secret_key = 'your-secret-key'

CLIENT_ID = 'coco_abc123xyz'
CLIENT_SECRET = 'secret_very_secret_string_save_this'
REDIRECT_URI = 'https://myapp.com/auth/callback'

@app.route('/auth/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')

    # Verify state
    if state != session.get('oauth_state'):
        return 'Invalid state', 400

    # Exchange code for tokens
    token_response = requests.post('https://cocobase.com/oauth/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })

    if token_response.status_code != 200:
        return redirect('/login?error=oauth_failed')

    tokens = token_response.json()
    access_token = tokens['access_token']

    # Get user info
    user_response = requests.get('https://cocobase.com/oauth/userinfo',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    user = user_response.json()
    # user = {'sub': '123', 'email': 'user@example.com', 'name': 'John Doe'}

    # Create or update user in database
    local_user = find_or_create_user(
        cocobase_id=user['sub'],
        email=user['email'],
        name=user['name'],
        email_verified=user.get('email_verified', False)
    )

    # Log user in
    session['user_id'] = local_user.id

    return redirect('/dashboard')

def find_or_create_user(cocobase_id, email, name, email_verified):
    # Your database logic here
    user = db.query(User).filter_by(cocobase_id=cocobase_id).first()

    if not user:
        user = User(
            cocobase_id=cocobase_id,
            email=email,
            name=name,
            email_verified=email_verified
        )
        db.add(user)
        db.commit()

    return user
```

#### Option C: PHP

```php
<?php
// callback.php

session_start();

$client_id = 'coco_abc123xyz';
$client_secret = 'secret_very_secret_string_save_this';
$redirect_uri = 'https://myapp.com/auth/callback.php';

// Get authorization code
$code = $_GET['code'] ?? null;
$state = $_GET['state'] ?? null;

// Verify state
if ($state !== $_SESSION['oauth_state']) {
    die('Invalid state');
}

if (!$code) {
    header('Location: /login.php?error=no_code');
    exit;
}

// Exchange code for tokens
$ch = curl_init('https://cocobase.com/oauth/token');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
    'grant_type' => 'authorization_code',
    'code' => $code,
    'redirect_uri' => $redirect_uri,
    'client_id' => $client_id,
    'client_secret' => $client_secret
]));

$response = curl_exec($ch);
curl_close($ch);

$tokens = json_decode($response, true);
$access_token = $tokens['access_token'];

// Get user info
$ch = curl_init('https://cocobase.com/oauth/userinfo');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Authorization: Bearer ' . $access_token
]);

$response = curl_exec($ch);
curl_close($ch);

$user = json_decode($response, true);

// Create or update user in database
$stmt = $pdo->prepare("SELECT * FROM users WHERE cocobase_id = ?");
$stmt->execute([$user['sub']]);
$existingUser = $stmt->fetch();

if (!$existingUser) {
    // Create new user
    $stmt = $pdo->prepare("
        INSERT INTO users (cocobase_id, email, name, email_verified, created_at)
        VALUES (?, ?, ?, ?, NOW())
    ");
    $stmt->execute([
        $user['sub'],
        $user['email'],
        $user['name'],
        $user['email_verified'] ? 1 : 0
    ]);
    $userId = $pdo->lastInsertId();
} else {
    $userId = $existingUser['id'];
}

// Log user in
$_SESSION['user_id'] = $userId;

// Redirect to app
header('Location: /dashboard.php');
?>
```

---

## Step 4: Database Schema

The developer needs to store CocoBase user info:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    cocobase_id VARCHAR(255) UNIQUE NOT NULL,  -- The 'sub' from CocoBase
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    profile_picture VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cocobase_id ON users(cocobase_id);
```

---

## Complete Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  1. User visits myapp.com                                   │
│     Clicks "Sign in with CocoBase" button                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Redirect to CocoBase                                    │
│     https://cocobase.com/oauth/authorize?                   │
│       client_id=coco_abc123xyz&                             │
│       redirect_uri=https://myapp.com/auth/callback&         │
│       scope=openid email profile&                           │
│       state=random123                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  3. User logs into CocoBase (if not already logged in)      │
│     Sees consent screen: "My Awesome App wants to..."       │
│     Clicks "Allow Access"                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  4. CocoBase redirects back to app                          │
│     https://myapp.com/auth/callback?                        │
│       code=auth_code_here&                                  │
│       state=random123                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  5. App backend exchanges code for tokens                   │
│     POST https://cocobase.com/oauth/token                   │
│     Returns: access_token, id_token, refresh_token          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  6. App gets user info                                      │
│     GET https://cocobase.com/oauth/userinfo                 │
│     Authorization: Bearer {access_token}                    │
│     Returns: { sub, email, name, ... }                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  7. App creates/updates user in local database              │
│     Creates session for user                                │
│     Redirects to /dashboard                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Using OAuth Libraries (Easier Way)

Instead of handling everything manually, developers can use libraries:

### Node.js - Passport.js

```javascript
const passport = require("passport");
const OAuth2Strategy = require("passport-oauth2");

passport.use(
  "cocobase",
  new OAuth2Strategy(
    {
      authorizationURL: "https://cocobase.com/oauth/authorize",
      tokenURL: "https://cocobase.com/oauth/token",
      clientID: "coco_abc123xyz",
      clientSecret: "secret_very_secret_string_save_this",
      callbackURL: "https://myapp.com/auth/callback",
    },
    async function (accessToken, refreshToken, profile, cb) {
      // Get user info
      const user = await getUserInfo(accessToken);
      const localUser = await findOrCreateUser(user);
      return cb(null, localUser);
    }
  )
);

app.get("/auth/cocobase", passport.authenticate("cocobase"));
app.get(
  "/auth/callback",
  passport.authenticate("cocobase", { failureRedirect: "/login" }),
  (req, res) => res.redirect("/dashboard")
);
```

### Python - Authlib

```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)
oauth.register(
    name='cocobase',
    client_id='coco_abc123xyz',
    client_secret='secret_very_secret_string_save_this',
    server_metadata_url='https://cocobase.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return oauth.cocobase.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def callback():
    token = oauth.cocobase.authorize_access_token()
    user = oauth.cocobase.parse_id_token(token)
    # Create user in database
    return redirect('/dashboard')
```

---

## Security Best Practices for Developers

1. **Always use HTTPS** - Never use OAuth over HTTP
2. **Verify state parameter** - Prevents CSRF attacks
3. **Store client_secret securely** - Use environment variables, never commit to git
4. **Use PKCE for mobile/SPA** - Extra security for public clients
5. **Validate redirect_uri** - Make sure it matches what's registered
6. **Handle token expiration** - Implement token refresh logic
7. **Store tokens securely** - Use httpOnly cookies or secure session storage

---

## Testing

Developers can test with:

```bash
# Get authorization code
open "https://cocobase.com/oauth/authorize?response_type=code&client_id=coco_abc123xyz&redirect_uri=http://localhost:3000/callback&scope=openid%20email%20profile&state=test123"

# Exchange code for token (from callback)
curl -X POST https://cocobase.com/oauth/token \
  -d "grant_type=authorization_code" \
  -d "code=AUTHORIZATION_CODE_HERE" \
  -d "redirect_uri=http://localhost:3000/callback" \
  -d "client_id=coco_abc123xyz" \
  -d "client_secret=secret_very_secret_string_save_this"

# Get user info
curl -H "Authorization: Bearer ACCESS_TOKEN_HERE" \
  https://cocobase.com/oauth/userinfo
```
