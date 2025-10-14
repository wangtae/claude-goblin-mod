"""
Claude Goblin CLI - Command-line interface using typer.

Main entry point for all claude-goblin commands.
"""
from typing import Optional
import typer
from rich.console import Console

from src.commands import (
    usage,
    update_usage,
    stats,
    export,
    heatmap,
    delete_usage,
    restore_backup,
    help as help_cmd,
    limits,
    status_bar,
    config_cmd,
)
from src.hooks.manager import setup_hooks, remove_hooks


# Create typer app
app = typer.Typer(
    name="claude-goblin",
    help="Python CLI for Claude Code utilities and usage tracking/analytics",
    add_completion=False,
    no_args_is_help=True,
)

# Create console for commands
console = Console()


@app.command(name="usage")
def usage_command(
    live: bool = typer.Option(False, "--live", help="Auto-refresh dashboard every 5 seconds (polling)"),
    watch: bool = typer.Option(False, "--watch", help="Auto-refresh only when files change (efficient)"),
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
    anon: bool = typer.Option(False, "--anon", help="Anonymize project names to project-001, project-002, etc"),
):
    """
    Show usage dashboard with KPI cards and breakdowns.

    Displays comprehensive usage statistics including:
    - Total tokens, prompts, and sessions
    - Current usage limits (session, weekly, Opus)
    - Token breakdown by model
    - Token breakdown by project

    Use --watch for file-change-based auto-refresh (most efficient).
    Use --live for time-based auto-refresh every 5 seconds.
    Use --fast to skip all updates and read from database only (requires existing database).
    Use --anon to anonymize project names (ranked by usage, project-001 is highest).
    """
    usage.run(console, live=live, watch=watch, fast=fast, anon=anon)


@app.command(name="stats")
def stats_command(
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
):
    """
    Show detailed statistics and cost analysis.

    Displays comprehensive statistics including:
    - Summary: total tokens, prompts, responses, sessions, days tracked
    - Cost analysis: estimated API costs vs Max Plan costs
    - Averages: tokens per session/response, cost per session/response
    - Text analysis: prompt length, politeness markers, phrase counts
    - Usage by model: token distribution across different models

    Use --fast to skip all updates and read from database only (requires existing database).
    """
    stats.run(console, fast=fast)


@app.command(name="limits")
def limits_command():
    """
    Show current usage limits (session, week, Opus).

    Displays current usage percentages and reset times for:
    - Session limit (resets after inactivity)
    - Weekly limit for all models (resets weekly)
    - Weekly Opus limit (resets weekly)

    Note: Must be run from a trusted folder where Claude Code has been used.
    """
    limits.run(console)


@app.command(name="heatmap")
def heatmap_command(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year to display (default: current year)"),
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
):
    """
    Show GitHub-style activity heatmap in the terminal.

    Displays your Claude Code activity for the year in a color-coded calendar grid,
    using the same visual design as PNG export but rendered directly in the terminal.

    Examples:
        ccu heatmap              Show current year heatmap
        ccu heatmap -y 2024      Show 2024 heatmap
        ccu heatmap --fast       Skip data collection, use cached data
    """
    heatmap.run(console, year=year, fast=fast)


@app.command(name="export")
def export_command(
    svg: bool = typer.Option(False, "--svg", help="Export as SVG instead of PNG"),
    open_file: bool = typer.Option(False, "--open", help="Open file after export"),
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Filter by year (default: current year)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """
    Export yearly heatmap as PNG or SVG file.

    Generates a high-resolution GitHub-style activity heatmap showing your
    Claude Code usage throughout the year. By default exports as PNG for the current year.

    Use --fast to skip all updates and read from database only (requires existing database).

    Examples:
        ccu export --open                  Export current year as PNG and open it
        ccu export --svg                   Export as SVG instead
        ccu export --fast                  Export from database without updating
        ccu export -y 2024                 Export specific year
        ccu export -o ~/usage.png          Specify output path

    Tip: Use 'ccu heatmap' to view in terminal without creating a file.
    """
    # Pass parameters via sys.argv for backward compatibility with export command
    import sys
    if svg and "svg" not in sys.argv:
        sys.argv.append("svg")
    if open_file and "--open" not in sys.argv:
        sys.argv.append("--open")
    if fast and "--fast" not in sys.argv:
        sys.argv.append("--fast")
    if year is not None:
        if "--year" not in sys.argv and "-y" not in sys.argv:
            sys.argv.extend(["--year", str(year)])
    if output is not None:
        if "--output" not in sys.argv and "-o" not in sys.argv:
            sys.argv.extend(["--output", output])

    export.run(console)


@app.command(name="update-usage")
def update_usage_command():
    """
    Update historical database with latest data.

    This command:
    1. Saves current usage data from JSONL files
    2. Fills in missing days with zero-usage records
    3. Ensures complete date coverage from earliest record to today

    Useful for ensuring continuous heatmap data without gaps.
    """
    update_usage.run(console)


@app.command(name="delete-usage")
def delete_usage_command(
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
):
    """
    Delete historical usage database.

    WARNING: This will permanently delete all historical usage data!

    Requires --force flag to prevent accidental deletion.
    A backup is automatically created before deletion.

    Example:
        ccu delete-usage --force
    """
    # Pass force flag via command module's own sys.argv check for backward compatibility
    import sys
    if force and "--force" not in sys.argv:
        sys.argv.append("--force")
    delete_usage.run(console)


@app.command(name="restore-backup")
def restore_backup_command():
    """
    Restore database from backup file.

    Restores the usage history database from a backup file (.db.bak).
    Creates a safety backup of the current database before restoring.

    Expected backup location: ~/.claude/usage/usage_history.db.bak
    """
    restore_backup.run(console)


@app.command(name="status-bar")
def status_bar_command(
    limit_type: str = typer.Argument("weekly", help="Type of limit to display: session, weekly, or opus"),
):
    """
    Launch macOS menu bar app (macOS only).

    Displays "CC: XX%" in your menu bar, showing current usage percentage.
    Updates automatically every 5 minutes.

    Arguments:
        limit_type: Which limit to display (session, weekly, or opus). Defaults to weekly.

    Examples:
        ccu status-bar weekly    Show weekly usage (default)
        ccu status-bar session   Show session usage
        ccu status-bar opus      Show Opus weekly usage

    Running in background:
        nohup ccu status-bar weekly > /dev/null 2>&1 &
    """
    if limit_type not in ["session", "weekly", "opus"]:
        console.print(f"[red]Error: Invalid limit type '{limit_type}'[/red]")
        console.print("[yellow]Valid types: session, weekly, opus[/yellow]")
        raise typer.Exit(1)

    status_bar.run(console, limit_type)


@app.command(name="setup-hooks")
def setup_hooks_command(
    hook_type: Optional[str] = typer.Argument(None, help="Hook type: usage, audio, audio-tts, or png"),
):
    """
    Setup Claude Code hooks for automation.

    Available hooks:
    - usage: Auto-track usage after each Claude response
    - audio: Play sounds for completion, permission, and compaction (3 sounds)
    - audio-tts: Speak messages using TTS with hook selection (macOS only)
    - png: Auto-update usage PNG after each Claude response

    Examples:
        ccu setup-hooks usage      Enable automatic usage tracking
        ccu setup-hooks audio      Enable audio notifications (3 sounds)
        ccu setup-hooks audio-tts  Enable TTS (choose which hooks)
        ccu setup-hooks png        Enable automatic PNG exports
    """
    setup_hooks(console, hook_type)


@app.command(name="remove-hooks")
def remove_hooks_command(
    hook_type: Optional[str] = typer.Argument(None, help="Hook type to remove: usage, audio, audio-tts, png, or leave empty for all"),
):
    """
    Remove Claude Code hooks configured by this tool.

    Examples:
        ccu remove-hooks           Remove all hooks
        ccu remove-hooks usage     Remove only usage tracking hook
        ccu remove-hooks audio     Remove only audio notification hook
        ccu remove-hooks audio-tts Remove only audio TTS hook
        ccu remove-hooks png       Remove only PNG export hook
    """
    remove_hooks(console, hook_type)


@app.command(name="config")
def config_command(
    action: str = typer.Argument(..., help="Action: show, set-db-path, clear-db-path, set-machine-name, clear-machine-name"),
    value: Optional[str] = typer.Argument(None, help="Value for set actions"),
):
    """
    Manage Claude Goblin configuration.

    Actions:
        show                    Display all current settings
        set-db-path <path>      Set custom database path (e.g., /mnt/d/OneDrive/.claude-goblin/usage_history.db)
        clear-db-path           Clear custom path and use auto-detect
        set-machine-name <name> Set friendly machine name (e.g., "Home-Desktop")
        clear-machine-name      Clear custom name and use hostname

    Examples:
        ccu config show
        ccu config set-db-path /mnt/d/OneDrive/.claude-goblin/usage_history.db
        ccu config set-machine-name "Home-Desktop"
        ccu config clear-db-path
    """
    config_cmd.run(console, action, value)


@app.command(name="help", hidden=True)
def help_command():
    """
    Show detailed help message.

    Displays comprehensive usage information including:
    - Available commands and their flags
    - Key features of the tool
    - Data sources and storage locations
    - Recommended setup workflow
    """
    help_cmd.run(console)


def main() -> None:
    """
    Main CLI entry point for Claude Goblin Usage tracker.

    Loads Claude Code usage data and provides commands for viewing,
    analyzing, and exporting usage statistics.

    Usage:
        ccu --help              Show available commands
        ccu usage               Show usage dashboard
        ccu usage --live        Show dashboard with auto-refresh
        ccu stats               Show detailed statistics
        ccu export              Export yearly heatmap

    Exit:
        Press Ctrl+C to exit
    """
    app()


if __name__ == "__main__":
    main()
