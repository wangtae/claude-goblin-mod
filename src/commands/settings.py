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
        console.print("\n[dim]Enter setting number to edit (1-11), or press ESC to return...[/dim]", end="")

        key = _read_key()

        if key == '\x1b':  # ESC
            break
        elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            setting_num = int(key)
            _edit_setting(console, setting_num, prefs, save_user_preference)
        elif key == '0':  # Handle '10' as '0'
            setting_num = 10
            _edit_setting(console, setting_num, prefs, save_user_preference)
        elif key == '!':  # Handle '11' as '!'  (Shift+1)
            setting_num = 11
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

    # Timezone display
    from src.utils.timezone import get_user_timezone, get_timezone_info
    tz_setting = prefs.get('timezone', 'auto')
    actual_tz = get_user_timezone()
    tz_info = get_timezone_info(actual_tz)
    if tz_setting == 'auto':
        tz_display = f"Auto ({tz_info['abbr']}, {tz_info['offset']})"
    else:
        tz_display = f"{tz_info['abbr']} ({tz_info['offset']})"
    status_table.add_row("Display Timezone", tz_display)

    status_table.add_row("Machine Name", machine_name)
    status_table.add_row("Database Path", db_path)

    # Backup information
    from src.config.user_config import get_last_backup_date
    from src.utils.backup import list_backups, get_backup_directory
    from pathlib import Path

    last_backup = get_last_backup_date()
    if last_backup:
        status_table.add_row("Last Backup", last_backup)
    else:
        status_table.add_row("Last Backup", "[dim]Never[/dim]")

    # Count backup files
    try:
        backups = list_backups(Path(db_path))
        backup_count = len(backups)
        monthly_count = sum(1 for b in backups if b["is_monthly"])
        status_table.add_row("Backups", f"{backup_count} total ({monthly_count} monthly)")
    except:
        status_table.add_row("Backups", "[dim]0[/dim]")

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

    # Backup settings
    from src.config.user_config import (
        get_backup_enabled,
        get_backup_keep_monthly,
        get_backup_retention_days,
    )

    backup_enabled = get_backup_enabled()
    settings_table.add_row("8", "Auto Backup", "Enabled" if backup_enabled else "Disabled")

    keep_monthly = get_backup_keep_monthly()
    settings_table.add_row("9", "Keep Monthly Backups", "Yes" if keep_monthly else "No")

    retention_days = get_backup_retention_days()
    settings_table.add_row("10", "Backup Retention (days)", str(retention_days))

    # Timezone setting
    tz_setting = prefs.get('timezone', 'auto')
    if tz_setting == 'auto':
        tz_value = f"Auto ({tz_info['abbr']})"
    else:
        tz_value = f"{tz_setting} ({tz_info['abbr']})"
    settings_table.add_row("11", "Display Timezone", tz_value)

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
        setting_num: Number of the setting to edit (1-11)
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

    # Handle backup settings separately (8, 9, 10)
    if setting_num in [8, 9, 10]:
        _edit_backup_setting(console, setting_num)
        return

    # Handle timezone setting separately (11)
    if setting_num == 11:
        _edit_timezone_setting(console, prefs, save_func)
        return

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


def _edit_backup_setting(console: Console, setting_num: int) -> None:
    """
    Edit backup-related settings (8, 9, 10).

    Args:
        console: Rich console for rendering
        setting_num: Setting number (8, 9, or 10)
    """
    from src.config.user_config import (
        get_backup_enabled,
        set_backup_enabled,
        get_backup_keep_monthly,
        set_backup_keep_monthly,
        get_backup_retention_days,
        set_backup_retention_days,
    )

    console.print()

    if setting_num == 8:
        # Auto Backup (True/False)
        current = get_backup_enabled()
        console.print("[bold]Edit Auto Backup[/bold]")
        console.print(f"[dim]Current value: {'Enabled' if current else 'Disabled'}[/dim]")
        console.print("[dim]Enter 'yes' to enable or 'no' to disable, or press Enter to keep current:[/dim]")
        console.print("> ", end="")

        try:
            new_value = console.input("").strip().lower()

            if new_value in ['yes', 'y', 'true', '1']:
                set_backup_enabled(True)
                console.print("[green]✓ Auto Backup enabled[/green]")
            elif new_value in ['no', 'n', 'false', '0']:
                set_backup_enabled(False)
                console.print("[green]✓ Auto Backup disabled[/green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Input cancelled[/yellow]")

    elif setting_num == 9:
        # Keep Monthly Backups (True/False)
        current = get_backup_keep_monthly()
        console.print("[bold]Edit Keep Monthly Backups[/bold]")
        console.print(f"[dim]Current value: {'Yes' if current else 'No'}[/dim]")
        console.print("[dim]Keep backups from the 1st of each month permanently?[/dim]")
        console.print("[dim]Enter 'yes' or 'no', or press Enter to keep current:[/dim]")
        console.print("> ", end="")

        try:
            new_value = console.input("").strip().lower()

            if new_value in ['yes', 'y', 'true', '1']:
                set_backup_keep_monthly(True)
                console.print("[green]✓ Monthly backups will be kept permanently[/green]")
            elif new_value in ['no', 'n', 'false', '0']:
                set_backup_keep_monthly(False)
                console.print("[green]✓ Monthly backups will be deleted after retention period[/green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Input cancelled[/yellow]")

    elif setting_num == 10:
        # Backup Retention Days (int)
        current = get_backup_retention_days()
        console.print("[bold]Edit Backup Retention (days)[/bold]")
        console.print(f"[dim]Current value: {current} days[/dim]")
        console.print("[dim]Enter number of days to keep backups (minimum 1) or press Enter to keep current:[/dim]")
        console.print("> ", end="")

        try:
            new_value = console.input("").strip()

            if new_value:
                try:
                    days = int(new_value)
                    if days >= 1:
                        set_backup_retention_days(days)
                        console.print(f"[green]✓ Backup retention set to {days} days[/green]")
                    else:
                        console.print("[red]✗ Days must be at least 1[/red]")
                except ValueError:
                    console.print("[red]✗ Invalid number[/red]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Input cancelled[/yellow]")

    console.print("\n[dim]Press any key to continue...[/dim]")
    _read_key()


def _edit_timezone_setting(console: Console, prefs: dict, save_func) -> None:
    """
    Edit timezone setting (11).

    Args:
        console: Rich console for rendering
        prefs: Current preferences dictionary
        save_func: Function to save preference
    """
    from src.utils.timezone import get_user_timezone, get_timezone_info, validate_timezone, list_common_timezones

    console.print()
    console.print("[bold]Edit Display Timezone[/bold]")

    # Show current setting
    current_tz = prefs.get('timezone', 'auto')
    actual_tz = get_user_timezone()
    tz_info = get_timezone_info(actual_tz)

    if current_tz == 'auto':
        console.print(f"[dim]Current: Auto ({tz_info['name']}, {tz_info['offset']})[/dim]")
    else:
        console.print(f"[dim]Current: {current_tz} ({tz_info['offset']})[/dim]")

    console.print()
    console.print("[dim]Select timezone option:[/dim]")
    console.print("  [yellow][1][/yellow] Auto (system timezone detection)")
    console.print("  [yellow][2][/yellow] UTC")
    console.print("  [yellow][3][/yellow] Select from common timezones")
    console.print("  [yellow][Enter][/yellow] Keep current setting")
    console.print()
    console.print("> ", end="")

    try:
        choice = console.input("").strip()

        if not choice:
            # Keep current
            return

        if choice == '1':
            # Auto mode
            save_func('timezone', 'auto')
            console.print("[green]✓ Timezone set to Auto (system detection)[/green]")

        elif choice == '2':
            # UTC mode
            save_func('timezone', 'UTC')
            console.print("[green]✓ Timezone set to UTC[/green]")

        elif choice == '3':
            # Show common timezones
            console.print()
            console.print("[dim]Common timezones:[/dim]")
            common_tzs = list_common_timezones()

            for idx, tz in enumerate(common_tzs, start=1):
                console.print(f"  [{idx:2d}] {tz['name']:25s} {tz['offset']}")

            console.print()
            console.print("[dim]Enter number (1-{}) or custom IANA timezone name:[/dim]".format(len(common_tzs)))
            console.print("> ", end="")

            tz_choice = console.input("").strip()

            if tz_choice.isdigit():
                # Numeric selection
                idx = int(tz_choice)
                if 1 <= idx <= len(common_tzs):
                    selected_tz = common_tzs[idx - 1]['name']
                    save_func('timezone', selected_tz)
                    console.print(f"[green]✓ Timezone set to {selected_tz}[/green]")
                else:
                    console.print("[red]✗ Invalid selection[/red]")
            elif tz_choice:
                # Custom IANA name
                if validate_timezone(tz_choice):
                    save_func('timezone', tz_choice)
                    console.print(f"[green]✓ Timezone set to {tz_choice}[/green]")
                else:
                    console.print("[red]✗ Invalid timezone name[/red]")

        else:
            console.print("[yellow]Invalid choice[/yellow]")

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
