#!/bin/bash

# Generate all VHS GIF recordings for Claude Goblin
# Usage: cd docs/gifs && ./generate-all.sh

set -e  # Exit on error

echo "🎬 Generating all GIF demos for Claude Goblin..."
echo ""

# Array of all tape scripts
SCRIPTS=(
  "00-vscode-integration.tape"
  "01-usage-mode.tape"
  "02-weekly-mode.tape"
  "03-weekly-daily-detail.tape"
  "04-weekly-message-detail.tape"
  "05-monthly-mode.tape"
  "06-yearly-mode.tape"
  "07-heatmap-mode.tape"
  "08-devices-mode.tape"
  "09-settings-menu.tape"
)

# Check if vhs is installed
if ! command -v vhs &> /dev/null; then
  echo "❌ Error: vhs is not installed."
  echo ""
  echo "Install with:"
  echo "  brew install vhs           # macOS"
  echo "  go install github.com/charmbracelet/vhs@latest  # Linux"
  exit 1
fi

# Check if ccu is available
if ! command -v ccu &> /dev/null; then
  echo "⚠️  Warning: ccu command not found in PATH"
  echo "Make sure Claude Goblin is installed before running VHS scripts."
  echo ""
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Generate each GIF
TOTAL=${#SCRIPTS[@]}
CURRENT=0

for script in "${SCRIPTS[@]}"; do
  CURRENT=$((CURRENT + 1))
  echo "[$CURRENT/$TOTAL] Generating ${script%.tape}.gif..."

  vhs "$script"

  if [ $? -eq 0 ]; then
    echo "✅ Generated ${script%.tape}.gif"
  else
    echo "❌ Failed to generate ${script%.tape}.gif"
  fi

  echo ""
done

echo "🎉 All GIFs generated successfully!"
echo ""
echo "Output location: docs/images/"
echo ""
echo "Next steps:"
echo "  1. Review generated GIFs in docs/images/"
echo "  2. Optimize file sizes if needed:"
echo "     cd ../images && for f in *.gif; do gifsicle -O3 --colors 256 \"\$f\" -o \"\${f%.gif}-opt.gif\"; done"
echo "  3. Update README.md to use GIFs instead of PNGs"
