# AgentDeck

**A physical status board for your Claude Code sessions.**

AgentDeck turns the top control section of an AKAI MPK Mini Mk4 — 8 RGB pads, a
push-encoder, and a transport strip — into an always-on dashboard for up to 8
parallel Claude Code sessions. Glance at your desk to see which session is
thinking, which one's running a tool, and which one is stuck waiting on you.
Press a pad to jump straight to it. Hit a transport button to accept or reject
a permission prompt without ever touching the keyboard.

No MPK on your desk? AgentDeck ships a full native macOS menu bar widget that
does everything the hardware does — same colors, same interactions, same
one-tap accept/reject — so the software half is a complete product on its own.

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-black" alt="macOS" />
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/swift-5-orange" alt="Swift 5" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
</p>

---

## Why

Running several Claude Code sessions at once means several terminal tabs or
VS Code windows quietly competing for your attention. Something finishes,
something wants a permission, something asks a question — and the only way
to know is to keep tabbing over and checking. AgentDeck moves that ambient
awareness off the screen entirely: 8 pads, 8 sessions, one glance.

- **Ambient status** — every pad is always lit to reflect its session's state:
  idle, thinking, running a tool, waiting on you, done, or errored.
- **Attention** — a session that needs a decision makes its pad blink.
- **Glance** — press the blinking pad; a notification (or the widget's peek)
  shows exactly what it's asking, and raises that session's window.
- **Decide** — dedicated transport buttons act as global Accept / Allow
  Always / Reject for whichever session is focused. No keyboard required.

It works identically with the physical hardware unplugged — the widget is
the deck.

---

## How it works

```
                    ┌─────────────────────────────────────┐
                    │         daemon (Python, headless)     │
 MPK Mini Mk4  MIDI │                                        │
 pads / encoder ───▶│  midi_io.py  ──▶  state.py (SessionStore) │
 / transport   ◀────│                        ▲    │           │
 (pad colors)       │                        │    ▼           │
                    │                 http_api.py (FastAPI,    │
                    │                 127.0.0.1, token-checked)│
                    └───────────────────▲───────────┬─────────┘
                                         │           │
                          POST /event    │           │  GET /events (SSE)
                                         │           ▼
                          Claude Code hooks     widget/ (SwiftUI,
                          (~/.claude/settings)   notch-anchored menu
                                                 bar app)
```

- **`daemon/`** — a single headless Python process. Claude Code hooks POST
  session lifecycle events to it; it drives the MPK's pad colors over MIDI
  and serves state to the widget over HTTP + Server-Sent Events. No database,
  no window enumeration — sessions are identified purely by `cwd`.
- **`widget/`** — a native SwiftUI menu bar app that mirrors the hardware
  exactly (same color vocabulary, same accept/reject/allow-always actions)
  and works fully standalone if no MPK is plugged in.
- **`hooks/`** — the Claude Code hook wiring that reports session state and
  blocks on permission prompts until you resolve them from the deck.

Two tiers of "needs you":

| Tier | What | How you resolve it |
|---|---|---|
| **Permissions** | A tool call needs approval | Pad blinks amber, fast. **Play/Stop** = allow once, **Loop** = allow always, **Record** = deny. |
| **Questions** | `AskUserQuestion` — no programmatic answer path exists | Pad blinks blue, slow. **Shift+pad** (or the widget) raises the session's window so you answer it yourself. |

For the full protocol notes, live-verified MIDI mapping, and build history,
see [`research/NOTES.md`](research/NOTES.md), [`daemon/config.py`](daemon/config.py),
and [`progressboard.md`](progressboard.md). [`CLAUDE.md`](CLAUDE.md) is the
original project brief, kept for context — its "MVP status" section at the
top is the authoritative summary of what's actually shipped versus what's
stale planning.

---

## Install

You need macOS. **You do not need the MPK Mini Mk4** — everything below works
with the widget alone; the hardware is an optional bonus layer, not a
dependency. Sections below are marked accordingly.

### 1. Clone and set up the daemon (required)

```bash
git clone <this-repo-url> agentdeck
cd agentdeck
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Wire up Claude Code hooks (required, one-time, global)

```bash
.venv/bin/python tools/setup_global_hooks.py
```

This merges `hooks/claude-settings.snippet.json` into `~/.claude/settings.json`
(backing up whatever's already there), and generates a local anti-spoofing
token at `~/.agentdeck/token` sent as `X-AgentDeck-Token` on every request —
enough so another local process can't casually spoof events, not real
security (this is a personal, localhost-only tool). It's global, so every
Claude Code session on the machine reports in, regardless of project.

### 3. Start the daemon

```bash
.venv/bin/python -m daemon.main
```

This starts the HTTP hub on `127.0.0.1:8765`. It's headless — no window, no
menu bar icon of its own. If an MPK Mini Mk4 is plugged in it also opens the
MIDI connection and starts driving pad colors; if not, it just runs the hub
and logs that no MIDI device was found. Either way it's fully functional.

To have it start at login and restart automatically if it crashes:

```bash
.venv/bin/python tools/install_launchd.py     # installs a launchd agent
.venv/bin/python tools/uninstall_launchd.py   # removes it
```

Logs land in `~/.agentdeck/logs/daemon.{out,err}.log`.

### 4. Build and run the widget (recommended — this is your UI without the MPK)

```bash
cd widget
./build.sh
open build/AgentDeckWidget.app
```

`build.sh` compiles with Swift Package Manager and wraps the binary into a
real `.app` — no Xcode project needed, though the package also opens
directly in Xcode (`File → Open` on `widget/`) if you want to debug
interactively. It's a `LSUIElement` agent app (no Dock icon) that sits fused
to the notch as a slim pill of 8 dots, one per slot, exactly mirroring the
physical pad layout. Hover to peek at whatever needs attention, click to
expand the full session list, right-click for **Launch at Login** / Quit.

Move the built `.app` into `/Applications` (or `~/Applications`) before
turning on Launch at Login, so `SMAppService` tracks a stable path across
rebuilds.

At this point — daemon running, hooks installed, widget open — start a
Claude Code session anywhere and watch it show up. **No MPK required for any
of this.**

### 5. Optional: connect the MPK Mini Mk4

Plug it in before or after starting the daemon (it's detected on connect).
All 8 pads blink white briefly on daemon startup while MIDI/HTTP init, then
settle into per-slot colors. The pads, encoder, and transport buttons work
exactly as described above with no extra configuration — note numbers and
CCs are already live-verified for this unit in `daemon/config.py`.

### 6. Claim a slot for your first project

The first time the daemon sees a Claude Code hook event from a repo it
doesn't recognize, it opens an interactive claim: every free pad blinks
white (or, widget-only, a "claim" row appears in the expanded view). Press
any blinking pad — or click a free slot in the widget — to bind that repo to
it. The binding is written to `~/.agentdeck/slots.json` and persists across
restarts; nothing auto-unbinds it.

To pin a repo to a specific slot ahead of time instead:

```bash
.venv/bin/python tools/assign_slot.py <slot 1-8> /path/to/repo --label short-name
```

To free a slot: hold **Record**, then press the pad within ~2.5s (or
right-click → **Unbind** in the widget). This raises the app one last time,
then unassigns it.

---

## Requirements

- macOS (uses AppleScript/System Events for window raising, `SMAppService`
  for login items, and `NSScreen` notch geometry — this project is not
  cross-platform).
- Python 3.9+.
- Swift 5 / Xcode command line tools, only if you're building the widget
  from source (`xcode-select --install` if you don't already have them).
- An AKAI MPK Mini Mk4, entirely optional, for the physical control surface.

---

## Contributing

This started as a personal weekend tool, so the bar for contributions is
"make it better without making it heavier." A few things to know before
sending a PR:

**Read `CLAUDE.md` first, specifically the "MVP status" section at the top.**
It documents where the implementation has diverged from the original
planning brief and why — several early design decisions (window enumeration,
`code -r` for raising windows, native notification banners) were tried,
found to have real bugs, and deliberately removed. If you're about to
reintroduce one of those patterns, that section explains why it was reverted
and what replaced it — read it before re-adding it.

**Live-verify, don't guess, on the MIDI/hardware side.** Every note number,
CC number, and color scheme in `daemon/config.py` and
`daemon/protocol/pad_colors.py` was confirmed against the real unit — several
third-party docs for this exact device turned out to be wrong. If you're
extending the MIDI mapping (new controls, a different Akai unit, etc.), use
`tools/midi_monitor.py` or `tools/mapping_ui.py` to capture real messages
before hardcoding numbers, and record findings in `research/NOTES.md`.

**Keep the daemon headless and the widget as the sole UI.** There is no menu
bar app on the Python side by design (an earlier `rumps` version was
removed). New user-facing surfaces belong in `widget/`, talking to the
daemon only over the existing HTTP + SSE API in `daemon/http_api.py` — don't
reach back into the daemon's in-process state from anywhere else.

**Hardware/software color and behavior parity is a hard rule**, per
`widget/design.md`: whatever a pad does, the corresponding widget slot must
do too, and vice versa. If you add an interaction to one surface, add it to
the other in the same PR, or explain in the PR description why it can't be
mirrored (e.g. gestures with no hardware equivalent).

### Workflow

1. Fork and branch off `main`.
2. For daemon/Python changes: activate `.venv`, keep changes covered by
   whatever pattern nearby code already uses — there's no formal test suite
   yet, so a clear manual verification (e.g. via `tools/midi_monitor.py`
   or a `curl` against `daemon/http_api.py`) is expected in the PR
   description.
3. For widget/Swift changes: `cd widget && swift build`, then verify
   interactively via Xcode or `./build.sh && open build/AgentDeckWidget.app`.
4. Update `research/NOTES.md` if you touch anything protocol-related, and
   `progressboard.md` with a short entry if you land anything non-trivial —
   both are the project's running record of what's actually been verified,
   not just planned.
5. Open a PR describing what changed and, more importantly, *why* — this
   project has already been bitten once by a plausible-looking change
   (`code -r` for window raising) that turned out to be silently destructive
   in a real session; a clear rationale makes that kind of regression easier
   to catch in review.

Bug reports and small fixes are welcome without any of the above ceremony —
just include repro steps and, if it's hardware-related, which unit/firmware
you're on.

---

## License

MIT — see [LICENSE](LICENSE).
