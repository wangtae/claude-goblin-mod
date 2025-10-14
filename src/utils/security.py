#region Imports
import os
import re
from pathlib import Path
from typing import Optional
#endregion


#region Constants
# DEBUG mode for detailed error messages
DEBUG = os.getenv("CCG_DEBUG", "false").lower() == "true"

# System directories that should never be written to
FORBIDDEN_WRITE_DIRS = [
    Path("/etc"),
    Path("/bin"),
    Path("/sbin"),
    Path("/usr/bin"),
    Path("/usr/sbin"),
    Path("/sys"),
    Path("/proc"),
    Path("/boot"),
    Path("/dev"),
    Path("C:\\Windows"),
    Path("C:\\Program Files"),
    Path("C:\\Program Files (x86)"),
    Path("C:\\ProgramData"),
]
#endregion


#region Functions


def validate_sound_name(sound_name: str) -> bool:
    """
    Validate that a sound name is safe for use in system commands.
    
    Only allows alphanumeric characters, hyphens, and underscores.
    This prevents command injection through sound names.
    
    Args:
        sound_name: The sound name to validate
        
    Returns:
        True if the sound name is safe, False otherwise
        
    Examples:
        >>> validate_sound_name("alert")
        True
        >>> validate_sound_name("my-sound")
        True
        >>> validate_sound_name("sound_1")
        True
        >>> validate_sound_name("sound; rm -rf /")
        False
        >>> validate_sound_name("../etc/passwd")
        False
    """
    if not sound_name:
        return False
    
    # Allow only alphanumeric, hyphens, and underscores
    # Maximum length of 64 characters
    pattern = r'^[a-zA-Z0-9_-]{1,64}$'
    return bool(re.match(pattern, sound_name))


def validate_output_path(path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate that an output file path is safe to write to.
    
    Checks for:
    - Path traversal attempts
    - Writes to system directories
    - Symbolic link attacks
    
    Args:
        path: The path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_output_path(Path("/tmp/output.png"))
        (True, None)
        >>> validate_output_path(Path("/etc/passwd"))
        (False, "Cannot write to system directory")
    """
    try:
        # Resolve to absolute path (follows symlinks)
        abs_path = path.resolve()
        
        # Check if trying to write to forbidden directories
        for forbidden in FORBIDDEN_WRITE_DIRS:
            try:
                # Check if abs_path is within or is the forbidden directory
                abs_path.relative_to(forbidden)
                return False, f"Cannot write to system directory: {forbidden}"
            except ValueError:
                # Not in this forbidden directory, continue checking
                continue
        
        # Check if parent directory exists or can be created
        parent = abs_path.parent
        if not parent.exists():
            # Check if we can create parent directory
            try:
                # Don't actually create it, just check permissions
                # by checking parent's parent
                if parent.parent.exists() and not os.access(parent.parent, os.W_OK):
                    return False, "Parent directory is not writable"
            except (OSError, PermissionError):
                return False, "Cannot access parent directory"
        elif not os.access(parent, os.W_OK):
            return False, "Directory is not writable"
        
        # Check if file exists and is a symlink
        if abs_path.exists() and abs_path.is_symlink():
            return False, "Cannot overwrite symbolic links"
        
        return True, None
        
    except (OSError, RuntimeError, ValueError) as e:
        return False, f"Invalid path: {e}"


def validate_file_path(path: Path, base_dir: Path) -> tuple[bool, Optional[str]]:
    """
    Validate that a file path is within the expected base directory.
    
    Prevents path traversal and symlink attacks when reading files.
    
    Args:
        path: The file path to validate
        base_dir: The base directory that path must be within
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> base = Path("/home/user/.claude")
        >>> validate_file_path(Path("/home/user/.claude/data.jsonl"), base)
        (True, None)
        >>> validate_file_path(Path("/etc/passwd"), base)
        (False, "Path is outside base directory")
    """
    try:
        # Resolve both paths to absolute
        abs_path = path.resolve()
        abs_base = base_dir.resolve()
        
        # Check if it's a symlink
        if path.is_symlink():
            return False, "Cannot follow symbolic links"
        
        # Check if resolved path is within base directory
        try:
            abs_path.relative_to(abs_base)
            return True, None
        except ValueError:
            return False, f"Path is outside base directory: {abs_base}"
            
    except (OSError, RuntimeError) as e:
        return False, f"Invalid path: {e}"


def sanitize_error_message(error: Exception, context: str = "") -> str:
    """
    Sanitize error messages to avoid exposing sensitive system information.
    
    In DEBUG mode, returns full error details.
    In production mode, returns generic error with context.
    
    Args:
        error: The exception to sanitize
        context: Additional context about what operation failed
        
    Returns:
        Sanitized error message
        
    Examples:
        >>> sanitize_error_message(FileNotFoundError("/secret/path/file.txt"), "reading file")
        "Error reading file: File not found"
    """
    if DEBUG:
        # In debug mode, return full error details
        import traceback
        return f"{context}: {error}\n{traceback.format_exc()}"
    
    # In production, return generic error without exposing paths
    error_type = type(error).__name__
    
    # Generic messages for common errors
    generic_messages = {
        "FileNotFoundError": "File not found",
        "PermissionError": "Permission denied",
        "OSError": "System error",
        "ValueError": "Invalid value",
        "RuntimeError": "Operation failed",
    }
    
    message = generic_messages.get(error_type, "An error occurred")
    
    if context:
        return f"Error {context}: {message}"
    return message


def generate_safe_filename(base_name: str, extension: str, include_pid: bool = False) -> str:
    """
    Generate a safe, unique filename with timestamp.
    
    Prevents race conditions and filename conflicts by including timestamp
    and optionally process ID.
    
    Args:
        base_name: Base name for the file (will be sanitized)
        extension: File extension (without dot)
        include_pid: Whether to include process ID for extra uniqueness
        
    Returns:
        Safe filename with timestamp
        
    Examples:
        >>> generate_safe_filename("backup", "db")
        "backup_20250114_123456.db"
        >>> generate_safe_filename("backup", "db", include_pid=True)
        "backup_20250114_123456_12345.db"
    """
    from datetime import datetime
    
    # Sanitize base name (remove unsafe characters)
    safe_base = re.sub(r'[^\w\-]', '_', base_name)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Include PID if requested
    if include_pid:
        pid = os.getpid()
        return f"{safe_base}_{timestamp}_{pid}.{extension}"
    
    return f"{safe_base}_{timestamp}.{extension}"


#endregion