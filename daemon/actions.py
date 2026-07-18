"""Side-effecting actions the MIDI/HTTP threads trigger: window-raising for
Tier 2 (CLAUDE.md's "Expand"/Shift+pad step), and writing a conservative
allow-rule for Tier 1's "Loop = allow always" button. No TTY, no tmux, no
keystroke injection — the VS Code extension is the only supported client, so
"raise the window" means "bring VS Code to front on this repo."
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from daemon import slots
from daemon.config import VSCODE_CLI_COMMAND


def raise_window(slot: int) -> bool:
    """Brings the VS Code window for `slot`'s repo to front. Returns True if
    an attempt was made (repo bound + a raise mechanism ran), not necessarily
    that the window actually came forward — no reliable way to confirm that
    from outside the app."""
    binding = slots.get(slot)
    if binding is None:
        return False

    repo = binding["repo"]

    if shutil.which(VSCODE_CLI_COMMAND):
        result = subprocess.run([VSCODE_CLI_COMMAND, "-r", repo], capture_output=True, timeout=10)
        if result.returncode == 0:
            return True

    # Fallback: activate the Code app via AppleScript. Doesn't target the
    # specific repo window if multiple are open, just brings *a* VS Code
    # window forward — better than nothing if `code` CLI isn't on PATH.
    subprocess.run(
        ["osascript", "-e", 'tell application "Visual Studio Code" to activate'],
        capture_output=True,
        timeout=10,
    )
    return True


def build_allow_rule(tool_name: str, tool_input: dict) -> str:
    """Builds a conservative permission-rule string for settings.json's
    permissions.allow list (see code.claude.com/docs/en/permissions for the
    `Tool(pattern)` syntax). Deliberately simple, not clever:
    - Bash/PowerShell: first-token prefix match, e.g. "Bash(npm *)"
    - tools with a file_path (Edit/Write/Read): exact match on that path
    - anything else: bare tool name (broadest option, last resort)
    """
    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        first_token = command.strip().split()[0]
        return f"{tool_name}({first_token} *)"

    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        return f"{tool_name}({file_path})"

    return tool_name


def add_allow_rule(slot: int, rule: str) -> bool:
    """Appends `rule` to <repo>/.claude/settings.json's permissions.allow list,
    creating the file/keys as needed. No-op (returns False) if the rule is
    already present or the slot has no bound repo."""
    binding = slots.get(slot)
    if binding is None:
        return False

    settings_path = Path(binding["repo"]) / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    permissions = data.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])

    if rule in allow:
        return False

    allow.append(rule)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    return True
