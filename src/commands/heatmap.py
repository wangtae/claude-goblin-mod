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

    Shows 3 heatmaps: token usage, week limit %, and opus limit %
    with the same visual design as PNG export but rendered directly
    in the terminal using Unicode block characters and colors.

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

        # Load limits data
        limits_data = _load_limits_data()

        # Display heatmaps
        _display_heatmap(console, stats, limits_data, year)

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


def _display_heatmap(console: Console, stats, limits_data: dict, year: Optional[int] = None) -> None:
    """
    Display 3 GitHub-style heatmaps in terminal: tokens, week %, opus %.

    Uses the same visual design as PNG export with Claude theme colors.

    Args:
        console: Rich console for output
        stats: Aggregated statistics
        limits_data: Dictionary mapping dates to week_pct and opus_pct
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

    # Day names
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Helper function to display one heatmap
    def display_single_heatmap(heatmap_title: str, color_func, legend_colors, legend_left: str, legend_right: str):
        console.print(f"[dim]{heatmap_title}[/dim]")
        console.print()

        # Build month label line
        month_line = "    "  # Space for day labels
        last_month = None
        for week in weeks:
            month_added = False
            for day_stats, date in week:
                if date is not None and not month_added:
                    month = date.month
                    if month != last_month:
                        month_name = date.strftime("%b")
                        # Take first char + "…" for compact display
                        month_line += month_name[0] + "… "
                        last_month = month
                        month_added = True
                    break
            if not month_added:
                month_line += "   "  # 3 spaces to match cell width

        console.print(Text(month_line, style="dim"))

        # Display 7 rows (one per day of week)
        for day_idx in range(7):
            line = Text()
            line.append(day_names[day_idx], style="dim")
            line.append(" ", style="")

            for week_idx, week in enumerate(weeks):
                day_stats, date = week[day_idx]

                if date is None:
                    line.append("   ", style="")  # 3 spaces: 2 for cell + 1 for gap
                else:
                    color_style = color_func(day_stats, date)
                    line.append("██", style=color_style)
                    line.append(" ", style="")  # Gap between cells

            console.print(line)

        console.print()

        # Legend
        legend = Text()
        legend.append(legend_left + " ", style="dim")
        for color in legend_colors:
            legend.append("██", style=color)
            legend.append(" ", style="")
        legend.append(legend_right, style="dim")

        console.print(legend)
        console.print()

    # 1. Token Usage heatmap
    def tokens_color_func(day_stats, date):
        return _get_tokens_style(day_stats, max_tokens, date, today)

    # Legend colors matching PNG export: dark grey + 4 orange shades
    token_legend_colors = [
        "#3C3C3A",  # Dark grey (no activity)
        "#66554D",  # 20% orange
        "#8A6E61",  # 40% orange
        "#AE8775",  # 60% orange
        "#D2A089",  # 80% orange
        "#CB7B5D",  # Full orange
    ]
    display_single_heatmap("Token Usage", tokens_color_func, token_legend_colors, "Less", "More")

    # 2. Week Limit % heatmap (blue → red gradient)
    def week_color_func(day_stats, date):
        date_key = date.strftime("%Y-%m-%d")
        week_pct = limits_data.get(date_key, {}).get("week_pct", 0)
        return _get_limits_style(week_pct, (93, 150, 203), date, today)

    # Legend: blue → red → dark red
    week_legend_colors = [
        "#5D96CB",  # Blue (0%)
        "#A36BA8",  # 33%
        "#CB5D5D",  # Red (100%)
        "#782850",  # Dark red (>100%)
    ]
    display_single_heatmap("Week Limit %", week_color_func, week_legend_colors, "0%", "100%+")

    # 3. Opus Limit % heatmap (green → red gradient)
    def opus_color_func(day_stats, date):
        date_key = date.strftime("%Y-%m-%d")
        opus_pct = limits_data.get(date_key, {}).get("opus_pct", 0)
        return _get_limits_style(opus_pct, (93, 203, 123), date, today)

    # Legend: green → red → dark red
    opus_legend_colors = [
        "#5DCB7B",  # Green (0%)
        "#A36B99",  # 33%
        "#CB5D5D",  # Red (100%)
        "#782850",  # Dark red (>100%)
    ]
    display_single_heatmap("Opus Limit %", opus_color_func, opus_legend_colors, "0%", "100%+")

    # Summary stats
    total_days = sum(1 for s in stats.daily_stats.values() if s.total_tokens > 0)
    total_tokens = sum(s.total_tokens for s in stats.daily_stats.values())
    console.print(f"[dim]Total: {total_tokens:,} tokens across {total_days} active days[/dim]")
    console.print()
    console.print("[dim]Tip: Use [bold]ccg export --open[/bold] for high-resolution PNG[/dim]")


def _load_limits_data() -> dict:
    """
    Load limits data from database.

    Returns:
        Dictionary mapping dates to {"week_pct": int, "opus_pct": int}
    """
    from src.storage.snapshot_db import DEFAULT_DB_PATH
    import sqlite3

    limits_data = {}

    try:
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()

        # Load limits snapshots
        cursor.execute("""
            SELECT date, week_used, week_limit, opus_used, opus_limit
            FROM limits_snapshots
            ORDER BY timestamp DESC
        """)

        for row in cursor.fetchall():
            date_str, week_used, week_limit, opus_used, opus_limit = row
            week_pct = int((week_used / week_limit * 100)) if week_limit > 0 else 0
            opus_pct = int((opus_used / opus_limit * 100)) if opus_limit > 0 else 0

            limits_data[date_str] = {
                "week_pct": week_pct,
                "opus_pct": opus_pct
            }

        conn.close()
    except:
        pass

    return limits_data


def _get_tokens_style(day_stats, max_tokens: int, date, today) -> str:
    """
    Get Rich color style for token usage (same as PNG export).

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


def _get_limits_style(pct: int, base_color_rgb: tuple[int, int, int], date, today) -> str:
    """
    Get Rich color style for limits percentage (same as PNG export).

    0% = base_color (blue/green), 100% = red, >100% = dark red/purple

    Args:
        pct: Usage percentage (0-100+)
        base_color_rgb: Base color (blue for week, green for opus)
        date: The date of this cell
        today: Today's date

    Returns:
        Rich color style string
    """
    # Future days: light grey
    if date > today:
        return "#6B6B68"

    # Past days with no data: dark grey
    if pct == 0:
        return "#3C3C3A"

    # >100%: dark red/purple
    if pct > 100:
        return "#782850"

    # 0-100%: interpolate from base_color to red
    ratio = pct / 100.0
    red = (203, 93, 93)

    r = int(base_color_rgb[0] + (red[0] - base_color_rgb[0]) * ratio)
    g = int(base_color_rgb[1] + (red[1] - base_color_rgb[1]) * ratio)
    b = int(base_color_rgb[2] + (red[2] - base_color_rgb[2]) * ratio)

    return f"#{r:02x}{g:02x}{b:02x}"


#endregion
