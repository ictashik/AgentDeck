#!/usr/bin/env python3
"""Pre-pin a repo to a specific slot, writing ~/.agentdeck/slots.json directly.

Not required for normal use — by default, the first Claude Code session in a
repo the daemon hasn't seen before triggers an interactive claim: all free
pads blink, press one to assign it (see daemon/pending_claim.py). Use this
tool only if you want to force a specific repo onto a specific pad ahead of
time, bypassing that interactive step.

One-time global setup (token + hooks merged into ~/.claude/settings.json) is
tools/setup_global_hooks.py, not this script.

Usage:
    python3 tools/assign_slot.py 3 /Users/you/repos/bfit-pipeline
    python3 tools/assign_slot.py 3 /Users/you/repos/bfit-pipeline --label bfit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daemon import slots  # noqa: E402


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
    print(f"Slot {args.slot} -> {repo_path} (label: {args.label or repo_path.name})")
    print(f"  {slots.SLOTS_PATH}")


if __name__ == "__main__":
    main()
