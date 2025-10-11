#region Imports
import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from claude_goblin_usage.hooks import usage, audio, png
#endregion


#region Functions


def setup_hooks(console: Console, hook_type: Optional[str] = None) -> None:
    """
    Set up Claude Code hooks for automation.

    Args:
        console: Rich console for output
        hook_type: Type of hook to set up ('usage', 'audio', 'png', or None for menu)
    """
    settings_path = Path.home() / ".claude" / "settings.json"

    if hook_type is None:
        # Show menu
        console.print("[bold cyan]Available hooks to set up:[/bold cyan]\n")
        console.print("  [bold]usage[/bold]  - Auto-track usage after each response")
        console.print("  [bold]audio[/bold]  - Play sound when Claude is ready for input")
        console.print("  [bold]png[/bold]    - Auto-update usage PNG after each response\n")
        console.print("Usage: claude-goblin --setup-hooks <type>")
        console.print("Example: claude-goblin --setup-hooks usage")
        return

    console.print(f"[bold cyan]Setting up {hook_type} hook[/bold cyan]\n")

    try:
        # Read existing settings
        if settings_path.exists():
            with open(settings_path, "r") as f:
                settings = json.load(f)
        else:
            settings = {}

        # Initialize hooks structure
        if "hooks" not in settings:
            settings["hooks"] = {}

        if "Stop" not in settings["hooks"]:
            settings["hooks"]["Stop"] = []

        # Delegate to specific hook module
        if hook_type == "usage":
            usage.setup(console, settings, settings_path)
        elif hook_type == "audio":
            audio.setup(console, settings, settings_path)
        elif hook_type == "png":
            png.setup(console, settings, settings_path)
        else:
            console.print(f"[red]Unknown hook type: {hook_type}[/red]")
            console.print("Valid types: usage, audio, png")
            return

        # Write settings back
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        console.print("\n[dim]Hook location: ~/.claude/settings.json[/dim]")
        console.print(f"[dim]To remove: claude-goblin --remove-hooks {hook_type}[/dim]")

    except Exception as e:
        console.print(f"[red]Error setting up hooks: {e}[/red]")
        import traceback
        traceback.print_exc()


def remove_hooks(console: Console, hook_type: Optional[str] = None) -> None:
    """
    Remove Claude Code hooks configured by this tool.

    Args:
        console: Rich console for output
        hook_type: Type of hook to remove ('usage', 'audio', 'png', or None for all)
    """
    settings_path = Path.home() / ".claude" / "settings.json"

    if not settings_path.exists():
        console.print("[yellow]No Claude Code settings file found.[/yellow]")
        return

    console.print(f"[bold cyan]Removing hooks[/bold cyan]\n")

    try:
        # Read existing settings
        with open(settings_path, "r") as f:
            settings = json.load(f)

        if "hooks" not in settings or "Stop" not in settings["hooks"]:
            console.print("[yellow]No hooks configured.[/yellow]")
            return

        original_count = len(settings["hooks"]["Stop"])

        # Remove hooks based on type
        if hook_type == "usage":
            settings["hooks"]["Stop"] = [
                hook for hook in settings["hooks"]["Stop"]
                if not usage.is_hook(hook)
            ]
            removed_type = "usage tracking"
        elif hook_type == "audio":
            settings["hooks"]["Stop"] = [
                hook for hook in settings["hooks"]["Stop"]
                if not audio.is_hook(hook)
            ]
            removed_type = "audio notification"
        elif hook_type == "png":
            settings["hooks"]["Stop"] = [
                hook for hook in settings["hooks"]["Stop"]
                if not png.is_hook(hook)
            ]
            removed_type = "PNG auto-update"
        else:
            # Remove all our hooks
            settings["hooks"]["Stop"] = [
                hook for hook in settings["hooks"]["Stop"]
                if not (usage.is_hook(hook) or audio.is_hook(hook) or png.is_hook(hook))
            ]
            removed_type = "all claude-goblin"

        removed_count = original_count - len(settings["hooks"]["Stop"])

        if removed_count == 0:
            console.print(f"[yellow]No {removed_type} hooks found to remove.[/yellow]")
            return

        # Write settings back
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        console.print(f"[green]✓ Removed {removed_count} {removed_type} hook(s)[/green]")
        console.print(f"[dim]Settings file: ~/.claude/settings.json[/dim]")

    except Exception as e:
        console.print(f"[red]Error removing hooks: {e}[/red]")
        import traceback
        traceback.print_exc()


#endregion
