# Changelog

## 2026-11-21

- `claude-code-harness`를 기반으로 Google Antigravity(`agy` CLI / App / IDE) 전용 하네스 저장소(`agy-code-harness`)를 구성했습니다.
- 커스텀 서브에이전트 6개를 `.agents/agents/*.md` 형식(`model: pro|inherit|flash`, `commandExecutionPolicy`, `subagent: true`, `mainAgent: false`)으로 이식했습니다.
- 스킬 6개를 `.agents/skills/*/SKILL.md`로 이식하고 `invoke_subagent` / `send_message` 기반 재시도 조율을 반영했습니다.
- 안전 훅 2개를 Antigravity `PreToolUse` JSON 입출력 계약(`toolCall.args` → `{"decision":"allow"|"deny"}`) 및 `.agents/hooks.json` 형식으로 전환했습니다.
- `~/.gemini/config` 대상 심볼릭 링크 및 `hooks.json` 안전 병합 설치기(`scripts/install.py`)와 단위/훅 테스트를 추가했습니다.
