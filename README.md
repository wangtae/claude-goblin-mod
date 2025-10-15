# Claude Code Goblin (Modified Fork)

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-required-orange?logo=anthropic)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

> [!IMPORTANT]
> This is a **modified fork** of [claude-goblin](https://github.com/data-goblin/claude-goblin) with multi-PC support and streamlined functionality.
>
> **Installation**: Run from source (see [Installation](#installation)) - `pip install claude-goblin` installs the original, not this fork.

**Interactive TUI dashboard for Claude Code usage analytics and long-term tracking.**

Most features are accessed through keyboard shortcuts in the interactive dashboard - minimal command-line interface by design.

---

## Quick Start

```bash
# Install pipx (if not already installed)
sudo apt install pipx       # Ubuntu/Debian
brew install pipx           # macOS

# Configure PATH
pipx ensurepath
source ~/.bashrc

# Clone and install
git clone https://github.com/wangtae/claude-goblin-mod.git
cd claude-goblin-mod
pipx install -e .

# Run from anywhere
ccu
```

That's it! The interactive dashboard will open with all your Claude Code usage data.

---

## Features

### Core Functionality

- 📊 **Interactive Dashboard** - All features accessible via keyboard shortcuts (no complex CLI commands)
- 🔄 **Real-time Updates** - Automatic file watching when Claude Code creates new logs
- 📅 **Long-term Tracking** - Preserves usage data beyond Claude Code's 30-day limit
- 🌐 **Multi-PC Sync** - Automatic cloud storage detection for seamless multi-computer tracking (OneDrive for WSL2/Windows, iCloud Drive for macOS)
- 🖥️ **Per-Machine Stats** - Track usage breakdown across different computers

### View Modes (All In-Dashboard)

Access via keyboard shortcuts - no separate commands needed:

- **Usage Mode** (`u`) - Current week limits with reset times and cost estimates
- **Weekly View** (`w`) - Daily breakdown with hourly drill-down
- **Monthly View** (`m`) - Project and daily statistics for current month
- **Yearly View** (`y`) - Annual overview with monthly/project breakdowns
- **Heatmap** (`h`) - GitHub-style activity visualization
- **Devices** (`d`) - Per-machine usage statistics

### This Fork's Enhancements

- ✅ **Automatic Cloud Storage Detection** - OneDrive (WSL2/Windows) or iCloud Drive (macOS) with zero-config
- ✅ **Timezone Support** - Auto-detect system timezone with configurable settings
- ✅ **Streamlined Codebase** - Removed unused features (hooks, status bar, export)
- ✅ **Configuration Management** - Simple config system for database path and machine names
- ✅ **Project Anonymization** - `--anon` flag for sharing screenshots safely

---

## Screenshots

All screenshots show the interactive TUI dashboard with real-time data and keyboard navigation.

### 0. VSCode Integration - Terminal Usage

![VSCode Usage](docs/images/00_vscode-usages.png)

**Key Features:**
- Runs seamlessly in VSCode's integrated terminal
- Works in compact window sizes (minimal vertical space needed)
- Supports various VSCode color themes
- Full keyboard navigation without leaving the editor
- Real-time updates while coding

**Use Case:** Monitor Claude Code usage without switching applications

### 1. Usage Mode - Real-time Limits

![Usage Mode](docs/images/01_usages.png)

**Key Features:**
- Current session usage (5-hour window) with reset countdown
- Weekly limit across all models with percentage bars
- Opus-specific weekly limit tracking
- Token breakdown: Input, Output, Cache Write, Cache Read
- Cost estimation and message count
- Auto-refreshes in background

**Keyboard:** `u` to switch to this view

### 2. Weekly View - Daily Breakdown

![Weekly View](docs/images/02_weekly.png)

**Key Features:**
- 7-day overview with daily statistics
- Visual progress bars for each day
- Token usage by model (Sonnet/Opus breakdown)
- Top 10 projects for the week
- Press number keys `1-7` to drill down into hourly details

**Keyboard:** `w` to switch to this view

### 3. Weekly Daily Detail - Hourly Breakdown

![Weekly Daily Detail](docs/images/03_weekly_daily.png)

**Key Features:**
- Hourly statistics for selected day
- Time-based token usage patterns
- Model and project breakdowns specific to that day
- Press number keys `1-24` to view individual message details
- Press `ESC` to return to weekly view

**Keyboard:** `1-7` from weekly view to select a day

### 4. Message Detail View - Individual Messages

![Message Detail](docs/images/04_weekly_daily_messages.png)

**Key Features:**
- Individual message metadata (timestamp, model, tokens)
- Input/Output token counts with cache statistics
- Cost per message
- Content preview for each message (42 characters)
- User prompts and Assistant responses shown separately

**Keyboard:** `1-24` from daily detail view to select an hour

### 5. Monthly View - Project Focus

![Monthly View](docs/images/05_monthly.png)

**Key Features:**
- Full month overview with daily bars
- Token usage trends throughout the month
- Top projects ranked by usage
- Cost and percentage breakdowns
- Navigate previous/next months with `<` and `>`

**Keyboard:** `m` to switch to this view

### 6. Yearly View - Annual Overview

![Yearly View](docs/images/06_yearly.png)

**Key Features:**
- 12-month summary with monthly statistics
- Annual token usage trends
- Project rankings for the entire year
- Year-to-date cost estimation
- Navigate previous/next years with `<` and `>`

**Keyboard:** `y` to switch to this view

### 7. Heatmap View - Activity Patterns

![Heatmap View](docs/images/07_heatmap.png)

**Key Features:**
- GitHub-style contribution graph
- Color intensity based on token usage
- Full year visualization (52 weeks)
- Identify usage patterns and trends
- Quick visual overview of activity

**Keyboard:** `h` to switch to this view

### 8. Devices View - Multi-PC Statistics

![Devices View](docs/images/08_devices.png)

**Key Features:**
- Per-machine usage breakdown
- Device names (customizable via settings)
- Token and cost totals per device
- Date range for each device's activity
- Useful for multi-PC setups with cloud storage sync (OneDrive on WSL2/Windows, iCloud Drive on macOS)

**Keyboard:** `d` to switch to this view

### 9. Settings Menu - Configuration

![Settings Menu](docs/images/09_settings.png)

**Key Features:**
- Color customization (solid colors and gradient ranges)
- Display mode preferences
- Auto-refresh interval settings
- Timezone configuration
- Backup management options
- Reset to defaults with confirmation

**Keyboard:** `s` to open settings menu from any view

---

## Installation

> [!IMPORTANT]
> This fork is installed from source, not PyPI. `pip install claude-goblin` installs the **original** version, not this fork!

### Recommended: Global Install with pipx

Install once with `pipx`, then use `ccu` from anywhere (no virtual environment needed):

```bash
# Install pipx (if not already installed)
sudo apt install pipx       # Ubuntu/Debian
brew install pipx           # macOS
pip install --user pipx     # Other systems

# Configure PATH
pipx ensurepath
source ~/.bashrc  # or restart terminal

# Clone and install
git clone https://github.com/wangtae/claude-goblin-mod.git
cd claude-goblin-mod
pipx install -e .

# Now you can use ccu anywhere
ccu  # Works from any directory!
```

**Why pipx?**
- ✅ **Isolated environment** - No dependency conflicts with other Python packages
- ✅ **Global access** - Use `ccu` from any directory without activating virtual environments
- ✅ **Editable mode** - Source code changes are immediately reflected (perfect for development)
- ✅ **Clean uninstall** - `pipx uninstall claude-goblin-mod` removes everything
- ✅ **Recommended by Python packaging community** for CLI tools

### Alternative: Local Editable Install (pip)

For systems where pipx is not available or if you prefer pip:

```bash
# Clone the repository
git clone https://github.com/wangtae/claude-goblin-mod.git
cd claude-goblin-mod

# Install in editable mode (creates ccu command)
pip install -e .

# Now you can use ccu anywhere
ccu  # Works from any directory!
```

**Note**: On some systems (Ubuntu 24.04+), you may encounter an "externally-managed-environment" error. In this case, use pipx instead (recommended) or create a virtual environment (see next section).

**If `ccu: command not found`**, add `~/.local/bin` to your PATH:
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

### Alternative: Virtual Environment

For completely isolated installation:

```bash
git clone https://github.com/wangtae/claude-goblin-mod.git
cd claude-goblin-mod

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Use (while venv is active)
ccu
```

### Alternative: Run from Source (No Install)

For quick testing without installation:

```bash
git clone https://github.com/wangtae/claude-goblin-mod.git
cd claude-goblin-mod

# Install dependencies only
pip install -r requirements.txt

# Run directly
python3 -m src.cli
```

---

## Usage

### Starting the Dashboard

```bash
ccu                          # Standard mode with file watching
ccu --refresh=30             # Refresh every 30 seconds instead
ccu --anon                   # Anonymize project names (for screenshots)
ccu --watch-interval=30      # File watch check interval
ccu --limits-interval=120    # Usage limits update interval
```

### Keyboard Shortcuts (In Dashboard)

**View Modes:**
- `u` - Usage mode (current limits and costs)
- `w` - Weekly view
- `m` - Monthly view
- `y` - Yearly view
- `h` - Heatmap view
- `d` - Devices view (multi-PC stats)

**Navigation:**
- `1-7` - Hourly drill-down for specific day (weekly mode)
- `<` / `>` - Previous/next period (weekly/monthly/yearly)
- `tab` - Change display mode/color scheme
- `r` - Manual refresh
- `s` - Settings menu
- `q` / `Esc` - Quit

**Everything is accessible via these keyboard shortcuts - no need to learn complex commands!**

### Additional Commands

Only a few commands exist outside the dashboard:

```bash
# Heatmap in terminal (also accessible via 'h' in dashboard)
ccu heatmap              # Current year
ccu heatmap --year 2024  # Specific year

# Configuration (rarely needed, OneDrive auto-detected)
ccu config show                              # View config
ccu config set-db-path <path>                # Set custom DB path
ccu config set-machine-name "Home-Desktop"   # Set friendly name

# Database management (rarely needed)
ccu reset-db --force     # Reset database
```

Most users will only ever run `ccu` to open the dashboard.

---

## How It Works

```mermaid
graph TD
    A[Claude Code] -->|writes| B[JSONL Files<br/>~/.claude/projects/*.jsonl]

    B --> ING{Dashboard<br/>ccu}

    ING --> DB[(SQLite Database<br/>Historical Data)]

    DB --> CMD1{Interactive Views}

    CMD1 --> OUT1[Usage Mode]
    CMD1 --> OUT2[Weekly/Monthly/Yearly]
    CMD1 --> OUT3[Heatmap]
    CMD1 --> OUT4[Devices]

    style A fill:#e0e0e0,stroke:#333,color:#000
    style B fill:#ff8800,stroke:#333,color:#000
    style DB fill:#4a9eff,stroke:#333,color:#fff
    style OUT1 fill:#90ee90,stroke:#333,color:#000
    style OUT2 fill:#90ee90,stroke:#333,color:#000
    style OUT3 fill:#90ee90,stroke:#333,color:#000
    style OUT4 fill:#90ee90,stroke:#333,color:#000
```

**Key Points:**
- **JSONL files** - Claude Code's raw logs (30-day rolling window)
- **Dashboard** - Reads JSONL and saves to SQLite (automatic deduplication)
- **Database** - Single source of truth, preserves data indefinitely
- **Interactive views** - All accessed via keyboard shortcuts in one dashboard

### Data Sources

| File | Location | Purpose |
|------|----------|---------|
| **JSONL logs** | `~/.claude/projects/*.jsonl` | Current 30-day usage from Claude Code |
| **SQLite DB** | `~/.claude/usage/usage_history.db` | Historical data (default location) |
| **SQLite DB** | `/mnt/d/OneDrive/.claude-goblin/usage_history.db` | OneDrive sync (auto-detected) |
| **Config** | `~/.claude/goblin_config.json` | User configuration |

---

## Multi-PC Synchronization

This fork automatically detects cloud storage for seamless multi-PC tracking:
- **OneDrive** (WSL2/Windows) - Automatically detected on `/mnt/c|d|e|f/OneDrive`
- **iCloud Drive** (macOS) - Automatically detected in `~/Library/Mobile Documents/com~apple~CloudDocs`

### Zero-Configuration Setup

```bash
# On PC-A (Desktop)
ccu
# → Auto-detects: /mnt/d/OneDrive/.claude-goblin/usage_history.db
# → OneDrive syncs to cloud automatically

# On PC-B (Laptop)
ccu
# → Auto-detects same OneDrive database
# ✅ Combined usage from both PCs!
```

### Database Location Priority

1. Config file setting (if manually set via `ccu config set-db-path`)
2. Environment variable `CLAUDE_GOBLIN_DB_PATH`
3. OneDrive auto-detection (WSL2: `/mnt/*/OneDrive/.claude-goblin/`)
4. iCloud Drive auto-detection (macOS: `~/Library/Mobile Documents/com~apple~CloudDocs/.claude-goblin/`)
5. Local fallback (`~/.claude/usage/`)

### Supported Cloud Storage by Platform

| Platform | Cloud Storage | Detection Path | Status |
|----------|---------------|----------------|--------|
| **WSL2** | OneDrive | `/mnt/c/d/e/f/OneDrive/.claude-goblin/` | ✅ Auto-detected |
| **Windows** | OneDrive | (via WSL2 mount) | ✅ Auto-detected |
| **macOS** | iCloud Drive | `~/Library/Mobile Documents/com~apple~CloudDocs/.claude-goblin/` | ✅ Auto-detected |
| **All** | Custom Path | Any location | ⚙️ Via `ccu config set-db-path` |

**Note**: iCloud Drive only works on macOS. OneDrive is for WSL2/Windows users.

### Deduplication

SQLite UNIQUE constraint on `(session_id, message_uuid)` prevents duplicates - multiple PCs can safely write to the same database.

---

## What It Tracks

- **Tokens** - Input, output, cache creation, cache read (by model and project)
- **Models** - Claude Sonnet, Opus, Haiku usage breakdown
- **Projects** - Folders/directories where you've used Claude Code
- **Sessions** - Unique conversation threads
- **Time Patterns** - Hourly, daily, monthly, yearly activity
- **Usage Limits** - Real-time session, weekly, and Opus limits with background updates
- **Devices** - Per-machine statistics (machine name, tokens, cost, date range)
- **Cost Estimates** - Calculate equivalent API costs vs Claude Pro subscription

High "Cache Read" percentages (80-90%+) indicate efficient context reuse, which speeds up responses and reduces costs.

---

## Technical Implementation

### Real-time Updates

**File Watching (Default)**
- Uses `watchdog` library to monitor `~/.claude/projects/*.jsonl`
- Updates dashboard automatically when Claude Code creates/modifies logs
- More efficient than polling

**Periodic Refresh** (`--refresh=N`)
- Updates every N seconds via polling
- Fallback for environments where file watching doesn't work

### Background Threads

- **Limits updater** - Fetches usage limits every 60 seconds (configurable)
- **Keyboard listener** - Non-blocking input handling for instant mode switching
- **File watcher** - Monitors JSONL files for changes

### Timezone Handling

Claude Code stores timestamps in **UTC**. This tool converts to your **local timezone** automatically:
- Auto-detect from `/etc/timezone` (Linux/WSL)
- Configurable in settings menu (press `s` in dashboard)
- Support for 'auto' mode, UTC, and IANA timezones

### Weekly Date Filtering

Parses Claude's `/usage` reset dates (e.g., "Oct 17, 10am (Asia/Seoul)") and filters data to match the current 7-day limit period shown in Claude Code.

---

## Requirements

- **Python** >= 3.10
- **Claude Code** (for generating usage data)
- **Dependencies:**
  - `rich` >= 13.7.0 - Terminal UI framework
  - `typer` >= 0.9.0 - CLI framework
  - `watchdog` >= 3.0.0 - File system monitoring

---

## Troubleshooting

### "No Claude Code data found"
- Ensure Claude Code is installed and you've used it at least once
- Check that `~/.claude/projects/` exists and contains `.jsonl` files

### Limits showing "Could not parse usage data"
- Run `claude` in a trusted folder first
- Claude needs folder trust to display `/usage` data

### Database errors
```bash
ccu reset-db --force  # Reset database
ccu                   # Rebuild from current data
```

### Multi-PC sync not working
```bash
ccu config show  # Check detected database path
ccu config set-db-path /path/to/OneDrive/.claude-goblin/usage_history.db
```

---

## Project Anonymization

Perfect for sharing screenshots publicly:

```bash
ccu --anon         # Anonymize in dashboard
ccu heatmap --anon # Anonymize in heatmap
```

Projects are renamed to `project-001`, `project-002`, etc., ranked by total token usage (highest usage = project-001).

---

## License

MIT License - see [LICENSE](LICENSE) file for details

---

## Contributing

Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## Credits

**Original Project:** [claude-goblin](https://github.com/data-goblin/claude-goblin) by Kurt Buhler

**Built with:**
- [Rich](https://github.com/Textualize/rich) - Terminal UI framework
- [Typer](https://github.com/tiangolo/typer) - CLI framework
- [Watchdog](https://github.com/gorakhargosh/watchdog) - File system monitoring

---

**AI Tools Disclaimer:** This project was developed with assistance from Claude Code.
