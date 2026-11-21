#!/bin/bash
# Antigravity PreToolUse hook (matcher: write_file|edit_file|write_to_file|replace_file_content|multi_replace_file_content):
# block writes to secret-bearing files.
# Protocol: stdout JSON {"decision":"deny","reason":"..."} to block, {"decision":"allow"} to pass through (exit 0).
set -u

INPUT=$(cat)

allow() {
  printf '{"decision":"allow"}\n'
  exit 0
}

block() {
  local reason="BLOCKED (protect-secrets.sh): $1"
  if command -v jq >/dev/null 2>&1; then
    jq -nc --arg reason "$reason" '{decision: "deny", reason: $reason}'
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json, sys; print(json.dumps({"decision": "deny", "reason": sys.argv[1]}))' "$reason"
  else
    printf '{"decision":"deny","reason":"BLOCKED (protect-secrets.sh)"}\n'
  fi
  exit 0
}

# --- JSON extraction: jq -> python3 -> loud-warn fail-open (never silent) ---
if command -v jq >/dev/null 2>&1; then
  FILE=$(printf '%s' "$INPUT" | jq -r '.toolCall.args.Path // .toolCall.args.TargetFile // .toolCall.args.file_path // .toolCall.args.path // ""' 2>/dev/null) || FILE=""
elif command -v python3 >/dev/null 2>&1; then
  FILE=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    args = json.load(sys.stdin).get("toolCall", {}).get("args", {})
    print(args.get("Path") or args.get("TargetFile") or args.get("file_path") or args.get("path") or "")
except Exception:
    pass
' 2>/dev/null) || FILE=""
else
  echo "[protect-secrets] WARNING: jq and python3 both missing — secret-write guard is DISABLED" >&2
  allow
fi
[ -z "$FILE" ] && allow

BASE="${FILE##*/}"

# Docs/templates that merely mention secret-ish words in their name are fine
# (.env.example, secret-rotation.md, ...).
case "$BASE" in
  *.md|*.txt|*.rst|*.example|*.sample|*.template) allow ;;
esac

case "$BASE" in
  *.env|*.env.*|*.envrc)
    block "Refusing to write env files ('$BASE'). Edit them by hand if needed." ;;
  *.pem|*.key|*.p12|*.pfx|*.p8|*.keystore)
    block "Refusing to write key/cert files ('$BASE')." ;;
  id_rsa*|id_ed25519*)
    block "Refusing to write SSH key files ('$BASE')." ;;
  .npmrc|.pypirc|.htpasswd)
    block "Refusing to write auth config files ('$BASE') — they often hold tokens." ;;
  # Credential-shaped names only — source files like token_service.py or
  # design-tokens.css must pass.
  *credentials*.json|*credentials*.yaml|*credentials*.yml|*secret*.json|*secret*.yaml|*secret*.yml|*token*.json|*token*.yaml|*token*.yml)
    block "File name looks credential-bearing ('$BASE'). Refusing to write." ;;
  .*credentials*|.*secret*|.*token*)
    block "Dotfile name looks credential-bearing ('$BASE'). Refusing to write." ;;
  *.mcp.json|mcp.json|mcp_config.json)
    block "Refusing to write MCP config ('$BASE') — may contain MCP tokens. Edit manually." ;;
esac

allow
