"""FastAPI app bound to 127.0.0.1 only (CLAUDE.md §2 — no hardened security needed,
just don't expose this beyond localhost).

Day 1 scope: POST /event, GET /state.
Day 2 scope: POST /permission-wait (blocks until a MIDI accept/reject arrives).
"""

from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from daemon.state import VALID_STATES, SessionStore

app = FastAPI(title="AgentDeck hub")

# Populated by daemon/main.py before the server starts serving.
store: SessionStore | None = None

# slot -> Event, used by /permission-wait to block until MIDI resolves it (Day 2).
_pending_permissions: dict[int, threading.Event] = {}
_pending_decisions: dict[int, str] = {}
_pending_lock = threading.Lock()


class EventPayload(BaseModel):
    slot: int
    agent: str | None = None
    state: str
    detail: str | None = None
    cwd: str | None = None


@app.post("/event")
def post_event(payload: EventPayload) -> dict[str, Any]:
    if store is None:
        raise HTTPException(status_code=503, detail="store not initialized")
    if payload.state not in VALID_STATES:
        raise HTTPException(status_code=400, detail=f"unknown state: {payload.state}")

    updated = store.update(
        payload.slot,
        agent=payload.agent,
        state=payload.state,
        detail=payload.detail,
        cwd=payload.cwd,
    )
    return {"ok": True, "slot": updated.slot, "state": updated.state}


@app.get("/state")
def get_state(slot: int | None = None) -> dict[str, Any]:
    if store is None:
        raise HTTPException(status_code=503, detail="store not initialized")

    if slot is not None:
        session = store.get(slot)
        if session is None:
            raise HTTPException(status_code=404, detail=f"no such slot: {slot}")
        return {"slot": session.slot, "agent": session.agent, "state": session.state,
                "detail": session.detail, "cwd": session.cwd, "updated_at": session.updated_at}

    return {
        "focused_slot": store.get_focus(),
        "slots": [
            {"slot": s.slot, "agent": s.agent, "state": s.state, "detail": s.detail,
             "cwd": s.cwd, "updated_at": s.updated_at}
            for s in store.all()
        ],
    }


@app.post("/permission-wait")
def permission_wait(payload: EventPayload) -> dict[str, str]:
    """Marks the slot waiting_permission and blocks until resolve_permission()
    is called by the MIDI thread with an accept/reject decision.

    Stub for Day 1 — wired up fully once the MIDI accept/reject path exists
    (CLAUDE.md §10, Day 2 checklist). For now this marks the state and returns
    immediately with a default "allow" so it doesn't hang Claude Code hooks
    before the MIDI side is built.
    """
    if store is None:
        raise HTTPException(status_code=503, detail="store not initialized")

    store.update(payload.slot, agent=payload.agent, state="waiting_permission", detail=payload.detail)

    event = threading.Event()
    with _pending_lock:
        _pending_permissions[payload.slot] = event

    # Day 1: no MIDI resolver exists yet, so don't actually block indefinitely.
    # Day 2 will replace this with event.wait(timeout=...) driven by resolve_permission().
    resolved = event.wait(timeout=0.01)
    with _pending_lock:
        decision = _pending_decisions.pop(payload.slot, "allow") if resolved else "allow"
        _pending_permissions.pop(payload.slot, None)

    return {"decision": decision}


def resolve_permission(slot: int, decision: str) -> bool:
    """Called by the MIDI thread when Accept/Reject is pressed for the focused
    slot. Returns True if a pending permission-wait was actually resolved."""
    with _pending_lock:
        event = _pending_permissions.get(slot)
        if event is None:
            return False
        _pending_decisions[slot] = decision
        event.set()
        return True
