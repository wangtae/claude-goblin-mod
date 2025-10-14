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
#endregion


#region Functions

def render_device_statistics(console: Console) -> None:
    """
    Render device statistics consistent with other dashboard views.

    Displays:
    - Device comparison table with bars
    - Detailed statistics per device
    - Cost breakdown by device

    Args:
        console: Rich console for output
    """
    device_stats = get_device_statistics()

    if not device_stats:
        console.print("[yellow]No device data available yet.[/yellow]")
        console.print("[dim]Run 'ccu usage' to start tracking device-specific statistics.[/dim]")
        return

    # Render device table (same style as model breakdown)
    device_panel = _render_device_table(device_stats)
    console.print(device_panel, end="")


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


def _render_device_table(devices: list[dict]) -> Panel:
    """
    Render device statistics table matching dashboard style.

    Args:
        devices: List of device statistics dictionaries

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

    # Helper function to create bars like dashboard
    def _create_bar(value: int, max_value: int, width: int = 20) -> Text:
        if max_value == 0:
            return Text("░" * width, style=DIM)
        filled = int((value / max_value) * width)
        bar = Text()
        bar.append("█" * filled, style=ORANGE)
        bar.append("░" * (width - filled), style=DIM)
        return bar

    # Calculate totals
    total_tokens = sum(d['total_tokens'] for d in devices)
    total_cost = sum(d['total_cost'] for d in devices)
    max_tokens = max(d['total_tokens'] for d in devices)

    # Sort by usage (descending)
    sorted_devices = sorted(devices, key=lambda x: x['total_tokens'], reverse=True)

    # Create table (same style as model breakdown)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Device", style="white", justify="left", width=25)
    table.add_column("Bar", justify="left")
    table.add_column("Tokens", style=ORANGE, justify="right")
    table.add_column("Percentage", style=CYAN, justify="right")
    table.add_column("Cost", style="green", justify="right", width=10)

    for device in sorted_devices:
        name = device['machine_name']
        tokens = device['total_tokens']
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Create bar
        bar = _create_bar(tokens, max_tokens, width=20)

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

    return Panel(
        table,
        title="[bold]Tokens by Device",
        border_style="white",
    )


#endregion
