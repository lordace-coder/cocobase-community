# GitHub Login Integration Guide

## How It Works

The GitHub login flow supports **two methods**:

### Method 1: Authorization Code Flow (Recommended - More Secure)
1. **Client**: User clicks "Login with GitHub"
2. **Client**: Redirect user to GitHub OAuth page
3. **GitHub**: User authorizes your app
4. **GitHub**: Redirects back to your app with an authorization `code`
5. **Client**: Send the `code` to your Cocobase backend
6. **Cocobase**: Exchanges `code` for `access_token` using `client_secret` (server-side - secure!)
7. **Cocobase**: Verifies token, gets user info from GitHub
8. **Cocobase**: Creates/logs in user and returns JWT token

### Method 2: Access Token Flow (Client-Side)
1. **Client**: User clicks "Login with GitHub"
2. **Client**: Opens GitHub OAuth popup/redirect
3. **GitHub**: User authorizes and returns `access_token` directly to client
4. **Client**: Send `access_token` to Cocobase backend
5. **Cocobase**: Verifies token with GitHub API
6. **Cocobase**: Gets user info from GitHub
7. **Cocobase**: Creates/logs in user and returns JWT token

---

## Setup Requirements

### 1. Create GitHub OAuth App
1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in details:
   - **Application name**: Your App Name
   - **Homepage URL**: `http://localhost:3000` (or your domain)
   - **Authorization callback URL**: `http://localhost:3000/auth/github/callback` (or your callback URL)
4. Save and copy:
   - **Client ID** (public - can be used in client code)
   - **Client Secret** (private - only needed for code exchange)

### 2. Configure in Cocobase
1. Go to your Cocobase project settings
2. Navigate to Integrations
3. Enable "GitHub Sign-In" integration
4. Add configuration:
   - `GITHUB_CLIENT_ID`: Your GitHub Client ID
   - `GITHUB_CLIENT_SECRET`: Your GitHub Client Secret (optional if using access_token flow)

---

## Implementation Examples

### Method 1: Code Exchange (Recommended)

**Step 1: Redirect to GitHub**
```javascript
// When user clicks "Login with GitHub"
const GITHUB_CLIENT_ID = 'your_github_client_id';
const REDIRECT_URI = 'http://localhost:3000/auth/github/callback';
const SCOPE = 'read:user user:email'; // Permissions needed

const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&scope=${SCOPE}`;

// Redirect user to GitHub
window.location.href = githubAuthUrl;
```

**Step 2: Handle Callback (After GitHub redirects back)**
```javascript
// On your callback page (e.g., /auth/github/callback)
// GitHub redirects to: http://localhost:3000/auth/github/callback?code=abc123

// Extract code from URL
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');

if (code) {
  // Send code to Cocobase
  const response = await fetch('https://api.cocobase.buzz/auth-collections/github-verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-cocobase-project-api-key'
    },
    body: JSON.stringify({
      code: code,
      redirect_uri: 'http://localhost:3000/auth/github/callback'
    })
  });

  const data = await response.json();

  if (response.ok) {
    // Success! User is logged in
    const { access_token, user } = data;

    // Save JWT token (for future API calls)
    localStorage.setItem('auth_token', access_token);

    // Redirect to dashboard or home
    window.location.href = '/dashboard';
  } else {
    // Handle error
    console.error('Login failed:', data.detail);
  }
}
```

---

### Method 2: Popup Flow (Client-Side Token)

```javascript
// Login with GitHub using popup
async function loginWithGitHub() {
  const GITHUB_CLIENT_ID = 'your_github_client_id';
  const REDIRECT_URI = 'http://localhost:3000/auth/github/popup';
  const SCOPE = 'read:user user:email';

  const authUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&scope=${SCOPE}`;

  // Open popup
  const popup = window.open(
    authUrl,
    'GitHub Login',
    'width=600,height=700'
  );

  // Listen for message from popup
  window.addEventListener('message', async (event) => {
    // Verify origin for security
    if (event.origin !== window.location.origin) return;

    if (event.data.type === 'github-auth') {
      const { code, error } = event.data;

      if (error) {
        console.error('GitHub auth error:', error);
        return;
      }

      if (code) {
        // Close popup
        popup.close();

        // Send code to Cocobase
        const response = await fetch('https://api.cocobase.buzz/auth-collections/github-verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'your-cocobase-project-api-key'
          },
          body: JSON.stringify({
            code: code,
            redirect_uri: REDIRECT_URI
          })
        });

        const data = await response.json();

        if (response.ok) {
          const { access_token, user } = data;
          localStorage.setItem('auth_token', access_token);
          console.log('Logged in as:', user.email);
          window.location.href = '/dashboard';
        } else {
          console.error('Login failed:', data.detail);
        }
      }
    }
  });
}
```

**Popup callback page** (`/auth/github/popup`):
```html
<!DOCTYPE html>
<html>
<head>
  <title>GitHub Auth</title>
</head>
<body>
  <p>Processing login...</p>
  <script>
    // Extract code from URL
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');

    // Send to parent window
    if (window.opener) {
      window.opener.postMessage({
        type: 'github-auth',
        code: code,
        error: error
      }, window.location.origin);
    }
  </script>
</body>
</html>
```

---

## Mobile App Implementation

### React Native / Expo

For mobile apps, use a library like `expo-auth-session` or `react-native-app-auth` to handle OAuth flow:

**Step 1: Install dependencies**
```bash
# For Expo
npx expo install expo-auth-session expo-crypto

# For React Native
npm install react-native-app-auth
```

**Step 2: Configure redirect URI**
```javascript
// In your GitHub OAuth App settings, add:
// myapp://auth/github (for custom scheme)
// or use expo scheme: exp://localhost:19000 (for Expo Go)
```

**Step 3: Implement login (Expo example)**
```javascript
import * as AuthSession from 'expo-auth-session';
import * as Crypto from 'expo-crypto';

const GITHUB_CLIENT_ID = 'your_github_client_id';
const COCOBASE_API_KEY = 'your_cocobase_api_key';

// Define redirect URI for mobile
const redirectUri = AuthSession.makeRedirectUri({
  scheme: 'myapp', // Your custom URL scheme
  path: 'auth/github'
});

async function loginWithGitHub() {
  try {
    // Step 1: Start OAuth flow
    const authUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=read:user user:email`;

    // Open GitHub auth in browser
    const result = await AuthSession.startAsync({
      authUrl: authUrl,
      returnUrl: redirectUri
    });

    if (result.type === 'success') {
      const code = result.params.code;

      // Step 2: Send code to Cocobase
      const response = await fetch('https://api.cocobase.buzz/auth-collections/github-verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': COCOBASE_API_KEY
        },
        body: JSON.stringify({
          code: code,
          redirect_uri: redirectUri,
          platform: 'mobile'
        })
      });

      const data = await response.json();

      if (response.ok) {
        const { access_token, user } = data;

        // Save token securely
        await SecureStore.setItemAsync('auth_token', access_token);

        console.log('Logged in:', user.email);
        return { success: true, user };
      } else {
        throw new Error(data.detail || 'Login failed');
      }
    } else {
      throw new Error('Auth cancelled or failed');
    }
  } catch (error) {
    console.error('GitHub login error:', error);
    return { success: false, error: error.message };
  }
}
```

**Step 4: Configure app.json (Expo)**
```json
{
  "expo": {
    "scheme": "myapp",
    "ios": {
      "bundleIdentifier": "com.yourcompany.yourapp"
    },
    "android": {
      "package": "com.yourcompany.yourapp"
    }
  }
}
```

### Flutter

**Step 1: Add dependencies to pubspec.yaml**
```yaml
dependencies:
  flutter_web_auth: ^0.5.0
  http: ^1.1.0
```

**Step 2: Implement login**
```dart
import 'package:flutter_web_auth/flutter_web_auth.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

const GITHUB_CLIENT_ID = 'your_github_client_id';
const COCOBASE_API_KEY = 'your_cocobase_api_key';
const CALLBACK_URL = 'myapp://auth/github';

Future<Map<String, dynamic>> loginWithGitHub() async {
  try {
    // Step 1: Start OAuth flow
    final authUrl = 'https://github.com/login/oauth/authorize?'
        'client_id=$GITHUB_CLIENT_ID&'
        'redirect_uri=${Uri.encodeComponent(CALLBACK_URL)}&'
        'scope=read:user user:email';

    // Open GitHub auth
    final result = await FlutterWebAuth.authenticate(
      url: authUrl,
      callbackUrlScheme: 'myapp',
    );

    // Extract code from callback URL
    final code = Uri.parse(result).queryParameters['code'];

    if (code == null) {
      throw Exception('No code received');
    }

    // Step 2: Send code to Cocobase
    final response = await http.post(
      Uri.parse('https://api.cocobase.buzz/auth-collections/github-verify'),
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': COCOBASE_API_KEY,
      },
      body: jsonEncode({
        'code': code,
        'redirect_uri': CALLBACK_URL,
        'platform': 'mobile',
      }),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      final accessToken = data['access_token'];
      final user = data['user'];

      // Save token securely (use flutter_secure_storage)
      print('Logged in: ${user['email']}');

      return {'success': true, 'user': user, 'token': accessToken};
    } else {
      throw Exception(data['detail'] ?? 'Login failed');
    }
  } catch (e) {
    print('GitHub login error: $e');
    return {'success': false, 'error': e.toString()};
  }
}
```

**Step 3: Configure AndroidManifest.xml**
```xml
<activity android:name="com.linusu.flutter_web_auth.CallbackActivity">
  <intent-filter android:label="flutter_web_auth">
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="myapp" />
  </intent-filter>
</activity>
```

**Step 4: Configure Info.plist (iOS)**
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>myapp</string>
    </array>
  </dict>
</array>
```

---

## Fetch Template

```javascript
// Complete fetch template for GitHub login
async function loginWithGitHubCode(code, redirectUri) {
  try {
    const response = await fetch('https://api.cocobase.buzz/auth-collections/github-verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'YOUR_COCOBASE_PROJECT_API_KEY' // Replace with your project API key
      },
      body: JSON.stringify({
        code: code,                    // Authorization code from GitHub
        redirect_uri: redirectUri,     // Must match the one used in OAuth flow
        platform: 'web'                // Optional: 'web' or 'mobile'
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    // Success!
    return {
      success: true,
      access_token: data.access_token,  // JWT token for your app
      user: data.user                    // User object with profile data
    };

  } catch (error) {
    console.error('GitHub login error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Usage:
const result = await loginWithGitHubCode('abc123code', 'http://localhost:3000/callback');
if (result.success) {
  localStorage.setItem('auth_token', result.access_token);
  console.log('User:', result.user);
}
```

---

## Response Format

**Success Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "data": {
      "name": "John Doe",
      "picture": "https://avatars.githubusercontent.com/u/123456",
      "username": "johndoe",
      "bio": "Software Developer",
      "location": "San Francisco, CA",
      "company": "Acme Inc"
    },
    "oauth_provider": "github",
    "oauth_id": "123456",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Error Response:**
```json
{
  "detail": "GitHub Sign-In integration is not enabled for this project"
}
```

---

## Configuration Options

### Request Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | Conditional* | Authorization code from GitHub OAuth callback |
| `access_token` | string | Conditional* | GitHub access token (if already obtained client-side) |
| `redirect_uri` | string | Required with `code` | Must match the redirect URI used in OAuth flow |
| `platform` | string | Optional | Platform identifier ('web', 'mobile') for analytics |

*Either `code` or `access_token` must be provided, but not both.

### Integration Settings

Configure these in your Cocobase project's GitHub integration:

| Setting | Required | Description |
|---------|----------|-------------|
| `GITHUB_CLIENT_ID` | Yes | Your GitHub OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | Conditional | Required only if using code exchange flow |

---

## Security Notes

1. **Client Secret**: Only needed for code exchange (Method 1). The secret stays on the server and is never exposed to clients.

2. **Redirect URI**: Must match exactly between:
   - The URI registered in your GitHub OAuth App
   - The URI used when redirecting to GitHub
   - The URI sent to Cocobase endpoint

3. **API Key**: Your Cocobase project API key should be kept secure. For web apps, it's okay to include it in client code since it's project-specific, not user-specific.

4. **JWT Token**: The `access_token` returned by Cocobase is a JWT token for your app. Store it securely and include it in future API requests.

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Either 'access_token' or 'code' must be provided" | Missing both parameters | Provide either `code` or `access_token` |
| "redirect_uri is required when using code" | Missing redirect_uri with code | Include the redirect_uri parameter |
| "GitHub Sign-In integration is not enabled" | Integration not configured | Enable and configure GitHub integration in project settings |
| "GITHUB_CLIENT_ID is not configured" | Missing Client ID | Add GITHUB_CLIENT_ID to integration settings |
| "Failed to fetch user info: 401" | Invalid token/code | Check that token/code is valid and not expired |
| "Unable to retrieve verified email from GitHub" | User's email is private | Ask user to make email public or verify it on GitHub |

---

## Testing Locally

1. **Set callback URL** in GitHub OAuth App to: `http://localhost:3000/auth/github/callback`
2. **Use localhost** in your redirect_uri parameter
3. **GitHub allows localhost** without HTTPS for development

---

## Next Steps

1. Copy your GitHub Client ID and Client Secret
2. Configure the GitHub integration in your Cocobase project
3. Implement the login flow using one of the examples above
4. Test the login flow
5. Store the JWT token and use it for authenticated API requests

**Pro Tip**: Use the code exchange flow (Method 1) for production apps as it's more secure!
