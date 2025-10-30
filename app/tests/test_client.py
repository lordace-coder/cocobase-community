import requests
from typing import Optional, Dict, Any, List
import json


class CollectionsClient:
    def __init__(self, base_url: str, api_key: str):
        """Initialize the collections test client."""
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }

    def _log_error(self, response, url):
        """Log detailed error information."""
        print(f"\n{'='*60}")
        print(f"ERROR: {response.status_code} - {response.reason}")
        print(f"URL: {url}")
        try:
            error_detail = response.json()
            print(f"Response Body:\n{json.dumps(error_detail, indent=2)}")
        except:
            print(f"Response Body: {response.text}")
        print(f"{'='*60}\n")

    def create_collection(self, name: str) -> Dict[str, Any]:
        """Create a new collection."""
        url = f"{self.base_url}/collections/"
        payload = {"name": name}
        response = requests.post(url, json=payload, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def update_collection(self, collection_id: str, name: str) -> Dict[str, Any]:
        """Update a collection."""
        url = f"{self.base_url}/collections/{collection_id}"
        payload = {"name": name}
        response = requests.patch(url, json=payload, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection."""
        url = f"{self.base_url}/collections/{collection_id}"
        response = requests.delete(url, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()

    def create_document(self, collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document in a collection."""
        url = f"{self.base_url}/collections/documents"
        payload = {"data": data}
        params = {"collection": collection}
        response = requests.post(url, json=payload, params=params, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def list_documents(
        self,
        collection_id: str,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[str] = None,
        order: str = "desc",
        populate: Optional[List[str]] = None,
        select: Optional[List[str]] = None,
        **filters,
    ) -> List[Dict[str, Any]]:
        """List documents in a collection with optional filtering and pagination."""
        url = f"{self.base_url}/collections/{collection_id}/documents"

        # Build params without populate/select first
        params = {"limit": limit, "offset": offset, "order": order}
        if sort:
            params["sort"] = sort

        # Add filter params
        params.update(filters)

        # Build full URL with multiple populate/select params
        from urllib.parse import urlencode

        query_parts = [urlencode(params)]

        if populate:
            for pop in populate:
                query_parts.append(f"populate={pop}")

        if select:
            for sel in select:
                query_parts.append(f"select={sel}")

        full_url = f"{url}?{'&'.join(query_parts)}"

        response = requests.get(full_url, headers=self.headers)
        if not response.ok:
            self._log_error(response, full_url)
        response.raise_for_status()

        result = response.json()

        # Debug logging for relationships
        if populate or select:
            print(f"\nDEBUG: Raw response type: {type(result)}")
            if isinstance(result, dict):
                print(f"DEBUG: Response keys: {result.keys()}")
                if "data" in result:
                    print(f"DEBUG: Data length: {len(result['data'])}")
            elif isinstance(result, list):
                print(f"DEBUG: Response list length: {len(result)}")

        # Handle both response formats:
        # 1. Direct list (standard query)
        # 2. Dict with "data" key (relationship resolver)
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return result

    def get_document(
        self,
        collection_id: str,
        document_id: str,
        populate: Optional[List[str]] = None,
        select: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get a single document by ID."""
        url = f"{self.base_url}/collections/{collection_id}/documents/{document_id}"

        # Build query string manually to support multiple populate/select params
        query_parts = []

        if populate:
            for pop in populate:
                query_parts.append(f"populate={pop}")

        if select:
            for sel in select:
                query_parts.append(f"select={sel}")

        if query_parts:
            url = f"{url}?{'&'.join(query_parts)}"

        response = requests.get(url, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def update_document(
        self, collection_id: str, document_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a document."""
        url = f"{self.base_url}/collections/{collection_id}/documents/{document_id}"
        payload = {"data": data}
        response = requests.patch(url, json=payload, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def delete_document(self, collection_id: str, document_id: str) -> None:
        """Delete a document."""
        url = f"{self.base_url}/collections/{collection_id}/documents/{document_id}"
        response = requests.delete(url, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()

    def batch_create_documents(
        self, collection_id: str, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create multiple documents at once."""
        url = f"{self.base_url}/collections/{collection_id}/batch/documents/create"
        payload = {"documents": documents}
        response = requests.post(url, json=payload, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def batch_delete_documents(
        self, collection_id: str, document_ids: List[str]
    ) -> Dict[str, Any]:
        """Delete multiple documents at once."""
        url = f"{self.base_url}/collections/{collection_id}/batch/documents/delete"
        payload = {"document_ids": document_ids}
        response = requests.post(url, json=payload, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def get_collection_schema(self, collection_id: str) -> Dict[str, Any]:
        """Get the inferred schema of a collection."""
        url = f"{self.base_url}/collections/{collection_id}/query/schema"
        response = requests.get(url, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def export_collection(
        self,
        collection_id: str,
        format: str = "json",
        populate: Optional[List[str]] = None,
        **filters,
    ) -> bytes:
        """Export collection data to JSON or CSV."""
        url = f"{self.base_url}/collections/{collection_id}/export"

        # Build params
        from urllib.parse import urlencode

        params = {"format": format, **filters}
        query_parts = [urlencode(params)]

        if populate:
            for pop in populate:
                query_parts.append(f"populate={pop}")

        full_url = f"{url}?{'&'.join(query_parts)}"

        response = requests.get(full_url, headers=self.headers)
        if not response.ok:
            self._log_error(response, full_url)
        response.raise_for_status()
        return response.content

    def aggregate_documents(
        self, collection_id: str, field: str, operation: str = "count", **filters
    ) -> Dict[str, Any]:
        """Perform aggregation operations on document fields."""
        url = f"{self.base_url}/collections/{collection_id}/query/documents/aggregate"
        params = {"field": field, "operation": operation}
        if filters:
            params.update(filters)
        response = requests.get(url, params=params, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()

    def group_by_field(
        self,
        collection_id: str,
        field: str,
        count_field: Optional[str] = None,
        **filters,
    ) -> List[Dict[str, Any]]:
        """Group documents by a field and count occurrences."""
        url = f"{self.base_url}/collections/{collection_id}/query/documents/group-by"
        params = {"field": field}
        if count_field:
            params["count_field"] = count_field
        if filters:
            params.update(filters)

        response = requests.get(url, params=params, headers=self.headers)
        if not response.ok:
            self._log_error(response, url)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Example usage
    API_URL = "http://127.0.0.1:8000"
    API_KEY = (
        "hPBqCur2ljFNXM6yPSExDFj8cmACVAYxT61x_SVQ"  # Replace with your test API key
    )

    client = CollectionsClient(API_URL, API_KEY)

    # # Create some documents
    # doc1 = client.create_document("users", {"name": "John", "age": 30})
    # doc2 = client.create_document("users", {"name": "Jane", "age": 25})

    # List documents with relationships
    # Check what collections exist
    docs = client.list_documents(
        collection_id="posts", populate=["author"], **{"author.role__contains": "admin"}
    )
    print(f"Filtered by author.email__contains='jane': {len(docs)} posts")
    if docs:
        print(f"Sample: {docs[0]['title']} by {docs[0]['author']['name']}")
