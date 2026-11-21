# Antigravity (AGY) Code Harness

Google Antigravity(`agy` CLI, Antigravity App, IDE)의 기본 동작을 덮어쓰지 않고, 계획·구현·리뷰·릴리스를 일관되게 돕는 가벼운 개인용 하네스입니다.

## 구성

- 커스텀 서브에이전트 6개 (`.agents/agents/`): `explorer`, `planner`, `coder`, `tester`, `reviewer`, `documenter`
- 스킬 6개 (`.agents/skills/`): `plan`, `work`, `review`, `release`, `setup`, `orchestrator`
- 안전 훅 2개 (`.agents/hooks/` + `.agents/hooks.json`): 파괴적 명령 차단, 비밀 파일 쓰기 차단
- 설치기 (`scripts/install.py`): 정본을 전역 `~/.gemini/config`에 심볼릭 링크하고 `hooks.json`의 `agy-harness-safety`만 안전하게 병합

수명주기 훅 루프, 디스크 재시도 카운터, 외부 `agy -p` runner, 에이전트 호출 알림, 편집 후 자동 lint는 사용하지 않습니다. 재시도가 필요하면 `orchestrator` 스킬이 대화 안에서 `send_message`로만 조율합니다.

## 권장 흐름

작은 수정은 메인 에이전트가 직접 처리합니다. 요구사항이나 위험이 있는 변경은 다음 흐름을 사용합니다.

```text
plan → work → review → release
```

- `plan`: `Plans.md`에 범위와 인수 기준을 정리합니다. (Antigravity 기본 `/plan` 모드와 구분해 `plan` 스킬로 활성화할 수 있습니다.)
- `work`: 승인된 Phase 하나를 작게 구현합니다. `tester`는 필요할 때만 사용합니다.
- `review`: 스펙, 보안, 정확성·유지보수성, 성능·운영성의 네 관점을 한 번 검토합니다.
- `release`: 사용자가 명시적으로 요청했을 때만 문서·커밋·푸시·PR을 준비합니다.
- `orchestrator`: 비단순 작업의 전체 흐름과 수정·재리뷰를 조율합니다. 최초 리뷰를 포함해 최대 3회만 수행합니다.

같은 지적이 반복되거나, 결과가 불명확하거나, 세 번째 리뷰에서도 승인되지 않으면 자동 진행을 멈추고 사용자에게 보고합니다.

## 모델과 실행 정책

| 역할 | 모델 (`model`) | 명령 정책 (`commandExecutionPolicy`) | 주 역할 |
|---|---|---|---|
| planner | `pro` | `off` | 요구사항·위험·인수 기준 판단 |
| reviewer | `pro` | `sandbox` | 독립 4관점 리뷰 |
| coder | `inherit` | `sandbox` | 승인된 Phase 구현 |
| tester | `inherit` | `sandbox` | 선택적 독립 검증 |
| explorer | `flash` | `sandbox` | 읽기 전용 코드 탐색 |
| documenter | `flash` | `off` | 검증된 동작의 문서 동기화 |

판단 오류의 비용이 큰 역할에 `pro`를 쓰고, 구현·검증은 현재 세션 모델(`inherit`)을 따릅니다. 탐색과 문서화는 `flash`로 지연과 토큰을 줄입니다. CLI/App/IDE 간 도구명 불일치로 인한 서브에이전트 정지를 피하기 위해 `tools` 화이트리스트는 생략하고 `commandExecutionPolicy`와 시스템 프롬프트로 경계를 강제합니다.

## 설치

```bash
git clone https://github.com/jangheejeong/agy-code-harness.git
cd agy-code-harness
python3 scripts/install.py
```

워크스페이스 내 중복 복제본 정리까지 함께 하려면 `--workspace`를 지정하세요.

```bash
python3 scripts/install.py --workspace /path/to/your-project --dry-run
python3 scripts/install.py --workspace /path/to/your-project
```

설치기는 다음 원칙을 지킵니다.

- `~/.gemini/config/agents`, `~/.gemini/config/skills`, `~/.gemini/config/hooks`에 이 저장소를 가리키는 심볼릭 링크를 만듭니다.
- `~/.gemini/config/hooks.json`에는 `agy-harness-safety` 키만 병합하며, 기존 사용자 훅(`orca-status` 등)은 그대로 보존합니다.
- 관리 대상이 아닌 기존 파일과 충돌하면 변경 전에 즉시 중단합니다.

## 검증

```bash
python3 -m unittest discover -s tests -v
bash .agents/hooks/tests/run-tests.sh
```

설치 후 새 Antigravity 세션(`agy` / App / IDE)에서 `agy agents` 또는 스킬 목록으로 반영 여부를 확인하세요. 자세한 운영 원칙은 [HARNESS.md](HARNESS.md)를 참고하세요.

## 설계 근거

- [Antigravity Skills](https://antigravity.google/docs/skills): 스킬은 progressive disclosure로 로드되므로 본문을 짧게 유지합니다.
- [Antigravity Custom Subagents](https://antigravity.google/docs/subagents): 격리 가치가 있는 독립 작업에만 서브에이전트를 사용합니다.
- [Antigravity Hooks](https://antigravity.google/docs/hooks): `PreToolUse` JSON 계약(`toolCall.args` → `{"decision":"allow"|"deny"}`)으로 최소 안전 가드만 둡니다.
