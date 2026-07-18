# AgentDeck

MPK Mini Mk4 as a Claude Code status deck for the VS Code extension. See
[CLAUDE.md](CLAUDE.md) for the original project brief/research and
[research/NOTES.md](research/NOTES.md) for the live-verified MIDI protocol.

**MVP scope**: Claude Code + the VS Code extension only. No terminal/tmux, no
opencode, no voice/STT — see the MVP prompt this scope was narrowed from for the
full rationale. opencode support is a possible post-MVP target; nothing for it is
wired up.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Merge [hooks/claude-settings.snippet.json](hooks/claude-settings.snippet.json)'s
`hooks` block into `~/.claude/settings.json` (global, so it applies across every
repo/session).

For each repo you'll work in:

```bash
.venv/bin/python tools/assign_slot.py <slot 1-8> /path/to/repo --label short-name
```

This writes `~/.agentdeck/slots.json` (slot -> repo, used for window-raising) and
that repo's `.claude/settings.local.json` `env` block with `AGENTDECK_SLOT` and the
anti-spoofing token the global hooks need (see `daemon/auth.py`) — the VS Code
extension has no shell to `export` from, so this is how the slot/token reach it.
`settings.local.json` is gitignored; never commit it.

## Running

```bash
.venv/bin/python -m daemon.main
```

Starts the HTTP hub (127.0.0.1:8765), MIDI I/O on the device's DAW Port, and the
menu bar app.

## The two tiers

- **Tier 1 — permissions**: resolved entirely on the deck. Pad blinks amber-fast,
  press Play/Stop to allow once, Loop to allow always (writes a conservative rule
  to the repo's `settings.json`), Record to deny.
- **Tier 2 — questions**: the deck can't answer these (no programmatic answer path
  exists for `AskUserQuestion`). Pad blinks blue-slow; Shift+pad raises the VS Code
  window so you answer it yourself.

## Status

See [progressboard.md](progressboard.md) for a running log of what's been done.
