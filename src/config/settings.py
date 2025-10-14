#region Imports
from pathlib import Path
from typing import Final

from src.utils.security import validate_file_path
#endregion


#region Constants
# Claude data directory
CLAUDE_DATA_DIR: Final[Path] = Path.home() / ".claude" / "projects"

# Default refresh interval for dashboard (seconds)
DEFAULT_REFRESH_INTERVAL: Final[int] = 5

# Number of days to show in activity graph
ACTIVITY_GRAPH_DAYS: Final[int] = 365

# Graph dimensions
GRAPH_WEEKS: Final[int] = 52  # 52 weeks = 364 days (close to 365)
GRAPH_DAYS_PER_WEEK: Final[int] = 7
#endregion


#region Functions


def get_claude_jsonl_files() -> list[Path]:
    """
    Get all JSONL files from Claude's project data directory.
    
    Security: Excludes symbolic links and validates paths remain within
    the base directory to prevent path traversal attacks.

    Returns:
        List of Path objects pointing to JSONL files

    Raises:
        FileNotFoundError: If Claude data directory doesn't exist
    """
    if not CLAUDE_DATA_DIR.exists():
        raise FileNotFoundError(
            f"Claude data directory not found at {CLAUDE_DATA_DIR}. "
            "Make sure Claude Code has been run at least once."
        )

    # SECURITY: Collect files while validating against path traversal
    validated_files = []
    for path in CLAUDE_DATA_DIR.rglob("*.jsonl"):
        # Skip symbolic links to prevent following them outside the directory
        if path.is_symlink():
            continue
        
        # Validate that resolved path is within CLAUDE_DATA_DIR
        is_valid, _ = validate_file_path(path, CLAUDE_DATA_DIR)
        if is_valid:
            validated_files.append(path)
    
    return validated_files
#endregion
