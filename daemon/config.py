"""Central config: slot count, HTTP port, MIDI note/CC numbers, tmux fallback targets.

The note/CC numbers below are PLACEHOLDERS from the community Mk4
reverse-engineering project referenced in CLAUDE.md §7. Verify against your own
unit with tools/midi_monitor.py before relying on them — presets can remap
these, and pad note numbers in particular vary by bank/preset.
"""

from __future__ import annotations

SLOT_COUNT = 8

HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8765

# Transport CC numbers (community-sourced, unverified for this unit — see §7).
CC_PLAY_STOP = 76
CC_RECORD = 77
CC_LOOP = 74
CC_FF = 78
CC_UNDO = 73
CC_TAP_TEMPO = 11
CC_SHIFT = 17
CC_BANK_MINUS = 15
CC_BANK_PLUS = 16

# Pad note numbers for Bank A, slots 1-8. UNVERIFIED — placeholder sequence,
# confirm with tools/midi_monitor.py against the dedicated AgentDeck preset.
PAD_NOTES = [i for i in range(1, SLOT_COUNT + 1)]

# tmux fallback: env var each session exports so Accept/Reject can fall back to
# `tmux send-keys` if the HTTP permission-wait hook doesn't behave as expected.
TMUX_TARGET_ENV_VAR = "AGENTDECK_TMUX_TARGET"
SLOT_ENV_VAR = "AGENTDECK_SLOT"
