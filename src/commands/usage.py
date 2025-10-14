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
                key = sys.stdin.read(1).lower()

                if key == 'w':
                    view_mode_ref['mode'] = VIEW_MODE_WEEKLY
                    view_mode_ref['changed'] = True
                elif key == 'm':
                    view_mode_ref['mode'] = VIEW_MODE_MONTHLY
                    view_mode_ref['changed'] = True
                elif key == 'y':
                    view_mode_ref['mode'] = VIEW_MODE_YEARLY
                    view_mode_ref['changed'] = True
                elif key == 'h':
                    view_mode_ref['mode'] = VIEW_MODE_HEATMAP
                    view_mode_ref['changed'] = True
                elif key == 'q':
                    stop_event.set()

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def run(console: Console, live: bool = False, watch: bool = False, fast: bool = False, anon: bool = False) -> None:
    """
    Handle the usage command.

    Loads Claude Code usage data and displays a dashboard with GitHub-style
    activity graph and statistics. Supports live refresh and file watching modes.

    Args:
        console: Rich console for output
        live: Enable auto-refresh mode with 5-second polling (default: False)
        watch: Enable file watching mode - updates only when files change (default: False)
        fast: Skip limits fetching for faster rendering (default: False)
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
    run_live = live or "--live" in sys.argv
    run_watch = watch or "--watch" in sys.argv
    skip_limits = fast or "--fast" in sys.argv
    anonymize = anon or "--anon" in sys.argv

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

        # Run with watch mode, live mode, or single display
        if run_watch:
            _run_watch_dashboard(jsonl_files, console, skip_limits, anonymize)
        elif run_live:
            _run_live_dashboard(jsonl_files, console, skip_limits, anonymize)
        else:
            _display_dashboard(jsonl_files, console, skip_limits, anonymize)

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
        "[dim]Watching for file changes... "
        "Dashboard will update when Claude Code creates or modifies log files.[/dim]\n"
        "[dim]Keyboard shortcuts: [w] Weekly | [m] Monthly | [y] Yearly | [h] Heatmap | [q] Quit[/dim]\n"
    )

    # Track current view mode
    view_mode_ref = {'mode': VIEW_MODE_WEEKLY, 'changed': False}
    stop_event = threading.Event()

    # Display initial dashboard
    _display_dashboard(jsonl_files, console, skip_limits, anonymize, view_mode=view_mode_ref['mode'])

    # Create callback that refreshes dashboard
    def on_file_change():
        # Re-fetch file list (in case new files were created)
        updated_files = get_claude_jsonl_files()
        _display_dashboard(updated_files, console, skip_limits, anonymize, view_mode=view_mode_ref['mode'])

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
                _display_dashboard(updated_files, console, skip_limits, anonymize, view_mode=view_mode_ref['mode'])
            time.sleep(0.2)  # Check more frequently for keyboard input

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


def _run_live_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False, anonymize: bool = False) -> None:
    """
    Run dashboard with auto-refresh (polling mode).

    Updates every 5 seconds regardless of whether files changed.
    Use --watch mode for more efficient file-change-based updates.

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
    console.print(
        f"[dim]Auto-refreshing every {DEFAULT_REFRESH_INTERVAL} seconds.[/dim]\n"
        "[dim]Keyboard shortcuts: [w] Weekly | [m] Monthly | [y] Yearly | [h] Heatmap | [q] Quit[/dim]\n"
        "[dim]Tip: Use --watch for more efficient file-change-based updates.[/dim]\n"
    )

    # Track current view mode
    view_mode_ref = {'mode': VIEW_MODE_WEEKLY, 'changed': False}
    stop_event = threading.Event()

    # Start keyboard listener thread (NOT daemon so we can clean up properly)
    keyboard_thread = threading.Thread(target=_keyboard_listener, args=(view_mode_ref, stop_event), daemon=False)
    keyboard_thread.start()

    try:
        while not stop_event.is_set():
            _display_dashboard(jsonl_files, console, skip_limits, anonymize, view_mode=view_mode_ref['mode'])

            # Sleep in small intervals to check for keyboard input
            for _ in range(int(DEFAULT_REFRESH_INTERVAL / 0.2)):
                if stop_event.is_set() or view_mode_ref.get('changed', False):
                    # If view changed, reset flag and refresh immediately
                    if view_mode_ref.get('changed', False):
                        view_mode_ref['changed'] = False
                    break
                time.sleep(0.2)

    except KeyboardInterrupt:
        stop_event.set()
        raise
    finally:
        # Ensure keyboard listener thread finishes and restores terminal
        stop_event.set()
        keyboard_thread.join(timeout=1.0)


def _display_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False, anonymize: bool = False, view_mode: str = VIEW_MODE_WEEKLY) -> None:
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
        view_mode: Display mode - weekly (default), monthly, yearly, or heatmap
    """
    from src.storage.snapshot_db import get_latest_limits, DEFAULT_DB_PATH, get_database_stats

    # Check if database exists when using --fast
    if skip_limits and not DEFAULT_DB_PATH.exists():
        console.clear()
        console.print("[red]Error: Cannot use --fast flag without existing database.[/red]")
        console.print("[yellow]Run 'ccg usage' (without --fast) first to create the database.[/yellow]")
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
            with console.status("[bold #ff8800]Updating usage limits...", spinner="dots", spinner_style="#ff8800"):
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

    # Get date range for footer
    dates = sorted(set(r.date_key for r in display_records))
    date_range = None
    if dates:
        date_range = f"{dates[0]} to {dates[-1]}"

    # Anonymize project names if requested
    if anonymize:
        display_records = _anonymize_projects(display_records)

    # Aggregate statistics
    stats = aggregate_all(display_records)

    # Render dashboard with limits from DB (no live fetch needed)
    render_dashboard(stats, display_records, console, skip_limits=True, clear_screen=False, date_range=date_range, limits_from_db=limits_from_db, fast_mode=skip_limits, view_mode=view_mode)


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
