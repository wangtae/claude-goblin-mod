# Scripts

This directory contains utility scripts for Claude Goblin.

## Migration Scripts

### migrate_to_onedrive.sh

Migrates existing database files from local storage to OneDrive for multi-PC synchronization.

**When to use:**
- You've been using local storage and want to switch to OneDrive sync
- OneDrive path was incorrectly detected (e.g., `/mnt/c/` instead of `/mnt/d/`)
- You need to move databases to a different OneDrive location

**Usage:**
```bash
./scripts/migrate_to_onedrive.sh
```

**What it does:**
1. Detects existing database location
2. Shows current DB files
3. Asks for target OneDrive path
4. Creates backup of current databases
5. Copies DB files to new location
6. Updates configuration file (`~/.claude/goblin_config.json`)

**Safety features:**
- Creates automatic backup before migration
- Validates paths before copying
- Preserves original files (manual cleanup required)

**Example:**
```bash
$ ./scripts/migrate_to_onedrive.sh
=== Claude Goblin OneDrive Migration ===

Step 1: Detecting current database location
Found databases at: /mnt/c/Users/wangt/OneDrive/.claude-goblin

Database files found:
-rw-r--r-- 1 wangt wangt  1.2M Oct 15 10:30 usage_history_HOME-WT.db
-rw-r--r-- 1 wangt wangt   48K Oct 15 10:30 machines.db

Step 2: Enter target OneDrive path
Enter the full path to your OneDrive directory:
Example: /mnt/d/OneDrive

> /mnt/d/OneDrive

Migration plan:
  From: /mnt/c/Users/wangt/OneDrive/.claude-goblin
  To:   /mnt/d/OneDrive/.claude-goblin

Proceed with migration? [y/N]: y
...
```

## Setup Wizard

The setup wizard now includes OneDrive path confirmation:

**Changes:**
- Prioritizes external drives (D:, E:, F:) over C: drive for OneDrive detection
- Asks user to confirm detected OneDrive path
- Allows user to enter custom path if auto-detection is wrong

**Running setup wizard:**
```bash
ccu config wizard  # Run setup wizard manually
```

The wizard will automatically run on first launch if no configuration exists.
