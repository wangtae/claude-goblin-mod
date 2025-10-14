#region Imports
from collections import defaultdict
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn
from rich.spinner import Spinner

from src.aggregation.daily_stats import AggregatedStats
from src.models.usage_record import UsageRecord
from src.storage.snapshot_db import get_limits_data
#endregion


#region Constants
# Claude-inspired color scheme
ORANGE = "#ff8800"
CYAN = "cyan"
DIM = "grey50"
BAR_WIDTH = 20
#endregion


#region Functions


def _format_number(num: int) -> str:
    """
    Format number with thousands separator and appropriate suffix.

    Args:
        num: Number to format

    Returns:
        Formatted string (e.g., "1.4bn", "523.7M", "45.2K", "1.234")
    """
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}bn".replace(".", ".")
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M".replace(".", ".")
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K".replace(".", ".")
    else:
        # Add thousands separator for numbers < 1000
        return f"{num:,}".replace(",", ".")


def _create_bar(value: int, max_value: int, width: int = BAR_WIDTH, color: str = ORANGE) -> Text:
    """
    Create a simple text bar for visualization.

    Args:
        value: Current value
        max_value: Maximum value for scaling
        width: Width of bar in characters
        color: Color for the filled portion of the bar

    Returns:
        Rich Text object with colored bar
    """
    if max_value == 0:
        return Text("▬" * width, style=DIM)

    filled = int((value / max_value) * width)
    bar = Text()
    bar.append("▬" * filled, style=color)
    bar.append("▬" * (width - filled), style=DIM)
    return bar


def render_dashboard(stats: AggregatedStats, records: list[UsageRecord], console: Console, skip_limits: bool = False, clear_screen: bool = True, date_range: str = None, limits_from_db: dict | None = None, fast_mode: bool = False, view_mode: str = "usage") -> None:
    """
    Render a concise, modern dashboard with KPI cards and breakdowns.

    Args:
        stats: Aggregated statistics
        records: Raw usage records for detailed breakdowns
        console: Rich console for rendering
        skip_limits: If True, skip fetching current limits for faster display
        clear_screen: If True, clear the screen before rendering (default True)
        date_range: Optional date range string to display in footer
        limits_from_db: Pre-fetched limits from database (avoids live fetch)
        fast_mode: If True, show warning that data is from last update
        view_mode: Display mode - "usage", "weekly", "monthly", "yearly", "heatmap", or "devices" (default: "usage")
    """
    # Optionally clear screen and reset cursor to top
    if clear_screen:
        import os
        # Use system clear command for complete terminal reset
        os.system('clear')

    # For heatmap mode, show heatmap instead of dashboard
    if view_mode == "heatmap":
        from src.commands.heatmap import _display_heatmap, _load_limits_data
        limits_data = _load_limits_data()
        _display_heatmap(console, stats, limits_data, year=None)
        # Show footer with keyboard shortcuts
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True)
        console.print()
        console.print(footer)
        return

    # For devices mode, show device statistics
    if view_mode == "devices":
        from src.visualization.device_stats import render_device_statistics
        render_device_statistics(console)
        # Show footer with keyboard shortcuts
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True)
        console.print()
        console.print(footer)
        return

    # For usage mode, show only Usage Limits
    if view_mode == "usage":
        from src.commands.limits import capture_limits
        from src.models.pricing import format_cost

        # Fetch limits
        if console:
            with console.status(f"[bold {ORANGE}]Loading usage limits...", spinner="dots", spinner_style=ORANGE):
                limits = capture_limits()
        else:
            limits = capture_limits()

        # Show Usage Limits if available
        if limits and "error" not in limits:
            # Remove timezone info from reset dates
            session_reset = limits['session_reset'].split(' (')[0] if '(' in limits['session_reset'] else limits['session_reset']
            week_reset = limits['week_reset'].split(' (')[0] if '(' in limits['week_reset'] else limits['week_reset']
            opus_reset = limits['opus_reset'].split(' (')[0] if '(' in limits['opus_reset'] else limits['opus_reset']

            # Calculate costs for each limit period
            session_cost = _calculate_session_cost(records)  # Last 5 hours, all models
            weekly_sonnet_cost = _calculate_weekly_sonnet_cost(records)  # Weekly, sonnet only
            weekly_opus_cost = _calculate_weekly_opus_cost(records)  # Weekly, opus only

            # Create table structure with 3 rows per limit
            limits_table = Table(show_header=False, box=None, padding=(0, 2))
            limits_table.add_column("Content", justify="left")

            # Session limit (3 rows)
            limits_table.add_row("Current session")
            session_bar = _create_bar(limits["session_pct"], 100, width=50, color="red")
            bar_text = Text()
            bar_text.append(session_bar)
            bar_text.append(f"  {limits['session_pct']}% used", style="bold white")
            limits_table.add_row(bar_text)
            limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
            limits_table.add_row("")  # Blank line

            # Week limit (3 rows)
            limits_table.add_row("Current week (all models)")
            week_bar = _create_bar(limits["week_pct"], 100, width=50, color="red")
            bar_text = Text()
            bar_text.append(week_bar)
            bar_text.append(f"  {limits['week_pct']}% used", style="bold white")
            limits_table.add_row(bar_text)
            limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
            limits_table.add_row("")  # Blank line

            # Opus limit (3 rows)
            limits_table.add_row("Current week (Opus)")
            opus_bar = _create_bar(limits["opus_pct"], 100, width=50, color="red")
            bar_text = Text()
            bar_text.append(opus_bar)
            bar_text.append(f"  {limits['opus_pct']}% used", style="bold white")
            limits_table.add_row(bar_text)
            limits_table.add_row(f"Resets {opus_reset} ({format_cost(weekly_opus_cost)})", style=DIM)

            # Wrap in outer "Usage Limits" panel (expand to fit terminal width)
            limits_outer_panel = Panel(
                limits_table,
                title="[bold]Usage Limits",
                border_style="white",
                expand=True,
            )

            console.print(limits_outer_panel, end="")
            console.print()

        # Show footer
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True)
        console.print(footer)
        return

    # Create KPI cards with limits (shows spinner if loading limits)
    kpi_section = _create_kpi_section(stats.overall_totals, records, view_mode=view_mode, skip_limits=skip_limits, console=console, limits_from_db=limits_from_db)

    # Create footer with export info, date range, and view mode
    footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True)

    # Always render Summary (and Usage Limits in weekly mode)
    console.print(kpi_section, end="")
    console.print()  # Blank line between sections

    # Create breakdowns for each view mode
    sections_to_render = []

    # Model breakdown is always important
    model_breakdown = _create_model_breakdown(records)
    sections_to_render.append(("model", model_breakdown))

    # Add mode-specific breakdown
    if view_mode == "weekly":
        daily_breakdown_weekly = _create_daily_breakdown_weekly(records)
        sections_to_render.append(("daily_weekly", daily_breakdown_weekly))
        hourly_breakdown = _create_hourly_breakdown(records)
        sections_to_render.append(("hourly", hourly_breakdown))
    elif view_mode == "monthly":
        project_breakdown = _create_project_breakdown(records)
        sections_to_render.append(("project", project_breakdown))
        daily_breakdown = _create_daily_breakdown(records)
        sections_to_render.append(("daily", daily_breakdown))
    elif view_mode == "yearly":
        project_breakdown = _create_project_breakdown(records)
        sections_to_render.append(("project", project_breakdown))
        monthly_breakdown = _create_monthly_breakdown(records)
        sections_to_render.append(("monthly", monthly_breakdown))

    # Render sections
    for section_type, section in sections_to_render:
        console.print(section, end="")
        console.print()  # Blank line between sections

    # Always render footer
    console.print(footer)


def _calculate_session_cost(records: list[UsageRecord]) -> float:
    """
    Calculate cost for session limit period (last 5 hours, all models).

    Args:
        records: List of usage records

    Returns:
        Total cost for session period
    """
    from src.models.pricing import calculate_cost
    from datetime import timedelta, timezone

    # Use timezone-aware datetime to match record.timestamp
    now = datetime.now(timezone.utc)
    five_hours_ago = now - timedelta(hours=5)

    session_cost = 0.0
    for record in records:
        if record.timestamp >= five_hours_ago and record.model and record.token_usage and record.model != "<synthetic>":
            cost = calculate_cost(
                record.token_usage.input_tokens,
                record.token_usage.output_tokens,
                record.model,
                record.token_usage.cache_creation_tokens,
                record.token_usage.cache_read_tokens,
            )
            session_cost += cost

    return session_cost


def _calculate_weekly_sonnet_cost(records: list[UsageRecord]) -> float:
    """
    Calculate cost for weekly sonnet usage (last 7 days, sonnet models only).

    Args:
        records: List of usage records

    Returns:
        Total cost for weekly sonnet usage
    """
    from src.models.pricing import calculate_cost
    from datetime import timedelta, timezone

    # Use timezone-aware datetime to match record.timestamp
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    weekly_cost = 0.0
    for record in records:
        if record.timestamp >= seven_days_ago and record.model and record.token_usage and record.model != "<synthetic>":
            # Check if it's a sonnet model
            if "sonnet" in record.model.lower():
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                weekly_cost += cost

    return weekly_cost


def _calculate_weekly_opus_cost(records: list[UsageRecord]) -> float:
    """
    Calculate cost for weekly opus usage (last 7 days, opus models only).

    Args:
        records: List of usage records

    Returns:
        Total cost for weekly opus usage
    """
    from src.models.pricing import calculate_cost
    from datetime import timedelta, timezone

    # Use timezone-aware datetime to match record.timestamp
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    weekly_cost = 0.0
    for record in records:
        if record.timestamp >= seven_days_ago and record.model and record.token_usage and record.model != "<synthetic>":
            # Check if it's an opus model
            if "opus" in record.model.lower():
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                weekly_cost += cost

    return weekly_cost


def _create_kpi_section(overall, records: list[UsageRecord], view_mode: str = "monthly", skip_limits: bool = False, console: Console = None, limits_from_db: dict | None = None) -> Group:
    """
    Create KPI cards with individual limit boxes beneath each (only for weekly mode).

    Args:
        overall: Overall statistics
        records: List of usage records (for cost calculation)
        view_mode: Current view mode - "monthly", "weekly", or "yearly"
        skip_limits: If True, skip fetching current limits (faster)
        console: Console instance for showing spinner
        limits_from_db: Pre-fetched limits from database (avoids live fetch)

    Returns:
        Group containing KPI cards and limit boxes (if weekly mode)
    """
    from src.models.pricing import calculate_cost, format_cost

    # Calculate total cost and token breakdown from records
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation = 0
    total_cache_read = 0

    for record in records:
        if record.model and record.token_usage and record.model != "<synthetic>":
            total_input_tokens += record.token_usage.input_tokens
            total_output_tokens += record.token_usage.output_tokens
            total_cache_creation += record.token_usage.cache_creation_tokens
            total_cache_read += record.token_usage.cache_read_tokens

            cost = calculate_cost(
                record.token_usage.input_tokens,
                record.token_usage.output_tokens,
                record.model,
                record.token_usage.cache_creation_tokens,
                record.token_usage.cache_read_tokens,
            )
            total_cost += cost

    # Create KPI cards in 2 rows of 3 cards each
    kpi_grid = Table.grid(padding=(0, 2), expand=False)
    kpi_grid.add_column(justify="center")
    kpi_grid.add_column(justify="center")
    kpi_grid.add_column(justify="center")

    # Row 1: Cost, Messages, Input Tokens
    cost_card = Panel(
        Text(_format_number(total_cost) if isinstance(total_cost, int) else format_cost(total_cost), style="bold green"),
        title="Cost",
        border_style="white",
        width=36,
    )

    messages_card = Panel(
        Text(_format_number(overall.total_prompts), style="bold white"),
        title="Messages",
        border_style="white",
        width=36,
    )

    input_tokens_card = Panel(
        Text(_format_number(total_input_tokens), style="bold cyan"),
        title="Input Tokens",
        border_style="white",
        width=36,
    )

    kpi_grid.add_row(cost_card, messages_card, input_tokens_card)

    # Row 2: Output Tokens, Cache Creation, Cache Read
    output_tokens_card = Panel(
        Text(_format_number(total_output_tokens), style="bold cyan"),
        title="Output Tokens",
        border_style="white",
        width=36,
    )

    cache_creation_card = Panel(
        Text(_format_number(total_cache_creation), style="bold magenta"),
        title="Cache Write",
        border_style="white",
        width=36,
    )

    cache_read_card = Panel(
        Text(_format_number(total_cache_read), style="bold magenta"),
        title="Cache Read",
        border_style="white",
        width=36,
    )

    kpi_grid.add_row(output_tokens_card, cache_creation_card, cache_read_card)

    # For weekly mode, add limit boxes below KPI cards
    if view_mode == "weekly":
        # Use limits from DB if provided, otherwise fetch live (unless skipped)
        limits = limits_from_db
        if limits is None and not skip_limits:
            from src.commands.limits import capture_limits
            if console:
                with console.status(f"[bold {ORANGE}]Loading usage limits...", spinner="dots", spinner_style=ORANGE):
                    limits = capture_limits()
            else:
                limits = capture_limits()

        # Create individual limit boxes if available
        if limits and "error" not in limits:
            # Remove timezone info from reset dates
            session_reset = limits['session_reset'].split(' (')[0] if '(' in limits['session_reset'] else limits['session_reset']
            week_reset = limits['week_reset'].split(' (')[0] if '(' in limits['week_reset'] else limits['week_reset']
            opus_reset = limits['opus_reset'].split(' (')[0] if '(' in limits['opus_reset'] else limits['opus_reset']

            # Calculate costs for each limit period
            from datetime import timedelta
            session_cost = _calculate_session_cost(records)  # Last 5 hours, all models
            weekly_sonnet_cost = _calculate_weekly_sonnet_cost(records)  # Weekly, sonnet only
            weekly_opus_cost = _calculate_weekly_opus_cost(records)  # Weekly, opus only

            # Create table structure with 3 rows per limit
            limits_table = Table(show_header=False, box=None, padding=(0, 2))
            limits_table.add_column("Content", justify="left")

            # Session limit (3 rows)
            limits_table.add_row("Current session")
            session_bar = _create_bar(limits["session_pct"], 100, width=50, color="red")
            bar_text = Text()
            bar_text.append(session_bar)
            bar_text.append(f"  {limits['session_pct']}% used", style="bold white")
            limits_table.add_row(bar_text)
            limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
            limits_table.add_row("")  # Blank line

            # Week limit (3 rows)
            limits_table.add_row("Current week (all models)")
            week_bar = _create_bar(limits["week_pct"], 100, width=50, color="red")
            bar_text = Text()
            bar_text.append(week_bar)
            bar_text.append(f"  {limits['week_pct']}% used", style="bold white")
            limits_table.add_row(bar_text)
            limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
            limits_table.add_row("")  # Blank line

            # Opus limit (3 rows)
            limits_table.add_row("Current week (Opus)")
            opus_bar = _create_bar(limits["opus_pct"], 100, width=50, color="red")
            bar_text = Text()
            bar_text.append(opus_bar)
            bar_text.append(f"  {limits['opus_pct']}% used", style="bold white")
            limits_table.add_row(bar_text)
            limits_table.add_row(f"Resets {opus_reset} ({format_cost(weekly_opus_cost)})", style=DIM)

            # Wrap in outer "Usage Limits" panel (expand to fit terminal width)
            limits_outer_panel = Panel(
                limits_table,
                title="[bold]Usage Limits",
                border_style="white",
                expand=True,
            )

            # Add single line spacing between Summary and Usage Limits
            spacing = Text("")
            return Group(kpi_grid, spacing, limits_outer_panel)

    # Return only KPI cards for monthly/yearly modes
    return Group(kpi_grid)


def _create_kpi_cards(overall) -> Table:
    """
    Create 3 KPI cards showing key metrics.

    Args:
        overall: Overall statistics

    Returns:
        Table grid with KPI cards
    """
    grid = Table.grid(padding=(0, 2), expand=False)
    grid.add_column(justify="center")
    grid.add_column(justify="center")
    grid.add_column(justify="center")

    # Total Tokens card
    tokens_card = Panel(
        Text.assemble(
            (_format_number(overall.total_tokens), f"bold {ORANGE}"),
            "\n",
            ("Total Tokens", DIM),
        ),
        border_style="white",
        width=28,
    )

    # Total Prompts card
    prompts_card = Panel(
        Text.assemble(
            (_format_number(overall.total_prompts), f"bold {ORANGE}"),
            "\n",
            ("Prompts Sent", DIM),
        ),
        border_style="white",
        width=28,
    )

    # Total Sessions card
    sessions_card = Panel(
        Text.assemble(
            (_format_number(overall.total_sessions), f"bold {ORANGE}"),
            "\n",
            ("Active Sessions", DIM),
        ),
        border_style="white",
        width=28,
    )

    grid.add_row(tokens_card, prompts_card, sessions_card)
    return grid


def _create_limits_bars() -> Panel | None:
    """
    Create progress bars showing current usage limits.

    Returns:
        Panel with limit progress bars, or None if no limits data
    """
    # Try to capture current limits
    from src.commands.limits import capture_limits

    limits = capture_limits()
    if not limits or "error" in limits:
        return None

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="white", justify="left")
    table.add_column("Bar", justify="left")
    table.add_column("Percent", style=ORANGE, justify="right")
    table.add_column("Reset", style=CYAN, justify="left")

    # Session limit
    session_bar = _create_bar(limits["session_pct"], 100, width=30)
    table.add_row(
        "[bold]Session",
        session_bar,
        f"{limits['session_pct']}%",
        f"resets {limits['session_reset']}",
    )

    # Week limit
    week_bar = _create_bar(limits["week_pct"], 100, width=30)
    table.add_row(
        "[bold]Week",
        week_bar,
        f"{limits['week_pct']}%",
        f"resets {limits['week_reset']}",
    )

    # Opus limit
    opus_bar = _create_bar(limits["opus_pct"], 100, width=30)
    table.add_row(
        "[bold]Opus",
        opus_bar,
        f"{limits['opus_pct']}%",
        f"resets {limits['opus_reset']}",
    )

    return Panel(
        table,
        title="[bold]Usage Limits",
        border_style="white",
    )


def _create_model_breakdown(records: list[UsageRecord]) -> Panel:
    """
    Create table showing token usage and cost per model.

    Args:
        records: List of usage records

    Returns:
        Panel with model breakdown table including costs
    """
    from src.models.pricing import calculate_cost, format_cost

    # Aggregate tokens and costs by model
    model_data: dict[str, dict] = defaultdict(lambda: {
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0
    })

    for record in records:
        if record.model and record.token_usage and record.model != "<synthetic>":
            model_data[record.model]["total_tokens"] += record.token_usage.total_tokens
            model_data[record.model]["input_tokens"] += record.token_usage.input_tokens
            model_data[record.model]["output_tokens"] += record.token_usage.output_tokens

            # Calculate cost for this record (including cache tokens)
            cost = calculate_cost(
                record.token_usage.input_tokens,
                record.token_usage.output_tokens,
                record.model,
                record.token_usage.cache_creation_tokens,
                record.token_usage.cache_read_tokens,
            )
            model_data[record.model]["cost"] += cost

    if not model_data:
        return Panel(
            Text("No model data available", style=DIM),
            title="[bold]Tokens by Model",
            border_style="white",
        )

    # Calculate totals
    total_tokens = sum(data["total_tokens"] for data in model_data.values())
    total_cost = sum(data["cost"] for data in model_data.values())
    max_tokens = max(data["total_tokens"] for data in model_data.values())

    # Sort by usage
    sorted_models = sorted(model_data.items(), key=lambda x: x[1]["total_tokens"], reverse=True)

    # Create table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Model", style="white", justify="left", width=25)
    table.add_column("Bar", justify="left")
    table.add_column("Tokens", style=ORANGE, justify="right")
    table.add_column("Percentage", style=CYAN, justify="right")
    table.add_column("Cost", style="green", justify="right", width=10)

    for model, data in sorted_models:
        # Shorten model name
        display_name = model.split("/")[-1] if "/" in model else model
        if "claude" in display_name.lower():
            display_name = display_name.replace("claude-", "")

        tokens = data["total_tokens"]
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Create bar
        bar = _create_bar(tokens, max_tokens, width=20)

        table.add_row(
            display_name,
            bar,
            _format_number(tokens),
            f"{percentage:.1f}%",
            format_cost(data["cost"]),
        )

    # Add separator line before total
    table.add_row("", "", "", "", "")

    # Add total row
    table.add_row(
        "[bold]Total",
        Text(""),
        f"[bold]{_format_number(total_tokens)}",
        "[bold]100.0%",
        f"[bold green]{format_cost(total_cost)}",
    )

    return Panel(
        table,
        title="[bold]Tokens by Model",
        border_style="white",
        expand=True,
    )


def _create_project_breakdown(records: list[UsageRecord]) -> Panel:
    """
    Create table showing token usage and cost per project.

    Args:
        records: List of usage records

    Returns:
        Panel with project breakdown table
    """
    from src.models.pricing import calculate_cost, format_cost

    # Aggregate tokens and costs by folder
    folder_data: dict[str, dict] = defaultdict(lambda: {
        "total_tokens": 0,
        "cost": 0.0
    })

    for record in records:
        if record.token_usage:
            folder_data[record.folder]["total_tokens"] += record.token_usage.total_tokens

            if record.model and record.model != "<synthetic>":
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                folder_data[record.folder]["cost"] += cost

    if not folder_data:
        return Panel(
            Text("No project data available", style=DIM),
            title="[bold]Tokens by Project",
            border_style="white",
        )

    # Calculate total
    total_tokens = sum(data["total_tokens"] for data in folder_data.values())

    # Sort by usage
    sorted_folders = sorted(folder_data.items(), key=lambda x: x[1]["total_tokens"], reverse=True)

    # Limit to top 10 projects
    sorted_folders = sorted_folders[:10]
    max_tokens = max(data["total_tokens"] for _, data in sorted_folders)

    # Create table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Project", style="white", justify="left", overflow="crop")
    table.add_column("Bar", justify="left", overflow="crop")
    table.add_column("Tokens", style=ORANGE, justify="right")
    table.add_column("Percentage", style=CYAN, justify="right")
    table.add_column("Cost", style="green", justify="right", width=10)

    for folder, data in sorted_folders:
        # Show only last 2 parts of path (without .../ prefix)
        parts = folder.split("/")
        if len(parts) > 2:
            display_name = "/".join(parts[-2:])
        else:
            display_name = folder

        # Manually truncate to 35 chars without ellipses
        if len(display_name) > 35:
            display_name = display_name[:35]

        tokens = data["total_tokens"]
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Create bar
        bar = _create_bar(tokens, max_tokens, width=20)

        table.add_row(
            display_name,
            bar,
            _format_number(tokens),
            f"{percentage:.1f}%",
            format_cost(data["cost"]),
        )

    return Panel(
        table,
        title="[bold]Tokens by Project",
        border_style="white",
        expand=True,
    )


def _create_daily_breakdown(records: list[UsageRecord]) -> Panel:
    """
    Create table showing daily usage breakdown for monthly mode.
    Shows all dates in the range, including days with no usage.

    Args:
        records: List of usage records

    Returns:
        Panel with daily breakdown table
    """
    from src.models.pricing import calculate_cost, format_cost
    from datetime import timedelta

    # Aggregate by date (format: "YYYY-MM-DD")
    daily_data: dict[str, dict] = defaultdict(lambda: {
        "cost": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation": 0,
        "cache_read": 0,
        "messages": 0
    })

    # Track min and max dates
    min_date = None
    max_date = None

    for record in records:
        if record.token_usage:
            # Extract date from timestamp
            date = record.timestamp.strftime("%Y-%m-%d")
            record_date = record.timestamp.date()

            # Update min/max dates
            if min_date is None or record_date < min_date:
                min_date = record_date
            if max_date is None or record_date > max_date:
                max_date = record_date

            daily_data[date]["input_tokens"] += record.token_usage.input_tokens
            daily_data[date]["output_tokens"] += record.token_usage.output_tokens
            daily_data[date]["cache_creation"] += record.token_usage.cache_creation_tokens
            daily_data[date]["cache_read"] += record.token_usage.cache_read_tokens
            daily_data[date]["messages"] += 1

            if record.model and record.model != "<synthetic>":
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                daily_data[date]["cost"] += cost

    if not daily_data or min_date is None or max_date is None:
        return Panel(
            Text("No daily data available", style=DIM),
            title="[bold]Daily Usage",
            border_style="white",
        )

    # Generate all dates in range
    all_dates = []
    current_date = min_date
    while current_date <= max_date:
        date_str = current_date.strftime("%Y-%m-%d")
        # Add date with actual data or zeros
        if date_str in daily_data:
            all_dates.append((date_str, daily_data[date_str]))
        else:
            # Add date with zero values
            all_dates.append((date_str, {
                "cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation": 0,
                "cache_read": 0,
                "messages": 0
            }))
        current_date += timedelta(days=1)

    # Sort by date in descending order (most recent first)
    sorted_dates = sorted(all_dates, reverse=True)

    # Create table with English column names
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Date", style="purple", justify="left", width=12)
    table.add_column("Cost", style="green", justify="right", width=10)
    table.add_column("Input", style=CYAN, justify="right", width=12)
    table.add_column("Output", style=CYAN, justify="right", width=12)
    table.add_column("Cache Write", style="magenta", justify="right", width=14)
    table.add_column("Cache Read", style="magenta", justify="right", width=14)
    table.add_column("Messages", style="white", justify="right", width=10)

    for date, data in sorted_dates:
        table.add_row(
            date,
            format_cost(data["cost"]),
            _format_number(data["input_tokens"]),
            _format_number(data["output_tokens"]),
            _format_number(data["cache_creation"]),
            _format_number(data["cache_read"]),
            str(data["messages"]),
        )

    return Panel(
        table,
        title="[bold]Daily Usage",
        border_style="white",
        expand=True,
    )


def _create_daily_breakdown_weekly(records: list[UsageRecord]) -> Panel:
    """
    Create graph-style daily usage breakdown for weekly mode.
    Shows cyan bar graphs with token amounts, percentages, and costs.

    Args:
        records: List of usage records

    Returns:
        Panel with daily breakdown in graph format
    """
    from src.models.pricing import calculate_cost, format_cost

    # Aggregate by date (format: "YYYY-MM-DD")
    daily_data: dict[str, dict] = defaultdict(lambda: {
        "total_tokens": 0,
        "cost": 0.0
    })

    for record in records:
        if record.token_usage:
            date = record.timestamp.strftime("%Y-%m-%d")
            daily_data[date]["total_tokens"] += record.token_usage.total_tokens

            if record.model and record.model != "<synthetic>":
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                daily_data[date]["cost"] += cost

    if not daily_data:
        return Panel(
            Text("No daily data available", style=DIM),
            title="[bold]Daily Usage",
            border_style="white",
        )

    # Calculate totals and max for scaling
    total_tokens = sum(data["total_tokens"] for data in daily_data.values())
    max_tokens = max(data["total_tokens"] for data in daily_data.values())

    # Sort by date in descending order (most recent first)
    sorted_dates = sorted(daily_data.items(), reverse=True)

    # Create table with bars
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Date", style="white", justify="left", width=17)
    table.add_column("Bar", justify="left")
    table.add_column("Tokens", style=ORANGE, justify="right")
    table.add_column("Percentage", style=CYAN, justify="right")
    table.add_column("Cost", style="green", justify="right", width=10)

    for date, data in sorted_dates:
        tokens = data["total_tokens"]
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Parse date and get day of week
        from datetime import datetime
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        day_name = date_obj.strftime("%a")  # Mon, Tue, Wed, etc.
        date_with_day = f"{date} ({day_name})"

        # Create bar (same style as Tokens by Model)
        bar = _create_bar(tokens, max_tokens, width=20)

        table.add_row(
            date_with_day,
            bar,
            _format_number(tokens),
            f"{percentage:.1f}%",
            format_cost(data["cost"]),
        )

    return Panel(
        table,
        title="[bold]Daily Usage",
        border_style="white",
        expand=True,
    )


def _create_hourly_breakdown(records: list[UsageRecord]) -> Panel:
    """
    Create table showing hourly usage breakdown for weekly mode.

    Args:
        records: List of usage records

    Returns:
        Panel with hourly breakdown table
    """
    from src.models.pricing import calculate_cost, format_cost

    # Aggregate by hour (format: "HH:00")
    hourly_data: dict[str, dict] = defaultdict(lambda: {
        "cost": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation": 0,
        "cache_read": 0,
        "messages": 0
    })

    for record in records:
        if record.token_usage:
            # Extract hour from timestamp
            hour = record.timestamp.strftime("%H:00")

            hourly_data[hour]["input_tokens"] += record.token_usage.input_tokens
            hourly_data[hour]["output_tokens"] += record.token_usage.output_tokens
            hourly_data[hour]["cache_creation"] += record.token_usage.cache_creation_tokens
            hourly_data[hour]["cache_read"] += record.token_usage.cache_read_tokens
            hourly_data[hour]["messages"] += 1

            if record.model and record.model != "<synthetic>":
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                hourly_data[hour]["cost"] += cost

    if not hourly_data:
        return Panel(
            Text("No hourly data available", style=DIM),
            title="[bold]Hourly Usage",
            border_style="white",
        )

    # Sort by hour in descending order (most recent first)
    sorted_hours = sorted(hourly_data.items(), reverse=True)

    # Create table with English column names
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Time", style="purple", justify="left", width=8)
    table.add_column("Cost", style="green", justify="right", width=10)
    table.add_column("Input", style=CYAN, justify="right", width=12)
    table.add_column("Output", style=CYAN, justify="right", width=12)
    table.add_column("Cache Write", style="magenta", justify="right", width=14)
    table.add_column("Cache Read", style="magenta", justify="right", width=14)
    table.add_column("Messages", style="white", justify="right", width=10)

    for hour, data in sorted_hours:
        table.add_row(
            hour,
            format_cost(data["cost"]),
            _format_number(data["input_tokens"]),
            _format_number(data["output_tokens"]),
            _format_number(data["cache_creation"]),
            _format_number(data["cache_read"]),
            str(data["messages"]),
        )

    return Panel(
        table,
        title="[bold]Hourly Usage",
        border_style="white",
        expand=True,
    )


def _create_monthly_breakdown(records: list[UsageRecord]) -> Panel:
    """
    Create table showing monthly usage breakdown for yearly mode.

    Args:
        records: List of usage records

    Returns:
        Panel with monthly breakdown table
    """
    from src.models.pricing import calculate_cost, format_cost

    # Aggregate by month (format: "YYYY-MM")
    monthly_data: dict[str, dict] = defaultdict(lambda: {
        "cost": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation": 0,
        "cache_read": 0,
        "messages": 0
    })

    for record in records:
        if record.token_usage:
            # Extract year-month from timestamp
            month = record.timestamp.strftime("%Y-%m")

            monthly_data[month]["input_tokens"] += record.token_usage.input_tokens
            monthly_data[month]["output_tokens"] += record.token_usage.output_tokens
            monthly_data[month]["cache_creation"] += record.token_usage.cache_creation_tokens
            monthly_data[month]["cache_read"] += record.token_usage.cache_read_tokens
            monthly_data[month]["messages"] += 1

            if record.model and record.model != "<synthetic>":
                cost = calculate_cost(
                    record.token_usage.input_tokens,
                    record.token_usage.output_tokens,
                    record.model,
                    record.token_usage.cache_creation_tokens,
                    record.token_usage.cache_read_tokens,
                )
                monthly_data[month]["cost"] += cost

    if not monthly_data:
        return Panel(
            Text("No monthly data available", style=DIM),
            title="[bold]Monthly Usage",
            border_style="white",
        )

    # Sort by month in descending order (most recent first)
    sorted_months = sorted(monthly_data.items(), reverse=True)

    # Create table with English column names
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Month", style="purple", justify="left", width=10)
    table.add_column("Cost", style="green", justify="right", width=10)
    table.add_column("Input", style=CYAN, justify="right", width=12)
    table.add_column("Output", style=CYAN, justify="right", width=12)
    table.add_column("Cache Write", style="magenta", justify="right", width=14)
    table.add_column("Cache Read", style="magenta", justify="right", width=14)
    table.add_column("Messages", style="white", justify="right", width=10)

    for month, data in sorted_months:
        table.add_row(
            month,
            format_cost(data["cost"]),
            _format_number(data["input_tokens"]),
            _format_number(data["output_tokens"]),
            _format_number(data["cache_creation"]),
            _format_number(data["cache_read"]),
            str(data["messages"]),
        )

    return Panel(
        table,
        title="[bold]Monthly Usage",
        border_style="white",
        expand=True,
    )


def _create_footer(date_range: str = None, fast_mode: bool = False, view_mode: str = "monthly", in_live_mode: bool = False) -> Text:
    """
    Create footer with export command info, date range, and view mode.

    Args:
        date_range: Optional date range string to display
        fast_mode: If True, show warning about fast mode
        view_mode: Current view mode - "monthly", "weekly", or "yearly"
        in_live_mode: If True, show keyboard shortcuts for mode switching

    Returns:
        Text with export instructions, date range, and view mode info
    """
    footer = Text()

    # Add fast mode warning if enabled
    if fast_mode:
        from src.storage.snapshot_db import get_database_stats
        db_stats = get_database_stats()
        if db_stats.get("newest_timestamp"):
            # Format ISO timestamp to be more readable
            timestamp_str = db_stats["newest_timestamp"]
            try:
                dt = datetime.fromisoformat(timestamp_str)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                footer.append("⚠ Fast mode: Reading from last update (", style="bold red")
                footer.append(f"{formatted_time}", style="bold red")
                footer.append(")\n\n", style="bold red")
            except (ValueError, AttributeError):
                footer.append(f"⚠ Fast mode: Reading from last update ({timestamp_str})\n\n", style="bold red")
        else:
            footer.append("⚠ Fast mode: Reading from database (no timestamp available)\n\n", style="bold red")

    # Add current view mode if in live mode
    if in_live_mode:
        footer.append("View: ", style=DIM)

        # Show current mode highlighted - simplified format
        # Usage
        if view_mode == "usage":
            footer.append("[u]sage ", style=f"bold {ORANGE}")
        else:
            footer.append("[u]sage ", style=DIM)

        # Weekly
        if view_mode == "weekly":
            footer.append("[w]eekly ", style=f"bold {ORANGE}")
        else:
            footer.append("[w]eekly ", style=DIM)

        # Monthly
        if view_mode == "monthly":
            footer.append("[m]onthly ", style=f"bold {ORANGE}")
        else:
            footer.append("[m]onthly ", style=DIM)

        # Yearly
        if view_mode == "yearly":
            footer.append("[y]early ", style=f"bold {ORANGE}")
        else:
            footer.append("[y]early ", style=DIM)

        # Heatmap
        if view_mode == "heatmap":
            footer.append("[h]eatmap ", style=f"bold {ORANGE}")
        else:
            footer.append("[h]eatmap ", style=DIM)

        # Devices
        if view_mode == "devices":
            footer.append("[d]evices ", style=f"bold {ORANGE}")
        else:
            footer.append("[d]evices ", style=DIM)

        # Quit
        footer.append("[q]uit", style=DIM)

        # Add date range if provided (on same line)
        if date_range:
            footer.append("  ", style=DIM)
            footer.append(f"{date_range}", style="bold white")

        # Add newline at end
        footer.append("\n")

        # Add arrow keys hint for monthly/yearly modes (second line)
        if view_mode in ["monthly", "yearly"]:
            footer.append("Use ", style=DIM)
            footer.append("←", style=f"bold {ORANGE}")
            footer.append(" ", style=DIM)
            footer.append("→", style=f"bold {ORANGE}")
            period_label = "month" if view_mode == "monthly" else "year"
            footer.append(f" to navigate {period_label}s", style=DIM)
            footer.append("\n")

    else:
        # No live mode, just date range if provided
        if date_range:
            footer.append("Data range: ", style=DIM)
            footer.append(f"{date_range}", style="bold white")
            footer.append("\n", style=DIM)

    return footer


#endregion
