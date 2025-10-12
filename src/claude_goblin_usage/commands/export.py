#region Imports
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

from claude_goblin_usage.aggregation.daily_stats import aggregate_all
from claude_goblin_usage.config.user_config import get_tracking_mode
from claude_goblin_usage.storage.snapshot_db import load_historical_records, get_limits_data
from claude_goblin_usage.utils._system import open_file
#endregion


#region Functions


def run(console: Console) -> None:
    """
    Export the heatmap to PNG or SVG.

    Exports a GitHub-style activity heatmap as an image file.
    Supports PNG (default) and SVG formats, with optional file opening.

    Args:
        console: Rich console for output

    Flags:
        svg: Export as SVG instead of PNG
        --open: Open file after export
        --year YYYY or -y YYYY: Filter by year (default: current year)
        -o FILE or --output FILE: Specify output file path
    """
    from claude_goblin_usage.visualization.export import export_heatmap_svg, export_heatmap_png

    # Determine format from arguments (PNG is default)
    format_type = "png"
    if "svg" in sys.argv:
        format_type = "svg"

    # Check for --open flag
    should_open = "--open" in sys.argv

    # Parse year filter (--year YYYY)
    year_filter = None
    for i, arg in enumerate(sys.argv):
        if arg in ["--year", "-y"] and i + 1 < len(sys.argv):
            try:
                year_filter = int(sys.argv[i + 1])
            except ValueError:
                console.print(f"[red]Invalid year: {sys.argv[i + 1]}[/red]")
                return
            break

    # Default to current year if not specified
    if year_filter is None:
        year_filter = datetime.now().year

    # Determine output path
    output_file = None
    custom_output = False
    for i, arg in enumerate(sys.argv):
        if arg in ["-o", "--output"] and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            custom_output = True
            break

    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"claude-usage-{timestamp}.{format_type}"

    # Use absolute path, or resolve based on whether -o flag was used
    output_path = Path(output_file)
    if not output_path.is_absolute():
        if custom_output:
            # If -o flag was used, resolve relative to current working directory
            output_path = Path.cwd() / output_path
        else:
            # Default location: ~/.claude/usage/
            default_dir = Path.home() / ".claude" / "usage"
            default_dir.mkdir(parents=True, exist_ok=True)
            output_path = default_dir / output_file

    try:
        console.print(f"[cyan]Loading usage data for {year_filter}...[/cyan]")

        # Read from database only (single source of truth)
        all_records = load_historical_records()

        if not all_records:
            console.print("[yellow]No usage data found in database. Run --usage to ingest data first.[/yellow]")
            return

        stats = aggregate_all(all_records)

        # Load limits data and tracking mode
        limits_data = get_limits_data()
        tracking_mode = get_tracking_mode()

        console.print(f"[cyan]Exporting to {format_type.upper()}...[/cyan]")

        if format_type == "png":
            export_heatmap_png(stats, output_path, limits_data=limits_data, year=year_filter, tracking_mode=tracking_mode)
        else:
            export_heatmap_svg(stats, output_path, year=year_filter)

        console.print(f"[green]✓ Exported to: {output_path.absolute()}[/green]")

        # Open the file if --open flag is present
        if should_open:
            console.print(f"[cyan]Opening {format_type.upper()}...[/cyan]")
            open_file(output_path)

    except ImportError as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:
        console.print(f"[red]Error exporting: {e}[/red]")
        import traceback
        traceback.print_exc()


#endregion
