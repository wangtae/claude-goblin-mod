"""
Automatic backup system for usage database.

Provides automatic daily backups with configurable retention policies.
Monthly backups (1st of each month) can be preserved permanently.
"""
#region Imports
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
#endregion


#region Functions


def auto_backup() -> bool:
    """
    Automatically backup the database if needed.

    This is the main entry point for automatic backups.
    Performs backup, cleanup, and updates configuration.

    Returns:
        True if backup was performed, False if skipped or failed
    """
    try:
        from src.config.user_config import (
            get_backup_enabled,
            get_backup_keep_monthly,
            get_backup_retention_days,
            set_last_backup_date,
        )
        from src.storage.snapshot_db import DEFAULT_DB_PATH

        # Check if backups are enabled
        if not get_backup_enabled():
            return False

        # Check if database exists
        if not DEFAULT_DB_PATH.exists():
            return False

        # Check if backup is needed today
        if not should_backup_today():
            return False

        # Create backup
        backup_path = create_backup(DEFAULT_DB_PATH)
        if not backup_path:
            return False

        # Update last backup date
        today = datetime.now().strftime("%Y-%m-%d")
        set_last_backup_date(today)

        # Cleanup old backups
        retention_days = get_backup_retention_days()
        keep_monthly = get_backup_keep_monthly()
        cleanup_old_backups(DEFAULT_DB_PATH, retention_days, keep_monthly)

        return True

    except Exception:
        # Silently fail - backup errors should not affect program execution
        return False


def should_backup_today() -> bool:
    """
    Check if a backup should be performed today.

    Returns True if:
    - No backup has been performed yet (last_backup_date is None), OR
    - Last backup date is before today

    Returns:
        True if backup is needed, False otherwise
    """
    from src.config.user_config import get_last_backup_date

    last_backup = get_last_backup_date()

    # Never backed up before
    if last_backup is None:
        return True

    # Compare with today
    try:
        last_date = datetime.strptime(last_backup, "%Y-%m-%d").date()
        today = datetime.now().date()
        return last_date < today
    except (ValueError, TypeError):
        # Invalid date format, perform backup
        return True


def create_backup(db_path: Path) -> Optional[Path]:
    """
    Create a backup of the database file.

    Backup location: Same directory as database, in /backups/ subdirectory
    Filename format:
    - Regular: usage_history_backup_YYYYMMDD.db
    - Monthly (1st): usage_history_backup_YYYYMMDD_monthly.db

    Args:
        db_path: Path to the database file

    Returns:
        Path to created backup file, or None if failed
    """
    try:
        # Ensure database exists
        if not db_path.exists():
            return None

        # Create backups directory
        backups_dir = db_path.parent / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")

        # Add "_monthly" suffix for 1st of the month
        if today.day == 1:
            backup_filename = f"usage_history_backup_{date_str}_monthly.db"
        else:
            backup_filename = f"usage_history_backup_{date_str}.db"

        backup_path = backups_dir / backup_filename

        # Copy database file
        shutil.copy2(db_path, backup_path)

        return backup_path

    except Exception:
        return None


def cleanup_old_backups(
    db_path: Path,
    retention_days: int,
    keep_monthly: bool = True
) -> int:
    """
    Delete backup files older than retention period.

    Monthly backups (files with "_monthly" suffix) can be preserved
    based on the keep_monthly parameter.

    Args:
        db_path: Path to the database file (used to find backups directory)
        retention_days: Number of days to keep backups
        keep_monthly: If True, preserve monthly backups permanently

    Returns:
        Number of backup files deleted
    """
    try:
        backups_dir = db_path.parent / "backups"

        if not backups_dir.exists():
            return 0

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        deleted_count = 0

        # Iterate through all backup files
        for backup_file in backups_dir.glob("usage_history_backup_*.db"):
            # Skip monthly backups if configured
            if keep_monthly and "_monthly" in backup_file.name:
                continue

            # Extract date from filename
            try:
                # Format: usage_history_backup_YYYYMMDD.db or usage_history_backup_YYYYMMDD_monthly.db
                filename_parts = backup_file.stem.split("_")
                date_str = filename_parts[3]  # YYYYMMDD

                # Parse date
                backup_date = datetime.strptime(date_str, "%Y%m%d")

                # Delete if older than retention period
                if backup_date < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1

            except (ValueError, IndexError):
                # Invalid filename format, skip
                continue

        return deleted_count

    except Exception:
        return 0


def list_backups(db_path: Path) -> list[dict]:
    """
    Get list of all backup files with metadata.

    Args:
        db_path: Path to the database file

    Returns:
        List of dictionaries containing backup metadata:
        - path: Path to backup file
        - date: Backup date (datetime object)
        - is_monthly: True if this is a monthly backup
        - size: File size in bytes
    """
    try:
        backups_dir = db_path.parent / "backups"

        if not backups_dir.exists():
            return []

        backups = []

        for backup_file in sorted(backups_dir.glob("usage_history_backup_*.db")):
            try:
                # Extract date from filename
                filename_parts = backup_file.stem.split("_")
                date_str = filename_parts[3]  # YYYYMMDD
                backup_date = datetime.strptime(date_str, "%Y%m%d")

                # Check if monthly
                is_monthly = "_monthly" in backup_file.name

                # Get file size
                size = backup_file.stat().st_size

                backups.append({
                    "path": backup_file,
                    "date": backup_date,
                    "is_monthly": is_monthly,
                    "size": size,
                })

            except (ValueError, IndexError):
                # Invalid filename format, skip
                continue

        # Sort by date (newest first)
        backups.sort(key=lambda x: x["date"], reverse=True)

        return backups

    except Exception:
        return []


def get_backup_directory(db_path: Path) -> Path:
    """
    Get the backups directory path.

    Args:
        db_path: Path to the database file

    Returns:
        Path to backups directory
    """
    return db_path.parent / "backups"


#endregion
