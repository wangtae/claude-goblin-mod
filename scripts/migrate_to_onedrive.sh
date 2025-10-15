#!/bin/bash
# Migration script to move database files to OneDrive
# This script helps move existing DB files from local storage to OneDrive

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Claude Goblin OneDrive Migration ===${NC}\n"

# Check if running on WSL2
if [[ ! -f /proc/version ]] || ! grep -qi microsoft /proc/version; then
    echo -e "${RED}Error: This script is designed for WSL2 only${NC}"
    exit 1
fi

# Function to check if directory exists
check_dir() {
    if [[ -d "$1" ]]; then
        return 0
    else
        return 1
    fi
}

# Detect current database location
echo -e "${CYAN}Step 1: Detecting current database location${NC}"

# Check common locations
OLD_PATH_1="/mnt/c/Users/$USER/OneDrive/.claude-goblin"
OLD_PATH_2="$HOME/.claude/usage"

OLD_PATH=""
if check_dir "$OLD_PATH_1"; then
    OLD_PATH="$OLD_PATH_1"
    echo -e "${GREEN}Found databases at: $OLD_PATH${NC}"
elif check_dir "$OLD_PATH_2"; then
    OLD_PATH="$OLD_PATH_2"
    echo -e "${GREEN}Found databases at: $OLD_PATH${NC}"
else
    echo -e "${YELLOW}No existing databases found in common locations${NC}"
    echo -e "${YELLOW}Locations checked:${NC}"
    echo "  - $OLD_PATH_1"
    echo "  - $OLD_PATH_2"
    exit 0
fi

# List DB files found
echo -e "\n${CYAN}Database files found:${NC}"
ls -lh "$OLD_PATH"/*.db 2>/dev/null || echo "  (none)"
echo ""

# Ask user for target OneDrive path
echo -e "${CYAN}Step 2: Enter target OneDrive path${NC}"
echo -e "${YELLOW}Enter the full path to your OneDrive directory:${NC}"
echo -e "${YELLOW}Example: /mnt/d/OneDrive${NC}"
echo ""
read -p "> " NEW_ONEDRIVE_ROOT

# Validate target path
if [[ ! -d "$NEW_ONEDRIVE_ROOT" ]]; then
    echo -e "${RED}Error: Directory does not exist: $NEW_ONEDRIVE_ROOT${NC}"
    exit 1
fi

# Construct target path
NEW_PATH="$NEW_ONEDRIVE_ROOT/.claude-goblin"

echo -e "\n${CYAN}Migration plan:${NC}"
echo -e "  ${YELLOW}From:${NC} $OLD_PATH"
echo -e "  ${YELLOW}To:${NC}   $NEW_PATH"
echo ""

# Confirm with user
read -p "Proceed with migration? [y/N]: " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Migration cancelled${NC}"
    exit 0
fi

# Create backup
echo -e "\n${CYAN}Step 3: Creating backup${NC}"
BACKUP_PATH="$OLD_PATH.backup.$(date +%Y%m%d_%H%M%S)"
cp -r "$OLD_PATH" "$BACKUP_PATH"
echo -e "${GREEN}Backup created: $BACKUP_PATH${NC}"

# Create target directory
echo -e "\n${CYAN}Step 4: Creating target directory${NC}"
mkdir -p "$NEW_PATH"
echo -e "${GREEN}Target directory ready: $NEW_PATH${NC}"

# Copy database files
echo -e "\n${CYAN}Step 5: Copying database files${NC}"
cp -v "$OLD_PATH"/*.db "$NEW_PATH/" 2>/dev/null || true

# Verify migration
echo -e "\n${CYAN}Step 6: Verifying migration${NC}"
if [[ -f "$NEW_PATH/machines.db" ]]; then
    echo -e "${GREEN}✓ machines.db migrated successfully${NC}"
else
    echo -e "${YELLOW}⚠ machines.db not found (this is okay if it doesn't exist yet)${NC}"
fi

# Count usage_history DBs
USAGE_DB_COUNT=$(ls "$NEW_PATH"/usage_history_*.db 2>/dev/null | wc -l)
echo -e "${GREEN}✓ Migrated $USAGE_DB_COUNT usage history database(s)${NC}"

# Update config file
echo -e "\n${CYAN}Step 7: Updating configuration${NC}"
CONFIG_FILE="$HOME/.claude/goblin_config.json"

if [[ -f "$CONFIG_FILE" ]]; then
    # Backup config
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"

    # Update db_path in config
    DB_PATH="$NEW_PATH/usage_history.db"
    python3 -c "
import json
import sys

config_file = '$CONFIG_FILE'
db_path = '$DB_PATH'

try:
    with open(config_file, 'r') as f:
        config = json.load(f)

    config['db_path'] = db_path

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print('Config updated successfully')
except Exception as e:
    print(f'Error updating config: {e}', file=sys.stderr)
    sys.exit(1)
"
    echo -e "${GREEN}✓ Configuration updated${NC}"
else
    echo -e "${YELLOW}⚠ Config file not found, skipping update${NC}"
    echo -e "${YELLOW}  You may need to run setup wizard again${NC}"
fi

# Summary
echo -e "\n${GREEN}=== Migration Complete ===${NC}"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo -e "  • Database files migrated to: ${GREEN}$NEW_PATH${NC}"
echo -e "  • Backup saved at: ${YELLOW}$BACKUP_PATH${NC}"
echo -e "  • Config updated: ${GREEN}$CONFIG_FILE${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Test the application: ${YELLOW}ccu usage${NC}"
echo -e "  2. Verify devices are visible: ${YELLOW}ccu devices${NC}"
echo -e "  3. If everything works, you can delete the backup:"
echo -e "     ${YELLOW}rm -rf $BACKUP_PATH${NC}"
echo ""
echo -e "${GREEN}Done!${NC}"
