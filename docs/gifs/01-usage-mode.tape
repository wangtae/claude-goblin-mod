# VHS Script: Usage Mode Demo
# Shows current session/week/opus limits with real-time data

Output ../images/01-usage-mode.gif

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

# Switch to usage mode (if not already there)
Type "u"
Sleep 3s

# Show tab functionality - cycle through display modes
Type@0.5s "Pressing Tab to cycle display modes..."
Sleep 1s
Tab
Sleep 2s
Tab
Sleep 2s
Tab
Sleep 2s
Tab
Sleep 2s

# Back to usage mode
Type "u"
Sleep 2s

# Exit
Type "q"
Sleep 1s
