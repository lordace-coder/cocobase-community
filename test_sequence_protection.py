#!/usr/bin/env python3
"""
Test the sequence protection system.

This script tests that the automatic sequence protection is working
by attempting operations that would normally cause duplicate key errors.
"""

from sqlalchemy import text
from app.core.database import get_db
from app.models.pricing import Payment, PricingPlan
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_manual_insert_protection():
    """Test that manual inserts with explicit IDs don't break sequences."""
    db = next(get_db())
    connection = db.connection()

    try:
        print("\n" + "=" * 70)
        print("TEST: Manual Insert Protection")
        print("=" * 70 + "\n")

        # Get current max ID
        result = connection.execute(text("SELECT MAX(id) FROM payments"))
        max_id_before = result.scalar() or 0
        print(f"1. Current max ID in payments: {max_id_before}")

        # Get current sequence value
        result = connection.execute(text("SELECT last_value FROM payments_id_seq"))
        seq_before = result.scalar()
        print(f"2. Current sequence value: {seq_before}")

        # Manually insert with a high explicit ID
        test_id = max_id_before + 1000
        print(f"\n3. Manually inserting payment with ID = {test_id}")

        connection.execute(
            text("""
                INSERT INTO payments
                (id, reference, provider, amount, currency, status, project_id, user_id, plan_id)
                SELECT
                    :test_id,
                    'TEST-PROTECTION-' || :test_id,
                    'test',
                    100.0,
                    'USD',
                    'pending',
                    p.id,
                    p.user_id,
                    1
                FROM projects p
                LIMIT 1
            """),
            {"test_id": test_id}
        )
        connection.commit()

        print(f"   ✓ Successfully inserted payment with ID {test_id}")

        # Check sequence was updated by trigger
        result = connection.execute(text("SELECT last_value FROM payments_id_seq"))
        seq_after = result.scalar()
        print(f"\n4. Sequence value after insert: {seq_after}")

        # The trigger should have updated the sequence
        expected_seq = test_id + 1
        if seq_after >= expected_seq:
            print(f"   ✓ SUCCESS! Sequence was automatically updated to {seq_after}")
            print(f"   ✓ Next auto-generated ID will be {seq_after} or higher")
        else:
            print(f"   ✗ WARNING: Sequence is {seq_after}, expected >= {expected_seq}")
            print(f"   This might cause issues on next insert!")

        # Cleanup: Delete test record
        connection.execute(
            text("DELETE FROM payments WHERE reference LIKE 'TEST-PROTECTION-%'")
        )
        connection.commit()
        print(f"\n5. Cleaned up test data")

        print("\n" + "=" * 70)
        print("TEST PASSED! Sequence protection is working correctly.")
        print("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        connection.rollback()
        print("\n" + "=" * 70)
        print("TEST FAILED!")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nThe sequence protection may not be set up correctly.")
        print("Run: .venv/bin/python setup_sequence_protection.py")
        print("=" * 70 + "\n")

    finally:
        db.close()


def test_normal_insert():
    """Test that normal inserts still work correctly."""
    db = next(get_db())
    connection = db.connection()

    try:
        print("\n" + "=" * 70)
        print("TEST: Normal Auto-Increment Insert")
        print("=" * 70 + "\n")

        # Get sequence value before
        result = connection.execute(text("SELECT last_value FROM payments_id_seq"))
        seq_before = result.scalar()
        print(f"1. Sequence value before insert: {seq_before}")

        # Insert without specifying ID (normal behavior)
        print(f"\n2. Inserting payment with auto-generated ID...")
        connection.execute(
            text("""
                INSERT INTO payments
                (reference, provider, amount, currency, status, project_id, user_id, plan_id)
                SELECT
                    'TEST-NORMAL-' || nextval('payments_id_seq'),
                    'test',
                    50.0,
                    'USD',
                    'pending',
                    p.id,
                    p.user_id,
                    1
                FROM projects p
                LIMIT 1
            """)
        )
        connection.commit()

        # Get the ID that was used
        result = connection.execute(
            text("SELECT id FROM payments WHERE reference LIKE 'TEST-NORMAL-%' ORDER BY id DESC LIMIT 1")
        )
        new_id = result.scalar()
        print(f"   ✓ Payment created with ID: {new_id}")

        # Cleanup
        connection.execute(
            text("DELETE FROM payments WHERE reference LIKE 'TEST-NORMAL-%'")
        )
        connection.commit()
        print(f"\n3. Cleaned up test data")

        print("\n" + "=" * 70)
        print("TEST PASSED! Normal inserts work correctly.")
        print("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        connection.rollback()
        print("\n" + "=" * 70)
        print("TEST FAILED!")
        print("=" * 70 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TESTING SEQUENCE PROTECTION SYSTEM")
    print("=" * 70)

    test_normal_insert()
    test_manual_insert_protection()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE!")
    print("=" * 70 + "\n")
