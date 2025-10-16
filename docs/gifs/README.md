# VHS Recording Scripts for Claude Goblin

This directory contains VHS (Video Hacking Software) scripts to generate GIF demos for the README.

## Prerequisites

Install VHS:
```bash
# macOS
brew install vhs

# Linux (requires Go)
go install github.com/charmbracelet/vhs@latest
```

## Usage

### Generate All GIFs

Run from project root:
```bash
cd docs/gifs
./generate-all.sh
```

### Generate Individual GIF

```bash
cd docs/gifs
vhs 01-usage-mode.tape
```

This will create `docs/images/01-usage-mode.gif`.

## Available Scripts

| Script | Output | Description |
|--------|--------|-------------|
| `00-vscode-integration.tape` | `00-vscode-integration.gif` | VSCode terminal integration |
| `01-usage-mode.tape` | `01-usage-mode.gif` | Current limits and Tab cycling |
| `02-weekly-mode.tape` | `02-weekly-mode.gif` | 7-day overview with navigation |
| `03-weekly-daily-detail.tape` | `03-weekly-daily-detail.gif` | Hourly breakdown for specific day |
| `04-weekly-message-detail.tape` | `04-weekly-message-detail.gif` | Individual message metadata |
| `05-monthly-mode.tape` | `05-monthly-mode.gif` | Monthly view with project rankings |
| `06-yearly-mode.tape` | `06-yearly-mode.gif` | Annual overview |
| `07-heatmap-mode.tape` | `07-heatmap-mode.gif` | Activity heatmap visualization |
| `08-devices-mode.tape` | `08-devices-mode.gif` | Multi-PC statistics |
| `09-settings-menu.tape` | `09-settings-menu.gif` | Configuration menu |

## Customization

Edit `.tape` files to adjust:
- **Timing**: Change `Sleep` durations
- **Size**: Adjust `Set Width` and `Set Height`
- **Theme**: Change `Set Theme` (e.g., "Dracula", "Monokai", "Nord")
- **Speed**: Adjust `Set PlaybackSpeed` and `Set TypingSpeed`

Example:
```tape
Set FontSize 14        # Larger font
Set Width 1400         # Wider viewport
Set Theme "Nord"       # Different color scheme
Sleep 5s              # Longer pause
```

## File Size Optimization

If GIFs are too large, optimize them:

```bash
# Install gifsicle
brew install gifsicle

# Optimize all GIFs
cd docs/images
for f in *.gif; do
  gifsicle -O3 --colors 256 "$f" -o "${f%.gif}-optimized.gif"
done
```

## Troubleshooting

**VHS command not found:**
```bash
# Add Go bin to PATH
export PATH="$HOME/go/bin:$PATH"
source ~/.bashrc
```

**Recording shows wrong content:**
- Make sure `ccu` is installed and in PATH
- Ensure database has data before recording
- Adjust `Sleep` durations if program loads slowly

**GIF quality is poor:**
- Increase `Set FrameRate` (default: 30)
- Increase `Set FontSize` (default: 13)
- Increase resolution (`Set Width` / `Set Height`)

## Notes

- All GIFs are output to `docs/images/` to match existing screenshots
- Scripts use relative paths (`../images/`) to work from `docs/gifs/`
- Dracula theme is used for consistency across all recordings
- Each script is self-contained and can be run independently
