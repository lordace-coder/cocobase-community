"""
Schema Migration API
Handles collection and field migrations: rename, add, delete fields, etc.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    Query,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access, get_current_user
from app.models.app_client import Project
from app.models.user import User
from app.models.collections import Collection, Document

router = APIRouter(
    prefix="/migrations",
    tags=["Schema Migrations"],
)


# ============================================
# SCHEMAS
# ============================================


class RenameCollectionRequest(BaseModel):
    """Request to rename a collection"""

    old_name: str = Field(..., description="Current collection name")
    new_name: str = Field(..., description="New collection name")


class RenameFieldRequest(BaseModel):
    """Request to rename a field in all documents"""

    collection: str = Field(..., description="Collection name or ID")
    old_field_name: str = Field(..., description="Current field name")
    new_field_name: str = Field(..., description="New field name")


class AddFieldRequest(BaseModel):
    """Request to add a field to all documents"""

    collection: str = Field(..., description="Collection name or ID")
    field_name: str = Field(..., description="Field name to add")
    default_value: Any = Field(None, description="Default value for the field")


class DeleteFieldRequest(BaseModel):
    """Request to delete a field from all documents"""

    collection: str = Field(..., description="Collection name or ID")
    field_name: str = Field(..., description="Field name to delete")


class ChangeFieldTypeRequest(BaseModel):
    """Request to change field type (with conversion)"""

    collection: str = Field(..., description="Collection name or ID")
    field_name: str = Field(..., description="Field name")
    target_type: str = Field(
        ..., description="Target type: string, number, boolean, array, object"
    )
    conversion_map: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional mapping for value conversions (e.g., {'yes': True, 'no': False})",
    )


class MergeFieldsRequest(BaseModel):
    """Request to merge multiple fields into one"""

    collection: str = Field(..., description="Collection name or ID")
    source_fields: List[str] = Field(..., description="Fields to merge")
    target_field: str = Field(..., description="Target field name")
    strategy: str = Field(
        "concat",
        description="Merge strategy: concat (string), sum (numbers), array (create array), first (first non-null)",
    )
    separator: Optional[str] = Field(" ", description="Separator for concat strategy")


class SplitFieldRequest(BaseModel):
    """Request to split a field into multiple fields"""

    collection: str = Field(..., description="Collection name or ID")
    source_field: str = Field(..., description="Field to split")
    target_fields: List[str] = Field(..., description="Target field names")
    separator: str = Field(" ", description="Separator to split by")


class MigrationResponse(BaseModel):
    """Response for migration operations"""

    success: bool
    message: str
    documents_affected: int
    execution_time_ms: int
    details: Optional[Dict[str, Any]] = None


# ============================================
# HELPER FUNCTIONS
# ============================================


def get_collection_by_name_or_id(
    collection: str, project_id: str, db: Session
) -> Collection:
    """Get collection by name or ID"""
    coll = (
        db.query(Collection)
        .filter(
            or_(Collection.id == collection, Collection.name == collection),
            Collection.project_id == project_id,
        )
        .first()
    )

    if not coll:
        raise HTTPException(404, f"Collection '{collection}' not found")

    return coll


def convert_value(value: Any, target_type: str, conversion_map: Dict = None) -> Any:
    """Convert value to target type"""
    if value is None:
        return None

    # Check conversion map first
    if conversion_map and value in conversion_map:
        return conversion_map[value]

    try:
        if target_type == "string":
            return str(value)
        elif target_type == "number":
            return float(value) if "." in str(value) else int(value)
        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ["true", "yes", "1", "y"]
            return bool(value)
        elif target_type == "array":
            if isinstance(value, list):
                return value
            return [value]
        elif target_type == "object":
            if isinstance(value, dict):
                return value
            return {"value": value}
        else:
            return value
    except Exception:
        return value  # Return original if conversion fails


# ============================================
# COLLECTION MIGRATIONS
# ============================================


@router.post("/rename-collection", response_model=MigrationResponse)
def rename_collection(
    payload: RenameCollectionRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Rename a collection.

    **Example:**
    ```json
    {
      "old_name": "users",
      "new_name": "customers"
    }
    ```

    **What it does:**
    - Renames the collection
    - All documents remain unchanged
    - Collection ID stays the same
    - Updates collection metadata
    """
    start_time = datetime.now()

    # Find collection by old name
    collection = (
        db.query(Collection)
        .filter(
            Collection.name == payload.old_name,
            Collection.project_id == project.id,
        )
        .first()
    )

    if not collection:
        raise HTTPException(404, f"Collection '{payload.old_name}' not found")

    # Check if new name already exists
    existing = (
        db.query(Collection)
        .filter(
            Collection.name == payload.new_name,
            Collection.project_id == project.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(400, f"Collection '{payload.new_name}' already exists")

    # Rename
    old_name = collection.name
    collection.name = payload.new_name

    db.add(collection)
    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Collection renamed from '{old_name}' to '{payload.new_name}'",
        documents_affected=0,
        execution_time_ms=execution_time,
        details={
            "collection_id": collection.id,
            "old_name": old_name,
            "new_name": payload.new_name,
        },
    )


# ============================================
# FIELD MIGRATIONS
# ============================================


@router.post("/rename-field", response_model=MigrationResponse)
def rename_field(
    payload: RenameFieldRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Rename a field in all documents of a collection.

    **Example:**
    ```json
    {
      "collection": "users",
      "old_field_name": "fullName",
      "new_field_name": "full_name"
    }
    ```

    **What it does:**
    - Renames the field in ALL documents
    - Preserves the field value
    - Removes the old field
    - Creates the new field with the old value

    **Before:**
    ```json
    {"id": "1", "fullName": "John Doe", "age": 30}
    ```

    **After:**
    ```json
    {"id": "1", "full_name": "John Doe", "age": 30}
    ```
    """
    start_time = datetime.now()

    # Get collection
    collection = get_collection_by_name_or_id(payload.collection, project.id, db)

    # Get all documents in collection
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()

    affected_count = 0

    for doc in documents:
        if not doc.data:
            continue

        # Check if old field exists
        if payload.old_field_name in doc.data:
            # Copy value to new field
            doc.data[payload.new_field_name] = doc.data[payload.old_field_name]

            # Delete old field
            del doc.data[payload.old_field_name]

            # Mark as modified (important for SQLAlchemy JSON tracking)
            from sqlalchemy.orm import attributes

            db.add(doc)
            attributes.flag_modified(doc, "data")
            affected_count += 1

    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Field '{payload.old_field_name}' renamed to '{payload.new_field_name}' in {affected_count} documents",
        documents_affected=affected_count,
        execution_time_ms=execution_time,
        details={
            "collection": collection.name,
            "old_field": payload.old_field_name,
            "new_field": payload.new_field_name,
        },
    )


@router.post("/add-field", response_model=MigrationResponse)
def add_field(
    payload: AddFieldRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Add a new field to all documents in a collection.

    **Example:**
    ```json
    {
      "collection": "users",
      "field_name": "status",
      "default_value": "active"
    }
    ```

    **What it does:**
    - Adds the field to ALL documents
    - Sets the default value
    - Skips documents that already have the field

    **Before:**
    ```json
    {"id": "1", "name": "John"}
    ```

    **After:**
    ```json
    {"id": "1", "name": "John", "status": "active"}
    ```
    """
    start_time = datetime.now()

    # Get collection
    collection = get_collection_by_name_or_id(payload.collection, project.id, db)

    # Get all documents
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()

    affected_count = 0

    for doc in documents:
        if not doc.data:
            doc.data = {}

        # Only add if field doesn't exist
        if payload.field_name not in doc.data:
            doc.data[payload.field_name] = payload.default_value
            db.add(doc)
            affected_count += 1

    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Field '{payload.field_name}' added to {affected_count} documents",
        documents_affected=affected_count,
        execution_time_ms=execution_time,
        details={
            "collection": collection.name,
            "field_name": payload.field_name,
            "default_value": payload.default_value,
        },
    )


@router.post("/delete-field", response_model=MigrationResponse)
def delete_field(
    payload: DeleteFieldRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Delete a field from all documents in a collection.

    **Example:**
    ```json
    {
      "collection": "users",
      "field_name": "legacy_id"
    }
    ```

    **What it does:**
    - Removes the field from ALL documents
    - Data is permanently deleted
    - ⚠️ This cannot be undone!

    **Before:**
    ```json
    {"id": "1", "name": "John", "legacy_id": "old123"}
    ```

    **After:**
    ```json
    {"id": "1", "name": "John"}
    ```
    """
    start_time = datetime.now()

    # Get collection
    collection = get_collection_by_name_or_id(payload.collection, project.id, db)

    # Get all documents
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()

    affected_count = 0

    for doc in documents:
        if not doc.data:
            continue

        # Remove field if exists
        if payload.field_name in doc.data:
            del doc.data[payload.field_name]
            db.add(doc)
            affected_count += 1

    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Field '{payload.field_name}' deleted from {affected_count} documents",
        documents_affected=affected_count,
        execution_time_ms=execution_time,
        details={
            "collection": collection.name,
            "field_name": payload.field_name,
        },
    )


@router.post("/change-field-type", response_model=MigrationResponse)
def change_field_type(
    payload: ChangeFieldTypeRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Change the type of a field in all documents.

    **Example:**
    ```json
    {
      "collection": "products",
      "field_name": "price",
      "target_type": "number"
    }
    ```

    **With conversion map:**
    ```json
    {
      "collection": "users",
      "field_name": "is_active",
      "target_type": "boolean",
      "conversion_map": {
        "yes": true,
        "no": false,
        "active": true,
        "inactive": false
      }
    }
    ```

    **Supported types:**
    - `string` - Convert to string
    - `number` - Convert to number (int or float)
    - `boolean` - Convert to boolean
    - `array` - Wrap in array if not already
    - `object` - Wrap in object if not already

    **Before:**
    ```json
    {"id": "1", "price": "99.99"}
    ```

    **After:**
    ```json
    {"id": "1", "price": 99.99}
    ```
    """
    start_time = datetime.now()

    # Validate target type
    valid_types = ["string", "number", "boolean", "array", "object"]
    if payload.target_type not in valid_types:
        raise HTTPException(
            400, f"Invalid target type. Must be one of: {', '.join(valid_types)}"
        )

    # Get collection
    collection = get_collection_by_name_or_id(payload.collection, project.id, db)

    # Get all documents
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()

    affected_count = 0
    conversion_errors = []

    for doc in documents:
        if not doc.data or payload.field_name not in doc.data:
            continue

        try:
            old_value = doc.data[payload.field_name]
            new_value = convert_value(
                old_value, payload.target_type, payload.conversion_map
            )

            if new_value != old_value:
                doc.data[payload.field_name] = new_value
                db.add(doc)
                affected_count += 1
        except Exception as e:
            conversion_errors.append(
                {
                    "document_id": doc.id,
                    "error": str(e),
                    "value": doc.data[payload.field_name],
                }
            )

    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Field '{payload.field_name}' type changed to '{payload.target_type}' in {affected_count} documents",
        documents_affected=affected_count,
        execution_time_ms=execution_time,
        details={
            "collection": collection.name,
            "field_name": payload.field_name,
            "target_type": payload.target_type,
            "conversion_errors": conversion_errors if conversion_errors else None,
        },
    )


@router.post("/merge-fields", response_model=MigrationResponse)
def merge_fields(
    payload: MergeFieldsRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Merge multiple fields into one field.

    **Example (concat strings):**
    ```json
    {
      "collection": "users",
      "source_fields": ["first_name", "last_name"],
      "target_field": "full_name",
      "strategy": "concat",
      "separator": " "
    }
    ```

    **Example (sum numbers):**
    ```json
    {
      "collection": "orders",
      "source_fields": ["subtotal", "tax", "shipping"],
      "target_field": "total",
      "strategy": "sum"
    }
    ```

    **Example (create array):**
    ```json
    {
      "collection": "products",
      "source_fields": ["tag1", "tag2", "tag3"],
      "target_field": "tags",
      "strategy": "array"
    }
    ```

    **Strategies:**
    - `concat` - Concatenate strings with separator
    - `sum` - Sum numbers
    - `array` - Create array from values
    - `first` - Use first non-null value

    **Before:**
    ```json
    {"id": "1", "first_name": "John", "last_name": "Doe"}
    ```

    **After:**
    ```json
    {"id": "1", "first_name": "John", "last_name": "Doe", "full_name": "John Doe"}
    ```
    """
    start_time = datetime.now()

    # Validate strategy
    valid_strategies = ["concat", "sum", "array", "first"]
    if payload.strategy not in valid_strategies:
        raise HTTPException(
            400, f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}"
        )

    # Get collection
    collection = get_collection_by_name_or_id(payload.collection, project.id, db)

    # Get all documents
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()

    affected_count = 0

    for doc in documents:
        if not doc.data:
            continue

        # Get values from source fields
        values = []
        for field in payload.source_fields:
            if field in doc.data and doc.data[field] is not None:
                values.append(doc.data[field])

        if not values:
            continue

        # Apply merge strategy
        try:
            if payload.strategy == "concat":
                merged_value = payload.separator.join(str(v) for v in values)
            elif payload.strategy == "sum":
                merged_value = sum(float(v) for v in values)
            elif payload.strategy == "array":
                merged_value = values
            elif payload.strategy == "first":
                merged_value = values[0]
            else:
                continue

            doc.data[payload.target_field] = merged_value
            db.add(doc)
            affected_count += 1
        except Exception:
            continue  # Skip documents with conversion errors

    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Fields {payload.source_fields} merged into '{payload.target_field}' in {affected_count} documents",
        documents_affected=affected_count,
        execution_time_ms=execution_time,
        details={
            "collection": collection.name,
            "source_fields": payload.source_fields,
            "target_field": payload.target_field,
            "strategy": payload.strategy,
        },
    )


@router.post("/split-field", response_model=MigrationResponse)
def split_field(
    payload: SplitFieldRequest,
    bg: BackgroundTasks,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
) -> MigrationResponse:
    """
    Split a field into multiple fields.

    **Example:**
    ```json
    {
      "collection": "users",
      "source_field": "full_name",
      "target_fields": ["first_name", "last_name"],
      "separator": " "
    }
    ```

    **What it does:**
    - Splits the source field by separator
    - Creates new fields with split values
    - Preserves the original field

    **Before:**
    ```json
    {"id": "1", "full_name": "John Doe"}
    ```

    **After:**
    ```json
    {
      "id": "1",
      "full_name": "John Doe",
      "first_name": "John",
      "last_name": "Doe"
    }
    ```

    **Note:** If split produces fewer values than target fields,
    remaining fields will be set to null.
    """
    start_time = datetime.now()

    # Get collection
    collection = get_collection_by_name_or_id(payload.collection, project.id, db)

    # Get all documents
    documents = db.query(Document).filter(Document.collection_id == collection.id).all()

    affected_count = 0

    for doc in documents:
        if not doc.data or payload.source_field not in doc.data:
            continue

        source_value = doc.data[payload.source_field]

        if not isinstance(source_value, str):
            continue

        # Split the value
        parts = source_value.split(payload.separator)

        # Assign to target fields
        for i, field_name in enumerate(payload.target_fields):
            if i < len(parts):
                doc.data[field_name] = parts[i]
            else:
                doc.data[field_name] = None

        db.add(doc)
        affected_count += 1

    db.commit()

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return MigrationResponse(
        success=True,
        message=f"Field '{payload.source_field}' split into {payload.target_fields} in {affected_count} documents",
        documents_affected=affected_count,
        execution_time_ms=execution_time,
        details={
            "collection": collection.name,
            "source_field": payload.source_field,
            "target_fields": payload.target_fields,
            "separator": payload.separator,
        },
    )


# ============================================
# UTILITY ENDPOINTS
# ============================================


@router.get("/{collection}/analyze-fields")
def analyze_collection_fields(
    collection: str,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Analyze fields in a collection to help plan migrations.

    Returns:
    - All unique field names
    - Field types (detected from sample)
    - Value distribution
    - Null counts
    - Sample values

    **Example:**
    ```bash
    GET /migrations/users/analyze-fields
    ```

    **Response:**
    ```json
    {
      "collection": "users",
      "total_documents": 1000,
      "fields": {
        "name": {
          "type": "string",
          "present_in": 980,
          "null_count": 20,
          "sample_values": ["John", "Jane", "Bob"]
        },
        "age": {
          "type": "number",
          "present_in": 950,
          "null_count": 50,
          "sample_values": [25, 30, 35]
        }
      }
    }
    ```
    """

    # Get collection
    coll = get_collection_by_name_or_id(collection, project.id, db)

    # Get all documents
    documents = db.query(Document).filter(Document.collection_id == coll.id).all()

    total_docs = len(documents)
    field_analysis = {}

    for doc in documents:
        if not doc.data:
            continue

        for field_name, value in doc.data.items():
            if field_name not in field_analysis:
                field_analysis[field_name] = {
                    "types": set(),
                    "present_count": 0,
                    "null_count": 0,
                    "sample_values": [],
                }

            field_analysis[field_name]["present_count"] += 1

            if value is None:
                field_analysis[field_name]["null_count"] += 1
            else:
                # Detect type
                value_type = type(value).__name__
                field_analysis[field_name]["types"].add(value_type)

                # Add sample (limit to 5)
                if len(field_analysis[field_name]["sample_values"]) < 5:
                    field_analysis[field_name]["sample_values"].append(value)

    # Format response
    formatted_fields = {}
    for field_name, analysis in field_analysis.items():
        formatted_fields[field_name] = {
            "types": list(analysis["types"]),
            "present_in": analysis["present_count"],
            "missing_in": total_docs - analysis["present_count"],
            "null_count": analysis["null_count"],
            "coverage_percentage": (
                round((analysis["present_count"] / total_docs) * 100, 2)
                if total_docs > 0
                else 0
            ),
            "sample_values": analysis["sample_values"],
        }

    return {
        "collection": coll.name,
        "collection_id": coll.id,
        "total_documents": total_docs,
        "unique_fields": len(formatted_fields),
        "fields": formatted_fields,
    }


@router.post("/{collection}/dry-run")
def dry_run_migration(
    collection: str,
    operation: str = Query(
        ..., description="Operation type: rename-field, add-field, delete-field, etc."
    ),
    params: Dict[str, Any] = None,
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Dry run a migration to see what would happen without making changes.

    **Example:**
    ```bash
    POST /migrations/users/dry-run?operation=rename-field
    {
      "old_field_name": "fullName",
      "new_field_name": "full_name"
    }
    ```

    Returns:
    - Number of documents that would be affected
    - Sample of changes
    - Potential issues
    """

    # Get collection
    coll = get_collection_by_name_or_id(collection, project.id, db)

    # Get sample documents
    sample_size = 10
    documents = (
        db.query(Document)
        .filter(Document.collection_id == coll.id)
        .limit(sample_size)
        .all()
    )

    affected_count = 0
    sample_changes = []

    if operation == "rename-field":
        old_name = params.get("old_field_name")
        new_name = params.get("new_field_name")

        for doc in documents:
            if doc.data and old_name in doc.data:
                affected_count += 1
                sample_changes.append(
                    {
                        "document_id": doc.id,
                        "before": {old_name: doc.data[old_name]},
                        "after": {new_name: doc.data[old_name]},
                    }
                )

    elif operation == "add-field":
        field_name = params.get("field_name")
        default_value = params.get("default_value")

        for doc in documents:
            if not doc.data or field_name not in doc.data:
                affected_count += 1
                sample_changes.append(
                    {
                        "document_id": doc.id,
                        "after": {field_name: default_value},
                    }
                )

    # Get total count
    total_affected = (
        db.query(func.count(Document.id))
        .filter(Document.collection_id == coll.id)
        .scalar()
    )

    return {
        "collection": coll.name,
        "operation": operation,
        "total_documents": total_affected,
        "estimated_affected": affected_count,
        "sample_changes": sample_changes,
        "warning": "This is a dry run. No changes were made.",
    }
