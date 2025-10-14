# Claude Goblin Mod - Installation Guide

This is a forked version of [claude-goblin](https://github.com/data-goblin/claude-goblin) with additional multi-PC support features.

## Installation Options

### Option 1: Run from Source (Recommended for Development)

Since this is a forked/modified version, you can run it directly from source without installing:

```bash
# Clone or navigate to your fork
cd /home/wangt/projects/personal/claude-goblin/claude-goblin-mod

# Install dependencies (one-time setup)
pip install rich typer

# Optional: Install export dependencies
pip install pillow cairosvg

# Run commands directly
python3 -m src.cli --help
python3 -m src.cli usage
python3 -m src.cli config show
```

### Option 2: Local Installation (Editable Mode)

Install your modified version locally:

```bash
cd /home/wangt/projects/personal/claude-goblin/claude-goblin-mod

# Install in editable mode
pip install -e .

# Now you can use 'ccu' or 'claude-goblin' commands
ccu --help
ccu usage
ccu config show
```

**Note**: This will install your modified version, not the original from PyPI.

### Option 3: Create Alias

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias ccu='python3 -m src.cli'
```

Then reload:
```bash
source ~/.bashrc
ccu --help
```

## Dependencies

### Required
- Python >= 3.10
- rich >= 13.7.0
- typer >= 0.9.0

### Optional (for export features)
- pillow >= 10.0.0
- cairosvg >= 2.7.0

### Platform-Specific
- rumps >= 0.4.0 (macOS only, for status bar)

## Verifying Installation

Test that everything works:

```bash
# From source (Option 1)
cd /home/wangt/projects/personal/claude-goblin/claude-goblin-mod
python3 -m src.cli config show

# From local install (Option 2)
ccu config show

# From alias (Option 3)
ccu config show
```

Expected output:
```
Claude Goblin Configuration

Database Settings
  DB Path (auto-detect): /mnt/d/OneDrive/.claude-goblin/usage_history.db
  (OneDrive sync enabled)

Machine Settings
  Machine Name (auto): desktop-wsl

Tracking Settings
  Storage Mode: aggregate
  Tracking Mode: both
  Plan Type: max_20x
```

## Differences from Original

This forked version includes:

1. **Automatic OneDrive Detection**
   - Detects OneDrive on multiple drives (C:, D:, E:, F:)
   - Supports custom OneDrive locations
   - Auto-creates `.claude-goblin` folder in OneDrive

2. **Configuration Management**
   - `ccu config` command for managing settings
   - Custom database path support
   - Custom machine name support

3. **Multi-PC Support** (Planned)
   - Per-machine statistics
   - Database merge command
   - Hostname tracking

## Troubleshooting

### "No module named 'typer'"

Install dependencies:
```bash
pip install rich typer
```

### "externally-managed-environment"

Use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Or use Option 1 (run from source) or Option 3 (alias).

### OneDrive Not Detected

Check if OneDrive exists:
```bash
ls -la /mnt/d/OneDrive
```

If OneDrive is in a different location, set it manually:
```bash
python3 -m src.cli config set-db-path /path/to/your/OneDrive/.claude-goblin/usage_history.db
```

### Testing the Installation

```bash
# Test OneDrive detection
python3 -c "
import sys
sys.path.insert(0, '.')
from src.storage.snapshot_db import DEFAULT_DB_PATH
print(f'DB Path: {DEFAULT_DB_PATH}')
"

# Test config functions
python3 -m src.cli config show
```

## Contributing Back to Original

If you want to contribute your changes to the original project:

1. Create a feature branch
2. Make your changes
3. Submit a pull request to: https://github.com/data-goblin/claude-goblin

## License

MIT License (same as original)
