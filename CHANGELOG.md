# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-10-11

### Fixed
- **CRITICAL**: Fixed data loss bug in "full" storage mode where `daily_snapshots` were being recalculated from scratch, causing historical data to be lost when JSONL files aged out (30-day window)
- Now only updates `daily_snapshots` for dates that currently have records, preserving all historical data forever

### Changed
- Migrated CLI from manual `sys.argv` parsing to `typer` for better UX and automatic help generation
- Updated command syntax: `claude-goblin <command>` instead of `claude-goblin --<command>`
  - Old: `claude-goblin --usage` → New: `claude-goblin usage`
  - Old: `claude-goblin --stats` → New: `claude-goblin stats`
  - Old: `claude-goblin --export` → New: `claude-goblin export`
  - All other commands follow the same pattern
- Updated hooks to use new command syntax (`claude-goblin update-usage` instead of `claude-goblin --update-usage`)
- Improved help messages with examples and better descriptions

### Added
- Added `typer>=0.9.0` as a dependency for CLI framework
- Added backward compatibility in hooks to recognize both old and new command syntax

## [0.1.0] - 2025-10-10

### Added
- Initial release
- Usage tracking and analytics for Claude Code
- GitHub-style activity heatmap visualization
- TUI dashboard with real-time stats
- Cost analysis and API pricing comparison
- Export functionality (PNG/SVG)
- Hook integration for automatic tracking
- macOS menu bar app for usage monitoring
- Support for both "aggregate" and "full" storage modes
- Historical database preservation (SQLite)
- Text analysis (politeness markers, phrase counting)
- Model and project breakdown statistics
