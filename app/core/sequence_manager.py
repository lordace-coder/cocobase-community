"""
Automatic PostgreSQL sequence management to prevent duplicate key errors.

This module provides utilities to automatically detect and fix sequence issues
in PostgreSQL databases, preventing the common "duplicate key value violates
unique constraint" error.
"""

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class SequenceManager:
    """Manages PostgreSQL sequences to prevent duplicate key errors."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.connection = db_session.connection()

    def get_tables_with_sequences(self) -> List[str]:
        """
        Automatically detect all tables with integer primary keys that use sequences.

        Returns:
            List of table names that have auto-incrementing sequences
        """
        query = text("""
            SELECT
                t.table_name
            FROM information_schema.tables t
            JOIN information_schema.columns c
                ON t.table_name = c.table_name
                AND t.table_schema = c.table_schema
            WHERE
                t.table_schema = 'public'
                AND t.table_type = 'BASE TABLE'
                AND c.column_name = 'id'
                AND c.data_type IN ('integer', 'bigint', 'smallint')
                AND c.column_default LIKE 'nextval%'
            ORDER BY t.table_name
        """)

        result = self.connection.execute(query)
        return [row[0] for row in result]

    def check_sequence_sync(self, table_name: str) -> Dict[str, any]:
        """
        Check if a table's sequence is in sync with its data.

        Args:
            table_name: Name of the table to check

        Returns:
            Dict with sync status and details
        """
        try:
            # Get max ID from table
            max_id_query = text(f"SELECT MAX(id) FROM {table_name}")
            max_id = self.connection.execute(max_id_query).scalar()

            if max_id is None:
                max_id = 0

            # Get current sequence value
            sequence_name = f"{table_name}_id_seq"
            seq_query = text(f"SELECT last_value FROM {sequence_name}")
            seq_value = self.connection.execute(seq_query).scalar()

            # Check if sequence might cause issues
            # If sequence value <= max_id, we'll have a collision
            is_synced = seq_value > max_id

            return {
                "table": table_name,
                "max_id": max_id,
                "sequence_value": seq_value,
                "is_synced": is_synced,
                "next_safe_value": max_id + 1
            }

        except Exception as e:
            logger.error(f"Error checking sequence for {table_name}: {e}")
            return {
                "table": table_name,
                "error": str(e),
                "is_synced": False
            }

    def fix_sequence(self, table_name: str) -> bool:
        """
        Fix a table's sequence to prevent duplicate key errors.

        Args:
            table_name: Name of the table to fix

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get max ID from table
            max_id_query = text(f"SELECT MAX(id) FROM {table_name}")
            max_id = self.connection.execute(max_id_query).scalar()

            if max_id is None:
                max_id = 0

            # Reset sequence
            next_id = max_id + 1
            sequence_name = f"{table_name}_id_seq"

            # Set the sequence value
            # Using false as third parameter so next nextval() returns next_id
            set_query = text(f"SELECT setval('{sequence_name}', {next_id}, false)")
            self.connection.execute(set_query)

            self.connection.commit()

            logger.info(
                f"✓ Fixed sequence for {table_name}: "
                f"max_id={max_id}, next_id={next_id}"
            )
            return True

        except Exception as e:
            logger.error(f"✗ Error fixing sequence for {table_name}: {e}")
            self.connection.rollback()
            return False

    def check_and_fix_all_sequences(self, auto_fix: bool = True) -> Dict[str, any]:
        """
        Check all sequences and optionally fix them automatically.

        Args:
            auto_fix: If True, automatically fix out-of-sync sequences

        Returns:
            Dict with summary of all tables checked and fixed
        """
        tables = self.get_tables_with_sequences()
        results = {
            "total_tables": len(tables),
            "checked": [],
            "fixed": [],
            "errors": []
        }

        logger.info(f"Checking {len(tables)} tables with sequences...")

        for table_name in tables:
            status = self.check_sequence_sync(table_name)
            results["checked"].append(status)

            if not status.get("is_synced", False) and auto_fix:
                if "error" not in status:
                    if self.fix_sequence(table_name):
                        results["fixed"].append(table_name)
                    else:
                        results["errors"].append(table_name)

        logger.info(
            f"Sequence check complete: "
            f"{len(results['fixed'])} fixed, "
            f"{len(results['errors'])} errors"
        )

        return results


def check_sequences_on_startup(db: Session) -> None:
    """
    Check and fix all sequences during application startup.

    This function should be called when the application starts to ensure
    all sequences are properly synchronized.

    Args:
        db: Database session
    """
    logger.info("Starting sequence synchronization check...")

    try:
        manager = SequenceManager(db)
        results = manager.check_and_fix_all_sequences(auto_fix=True)

        if results["fixed"]:
            logger.warning(
                f"Fixed {len(results['fixed'])} sequence(s): "
                f"{', '.join(results['fixed'])}"
            )

        if results["errors"]:
            logger.error(
                f"Failed to fix {len(results['errors'])} sequence(s): "
                f"{', '.join(results['errors'])}"
            )

        if not results["fixed"] and not results["errors"]:
            logger.info("✓ All sequences are properly synchronized")

    except Exception as e:
        logger.error(f"Error during sequence check: {e}")


def create_sequence_fix_trigger(db: Session, table_name: str) -> None:
    """
    Create a PostgreSQL trigger to automatically fix sequence after manual inserts.

    This creates a trigger that updates the sequence whenever a row is inserted
    with a manually specified ID.

    Args:
        db: Database session
        table_name: Name of the table to protect
    """
    sequence_name = f"{table_name}_id_seq"
    trigger_name = f"fix_{table_name}_sequence"
    function_name = f"fix_{table_name}_sequence_func"

    # Create trigger function
    function_sql = text(f"""
        CREATE OR REPLACE FUNCTION {function_name}()
        RETURNS TRIGGER AS $$
        DECLARE
            max_id INTEGER;
        BEGIN
            -- Get the maximum ID
            EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM {table_name}' INTO max_id;

            -- Update sequence if needed
            PERFORM setval('{sequence_name}', max_id + 1, false);

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    trigger_sql = text(f"""
        DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};

        CREATE TRIGGER {trigger_name}
        AFTER INSERT ON {table_name}
        FOR EACH STATEMENT
        EXECUTE FUNCTION {function_name}();
    """)

    try:
        connection = db.connection()
        connection.execute(function_sql)
        connection.execute(trigger_sql)
        connection.commit()
        logger.info(f"✓ Created sequence protection trigger for {table_name}")
    except Exception as e:
        logger.error(f"✗ Error creating trigger for {table_name}: {e}")
        connection.rollback()


def setup_automatic_sequence_management(db: Session) -> None:
    """
    Set up automatic sequence management for all tables.

    This creates triggers that automatically fix sequences after any insert,
    preventing sequence issues permanently.

    Args:
        db: Database session
    """
    logger.info("Setting up automatic sequence management...")

    manager = SequenceManager(db)
    tables = manager.get_tables_with_sequences()

    for table_name in tables:
        create_sequence_fix_trigger(db, table_name)

    logger.info(f"✓ Automatic sequence management set up for {len(tables)} tables")
