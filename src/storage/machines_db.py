#region Imports
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
#endregion


#region Functions

def get_machines_db_path() -> Path:
    """
    Get the path to machines.db (PC metadata database).

    Returns:
        Path to machines.db in the same directory as usage_history DBs
    """
    from src.storage.snapshot_db import get_default_db_path

    # Get base directory from default DB path
    base_db_path = get_default_db_path()
    machines_db_path = base_db_path.parent / "machines.db"

    return machines_db_path


def init_machines_db(db_path: Optional[Path] = None) -> None:
    """
    Initialize the machines.db database for PC metadata.

    Creates a table to track all registered PCs:
    - machine_name: Hostname or custom name
    - hostname: System hostname
    - registered_date: First registration date
    - last_seen: Last activity date
    - active: Whether this PC is still active (1=active, 0=inactive)

    Args:
        db_path: Path to machines.db file (optional)

    Raises:
        sqlite3.Error: If database initialization fails
    """
    if db_path is None:
        db_path = get_machines_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()

        # Use DELETE mode for OneDrive compatibility
        cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA synchronous=FULL")

        # Create machines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                machine_name TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                registered_date TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)

        conn.commit()
    finally:
        conn.close()


def register_machine(machine_name: str, hostname: str, db_path: Optional[Path] = None) -> None:
    """
    Register a new machine or update last_seen for existing machine.

    Uses INSERT OR REPLACE to handle both new and existing machines:
    - New machine: Creates entry with current timestamp
    - Existing machine: Updates last_seen timestamp

    Args:
        machine_name: Machine name (from user_config or hostname)
        hostname: System hostname
        db_path: Path to machines.db file (optional)

    Raises:
        sqlite3.Error: If database operation fails
    """
    if db_path is None:
        db_path = get_machines_db_path()

    init_machines_db(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Check if machine exists
        cursor.execute("SELECT registered_date FROM machines WHERE machine_name = ?", (machine_name,))
        existing = cursor.fetchone()

        if existing:
            # Update last_seen only
            cursor.execute("""
                UPDATE machines
                SET last_seen = ?, hostname = ?
                WHERE machine_name = ?
            """, (now, hostname, machine_name))
        else:
            # Insert new machine
            cursor.execute("""
                INSERT INTO machines (machine_name, hostname, registered_date, last_seen, active)
                VALUES (?, ?, ?, ?, 1)
            """, (machine_name, hostname, now, now))

        conn.commit()
    finally:
        conn.close()


def get_all_machines(include_inactive: bool = False, db_path: Optional[Path] = None) -> list[dict]:
    """
    Get list of all registered machines.

    Args:
        include_inactive: Include inactive machines (default: False)
        db_path: Path to machines.db file (optional)

    Returns:
        List of machine info dictionaries with keys:
        - machine_name: Machine name
        - hostname: System hostname
        - registered_date: Registration date
        - last_seen: Last activity date
        - active: Active status (1 or 0)

    Raises:
        sqlite3.Error: If database query fails
    """
    if db_path is None:
        db_path = get_machines_db_path()

    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()

        if include_inactive:
            cursor.execute("SELECT * FROM machines ORDER BY last_seen DESC")
        else:
            cursor.execute("SELECT * FROM machines WHERE active = 1 ORDER BY last_seen DESC")

        machines = []
        for row in cursor.fetchall():
            machines.append({
                "machine_name": row[0],
                "hostname": row[1],
                "registered_date": row[2],
                "last_seen": row[3],
                "active": row[4],
            })

        return machines
    finally:
        conn.close()


def deactivate_machine(machine_name: str, db_path: Optional[Path] = None) -> None:
    """
    Mark a machine as inactive.

    Inactive machines are not included in queries by default,
    but their data is preserved.

    Args:
        machine_name: Machine name to deactivate
        db_path: Path to machines.db file (optional)

    Raises:
        sqlite3.Error: If database operation fails
    """
    if db_path is None:
        db_path = get_machines_db_path()

    init_machines_db(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE machines SET active = 0 WHERE machine_name = ?", (machine_name,))
        conn.commit()
    finally:
        conn.close()


def activate_machine(machine_name: str, db_path: Optional[Path] = None) -> None:
    """
    Mark a machine as active.

    Args:
        machine_name: Machine name to activate
        db_path: Path to machines.db file (optional)

    Raises:
        sqlite3.Error: If database operation fails
    """
    if db_path is None:
        db_path = get_machines_db_path()

    init_machines_db(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE machines SET active = 1 WHERE machine_name = ?", (machine_name,))
        conn.commit()
    finally:
        conn.close()


#endregion
