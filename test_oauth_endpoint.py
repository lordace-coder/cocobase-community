#!/usr/bin/env python3
"""
Test script to verify OAuth endpoints are working.
Run this to test the OAuth client endpoints locally.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Change if your server runs on different port
PLATFORM_USER_EMAIL = "your-email@example.com"  # Change this
PLATFORM_USER_PASSWORD = "your-password"  # Change this

def login_and_get_token():
    """Login as platform user and get Bearer token."""
    print("1. Logging in as platform user...")

    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": PLATFORM_USER_EMAIL,
            "password": PLATFORM_USER_PASSWORD
        }
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    token = data.get("access_token")

    if not token:
        print("❌ No access_token in response")
        print(response.text)
        return None

    print(f"✅ Login successful! Got token: {token[:20]}...")
    return token


def list_oauth_clients(token):
    """List all OAuth clients for the authenticated user."""
    print("\n2. Listing OAuth clients...")

    response = requests.get(
        f"{BASE_URL}/oauth/clients",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )

    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ Failed to list clients")
        print(response.text)
        return None

    data = response.json()
    print(f"✅ Found {len(data.get('clients', []))} OAuth clients")
    print(json.dumps(data, indent=2))
    return data


def create_oauth_client(token):
    """Create a new OAuth client."""
    print("\n3. Creating OAuth client...")

    client_data = {
        "name": "Test OAuth Client",
        "description": "Created via test script",
        "redirect_uris": ["http://localhost:3000/callback"],
        "scopes": ["openid", "email", "profile"],
        "is_confidential": True
    }

    response = requests.post(
        f"{BASE_URL}/oauth/clients",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=client_data
    )

    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ Failed to create client")
        print(response.text)
        return None

    data = response.json()
    print(f"✅ Created OAuth client!")
    print(f"   Client ID: {data.get('client_id')}")
    print(f"   Client Secret: {data.get('client_secret')}")
    print(f"   ⚠️  SAVE THE SECRET - it's only shown once!")
    return data


def main():
    print("=" * 60)
    print("OAuth Endpoint Test Script")
    print("=" * 60)
    print(f"\nTesting against: {BASE_URL}")
    print(f"User: {PLATFORM_USER_EMAIL}")
    print("\nMake sure:")
    print("  1. Your FastAPI server is running")
    print("  2. You've updated PLATFORM_USER_EMAIL and PLATFORM_USER_PASSWORD")
    print("=" * 60)

    # Step 1: Login
    token = login_and_get_token()
    if not token:
        print("\n❌ Cannot proceed without token")
        return

    # Step 2: List existing clients
    list_oauth_clients(token)

    # Step 3: Create a new client
    create_oauth_client(token)

    # Step 4: List again to see the new client
    print("\n4. Listing clients again...")
    list_oauth_clients(token)

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
