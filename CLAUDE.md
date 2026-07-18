# AgentDeck — MPK Mini Mk4 as a Claude Code / opencode status deck

> Working name, rename freely. This file is the project brief — read it fully before writing code.
> Platform: macOS (MacBook Pro). Controller: AKAI MPK Mini Mk4. Piano keys are explicitly out of scope.

## 0. MVP status — read this first

This file is the **original planning brief**, kept as-is for context. Implementation has since
moved past it in ways that make several sections below stale. Treat this section as the
override; everything after it is history, not current spec.

**Where things actually stand** (see [progressboard.md](progressboard.md) for the full history,
[research/NOTES.md](research/NOTES.md) for live-verified protocol, [README.md](README.md) for
setup):

- **Protocol discovery is done.** §8's unknowns are resolved: transport CCs, pad note numbers,
  encoder CCs, and the pad-LED-color scheme are all live-verified against the real unit (not
  guessed from third-party docs, several of which turned out wrong for this unit). Only the
  onboard screen text protocol remains unresolved — permanently downgraded to a stretch goal;
  the macOS notification banner is the real "glance" mechanism, not a fallback for it.
- **Scope narrowed to an MVP**, per an explicit follow-up prompt that takes precedence over §1's
  "Claude Code / opencode" framing and §2's non-goals:
  - **Claude Code only.** opencode is not wired up (§11's plugin sketch was never built).
    Post-MVP target, not current scope.
  - **No TTY, ever.** The user runs Claude Code exclusively through the VS Code extension, not a
    terminal. Every mention of `tmux send-keys` as an accept/reject fallback (§10) is dead —
    there is no shell to send keys into. `daemon/actions.py` raises the VS Code window instead
    (`code -r`, AppleScript fallback).
  - **No voice/STT**, contradicting §15's stretch-goal mention — not part of this project's
    direction.
  - **Local anti-spoofing token added**, tightening §2's "no hardened security" slightly: a
    token in `~/.agentdeck/token` is sent as `X-AgentDeck-Token` and checked by the hub. Still
    not real security (still localhost-only, still a personal tool) — just enough that another
    local process can't casually POST fake events.
- **The interaction flow in §1 gained a second tier.** The original flow (Accept/Reject via two
  transport buttons) only covers permission prompts. `AskUserQuestion` calls can't be answered
  by the deck at all (no programmatic answer path exists) — those get their own state
  (`waiting_question`), their own blink pattern (blue, slow — distinct from permission's amber,
  fast; no confirmed orange/violet LED velocity exists, see research/NOTES.md), and are resolved
  by **Shift+pad** raising the relevant VS Code window so the user answers it themselves, not by
  the transport buttons. §7's control table is superseded by this — see `daemon/midi_io.py` for
  the actual current mapping.
- **§10's hook JSON is wrong as written** — verified against current docs
  (code.claude.com/docs/en/hooks): the `PermissionRequest` http hook's response schema is a
  nested `hookSpecificOutput.decision.behavior`, not the flat `{"decision": "allow"}` sketched
  there. `hooks/claude-settings.snippet.json` and `daemon/http_api.py` have the corrected shape.
- **Loop button gained a real action**: "allow always" doesn't just return an allow decision, it
  writes a conservative rule to the repo's `settings.json` (`daemon/actions.py`) so the same
  command doesn't re-prompt.
- **§5's "statically assigned via an environment variable" slot model is gone.** No more
  `AGENTDECK_SLOT`, no more per-repo settings — sessions are identified by `cwd` (already in
  every hook payload) and the daemon resolves cwd -> slot via `~/.agentdeck/slots.json`
  (`daemon/slots.py`). The first session in a repo the daemon hasn't seen claims a slot
  interactively: every free pad blinks white, pressing one binds that repo to it
  (`daemon/pending_claim.py`), with a notification prompting the click. `tools/assign_slot.py`
  still exists for pre-pinning a repo to a specific slot, but it's optional now, not required
  setup. One-time global setup (token + hooks) is `tools/setup_global_hooks.py`.

## 1. What this is

We're turning the top control section of an MPK Mini Mk4 (8 RGB pads, 8 knobs, transport
buttons, push-encoder + tiny screen) into a physical status board for up to **8 parallel
Claude Code / opencode sessions**, plus a macOS menu bar app that mirrors the same state on
the monitor. It's the DIY, tool-agnostic answer to OpenAI's $230 "Codex Micro" — except it
works with the tools we actually use, and we already own the hardware.

Full context/prior research from planning: pad RGB and the onboard screen are almost
certainly SysEx-controlled, and the fastest way to learn the exact bytes is to read Akai's
own official Ableton Live control-surface script for the Mk4 rather than blind-guess via USB
sniffing (see §8, Protocol Discovery).

### Core interaction flow (design this exactly)

This is the spec, verbatim from the intended UX — implement it faithfully:

1. **Ambient status** — each of the 8 pads is always lit to reflect one session's state
   (idle / thinking / running a tool / waiting on you / done / errored). No action needed to
   see this — it's glanceable from across the room.
2. **Attention** — a session that needs a decision (permission prompt) makes its pad **blink**.
   Say session 3 needs input: pad 3 blinks red.
3. **Glance** — pressing the blinking pad fires a native macOS notification banner (and, if
   the onboard screen protocol gets cracked, a short line on the MPK's own screen too) showing
   what session 3 actually wants — e.g. `session 3 (bfit-pipeline): run "rm -rf build/"?`.
   This also marks session 3 as the **focused session**.
4. **Expand** — pressing the push-encoder opens the full menu bar dropdown, scrolled to the
   focused session, showing the complete detail (command, cwd, elapsed time, last few tool
   calls).
5. **Decide** — two dedicated transport buttons act as global **Accept** / **Reject** for
   whichever session is currently focused. Pressing one resolves it and the pad stops blinking.

Everything else (which exact bytes light which color, which button is physically "Accept") is
an implementation detail underneath this flow — don't let it drift.

## 2. Non-goals (v1)

- **No piano keybed mapping.** Ignore Note On/Off messages in the keybed's note range entirely.
- **No live "reasoning effort" dial.** Neither Claude Code nor opencode expose a documented
  API for continuously adjusting thinking budget mid-session. A knob-driven *stepped* preset
  switcher (e.g. cycle `/model` or a thinking-budget flag) is a fine v2 idea, not a v1 goal.
- **No remote/multi-machine support.** Everything runs on localhost on this Mac.
- **No hardened security.** This is a personal dev tool. Bind the local HTTP server to
  `127.0.0.1` only and don't expose it further — that's the extent of the security posture
  needed here.
- **Not trying to recreate Codex Micro's joystick "trigger a skill" gesture.** Nice stretch
  goal, not core to the brief.

## 3. Hardware reference — what's confirmed vs. unknown

Confirmed (from the official Akai user guide and product pages):

- 8 RGB-backlit MPC-style pads, velocity + pressure sensitive, 2 banks.
- 8 assignable Q-Link knobs (unused in v1 — reserved for v2).
- A dedicated transport section sending CC messages (Play/Stop, Record, Loop, FF, Undo, Tap
  Tempo, Bank +/-, Shift) — confirmed CC numbers from a community Mk4 reverse-engineering
  project: Play/Stop=CC76, Record=CC77, Loop=CC74, FF=CC78, Undo=CC73, Tap Tempo=CC11,
  Shift=CC17, Bank-=CC15, Bank+=CC16. **Verify against your own unit** with the MIDI monitor
  script in §10 before hardcoding — presets can remap these.
- A push-encoder near the screen: "turn to select and adjust settings, push to select" (per
  Akai's own user guide) — this is exactly the "browse / expand" gesture we want, reuse it as
  designed.
- A small full-color screen that Akai's own docs describe as host-drivable ("VST feedback...
  one-to-one integration... control scripts"), confirmed to visibly change content when
  Ableton's control script drives it ("confirm the screen changes to the DAW preset view").

Unknown / research required (see §8):

- Exact SysEx (or note-velocity) scheme for setting individual pad RGB colors.
- Exact SysEx scheme for pushing text to the onboard screen, and whether it's a free-text
  buffer or fixed UI fields (preset name / parameter / value).
- Whether the screen's host-driven channel requires the driving macOS app to hold foreground
  focus (Akai's own troubleshooting docs mention their bundled software losing the "control
  script connection" on focus loss — unclear if that's specific to their software or true of
  the underlying SysEx channel). **Test this early, Day 2 AM** — it determines whether the
  screen is usable at all from a background daemon.

## 4. System architecture

One long-running Python process ("the hub") does almost everything. Keep it a single process
— it avoids IPC complexity for zero benefit at this scale.

```
                         ┌───────────────────────────────────────────┐
                         │              hub (Python, 1 process)       │
                         │                                             │
 MPK Mini Mk4    MIDI in │  midi_io.py  ──▶  state.py (shared store)  │
 pads/encoder/  ─────────▶  (mido +          ▲          │             │
 transport      MIDI out │   rtmidi)         │          ▼             │
      ◀──────────────────┤                http_api.py (FastAPI,       │
 (pad colors,             │                127.0.0.1 only)             │
  screen text —           │                   ▲                        │
  once cracked)           │                   │ POST /event            │
                         │                   │                        │
                         │              menubar.py (rumps,             │
                         │              reads same state store,        │
                         │              runs on main thread)            │
                         └───────────────────────────────────────────┘
                                              ▲
                        POST /event           │           POST /event
                    ┌─────────────────────────┴─────────────────────────┐
                    │                                                     │
         Claude Code hooks                                    opencode plugin
      (.claude/settings.json,                              (TypeScript, subscribes
       shell/HTTP hook commands)                             to session/permission events)
```

Why one process: `rumps` needs the Cocoa run loop on the main thread; MIDI I/O and the HTTP
server run on background threads and mutate the same in-memory state dict behind a lock. No
database, no message broker — this is a weekend project for one person's laptop.

### Threads inside the hub

1. **Main thread** — `rumps.App` run loop (menu bar icon + dropdown).
2. **MIDI thread** — blocking `mido` input callback loop; translates pad/encoder/transport
   messages into either local UI actions (focus a session, open dropdown) or into resolving a
   pending permission (accept/reject).
3. **HTTP server thread** — FastAPI + uvicorn (or plain `http.server` if you want zero
   dependencies) bound to `127.0.0.1:8765` (pick any free local port). Both Claude Code hooks
   and the opencode plugin POST here. This is also where a `PermissionRequest`-style request
   can **block** until a MIDI accept/reject arrives (see §6).
4. Everything reads/writes one `SessionStore` object guarded by a `threading.Lock`.

## 5. Session slot model

Slots are **statically assigned via an environment variable**, not auto-discovered — this
avoids race conditions and keeps "which pad is which session" deterministic and boring.

Convention: run each of your 8 parallel sessions in its own tmux pane/window (or plain
Terminal tab), and export before launching `claude` or `opencode`:

```bash
export AGENTDECK_SLOT=3
export AGENTDECK_TMUX_TARGET="work:1.2"   # tmux session:window.pane, used only as a
                                            # keystroke-injection fallback (see §6)
claude
```

Every event the hub receives carries this slot number, so the hub never has to guess which
physical pad corresponds to which session.

## 6. State machine

```
idle ──▶ thinking ──▶ running_tool ──▶ thinking ──▶ ... ──▶ done
           │                │
           ▼                ▼
    waiting_input     waiting_permission
    (Notification,     (PermissionRequest /
     idle_prompt)       permission.asked)
```

| State               | Meaning                              | Triggered by (Claude Code)         | Triggered by (opencode)         |
|---------------------|---------------------------------------|-------------------------------------|-----------------------------------|
| `idle`              | session open, nothing happening       | `SessionStart`                      | `session.created`, `session.idle` |
| `thinking`           | model generating                      | `UserPromptSubmit`                  | `session.status`                  |
| `running_tool`        | a tool call is executing              | `PreToolUse` / `PostToolUse`        | `message.part.updated`            |
| `waiting_permission`  | **blink** — needs accept/reject       | `PermissionRequest`                 | `permission.asked`                |
| `waiting_input`       | needs attention, not a binary decision| `Notification`                      | `session.idle` (if genuinely idle-waiting) |
| `done`               | brief green flash, then back to idle  | `Stop`                              | `session.idle` after completion   |
| `error`              | orange/red solid                      | `PostToolUseFailure`                | `session.error`                   |

Only `waiting_permission` blinks and is resolvable via the Accept/Reject buttons. Everything
else is display-only.

## 7. MIDI mapping (top section only — no keybed)

Set up a **dedicated custom preset on the MPK Mini itself** (hold SHIFT + USER PRESETS, per
the Mk4's own preset-switching flow) so pads/knobs/transport reliably send fixed note/CC
numbers regardless of whatever preset you're using for actual music. Don't rely on whatever
the default/factory preset happens to send.

| Control                     | Role                                                  |
|------------------------------|--------------------------------------------------------|
| Pads 1–8 (Bank A)            | Session slots 1–8. Color = state (§6). Single press = focus + notification banner. |
| Push-encoder (turn)          | Scroll focused session up/down through the 8 slots.    |
| Push-encoder (press)         | Open/expand the menu bar dropdown for the focused session. |
| Transport: Play/Stop         | **Accept** the focused session's pending permission.    |
| Transport: Record            | **Reject** the focused session's pending permission.    |
| Transport: Bank -/+          | (v2) cycle focus without touching a pad.                |
| 8 Q-Link knobs               | Unassigned in v1. Reserved for v2 (see §12).            |

Confirm actual note/CC numbers for your unit with `tools/midi_monitor.py` (§10) before wiring
any of this — don't trust numbers from someone else's preset dump.

## 8. Protocol discovery (Day 2 critical path)

This is the one piece of the project that's genuinely unknown going in. Don't skip straight to
byte-guessing — there's a much faster path:

1. Akai ships an official Python control-surface script for the Mk4, bundled inside Ableton
   Live 11/12 (confirmed by Akai's own "MPK mini IV | Ableton Live Setup Guide" — pressing the
   DAW button and opening Live changes the onboard screen to a "DAW preset view").
2. There is a long-running, actively maintained unofficial mirror of everything Ableton ships:
   `github.com/gluon/AbletonLive12_MIDIRemoteScripts` (and an `AbletonLive11_...` sibling repo)
   — plain, unencrypted Python. Look for a folder named something like `MPK_Mini_Mk4` /
   `MPK_mini_IV` / similar.
3. Read that script. It will show the literal SysEx (or note-velocity) messages Akai's own
   code sends to set pad colors and — if it does the same for the screen — write text to it.
   This answers both the pad-color and screen-text unknowns from one source, since it's the
   same script driving both.
4. If the mirror doesn't have it yet, fall back to installing Ableton Live (a free Live Lite
   license/trial is enough) and finding the script directly under Ableton's own
   `MIDI Remote Scripts` folder on disk.
5. Last resort only: install the script in Live, open a MIDI monitor (`tools/midi_monitor.py`
   in passthrough mode, or a dedicated tool like MIDI Monitor.app) on the *output* side while
   Live drives the device, and correlate GUI actions (changing a pad's clip color, etc.) with
   the SysEx bytes that go out. This is the technique from the MPK Mini Mk3 reverse-engineering
   precedent — slower, use only if steps 1–4 come up empty.

**Write findings into `research/NOTES.md` as you go**, and once confirmed, encode them in
`daemon/protocol/pad_colors.py` (required) and `daemon/protocol/screen.py` (best-effort — if
step 3 shows the screen is fixed-field only, or focus-locked to the foreground app per §3,
downgrade it to a stretch goal and lean on the macOS notification banner as the primary
"glance" mechanism instead, per the interaction flow in §1).

## 9. Directory structure

```
agentdeck/
├── CLAUDE.md
├── README.md
├── daemon/
│   ├── main.py              # entry point — starts rumps app + background threads
│   ├── state.py              # SessionState model, thread-safe SessionStore
│   ├── midi_io.py             # mido/rtmidi in + out, translates raw MIDI <-> actions
│   ├── http_api.py            # FastAPI app: POST /event, GET /state, blocking permission wait
│   ├── menubar.py              # rumps.App subclass, menu construction, notifications
│   ├── config.py                # slot count, port, note/CC numbers, tmux fallback targets
│   └── protocol/
│       ├── pad_colors.py        # filled in after §8 research
│       └── screen.py             # filled in after §8 research (optional)
├── hooks/
│   └── claude-settings.snippet.json   # merge into .claude/settings.json per project
├── opencode-plugin/
│   └── agentdeck.ts
├── research/
│   ├── NOTES.md                  # protocol discovery findings
│   └── akai_script_dump/          # extracted reference script, for local reading only
└── tools/
    ├── midi_monitor.py            # raw MIDI logger — first thing you run
    └── send_test_sysex.py          # scratch pad for protocol experiments
```

## 10. Claude Code integration

Hooks live in `.claude/settings.json` (project) or `~/.claude/settings.json` (global — better
here, since you want this across all 8 sessions regardless of project). **Verify the current
hook event names, matcher syntax, and HTTP hook schema against
`https://code.claude.com/docs/en/hooks` before implementing** — hooks have grown a lot of
events over time and this snippet is a starting point, not gospel:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{ "type": "command",
        "command": "curl -s -X POST http://127.0.0.1:8765/event -H 'Content-Type: application/json' -d \"{\\\"slot\\\":$AGENTDECK_SLOT,\\\"agent\\\":\\\"claude-code\\\",\\\"state\\\":\\\"idle\\\"}\"" }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{ "type": "command",
        "command": "curl -s -X POST http://127.0.0.1:8765/event -d \"{\\\"slot\\\":$AGENTDECK_SLOT,\\\"agent\\\":\\\"claude-code\\\",\\\"state\\\":\\\"thinking\\\"}\"" }]
    }],
    "PreToolUse": [{
      "hooks": [{ "type": "command",
        "command": "curl -s -X POST http://127.0.0.1:8765/event -d \"{\\\"slot\\\":$AGENTDECK_SLOT,\\\"agent\\\":\\\"claude-code\\\",\\\"state\\\":\\\"running_tool\\\",\\\"detail\\\":\\\"$CLAUDE_TOOL_NAME\\\"}\"" }]
    }],
    "Stop": [{
      "hooks": [{ "type": "command",
        "command": "curl -s -X POST http://127.0.0.1:8765/event -d \"{\\\"slot\\\":$AGENTDECK_SLOT,\\\"agent\\\":\\\"claude-code\\\",\\\"state\\\":\\\"done\\\"}\"" }]
    }],
    "Notification": [{
      "hooks": [{ "type": "command",
        "command": "curl -s -X POST http://127.0.0.1:8765/event -d \"{\\\"slot\\\":$AGENTDECK_SLOT,\\\"agent\\\":\\\"claude-code\\\",\\\"state\\\":\\\"waiting_input\\\"}\"" }]
    }],
    "PermissionRequest": [{
      "hooks": [{ "type": "http",
        "url": "http://127.0.0.1:8765/permission-wait",
        "timeout": 300 }]
    }]
  }
}
```

The `PermissionRequest` HTTP hook is the important one: implement `/permission-wait` in
`http_api.py` to (a) mark the slot `waiting_permission` and start it blinking, (b) block the
HTTP response using a `threading.Event` keyed by slot, (c) when the MIDI thread sees
Accept/Reject for the focused slot, set that event with the decision, and (d) return
`{"decision": "allow"}` or `{"decision": "deny"}` to unblock Claude Code. **Confirm this exact
response schema against the docs** — treat it as the mechanism to build toward, not a
guaranteed-correct payload.

**Fallback if the HTTP hook doesn't behave as expected:** keep it simple — have Accept/Reject
instead run `tmux send-keys -t $AGENTDECK_TMUX_TARGET y Enter` / `... n Enter` into the pane
directly. Less elegant, much harder to get wrong.

## 11. opencode integration

opencode plugins are TypeScript, run inside opencode's own Bun process, and get a `client`
object — meaning this side can skip the HTTP round-trip for actions and call back into
opencode directly. Confirm the exact permission-reply method name against
`@opencode-ai/plugin`'s types before relying on it; sketch:

```ts
// opencode-plugin/agentdeck.ts
import type { Plugin } from "@opencode-ai/plugin"

const HUB = "http://127.0.0.1:8765"
const slot = process.env.AGENTDECK_SLOT

export const AgentDeck: Plugin = async ({ client }) => {
  const post = (state: string, detail?: string) =>
    fetch(`${HUB}/event`, {
      method: "POST",
      body: JSON.stringify({ slot, agent: "opencode", state, detail }),
    }).catch(() => {}) // don't crash the session if the hub isn't running

  return {
    event: async ({ event }) => {
      switch (event.type) {
        case "session.created": return post("idle")
        case "session.idle": return post("idle")
        case "session.status": return post("thinking")
        case "permission.asked":
          await post("waiting_permission", event.properties?.title)
          // TODO: poll GET /state?slot=... or hold an SSE connection open,
          // then call the real reply method once accept/reject arrives — verify
          // exact API surface (likely something under client.session.*) against
          // current @opencode-ai/plugin types.
          return
        case "permission.replied": return post("running_tool")
      }
    },
  }
}
```

## 12. Menu bar app (rumps)

`rumps` is the right tool here: pure Python (fits everything else in the daemon), and its
menu items work as literal clickable "buttons" — which is exactly what's needed for the
Accept/Reject UI. No need to reach for a SwiftUI `MenuBarExtra` app for v1; that's a fine v2
polish upgrade if you want richer visuals later, but it's a separate language/process and not
worth the weekend budget now.

- **Icon**: reflects worst-case state across all 8 slots (any `waiting_permission` → the icon
  itself blinks via a `rumps.Timer` toggling between two icon images every ~600ms; otherwise
  shows a static "all clear" icon).
- **Dropdown menu**: 8 items, one per slot, each showing a status emoji/color + short label
  (repo name or cwd basename + current state). Clicking a slot's item focuses it and shows the
  full detail as the item's submenu or via `rumps.alert`. Two more items, "Accept" and
  "Reject," act on whichever slot is currently focused — these are literally what "use the
  buttons itself to accept/reject" maps to on the software side, mirroring the transport
  buttons on hardware.
- **"Press pad → see something" mechanism**: use `rumps.notification(title, subtitle,
  message)` for the glance step (§1, step 3). This is the reliable, always-works mechanism —
  it doesn't depend on cracking the onboard screen protocol and shows up regardless of which
  app has focus. Treat pushing the same text to the MPK's own screen (once/if §8 cracks that
  protocol) as a nice-to-have duplicate, not a dependency.
- Programmatically *opening* the dropdown from a MIDI press (rather than the user clicking the
  menu bar icon) isn't exposed by rumps' high-level API — it needs a direct PyObjC call to
  simulate a click on the `NSStatusItem`'s button. Treat this as a stretch enhancement; the
  notification banner already satisfies the "see something" requirement without it.

## 13. Build plan

### Day 1 — plumbing, no protocol unknowns yet

- [ ] Scaffold the repo per §9. `pip install mido python-rtmidi rumps fastapi uvicorn`.
- [ ] `tools/midi_monitor.py`: list MIDI ports, print every incoming message. Confirm actual
      note numbers for pads and CC numbers for transport buttons/encoder on your unit.
- [ ] Set up a dedicated MPK Mini preset with fixed pad notes, save it to a user slot.
- [ ] `daemon/state.py`: `SessionState` dataclass + thread-safe `SessionStore` (dict keyed by
      slot 1–8).
- [ ] `daemon/http_api.py`: `POST /event`, `GET /state`. Run it, `curl` it manually, confirm
      state updates.
- [ ] Wire the `.claude/settings.json` snippet from §10 (command-type hooks only for now,
      skip the HTTP `PermissionRequest` hook until Day 2). Run a real Claude Code session with
      `AGENTDECK_SLOT=1` and confirm events land in `GET /state`.
- [ ] `daemon/menubar.py`: static rumps menu, 8 hardcoded rows, confirm it renders and updates
      when you manually POST to `/event`.

**End of Day 1**: a real Claude Code session's lifecycle is visible in the menu bar, driven
entirely by hooks — before any MIDI or color work exists.

### Day 2 — protocol discovery + the hardware loop

- [ ] Do §8's protocol discovery first thing. Time-box it — if pad colors aren't cracked by
      early afternoon, fall back to on/off (full-white vs. off) pads for v1 and treat color as
      a follow-up.
- [ ] Test the screen's focus-dependency question from §3 empirically, before investing more
      time in it.
- [ ] `daemon/protocol/pad_colors.py`: implement, wire into `state.py` so every state change
      pushes a color update.
- [ ] `daemon/midi_io.py`: wire pad press → focus + `rumps.notification`; encoder press →
      dropdown expand (or the alert-based stand-in); transport Play/Stop + Record → Accept/
      Reject on the focused slot.
- [ ] Implement the `PermissionRequest` HTTP hook + blocking `/permission-wait` endpoint from
      §10. Test end-to-end: trigger a real permission prompt, press a pad, confirm it resolves.
      Have the tmux `send-keys` fallback ready in case the HTTP hook's blocking behavior
      doesn't match expectations.
- [ ] `opencode-plugin/agentdeck.ts`: implement, test against a real opencode session with
      `AGENTDECK_SLOT=2`.
- [ ] Add blink logic for `waiting_permission` (timer thread toggling a color on/off).
- [ ] Optional polish: a `launchd` plist (or just a documented `./run.sh`) so the daemon
      starts automatically.

## 14. Open questions (don't guess — verify before hardcoding)

- Exact pad RGB SysEx/note-velocity scheme (§8).
- Exact screen text protocol, and whether it's foreground-focus-dependent (§3, §8).
- Current Claude Code HTTP hook JSON schema and blocking semantics — verify against
  `code.claude.com/docs/en/hooks` at implementation time, this spec's JSON is a best-effort
  sketch.
- Exact opencode `@opencode-ai/plugin` method for programmatically replying to a
  `permission.asked` event — verify against the installed package's types.

## 15. Stretch goals (v2, not this weekend)

- 8 Q-Link knobs → stepped presets (model choice, thinking-budget tier) rather than a live
  dial, per §2.
- Push-and-hold a pad → push-to-talk dictation into the focused session (you already have
  Sarvam AI / STT plumbing from the Sodiet WhatsApp work — could reuse that pattern here).
- Native SwiftUI `MenuBarExtra` rewrite of the dropdown for richer visuals (diff previews,
  etc.) once the Python version proves the concept.
- Unified dashboard showing Claude Code and opencode sessions side by side with clearer
  per-agent iconography.
