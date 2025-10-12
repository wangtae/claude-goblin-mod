#region Imports
import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from src.models.usage_record import TokenUsage, UsageRecord
#endregion


#region Functions


def parse_jsonl_file(file_path: Path) -> Iterator[UsageRecord]:
    """
    Parse a single JSONL file and yield UsageRecord objects.

    Extracts usage data from Claude Code session logs, including:
    - Token usage (input, output, cache creation, cache read)
    - Session metadata (model, folder, version, branch)
    - Timestamps and identifiers

    Args:
        file_path: Path to the JSONL file to parse

    Yields:
        UsageRecord objects for each assistant message with usage data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                record = _parse_record(data)
                if record:
                    yield record
            except json.JSONDecodeError as e:
                # Skip malformed lines but continue processing
                print(f"Warning: Skipping malformed JSON at {file_path}:{line_num}: {e}")
                continue


def parse_all_jsonl_files(file_paths: list[Path]) -> list[UsageRecord]:
    """
    Parse multiple JSONL files and return all usage records.

    Args:
        file_paths: List of paths to JSONL files

    Returns:
        List of all UsageRecord objects found across all files

    Raises:
        ValueError: If file_paths is empty
    """
    if not file_paths:
        raise ValueError("No JSONL files provided to parse")

    records: list[UsageRecord] = []
    for file_path in file_paths:
        try:
            records.extend(parse_jsonl_file(file_path))
        except FileNotFoundError:
            print(f"Warning: File not found, skipping: {file_path}")
        except Exception as e:
            print(f"Warning: Error parsing {file_path}: {e}")

    return records


def _parse_record(data: dict) -> Optional[UsageRecord]:
    """
    Parse a single JSON record into a UsageRecord.

    Processes both user prompts and assistant responses.
    Skips system events and other message types.

    Args:
        data: Parsed JSON object from JSONL line

    Returns:
        UsageRecord for user or assistant messages, None otherwise
    """
    message_type = data.get("type")

    # Only process user and assistant messages
    if message_type not in ("user", "assistant"):
        return None

    # Parse timestamp
    timestamp_str = data.get("timestamp")
    if not timestamp_str:
        return None

    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    # Extract metadata (common to both user and assistant)
    session_id = data.get("sessionId", "unknown")
    message_uuid = data.get("uuid", "unknown")
    folder = data.get("cwd", "unknown")
    git_branch = data.get("gitBranch")
    version = data.get("version", "unknown")

    # Extract message data
    message = data.get("message", {})
    model = message.get("model")

    # Filter out synthetic models (test/internal artifacts)
    if model == "<synthetic>":
        return None

    # Extract content for analysis
    content = None
    char_count = 0
    if isinstance(message.get("content"), str):
        content = message["content"]
        char_count = len(content)
    elif isinstance(message.get("content"), list):
        # Handle content blocks (concatenate text)
        text_parts = []
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        content = "\n".join(text_parts) if text_parts else None
        char_count = len(content) if content else 0

    # Extract token usage (only available for assistant messages)
    token_usage = None
    if message_type == "assistant":
        usage_data = message.get("usage")
        if usage_data:
            cache_creation = usage_data.get("cache_creation", {})
            cache_creation_tokens = (
                cache_creation.get("cache_creation_input_tokens", 0)
                + cache_creation.get("ephemeral_5m_input_tokens", 0)
                + cache_creation.get("ephemeral_1h_input_tokens", 0)
            )

            token_usage = TokenUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
            )

    return UsageRecord(
        timestamp=timestamp,
        session_id=session_id,
        message_uuid=message_uuid,
        message_type=message_type,
        model=model,
        folder=folder,
        git_branch=git_branch,
        version=version,
        token_usage=token_usage,
        content=content,
        char_count=char_count,
    )
#endregion
