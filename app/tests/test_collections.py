import os
import sys
import unittest
import uuid

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_client import CollectionsClient

# Configuration
API_URL = "http://127.0.0.1:8000"
API_KEY = "VTXjd5f7SRhfyqpKKenvSNCYzOSOaVBj75pYBQ8Z"  # Replace with your test API key


class BaseCollectionTest(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.client = CollectionsClient(API_URL, API_KEY)
        collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
        self.test_collection = self.client.create_collection(collection_name)

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        try:
            self.client.delete_collection(self.test_collection["id"])
        except Exception:
            pass


class TestCollections(BaseCollectionTest):
    def test_create_collection(self):
        """Test creating a new collection."""
        name = f"test_{uuid.uuid4().hex[:8]}"
        collection = self.client.create_collection(name)
        self.assertEqual(collection["name"], name)
        self.assertIn("id", collection)

        # Cleanup
        self.client.delete_collection(collection["id"])

    def test_update_collection(self):
        """Test updating a collection name."""
        new_name = f"updated_{uuid.uuid4().hex[:8]}"
        updated = self.client.update_collection(self.test_collection["id"], new_name)
        self.assertEqual(updated["name"], new_name)
        self.assertEqual(updated["id"], self.test_collection["id"])

    def test_delete_collection(self):
        """Test deleting a collection."""
        collection = self.client.create_collection(f"test_{uuid.uuid4().hex[:8]}")
        self.client.delete_collection(collection["id"])

        # Verify deletion
        with self.assertRaises(Exception):
            self.client.get_collection_schema(collection["id"])


class TestDocuments(BaseCollectionTest):
    def test_create_document(self):
        """Test creating a new document."""
        data = {"name": "John Doe", "age": 30}
        doc = self.client.create_document(self.test_collection["name"], data)
        self.assertEqual(doc["data"], data)
        self.assertIn("id", doc)

    def test_list_documents(self):
        """Test listing documents with filters."""
        # Create test documents
        docs_data = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
            {"name": "Bob", "age": 35},
        ]

        for data in docs_data:
            self.client.create_document(self.test_collection["name"], data)

        # Test basic listing
        docs = self.client.list_documents(self.test_collection["id"])
        self.assertEqual(len(docs), 3)

        # Test filtering
        filtered = self.client.list_documents(self.test_collection["id"], age_gte=30)
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(d["data"]["age"] >= 30 for d in filtered))

    def test_get_document(self):
        """Test getting a single document."""
        data = {"name": "John Doe", "age": 30}
        created = self.client.create_document(self.test_collection["name"], data)

        doc = self.client.get_document(self.test_collection["id"], created["id"])
        self.assertEqual(doc["data"], data)
        self.assertEqual(doc["id"], created["id"])

    def test_update_document(self):
        """Test updating a document."""
        doc = self.client.create_document(
            self.test_collection["name"], {"name": "John", "age": 30}
        )

        updated_data = {"name": "John", "age": 31}
        updated = self.client.update_document(
            self.test_collection["id"], doc["id"], updated_data
        )
        self.assertEqual(updated["data"]["age"], 31)

    def test_delete_document(self):
        """Test deleting a document."""
        doc = self.client.create_document(
            self.test_collection["name"], {"name": "John"}
        )
        self.client.delete_document(self.test_collection["id"], doc["id"])

        # Verify deletion
        with self.assertRaises(Exception):
            self.client.get_document(self.test_collection["id"], doc["id"])


class TestBatchOperations(BaseCollectionTest):
    def test_batch_create_documents(self):
        """Test creating multiple documents at once."""
        documents = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
            {"name": "Bob", "age": 35},
        ]

        created = self.client.batch_create_documents(
            self.test_collection["id"], documents
        )
        self.assertEqual(len(created), 3)
        self.assertTrue(all("id" in doc for doc in created))

    def test_batch_delete_documents(self):
        """Test deleting multiple documents at once."""
        # Create test documents
        docs = [
            self.client.create_document(self.test_collection["name"], {"name": "John"}),
            self.client.create_document(self.test_collection["name"], {"name": "Jane"}),
        ]
        doc_ids = [doc["id"] for doc in docs]

        result = self.client.batch_delete_documents(self.test_collection["id"], doc_ids)
        self.assertEqual(result["count"], 2)


class TestAdvancedFeatures(BaseCollectionTest):
    def test_get_collection_schema(self):
        """Test getting collection schema."""
        # Create some documents with different schemas
        self.client.create_document(
            self.test_collection["name"], {"name": "John", "age": 30}
        )
        self.client.create_document(
            self.test_collection["name"], {"name": "Jane", "score": 95.5}
        )

        schema = self.client.get_collection_schema(self.test_collection["id"])
        self.assertIn("fields", schema)
        self.assertIn("name", schema["fields"])
        self.assertIn("age", schema["fields"])
        self.assertIn("score", schema["fields"])

    def test_export_collection(self):
        """Test exporting collection data."""
        # Create test documents
        self.client.create_document(
            self.test_collection["name"], {"name": "John", "age": 30}
        )
        self.client.create_document(
            self.test_collection["name"], {"name": "Jane", "age": 25}
        )

        # Test JSON export
        json_data = self.client.export_collection(
            self.test_collection["id"], format="json"
        )
        self.assertTrue(json_data)

        # Test CSV export
        csv_data = self.client.export_collection(
            self.test_collection["id"], format="csv"
        )
        self.assertTrue(csv_data)

    def test_aggregate_documents(self):
        """Test document aggregation."""
        # Create test documents
        for age in [25, 30, 35, 40]:
            self.client.create_document(
                self.test_collection["name"], {"name": f"User{age}", "age": age}
            )

        # Test average age
        avg_result = self.client.aggregate_documents(
            self.test_collection["id"], "age", "avg"
        )
        self.assertEqual(avg_result["result"], 32.5)  # (25 + 30 + 35 + 40) / 4

        # Test count
        count_result = self.client.aggregate_documents(
            self.test_collection["id"], "age", "count"
        )
        self.assertEqual(count_result["result"], 4)

    def test_group_by_field(self):
        """Test grouping documents by field."""
        # Create test documents
        docs_data = [
            {"status": "active", "type": "user"},
            {"status": "active", "type": "admin"},
            {"status": "inactive", "type": "user"},
        ]
        for data in docs_data:
            self.client.create_document(self.test_collection["name"], data)

        # Group by status
        groups = self.client.group_by_field(self.test_collection["id"], "status")
        self.assertEqual(len(groups), 2)
        active_group = next(g for g in groups if g["status"] == "active")
        self.assertEqual(active_group["count"], 2)


if __name__ == "__main__":
    unittest.main()
