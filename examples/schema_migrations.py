#!/usr/bin/env python3
"""
Schema Migrations - Python Examples
Complete examples for using the schema migrations API
"""

import requests
import json
from typing import Dict, Any, List

# Configuration
API_BASE_URL = "https://api.cocobase.com"
API_KEY = "your-api-key-here"

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# ============================================
# COLLECTION MIGRATIONS
# ============================================


def rename_collection(old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a collection"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/rename-collection",
        headers=HEADERS,
        json={"old_name": old_name, "new_name": new_name},
    )
    return response.json()


# ============================================
# FIELD MIGRATIONS
# ============================================


def rename_field(collection: str, old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a field in all documents"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/rename-field",
        headers=HEADERS,
        json={
            "collection": collection,
            "old_field_name": old_name,
            "new_field_name": new_name,
        },
    )
    return response.json()


def add_field(collection: str, field_name: str, default_value: Any) -> Dict[str, Any]:
    """Add a field to all documents"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/add-field",
        headers=HEADERS,
        json={
            "collection": collection,
            "field_name": field_name,
            "default_value": default_value,
        },
    )
    return response.json()


def delete_field(collection: str, field_name: str) -> Dict[str, Any]:
    """Delete a field from all documents"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/delete-field",
        headers=HEADERS,
        json={"collection": collection, "field_name": field_name},
    )
    return response.json()


def change_field_type(
    collection: str,
    field_name: str,
    target_type: str,
    conversion_map: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Change field type with optional conversion map"""
    payload = {
        "collection": collection,
        "field_name": field_name,
        "target_type": target_type,
    }

    if conversion_map:
        payload["conversion_map"] = conversion_map

    response = requests.post(
        f"{API_BASE_URL}/migrations/change-field-type", headers=HEADERS, json=payload
    )
    return response.json()


def merge_fields(
    collection: str,
    source_fields: List[str],
    target_field: str,
    strategy: str = "concat",
    separator: str = " ",
) -> Dict[str, Any]:
    """Merge multiple fields into one"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/merge-fields",
        headers=HEADERS,
        json={
            "collection": collection,
            "source_fields": source_fields,
            "target_field": target_field,
            "strategy": strategy,
            "separator": separator,
        },
    )
    return response.json()


def split_field(
    collection: str, source_field: str, target_fields: List[str], separator: str = " "
) -> Dict[str, Any]:
    """Split one field into multiple fields"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/split-field",
        headers=HEADERS,
        json={
            "collection": collection,
            "source_field": source_field,
            "target_fields": target_fields,
            "separator": separator,
        },
    )
    return response.json()


# ============================================
# UTILITY FUNCTIONS
# ============================================


def analyze_collection(collection: str) -> Dict[str, Any]:
    """Analyze collection fields"""
    response = requests.get(
        f"{API_BASE_URL}/migrations/{collection}/analyze-fields", headers=HEADERS
    )
    return response.json()


def dry_run(collection: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Test migration without making changes"""
    response = requests.post(
        f"{API_BASE_URL}/migrations/{collection}/dry-run?operation={operation}",
        headers=HEADERS,
        json=params,
    )
    return response.json()


# ============================================
# EXAMPLE WORKFLOWS
# ============================================


def example_1_normalize_user_fields():
    """
    Example 1: Normalize inconsistent field names in users collection
    """
    print("=" * 60)
    print("Example 1: Normalize User Fields")
    print("=" * 60)

    # Step 1: Analyze collection
    print("\n📊 Analyzing collection...")
    analysis = analyze_collection("users")
    print(f"Total documents: {analysis['total_documents']}")
    print(f"Unique fields: {analysis['unique_fields']}")

    # Step 2: Rename inconsistent fields
    print("\n🔄 Renaming fields...")

    # fullName → full_name
    result = rename_field("users", "fullName", "full_name")
    print(f"✅ Renamed fullName → full_name ({result['documents_affected']} docs)")

    # emailAddress → email
    result = rename_field("users", "emailAddress", "email")
    print(f"✅ Renamed emailAddress → email ({result['documents_affected']} docs)")

    print("\n✨ Done! User fields normalized.")


def example_2_add_user_status_system():
    """
    Example 2: Add status tracking to existing users
    """
    print("\n" + "=" * 60)
    print("Example 2: Add User Status System")
    print("=" * 60)

    # Add status field
    print("\n➕ Adding status field...")
    result = add_field("users", "status", "active")
    print(f"✅ Added status field to {result['documents_affected']} documents")

    # Add is_verified field
    print("\n➕ Adding is_verified field...")
    result = add_field("users", "is_verified", False)
    print(f"✅ Added is_verified field to {result['documents_affected']} documents")

    # Add created_at field
    print("\n➕ Adding created_at field...")
    result = add_field("users", "created_at", None)
    print(f"✅ Added created_at field to {result['documents_affected']} documents")

    print("\n✨ Done! Status system added.")


def example_3_merge_name_fields():
    """
    Example 3: Merge first_name and last_name into full_name
    """
    print("\n" + "=" * 60)
    print("Example 3: Merge Name Fields")
    print("=" * 60)

    # Test with dry run first
    print("\n🧪 Testing with dry run...")
    dry_result = dry_run(
        "users",
        "merge-fields",
        {
            "source_fields": ["first_name", "last_name"],
            "target_field": "full_name",
            "strategy": "concat",
            "separator": " ",
        },
    )
    print(f"Would affect: {dry_result['estimated_affected']} documents")
    print("Sample changes:")
    for change in dry_result.get("sample_changes", [])[:3]:
        print(f"  - {change}")

    # Execute merge
    print("\n🔄 Executing merge...")
    result = merge_fields(
        "users", ["first_name", "last_name"], "full_name", "concat", " "
    )
    print(f"✅ Merged fields in {result['documents_affected']} documents")
    print(f"⏱️  Execution time: {result['execution_time_ms']}ms")

    print("\n✨ Done! Names merged.")


def example_4_convert_price_to_number():
    """
    Example 4: Convert price strings to numbers
    """
    print("\n" + "=" * 60)
    print("Example 4: Convert Price to Number")
    print("=" * 60)

    # Analyze first
    print("\n📊 Analyzing products...")
    analysis = analyze_collection("products")
    price_field = analysis["fields"].get("price", {})
    print(f"Price field types: {price_field.get('types', [])}")
    print(f"Sample values: {price_field.get('sample_values', [])}")

    # Convert to number
    print("\n🔄 Converting prices to numbers...")
    result = change_field_type("products", "price", "number")
    print(f"✅ Converted {result['documents_affected']} documents")

    if result["details"].get("conversion_errors"):
        print("\n⚠️  Conversion errors:")
        for error in result["details"]["conversion_errors"][:5]:
            print(f"  - Doc {error['document_id']}: {error['error']}")

    print("\n✨ Done! Prices converted.")


def example_5_split_full_name():
    """
    Example 5: Split full_name into first_name and last_name
    """
    print("\n" + "=" * 60)
    print("Example 5: Split Full Name")
    print("=" * 60)

    print("\n🔄 Splitting full_name...")
    result = split_field("users", "full_name", ["first_name", "last_name"], " ")
    print(f"✅ Split field in {result['documents_affected']} documents")

    print("\n✨ Done! Names split.")


def example_6_calculate_order_totals():
    """
    Example 6: Calculate order totals from subtotal + tax + shipping
    """
    print("\n" + "=" * 60)
    print("Example 6: Calculate Order Totals")
    print("=" * 60)

    print("\n🔄 Merging price fields to calculate totals...")
    result = merge_fields("orders", ["subtotal", "tax", "shipping"], "total", "sum")
    print(f"✅ Calculated totals for {result['documents_affected']} orders")

    print("\n✨ Done! Totals calculated.")


def example_7_cleanup_legacy_fields():
    """
    Example 7: Delete legacy fields no longer needed
    """
    print("\n" + "=" * 60)
    print("Example 7: Cleanup Legacy Fields")
    print("=" * 60)

    # List of legacy fields to delete
    legacy_fields = ["legacy_id", "old_status", "deprecated_field"]

    for field in legacy_fields:
        print(f"\n🗑️  Deleting {field}...")
        result = delete_field("users", field)
        print(f"✅ Deleted from {result['documents_affected']} documents")

    print("\n✨ Done! Legacy fields removed.")


def example_8_convert_boolean_fields():
    """
    Example 8: Convert string boolean fields to actual booleans
    """
    print("\n" + "=" * 60)
    print("Example 8: Convert Boolean Fields")
    print("=" * 60)

    # Convert is_active with custom mapping
    print("\n🔄 Converting is_active to boolean...")
    result = change_field_type(
        "users",
        "is_active",
        "boolean",
        conversion_map={
            "yes": True,
            "no": False,
            "active": True,
            "inactive": False,
            "1": True,
            "0": False,
        },
    )
    print(f"✅ Converted {result['documents_affected']} documents")

    print("\n✨ Done! Booleans converted.")


# ============================================
# MIGRATION WORKFLOW
# ============================================


def safe_migration_workflow(collection: str):
    """
    Safe migration workflow with best practices
    """
    print("\n" + "=" * 60)
    print("Safe Migration Workflow")
    print("=" * 60)

    # Step 1: Analyze
    print("\n📊 Step 1: Analyzing collection...")
    analysis = analyze_collection(collection)
    print(f"Collection: {analysis['collection']}")
    print(f"Documents: {analysis['total_documents']}")
    print(f"Fields: {analysis['unique_fields']}")

    # Step 2: Plan
    print("\n📝 Step 2: Planning migration...")
    print("Operations to perform:")
    print("  1. Rename fullName → full_name")
    print("  2. Add status field")
    print("  3. Delete legacy_id field")

    # Step 3: Dry run
    print("\n🧪 Step 3: Testing with dry run...")
    dry_result = dry_run(
        collection,
        "rename-field",
        {"old_field_name": "fullName", "new_field_name": "full_name"},
    )
    print(f"Would affect: {dry_result['estimated_affected']} documents")

    # Step 4: Backup (export)
    print("\n💾 Step 4: Creating backup...")
    print("(Export data before proceeding)")
    # In real scenario: export_response = requests.get(f"{API_BASE_URL}/collections/{collection}/export")

    # Step 5: Execute
    print("\n⚡ Step 5: Executing migrations...")

    # Operation 1: Rename
    result1 = rename_field(collection, "fullName", "full_name")
    print(f"✅ Renamed field: {result1['documents_affected']} docs")

    # Operation 2: Add field
    result2 = add_field(collection, "status", "active")
    print(f"✅ Added field: {result2['documents_affected']} docs")

    # Operation 3: Delete field
    result3 = delete_field(collection, "legacy_id")
    print(f"✅ Deleted field: {result3['documents_affected']} docs")

    # Step 6: Verify
    print("\n✅ Step 6: Verifying changes...")
    final_analysis = analyze_collection(collection)
    print(f"Final field count: {final_analysis['unique_fields']}")

    print("\n✨ Migration complete!")


# ============================================
# MAIN
# ============================================


def main():
    """Run examples"""
    print("\n🚀 CocoBase Schema Migrations - Python Examples\n")

    # Uncomment to run specific examples:

    # example_1_normalize_user_fields()
    # example_2_add_user_status_system()
    # example_3_merge_name_fields()
    # example_4_convert_price_to_number()
    # example_5_split_full_name()
    # example_6_calculate_order_totals()
    # example_7_cleanup_legacy_fields()
    # example_8_convert_boolean_fields()
    # safe_migration_workflow("users")

    print("\n💡 Tips:")
    print("  1. Always analyze before migrating")
    print("  2. Use dry run to test")
    print("  3. Backup data before major changes")
    print("  4. Run one operation at a time")
    print("  5. Monitor execution time")

    print("\n📚 Documentation:")
    print("  - Full guide: SCHEMA_MIGRATIONS_GUIDE.md")
    print("  - Quick ref: SCHEMA_MIGRATIONS_QUICK_REF.md")


if __name__ == "__main__":
    print("⚠️  Before running:")
    print("  1. Replace API_KEY with your actual key")
    print("  2. Update API_BASE_URL if needed")
    print("  3. Uncomment examples to run")
    print("\n")

    # main()
