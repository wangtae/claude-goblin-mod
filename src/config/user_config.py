#region Imports
import json
import shutil
from pathlib import Path
from typing import Optional
#endregion


#region Constants
_BASE_DIR = Path.home() / ".claude"
APP_DATA_DIR = _BASE_DIR / "claude-goblin-mod"
_CONFIG_FILENAME = "claude-goblin.json"
LEGACY_CONFIG_FILENAMES = [
    "claude-goblin.json",
    "goblin_config.json",  # Original filename
]
LEGACY_CONFIG_PATHS = [_BASE_DIR / name for name in LEGACY_CONFIG_FILENAMES]
CONFIG_PATH = APP_DATA_DIR / _CONFIG_FILENAME
#endregion


#region Helpers

def _ensure_app_dir() -> bool:
    """Ensure the application data directory exists. Returns True if available."""
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except (PermissionError, OSError):
        return False


def _migrate_legacy_config() -> None:
    """
    Move legacy config file from ~/.claude/claude-goblin.json to the new location.

    If migration fails (e.g., cross-device move issues), falls back to copying.
    """
    if CONFIG_PATH.exists():
        return

    if not _ensure_app_dir():
        return

    for legacy_path in LEGACY_CONFIG_PATHS:
        if not legacy_path.exists():
            continue

        try:
            shutil.move(str(legacy_path), str(CONFIG_PATH))
            return
        except (OSError, shutil.Error):
            # Try copy + cleanup as fallback
            try:
                shutil.copy2(str(legacy_path), str(CONFIG_PATH))
            except (OSError, shutil.Error):
                continue

            try:
                legacy_path.unlink()
            except OSError:
                pass
            return


#endregion


#region Functions


def load_config() -> dict:
    """
    Load user configuration from disk.

    Returns:
        Configuration dictionary with user preferences
    """
    _migrate_legacy_config()

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return get_default_config()

    for legacy_path in LEGACY_CONFIG_PATHS:
        if not legacy_path.exists():
            continue
        try:
            with open(legacy_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return get_default_config()

    return get_default_config()


def save_config(config: dict) -> None:
    """
    Save user configuration to disk.

    Args:
        config: Configuration dictionary to save

    Raises:
        IOError: If config cannot be written
    """
    target_path = CONFIG_PATH if _ensure_app_dir() else None
    if target_path is None:
        existing = next((p for p in LEGACY_CONFIG_PATHS if p.exists()), None)
        target_path = existing or LEGACY_CONFIG_PATHS[-1]

    with open(target_path, "w") as f:
        json.dump(config, f, indent=2)


def get_default_config() -> dict:
    """
    Get default configuration values.

    Returns:
        Default configuration dictionary
    """
    return {
        "plan_type": "max_20x",  # "pro", "max_5x", or "max_20x"
        "tracking_mode": "both",  # "both", "tokens", or "limits"
        "db_path": None,  # Custom database path (None = auto-detect)
        "machine_name": None,  # Custom machine name (None = use hostname)
        "backup_enabled": True,  # Enable automatic backups
        "backup_keep_monthly": True,  # Keep monthly backups (1st of each month)
        "backup_retention_days": 30,  # Number of days to keep backups
        "last_backup_date": None,  # Last backup date (YYYY-MM-DD)
        "version": "1.0"
    }


def get_storage_mode() -> str:
    """
    Get the current storage mode setting.

    Storage mode is now fixed to "full" for data safety and integrity.
    Full mode prevents duplicate aggregation issues across multiple devices.

    Returns:
        Always returns "full"
    """
    return "full"


def get_plan_type() -> str:
    """
    Get the current Claude Code plan type.

    Returns:
        One of "pro", "max_5x", or "max_20x"
    """
    config = load_config()
    return config.get("plan_type", "max_20x")


def set_plan_type(plan: str) -> None:
    """
    Set the Claude Code plan type.

    Args:
        plan: One of "pro", "max_5x", or "max_20x"

    Raises:
        ValueError: If plan is not valid
    """
    if plan not in ["pro", "max_5x", "max_20x"]:
        raise ValueError(f"Invalid plan type: {plan}. Must be 'pro', 'max_5x', or 'max_20x'")

    config = load_config()
    config["plan_type"] = plan
    save_config(config)


def get_tracking_mode() -> str:
    """
    Get the current tracking mode setting.

    Returns:
        One of "both", "tokens", or "limits"
    """
    config = load_config()
    return config.get("tracking_mode", "both")


def set_tracking_mode(mode: str) -> None:
    """
    Set the tracking mode for data capture and visualization.

    Args:
        mode: One of "both", "tokens", or "limits"

    Raises:
        ValueError: If mode is not valid
    """
    if mode not in ["both", "tokens", "limits"]:
        raise ValueError(f"Invalid tracking mode: {mode}. Must be 'both', 'tokens', or 'limits'")

    config = load_config()
    config["tracking_mode"] = mode
    save_config(config)


def get_db_path() -> Optional[str]:
    """
    Get the custom database path from config.

    Returns:
        Custom database path or None if not set (use auto-detect)
    """
    config = load_config()
    return config.get("db_path")


def set_db_path(path: str) -> None:
    """
    Set a custom database path.

    Args:
        path: Full path to database file (e.g., /mnt/d/OneDrive/.claude-goblin/usage_history.db)

    Raises:
        ValueError: If path is invalid
    """
    from pathlib import Path

    # Validate path
    db_path = Path(path)

    # Ensure parent directory exists or can be created
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        raise ValueError(f"Cannot create directory {db_path.parent}: {e}")

    config = load_config()
    config["db_path"] = str(db_path)
    save_config(config)


def clear_db_path() -> None:
    """
    Clear custom database path (revert to auto-detect).
    """
    config = load_config()
    config["db_path"] = None
    save_config(config)


def get_machine_name() -> str:
    """
    Get the machine name for this device.

    Returns:
        Custom machine name if set, otherwise hostname
    """
    import socket

    config = load_config()
    custom_name = config.get("machine_name")

    # Use custom name if set, otherwise fallback to hostname
    if custom_name:
        return custom_name

    # Get hostname
    try:
        hostname = socket.gethostname()
        return hostname
    except:
        return "unknown"


def set_machine_name(name: str) -> None:
    """
    Set a custom machine name for this PC.

    Args:
        name: Friendly machine name (e.g., "Home-Desktop", "Work-Laptop")
    """
    config = load_config()
    config["machine_name"] = name
    save_config(config)


def clear_machine_name() -> None:
    """
    Clear custom machine name (revert to hostname).
    """
    config = load_config()
    config["machine_name"] = None
    save_config(config)


def get_backup_enabled() -> bool:
    """
    Get whether automatic backups are enabled.

    Returns:
        True if backups are enabled, False otherwise
    """
    config = load_config()
    return config.get("backup_enabled", True)


def set_backup_enabled(enabled: bool) -> None:
    """
    Enable or disable automatic backups.

    Args:
        enabled: True to enable backups, False to disable
    """
    config = load_config()
    config["backup_enabled"] = enabled
    save_config(config)


def get_backup_keep_monthly() -> bool:
    """
    Get whether monthly backups (1st of each month) should be kept permanently.

    Returns:
        True if monthly backups should be kept, False otherwise
    """
    config = load_config()
    return config.get("backup_keep_monthly", True)


def set_backup_keep_monthly(keep: bool) -> None:
    """
    Set whether to keep monthly backups permanently.

    Args:
        keep: True to keep monthly backups, False to delete them normally
    """
    config = load_config()
    config["backup_keep_monthly"] = keep
    save_config(config)


def get_backup_retention_days() -> int:
    """
    Get the number of days to keep backup files.

    Returns:
        Number of days to keep backups (default: 30)
    """
    config = load_config()
    return config.get("backup_retention_days", 30)


def set_backup_retention_days(days: int) -> None:
    """
    Set the number of days to keep backup files.

    Args:
        days: Number of days (minimum 1)

    Raises:
        ValueError: If days is less than 1
    """
    if days < 1:
        raise ValueError("Backup retention days must be at least 1")

    config = load_config()
    config["backup_retention_days"] = days
    save_config(config)


def get_last_backup_date() -> Optional[str]:
    """
    Get the date of the last successful backup.

    Returns:
        Last backup date in YYYY-MM-DD format, or None if never backed up
    """
    config = load_config()
    return config.get("last_backup_date")


def set_last_backup_date(date_str: str) -> None:
    """
    Set the date of the last successful backup.

    Args:
        date_str: Date in YYYY-MM-DD format
    """
    config = load_config()
    config["last_backup_date"] = date_str
    save_config(config)


#region Public helpers

def get_app_data_dir() -> Path:
    """
    Return the base directory for claude-goblin-mod data (~/.claude/claude-goblin-mod).
    """
    _ensure_app_dir()
    return APP_DATA_DIR


#endregion


#endregion
