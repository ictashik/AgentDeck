#!/bin/bash
# Posts one state-transition event to the AgentDeck hub. Called from
# .claude/settings.json command hooks with the target state as $1.
#
# Sessions are identified by cwd, not a pre-configured slot number — the
# daemon resolves cwd -> slot itself (daemon/slots.py), prompting an
# interactive pad-claim if it's a repo it hasn't seen before (see
# daemon/pending_claim.py). No per-repo setup needed.
#
# Claude Code hooks pass their payload as JSON on stdin (not env vars like
# $CLAUDE_TOOL_NAME — verified against code.claude.com/docs/en/hooks), so this
# reads stdin to pull tool_name/cwd/question-text.
#
# Never blocks or fails the calling hook: if the hub isn't running, this exits
# 0 silently so a dead hub can't break sessions.
set -u

STATE="${1:?usage: post_event.sh <state>}"
HUB_URL="${AGENTDECK_HUB_URL:-http://127.0.0.1:8765}"
TOKEN_FILE="$HOME/.agentdeck/token"

INPUT="$(cat 2>/dev/null || true)"
TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"

[ -z "$CWD" ] && exit 0

# For waiting_question (PreToolUse matched on AskUserQuestion), prefer the
# actual question text over the tool name — that's what's useful to see on a
# notification. Field shape isn't documented, so try a couple of fallbacks.
DETAIL="$TOOL_NAME"
if [ "$STATE" = "waiting_question" ]; then
  QUESTION="$(printf '%s' "$INPUT" | jq -r '.tool_input.questions[0].question // .tool_input.question // empty' 2>/dev/null)"
  [ -n "$QUESTION" ] && DETAIL="$QUESTION"
fi

PAYLOAD="$(jq -n \
  --arg cwd "$CWD" \
  --arg agent "claude-code" \
  --arg state "$STATE" \
  --arg detail "${DETAIL:-}" \
  '{cwd: $cwd, agent: $agent, state: $state}
   + (if $detail != "" then {detail: $detail} else {} end)')"

TOKEN_HEADER=()
if [ -f "$TOKEN_FILE" ]; then
  TOKEN_HEADER=(-H "X-AgentDeck-Token: $(cat "$TOKEN_FILE")")
fi

curl -s -m 2 -X POST "$HUB_URL/event" -H 'Content-Type: application/json' "${TOKEN_HEADER[@]}" -d "$PAYLOAD" >/dev/null 2>&1 || true
