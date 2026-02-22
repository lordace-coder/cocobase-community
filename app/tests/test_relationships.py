import os
import sys
import unittest
import uuid
import json

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_client import CollectionsClient

# Configuration
API_URL = "http://127.0.0.1:8000"
API_KEY = "hPBqCur2ljFNXM6yPSExDFj8cmACVAYxT61x_SVQ"  # Replace with your test API key


class TestRelationships(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test data once for all relationship tests."""
        cls.client = CollectionsClient(API_URL, API_KEY)

        # Create collections
        cls.authors_collection = f"authors"
        cls.posts_collection = f"posts"
        cls.comments_collection = f"comments"
        cls.categories_collection = f"categories"

        # Create authors
        cls.author1 = cls.client.create_document(
            cls.authors_collection,
            {"name": "John Doe", "email": "john@example.com", "role": "admin"},
        )
        cls.author2 = cls.client.create_document(
            cls.authors_collection,
            {"name": "Jane Smith", "email": "jane@example.com", "role": "editor"},
        )

        # Create categories
        cls.category1 = cls.client.create_document(
            cls.categories_collection, {"name": "Technology", "slug": "tech"}
        )
        cls.category2 = cls.client.create_document(
            cls.categories_collection, {"name": "Business", "slug": "business"}
        )

        # Create posts with foreign keys
        cls.post1 = cls.client.create_document(
            cls.posts_collection,
            {
                "title": "Understanding Python",
                "content": "Python is great",
                "author_id": cls.author1["id"],
                "category_id": cls.category1["id"],
                "views": 100,
            },
        )
        cls.post2 = cls.client.create_document(
            cls.posts_collection,
            {
                "title": "FastAPI Tutorial",
                "content": "FastAPI is fast",
                "author_id": cls.author1["id"],
                "category_id": cls.category1["id"],
                "views": 200,
            },
        )
        cls.post3 = cls.client.create_document(
            cls.posts_collection,
            {
                "title": "Business Strategy",
                "content": "Strategic planning",
                "author_id": cls.author2["id"],
                "category_id": cls.category2["id"],
                "views": 150,
            },
        )

        # Create comments with foreign keys
        cls.comment1 = cls.client.create_document(
            cls.comments_collection,
            {
                "text": "Great article!",
                "post_id": cls.post1["id"],
                "author_id": cls.author2["id"],
            },
        )
        cls.comment2 = cls.client.create_document(
            cls.comments_collection,
            {
                "text": "Very helpful",
                "post_id": cls.post1["id"],
                "author_id": cls.author1["id"],
            },
        )
        cls.comment3 = cls.client.create_document(
            cls.comments_collection,
            {
                "text": "Thanks for sharing",
                "post_id": cls.post2["id"],
                "author_id": cls.author2["id"],
            },
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up test collections."""
        try:
            # cls.client.delete_collection(cls.authors_collection)
            # cls.client.delete_collection(cls.posts_collection)
            # cls.client.delete_collection(cls.comments_collection)
            # cls.client.delete_collection(cls.categories_collection)
            pass
        except Exception as e:
            print(f"Cleanup warning: {e}")

    def test_populate_single_relationship(self):
        """Test populating a single belongs_to relationship."""
        # Get posts with author populated
        posts = self.client.list_documents(self.posts_collection, populate=["author"])

        print(f"\nDEBUG: Received {len(posts)} posts")
        if len(posts) > 0:
            print(
                f"DEBUG: First post structure: {json.dumps(posts[0], indent=2, default=str)}"
            )

        self.assertGreater(len(posts), 0)

        # Check that author is populated (not just an ID)
        for post in posts:
            # Handle both response structures
            post_data = post.get("data", post)

            if "author_id" in post_data:
                self.assertIn("author", post)
                self.assertIsInstance(post["author"], dict)
                self.assertIn("name", post["author"])
                self.assertIn("email", post["author"])

    def test_populate_multiple_relationships(self):
        """Test populating multiple relationships at once."""
        # Get posts with both author and category populated
        posts = self.client.list_documents(
            self.posts_collection, populate=["author", "category"]
        )

        self.assertGreater(len(posts), 0)

        for post in posts:
            # Check author is populated
            if "author_id" in post["data"]:
                self.assertIn("author", post)
                self.assertIsInstance(post["author"], dict)
                self.assertIn("name", post["author"])

            # Check category is populated
            if "category_id" in post["data"]:
                self.assertIn("category", post)
                self.assertIsInstance(post["category"], dict)
                self.assertIn("name", post["category"])

    def test_nested_population(self):
        """Test nested relationship population (e.g., comment.author and comment.post.author)."""
        # Get comments with nested relationships
        comments = self.client.list_documents(
            self.comments_collection,
            populate=["author", "post.author", "post.category"],
        )

        self.assertGreater(len(comments), 0)

        for comment in comments:
            # Check author is populated
            if "author_id" in comment["data"]:
                self.assertIn("author", comment)
                self.assertIsInstance(comment["author"], dict)

            # Check post is populated
            if "post_id" in comment["data"]:
                self.assertIn("post", comment)
                self.assertIsInstance(comment["post"], dict)

                # Check nested author in post
                if "author_id" in comment["post"]:
                    self.assertIn("author", comment["post"])
                    self.assertIsInstance(comment["post"]["author"], dict)

                # Check nested category in post
                if "category_id" in comment["post"]:
                    self.assertIn("category", comment["post"])
                    self.assertIsInstance(comment["post"]["category"], dict)

    def test_filter_by_relationship_field(self):
        """Test filtering documents by related document fields."""
        # Find posts by admin authors
        admin_posts = self.client.list_documents(
            self.posts_collection, populate=["author"], **{"author.role": "admin"}
        )

        self.assertGreater(len(admin_posts), 0)

        # Verify all returned posts are by admin authors
        for post in admin_posts:
            if "author" in post:
                self.assertEqual(post["author"]["role"], "admin")

    def test_filter_by_nested_relationship(self):
        """Test filtering by nested relationship fields."""
        # Find comments on posts by admin authors
        comments = self.client.list_documents(
            self.comments_collection,
            populate=["post.author"],
            **{"post.author.role": "admin"},
        )

        # Should return comments on posts by admin authors
        if len(comments) > 0:
            for comment in comments:
                if "post" in comment and "author" in comment["post"]:
                    self.assertEqual(comment["post"]["author"]["role"], "admin")

    def test_filter_by_relationship_and_regular_field(self):
        """Test combining relationship filters with regular field filters."""
        # Find posts by admin authors with more than 100 views
        posts = self.client.list_documents(
            self.posts_collection,
            populate=["author"],
            views_gte=100,
            **{"author.role": "admin"},
        )

        for post in posts:
            self.assertGreaterEqual(post["data"]["views"], 100)
            if "author" in post:
                self.assertEqual(post["author"]["role"], "admin")

    def test_select_with_relationships(self):
        """Test selecting specific fields with relationships."""
        # Get only title and author name
        posts = self.client.list_documents(
            self.posts_collection,
            populate=["author"],
            select=["title", "author.name", "author.email"],
        )

        self.assertGreater(len(posts), 0)

        for post in posts:
            # Should have id (always included), title, and author with only name/email
            self.assertIn("id", post)
            self.assertIn("title", post)

            if "author" in post:
                self.assertIn("name", post["author"])
                self.assertIn("email", post["author"])
                # Should NOT have other fields like role (unless we selected it)
                # This depends on your implementation

    def test_aggregate_with_relationship_filter(self):
        """Test aggregation with relationship filters."""
        # Count posts by admin authors
        result = self.client.aggregate_documents(
            self.posts_collection,
            field="views",
            operation="sum",
            **{"author.role": "admin"},
        )

        self.assertIn("result", result)
        self.assertIsNotNone(result["result"])
        # Should sum views only from admin author posts

    def test_group_by_with_relationship_filter(self):
        """Test group by with relationship filters."""
        # Group posts by category, but only for admin authors
        groups = self.client.group_by_field(
            self.posts_collection, field="category_id", **{"author.role": "admin"}
        )

        self.assertIsInstance(groups, list)
        # All grouped posts should be from admin authors

    def test_get_single_document_with_relationships(self):
        """Test getting a single document with populated relationships."""
        # Get a specific post with relationships
        post = self.client.get_document(
            self.posts_collection, self.post1["id"], populate=["author", "category"]
        )

        self.assertEqual(post["id"], self.post1["id"])

        # Check relationships are populated
        if "author_id" in post:
            self.assertIn("author", post)
            self.assertIsInstance(post["author"], dict)
            self.assertIn("name", post["author"])

        if "category_id" in post:
            self.assertIn("category", post)
            self.assertIsInstance(post["category"], dict)
            self.assertIn("name", post["category"])

    def test_export_with_relationships(self):
        """Test exporting data with populated relationships."""
        # Export posts with author information
        json_data = self.client.export_collection(
            self.posts_collection, format="json", populate=["author", "category"]
        )

        self.assertIsNotNone(json_data)
        self.assertGreater(len(json_data), 0)

        # Parse JSON to verify structure
        import json

        data = json.loads(json_data.decode("utf-8"))

        self.assertIsInstance(data, list)
        if len(data) > 0:
            # Check that relationships are included in export
            first_post = data[0]
            if "author_id" in first_post:
                self.assertIn("author", first_post)
                self.assertIsInstance(first_post["author"], dict)

    def test_count_with_relationship_filter(self):
        """Test counting documents with relationship filters."""
        # This would require a count endpoint that supports filters
        # For now, we can verify by listing and checking length
        posts = self.client.list_documents(
            self.posts_collection, **{"author.role": "admin"}
        )

        admin_post_count = len(posts)

        # Verify count is correct
        all_posts = self.client.list_documents(self.posts_collection)

        self.assertLessEqual(admin_post_count, len(all_posts))

    def test_reverse_relationship(self):
        """Test reverse relationship (e.g., get author's posts)."""
        # Get author with their posts (if supported)
        # This tests the reverse relationship where we populate posts from author
        author = self.client.get_document(
            self.authors_collection,
            self.author1["id"],
            populate=["posts"],  # Reverse relationship
        )

        self.assertEqual(author["id"], self.author1["id"])

        # Check if posts are populated (implementation dependent)
        if "posts" in author:
            self.assertIsInstance(author["posts"], list)
            self.assertGreater(len(author["posts"]), 0)

    def test_multiple_foreign_key_same_collection(self):
        """Test when multiple fields reference the same collection."""
        # Create a post with both author and editor from same collection
        post_with_editor = self.client.create_document(
            self.posts_collection,
            {
                "title": "Edited Post",
                "content": "Content here",
                "author_id": self.author1["id"],
                "editor_id": self.author2["id"],  # Different person, same collection
                "category_id": self.category1["id"],
            },
        )

        # Get the post with both relationships populated
        post = self.client.get_document(
            self.posts_collection, post_with_editor["id"], populate=["author", "editor"]
        )

        # Both should be populated as separate fields
        if "author_id" in post:
            self.assertIn("author", post)
            self.assertEqual(post["author"]["id"], self.author1["id"])

        if "editor_id" in post:
            self.assertIn("editor", post)
            self.assertEqual(post["editor"]["id"], self.author2["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
