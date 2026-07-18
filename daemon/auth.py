"""Local anti-spoofing token. Not real security (this is a localhost-only
personal tool per CLAUDE.md §2) — just enough that some other process on the
same machine can't casually POST fake events into the hub. Enabled by default,
toggle with AGENTDECK_AUTH_ENABLED=0.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

TOKEN_PATH = Path.home() / ".agentdeck" / "token"
AUTH_ENABLED = os.environ.get("AGENTDECK_AUTH_ENABLED", "1") != "0"


def get_or_create_token() -> str:
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(24)
    TOKEN_PATH.write_text(token)
    TOKEN_PATH.chmod(0o600)
    return token
