import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import Json
import sys
import json

SOURCE = "postgresql://cocobase_owner:npg_zLEhvQOD1Iu9@ep-lucky-glade-a5sg2kpd-pooler.us-east-2.aws.neon.tech/cocobase?sslmode=require"
TARGET = "postgres://user_96043cdf:00d1a63b99fe0e6832a47882375ba350@db.pxxl.pro:56886/db_83f9b0ea"


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

    try:
        # Connect to databases
        print("📡 Connecting to source database...")
        src = psycopg2.connect(SOURCE)
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

        # Step 1: Create tables
        print("=" * 50)
        print("STEP 1: Creating table structures")
        print("=" * 50)

        for table in tables:
            try:
                # Drop table if exists (for clean migration)
                tgt_cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

                # Get CREATE TABLE statement
                create_stmt, json_cols = get_table_create_statement(src_cur, table)
                table_info[table] = {"json_cols": json_cols}

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

        # Step 2: Copy data
        print("=" * 50)
        print("STEP 2: Copying data")
        print("=" * 50)

        for table in tables:
            # Skip tables that failed to create
            if "error" in table_info.get(table, {}):
                print(f"⏭️  Skipping {table} (table creation failed)")
                continue

            try:
                print(f"📦 Copying {table}...", end=" ")

                # Get data from source
                src_cur.execute(f"SELECT * FROM {table}")
                rows = src_cur.fetchall()

                if not rows:
                    print("(empty table)")
                    continue

                # Get column names
                cols = [desc[0] for desc in src_cur.description]
                placeholders = ",".join(["%s"] * len(cols))

                # Find JSON column indices
                json_cols = table_info[table].get("json_cols", [])
                json_indices = [i for i, col in enumerate(cols) if col in json_cols]

                # Insert data in batches
                batch_size = 500
                total_inserted = 0

                for i in range(0, len(rows), batch_size):
                    batch = rows[i : i + batch_size]

                    # Convert dict columns to JSON
                    if json_indices:
                        batch = [
                            convert_row_for_insert(row, json_indices) for row in batch
                        ]

                    tgt_cur.executemany(
                        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                        batch,
                    )
                    total_inserted += len(batch)

                print(f"✅ {total_inserted} rows")

            except Exception as e:
                print(f"\n❌ Error copying {table}: {str(e)}")
                print(f"   First row sample: {rows[0] if rows else 'N/A'}")
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

        # Close connections
        src_cur.close()
        src.close()
        tgt_cur.close()
        tgt.close()

        print("\n" + "=" * 50)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 50)

        # Show summary
        failed_tables = [t for t, info in table_info.items() if "error" in info]
        if failed_tables:
            print(f"\n⚠️  WARNING: {len(failed_tables)} tables had issues:")
            for t in failed_tables:
                print(f"   - {t}")

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    migrate()
