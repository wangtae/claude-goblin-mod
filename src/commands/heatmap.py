#region Imports
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.aggregation.daily_stats import aggregate_all
from src.config.settings import get_claude_jsonl_files
from src.config.user_config import get_storage_mode
from src.data.jsonl_parser import parse_all_jsonl_files
from src.storage.snapshot_db import load_historical_records, save_snapshot
#endregion


#region Functions


def run(console: Console, year: Optional[int] = None, fast: bool = False) -> None:
    """
    Display GitHub-style activity heatmap in the terminal.

    Shows token usage across the year with the same visual design as PNG export
    but rendered directly in the terminal using Unicode block characters and colors.

    Args:
        console: Rich console for output
        year: Year to display (defaults to current year)
        fast: Skip data collection, read from database only

    Exit:
        Exits with status 0 on success, 1 on error
    """
    import sys

    try:
        # Load and update data (unless fast mode)
        if not fast:
            with console.status("[bold #ff8800]Loading Claude Code usage data...", spinner="dots", spinner_style="#ff8800"):
                jsonl_files = get_claude_jsonl_files()

            if not jsonl_files:
                console.print(
                    "[yellow]No Claude Code data found. "
                    "Make sure you've used Claude Code at least once.[/yellow]"
                )
                return

            # Update data
            with console.status("[bold #ff8800]Updating usage data...", spinner="dots", spinner_style="#ff8800"):
                current_records = parse_all_jsonl_files(jsonl_files)
                if current_records:
                    save_snapshot(current_records, storage_mode=get_storage_mode())

        # Load from database
        with console.status("[bold #ff8800]Preparing heatmap...", spinner="dots", spinner_style="#ff8800"):
            all_records = load_historical_records()

        if not all_records:
            console.print(
                "[yellow]No Claude Code usage data found.[/yellow]\n"
                "[dim]This could mean:[/dim]\n"
                "[dim]  • Claude Code has not been used yet on this machine[/dim]\n"
                "[dim]  • No JSONL log files exist in ~/.claude/projects/[/dim]\n"
            )
            return

        # Aggregate statistics
        stats = aggregate_all(all_records)

        # Display heatmap
        _display_heatmap(console, stats, year)

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


def _display_heatmap(console: Console, stats, year: Optional[int] = None) -> None:
    """
    Display GitHub-style heatmap in terminal.

    Uses the same visual design as PNG export with Claude theme colors.

    Args:
        console: Rich console for output
        stats: Aggregated statistics
        year: Year to display (defaults to current year)
    """
    # Determine year
    today = datetime.now().date()
    display_year = year if year is not None else today.year
    start_date = datetime(display_year, 1, 1).date()
    end_date = datetime(display_year, 12, 31).date()

    # Build weeks structure (same as PNG export)
    jan1_day = (start_date.weekday() + 1) % 7
    weeks = []
    current_week = []

    # Pad first week
    for _ in range(jan1_day):
        current_week.append((None, None))

    # Add all days
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.strftime("%Y-%m-%d")
        day_stats = stats.daily_stats.get(date_key)
        current_week.append((day_stats, current_date))

        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []

        current_date += timedelta(days=1)

    # Pad final week
    if current_week:
        while len(current_week) < 7:
            current_week.append((None, None))
        weeks.append(current_week)

    # Calculate max tokens for color scaling
    max_tokens = max(
        (s.total_tokens for s in stats.daily_stats.values()), default=1
    ) if stats.daily_stats else 1

    # Clear screen and display
    console.clear()

    # Title with Claude guy icon
    title = Text()
    title.append("🤖 ", style="bold")
    title.append(f"Your Claude Code activity in {display_year}", style="bold white")
    console.print(title)
    console.print()

    # Create heatmap table
    table = Table(show_header=False, show_edge=False, pad_edge=False, padding=(0, 0), box=None)

    # Add day labels column
    table.add_column("", justify="right", width=4, style="dim")

    # Add month label row with proper spacing
    month_row = [""]
    last_month = None
    for week_idx, week in enumerate(weeks):
        for day_stats, date in week:
            if date is not None:
                month = date.month
                if month != last_month:
                    month_name = date.strftime("%b")
                    month_row.append(month_name)
                    last_month = month
                else:
                    month_row.append("")
                break
        else:
            month_row.append("")

    # Add week columns (one per week)
    for _ in range(len(weeks)):
        table.add_column("", width=2)

    # Add month labels row
    table.add_row(*[Text(m, style="dim") for m in month_row])

    # Day names
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Add heatmap rows (one per day of week)
    for day_idx in range(7):
        row = [Text(day_names[day_idx], style="dim")]

        for week in weeks:
            day_stats, date = week[day_idx]

            if date is None:
                # Empty cell
                cell = Text("  ")
            else:
                # Get color based on activity
                color_style = _get_cell_style(day_stats, max_tokens, date, today)
                cell = Text("██", style=color_style)

            row.append(cell)

        table.add_row(*row)

    console.print(table)
    console.print()

    # Legend
    legend = Text()
    legend.append("Less ", style="dim")
    legend.append("██", style="#3C3C3A")  # Dark grey (no activity)
    legend.append(" ", style="")
    legend.append("██", style="#7E5E54")  # 20% orange
    legend.append(" ", style="")
    legend.append("██", style="#9F7A68")  # 40% orange
    legend.append(" ", style="")
    legend.append("██", style="#BF977C")  # 60% orange
    legend.append(" ", style="")
    legend.append("██", style="#E0B491")  # 80% orange
    legend.append(" ", style="")
    legend.append("██", style="#CB7B5D")  # Full orange
    legend.append(" More", style="dim")

    console.print(legend)
    console.print()

    # Summary stats
    total_days = sum(1 for s in stats.daily_stats.values() if s.total_tokens > 0)
    total_tokens = sum(s.total_tokens for s in stats.daily_stats.values())
    console.print(f"[dim]Total: {total_tokens:,} tokens across {total_days} active days[/dim]")
    console.print()
    console.print("[dim]Tip: Use [bold]ccg export --open[/bold] for high-resolution PNG[/dim]")


def _get_cell_style(day_stats, max_tokens: int, date, today) -> str:
    """
    Get Rich color style for a cell based on activity level.

    Uses the same color logic as PNG export with Claude theme colors.

    Args:
        day_stats: Statistics for the day
        max_tokens: Maximum tokens for scaling
        date: The date of this cell
        today: Today's date

    Returns:
        Rich color style string
    """
    # Future days: light grey
    if date > today:
        return "#6B6B68"

    # Past days with no activity: dark grey
    if not day_stats or day_stats.total_tokens == 0:
        return "#3C3C3A"

    # Calculate intensity ratio (0.0 to 1.0)
    ratio = day_stats.total_tokens / max_tokens if max_tokens > 0 else 0

    # Apply non-linear scaling (same as PNG export)
    ratio = ratio ** 0.5

    # Interpolate from dark grey (#3C3C3A) to orange (#CB7B5D)
    dark_grey = (60, 60, 58)
    orange = (203, 123, 93)

    r = int(dark_grey[0] + (orange[0] - dark_grey[0]) * ratio)
    g = int(dark_grey[1] + (orange[1] - dark_grey[1]) * ratio)
    b = int(dark_grey[2] + (orange[2] - dark_grey[2]) * ratio)

    return f"#{r:02x}{g:02x}{b:02x}"


#endregion
