#!/usr/bin/env python3
"""
Update machine_name from 'Unknown' to 'Laptop-WT' in usage database.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("/mnt/d/OneDrive/.claude-goblin/usage_history.db")
NEW_MACHINE_NAME = "Laptop-WT"

def main():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)

    try:
        cursor = conn.cursor()

        print("\n" + "="*60)
        print("BEFORE UPDATE - Device Statistics")
        print("="*60)

        # Show current device statistics
        cursor.execute("""
            SELECT
                COALESCE(machine_name, 'NULL') as machine,
                COUNT(*) as record_count,
                SUM(total_tokens) as total_tokens
            FROM usage_records
            GROUP BY machine_name
            ORDER BY total_tokens DESC
        """)

        print("\nusage_records table:")
        for row in cursor.fetchall():
            machine = row[0]
            count = row[1]
            tokens = row[2] or 0
            print(f"  {machine:20s}: {count:8,} records, {tokens:15,} tokens")

        cursor.execute("""
            SELECT
                machine_name,
                COUNT(*) as record_count,
                SUM(total_tokens) as total_tokens
            FROM device_usage_aggregates
            GROUP BY machine_name
            ORDER BY total_tokens DESC
        """)

        print("\ndevice_usage_aggregates table:")
        for row in cursor.fetchall():
            machine = row[0] or 'NULL'
            count = row[1]
            tokens = row[2] or 0
            print(f"  {machine:20s}: {count:8,} records, {tokens:15,} tokens")

        cursor.execute("""
            SELECT
                machine_name,
                COUNT(*) as record_count,
                SUM(total_tokens) as total_tokens
            FROM device_model_aggregates
            GROUP BY machine_name
            ORDER BY total_tokens DESC
        """)

        print("\ndevice_model_aggregates table:")
        for row in cursor.fetchall():
            machine = row[0] or 'NULL'
            count = row[1]
            tokens = row[2] or 0
            print(f"  {machine:20s}: {count:8,} records, {tokens:15,} tokens")

        print("\n" + "="*60)
        print("UPDATING machine_name to 'Laptop-WT'")
        print("="*60)

        # Update usage_records
        cursor.execute("""
            UPDATE usage_records
            SET machine_name = ?
            WHERE machine_name IS NULL
               OR machine_name = ''
               OR machine_name = 'Unknown'
        """, (NEW_MACHINE_NAME,))

        updated_usage_records = cursor.rowcount
        print(f"\nusage_records: Updated {updated_usage_records:,} records")

        # Update device_usage_aggregates
        cursor.execute("""
            UPDATE device_usage_aggregates
            SET machine_name = ?
            WHERE machine_name = 'Unknown'
        """, (NEW_MACHINE_NAME,))

        updated_device_aggregates = cursor.rowcount
        print(f"device_usage_aggregates: Updated {updated_device_aggregates:,} records")

        # Update device_model_aggregates
        cursor.execute("""
            UPDATE device_model_aggregates
            SET machine_name = ?
            WHERE machine_name = 'Unknown'
        """, (NEW_MACHINE_NAME,))

        updated_model_aggregates = cursor.rowcount
        print(f"device_model_aggregates: Updated {updated_model_aggregates:,} records")

        # Commit changes
        conn.commit()
        print("\nChanges committed successfully!")

        print("\n" + "="*60)
        print("AFTER UPDATE - Device Statistics")
        print("="*60)

        # Show updated device statistics
        cursor.execute("""
            SELECT
                COALESCE(machine_name, 'NULL') as machine,
                COUNT(*) as record_count,
                SUM(total_tokens) as total_tokens
            FROM usage_records
            GROUP BY machine_name
            ORDER BY total_tokens DESC
        """)

        print("\nusage_records table:")
        for row in cursor.fetchall():
            machine = row[0]
            count = row[1]
            tokens = row[2] or 0
            print(f"  {machine:20s}: {count:8,} records, {tokens:15,} tokens")

        cursor.execute("""
            SELECT
                machine_name,
                COUNT(*) as record_count,
                SUM(total_tokens) as total_tokens
            FROM device_usage_aggregates
            GROUP BY machine_name
            ORDER BY total_tokens DESC
        """)

        print("\ndevice_usage_aggregates table:")
        for row in cursor.fetchall():
            machine = row[0] or 'NULL'
            count = row[1]
            tokens = row[2] or 0
            print(f"  {machine:20s}: {count:8,} records, {tokens:15,} tokens")

        cursor.execute("""
            SELECT
                machine_name,
                COUNT(*) as record_count,
                SUM(total_tokens) as total_tokens
            FROM device_model_aggregates
            GROUP BY machine_name
            ORDER BY total_tokens DESC
        """)

        print("\ndevice_model_aggregates table:")
        for row in cursor.fetchall():
            machine = row[0] or 'NULL'
            count = row[1]
            tokens = row[2] or 0
            print(f"  {machine:20s}: {count:8,} records, {tokens:15,} tokens")

        print("\n" + "="*60)
        print("UPDATE COMPLETE")
        print("="*60)
        print(f"\nTotal records updated: {updated_usage_records + updated_device_aggregates + updated_model_aggregates:,}")
        print(f"\nAll 'Unknown' machine names have been changed to '{NEW_MACHINE_NAME}'")

    except Exception as e:
        print(f"\nError: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
