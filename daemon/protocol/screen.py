"""Onboard screen text protocol for the MPK Mini Mk4 — UNRESOLVED, stretch goal.

No source (Ableton's decompiled control-surface script, the independent
philoSurfer/reason_akai_mpk_mini_mk4 reverse-engineering project, or general web
search) documents a free-text or fixed-field screen-write SysEx for this device.
See research/NOTES.md's "Unresolved: onboard screen text protocol" section for the
full writeup, including why blindly guessing SysEx function codes against the real
unit is riskier than it sounds (a documented warning about triggering firmware
update mode from unrelated protocol research on this same device).

Per CLAUDE.md §3/§8, this is downgraded to a stretch goal. The macOS notification
banner (rumps.notification, see daemon/menubar.py) is the primary "glance"
mechanism and does not depend on this module at all.
"""

from __future__ import annotations


def push_text(*_args: object, **_kwargs: object) -> None:
    """Not implemented — see module docstring. Intentionally a no-op stub so
    callers can wire it in optimistically without crashing before the protocol
    is cracked."""
    return None
