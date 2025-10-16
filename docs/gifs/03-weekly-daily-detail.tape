# VHS Script: Weekly Daily Detail Demo
# Shows hourly breakdown for a specific day with message drill-down

Output ../images/03-weekly-daily-detail.gif

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

# Drill down into first day
Type "1"
Sleep 3s

# Show hourly breakdown (press 1 for first hour)
Type "1"
Sleep 3s

# Back to daily view
Escape
Sleep 2s

# Back to weekly view
Escape
Sleep 2s

# Exit
Type "q"
Sleep 1s
