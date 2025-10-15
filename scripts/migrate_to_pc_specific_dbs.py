#!/usr/bin/env python3
"""
Migrate data from single usage_history.db to PC-specific DB files.

This script:
1. Reads the old usage_history.db file
2. Groups records by machine_name
3. Writes each group to usage_history_{machine_name}.db
4. Renames the old DB to usage_history.db.backup
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from datetime import datetime, timezone

from src.storage.snapshot_db import get_storage_dir
from src.storage.machines_db import init_machines_db, register_machine


def migrate_data():
    """Migrate from single DB to PC-specific DBs."""
    storage_dir = get_storage_dir()
    old_db_path = storage_dir / "usage_history.db"

    if not old_db_path.exists():
        print(f"No old database found at {old_db_path}")
        print("Migration not needed.")
        return

    print(f"Found old database: {old_db_path}")

    # Initialize machines.db
    machines_db_path = storage_dir / "machines.db"
    init_machines_db(machines_db_path)
    print(f"Initialized machines.db: {machines_db_path}")

    # Connect to old DB
    old_conn = sqlite3.connect(old_db_path, timeout=30.0)
    try:
        cursor = old_conn.cursor()

        # Get list of distinct machines
        cursor.execute("SELECT DISTINCT COALESCE(machine_name, 'Unknown') FROM usage_records ORDER BY machine_name")
        machines = [row[0] for row in cursor.fetchall()]

        print(f"\nFound {len(machines)} machine(s): {', '.join(machines)}")

        # Process each machine
        for machine_name in machines:
            print(f"\nProcessing {machine_name}...")

            # Create new DB for this machine
            new_db_path = storage_dir / f"usage_history_{machine_name}.db"

            # Import init_database from snapshot_db
            from src.storage.snapshot_db import init_database
            init_database(new_db_path)

            # Connect to new DB
            new_conn = sqlite3.connect(new_db_path, timeout=30.0)
            try:
                new_cursor = new_conn.cursor()

                # Copy usage_records for this machine
                cursor.execute("""
                    SELECT * FROM usage_records
                    WHERE COALESCE(machine_name, 'Unknown') = ?
                """, (machine_name,))

                records = cursor.fetchall()
                print(f"  Found {len(records)} records")

                if records:
                    # Get column names
                    cursor.execute("PRAGMA table_info(usage_records)")
                    columns = [row[1] for row in cursor.fetchall()]
                    placeholders = ','.join(['?' for _ in columns])

                    # Insert records into new DB
                    new_cursor.executemany(
                        f"INSERT OR IGNORE INTO usage_records ({','.join(columns)}) VALUES ({placeholders})",
                        records
                    )

                    # Copy daily_snapshots (aggregate all machines' data)
                    cursor.execute("SELECT * FROM daily_snapshots")
                    snapshots = cursor.fetchall()

                    if snapshots:
                        cursor.execute("PRAGMA table_info(daily_snapshots)")
                        snap_columns = [row[1] for row in cursor.fetchall()]
                        snap_placeholders = ','.join(['?' for _ in snap_columns])

                        new_cursor.executemany(
                            f"INSERT OR IGNORE INTO daily_snapshots ({','.join(snap_columns)}) VALUES ({snap_placeholders})",
                            snapshots
                        )

                    # Copy limits_snapshots
                    cursor.execute("SELECT * FROM limits_snapshots")
                    limits = cursor.fetchall()

                    if limits:
                        cursor.execute("PRAGMA table_info(limits_snapshots)")
                        limits_columns = [row[1] for row in cursor.fetchall()]
                        limits_placeholders = ','.join(['?' for _ in limits_columns])

                        new_cursor.executemany(
                            f"INSERT OR IGNORE INTO limits_snapshots ({','.join(limits_columns)}) VALUES ({limits_placeholders})",
                            limits
                        )

                    # Copy model_pricing (shared across all DBs)
                    cursor.execute("SELECT * FROM model_pricing")
                    pricing = cursor.fetchall()

                    if pricing:
                        cursor.execute("PRAGMA table_info(model_pricing)")
                        pricing_columns = [row[1] for row in cursor.fetchall()]
                        pricing_placeholders = ','.join(['?' for _ in pricing_columns])

                        new_cursor.executemany(
                            f"INSERT OR REPLACE INTO model_pricing ({','.join(pricing_columns)}) VALUES ({pricing_placeholders})",
                            pricing
                        )

                    # Copy user_preferences (shared across all DBs)
                    try:
                        cursor.execute("SELECT * FROM user_preferences")
                        prefs = cursor.fetchall()

                        if prefs:
                            cursor.execute("PRAGMA table_info(user_preferences)")
                            prefs_columns = [row[1] for row in cursor.fetchall()]
                            prefs_placeholders = ','.join(['?' for _ in prefs_columns])

                            new_cursor.executemany(
                                f"INSERT OR REPLACE INTO user_preferences ({','.join(prefs_columns)}) VALUES ({prefs_placeholders})",
                                prefs
                            )
                    except sqlite3.OperationalError:
                        # user_preferences table might not exist in old DB
                        pass

                    new_conn.commit()
                    print(f"  ✓ Migrated to {new_db_path.name}")

                # Register machine in machines.db
                # Try to get hostname from records if available
                cursor.execute("""
                    SELECT DISTINCT folder FROM usage_records
                    WHERE COALESCE(machine_name, 'Unknown') = ?
                    LIMIT 1
                """, (machine_name,))
                result = cursor.fetchone()
                hostname = machine_name  # Default to machine_name if no other info

                register_machine(machine_name, hostname, machines_db_path)
                print(f"  ✓ Registered in machines.db")

            finally:
                new_conn.close()

        # Backup old DB
        backup_path = old_db_path.parent / f"usage_history.db.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        old_db_path.rename(backup_path)
        print(f"\n✓ Backed up old database to: {backup_path}")

        print("\n✓ Migration complete!")
        print(f"\nCreated {len(machines)} PC-specific database(s):")
        for machine_name in machines:
            db_path = storage_dir / f"usage_history_{machine_name}.db"
            print(f"  - {db_path}")

    finally:
        old_conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Single DB → PC-specific DBs")
    print("=" * 60)

    try:
        migrate_data()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
