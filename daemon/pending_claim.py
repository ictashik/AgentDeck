"""Interactive slot-claiming: when a hook reports a `cwd` with no binding in
slots.json, it goes into a claim queue here. The free pads blink (see
daemon/midi_io.py's LED refresh) until the user presses one of them, which
claims that slot for the head-of-queue cwd via daemon.slots.assign().

Only one cwd is "active" (blinking) at a time — if more show up while one is
pending, they queue behind it. Keeps the "which press claims which repo"
question unambiguous without needing per-cwd UI.
"""

from __future__ import annotations

import threading
from pathlib import Path

from daemon import slots

_lock = threading.Lock()
_queue: list[str] = []
_claim_events: dict[str, threading.Event] = {}
_claim_results: dict[str, int] = {}


def enqueue(cwd: str) -> bool:
    """Adds `cwd` to the claim queue if it isn't already bound or already
    queued. Returns True if this is a newly-seen pending cwd (so the caller
    can fire a one-time notification), False otherwise."""
    if slots.find_slot_for_cwd(cwd) is not None:
        return False
    with _lock:
        if cwd in _queue:
            return False
        _queue.append(cwd)
        _claim_events[cwd] = threading.Event()
        return True


def current_pending_cwd() -> str | None:
    with _lock:
        return _queue[0] if _queue else None


def claim(slot: int) -> str | None:
    """Called when a free pad is pressed. Binds `slot` to the head-of-queue
    cwd, if any. Returns the claimed cwd, or None if nothing was pending."""
    with _lock:
        if not _queue:
            return None
        cwd = _queue.pop(0)
        event = _claim_events.pop(cwd)

    slots.assign(slot, cwd, label=Path(cwd).name)
    with _lock:
        _claim_results[cwd] = slot
    event.set()
    return cwd


def wait_for_claim(cwd: str, timeout: float) -> int | None:
    """Blocks (for /permission-wait's use) until `cwd` is claimed or timeout
    elapses. Returns the assigned slot, or None on timeout."""
    with _lock:
        event = _claim_events.get(cwd)
    if event is None:
        # Already claimed (or never enqueued) — check directly.
        return slots.find_slot_for_cwd(cwd)

    if not event.wait(timeout=timeout):
        return None
    with _lock:
        return _claim_results.pop(cwd, None)
