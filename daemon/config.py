"""Central config: slot count, HTTP port, MIDI note/CC numbers, tmux fallback targets.

Transport CC numbers and pad notes below are confirmed against the default DAW
preset by three independent sources (see research/NOTES.md) — not yet re-verified
live on this specific unit with tools/midi_monitor.py, but corroborated enough to
treat as reliable defaults. Still worth a quick confirm once the dedicated
AgentDeck preset exists (CLAUDE.md §13), since presets can remap these.
"""

from __future__ import annotations

SLOT_COUNT = 8

HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8765

# Transport CC numbers, all on channel 1. Toggle buttons (Play/Stop, Record,
# Loop, FF, Undo) send 127 on press only, no release message. Momentary buttons
# (Tap Tempo, Shift, Bank -/+) send 127 on press, 0 on release.
CC_PLAY_STOP = 76
CC_RECORD = 77
CC_LOOP = 74
CC_FF = 78
CC_UNDO = 73
CC_TAP_TEMPO = 11
CC_SHIFT = 17
CC_BANK_MINUS = 15
CC_BANK_PLUS = 16

# Pad note numbers for Bank A, slots 1-8 (default DAW preset), on channel 10
# (the drum channel, 0-indexed 9 in raw MIDI). See research/NOTES.md.
PAD_NOTES = [48, 50, 52, 53, 55, 57, 59, 60]
PAD_CHANNEL = 9  # 0-indexed; "channel 10" in 1-indexed MIDI convention

# tmux fallback: env var each session exports so Accept/Reject can fall back to
# `tmux send-keys` if the HTTP permission-wait hook doesn't behave as expected.
TMUX_TARGET_ENV_VAR = "AGENTDECK_TMUX_TARGET"
SLOT_ENV_VAR = "AGENTDECK_SLOT"
