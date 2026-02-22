#!/usr/bin/env python3
"""Check database schema for PickleType columns"""

import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.zeikigvcfqdyzfhlvdid:lordace12@aws-1-eu-west-1.pooler.supabase.com:6543/postgres",
)


def check_schema():
    """Check the current database schema for the problematic columns"""

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            print("=" * 70)
            print("DATABASE SCHEMA CHECK")
            print("=" * 70)

            # Check alembic version
            print("\n📋 Checking Alembic Migration Status:")
            print("-" * 70)
            try:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                print(f"Current alembic version: {version}")

                # Check if our migrations are applied
                if version == 'a9ef5fd16185':
                    print("✅ All migrations applied (including allowed_origins migration)")
                elif version == 'd201486f3935':
                    print("⚠️  Roles migration applied, but allowed_origins migration NOT applied")
                    print("   Need to run: alembic upgrade head")
                else:
                    print(f"⚠️  Migrations pending. Current: {version}")
                    print("   Need to run: alembic upgrade head")
            except Exception as e:
                print(f"❌ Error checking alembic version: {e}")

            # Check projects table schema
            print("\n📋 Checking 'projects' table schema:")
            print("-" * 70)
            result = conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'projects'
                AND column_name = 'allowed_origins'
            """))

            for row in result:
                col_name, data_type, udt_name = row
                print(f"Column: {col_name}")
                print(f"  Data type: {data_type}")
                print(f"  UDT name: {udt_name}")

                if data_type == 'bytea':
                    print("  ❌ PROBLEM: Still using bytea (PickleType)")
                    print("  ⚠️  Need to run: alembic upgrade head")
                elif data_type == 'ARRAY':
                    print("  ✅ Correctly using ARRAY type")

            # Check app_users table schema
            print("\n📋 Checking 'app_users' table schema:")
            print("-" * 70)
            result = conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'app_users'
                AND column_name = 'roles'
            """))

            for row in result:
                col_name, data_type, udt_name = row
                print(f"Column: {col_name}")
                print(f"  Data type: {data_type}")
                print(f"  UDT name: {udt_name}")

                if data_type == 'bytea':
                    print("  ❌ PROBLEM: Still using bytea (PickleType)")
                    print("  ⚠️  Need to run: alembic upgrade head")
                elif data_type == 'ARRAY':
                    print("  ✅ Correctly using ARRAY type")

            # Sample data check
            print("\n📋 Checking sample data from projects table:")
            print("-" * 70)
            result = conn.execute(text("""
                SELECT id, allowed_origins, pg_typeof(allowed_origins) as type
                FROM projects
                LIMIT 3
            """))

            for row in result:
                project_id, origins, pg_type = row
                print(f"Project {project_id}:")
                print(f"  Type in DB: {pg_type}")
                print(f"  Value: {origins}")
                print(f"  Python type: {type(origins)}")

            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print("\nIf you see 'bytea' type above, you need to run the migrations:")
            print("  docker-compose exec <service> alembic upgrade head")
            print("\nIf you see 'ARRAY' type, the schema is correct and the issue")
            print("might be with cached data or SQLAlchemy type confusion.")
            print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        engine.dispose()


if __name__ == "__main__":
    check_schema()
