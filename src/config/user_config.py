#region Imports
import json
from pathlib import Path
from typing import Optional
#endregion


#region Constants
CONFIG_PATH = Path.home() / ".claude" / "goblin_config.json"
#endregion


#region Functions


def load_config() -> dict:
    """
    Load user configuration from disk.

    Returns:
        Configuration dictionary with user preferences
    """
    if not CONFIG_PATH.exists():
        return get_default_config()

    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return get_default_config()


def save_config(config: dict) -> None:
    """
    Save user configuration to disk.

    Args:
        config: Configuration dictionary to save

    Raises:
        IOError: If config cannot be written
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_default_config() -> dict:
    """
    Get default configuration values.

    Returns:
        Default configuration dictionary
    """
    return {
        "storage_mode": "aggregate",  # "aggregate" or "full"
        "plan_type": "max_20x",  # "pro", "max_5x", or "max_20x"
        "tracking_mode": "both",  # "both", "tokens", or "limits"
        "version": "1.0"
    }


def get_storage_mode() -> str:
    """
    Get the current storage mode setting.

    Returns:
        Either "aggregate" or "full"
    """
    config = load_config()
    return config.get("storage_mode", "aggregate")


def set_storage_mode(mode: str) -> None:
    """
    Set the storage mode.

    Args:
        mode: Either "aggregate" or "full"

    Raises:
        ValueError: If mode is not valid
    """
    if mode not in ["aggregate", "full"]:
        raise ValueError(f"Invalid storage mode: {mode}. Must be 'aggregate' or 'full'")

    config = load_config()
    config["storage_mode"] = mode
    save_config(config)


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


#endregion
