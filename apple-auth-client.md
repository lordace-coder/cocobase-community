# Apple Sign-In Authentication

This feature allows your application users to sign in using their Apple ID through ID token verification. This implementation works seamlessly for both web and mobile (iOS) applications.

## How It Works

This implementation uses **ID token verification** for a modern, secure authentication flow:

1. Your client (web/iOS app) uses Apple Sign-In SDK to authenticate the user
2. Apple returns an ID token (and optional user data) to your client
3. Your client sends the ID token to CocoBase
4. CocoBase verifies the token with Apple's public keys
5. CocoBase creates/logs in the user and returns your app's JWT token

**Benefits:**
- ✅ Native iOS experience with system Sign in with Apple
- ✅ Privacy-focused (users can hide their email with private relay)
- ✅ Simple implementation (single API call)
- ✅ Secure token verification server-side
- ✅ Required for iOS apps in App Store (when other social logins are offered)

**Important Note:** Apple only sends user data (name) on the **first authentication**. Store this information immediately when received, as subsequent logins will only provide the ID token.

## Prerequisites

Before implementing Apple Sign-In, you need to:

1. **Set up Apple Sign-In:**
   - Go to [Apple Developer Portal](https://developer.apple.com/)
   - Sign in with your Apple Developer account ($99/year required)
   - Register an App ID with Sign in with Apple capability enabled

2. **For Web Applications:**
   - Create a Service ID in Apple Developer Portal
   - Configure domains and return URLs
   - Enable Sign in with Apple for the Service ID

3. **For iOS Applications:**
   - Enable Sign in with Apple capability in Xcode
   - App ID will be your bundle identifier

4. **Enable Apple Sign-In integration** in your CocoBase project settings

5. **Configure your project** with the Apple Client ID

## Configuration

Add the following configuration to your CocoBase project integration settings:

```json
{
  "APPLE_CLIENT_ID": "com.yourcompany.yourapp"
}
```

### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `APPLE_CLIENT_ID` | string | Yes | Service ID (for web) or App Bundle ID (for iOS) |
| `APPLE_TEAM_ID` | string | No | Your Apple Developer Team ID (only if generating client_secret server-side) |
| `APPLE_KEY_ID` | string | No | Apple Key ID (only if generating client_secret server-side) |
| `APPLE_PRIVATE_KEY` | string | No | Apple Private Key content (only if generating client_secret server-side) |

**Note:** For most use cases, you only need `APPLE_CLIENT_ID`. The other parameters are only required if you plan to generate client secrets server-side (advanced use case).

## API Endpoint

### Verify Apple ID Token

**Endpoint:** `POST /auth-collections/apple-verify`

**Headers:**
```
x-api-key: your-project-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "id_token": "eyJraWQiOiJlWGF1bm1MIiwiYWxnIjoiUlMyNTYifQ...",
  "user": {
    "name": {
      "firstName": "John",
      "lastName": "Doe"
    }
  },
  "platform": "ios"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id_token` | string | Yes | The ID token from Apple Sign-In |
| `user` | object | No | User data object (only sent by Apple on first sign-in) |
| `user.name.firstName` | string | No | User's first name |
| `user.name.lastName` | string | No | User's last name |
| `platform` | string | No | Platform identifier for analytics ("ios", "web") |

**Success Response (200):**
```json
{
  "access_token": "your_jwt_token_for_subsequent_api_calls",
  "user": {
    "id": "user-uuid",
    "email": "user@privaterelay.appleid.com",
    "data": {
      "username": "johndoe",
      "name": "John Doe",
      "is_private_email": true
    },
    "oauth_provider": "apple",
    "created_at": "2025-11-16T10:30:00Z"
  }
}
```

**Error Responses:**

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Apple Sign-In integration is not enabled | Integration not activated in project settings |
| 400 | APPLE_CLIENT_ID is not configured | Client ID missing from project config |
| 400 | Invalid Apple ID token | Token verification failed or token expired |
| 400 | Apple ID token has expired | Token is no longer valid |
| 400 | This email is already registered with password authentication | User must use email/password login |
| 400 | This email is already registered with Google Sign-In | User must use Google to login |
| 500 | An error occurred during authentication | Server error |

## Implementation Examples

### iOS (Swift with Sign in with Apple)

```swift
import AuthenticationServices

class ViewController: UIViewController, ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding {

    func setupAppleSignInButton() {
        let appleSignInButton = ASAuthorizationAppleIDButton()
        appleSignInButton.addTarget(self, action: #selector(handleAppleSignIn), for: .touchUpInside)
        // Add button to your view
    }

    @objc func handleAppleSignIn() {
        let appleIDProvider = ASAuthorizationAppleIDProvider()
        let request = appleIDProvider.createRequest()
        request.requestedScopes = [.fullName, .email]

        let authorizationController = ASAuthorizationController(authorizationRequests: [request])
        authorizationController.delegate = self
        authorizationController.presentationContextProvider = self
        authorizationController.performRequests()
    }

    // MARK: - ASAuthorizationControllerDelegate

    func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        if let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential {
            guard let identityToken = appleIDCredential.identityToken,
                  let idTokenString = String(data: identityToken, encoding: .utf8) else {
                return
            }

            // Prepare user data (only available on first sign-in)
            var userData: [String: Any]? = nil
            if let fullName = appleIDCredential.fullName,
               let firstName = fullName.givenName,
               let lastName = fullName.familyName {
                userData = [
                    "name": [
                        "firstName": firstName,
                        "lastName": lastName
                    ]
                ]
            }

            // Send to CocoBase
            authenticateWithCocoBase(idToken: idTokenString, user: userData)
        }
    }

    func authenticateWithCocoBase(idToken: String, user: [String: Any]?) {
        let url = URL(string: "https://api.cocobase.buzz/auth-collections/apple-verify")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("YOUR_PROJECT_API_KEY", forHTTPHeaderField: "x-api-key")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = [
            "id_token": idToken,
            "platform": "ios"
        ]
        if let user = user {
            body["user"] = user
        }

        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data,
                  let httpResponse = response as? HTTPURLResponse else { return }

            if httpResponse.statusCode == 200,
               let json = try? JSONDecoder().decode(AuthResponse.self, from: data) {
                // Store token
                UserDefaults.standard.set(json.access_token, forKey: "auth_token")
                DispatchQueue.main.async {
                    // Navigate to main screen
                }
            } else {
                // Handle error
                print("Authentication failed")
            }
        }.resume()
    }

    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        return self.view.window!
    }
}

// Response model
struct AuthResponse: Codable {
    let access_token: String
    let user: UserInfo
}

struct UserInfo: Codable {
    let id: String
    let email: String
}
```

### iOS (SwiftUI)

```swift
import SwiftUI
import AuthenticationServices

struct LoginView: View {
    @State private var isAuthenticated = false

    var body: some View {
        VStack {
            SignInWithAppleButton(
                onRequest: { request in
                    request.requestedScopes = [.fullName, .email]
                },
                onCompletion: { result in
                    switch result {
                    case .success(let authorization):
                        handleAppleSignIn(authorization: authorization)
                    case .failure(let error):
                        print("Apple Sign-In failed: \(error)")
                    }
                }
            )
            .frame(height: 50)
            .padding()
        }
    }

    func handleAppleSignIn(authorization: ASAuthorization) {
        guard let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let identityToken = appleIDCredential.identityToken,
              let idTokenString = String(data: identityToken, encoding: .utf8) else {
            return
        }

        // Prepare user data
        var userData: [String: [String: String]]? = nil
        if let fullName = appleIDCredential.fullName,
           let firstName = fullName.givenName,
           let lastName = fullName.familyName {
            userData = [
                "name": [
                    "firstName": firstName,
                    "lastName": lastName
                ]
            ]
        }

        // Send to CocoBase
        Task {
            await authenticateWithCocoBase(idToken: idTokenString, user: userData)
        }
    }

    func authenticateWithCocoBase(idToken: String, user: [String: [String: String]]?) async {
        guard let url = URL(string: "https://api.cocobase.buzz/auth-collections/apple-verify") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("YOUR_PROJECT_API_KEY", forHTTPHeaderField: "x-api-key")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = [
            "id_token": idToken,
            "platform": "ios"
        ]
        if let user = user {
            body["user"] = user
        }

        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                let authResponse = try JSONDecoder().decode(AuthResponse.self, from: data)
                UserDefaults.standard.set(authResponse.access_token, forKey: "auth_token")
                isAuthenticated = true
            }
        } catch {
            print("Authentication error: \(error)")
        }
    }
}
```

### Web (JavaScript with Apple JS SDK)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Sign in with Apple</title>
    <meta name="appleid-signin-client-id" content="YOUR_SERVICE_ID">
    <meta name="appleid-signin-scope" content="name email">
    <meta name="appleid-signin-redirect-uri" content="https://yourdomain.com">
    <meta name="appleid-signin-state" content="signin">
    <meta name="appleid-signin-use-popup" content="true">
    <script type="text/javascript" src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"></script>
</head>
<body>
    <!-- Apple Sign-In Button -->
    <div id="appleid-signin" data-color="black" data-border="true" data-type="sign in"></div>

    <script>
        // Listen for authorization success
        document.addEventListener('AppleIDSignInOnSuccess', async (event) => {
            const { authorization } = event.detail;

            // Prepare request body
            const body = {
                id_token: authorization.id_token,
                platform: 'web'
            };

            // Add user data if available (first sign-in only)
            if (authorization.user) {
                body.user = authorization.user;
            }

            try {
                const response = await fetch('https://api.cocobase.buzz/auth-collections/apple-verify', {
                    method: 'POST',
                    headers: {
                        'x-api-key': 'YOUR_PROJECT_API_KEY',
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(body)
                });

                const data = await response.json();

                if (response.ok) {
                    // Store token and redirect
                    localStorage.setItem('auth_token', data.access_token);
                    window.location.href = '/dashboard';
                } else {
                    alert('Authentication failed: ' + data.detail);
                }
            } catch (error) {
                console.error('Error:', error);
            }
        });

        // Listen for authorization failure
        document.addEventListener('AppleIDSignInOnFailure', (event) => {
            console.error('Apple Sign-In failed:', event.detail.error);
        });
    </script>
</body>
</html>
```

### React Native

**Note:** React Native doesn't have official Apple Sign-In support. Use native modules or community libraries:

```bash
npm install @invertase/react-native-apple-authentication
```

```jsx
import { appleAuth } from '@invertase/react-native-apple-authentication';

async function signInWithApple() {
  try {
    // Perform Apple Sign-In request
    const appleAuthRequestResponse = await appleAuth.performRequest({
      requestedOperation: appleAuth.Operation.LOGIN,
      requestedScopes: [appleAuth.Scope.EMAIL, appleAuth.Scope.FULL_NAME],
    });

    const { identityToken, fullName } = appleAuthRequestResponse;

    if (!identityToken) {
      throw new Error('No identity token returned');
    }

    // Prepare user data (only available on first sign-in)
    let userData = undefined;
    if (fullName && fullName.givenName && fullName.familyName) {
      userData = {
        name: {
          firstName: fullName.givenName,
          lastName: fullName.familyName,
        }
      };
    }

    // Send to CocoBase
    const response = await fetch('https://api.cocobase.buzz/auth-collections/apple-verify', {
      method: 'POST',
      headers: {
        'x-api-key': 'YOUR_PROJECT_API_KEY',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id_token: identityToken,
        user: userData,
        platform: 'ios'
      })
    });

    const data = await response.json();

    if (response.ok) {
      // Store token securely
      await AsyncStorage.setItem('auth_token', data.access_token);
      // Navigate to home screen
      navigation.navigate('Home');
    } else {
      Alert.alert('Authentication Failed', data.detail);
    }
  } catch (error) {
    console.error('Apple Sign-In error:', error);
  }
}
```

## User Management

### New Users
When a user signs in with Apple for the first time:
- A new `AppUser` record is created
- `oauth_id` is set to Apple's unique user ID (`sub` field)
- `oauth_provider` is set to `"apple"`
- `email` is set from Apple (may be private relay email)
- `data.name` is set from the user object (if provided)
- `data.is_private_email` indicates if user chose to hide their email

### Existing Users
For users who already exist in the system:
- **Apple OAuth users**: Successfully logged in with new token
- **Password users**: Error returned - must use password login
- **Other OAuth users (e.g., Google)**: Error returned - must use original provider

### Important Notes

1. **User Data Availability:**
   - Apple only sends `fullName` and `email` on the **first authorization**
   - Subsequent sign-ins only provide the `identityToken`
   - **Store name information immediately** when received
   - For returning users, retrieve name from your database

2. **Private Email Relay:**
   - Users can choose to "Hide My Email"
   - Apple generates a unique relay email: `user@privaterelay.appleid.com`
   - This email forwards to the user's real email
   - Store the `is_private_email` flag in user data

3. **Email Verification:**
   - Emails from Apple are always verified
   - No need for additional email verification flow

## Security Features

- ✅ **Token Verification**: ID tokens verified using Apple's public keys (RS256)
- ✅ **Email Privacy**: Support for Apple's private relay emails
- ✅ **Provider Isolation**: Users can't mix authentication providers
- ✅ **Secure Token Generation**: Your app's JWT tokens generated server-side
- ✅ **Token Expiration**: ID tokens expire after 10 minutes
- ✅ **Public Key Rotation**: Automatic fetching of Apple's current public keys

## Apple Developer Setup

### For iOS Apps

1. **Enable Sign in with Apple:**
   - Open your project in Xcode
   - Select your target → Signing & Capabilities
   - Click "+ Capability" → Sign in with Apple

2. **App ID Configuration:**
   - Go to [Apple Developer Portal](https://developer.apple.com/account/resources/identifiers/list)
   - Select your App ID
   - Enable "Sign in with Apple"
   - Save and regenerate provisioning profiles

### For Web Apps

1. **Create a Service ID:**
   - Go to Apple Developer Portal → Certificates, Identifiers & Profiles
   - Click "+" → Service IDs
   - Register a new Service ID (e.g., `com.yourcompany.yourapp.web`)

2. **Configure Service ID:**
   - Enable "Sign in with Apple"
   - Configure domains: Add your website domain
   - Configure return URLs: Add your callback URL
   - Save

3. **Use Service ID as Client ID:**
   - In CocoBase configuration, use the Service ID as `APPLE_CLIENT_ID`

## Troubleshooting

### Common Issues

1. **"APPLE_CLIENT_ID is not configured"**
   - Ensure you've added the client ID to your CocoBase project integration settings
   - For iOS: Use your App Bundle ID
   - For Web: Use your Service ID

2. **"Invalid Apple ID token"**
   - Token may have expired (tokens expire after 10 minutes)
   - Ensure the token is from the correct environment (development/production)
   - Verify client ID matches the one used to generate the token

3. **"This email is already registered with password authentication"**
   - User must use email/password login instead
   - Consider implementing account linking

4. **User data (name) is null on subsequent logins**
   - This is expected Apple behavior
   - Store name information on first sign-in
   - Retrieve from your database for returning users

5. **Private relay emails**
   - User chose "Hide My Email"
   - Store the relay email - Apple handles forwarding
   - Check `is_private_email` flag in user data

### Debug Tips

- Check server logs for detailed error messages
- Verify the integration is enabled in your CocoBase dashboard
- Test with a test Apple ID first
- Inspect the ID token at [jwt.io](https://jwt.io) to verify its contents
- Ensure your Apple Developer account is in good standing
- For iOS: Check that Sign in with Apple capability is enabled in Xcode
- For Web: Verify domains and return URLs are correctly configured

## App Store Requirements

**Important for iOS Apps:**

If your app offers any other social login options (Google, Facebook, etc.), **Apple requires you to also offer Sign in with Apple** per [App Store Review Guidelines 4.8](https://developer.apple.com/app-store/review/guidelines/#sign-in-with-apple).

Failure to comply may result in app rejection during review.

## Privacy Considerations

Apple Sign-In is designed with privacy in mind:

- Users can hide their real email address
- No tracking or profiling by third parties
- Users control what information is shared
- Two-factor authentication built-in
- Minimal data collection

Respect user privacy by:
- Only requesting necessary information
- Clearly explaining why you need data
- Honoring "Hide My Email" choices
- Implementing proper data handling practices
