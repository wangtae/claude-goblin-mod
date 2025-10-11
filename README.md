# Claude Goblin

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-required-orange?logo=anthropic)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

Python command line tool to help with Claude Code utilities and usage tracking.

> **Platform Note**: Developed and tested on macOS (Python 3.13). Should work on Linux and Windows but is untested on those platforms.

## Features

- Local snapshotting of Claude Code logs for analytics.
- Local snapshotting of usage limits from the Claude Code `/usage` command.
- Dashboard and stats of usage and limit history.
- Hook setup to automate data logging or analysis of Claude Code as well as audio notifications.

## Installation

### With UV (recommended)
```bash
# Clone the repository
git clone https://github.com/data-goblin/claude-goblin.git
cd claude-goblin

# Install with uv
uv pip install -e .

# Optional: Install export dependencies for PNG/SVG generation
uv pip install -e ".[export]"
```

### With pip
```bash
# Clone the repository
git clone https://github.com/data-goblin/claude-goblin.git
cd claude-goblin

# Install with pip
pip install -e .

# Optional: Install export dependencies
pip install -e ".[export]"
```

## First-Time Setup

After installation, start tracking your Claude Code usage:

```bash
# View your current usage dashboard
claude-goblin --usage

# (Optional) Enable automatic tracking with hooks
claude-goblin --setup-hooks usage
```

**Note**: The `--usage` command automatically saves your data to the historical database every time you run it. No manual setup required.

### Commands Explained

- **`--update-usage`**: Update historical database with latest data and fill in missing date gaps with empty records (use when you want continuous date coverage for the heatmap)

For most users, just run `--usage` regularly and it will handle data tracking automatically. Use `--setup-hooks usage` to automate this completely.

## Commands

### Data Management
- `claude-goblin --update-usage` - Update historical database with latest data
- `claude-goblin --delete-usage --force` - Delete historical database (requires --force)
- `claude-goblin --restore-backup` - Restore from backup

### Dashboard & Analytics
- `claude-goblin --usage` - Show usage dashboard with KPI cards and breakdowns
- `claude-goblin --usage --live` - Auto-refresh dashboard every 5 seconds
- `claude-goblin --usage --fast` - Skip live limits for faster rendering
- `claude-goblin --limits` - Show current usage limits (session, week, Opus)
- `claude-goblin --stats` - Show detailed statistics and cost analysis

### Export
- `claude-goblin --export` - Export yearly heatmap as PNG (default)
- `claude-goblin --export svg` - Export as SVG image
- `claude-goblin --export --open` - Export and open the image
- `claude-goblin --export -y 2024` - Export specific year
- `claude-goblin --export -o output.png` - Specify output file

### Hooks (Advanced)
- `claude-goblin --setup-hooks usage` - Auto-update database on Claude exit
- `claude-goblin --setup-hooks audio` - Play sound on Claude exit
- `claude-goblin --setup-hooks png` - Generate PNG on Claude exit
- `claude-goblin --remove-hooks` - Remove all hooks

## Data Source

Claude Goblin reads usage data from Claude Code's session logs:
```
~/.claude/projects/*.jsonl
```

**Important**: Claude Code retains session logs for approximately **30 days** (rolling window). Claude Goblin solves this by:
- Automatically saving data to an SQLite database (`~/.claude/usage/usage_history.db`) whenever you run `--usage`
- Preserving historical data indefinitely
- Merging current + historical data for complete analytics

## How It Works

Claude Goblin uses a simple ingestion → storage → display architecture:

### Data Flow

```mermaid
graph TD
    A[Claude Code] -->|writes| B[JSONL Files<br/>~/.claude/projects/*.jsonl]
    A -.->|triggers| H[Hooks]

    B --> ING{Ingestion<br/>--usage<br/>--update-usage}
    H -.->|automates| ING

    ING --> DB[(Database<br/>~/.claude/usage/usage_history.db)]

    DB --> CMD1{--usage}
    DB --> CMD2{--stats}
    DB --> CMD3{--export}

    CMD1 --> OUT1[TUI Dashboard]
    CMD2 --> OUT2[Summary Stats<br/>in Terminal]
    CMD3 --> OUT3[Annual Activity PNG]

    H -.->|automates| CMD3

    style A fill:#e0e0e0,stroke:#333,color:#000
    style B fill:#ff8800,stroke:#333,color:#000
    style DB fill:#4a9eff,stroke:#333,color:#fff
    style OUT1 fill:#90ee90,stroke:#333,color:#000
    style OUT2 fill:#90ee90,stroke:#333,color:#000
    style OUT3 fill:#90ee90,stroke:#333,color:#000
    style H fill:#ffeb3b,stroke:#333,color:#000
```

**Key Points:**
- **JSONL files** are raw logs with a 30-day rolling window (older data disappears)
- **Ingestion** step reads JSONL and saves to DB (with automatic deduplication via `UNIQUE` constraint)
- **Database** is the single source of truth - all display commands read from here only
- **Hooks** can automate ingestion after each Claude response

### Command Behavior

**`claude-goblin --usage`** (Display + Ingestion)
1. **Ingestion**: Reads JSONL files from `~/.claude/projects/*.jsonl` and saves to DB
2. **Display**: Reads data from DB and renders dashboard

**`claude-goblin --export`** (Display only)
1. Reads data from DB at `~/.claude/usage/usage_history.db`
2. Generates yearly heatmap
3. Exports to current directory as `claude-usage-<timestamp>.png` (or specify with `-o`)

**`claude-goblin --stats`** (Display only)
1. Reads data from DB at `~/.claude/usage/usage_history.db`
2. Displays comprehensive statistics

**`claude-goblin --update-usage`** (Ingestion only)
1. Reads JSONL files from `~/.claude/projects/*.jsonl`
2. Saves to DB at `~/.claude/usage/usage_history.db` (with automatic deduplication)
3. Fills in missing dates with empty records (ensures continuous heatmap)

### File Locations

| File | Location | Purpose |
|------|----------|---------|
| **JSONL logs** | `~/.claude/projects/*.jsonl` | Current 30-day usage data from Claude Code |
| **SQLite DB** | `~/.claude/usage/usage_history.db` | Historical usage data preserved indefinitely |
| **Manual exports** | `./claude-usage-<timestamp>.png` | PNG/SVG heatmaps in current directory (or specify with `-o`) |
| **Hook exports** | `~/.claude/usage/claude-usage.png` | Default location for PNG hook auto-updates |

## --usage TUI dashboard

Example TUI:

![TUI dashboard of Claude Code usage](TUI.png)

## Yearly Heatmap

Export a GitHub-style yearly activity heatmap:

```bash
claude-goblin --export --open
```

Example heatmap:

![Yearly activity heatmap](heatmap.png)

### Export Formats

- **PNG** (default): `claude-goblin --export`


## Historical Data

Claude Goblin automatically saves data every time you run `--usage`. To manually manage:

```bash
# View historical stats
claude-goblin --stats

# Update database with latest data and fill date gaps
claude-goblin --update-usage

# Delete all history
claude-goblin --delete-usage -f
```

## What It Tracks

- **Tokens**: Input, output, cache creation, cache read (by model and project)
- **Prompts**: User prompts and assistant responses
- **Sessions**: Unique conversation threads
- **Models**: Which Claude models you've used (Sonnet, Opus, Haiku)
- **Projects**: Folders/directories where you've used Claude
- **Time**: Daily activity patterns throughout the year
- **Usage Limits**: Real-time session, weekly, and Opus limits


## Technical Details

### Timezone Handling

All timestamps in Claude Code's JSONL files seem to be stored in **UTC**. Claude Goblin should convert to your **local timezone** when grouping activity by date. This has only been tested with European CET.

### Cache Efficiency

The token breakdown shows cache efficiency. High "Cache Read" percentages (80-90%+) mean Claude Code is effectively reusing context, which:
- Speeds up responses
- Can reduce costs on usage-based plans
- Indicates good context management

## Requirements

- Python >= 3.10
- Claude Code (for generating usage data)
- Pillow + CairoSVG for PNG export

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

I don't have much time but I'll review PRs when I can.

## Troubleshooting

### "No Claude Code data found"
- Ensure Claude Code is installed and you've used it at least once
- Check that `~/.claude/projects/` exists and contains `.jsonl` files

### Limits showing "Could not parse usage data"
- Run `claude` in a trusted folder first
- Claude needs folder trust to display usage limits

### Export fails
- Install export dependencies: `pip install -e ".[export]"`
- For PNG: requires Pillow and CairoSVG

### Database errors
- Try deleting and recreating: `claude-goblin --delete-usage --force`
- Then run: `claude-goblin --usage` to rebuild from current data

## **AI Tools Disclaimer**: 
This project was developed with assistance from Claude Code.

## Credits

Built with:
- [Rich](https://github.com/Textualize/rich) - Terminal UI framework
- [Pillow](https://python-pillow.org/) - Image processing (optional)
- [CairoSVG](https://cairosvg.org/) - SVG to PNG conversion (optional)
