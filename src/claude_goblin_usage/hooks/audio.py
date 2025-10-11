#region Imports
import platform
from pathlib import Path
from typing import Optional

from rich.console import Console

from claude_goblin_usage.utils._system import get_sound_command
#endregion


#region Functions


def setup(console: Console, settings: dict, settings_path: Path) -> None:
    """
    Set up the audio notification hook.

    Args:
        console: Rich console for output
        settings: Settings dictionary to modify
        settings_path: Path to settings.json file
    """
    # Offer sound choices
    console.print("[bold cyan]Choose a notification sound:[/bold cyan]\n")

    system = platform.system()
    if system == "Darwin":
        sounds = [
            ("Glass", "Clear glass sound (recommended)"),
            ("Ping", "Short ping sound"),
            ("Purr", "Soft purr sound"),
            ("Tink", "Quick tink sound"),
            ("Pop", "Pop sound"),
        ]
    elif system == "Windows":
        sounds = [
            ("Windows Notify", "Default notification"),
            ("Windows Ding", "Ding sound"),
            ("chimes", "Chimes sound"),
            ("chord", "Chord sound"),
            ("notify", "System notify"),
        ]
    else:  # Linux
        sounds = [
            ("complete", "Completion sound"),
            ("bell", "Bell sound"),
            ("message", "Message sound"),
            ("dialog-information", "Info dialog"),
            ("service-login", "Login sound"),
        ]

    for idx, (name, desc) in enumerate(sounds, 1):
        console.print(f"  {idx}. {name} - {desc}")

    console.print("\n[dim]Enter number (1-5) or press Enter for default:[/dim] ", end="")

    # Read user input
    try:
        user_input = input().strip()
        if user_input == "":
            # Default to first option
            selected_sound = sounds[0][0]
        elif user_input.isdigit() and 1 <= int(user_input) <= 5:
            # Valid number selection
            selected_sound = sounds[int(user_input) - 1][0]
        else:
            console.print("[yellow]Invalid selection, using default[/yellow]")
            selected_sound = sounds[0][0]
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled[/yellow]")
        return

    hook_command = get_sound_command(selected_sound)

    if not hook_command:
        console.print("[red]Audio hooks not supported on this platform[/red]")
        return

    # Check for existing audio hooks and remove them
    original_count = len(settings["hooks"]["Stop"])

    settings["hooks"]["Stop"] = [
        hook for hook in settings["hooks"]["Stop"]
        if not is_hook(hook)
    ]
    audio_hook_removed = len(settings["hooks"]["Stop"]) < original_count

    # Add new hook
    settings["hooks"]["Stop"].append({
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": hook_command
        }]
    })

    if audio_hook_removed:
        console.print("[cyan]Replaced existing audio notification hook[/cyan]")

    console.print(f"[green]✓ Successfully configured audio notification hook ({selected_sound})[/green]")
    console.print("\n[bold]What this does:[/bold]")
    console.print("  • Plays a sound when Claude finishes responding")
    console.print(f"  • Sound: {selected_sound}")
    console.print("  • Runs in the background")


def is_hook(hook) -> bool:
    """
    Check if a hook is an audio notification hook.

    Args:
        hook: Hook configuration dictionary

    Returns:
        True if this is an audio notification hook, False otherwise
    """
    if not isinstance(hook, dict) or "hooks" not in hook:
        return False
    for h in hook.get("hooks", []):
        cmd = h.get("command", "")
        if any(audio_cmd in cmd for audio_cmd in ["afplay", "powershell", "paplay", "aplay"]):
            return True
    return False


#endregion
