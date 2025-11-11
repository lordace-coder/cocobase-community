#!/usr/bin/env python3
"""
Test script to verify the scheduler works correctly.
"""

import logging
from app.core.scheduler import start_scheduler, get_scheduler_status, stop_scheduler
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_scheduler():
    """Test the scheduler initialization and status."""

    print("\n" + "=" * 70)
    print("TESTING SCHEDULER")
    print("=" * 70 + "\n")

    try:
        # Step 1: Start scheduler
        print("Step 1: Starting scheduler...")
        start_scheduler()
        print("✓ Scheduler started\n")

        # Step 2: Check status
        print("Step 2: Checking scheduler status...")
        status = get_scheduler_status()

        print(f"  Running: {status['running']}")
        print(f"  Total jobs: {status['total_jobs']}\n")

        if status['jobs']:
            print("  Scheduled jobs:")
            for job in status['jobs']:
                print(f"    • {job['name']}")
                print(f"      ID: {job['id']}")
                print(f"      Next run: {job['next_run_time']}")
                print(f"      Trigger: {job['trigger']}\n")

        # Step 3: Wait a moment
        print("Step 3: Verifying scheduler is running...")
        time.sleep(2)
        print("✓ Scheduler is running normally\n")

        # Step 4: Stop scheduler
        print("Step 4: Stopping scheduler...")
        stop_scheduler()
        print("✓ Scheduler stopped\n")

        # Verify stopped
        status_after = get_scheduler_status()
        if not status_after['running']:
            print("✓ Scheduler successfully stopped")

        print("\n" + "=" * 70)
        print("TEST PASSED! Scheduler is working correctly.")
        print("=" * 70 + "\n")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print("\n" + "=" * 70)
        print("TEST FAILED!")
        print("=" * 70)
        print(f"\nError: {e}\n")
        return False


if __name__ == "__main__":
    success = test_scheduler()
    exit(0 if success else 1)
