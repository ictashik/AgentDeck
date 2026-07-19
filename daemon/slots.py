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
    """Matches `cwd` against a bound repo exactly, or against any repo that's
    an ancestor directory of it — a hook firing from a subfolder (e.g. a
    Bash tool `cd`ing into a repo's subdirectory mid-session, live-observed
    for both this repo's own `widget/` subfolder and an unrelated repo's
    nested folder) would otherwise look like an unrecognized new repo,
    triggering a spurious pending-claim prompt and a duplicate binding for
    what's really the same session. When multiple bindings match (e.g. a
    subfolder is *also* explicitly pinned via tools/assign_slot.py, on top
    of its parent repo being bound elsewhere), the most specific — longest
    matching repo path — wins."""
    best_slot: int | None = None
    best_len = -1
    for slot_str, binding in load().items():
        repo = binding["repo"].rstrip("/")
        if (cwd == repo or cwd.startswith(repo + "/")) and len(repo) > best_len:
            best_len = len(repo)
            best_slot = int(slot_str)
    return best_slot


def free_slots() -> list[int]:
    bound = {int(s) for s in load()}
    return [slot for slot in range(1, SLOT_COUNT + 1) if slot not in bound]
