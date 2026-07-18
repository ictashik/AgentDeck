"""~/.agentdeck/slots.json is the source of truth for slot -> repo binding.

Sessions identify themselves by `cwd` (present in every Claude Code hook
payload already — no per-repo env var needed). The daemon resolves cwd -> slot
via this file; when a cwd has no binding yet, daemon/pending_claim.py takes
over to prompt for one interactively (blink the free pads, claim on press).
`tools/assign_slot.py` remains for pre-pinning a repo to a specific slot
without going through that interactive flow.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TypedDict

from daemon.config import SLOT_COUNT

SLOTS_PATH = Path.home() / ".agentdeck" / "slots.json"

_lock = threading.Lock()


class SlotBinding(TypedDict):
    repo: str
    label: str
    app: str | None


def load() -> dict[str, SlotBinding]:
    with _lock:
        if not SLOTS_PATH.exists():
            return {}
        return json.loads(SLOTS_PATH.read_text())


def save(bindings: dict[str, SlotBinding]) -> None:
    with _lock:
        SLOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SLOTS_PATH.write_text(json.dumps(bindings, indent=2))


def assign(slot: int, repo: str, label: str | None = None, app: str | None = None) -> None:
    bindings = load()
    bindings[str(slot)] = {"repo": repo, "label": label or Path(repo).name, "app": app}
    save(bindings)


def get(slot: int) -> SlotBinding | None:
    return load().get(str(slot))


def unassign(slot: int) -> None:
    bindings = load()
    bindings.pop(str(slot), None)
    save(bindings)


def find_slot_for_cwd(cwd: str) -> int | None:
    for slot_str, binding in load().items():
        if binding["repo"] == cwd:
            return int(slot_str)
    return None


def free_slots() -> list[int]:
    bound = {int(s) for s in load()}
    return [slot for slot in range(1, SLOT_COUNT + 1) if slot not in bound]
