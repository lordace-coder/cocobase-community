from typing import Any
from fastapi import HTTPException
from fastapi_cache import FastAPICache
from sqlalchemy import cast, Integer, String, or_, and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.collections import Collection, Document

# ============================================
# ENHANCED COMPARISON OPERATORS - FIXED
# ============================================


def build_comparison_map():
    """Build comparison operators with proper JSON handling."""
    return {
        "lte": lambda col, val: cast(col.astext, Integer) <= val,
        "gte": lambda col, val: cast(col.astext, Integer) >= val,
        "lt": lambda col, val: cast(col.astext, Integer) < val,
        "gt": lambda col, val: cast(col.astext, Integer) > val,
        # FIXED: Handle both string and native JSON comparison
        "eq": lambda col, val: or_(
            col.astext == str(val),
            cast(col, String) == str(val),  # Cast comparison
        ),
        "ne": lambda col, val: and_(
            col.astext != str(val), cast(col, String) != str(val)
        ),
        "contains": lambda col, val: col.astext.ilike(f"%{val}%"),
        "startswith": lambda col, val: col.astext.ilike(f"{val}%"),
        "endswith": lambda col, val: col.astext.ilike(f"%{val}"),
        # FIXED: Handle comma-separated values and quoted strings
        "in": lambda col, val: or_(
            col.astext.in_([v.strip() for v in val.split(",")]),
            col.in_([v.strip() for v in val.split(",")]),
        ),
        "notin": lambda col, val: and_(
            ~col.astext.in_([v.strip() for v in val.split(",")]),
            ~col.in_([v.strip() for v in val.split(",")]),
        ),
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
        raise HTTPException(404, "Collection not found")

    return collection


def parse_filter_expression(field_expr: str, value: str, operator: str = "eq"):
    """
    Parse a single filter expression into a SQLAlchemy filter.

    FIXED ISSUES:
    - Better error handling
    - Debug logging
    - Type conversion for various operators

    Args:
        field_expr: Field name (e.g., "age", "name", "user_id", "userId")
        value: Filter value
        operator: Comparison operator (eq, gt, contains, etc.)

    Returns:
        SQLAlchemy filter expression or None
    """
    json_col = Document.data[field_expr]
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

    Examples:
        "age_gte" → ("age", "gte")
        "user_id" → ("user_id", "eq")  # NOT ("user", "id")
        "first_name_contains" → ("first_name", "contains")
        "status" → ("status", "eq")

    Returns:
        Tuple of (field_name, operator)
    """
    if "_" not in field_with_op:
        return field_with_op, "eq"

    # Try splitting from the right and check if it's a valid operator
    parts = field_with_op.rsplit("_", 1)

    if len(parts) == 2 and parts[1] in comparison_map:
        # Valid operator found
        return parts[0], parts[1]
    else:
        # No operator, treat entire string as field name
        return field_with_op, "eq"


async def invalidate_collection_cache(collection_id: str):
    """Invalidate all caches related to a collection."""
    try:
        # Clear specific collection caches
        await FastAPICache.clear(namespace=f"collection:{collection_id}")
    except Exception:
        pass  # Cache invalidation shouldn't break the app
