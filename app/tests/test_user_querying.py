"""
Test suite for advanced user querying features
"""

import unittest
import requests
from typing import Optional


class TestUserAdvancedQuerying(unittest.TestCase):
    """Test advanced querying capabilities for /auth/users endpoint"""

    def setUp(self):
        """Setup test configuration"""
        self.base_url = "http://localhost:8000/auth"
        self.headers = {
            "Content-Type": "application/json",
            # Add your API key or authentication token here
            # "Authorization": "Bearer YOUR_TOKEN_HERE"
        }

    def test_basic_filtering(self):
        """Test basic filtering with AND logic"""
        print("\n1. Testing basic filtering...")

        # Filter verified users
        response = requests.get(
            f"{self.base_url}/users",
            params={"confirmed_email": "true"},
            headers=self.headers,
        )
        print(f"   Verified users: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} verified users")
            print(f"   Has more: {data['has_more']}")

    def test_contains_operator(self):
        """Test contains operator for substring search"""
        print("\n2. Testing contains operator...")

        # Search for users with 'admin' in username
        response = requests.get(
            f"{self.base_url}/users",
            params={"username_contains": "admin"},
            headers=self.headers,
        )
        print(f"   Username contains 'admin': {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} matching users")
            if data["data"]:
                print(f"   Example: {data['data'][0].get('username')}")

    def test_multi_field_or_search(self):
        """Test searching across multiple fields with OR logic"""
        print("\n3. Testing multi-field OR search...")

        # Search for 'john' in either username OR email
        response = requests.get(
            f"{self.base_url}/users",
            params={"username__or__email_contains": "john"},
            headers=self.headers,
        )
        print(f"   Username OR email contains 'john': {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} matching users")

    def test_or_conditions(self):
        """Test OR conditions with [or] prefix"""
        print("\n4. Testing OR conditions...")

        # Users with gmail OR yahoo email
        response = requests.get(
            f"{self.base_url}/users",
            params={"[or]email_contains": "gmail", "[or]email_contains": "yahoo"},
            headers=self.headers,
        )
        print(f"   Gmail OR Yahoo users: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} users")

    def test_null_checks(self):
        """Test null/not null filtering"""
        print("\n5. Testing null checks...")

        # Users without Google authentication
        response = requests.get(
            f"{self.base_url}/users",
            params={"google_id_isnull": "true"},
            headers=self.headers,
        )
        print(f"   Users without Google auth: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} users without Google auth")

        # Users WITH Google authentication
        response = requests.get(
            f"{self.base_url}/users",
            params={"google_id_isnull": "false"},
            headers=self.headers,
        )
        print(f"   Users with Google auth: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} users with Google auth")

    def test_email_domain_filtering(self):
        """Test filtering by email domain"""
        print("\n6. Testing email domain filtering...")

        # Users with company email domain
        response = requests.get(
            f"{self.base_url}/users",
            params={"email_endswith": "@company.com"},
            headers=self.headers,
        )
        print(f"   Company email users: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} company users")

    def test_pagination(self):
        """Test pagination parameters"""
        print("\n7. Testing pagination...")

        # Get first page
        response = requests.get(
            f"{self.base_url}/users",
            params={"limit": 10, "offset": 0},
            headers=self.headers,
        )
        print(f"   First page (limit=10): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total users: {data['total']}")
            print(f"   Returned: {len(data['data'])} users")
            print(f"   Has more: {data['has_more']}")

        # Get second page
        if data["has_more"]:
            response = requests.get(
                f"{self.base_url}/users",
                params={"limit": 10, "offset": 10},
                headers=self.headers,
            )
            print(f"   Second page (offset=10): {response.status_code}")

    def test_sorting(self):
        """Test sorting functionality"""
        print("\n8. Testing sorting...")

        # Sort by created_at descending (newest first)
        response = requests.get(
            f"{self.base_url}/users",
            params={"sort": "created_at", "order": "desc", "limit": 5},
            headers=self.headers,
        )
        print(f"   Sort by created_at desc: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Newest {len(data['data'])} users")

        # Sort by email ascending
        response = requests.get(
            f"{self.base_url}/users",
            params={"sort": "email", "order": "asc", "limit": 5},
            headers=self.headers,
        )
        print(f"   Sort by email asc: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   First {len(data['data'])} users alphabetically")

    def test_complex_queries(self):
        """Test complex queries combining multiple features"""
        print("\n9. Testing complex queries...")

        # Verified users with gmail, sorted by username
        response = requests.get(
            f"{self.base_url}/users",
            params={
                "confirmed_email": "true",
                "email_contains": "gmail",
                "sort": "username",
                "order": "asc",
                "limit": 20,
            },
            headers=self.headers,
        )
        print(f"   Complex query: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} verified Gmail users")
            print(f"   Returned {len(data['data'])} users (limit=20)")

    def test_in_operator(self):
        """Test IN operator for multiple values"""
        print("\n10. Testing IN operator...")

        # This would work if you have specific usernames to test
        # Uncomment and modify with actual usernames from your database
        """
        response = requests.get(
            f"{self.base_url}/users",
            params={"username_in": "admin,user1,user2"},
            headers=self.headers
        )
        print(f"   Username in list: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['total']} users")
        """
        print("   (Skipped - requires specific usernames)")


def run_all_tests():
    """Run all tests and display results"""
    print("=" * 60)
    print("ADVANCED USER QUERYING TEST SUITE")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestUserAdvancedQuerying)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)


if __name__ == "__main__":
    # You can run specific tests or all tests

    # Run all tests
    run_all_tests()

    # Or run a specific test
    # test = TestUserAdvancedQuerying()
    # test.setUp()
    # test.test_basic_filtering()
