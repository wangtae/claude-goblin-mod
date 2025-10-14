#region Imports
import os
import platform
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.usage_record import UsageRecord
#endregion


#region Constants and Path Detection

def _try_create_folder(path: Path) -> bool:
    """
    Try to create folder. Return True if successful or already exists.

    Args:
        path: Path to folder to create

    Returns:
        True if folder exists or was created successfully, False otherwise
    """
    try:
        # Check if parent exists (e.g., OneDrive root)
        if path.parent.parent.exists():
            path.mkdir(parents=True, exist_ok=True)
            return True
        elif path.exists():
            return True
    except (PermissionError, OSError):
        pass
    return False


def get_default_db_path() -> Path:
    """
    Auto-detect OneDrive/iCloud and use it for database storage.
    Falls back to local storage if cloud storage is not available.

    Priority:
    1. Config file: user_config.get_db_path()
    2. Environment variable: CLAUDE_GOBLIN_DB_PATH
    3. OneDrive (WSL2): /mnt/c/Users/{username}/OneDrive/.claude-goblin/ or /mnt/d/OneDrive/.claude-goblin/
    4. iCloud (macOS): ~/Library/Mobile Documents/com~apple~CloudDocs/.claude-goblin/
    5. Local fallback: ~/.claude/usage/

    Returns:
        Path to the database file
    """
    # 1. Config file override
    try:
        from src.config.user_config import get_db_path
        config_path = get_db_path()
        if config_path:
            return Path(config_path)
    except ImportError:
        pass  # Config module not available yet (first install)

    # 2. Environment variable override
    custom_path = os.getenv("CLAUDE_GOBLIN_DB_PATH")
    if custom_path:
        return Path(custom_path)

    # 3. WSL2 OneDrive detection
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        username = os.getenv("USER")

        # Try multiple common OneDrive locations
        onedrive_candidates = []

        if username:
            # Standard Windows user profile location
            onedrive_candidates.append(Path(f"/mnt/c/Users/{username}/OneDrive"))

        # Check all mounted drives (C:, D:, E:, etc.)
        for drive in ["c", "d", "e", "f"]:
            onedrive_candidates.append(Path(f"/mnt/{drive}/OneDrive"))

        # Try each candidate
        for onedrive_base in onedrive_candidates:
            if onedrive_base.exists():
                onedrive_path = onedrive_base / ".claude-goblin" / "usage_history.db"

                if _try_create_folder(onedrive_path.parent):
                    return onedrive_path

    # 4. macOS iCloud Drive detection
    elif platform.system() == "Darwin":
        icloud_base = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"

        if icloud_base.exists():
            icloud_path = icloud_base / ".claude-goblin" / "usage_history.db"

            if _try_create_folder(icloud_path.parent):
                return icloud_path

    # 5. Local fallback
    return Path.home() / ".claude" / "usage" / "usage_history.db"


# Initialize default path
DEFAULT_DB_PATH = get_default_db_path()

#endregion


#region Functions


def init_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    Initialize the SQLite database for historical snapshots.

    Creates tables if they don't exist:
    - daily_snapshots: Daily aggregated usage data
    - usage_records: Individual usage records for detailed analysis

    Enables WAL mode for better concurrent access (safe for multi-PC OneDrive sync).

    Args:
        db_path: Path to the SQLite database file

    Raises:
        sqlite3.Error: If database initialization fails
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30.0)  # 30 second timeout for OneDrive sync
    try:
        cursor = conn.cursor()

        # Enable WAL mode for better concurrent access
        # WAL allows multiple readers and one writer simultaneously
        # Safe for OneDrive sync as WAL files sync properly
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")  # Faster while still safe
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout

        # Table for daily aggregated snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                date TEXT PRIMARY KEY,
                total_prompts INTEGER NOT NULL,
                total_responses INTEGER NOT NULL,
                total_sessions INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cache_creation_tokens INTEGER NOT NULL,
                cache_read_tokens INTEGER NOT NULL,
                snapshot_timestamp TEXT NOT NULL
            )
        """)

        # Table for detailed usage records
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
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cache_creation_tokens INTEGER NOT NULL,
                cache_read_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                machine_name TEXT,
                UNIQUE(session_id, message_uuid)
            )
        """)

        # Migration: Add machine_name column if it doesn't exist
        cursor.execute("PRAGMA table_info(usage_records)")
        columns = [row[1] for row in cursor.fetchall()]
        if "machine_name" not in columns:
            cursor.execute("ALTER TABLE usage_records ADD COLUMN machine_name TEXT")

        # Index for faster date-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_records_date
            ON usage_records(date)
        """)

        # Table for usage limits snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS limits_snapshots (
                timestamp TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                session_pct INTEGER,
                week_pct INTEGER,
                opus_pct INTEGER,
                session_reset TEXT,
                week_reset TEXT,
                opus_reset TEXT
            )
        """)

        # Index for faster date-based queries on limits
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_limits_snapshots_date
            ON limits_snapshots(date)
        """)

        # Table for model pricing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_pricing (
                model_name TEXT PRIMARY KEY,
                input_price_per_mtok REAL NOT NULL,
                output_price_per_mtok REAL NOT NULL,
                cache_write_price_per_mtok REAL NOT NULL,
                cache_read_price_per_mtok REAL NOT NULL,
                last_updated TEXT NOT NULL,
                notes TEXT
            )
        """)

        # Table for user preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert default preferences
        default_prefs = [
            ('usage_display_mode', '0'),           # M1=0, M2=1, M3=2, M4=3
            ('color_mode', 'gradient'),            # solid | gradient
            ('color_solid', '#00A7E1'),            # bright_blue
            ('color_gradient_low', '#00C853'),     # green
            ('color_gradient_mid', '#FFD600'),     # yellow
            ('color_gradient_high', '#FF1744'),    # red
            ('color_unfilled', '#424242'),         # grey
            ('storage_mode', 'aggregate'),         # aggregate | detail
            ('tracking_mode', 'both'),             # both | usage | limits
            ('machine_name', ''),                  # custom name or empty
            ('db_path', ''),                       # custom path or empty
            ('anonymize_projects', '0'),           # 0=off, 1=on
        ]

        for key, value in default_prefs:
            cursor.execute("""
                INSERT OR IGNORE INTO user_preferences (key, value)
                VALUES (?, ?)
            """, (key, value))

        # Populate pricing data for known models
        pricing_data = [
            # Current models
            ('claude-opus-4-1-20250805', 15.00, 75.00, 18.75, 1.50, 'Current flagship model'),
            ('claude-sonnet-4-5-20250929', 3.00, 15.00, 3.75, 0.30, 'Current balanced model (≤200K tokens)'),
            ('claude-haiku-3-5-20241022', 0.80, 4.00, 1.00, 0.08, 'Current fast model'),

            # Legacy models (approximate pricing)
            ('claude-sonnet-4-20250514', 3.00, 15.00, 3.75, 0.30, 'Legacy Sonnet 4'),
            ('claude-opus-4-20250514', 15.00, 75.00, 18.75, 1.50, 'Legacy Opus 4'),
            ('claude-sonnet-3-7-20250219', 3.00, 15.00, 3.75, 0.30, 'Legacy Sonnet 3.7'),

            # Synthetic/test models
            ('<synthetic>', 0.00, 0.00, 0.00, 0.00, 'Test/synthetic model - no cost'),
        ]

        timestamp = datetime.now().isoformat()
        for model_name, input_price, output_price, cache_write, cache_read, notes in pricing_data:
            cursor.execute("""
                INSERT OR REPLACE INTO model_pricing (
                    model_name, input_price_per_mtok, output_price_per_mtok,
                    cache_write_price_per_mtok, cache_read_price_per_mtok,
                    last_updated, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (model_name, input_price, output_price, cache_write, cache_read, timestamp, notes))

        conn.commit()
    finally:
        conn.close()


def save_snapshot(records: list[UsageRecord], db_path: Path = DEFAULT_DB_PATH, storage_mode: str = "aggregate") -> int:
    """
    Save usage records to the database as a snapshot.

    Only saves records that don't already exist (based on session_id + message_uuid).
    Also updates daily_snapshots table with aggregated data.

    Args:
        records: List of usage records to save
        db_path: Path to the SQLite database file
        storage_mode: "aggregate" (daily totals only) or "full" (individual records)

    Returns:
        Number of new records saved

    Raises:
        sqlite3.Error: If database operation fails
    """
    if not records:
        return 0

    init_database(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)
    saved_count = 0

    try:
        cursor = conn.cursor()

        # Save individual records only if in "full" mode
        if storage_mode == "full":
            # Get machine name once for all records
            from src.config.user_config import get_machine_name
            machine_name = get_machine_name()

            for record in records:
                # Get token values (0 for user messages without token_usage)
                input_tokens = record.token_usage.input_tokens if record.token_usage else 0
                output_tokens = record.token_usage.output_tokens if record.token_usage else 0
                cache_creation_tokens = record.token_usage.cache_creation_tokens if record.token_usage else 0
                cache_read_tokens = record.token_usage.cache_read_tokens if record.token_usage else 0
                total_tokens = record.token_usage.total_tokens if record.token_usage else 0

                try:
                    cursor.execute("""
                        INSERT INTO usage_records (
                            date, timestamp, session_id, message_uuid, message_type,
                            model, folder, git_branch, version,
                            input_tokens, output_tokens,
                            cache_creation_tokens, cache_read_tokens, total_tokens,
                            machine_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.date_key,
                        record.timestamp.isoformat(),
                        record.session_id,
                        record.message_uuid,
                        record.message_type,
                        record.model,
                        record.folder,
                        record.git_branch,
                        record.version,
                        input_tokens,
                        output_tokens,
                        cache_creation_tokens,
                        cache_read_tokens,
                        total_tokens,
                        machine_name,
                    ))
                    saved_count += 1
                except sqlite3.IntegrityError:
                    # Record already exists, skip it
                    pass

        # Update daily snapshots (aggregate by date)
        if storage_mode == "full":
            # In full mode, only update dates that have records in usage_records
            # IMPORTANT: Never use REPLACE - it would delete old data when JSONL files age out
            # Instead, recalculate only for dates that currently have records
            timestamp = datetime.now().isoformat()

            # Get all dates that currently have usage_records
            cursor.execute("SELECT DISTINCT date FROM usage_records")
            dates_with_records = [row[0] for row in cursor.fetchall()]

            for date in dates_with_records:
                # Calculate totals for this date from usage_records
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN message_type = 'user' THEN 1 ELSE 0 END) as total_prompts,
                        SUM(CASE WHEN message_type = 'assistant' THEN 1 ELSE 0 END) as total_responses,
                        COUNT(DISTINCT session_id) as total_sessions,
                        SUM(total_tokens) as total_tokens,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        SUM(cache_creation_tokens) as cache_creation_tokens,
                        SUM(cache_read_tokens) as cache_read_tokens
                    FROM usage_records
                    WHERE date = ?
                """, (date,))

                row = cursor.fetchone()

                # Use INSERT OR REPLACE only for dates that currently have data
                # This preserves historical daily_snapshots for dates no longer in usage_records
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_snapshots (
                        date, total_prompts, total_responses, total_sessions, total_tokens,
                        input_tokens, output_tokens, cache_creation_tokens,
                        cache_read_tokens, snapshot_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date,
                    row[0] or 0,
                    row[1] or 0,
                    row[2] or 0,
                    row[3] or 0,
                    row[4] or 0,
                    row[5] or 0,
                    row[6] or 0,
                    row[7] or 0,
                    timestamp,
                ))
        else:
            # In aggregate mode, compute from incoming records
            from collections import defaultdict
            daily_aggregates = defaultdict(lambda: {
                "prompts": 0,
                "responses": 0,
                "sessions": set(),
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
            })

            for record in records:
                date_key = record.date_key
                daily_aggregates[date_key]["sessions"].add(record.session_id)

                # Count message types
                if record.is_user_prompt:
                    daily_aggregates[date_key]["prompts"] += 1
                elif record.is_assistant_response:
                    daily_aggregates[date_key]["responses"] += 1

                # Token usage only on assistant messages
                if record.token_usage:
                    daily_aggregates[date_key]["input_tokens"] += record.token_usage.input_tokens
                    daily_aggregates[date_key]["output_tokens"] += record.token_usage.output_tokens
                    daily_aggregates[date_key]["cache_creation_tokens"] += record.token_usage.cache_creation_tokens
                    daily_aggregates[date_key]["cache_read_tokens"] += record.token_usage.cache_read_tokens
                    daily_aggregates[date_key]["total_tokens"] += record.token_usage.total_tokens

            # Insert or update daily snapshots
            timestamp = datetime.now().isoformat()
            for date_key, agg in daily_aggregates.items():
                # Get existing data for this date to merge with new data
                cursor.execute("""
                    SELECT total_prompts, total_responses, total_sessions, total_tokens,
                           input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
                    FROM daily_snapshots WHERE date = ?
                """, (date_key,))
                existing = cursor.fetchone()

                if existing:
                    # Merge with existing (add to existing totals)
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_snapshots (
                            date, total_prompts, total_responses, total_sessions, total_tokens,
                            input_tokens, output_tokens, cache_creation_tokens,
                            cache_read_tokens, snapshot_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        date_key,
                        existing[0] + agg["prompts"],
                        existing[1] + agg["responses"],
                        existing[2] + len(agg["sessions"]),
                        existing[3] + agg["total_tokens"],
                        existing[4] + agg["input_tokens"],
                        existing[5] + agg["output_tokens"],
                        existing[6] + agg["cache_creation_tokens"],
                        existing[7] + agg["cache_read_tokens"],
                        timestamp,
                    ))
                else:
                    # New date, insert fresh
                    cursor.execute("""
                        INSERT INTO daily_snapshots (
                            date, total_prompts, total_responses, total_sessions, total_tokens,
                            input_tokens, output_tokens, cache_creation_tokens,
                            cache_read_tokens, snapshot_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        date_key,
                        agg["prompts"],
                        agg["responses"],
                        len(agg["sessions"]),
                        agg["total_tokens"],
                        agg["input_tokens"],
                        agg["output_tokens"],
                        agg["cache_creation_tokens"],
                        agg["cache_read_tokens"],
                        timestamp,
                    ))
                saved_count += 1

        conn.commit()
    finally:
        conn.close()

    return saved_count


def save_limits_snapshot(
    session_pct: int,
    week_pct: int,
    opus_pct: int,
    session_reset: str,
    week_reset: str,
    opus_reset: str,
    db_path: Path = DEFAULT_DB_PATH
) -> None:
    """
    Save usage limits snapshot to the database.

    Args:
        session_pct: Session usage percentage
        week_pct: Week (all models) usage percentage
        opus_pct: Opus usage percentage
        session_reset: Session reset time
        week_reset: Week reset time
        opus_reset: Opus reset time
        db_path: Path to the SQLite database file

    Raises:
        sqlite3.Error: If database operation fails
    """
    init_database(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT OR REPLACE INTO limits_snapshots (
                timestamp, date, session_pct, week_pct, opus_pct,
                session_reset, week_reset, opus_reset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            date,
            session_pct,
            week_pct,
            opus_pct,
            session_reset,
            week_reset,
            opus_reset,
        ))

        conn.commit()
    finally:
        conn.close()


def load_historical_records(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH
) -> list[UsageRecord]:
    """
    Load historical usage records from the database.

    Reads from usage_records table if available (full mode).
    Falls back to daily_snapshots if usage_records is empty (aggregate mode from other PC).

    Args:
        start_date: Optional start date in YYYY-MM-DD format (inclusive)
        end_date: Optional end date in YYYY-MM-DD format (inclusive)
        db_path: Path to the SQLite database file

    Returns:
        List of UsageRecord objects

    Raises:
        sqlite3.Error: If database query fails
    """
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()

        # Try usage_records first (full mode)
        query = "SELECT * FROM usage_records WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date, timestamp"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # If usage_records has data, use it
        if rows:
            records = []
            from src.models.usage_record import TokenUsage

            for row in rows:
                # Parse the row into a UsageRecord
                # Row columns: id, date, timestamp, session_id, message_uuid, message_type,
                #              model, folder, git_branch, version,
                #              input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, total_tokens

                # Only create TokenUsage if tokens exist (assistant messages)
                token_usage = None
                if row[10] > 0 or row[11] > 0:  # if input_tokens or output_tokens exist
                    token_usage = TokenUsage(
                        input_tokens=row[10],
                        output_tokens=row[11],
                        cache_creation_tokens=row[12],
                        cache_read_tokens=row[13],
                    )

                record = UsageRecord(
                    timestamp=datetime.fromisoformat(row[2]),
                    session_id=row[3],
                    message_uuid=row[4],
                    message_type=row[5],
                    model=row[6],
                    folder=row[7],
                    git_branch=row[8],
                    version=row[9],
                    token_usage=token_usage,
                )
                records.append(record)

            return records

        # Fall back to daily_snapshots (aggregate mode from other PC)
        query = "SELECT * FROM daily_snapshots WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        cursor.execute(query, params)
        snapshot_rows = cursor.fetchall()

        if not snapshot_rows:
            return []

        # Convert daily_snapshots to synthetic UsageRecord objects
        # Row columns: date, total_prompts, total_responses, total_sessions, total_tokens,
        #              input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, snapshot_timestamp
        records = []
        from src.models.usage_record import TokenUsage

        for row in snapshot_rows:
            date = row[0]
            total_responses = row[2]
            input_tokens = row[5]
            output_tokens = row[6]
            cache_creation_tokens = row[7]
            cache_read_tokens = row[8]

            # Create one synthetic record per day representing aggregated assistant responses
            if total_responses > 0:
                token_usage = TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    cache_read_tokens=cache_read_tokens,
                )

                # Use date as both timestamp and session_id (aggregated data)
                timestamp = datetime.fromisoformat(f"{date}T12:00:00+00:00")

                record = UsageRecord(
                    timestamp=timestamp,
                    session_id=f"aggregated-{date}",
                    message_uuid=f"aggregated-{date}",
                    message_type="assistant",
                    model=None,  # Model info not available in aggregate mode
                    folder="unknown",
                    git_branch=None,
                    version="unknown",
                    token_usage=token_usage,
                )
                records.append(record)

        return records
    finally:
        conn.close()


def get_text_analysis_stats(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """
    Analyze message content from JSONL files for text statistics.

    Returns:
        Dictionary with text analysis statistics
    """
    from src.config.settings import get_claude_jsonl_files
    from src.data.jsonl_parser import parse_all_jsonl_files
    from src.utils.text_analysis import (
        count_swears,
        count_perfect_phrases,
        count_absolutely_right_phrases,
        count_thank_phrases,
        count_please_phrases,
    )

    try:
        # Get current JSONL files
        jsonl_files = get_claude_jsonl_files()
        if not jsonl_files:
            return {
                "user_swears": 0,
                "assistant_swears": 0,
                "perfect_count": 0,
                "absolutely_right_count": 0,
                "user_thanks": 0,
                "user_please": 0,
                "avg_user_prompt_chars": 0,
                "total_user_chars": 0,
            }

        # Parse all records
        records = parse_all_jsonl_files(jsonl_files)

        user_swears = 0
        assistant_swears = 0
        perfect_count = 0
        absolutely_right_count = 0
        user_thanks = 0
        user_please = 0
        total_user_chars = 0
        user_prompt_count = 0

        for record in records:
            if not record.content:
                continue

            if record.is_user_prompt:
                user_swears += count_swears(record.content)
                user_thanks += count_thank_phrases(record.content)
                user_please += count_please_phrases(record.content)
                total_user_chars += record.char_count
                user_prompt_count += 1
            elif record.is_assistant_response:
                assistant_swears += count_swears(record.content)
                perfect_count += count_perfect_phrases(record.content)
                absolutely_right_count += count_absolutely_right_phrases(record.content)

        avg_user_prompt_chars = total_user_chars / user_prompt_count if user_prompt_count > 0 else 0

        return {
            "user_swears": user_swears,
            "assistant_swears": assistant_swears,
            "perfect_count": perfect_count,
            "absolutely_right_count": absolutely_right_count,
            "user_thanks": user_thanks,
            "user_please": user_please,
            "avg_user_prompt_chars": round(avg_user_prompt_chars),
            "total_user_chars": total_user_chars,
        }
    except Exception:
        # Return zeros if analysis fails
        return {
            "user_swears": 0,
            "assistant_swears": 0,
            "perfect_count": 0,
            "absolutely_right_count": 0,
            "user_thanks": 0,
            "user_please": 0,
            "avg_user_prompt_chars": 0,
            "total_user_chars": 0,
        }


def get_limits_data(db_path: Path = DEFAULT_DB_PATH) -> dict[str, dict[str, int]]:
    """
    Get daily maximum limits percentages from the database.

    Returns a dictionary mapping dates to their max limits:
    {
        "2025-10-11": {"week_pct": 14, "opus_pct": 8},
        ...
    }

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary mapping dates to max week_pct and opus_pct for that day
    """
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()

        # Get max week_pct and opus_pct per day
        cursor.execute("""
            SELECT
                date,
                MAX(week_pct) as max_week,
                MAX(opus_pct) as max_opus
            FROM limits_snapshots
            GROUP BY date
            ORDER BY date
        """)

        return {
            row[0]: {
                "week_pct": row[1] or 0,
                "opus_pct": row[2] or 0
            }
            for row in cursor.fetchall()
        }
    finally:
        conn.close()


def get_latest_limits(db_path: Path = DEFAULT_DB_PATH) -> dict | None:
    """
    Get the most recent limits snapshot from the database.

    Returns a dictionary with the latest limits data:
    {
        "session_pct": 14,
        "week_pct": 18,
        "opus_pct": 8,
        "session_reset": "Oct 16, 10:59am (Europe/Brussels)",
        "week_reset": "Oct 18, 3pm (Europe/Brussels)",
        "opus_reset": "Oct 18, 3pm (Europe/Brussels)",
    }

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary with latest limits, or None if no data exists
    """
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()

        # Get most recent limits snapshot
        cursor.execute("""
            SELECT session_pct, week_pct, opus_pct,
                   session_reset, week_reset, opus_reset
            FROM limits_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "session_pct": row[0] or 0,
            "week_pct": row[1] or 0,
            "opus_pct": row[2] or 0,
            "session_reset": row[3] or "",
            "week_reset": row[4] or "",
            "opus_reset": row[5] or "",
        }
    finally:
        conn.close()


def get_device_statistics(db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """
    Get usage statistics grouped by device/machine.

    Returns:
        List of dictionaries with device statistics:
        [
            {
                "machine_name": "PC-A",
                "total_records": 5000,
                "total_sessions": 10,
                "total_messages": 1000,
                "total_tokens": 50000000,
                "input_tokens": 10000,
                "output_tokens": 40000,
                "cache_creation_tokens": 5000000,
                "cache_read_tokens": 45000000,
                "total_cost": 123.45,
                "oldest_date": "2025-09-14",
                "newest_date": "2025-10-14",
            },
            ...
        ]
    """
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()

        # Get statistics by machine
        cursor.execute("""
            SELECT
                COALESCE(machine_name, 'Unknown') as machine,
                COUNT(*) as total_records,
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(CASE WHEN message_type = 'assistant' THEN 1 END) as total_messages,
                SUM(total_tokens) as total_tokens,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(cache_creation_tokens) as cache_creation_tokens,
                SUM(cache_read_tokens) as cache_read_tokens,
                MIN(date) as oldest_date,
                MAX(date) as newest_date
            FROM usage_records
            GROUP BY machine
            ORDER BY total_tokens DESC
        """)

        results = []
        for row in cursor.fetchall():
            machine_name = row[0]
            total_records = row[1]
            total_sessions = row[2]
            total_messages = row[3]
            total_tokens = row[4] or 0
            input_tokens = row[5] or 0
            output_tokens = row[6] or 0
            cache_creation_tokens = row[7] or 0
            cache_read_tokens = row[8] or 0
            oldest_date = row[9]
            newest_date = row[10]

            # Calculate cost for this device
            cursor.execute("""
                SELECT
                    ur.model,
                    SUM(ur.input_tokens) as total_input,
                    SUM(ur.output_tokens) as total_output,
                    SUM(ur.cache_creation_tokens) as total_cache_write,
                    SUM(ur.cache_read_tokens) as total_cache_read,
                    mp.input_price_per_mtok,
                    mp.output_price_per_mtok,
                    mp.cache_write_price_per_mtok,
                    mp.cache_read_price_per_mtok
                FROM usage_records ur
                LEFT JOIN model_pricing mp ON ur.model = mp.model_name
                WHERE COALESCE(ur.machine_name, 'Unknown') = ? AND ur.model IS NOT NULL
                GROUP BY ur.model
            """, (machine_name,))

            device_cost = 0.0
            for cost_row in cursor.fetchall():
                input_tok = cost_row[1] or 0
                output_tok = cost_row[2] or 0
                cache_write_tok = cost_row[3] or 0
                cache_read_tok = cost_row[4] or 0

                input_price = cost_row[5] or 0.0
                output_price = cost_row[6] or 0.0
                cache_write_price = cost_row[7] or 0.0
                cache_read_price = cost_row[8] or 0.0

                device_cost += (
                    (input_tok / 1_000_000) * input_price +
                    (output_tok / 1_000_000) * output_price +
                    (cache_write_tok / 1_000_000) * cache_write_price +
                    (cache_read_tok / 1_000_000) * cache_read_price
                )

            results.append({
                "machine_name": machine_name,
                "total_records": total_records,
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_cost": round(device_cost, 2),
                "oldest_date": oldest_date,
                "newest_date": newest_date,
            })

        return results
    finally:
        conn.close()


def save_user_preference(key: str, value: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    Save a single user preference to database.

    Args:
        key: Preference key (e.g., 'color_mode', 'usage_display_mode')
        value: Preference value (stored as string)
        db_path: Path to the SQLite database file

    Raises:
        sqlite3.Error: If database operation fails
    """
    init_database(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, timestamp))

        conn.commit()
    finally:
        conn.close()


def load_user_preferences(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """
    Load all user preferences from database with defaults.

    Returns:
        Dictionary mapping preference keys to their values.
        Provides default values for any missing keys.

    Raises:
        sqlite3.Error: If database query fails
    """
    # Default preferences (fallback if DB doesn't exist or is empty)
    defaults = {
        'usage_display_mode': '0',           # M1=0, M2=1, M3=2, M4=3
        'color_mode': 'gradient',            # solid | gradient
        'color_solid': '#00A7E1',            # bright_blue
        'color_gradient_low': '#00C853',     # green
        'color_gradient_mid': '#FFD600',     # yellow
        'color_gradient_high': '#FF1744',    # red
        'color_unfilled': '#424242',         # grey
        'storage_mode': 'aggregate',         # aggregate | detail
        'tracking_mode': 'both',             # both | usage | limits
        'machine_name': '',                  # custom name or empty
        'db_path': '',                       # custom path or empty
        'anonymize_projects': '0',           # 0=off, 1=on
    }

    if not db_path.exists():
        return defaults

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()

        # Ensure user_preferences table exists (migration for existing DBs)
        try:
            cursor.execute("SELECT key, value FROM user_preferences")
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # Table doesn't exist, initialize database to create it
            conn.close()
            init_database(db_path)
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_preferences")
            rows = cursor.fetchall()

        # Merge DB values with defaults
        prefs = defaults.copy()
        for key, value in rows:
            prefs[key] = value

        return prefs
    finally:
        conn.close()


def save_all_preferences(prefs: dict, db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    Save multiple preferences at once (batch update).

    Args:
        prefs: Dictionary mapping preference keys to values
        db_path: Path to the SQLite database file

    Raises:
        sqlite3.Error: If database operation fails
    """
    init_database(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        for key, value in prefs.items():
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, timestamp))

        conn.commit()
    finally:
        conn.close()


def get_database_stats(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """
    Get statistics about the historical database.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary with statistics including:
        - total_records, total_days, oldest_date, newest_date, newest_timestamp
        - total_tokens, total_prompts, total_sessions
        - tokens_by_model: dict of model -> token count
        - avg_tokens_per_session, avg_tokens_per_prompt
    """
    if not db_path.exists():
        return {
            "total_records": 0,
            "total_days": 0,
            "oldest_date": None,
            "newest_date": None,
            "newest_timestamp": None,
            "total_tokens": 0,
            "total_prompts": 0,
            "total_responses": 0,
            "total_sessions": 0,
            "tokens_by_model": {},
            "cost_by_model": {},
            "total_cost": 0.0,
            "avg_tokens_per_session": 0,
            "avg_tokens_per_response": 0,
            "avg_cost_per_session": 0.0,
            "avg_cost_per_response": 0.0,
        }

    conn = sqlite3.connect(db_path, timeout=30.0)

    try:
        cursor = conn.cursor()

        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM usage_records")
        total_records = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT date) FROM usage_records")
        total_days = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(date), MAX(date) FROM usage_records")
        oldest_date, newest_date = cursor.fetchone()

        # Get newest snapshot timestamp
        cursor.execute("SELECT MAX(snapshot_timestamp) FROM daily_snapshots")
        newest_timestamp = cursor.fetchone()[0]

        # Aggregate statistics from daily_snapshots
        cursor.execute("""
            SELECT
                SUM(total_tokens) as total_tokens,
                SUM(total_prompts) as total_prompts,
                SUM(total_responses) as total_responses,
                SUM(total_sessions) as total_sessions
            FROM daily_snapshots
        """)
        row = cursor.fetchone()
        total_tokens = row[0] or 0
        total_prompts = row[1] or 0
        total_responses = row[2] or 0
        total_sessions = row[3] or 0

        # Tokens by model (only available if usage_records exist)
        tokens_by_model = {}
        if total_records > 0:
            cursor.execute("""
                SELECT model, SUM(total_tokens) as tokens
                FROM usage_records
                GROUP BY model
                ORDER BY tokens DESC
            """)
            tokens_by_model = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

        # Calculate costs by joining with pricing table
        total_cost = 0.0
        cost_by_model = {}

        if total_records > 0:
            cursor.execute("""
                SELECT
                    ur.model,
                    SUM(ur.input_tokens) as total_input,
                    SUM(ur.output_tokens) as total_output,
                    SUM(ur.cache_creation_tokens) as total_cache_write,
                    SUM(ur.cache_read_tokens) as total_cache_read,
                    mp.input_price_per_mtok,
                    mp.output_price_per_mtok,
                    mp.cache_write_price_per_mtok,
                    mp.cache_read_price_per_mtok
                FROM usage_records ur
                LEFT JOIN model_pricing mp ON ur.model = mp.model_name
                WHERE ur.model IS NOT NULL
                GROUP BY ur.model
            """)

            for row in cursor.fetchall():
                model = row[0]
                input_tokens = row[1] or 0
                output_tokens = row[2] or 0
                cache_write_tokens = row[3] or 0
                cache_read_tokens = row[4] or 0

                # Pricing per million tokens
                input_price = row[5] or 0.0
                output_price = row[6] or 0.0
                cache_write_price = row[7] or 0.0
                cache_read_price = row[8] or 0.0

                # Calculate cost in dollars
                model_cost = (
                    (input_tokens / 1_000_000) * input_price +
                    (output_tokens / 1_000_000) * output_price +
                    (cache_write_tokens / 1_000_000) * cache_write_price +
                    (cache_read_tokens / 1_000_000) * cache_read_price
                )

                cost_by_model[model] = model_cost
                total_cost += model_cost

        # Calculate averages
        avg_tokens_per_session = total_tokens / total_sessions if total_sessions > 0 else 0
        avg_tokens_per_response = total_tokens / total_responses if total_responses > 0 else 0
        avg_cost_per_session = total_cost / total_sessions if total_sessions > 0 else 0
        avg_cost_per_response = total_cost / total_responses if total_responses > 0 else 0

        return {
            "total_records": total_records,
            "total_days": total_days,
            "oldest_date": oldest_date,
            "newest_date": newest_date,
            "newest_timestamp": newest_timestamp,
            "total_tokens": total_tokens,
            "total_prompts": total_prompts,
            "total_responses": total_responses,
            "total_sessions": total_sessions,
            "tokens_by_model": tokens_by_model,
            "cost_by_model": cost_by_model,
            "total_cost": total_cost,
            "avg_tokens_per_session": round(avg_tokens_per_session),
            "avg_tokens_per_response": round(avg_tokens_per_response),
            "avg_cost_per_session": round(avg_cost_per_session, 2),
            "avg_cost_per_response": round(avg_cost_per_response, 4),
        }
    finally:
        conn.close()
#endregion
