"""
Helper for resolving relationships in AppUser queries.
Extracted from AutoRelationshipResolver to work specifically with AppUsers.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.app_client import AppUser
from app.models.collections import Collection, Document


class UserRelationshipHelper:
    """
    Helper class for populating relationships in AppUser data.
    Works with both AppUser-to-AppUser and AppUser-to-Document relationships.
    """

    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id

    def populate_user_relationships(
        self, users_data: List[Dict[str, Any]], populate: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Populate relationships for a list of user dictionaries.
        OPTIMIZED: Uses batch queries to avoid N+1 problem.

        Args:
            users_data: List of user dictionaries with 'data' field
            populate: List of field names to populate (e.g., ['referred_by', 'followers'])

        Returns:
            The same list with populated relationships added as {field}
        """
        if not users_data or not populate:
            return users_data

        # Collect ALL IDs for each relationship field (BATCH OPTIMIZATION)
        for rel_path in populate:
            all_ids_to_fetch = []

            # Collect all IDs that need to be fetched for this relationship
            for user_dict in users_data:
                if rel_path in user_dict.get("data", {}):
                    related_value = user_dict["data"][rel_path]
                    if related_value:
                        if isinstance(related_value, list):
                            all_ids_to_fetch.extend(
                                [rid for rid in related_value if rid]
                            )
                        else:
                            all_ids_to_fetch.append(related_value)

            if not all_ids_to_fetch:
                continue

            # BATCH FETCH: Get all related entities in ONE query
            related_map = self._batch_fetch_relations(all_ids_to_fetch)

            # Now populate each user with the fetched data
            for user_dict in users_data:
                if rel_path in user_dict.get("data", {}):
                    related_value = user_dict["data"][rel_path]
                    if related_value:
                        if isinstance(related_value, list):
                            # Handle array of IDs
                            populated_items = [
                                related_map[rid]
                                for rid in related_value
                                if rid and rid in related_map
                            ]
                            if populated_items:

                                user_dict["data"][f"{rel_path}"] = populated_items
                        else:
                            # Single relationship
                            if related_value in related_map:
                                # Add populated relationship inside data with  suffix
                                user_dict["data"][f"{rel_path}"] = related_map[
                                    related_value
                                ]

        return users_data

    def _batch_fetch_relations(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        OPTIMIZED: Batch fetch all related entities in ONE query.
        Returns a map of {id: serialized_entity}
        """
        # Remove duplicates
        unique_ids = list(set(ids))

        # Batch fetch from AppUsers
        related_users = (
            self.db.query(AppUser)
            .filter(
                AppUser.id.in_(unique_ids),
                AppUser.client_id == self.project_id,
            )
            .all()
        )

        # Build map
        result_map = {user.id: self._serialize_user(user) for user in related_users}

        # Find missing IDs and fetch from Documents if needed
        found_ids = set(result_map.keys())
        missing_ids = [uid for uid in unique_ids if uid not in found_ids]

        if missing_ids:
            related_docs = (
                self.db.query(Document)
                .join(Collection)
                .filter(
                    Document.id.in_(missing_ids),
                    Collection.project_id == self.project_id,
                )
                .all()
            )

            for doc in related_docs:
                result_map[doc.id] = self._serialize_document(doc)

        return result_map

    def _fetch_single_relation(self, related_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single related entity (AppUser or Document).
        Tries AppUser first, then falls back to Documents.
        """
        # Try to fetch from AppUsers first
        related_user = (
            self.db.query(AppUser)
            .filter(
                AppUser.id == related_id,
                AppUser.client_id == self.project_id,
            )
            .first()
        )

        if related_user:
            return self._serialize_user(related_user)

        # Fallback: Try to fetch from collection documents
        related_doc = (
            self.db.query(Document)
            .join(Collection)
            .filter(
                Document.id == related_id,
                Collection.project_id == self.project_id,
            )
            .first()
        )

        if related_doc:
            return self._serialize_document(related_doc)

        return None

    def _fetch_multiple_relations(self, related_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple related entities (AppUsers or Documents).
        Tries to fetch all from AppUsers first, then fills in missing ones from Documents.
        """
        populated_items = []

        # Batch fetch from AppUsers
        related_users = (
            self.db.query(AppUser)
            .filter(
                AppUser.id.in_(related_ids),
                AppUser.client_id == self.project_id,
            )
            .all()
        )

        # Create a set of found user IDs
        found_user_ids = {user.id for user in related_users}

        # Add all found users
        for user in related_users:
            populated_items.append(self._serialize_user(user))

        # Find missing IDs
        missing_ids = [rid for rid in related_ids if rid not in found_user_ids]

        # Batch fetch missing IDs from Documents
        if missing_ids:
            related_docs = (
                self.db.query(Document)
                .join(Collection)
                .filter(
                    Document.id.in_(missing_ids),
                    Collection.project_id == self.project_id,
                )
                .all()
            )

            for doc in related_docs:
                populated_items.append(self._serialize_document(doc))

        return populated_items

    def _serialize_user(self, user: AppUser) -> Dict[str, Any]:
        """Convert AppUser to dictionary (exclude sensitive fields)."""
        result = {
            "id": user.id,
            "email": user.email,
            "data": user.data or {},
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

        # Add roles if exists
        if hasattr(user, "roles") and user.roles:
            result["roles"] = user.roles

        return result

    def _serialize_document(self, doc: Document) -> Dict[str, Any]:
        """Convert Document to dictionary."""
        return {
            "id": doc.id,
            "data": doc.data or {},
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
