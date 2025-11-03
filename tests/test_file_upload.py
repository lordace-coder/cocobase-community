#!/usr/bin/env python3
"""
Test script for file upload with document creation/update
Demonstrates the new file upload functionality
"""

import requests
import json
from pathlib import Path

# Configuration
API_BASE_URL = "https://api.cocobase.com"
API_KEY = "your-api-key-here"  # Replace with your actual API key

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def test_create_document_with_files():
    """Test creating a document with file uploads"""
    print("🧪 Test 1: Create document with files")
    print("-" * 50)

    # Prepare data
    document_data = {
        "name": "Gaming Laptop",
        "price": 1299.99,
        "category": "electronics",
        "specs": {"ram": "16GB", "storage": "512GB SSD", "processor": "Intel i7"},
    }

    # Prepare files (create dummy files for testing)
    files = [
        (
            "files",
            (
                "laptop-front.jpg",
                open("test-images/laptop-front.jpg", "rb"),
                "image/jpeg",
            ),
        ),
        (
            "files",
            (
                "laptop-side.jpg",
                open("test-images/laptop-side.jpg", "rb"),
                "image/jpeg",
            ),
        ),
    ]

    # Prepare form data
    data = {"data": json.dumps(document_data)}

    # Send request
    response = requests.post(
        f"{API_BASE_URL}/collections/documents?collection=products",
        headers=HEADERS,
        data=data,
        files=files,
    )

    # Check response
    if response.status_code == 201:
        result = response.json()
        print("✅ Success!")
        print(f"Document ID: {result['id']}")
        print(
            f"File URLs: {result['data'].get('file_urls', result['data'].get('file_url'))}"
        )
        print(json.dumps(result, indent=2))
        return result["id"]
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        return None


def test_create_document_json_only():
    """Test creating document without files (backward compatibility)"""
    print("\n🧪 Test 2: Create document JSON only (backward compatibility)")
    print("-" * 50)

    document_data = {
        "data": {"name": "Wireless Mouse", "price": 29.99, "category": "accessories"}
    }

    response = requests.post(
        f"{API_BASE_URL}/collections/documents?collection=products",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=document_data,
    )

    if response.status_code == 201:
        result = response.json()
        print("✅ Success! (Backward compatibility works)")
        print(f"Document ID: {result['id']}")
        return result["id"]
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        return None


def test_update_document_with_files(document_id):
    """Test updating document with new files"""
    print(f"\n🧪 Test 3: Update document {document_id} with new files")
    print("-" * 50)

    # Prepare update data
    update_data = {"price": 1199.99, "on_sale": True}  # Reduced price

    # Prepare new file
    files = [
        (
            "files",
            ("laptop-new.jpg", open("test-images/laptop-new.jpg", "rb"), "image/jpeg"),
        )
    ]

    data = {"data": json.dumps(update_data)}

    response = requests.patch(
        f"{API_BASE_URL}/collections/products/documents/{document_id}",
        headers=HEADERS,
        data=data,
        files=files,
    )

    if response.status_code == 200:
        result = response.json()
        print("✅ Success!")
        print(f"Updated price: ${result['data']['price']}")
        print(
            f"File URLs: {result['data'].get('file_urls', result['data'].get('file_url'))}"
        )
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def test_single_file_upload():
    """Test uploading single file (should use file_url not file_urls)"""
    print("\n🧪 Test 4: Create document with single file")
    print("-" * 50)

    document_data = {
        "name": "User Profile",
        "email": "john@example.com",
        "bio": "Software developer",
    }

    files = [
        ("files", ("avatar.jpg", open("test-images/avatar.jpg", "rb"), "image/jpeg"))
    ]

    data = {"data": json.dumps(document_data)}

    response = requests.post(
        f"{API_BASE_URL}/collections/documents?collection=users",
        headers=HEADERS,
        data=data,
        files=files,
    )

    if response.status_code == 201:
        result = response.json()
        print("✅ Success!")

        # Check if single file uses file_url (string)
        if "file_url" in result["data"]:
            print("✅ Correct! Single file stored as 'file_url' (string)")
            print(f"File URL: {result['data']['file_url']}")
        elif "file_urls" in result["data"]:
            print("⚠️ Warning: Single file stored as 'file_urls' (should be 'file_url')")

        print(json.dumps(result, indent=2))
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def test_storage_limit():
    """Test storage limit enforcement"""
    print("\n🧪 Test 5: Test storage limit (should fail if over limit)")
    print("-" * 50)

    # Try to upload a very large file
    print("Creating 60MB dummy file...")

    # Create large dummy file (60MB - exceeds free plan limit of 50MB)
    large_file_path = Path("test-large-file.bin")
    with open(large_file_path, "wb") as f:
        f.write(b"0" * (60 * 1024 * 1024))  # 60MB

    document_data = {"name": "Large file test"}

    files = [
        (
            "files",
            ("large-file.bin", open(large_file_path, "rb"), "application/octet-stream"),
        )
    ]

    data = {"data": json.dumps(document_data)}

    response = requests.post(
        f"{API_BASE_URL}/collections/documents?collection=test",
        headers=HEADERS,
        data=data,
        files=files,
    )

    # Cleanup
    large_file_path.unlink()

    if response.status_code == 413:
        print("✅ Correct! Storage limit enforced")
        print(response.json())
    elif response.status_code == 201:
        print("⚠️ Warning: File uploaded (may have enough storage)")
    else:
        print(f"❌ Unexpected error: {response.status_code}")
        print(response.json())


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("FILE UPLOAD TESTS")
    print("=" * 50)

    # Test 1: Create with files
    doc_id = test_create_document_with_files()

    # Test 2: JSON only (backward compatibility)
    test_create_document_json_only()

    # Test 3: Update with files
    if doc_id:
        test_update_document_with_files(doc_id)

    # Test 4: Single file
    test_single_file_upload()

    # Test 5: Storage limit
    test_storage_limit()

    print("\n" + "=" * 50)
    print("TESTS COMPLETED")
    print("=" * 50)


if __name__ == "__main__":
    print("⚠️  Before running, make sure to:")
    print("1. Replace API_KEY with your actual key")
    print("2. Create test-images/ folder with sample images")
    print("3. Install requests: pip install requests")
    print()

    # Uncomment to run tests
    # run_all_tests()

    print("\n📝 Example Usage:\n")
    print("python test_file_upload.py")
