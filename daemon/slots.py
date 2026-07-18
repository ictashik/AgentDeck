"""~/.agentdeck/slots.json is the source of truth for slot -> repo binding.
AGENTDECK_SLOT (env var, set per-repo — see hooks/claude-settings.snippet.json)
still tags each hook event so the daemon knows which slot fired; this module
answers "given a slot, what repo/label does it belong to" for window-raising
and menu bar display.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TypedDict

SLOTS_PATH = Path.home() / ".agentdeck" / "slots.json"

_lock = threading.Lock()


class SlotBinding(TypedDict):
    repo: str
    label: str


def load() -> dict[str, SlotBinding]:
    with _lock:
        if not SLOTS_PATH.exists():
            return {}
        return json.loads(SLOTS_PATH.read_text())


def save(bindings: dict[str, SlotBinding]) -> None:
    with _lock:
        SLOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SLOTS_PATH.write_text(json.dumps(bindings, indent=2))


def assign(slot: int, repo: str, label: str | None = None) -> None:
    bindings = load()
    bindings[str(slot)] = {"repo": repo, "label": label or Path(repo).name}
    save(bindings)


def get(slot: int) -> SlotBinding | None:
    return load().get(str(slot))
