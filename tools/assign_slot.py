#!/usr/bin/env python3
"""Assign a slot number to a repo. Two things happen:

1. Writes ~/.agentdeck/slots.json, the source of truth daemon/actions.py reads
   to know which repo to raise a window for.
2. Writes/merges <repo>/.claude/settings.local.json's "env" block with
   AGENTDECK_SLOT and AGENTDECK_TOKEN — since the VS Code extension has no
   shell to `export` from, this is how each repo's Claude Code session picks
   up its slot number and the anti-spoofing token (see daemon/auth.py) that
   the PermissionRequest http hook's headers reference. The global hooks in
   hooks/claude-settings.snippet.json (-> ~/.claude/settings.json) read these
   via $AGENTDECK_SLOT / $AGENTDECK_TOKEN.

Run this once per repo you plan to work in.

Usage:
    python3 tools/assign_slot.py 3 /Users/you/repos/bfit-pipeline
    python3 tools/assign_slot.py 3 /Users/you/repos/bfit-pipeline --label bfit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daemon import slots  # noqa: E402
from daemon.auth import get_or_create_token  # noqa: E402


def _write_settings_local_env(repo_path: Path, slot: int, token: str) -> Path:
    settings_path = repo_path / ".claude" / "settings.local.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    env = data.setdefault("env", {})
    env["AGENTDECK_SLOT"] = str(slot)
    env["AGENTDECK_TOKEN"] = token
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    return settings_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slot", type=int, help="slot number 1-8")
    parser.add_argument("repo", help="absolute path to the repo")
    parser.add_argument("--label", help="short display label, defaults to the repo dir name")
    args = parser.parse_args()

    repo_path = Path(args.repo).expanduser().resolve()
    if not repo_path.is_dir():
        print(f"Not a directory: {repo_path}", file=sys.stderr)
        sys.exit(1)

    slots.assign(args.slot, str(repo_path), args.label)
    token = get_or_create_token()
    settings_path = _write_settings_local_env(repo_path, args.slot, token)

    print(f"Slot {args.slot} -> {repo_path} (label: {args.label or repo_path.name})")
    print(f"  {slots.SLOTS_PATH}")
    print(f"  {settings_path} (env.AGENTDECK_SLOT, env.AGENTDECK_TOKEN)")
    print(
        "\nMake sure hooks/claude-settings.snippet.json's contents are merged into "
        "~/.claude/settings.json (global) — see README."
    )


if __name__ == "__main__":
    main()
