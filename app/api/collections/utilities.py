from collections import defaultdict
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy import cast, Integer, String, or_, and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.app_client import AppUser

from app.models.collections import Collection, Document

# ============================================
# ENHANCED COMPARISON OPERATORS - FIXED
# ============================================


def build_comparison_map():
    """Build comparison operators with proper JSON handling.

    NOTE: Columns passed to these lambdas are expected to be already cast to text via .astext
    """
    return {
        "lte": lambda col, val: cast(col, Integer) <= val,
        "gte": lambda col, val: cast(col, Integer) >= val,
        "lt": lambda col, val: cast(col, Integer) < val,
        "gt": lambda col, val: cast(col, Integer) > val,
        # col is already text (via .astext), so compare directly
        "eq": lambda col, val: col == str(val),
        "ne": lambda col, val: col != str(val),
        "contains": lambda col, val: col.ilike(f"%{val}%"),
        "startswith": lambda col, val: col.ilike(f"{val}%"),
        "endswith": lambda col, val: col.ilike(f"%{val}"),
        # For IN/NOTIN, split comma-separated values and compare as text
        "in": lambda col, val: col.in_([v.strip() for v in val.split(",")]),
        "notin": lambda col, val: ~col.in_([v.strip() for v in val.split(",")]),
        "isnull": lambda col, val: (
            col.is_(None) if val.lower() in ("true", "1") else col.isnot(None)
        ),
    }


comparison_map = build_comparison_map()


# ============================================
# HELPER FUNCTIONS - IMPROVED
# ============================================


def get_collection_by_id_or_name(
    collection_identifier: str, project_id: str, db: Session
) -> Collection:
    """
    Reusable function to get collection by ID or name.
    Optimized with single query using OR.
    """
    collection = (
        db.query(Collection)
        .filter(
            or_(
                Collection.id == collection_identifier,
                Collection.name == collection_identifier,
            ),
            Collection.project_id == project_id,
        )
        .first()
    )

    if not collection:
        # Create the collection (use identifier as the name) and persist it
        collection = Collection(name=collection_identifier, project_id=project_id)
        db.add(collection)
        try:
            db.commit()
            db.refresh(collection)
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create collection")

    return collection


def parse_filter_expression(field_expr: str, value: str, operator: str = "eq"):
    """
    Parse a single filter expression into a SQLAlchemy filter.

    FIXED ISSUES:
    - Better error handling
    - Debug logging
    - Type conversion for various operators
    - Always use .astext to cast JSONB to text to avoid JSON syntax errors

    Args:
        field_expr: Field name (e.g., "age", "name", "user_id", "userId")
        value: Filter value
        operator: Comparison operator (eq, gt, contains, etc.)

    Returns:
        SQLAlchemy filter expression or None
    """
    # CRITICAL FIX: Use .astext to convert JSONB to text IMMEDIATELY
    # This ensures all downstream operations treat it as text, not JSON
    json_col = Document.data[field_expr].astext
    comp_fn = comparison_map.get(operator)

    if not comp_fn:
        print(f"WARNING: Unknown operator '{operator}' for field '{field_expr}'")
        return None

    try:
        # Type conversion for numeric operators
        if operator in {"lte", "gte", "lt", "gt"}:
            try:
                typed_value = int(value)
            except ValueError:
                try:
                    typed_value = float(value)
                except ValueError:
                    print(
                        f"WARNING: Cannot convert '{value}' to number for {operator} operator"
                    )
                    return None
        else:
            typed_value = value

        filter_expr = comp_fn(json_col, typed_value)
        print(f"DEBUG: Created filter - {field_expr} {operator} {typed_value}")
        return filter_expr

    except (ValueError, TypeError) as e:
        print(f"ERROR: Filter parsing failed for {field_expr} {operator} {value}: {e}")
        return None


def build_query_filters(
    query_params: dict, base_query, reserved_params: set = None
) -> Any:
    """
    Build dynamic query filters from query parameters with advanced boolean logic.

    FIXED ISSUES:
    - Better operator detection (avoids false positives with underscores)
    - Proper handling of field names with underscores (user_id, first_name, etc.)
    - Debug logging for troubleshooting
    - More robust multi-field OR/AND parsing

    SYNTAX RULES:
    ============

    1. BASIC FILTERS (implicit AND):
       ?age_gte=18&status=active
       → (age >= 18) AND (status = 'active')

    2. OR CONDITIONS (same value for multiple fields):
       ?name__or__email_contains=john
       → (name ILIKE '%john%') OR (email ILIKE '%john%')

    3. AND CONDITIONS (same value for multiple fields):
       ?firstName__and__lastName=John
       → (firstName = 'John') AND (lastName = 'John')

    4. COMPLEX OR GROUPS (using [or] prefix):
       ?[or]age_gte=18&[or]role=admin
       → (age >= 18) OR (role = 'admin')

    5. MIXED AND/OR (grouping):
       ?age_gte=18&status=active&[or]role=admin&[or]isVip=true
       → (age >= 18) AND (status = 'active') AND ((role = 'admin') OR (isVip = true))

    6. MULTIPLE OR GROUPS (using [or:groupname]):
       ?[or:group1]age_gte=18&[or:group1]status=active&[or:group2]role=admin&[or:group2]isPremium=true
       → ((age >= 18) OR (status = 'active')) AND ((role = 'admin') OR (isPremium = true))

    OPERATORS:
    =========
    eq, ne, lt, gt, lte, gte, contains, startswith, endswith, in, notin, isnull

    EXAMPLES:
    ========
    # Find users with specific user_id (handles underscores correctly)
    ?user_id=901235c6-9564-4de0-bb40-0c5db80d4f26

    # Users over 18 OR admins
    ?[or]age_gte=18&[or]role=admin

    # Active users between 18-65
    ?status=active&age_gte=18&age_lte=65

    # Search in name or email
    ?name__or__email_contains=john

    # Premium users OR (active AND verified)
    ?[or]isPremium=true&status=active&isVerified=true

    # Complex: (age > 18 AND status = active) OR role = admin
    ?[or:a]age_gte=18&[or:a]status=active&[or:b]role=admin
    """
    if reserved_params is None:
        reserved_params = {"limit", "offset", "id", "sort", "order"}

    print(f"\n{'='*60}")
    print(f"DEBUG: Building filters from query params: {query_params}")
    print(f"{'='*60}\n")

    # Organize filters by type
    and_filters = []  # Default AND filters
    or_groups = {}  # OR groups by name

    for key, value in query_params.items():
        if key in reserved_params:
            continue

        print(f"DEBUG: Processing param: {key}={value}")

        # Extract OR group prefix: [or], [or:groupname]
        or_group = None
        actual_key = key

        if key.startswith("[or]"):
            # Simple OR: [or]age_gte=18
            actual_key = key[4:]  # Remove [or] prefix
            or_group = "__simple_or__"
            print(f"  → Detected simple OR filter")
        elif key.startswith("[or:") and "]" in key:
            # Named OR group: [or:group1]age_gte=18
            end_bracket = key.index("]")
            group_name = key[4:end_bracket]
            actual_key = key[end_bracket + 1 :]
            or_group = group_name
            print(f"  → Detected OR group: {group_name}")

        # Parse the actual filter
        # Handle multi-field OR: field1__or__field2_operator=value
        if "__or__" in actual_key:
            print(f"  → Multi-field OR detected")
            or_fields = []
            or_parts = actual_key.split("__or__")

            for field_with_op in or_parts:
                field, op = extract_field_and_operator(field_with_op)
                print(f"    → Field: {field}, Operator: {op}")

                filter_expr = parse_filter_expression(field, value, op)
                if filter_expr is not None:
                    or_fields.append(filter_expr)

            if or_fields:
                combined = or_(*or_fields)
                if or_group:
                    if or_group not in or_groups:
                        or_groups[or_group] = []
                    or_groups[or_group].append(combined)
                else:
                    and_filters.append(combined)

        # Handle multi-field AND: field1__and__field2_operator=value
        elif "__and__" in actual_key:
            print(f"  → Multi-field AND detected")
            and_fields = []
            and_parts = actual_key.split("__and__")

            for field_with_op in and_parts:
                field, op = extract_field_and_operator(field_with_op)
                print(f"    → Field: {field}, Operator: {op}")

                filter_expr = parse_filter_expression(field, value, op)
                if filter_expr is not None:
                    and_fields.append(filter_expr)

            if and_fields:
                combined = and_(*and_fields)
                if or_group:
                    if or_group not in or_groups:
                        or_groups[or_group] = []
                    or_groups[or_group].append(combined)
                else:
                    and_filters.append(combined)

        # Handle single field filters
        else:
            field, op = extract_field_and_operator(actual_key)
            print(f"  → Single field: {field}, Operator: {op}")

            filter_expr = parse_filter_expression(field, value, op)
            if filter_expr is not None:
                if or_group:
                    if or_group not in or_groups:
                        or_groups[or_group] = []
                    or_groups[or_group].append(filter_expr)
                else:
                    and_filters.append(filter_expr)

    # Build final filter
    final_filters = []

    # Add AND filters
    if and_filters:
        print(f"\nDEBUG: Adding {len(and_filters)} AND filters")
    final_filters.extend(and_filters)

    # Add OR groups (each group becomes an OR clause, groups are ANDed together)
    for group_name, group_filters in or_groups.items():
        if group_filters:
            print(
                f"DEBUG: Adding OR group '{group_name}' with {len(group_filters)} filters"
            )
            final_filters.append(or_(*group_filters))

    # Apply all filters with AND
    if final_filters:
        print(f"\nDEBUG: Applying {len(final_filters)} total filter groups\n")
        base_query = base_query.filter(and_(*final_filters))
    else:
        print("\nDEBUG: No filters applied\n")

    return base_query


def extract_field_and_operator(field_with_op: str) -> tuple[str, str]:
    """
    Extract field name and operator from a field expression.

    FIXED: Better detection to avoid false positives with underscores in field names.
    Supports both single underscore (_op) and double underscore (__op) patterns.

    Examples:
        "age_gte" → ("age", "gte")
        "email__contains" → ("email", "contains")  # Double underscore
        "user_id" → ("user_id", "eq")  # NOT ("user", "id")
        "first_name_contains" → ("first_name", "contains")
        "status" → ("status", "eq")

    Returns:
        Tuple of (field_name, operator)
    """
    if "_" not in field_with_op:
        return field_with_op, "eq"

    # First, try double underscore pattern (__operator)
    if "__" in field_with_op:
        parts = field_with_op.rsplit("__", 1)
        if len(parts) == 2 and parts[1] in comparison_map:
            return parts[0], parts[1]

    # Fall back to single underscore pattern (_operator)
    parts = field_with_op.rsplit("_", 1)

    if len(parts) == 2 and parts[1] in comparison_map:
        # Valid operator found
        return parts[0], parts[1]
    else:
        # No operator, treat entire string as field name
        return field_with_op, "eq"


class AutoRelationshipResolver:
    """
    Automatically resolve relationships for both Users and Collection Documents.
    """

    # Reserved collection names that map to actual models
    SYSTEM_COLLECTIONS = {
        "users": AppUser,
        "app_users": AppUser,
        "appusers": AppUser,
    }

    def __init__(self, db: Session):
        self.db = db
        self._collection_cache: Dict[str, Collection] = {}
        self._system_model_cache: Dict[str, Any] = {}

    def query_with_relationships(
        self,
        collection: Collection,
        query_params: dict,
        populate: Optional[List[str]] = None,
        select: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Enhanced query that supports relationships."""
        # Build base query with your existing filter logic
        base_query = self.db.query(Document).filter(
            Document.collection_id == collection.id
        )

        # Separate relationship filters from regular filters
        regular_filters = {}
        relationship_filters = {}

        # Reserved params that should not be treated as filters
        reserved_params = {"limit", "offset", "sort", "order", "populate", "select"}

        for key, value in query_params.items():
            if key in reserved_params:
                continue
            elif "." in key and not key.startswith("["):
                # Relationship filter: author.role=admin, user.email=test@test.com
                relationship_filters[key] = value
            else:
                regular_filters[key] = value

        # Apply regular filters using your existing logic
        if regular_filters:
            base_query = build_query_filters(regular_filters, base_query)

        # Apply relationship filters (new)
        if relationship_filters:
            base_query = self._apply_relationship_filters(
                base_query, relationship_filters, collection
            )

        # Optimize COUNT: only count on first page or if explicitly requested
        # Skip count with ?count=false for maximum speed
        count_param = query_params.get("count", "auto").lower()
        if count_param == "false":
            total = -1  # Skip count
        elif count_param == "true" or (count_param == "auto" and offset == 0):
            total = base_query.count()
        else:
            total = -1  # Unknown count for pagination

        # Apply sorting
        sort_field = query_params.get("sort", "created_at")
        sort_order = query_params.get("order", "desc")
        base_query = self._apply_sorting(base_query, sort_field, sort_order)

        # Apply pagination
        base_query = base_query.offset(offset).limit(limit)

        # Execute query
        documents = base_query.all()

        # Transform results with relationship population
        results = []
        for doc in documents:
            result = self._transform_document(
                doc, populate, select, collection.project_id
            )
            results.append(result)

        return {
            "data": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }

    def _is_system_collection(self, collection_name: str) -> bool:
        """Check if this is a system collection (like users)."""
        return collection_name.lower() in self.SYSTEM_COLLECTIONS

    def _get_system_model(self, collection_name: str):
        """Get the system model class for a collection name."""
        return self.SYSTEM_COLLECTIONS.get(collection_name.lower())

    def _apply_relationship_filters(
        self,
        query,
        filters: Dict[str, str],
        collection: Collection,
    ):
        """
        Apply filters on related collections or users with operator support.

        Examples:
        - author.role=admin (exact match)
        - author.email__contains=john (contains operator)
        - author.name__startswith=John (startswith operator)
        - category.name=tech (if category_id points to categories collection)
        - user.email=test@test.com (if user_id points to AppUser model)
        """
        print(f"\nDEBUG _apply_relationship_filters: Received {len(filters)} filters")
        for k, v in filters.items():
            print(f"  DEBUG: Filter key='{k}', value='{v}'")

        for path, value in filters.items():
            parts = path.split(".", 1)
            rel_field = parts[0]
            nested_field_with_op = parts[1]

            print(
                f"  DEBUG: rel_field='{rel_field}', nested_field_with_op='{nested_field_with_op}'"
            )

            # Extract operator from nested field (e.g., email__contains -> email, contains)
            nested_field, operator = extract_field_and_operator(nested_field_with_op)

            print(
                f"  DEBUG: Extracted nested_field='{nested_field}', operator='{operator}'"
            )

            # Detect relationship type
            id_field = f"{rel_field}_id"
            ids_field = f"{rel_field}_ids"

            # Determine target (system model or collection)
            target_collection_name = self._pluralize(rel_field)

            if self._is_system_collection(target_collection_name):
                # Filter by AppUser model
                query = self._apply_user_filter(
                    query, id_field, ids_field, nested_field, value, operator
                )
            else:
                # Filter by collection document
                query = self._apply_collection_filter(
                    query,
                    id_field,
                    ids_field,
                    target_collection_name,
                    nested_field,
                    value,
                    collection.project_id,
                    operator,
                )

        return query

    def _apply_user_filter(
        self,
        query,
        id_field: str,
        ids_field: str,
        nested_field: str,
        value: str,
        operator: str = "eq",
    ):
        """Apply filter on AppUser model with operator support."""
        # Build subquery for matching users
        user_field = getattr(AppUser, nested_field, None)

        if user_field is None:
            # Try JSONB data field if it exists
            if hasattr(AppUser, "data"):
                # Use parse_filter_expression for operator support
                json_col = AppUser.data[nested_field]
                comp_fn = comparison_map.get(operator)

                if comp_fn:
                    # Type conversion for numeric operators
                    if operator in {"lte", "gte", "lt", "gt"}:
                        try:
                            typed_value = int(value)
                        except ValueError:
                            try:
                                typed_value = float(value)
                            except ValueError:
                                typed_value = value
                    else:
                        typed_value = value

                    filter_expr = comp_fn(json_col, typed_value)
                    subquery = self.db.query(AppUser.id).filter(filter_expr)
                else:
                    # Fallback to exact match
                    subquery = self.db.query(AppUser.id).filter(
                        AppUser.data[nested_field].astext == str(value)
                    )
            else:
                print(f"WARNING: Field '{nested_field}' not found in AppUser model")
                return query
        else:
            # Direct column filter with operator support
            if operator == "eq":
                filter_cond = user_field == value
            elif operator == "ne":
                filter_cond = user_field != value
            elif operator == "contains":
                filter_cond = user_field.ilike(f"%{value}%")
            elif operator == "startswith":
                filter_cond = user_field.ilike(f"{value}%")
            elif operator == "endswith":
                filter_cond = user_field.ilike(f"%{value}")
            elif operator == "in":
                filter_cond = user_field.in_([v.strip() for v in value.split(",")])
            elif operator == "notin":
                filter_cond = ~user_field.in_([v.strip() for v in value.split(",")])
            else:
                # Fallback to exact match
                filter_cond = user_field == value

            subquery = self.db.query(AppUser.id).filter(filter_cond)

        # Apply to main query
        # FIX: Use .astext to cast JSONB to text for proper IN comparison
        # This ensures UUID strings are compared as text, not raw JSON
        query = query.filter(
            or_(
                Document.data[id_field].astext.in_(subquery),
                Document.data[ids_field].astext.in_(subquery),
            )
        )

        return query

    def _apply_collection_filter(
        self,
        query,
        id_field: str,
        ids_field: str,
        target_collection_name: str,
        nested_field: str,
        value: str,
        project_id: str,
        operator: str = "eq",
    ):
        """Apply filter on collection document with operator support."""
        target_collection = self._get_collection_by_name(
            target_collection_name, project_id
        )

        if not target_collection:
            print(f"WARNING: Collection '{target_collection_name}' not found")
            return query

        # Build filter expression with operator support
        json_col = Document.data[nested_field]
        comp_fn = comparison_map.get(operator)

        if comp_fn:
            # Type conversion for numeric operators
            if operator in {"lte", "gte", "lt", "gt"}:
                try:
                    typed_value = int(value)
                except ValueError:
                    try:
                        typed_value = float(value)
                    except ValueError:
                        typed_value = value
            else:
                typed_value = value

            filter_expr = comp_fn(json_col, typed_value)
        else:
            # Fallback to exact match
            filter_expr = json_col.astext == str(value)

        # Build subquery
        subquery = self.db.query(Document.id).filter(
            and_(
                Document.collection_id == target_collection.id,
                filter_expr,
            )
        )

        # Apply to main query
        # FIX: Use .astext to cast JSONB to text for proper IN comparison
        # This ensures UUID strings are compared as text, not raw JSON
        query = query.filter(
            or_(
                Document.data[id_field].astext.in_(subquery),
                # For array fields, check if any ID in the array matches subquery results
                Document.data[ids_field].astext.in_(subquery),
            )
        )

        return query

    def _transform_document(
        self,
        doc: Document,
        populate: Optional[List[str]],
        select: Optional[List[str]],
        project_id: str,
    ) -> Dict[str, Any]:
        """Transform document with relationship population."""
        result = {
            "id": doc.id,
            "data": doc.data or {},
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }

        # Populate relationships
        if populate:
            result = self._populate_relationships(result, populate, project_id)

        # Select specific fields
        if select:
            result = self._select_fields(result, select)

        return result

    def _populate_relationships(
        self, doc: Dict[str, Any], populate: List[str], project_id: str
    ) -> Dict[str, Any]:
        """
        Auto-populate relationships (users or collections).

        Supports explicit source specification with syntax:
        - 'user' → auto-detect (default behavior)
        - 'user:appuser' → force fetch from AppUser
        - 'user:posts' → force fetch from 'posts' collection (specific collection)
        - 'user:members' → force fetch from 'members' collection
        """
        populate_map = self._parse_populate_paths(populate)

        for field_path, nested_populates in populate_map.items():
            # Extract force_source if specified (e.g., "user:appuser" or "user:posts")
            force_source = None
            target_collection = None
            actual_field = field_path

            if ":" in field_path and not "." in field_path:
                parts = field_path.split(":", 1)
                actual_field = parts[0]
                source_spec = parts[1].lower()

                if source_spec == "appuser":
                    force_source = "appuser"
                else:
                    # It's a specific collection name
                    force_source = "collection"
                    target_collection = source_spec

            # Handle nested paths
            if "." in actual_field:
                parts = actual_field.split(".", 1)
                parent_field = parts[0]
                nested_path = parts[1]

                # Populate parent first
                if parent_field not in populate_map or not doc.get(parent_field):
                    doc = self._populate_single_field(
                        doc,
                        parent_field,
                        project_id,
                        [],
                        force_source,
                        target_collection,
                    )

                # Then populate nested
                if parent_field in doc:
                    if isinstance(doc[parent_field], list):
                        doc[parent_field] = [
                            self._populate_relationships(
                                item, [nested_path], project_id
                            )
                            for item in doc[parent_field]
                            if isinstance(item, dict)
                        ]
                    elif isinstance(doc[parent_field], dict):
                        doc[parent_field] = self._populate_relationships(
                            doc[parent_field], [nested_path], project_id
                        )
            else:
                # Simple field population
                doc = self._populate_single_field(
                    doc,
                    actual_field,
                    project_id,
                    nested_populates,
                    force_source,
                    target_collection,
                )

        return doc

    def _populate_single_field(
        self,
        doc: Dict[str, Any],
        field_name: str,
        project_id: str,
        nested_populates: List[str],
        force_source: Optional[str] = None,
        target_collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Populate a single relationship field.

        Detects if it should fetch from AppUser or Collection.

        Args:
            force_source: Optional explicit source type ('appuser' or 'collection')
                         Overrides automatic detection based on field name.
            target_collection: Optional specific collection name to use instead of auto-pluralization
        """
        id_field = f"{field_name}_id"
        ids_field = f"{field_name}_ids"

        # Access data from the data field
        doc_data = doc.get("data", {})

        # Determine target collection name
        if target_collection:
            # Use explicit collection name provided
            target_name = target_collection
        else:
            # Auto-pluralize field name
            target_name = self._pluralize(field_name)

        # Check if source is explicitly specified
        if force_source == "appuser":
            is_user_relation = True
        elif force_source == "collection":
            is_user_relation = False
        else:
            # Auto-detect based on naming
            is_user_relation = self._is_system_collection(target_name)

        # Determine which field to check (try field_id first, then field itself)
        field_to_check = None
        field_value = None

        # Case 1a: Check for field_id (e.g., author_id)
        if id_field in doc_data and doc_data[id_field]:
            field_to_check = id_field
            field_value = doc_data[id_field]
        # Case 1b: Check for field itself (e.g., author)
        elif field_name in doc_data and doc_data[field_name]:
            # Check if it's a single ID (string) or array
            if isinstance(doc_data[field_name], list):
                field_to_check = "array"
                field_value = doc_data[field_name]
            else:
                field_to_check = field_name
                field_value = doc_data[field_name]
        # Case 2: Check for field_ids (e.g., author_ids)
        elif ids_field in doc_data and doc_data[ids_field]:
            field_to_check = "array"
            field_value = doc_data[ids_field]

        # Fetch and populate the relationship
        if field_to_check and field_value:
            if field_to_check == "array":
                # Array of IDs
                if isinstance(field_value, list):
                    if is_user_relation:
                        related = self._fetch_users(
                            field_value, nested_populates, project_id
                        )
                    else:
                        related = self._fetch_related_documents(
                            target_name, project_id, field_value, nested_populates
                        )
                    # Add populated data inside the data field with  suffix
                    doc["data"][f"{field_name}"] = related
            else:
                # Single ID
                if is_user_relation:
                    related = self._fetch_user(
                        field_value, nested_populates, project_id
                    )
                else:
                    related = self._fetch_related_document(
                        target_name, project_id, field_value, nested_populates
                    )
                if related:
                    # Add populated data inside the data field with  suffix
                    doc["data"][f"{field_name}"] = related
        else:
            # Case 3: Reverse relationship (no direct field found)
            if is_user_relation:
                # Don't support reverse user relationships
                pass
            else:
                singular = self._singularize(field_name)
                foreign_key = f"{singular}_id"
                related = self._fetch_reverse_related(
                    field_name, project_id, foreign_key, doc["id"], nested_populates
                )
                if related:
                    # Add populated data inside the data field with  suffix
                    doc["data"][f"{field_name}"] = related

        return doc

    def _fetch_user(
        self, user_id: str, nested_populates: List[str], project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single AppUser."""
        user = self.db.query(AppUser).filter(AppUser.id == user_id).first()

        if not user:
            return None

        # Build user data (exclude sensitive fields)
        result = {
            "id": user.id,
            "email": user.email,
            "data": user.data or {},
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

        # Add roles if exists
        if hasattr(user, "roles") and user.roles:
            result["roles"] = user.roles

        # DON'T include password from data!
        if "password" in result["data"]:
            result["data"].pop("password")

        # Recursively populate nested (if user has relationships)
        if nested_populates:
            result = self._populate_relationships(result, nested_populates, project_id)

        return result

    def _fetch_users(
        self, user_ids: List[str], nested_populates: List[str], project_id: str
    ) -> List[Dict[str, Any]]:
        """Fetch multiple AppUsers (batch)."""
        users = self.db.query(AppUser).filter(AppUser.id.in_(user_ids)).all()

        results = []
        for user in users:
            result = {
                "id": user.id,
                "email": user.email,
                "data": user.data or {},
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }

            if hasattr(user, "roles") and user.roles:
                result["roles"] = user.roles

            # DON'T include password from data!
            if "password" in result["data"]:
                result["data"].pop("password")

            if nested_populates:
                result = self._populate_relationships(
                    result, nested_populates, project_id
                )

            results.append(result)

        return results

    def _fetch_related_document(
        self,
        collection_name: str,
        project_id: str,
        doc_id: str,
        nested_populates: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single related document from collection."""
        collection = self._get_collection_by_name(collection_name, project_id)
        if not collection:
            return None

        doc = (
            self.db.query(Document)
            .filter(Document.collection_id == collection.id, Document.id == doc_id)
            .first()
        )

        if not doc:
            return None

        result = {
            "id": doc.id,
            "data": doc.data or {},
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }

        if nested_populates:
            result = self._populate_relationships(result, nested_populates, project_id)

        return result

    def _fetch_related_documents(
        self,
        collection_name: str,
        project_id: str,
        doc_ids: List[str],
        nested_populates: List[str],
    ) -> List[Dict[str, Any]]:
        """Fetch multiple related documents (batch)."""
        collection = self._get_collection_by_name(collection_name, project_id)
        if not collection:
            return []

        docs = (
            self.db.query(Document)
            .filter(Document.collection_id == collection.id, Document.id.in_(doc_ids))
            .all()
        )

        results = []
        for doc in docs:
            result = {
                "id": doc.id,
                "data": doc.data or {},
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            if nested_populates:
                result = self._populate_relationships(
                    result, nested_populates, project_id
                )
            results.append(result)

        return results

    def _fetch_reverse_related(
        self,
        collection_name: str,
        project_id: str,
        foreign_key: str,
        reference_id: str,
        nested_populates: List[str],
    ) -> List[Dict[str, Any]]:
        """Fetch documents that reference this document."""
        collection = self._get_collection_by_name(collection_name, project_id)
        if not collection:
            return []

        docs = (
            self.db.query(Document)
            .filter(
                Document.collection_id == collection.id,
                Document.data[foreign_key].astext == reference_id,
            )
            .all()
        )

        results = []
        for doc in docs:
            result = {
                "id": doc.id,
                "data": doc.data or {},
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            if nested_populates:
                result = self._populate_relationships(
                    result, nested_populates, project_id
                )
            results.append(result)

        return results

    # ... (keep all other helper methods from previous implementation)

    def _parse_populate_paths(self, populate: List[str]) -> Dict[str, List[str]]:
        """Parse populate paths."""
        result = defaultdict(list)

        for path in populate:
            if "." in path:
                parts = path.split(".", 1)
                parent = parts[0]
                nested = parts[1]
                result[parent].append(nested)
            else:
                if path not in result:
                    result[path] = []

        return dict(result)

    def _select_fields(self, doc: Dict[str, Any], select: List[str]) -> Dict[str, Any]:
        """Select only specified fields."""
        result = {"id": doc["id"]}

        for field_path in select:
            parts = field_path.split(".")
            value = doc
            valid = True

            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    valid = False
                    break

            if valid:
                self._set_nested_value(result, parts, value)

        return result

    def _set_nested_value(self, obj: Dict, path: List[str], value: Any):
        """Set nested value."""
        for key in path[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]
        obj[path[-1]] = value

    def _apply_sorting(self, query, sort_field: str, sort_order: str):
        """Apply sorting."""
        if sort_field in ["created_at", "updated_at", "id"]:
            col = getattr(Document, sort_field)
            return query.order_by(col.desc() if sort_order == "desc" else col.asc())
        else:
            if sort_order == "desc":
                return query.order_by(Document.data[sort_field].desc())
            else:
                return query.order_by(Document.data[sort_field].asc())

    def _get_collection_by_name(
        self, name: str, project_id: str
    ) -> Optional[Collection]:
        """Get collection with caching - tries both singular and plural forms."""
        cache_key = f"{project_id}:{name}"

        if cache_key in self._collection_cache:
            return self._collection_cache[cache_key]

        # Try exact name first
        collection = (
            self.db.query(Collection)
            .filter(Collection.name == name, Collection.project_id == project_id)
            .first()
        )

        # If not found, try singular form (remove 's')
        if not collection and name.endswith("s"):
            singular_name = self._singularize(name)
            collection = (
                self.db.query(Collection)
                .filter(
                    Collection.name == singular_name,
                    Collection.project_id == project_id,
                )
                .first()
            )
            print(
                f"DEBUG: Tried singular form '{singular_name}' - {'Found' if collection else 'Not found'}"
            )

        # If still not found, try plural form (add 's')
        if not collection and not name.endswith("s"):
            plural_name = self._pluralize(name)
            collection = (
                self.db.query(Collection)
                .filter(
                    Collection.name == plural_name, Collection.project_id == project_id
                )
                .first()
            )
            print(
                f"DEBUG: Tried plural form '{plural_name}' - {'Found' if collection else 'Not found'}"
            )

        if collection:
            self._collection_cache[cache_key] = collection
        else:
            print(f"WARNING: Collection '{name}' not found in project {project_id}")

        return collection

    def _pluralize(self, word: str) -> str:
        """Simple pluralization."""
        if word.endswith("y"):
            return word[:-1] + "ies"
        elif word.endswith("s"):
            return word + "es"
        else:
            return word + "s"

    def _singularize(self, word: str) -> str:
        """Simple singularization."""
        if word.endswith("ies"):
            return word[:-3] + "y"
        elif word.endswith("ses"):
            return word[:-2]
        elif word.endswith("s"):
            return word[:-1]
        return word
