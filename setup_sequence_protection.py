#!/usr/bin/env python3
"""
Set up automatic sequence protection for all tables.

This script creates database triggers that automatically fix sequences
after any insert operation, preventing duplicate key errors permanently.

Run this once to set up the protection, and you'll never have sequence
issues again.
"""

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.sequence_manager import (
    SequenceManager,
    setup_automatic_sequence_management,
    check_sequences_on_startup,
)
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Set up automatic sequence protection."""
    print("\n" + "=" * 70)
    print("SETTING UP AUTOMATIC SEQUENCE PROTECTION")
    print("=" * 70 + "\n")

    try:
        # Get database session
        db: Session = next(get_db())

        # Step 1: Check and fix current sequences
        print("Step 1: Checking and fixing current sequences...")
        print("-" * 70)
        check_sequences_on_startup(db)

        # Step 2: Set up automatic triggers
        print("\nStep 2: Setting up automatic sequence protection triggers...")
        print("-" * 70)
        setup_automatic_sequence_management(db)

        # Step 3: Verify setup
        print("\nStep 3: Verifying setup...")
        print("-" * 70)
        manager = SequenceManager(db)
        results = manager.check_and_fix_all_sequences(auto_fix=False)

        print(f"\n✓ Successfully checked {results['total_tables']} tables")

        all_synced = all(
            status.get("is_synced", False)
            for status in results["checked"]
        )

        if all_synced:
            print("✓ All sequences are properly synchronized!")
        else:
            out_of_sync = [
                status["table"]
                for status in results["checked"]
                if not status.get("is_synced", False)
            ]
            print(f"⚠ Warning: {len(out_of_sync)} sequences still out of sync:")
            for table in out_of_sync:
                print(f"  - {table}")

        print("\n" + "=" * 70)
        print("SETUP COMPLETE!")
        print("=" * 70)
        print("\nYour database now has automatic sequence protection.")
        print("Sequences will be automatically fixed after any insert.")
        print("You should never see duplicate key errors again!")
        print("=" * 70 + "\n")

        db.close()

    except Exception as e:
        logger.error(f"Error during setup: {e}", exc_info=True)
        print("\n" + "=" * 70)
        print("SETUP FAILED!")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nPlease check the error message above and try again.")
        print("=" * 70 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
