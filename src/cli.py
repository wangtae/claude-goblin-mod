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
    reset_db,
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
    no_args_is_help=False,  # Changed to False to allow callback
)

# Create console for commands
console = Console()


@app.callback(invoke_without_command=True)
def default_callback(ctx: typer.Context):
    """
    Default callback when no command is provided.
    Runs 'usage' command by default.
    """
    if ctx.invoked_subcommand is None:
        # No command provided, run usage command
        usage.run(console, refresh=None, anon=False)


@app.command(name="usage", hidden=True)
def usage_command(
    refresh: Optional[int] = typer.Option(None, "--refresh", help="Refresh interval in seconds (e.g., --refresh=30). Watches file changes if not specified."),
    anon: bool = typer.Option(False, "--anon", help="Anonymize project names to project-001, project-002, etc"),
):
    """Show interactive usage dashboard (hidden, use 'ccu' instead)."""
    usage.run(console, refresh=refresh, anon=anon)


@app.command(name="stats", hidden=True)
def stats_command(
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
):
    """Show detailed statistics and cost analysis (hidden)."""
    stats.run(console, fast=fast)


@app.command(name="limits", hidden=True)
def limits_command():
    """Show current usage limits (hidden)."""
    limits.run(console)


@app.command(name="heatmap", hidden=True)
def heatmap_command(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year to display (default: current year)"),
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
):
    """Show GitHub-style activity heatmap in the terminal (hidden)."""
    heatmap.run(console, year=year, fast=fast)


@app.command(name="export", hidden=True)
def export_command(
    svg: bool = typer.Option(False, "--svg", help="Export as SVG instead of PNG"),
    open_file: bool = typer.Option(False, "--open", help="Open file after export"),
    fast: bool = typer.Option(False, "--fast", help="Skip updates, read from database only (faster)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Filter by year (default: current year)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export yearly heatmap as PNG or SVG file (hidden)."""
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


@app.command(name="update-usage", hidden=True)
def update_usage_command():
    """Update historical database with latest data (hidden)."""
    update_usage.run(console)


@app.command(name="delete-usage", hidden=True)
def delete_usage_command(
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
):
    """Delete historical usage database (hidden)."""
    # Pass force flag via command module's own sys.argv check for backward compatibility
    import sys
    if force and "--force" not in sys.argv:
        sys.argv.append("--force")
    delete_usage.run(console)


@app.command(name="restore-backup", hidden=True)
def restore_backup_command():
    """Restore database from backup file (hidden)."""
    restore_backup.run(console)


@app.command(name="reset-db", hidden=True)
def reset_db_command(
    force: bool = typer.Option(False, "--force", help="Force reset without confirmation"),
    keep_backups: bool = typer.Option(False, "--keep-backups", help="Keep backup files"),
):
    """Reset database (delete and start fresh) (hidden)."""
    import sys
    if force and "--force" not in sys.argv:
        sys.argv.append("--force")
    if keep_backups and "--keep-backups" not in sys.argv:
        sys.argv.append("--keep-backups")
    reset_db.run(console)


@app.command(name="status-bar", hidden=True)
def status_bar_command(
    limit_type: str = typer.Argument("weekly", help="Type of limit to display: session, weekly, or opus"),
):
    """Launch macOS menu bar app (hidden)."""
    if limit_type not in ["session", "weekly", "opus"]:
        console.print(f"[red]Error: Invalid limit type '{limit_type}'[/red]")
        console.print("[yellow]Valid types: session, weekly, opus[/yellow]")
        raise typer.Exit(1)

    status_bar.run(console, limit_type)


@app.command(name="setup-hooks", hidden=True)
def setup_hooks_command(
    hook_type: Optional[str] = typer.Argument(None, help="Hook type: usage, audio, audio-tts, or png"),
):
    """Setup Claude Code hooks for automation (hidden)."""
    setup_hooks(console, hook_type)


@app.command(name="remove-hooks", hidden=True)
def remove_hooks_command(
    hook_type: Optional[str] = typer.Argument(None, help="Hook type to remove: usage, audio, audio-tts, png, or leave empty for all"),
):
    """Remove Claude Code hooks configured by this tool (hidden)."""
    remove_hooks(console, hook_type)


@app.command(name="config", hidden=True)
def config_command(
    action: str = typer.Argument(..., help="Action: show, set-db-path, clear-db-path, set-machine-name, clear-machine-name"),
    value: Optional[str] = typer.Argument(None, help="Value for set actions"),
):
    """Manage Claude Goblin configuration (hidden)."""
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
        ccu usage               Interactive dashboard with file watching
        ccu usage --refresh=30  Update every 30 seconds
        ccu stats               Show detailed statistics
        ccu export              Export yearly heatmap

    Exit:
        Press Ctrl+C or [q] to exit
    """
    app()


if __name__ == "__main__":
    main()
