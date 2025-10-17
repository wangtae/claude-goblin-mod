# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2025-10-17

### Added
- **Data Synchronization Status Check**: New feature in settings menu to verify if local Claude Code source data (JSONL files) matches database records
  - Interactive sync check with `[i]` key in settings
  - Automatic status display with color-coded indicators (green for synced, yellow for issues)
  - Multi-scenario detection:
    - Synced: Timestamps within 1 second, record counts match
    - DB Outdated: Source has newer data with missing record count
    - Multi-PC Sync: Database has more records (another PC may have synced)
    - Integrity Issue: Source is newer but has fewer records
  - Manual sync option with user confirmation
  - Progress indicators with spinners during analysis and sync operations
- Comprehensive version documentation in `docs/versions/1.2.2.md`

### Technical Details
- Added `check_data_sync_status()` function in `src/storage/snapshot_db.py` (lines 3728-3833)
- Modified `src/commands/settings.py` to integrate sync status display and interactive check
- Smart timestamp comparison with 1-second tolerance
- Safe sync process requiring user confirmation

## [1.2.1] - 2025-10-17

### Added
- **Yearly Heatmap Visualization**: Complete year-at-a-glance view in heatmap command
  - Shows 12 months horizontally with weeks vertically
  - 5-level opacity gradient for better visual distinction
  - Table-based layout for square cells and better alignment
  - Month headers and weekday labels
  - Yearly totals at the bottom
- Comprehensive version documentation in `docs/versions/1.2.1.md`

### Changed
- **Heatmap Cell Display**: Improved from Unicode blocks to table-based layout
  - Square-shaped cells (2x2 character spaces)
  - More consistent spacing and alignment
  - Better visual balance across different terminal sizes

### Fixed
- Monthly heatmap alignment issues
- Cell size inconsistencies between monthly and yearly views
- Yearly totals alignment in heatmap display

### Technical Details
- Modified `src/commands/heatmap.py` for yearly heatmap implementation
- Replaced Unicode block characters with Rich Table-based layout
- Added `_generate_yearly_heatmap()` function
- Enhanced color gradient calculation for 5 opacity levels

## [1.2.0] - 2025-10-17

### Added
- **OneDrive Synchronization Improvements**: Enhanced multi-device support
- **Device Statistics**: New command to view usage statistics per device
  - Shows total tokens, prompts, requests, and cost per device
  - Sortable by any column
  - Time range filtering support
- Version tagging and documentation workflow

### Changed
- Improved data synchronization across multiple PCs
- Enhanced database snapshot mechanism

### Technical Details
- Added `src/commands/device_stats.py` for device statistics
- Enhanced `src/storage/snapshot_db.py` for better sync handling

## [1.0.4] - Previous Release

### Initial Fork Features
- Multi-PC support via OneDrive synchronization
- SQLite-based local database for performance
- Rich TUI with interactive dashboard
- Usage analytics and visualization
- Cost tracking and reporting

---

For detailed release notes, see [docs/versions/](docs/versions/) directory.
