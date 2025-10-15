"""
Setup wizard for first-time configuration.

Guides users through initial setup including:
- Database storage location (OneDrive sync vs local-only)
- Machine name configuration
"""
import sys
import tty
import termios
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def run_setup_wizard(console: Console) -> bool:
    """
    Run the initial setup wizard.

    Returns:
        True if setup completed successfully, False if cancelled
    """
    console.clear()
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Welcome to Claude Goblin![/bold cyan]\n\n"
        "This wizard will help you configure your usage tracking.",
        border_style="cyan"
    ))
    console.print()

    # Step 1: Database location
    db_path = _select_database_location(console)
    if db_path is None:
        return False  # User cancelled

    # Step 2: Machine name (optional)
    machine_name = _configure_machine_name(console)
    if machine_name is None:
        return False  # User cancelled

    # Save configuration
    from src.config.user_config import set_db_path, set_machine_name

    if db_path != "auto":
        set_db_path(str(db_path))

    if machine_name:
        set_machine_name(machine_name)

    # Show summary
    _show_setup_summary(console, db_path, machine_name)

    return True


def _select_database_location(console: Console) -> Path | str | None:
    """
    Let user select database storage location.

    Returns:
        Path object, "auto" for auto-detect, or None if cancelled
    """
    console.print("[bold]Step 1: Database Storage Location[/bold]")
    console.print()
    console.print("[dim]Choose where to store your usage data:[/dim]")
    console.print()

    # Detect available options
    from src.storage.snapshot_db import get_default_db_path
    import platform
    import os

    options = []
    option_paths = {}

    # Option 1: OneDrive (if available)
    onedrive_available = False
    onedrive_path = None

    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        # WSL2 - check for OneDrive (prioritize external drives)
        username = os.getenv("USER")

        # Check external drives first (D:, E:, F:)
        for drive in ["d", "e", "f"]:
            candidate = Path(f"/mnt/{drive}/OneDrive")
            if candidate.exists():
                onedrive_path = candidate / ".claude-goblin" / "usage_history.db"
                onedrive_available = True
                break

        # Check C: drive as fallback
        if not onedrive_available:
            candidate = Path("/mnt/c/OneDrive")
            if candidate.exists():
                onedrive_path = candidate / ".claude-goblin" / "usage_history.db"
                onedrive_available = True

        # Check C:/Users/{username}/OneDrive as last resort
        if not onedrive_available and username:
            candidate = Path(f"/mnt/c/Users/{username}/OneDrive")
            if candidate.exists():
                onedrive_path = candidate / ".claude-goblin" / "usage_history.db"
                onedrive_available = True

    elif platform.system() == "Darwin":
        # macOS - check for iCloud Drive
        icloud_base = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
        if icloud_base.exists():
            onedrive_path = icloud_base / ".claude-goblin" / "usage_history.db"
            onedrive_available = True

    # Build options list
    if onedrive_available:
        options.append({
            "key": "1",
            "name": "OneDrive/iCloud Sync",
            "desc": "Multi-device sync (recommended for multiple PCs)",
            "path": onedrive_path,
            "color": "green"
        })
        option_paths["1"] = onedrive_path

    # Option 2: Local storage
    local_path = Path.home() / ".claude" / "usage" / "usage_history.db"
    options.append({
        "key": "2" if onedrive_available else "1",
        "name": "Local Storage",
        "desc": "Single device only (no cloud sync)",
        "path": local_path,
        "color": "yellow"
    })
    option_paths["2" if onedrive_available else "1"] = local_path

    # Option 3: Custom path
    custom_key = str(len(options) + 1)
    options.append({
        "key": custom_key,
        "name": "Custom Path",
        "desc": "Specify your own location",
        "path": None,
        "color": "cyan"
    })

    # Display options
    for opt in options:
        console.print(f"  [{opt['color']}][{opt['key']}][/{opt['color']}] {opt['name']}")
        console.print(f"      [dim]{opt['desc']}[/dim]")
        if opt['path']:
            console.print(f"      [dim]{opt['path']}[/dim]")
        console.print()

    console.print(f"  [dim][ESC] Cancel setup[/dim]")
    console.print()

    # Get user choice
    while True:
        console.print("[dim]Select an option:[/dim] ", end="")
        key = _read_key()

        if key == '\x1b':  # ESC
            console.print("[yellow]Cancelled[/yellow]")
            return None

        if key in option_paths:
            console.print(key)
            selected_path = option_paths[key]

            # If OneDrive was selected, ask for confirmation
            if key == "1" and onedrive_available:
                confirmed_path = _confirm_onedrive_path(console, selected_path)
                if confirmed_path is None:
                    return None  # User cancelled
                return confirmed_path

            return selected_path

        if key == custom_key:
            console.print(key)
            return _get_custom_path(console)

        console.print(f"\n[red]Invalid option. Please select 1-{len(options)} or ESC to cancel.[/red]\n")


def _confirm_onedrive_path(console: Console, detected_path: Path) -> Path | None:
    """
    Confirm OneDrive path with user or allow modification.

    Args:
        console: Rich console for output
        detected_path: Auto-detected OneDrive path

    Returns:
        Confirmed Path, custom Path, or None if cancelled
    """
    console.print()
    console.print("[bold]Confirm OneDrive Path[/bold]")
    console.print()
    console.print("[dim]Detected OneDrive location:[/dim]")
    console.print(f"  [cyan]{detected_path}[/cyan]")
    console.print()
    console.print("[dim]Is this correct?[/dim]")
    console.print("  [green][y][/green] Yes, use this path")
    console.print("  [yellow][n][/yellow] No, enter custom path")
    console.print("  [dim][ESC] Cancel setup[/dim]")
    console.print()

    while True:
        console.print("[dim]Your choice:[/dim] ", end="")
        key = _read_key()

        if key == '\x1b':  # ESC
            console.print("[yellow]Cancelled[/yellow]")
            return None

        if key.lower() == 'y':
            console.print(key)
            console.print(f"[green]✓ Using detected path[/green]")
            return detected_path

        if key.lower() == 'n':
            console.print(key)
            # Ask for custom OneDrive path
            return _get_custom_onedrive_path(console)

        console.print(f"\n[red]Invalid choice. Press 'y', 'n', or ESC.[/red]\n")


def _get_custom_onedrive_path(console: Console) -> Path | None:
    """
    Get custom OneDrive path from user when auto-detection is wrong.

    Returns:
        Custom Path or None if cancelled
    """
    console.print()
    console.print("[bold]Custom OneDrive Path[/bold]")
    console.print("[dim]Enter the correct OneDrive directory path (not including .claude-goblin):[/dim]")
    console.print("[dim]Example: /mnt/d/OneDrive[/dim]")
    console.print()

    try:
        sys.stdout.write("> ")
        sys.stdout.flush()
        path_str = input().strip()

        if not path_str:
            console.print("[yellow]Cancelled[/yellow]")
            return None

        onedrive_root = Path(path_str)

        # Validate that it's a directory
        if not onedrive_root.exists():
            console.print(f"[red]✗ Directory does not exist: {onedrive_root}[/red]")
            console.print("[yellow]Please check the path and try running setup wizard again.[/yellow]")
            return None

        if not onedrive_root.is_dir():
            console.print(f"[red]✗ Path is not a directory: {onedrive_root}[/red]")
            return None

        # Construct full DB path
        db_path = onedrive_root / ".claude-goblin" / "usage_history.db"

        # Try to create the directory
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Using custom OneDrive path: {db_path}[/green]")
            return db_path
        except (PermissionError, OSError) as e:
            console.print(f"[red]✗ Cannot create directory: {e}[/red]")
            console.print("[yellow]Please check permissions and try again.[/yellow]")
            return None

    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled[/yellow]")
        return None


def _get_custom_path(console: Console) -> Path | None:
    """
    Get custom database path from user.

    Returns:
        Path object or None if cancelled
    """
    console.print()
    console.print("[bold]Custom Database Path[/bold]")
    console.print("[dim]Enter full path to database file (or press Enter to cancel):[/dim]")
    console.print("[dim]Example: /mnt/d/MyFolder/.claude-goblin/usage_history.db[/dim]")

    try:
        sys.stdout.write("> ")
        sys.stdout.flush()
        path_str = input().strip()

        if not path_str:
            console.print("[yellow]Cancelled[/yellow]")
            return None

        db_path = Path(path_str)

        # Validate path
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Using custom path: {db_path}[/green]")
            return db_path
        except (PermissionError, OSError) as e:
            console.print(f"[red]✗ Cannot create directory: {e}[/red]")
            console.print("[yellow]Falling back to local storage...[/yellow]")
            return Path.home() / ".claude" / "usage" / "usage_history.db"

    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled[/yellow]")
        return None


def _configure_machine_name(console: Console) -> str | None:
    """
    Configure machine name (optional).

    Returns:
        Machine name string (empty string for auto), or None if cancelled
    """
    import socket

    console.print()
    console.print("[bold]Step 2: Machine Name (Optional)[/bold]")
    console.print()
    console.print("[dim]Give this device a friendly name for multi-device tracking.[/dim]")
    console.print("[dim]Leave empty to use hostname.[/dim]")
    console.print()

    hostname = socket.gethostname()
    console.print(f"[dim]Current hostname: {hostname}[/dim]")
    console.print()
    console.print("[dim]Examples: Home-Desktop, Work-Laptop, Gaming-PC[/dim]")

    try:
        sys.stdout.write("> ")
        sys.stdout.flush()
        name = input().strip()

        if name:
            console.print(f"[green]✓ Machine name: {name}[/green]")
            return name
        else:
            console.print(f"[green]✓ Using hostname: {hostname}[/green]")
            return ""

    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled[/yellow]")
        return None


def _show_setup_summary(console: Console, db_path: Path | str, machine_name: str) -> None:
    """
    Show setup summary and next steps.
    """
    import socket

    console.print()
    console.print(Panel.fit(
        "[bold green]Setup Complete![/bold green]\n\n"
        "Your configuration has been saved.",
        border_style="green"
    ))
    console.print()

    # Show configuration
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    if db_path == "auto":
        table.add_row("Database", "[dim]Auto-detect[/dim]")
    else:
        table.add_row("Database", str(db_path))
        if "OneDrive" in str(db_path) or "CloudDocs" in str(db_path):
            table.add_row("", "[green]✓ Multi-device sync enabled[/green]")
        else:
            table.add_row("", "[yellow]⚠ Local storage (no sync)[/yellow]")

    if machine_name:
        table.add_row("Machine Name", machine_name)
    else:
        hostname = socket.gethostname()
        table.add_row("Machine Name", f"{hostname} [dim](auto)[/dim]")

    console.print(table)
    console.print()

    console.print("[dim]You can change these settings anytime:[/dim]")
    console.print("[dim]  • Press 's' in the dashboard to open Settings[/dim]")
    console.print("[dim]  • Run 'ccu config show' to view current settings[/dim]")
    console.print()
    console.print("[green]Press any key to continue...[/green]")
    _read_key()


def _read_key() -> str:
    """
    Read a single key from stdin.

    Returns:
        The key pressed as a string
    """
    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)

            # Handle Ctrl+C
            if key == '\x03':
                raise KeyboardInterrupt

            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        # Fallback for non-Unix systems
        return input()


def should_run_setup_wizard() -> bool:
    """
    Check if setup wizard should run.

    Returns:
        True if this is first-time setup, False otherwise
    """
    from src.config.user_config import CONFIG_PATH

    # Run wizard if config file doesn't exist
    if not CONFIG_PATH.exists():
        return True

    # Check if setup_completed flag exists
    try:
        from src.config.user_config import load_config
        config = load_config()
        return not config.get("setup_completed", False)
    except:
        return True


def mark_setup_completed() -> None:
    """Mark setup wizard as completed."""
    from src.config.user_config import load_config, save_config

    config = load_config()
    config["setup_completed"] = True
    save_config(config)
