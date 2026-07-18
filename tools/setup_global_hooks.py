#!/usr/bin/env python3
"""One-time global setup: merges hooks/claude-settings.snippet.json into
~/.claude/settings.json (global — applies across every repo/session, per
CLAUDE.md §10), with two substitutions the static template can't do on its own:

1. Injects the real anti-spoofing token (daemon/auth.py) as env.AGENTDECK_TOKEN,
   so the PermissionRequest http hook's header substitution has something to
   read. The token is per-machine, so it can't be hardcoded into the
   repo-tracked template.
2. Rewrites the command hooks' "${CLAUDE_PROJECT_DIR}/hooks/post_event.sh" to
   an absolute path to *this* repo's post_event.sh. ${CLAUDE_PROJECT_DIR}
   resolves to whatever repo is currently open when a global hook fires — not
   necessarily this one — so the relative form would silently break for every
   repo except AgentDeck itself.

Merges rather than overwrites: existing hooks for other event names are kept,
and this tool's hook entries are appended to (not replacing) any existing
entries for the same event name. The existing file is backed up first.

Usage:
    python3 tools/setup_global_hooks.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daemon.auth import get_or_create_token  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SNIPPET_PATH = REPO_ROOT / "hooks" / "claude-settings.snippet.json"
GLOBAL_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
POST_EVENT_SH = REPO_ROOT / "hooks" / "post_event.sh"


def _resolve_project_dir_placeholder(snippet: dict) -> dict:
    """Deep-copies `snippet`, rewriting any "${CLAUDE_PROJECT_DIR}/hooks/post_event.sh"
    command string to this repo's absolute path."""
    resolved = copy.deepcopy(snippet)
    placeholder = "${CLAUDE_PROJECT_DIR}/hooks/post_event.sh"
    absolute = str(POST_EVENT_SH)

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "command" and value == placeholder:
                    node[key] = absolute
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(resolved)
    return resolved


def _merge_hooks(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for event_name, incoming_groups in incoming.items():
        existing_groups = merged.get(event_name, [])
        merged[event_name] = existing_groups + [g for g in incoming_groups if g not in existing_groups]
    return merged


def main() -> None:
    snippet = json.loads(SNIPPET_PATH.read_text())
    snippet = _resolve_project_dir_placeholder(snippet)
    token = get_or_create_token()

    existing: dict = {}
    if GLOBAL_SETTINGS_PATH.exists():
        existing = json.loads(GLOBAL_SETTINGS_PATH.read_text())
        backup_path = GLOBAL_SETTINGS_PATH.with_suffix(f".json.bak-{int(time.time())}")
        shutil.copy2(GLOBAL_SETTINGS_PATH, backup_path)
        print(f"Backed up existing {GLOBAL_SETTINGS_PATH} -> {backup_path}")

    merged = dict(existing)
    env = dict(merged.get("env", {}))
    env["AGENTDECK_TOKEN"] = token
    merged["env"] = env
    merged["hooks"] = _merge_hooks(merged.get("hooks", {}), snippet["hooks"])

    GLOBAL_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLOBAL_SETTINGS_PATH.write_text(json.dumps(merged, indent=2) + "\n")

    print(f"Wrote {GLOBAL_SETTINGS_PATH}")
    print(f"  env.AGENTDECK_TOKEN set")
    print(f"  hooks: {', '.join(snippet['hooks'].keys())}")
    print(f"  post_event.sh resolved to: {POST_EVENT_SH}")
    print("\nNo per-repo setup needed — sessions in any repo will now be picked up")
    print("automatically (blinking free pads to claim on first use), or pre-pin one")
    print("with tools/assign_slot.py.")


if __name__ == "__main__":
    main()
