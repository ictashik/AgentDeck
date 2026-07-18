"""Pad RGB color protocol for the MPK Mini Mk4 ("MPK mini IV").

STATUS: unverified on real hardware. See research/NOTES.md for the full writeup and
sourcing. Short version: Akai's own (decompiled) Ableton Live 12 control-surface
script sets pad LEDs via a plain Note On message — no SysEx — where the MIDI
*channel* selects the brightness/blink mode and the *velocity* selects the color:

    note_on(status=0x90 + channel_offset, note=<pad's note number>, velocity=<color>)

The four channel-offset constants below (HALF/FULL/BLINK/PULSE) are a **guess**
carried over from a different device (APC64) on the same control-surface framework
generation — Ableton's dump is missing the MPK_mini_IV-specific file that would
confirm these values for this device. Do not trust them until verified live (see
research/NOTES.md's "Recommended next verification step").

Color velocity values ARE taken directly from the MPK_mini_IV-specific dump
(research/akai_script_dump/MPK_mini_IV/colors.py) and are higher-confidence than the
channel offsets, though still not yet confirmed by observation on this unit.
"""

from __future__ import annotations

from dataclasses import dataclass

# Color index -> velocity byte, from research/akai_script_dump/MPK_mini_IV/colors.py.
COLOR_OFF = 0
COLOR_GREY = 1
COLOR_WHITE = 3
COLOR_RED = 5
COLOR_AMBER = 9
COLOR_GREEN = 21
COLOR_BLUE = 45

# UNVERIFIED channel offsets — carried over from APC64/midi.py as a starting guess
# only, per research/NOTES.md. Confirm against the real MPK Mini Mk4 before trusting.
HALF_BRIGHTNESS_LED_CHANNEL = 0
FULL_BRIGHTNESS_LED_CHANNEL = 6
PULSE_LED_CHANNEL = 10
BLINK_LED_CHANNEL = 14

NOTE_ON_STATUS = 0x90


@dataclass(frozen=True)
class PadColorMessage:
    """A single MIDI Note On message that (hypothesized to) set one pad's LED."""

    status: int
    note: int
    velocity: int

    def to_bytes(self) -> bytes:
        return bytes((self.status, self.note, self.velocity))


def pad_color_message(note: int, color: int, *, channel_offset: int = FULL_BRIGHTNESS_LED_CHANNEL) -> PadColorMessage:
    """Builds the (unverified) Note On message believed to set a pad's LED.

    `note` is the pad's assigned note number (see daemon.config.PAD_NOTES).
    `color` is one of the COLOR_* constants above.
    `channel_offset` picks brightness/blink mode — see module docstring caveat.
    """
    return PadColorMessage(status=NOTE_ON_STATUS + channel_offset, note=note, velocity=color)


# CLAUDE.md §6 state -> pad color mapping. Fill in once channel offsets are
# confirmed; BLINK_LED_CHANNEL is a guess for waiting_permission's blink requirement,
# so treat that mapping as the most speculative entry here.
STATE_COLORS: dict[str, tuple[int, int]] = {
    "idle": (COLOR_WHITE, HALF_BRIGHTNESS_LED_CHANNEL),
    "thinking": (COLOR_BLUE, FULL_BRIGHTNESS_LED_CHANNEL),
    "running_tool": (COLOR_AMBER, FULL_BRIGHTNESS_LED_CHANNEL),
    "waiting_permission": (COLOR_RED, BLINK_LED_CHANNEL),
    "waiting_input": (COLOR_AMBER, PULSE_LED_CHANNEL),
    "done": (COLOR_GREEN, FULL_BRIGHTNESS_LED_CHANNEL),
    "error": (COLOR_RED, FULL_BRIGHTNESS_LED_CHANNEL),
}


def message_for_state(note: int, state: str) -> PadColorMessage:
    color, channel_offset = STATE_COLORS.get(state, (COLOR_OFF, HALF_BRIGHTNESS_LED_CHANNEL))
    return pad_color_message(note, color, channel_offset=channel_offset)
