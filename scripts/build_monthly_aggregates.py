#!/usr/bin/env python3
"""
Build monthly device statistics aggregates for all machines.

This script scans all PC-specific databases and creates monthly aggregates
for faster device statistics queries.

Run this once to build initial aggregates for existing historical data.
After that, aggregates are automatically maintained by save_snapshot().
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.snapshot_db import get_all_machine_db_paths, update_monthly_device_stats


def main():
    """Build monthly aggregates for all machines."""
    print("=" * 70)
    print("Building Monthly Device Statistics Aggregates")
    print("=" * 70)

    # Get all machine DB paths
    machine_db_paths = get_all_machine_db_paths()

    if not machine_db_paths:
        print("\n❌ No machine databases found.")
        print("   Make sure you have at least one usage_history_{machine}.db file.")
        return 1

    print(f"\n📊 Found {len(machine_db_paths)} machine database(s):\n")
    for machine_name, db_path in machine_db_paths:
        if db_path.exists():
            print(f"  ✓ {machine_name:20s} ({db_path.name})")
        else:
            print(f"  ✗ {machine_name:20s} (NOT FOUND)")

    print("\n" + "=" * 70)
    print("Processing each machine...")
    print("=" * 70)

    success_count = 0
    for machine_name, db_path in machine_db_paths:
        if not db_path.exists():
            print(f"\n⏭️  Skipping {machine_name} (DB not found)")
            continue

        print(f"\n📈 Processing {machine_name}...")
        try:
            # Update monthly aggregates for this machine
            update_monthly_device_stats(db_path)
            print(f"  ✓ Successfully built aggregates for {machine_name}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ Failed to process {machine_name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  Total machines: {len(machine_db_paths)}")
    print(f"  Successfully processed: {success_count}")
    print(f"  Failed: {len(machine_db_paths) - success_count}")

    print("\n✅ Done! Device statistics queries will now be much faster.")
    print("   Monthly aggregates will be automatically maintained going forward.")

    return 0 if success_count == len(machine_db_paths) else 1


if __name__ == "__main__":
    sys.exit(main())
