# Security Remediation Plan

## Overview
This document details the security vulnerabilities found in claude-goblin-mod and the remediation steps taken to address them.

## Vulnerabilities Addressed

### 1. HIGH SEVERITY: Command Injection (CVE-Style Issues)

**Location**: `src/utils/_system.py`

**Issues**:
- Line 24: Windows `subprocess.run()` uses `shell=True` with user-controlled input
- Lines 44, 47, 51: Sound names inserted directly into shell commands without validation

**Impact**: Arbitrary command execution if malicious input is provided through file paths or sound names

**Remediation**:
- Remove `shell=True` from Windows subprocess call
- Implement strict input validation for sound names (alphanumeric, hyphens, underscores only)
- Use parameterized command arrays instead of string interpolation
- Add path sanitization for file operations

### 2. MEDIUM SEVERITY: Insufficient Output Path Validation

**Location**: `src/commands/export.py:77-96`

**Issues**:
- User-provided output paths accepted without validation
- Potential to overwrite system files or write to protected directories

**Impact**: File system integrity compromise, potential privilege escalation

**Remediation**:
- Implement path validation function to block system directories
- Verify paths resolve within safe boundaries
- Add explicit allow-list for writable directories
- Prevent path traversal attacks

### 3. MEDIUM SEVERITY: Path Traversal via Symbolic Links

**Location**: `src/config/settings.py:42`

**Issues**:
- `rglob()` follows symbolic links, potentially accessing files outside intended directory
- No validation that discovered files are within the expected directory tree

**Impact**: Information disclosure, unintended file access

**Remediation**:
- Check for and exclude symbolic links
- Validate resolved paths remain within `CLAUDE_DATA_DIR`
- Add boundary checking for all file operations

### 4. LOW SEVERITY: Race Condition in Backup Files

**Location**: `src/hooks/usage.py:85`

**Issues**:
- Fixed backup filename allows race conditions with concurrent processes
- Backups can overwrite each other

**Impact**: Data loss, backup corruption

**Remediation**:
- Use timestamp-based backup filenames
- Add process ID to ensure uniqueness
- Implement atomic file operations

### 5. LOW SEVERITY: Sensitive Information in Error Messages

**Location**: Multiple files using `traceback.print_exc()`

**Issues**:
- Full stack traces expose system paths and internal structure
- Debug information visible to all users

**Impact**: Information disclosure aiding further attacks

**Remediation**:
- Implement DEBUG mode flag
- Show minimal error messages in production
- Log detailed errors securely
- Sanitize error messages before display

## Implementation Checklist

- [x] Create security utilities module (`src/utils/security.py`)
- [ ] Update `_system.py` with input validation and safe subprocess calls
- [ ] Add path validation to `export.py`
- [ ] Secure file discovery in `settings.py`
- [ ] Implement timestamp-based backup naming
- [ ] Add DEBUG mode configuration
- [ ] Update error handling across all modules
- [ ] Add dependency security scanning to CI/CD
- [ ] Document security best practices for contributors

## Testing Requirements

Each remediation must be tested for:
1. Normal operation continues to work
2. Malicious input is properly rejected
3. Error messages are informative but not revealing
4. Performance impact is minimal

## Maintenance

- Run `pip-audit` monthly to check for dependency vulnerabilities
- Review security advisories for dependencies (rich, typer, pillow, cairosvg)
- Update this document when new vulnerabilities are discovered or fixed

## References

- OWASP Command Injection: https://owasp.org/www-community/attacks/Command_Injection
- CWE-78: OS Command Injection
- CWE-22: Path Traversal
- CWE-209: Information Exposure Through Error Messages