# TODO - Claude Goblin

## 🔴 미완료 작업 (2025-10-15)

### Settings 페이지 입력 기능 오류

**문제 상황:**
- Settings 페이지에서 색상 값(1-5번) 또는 간격 값(6-7번) 편집 시도 시 입력이 제대로 되지 않음
- 입력란에서 아무것도 입력하지 않고 엔터를 누르면 "Invalid hex color format" 오류 표시
- 입력 후 프로그램이 정상 작동하지 않고 종료도 불가능 (Ctrl+C도 무반응)
- ESC 키로 종료는 가능함

**시도한 해결책:**
1. ❌ 터미널 모드 전환 로직 수정 (termios 사용)
   - raw mode와 normal mode 간 전환 시도
   - 결과: 여전히 입력 불가

2. ❌ `input()` 함수 사용
   - Python 기본 input() 함수 사용 시도
   - 결과: 터미널 상태 충돌로 실패

3. ❌ `console.input()` 함수 사용
   - Rich Console의 input() 메서드로 변경
   - 결과: 여전히 입력 불가

**근본 원인 분석 필요:**
- `_read_key()` 함수가 raw mode를 사용하여 단일 키 입력을 받음
- 메인 루프에서 `_read_key()` 호출 후 터미널이 특정 상태로 남아있을 가능성
- `_edit_setting()` 함수 진입 시 터미널 상태가 텍스트 입력에 적합하지 않음
- Rich Console과 termios의 상호작용 문제 가능성

**영향받는 파일:**
- `src/commands/settings.py` (lines 150-222)
  - `_edit_setting()` 함수
  - `_read_key()` 함수

**다음 시도할 수 있는 방법:**
1. `_edit_setting()` 함수 진입 시 명시적으로 터미널을 cooked mode로 초기화
2. `_read_key()` 대신 다른 키 입력 메커니즘 사용 (예: Rich의 Prompt 클래스)
3. 입력 부분을 별도 함수로 분리하여 터미널 상태 완전히 격리
4. 다른 Claude Goblin 명령어들의 입력 처리 방식 참고 (예: usage.py, help.py 등)

**우선순위:** 🔴 HIGH
- Settings 페이지의 핵심 기능이 작동하지 않음
- 사용자가 색상 및 간격 설정을 변경할 수 없음

---

## 📋 예정 작업 (2025-10-15)

### 프로젝트 이름 및 배포 설정 변경

**1. 프로젝트 이름을 `cc-usage`로 변경**
- **작업 내용:**
  - PyPI 패키지 이름: `cc-usage` (Claude Code Usage의 약자)
  - 실행 명령어: `ccu` (현재 유지)
  - 기존 `claude-goblin-mod` → `cc-usage`로 전체 변경
- **변경 필요 파일:**
  - `pyproject.toml` - `[project] name` 변경
  - `README.md` - 프로젝트 이름 및 설치 가이드 업데이트
  - GitHub repository 이름 변경 (선택)
- **설치 예시:**
  ```bash
  pipx install cc-usage  # 패키지 이름
  ccu                    # 실행 명령어
  ```

**2. pipx 설치 방법 문서화**
- **작업 내용:**
  - README.md에 pipx 설치 가이드 추가 (권장 방법으로 명시)
  - 가상환경 없이 전역 실행 가능함을 명확히 설명
  - pip 설치 방법도 대안으로 제시
- **문서 구조:**
  ```markdown
  ## Installation

  ### Recommended: Using pipx (Isolated + Global Access)
  pipx install cc-usage

  ### Alternative: System-wide installation
  pip install cc-usage

  ## Usage
  After installation, run:
  ccu

  No virtual environment activation needed!
  ```
- **추가 설명 항목:**
  - pipx란 무엇인가? (CLI 도구 전용 패키지 관리자)
  - 왜 pipx를 권장하는가? (격리된 환경 + 전역 접근)
  - pipx 설치 방법 (`pip install pipx` → `pipx ensurepath`)

**우선순위:** 🟢 LOW-MEDIUM
- PyPI 배포 전에 반드시 완료해야 함
- Settings 입력 오류 해결 후 진행 권장
- 프로젝트 이름 변경은 초기 배포 전에 하는 것이 좋음 (이후 변경 시 혼란)

---

### OneDrive 동기화 기능 구현

**1. Settings 페이지에 Claude 사용 데이터 파일 경로 표시**
- **작업 내용:**
  - Device별 실제 Claude usage 데이터를 담고 있는 파일 경로를 Settings 페이지에 표시
  - Status 섹션에 "Claude Usage File Path" 항목 추가
- **관련 파일:**
  - `src/commands/settings.py` - Status 섹션 업데이트
  - Claude Desktop의 실제 usage 파일 위치 확인 필요

**2. OneDrive에 디바이스별 데이터 저장 방식 확인**
- **작업 내용:**
  - 현재 데이터베이스 파일을 OneDrive에 디바이스별로 저장하는 방식 분석
  - 각 디바이스의 데이터 동기화 메커니즘 확인
  - 디바이스 식별 방법 (machine_name 사용 여부 등) 검토
- **확인 필요 사항:**
  - 현재 데이터베이스 파일이 로컬에만 저장되는지, OneDrive와 연동되는지
  - 디바이스별 데이터 분리 저장 구조 (예: `onedrive/ccu/{machine_name}/db.sqlite`)
  - 동기화 충돌 방지 메커니즘 존재 여부
- **관련 파일:**
  - `src/storage/snapshot_db.py` - 데이터베이스 경로 및 초기화 로직

**3. OneDrive 경로 자동 탐지 및 사용자 입력 처리**
- **작업 내용:**
  - OneDrive 기본 경로가 아닌 경우 자동 탐지 가능 여부 조사
  - Windows/Linux/macOS의 OneDrive 기본 경로 확인
  - 자동 탐지 실패 시 사용자에게 경로 입력 받는 로직 구현
- **구현 방안:**
  - **Option A (자동 탐지):**
    - 환경 변수 확인 (예: `ONEDRIVE`, `OneDrive` 등)
    - 기본 경로 리스트 순회 검색
      - Windows: `%USERPROFILE%\OneDrive`, `%OneDrive%`
      - Linux: `~/OneDrive` (비공식 클라이언트)
      - macOS: `~/OneDrive`
  - **Option B (사용자 입력):**
    - 초기 설치 시 OneDrive 경로 입력 프롬프트 표시
    - 설정값을 데이터베이스에 저장 (`user_preferences` 테이블)
    - Settings 페이지에서 경로 변경 가능하도록 구현
- **관련 파일:**
  - 새 파일 생성 필요: `src/utils/onedrive_helper.py` (경로 탐지 로직)
  - `src/cli.py` - 초기 설정 프로세스 추가
  - `src/storage/snapshot_db.py` - OneDrive 경로 저장/로드

**4. 멀티 디바이스 데이터 합산 및 충돌 방지**
- **작업 내용:**
  - 여러 PC에서 CCU 설치 시 데이터 충돌 없이 합산되는 구조 구현
  - OneDrive에 데이터베이스가 이미 존재하는 경우 처리 로직
  - 새 디바이스 추가 시 기존 데이터와 병합 로직
- **구현 요구사항:**
  - **케이스 1: OneDrive에 DB 존재**
    - 기존 DB를 로컬로 다운로드/동기화
    - 현재 디바이스 데이터를 추가 (INSERT OR IGNORE 방식)
    - 디바이스 식별자로 데이터 구분 (machine_name 또는 device_id)
  - **케이스 2: OneDrive에 DB 없음**
    - 새 DB 생성 및 초기화
    - OneDrive 경로에 DB 저장
    - 현재 디바이스 데이터 수집 시작
  - **케이스 3: 동시 쓰기 충돌 방지**
    - 파일 락(lock) 메커니즘 또는 타임스탬프 기반 병합
    - 각 디바이스별 임시 로컬 DB 유지 후 주기적 동기화
    - OneDrive 파일 변경 감지 및 자동 병합
- **데이터베이스 스키마 변경:**
  - 모든 테이블에 `device_id` 또는 `machine_name` 컬럼 추가 필요 여부 확인
  - 복합 기본 키 설정 (예: `PRIMARY KEY (timestamp, device_id)`)
- **관련 파일:**
  - `src/storage/snapshot_db.py` - DB 초기화, 병합, 동기화 로직
  - `src/utils/onedrive_helper.py` - 동기화 및 충돌 감지
  - `database/migrations/` - 스키마 변경 마이그레이션 파일

**우선순위:** 🟡 MEDIUM
- OneDrive 동기화는 멀티 디바이스 사용자에게 중요한 기능
- 현재 Settings 입력 기능 오류 해결이 우선
- 구현 전 현재 코드베이스의 데이터 저장 방식 상세 분석 필요

---

## 완료된 작업 목록

### ✅ Usage 모드 푸터 변경 (2025-10-15)
- "Use tab or c to change mode." → "Use tab to change mode."로 변경
- 모드 표시를 "M1 | Solid" → "S1-S4" (Solid), "G1-G4" (Gradient) 형식으로 변경

### ✅ 비-Usage 페이지에 [s]ettings 단축키 추가 (2025-10-15)
- weekly, monthly, yearly, heatmap, devices 페이지에 [s]ettings 단축키 추가
- usage 페이지에는 추가하지 않음 (간소화 모드)

### ✅ Tab 키로 8개 모드 순환 구현 (2025-10-15)
- S1 → S2 → S3 → S4 → G1 → G2 → G3 → G4 → S1 순환
- 'c' 키 바인딩 제거

### ✅ [q]uit 단축키 제거 및 ESC 안내 추가 (2025-10-15)
- 비-Usage 페이지에서 [q]uit 제거
- 'q' 키 바인딩 제거
- "esc key to quit" 텍스트 추가

### ✅ Settings 페이지 재설계 (2025-10-15)
- Status 섹션 (읽기 전용): Display Mode, Color Mode, Machine Name, Database Path
- Settings 섹션 (편집 가능): 5개 색상 값 + 2개 자동 갱신 간격
- Storage Mode, Tracking Mode, Anonymize Projects 제거
- 숫자 키(1-7)로 항목 선택
- Hex 색상 검증 로직 구현
- 간격 최소값 검증 (10초)

**참고:** Settings 페이지 재설계는 완료되었으나, 입력 기능이 작동하지 않아 실사용 불가
