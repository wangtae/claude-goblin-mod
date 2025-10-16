# VHS Script: Weekly Mode Demo
# Shows 7-day overview with daily breakdown and drill-down navigation

Output ../images/02-weekly-mode.gif

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

# Switch to weekly mode
Type "w"
Sleep 3s

# Navigate to previous/next week
Type "<"
Sleep 2s
Type ">"
Sleep 2s

# Drill down into first day (press 1)
Type "1"
Sleep 3s

# Back to weekly view
Escape
Sleep 2s

# Exit
Type "q"
Sleep 1s
