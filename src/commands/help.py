#region Imports
from rich.console import Console
#endregion


#region Functions


def run(console: Console) -> None:
    """
    Display help message.

    Shows comprehensive usage information including:
    - Available commands and their flags
    - Key features of the tool
    - Data sources and storage locations
    - Recommended setup workflow

    Args:
        console: Rich console for output
    """
    help_text = """
[bold cyan]Claude Goblin Usage Tracker[/bold cyan]

Track and visualize your Claude Code usage with GitHub-style activity graphs.
Automatically saves historical snapshots to preserve data beyond the 30-day rolling window.

[bold]Usage:[/bold]
  ccu                                Show this help message
  ccu limits                         Show usage percentages (session, week, opus)
  ccu status-bar [type]              Launch macOS menu bar app (session|weekly|opus)
                                     Defaults to weekly if type not specified
  ccu usage                          Show usage stats (single shot)
  ccu usage --live                   Show usage with auto-refresh
  ccu update-usage                   Update historical database with latest data
  ccu setup-hooks <type>             Configure Claude Code hooks (usage|audio|png)
  ccu remove-hooks [type]            Remove hooks (usage|audio|png, or all if not specified)
  ccu export                         Export heatmap as PNG image (default)
                                     Use --svg for SVG format
                                     Use --open to open after export
                                     Use -o FILE to specify output path
                                     Use --year YYYY to select year (default: current)
  ccu stats                          Show historical database statistics
  ccu restore-backup                 Restore database from backup (.db.bak file)
  ccu delete-usage -f                Delete all historical data (requires --force)
  ccu help                           Show this help message

[bold]Features:[/bold]
  • GitHub-style 365-day activity heatmap
  • Token usage breakdown (input, output, cache)
  • Session and prompt counts
  • Model and project folder breakdowns
  • Live auto-refresh dashboard
  • Automatic historical data preservation
  • Claude Code hooks integration for real-time tracking

[bold]Data Sources:[/bold]
  Current (30 days): ~/.claude/projects/*.jsonl
  Historical: ~/.claude/usage/usage_history.db

[bold]Recommended Setup:[/bold]
  1. Run: ccu usage
     (View your dashboard and save initial snapshot)
  2. Optional: ccu setup-hooks usage
     (Configure automatic tracking after each Claude response)
  3. Optional: ccu setup-hooks audio
     (Play sound when Claude is ready for input)

[bold]Exit:[/bold]
  Press Ctrl+C to exit

[bold]Note:[/bold]
  Claude Code keeps a rolling 30-day window of logs. This tool automatically
  snapshots your data each time you run it, building a complete history over time.
  With hooks enabled, tracking happens automatically in the background.
"""
    console.print(help_text)


#endregion
