# Multi-PC Support Implementation Plan

## Overview

This document outlines the implementation plan for adding multi-PC support to Claude Goblin, enabling users to track and analyze their Claude Code usage across multiple computers with automatic synchronization via OneDrive.

## Problem Statement

Currently, each PC stores usage data independently in `~/.claude/usage/usage_history.db`, making it impossible to:
- Track total usage across all PCs
- Compare usage patterns between different machines
- Maintain continuous history when switching between computers

## Solution Architecture

### Core Concept

- **Single SQLite database** shared across PCs via cloud storage (OneDrive)
- **Automatic deduplication** using UNIQUE constraint on `(session_id, message_uuid)`
- **Per-machine identification** using hostname field for PC-specific statistics

### Key Features

1. **Automatic OneDrive Detection**: Auto-detect and use OneDrive folder for database storage
2. **Conflict Resolution**: Merge database tool for handling sync conflicts
3. **Machine Identification**: Track which PC generated each usage record
4. **Per-Machine Statistics**: View usage breakdown by machine

## Implementation Phases

---

## Phase 1: OneDrive Auto-Sync (Priority: HIGH)

### Goal
Enable automatic synchronization of usage database across multiple PCs via OneDrive.

### 1.1 Automatic Path Detection

**File**: `src/storage/snapshot_db.py`

**Changes**:
```python
import os
import platform
from pathlib import Path

def get_default_db_path() -> Path:
    """
    Auto-detect OneDrive and use it for database storage.
    Falls back to local storage if OneDrive is not available.

    Priority:
    1. Environment variable: CLAUDE_GOBLIN_DB_PATH
    2. OneDrive (WSL2): /mnt/c/Users/{username}/OneDrive/.claude-goblin/
    3. iCloud (macOS): ~/Library/Mobile Documents/com~apple~CloudDocs/.claude-goblin/
    4. Local fallback: ~/.claude/usage/
    """
    # 1. Environment variable override
    custom_path = os.getenv("CLAUDE_GOBLIN_DB_PATH")
    if custom_path:
        return Path(custom_path)

    # 2. WSL2 OneDrive detection
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        username = os.getenv("USER")
        onedrive_path = Path(f"/mnt/c/Users/{username}/OneDrive/.claude-goblin/usage_history.db")

        if _try_create_folder(onedrive_path.parent):
            return onedrive_path

    # 3. macOS iCloud Drive detection
    elif platform.system() == "Darwin":
        icloud_path = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/.claude-goblin/usage_history.db"
        if _try_create_folder(icloud_path.parent):
            return icloud_path

    # 4. Local fallback
    return Path.home() / ".claude" / "usage" / "usage_history.db"

def _try_create_folder(path: Path) -> bool:
    """Try to create folder. Return True if successful or already exists."""
    try:
        if path.parent.exists() or path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return True
    except (PermissionError, OSError):
        pass
    return False

# Update global constant
DEFAULT_DB_PATH = get_default_db_path()
```

**Benefits**:
- Zero manual configuration for most users
- Automatic cloud sync without symlinks
- Cross-platform support (WSL2, macOS)
- Environment variable override for advanced users

### 1.2 Conflict Resolution Tool

**File**: `src/commands/merge_db.py` (NEW)

**Purpose**: Manually merge databases when OneDrive creates conflict files (e.g., `usage_history-PC-B.db`)

```python
"""Database merge command for resolving sync conflicts."""

import shutil
import sqlite3
from pathlib import Path

from rich.console import Console
from src.storage.snapshot_db import DEFAULT_DB_PATH


def run(console: Console, source_db_path: str) -> None:
    """
    Merge another database into the current one.

    Automatically handles duplicates using UNIQUE constraint.
    Creates backup before merge.

    Args:
        console: Rich console for output
        source_db_path: Path to database to merge from
    """
    source_path = Path(source_db_path)

    if not source_path.exists():
        console.print(f"[red]Error: Source database not found: {source_path}[/red]")
        return

    if source_path == DEFAULT_DB_PATH:
        console.print("[red]Error: Cannot merge database into itself[/red]")
        return

    console.print(f"[cyan]Merging databases...[/cyan]")
    console.print(f"[dim]Source: {source_path}[/dim]")
    console.print(f"[dim]Target: {DEFAULT_DB_PATH}[/dim]\n")

    # Create backup
    backup_path = DEFAULT_DB_PATH.parent / f"{DEFAULT_DB_PATH.name}.pre-merge.bak"
    shutil.copy2(DEFAULT_DB_PATH, backup_path)
    console.print(f"[green]✓ Backup created: {backup_path}[/green]\n")

    # Perform merge
    try:
        merged, skipped = _merge_databases(source_path, DEFAULT_DB_PATH)

        console.print("[green]✓ Merge completed successfully![/green]")
        console.print(f"[dim]Records added: {merged}[/dim]")
        console.print(f"[dim]Duplicates skipped: {skipped}[/dim]")

        # Optionally rename source file
        merged_marker = source_path.parent / f"{source_path.stem}.merged{source_path.suffix}"
        source_path.rename(merged_marker)
        console.print(f"[dim]Source renamed to: {merged_marker}[/dim]")

    except Exception as e:
        console.print(f"[red]Error during merge: {e}[/red]")
        console.print(f"[yellow]Backup available at: {backup_path}[/yellow]")
        raise


def _merge_databases(source_path: Path, target_path: Path) -> tuple[int, int]:
    """
    Merge all records from source into target.

    Returns:
        Tuple of (records_added, duplicates_skipped)
    """
    source_conn = sqlite3.connect(source_path)
    target_conn = sqlite3.connect(target_path)

    merged_count = 0
    skipped_count = 0

    try:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # Merge usage_records
        source_cursor.execute("SELECT * FROM usage_records")
        for row in source_cursor.fetchall():
            try:
                target_cursor.execute("""
                    INSERT INTO usage_records
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
                merged_count += 1
            except sqlite3.IntegrityError:
                # Duplicate (session_id, message_uuid), skip
                skipped_count += 1

        # Merge daily_snapshots (use REPLACE for aggregates)
        source_cursor.execute("SELECT * FROM daily_snapshots")
        for row in source_cursor.fetchall():
            target_cursor.execute("""
                INSERT OR REPLACE INTO daily_snapshots
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)

        # Merge limits_snapshots
        source_cursor.execute("SELECT * FROM limits_snapshots")
        for row in source_cursor.fetchall():
            try:
                target_cursor.execute("""
                    INSERT INTO limits_snapshots
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            except sqlite3.IntegrityError:
                # Duplicate timestamp, skip
                pass

        target_conn.commit()

    finally:
        source_conn.close()
        target_conn.close()

    return merged_count, skipped_count
```

**CLI Integration**: Add to `src/cli.py`

```python
@app.command(name="merge-db")
def merge_db_command(
    source: str = typer.Argument(..., help="Path to database file to merge"),
):
    """
    Merge another database into the current one.

    Use this when OneDrive creates conflict files (e.g., usage_history-PC-B.db)
    or when manually importing data from another PC.

    Example:
        ccg merge-db /mnt/c/Users/wangt/OneDrive/.claude-goblin/usage_history-Laptop.db
    """
    from src.commands import merge_db
    merge_db.run(console, source)
```

---

## Phase 2: Per-Machine Statistics (Priority: MEDIUM)

### Goal
Enable tracking and analysis of usage patterns per machine.

### 2.1 Database Schema Extension

**File**: `src/storage/snapshot_db.py`

**Changes**:
```python
def init_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initialize database with hostname support."""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            message_uuid TEXT NOT NULL,
            message_type TEXT NOT NULL,
            model TEXT,
            folder TEXT NOT NULL,
            git_branch TEXT,
            version TEXT NOT NULL,
            hostname TEXT,              -- NEW: Machine identifier
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cache_creation_tokens INTEGER NOT NULL,
            cache_read_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            UNIQUE(session_id, message_uuid)
        )
    """)

    # ... rest of init code ...

def migrate_add_hostname() -> None:
    """Add hostname column to existing database."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    try:
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(usage_records)")
        columns = [col[1] for col in cursor.fetchall()]

        if "hostname" not in columns:
            cursor.execute("ALTER TABLE usage_records ADD COLUMN hostname TEXT")
            conn.commit()
    finally:
        conn.close()

# Run migration on first import
if DEFAULT_DB_PATH.exists():
    migrate_add_hostname()
```

### 2.2 Model Update

**File**: `src/models/usage_record.py`

**Changes**:
```python
@dataclass(frozen=True)
class UsageRecord:
    """
    Represents a single usage event from Claude Code.
    """
    timestamp: datetime
    session_id: str
    message_uuid: str
    message_type: str
    model: Optional[str]
    folder: str
    git_branch: Optional[str]
    version: str
    hostname: Optional[str] = None  # NEW: Machine identifier
    token_usage: Optional[TokenUsage] = None
    content: Optional[str] = None
    char_count: int = 0

    # ... rest of class ...
```

### 2.3 Data Collection Update

**File**: `src/data/jsonl_parser.py`

**Changes**:
```python
import socket

def _parse_record(data: dict) -> Optional[UsageRecord]:
    """Parse a single JSON record with hostname."""

    # ... existing parsing code ...

    # Add hostname
    hostname = socket.gethostname()

    return UsageRecord(
        timestamp=timestamp,
        session_id=session_id,
        message_uuid=message_uuid,
        message_type=message_type,
        model=model,
        folder=folder,
        git_branch=git_branch,
        version=version,
        hostname=hostname,  # NEW
        token_usage=token_usage,
        content=content,
        char_count=char_count,
    )
```

### 2.4 User-Friendly Machine Names

**File**: `src/config/user_config.py`

**New Functions**:
```python
def get_machine_name() -> str:
    """
    Get user-friendly machine name.

    Priority:
    1. Environment variable: CLAUDE_GOBLIN_MACHINE_NAME
    2. Config file: machine_name
    3. Auto-generated: socket.gethostname()
    """
    # 1. Environment variable
    env_name = os.getenv("CLAUDE_GOBLIN_MACHINE_NAME")
    if env_name:
        return env_name

    # 2. Config file
    config = load_config()
    if config.get("machine_name"):
        return config["machine_name"]

    # 3. Hostname
    return socket.gethostname()


def set_machine_name(name: str) -> None:
    """Set custom machine name in config."""
    config = load_config()
    config["machine_name"] = name
    save_config(config)
```

**CLI Integration**: Add to `src/cli.py`

```python
@app.command(name="config")
def config_command(
    action: str = typer.Argument(..., help="Action: set-machine-name or get-machine-name"),
    value: Optional[str] = typer.Argument(None, help="Value for set actions"),
):
    """
    Manage Claude Goblin configuration.

    Examples:
        ccg config set-machine-name "Home-Desktop"
        ccg config get-machine-name
    """
    from src.config.user_config import get_machine_name, set_machine_name

    if action == "get-machine-name":
        console.print(f"Machine name: {get_machine_name()}")
    elif action == "set-machine-name":
        if not value:
            console.print("[red]Error: Machine name required[/red]")
            return
        set_machine_name(value)
        console.print(f"[green]✓ Machine name set to: {value}[/green]")
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
```

### 2.5 Statistics Command Enhancement

**File**: `src/commands/stats.py`

**New Function**:
```python
def show_machine_stats(all_records: list, console: Console) -> None:
    """Show usage statistics grouped by machine."""
    from collections import defaultdict

    machine_stats = defaultdict(lambda: {
        "tokens": 0,
        "prompts": 0,
        "responses": 0,
        "sessions": set(),
        "cost": 0.0,
    })

    for record in all_records:
        machine = record.hostname or "Unknown"

        if record.is_user_prompt:
            machine_stats[machine]["prompts"] += 1
        elif record.is_assistant_response:
            machine_stats[machine]["responses"] += 1

        if record.token_usage:
            machine_stats[machine]["tokens"] += record.token_usage.total_tokens

        machine_stats[machine]["sessions"].add(record.session_id)

    # Convert sets to counts
    for machine in machine_stats:
        machine_stats[machine]["sessions"] = len(machine_stats[machine]["sessions"])

    # Sort by tokens descending
    sorted_machines = sorted(
        machine_stats.items(),
        key=lambda x: x[1]["tokens"],
        reverse=True
    )

    # Display table
    table = Table(title="Usage by Machine")
    table.add_column("Machine", style="cyan")
    table.add_column("Tokens", justify="right", style="green")
    table.add_column("Sessions", justify="right")
    table.add_column("Prompts", justify="right")
    table.add_column("Responses", justify="right")

    total_tokens = sum(stats["tokens"] for _, stats in sorted_machines)

    for machine, stats in sorted_machines:
        percentage = (stats["tokens"] / total_tokens * 100) if total_tokens > 0 else 0

        table.add_row(
            machine,
            f"{stats['tokens']:,} ({percentage:.1f}%)",
            f"{stats['sessions']:,}",
            f"{stats['prompts']:,}",
            f"{stats['responses']:,}",
        )

    console.print(table)
```

**Update `run()` function**:
```python
def run(console: Console, fast: bool = False, by_machine: bool = False) -> None:
    """Show statistics with optional machine breakdown."""

    # ... existing stats code ...

    if by_machine:
        console.print("\n")
        show_machine_stats(all_records, console)
```

**CLI Update**: Modify `stats_command()` in `src/cli.py`

```python
@app.command(name="stats")
def stats_command(
    fast: bool = typer.Option(False, "--fast", help="Skip updates"),
    by_machine: bool = typer.Option(False, "--by-machine", help="Show breakdown by machine"),
):
    """
    Show detailed statistics and cost analysis.

    Use --by-machine to see usage breakdown by PC.
    """
    stats.run(console, fast=fast, by_machine=by_machine)
```

### 2.6 Dashboard Enhancement

**File**: `src/visualization/dashboard.py`

**Add machine breakdown section** (similar to project breakdown):

```python
def render_dashboard(stats, all_records, console, ...):
    """Render dashboard with machine breakdown."""

    # ... existing dashboard sections ...

    # Add machine breakdown if multiple machines detected
    machines = set(r.hostname for r in all_records if r.hostname)
    if len(machines) > 1:
        console.print("\n[bold]Top 5 Machines[/bold]")
        render_machine_breakdown(all_records, console)


def render_machine_breakdown(all_records, console):
    """Render top 5 machines by token usage."""
    from collections import defaultdict

    machine_tokens = defaultdict(int)

    for record in all_records:
        if record.token_usage and record.hostname:
            machine_tokens[record.hostname] += record.token_usage.total_tokens

    # Sort and take top 5
    sorted_machines = sorted(
        machine_tokens.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    total_tokens = sum(machine_tokens.values())

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Machine", style="cyan")
    table.add_column("Tokens", justify="right")
    table.add_column("Bar")
    table.add_column("Percentage", justify="right", style="dim")

    for machine, tokens in sorted_machines:
        percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0
        bar_width = int(percentage / 2)  # Scale to 50 chars max
        bar = "█" * bar_width

        table.add_row(
            machine,
            f"{tokens:,}",
            bar,
            f"{percentage:.1f}%"
        )

    console.print(table)
```

---

## Phase 3: User Experience Improvements (Priority: LOW)

### 3.1 Diagnostic Tool

**File**: `src/commands/doctor.py` (NEW)

```python
"""Diagnostic tool for troubleshooting Claude Goblin."""

from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.storage.snapshot_db import DEFAULT_DB_PATH, get_database_stats
from src.config.settings import CLAUDE_DATA_DIR
from src.config.user_config import get_machine_name


def run(console: Console) -> None:
    """Run diagnostic checks and display system status."""

    console.print("[bold cyan]Claude Goblin Diagnostic Tool[/bold cyan]\n")

    # Check 1: Database location
    console.print("[bold]1. Database Location[/bold]")
    console.print(f"Path: {DEFAULT_DB_PATH}")
    console.print(f"Exists: {DEFAULT_DB_PATH.exists()}")

    if DEFAULT_DB_PATH.exists():
        size_mb = DEFAULT_DB_PATH.stat().st_size / (1024 * 1024)
        console.print(f"Size: {size_mb:.2f} MB")

        stats = get_database_stats()
        console.print(f"Records: {stats['total_records']:,}")
        console.print(f"Days tracked: {stats['total_days']}")

    console.print()

    # Check 2: OneDrive detection
    console.print("[bold]2. Cloud Sync Status[/bold]")

    if "OneDrive" in str(DEFAULT_DB_PATH):
        console.print("[green]✓ Using OneDrive sync[/green]")
    elif "CloudDocs" in str(DEFAULT_DB_PATH):
        console.print("[green]✓ Using iCloud Drive sync[/green]")
    else:
        console.print("[yellow]⚠ Using local storage (no cloud sync)[/yellow]")

    console.print()

    # Check 3: Conflict files
    console.print("[bold]3. Conflict Detection[/bold]")

    conflict_files = list(DEFAULT_DB_PATH.parent.glob("*conflict*"))
    conflict_files += list(DEFAULT_DB_PATH.parent.glob("*-PC-*"))

    if conflict_files:
        console.print(f"[yellow]⚠ Found {len(conflict_files)} conflict file(s)[/yellow]")
        for cf in conflict_files:
            console.print(f"  - {cf.name}")
        console.print("\nRun: [cyan]ccg merge-db <conflict-file>[/cyan] to resolve")
    else:
        console.print("[green]✓ No conflict files detected[/green]")

    console.print()

    # Check 4: Machine info
    console.print("[bold]4. Machine Information[/bold]")
    console.print(f"Machine name: {get_machine_name()}")
    console.print(f"Claude data: {CLAUDE_DATA_DIR}")
    console.print(f"JSONL files: {len(list(CLAUDE_DATA_DIR.glob('*.jsonl')))}")

    console.print()

    # Check 5: Database integrity
    console.print("[bold]5. Database Integrity[/bold]")

    try:
        import sqlite3
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        if result == "ok":
            console.print("[green]✓ Database integrity OK[/green]")
        else:
            console.print(f"[red]✗ Integrity issue: {result}[/red]")

        conn.close()
    except Exception as e:
        console.print(f"[red]✗ Cannot check integrity: {e}[/red]")

    console.print()
    console.print("[dim]For more help, visit: https://github.com/data-goblin/claude-goblin[/dim]")
```

**CLI Integration**:
```python
@app.command(name="doctor")
def doctor_command():
    """
    Run diagnostic checks.

    Checks:
    - Database location and status
    - OneDrive/iCloud sync detection
    - Conflict file detection
    - Machine information
    - Database integrity
    """
    from src.commands import doctor
    doctor.run(console)
```

### 3.2 Documentation Update

**File**: `README.md`

Add new section:

```markdown
## Multi-PC Usage

Claude Goblin supports automatic synchronization across multiple PCs using cloud storage.

### Automatic Setup (Recommended)

Claude Goblin automatically detects and uses:
- **OneDrive** (Windows/WSL2): `/mnt/c/Users/your-name/OneDrive/.claude-goblin/`
- **iCloud Drive** (macOS): `~/Library/Mobile Documents/com~apple~CloudDocs/.claude-goblin/`

**No configuration needed!** Just install and run:

```bash
# PC-A
pip install claude-goblin
ccg usage  # Automatically uses OneDrive

# PC-B (syncs automatically via OneDrive)
pip install claude-goblin
ccg usage  # Finds existing database, merges data
```

### Per-Machine Statistics

View usage breakdown by computer:

```bash
ccg stats --by-machine

# Output:
┌──────────────┬───────────┬──────────┐
│ Machine      │ Tokens    │ Sessions │
├──────────────┼───────────┼──────────┤
│ Desktop-WSL  │ 1,234,567 │ 145      │
│ Laptop-WSL   │   823,451 │  89      │
│ Work-Mac     │   456,789 │  34      │
└──────────────┴───────────┴──────────┘
```

### Custom Machine Names

Set a friendly name for each PC:

```bash
# On desktop
ccg config set-machine-name "Home-Desktop"

# On laptop
ccg config set-machine-name "Work-Laptop"
```

### Manual Configuration

If automatic detection fails, set a custom path:

```bash
# Using environment variable
export CLAUDE_GOBLIN_DB_PATH="/mnt/c/Users/your-name/OneDrive/.claude-goblin/usage_history.db"

# Or using symlink
ln -sf /mnt/c/Users/your-name/OneDrive/.claude-goblin/usage_history.db ~/.claude/usage/usage_history.db
```

### Handling Conflicts

If OneDrive creates conflict files (e.g., when editing on multiple PCs offline):

```bash
# Check for conflicts
ccg doctor

# Merge conflict files
ccg merge-db /path/to/usage_history-conflict.db
```

### Troubleshooting

```bash
# Verify setup
ccg doctor

# Common issues:
# 1. "No cloud sync detected" - OneDrive not installed or path not found
# 2. "Conflict files found" - Use ccg merge-db to resolve
# 3. "Database integrity failed" - Restore from backup
```
```

---

## Migration Strategy

### Backward Compatibility

1. **Existing databases**: `hostname` column is NULL for old records
2. **Graceful degradation**: Stats work with or without hostname
3. **Auto-migration**: Column added automatically on first run

### Testing Plan

1. **Unit tests**: Database path detection logic
2. **Integration tests**: Merge functionality
3. **Manual testing**:
   - Fresh install on clean system
   - Upgrade from existing installation
   - Multi-PC sync scenarios
   - Conflict resolution

---

## Success Metrics

- ✅ OneDrive auto-detection works on WSL2
- ✅ Database merges without data loss
- ✅ Per-machine statistics accurate
- ✅ Zero-config experience for most users
- ✅ Backward compatible with existing databases

---

## Timeline Estimate

- **Phase 1** (High Priority): 4-6 hours
  - Auto path detection: 2 hours
  - Merge command: 2-3 hours
  - Testing: 1 hour

- **Phase 2** (Medium Priority): 3-4 hours
  - Schema migration: 1 hour
  - Model/parser updates: 1 hour
  - Stats command: 1-2 hours

- **Phase 3** (Low Priority): 2-3 hours
  - Doctor command: 1 hour
  - Documentation: 1-2 hours

**Total**: 9-13 hours

---

## Future Enhancements

- **Git-based sync**: Export/import JSON for version control
- **Per-machine export**: Generate separate heatmaps for each PC
- **Machine comparison**: Side-by-side usage analysis
- **Auto-backup**: Periodic backups to prevent data loss
- **Conflict auto-resolution**: Automatic merge when conflicts detected
