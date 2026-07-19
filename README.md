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

Starts the HTTP hub (127.0.0.1:8765) and MIDI I/O on the device's DAW Port. Headless —
no UI of its own; see [Widget](#widget) below for that. All 8 pads blink white while it
starts up (token/HTTP/MIDI init); once that settles, each pad switches to its real
per-slot color.

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
recognize, every free pad blinks white and the [widget](#widget)'s expanded view shows
a claim row — press any blinking pad, or click a free slot number in the widget, to
claim it for that repo. The binding sticks in `~/.agentdeck/slots.json` across daemon
restarts.

Bindings are never auto-unbound (no window-close detection to get wrong). To free a
pad: hold **Record** then press the pad within ~2.5s (`UNBIND_ARM_SECONDS` in
`daemon/config.py`) — this raises the app one last time, then unassigns it. Record
alone still works as Reject for a pending permission, unaffected. The widget offers the
same action via right-click → Unbind on a session row.

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

## Widget

A native SwiftUI menu bar app (`widget/`) is the software UI — the daemon itself is
headless. It's a **complete, standalone interface**: every state, every color, every
interaction (accept/deny, claim, unbind, raise a window) works identically whether the
MPK is plugged in or not. See `widget/` for the design philosophy this implements.

```bash
cd widget
./build.sh
open build/AgentDeckWidget.app
```

`build.sh` compiles via Swift Package Manager and wraps the binary into a real `.app`
bundle (no Xcode project needed — the package also opens directly in Xcode via
File → Open on the `widget/` folder, if you want to debug interactively). It's an
agent app (`LSUIElement`, no Dock icon) that sits fused to the notch as a compact pill
of 8 dots — one per slot, mirroring the physical pads exactly, plus a small muted
connection glyph for whether the MPK is attached. Hover to peek at any actionable
slot, click to expand the full session list, right-click for Launch at Login / Quit.

It talks to the daemon's hub over plain HTTP + a Server-Sent-Events stream
(`GET /events`) — no hardware, no MIDI, no separate permissions beyond your existing
`~/.agentdeck/token`. Move the built `.app` to `/Applications` (or `~/Applications`)
before turning on "Launch at Login" from its right-click menu, so `SMAppService` keeps
tracking the same stable path across rebuilds.

## The two tiers

- **Tier 1 — permissions**: resolved entirely on the deck. Pad blinks amber-fast,
  press Play/Stop to allow once, Loop to allow always (writes a conservative rule
  to the repo's `settings.json`), Record to deny.
- **Tier 2 — questions**: the deck can't answer these (no programmatic answer path
  exists for `AskUserQuestion`). Pad blinks blue-slow; Shift+pad (or the widget's
  "Go to window" button) raises the session's app window so you answer it yourself.

## Status

See [progressboard.md](progressboard.md) for a running log of what's been done.
