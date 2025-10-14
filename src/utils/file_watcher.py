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
    and triggers a callback when changes are detected.
    """

    def __init__(self, callback: Callable[[], None], debounce_seconds: float = 1.0):
        """
        Initialize the JSONL file handler.

        Args:
            callback: Function to call when JSONL files change
            debounce_seconds: Minimum seconds between callback invocations (prevents rapid-fire updates)
        """
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.last_triggered = 0.0

    def on_modified(self, event: FileModifiedEvent) -> None:
        """
        Called when a file is modified.

        Args:
            event: File modification event
        """
        if event.is_directory:
            return

        if event.src_path.endswith('.jsonl'):
            self._trigger_callback()

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Called when a file is created.

        Args:
            event: File creation event
        """
        if event.is_directory:
            return

        if event.src_path.endswith('.jsonl'):
            self._trigger_callback()

    def _trigger_callback(self) -> None:
        """
        Trigger the callback with debouncing.

        Prevents rapid-fire callbacks when multiple files change simultaneously.
        """
        current_time = time.time()

        # Debounce: only trigger if enough time has passed since last trigger
        if current_time - self.last_triggered >= self.debounce_seconds:
            self.last_triggered = current_time
            self.callback()


class FileWatcher:
    """
    File watcher for monitoring Claude Code JSONL files.

    Uses watchdog to efficiently monitor file system changes without polling.
    """

    def __init__(self, watch_path: Path, callback: Callable[[], None], debounce_seconds: float = 1.0):
        """
        Initialize the file watcher.

        Args:
            watch_path: Directory to watch for changes
            callback: Function to call when files change
            debounce_seconds: Minimum seconds between callback invocations
        """
        self.watch_path = watch_path
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer: Optional[Observer] = None

    def start(self) -> None:
        """
        Start watching for file changes.

        Raises:
            FileNotFoundError: If watch_path doesn't exist
        """
        if not self.watch_path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {self.watch_path}")

        event_handler = JSONLFileHandler(self.callback, self.debounce_seconds)
        self.observer = Observer()

        # Watch recursively (includes subdirectories)
        self.observer.schedule(event_handler, str(self.watch_path), recursive=True)
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


#endregion


#region Functions

def watch_claude_files(callback: Callable[[], None], debounce_seconds: float = 1.0) -> FileWatcher:
    """
    Create a file watcher for Claude Code JSONL files.

    Args:
        callback: Function to call when files change
        debounce_seconds: Minimum seconds between callback invocations

    Returns:
        FileWatcher instance

    Example:
        >>> def on_change():
        ...     print("Files changed!")
        >>>
        >>> watcher = watch_claude_files(on_change)
        >>> watcher.start()
        >>>
        >>> # Do other work...
        >>>
        >>> watcher.stop()
    """
    from src.config.settings import CLAUDE_DATA_DIR
    return FileWatcher(CLAUDE_DATA_DIR, callback, debounce_seconds)


#endregion
