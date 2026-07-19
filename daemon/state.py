"""SessionState model and thread-safe SessionStore.

Slots are statically assigned (CLAUDE.md §5) via AGENTDECK_SLOT — the hub never
auto-discovers sessions, it just reflects whatever state each slot last reported.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, replace
from typing import Literal

from daemon.config import SLOT_COUNT

State = Literal[
    "idle",
    "thinking",
    "running_tool",
    "waiting_permission",
    "waiting_question",
    "waiting_input",
    "done",
    "error",
]

VALID_STATES: frozenset[str] = frozenset(
    (
        "idle",
        "thinking",
        "running_tool",
        "waiting_permission",
        "waiting_question",
        "waiting_input",
        "done",
        "error",
    )
)

# States that blink on the pad (CLAUDE.md §6 said only waiting_permission; the
# MVP prompt adds waiting_question with a visually distinct slower rhythm).
BLINKING_STATES: frozenset[str] = frozenset(("waiting_permission", "waiting_question"))


@dataclass
class SessionState:
    slot: int
    agent: str | None = None
    state: State = "idle"
    detail: str | None = None
    cwd: str | None = None
    updated_at: float = field(default_factory=time.time)

    def is_blinking(self) -> bool:
        return self.state in BLINKING_STATES


class SessionStore:
    """Dict of slot -> SessionState, guarded by a lock. Also tracks which slot
    is currently "focused" (per CLAUDE.md §1 steps 3-5: pad press or encoder
    scroll sets focus, Accept/Reject act on the focused slot)."""

    def __init__(self, slot_count: int = SLOT_COUNT) -> None:
        self._lock = threading.Lock()
        self._slots: dict[int, SessionState] = {
            slot: SessionState(slot=slot) for slot in range(1, slot_count + 1)
        }
        self._focused_slot: int | None = None
        # True from construction until daemon/main.py finishes startup (token,
        # HTTP server, MIDI ports, the initial VS Code window sweep). All pads
        # blink while this is set — see midi_io._refresh_pad_colors.
        self._loading = True
        # Whether the MPK's DAW Port is currently open (daemon/midi_io.py sets
        # this) — exposed over HTTP so the SwiftUI widget's connection glyph
        # can reflect it without the widget needing to touch MIDI itself.
        self._midi_connected = False

    def update(
        self,
        slot: int,
        *,
        agent: str | None = None,
        state: State | None = None,
        detail: str | None = None,
        cwd: str | None = None,
    ) -> SessionState:
        with self._lock:
            current = self._slots.get(slot)
            if current is None:
                current = SessionState(slot=slot)
            updated = replace(
                current,
                agent=agent if agent is not None else current.agent,
                state=state if state is not None else current.state,
                detail=detail if detail is not None else current.detail,
                cwd=cwd if cwd is not None else current.cwd,
                updated_at=time.time(),
            )
            self._slots[slot] = updated
            return updated

    def get(self, slot: int) -> SessionState | None:
        with self._lock:
            return self._slots.get(slot)

    def reset(self, slot: int) -> None:
        """Clears a slot back to its default idle/unbound look — used when
        Record+Pad manually unbinds a slot (see daemon/midi_io.py)."""
        with self._lock:
            self._slots[slot] = SessionState(slot=slot)
            if self._focused_slot == slot:
                self._focused_slot = None

    def all(self) -> list[SessionState]:
        with self._lock:
            return [self._slots[slot] for slot in sorted(self._slots)]

    def set_focus(self, slot: int) -> None:
        with self._lock:
            if slot in self._slots:
                self._focused_slot = slot

    def get_focus(self) -> int | None:
        with self._lock:
            return self._focused_slot

    def any_waiting_permission(self) -> bool:
        with self._lock:
            return any(s.state == "waiting_permission" for s in self._slots.values())

    def any_blinking(self) -> bool:
        with self._lock:
            return any(s.state in BLINKING_STATES for s in self._slots.values())

    def is_loading(self) -> bool:
        with self._lock:
            return self._loading

    def set_loading(self, loading: bool) -> None:
        with self._lock:
            self._loading = loading

    def is_midi_connected(self) -> bool:
        with self._lock:
            return self._midi_connected

    def set_midi_connected(self, connected: bool) -> None:
        with self._lock:
            self._midi_connected = connected
