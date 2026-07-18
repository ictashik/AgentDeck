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
.venv/bin/python tools/setup_global_hooks.py
```

The last step is one-time and global: it merges `hooks/claude-settings.snippet.json`
into `~/.claude/settings.json` (backing up whatever's already there) and injects the
anti-spoofing token (`daemon/auth.py`) into its `env` block. No per-repo setup is
needed after this.

## Running

```bash
.venv/bin/python -m daemon.main
```

Starts the HTTP hub (127.0.0.1:8765), MIDI I/O on the device's DAW Port, and the
menu bar app.

## Slot assignment

Sessions are identified by their `cwd`, not a pre-configured slot number. The first
time the daemon sees a Claude Code session in a repo it doesn't recognize, every free
pad blinks white and you get a "New VS Code Window Detected" notification — press any
blinking pad to claim it for that repo. The binding sticks in `~/.agentdeck/slots.json`
across daemon restarts.

To pin a specific repo to a specific pad ahead of time instead (bypassing the
interactive claim):

```bash
.venv/bin/python tools/assign_slot.py <slot 1-8> /path/to/repo --label short-name
```

## The two tiers

- **Tier 1 — permissions**: resolved entirely on the deck. Pad blinks amber-fast,
  press Play/Stop to allow once, Loop to allow always (writes a conservative rule
  to the repo's `settings.json`), Record to deny.
- **Tier 2 — questions**: the deck can't answer these (no programmatic answer path
  exists for `AskUserQuestion`). Pad blinks blue-slow; Shift+pad raises the VS Code
  window so you answer it yourself.

## Status

See [progressboard.md](progressboard.md) for a running log of what's been done.
