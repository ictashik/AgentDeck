"""Central config: slot count, HTTP port, MIDI note/CC numbers, tmux fallback targets.

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

# tmux fallback: env var each session exports so Accept/Reject can fall back to
# `tmux send-keys` if the HTTP permission-wait hook doesn't behave as expected.
TMUX_TARGET_ENV_VAR = "AGENTDECK_TMUX_TARGET"
SLOT_ENV_VAR = "AGENTDECK_SLOT"
