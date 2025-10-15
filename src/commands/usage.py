#region Imports
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import re

from rich.console import Console

from src.aggregation.daily_stats import aggregate_all
from src.commands.limits import capture_limits
from src.config.settings import (
    DEFAULT_REFRESH_INTERVAL,
    get_claude_jsonl_files,
)
from src.config.user_config import get_tracking_mode
from src.data.jsonl_parser import parse_all_jsonl_files
from src.storage.snapshot_db import (
    get_database_stats,
    load_historical_records,
    save_limits_snapshot,
    save_snapshot,
)
from src.visualization.dashboard import render_dashboard
#endregion


#region Constants
# View modes for dashboard
VIEW_MODE_WEEKLY = "weekly"
VIEW_MODE_MONTHLY = "monthly"
VIEW_MODE_YEARLY = "yearly"
VIEW_MODE_HEATMAP = "heatmap"
VIEW_MODE_DEVICES = "devices"
#endregion


#region Functions


def _parse_week_reset_date(week_reset_str: str) -> datetime | None:
    """
    Parse week reset string to datetime object.

    Args:
        week_reset_str: Reset string like "Oct 17, 10am (Asia/Seoul)"

    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Remove timezone part
        reset_no_tz = week_reset_str.split(' (')[0]

        # Parse "Oct 17, 10am" format
        match = re.search(r'([A-Za-z]+)\s+(\d+)', reset_no_tz)
        if not match:
            return None

        month_name = match.group(1)
        day = int(match.group(2))

        # Use current year
        year = datetime.now().year

        # Parse month
        month_num = datetime.strptime(month_name, '%b').month

        return datetime(year, month_num, day)
    except Exception:
        return None


def _filter_records_by_week(records: list, week_reset_date: datetime) -> list:
    """
    Filter records to current week limit period (7 days before reset).

    Args:
        records: List of UsageRecord objects
        week_reset_date: Week reset datetime

    Returns:
        Filtered list of records within the week period
    """
    week_start = week_reset_date - timedelta(days=7)
    week_start_date = week_start.date()
    week_end_date = week_reset_date.date()

    filtered = []
    for record in records:
        # Parse date_key (format: "YYYY-MM-DD")
        try:
            record_date = datetime.strptime(record.date_key, "%Y-%m-%d").date()
            if week_start_date <= record_date <= week_end_date:
                filtered.append(record)
        except Exception:
            continue

    return filtered


def _limits_updater_thread(stop_event: threading.Event, interval: int = 60) -> None:
    """
    Background thread that updates usage limits at regular intervals.

    Updates limits data from Claude CLI and saves to database every N seconds.
    This prevents blocking the main dashboard updates while keeping limits data fresh.

    Args:
        stop_event: Threading event to signal when to stop updating
        interval: Seconds between updates (default: 60)
    """
    # Wait 5 seconds before first update (let initial dashboard render first)
    if not stop_event.wait(5):
        # Do initial update
        tracking_mode = get_tracking_mode()
        if tracking_mode in ["both", "limits"]:
            try:
                limits = capture_limits()
                if limits and "error" not in limits:
                    save_limits_snapshot(
                        session_pct=limits["session_pct"],
                        week_pct=limits["week_pct"],
                        opus_pct=limits["opus_pct"],
                        session_reset=limits["session_reset"],
                        week_reset=limits["week_reset"],
                        opus_reset=limits["opus_reset"],
                    )
            except Exception:
                pass  # Silently ignore errors in background thread

    # Continue updating at regular intervals
    while not stop_event.is_set():
        if stop_event.wait(interval):
            break  # Stop event was set during wait

        tracking_mode = get_tracking_mode()
        if tracking_mode in ["both", "limits"]:
            try:
                limits = capture_limits()
                if limits and "error" not in limits:
                    save_limits_snapshot(
                        session_pct=limits["session_pct"],
                        week_pct=limits["week_pct"],
                        opus_pct=limits["opus_pct"],
                        session_reset=limits["session_reset"],
                        week_reset=limits["week_reset"],
                        opus_reset=limits["opus_reset"],
                    )
            except Exception:
                pass  # Silently ignore errors in background thread


def _keyboard_listener(view_mode_ref: dict, stop_event: threading.Event) -> None:
    """
    Listen for keyboard input to switch view modes.

    Runs in a separate thread to handle keyboard input without blocking dashboard.

    Args:
        view_mode_ref: Dict with 'mode' key to track current view mode
        stop_event: Threading event to signal when to stop listening
    """
    import sys
    import tty
    import termios
    import os

    # Enable debug mode with environment variable: DEBUG_ARROWS=1
    debug_arrows = os.environ.get('DEBUG_ARROWS', '0') == '1'

    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin.fileno())

        while not stop_event.is_set():
            # Check if input is available (non-blocking with timeout)
            import select
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)

                # Check for arrow keys (escape sequences)
                if key == '\x1b':  # ESC
                    if debug_arrows:
                        print(f"\n[DEBUG] Got ESC, reading sequence...", file=sys.stderr)

                    # Read the rest of the escape sequence
                    # Arrow keys send: ESC [ A/B/C/D
                    # Wait a bit longer for the rest of the sequence to arrive
                    remaining = []
                    for _ in range(2):  # Read next 2 characters
                        if select.select([sys.stdin], [], [], 0.5)[0]:  # Increased timeout to 0.5s
                            remaining.append(sys.stdin.read(1))
                        else:
                            # Timeout - might be a plain ESC press
                            if debug_arrows:
                                print(f"[DEBUG] Timeout reading sequence", file=sys.stderr)
                            break

                    if debug_arrows:
                        print(f"[DEBUG] Remaining: {[repr(c) for c in remaining]}, len={len(remaining)}", file=sys.stderr)

                    # Check if it's an arrow key
                    if len(remaining) == 2 and remaining[0] == '[':
                        arrow = remaining[1]
                        if debug_arrows:
                            print(f"[DEBUG] Arrow key: {repr(arrow)}, mode={view_mode_ref['mode']}", file=sys.stderr)

                        if arrow == 'D':  # Left arrow
                            # Go to previous period
                            if view_mode_ref['mode'] in [VIEW_MODE_WEEKLY, VIEW_MODE_MONTHLY, VIEW_MODE_YEARLY]:
                                old_offset = view_mode_ref.get('offset', 0)
                                view_mode_ref['offset'] = old_offset - 1
                                view_mode_ref['changed'] = True
                                if debug_arrows:
                                    print(f"[DEBUG] Left arrow: offset {old_offset} -> {view_mode_ref['offset']}", file=sys.stderr)
                            continue  # Skip the rest of the key processing
                        elif arrow == 'C':  # Right arrow
                            # Go to next period (don't go beyond current)
                            if view_mode_ref['mode'] in [VIEW_MODE_WEEKLY, VIEW_MODE_MONTHLY, VIEW_MODE_YEARLY]:
                                current_offset = view_mode_ref.get('offset', 0)
                                if current_offset < 0:  # Only allow if we're in the past
                                    view_mode_ref['offset'] = current_offset + 1
                                    view_mode_ref['changed'] = True
                                    if debug_arrows:
                                        print(f"[DEBUG] Right arrow: offset {current_offset} -> {view_mode_ref['offset']}", file=sys.stderr)
                                elif debug_arrows:
                                    print(f"[DEBUG] Right arrow: already at present (offset={current_offset})", file=sys.stderr)
                            continue  # Skip the rest of the key processing

                    # If we got here, it's a plain ESC press (not arrow key)
                    # If in message detail mode (hourly detail), exit to daily detail view
                    if view_mode_ref.get('hourly_detail_hour') is not None:
                        view_mode_ref['hourly_detail_hour'] = None
                        view_mode_ref['changed'] = True
                        continue
                    # If in daily detail mode, exit to normal weekly view
                    if view_mode_ref.get('daily_detail_date'):
                        view_mode_ref['daily_detail_date'] = None
                        view_mode_ref['changed'] = True
                        continue
                    # Otherwise, treat ESC as quit command
                    stop_event.set()
                    continue

                key = key.lower()

                # Map Korean characters to English keys (for Korean keyboard mode)
                hangul_to_english = {
                    'ㅕ': 'u',  # u key in Korean mode
                    'ㅈ': 'w',  # w key in Korean mode
                    'ㅡ': 'm',  # m key in Korean mode
                    'ㅛ': 'y',  # y key in Korean mode
                    'ㅗ': 'h',  # h key in Korean mode
                    'ㅇ': 'd',  # d key in Korean mode
                    'ㅂ': 'q',  # q key in Korean mode
                    'ㄱ': 'r',  # r key in Korean mode
                    'ㄴ': 's',  # s key in Korean mode
                    'ㅏ': '<',  # < key in Korean mode (shift+,)
                    'ㅐ': '>',  # > key in Korean mode (shift+.)
                    # Numbers with shift (Korean keyboard)
                    '!': '1',  # shift+1 in Korean mode
                    '@': '2',  # shift+2 in Korean mode
                    '#': '3',  # shift+3 in Korean mode
                    '$': '4',  # shift+4 in Korean mode
                    '%': '5',  # shift+5 in Korean mode
                    '^': '6',  # shift+6 in Korean mode
                    '&': '7',  # shift+7 in Korean mode
                    '*': '8',  # shift+8 in Korean mode
                    '(': '9',  # shift+9 in Korean mode
                }
                if key in hangul_to_english:
                    key = hangul_to_english[key]

                # Flush any remaining characters in the input buffer
                # to prevent stale input from affecting future reads
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)

                if key == 'u':
                    view_mode_ref['mode'] = "usage"
                    view_mode_ref['offset'] = 0  # Reset offset when changing mode
                    view_mode_ref['changed'] = True
                elif key == 'w':
                    view_mode_ref['mode'] = VIEW_MODE_WEEKLY
                    view_mode_ref['offset'] = 0  # Reset offset when changing mode
                    view_mode_ref['changed'] = True
                elif key == 'm':
                    view_mode_ref['mode'] = VIEW_MODE_MONTHLY
                    view_mode_ref['offset'] = 0  # Reset offset when changing mode
                    view_mode_ref['changed'] = True
                elif key == 'y':
                    view_mode_ref['mode'] = VIEW_MODE_YEARLY
                    view_mode_ref['offset'] = 0  # Reset offset when changing mode
                    view_mode_ref['changed'] = True
                elif key == 'h':
                    view_mode_ref['mode'] = VIEW_MODE_HEATMAP
                    view_mode_ref['offset'] = 0  # Reset offset when changing mode
                    view_mode_ref['changed'] = True
                elif key == 'd':
                    view_mode_ref['mode'] = VIEW_MODE_DEVICES
                    view_mode_ref['offset'] = 0  # Reset offset when changing mode
                    view_mode_ref['changed'] = True
                elif key == '\t':  # Tab key
                    if view_mode_ref['mode'] == "usage":
                        # Cycle through 8 modes: S1 -> S2 -> S3 -> S4 -> G1 -> G2 -> G3 -> G4 -> S1
                        # Current state: usage_display_mode (0-3) and color_mode ('solid' or 'gradient')
                        current_display = view_mode_ref.get('usage_display_mode', 0)
                        current_color = view_mode_ref.get('color_mode', 'gradient')

                        # Convert to 0-7 index (0-3: Solid modes, 4-7: Gradient modes)
                        if current_color == 'solid':
                            current_index = current_display  # 0-3
                        else:
                            current_index = current_display + 4  # 4-7

                        # Increment and wrap around
                        new_index = (current_index + 1) % 8

                        # Convert back to display mode and color mode
                        if new_index < 4:
                            new_display = new_index
                            new_color = 'solid'
                        else:
                            new_display = new_index - 4
                            new_color = 'gradient'

                        # Update state
                        view_mode_ref['usage_display_mode'] = new_display
                        view_mode_ref['color_mode'] = new_color
                        view_mode_ref['changed'] = True

                        # Save to DB
                        from src.storage.snapshot_db import save_user_preference
                        save_user_preference('usage_display_mode', str(new_display))
                        save_user_preference('color_mode', new_color)
                elif key == 's':  # Settings menu
                    # Save current view mode to restore later
                    previous_mode = view_mode_ref['mode']

                    # Set mode to 'settings' to pause auto-refresh
                    view_mode_ref['mode'] = 'settings'

                    # Restore terminal to ORIGINAL normal mode (from program start)
                    import termios
                    original_settings = view_mode_ref.get('original_terminal_settings')
                    if original_settings:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_settings)

                    # Open settings menu (blocks until ESC is pressed)
                    from src.commands.settings import run as settings_run
                    from rich.console import Console
                    settings_console = Console()
                    settings_run(settings_console)

                    # Restore raw mode for keyboard listener AFTER settings exits
                    import tty
                    tty.setcbreak(sys.stdin.fileno())

                    # Reload preferences after settings close
                    from src.storage.snapshot_db import load_user_preferences
                    from src.config.defaults import DEFAULT_COLORS
                    prefs = load_user_preferences()
                    view_mode_ref['usage_display_mode'] = int(prefs.get('usage_display_mode', '0'))
                    view_mode_ref['color_mode'] = prefs.get('color_mode', 'gradient')
                    view_mode_ref['colors'] = {
                        'color_solid': prefs.get('color_solid', DEFAULT_COLORS['color_solid']),
                        'color_gradient_low': prefs.get('color_gradient_low', DEFAULT_COLORS['color_gradient_low']),
                        'color_gradient_mid': prefs.get('color_gradient_mid', DEFAULT_COLORS['color_gradient_mid']),
                        'color_gradient_high': prefs.get('color_gradient_high', DEFAULT_COLORS['color_gradient_high']),
                        'color_unfilled': prefs.get('color_unfilled', DEFAULT_COLORS['color_unfilled']),
                    }
                    # Restore previous mode and trigger refresh
                    view_mode_ref['mode'] = previous_mode
                    view_mode_ref['changed'] = True
                elif key == '<':
                    # Only for weekly/monthly/yearly modes - go to previous period
                    if view_mode_ref['mode'] in [VIEW_MODE_WEEKLY, VIEW_MODE_MONTHLY, VIEW_MODE_YEARLY]:
                        view_mode_ref['offset'] = view_mode_ref.get('offset', 0) - 1
                        view_mode_ref['changed'] = True
                elif key == '>':
                    # Only for weekly/monthly/yearly modes - go to next period
                    if view_mode_ref['mode'] in [VIEW_MODE_WEEKLY, VIEW_MODE_MONTHLY, VIEW_MODE_YEARLY]:
                        current_offset = view_mode_ref.get('offset', 0)
                        if current_offset < 0:  # Only allow if we're in the past
                            view_mode_ref['offset'] = current_offset + 1
                            view_mode_ref['changed'] = True
                elif key == 'r':
                    # Manual refresh - update data
                    view_mode_ref['manual_refresh'] = True
                    view_mode_ref['changed'] = True
                elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    # Number keys for navigation
                    day_index = int(key) - 1  # Convert to 0-indexed

                    # If in daily detail mode, navigate to hourly detail (message view)
                    if view_mode_ref.get('daily_detail_date'):
                        # Get hourly data from daily detail view
                        # Number keys map to hours (1 = first hour shown, 2 = second hour, etc.)
                        # We need to get the sorted hours from the daily detail view
                        # For now, we'll store hourly_hours in view_mode_ref similar to weekly_dates
                        hourly_hours = view_mode_ref.get('hourly_hours', [])

                        if day_index < len(hourly_hours):
                            # Set the hourly detail hour (store as integer 0-23)
                            view_mode_ref['hourly_detail_hour'] = hourly_hours[day_index]
                            view_mode_ref['changed'] = True
                    # If in weekly mode (not in daily detail), navigate to daily detail
                    elif view_mode_ref['mode'] == VIEW_MODE_WEEKLY:
                        # Check if we have weekly dates available
                        weekly_dates = view_mode_ref.get('weekly_dates', [])

                        if day_index < len(weekly_dates):
                            # Set the daily detail date
                            view_mode_ref['daily_detail_date'] = weekly_dates[day_index]
                            view_mode_ref['changed'] = True
                elif key == '\x1b':  # ESC key pressed again (not arrow key)
                    # If in daily detail mode, exit to normal weekly view
                    if view_mode_ref.get('daily_detail_date'):
                        view_mode_ref['daily_detail_date'] = None
                        view_mode_ref['changed'] = True
                    # Note: ESC to quit is already handled above in the escape sequence section

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def run(console: Console, refresh: int | None = None, anon: bool = False, watch_interval: int = 60, limits_interval: int = 60) -> None:
    """
    Handle the usage command.

    Loads Claude Code usage data and displays an interactive dashboard with:
    - Real-time file watching (updates when Claude Code creates new logs) - default
    - Or periodic refresh at specified interval (if --refresh is provided)
    - Keyboard shortcuts to switch between different views
    - GitHub-style activity visualization

    Args:
        console: Rich console for output
        refresh: Refresh interval in seconds (None = file watching mode)
        anon: Anonymize project names to project-001, project-002, etc (default: False)
        watch_interval: File watch check interval in seconds (default: 60)
        limits_interval: Usage limits update interval in seconds (default: 60)

    Exit:
        Exits with status 0 on success, 1 on error
    """
    import termios

    # Save terminal settings at the very start
    original_terminal_settings = None
    try:
        original_terminal_settings = termios.tcgetattr(sys.stdin)
    except:
        pass  # Not a TTY or stdin not available

    # Hide cursor for cleaner look
    try:
        console.show_cursor(False)
    except:
        pass  # Not a TTY

    # Clear screen to create clean starting point
    # Use console.clear() for better VSCode compatibility (avoids triggering sticky scroll)
    try:
        from rich.console import Console
        temp_console = Console()
        temp_console.clear()
    except:
        pass

    # Check for --anon flag: CLI flag > DB setting
    # Load anonymize setting from DB
    from src.storage.snapshot_db import load_user_preferences
    prefs = load_user_preferences()
    anonymize_from_db = prefs.get('anonymize_projects', '0') == '1'
    # CLI flag takes priority over DB setting
    anonymize = anon or "--anon" in sys.argv or anonymize_from_db

    # Check for --refresh in sys.argv if not passed as parameter
    if refresh is None:
        for arg in sys.argv:
            if arg.startswith("--refresh="):
                try:
                    refresh = int(arg.split("=")[1])
                except:
                    pass

    try:
        with console.status("[bold #ff8800]Loading Claude Code usage data...", spinner="dots", spinner_style="#ff8800"):
            jsonl_files = get_claude_jsonl_files()

        if not jsonl_files:
            console.print(
                "[yellow]No Claude Code data found. "
                "Make sure you've used Claude Code at least once.[/yellow]"
            )
            return

        console.print(f"[dim]Found {len(jsonl_files)} session files[/dim]")
        console.print("[dim]Tip: Run 'ccu --help' to see all available options[/dim]\n", end="")

        # Choose between refresh mode (polling) or watch mode (file events)
        if refresh is not None:
            _run_refresh_dashboard(jsonl_files, console, original_terminal_settings, refresh_interval=refresh, anonymize=anonymize, limits_interval=limits_interval)
        else:
            _run_watch_dashboard(jsonl_files, console, original_terminal_settings, skip_limits=False, anonymize=anonymize, watch_interval=watch_interval, limits_interval=limits_interval)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        # Ctrl+C pressed - exit immediately without message
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Restore cursor
        try:
            console.show_cursor(True)
        except:
            pass

        # Always restore terminal settings before exiting
        if original_terminal_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
            except:
                pass


def _run_refresh_dashboard(jsonl_files: list[Path], console: Console, original_terminal_settings, refresh_interval: int = 30, anonymize: bool = False, limits_interval: int = 60) -> None:
    """
    Run dashboard with periodic refresh - updates at fixed intervals.

    Simpler than watch mode, just polls every N seconds. Good for environments where
    file watching might not work reliably.

    Keyboard shortcuts:
        w - Switch to weekly mode (default, current week limit period)
        m - Switch to monthly mode
        y - Switch to yearly mode (monthly statistics)
        h - Switch to heatmap view
        d - Switch to devices view
        q - Quit

    Args:
        jsonl_files: List of JSONL files to parse
        console: Rich console for output
        refresh_interval: Seconds between updates (default: 30)
        anonymize: Anonymize project names
        limits_interval: Usage limits update interval in seconds (default: 60)
    """
    console.print(
        f"\n[white]Refreshing every {refresh_interval} seconds... "
        f"Dashboard will update automatically.[/white]"
    )

    # Load user preferences from DB
    from src.storage.snapshot_db import load_user_preferences
    from src.config.defaults import DEFAULT_COLORS
    prefs = load_user_preferences()

    # Track current view mode, time offset, usage display mode, and color mode
    # Initialize from DB settings
    usage_display_mode = int(prefs.get('usage_display_mode', '0'))
    color_mode = prefs.get('color_mode', 'gradient')
    colors = {
        'color_solid': prefs.get('color_solid', DEFAULT_COLORS['color_solid']),
        'color_gradient_low': prefs.get('color_gradient_low', DEFAULT_COLORS['color_gradient_low']),
        'color_gradient_mid': prefs.get('color_gradient_mid', DEFAULT_COLORS['color_gradient_mid']),
        'color_gradient_high': prefs.get('color_gradient_high', DEFAULT_COLORS['color_gradient_high']),
        'color_unfilled': prefs.get('color_unfilled', DEFAULT_COLORS['color_unfilled']),
    }

    view_mode_ref = {
        'mode': "usage",
        'changed': False,
        'offset': 0,
        'usage_display_mode': usage_display_mode,
        'color_mode': color_mode,
        'colors': colors,
        'original_terminal_settings': original_terminal_settings,  # Store for settings page
    }
    stop_event = threading.Event()

    # Start keyboard listener thread
    keyboard_thread = threading.Thread(target=_keyboard_listener, args=(view_mode_ref, stop_event), daemon=False)
    keyboard_thread.start()

    # Start background limits updater thread
    limits_thread = threading.Thread(target=_limits_updater_thread, args=(stop_event, limits_interval), daemon=True)
    limits_thread.start()

    # Display initial dashboard (skip limits update - will be done by background thread)
    _display_dashboard(jsonl_files, console, skip_limits=False, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)

    try:
        # Keep refreshing at intervals
        last_refresh = time.time()
        while not stop_event.is_set():
            # Skip refresh if in settings mode
            if view_mode_ref.get('mode') == 'settings':
                time.sleep(0.1)
                continue

            # Check for view mode changes frequently
            if view_mode_ref.get('changed', False):
                view_mode_ref['changed'] = False
                updated_files = get_claude_jsonl_files()
                # Check if it's a manual refresh (r key) or just mode change
                if view_mode_ref.get('manual_refresh', False):
                    view_mode_ref['manual_refresh'] = False
                    # Manual refresh: update data
                    _display_dashboard(updated_files, console, skip_limits=False, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref, show_status=False)
                    last_refresh = time.time()  # Reset timer after manual refresh
                else:
                    # Mode change only: use cached data for instant switching
                    _display_dashboard(updated_files, console, skip_limits=True, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref, show_status=False)

            # Periodic refresh
            elif time.time() - last_refresh >= refresh_interval:
                updated_files = get_claude_jsonl_files()
                # Skip limits update - background thread handles it, no status messages
                _display_dashboard(updated_files, console, skip_limits=False, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref, show_status=False)
                last_refresh = time.time()

            time.sleep(0.05)  # Check frequently for keyboard input

    except KeyboardInterrupt:
        stop_event.set()
        raise
    finally:
        # Ensure threads finish
        stop_event.set()
        keyboard_thread.join(timeout=1.0)


def _run_watch_dashboard(jsonl_files: list[Path], console: Console, original_terminal_settings, skip_limits: bool = False, anonymize: bool = False, watch_interval: int = 60, limits_interval: int = 60) -> None:
    """
    Run dashboard with file watching - updates only when JSONL files change.

    More efficient than polling mode as it only updates when files actually change.
    Uses the watchdog library to monitor file system events.

    Keyboard shortcuts:
        w - Switch to weekly mode (default, current week limit period)
        m - Switch to monthly mode
        y - Switch to yearly mode (monthly statistics)
        h - Switch to heatmap view
        q - Quit

    Args:
        jsonl_files: List of JSONL files to parse
        console: Rich console for output
        skip_limits: Skip limits fetching for faster rendering
        anonymize: Anonymize project names
        watch_interval: File watch check interval in seconds (default: 60)
        limits_interval: Usage limits update interval in seconds (default: 60)
    """
    from src.utils.file_watcher import watch_claude_files

    console.print(
        "\n[white]Watching for file changes... "
        "Dashboard will update when Claude Code creates or modifies log files.[/white]"
    )

    # Load user preferences from DB
    from src.storage.snapshot_db import load_user_preferences
    from src.config.defaults import DEFAULT_COLORS
    prefs = load_user_preferences()

    # Track current view mode, time offset, usage display mode, and color mode
    # Initialize from DB settings
    usage_display_mode = int(prefs.get('usage_display_mode', '0'))
    color_mode = prefs.get('color_mode', 'gradient')
    colors = {
        'color_solid': prefs.get('color_solid', DEFAULT_COLORS['color_solid']),
        'color_gradient_low': prefs.get('color_gradient_low', DEFAULT_COLORS['color_gradient_low']),
        'color_gradient_mid': prefs.get('color_gradient_mid', DEFAULT_COLORS['color_gradient_mid']),
        'color_gradient_high': prefs.get('color_gradient_high', DEFAULT_COLORS['color_gradient_high']),
        'color_unfilled': prefs.get('color_unfilled', DEFAULT_COLORS['color_unfilled']),
    }

    view_mode_ref = {
        'mode': "usage",
        'changed': False,
        'offset': 0,
        'usage_display_mode': usage_display_mode,
        'color_mode': color_mode,
        'colors': colors,
        'original_terminal_settings': original_terminal_settings,  # Store for settings page
    }
    stop_event = threading.Event()

    # Start background limits updater thread
    limits_thread = threading.Thread(target=_limits_updater_thread, args=(stop_event, limits_interval), daemon=True)
    limits_thread.start()

    # Display initial dashboard (skip limits update - will be done by background thread)
    _display_dashboard(jsonl_files, console, skip_limits, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)

    # Start file watcher (monitors changes without immediate callback)
    watcher = watch_claude_files()
    watcher.start()

    # Start keyboard listener thread (NOT daemon so we can clean up properly)
    keyboard_thread = threading.Thread(target=_keyboard_listener, args=(view_mode_ref, stop_event), daemon=False)
    keyboard_thread.start()

    try:
        # Track last file check time
        last_file_check = time.time()

        # Keep the main thread alive and check for view mode changes and file updates
        while watcher.is_alive() and not stop_event.is_set():
            current_time = time.time()

            # Skip refresh if in settings mode
            if view_mode_ref.get('mode') == 'settings':
                time.sleep(0.1)
                continue

            # Check for view mode changes (instant response)
            if view_mode_ref.get('changed', False):
                # Refresh dashboard with new view mode
                view_mode_ref['changed'] = False
                updated_files = get_claude_jsonl_files()
                # Check if it's a manual refresh (r key) or just mode change
                if view_mode_ref.get('manual_refresh', False):
                    view_mode_ref['manual_refresh'] = False
                    # Manual refresh: update data
                    _display_dashboard(updated_files, console, skip_limits=False, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref, show_status=False)
                    last_file_check = current_time  # Reset timer after manual refresh
                else:
                    # Mode change only: use cached data for instant switching
                    _display_dashboard(updated_files, console, skip_limits=True, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref, show_status=False)

            # Check for file changes at specified interval
            elif current_time - last_file_check >= watch_interval:
                if watcher.get_and_reset_changes():
                    # Files changed - refresh dashboard without status messages
                    updated_files = get_claude_jsonl_files()
                    _display_dashboard(updated_files, console, skip_limits, skip_limits_update=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref, show_status=False)
                last_file_check = current_time

            time.sleep(0.05)  # Check more frequently for keyboard input

        # Stop watcher if quit was pressed
        if stop_event.is_set():
            watcher.stop()

    except KeyboardInterrupt:
        stop_event.set()
        watcher.stop()
        raise
    finally:
        # Ensure threads finish
        stop_event.set()
        keyboard_thread.join(timeout=1.0)


def _display_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False, skip_limits_update: bool = False, anonymize: bool = False, view_mode: str = "usage", view_mode_ref: dict | None = None, show_status: bool = True) -> None:
    """
    Ingest JSONL data and display dashboard.

    This performs two steps:
    1. Ingestion: Read JSONL files and save to DB (with deduplication)
    2. Display: Read from DB and render dashboard

    Args:
        jsonl_files: List of JSONL files to parse
        console: Rich console for output
        skip_limits: Skip ALL updates, read directly from DB (fast mode)
        skip_limits_update: Skip only limits update (use DB cache), but still update usage data
        anonymize: Anonymize project names to project-001, project-002, etc
        view_mode: Display mode - usage (default), weekly, monthly, yearly, or heatmap
        view_mode_ref: Reference dict to check for view mode changes and time offset (for interruption)
        show_status: Show status messages (default: True, set to False for instant mode switching)
    """
    from src.storage.snapshot_db import get_latest_limits, DEFAULT_DB_PATH, get_database_stats

    # Check if database exists when using --fast
    if skip_limits and not DEFAULT_DB_PATH.exists():
        console.clear()
        console.print("[red]Error: Cannot use --fast flag without existing database.[/red]")
        console.print("[yellow]Run 'ccu usage' (without --fast) first to create the database.[/yellow]")
        return

    # Update data unless in fast mode
    if not skip_limits:
        # Step 1: Update usage data
        if show_status:
            with console.status("[bold #ff8800]Updating usage data...", spinner="dots", spinner_style="#ff8800"):
                current_records = parse_all_jsonl_files(jsonl_files)

                # Save to database (with automatic deduplication via UNIQUE constraint)
                if current_records:
                    save_snapshot(current_records)
        else:
            # Fast mode: no status messages
            current_records = parse_all_jsonl_files(jsonl_files)
            if current_records:
                save_snapshot(current_records)

        # Step 2: Update limits data (if enabled and not skipped)
        if not skip_limits_update:
            tracking_mode = get_tracking_mode()
            if tracking_mode in ["both", "limits"]:
                # Run limits capture in a thread so we can interrupt it if mode changes
                limits_result = {'data': None, 'completed': False}

                def capture_limits_thread():
                    try:
                        limits_result['data'] = capture_limits()
                        limits_result['completed'] = True
                    except Exception:
                        limits_result['completed'] = True

                limits_thread = threading.Thread(target=capture_limits_thread, daemon=True)
                limits_thread.start()

                # Show spinner while waiting, but check for interruption
                if show_status:
                    with console.status("[bold #ff8800]Updating usage limits...", spinner="dots", spinner_style="#ff8800") as status:
                        while limits_thread.is_alive():
                            # Check if mode changed - if so, abandon limits update
                            if view_mode_ref and view_mode_ref.get('changed', False):
                                # Mode changed - stop waiting and proceed without limits update
                                break
                            time.sleep(0.1)  # Poll every 100ms
                else:
                    # Fast mode: wait without spinner
                    while limits_thread.is_alive():
                        if view_mode_ref and view_mode_ref.get('changed', False):
                            break
                        time.sleep(0.1)

                # Save limits if capture completed successfully
                if limits_result['completed']:
                    limits = limits_result['data']
                    if limits and "error" not in limits:
                        save_limits_snapshot(
                            session_pct=limits["session_pct"],
                            week_pct=limits["week_pct"],
                            opus_pct=limits["opus_pct"],
                            session_reset=limits["session_reset"],
                            week_reset=limits["week_reset"],
                            opus_reset=limits["opus_reset"],
                        )

    # Step 3: Prepare dashboard from database
    if show_status:
        with console.status("[bold #ff8800]Preparing dashboard...", spinner="dots", spinner_style="#ff8800"):
            all_records = load_historical_records()

            # Get latest limits from DB (if we saved them above or if they exist)
            limits_from_db = get_latest_limits()
    else:
        # Fast mode: no status messages
        all_records = load_historical_records()
        limits_from_db = get_latest_limits()

    if not all_records:
        console.clear()
        console.print(
            "[yellow]No Claude Code usage data found.[/yellow]\n"
            "[dim]This could mean:[/dim]\n"
            "[dim]  • Claude Code has not been used yet on this machine[/dim]\n"
            "[dim]  • No JSONL log files exist in ~/.claude/projects/[/dim]\n"
        )
        return

    # Clear screen before displaying dashboard
    console.clear()

    # Get time offset from view_mode_ref
    time_offset = view_mode_ref.get('offset', 0) if view_mode_ref else 0

    # Apply view mode filter
    display_records = all_records
    if view_mode in [VIEW_MODE_WEEKLY, "usage"] and limits_from_db and limits_from_db.get("week_reset"):
        # Parse week reset date and filter records
        week_reset_date = _parse_week_reset_date(limits_from_db["week_reset"])
        if week_reset_date:
            # Apply offset for week navigation
            adjusted_week_reset_date = week_reset_date - timedelta(weeks=-time_offset)
            display_records = _filter_records_by_week(all_records, adjusted_week_reset_date)
            if not display_records:
                # Fall back to monthly if no data in weekly range
                display_records = all_records
                view_mode = VIEW_MODE_MONTHLY
            else:
                # Store weekly dates for keyboard navigation
                # Extract unique dates and sort them (most recent first, matching daily breakdown display)
                from collections import defaultdict
                daily_data = defaultdict(int)
                for record in display_records:
                    if record.token_usage:
                        date = record.timestamp.strftime("%Y-%m-%d") if hasattr(record, 'timestamp') else record.date_key
                        daily_data[date] += record.token_usage.total_tokens

                # Sort by date in descending order (most recent first)
                sorted_dates = sorted(daily_data.keys(), reverse=True)

                # Store in view_mode_ref for keyboard listener
                if view_mode_ref:
                    view_mode_ref['weekly_dates'] = sorted_dates
    elif view_mode == VIEW_MODE_MONTHLY:
        # Filter by month with offset
        now = datetime.now()
        target_month = now.month + time_offset
        target_year = now.year

        # Adjust year if month goes out of bounds
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        while target_month > 12:
            target_month -= 12
            target_year += 1

        # Filter records for target month
        filtered = []
        for record in all_records:
            try:
                record_date = datetime.strptime(record.date_key, "%Y-%m-%d")
                if record_date.year == target_year and record_date.month == target_month:
                    filtered.append(record)
            except Exception:
                continue

        display_records = filtered if filtered else all_records
    elif view_mode == VIEW_MODE_YEARLY:
        # Filter by year with offset
        target_year = datetime.now().year + time_offset

        # Filter records for target year
        filtered = []
        for record in all_records:
            try:
                record_date = datetime.strptime(record.date_key, "%Y-%m-%d")
                if record_date.year == target_year:
                    filtered.append(record)
            except Exception:
                continue

        display_records = filtered if filtered else all_records

    # Get date range for footer
    dates = sorted(set(r.date_key for r in display_records))
    date_range = None
    if dates:
        # Convert from "YYYY-MM-DD" to "YY/MM/DD"
        def format_short_date(date_str: str) -> str:
            """Convert YYYY-MM-DD to YY/MM/DD"""
            parts = date_str.split("-")
            if len(parts) == 3:
                year = parts[0][-2:]  # Last 2 digits of year
                month = parts[1]
                day = parts[2]
                return f"{year}/{month}/{day}"
            return date_str

        start_date = format_short_date(dates[0])
        end_date = format_short_date(dates[-1])
        date_range = f"{start_date} ~ {end_date}"

    # Anonymize project names if requested
    if anonymize:
        display_records = _anonymize_projects(display_records)

    # Aggregate statistics
    stats = aggregate_all(display_records)

    # Render dashboard with limits from DB (no live fetch needed)
    # Note: fast_mode is always False to avoid showing warning message
    render_dashboard(stats, display_records, console, skip_limits=True, clear_screen=False, date_range=date_range, limits_from_db=limits_from_db, fast_mode=False, view_mode=view_mode, view_mode_ref=view_mode_ref)


def _anonymize_projects(records: list) -> list:
    """
    Anonymize project folder names by ranking them by total tokens and replacing
    with project-001, project-002, etc (where project-001 is the highest usage).

    Args:
        records: List of UsageRecord objects

    Returns:
        List of UsageRecord objects with anonymized folder names
    """
    from collections import defaultdict
    from dataclasses import replace

    # Calculate total tokens per project
    project_totals = defaultdict(int)
    for record in records:
        if record.token_usage:
            project_totals[record.folder] += record.token_usage.total_tokens

    # Sort projects by total tokens (descending) and create mapping
    sorted_projects = sorted(project_totals.items(), key=lambda x: x[1], reverse=True)
    project_mapping = {
        folder: f"project-{str(i+1).zfill(3)}"
        for i, (folder, _) in enumerate(sorted_projects)
    }

    # Replace folder names in records
    anonymized_records = []
    for record in records:
        anonymized_records.append(
            replace(record, folder=project_mapping.get(record.folder, record.folder))
        )

    return anonymized_records


#endregion
