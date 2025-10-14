# Multi-Provider Architecture Design (Draft)

> **Status**: Planning / Draft
> **Created**: 2025-10-15
> **Target Version**: v2.0+

## Overview

현재 Claude Goblin은 **Claude Code** 전용이지만, 향후 다양한 AI 코딩 어시스턴트를 지원하는 **멀티 프로바이더 아키텍처**로 확장 예정.

---

## Supported Providers (Planned)

### Current (v1.x)
- ✅ **Claude Code** (Anthropic Desktop App)
  - Data Source: `~/.claude/projects/*.jsonl`
  - Models: Claude Sonnet, Opus, Haiku

### Planned (v2.0+)
- ⬜ **Cursor** (AI-powered IDE)
  - Data Source: `~/.cursor/logs/` or SQLite DB
  - Models: GPT-4, Claude (via Cursor API)

- ⬜ **GitHub Copilot / Codex**
  - Data Source: GitHub API or VSCode extension logs
  - Models: Codex, GPT-4

- ⬜ **Continue.dev** (Open-source VSCode extension)
  - Data Source: `~/.continue/usage.json`
  - Models: Multi-provider (OpenAI, Anthropic, Ollama, etc.)

- ⬜ **Claude API** (Direct API usage)
  - Data Source: API logs or Anthropic Console scraping
  - Models: Claude Sonnet, Opus, Haiku

- ⬜ **Cline** (VSCode extension, formerly Claude Dev)
  - Data Source: VSCode extension logs
  - Models: Claude via API

---

## Architecture Design

### Provider Abstraction Layer

모든 프로바이더는 공통 인터페이스(`BaseProvider`)를 구현하여 플러그인 방식으로 추가 가능.

```python
# src/providers/base.py
class BaseProvider(ABC):
    """Base interface for all AI coding assistant providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider internal name (e.g., 'claude-code')"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Provider display name (e.g., 'Claude Code')"""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Provider icon (emoji or URL)"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is installed and accessible"""
        pass

    @abstractmethod
    def get_data_source_path(self) -> Optional[str]:
        """Get path to data source (logs, DB, API endpoint, etc.)"""
        pass

    @abstractmethod
    def fetch_usage_records(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[UsageRecord]:
        """Fetch usage records from provider"""
        pass

    @abstractmethod
    def get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing info for model"""
        pass
```

### Unified Data Model

프로바이더에 관계없이 통일된 데이터 모델 사용.

```python
@dataclass
class UsageRecord:
    """Provider-agnostic usage record"""
    provider: str                    # 'claude-code', 'cursor', 'codex', etc.
    provider_version: str
    timestamp: datetime
    session_id: str
    message_uuid: str
    message_type: str               # 'user', 'assistant', 'system'
    model: str                       # 'claude-sonnet-4', 'gpt-4', etc.
    model_provider: str              # 'anthropic', 'openai', 'github'
    folder: str                      # Project folder
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    machine_name: Optional[str] = None
    git_branch: Optional[str] = None
    metadata: Optional[Dict] = None  # Provider-specific extra data
```

---

## Database Schema (Multi-Provider)

### Extended Tables

```sql
-- 기존 usage_records 확장
CREATE TABLE usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Provider 식별
    provider TEXT NOT NULL,              -- 'claude-code', 'cursor', 'codex'
    provider_version TEXT,

    -- 기존 필드
    date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    message_uuid TEXT NOT NULL,
    message_type TEXT NOT NULL,

    -- 모델 정보 (통합)
    model TEXT,
    model_provider TEXT,                 -- 'anthropic', 'openai', 'github'

    -- 프로젝트 정보
    folder TEXT NOT NULL,
    git_branch TEXT,

    -- 토큰 사용량
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL,

    -- 비용
    estimated_cost REAL,

    -- 메타데이터
    machine_name TEXT,

    -- 중복 방지 (provider별)
    UNIQUE(provider, session_id, message_uuid)
);

-- Provider 설정 테이블 (새로 추가)
CREATE TABLE providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,           -- 'claude-code', 'cursor'
    display_name TEXT NOT NULL,          -- 'Claude Code', 'Cursor'
    enabled BOOLEAN DEFAULT 1,           -- 활성화 여부
    data_source_type TEXT NOT NULL,      -- 'jsonl', 'api', 'sqlite'
    data_source_path TEXT,               -- 경로 또는 API endpoint
    icon TEXT,                            -- 아이콘 (emoji 또는 URL)
    color TEXT,                           -- 대시보드 색상
    last_sync TIMESTAMP,                 -- 마지막 동기화 시간
    config JSON                           -- Provider별 추가 설정
);

-- Provider별 가격 정보
CREATE TABLE provider_pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,               -- 'anthropic', 'openai', 'github'
    model_name TEXT NOT NULL,
    input_price_per_mtok REAL NOT NULL,
    output_price_per_mtok REAL NOT NULL,
    cache_write_price_per_mtok REAL,
    cache_read_price_per_mtok REAL,
    last_updated TEXT NOT NULL,
    UNIQUE(provider, model_name)
);
```

---

## File Structure

```
claude-goblin-mod/
├── src/
│   ├── providers/              # 🆕 Provider 추상화
│   │   ├── __init__.py
│   │   ├── base.py            # BaseProvider interface
│   │   ├── claude_code.py     # Claude Code (현재)
│   │   ├── cursor.py          # Cursor (향후)
│   │   ├── codex.py           # Codex/Copilot (향후)
│   │   ├── continue_dev.py    # Continue.dev (향후)
│   │   ├── claude_api.py      # Claude API (향후)
│   │   ├── cline.py           # Cline (향후)
│   │   └── registry.py        # Provider registry
│   ├── commands/
│   │   ├── settings.py        # Multi-provider settings
│   │   ├── providers.py       # 🆕 Provider management
│   │   └── ...
│   ├── storage/
│   │   ├── snapshot_db.py     # Multi-provider DB schema
│   │   └── ...
│   └── ...
└── ...
```

---

## UI/UX Changes

### Settings Page (Multi-Provider)

```
Status (Read-Only):
┌────────────────────────────────────────────────┐
│ Active Providers:                              │
│   🤖 Claude Code (14,523 messages)            │
│   ⚡ Cursor (2,341 messages)         [Coming] │
│   🐙 Codex (disabled)                [Coming] │
│                                                │
│ Display Mode: M1 (simple, bar+%)               │
│ Color Mode: Gradient                           │
│ Machine Name: Home-Desktop                     │
│ Database Path: ~/GoogleDrive/.../db            │
│ Sync Service: Google Drive                     │
└────────────────────────────────────────────────┘

Settings (Editable):
 1-5. Color settings
 6-7. Refresh intervals

Provider Management:
 [P] Manage Providers (enable/disable/configure)
 [A] Add New Provider (future)

Storage & Sync:
 8. Storage Location: Local / Cloud

Database Operations:
 [I] Initialize  [D] Delete  [R] Restore  [B] Backup
```

### New Dashboard Mode: Providers Mode

```
Press [p] → Providers Mode

Provider Breakdown (This Month)
┌─────────────┬──────────┬───────────┬──────────┐
│ Provider    │ Messages │ Tokens    │ Cost     │
├─────────────┼──────────┼───────────┼──────────┤
│ 🤖 Claude Code│ 14,523   │ 45.2M     │ $12.34   │
│ ⚡ Cursor     │ 2,341    │ 8.7M      │ $3.21    │
│ 🐙 Codex      │ -        │ -         │ -        │
├─────────────┼──────────┼───────────┼──────────┤
│ Total       │ 16,864   │ 53.9M     │ $15.55   │
└─────────────┴──────────┴───────────┴──────────┘

Model Breakdown (All Providers)
┌────────────────────┬──────────┬───────────┐
│ Model              │ Messages │ Tokens    │
├────────────────────┼──────────┼───────────┤
│ claude-sonnet-4    │ 12,234   │ 38.1M     │
│ gpt-4 (via Cursor) │ 2,100    │ 7.2M      │
│ claude-opus-4      │ 1,200    │ 5.8M      │
│ gpt-3.5-turbo      │ 241      │ 1.5M      │
└────────────────────┴──────────┴───────────┘

Shortcuts: [u]sage [w]eekly [m]onthly [y]early [h]eatmap
           [d]evices [p]roviders [s]ettings [ESC] quit
```

### Provider Management Screen

```
Provider Management
┌────────────────────────────────────────────────┐
│ 🤖 Claude Code                      [Enabled]  │
│    Path: ~/.claude/projects/*.jsonl            │
│    Last Sync: 2025-10-15 14:23                 │
│    Records: 14,523 messages                    │
│    [Configure]                                 │
├────────────────────────────────────────────────┤
│ ⚡ Cursor                          [Coming]   │
│    Status: Not Installed                       │
│    [Learn More]                                │
├────────────────────────────────────────────────┤
│ 🐙 GitHub Copilot                 [Coming]   │
│    Status: Planned for v2.0                    │
│    [Vote on Roadmap]                           │
├────────────────────────────────────────────────┤
│ 🔧 Continue.dev                   [Coming]   │
│    Status: Community Requested                 │
│    [Request Feature]                           │
└────────────────────────────────────────────────┘

Press [ESC] to return
```

---

## Implementation Roadmap

### Phase 1: Foundation (v1.x - Current)
- ✅ Claude Code support
- ✅ Multi-platform sync (Google Drive, OneDrive, etc.)
- ⬜ Settings page completion
- ⬜ DB operations (I/D/R/B)

### Phase 2: Provider Abstraction (v1.5)
- ⬜ Create `src/providers/` directory
- ⬜ Define `BaseProvider` interface
- ⬜ Refactor `ClaudeCodeProvider` (existing code)
- ⬜ Implement `ProviderRegistry`
- ⬜ Extend DB schema (add `provider` column)
- ⬜ Add provider filter to dashboard

### Phase 3: First Additional Provider (v2.0)
- ⬜ Implement `CursorProvider`
- ⬜ Cursor usage log parser
- ⬜ Provider management UI
- ⬜ Multi-provider unified dashboard
- ⬜ Provider mode (`p` key)

### Phase 4: Additional Providers (v2.x)
- ⬜ `CodexProvider` / GitHub Copilot
- ⬜ `ContinueDevProvider`
- ⬜ `ClaudeAPIProvider` (Direct API)
- ⬜ `ClineProvider`

### Phase 5: Advanced Features (v3.0+)
- ⬜ Provider-specific pricing comparison
- ⬜ Model recommendation engine
- ⬜ Cost optimization suggestions
- ⬜ Provider usage analytics
- ⬜ Plugin system for community providers

---

## Technical Challenges

### 1. Data Source Heterogeneity

**Challenge**: 각 프로바이더의 데이터 소스가 다름
- Claude Code: JSONL files
- Cursor: SQLite DB or logs
- Codex: GitHub API
- Continue.dev: JSON config

**Solution**: Provider별 parser 구현, 공통 `UsageRecord` 모델로 변환

### 2. Pricing Models

**Challenge**: 프로바이더마다 다른 가격 체계
- Anthropic: Per-token (input/output/cache)
- OpenAI: Per-token (input/output)
- GitHub: Subscription-based
- Cursor: Hybrid (subscription + usage)

**Solution**: `provider_pricing` 테이블 + provider별 pricing calculator

### 3. Real-time vs Batch Sync

**Challenge**: 일부 프로바이더는 실시간 로그, 일부는 API 폴링 필요

**Solution**: Provider별 `sync_mode` 설정
- `real-time`: File watching
- `polling`: Periodic API calls
- `manual`: User-triggered sync

### 4. Authentication

**Challenge**: API 기반 프로바이더는 인증 필요 (GitHub, Claude API)

**Solution**:
- Secure credential storage (OS keyring)
- OAuth flow for API providers
- Environment variable support

---

## Data Source Examples

### Claude Code (Current)
```json
// ~/.claude/projects/<uuid>.jsonl
{
  "session_id": "abc123",
  "message_uuid": "def456",
  "timestamp": "2025-10-15T14:23:45Z",
  "message_type": "assistant",
  "model": "claude-sonnet-4-5-20250929",
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "cache_creation_input_tokens": 100,
    "cache_read_input_tokens": 500
  },
  "folder": "/home/user/project",
  "git_branch": "main",
  "version": "0.7.2"
}
```

### Cursor (Hypothetical)
```json
// ~/.cursor/usage/usage.db (SQLite)
// Or ~/.cursor/logs/usage.json
{
  "id": "xyz789",
  "timestamp": "2025-10-15T14:25:30Z",
  "model": "gpt-4",
  "provider": "openai",
  "prompt_tokens": 800,
  "completion_tokens": 300,
  "total_tokens": 1100,
  "cost_usd": 0.035,
  "workspace": "/home/user/project",
  "file": "src/main.py"
}
```

### GitHub Copilot (Hypothetical)
```json
// GitHub API response
{
  "usage": [
    {
      "date": "2025-10-15",
      "total_suggestions": 145,
      "accepted_suggestions": 67,
      "editor": "vscode",
      "language": "python"
    }
  ]
}
```

### Continue.dev (Hypothetical)
```json
// ~/.continue/usage.json
{
  "sessions": [
    {
      "id": "session123",
      "provider": "anthropic",
      "model": "claude-3-opus-20240229",
      "timestamp": "2025-10-15T14:30:00Z",
      "input_tokens": 500,
      "output_tokens": 200,
      "cost": 0.015
    }
  ]
}
```

---

## Provider-Specific Features

### Claude Code
- ✅ Session limits tracking
- ✅ Weekly limits tracking
- ✅ Opus limits tracking
- ✅ Cache efficiency metrics

### Cursor
- ⬜ Model switching tracking (GPT-4 ↔ Claude)
- ⬜ Inline completion vs Chat usage
- ⬜ Subscription tier tracking

### GitHub Copilot
- ⬜ Suggestion acceptance rate
- ⬜ Language breakdown
- ⬜ Editor-specific stats

### Continue.dev
- ⬜ Multi-provider usage in single session
- ⬜ Context provider tracking (codebase, docs, web)
- ⬜ Slash command usage

---

## Configuration Example

### provider_config.json

```json
{
  "providers": {
    "claude-code": {
      "enabled": true,
      "priority": 1,
      "data_source": {
        "type": "jsonl",
        "path": "~/.claude/projects",
        "watch": true
      },
      "sync": {
        "mode": "real-time",
        "interval": null
      }
    },
    "cursor": {
      "enabled": false,
      "priority": 2,
      "data_source": {
        "type": "sqlite",
        "path": "~/.cursor/usage/usage.db",
        "watch": false
      },
      "sync": {
        "mode": "manual",
        "interval": null
      }
    },
    "codex": {
      "enabled": false,
      "priority": 3,
      "data_source": {
        "type": "api",
        "endpoint": "https://api.github.com/user/copilot/usage",
        "auth": {
          "type": "token",
          "token_env": "GITHUB_TOKEN"
        }
      },
      "sync": {
        "mode": "polling",
        "interval": 3600
      }
    }
  }
}
```

---

## Migration Strategy

### From Single-Provider to Multi-Provider

**Step 1: Add provider column to existing records**
```sql
-- Migration: Add provider column with default value
ALTER TABLE usage_records ADD COLUMN provider TEXT DEFAULT 'claude-code';
ALTER TABLE usage_records ADD COLUMN model_provider TEXT DEFAULT 'anthropic';
```

**Step 2: Backfill existing data**
```sql
-- Set provider for all existing records
UPDATE usage_records
SET provider = 'claude-code', model_provider = 'anthropic'
WHERE provider IS NULL;
```

**Step 3: Update UNIQUE constraint**
```sql
-- Drop old constraint
-- SQLite doesn't support DROP CONSTRAINT, need to recreate table
-- Or use new table with updated schema

-- New constraint
CREATE UNIQUE INDEX idx_provider_session_message
ON usage_records(provider, session_id, message_uuid);
```

---

## Community Contributions

### Plugin System (v3.0+)

사용자가 커스텀 프로바이더를 추가할 수 있는 플러그인 시스템.

```python
# ~/.claude-goblin/plugins/my_custom_provider.py
from claude_goblin.providers import BaseProvider, UsageRecord

class MyCustomProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "my-custom-provider"

    # ... implement other methods
```

**Plugin Discovery:**
```bash
ccu plugin install ~/.claude-goblin/plugins/my_custom_provider.py
ccu plugin list
ccu plugin enable my-custom-provider
```

---

## References

### External APIs

- **Anthropic API**: https://docs.anthropic.com/en/api
- **OpenAI API**: https://platform.openai.com/docs/api-reference
- **GitHub Copilot API**: https://docs.github.com/en/copilot
- **Cursor**: (No public API yet)
- **Continue.dev**: https://github.com/continuedev/continue

### Similar Projects

- **OpenAI Token Counter**: https://github.com/openai/openai-cookbook
- **Copilot Stats**: VSCode extension for Copilot analytics
- **AI Code Assistant Tracker**: (Various community projects)

---

## Notes

- This is a **draft design document** for future development
- Implementation timeline depends on community interest and priority
- Some providers may not have accessible usage data
- API-based providers require authentication setup
- Privacy considerations for cloud-synced multi-provider data

---

## Discussion

### Open Questions

1. **Provider Priority**: 여러 프로바이더가 동시에 같은 프로젝트에 사용될 경우?
2. **Cost Attribution**: 한 프로젝트에서 여러 모델 사용 시 비용 추적?
3. **Data Retention**: 프로바이더별로 다른 retention 정책?
4. **Privacy**: API key 등 민감 정보 저장 방식?

### Feedback Needed

- Which providers should be prioritized?
- What features are most valuable for multi-provider support?
- How should provider-specific features be exposed in UI?

---

**Last Updated**: 2025-10-15
**Status**: Draft / Planning
**Next Steps**: Complete Settings page, then start Phase 2 (Provider Abstraction)
