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
YELLOW = "bright_yellow"
CYAN = "cyan"  # For percentages
BLUE = "dodger_blue1"  # More distinct blue for Input/Output tokens (distinct from cyan)
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


def _get_bar_color(percentage: int, color_mode: str, colors: dict) -> str:
    """
    Get color based on color mode and usage percentage.

    Args:
        percentage: Usage percentage (0-100)
        color_mode: Color mode ("solid" or "gradient")
        colors: Dictionary with color values:
            - solid: Color for solid mode (hex or Rich color name)
            - gradient_low: Color for 0-X% (hex or Rich color name)
            - gradient_mid: Color for X-Y% (hex or Rich color name)
            - gradient_high: Color for Y-100% (hex or Rich color name)
            - unfilled: Color for unfilled portion (hex or Rich color name)
            - color_range_low: Low range threshold (default: 60)
            - color_range_high: High range threshold (default: 85)

    Returns:
        Color string (hex or Rich color name) for Rich library
    """
    from src.config.defaults import DEFAULT_COLORS

    if color_mode == "solid":
        return colors.get("color_solid", DEFAULT_COLORS['color_solid'])
    elif color_mode == "gradient":
        # Get user-defined color range thresholds
        color_range_low = int(colors.get("color_range_low", DEFAULT_COLORS.get('color_range_low', '60')))
        color_range_high = int(colors.get("color_range_high", DEFAULT_COLORS.get('color_range_high', '85')))

        # Gradation mode: percentage-based colors with user-defined thresholds
        if percentage < color_range_low:
            return colors.get("color_gradient_low", DEFAULT_COLORS['color_gradient_low'])
        elif percentage < color_range_high:
            return colors.get("color_gradient_mid", DEFAULT_COLORS['color_gradient_mid'])
        else:
            return colors.get("color_gradient_high", DEFAULT_COLORS['color_gradient_high'])
    else:
        return colors.get("color_solid", DEFAULT_COLORS['color_solid'])


def _create_usage_bar_with_percent(percentage: int, width: int = 50, color_mode: str = "gradient", colors: dict = None) -> Text:
    """
    Create a usage bar for usage page with percentage at the end.
    Format: ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 8%

    Args:
        percentage: Percentage value (0-100)
        width: Total width of bar (excluding percentage text)
        color_mode: Color mode ("solid" or "gradient")
        colors: Dictionary with color values (solid, gradient_low/mid/high, unfilled)

    Returns:
        Rich Text object with bar and percentage
    """
    from src.config.defaults import DEFAULT_COLORS

    if colors is None:
        colors = DEFAULT_COLORS

    filled = int((percentage / 100) * width)
    bar_color = _get_bar_color(percentage, color_mode, colors)
    unfilled_color = colors.get("color_unfilled", DEFAULT_COLORS['color_unfilled'])

    bar_text = Text()
    bar_text.append("█" * filled, style=bar_color)
    bar_text.append("█" * (width - filled), style=unfilled_color)
    bar_text.append(f" {percentage}%", style="bold white")
    return bar_text


def render_dashboard(stats: AggregatedStats, records: list[UsageRecord], console: Console, skip_limits: bool = False, clear_screen: bool = True, date_range: str = None, limits_from_db: dict | None = None, fast_mode: bool = False, view_mode: str = "usage", is_updating: bool = False, view_mode_ref: dict | None = None) -> None:
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
        is_updating: If True, show updating spinner in footer
        view_mode_ref: Reference dict for view mode state (includes usage_display_mode)
    """
    # Optionally clear screen and reset cursor to top
    if clear_screen:
        # Use console.clear() for better compatibility with VSCode terminal
        console.clear()

    # For heatmap mode, show heatmap instead of dashboard
    if view_mode == "heatmap":
        from src.commands.heatmap import _display_heatmap, _load_limits_data
        limits_data = _load_limits_data()
        _display_heatmap(console, stats, limits_data, year=None)
        # Show footer with keyboard shortcuts
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True, is_updating=is_updating, view_mode_ref=view_mode_ref)
        console.print()
        console.print(footer, end="")
        return

    # For devices mode, show device statistics
    if view_mode == "devices":
        from src.visualization.device_stats import render_device_statistics
        render_device_statistics(console)
        # Show footer with keyboard shortcuts
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True, is_updating=is_updating, view_mode_ref=view_mode_ref)
        console.print()
        console.print(footer, end="")
        return

    # For usage mode, show only Usage Limits
    if view_mode == "usage":
        from src.models.pricing import format_cost

        # Add blank line at top
        console.print()

        # Get usage display mode from view_mode_ref
        usage_display_mode = view_mode_ref.get('usage_display_mode', 0) if view_mode_ref else 0
        # 0 = M1 (no border, bar+%), 1 = M2 (no border, separate %), 2 = M3 (border, bar+%), 3 = M4 (border, separate %)

        # Get color mode and colors from view_mode_ref
        from src.config.defaults import DEFAULT_COLORS
        color_mode = view_mode_ref.get('color_mode', 'gradient') if view_mode_ref else 'gradient'
        colors = view_mode_ref.get('colors', DEFAULT_COLORS) if view_mode_ref else DEFAULT_COLORS

        # Determine bar width and style based on mode
        is_m1_mode = usage_display_mode == 0
        is_m2_mode = usage_display_mode == 1
        is_m3_mode = usage_display_mode == 2
        is_m4_mode = usage_display_mode == 3

        # Both modes use terminal width auto-sizing
        terminal_width = console.width
        bar_width = max(20, terminal_width - 14)

        # Use limits from DB if available, otherwise fetch live
        limits = limits_from_db
        if limits is None and not skip_limits:
            from src.commands.limits import capture_limits
            if console:
                with console.status(f"[bold {ORANGE}]Loading usage limits...", spinner="dots", spinner_style=ORANGE):
                    limits = capture_limits()
            else:
                limits = capture_limits()

        # Show Usage Limits if available
        if limits and "error" not in limits:
            # Format reset dates from "Oct 17, 10am" to "10/17"
            def format_reset_date(reset_str: str) -> str:
                """Convert 'Oct 17, 10am (Asia/Seoul)' to '10/17'"""
                import re
                # Remove timezone part
                reset_no_tz = reset_str.split(' (')[0] if '(' in reset_str else reset_str
                # Extract month and day from "Oct 17, 10am" format
                match = re.search(r'([A-Za-z]+)\s+(\d+)', reset_no_tz)
                if match:
                    month_name = match.group(1)
                    day = match.group(2)
                    # Convert month name to number
                    from datetime import datetime
                    month_num = datetime.strptime(month_name, '%b').month
                    return f"{month_num}/{day}"
                return reset_no_tz

            session_reset = format_reset_date(limits['session_reset'])
            week_reset = format_reset_date(limits['week_reset'])
            opus_reset = format_reset_date(limits['opus_reset'])

            # Calculate costs for each limit period
            session_cost = _calculate_session_cost(records)  # Last 5 hours, all models
            weekly_sonnet_cost = _calculate_weekly_sonnet_cost(records)  # Weekly, sonnet only
            weekly_opus_cost = _calculate_weekly_opus_cost(records)  # Weekly, opus only

            # Create table structure with 3 rows per limit
            # M1/M2 modes use no padding, M3/M4 modes use reduced padding for compact display
            table_padding = (0, 1) if (is_m3_mode or is_m4_mode) else (0, 0)
            limits_table = Table(show_header=False, box=None, padding=table_padding)
            limits_table.add_column("Content", justify="left")

            # M1 mode: compact style with bar+percentage combined, no border
            if is_m1_mode:
                # Session limit (3 rows)
                limits_table.add_row("Current session")
                session_bar = _create_usage_bar_with_percent(limits["session_pct"], width=bar_width, color_mode=color_mode, colors=colors)
                limits_table.add_row(session_bar)
                limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Week limit (3 rows)
                limits_table.add_row("Current week (all models)")
                week_bar = _create_usage_bar_with_percent(limits["week_pct"], width=bar_width, color_mode=color_mode, colors=colors)
                limits_table.add_row(week_bar)
                limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Opus limit (3 rows)
                limits_table.add_row("Current week (Opus)")
                opus_bar = _create_usage_bar_with_percent(limits["opus_pct"], width=bar_width, color_mode=color_mode, colors=colors)
                limits_table.add_row(opus_bar)
                limits_table.add_row(f"Resets {opus_reset} ({format_cost(weekly_opus_cost)})", style=DIM)

                # Display table without panel wrapper
                console.print(limits_table)

            elif is_m2_mode:
                # M2 mode: M1 style (no border) with M4 bars (percentage separated)
                # Session limit (3 rows)
                limits_table.add_row("Current session")
                session_bar = _create_bar(limits["session_pct"], 100, width=bar_width, color=_get_bar_color(limits["session_pct"], color_mode, colors))
                bar_text = Text()
                bar_text.append(session_bar)
                bar_text.append(f"  {limits['session_pct']}%", style="bold white")
                limits_table.add_row(bar_text)
                limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Week limit (3 rows)
                limits_table.add_row("Current week (all models)")
                week_bar = _create_bar(limits["week_pct"], 100, width=bar_width, color=_get_bar_color(limits["week_pct"], color_mode, colors))
                bar_text = Text()
                bar_text.append(week_bar)
                bar_text.append(f"  {limits['week_pct']}%", style="bold white")
                limits_table.add_row(bar_text)
                limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Opus limit (3 rows)
                limits_table.add_row("Current week (Opus)")
                opus_bar = _create_bar(limits["opus_pct"], 100, width=bar_width, color=_get_bar_color(limits["opus_pct"], color_mode, colors))
                bar_text = Text()
                bar_text.append(opus_bar)
                bar_text.append(f"  {limits['opus_pct']}%", style="bold white")
                limits_table.add_row(bar_text)
                limits_table.add_row(f"Resets {opus_reset} ({format_cost(weekly_opus_cost)})", style=DIM)

                # Display table without panel wrapper (like M1)
                console.print(limits_table)

            elif is_m3_mode:
                # M3 mode: dashboard style with bar+percentage combined (like M1) and panel wrapper
                # Session limit (3 rows)
                limits_table.add_row("Current session")
                session_bar = _create_usage_bar_with_percent(limits["session_pct"], width=bar_width, color_mode=color_mode, colors=colors)
                limits_table.add_row(session_bar)
                limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Week limit (3 rows)
                limits_table.add_row("Current week (all models)")
                week_bar = _create_usage_bar_with_percent(limits["week_pct"], width=bar_width, color_mode=color_mode, colors=colors)
                limits_table.add_row(week_bar)
                limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Opus limit (3 rows)
                limits_table.add_row("Current week (Opus)")
                opus_bar = _create_usage_bar_with_percent(limits["opus_pct"], width=bar_width, color_mode=color_mode, colors=colors)
                limits_table.add_row(opus_bar)
                limits_table.add_row(f"Resets {opus_reset} ({format_cost(weekly_opus_cost)})", style=DIM)

                # Wrap in outer "Usage Limits" panel
                limits_outer_panel = Panel(
                    limits_table,
                    title="[bold]Usage Limits",
                    border_style="white",
                    expand=True,
                )
                console.print(limits_outer_panel)

            elif is_m4_mode:
                # M4 mode: dashboard style with percentage separated and panel wrapper
                # Session limit (3 rows)
                limits_table.add_row("Current session")
                session_bar = _create_bar(limits["session_pct"], 100, width=bar_width, color=_get_bar_color(limits["session_pct"], color_mode, colors))
                bar_text = Text()
                bar_text.append(session_bar)
                bar_text.append(f"  {limits['session_pct']}%", style="bold white")
                limits_table.add_row(bar_text)
                limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Week limit (3 rows)
                limits_table.add_row("Current week (all models)")
                week_bar = _create_bar(limits["week_pct"], 100, width=bar_width, color=_get_bar_color(limits["week_pct"], color_mode, colors))
                bar_text = Text()
                bar_text.append(week_bar)
                bar_text.append(f"  {limits['week_pct']}%", style="bold white")
                limits_table.add_row(bar_text)
                limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
                limits_table.add_row("")  # Blank line

                # Opus limit (3 rows)
                limits_table.add_row("Current week (Opus)")
                opus_bar = _create_bar(limits["opus_pct"], 100, width=bar_width, color=_get_bar_color(limits["opus_pct"], color_mode, colors))
                bar_text = Text()
                bar_text.append(opus_bar)
                bar_text.append(f"  {limits['opus_pct']}%", style="bold white")
                limits_table.add_row(bar_text)
                limits_table.add_row(f"Resets {opus_reset} ({format_cost(weekly_opus_cost)})", style=DIM)

                # Wrap in outer "Usage Limits" panel
                limits_outer_panel = Panel(
                    limits_table,
                    title="[bold]Usage Limits",
                    border_style="white",
                    expand=True,
                )
                console.print(limits_outer_panel)

        # Show footer at bottom for usage mode
        console.print()
        footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True, is_updating=is_updating, view_mode_ref=view_mode_ref)
        console.print(footer, end="")

        return

    # Check if we're in daily detail mode or message detail mode for weekly view
    daily_detail_date = None
    hourly_detail_hour = None
    if view_mode == "weekly" and view_mode_ref:
        daily_detail_date = view_mode_ref.get("daily_detail_date")
        hourly_detail_hour = view_mode_ref.get("hourly_detail_hour")

    # Create footer with export info, date range, and view mode
    footer = _create_footer(date_range, fast_mode=fast_mode, view_mode=view_mode, in_live_mode=True, is_updating=is_updating, view_mode_ref=view_mode_ref)

    # Create breakdowns for each view mode
    sections_to_render = []

    if daily_detail_date and hourly_detail_hour is not None:
        # Message detail mode - show messages for specific hour
        from src.storage.snapshot_db import load_all_devices_messages_by_hour
        hourly_messages = load_all_devices_messages_by_hour(daily_detail_date, hourly_detail_hour)
        message_detail = _create_message_detail_view(hourly_messages, daily_detail_date, hourly_detail_hour)
        sections_to_render.append(("message_detail", message_detail))
    elif daily_detail_date:
        # Daily detail mode - show only the detail view without KPI section
        daily_detail = _create_daily_detail_view(records, daily_detail_date)
        sections_to_render.append(("daily_detail", daily_detail))

        # Calculate hourly hours for keyboard navigation
        # Filter records to only those from target_date
        from collections import defaultdict
        from src.utils.timezone import format_local_time, get_user_timezone

        filtered_records = [
            record for record in records
            if record.timestamp.strftime("%Y-%m-%d") == daily_detail_date
        ]

        if filtered_records:
            user_tz = get_user_timezone()
            hourly_data = defaultdict(int)

            for record in filtered_records:
                if record.token_usage:
                    # Convert UTC timestamp to local timezone hour
                    hour = format_local_time(record.timestamp, "%H:00", user_tz)
                    hourly_data[hour] += record.token_usage.total_tokens

            # Sort by hour in descending order (same as display order)
            sorted_hours = sorted(hourly_data.keys(), reverse=True)

            # Extract hour numbers (00-23) as integers
            hourly_hours_int = []
            for hour_str in sorted_hours:
                try:
                    hour_int = int(hour_str.split(":")[0])
                    hourly_hours_int.append(hour_int)
                except:
                    pass

            # Store in view_mode_ref for keyboard listener
            if view_mode_ref:
                view_mode_ref['hourly_hours'] = hourly_hours_int
    else:
        # Normal mode - show KPI section and breakdowns
        kpi_section = _create_kpi_section(stats.overall_totals, records, view_mode=view_mode, skip_limits=skip_limits, console=console, limits_from_db=limits_from_db, view_mode_ref=view_mode_ref)

        # Render Summary (and Usage Limits in weekly mode)
        console.print(kpi_section, end="")
        console.print()  # Blank line between sections

        # Model breakdown is always important
        model_breakdown = _create_model_breakdown(records)
        sections_to_render.append(("model", model_breakdown))

        # Add mode-specific breakdown
        if view_mode == "weekly":
            # Show normal weekly breakdown
            project_breakdown = _create_project_breakdown(records)
            sections_to_render.append(("project", project_breakdown))

            # Get week range from view_mode_ref if available
            week_start = view_mode_ref.get('week_start_date') if view_mode_ref else None
            week_end = view_mode_ref.get('week_end_date') if view_mode_ref else None
            reset_time = view_mode_ref.get('week_reset_time') if view_mode_ref else None
            reset_day = view_mode_ref.get('week_reset_day') if view_mode_ref else None

            daily_breakdown_weekly = _create_daily_breakdown_weekly(records, week_start, week_end, reset_time, reset_day)
            sections_to_render.append(("daily_weekly", daily_breakdown_weekly))
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
    console.print(footer, end="")


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


def _create_kpi_section(overall, records: list[UsageRecord], view_mode: str = "monthly", skip_limits: bool = False, console: Console = None, limits_from_db: dict | None = None, view_mode_ref: dict | None = None) -> Group:
    """
    Create KPI cards with individual limit boxes beneath each (only for weekly mode).

    Args:
        overall: Overall statistics
        records: List of usage records (for cost calculation)
        view_mode: Current view mode - "monthly", "weekly", or "yearly"
        skip_limits: If True, skip fetching current limits (faster)
        console: Console instance for showing spinner
        limits_from_db: Pre-fetched limits from database (avoids live fetch)
        view_mode_ref: Reference dict for view mode state (includes color settings)

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
        Text(_format_number(total_input_tokens), style=f"bold {BLUE}"),
        title="Input Tokens",
        border_style="white",
        width=36,
    )

    kpi_grid.add_row(cost_card, messages_card, input_tokens_card)

    # Row 2: Output Tokens, Cache Creation, Cache Read
    output_tokens_card = Panel(
        Text(_format_number(total_output_tokens), style=f"bold {BLUE}"),
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

            # Get color mode and colors from view_mode_ref
            from src.config.defaults import DEFAULT_COLORS
            color_mode = view_mode_ref.get('color_mode', 'gradient') if view_mode_ref else 'gradient'
            colors = view_mode_ref.get('colors', DEFAULT_COLORS) if view_mode_ref else DEFAULT_COLORS

            # Calculate bar width based on terminal width (same as usage mode)
            terminal_width = console.width if console else 120
            bar_width = max(20, terminal_width - 14)

            # Create table structure with 3 rows per limit (G3 style - bar+percentage combined)
            limits_table = Table(show_header=False, box=None, padding=(0, 2))
            limits_table.add_column("Content", justify="left")

            # Session limit (3 rows)
            limits_table.add_row("Current session")
            session_bar = _create_usage_bar_with_percent(limits["session_pct"], width=bar_width, color_mode=color_mode, colors=colors)
            limits_table.add_row(session_bar)
            limits_table.add_row(f"Resets {session_reset} ({format_cost(session_cost)})", style=DIM)
            limits_table.add_row("")  # Blank line

            # Week limit (3 rows)
            limits_table.add_row("Current week (all models)")
            week_bar = _create_usage_bar_with_percent(limits["week_pct"], width=bar_width, color_mode=color_mode, colors=colors)
            limits_table.add_row(week_bar)
            limits_table.add_row(f"Resets {week_reset} ({format_cost(weekly_sonnet_cost)})", style=DIM)
            limits_table.add_row("")  # Blank line

            # Opus limit (3 rows)
            limits_table.add_row("Current week (Opus)")
            opus_bar = _create_usage_bar_with_percent(limits["opus_pct"], width=bar_width, color_mode=color_mode, colors=colors)
            limits_table.add_row(opus_bar)
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
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Model", style="white", justify="left", width=30, overflow="crop")
    table.add_column("", justify="left", width=20)  # Bar column (no header)
    table.add_column("Tokens", style=ORANGE, justify="right", width=12)
    table.add_column("%", style=CYAN, justify="right", width=8)
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
            f"[cyan]{percentage:.1f}%[/cyan]",
            format_cost(data["cost"]),
        )

    # Add separator line before total
    table.add_row("", "", "", "", "")

    # Add total row
    table.add_row(
        "[bold]Total",
        Text(""),
        f"[bold]{_format_number(total_tokens)}",
        "[bold cyan]100.0%",
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
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Project", style="white", justify="left", width=30, overflow="crop")
    table.add_column("", justify="left", width=20)  # Bar column (no header)
    table.add_column("Tokens", style=ORANGE, justify="right", width=12)
    table.add_column("%", style=CYAN, justify="right", width=8)
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
            f"[cyan]{percentage:.1f}%[/cyan]",
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
    table.add_column("Input", style=BLUE, justify="right", width=12)
    table.add_column("Output", style=BLUE, justify="right", width=12)
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


def _create_daily_breakdown_weekly(records: list[UsageRecord], week_start_date=None, week_end_date=None, reset_time=None, reset_day=None) -> Panel:
    """
    Create graph-style daily usage breakdown for weekly mode.
    Shows all 7 days of the week period, including days with no usage.
    Days without data show "-" for tokens/cost and 0% for percentage.

    Args:
        records: List of usage records (already filtered to week period)
        week_start_date: Start date of the week period (date object)
        week_end_date: End date of the week period (date object)
        reset_time: Reset time in HH:MM format (e.g., "09:59")
        reset_day: Reset day of week (e.g., "Fri", "Mon")

    Returns:
        Panel with daily breakdown in graph format
    """
    from src.models.pricing import calculate_cost, format_cost
    from datetime import timedelta

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

    # If week range not provided, try to infer from records
    if week_start_date is None or week_end_date is None:
        # Try to find min/max from records
        dates_with_data = []
        for record in records:
            if record.token_usage:
                dates_with_data.append(record.timestamp.date())

        if dates_with_data:
            week_start_date = min(dates_with_data)
            week_end_date = max(dates_with_data)
        else:
            # No data at all
            return Panel(
                Text("No daily data available", style=DIM),
                title="[bold]Daily Usage",
                border_style="white",
            )

    # Generate all dates in the week range (should be exactly 7 days)
    all_dates = []
    current_date = week_start_date
    while current_date <= week_end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        if date_str in daily_data:
            all_dates.append((date_str, daily_data[date_str]))
        else:
            # Day with no data - use zeros
            all_dates.append((date_str, {
                "total_tokens": 0,
                "cost": 0.0
            }))
        current_date += timedelta(days=1)

    # Calculate totals and max for scaling (only from days with data)
    total_tokens = sum(data["total_tokens"] for _, data in all_dates)
    max_tokens = max((data["total_tokens"] for _, data in all_dates), default=0)

    # Sort by date in descending order (most recent first)
    sorted_dates = sorted(all_dates, reverse=True)

    # Create table with bars
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Date", style="white", justify="left", width=30)
    table.add_column("", justify="left", width=20)  # Bar column (no header)
    table.add_column("Tokens", style=ORANGE, justify="right", width=12)
    table.add_column("%", style=CYAN, justify="right", width=8)
    table.add_column("Cost", style="green", justify="right", width=10)

    for idx, (date, data) in enumerate(sorted_dates, start=1):
        tokens = data["total_tokens"]
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Parse date and get day of week
        from datetime import datetime
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        day_name = date_obj.strftime("%a")  # Mon, Tue, Wed, etc.

        # Check if this is the reset day and add time annotation
        # Combine shortcut and date with single space: [1] 2025-10-15 (Mon) [09:59]
        if reset_day and reset_time and day_name == reset_day:
            date_with_shortcut = f"[yellow][{idx}][/yellow] {date} ({day_name}) [purple][{reset_time}][/purple]"
        else:
            date_with_shortcut = f"[yellow][{idx}][/yellow] {date} ({day_name})"

        # If no data for this day, show "-" for tokens/cost and empty bar
        if tokens == 0:
            # Empty bar (all dim)
            bar = Text("▬" * 20, style=DIM)
            tokens_display = "[dim]-[/dim]"
            percentage_display = "[dim]-[/dim]"
            cost_display = "[dim]-[/dim]"
        else:
            # Normal display with bar
            bar = _create_bar(tokens, max_tokens, width=20)
            tokens_display = _format_number(tokens)
            percentage_display = f"[cyan]{percentage:.1f}%[/cyan]"
            cost_display = format_cost(data["cost"])

        table.add_row(
            date_with_shortcut,
            bar,
            tokens_display,
            percentage_display,
            cost_display,
        )

    return Panel(
        table,
        title="[bold]Daily Usage",
        subtitle="[dim]Press number keys (1-7) to view detailed hourly breakdown[/dim]",
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
    table.add_column("Input", style=BLUE, justify="right", width=12)
    table.add_column("Output", style=BLUE, justify="right", width=12)
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
    table.add_column("Input", style=BLUE, justify="right", width=12)
    table.add_column("Output", style=BLUE, justify="right", width=12)
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


def _create_daily_detail_view(records: list[UsageRecord], target_date: str) -> Group:
    """
    Create detailed view for a specific day showing hourly usage, models, and projects.

    Args:
        records: List of usage records
        target_date: Target date in YYYY-MM-DD format (e.g., "2025-10-15")

    Returns:
        Group containing hourly, model, and project breakdowns for the target date
    """
    from src.models.pricing import calculate_cost, format_cost

    # Parse target date to get day of week
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    day_name = date_obj.strftime("%A")  # Full day name (Monday, Tuesday, etc.)
    title_date = f"{target_date} ({day_name})"

    # Filter records to only those from target_date
    filtered_records = [
        record for record in records
        if record.timestamp.strftime("%Y-%m-%d") == target_date
    ]

    if not filtered_records:
        return Group(
            Panel(
                Text(f"No data available for {target_date}", style=DIM),
                title=f"[bold]Daily Detail - {title_date}",
                border_style="white",
            )
        )

    # Create hourly breakdown
    hourly_data: dict[str, dict] = defaultdict(lambda: {
        "cost": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation": 0,
        "cache_read": 0,
        "messages": 0
    })

    # Import timezone utilities and get timezone once (performance optimization)
    from src.utils.timezone import format_local_time, get_user_timezone
    user_tz = get_user_timezone()  # Load timezone once instead of per-record

    for record in filtered_records:
        if record.token_usage:
            # Convert UTC timestamp to local timezone for display
            hour = format_local_time(record.timestamp, "%H:00", user_tz)
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

    # Create hourly table
    hourly_table = Table(show_header=True, box=None, padding=(0, 2))
    hourly_table.add_column("", style="yellow", justify="left", width=5)  # Shortcut column
    hourly_table.add_column("Time", style="purple", justify="left", width=8)
    hourly_table.add_column("Cost", style="green", justify="right", width=10)
    hourly_table.add_column("Input", style=BLUE, justify="right", width=12)
    hourly_table.add_column("Output", style=BLUE, justify="right", width=12)
    hourly_table.add_column("Cache Write", style="magenta", justify="right", width=14)
    hourly_table.add_column("Cache Read", style="magenta", justify="right", width=14)
    hourly_table.add_column("Messages", style="white", justify="right", width=10)

    # Sort by hour in descending order (most recent first) to show current work at top
    sorted_hours = sorted(hourly_data.items(), reverse=True)

    for idx, (hour, data) in enumerate(sorted_hours, start=1):
        # Use numbers 1-9, then letters a-o for shortcuts (supports up to 24 hours)
        if idx <= 9:
            shortcut = str(idx)
        else:
            shortcut = chr(ord('a') + idx - 10)  # 10->a, 11->b, ..., 24->o

        hourly_table.add_row(
            f"[{shortcut}]",  # Shortcut key
            hour,
            format_cost(data["cost"]),
            _format_number(data["input_tokens"]),
            _format_number(data["output_tokens"]),
            _format_number(data["cache_creation"]),
            _format_number(data["cache_read"]),
            str(data["messages"]),
        )

    hourly_panel = Panel(
        hourly_table,
        title=f"[bold]Hourly Usage - {title_date}",
        subtitle="[dim]Press keys [1]-[9], [a]-[o] to view message details for that hour[/dim]",
        border_style="white",
        expand=True,
    )

    # Create model breakdown
    model_data: dict[str, dict] = defaultdict(lambda: {
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0
    })

    for record in filtered_records:
        if record.model and record.token_usage and record.model != "<synthetic>":
            model_data[record.model]["total_tokens"] += record.token_usage.total_tokens
            model_data[record.model]["input_tokens"] += record.token_usage.input_tokens
            model_data[record.model]["output_tokens"] += record.token_usage.output_tokens

            cost = calculate_cost(
                record.token_usage.input_tokens,
                record.token_usage.output_tokens,
                record.model,
                record.token_usage.cache_creation_tokens,
                record.token_usage.cache_read_tokens,
            )
            model_data[record.model]["cost"] += cost

    total_tokens = sum(data["total_tokens"] for data in model_data.values())
    total_cost = sum(data["cost"] for data in model_data.values())
    max_tokens = max(data["total_tokens"] for data in model_data.values()) if model_data else 0
    sorted_models = sorted(model_data.items(), key=lambda x: x[1]["total_tokens"], reverse=True)

    model_table = Table(show_header=False, box=None, padding=(0, 2))
    model_table.add_column("Model", style="white", justify="left", width=25)
    model_table.add_column("Bar", justify="left")
    model_table.add_column("Tokens", style=ORANGE, justify="right")
    model_table.add_column("Percentage", style=CYAN, justify="right")
    model_table.add_column("Cost", style="green", justify="right", width=10)

    for model, data in sorted_models:
        display_name = model.split("/")[-1] if "/" in model else model
        if "claude" in display_name.lower():
            display_name = display_name.replace("claude-", "")

        tokens = data["total_tokens"]
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0
        bar = _create_bar(tokens, max_tokens, width=20)

        model_table.add_row(
            display_name,
            bar,
            _format_number(tokens),
            f"[cyan]{percentage:.1f}%[/cyan]",
            format_cost(data["cost"]),
        )

    # Add total row
    model_table.add_row("", "", "", "", "")
    model_table.add_row(
        "[bold]Total",
        Text(""),
        f"[bold]{_format_number(total_tokens)}",
        "[bold cyan]100.0%",
        f"[bold green]{format_cost(total_cost)}",
    )

    model_panel = Panel(
        model_table,
        title=f"[bold]Tokens by Model - {title_date}",
        border_style="white",
        expand=True,
    )

    # Create project breakdown
    folder_data: dict[str, dict] = defaultdict(lambda: {
        "total_tokens": 0,
        "cost": 0.0
    })

    for record in filtered_records:
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

    total_tokens_proj = sum(data["total_tokens"] for data in folder_data.values())
    sorted_folders = sorted(folder_data.items(), key=lambda x: x[1]["total_tokens"], reverse=True)
    sorted_folders = sorted_folders[:10]  # Limit to top 10
    max_tokens_proj = max(data["total_tokens"] for _, data in sorted_folders) if sorted_folders else 0

    project_table = Table(show_header=False, box=None, padding=(0, 2))
    project_table.add_column("Project", style="white", justify="left", overflow="crop")
    project_table.add_column("Bar", justify="left", overflow="crop")
    project_table.add_column("Tokens", style=ORANGE, justify="right")
    project_table.add_column("Percentage", style=CYAN, justify="right")
    project_table.add_column("Cost", style="green", justify="right", width=10)

    for folder, data in sorted_folders:
        parts = folder.split("/")
        if len(parts) > 2:
            display_name = "/".join(parts[-2:])
        else:
            display_name = folder

        if len(display_name) > 35:
            display_name = display_name[:35]

        tokens = data["total_tokens"]
        percentage = (tokens / total_tokens_proj * 100) if total_tokens_proj > 0 else 0
        bar = _create_bar(tokens, max_tokens_proj, width=20)

        project_table.add_row(
            display_name,
            bar,
            _format_number(tokens),
            f"[cyan]{percentage:.1f}%[/cyan]",
            format_cost(data["cost"]),
        )

    project_panel = Panel(
        project_table,
        title=f"[bold]Tokens by Project - {title_date}",
        border_style="white",
        expand=True,
    )

    # Add spacing between panels
    spacing = Text("")
    return Group(hourly_panel, spacing, model_panel, spacing, project_panel)


def _create_message_detail_view(records: list[UsageRecord], target_date: str, target_hour: int) -> Group:
    """
    Create detailed view for messages in a specific hour.

    Args:
        records: List of usage records for the target hour
        target_date: Target date in YYYY-MM-DD format (e.g., "2025-10-15")
        target_hour: Target hour in 24-hour format (0-23)

    Returns:
        Group containing message detail table and content previews
    """
    from src.models.pricing import calculate_cost, format_cost
    from src.utils.timezone import format_local_time, get_user_timezone

    # Parse target date to get day of week
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    day_name = date_obj.strftime("%A")
    hour_str = f"{target_hour:02d}:00"
    title_text = f"{target_date} ({day_name}) - {hour_str}"

    if not records:
        return Group(
            Panel(
                Text(f"No messages found for {target_date} at {hour_str}", style=DIM),
                title=f"[bold]Message Detail - {title_text}",
                border_style="white",
            )
        )

    # Get timezone once for performance
    user_tz = get_user_timezone()

    # Group messages by session for visual separation
    from collections import defaultdict
    sessions: dict[str, list[UsageRecord]] = defaultdict(list)
    for record in records:
        sessions[record.session_id].append(record)

    # Build list of message items (each is a small table with optional content)
    message_items = []

    # Process each session
    for session_idx, (session_id, session_records) in enumerate(sessions.items()):
        # Add session separator (except before first session)
        if session_idx > 0:
            message_items.append(Text(""))

        # Add each message in the session
        for record in session_records:
            # Format time (HH:MM:SS in local timezone)
            time_str = format_local_time(record.timestamp, "%H:%M:%S", user_tz)

            # Message type
            msg_type = "User" if record.is_user_prompt else "Asst"

            # Model name (shortened)
            if record.model:
                model_name = record.model.split("/")[-1] if "/" in record.model else record.model
                if "claude" in model_name.lower():
                    model_name = model_name.replace("claude-", "")
            else:
                model_name = "-"

            # Token values (only for assistant messages)
            if record.token_usage:
                input_tok = _format_number(record.token_usage.input_tokens)
                output_tok = _format_number(record.token_usage.output_tokens)
                cache_write = _format_number(record.token_usage.cache_creation_tokens)
                cache_read = _format_number(record.token_usage.cache_read_tokens)

                # Calculate cost
                if record.model and record.model != "<synthetic>":
                    cost = calculate_cost(
                        record.token_usage.input_tokens,
                        record.token_usage.output_tokens,
                        record.model,
                        record.token_usage.cache_creation_tokens,
                        record.token_usage.cache_read_tokens,
                    )
                    cost_str = format_cost(cost)
                else:
                    cost_str = "-"
            else:
                input_tok = "-"
                output_tok = "-"
                cache_write = "-"
                cache_read = "-"
                cost_str = "-"

            # Create a small table for this message
            msg_table = Table(show_header=False, box=None, padding=(0, 2), show_edge=False)
            msg_table.add_column("Time", style="purple", justify="left", width=10)
            msg_table.add_column("Type", style="white", justify="left", width=6)
            msg_table.add_column("Model", style="white", justify="left", width=18)
            msg_table.add_column("Input", style=BLUE, justify="right", width=10)
            msg_table.add_column("Output", style=BLUE, justify="right", width=10)
            msg_table.add_column("Cache W", style="magenta", justify="right", width=10)
            msg_table.add_column("Cache R", style="magenta", justify="right", width=10)
            msg_table.add_column("Cost", style="green", justify="right", width=10)

            msg_table.add_row(
                time_str,
                msg_type,
                model_name,
                input_tok,
                output_tok,
                cache_write,
                cache_read,
                cost_str,
            )

            message_items.append(msg_table)

            # Add content preview immediately below all messages (both User and Asst)
            if record.content:
                preview = record.content.strip().replace("\n", " ")
                # Truncate to 70% of original length (60 * 0.7 = 42 chars)
                if len(preview) > 42:
                    preview = preview[:42] + "..."

                # Create content text with indent to align with "Asst" column + 2 spaces
                # Time column (10) + padding (4) + 2 extra spaces = 16
                content_text = Text()
                content_text.append("                ", style=DIM)  # Indent to Asst position + 2
                content_text.append("ㄴ ", style=DIM)
                content_text.append(preview, style=DIM)
                message_items.append(content_text)

    # Create header table
    header_table = Table(show_header=True, box=None, padding=(0, 2))
    header_table.add_column("Time", style="purple", justify="left", width=10)
    header_table.add_column("Type", style="white", justify="left", width=6)
    header_table.add_column("Model", style="white", justify="left", width=18)
    header_table.add_column("Input", style=BLUE, justify="right", width=10)
    header_table.add_column("Output", style=BLUE, justify="right", width=10)
    header_table.add_column("Cache W", style="magenta", justify="right", width=10)
    header_table.add_column("Cache R", style="magenta", justify="right", width=10)
    header_table.add_column("Cost", style="green", justify="right", width=10)

    # Combine header and messages
    all_items = [header_table] + message_items

    # Create panel
    panel = Panel(
        Group(*all_items),
        title=f"[bold]Message Detail - {title_text}",
        subtitle="[dim]Press esc to return to daily view[/dim]",
        border_style="white",
        expand=True,
    )

    return Group(panel)


def _create_footer(date_range: str = None, fast_mode: bool = False, view_mode: str = "monthly", in_live_mode: bool = False, is_updating: bool = False, view_mode_ref: dict | None = None) -> Text:
    """
    Create footer with export command info, date range, and view mode.

    Args:
        date_range: Optional date range string to display
        fast_mode: If True, show warning about fast mode
        view_mode: Current view mode - "monthly", "weekly", or "yearly"
        in_live_mode: If True, show keyboard shortcuts for mode switching
        is_updating: If True, show updating spinner instead of last update time
        view_mode_ref: Reference dict for view mode state (includes usage_display_mode)

    Returns:
        Text with export instructions, date range, and view mode info
    """
    footer = Text()

    # Get last update time from database (only if not currently updating)
    last_update_time = None
    if not is_updating:
        try:
            from src.storage.snapshot_db import get_database_stats
            from src.utils.timezone import format_local_time, get_user_timezone
            # Get timezone once for performance
            user_tz = get_user_timezone()
            db_stats = get_database_stats()
            if db_stats.get("newest_timestamp"):
                timestamp_str = db_stats["newest_timestamp"]
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    last_update_time = format_local_time(dt, "%H:%M:%S", user_tz)
                except (ValueError, AttributeError):
                    pass
        except Exception:
            pass

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
        # Check if in daily detail mode or message detail mode
        in_daily_detail = view_mode == "weekly" and view_mode_ref and view_mode_ref.get("daily_detail_date")
        in_message_detail = view_mode == "weekly" and view_mode_ref and view_mode_ref.get("hourly_detail_hour") is not None

        # Show "Shortcut:" for usage mode, "View:" for others
        if view_mode == "usage":
            footer.append("Shortcut: ", style=DIM)
        else:
            footer.append("View: ", style=DIM)

        # Show simplified format for usage mode, full names for others
        if view_mode == "usage":
            # Simplified format for usage mode (only show usage and weekly)
            footer.append("[u]sage", style=f"black on {YELLOW}")
            footer.append(" ", style="")
            footer.append("[w]eekly", style=DIM)
        elif in_message_detail:
            # Message detail mode - show date and hour
            daily_date = view_mode_ref.get("daily_detail_date")
            hourly_hour = view_mode_ref.get("hourly_detail_hour")
            # Parse date to get day of week
            try:
                date_obj = datetime.strptime(daily_date, "%Y-%m-%d")
                day_name = date_obj.strftime("%a")
                hour_str = f"{hourly_hour:02d}:00"
                footer.append(f"Message Detail - {daily_date} ({day_name}) {hour_str}", style=f"black on {YELLOW}")
            except:
                footer.append(f"Message Detail - {daily_date} {hourly_hour:02d}:00", style=f"black on {YELLOW}")
        elif in_daily_detail:
            # Daily detail mode - show date
            daily_date = view_mode_ref.get("daily_detail_date")
            # Parse date to get day of week
            try:
                date_obj = datetime.strptime(daily_date, "%Y-%m-%d")
                day_name = date_obj.strftime("%a")
                footer.append(f"Daily Detail - {daily_date} ({day_name})", style=f"black on {YELLOW}")
            except:
                footer.append(f"Daily Detail - {daily_date}", style=f"black on {YELLOW}")
        else:
            # Full names for other modes
            # Usage
            if view_mode == "usage":
                footer.append("[u]sage", style=f"black on {YELLOW}")
            else:
                footer.append("[u]sage", style=DIM)
            footer.append(" ", style="")

            # Weekly
            if view_mode == "weekly":
                footer.append("[w]eekly", style=f"black on {YELLOW}")
            else:
                footer.append("[w]eekly", style=DIM)
            footer.append(" ", style="")

            # Monthly
            if view_mode == "monthly":
                footer.append("[m]onthly", style=f"black on {YELLOW}")
            else:
                footer.append("[m]onthly", style=DIM)
            footer.append(" ", style="")

            # Yearly
            if view_mode == "yearly":
                footer.append("[y]early", style=f"black on {YELLOW}")
            else:
                footer.append("[y]early", style=DIM)
            footer.append(" ", style="")

            # Heatmap
            if view_mode == "heatmap":
                footer.append("[h]eatmap", style=f"black on {YELLOW}")
            else:
                footer.append("[h]eatmap", style=DIM)
            footer.append(" ", style="")

            # Devices
            if view_mode == "devices":
                footer.append("[d]evices", style=f"black on {YELLOW}")
            else:
                footer.append("[d]evices", style=DIM)
            footer.append(" ", style="")

            # Settings
            footer.append("[s]ettings", style=DIM)

        # Add date range if provided (on same line), but not for usage mode, daily detail, or message detail mode
        if date_range and view_mode != "usage" and not in_daily_detail and not in_message_detail:
            footer.append("  ", style=DIM)
            footer.append(f"{date_range}", style="bold cyan")

        # Add newline at end
        footer.append("\n")

        # Add navigation hint for usage mode (second line) - change display mode and color
        if view_mode == "usage":
            # Get current display mode
            usage_display_mode = view_mode_ref.get('usage_display_mode', 0) if view_mode_ref else 0

            # Get current color mode
            color_mode = view_mode_ref.get('color_mode', 'gradient') if view_mode_ref else 'gradient'

            # Build mode name: S1-S4 for Solid, G1-G4 for Gradient
            mode_prefix = "S" if color_mode == "solid" else "G"
            mode_number = (usage_display_mode % 4) + 1  # Convert 0-3 to 1-4
            current_mode_name = f"{mode_prefix}{mode_number}"

            footer.append("Use ", style=DIM)
            footer.append("tab", style=f"bold {YELLOW}")
            footer.append(" to change mode(", style=DIM)
            footer.append(current_mode_name, style="white")
            footer.append(")", style=DIM)
            footer.append("\n")

        # Add navigation hint for non-usage modes (second line)
        if view_mode in ["weekly", "monthly", "yearly"]:
            # Check if in message detail mode or daily detail mode
            in_message_detail = view_mode == "weekly" and view_mode_ref and view_mode_ref.get("hourly_detail_hour") is not None
            in_daily_detail = view_mode == "weekly" and view_mode_ref and view_mode_ref.get("daily_detail_date")

            if in_message_detail:
                # Message detail mode - show return instruction
                footer.append("Press ", style=DIM)
                footer.append("esc", style=f"bold {YELLOW}")
                footer.append(" to return to daily view.", style=DIM)
                footer.append("\n")
            elif in_daily_detail:
                # Daily detail mode - show return instruction
                footer.append("Press ", style=DIM)
                footer.append("esc", style=f"bold {YELLOW}")
                footer.append(" to return to weekly view.", style=DIM)
                footer.append("\n")
            else:
                # Navigation for weekly/monthly/yearly modes
                footer.append("Use ", style=DIM)
                footer.append("<", style=f"bold {YELLOW}")
                footer.append(" ", style=DIM)
                footer.append(">", style=f"bold {YELLOW}")
                if view_mode == "weekly":
                    period_label = "week"
                elif view_mode == "monthly":
                    period_label = "month"
                else:
                    period_label = "year"
                footer.append(f" to navigate {period_label}s, ", style=DIM)
                footer.append("esc", style=f"bold {YELLOW}")
                footer.append(" key to quit.", style=DIM)
                footer.append("\n")
        elif view_mode in ["heatmap", "devices"]:
            # Quit instruction for heatmap and devices modes
            footer.append("Use ", style=DIM)
            footer.append("esc", style=f"bold {YELLOW}")
            footer.append(" key to quit.", style=DIM)
            footer.append("\n")

        # Add auto update time or updating status (last line, so cursor appears on right)
        if is_updating:
            footer.append("Auto [r]efresh: ", style=DIM)
            footer.append("Updating... ", style="bold yellow")
            footer.append("◼", style="bold yellow blink")
        elif last_update_time:
            footer.append("Auto [r]efresh: ", style=DIM)
            footer.append(f"{last_update_time} ", style="bold cyan")

    else:
        # No live mode, just date range if provided
        if date_range:
            footer.append("Data range: ", style=DIM)
            footer.append(f"{date_range}", style="bold cyan")
            footer.append("\n", style=DIM)

    return footer


#endregion
