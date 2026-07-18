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
#
# The app to raise on pad press (daemon/actions.py) is detected by walking
# this process's own ancestry and checking each ancestor's full command path
# — NOT by reading $TERM_PROGRAM. $TERM_PROGRAM is an env var, and env vars
# are inherited down the process tree: if VS Code itself was ever launched
# from a terminal (e.g. `code .`), every child it spawns — including the
# extension's Claude Code subprocess — inherits that terminal's
# $TERM_PROGRAM (e.g. "Apple_Terminal"), not "vscode". That inherited-stale
# value was causing raise_window to activate a terminal instead of running
# `code -r`. Walking the live process tree instead answers "which app is
# actually running this session right now," which is what raise_window needs.
detect_app() {
  local pid="$$" cmd i
  for i in $(seq 1 12); do
    pid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
    [ -z "$pid" ] || [ "$pid" = "1" ] && return 0
    cmd="$(ps -o command= -p "$pid" 2>/dev/null)"
    case "$cmd" in
      *"Visual Studio Code.app"*) printf 'vscode'; return 0 ;;
      *"Terminal.app"*) printf 'Apple_Terminal'; return 0 ;;
      *"iTerm.app"*) printf 'iTerm.app'; return 0 ;;
    esac
  done
}
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

APP="$(detect_app)"
[ -z "$APP" ] && APP="${TERM_PROGRAM:-}"  # fallback: an app we don't recognize by path, trust $TERM_PROGRAM

PAYLOAD="$(jq -n \
  --arg cwd "$CWD" \
  --arg agent "claude-code" \
  --arg state "$STATE" \
  --arg detail "${DETAIL:-}" \
  --arg term_program "$APP" \
  '{cwd: $cwd, agent: $agent, state: $state}
   + (if $detail != "" then {detail: $detail} else {} end)
   + (if $term_program != "" then {term_program: $term_program} else {} end)')"

TOKEN_HEADER=()
if [ -f "$TOKEN_FILE" ]; then
  TOKEN_HEADER=(-H "X-AgentDeck-Token: $(cat "$TOKEN_FILE")")
fi

curl -s -m 2 -X POST "$HUB_URL/event" -H 'Content-Type: application/json' "${TOKEN_HEADER[@]}" -d "$PAYLOAD" >/dev/null 2>&1 || true
