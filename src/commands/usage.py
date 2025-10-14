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
from src.config.user_config import get_storage_mode, get_tracking_mode
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
                    # Read the rest of the escape sequence
                    # Arrow keys send: ESC [ A/B/C/D
                    remaining = []
                    for _ in range(2):  # Read next 2 characters
                        if select.select([sys.stdin], [], [], 0.05)[0]:
                            remaining.append(sys.stdin.read(1))

                    # Check if it's an arrow key
                    if len(remaining) == 2 and remaining[0] == '[':
                        arrow = remaining[1]
                        if arrow == 'D':  # Left arrow
                            # Go to previous period
                            if view_mode_ref['mode'] in [VIEW_MODE_MONTHLY, VIEW_MODE_YEARLY]:
                                view_mode_ref['offset'] = view_mode_ref.get('offset', 0) - 1
                                view_mode_ref['changed'] = True
                        elif arrow == 'C':  # Right arrow
                            # Go to next period (don't go beyond current)
                            if view_mode_ref['mode'] in [VIEW_MODE_MONTHLY, VIEW_MODE_YEARLY]:
                                current_offset = view_mode_ref.get('offset', 0)
                                if current_offset < 0:  # Only allow if we're in the past
                                    view_mode_ref['offset'] = current_offset + 1
                                    view_mode_ref['changed'] = True
                    continue

                key = key.lower()

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
                elif key == 'q':
                    stop_event.set()

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def run(console: Console, refresh: int | None = None, anon: bool = False) -> None:
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

    # Check sys.argv for backward compatibility (hooks still use old style)
    anonymize = anon or "--anon" in sys.argv

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

        console.print(f"[dim]Found {len(jsonl_files)} session files[/dim]", end="")

        # Choose between refresh mode (polling) or watch mode (file events)
        if refresh is not None:
            _run_refresh_dashboard(jsonl_files, console, refresh_interval=refresh, anonymize=anonymize)
        else:
            _run_watch_dashboard(jsonl_files, console, skip_limits=False, anonymize=anonymize)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[cyan]Exiting...[/cyan]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always restore terminal settings before exiting
        if original_terminal_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_terminal_settings)
            except:
                pass


def _run_refresh_dashboard(jsonl_files: list[Path], console: Console, refresh_interval: int = 30, anonymize: bool = False) -> None:
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
    """
    console.print(
        f"\n[white]Refreshing every {refresh_interval} seconds... "
        f"Dashboard will update automatically.[/white]"
    )

    # Track current view mode and time offset
    view_mode_ref = {'mode': "usage", 'changed': False, 'offset': 0}
    stop_event = threading.Event()

    # Start keyboard listener thread
    keyboard_thread = threading.Thread(target=_keyboard_listener, args=(view_mode_ref, stop_event), daemon=False)
    keyboard_thread.start()

    # Display initial dashboard
    _display_dashboard(jsonl_files, console, skip_limits=False, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)

    try:
        # Keep refreshing at intervals
        last_refresh = time.time()
        while not stop_event.is_set():
            # Check for view mode changes frequently
            if view_mode_ref.get('changed', False):
                view_mode_ref['changed'] = False
                updated_files = get_claude_jsonl_files()
                # Use skip_limits=True for faster response on view mode changes
                _display_dashboard(updated_files, console, skip_limits=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)
                last_refresh = time.time()  # Reset timer after manual refresh

            # Periodic refresh
            elif time.time() - last_refresh >= refresh_interval:
                updated_files = get_claude_jsonl_files()
                _display_dashboard(updated_files, console, skip_limits=False, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)
                last_refresh = time.time()

            time.sleep(0.05)  # Check frequently for keyboard input

    except KeyboardInterrupt:
        stop_event.set()
        raise
    finally:
        # Ensure keyboard listener thread finishes
        stop_event.set()
        keyboard_thread.join(timeout=1.0)


def _run_watch_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False, anonymize: bool = False) -> None:
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
    """
    from src.utils.file_watcher import watch_claude_files

    console.print(
        "\n[white]Watching for file changes... "
        "Dashboard will update when Claude Code creates or modifies log files.[/white]"
    )

    # Track current view mode and time offset
    view_mode_ref = {'mode': "usage", 'changed': False, 'offset': 0}
    stop_event = threading.Event()

    # Display initial dashboard
    _display_dashboard(jsonl_files, console, skip_limits, anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)

    # Create callback that refreshes dashboard
    def on_file_change():
        # Re-fetch file list (in case new files were created)
        updated_files = get_claude_jsonl_files()
        _display_dashboard(updated_files, console, skip_limits, anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)

    # Start file watcher with 10-second debounce to prevent rapid-fire updates
    # when Claude Code generates multiple responses in succession
    watcher = watch_claude_files(on_file_change, debounce_seconds=10.0)
    watcher.start()

    # Start keyboard listener thread (NOT daemon so we can clean up properly)
    keyboard_thread = threading.Thread(target=_keyboard_listener, args=(view_mode_ref, stop_event), daemon=False)
    keyboard_thread.start()

    try:
        # Keep the main thread alive and check for view mode changes
        while watcher.is_alive() and not stop_event.is_set():
            if view_mode_ref.get('changed', False):
                # Refresh dashboard with new view mode
                view_mode_ref['changed'] = False
                updated_files = get_claude_jsonl_files()
                # Use skip_limits=True for faster response on view mode changes
                _display_dashboard(updated_files, console, skip_limits=True, anonymize=anonymize, view_mode=view_mode_ref['mode'], view_mode_ref=view_mode_ref)
            time.sleep(0.05)  # Check more frequently for keyboard input

        # Stop watcher if quit was pressed
        if stop_event.is_set():
            watcher.stop()

    except KeyboardInterrupt:
        stop_event.set()
        watcher.stop()
        raise
    finally:
        # Ensure keyboard listener thread finishes and restores terminal
        stop_event.set()
        keyboard_thread.join(timeout=1.0)


def _display_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False, anonymize: bool = False, view_mode: str = "usage", view_mode_ref: dict | None = None) -> None:
    """
    Ingest JSONL data and display dashboard.

    This performs two steps:
    1. Ingestion: Read JSONL files and save to DB (with deduplication)
    2. Display: Read from DB and render dashboard

    Args:
        jsonl_files: List of JSONL files to parse
        console: Rich console for output
        skip_limits: Skip ALL updates, read directly from DB (fast mode)
        anonymize: Anonymize project names to project-001, project-002, etc
        view_mode: Display mode - usage (default), weekly, monthly, yearly, or heatmap
        view_mode_ref: Reference dict to check for view mode changes and time offset (for interruption)
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
        with console.status("[bold #ff8800]Updating usage data...", spinner="dots", spinner_style="#ff8800"):
            current_records = parse_all_jsonl_files(jsonl_files)

            # Save to database (with automatic deduplication via UNIQUE constraint)
            if current_records:
                save_snapshot(current_records, storage_mode=get_storage_mode())

        # Step 2: Update limits data (if enabled)
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
            with console.status("[bold #ff8800]Updating usage limits...", spinner="dots", spinner_style="#ff8800") as status:
                while limits_thread.is_alive():
                    # Check if mode changed - if so, abandon limits update
                    if view_mode_ref and view_mode_ref.get('changed', False):
                        # Mode changed - stop waiting and proceed without limits update
                        break
                    time.sleep(0.1)  # Poll every 100ms

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
    with console.status("[bold #ff8800]Preparing dashboard...", spinner="dots", spinner_style="#ff8800"):
        all_records = load_historical_records()

        # Get latest limits from DB (if we saved them above or if they exist)
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
    if view_mode == VIEW_MODE_WEEKLY and limits_from_db and limits_from_db.get("week_reset"):
        # Parse week reset date and filter records
        week_reset_date = _parse_week_reset_date(limits_from_db["week_reset"])
        if week_reset_date:
            display_records = _filter_records_by_week(all_records, week_reset_date)
            if not display_records:
                # Fall back to monthly if no data in weekly range
                display_records = all_records
                view_mode = VIEW_MODE_MONTHLY
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
    render_dashboard(stats, display_records, console, skip_limits=True, clear_screen=False, date_range=date_range, limits_from_db=limits_from_db, fast_mode=False, view_mode=view_mode)


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
