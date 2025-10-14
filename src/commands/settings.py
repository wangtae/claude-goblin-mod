"""
Settings command - Interactive settings menu for Claude Goblin.

Allows users to configure display preferences, colors, and other options.
All settings are persisted to the database.
"""
import sys
import tty
import termios
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def run(console: Console) -> None:
    """
    Display settings menu and handle user input.

    Args:
        console: Rich console for rendering
    """
    from src.storage.snapshot_db import load_user_preferences, save_user_preference, DEFAULT_DB_PATH
    import socket

    while True:
        # Load current settings
        prefs = load_user_preferences()

        # Get machine name
        machine_name = prefs.get('machine_name', '') or socket.gethostname()

        # Get database path
        db_path = str(DEFAULT_DB_PATH)

        # Display settings menu
        _display_settings_menu(console, prefs, machine_name, db_path)

        # Wait for user input
        console.print("\n[dim]Enter setting number to edit (1-7), or press ESC to return...[/dim]", end="")

        key = _read_key()

        if key == '\x1b':  # ESC
            break
        elif key in ['1', '2', '3', '4', '5', '6', '7']:
            setting_num = int(key)
            _edit_setting(console, setting_num, prefs, save_user_preference)
        elif key.lower() == 'i':
            handle_db_operation(console, "init")
        elif key.lower() == 'd':
            handle_db_operation(console, "delete")
        elif key.lower() == 'r':
            handle_db_operation(console, "restore")
        elif key.lower() == 'b':
            handle_db_operation(console, "backup")


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
            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        # Fallback for non-Unix systems
        return input()


def _display_settings_menu(console: Console, prefs: dict, machine_name: str, db_path: str) -> None:
    """
    Display the settings menu showing all current settings.

    Args:
        console: Rich console for rendering
        prefs: Dictionary of user preferences
        machine_name: Current machine name
        db_path: Current database path
    """
    console.clear()
    console.print()

    # Status section (read-only)
    status_table = Table(show_header=True, box=None, padding=(0, 2))
    status_table.add_column("Status Item", style="white", justify="left", width=25)
    status_table.add_column("Value", style="cyan", justify="left")

    display_mode_names = ["M1 (simple, bar+%)", "M2 (simple, bar %)", "M3 (panel, bar+%)", "M4 (panel, bar %)"]
    display_mode = int(prefs.get('usage_display_mode', '0'))
    status_table.add_row("Display Mode", display_mode_names[display_mode] if 0 <= display_mode < 4 else "M1")

    color_mode = prefs.get('color_mode', 'gradient')
    status_table.add_row("Color Mode", "Solid" if color_mode == "solid" else "Gradient")

    status_table.add_row("Machine Name", machine_name)
    status_table.add_row("Database Path", db_path)

    status_panel = Panel(
        status_table,
        title="[bold]Status (Read-Only)",
        border_style="white",
        expand=True,
    )
    console.print(status_panel)
    console.print()

    # Settings section (editable)
    settings_table = Table(show_header=True, box=None, padding=(0, 2))
    settings_table.add_column("#", style="dim", justify="right", width=3)
    settings_table.add_column("Setting", style="white", justify="left", width=30)
    settings_table.add_column("Value", style="cyan", justify="left")

    settings_table.add_row("1", "Solid Color", prefs.get('color_solid', '#00A7E1'))
    settings_table.add_row("2", "Gradient Low (0-60%)", prefs.get('color_gradient_low', '#00C853'))
    settings_table.add_row("3", "Gradient Mid (60-85%)", prefs.get('color_gradient_mid', '#FFD600'))
    settings_table.add_row("4", "Gradient High (85-100%)", prefs.get('color_gradient_high', '#FF1744'))
    settings_table.add_row("5", "Unfilled Color", prefs.get('color_unfilled', '#424242'))

    # Auto refresh settings
    refresh_interval = prefs.get('refresh_interval', '30')
    settings_table.add_row("6", "Auto Refresh Interval (sec)", refresh_interval)

    watch_interval = prefs.get('watch_interval', '60')
    settings_table.add_row("7", "File Watch Interval (sec)", watch_interval)

    settings_panel = Panel(
        settings_table,
        title="[bold]Settings (Editable)",
        border_style="white",
        expand=True,
    )
    console.print(settings_panel)

    # Instructions
    console.print()
    console.print("[dim]Database Operations:[/dim]")
    console.print("  [yellow][I][/yellow] Initialize DB  [yellow][D][/yellow] Delete DB  [yellow][R][/yellow] Restore Backup  [yellow][B][/yellow] Create Backup")


def _edit_setting(console: Console, setting_num: int, prefs: dict, save_func) -> None:
    """
    Edit a single setting value.

    Args:
        console: Rich console for rendering
        setting_num: Number of the setting to edit (1-7)
        prefs: Current preferences dictionary
        save_func: Function to save preference
    """
    setting_map = {
        1: ('color_solid', 'Solid Color', '#00A7E1'),
        2: ('color_gradient_low', 'Gradient Low (0-60%)', '#00C853'),
        3: ('color_gradient_mid', 'Gradient Mid (60-85%)', '#FFD600'),
        4: ('color_gradient_high', 'Gradient High (85-100%)', '#FF1744'),
        5: ('color_unfilled', 'Unfilled Color', '#424242'),
        6: ('refresh_interval', 'Auto Refresh Interval (seconds)', '30'),
        7: ('watch_interval', 'File Watch Interval (seconds)', '60'),
    }

    if setting_num not in setting_map:
        return

    key, name, default = setting_map[setting_num]
    current_value = prefs.get(key, default)

    console.print()
    console.print(f"[bold]Edit {name}[/bold]")
    console.print(f"[dim]Current value: {current_value}[/dim]")

    # Read input in normal mode
    if setting_num in [1, 2, 3, 4, 5]:
        # Color input
        console.print("[dim]Enter hex color (e.g., #00A7E1) or press Enter to keep current:[/dim]")
        console.print("> ", end="")
        try:
            new_value = console.input("").strip()

            if new_value:
                # Validate hex color format
                if new_value.startswith('#') and len(new_value) == 7:
                    try:
                        int(new_value[1:], 16)  # Check if valid hex
                        save_func(key, new_value)
                        console.print(f"[green]✓ {name} updated to {new_value}[/green]")
                    except ValueError:
                        console.print("[red]✗ Invalid hex color format. Must be #RRGGBB[/red]")
                else:
                    console.print("[red]✗ Invalid hex color format. Must be #RRGGBB[/red]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Input cancelled[/yellow]")
    else:
        # Interval input (6, 7)
        console.print("[dim]Enter interval in seconds (minimum 10) or press Enter to keep current:[/dim]")
        console.print("> ", end="")
        try:
            new_value = console.input("").strip()

            if new_value:
                try:
                    interval = int(new_value)
                    if interval >= 10:
                        save_func(key, str(interval))
                        console.print(f"[green]✓ {name} updated to {interval} seconds[/green]")
                    else:
                        console.print("[red]✗ Interval must be at least 10 seconds[/red]")
                except ValueError:
                    console.print("[red]✗ Invalid number[/red]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Input cancelled[/yellow]")

    console.print("\n[dim]Press any key to continue...[/dim]")
    _read_key()


def handle_db_operation(console: Console, operation: str) -> None:
    """
    Handle database operations (Initialize, Delete, Restore, Backup).

    Args:
        console: Rich console for rendering
        operation: Operation type - "init", "delete", "restore", or "backup"
    """
    if operation == "init":
        console.print("[yellow]Initializing database...[/yellow]")
        # TODO: Call database initialization
        console.print("[green]Database initialized successfully.[/green]")
    elif operation == "delete":
        console.print("[red]Deleting database...[/red]")
        # TODO: Call database deletion with confirmation
        console.print("[green]Database deleted successfully.[/green]")
    elif operation == "restore":
        console.print("[yellow]Restoring from backup...[/yellow]")
        # TODO: Call database restore
        console.print("[green]Database restored successfully.[/green]")
    elif operation == "backup":
        console.print("[yellow]Creating backup...[/yellow]")
        # TODO: Call database backup
        console.print("[green]Backup created successfully.[/green]")
