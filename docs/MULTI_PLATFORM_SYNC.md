# Multi-Platform Database Synchronization Guide

## Overview

This guide explains how to synchronize Claude Goblin's usage database across multiple computers running different operating systems (Windows, Linux, macOS).

## Key Requirements

### Cross-Platform Compatibility

Claude Goblin's database is designed to work seamlessly across platforms:

✅ **SQLite Database** - Platform-independent binary format
✅ **WAL Mode** - Safe for cloud sync (handles concurrent access)
✅ **UTF-8 Encoding** - Unicode support on all platforms
✅ **POSIX Paths** - Automatically adapted per OS

### Supported Synchronization Methods

| Method | Windows | Linux | macOS | Free Tier | Cross-Platform | Recommendation |
|--------|---------|-------|-------|-----------|----------------|----------------|
| **Google Drive** ⭐⭐⭐ | ✅ | ✅ | ✅ | **15 GB** | ✅ Excellent | **Best Choice** |
| **Dropbox** | ✅ | ✅ | ✅ | 2 GB | ✅ Excellent | Good Alternative |
| **Syncthing** | ✅ | ✅ | ✅ | Unlimited | ✅ Good | Privacy-focused |
| **OneDrive** | ✅ | ⚠️ (3rd-party) | ⚠️ (limited) | 5 GB | ⚠️ Partial | WSL2 only |
| **iCloud Drive** | ❌ | ❌ | ✅ | 5 GB | ❌ macOS Only | Not Recommended |

---

## 🥇 Recommended: Google Drive

**Why Google Drive is the best choice:**

✅ **Generous Free Tier** - 15 GB (vs Dropbox 2GB, OneDrive 5GB)
✅ **Official Cross-Platform Support** - Native apps for Windows, Linux, macOS
✅ **Excellent Sync Performance** - Fast and reliable
✅ **Large User Base** - Well-tested and stable
✅ **Easy Setup** - Minimal configuration needed

---

## Setup: Google Drive (All Platforms)

### Step 1: Install Google Drive Client

#### Windows

1. Download **Google Drive for Desktop**
   - Visit: https://www.google.com/drive/download/
   - Download and install
   - Sign in with your Google account

2. Default folder location:
   ```
   C:\Users\YourName\Google Drive\My Drive\
   ```

#### macOS

1. Download **Google Drive for Desktop**
   - Visit: https://www.google.com/drive/download/
   - Download and install
   - Sign in with your Google account

2. Default folder location:
   ```
   ~/Google Drive/My Drive/
   ```

#### Linux (Ubuntu/Debian)

**Option A: google-drive-ocamlfuse (Recommended)**

```bash
# Add PPA repository
sudo add-apt-repository ppa:alessandro-strada/ppa
sudo apt update

# Install
sudo apt install google-drive-ocamlfuse

# Authenticate (opens browser)
google-drive-ocamlfuse

# Create mount point
mkdir ~/GoogleDrive

# Mount Google Drive
google-drive-ocamlfuse ~/GoogleDrive
```

**Auto-mount on startup:**

Create systemd service:
```bash
mkdir -p ~/.config/systemd/user/
nano ~/.config/systemd/user/google-drive.service
```

Add this content:
```ini
[Unit]
Description=Google Drive Mount
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/google-drive-ocamlfuse %h/GoogleDrive
ExecStop=/bin/fusermount -u %h/GoogleDrive
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable service:
```bash
systemctl --user enable google-drive
systemctl --user start google-drive
```

**Option B: rclone (Advanced)**

```bash
# Install rclone
sudo apt install rclone

# Configure Google Drive
rclone config
# Choose: n (new remote)
# Name: gdrive
# Storage: google drive
# Follow authentication prompts

# Mount (manual)
mkdir ~/GoogleDrive
rclone mount gdrive: ~/GoogleDrive --vfs-cache-mode writes &
```

---

### Step 2: Create Claude Goblin Folder

**On All Platforms:**

Create a dedicated folder for Claude Goblin database:

**Windows (PowerShell):**
```powershell
mkdir "C:\Users\YourName\Google Drive\My Drive\claude-goblin"
```

**macOS (Terminal):**
```bash
mkdir -p ~/Google\ Drive/My\ Drive/claude-goblin
```

**Linux (Terminal):**
```bash
mkdir -p ~/GoogleDrive/claude-goblin
```

---

### Step 3: Configure Claude Goblin

#### Option A: Environment Variable (Recommended)

Set the database path via environment variable:

**Windows (PowerShell):**
```powershell
# Temporary (current session)
$env:CLAUDE_GOBLIN_DB_PATH = "C:\Users\YourName\Google Drive\My Drive\claude-goblin\usage_history.db"

# Permanent (System Settings)
# 1. Open System Properties → Advanced → Environment Variables
# 2. Add new User Variable:
#    Name: CLAUDE_GOBLIN_DB_PATH
#    Value: C:\Users\YourName\Google Drive\My Drive\claude-goblin\usage_history.db
```

**macOS/Linux (Bash/Zsh):**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export CLAUDE_GOBLIN_DB_PATH="$HOME/Google Drive/My Drive/claude-goblin/usage_history.db"' >> ~/.bashrc

# Or for Linux with google-drive-ocamlfuse:
echo 'export CLAUDE_GOBLIN_DB_PATH="$HOME/GoogleDrive/claude-goblin/usage_history.db"' >> ~/.bashrc

# Reload shell config
source ~/.bashrc
```

#### Option B: Config Command

Alternatively, use Claude Goblin's config command:

**Windows:**
```powershell
ccu config set-db-path "C:\Users\YourName\Google Drive\My Drive\claude-goblin\usage_history.db"
```

**macOS:**
```bash
ccu config set-db-path "$HOME/Google Drive/My Drive/claude-goblin/usage_history.db"
```

**Linux:**
```bash
ccu config set-db-path "$HOME/GoogleDrive/claude-goblin/usage_history.db"
```

**Verify configuration:**
```bash
ccu config show
```

---

### Step 4: Set Machine Name (Recommended)

Set a unique name for each PC to track per-machine statistics:

```bash
# Desktop
ccu config set-machine-name "Home-Desktop"

# Laptop
ccu config set-machine-name "Work-Laptop"

# MacBook
ccu config set-machine-name "MacBook-Pro"
```

---

### Step 5: Initialize and Verify Sync

**On First PC (where you have existing data):**

```bash
# Run usage command to create database in Google Drive
ccu usage

# Database will be created at:
# Google Drive/My Drive/claude-goblin/usage_history.db
```

**On Other PCs (after Google Drive syncs):**

1. **Wait for Google Drive to sync** (check sync status in system tray)

2. **Verify database exists:**
   ```bash
   # Windows
   dir "C:\Users\YourName\Google Drive\My Drive\claude-goblin\"

   # macOS/Linux
   ls -la ~/GoogleDrive/claude-goblin/
   # Should show: usage_history.db, usage_history.db-wal, usage_history.db-shm
   ```

3. **Run Claude Goblin:**
   ```bash
   ccu usage

   # Press 'd' to view Devices mode
   # You should see all machines listed
   ```

---

## Multi-Device Example: 3 PCs (Windows + Linux + macOS)

### Scenario

- **PC-A**: Windows 11 Desktop (Home)
- **PC-B**: Ubuntu 24.04 Laptop (Office)
- **PC-C**: macOS Sonoma MacBook (Travel)

### Setup Steps

#### 1. Install Google Drive on All 3 PCs

**PC-A (Windows):**
- Download from https://www.google.com/drive/download/
- Sign in with same Google account

**PC-B (Linux):**
```bash
sudo add-apt-repository ppa:alessandro-strada/ppa
sudo apt update && sudo apt install google-drive-ocamlfuse
google-drive-ocamlfuse
mkdir ~/GoogleDrive
google-drive-ocamlfuse ~/GoogleDrive
```

**PC-C (macOS):**
- Download from https://www.google.com/drive/download/
- Sign in with same Google account

#### 2. Create Shared Folder (do this on ANY one PC)

```bash
# PC-A (Windows PowerShell)
mkdir "C:\Users\Alice\Google Drive\My Drive\claude-goblin"

# Folder will automatically sync to PC-B and PC-C
```

#### 3. Configure Database Path on Each PC

**PC-A (Windows):**
```powershell
$env:CLAUDE_GOBLIN_DB_PATH = "C:\Users\Alice\Google Drive\My Drive\claude-goblin\usage_history.db"

ccu config set-machine-name "Desktop-Windows"
```

**PC-B (Linux):**
```bash
export CLAUDE_GOBLIN_DB_PATH="$HOME/GoogleDrive/claude-goblin/usage_history.db"
echo 'export CLAUDE_GOBLIN_DB_PATH="$HOME/GoogleDrive/claude-goblin/usage_history.db"' >> ~/.bashrc

ccu config set-machine-name "Laptop-Ubuntu"
```

**PC-C (macOS):**
```bash
export CLAUDE_GOBLIN_DB_PATH="$HOME/Google Drive/My Drive/claude-goblin/usage_history.db"
echo 'export CLAUDE_GOBLIN_DB_PATH="$HOME/Google Drive/My Drive/claude-goblin/usage_history.db"' >> ~/.zshrc

ccu config set-machine-name "MacBook-Pro"
```

#### 4. Verify Multi-Device Sync

**On any PC:**
```bash
ccu usage

# Press 'd' for Devices mode
# Expected output:
┌─────────────────┬──────────┬───────────────┬────────────┬──────────────────┐
│ Machine         │ Messages │ Total Tokens  │ Est. Cost  │ Date Range       │
├─────────────────┼──────────┼───────────────┼────────────┼──────────────────┤
│ Desktop-Windows │ 1,234    │ 45.2M         │ $12.34     │ 2025-01-01 to... │
│ Laptop-Ubuntu   │ 567      │ 23.1M         │ $5.67      │ 2025-01-15 to... │
│ MacBook-Pro     │ 890      │ 34.5M         │ $8.90      │ 2025-02-01 to... │
└─────────────────┴──────────┴───────────────┴────────────┴──────────────────┘
```

---

## Database Conflict Resolution

### How Claude Goblin Prevents Conflicts

**Built-in Safeguards:**

1. **WAL Mode** - Write-Ahead Logging allows concurrent reads
   ```sql
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   PRAGMA busy_timeout=30000;  -- 30 second timeout
   ```

2. **UNIQUE Constraint** - Prevents duplicate records
   ```sql
   UNIQUE(session_id, message_uuid)
   ```

3. **INSERT OR IGNORE** - Silently skips duplicates
   ```python
   cursor.execute("""
       INSERT OR IGNORE INTO usage_records (...)
       VALUES (?, ?, ...)
   """, values)
   ```

### Handling Google Drive Conflict Files

**If Google Drive creates a conflict file:**

```
usage_history (1).db
usage_history (conflicted copy).db
```

**Why this happens:**
- Two PCs wrote to database at exact same time
- Google Drive couldn't merge changes automatically
- Cloud service created a copy to preserve both versions

**Resolution Steps:**

1. **Check which file has most recent data:**
   ```bash
   # Main file
   ccu stats

   # Conflict file
   ccu config set-db-path "~/GoogleDrive/claude-goblin/usage_history (1).db"
   ccu stats
   ```

2. **Compare record counts and date ranges:**
   - Keep the file with more records
   - Or keep the file with more recent data

3. **Merge manually (if needed):**
   ```bash
   # TODO: Future feature
   ccu merge-db "~/GoogleDrive/claude-goblin/usage_history (1).db"
   ```

4. **Reset to main file and delete conflict:**
   ```bash
   ccu config clear-db-path
   rm "~/GoogleDrive/claude-goblin/usage_history (1).db"
   ```

### Best Practices to Avoid Conflicts

✅ **DO:**
- Let Google Drive finish syncing before shutting down PC
- Use unique machine names on each PC
- Keep all PCs running same Claude Goblin version
- Check Google Drive sync status before running `ccu usage`

❌ **DON'T:**
- Run `ccu usage` on multiple PCs simultaneously (wait 1-2 minutes between)
- Force-quit during database writes
- Manually edit database files
- Mix different sync services (stick to Google Drive)

---

## Troubleshooting

### Problem: Database not syncing between PCs

**Check 1: Verify Google Drive is syncing**

**Windows:**
- Check system tray icon (should show synced status)
- Right-click file → Properties → Check sync status

**macOS:**
- Check menu bar icon
- Right-click file → Get Info → Check sync status

**Linux:**
```bash
# google-drive-ocamlfuse
df -h | grep GoogleDrive

# rclone
ps aux | grep rclone
```

**Check 2: Verify database path is correct**
```bash
ccu config show

# Should show Google Drive path, NOT local path:
# ✅ Database Path: ~/GoogleDrive/claude-goblin/usage_history.db
# ❌ Database Path: ~/.claude/usage/usage_history.db
```

**Check 3: Manually check file exists**
```bash
# Windows (PowerShell)
Get-ChildItem "C:\Users\YourName\Google Drive\My Drive\claude-goblin\"

# macOS/Linux
ls -lah ~/GoogleDrive/claude-goblin/
# Should show: usage_history.db (main), .db-wal (WAL), .db-shm (shared memory)
```

---

### Problem: "Database locked" error

**Cause**: Another instance or cloud sync is accessing the database

**Solution 1: Wait for Google Drive sync to complete**
```bash
# Check sync status in system tray/menu bar
# Wait 10-30 seconds for sync to finish
```

**Solution 2: Check for zombie processes**

**Windows (PowerShell):**
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
# If found: Stop-Process -Id <PID>
```

**macOS/Linux:**
```bash
ps aux | grep ccu
# If found: kill <PID>
```

**Solution 3: Check WAL checkpoint**
```bash
# WAL files can grow large if not checkpointed
# Restart ccu to force checkpoint:
ccu stats
```

---

### Problem: Different data on each PC

**Cause**: Each PC is using different database (not synced)

**Diagnosis:**
```bash
# On each PC, check:
ccu config show

# PC-A shows: ~/.claude/usage/usage_history.db  ← Wrong (local)
# PC-B shows: ~/GoogleDrive/claude-goblin/usage_history.db  ← Correct
```

**Solution: Reconfigure all PCs to use Google Drive path**
```bash
# On each PC with wrong path:
ccu config set-db-path ~/GoogleDrive/claude-goblin/usage_history.db

# Or set environment variable (permanent):
echo 'export CLAUDE_GOBLIN_DB_PATH="$HOME/GoogleDrive/claude-goblin/usage_history.db"' >> ~/.bashrc
source ~/.bashrc
```

---

### Problem: Google Drive sync is slow

**Cause**: Large WAL files or network issues

**Solution 1: Force WAL checkpoint**
```bash
# This merges WAL into main database
ccu update-usage
```

**Solution 2: Check Google Drive network settings**
- Windows/macOS: Google Drive preferences → Network settings
- Increase upload/download bandwidth limits
- Check "Sync everything" is enabled

**Solution 3: Verify file sizes**
```bash
ls -lh ~/GoogleDrive/claude-goblin/

# Expected sizes:
# usage_history.db      : ~5-50 MB (depends on usage)
# usage_history.db-wal  : ~1-5 MB (should checkpoint regularly)
# usage_history.db-shm  : ~32 KB (small shared memory file)

# If WAL is > 10 MB, run:
ccu update-usage  # Forces checkpoint
```

---

## Performance Considerations

### Google Drive Sync Performance

**Typical Sync Latency:**
- **Windows/macOS**: ~10-30 seconds between write and sync
- **Linux (ocamlfuse)**: ~30-60 seconds
- **Network dependent**: Faster on high-speed connections

**Database Size Impact:**
- 1 year of usage: ~5-10 MB
- 5 years of usage: ~25-50 MB
- WAL files: ~1-5 MB (temporary)
- Total: ~30-55 MB for 5 years

**Optimization Tips:**
1. **Enable selective sync** only for `claude-goblin` folder (if using Google Drive for other files)
2. **Use SSD** for Google Drive folder location
3. **Schedule intensive syncs** during off-peak hours

---

## Migration Guide

### Moving from Local to Google Drive

**Step 1: Backup existing database**
```bash
cp ~/.claude/usage/usage_history.db ~/.claude/usage/usage_history.backup.db
```

**Step 2: Copy to Google Drive**

**Windows:**
```powershell
Copy-Item "$env:USERPROFILE\.claude\usage\usage_history.db" "C:\Users\YourName\Google Drive\My Drive\claude-goblin\usage_history.db"
```

**macOS/Linux:**
```bash
cp ~/.claude/usage/usage_history.db ~/GoogleDrive/claude-goblin/usage_history.db
```

**Step 3: Update configuration**
```bash
ccu config set-db-path ~/GoogleDrive/claude-goblin/usage_history.db
```

**Step 4: Verify**
```bash
ccu stats
# Should show same data as before migration
```

**Step 5: Setup on other PCs**
```bash
# Wait for Google Drive to sync database file (check sync status)
# Then configure path:
ccu config set-db-path ~/GoogleDrive/claude-goblin/usage_history.db
ccu usage
```

---

### Moving from OneDrive to Google Drive

```bash
# Step 1: Copy database
cp /mnt/d/OneDrive/.claude-goblin/usage_history.db ~/GoogleDrive/claude-goblin/usage_history.db

# Step 2: Update config
ccu config set-db-path ~/GoogleDrive/claude-goblin/usage_history.db

# Step 3: Verify
ccu stats
```

---

## Security & Privacy

### Data Encryption

**Google Drive:**
- ✅ Encrypted in transit (HTTPS)
- ✅ Encrypted at rest on Google servers
- ⚠️ Google can technically access data (encrypted with their keys)
- 💡 Future feature: Client-side encryption before upload

### Data Privacy

**What's stored in the database:**
- ✅ Token usage statistics (numbers only)
- ✅ Project folder names (can be anonymized)
- ✅ Model names (claude-sonnet-4, etc.)
- ✅ Timestamps and dates
- ❌ NO conversation contents
- ❌ NO API keys or credentials
- ❌ NO code from your projects

**Enable anonymization:**
```bash
ccu usage --anon
# Shows: project-001, project-002 instead of real folder names
```

---

## FAQ

### Can I use different Google accounts on different PCs?

❌ **No** - All PCs must be signed into the **same Google account** to share the database.

### Can I sync with both Google Drive and OneDrive?

❌ **No** - Choose one cloud service and stick with it. Using multiple services will create separate databases.

### What happens if I'm offline?

✅ **Local changes are saved** - Database writes work offline
⚠️ **Syncs when online** - Changes upload when Google Drive reconnects
✅ **Automatic merge** - UNIQUE constraint prevents duplicates when syncs occur

### Do all PCs need to be online at the same time?

❌ **No** - Google Drive acts as intermediary
- Each PC syncs independently with Google's cloud
- Changes propagate when each PC comes online

### Can I access the database on mobile?

⚠️ **View only** - Google Drive app can show the database file
❌ **Can't run Claude Goblin** - No mobile version available (yet)
💡 **Future feature** - Mobile dashboard for viewing stats

### How much Google Drive storage does this use?

📊 **Very little** - Typical usage:
- 1 year: ~5-10 MB
- 5 years: ~25-50 MB
- Still have **14.9+ GB** free for other files

---

## Alternative Methods

### Option 2: Dropbox

**Pros:**
- Official Linux client
- Excellent sync reliability
- Good performance

**Cons:**
- Only 2 GB free (vs Google Drive 15 GB)
- Limited device count on free tier

**Setup:**
```bash
# Install Dropbox
# Windows/macOS: https://www.dropbox.com/install
# Linux:
cd ~ && wget -O - "https://www.dropbox.com/download?plat=lnx.x86_64" | tar xzf -
~/.dropbox-dist/dropboxd

# Configure path
ccu config set-db-path ~/Dropbox/claude-goblin/usage_history.db
```

---

### Option 3: Syncthing (Privacy-focused)

**Pros:**
- ✅ Unlimited storage
- ✅ Complete privacy (P2P, no cloud)
- ✅ Open source

**Cons:**
- ⚠️ Devices must be online simultaneously for sync
- ⚠️ More complex setup
- ⚠️ No cloud backup

**Setup:**
```bash
# Install Syncthing
# Windows: https://syncthing.net/downloads/
# Linux: sudo apt install syncthing
# macOS: brew install syncthing

# Access Web UI: http://localhost:8384
# Add folder: ~/Sync/claude-goblin
# Exchange device IDs between PCs
# Share folder

# Configure path
ccu config set-db-path ~/Sync/claude-goblin/usage_history.db
```

---

## Roadmap

### Planned Features

**v1.1: Conflict Resolver Tool**
```bash
ccu merge-db ~/GoogleDrive/claude-goblin/usage_history\ (1).db
# Automatically merge conflict databases
```

**v1.2: Encrypted Database**
```bash
ccu config set-encryption-key
# Encrypt database before cloud upload
# Provides client-side encryption
```

**v1.3: Selective Sync**
```bash
ccu config set-sync-mode selective
# Only sync aggregated data, not individual records
# Reduces database size for low-storage situations
```

**v1.4: Mobile Dashboard**
- View-only mobile app
- Check usage stats on phone
- Read from Google Drive database

---

## Support

### Getting Help

- **GitHub Issues**: https://github.com/yourusername/claude-goblin-mod/issues
- **Documentation**: https://github.com/yourusername/claude-goblin-mod/docs/

### Reporting Sync Issues

Please include:
1. Cloud service used (Google Drive/Dropbox/Syncthing)
2. Operating systems of all PCs (Windows 11, Ubuntu 24.04, macOS Sonoma, etc.)
3. Database path (`ccu config show`)
4. Google Drive client version
5. Error messages (full output)
6. Steps to reproduce

---

## Conclusion

**Recommended Setup for Most Users:**

1. ✅ Install **Google Drive** on all devices (Windows, Linux, macOS)
2. ✅ Create `claude-goblin` folder in Google Drive
3. ✅ Set `CLAUDE_GOBLIN_DB_PATH` environment variable on all PCs
4. ✅ Set unique machine names: `ccu config set-machine-name`
5. ✅ Run `ccu usage` and verify sync

**Result:**
- ✅ All your Claude Code usage data synced across all computers
- ✅ Per-machine statistics in Devices mode (`d` key)
- ✅ Zero configuration beyond initial setup
- ✅ 15 GB free storage (plenty for years of data)
- ✅ Works reliably on Windows, Linux, and macOS

**Next Steps:**
- Read [Installation Guide](INSTALLATION.md)
- See [Multi-PC Implementation Plan](MULTI_PC_IMPLEMENTATION_PLAN.md)
- Check [README](../README.md) for command reference
