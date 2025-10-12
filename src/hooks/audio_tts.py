#region Imports
import json
import subprocess
import sys
import platform
from pathlib import Path

from rich.console import Console
#endregion


#region Functions


def setup(console: Console, settings: dict, settings_path: Path) -> None:
    """
    Set up the audio TTS notification hook.

    Uses headless Claude Code to summarize permission requests and speaks them
    using the system's text-to-speech engine (macOS 'say' command).

    Args:
        console: Rich console for output
        settings: Settings dictionary to modify
        settings_path: Path to settings.json file
    """
    # Check if macOS (currently only supports macOS 'say' command)
    system = platform.system()
    if system != "Darwin":
        console.print("[red]Error: Audio TTS hook is currently only supported on macOS[/red]")
        console.print("[yellow]Requires the 'say' command which is macOS-specific[/yellow]")
        return

    # Check if claude command is available
    try:
        result = subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            console.print("[red]Error: 'claude' command not found in PATH[/red]")
            console.print("[yellow]Make sure Claude Code CLI is installed and accessible[/yellow]")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("[red]Error: Could not verify 'claude' command availability[/red]")
        return

    console.print("[bold cyan]Setting up Audio TTS Hook[/bold cyan]\n")
    console.print("[dim]This hook uses Claude Code to summarize permission requests and speaks them aloud.[/dim]\n")

    # Get path to the TTS hook script
    hook_script = Path(__file__).parent / "scripts" / "audio_tts_hook.sh"

    # Create the hook script if it doesn't exist
    hook_script.parent.mkdir(parents=True, exist_ok=True)

    # Write the hook script
    hook_script_content = """#!/bin/bash
# Audio TTS Hook for Claude Code
# Reads notification JSON from stdin and speaks a summary using macOS 'say'

# Read JSON from stdin
json_input=$(cat)

# Extract the message content from the JSON
# This assumes the notification JSON has a structure like {"message": "..."}
# Adjust parsing based on actual hook JSON format
message=$(echo "$json_input" | python3 -c "
import sys
import json
try:
    data = json.load(sys.stdin)
    # Try different possible fields for the message
    msg = data.get('message') or data.get('text') or data.get('content') or str(data)
    print(msg)
except:
    print('Permission request received')
")

# Use Claude to summarize (with timeout to avoid hanging)
summary=$(timeout 3s claude -p "Summarize this Claude Code permission request in 5-10 words max, be direct: $message" 2>/dev/null | head -n 1)

# Fallback if Claude fails or times out
if [ -z "$summary" ] || [ $? -ne 0 ]; then
    summary="Claude requesting permission"
fi

# Speak the summary using macOS 'say' (run in background to avoid blocking)
echo "$summary" | say &

# Optional: Log for debugging
# echo "$(date): TTS spoke: $summary" >> ~/.claude/tts_hook.log
"""

    hook_script.write_text(hook_script_content)
    hook_script.chmod(0o755)  # Make executable

    # Initialize hook structures
    if "Notification" not in settings["hooks"]:
        settings["hooks"]["Notification"] = []

    # Remove existing TTS hooks
    notification_removed = len(settings["hooks"]["Notification"])

    settings["hooks"]["Notification"] = [
        hook for hook in settings["hooks"]["Notification"]
        if not is_hook(hook)
    ]

    notification_removed = notification_removed > len(settings["hooks"]["Notification"])

    # Add new TTS hook
    settings["hooks"]["Notification"].append({
        "hooks": [{
            "type": "command",
            "command": str(hook_script.absolute())
        }]
    })

    if notification_removed:
        console.print("[cyan]Replaced existing audio TTS notification hook[/cyan]")

    console.print(f"[green]✓ Successfully configured audio TTS notification hook[/green]")
    console.print("\n[bold]What this does:[/bold]")
    console.print("  • When Claude requests permission, it speaks a summary aloud")
    console.print("  • Uses headless Claude Code to generate concise summaries")
    console.print("  • Falls back to generic message if Claude is unavailable")
    console.print(f"\n[dim]Hook script: {hook_script}[/dim]")


def is_hook(hook) -> bool:
    """
    Check if a hook is an audio TTS notification hook.

    Args:
        hook: Hook configuration dictionary

    Returns:
        True if this is an audio TTS notification hook, False otherwise
    """
    if not isinstance(hook, dict) or "hooks" not in hook:
        return False
    for h in hook.get("hooks", []):
        cmd = h.get("command", "")
        if "audio_tts_hook.sh" in cmd:
            return True
    return False


#endregion
