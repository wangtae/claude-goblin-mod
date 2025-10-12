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
  claude-goblin                      Show this help message
  claude-goblin limits               Show usage percentages (session, week, opus)
  claude-goblin status-bar [type]    Launch macOS menu bar app (session|weekly|opus)
                                     Defaults to weekly if type not specified
  claude-goblin usage                Show usage stats (single shot)
  claude-goblin usage --live         Show usage with auto-refresh
  claude-goblin update-usage         Update historical database with latest data
  claude-goblin setup-hooks <type>   Configure Claude Code hooks (usage|audio|png)
  claude-goblin remove-hooks [type]  Remove hooks (usage|audio|png, or all if not specified)
  claude-goblin export               Export heatmap as PNG image (default)
                                     Use --svg for SVG format
                                     Use --open to open after export
                                     Use -o FILE to specify output path
                                     Use --year YYYY to select year (default: current)
  claude-goblin stats                Show historical database statistics
  claude-goblin restore-backup       Restore database from backup (.db.bak file)
  claude-goblin delete-usage -f      Delete all historical data (requires --force)
  claude-goblin help                 Show this help message

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
  1. Run: claude-goblin usage
     (View your dashboard and save initial snapshot)
  2. Optional: claude-goblin setup-hooks usage
     (Configure automatic tracking after each Claude response)
  3. Optional: claude-goblin setup-hooks audio
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
