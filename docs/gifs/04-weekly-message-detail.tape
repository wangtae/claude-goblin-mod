# VHS Script: Message Detail Demo
# Shows individual message metadata with token counts and cost

Output ../images/04-weekly-message-detail.gif

# Terminal settings
Set FontSize 13
Set Width 1200
Set Height 700
Set Theme "Dracula"
Set TypingSpeed 0.05s

# Start the program
Type "ccu"
Enter
Sleep 4s

# Navigate to weekly → daily → hourly message detail
Type "w"
Sleep 2s
Type "1"
Sleep 2s
Type "1"
Sleep 3s

# Scroll through messages (if needed)
Sleep 2s

# Back to daily
Escape
Sleep 1s

# Back to weekly
Escape
Sleep 1s

# Exit
Type "q"
Sleep 1s
