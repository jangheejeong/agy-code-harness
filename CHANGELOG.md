# Changelog

## 2026-11-21

- `claude-code-harness`를 기반으로 Google Antigravity(`agy` CLI / App / IDE) 전용 하네스 저장소(`agy-code-harness`)를 구성했습니다.
- 커스텀 서브에이전트 6개를 `.agents/agents/*.md` 형식(Gemini 4 Carbon/Neon/Argon 모델 라우팅, `commandExecutionPolicy`, `subagent: true`, `mainAgent: false`)으로 이식했습니다.
- 스킬 6개를 `.agents/skills/*/SKILL.md`로 이식하고 `invoke_subagent` / `send_message` 기반 재시도 조율을 반영했습니다.
- 안전 훅 2개를 Antigravity `PreToolUse` JSON 입출력 계약(`toolCall.args` → `{"decision":"allow"|"deny"}`) 및 `.agents/hooks.json` 형식으로 전환했습니다.
- `~/.gemini/config` 대상 심볼릭 링크 및 `hooks.json` 안전 병합 설치기(`scripts/install.py`)와 단위/훅 테스트를 추가했습니다.
- 사람 리뷰어용 읽기 전용 PR/브랜치 워크스루 스킬(`pr-walkthrough`, 총 7개 스킬)과 `references/walkthrough-template.md` 템플릿을 추가했습니다.
- `scripts/install.py`의 `exact_skill_dir_match`를 재귀적 비심볼릭 트리 및 SHA-256 해시 검증으로 확장해 다중 파일 스킬 디렉터리의 안전한 정리와 충돌 차단을 지원합니다.
- `coder` 및 `reviewer` 에이전트에 SLAP(단일 추상화 수준)·Stepdown Rule 기반 가독성 지침(과잉 추상화 방지 포함)을 추가했습니다.
