#region Imports
import sys
import time
from pathlib import Path

from rich.console import Console

from claude_goblin_usage.aggregation.daily_stats import aggregate_all
from claude_goblin_usage.config.settings import (
    DEFAULT_REFRESH_INTERVAL,
    get_claude_jsonl_files,
)
from claude_goblin_usage.config.user_config import get_storage_mode
from claude_goblin_usage.data.jsonl_parser import parse_all_jsonl_files
from claude_goblin_usage.storage.snapshot_db import (
    get_database_stats,
    load_historical_records,
    save_snapshot,
)
from claude_goblin_usage.visualization.dashboard import render_dashboard
#endregion


#region Functions


def run(console: Console, live: bool = False, fast: bool = False) -> None:
    """
    Handle the usage command.

    Loads Claude Code usage data and displays a dashboard with GitHub-style
    activity graph and statistics. Supports live refresh mode.

    Args:
        console: Rich console for output
        live: Enable auto-refresh mode (default: False)
        fast: Skip limits fetching for faster rendering (default: False)

    Exit:
        Exits with status 0 on success, 1 on error
    """
    # Check sys.argv for backward compatibility (hooks still use old style)
    run_live = live or "--live" in sys.argv
    skip_limits = fast or "--fast" in sys.argv

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

        # Run with or without live refresh
        if run_live:
            _run_live_dashboard(jsonl_files, console, skip_limits)
        else:
            _display_dashboard(jsonl_files, console, skip_limits)

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


def _run_live_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False) -> None:
    """
    Run dashboard with auto-refresh.

    Args:
        jsonl_files: List of JSONL files to parse
        console: Rich console for output
        skip_limits: Skip limits fetching for faster rendering
    """
    console.print(
        f"[dim]Auto-refreshing every {DEFAULT_REFRESH_INTERVAL} seconds. "
        "Press Ctrl+C to exit.[/dim]\n"
    )

    while True:
        try:
            _display_dashboard(jsonl_files, console, skip_limits)
            time.sleep(DEFAULT_REFRESH_INTERVAL)
        except KeyboardInterrupt:
            raise


def _display_dashboard(jsonl_files: list[Path], console: Console, skip_limits: bool = False) -> None:
    """
    Ingest JSONL data and display dashboard.

    This performs two steps:
    1. Ingestion: Read JSONL files and save to DB (with deduplication)
    2. Display: Read from DB and render dashboard

    Args:
        jsonl_files: List of JSONL files to parse
        console: Rich console for output
        skip_limits: Skip limits fetching for faster rendering
    """
    # Step 1: Ingestion - parse JSONL and save to DB
    with console.status("[bold #ff8800]Ingesting session data...", spinner="dots", spinner_style="#ff8800"):
        current_records = parse_all_jsonl_files(jsonl_files)

        # Save to database (with automatic deduplication via UNIQUE constraint)
        if current_records:
            save_snapshot(current_records, storage_mode=get_storage_mode())

    # Step 2: Display - read from database only
    with console.status("[bold #ff8800]Loading data from database...", spinner="dots", spinner_style="#ff8800"):
        all_records = load_historical_records()

    if not all_records:
        console.clear()
        console.print(
            "[yellow]No usage data found in database. Run --update-usage to ingest data.[/yellow]"
        )
        return

    # Clear screen before displaying dashboard
    console.clear()

    # Get date range for footer
    dates = sorted(set(r.date_key for r in all_records))
    date_range = None
    if dates:
        date_range = f"{dates[0]} to {dates[-1]}"

    # Aggregate statistics
    stats = aggregate_all(all_records)

    # Render dashboard
    render_dashboard(stats, all_records, console, skip_limits=skip_limits, clear_screen=False, date_range=date_range)


#endregion
