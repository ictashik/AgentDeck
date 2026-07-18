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
menu bar app. All 8 pads blink white while it starts up (token/HTTP/MIDI init); once
that settles, each pad switches to its real per-slot color.

### Run automatically / restart on crash

```bash
.venv/bin/python tools/install_launchd.py
```

Installs a per-user `launchd` agent (`~/Library/LaunchAgents/com.agentdeck.daemon.plist`)
that starts the daemon at login and restarts it automatically if it ever exits —
`KeepAlive` in the plist. Logs go to `~/.agentdeck/logs/daemon.{out,err}.log`. Re-run
the installer any time you change the plist template to apply the update. To remove it:

```bash
.venv/bin/python tools/uninstall_launchd.py
```

## Slot assignment

Sessions are identified by their `cwd`, not a pre-configured slot number — there's no
VS Code window enumeration involved at all, so this works the same whether a session
runs in the VS Code extension, VS Code's integrated terminal, or a plain terminal app.
The first time the daemon sees a Claude Code hook event from a repo it doesn't
recognize, every free pad blinks white and you get a "New Claude Code Session Detected"
notification — press any blinking pad to claim it for that repo. The binding sticks in
`~/.agentdeck/slots.json` across daemon restarts.

Bindings are never auto-unbound (no window-close detection to get wrong). To free a pad,
hold **Record** then press the pad within ~2.5s (`UNBIND_ARM_SECONDS` in
`daemon/config.py`) — this raises the app one last time, then unassigns it and fires a
confirmation notification. Record alone still works as Reject for a pending permission,
unaffected.

Pressing a claimed pad (or Shift+pad) raises that session's app: VS Code via `code -r`
if the session came from the extension or its integrated terminal, otherwise whatever
terminal app is actually in the hook's process ancestry at the moment it fires (see
`hooks/post_event.sh`'s `detect_app`, deliberately not `$TERM_PROGRAM` — that env var is
inherited down the process tree and goes stale, e.g. a VS Code session whose app was
ever launched from a terminal would otherwise wrongly report itself as that terminal;
`daemon.config.TERM_PROGRAM_APP_NAMES` — currently maps `vscode` and `Apple_Terminal`,
live-verify others as you add them). Raising a plain terminal only brings the app
forward, not the specific window/tab — there's no `code -r`-equivalent for that.

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
  exists for `AskUserQuestion`). Pad blinks blue-slow; Shift+pad raises the session's
  app window so you answer it yourself.

## Status

See [progressboard.md](progressboard.md) for a running log of what's been done.
