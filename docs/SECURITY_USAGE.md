# Security Usage Guide

## Overview

이 문서는 claude-goblin의 보안 기능 사용 방법과 보안 모범 사례를 설명합니다.

## 환경 변수

### 디버그 모드

보안상 프로덕션 환경에서는 상세한 오류 메시지를 표시하지 않습니다. 개발 중 상세한 오류 정보가 필요한 경우 다음과 같이 설정하세요:

```bash
export CCG_DEBUG=true
ccg usage
```

또는 일회성으로 실행:

```bash
CCG_DEBUG=true ccg usage
```

**경고**: 디버그 모드는 시스템 경로와 내부 구조를 노출할 수 있으므로 프로덕션 환경에서는 사용하지 마세요.

## 보안 기능

### 1. 명령 주입 방어 (Command Injection Prevention)

**사운드 재생 기능**

시스템 사운드를 재생할 때 사운드 이름은 자동으로 검증됩니다:

```python
# 안전한 사운드 이름
✓ "alert"
✓ "notification-1"
✓ "sound_beep"

# 거부되는 사운드 이름
✗ "sound; rm -rf /"
✗ "../../../etc/passwd"
✗ "sound$(malicious)"
```

허용되는 문자:
- 영문자 (a-z, A-Z)
- 숫자 (0-9)
- 하이픈 (-)
- 언더스코어 (_)
- 최대 길이: 64자

### 2. 파일 경로 검증 (Path Validation)

**출력 파일 보호**

export 명령어를 사용할 때 출력 경로가 자동으로 검증됩니다:

```bash
# 안전한 경로
✓ ccg export -o ~/reports/usage.png
✓ ccg export -o ./output/usage.svg

# 차단되는 경로
✗ ccg export -o /etc/important-file
✗ ccg export -o /usr/bin/malicious
✗ ccg export -o "C:\Windows\System32\file.png"
```

보호되는 시스템 디렉토리:
- Linux/macOS: `/etc`, `/bin`, `/sbin`, `/usr/bin`, `/usr/sbin`, `/sys`, `/proc`, `/boot`, `/dev`
- Windows: `C:\Windows`, `C:\Program Files`, `C:\Program Files (x86)`, `C:\ProgramData`

### 3. 경로 탐색 방어 (Path Traversal Prevention)

**데이터 파일 읽기**

JSONL 파일을 읽을 때 심볼릭 링크를 따라가지 않으며, 모든 파일이 의도한 디렉토리 내에 있는지 확인합니다:

```python
# 자동으로 검증됨
- 심볼릭 링크 제외
- 디렉토리 경계 검사
- 절대 경로 검증
```

### 4. 백업 파일 보호

**타임스탬프 기반 백업**

데이터베이스 백업 시 타임스탬프와 프로세스 ID를 포함한 고유한 파일명이 생성됩니다:

```bash
# 이전 방식 (경쟁 조건 가능)
usage_history.db.bak

# 새로운 방식 (안전)
usage_history_20250114_123456_12345.db
```

이렇게 하면:
- 동시 실행 시 백업이 서로 덮어쓰지 않음
- 각 백업의 생성 시간을 명확히 알 수 있음
- 여러 백업 버전 유지 가능

## 보안 감사

### 의존성 검사

프로젝트에 보안 감사 도구가 포함되어 있습니다:

```bash
# 보안 도구 설치
pip install -e ".[security]"

# 의존성 취약점 검사
pip-audit

# 또는 safety 사용
safety check
```

정기적으로 (최소 월 1회) 실행하여 알려진 취약점을 확인하세요.

### 권장 보안 점검 체크리스트

**매월:**
- [ ] `pip-audit` 실행하여 취약한 의존성 확인
- [ ] 보안 업데이트가 있는 패키지 업그레이드

**새 기능 추가 시:**
- [ ] 사용자 입력이 검증되는지 확인
- [ ] 파일 경로가 안전한지 확인
- [ ] 시스템 명령어 실행 시 주입 공격 가능성 검토

**프로덕션 배포 전:**
- [ ] `CCG_DEBUG=false` 확인 (또는 설정 안 함)
- [ ] 불필요한 오류 정보 노출 여부 확인
- [ ] 의존성 취약점 스캔 수행

## 보안 모범 사례

### 1. 최소 권한 원칙

claude-goblin은 사용자 홈 디렉토리(`~/.claude/`)만 사용합니다:

```bash
# 데이터 위치
~/.claude/projects/          # JSONL 데이터
~/.claude/usage_history.db   # 사용 기록 데이터베이스
~/.claude/usage/             # 내보내기 기본 위치
~/.claude/settings.json      # 설정 (hook 포함)
```

### 2. 정기 백업

중요한 변경 전에 데이터베이스를 백업하세요:

```bash
# 스토리지 모드 변경 전
ccg setup usage  # 프롬프트에서 백업 옵션 선택

# 수동 백업
cp ~/.claude/usage_history.db ~/.claude/backups/usage_history_$(date +%Y%m%d).db
```

### 3. 안전한 설정

hook 설정 시 신뢰할 수 있는 명령어만 사용하세요:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [{
          "type": "command",
          "command": "ccg update-usage > /dev/null 2>&1 &"
        }]
      }
    ]
  }
}
```

## 문제 보고

보안 취약점을 발견한 경우:

1. **공개적으로 보고하지 마세요**
2. GitHub Issues의 "Security" 템플릿 사용
3. 또는 프로젝트 관리자에게 직접 연락

포함할 정보:
- 취약점 설명
- 재현 단계
- 예상되는 영향
- 가능한 경우 해결 방법 제안

## 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

## 라이선스 및 책임

이 소프트웨어는 MIT 라이선스 하에 "있는 그대로" 제공됩니다. 보안 기능이 구현되어 있지만, 완벽한 보안을 보장하지 않습니다. 사용자는 자신의 환경에서 적절한 보안 조치를 취할 책임이 있습니다.