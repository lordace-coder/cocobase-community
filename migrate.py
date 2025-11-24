import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import Json
import sys
import json

# Disable output buffering for real-time progress
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

SOURCE = "postgresql://postgres.zeikigvcfqdyzfhlvdid:lordace12@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
TARGET = "postgresql://postgres:lordace12@coco-postgress.fly.dev:5432/postgres"


def get_table_create_statement(cursor, table_name):
    """Generate CREATE TABLE statement from source database"""
    cursor.execute(
        f"""
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default,
            udt_name
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """
    )

    columns = cursor.fetchall()
    if not columns:
        return None, []

    col_defs = []
    serial_cols = []
    json_cols = []

    for col_name, data_type, max_len, nullable, default, udt_name in columns:
        col_def = f"{col_name} "

        # Check if it's a serial/auto-increment column
        is_serial = default and "nextval" in str(default)

        # Handle data types
        if is_serial:
            col_def += "SERIAL"
            serial_cols.append(col_name)
        elif data_type == "character varying":
            col_def += f"VARCHAR({max_len})" if max_len else "VARCHAR"
        elif data_type == "ARRAY":
            # Handle array types - get the base type from udt_name
            if udt_name.startswith("_"):
                base_type = udt_name[1:]  # Remove leading underscore
                if base_type == "text" or base_type == "varchar":
                    col_def += "TEXT[]"
                elif base_type == "int4":
                    col_def += "INTEGER[]"
                elif base_type == "int8":
                    col_def += "BIGINT[]"
                elif base_type == "uuid":
                    col_def += "UUID[]"
                else:
                    col_def += f"{base_type.upper()}[]"
            else:
                col_def += "TEXT[]"  # Default fallback
        elif data_type == "USER-DEFINED":
            if udt_name in ["json", "jsonb"]:
                col_def += udt_name.upper()
                json_cols.append(col_name)
            else:
                col_def += "TEXT"
        elif udt_name in ["json", "jsonb"]:
            col_def += udt_name.upper()
            json_cols.append(col_name)
        else:
            col_def += data_type.upper()

        # Add NOT NULL (skip for serial columns as they're auto NOT NULL)
        if nullable == "NO" and not is_serial:
            col_def += " NOT NULL"

        # Add DEFAULT (skip serial defaults)
        if default and not is_serial:
            col_def += f" DEFAULT {default}"

        col_defs.append(col_def)

    return f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})", json_cols


def get_primary_keys(cursor, table_name):
    """Get primary key constraints"""
    cursor.execute(
        f"""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = '{table_name}'::regclass AND i.indisprimary
    """
    )
    return [row[0] for row in cursor.fetchall()]


def convert_row_for_insert(row, json_column_indices):
    """Convert dict values to JSON for insertion"""
    converted = list(row)
    for idx in json_column_indices:
        if converted[idx] is not None and isinstance(converted[idx], dict):
            converted[idx] = Json(converted[idx])
    return tuple(converted)


def migrate():
    print("🔄 Starting database migration...\n")

    src = None
    tgt = None
    src_cur = None
    tgt_cur = None

    try:
        # Connect to databases
        print("📡 Connecting to source database...")
        src = psycopg2.connect(SOURCE)
        # Don't use autocommit on source - needed for server-side cursors
        src_cur = src.cursor()

        print("📡 Connecting to target database...")
        tgt = psycopg2.connect(TARGET)
        tgt.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        tgt_cur = tgt.cursor()

        print("✅ Connected successfully!\n")

        # Get all tables
        src_cur.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """
        )

        tables = [row[0] for row in src_cur.fetchall()]
        print(f"📋 Found {len(tables)} tables: {tables}\n")

        # Store table info
        table_info = {}

        # Step 1: Create tables (only if they don't exist)
        print("=" * 50)
        print("STEP 1: Creating table structures (if needed)")
        print("=" * 50)

        for table in tables:
            try:
                # Check if table already exists
                tgt_cur.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = '{table}'
                    )
                """)
                exists = tgt_cur.fetchone()[0]

                # Get JSON columns info for later
                _, json_cols = get_table_create_statement(src_cur, table)
                table_info[table] = {"json_cols": json_cols}

                if exists:
                    print(f"⏭️  Skipped {table} (already exists)")
                else:
                    # Get CREATE TABLE statement
                    create_stmt, _ = get_table_create_statement(src_cur, table)

                    if create_stmt:
                        tgt_cur.execute(create_stmt)
                        print(f"✅ Created table: {table}")
                    else:
                        print(f"⚠️  Skipped: {table} (no columns found)")

            except Exception as e:
                print(f"❌ Error creating {table}: {str(e)}")
                table_info[table] = {"error": str(e)}
                continue

        print()

        # Step 2: Copy data (documents last since it's largest)
        print("=" * 50)
        print("STEP 2: Copying data")
        print("=" * 50)

        # Skip route_hits (not used anymore)
        # Reorder tables: copy documents last
        tables_ordered = [t for t in tables if t not in ('documents', 'route_hits')]
        if 'documents' in tables:
            tables_ordered.append('documents')

        for table in tables_ordered:
            # Skip tables that failed to create
            if "error" in table_info.get(table, {}):
                print(f"⏭️  Skipping {table} (table creation failed)")
                continue

            try:
                print(f"📦 Copying {table}...")

                # Check if table already has data
                tgt_cur.execute(f"SELECT COUNT(*) FROM {table}")
                existing_count = tgt_cur.fetchone()[0]

                # Get total count from source
                src_cur.execute(f"SELECT COUNT(*) FROM {table}")
                total_count = src_cur.fetchone()[0]

                if total_count == 0:
                    print(f"   (empty table)")
                    continue

                # If some rows exist, continue from where we left off
                if existing_count > 0:
                    if existing_count >= total_count:
                        print(f"   ⏭️  Already complete ({existing_count}/{total_count} rows)")
                        continue
                    else:
                        print(f"   ⚠️  Partial: {existing_count}/{total_count} rows exist, continuing...")
                else:
                    print(f"   Total rows to copy: {total_count}")

                # Fetch data in batches using OFFSET/LIMIT (prevents memory issues and timeouts)
                batch_size = 10  # Small batches for frequent progress updates
                total_inserted = 0
                offset = existing_count  # Start from where we left off

                # Get column names first
                src_cur.execute(f"SELECT * FROM {table} LIMIT 1")
                cols = [desc[0] for desc in src_cur.description]
                placeholders = ",".join(["%s"] * len(cols))

                # Find JSON column indices
                json_cols = table_info[table].get("json_cols", [])
                json_indices = [i for i, col in enumerate(cols) if col in json_cols]

                while offset < total_count:
                    # Fetch batch
                    src_cur.execute(f"SELECT * FROM {table} OFFSET {offset} LIMIT {batch_size}")
                    rows = src_cur.fetchall()

                    if not rows:
                        break

                    # Convert dict columns to JSON
                    if json_indices:
                        converted_batch = [
                            convert_row_for_insert(row, json_indices) for row in rows
                        ]
                    else:
                        converted_batch = rows

                    # Insert batch (skip duplicates)
                    try:
                        tgt_cur.executemany(
                            f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                            converted_batch,
                        )
                        total_inserted += len(rows)
                    except Exception as e:
                        # If duplicate, skip and continue
                        if "duplicate" in str(e).lower():
                            print(f"   ⚠️  Skipping duplicates at offset {offset}")
                        else:
                            raise

                    offset += batch_size

                    # Show progress with current total
                    current_total = existing_count + total_inserted
                    progress = (current_total / total_count) * 100
                    remaining = total_count - current_total
                    print(f"   Progress: {current_total}/{total_count} ({progress:.1f}%) - {remaining} remaining")

                print(f"   ✅ Completed: {existing_count + total_inserted} total rows ({total_inserted} new)")

            except Exception as e:
                print(f"\n❌ Error copying {table}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print()

        # Step 3: Reset sequences for SERIAL columns
        print("=" * 50)
        print("STEP 3: Resetting auto-increment sequences")
        print("=" * 50)

        for table in tables:
            if "error" in table_info.get(table, {}):
                continue

            try:
                # Find columns with sequences
                src_cur.execute(
                    f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    AND column_default LIKE 'nextval%'
                """
                )

                serial_cols = [row[0] for row in src_cur.fetchall()]

                for col in serial_cols:
                    # Get max value
                    tgt_cur.execute(f"SELECT MAX({col}) FROM {table}")
                    max_val = tgt_cur.fetchone()[0]

                    if max_val:
                        seq_name = f"{table}_{col}_seq"
                        tgt_cur.execute(f"SELECT setval('{seq_name}', {max_val})")
                        print(f"✅ Reset sequence for {table}.{col} to {max_val}")

            except Exception as e:
                print(f"⚠️  Could not reset sequence for {table}: {str(e)}")

        print()

        # Step 4: Add primary keys
        print("=" * 50)
        print("STEP 4: Adding primary keys")
        print("=" * 50)

        for table in tables:
            if "error" in table_info.get(table, {}):
                continue

            try:
                pk_cols = get_primary_keys(src_cur, table)
                if pk_cols:
                    pk_name = f"{table}_pkey"
                    tgt_cur.execute(
                        f"ALTER TABLE {table} ADD CONSTRAINT {pk_name} PRIMARY KEY ({','.join(pk_cols)})"
                    )
                    print(f"✅ Added primary key to {table}: {pk_cols}")
            except Exception as e:
                print(f"⚠️  Could not add primary key to {table}: {str(e)}")

        print("\n" + "=" * 50)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 50)

        # Show summary
        failed_tables = [t for t, info in table_info.items() if "error" in info]
        if failed_tables:
            print(f"\n⚠️  WARNING: {len(failed_tables)} tables had issues:")
            for t in failed_tables:
                print(f"   - {t}: {table_info[t].get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ensure connections are closed properly
        if src_cur:
            try:
                src_cur.close()
            except:
                pass
        if src:
            try:
                src.close()
            except:
                pass
        if tgt_cur:
            try:
                tgt_cur.close()
            except:
                pass
        if tgt:
            try:
                tgt.close()
            except:
                pass


if __name__ == "__main__":
    migrate()
