# Google Sign-In Authentication

This feature allows your application users to sign in using their Google accounts through ID token verification. This modern approach works seamlessly for both web and mobile applications.

## How It Works

Unlike traditional OAuth redirect flows, this implementation uses **ID token verification**:

1. Your client (web/mobile app) uses Google Sign-In SDK to authenticate the user
2. Google returns an ID token to your client
3. Your client sends the ID token to CocoBase
4. CocoBase verifies the token with Google's public keys
5. CocoBase creates/logs in the user and returns your app's JWT token

**Benefits:**
- ✅ Works natively on mobile (no browser redirects)
- ✅ Better UX (Google One-Tap on web, native Sign-In on mobile)
- ✅ Simpler implementation (single API call)
- ✅ More secure (token verification server-side)
- ✅ No deep linking or custom URL schemes needed

## Prerequisites

Before implementing Google Sign-In, you need to:

1. **Set up Google OAuth credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Create credentials for each platform:
     - **Web**: Application type = "Web application"
     - **iOS**: Application type = "iOS"
     - **Android**: Application type = "Android"

2. **Enable Google Sign-In integration** in your CocoBase project settings

3. **Configure your project** with the Google Client ID

## Configuration

Add the following configuration to your CocoBase project integration settings:

```json
{
  "GOOGLE_CLIENT_ID": "your-google-client-id.apps.googleusercontent.com"
}
```

### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `GOOGLE_CLIENT_ID` | string | Yes | OAuth 2.0 Client ID from Google Cloud Console (Web client ID recommended) |
| `GOOGLE_WEB_CLIENT_ID` | string | No | Optional separate client ID for web (if different from mobile) |

**Note:** Use your **Web Client ID** as it works for both web and mobile token verification.

## API Endpoint

### Verify Google ID Token

**Endpoint:** `POST /auth-collections/google-verify`

**Headers:**
```
x-api-key: your-project-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjZmODkw...",
  "platform": "web"  // optional: "web", "mobile", "ios", "android"
}
```

**Success Response (200):**
```json
{
  "access_token": "your_jwt_token_for_subsequent_api_calls",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "data": {
      "username": "johndoe",
      "name": "John Doe",
      "picture": "https://lh3.googleusercontent.com/...",
      "given_name": "John",
      "family_name": "Doe"
    },
    "oauth_provider": "google",
    "created_at": "2025-11-16T10:30:00Z"
  }
}
```

**Error Responses:**

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Google Sign-In integration is not enabled | Integration not activated in project settings |
| 400 | GOOGLE_CLIENT_ID is not configured | Client ID missing from project config |
| 400 | Invalid Google ID token | Token verification failed or token expired |
| 400 | This email is already registered with password authentication | User must use email/password login |
| 400 | This email is already registered with Apple Sign-In | User must use Apple to login |
| 500 | An error occurred during authentication | Server error |

## Implementation Examples

### Web (React with Google One-Tap)

```bash
npm install @react-oauth/google
```

```jsx
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';

function App() {
  return (
    <GoogleOAuthProvider clientId="YOUR_GOOGLE_CLIENT_ID">
      <LoginComponent />
    </GoogleOAuthProvider>
  );
}

function LoginComponent() {
  const handleGoogleSignIn = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      // Send ID token to CocoBase
      const response = await fetch('https://api.cocobase.buzz/auth-collections/google-verify', {
        method: 'POST',
        headers: {
          'x-api-key': 'YOUR_PROJECT_API_KEY',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_token: tokenResponse.credential,
          platform: 'web'
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Store the access token
        localStorage.setItem('auth_token', data.access_token);
        // Redirect to dashboard
        window.location.href = '/dashboard';
      } else {
        console.error('Authentication failed:', data.detail);
      }
    },
    onError: () => console.error('Google Sign-In failed'),
  });

  return <button onClick={handleGoogleSignIn}>Sign in with Google</button>;
}
```

### Web (Vanilla JavaScript with Google One-Tap)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Google Sign-In</title>
    <script src="https://accounts.google.com/gsi/client" async></script>
</head>
<body>
    <!-- Google One-Tap Sign-In -->
    <div id="g_id_onload"
         data-client_id="YOUR_GOOGLE_CLIENT_ID"
         data-callback="handleCredentialResponse">
    </div>

    <!-- Google Sign-In Button -->
    <div class="g_id_signin" data-type="standard"></div>

    <script>
        async function handleCredentialResponse(response) {
            // response.credential is the ID token
            try {
                const result = await fetch('https://api.cocobase.buzz/auth-collections/google-verify', {
                    method: 'POST',
                    headers: {
                        'x-api-key': 'YOUR_PROJECT_API_KEY',
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        id_token: response.credential,
                        platform: 'web'
                    })
                });

                const data = await result.json();

                if (result.ok) {
                    // Store token and redirect
                    localStorage.setItem('auth_token', data.access_token);
                    window.location.href = '/dashboard';
                } else {
                    alert('Authentication failed: ' + data.detail);
                }
            } catch (error) {
                console.error('Error:', error);
            }
        }
    </script>
</body>
</html>
```

### Mobile (React Native)

```bash
npm install @react-native-google-signin/google-signin
```

```jsx
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import { useEffect } from 'react';

function App() {
  useEffect(() => {
    // Configure Google Sign-In
    GoogleSignin.configure({
      webClientId: 'YOUR_GOOGLE_WEB_CLIENT_ID', // From Google Cloud Console
      iosClientId: 'YOUR_IOS_CLIENT_ID', // Optional, auto-detected
      offlineAccess: false,
    });
  }, []);

  const signInWithGoogle = async () => {
    try {
      await GoogleSignin.hasPlayServices();
      const userInfo = await GoogleSignin.signIn();

      // Send ID token to CocoBase
      const response = await fetch('https://api.cocobase.buzz/auth-collections/google-verify', {
        method: 'POST',
        headers: {
          'x-api-key': 'YOUR_PROJECT_API_KEY',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_token: userInfo.idToken,
          platform: 'mobile'
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Store token (use secure storage in production)
        await AsyncStorage.setItem('auth_token', data.access_token);
        // Navigate to main screen
        navigation.navigate('Home');
      } else {
        Alert.alert('Authentication Failed', data.detail);
      }
    } catch (error) {
      console.error('Google Sign-In error:', error);
    }
  };

  return (
    <Button title="Sign in with Google" onPress={signInWithGoogle} />
  );
}
```

### Mobile (Flutter)

```yaml
# pubspec.yaml
dependencies:
  google_sign_in: ^6.1.0
```

```dart
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AuthService {
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'profile'],
    clientId: 'YOUR_WEB_CLIENT_ID', // Web client ID
  );

  Future<void> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn();

      if (account == null) return; // User canceled

      final GoogleSignInAuthentication auth = await account.authentication;

      // Send ID token to CocoBase
      final response = await http.post(
        Uri.parse('https://api.cocobase.buzz/auth-collections/google-verify'),
        headers: {
          'x-api-key': 'YOUR_PROJECT_API_KEY',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'id_token': auth.idToken,
          'platform': 'mobile',
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        // Store token securely
        await storage.write(key: 'auth_token', value: data['access_token']);
        // Navigate to home
      } else {
        final error = jsonDecode(response.body);
        print('Authentication failed: ${error['detail']}');
      }
    } catch (error) {
      print('Google Sign-In error: $error');
    }
  }
}
```

### iOS (Swift)

```swift
import GoogleSignIn

func signInWithGoogle() {
    guard let clientID = "YOUR_IOS_CLIENT_ID" else { return }
    let config = GIDConfiguration(clientID: clientID)
    GIDSignIn.sharedInstance.configuration = config

    GIDSignIn.sharedInstance.signIn(withPresenting: self) { result, error in
        guard error == nil else { return }
        guard let user = result?.user, let idToken = user.idToken?.tokenString else { return }

        // Send ID token to CocoBase
        let url = URL(string: "https://api.cocobase.buzz/auth-collections/google-verify")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("YOUR_PROJECT_API_KEY", forHTTPHeaderField: "x-api-key")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "id_token": idToken,
            "platform": "ios"
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data else { return }
            if let json = try? JSONDecoder().decode(AuthResponse.self, from: data) {
                // Store token and navigate
                UserDefaults.standard.set(json.access_token, forKey: "auth_token")
            }
        }.resume()
    }
}
```

## User Management

### New Users
When a user signs in with Google for the first time:
- A new `AppUser` record is created
- `oauth_id` is set to Google's unique user ID (`sub` field)
- `oauth_provider` is set to `"google"`
- `email` is set from Google profile
- `data` includes username, name, picture, given_name, and family_name

### Existing Users
For users who already exist in the system:
- **Google OAuth users**: Successfully logged in with new token
- **Password users**: Error returned - must use password login
- **Other OAuth users (e.g., Apple)**: Error returned - must use original provider

## Security Features

- ✅ **Token Verification**: ID tokens verified using Google's public certificates
- ✅ **Email Verification**: Only Google-verified emails accepted
- ✅ **Provider Isolation**: Users can't mix authentication providers
- ✅ **Secure Token Generation**: Your app's JWT tokens generated server-side
- ✅ **No Client Secrets**: Client-side apps never handle sensitive secrets

## Troubleshooting

### Common Issues

1. **"GOOGLE_CLIENT_ID is not configured"**
   - Ensure you've added the client ID to your CocoBase project integration settings
   - Verify the integration is enabled

2. **"Invalid Google ID token"**
   - Token may have expired (tokens expire after 1 hour)
   - Ensure you're using the Web Client ID for token verification
   - Check that the client ID in your app matches the one in CocoBase settings

3. **"This email is already registered with password authentication"**
   - User must use email/password login instead
   - Consider adding account linking feature in your app

4. **Token verification fails on mobile**
   - Ensure you're using the `webClientId` parameter (not just iOS/Android client IDs)
   - Web Client ID is required for backend token verification

5. **CORS errors on web**
   - Ensure your domain is added to allowed origins in CocoBase project settings

### Debug Tips

- Check server logs for detailed error messages
- Verify the integration is enabled in your CocoBase dashboard
- Test with a fresh Google account to verify the complete flow
- Use Google's [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) to test token generation
- Inspect the ID token at [jwt.io](https://jwt.io) to verify its contents

## Migration from Old Redirect Flow

If you're migrating from the old OAuth redirect flow:

**Old Flow (Deprecated):**
- `GET /auth-collections/login-google` → Returns OAuth URL
- User redirects to Google → Redirects back to `/auth-google-redirect/{project_id}`

**New Flow (Current):**
- Client uses Google Sign-In SDK → Gets ID token
- `POST /auth-collections/google-verify` with ID token → Returns your JWT

**Benefits of migrating:**
- Better mobile UX (no browser context switches)
- Simpler client code (single API call vs redirect handling)
- Faster authentication (no page reloads)
- Modern best practices

**Migration steps:**
1. Update your client to use Google Sign-In SDK
2. Replace redirect flow code with direct API call to `/google-verify`
3. Remove old redirect URL configuration
4. Test thoroughly on all platforms
