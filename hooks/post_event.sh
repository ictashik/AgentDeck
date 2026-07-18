#!/bin/bash
# Posts one state-transition event to the AgentDeck hub. Called from
# .claude/settings.json command hooks with the target state as $1.
#
# Claude Code hooks pass their payload as JSON on stdin (not env vars like
# $CLAUDE_TOOL_NAME — verified against code.claude.com/docs/en/hooks), so this
# reads stdin to pull tool_name/cwd when present, rather than relying on env.
#
# Never blocks or fails the calling hook: if AGENTDECK_SLOT isn't set, or the
# hub isn't running, this exits 0 silently so a dead hub can't break sessions.
set -u

STATE="${1:?usage: post_event.sh <state>}"
HUB_URL="${AGENTDECK_HUB_URL:-http://127.0.0.1:8765}"
SLOT="${AGENTDECK_SLOT:-}"

[ -z "$SLOT" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"

PAYLOAD="$(jq -n \
  --argjson slot "$SLOT" \
  --arg agent "claude-code" \
  --arg state "$STATE" \
  --arg detail "${TOOL_NAME:-}" \
  --arg cwd "${CWD:-}" \
  '{slot: $slot, agent: $agent, state: $state}
   + (if $detail != "" then {detail: $detail} else {} end)
   + (if $cwd != "" then {cwd: $cwd} else {} end)')"

curl -s -m 2 -X POST "$HUB_URL/event" -H 'Content-Type: application/json' -d "$PAYLOAD" >/dev/null 2>&1 || true
