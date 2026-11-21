#!/bin/bash
set -u

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
BLOCK="$ROOT/.agents/hooks/block-destructive.sh"
SECRETS="$ROOT/.agents/hooks/protect-secrets.sh"
passed=0
failed=0

extract_decision() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.decision // ""' 2>/dev/null
  else
    python3 -c 'import json, sys; print(json.load(sys.stdin).get("decision", ""))' 2>/dev/null
  fi
}

check() {
  local name="$1" expected="$2" script="$3" payload="$4" output status actual
  set +e
  output=$(printf '%s' "$payload" | bash "$script" 2>/dev/null)
  status=$?
  set -e
  actual=$(printf '%s' "$output" | extract_decision)
  if [ "$status" -eq 0 ] && [ "$actual" = "$expected" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL %s: expected status=0 decision=%s, got status=%s decision=%s (out=%s)\n' \
      "$name" "$expected" "$status" "$actual" "$output" >&2
  fi
}

set -e

check "root rm" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf /"}}}'
check "home rm" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf $HOME"}}}'
check "system rm in compound command" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"echo ok && rm -rf /etc/cache"}}}'
check "force push" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"git push --force origin main"}}}'
check "short force push" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"git -C repo push -f origin main"}}}'
check "force refspec" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"git push origin +main"}}}'
check "remote hard reset" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"git reset --hard origin/main"}}}'
check "physical disk write" "deny" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"dd if=/tmp/x of=/dev/rdisk2"}}}'
check "build cleanup" "allow" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf build"}}}'
check "normal push" "allow" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"git push origin feature/x"}}}'
check "local hard reset" "allow" "$BLOCK" '{"toolCall":{"name":"run_command","args":{"CommandLine":"git reset --hard HEAD~1"}}}'
check "invalid input fails open" "allow" "$BLOCK" 'not-json'

check "env file (CLI Path)" "deny" "$SECRETS" '{"toolCall":{"name":"write_file","args":{"Path":"/tmp/.env.local"}}}'
check "private key (IDE TargetFile)" "deny" "$SECRETS" '{"toolCall":{"name":"write_to_file","args":{"TargetFile":"/tmp/client.pem"}}}'
check "credential json" "deny" "$SECRETS" '{"toolCall":{"name":"edit_file","args":{"Path":"/tmp/aws-credentials.json"}}}'
check "mcp config" "deny" "$SECRETS" '{"toolCall":{"name":"write_file","args":{"Path":"/tmp/mcp_config.json"}}}'
check "dot mcp config" "deny" "$SECRETS" '{"toolCall":{"name":"write_file","args":{"Path":"/tmp/.mcp.json"}}}'
check "env template" "allow" "$SECRETS" '{"toolCall":{"name":"write_file","args":{"Path":"/tmp/.env.example"}}}'
check "credential docs" "allow" "$SECRETS" '{"toolCall":{"name":"write_file","args":{"Path":"/tmp/credentials.md"}}}'
check "source token name" "allow" "$SECRETS" '{"toolCall":{"name":"edit_file","args":{"Path":"/tmp/token_service.py"}}}'
check "ordinary source" "allow" "$SECRETS" '{"toolCall":{"name":"replace_file_content","args":{"TargetFile":"/tmp/service.py"}}}'

printf '%s passed, %s failed\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
