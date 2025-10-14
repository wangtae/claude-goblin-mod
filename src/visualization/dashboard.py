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
        return Text("░" * width, style=DIM)

    filled = int((value / max_value) * width)
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * (width - filled), style=DIM)
    return bar


def render_dashboard(stats: AggregatedStats, records: list[UsageRecord], console: Console, skip_limits: bool = False, clear_screen: bool = True, date_range: str = None, limits_from_db: dict | None = None, fast_mode: bool = False, view_mode: str = "monthly") -> None:
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
        view_mode: Display mode - "monthly", "weekly", or "yearly" (default: "monthly")
    """
    # Optionally clear screen
    if clear_screen:
        console.clear()

    # For yearly mode, show heatmap instead of dashboard
    if view_mode == "yearly":
        from src.commands.heatmap import _display_heatmap, _load_limits_data
        limits_data = _load_limits_data()
        _display_heatmap(console, stats, limits_data, year=None)
        # Show footer with keyboard shortcuts
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True)
        console.print()
        console.print(footer)
        return

    # Create KPI cards with limits (shows spinner if loading limits)
    kpi_section = _create_kpi_section(stats.overall_totals, records, view_mode=view_mode, skip_limits=skip_limits, console=console, limits_from_db=limits_from_db)

    # Create breakdowns
    model_breakdown = _create_model_breakdown(records)

    # Create footer with export info, date range, and view mode
    footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True)

    # Render all components
    console.print(kpi_section, end="")
    console.print()  # Blank line between sections
    console.print(model_breakdown, end="")

    # Show hourly usage table in weekly mode
    if view_mode == "weekly":
        hourly_breakdown = _create_hourly_breakdown(records)
        console.print()  # Blank line between sections
        console.print(hourly_breakdown, end="")
    # Show project breakdown in monthly mode
    elif view_mode == "monthly":
        project_breakdown = _create_project_breakdown(records)
        console.print()  # Blank line between sections
        console.print(project_breakdown, end="")

    console.print()  # Blank line before footer
    console.print(footer)


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

    # Create KPI cards in 2 rows
    # Row 1: cost, prompts, sessions
    # Row 2: input, output, cache write, cache read tokens
    kpi_grid = Table.grid(padding=(0, 2), expand=False)
    kpi_grid.add_column(justify="center")
    kpi_grid.add_column(justify="center")
    kpi_grid.add_column(justify="center")
    kpi_grid.add_column(justify="center")

    # Row 1 - Main metrics
    cost_card = Panel(
        Text(format_cost(total_cost), style="bold green"),
        title="비용",
        border_style="white",
        width=24,
    )

    prompts_card = Panel(
        Text(_format_number(overall.total_prompts), style="bold white"),
        title="메시지 수",
        border_style="white",
        width=24,
    )

    sessions_card = Panel(
        Text(_format_number(overall.total_sessions), style="bold white"),
        title="세션 수",
        border_style="white",
        width=24,
    )

    kpi_grid.add_row(cost_card, prompts_card, sessions_card, Text(""))

    # Row 2 - Token breakdown
    input_card = Panel(
        Text(_format_number(total_input_tokens), style="bold cyan"),
        title="입력 토큰",
        border_style="white",
        width=24,
    )

    output_card = Panel(
        Text(_format_number(total_output_tokens), style="bold cyan"),
        title="출력 토큰",
        border_style="white",
        width=24,
    )

    cache_write_card = Panel(
        Text(_format_number(total_cache_creation), style="bold magenta"),
        title="캐시 생성",
        border_style="white",
        width=24,
    )

    cache_read_card = Panel(
        Text(_format_number(total_cache_read), style="bold magenta"),
        title="캐시 읽기",
        border_style="white",
        width=24,
    )

    kpi_grid.add_row(input_card, output_card, cache_write_card, cache_read_card)

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
            limit_grid = Table.grid(padding=(0, 2), expand=False)
            limit_grid.add_column(justify="center")
            limit_grid.add_column(justify="center")
            limit_grid.add_column(justify="center")

            # Remove timezone info from reset dates
            session_reset = limits['session_reset'].split(' (')[0] if '(' in limits['session_reset'] else limits['session_reset']
            week_reset = limits['week_reset'].split(' (')[0] if '(' in limits['week_reset'] else limits['week_reset']
            opus_reset = limits['opus_reset'].split(' (')[0] if '(' in limits['opus_reset'] else limits['opus_reset']

            # Session limit box (with cost)
            session_bar = _create_bar(limits["session_pct"], 100, width=16, color="red")
            session_content = Text()
            session_content.append(f"{limits['session_pct']}% ", style="bold red")
            session_content.append(session_bar)
            session_content.append(f"\nResets: {session_reset}", style="white")
            session_content.append(f"\n{format_cost(total_cost)}", style="bold green")
            session_box = Panel(
                session_content,
                title="[red]Session Limit",
                border_style="white",
                width=28,
            )

            # Week limit box (with cost)
            week_bar = _create_bar(limits["week_pct"], 100, width=16, color="red")
            week_content = Text()
            week_content.append(f"{limits['week_pct']}% ", style="bold red")
            week_content.append(week_bar)
            week_content.append(f"\nResets: {week_reset}", style="white")
            week_content.append(f"\n{format_cost(total_cost)}", style="bold green")
            week_box = Panel(
                week_content,
                title="[red]Weekly Limit",
                border_style="white",
                width=28,
            )

            # Opus limit box (with cost)
            opus_bar = _create_bar(limits["opus_pct"], 100, width=16, color="red")
            opus_content = Text()
            opus_content.append(f"{limits['opus_pct']}% ", style="bold red")
            opus_content.append(opus_bar)
            opus_content.append(f"\nResets: {opus_reset}", style="white")
            opus_content.append(f"\n{format_cost(total_cost)}", style="bold green")
            opus_box = Panel(
                opus_content,
                title="[red]Opus Limit",
                border_style="white",
                width=28,
            )

            limit_grid.add_row(session_box, week_box, opus_box)

            # Add spacing between KPI cards and limits with a simple newline
            spacing = Text("\n")
            return Group(kpi_grid, spacing, limit_grid)

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
    )


def _create_project_breakdown(records: list[UsageRecord]) -> Panel:
    """
    Create table showing token usage per project.

    Args:
        records: List of usage records

    Returns:
        Panel with project breakdown table
    """
    # Aggregate tokens by folder
    folder_tokens: dict[str, int] = defaultdict(int)

    for record in records:
        if record.token_usage:
            folder_tokens[record.folder] += record.token_usage.total_tokens

    if not folder_tokens:
        return Panel(
            Text("No project data available", style=DIM),
            title="[bold]Tokens by Project",
            border_style="white",
        )

    # Calculate total and max
    total_tokens = sum(folder_tokens.values())

    # Sort by usage
    sorted_folders = sorted(folder_tokens.items(), key=lambda x: x[1], reverse=True)

    # Limit to top 10 projects
    sorted_folders = sorted_folders[:10]
    max_tokens = max(tokens for _, tokens in sorted_folders)

    # Create table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Project", style="white", justify="left", overflow="crop")
    table.add_column("Bar", justify="left", overflow="crop")
    table.add_column("Tokens", style=ORANGE, justify="right")
    table.add_column("Percentage", style=CYAN, justify="right")

    for folder, tokens in sorted_folders:
        # Show only last 2-3 parts of path and truncate if needed
        parts = folder.split("/")
        if len(parts) > 3:
            display_name = ".../" + "/".join(parts[-2:])
        elif len(parts) > 2:
            display_name = "/".join(parts[-2:])
        else:
            display_name = folder

        # Manually truncate to 35 chars without ellipses
        if len(display_name) > 35:
            display_name = display_name[:35]

        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Create bar
        bar = _create_bar(tokens, max_tokens, width=20)

        table.add_row(
            display_name,
            bar,
            _format_number(tokens),
            f"{percentage:.1f}%",
        )

    return Panel(
        table,
        title="[bold]Tokens by Project",
        border_style="white",
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
            title="[bold]시간별 사용량",
            border_style="white",
        )

    # Sort by hour
    sorted_hours = sorted(hourly_data.items())

    # Create table with Korean column names matching the screenshot
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("시간", style="purple", justify="left", width=8)
    table.add_column("비용", style="green", justify="right", width=10)
    table.add_column("입력 토큰", style=CYAN, justify="right", width=12)
    table.add_column("출력 토큰", style=CYAN, justify="right", width=12)
    table.add_column("캐시 생성", style="magenta", justify="right", width=14)
    table.add_column("캐시 읽기", style="magenta", justify="right", width=14)
    table.add_column("메시지 수", style="white", justify="right", width=10)

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
        title="[bold]시간별 사용량",
        border_style="white",
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

        # Show current mode highlighted
        if view_mode == "monthly":
            footer.append("[m] Monthly", style=f"bold {ORANGE}")
        else:
            footer.append("[m] Monthly", style=DIM)
        footer.append(" | ", style=DIM)

        if view_mode == "weekly":
            footer.append("[w] Weekly", style=f"bold {ORANGE}")
        else:
            footer.append("[w] Weekly", style=DIM)
        footer.append(" | ", style=DIM)

        if view_mode == "yearly":
            footer.append("[y] Yearly", style=f"bold {ORANGE}")
        else:
            footer.append("[y] Yearly", style=DIM)
        footer.append(" | ", style=DIM)

        footer.append("[q] Quit\n", style=DIM)

    # Add date range if provided
    if date_range:
        view_label = {
            "monthly": "Monthly",
            "weekly": "Weekly (7-day period)",
            "yearly": "Yearly"
        }.get(view_mode, "Monthly")

        footer.append("Data range: ", style=DIM)
        footer.append(f"{date_range}", style=f"bold {CYAN}")
        footer.append(f" ({view_label})\n", style=DIM)

    # Add export tip (only for non-yearly modes)
    if view_mode != "yearly":
        footer.append("Tip: ", style=DIM)
        footer.append("Export heatmap with ", style=DIM)
        footer.append("ccg export --open", style=f"bold {CYAN}")

    return footer


#endregion
