#!/bin/bash
# Posts one state-transition event to the AgentDeck hub. Called from
# .claude/settings.json command hooks with the target state as $1.
#
# Claude Code hooks pass their payload as JSON on stdin (not env vars like
# $CLAUDE_TOOL_NAME — verified against code.claude.com/docs/en/hooks), so this
# reads stdin to pull tool_name/cwd/question-text when present, rather than
# relying on env.
#
# Never blocks or fails the calling hook: if AGENTDECK_SLOT isn't set, or the
# hub isn't running, this exits 0 silently so a dead hub can't break sessions.
set -u

STATE="${1:?usage: post_event.sh <state>}"
HUB_URL="${AGENTDECK_HUB_URL:-http://127.0.0.1:8765}"
SLOT="${AGENTDECK_SLOT:-}"
TOKEN_FILE="$HOME/.agentdeck/token"

[ -z "$SLOT" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"

# For waiting_question (PreToolUse matched on AskUserQuestion), prefer the
# actual question text over the tool name — that's what's useful to see on a
# notification. Field shape isn't documented, so try a couple of fallbacks.
DETAIL="$TOOL_NAME"
if [ "$STATE" = "waiting_question" ]; then
  QUESTION="$(printf '%s' "$INPUT" | jq -r '.tool_input.questions[0].question // .tool_input.question // empty' 2>/dev/null)"
  [ -n "$QUESTION" ] && DETAIL="$QUESTION"
fi

PAYLOAD="$(jq -n \
  --argjson slot "$SLOT" \
  --arg agent "claude-code" \
  --arg state "$STATE" \
  --arg detail "${DETAIL:-}" \
  --arg cwd "${CWD:-}" \
  '{slot: $slot, agent: $agent, state: $state}
   + (if $detail != "" then {detail: $detail} else {} end)
   + (if $cwd != "" then {cwd: $cwd} else {} end)')"

TOKEN_HEADER=()
if [ -f "$TOKEN_FILE" ]; then
  TOKEN_HEADER=(-H "X-AgentDeck-Token: $(cat "$TOKEN_FILE")")
fi

curl -s -m 2 -X POST "$HUB_URL/event" -H 'Content-Type: application/json' "${TOKEN_HEADER[@]}" -d "$PAYLOAD" >/dev/null 2>&1 || true
