# Antigravity (AGY) Code Harness 운영 가이드

이 하네스는 모든 작업을 무겁게 만드는 프레임워크가 아닙니다. 작은 일은 Antigravity 메인이 바로 처리하고, 판단과 검증을 분리할 가치가 있는 일에만 커스텀 서브에이전트를 사용합니다.

## 어떤 흐름을 고를까요?

오탈자, 작은 설정 수정, 설명 요청은 메인이 직접 처리합니다. 여러 파일을 바꾸거나 인수 기준이 필요하거나 실패 비용이 큰 작업은 아래 흐름으로 진행합니다.

```text
요구사항 → plan → work → review → release
```

전체 조율이 필요하면 `orchestrator` 스킬을 호출합니다. `orchestrator`는 필요한 단계만 선택하며, 모든 서브에이전트를 의무적으로 호출하지 않습니다.

---

## 단계별 역할

### `plan`

`planner`가 코드와 요구사항을 읽고 `Plans.md`에 작은 Phase와 검증 가능한 인수 기준을 작성합니다. 요구사항이 이미 명확한 사소한 변경에는 생략할 수 있습니다.

### `work`

`coder`가 승인된 Phase 하나만 구현하고 관련 테스트를 실행합니다. 로그가 길거나 별도의 검증 관점이 필요한 경우에만 `tester`를 호출합니다. `coder`와 `tester`는 커밋이나 푸시를 하지 않습니다.

### `review`

`reviewer`가 다음 네 관점을 한 번에 확인합니다.

- 스펙 정합성
- 보안
- 정확성·유지보수성
- 성능·운영성

직접 `review`를 호출하면 한 번만 검토하고 결과를 반환합니다. 자동 수정 반복은 `orchestrator`의 책임입니다.

### `release`

사용자가 명시적으로 요청한 경우에만 `documenter`, 커밋, 푸시, PR 준비를 수행합니다. 리뷰를 우회하거나 자동으로 머지하지 않습니다.

---

## 수정·재리뷰 규칙

`orchestrator`는 최초 리뷰를 포함해 최대 3회의 리뷰를 조율합니다. 문제가 있으면 `send_message`로 같은 `coder`에게 수정을 요청하고 같은 `reviewer`에게 재검토를 맡겨 문맥 손실을 줄입니다.

다음 조건에서는 즉시 멈춥니다.

- `reviewer`가 `<verdict>APPROVE</verdict>`를 반환했습니다.
- 같은 지적이 실질적 변화 없이 반복됐습니다.
- `reviewer` 결과가 없거나 판정이 불명확합니다(`UNKNOWN`).
- 세 번째 리뷰에서도 승인되지 않았습니다.
- 사용자 선택이나 외부 권한이 필요합니다.

`Stop` 훅으로 정상 종료를 막거나 오케스트레이터를 다시 실행하지 않습니다. 이 규칙은 대화 안의 명시적인 작업 흐름이며, 상태 파일이나 외부 runner에 의존하지 않습니다.

---

## 서브에이전트 설정 (Gemini 4)

| 에이전트 | 모델 | 명령 정책 | 주 역할 |
|---|---|---|---|
| 메인(권장) | `gemini-4-neon-medium` | - | 사용자와 작업 조율, 작은 작업 직접 처리 |
| planner | `gemini-4-carbon-high` | `off` | 요구사항·위험·인수 기준 판단 |
| reviewer | `gemini-4-carbon-high` | `sandbox` | 독립 4관점 리뷰 |
| coder | `gemini-4-neon-high` | `sandbox` | 승인된 Phase 구현 |
| tester | `gemini-4-neon-high` | `sandbox` | 선택적 독립 검증 |
| explorer | `gemini-4-argon-medium` | `sandbox` | 읽기 전용 코드 탐색 |
| documenter | `gemini-4-argon-low` | `off` | 검증된 동작의 문서 동기화 |

서브에이전트 프롬프트에는 역할과 금지사항만 둡니다. 프로젝트 규칙과 인수 기준은 호출할 때 필요한 부분만 전달해 반복 토큰을 줄입니다.

---

## 안전 훅

기본 설정(`.agents/hooks.json`의 `agy-harness-safety`)에는 두 개의 `PreToolUse` 훅만 있습니다.

- `block-destructive.sh` (`matcher: "run_command"`): 광범위한 삭제(`rm -rf /`, `$HOME`, 시스템 경로), 강제 Git 푸시(`--force`, `-f`, `+refspec`), `git reset --hard origin/*`, 물리 디스크 `dd`를 차단합니다.
- `protect-secrets.sh` (`matcher: "write_file|edit_file|write_to_file|replace_file_content|multi_replace_file_content"`): `.env`, 개인키, credentials, `mcp_config.json` 같은 비밀 파일 쓰기를 차단합니다.

두 훅은 Antigravity `PreToolUse` JSON 계약을 따르며, 차단 시 `{"decision":"deny","reason":"..."}`, 통과 시 `{"decision":"allow"}`를 출력합니다. 안전 훅은 보조 가드이며 Antigravity의 권한 설정과 터미널 샌드박스를 대신하지 않습니다.

---

## 설치와 업데이트

정본 저장소에서 설치기를 실행합니다.

```bash
python3 scripts/install.py
```

설치기는 `~/.gemini/config`에 에이전트·스킬·안전 훅 심볼릭 링크를 맞추고 `~/.gemini/config/hooks.json`에 `agy-harness-safety` 항목만 병합합니다. 기존 사용자 훅이나 프로젝트 전용 스킬은 건드리지 않습니다.

특정 프로젝트의 `.agents/`에 과거 복제본이 있다면 `--workspace`로 함께 정리할 수 있습니다.

```bash
python3 scripts/install.py --workspace /path/to/project --dry-run
```

---

## 검증과 문제 해결

저장소 자체 검증은 아래 두 명령이면 충분합니다.

```bash
python3 -m unittest discover -s tests -v
bash .agents/hooks/tests/run-tests.sh
```

스킬이나 서브에이전트가 보이지 않으면 새 Antigravity 세션에서 확인하세요. 훅 오류가 나면 `~/.gemini/config/hooks.json`과 프로젝트의 `.agents/hooks.json`을 함께 확인해야 합니다.

모델이나 에이전트 역할을 바꾸면 `.agents/agents/*.md`, `README.md`, 이 문서의 표를 함께 수정하고 계약 테스트를 실행하세요.
