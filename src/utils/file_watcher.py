#region Imports
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
#endregion


#region Classes

class JSONLFileHandler(FileSystemEventHandler):
    """
    File system event handler for JSONL files.

    Monitors Claude Code project directories for changes to .jsonl files
    and sets a flag when changes are detected (instead of triggering immediate callback).
    """

    def __init__(self):
        """Initialize the JSONL file handler."""
        super().__init__()
        self.has_changes = False
        self.last_change_time = 0.0

    def on_modified(self, event: FileModifiedEvent) -> None:
        """
        Called when a file is modified.

        Args:
            event: File modification event
        """
        if event.is_directory:
            return

        if event.src_path.endswith('.jsonl'):
            self.has_changes = True
            self.last_change_time = time.time()

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Called when a file is created.

        Args:
            event: File creation event
        """
        if event.is_directory:
            return

        if event.src_path.endswith('.jsonl'):
            self.has_changes = True
            self.last_change_time = time.time()

    def get_and_reset_changes(self) -> bool:
        """
        Check if changes occurred and reset the flag.

        Returns:
            True if changes were detected since last check, False otherwise
        """
        if self.has_changes:
            self.has_changes = False
            return True
        return False


class FileWatcher:
    """
    File watcher for monitoring Claude Code JSONL files.

    Uses watchdog to efficiently monitor file system changes without polling.
    Changes are tracked via a flag that can be checked periodically.
    """

    def __init__(self, watch_path: Path):
        """
        Initialize the file watcher.

        Args:
            watch_path: Directory to watch for changes
        """
        self.watch_path = watch_path
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[JSONLFileHandler] = None

    def start(self) -> None:
        """
        Start watching for file changes.

        Raises:
            FileNotFoundError: If watch_path doesn't exist
        """
        if not self.watch_path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {self.watch_path}")

        self.event_handler = JSONLFileHandler()
        self.observer = Observer()

        # Watch recursively (includes subdirectories)
        self.observer.schedule(self.event_handler, str(self.watch_path), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def is_alive(self) -> bool:
        """
        Check if the watcher is running.

        Returns:
            True if watcher is active, False otherwise
        """
        return self.observer is not None and self.observer.is_alive()

    def get_and_reset_changes(self) -> bool:
        """
        Check if file changes occurred since last check and reset the flag.

        Returns:
            True if changes were detected, False otherwise
        """
        if self.event_handler:
            return self.event_handler.get_and_reset_changes()
        return False


#endregion


#region Functions

def watch_claude_files() -> FileWatcher:
    """
    Create a file watcher for Claude Code JSONL files.

    The watcher monitors file changes but doesn't trigger immediate callbacks.
    Instead, use `watcher.get_and_reset_changes()` to check for changes periodically.

    Returns:
        FileWatcher instance

    Example:
        >>> watcher = watch_claude_files()
        >>> watcher.start()
        >>>
        >>> # In your main loop:
        >>> if watcher.get_and_reset_changes():
        ...     print("Files changed!")
        >>>
        >>> watcher.stop()
    """
    from src.config.settings import CLAUDE_DATA_DIR
    return FileWatcher(CLAUDE_DATA_DIR)


#endregion
