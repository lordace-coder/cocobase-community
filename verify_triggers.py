#!/usr/bin/env python3
"""Verify that sequence protection triggers are active."""

from sqlalchemy import text
from app.core.database import get_db


def verify_triggers():
    """Check which tables have sequence protection triggers."""
    db = next(get_db())
    connection = db.connection()

    query = text("""
        SELECT
            event_object_table as table_name,
            trigger_name
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        AND trigger_name LIKE 'fix_%_sequence'
        ORDER BY table_name
    """)

    result = connection.execute(query)
    triggers = list(result)

    print("\n" + "=" * 60)
    print("SEQUENCE PROTECTION STATUS")
    print("=" * 60 + "\n")

    if not triggers:
        print("⚠ No sequence protection triggers found!")
        print("\nRun: .venv/bin/python setup_sequence_protection.py\n")
    else:
        print(f"✓ Found {len(triggers)} active triggers:\n")
        for trigger in triggers:
            table_name = trigger[0]
            trigger_name = trigger[1]
            print(f"  ✓ {table_name:<30} → {trigger_name}")

        print("\n" + "=" * 60)
        print("All protected tables auto-fix sequences after inserts.")
        print("=" * 60 + "\n")

    db.close()


if __name__ == "__main__":
    verify_triggers()
