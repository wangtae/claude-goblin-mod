#region Imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.storage.snapshot_db import get_device_statistics
#endregion


#region Constants
# Claude-inspired color scheme (match dashboard.py)
ORANGE = "#ff8800"
CYAN = "cyan"
DIM = "grey50"

# Device-specific colors (distinct colors for each device)
DEVICE_COLORS = [
    "#ff8800",  # Orange
    "#00d4ff",  # Cyan
    "#ff3366",  # Pink
    "#00ff88",  # Green
    "#bb86fc",  # Purple
    "#ffdd00",  # Yellow
    "#ff6b6b",  # Red
    "#4ecdc4",  # Teal
]
#endregion


#region Functions

def render_device_statistics(console: Console, week_offset: int = 0, display_period: str = "all") -> None:
    """
    Render device statistics consistent with other dashboard views.

    Displays:
    - Device comparison table with bars (each device with unique color)
    - Weekly hourly heatmap for each device
    - Color legend with opacity percentage examples
    - Cost breakdown by device

    Args:
        console: Rich console for output
        week_offset: Number of weeks to offset (0=current week, -1=last week, 1=next week)
        display_period: Display period - "all", "monthly", or "weekly"
    """
    # Get device statistics filtered by period
    from src.storage.snapshot_db import get_device_statistics_for_period
    device_stats = get_device_statistics_for_period(period=display_period)

    if not device_stats:
        console.print("[yellow]No device data available yet.[/yellow]")
        console.print("[dim]Run 'ccu usage' to start tracking device-specific statistics.[/dim]")
        return

    # Render device table (same style as model breakdown, with unique colors)
    device_panel = _render_device_table(device_stats, display_period)
    console.print(device_panel, end="")
    console.print()  # Blank line

    # Render weekly hourly heatmap for each device
    heatmap_panel = _render_device_heatmaps(device_stats, week_offset, display_period)
    console.print(heatmap_panel, end="")


def _render_single_device_view(device: dict) -> Panel:
    """Render detailed view for a single device."""
    # Create detailed info table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Device Name", device["machine_name"])
    table.add_row("Messages", f"{device['total_messages']:,}")
    table.add_row("Sessions", f"{device['total_sessions']:,}")
    table.add_row("Total Tokens", f"{device['total_tokens']:,}")
    table.add_row("Input Tokens", f"{device['input_tokens']:,}")
    table.add_row("Output Tokens", f"{device['output_tokens']:,}")
    table.add_row("Cache Write", f"{device['cache_creation_tokens']:,}")
    table.add_row("Cache Read", f"{device['cache_read_tokens']:,}")
    table.add_row("Estimated Cost", f"${device['total_cost']:,.2f}")
    table.add_row("Active Period", f"{device['oldest_date']} → {device['newest_date']}")

    # Cache efficiency
    cache_total = device['cache_creation_tokens'] + device['cache_read_tokens']
    if cache_total > 0:
        cache_efficiency = (device['cache_read_tokens'] / cache_total * 100)
        table.add_row("Cache Efficiency", f"{cache_efficiency:.1f}%")

    return Panel(table, title="[bold]Device Details[/bold]", border_style="cyan")


def _render_device_chart(devices: list[dict]) -> Panel:
    """Render bar chart comparing devices by tokens."""
    # Find max tokens for scaling
    max_tokens = max(d['total_tokens'] for d in devices)

    # Create visualization
    lines = []
    lines.append("[bold]Token Usage by Device[/bold]\n")

    for device in devices:
        name = device['machine_name'][:20]  # Truncate long names
        tokens = device['total_tokens']
        cost = device['total_cost']

        # Calculate bar length (max 30 chars)
        if max_tokens > 0:
            bar_length = int((tokens / max_tokens) * 30)
        else:
            bar_length = 0

        # Create bar with gradient
        bar = "█" * bar_length

        # Color based on usage
        if tokens == max_tokens:
            bar_color = "red"
        elif tokens > max_tokens * 0.5:
            bar_color = "yellow"
        else:
            bar_color = "green"

        # Format line
        line = f"{name:20s} [{bar_color}]{bar:30s}[/{bar_color}] {tokens:>15,} (${cost:>8,.2f})"
        lines.append(line)

    content = "\n".join(lines)
    return Panel(content, border_style="blue")


def _render_device_table(devices: list[dict], display_period: str = "all") -> Panel:
    """
    Render device statistics table matching dashboard style.

    Args:
        devices: List of device statistics dictionaries
        display_period: Display period - "all", "monthly", or "weekly"

    Returns:
        Panel with device breakdown table
    """
    from src.models.pricing import format_cost

    if not devices:
        return Panel(
            Text("No device data available", style=DIM),
            title="[bold]Tokens by Device",
            border_style="white",
        )

    # Helper function to format numbers like dashboard
    def _format_number(num: int) -> str:
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}bn"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return f"{num:,}"

    # Helper function to create bars with device-specific color
    def _create_bar(value: int, max_value: int, color: str, width: int = 20) -> Text:
        if max_value == 0:
            return Text("░" * width, style=DIM)
        filled = int((value / max_value) * width)
        bar = Text()
        bar.append("█" * filled, style=color)
        bar.append("░" * (width - filled), style=DIM)
        return bar

    # Calculate totals
    total_tokens = sum(d['total_tokens'] for d in devices)
    total_cost = sum(d['total_cost'] for d in devices)
    max_tokens = max(d['total_tokens'] for d in devices)

    # Sort by usage (descending)
    sorted_devices = sorted(devices, key=lambda x: x['total_tokens'], reverse=True)

    # Create table (same style as model breakdown)
    table = Table(show_header=False, box=None, padding=(1, 2))
    table.add_column("Device", style="white", justify="left", width=25)
    table.add_column("Bar", justify="left")
    table.add_column("Tokens", style=ORANGE, justify="right")
    table.add_column("Percentage", style=CYAN, justify="right")
    table.add_column("Cost", style="green", justify="right", width=10)

    for idx, device in enumerate(sorted_devices):
        name = device['machine_name']
        tokens = device['total_tokens']
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Get unique color for this device
        device_color = DEVICE_COLORS[idx % len(DEVICE_COLORS)]

        # Create bar with device-specific color
        bar = _create_bar(tokens, max_tokens, device_color, width=20)

        table.add_row(
            name[:25],  # Truncate long names
            bar,
            _format_number(tokens),
            f"{percentage:.1f}%",
            format_cost(device['total_cost']),
        )

    # Add total row
    table.add_row(
        "[bold]Total",
        Text(""),
        f"[bold]{_format_number(total_tokens)}",
        "[bold]100.0%",
        f"[bold green]{format_cost(total_cost)}",
    )

    # Build title with period info
    if display_period == "all":
        title = "[bold]Tokens by Device[/bold] [dim](All Time)[/dim]"
    elif display_period == "monthly":
        from datetime import datetime
        current_month = datetime.now().strftime("%B %Y")
        title = f"[bold]Tokens by Device[/bold] [dim]({current_month})[/dim]"
    elif display_period == "weekly":
        from datetime import datetime, timedelta
        today = datetime.now().date()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        week_range = f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}"
        title = f"[bold]Tokens by Device[/bold] [dim](Week: {week_range})[/dim]"
    else:
        title = "[bold]Tokens by Device[/bold]"

    return Panel(
        table,
        title=title,
        border_style="white",
    )


def _render_device_heatmaps(devices: list[dict], week_offset: int = 0, display_period: str = "weekly") -> Panel:
    """
    Render hourly heatmap for each device.

    Shows usage distribution across:
    - 7 days (Monday to Sunday)
    - 24 hours (00:00 to 23:00)

    Color opacity represents usage intensity with percentage labels.

    Args:
        devices: List of device statistics dictionaries
        week_offset: Number of weeks to offset (0=current week, -1=last week, 1=next week)
                     Only used when display_period="weekly"
        display_period: Display period - "all", "monthly", or "weekly"

    Returns:
        Panel with heatmaps for all devices
    """
    from src.storage.snapshot_db import get_device_hourly_distribution
    from datetime import datetime, timedelta

    if not devices:
        return Panel(
            Text("No device data available", style=DIM),
            title="[bold]Hourly Distribution by Device",
            border_style="white",
        )

    # Calculate date range and title based on period
    today = datetime.now().date()

    if display_period == "all":
        date_range = "All Time"
        period_label = " [dim](All Time)[/dim]"
    elif display_period == "monthly":
        current_month = today.strftime("%B %Y")
        date_range = current_month
        period_label = f" [dim]({current_month})[/dim]"
    else:  # weekly
        days_since_monday = today.weekday()
        current_week_monday = today - timedelta(days=days_since_monday)
        target_week_monday = current_week_monday + timedelta(weeks=week_offset)
        target_week_sunday = target_week_monday + timedelta(days=6)
        date_range = f"{target_week_monday.strftime('%m/%d')} - {target_week_sunday.strftime('%m/%d')}"

        if week_offset == 0:
            period_label = f" ({date_range}) [dim]← Current Week →[/dim]"
        elif week_offset < 0:
            period_label = f" ({date_range}) [dim]← {abs(week_offset)} week(s) ago →[/dim]"
        else:
            period_label = f" ({date_range}) [dim]← {week_offset} week(s) ahead →[/dim]"

    # Sort devices by usage (same order as table)
    sorted_devices = sorted(devices, key=lambda x: x['total_tokens'], reverse=True)

    # Create heatmap tables for each device
    heatmap_tables = []

    for idx, device in enumerate(sorted_devices):
        device_name = device['machine_name']
        device_color = DEVICE_COLORS[idx % len(DEVICE_COLORS)]

        # Get hourly distribution for this device with period parameter
        hourly_data = get_device_hourly_distribution(device_name, week_offset=week_offset, period=display_period)

        # Create heatmap table
        heatmap_table = _create_weekly_heatmap(device_name, hourly_data, device_color)
        heatmap_tables.append(heatmap_table)

    # Add color legend
    legend = _create_heatmap_legend()

    # Combine all tables with legend
    from rich.console import Group
    sections = []
    for table in heatmap_tables:
        sections.append(table)
        sections.append(Text())  # Blank line between tables
    sections.append(legend)

    # Build title
    title = f"[bold]Weekly Hourly Distribution by Device[/bold]{period_label}"

    return Panel(
        Group(*sections),
        title=title,
        border_style="white",
        expand=True,
    )


def _create_weekly_heatmap(device_name: str, hourly_data: dict, color: str) -> Table:
    """
    Create a weekly hourly heatmap table for a single device.

    Args:
        device_name: Name of the device
        hourly_data: Dict with (day, hour) -> token_count
        color: Device-specific color

    Returns:
        Table object with heatmap visualization
    """
    # Days of week
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Find max value for normalization
    max_value = max(hourly_data.values()) if hourly_data else 1

    # Create table with device name as title
    table = Table(
        show_header=True,
        box=None,
        padding=(0, 0),
        title=f"[bold white]{device_name}",
        title_justify="left",
    )

    # Add day column
    table.add_column("", style="cyan", width=4, justify="right")

    # Add hour columns (0-23)
    for hour in range(24):
        table.add_column(f"{hour:02d}", style=DIM, width=3, justify="center")

    # Render each day as a row
    for day_idx, day_name in enumerate(days):
        row_cells = [day_name]

        for hour in range(24):
            key = (day_idx, hour)
            value = hourly_data.get(key, 0)

            # Calculate opacity (0-100%, normalize to 5 steps)
            if max_value > 0:
                opacity_raw = (value / max_value) * 100  # 0.0 ~ 100.0
                # Normalize to 5 steps: 0%, 20%, 40%, 60%, 80%, 100%
                if opacity_raw == 0:
                    opacity_percent = 0
                elif opacity_raw <= 20:
                    opacity_percent = 20
                elif opacity_raw <= 40:
                    opacity_percent = 40
                elif opacity_raw <= 60:
                    opacity_percent = 60
                elif opacity_raw <= 80:
                    opacity_percent = 80
                else:
                    opacity_percent = 100
            else:
                opacity_percent = 0

            # Create cell with background color based on opacity
            if opacity_percent == 0:
                # No usage - dark background
                cell_text = " "
                cell_style = "on grey15"
            else:
                # Show only background color, no text
                cell_text = " "

                # Calculate color with opacity (blend with background)
                # Parse hex color (e.g., "#ff8800" -> (255, 136, 0))
                hex_color = color.lstrip('#')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)

                # Blend with dark background (grey15 ≈ rgb(38,38,38))
                # Low usage → closer to bg_val (darker)
                # High usage → closer to original color (brighter)
                bg_val = 38

                # Use normalized opacity: 10%, 20%, ..., 100%
                # For heatmap visualization: higher opacity = brighter color
                opacity_factor = opacity_percent / 100.0

                # Calculate blended color
                # Formula: bg + (color - bg) * opacity
                # When opacity=0.1: mostly background (dark)
                # When opacity=1.0: full color (bright)
                blended_r = int(bg_val + (r - bg_val) * opacity_factor)
                blended_g = int(bg_val + (g - bg_val) * opacity_factor)
                blended_b = int(bg_val + (b - bg_val) * opacity_factor)

                blended_color = f"#{blended_r:02x}{blended_g:02x}{blended_b:02x}"

                # Text color based on opacity (5 steps)
                if opacity_percent <= 40:
                    text_color = "white"  # Bright text for low-medium usage
                else:
                    text_color = "white"  # White text for all levels

                cell_style = f"{text_color} on {blended_color}"

            row_cells.append(Text(cell_text, style=cell_style))

        table.add_row(*row_cells)

    return table


def _create_heatmap_legend() -> Text:
    """
    Create a legend showing color opacity levels and their meanings.

    Returns:
        Text object with legend
    """
    legend = Text()

    legend.append("Legend: ", style="bold white")
    legend.append("▪ 0%  ", style=DIM)
    legend.append("▪ <25%  ", style="dim")
    legend.append("▪ 25-50%  ", style="white")
    legend.append("▪ 50-75%  ", style="white")
    legend.append("▪ 75-100%", style="bold white")

    return legend


#endregion
