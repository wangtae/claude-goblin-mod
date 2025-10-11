#region Imports
import sys

from rich.console import Console

from claude_goblin_usage.commands import (
    usage,
    update_usage,
    stats,
    export,
    delete_usage,
    restore_backup,
    help,
    limits,
)
from claude_goblin_usage.hooks.manager import setup_hooks, remove_hooks
#endregion


#region Functions


def main() -> None:
    """
    Main CLI entry point for Claude Goblin Usage tracker.

    Loads Claude Code usage data and displays a live-updating dashboard
    with GitHub-style activity graph and statistics.

    Usage:
        claude-goblin              # Show help
        claude-goblin --usage      # Show usage stats (single shot)
        claude-goblin --usage --live  # Show usage with auto-refresh
        claude-goblin --help       # Show help message

    Exit:
        Press Ctrl+C to exit
    """
    console = Console()

    # Parse command line arguments
    show_usage_flag = "--usage" in sys.argv
    show_help_flag = "--help" in sys.argv or "-h" in sys.argv
    show_limits_flag = "--limits" in sys.argv
    show_stats_flag = "--stats" in sys.argv
    setup_hooks_flag = "--setup" in sys.argv or "--setup-hooks" in sys.argv
    remove_hooks_flag = "--remove-hooks" in sys.argv
    update_usage_flag = "--update-usage" in sys.argv
    export_flag = "--export" in sys.argv
    delete_usage_flag = "--delete-usage" in sys.argv
    restore_backup_flag = "--restore-backup" in sys.argv

    # Dispatch to appropriate command handler
    if show_help_flag:
        help.run(console)
        return

    if show_limits_flag:
        limits.run(console)
        return

    if show_stats_flag:
        stats.run(console)
        return

    if setup_hooks_flag:
        hook_type = None
        if "usage" in sys.argv:
            hook_type = "usage"
        elif "audio" in sys.argv or "sound" in sys.argv:
            hook_type = "audio"
        elif "png" in sys.argv:
            hook_type = "png"
        setup_hooks(console, hook_type)
        return

    if remove_hooks_flag:
        hook_type = None
        if "usage" in sys.argv:
            hook_type = "usage"
        elif "audio" in sys.argv or "sound" in sys.argv:
            hook_type = "audio"
        elif "png" in sys.argv:
            hook_type = "png"
        remove_hooks(console, hook_type)
        return

    if update_usage_flag:
        update_usage.run(console)
        return

    if export_flag:
        export.run(console)
        return

    if delete_usage_flag:
        delete_usage.run(console)
        return

    if restore_backup_flag:
        restore_backup.run(console)
        return

    if show_usage_flag:
        usage.run(console)
        return

    # Default behavior (no command specified) - show help
    help.run(console)


#endregion
