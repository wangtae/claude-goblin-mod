"""
Configuration management command.

Allows users to view and modify Claude Goblin settings.
"""
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.config.user_config import (
    get_db_path,
    set_db_path,
    clear_db_path,
    get_machine_name,
    set_machine_name,
    clear_machine_name,
    get_storage_mode,
    get_tracking_mode,
    get_plan_type,
)
from src.storage.snapshot_db import DEFAULT_DB_PATH


def run(console: Console, action: str, value: str | None = None) -> None:
    """
    Handle configuration commands.

    Args:
        console: Rich console for output
        action: Configuration action to perform
        value: Optional value for set actions

    Actions:
        show - Display all current settings
        set-db-path <path> - Set custom database path
        clear-db-path - Clear custom database path (use auto-detect)
        set-machine-name <name> - Set custom machine name
        clear-machine-name - Clear custom machine name (use hostname)
    """
    if action == "show":
        _show_config(console)

    elif action == "set-db-path":
        if not value:
            console.print("[red]Error: Database path required[/red]")
            console.print("[yellow]Usage: ccg config set-db-path /path/to/usage_history.db[/yellow]")
            return

        try:
            set_db_path(value)
            console.print(f"[green]✓ Database path set to: {value}[/green]")
            console.print("[dim]Restart any running commands to use the new path.[/dim]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")

    elif action == "clear-db-path":
        clear_db_path()
        console.print("[green]✓ Database path cleared (using auto-detect)[/green]")
        console.print(f"[dim]Auto-detected path: {DEFAULT_DB_PATH}[/dim]")

    elif action == "set-machine-name":
        if not value:
            console.print("[red]Error: Machine name required[/red]")
            console.print("[yellow]Usage: ccg config set-machine-name \"My-Desktop\"[/yellow]")
            return

        set_machine_name(value)
        console.print(f"[green]✓ Machine name set to: {value}[/green]")

    elif action == "clear-machine-name":
        import socket
        clear_machine_name()
        hostname = socket.gethostname()
        console.print("[green]✓ Machine name cleared (using hostname)[/green]")
        console.print(f"[dim]Hostname: {hostname}[/dim]")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("\n[yellow]Available actions:[/yellow]")
        console.print("  show                    - Display all settings")
        console.print("  set-db-path <path>      - Set custom database path")
        console.print("  clear-db-path           - Clear custom database path")
        console.print("  set-machine-name <name> - Set custom machine name")
        console.print("  clear-machine-name      - Clear custom machine name")


def _show_config(console: Console) -> None:
    """Display all current configuration settings."""
    import socket

    console.print("\n[bold cyan]Claude Goblin Configuration[/bold cyan]\n")

    # Database settings
    table = Table(title="Database Settings", show_header=False, box=None, padding=(0, 2))
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    custom_db_path = get_db_path()
    if custom_db_path:
        table.add_row("DB Path (custom)", custom_db_path)
        table.add_row("", "[dim](using custom path)[/dim]")
    else:
        table.add_row("DB Path (auto-detect)", str(DEFAULT_DB_PATH))

        if "OneDrive" in str(DEFAULT_DB_PATH):
            table.add_row("", "[dim](OneDrive sync enabled)[/dim]")
        elif "CloudDocs" in str(DEFAULT_DB_PATH):
            table.add_row("", "[dim](iCloud Drive sync enabled)[/dim]")
        else:
            table.add_row("", "[dim](local storage, no cloud sync)[/dim]")

    console.print(table)
    console.print()

    # Machine settings
    table = Table(title="Machine Settings", show_header=False, box=None, padding=(0, 2))
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    custom_machine_name = get_machine_name()
    if custom_machine_name:
        table.add_row("Machine Name (custom)", custom_machine_name)
    else:
        hostname = socket.gethostname()
        table.add_row("Machine Name (auto)", hostname)

    console.print(table)
    console.print()

    # Tracking settings
    table = Table(title="Tracking Settings", show_header=False, box=None, padding=(0, 2))
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Storage Mode", get_storage_mode())
    table.add_row("Tracking Mode", get_tracking_mode())
    table.add_row("Plan Type", get_plan_type())

    console.print(table)

    # Help text
    console.print("\n[dim]To change settings, run:[/dim]")
    console.print("[dim]  ccg config set-db-path /path/to/database.db[/dim]")
    console.print("[dim]  ccg config set-machine-name \"My-Desktop\"[/dim]")
    console.print()
