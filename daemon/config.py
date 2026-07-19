"""Central config: slot count, HTTP port, MIDI note/CC numbers.

Transport CCs, pad notes, and encoder CCs below are LIVE-VERIFIED against the real
unit (preset 1 / DAW) using tools/mapping_ui.py — see research/NOTES.md and
research/live_mapping.json for the raw captures. This superseded several values
from third-party docs that turned out wrong for this specific unit (Tap Tempo,
Bank -, Bank +) and confirmed this unit has no dedicated Fast Forward button.
"""

from __future__ import annotations

SLOT_COUNT = 8

HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8765

# Transport CC numbers, all on channel 1, sent on the DAW Port (not the plain
# MIDI Port). Toggle buttons (Play/Stop, Record, Loop, Undo) send 127 on press
# only, no release message. Momentary buttons (Tap Tempo, Shift, Bank -/+) send
# 127 on press, 0 on release. This unit has no dedicated Fast Forward button.
CC_PLAY_STOP = 76
CC_RECORD = 77
CC_LOOP = 74
CC_UNDO = 73
CC_TAP_TEMPO = 82  # live-verified; third-party docs said 11 — wrong for this unit
CC_SHIFT = 17
CC_BANK_MINUS = 80  # live-verified; third-party docs said 15 — wrong for this unit
CC_BANK_PLUS = 81   # live-verified; third-party docs said 16 — wrong for this unit

# Push-encoder, sent on the DAW Port. Turn is relative: value 1 = one step
# clockwise, value 127 = one step counter-clockwise (two's-complement style).
CC_ENCODER_TURN = 14
ENCODER_CW_VALUE = 1
ENCODER_CCW_VALUE = 127
CC_ENCODER_PRESS = 13

# Pad note numbers for Bank A, slots 1-8 (preset 1 / DAW), on channel 10 (the
# drum channel, 0-indexed 9 in raw MIDI). Live-verified — differs from
# third-party docs, which listed a non-contiguous 48/50/52/53/55/57/59/60.
PAD_NOTES = [36, 37, 38, 39, 40, 41, 42, 43]
PAD_CHANNEL = 9  # 0-indexed; "channel 10" in 1-indexed MIDI convention

# Live-verified, undocumented anywhere: holding Shift suppresses the pad's
# normal Note On entirely (no note_on + separate CC17 to compose in software —
# the device itself intercepts it) and instead sends a dedicated CC on the DAW
# Port: CC32 = Shift+Pad1, CC33 = Shift+Pad2, ... CC39 = Shift+Pad8. The CC
# arriving IS the Shift+Pad signal; no need to separately track Shift state.
CC_SHIFT_PAD_BASE = 32

# Live-verified: pad LED color-setting Note On messages (daemon/protocol/pad_colors.py)
# only take effect on the DAW Port — the plain MIDI Port silently does nothing.
# Port names are assigned by the OS and vary slightly; match on this substring.
PAD_LED_PORT_HINT = "DAW Port"

SLOT_ENV_VAR = "AGENTDECK_SLOT"

# MPC-style pads are pressure-sensitive and double-fire on a single physical
# press; ignore repeat Note On for the same slot within this window.
PAD_DEBOUNCE_SECONDS = 0.4

# How long /permission-wait blocks for a MIDI decision before giving up and
# returning "no decision" (letting Claude Code's own prompt show). Kept a bit
# under the hook's own "timeout" in hooks/claude-settings.snippet.json so this
# server responds cleanly instead of the hook timing out first.
PERMISSION_WAIT_TIMEOUT_SECONDS = 290

# System Events process name for VS Code, used by daemon/actions.py to target
# the specific window for a repo (by basename match on its title) rather than
# just bringing *some* VS Code window forward. Needs Accessibility permission
# granted to whatever process runs the daemon — same requirement the old
# window_sweep had; degrades to a blanket app-activate if it's not granted.
VSCODE_PROCESS_NAME = "Code"

# Slot bindings record which app is running the Claude Code session — detected
# by hooks/post_event.sh walking its own process ancestry (NOT read from
# $TERM_PROGRAM, which is inherited down the process tree and goes stale: a VS
# Code session whose app was ever launched from a terminal inherits that
# terminal's $TERM_PROGRAM, wrongly reporting itself as a terminal). Keys here
# match detect_app()'s output; values are the app name AppleScript's
# `tell application "..."` expects. Best-effort/unverified beyond "vscode" and
# "Apple_Terminal" — extend detect_app()'s path matches (and this map) as
# other terminals get used for real. Unrecognized values are not activated
# (avoids passing an untrusted string straight into an AppleScript string).
TERM_PROGRAM_APP_NAMES = {
    "vscode": "Visual Studio Code",
    "Apple_Terminal": "Terminal",
    "iTerm.app": "iTerm2",
}

# Record+Pad unbinds a slot (daemon/midi_io.py): Record arms a short window,
# and the next pad press within it unbinds that slot instead of focusing it.
UNBIND_ARM_SECONDS = 2.5
