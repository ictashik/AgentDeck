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
    "waiting_input",
    "done",
    "error",
]

VALID_STATES: frozenset[str] = frozenset(
    ("idle", "thinking", "running_tool", "waiting_permission", "waiting_input", "done", "error")
)


@dataclass
class SessionState:
    slot: int
    agent: str | None = None
    state: State = "idle"
    detail: str | None = None
    cwd: str | None = None
    updated_at: float = field(default_factory=time.time)

    def is_blinking(self) -> bool:
        return self.state == "waiting_permission"


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
