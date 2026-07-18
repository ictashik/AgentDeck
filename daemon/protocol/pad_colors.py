"""Pad RGB color protocol for the MPK Mini Mk4 ("MPK mini IV").

STATUS: live-verified against the real unit. See research/NOTES.md ("Live
verification: pad LED color") for the full session. Confirmed scheme: pad LEDs
are set via a plain Note On — no SysEx — sent on the **DAW Port specifically**
(the same port transport CCs turned out to require; the plain MIDI Port does
nothing for LEDs), where the MIDI *channel* selects brightness/blink mode and
the *velocity* selects color:

    note_on(status=0x90 + channel, note=<pad's note number>, velocity=<color>)

Confirmed channel semantics (0-indexed MIDI channel byte):
- 0-3: steady, increasing brightness (0=dim, 3=bright)
- 6: also steady (untested how it differs from 0-3; not used here)
- 7-15: blinking, with the blink interval getting *longer* as the channel
  number increases (7=fastest blink, 15=slowest)

Color velocity values were already correct from the decompiled Ableton script
(research/akai_script_dump/MPK_mini_IV/colors.py) and are now confirmed live —
all work as expected except GREY, which is visually too dim to distinguish
from OFF on this unit.
"""

from __future__ import annotations

from dataclasses import dataclass

# Color index -> velocity byte. Live-confirmed against the real unit; GREY is
# visually indistinguishable from OFF (too dim), everything else is clearly distinct.
COLOR_OFF = 0
COLOR_GREY = 1
COLOR_WHITE = 3
COLOR_RED = 5
COLOR_AMBER = 9
COLOR_GREEN = 21
COLOR_BLUE = 45

# Channel semantics, live-confirmed (see module docstring). Must be sent on the
# DAW Port — see daemon.config.PAD_LED_PORT_HINT.
BRIGHTNESS_DIM = 0
BRIGHTNESS_BRIGHT = 3
BLINK_FAST = 7
BLINK_SLOW = 15

NOTE_ON_STATUS = 0x90


@dataclass(frozen=True)
class PadColorMessage:
    """A single MIDI Note On message that sets one pad's LED. Must be sent on
    the DAW Port, not the plain MIDI Port — see daemon.config.PAD_LED_PORT_HINT."""

    status: int
    note: int
    velocity: int

    def to_bytes(self) -> bytes:
        return bytes((self.status, self.note, self.velocity))


def pad_color_message(note: int, color: int, *, channel: int = BRIGHTNESS_BRIGHT) -> PadColorMessage:
    """Builds the Note On message that sets a pad's LED.

    `note` is the pad's assigned note number (see daemon.config.PAD_NOTES).
    `color` is one of the COLOR_* constants above.
    `channel` picks brightness/blink mode — see module docstring.
    """
    return PadColorMessage(status=NOTE_ON_STATUS + channel, note=note, velocity=color)


# CLAUDE.md §6 state -> pad color mapping. Only waiting_permission blinks per
# §6 ("Only waiting_permission blinks... Everything else is display-only"), so
# it's the only state using a BLINK_* channel; error uses the same RED at
# steady brightness to stay visually distinct from it.
STATE_COLORS: dict[str, tuple[int, int]] = {
    "idle": (COLOR_WHITE, BRIGHTNESS_DIM),
    "thinking": (COLOR_BLUE, BRIGHTNESS_BRIGHT),
    "running_tool": (COLOR_AMBER, BRIGHTNESS_BRIGHT),
    "waiting_permission": (COLOR_RED, BLINK_FAST),
    "waiting_input": (COLOR_AMBER, BRIGHTNESS_DIM),
    "done": (COLOR_GREEN, BRIGHTNESS_BRIGHT),
    "error": (COLOR_RED, BRIGHTNESS_BRIGHT),
}


def message_for_state(note: int, state: str) -> PadColorMessage:
    color, channel = STATE_COLORS.get(state, (COLOR_OFF, BRIGHTNESS_DIM))
    return pad_color_message(note, color, channel=channel)
