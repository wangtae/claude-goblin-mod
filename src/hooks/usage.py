#region Imports
from pathlib import Path

from rich.console import Console

from src.config.user_config import get_storage_mode
#endregion


#region Functions


def setup(console: Console, settings: dict, settings_path: Path) -> None:
    """
    Set up the usage tracking hook.

    Args:
        console: Rich console for output
        settings: Settings dictionary to modify
        settings_path: Path to settings.json file
    """
    # Storage mode is now fixed to "full" for data safety
    storage_mode = get_storage_mode()

    hook_command = "ccu update-usage > /dev/null 2>&1 &"

    # Check if already exists
    hook_exists = any(is_hook(hook) for hook in settings["hooks"]["Stop"])

    if hook_exists:
        console.print(f"\n[yellow]Usage tracking hook already configured![/yellow]")
        console.print(f"[cyan]Using full storage mode for data safety and integrity.[/cyan]")
        return

    # Add hook
    settings["hooks"]["Stop"].append({
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": hook_command
        }]
    })

    console.print(f"[green]✓ Successfully configured usage tracking hook (full mode)[/green]")
    console.print("\n[bold]What this does:[/bold]")
    console.print("  • Runs after each Claude response completes")
    console.print("  • Saves every individual message for detailed analytics")
    console.print("  • Prevents duplicate data with unique constraints")
    console.print("  • Fills in gaps with empty records")
    console.print("  • Runs silently in the background")


def is_hook(hook) -> bool:
    """
    Check if a hook is a usage tracking hook.

    Recognizes both old-style (--update-usage) and new-style (update-usage) commands.

    Args:
        hook: Hook configuration dictionary

    Returns:
        True if this is a usage tracking hook, False otherwise
    """
    if not isinstance(hook, dict) or "hooks" not in hook:
        return False
    for h in hook.get("hooks", []):
        command = h.get("command", "")
        # Support both old-style (--update-usage) and new-style (update-usage)
        # Also support both claude-goblin and ccu aliases
        if ("claude-goblin --update-usage" in command or "claude-goblin update-usage" in command or
            "ccu --update-usage" in command or "ccu update-usage" in command):
            return True
    return False


#endregion
