"""Side-effecting actions the MIDI/HTTP threads trigger: window-raising for
Tier 2 (CLAUDE.md's "Expand"/Shift+pad step), and writing a conservative
allow-rule for Tier 1's "Loop = allow always" button. No TTY, no tmux, no
keystroke injection. "Raise the window" targets the specific VS Code window
for a repo (via System Events, by title basename) when several are open, and
falls back to a plain app-activate for non-VS-Code sessions or when the
specific-window match fails.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from daemon import slots
from daemon.config import (
    TERM_PROGRAM_APP_NAMES,
    VSCODE_CLI_COMMAND,
    VSCODE_CLI_FALLBACK_PATHS,
    VSCODE_PROCESS_NAME,
)


def _find_code_cli() -> str | None:
    found = shutil.which(VSCODE_CLI_COMMAND)
    if found:
        return found
    # shutil.which uses this process's PATH, which under launchd is just
    # "/usr/bin:/bin:/usr/sbin:/sbin" — it won't find /usr/local/bin/code.
    # See daemon.config.VSCODE_CLI_FALLBACK_PATHS.
    return next((p for p in VSCODE_CLI_FALLBACK_PATHS if Path(p).exists()), None)


def _escape_applescript_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _list_vscode_window_titles() -> list[str]:
    result = subprocess.run(
        ["osascript", "-e", f'tell application "System Events" to tell process "{VSCODE_PROCESS_NAME}" to get name of every window'],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return []
    # osascript joins a list with ", " — titles that happen to contain that
    # exact substring (rare) would split wrong; not worth guarding against
    # for a personal tool.
    return [t.strip() for t in result.stdout.split(",") if t.strip()]


def _matches_repo(title: str, basename: str) -> bool:
    """A VS Code window's OS-level title reflects whatever's currently
    focused *inside* the window, not just the repo — an editor tab uses
    em-dash segments ("file — repo — Visual Studio Code"), but the Claude
    Code side panel uses a plain hyphen ("<chat subject> - repo"), with no
    trailing app-name segment at all. Only the trailing segment identifies
    the repo reliably; a bare substring/`contains` match is what let an
    unrelated window (e.g. one whose chat subject happens to mention the
    repo name) get raised instead of the right one."""
    for sep in (" — ", " - "):
        if sep in title:
            segments = [s.strip() for s in title.split(sep)]
            segments = [s for s in segments if s and s != "Visual Studio Code"]
            if segments and segments[-1] == basename:
                return True
    return title.strip() == basename


def _raise_vscode_window(repo: str) -> None:
    # `code -r` is the mechanism that actually matters: it goes through VS
    # Code's own IPC, so it can switch macOS Spaces to reach the right
    # window — unlike System Events below, which (confirmed live) only ever
    # sees windows on the *current* Space. It was silently never running at
    # all under launchd until _find_code_cli()'s fallback paths were added
    # (see daemon.config.VSCODE_CLI_FALLBACK_PATHS) — shutil.which() alone
    # came up empty against launchd's minimal PATH, so every past "raise"
    # was actually just the blanket activate below: a no-op if VS Code was
    # already frontmost, or "bring forward whatever VS Code window was last
    # used" otherwise. That matched the exact symptom reported live.
    code_path = _find_code_cli()
    if code_path:
        subprocess.run([code_path, "-r", repo], capture_output=True, timeout=10)

    # `code -r` reveals the window but doesn't always bring it to the
    # foreground on macOS (confirmed live — it can return success with the
    # window still behind others). Try to target that specific window by
    # exact title match via System Events for the "still behind others, but
    # on the current Space" case (needs Accessibility permission on whatever
    # runs the daemon — same requirement window_sweep used to have); if that
    # doesn't find it (different Space, or no permission), `code -r` above
    # is still doing the real work of switching Space/window, so a plain
    # app-activate as a last nudge is enough rather than a hard requirement.
    basename = Path(repo).name
    title = next((t for t in _list_vscode_window_titles() if _matches_repo(t, basename)), None)

    if title is not None:
        escaped_title = _escape_applescript_string(title)
        script = f'''
        tell application "System Events"
            tell process "{VSCODE_PROCESS_NAME}"
                perform action "AXRaise" of (first window whose name is "{escaped_title}")
                set frontmost to true
            end tell
        end tell
        '''
        result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        if result.returncode == 0:
            return

    subprocess.run(
        ["osascript", "-e", 'tell application "Visual Studio Code" to activate'],
        capture_output=True,
        timeout=10,
    )


def raise_window(slot: int) -> bool:
    """Brings the app for `slot`'s repo to front — VS Code, targeting the
    specific window for this repo (see _raise_vscode_window), if the session
    was launched from the VS Code extension or its integrated terminal;
    otherwise whatever terminal app the hook detected via process ancestry
    (see hooks/post_event.sh's detect_app and
    daemon.config.TERM_PROGRAM_APP_NAMES) — brought to front as an app only,
    no equivalent of `code -r`'s window targeting exists for a plain
    terminal. Returns True if an attempt was made (repo bound + a raise
    mechanism ran), not necessarily that the window actually came forward —
    no reliable way to confirm that from outside the app."""
    binding = slots.get(slot)
    if binding is None:
        return False

    repo = binding["repo"]
    app = binding.get("app") or "vscode"

    if app == "vscode":
        _raise_vscode_window(repo)
        return True

    app_name = TERM_PROGRAM_APP_NAMES.get(app)
    if app_name is None:
        return False  # unrecognized non-vscode app: nothing safe to activate
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
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
