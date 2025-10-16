# VHS Script: Settings Menu Demo
# Shows configuration options and customization features

Output ../images/09-settings-menu.gif

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

# Open settings menu
Type "s"
Sleep 3s

# Navigate through settings (arrows or numbers)
Down
Sleep 1s
Down
Sleep 1s
Down
Sleep 1s
Up
Sleep 1s

# Exit settings
Escape
Sleep 1s

# Exit program
Type "q"
Sleep 1s
