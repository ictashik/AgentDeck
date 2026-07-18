"""FastAPI app bound to 127.0.0.1 only (CLAUDE.md §2 — no hardened security
needed beyond that, plus the optional local anti-spoofing token in daemon/auth.py).

Sessions are identified by `cwd` (present in every Claude Code hook payload
already), not a pre-configured slot number — daemon/slots.py resolves cwd ->
slot, and daemon/pending_claim.py handles the interactive "no binding yet,
blink the free pads until one is claimed" flow.

- POST /event: lifecycle updates from command hooks (post_event.sh).
- GET /state: read-only, used by the menu bar and for debugging.
- POST /permission-wait: the Tier 1 blocking hook. Verified against
  code.claude.com/docs/en/hooks — the response schema is a nested
  hookSpecificOutput.decision.behavior, NOT a flat {"decision": "allow"} as an
  earlier draft of this project assumed.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from daemon import actions, pending_claim, slots
from daemon.auth import AUTH_ENABLED, get_or_create_token
from daemon.config import PERMISSION_WAIT_TIMEOUT_SECONDS
from daemon.state import VALID_STATES, SessionStore

app = FastAPI(title="AgentDeck hub")

# Populated by daemon/main.py before the server starts serving.
store: SessionStore | None = None

# slot -> Event/decision, used by /permission-wait to block until MIDI resolves it.
# Decision is one of "allow", "allow_always", "deny".
_pending_permissions: dict[int, threading.Event] = {}
_pending_decisions: dict[int, str] = {}
_pending_lock = threading.Lock()


def require_token(x_agentdeck_token: str | None = Header(default=None)) -> None:
    if not AUTH_ENABLED:
        return
    if x_agentdeck_token != get_or_create_token():
        raise HTTPException(status_code=401, detail="missing or invalid X-AgentDeck-Token")


class EventPayload(BaseModel):
    cwd: str
    agent: str | None = None
    state: str
    detail: str | None = None


@app.post("/event")
def post_event(payload: EventPayload, x_agentdeck_token: str | None = Header(default=None)) -> dict[str, Any]:
    require_token(x_agentdeck_token)
    if store is None:
        raise HTTPException(status_code=503, detail="store not initialized")
    if payload.state not in VALID_STATES:
        raise HTTPException(status_code=400, detail=f"unknown state: {payload.state}")

    slot = slots.find_slot_for_cwd(payload.cwd)
    if slot is None:
        pending_claim.enqueue(payload.cwd)
        return {"ok": True, "pending_claim": True}

    updated = store.update(slot, agent=payload.agent, state=payload.state, detail=payload.detail, cwd=payload.cwd)
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


def _command_summary(tool_input: dict) -> str | None:
    command = tool_input.get("command")
    if isinstance(command, str):
        return command
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str):
        return file_path
    return None


@app.post("/permission-wait")
def permission_wait(payload: dict, x_agentdeck_token: str | None = Header(default=None)) -> dict:
    """The PermissionRequest http hook target. `payload` is Claude Code's own
    hook input (session_id, tool_name, tool_input, cwd, ...) — not a shape we
    control, so this is a plain dict rather than a pydantic model.
    """
    require_token(x_agentdeck_token)
    if store is None:
        raise HTTPException(status_code=503, detail="store not initialized")

    cwd = payload.get("cwd")
    if not cwd:
        raise HTTPException(status_code=400, detail="hook payload missing cwd")

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    # AskUserQuestion also fires PermissionRequest (it's a tool call requiring
    # permission), but Tier 2 is handled entirely by the PreToolUse hook +
    # Shift+pad window-raise — the deck can't answer a question, so just defer.
    if tool_name == "AskUserQuestion":
        return {}

    start = time.monotonic()
    slot = slots.find_slot_for_cwd(cwd)
    if slot is None:
        pending_claim.enqueue(cwd)
        slot = pending_claim.wait_for_claim(cwd, timeout=PERMISSION_WAIT_TIMEOUT_SECONDS)
        if slot is None:
            # Never claimed in time — no decision, let Claude Code's own
            # prompt show rather than guessing.
            return {}

    remaining = max(0.0, PERMISSION_WAIT_TIMEOUT_SECONDS - (time.monotonic() - start))

    detail = _command_summary(tool_input)
    store.update(slot, state="waiting_permission", detail=detail, cwd=cwd)

    event = threading.Event()
    with _pending_lock:
        _pending_permissions[slot] = event

    resolved = event.wait(timeout=remaining)
    with _pending_lock:
        decision = _pending_decisions.pop(slot, None) if resolved else None
        _pending_permissions.pop(slot, None)

    if decision is None:
        # No MIDI decision arrived in time — return no decision so Claude
        # Code's own permission prompt shows. Never auto-deny or auto-allow.
        return {}

    if decision == "allow_always":
        rule = actions.build_allow_rule(tool_name, tool_input)
        actions.add_allow_rule(slot, rule)
        behavior = "allow"
    else:
        behavior = decision  # "allow" or "deny"

    store.update(slot, state="thinking")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": behavior},
        }
    }


def resolve_permission(slot: int, decision: str) -> bool:
    """Called by the MIDI thread when a transport button is pressed for the
    focused slot. `decision` is "allow", "allow_always", or "deny". Returns
    True if a pending permission-wait was actually resolved."""
    with _pending_lock:
        event = _pending_permissions.get(slot)
        if event is None:
            return False
        _pending_decisions[slot] = decision
        event.set()
        return True


def has_pending_permission(slot: int) -> bool:
    with _pending_lock:
        return slot in _pending_permissions
