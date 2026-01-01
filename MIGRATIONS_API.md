# Schema Migrations API

The Migrations API enables dynamic schema evolution for collections without downtime. Modify field structures, rename fields, change types, and merge or split fields across all documents in a collection.

## Base Path

```
POST /migrations/{endpoint}
GET /migrations/{collection}/{endpoint}
```

**Query Parameters (all endpoints):**
- `project_id` (required, string) - The project ID for authorization

**Authentication:**
- Requires `project` dependency validation through `require_dashboard_access`

---

## Collection Migrations

### Rename Collection

**Route:** `POST /migrations/rename-collection`

**Purpose:** Rename a collection while preserving all documents and metadata.

**Request Body:**
```json
{
  "old_name": "string - Current collection name",
  "new_name": "string - New collection name"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Collection renamed from 'old_name' to 'new_name'",
  "documents_affected": 0,
  "execution_time_ms": integer,
  "details": {
    "collection_id": "string - UUID of collection",
    "old_name": "string",
    "new_name": "string"
  }
}
```

**How It Works:**
1. Locates collection by `old_name`
2. Validates `new_name` doesn't already exist in project
3. Updates collection metadata
4. Returns collection ID, old name, new name
5. All documents remain unchanged; collection ID persists

**Errors:**
- `404` - Collection not found
- `400` - New collection name already exists

---

## Field Migrations

All field migrations operate on the `data` JSONB column. The system modifies individual field keys and persists changes atomically per document.

### Rename Field

**Route:** `POST /migrations/rename-field`

**Purpose:** Rename a field across all documents in a collection.

**Request Body:**
```json
{
  "collection": "string - Collection name or ID",
  "old_field_name": "string - Current field name",
  "new_field_name": "string - New field name"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Field 'old_field_name' renamed to 'new_field_name' in N documents",
  "documents_affected": integer,
  "execution_time_ms": integer,
  "details": {
    "collection": "string - Collection name",
    "old_field": "string",
    "new_field": "string"
  }
}
```

**How It Works:**
1. Resolves collection by name or ID
2. Iterates all documents in collection
3. For each document containing `old_field_name`:
   - Copies value to `new_field_name`
   - Deletes `old_field_name`
   - Flags document's `data` column as modified (SQLAlchemy JSON tracking)
   - Increments affected count
4. Commits all changes in single transaction
5. Returns count of documents updated

**Key Implementation Detail:**
- Uses `flag_modified(doc, "data")` to ensure SQLAlchemy detects JSONB mutations
- In-place dictionary modification (`doc.data[key] = value`) requires explicit change tracking

---

### Add Field

**Route:** `POST /migrations/add-field`

**Purpose:** Add a new field with default value to all documents in a collection.

**Request Body:**
```json
{
  "collection": "string - Collection name or ID",
  "field_name": "string - Field name to add",
  "default_value": "any - Default value (can be null)"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Field 'field_name' added to N documents",
  "documents_affected": integer,
  "execution_time_ms": integer,
  "details": {
    "collection": "string - Collection name",
    "field_name": "string",
    "default_value": "any"
  }
}
```

**How It Works:**
1. Resolves collection by name or ID
2. Iterates all documents in collection
3. For each document missing `field_name`:
   - Initializes `doc.data` to `{}` if null
   - Adds field with `default_value`
   - Increments affected count
4. Skips documents that already have the field (idempotent)
5. Commits transaction

**Behavior:**
- Non-destructive: Only adds to documents lacking the field
- Safe to rerun: Existing fields untouched
- `default_value` can be any type (number, string, array, object, null)

---

### Delete Field

**Route:** `POST /migrations/delete-field`

**Purpose:** Remove a field from all documents in a collection (permanent deletion).

**Request Body:**
```json
{
  "collection": "string - Collection name or ID",
  "field_name": "string - Field name to delete"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Field 'field_name' deleted from N documents",
  "documents_affected": integer,
  "execution_time_ms": integer,
  "details": {
    "collection": "string - Collection name",
    "field_name": "string"
  }
}
```

**How It Works:**
1. Resolves collection by name or ID
2. Iterates all documents in collection
3. For each document containing `field_name`:
   - Removes field from JSONB object
   - Increments affected count
4. Skips documents without the field
5. Commits transaction

**⚠️ Permanent:** This operation cannot be undone. The data is permanently deleted from the database.

---

### Change Field Type

**Route:** `POST /migrations/change-field-type`

**Purpose:** Convert field values to a different type, with optional custom conversion mapping.

**Request Body:**
```json
{
  "collection": "string - Collection name or ID",
  "field_name": "string - Field to convert",
  "target_type": "string - Target type: string, number, boolean, array, object",
  "conversion_map": "object|null - Optional mapping {'old_value': new_value}"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Field 'field_name' type changed to 'target_type' in N documents",
  "documents_affected": integer,
  "execution_time_ms": integer,
  "details": {
    "collection": "string - Collection name",
    "field_name": "string",
    "target_type": "string",
    "conversion_errors": [
      {
        "document_id": "string - UUID",
        "error": "string - Error message",
        "value": "any - Original value that failed"
      }
    ]
  }
}
```

**Supported Target Types:**

| Type | Behavior | Example |
|------|----------|---------|
| `string` | Converts value to string | `123` → `"123"` |
| `number` | Converts to int or float | `"99.99"` → `99.99` |
| `boolean` | Parses boolean values | `"true"` / `"yes"` / `"1"` → `true` |
| `array` | Wraps value in array if not already | `"value"` → `["value"]` |
| `object` | Wraps value in object if not already | `"value"` → `{"value": "value"}` |

**How It Works:**
1. Validates `target_type` against supported types
2. Resolves collection by name or ID
3. Iterates all documents in collection
4. For each document with `field_name`:
   - Checks `conversion_map` first for custom mapping
   - Falls back to default type conversion
   - If conversion succeeds and value changed:
     - Updates field
     - Increments affected count
   - If conversion fails:
     - Logs error with document ID and value
     - Continues to next document
5. Commits all successful conversions
6. Returns list of conversion errors (if any) in response

**Boolean Conversion:**
- Recognizes `true`, `yes`, `1`, `y` (case-insensitive) as `true`
- All other values convert to `false`

**Error Handling:**
- Gracefully skips documents where conversion fails
- Returns error details so you can investigate specific failures
- Does not rollback successful conversions for failed documents

---

### Merge Fields

**Route:** `POST /migrations/merge-fields`

**Purpose:** Combine multiple fields into a single field using various strategies.

**Request Body:**
```json
{
  "collection": "string - Collection name or ID",
  "source_fields": ["string", ...],
  "target_field": "string - Target field name",
  "strategy": "string - Strategy: concat, sum, array, first",
  "separator": "string - Separator for concat strategy (default: ' ')"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Fields [...] merged into 'target_field' in N documents",
  "documents_affected": integer,
  "execution_time_ms": integer,
  "details": {
    "collection": "string - Collection name",
    "source_fields": ["string", ...],
    "target_field": "string",
    "strategy": "string"
  }
}
```

**Merge Strategies:**

| Strategy | Behavior | Example |
|----------|----------|---------|
| `concat` | Join strings with separator | `["John", "Doe"]` → `"John Doe"` |
| `sum` | Sum numeric values | `[10, 20, 5]` → `35` |
| `array` | Create array from non-null values | `["a", "b", "c"]` → `["a", "b", "c"]` |
| `first` | Use first non-null value | `[null, "value", "other"]` → `"value"` |

**How It Works:**
1. Validates `strategy` against supported strategies
2. Resolves collection by name or ID
3. Iterates all documents in collection
4. For each document:
   - Collects non-null values from `source_fields`
   - If no values found: skips document
   - Applies merge strategy:
     - **concat**: joins with separator
     - **sum**: numeric addition
     - **array**: creates array
     - **first**: selects first value
   - Sets `target_field` to merged value
   - Increments affected count
5. Skips documents with conversion errors
6. Commits transaction

**Behavior Notes:**
- **Null handling**: Non-null values only (nulls filtered before merging)
- **Empty results**: Documents with no matching values are skipped
- **Target field**: Created if doesn't exist; overwritten if exists
- **Source fields**: Original fields remain unchanged

---

### Split Field

**Route:** `POST /migrations/split-field`

**Purpose:** Split a single field into multiple fields using a separator.

**Request Body:**
```json
{
  "collection": "string - Collection name or ID",
  "source_field": "string - Field to split",
  "target_fields": ["string", ...],
  "separator": "string - Separator to split by (default: ' ')"
}
```

**Response:**
```json
{
  "success": boolean,
  "message": "Field 'source_field' split into [...] in N documents",
  "documents_affected": integer,
  "execution_time_ms": integer,
  "details": {
    "collection": "string - Collection name",
    "source_field": "string",
    "target_fields": ["string", ...],
    "separator": "string"
  }
}
```

**How It Works:**
1. Resolves collection by name or ID
2. Iterates all documents in collection
3. For each document containing `source_field`:
   - Validates field value is a string
   - Splits value by separator: `value.split(separator)`
   - Assigns each part to corresponding target field
   - Sets remaining target fields to `null` if split produces fewer values
   - Increments affected count
4. Skips documents where field is non-string or missing
5. Commits transaction

**Behavior Notes:**
- **Preservation**: Original `source_field` remains in document
- **Null padding**: If split produces fewer parts than target fields, remaining fields are `null`
- **Non-string fields**: Skipped (only strings can be split)
- **Overwrite**: Target fields are overwritten if they exist

**Example with Null Padding:**
```
source_field: "John"
target_fields: ["first_name", "last_name"]
separator: " "

Split result: ["John"]  // Only 1 part, 2 targets
Result:
  first_name: "John"
  last_name: null
```

---

## Utility Endpoints

### Analyze Collection Fields

**Route:** `GET /migrations/{collection}/analyze-fields`

**Purpose:** Inspect field structure and statistics before planning migrations.

**Query Parameters:**
- `collection` (path parameter, required) - Collection name or ID
- `project_id` (query parameter, required) - Project ID

**Response:**
```json
{
  "collection": "string - Collection name",
  "collection_id": "string - UUID",
  "total_documents": integer,
  "unique_fields": integer,
  "fields": {
    "{field_name}": {
      "types": ["string", ...],
      "present_in": integer,
      "missing_in": integer,
      "null_count": integer,
      "coverage_percentage": number,
      "sample_values": [...]
    }
  }
}
```

**How It Works:**
1. Resolves collection by name or ID
2. Iterates all documents in collection
3. For each unique field found:
   - Detects value types (from sample)
   - Counts documents where field is present
   - Counts null values
   - Collects sample values (up to 5)
   - Calculates coverage percentage
4. Returns aggregate statistics

**Use Cases:**
- Identify field coverage (% of documents with field)
- Detect inconsistent field types
- Plan type conversions or cleanups
- Understand schema fragmentation

---

### Dry Run Migration

**Route:** `POST /migrations/{collection}/dry-run`

**Purpose:** Preview migration impact without making changes.

**Query Parameters:**
- `collection` (path parameter, required) - Collection name or ID
- `operation` (query parameter, required) - Operation type: `rename-field`, `add-field`, `delete-field`, etc.
- `params` (body, optional) - Operation parameters matching the full migration request
- `project_id` (query parameter, required) - Project ID

**Request Body:**
```json
{
  "old_field_name": "string - For rename-field operation",
  "new_field_name": "string - For rename-field operation",
  "field_name": "string - For add-field operation",
  "default_value": "any - For add-field operation"
}
```

**Response:**
```json
{
  "collection": "string - Collection name",
  "operation": "string - Operation type",
  "total_documents": integer,
  "estimated_affected": integer,
  "sample_changes": [
    {
      "document_id": "string - UUID",
      "before": "object - Sample before state",
      "after": "object - Sample after state"
    }
  ],
  "warning": "This is a dry run. No changes were made."
}
```

**How It Works:**
1. Resolves collection by name or ID
2. Loads sample of up to 10 documents
3. Simulates operation on sample:
   - **rename-field**: Shows fields that would be renamed
   - **add-field**: Shows documents that would receive new field
4. Calculates total affected count from full document set
5. Returns estimated impact without modifying database

**Use Cases:**
- Verify operation logic before execution
- Estimate scope of migration
- Preview changes on sample documents
- Identify potential issues (e.g., missing fields)

---

## Response Schema

All migration operations return a `MigrationResponse` object:

```json
{
  "success": boolean - Operation completed without fatal errors,
  "message": "string - Human-readable operation summary",
  "documents_affected": integer - Count of documents modified,
  "execution_time_ms": integer - Duration in milliseconds,
  "details": {
    "collection": "string",
    ...operation-specific fields...
  }
}
```

---

## Error Handling

### HTTP Status Codes

- `404` - Collection or field not found
- `400` - Invalid request parameters (unsupported type, strategy, etc.)
- `401` - Unauthorized (invalid project access)

### Error Response Format

```json
{
  "detail": "string - Error message"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Collection not found | Invalid collection name/ID | Verify collection exists via `/collections` endpoint |
| Invalid target type | Unsupported type string | Use one of: `string`, `number`, `boolean`, `array`, `object` |
| Invalid strategy | Unsupported merge strategy | Use one of: `concat`, `sum`, `array`, `first` |
| Field already exists | Target field already exists | Rename or delete existing field first |

---

## Implementation Details

### Database Interaction

- **ORM**: SQLAlchemy with PostgreSQL
- **Data Column**: All field migrations modify `Document.data` (JSONB type)
- **Change Tracking**: Uses `flag_modified()` for JSONB mutations
- **Transactions**: Single `db.commit()` per operation (atomic)
- **Query Pattern**: Load all documents in memory, modify, persist

### Performance Considerations

- **In-Memory Processing**: All documents loaded into memory for iteration
- **Batch Commits**: Single transaction per operation (reduces I/O)
- **Large Collections**: For very large collections (>100k docs), consider implementing bulk SQL operations
- **Execution Time**: Returned in milliseconds; includes serialization and commit time

### Transaction Safety

- All changes within single transaction
- Rollback on error leaves database unchanged
- `db.commit()` persists all modifications

---

## Collection Parameter Matching

The `collection` parameter in request bodies accepts either:
- **Collection name** (string): `"users"`, `"products"`
- **Collection ID** (UUID): `"550e8400-e29b-41d4-a716-446655440000"`

The system resolves by querying:
```sql
WHERE Collection.id = collection OR Collection.name = collection
AND Collection.project_id = project.id
```

---

## Authorization

All migration endpoints require:
1. Valid API key via header (`Authorization: Bearer {token}`)
2. Project access validation (user must be dashboard admin)
3. Project ID match in query parameter

Access check uses `require_dashboard_access` dependency.
