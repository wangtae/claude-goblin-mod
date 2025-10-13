#!/bin/bash
# Audio TTS Hook for Claude Code
# Reads hook JSON from stdin and speaks it using macOS 'say'

# Read JSON from stdin
json_input=$(cat)

# Extract the message content from the JSON
# Try different fields depending on hook type
message=$(echo "$json_input" | python3 -c "
import sys
import json
try:
    data = json.load(sys.stdin)
    hook_type = data.get('hook_event_name', '')

    # Get appropriate message based on hook type
    if hook_type == 'Notification':
        msg = data.get('message', 'Claude requesting permission')
    elif hook_type == 'Stop':
        msg = 'Claude finished responding'
    elif hook_type == 'PreCompact':
        trigger = data.get('trigger', 'unknown')
        if trigger == 'auto':
            msg = 'Auto compacting conversation'
        else:
            msg = 'Manually compacting conversation'
    else:
        msg = data.get('message', 'Claude event')

    print(msg)
except:
    print('Claude event')
")

# Speak the message using macOS 'say' with selected voice (run in background to avoid blocking)
echo "$message" | say -v Samantha &

# Optional: Log for debugging
# echo "$(date): TTS spoke: $message" >> ~/.claude/tts_hook.log
