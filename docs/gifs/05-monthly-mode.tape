# VHS Script: Monthly Mode Demo
# Shows full month overview with daily bars and project rankings

Output ../images/05-monthly-mode.gif

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

# Switch to monthly mode
Type "m"
Sleep 3s

# Navigate previous/next month
Type "<"
Sleep 2s
Type ">"
Sleep 2s
Type ">"
Sleep 2s

# Exit
Type "q"
Sleep 1s
