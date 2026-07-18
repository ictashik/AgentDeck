# Progress Board

Short log, one entry per commit.

- Scaffolded repo structure per §9 (daemon/, hooks/, opencode-plugin/, research/, tools/), venv + requirements.txt, README.
- Added `tools/midi_monitor.py` (port lister + raw MIDI logger), `daemon/config.py`, `daemon/state.py` (SessionState + thread-safe SessionStore), `daemon/http_api.py` (`POST /event`, `GET /state`, stubbed `/permission-wait`). Verified end-to-end with a live uvicorn server + curl.
- Added `hooks/post_event.sh` + `hooks/claude-settings.snippet.json` for Claude Code command hooks. Verified against current docs that hooks pass data via stdin JSON, not env vars like `$CLAUDE_TOOL_NAME` as CLAUDE.md's original sketch assumed — corrected accordingly. Tested the script end-to-end against a live hub.
- Added `daemon/menubar.py` (rumps app, 8 slot rows, Accept/Reject, blinking icon) and `daemon/main.py` (wires HTTP server thread + rumps main-thread loop). **Day 1 milestone reached**: ran the full daemon and drove it through a complete session lifecycle (idle → thinking → running_tool → done) via the real hook script — confirmed end-to-end with no crashes.
- Day 2 protocol research (§8): confirmed transport CC numbers and pad note numbers against two independent reverse-engineering sources (matches CLAUDE.md's original placeholders exactly). Found a strong but unverified lead that pad LED colors are set via plain Note On (no SysEx) — documented in `research/NOTES.md`, implemented in `daemon/protocol/pad_colors.py` with clear UNVERIFIED markers on the channel-offset constants. Screen text protocol stays unresolved (no source documents it) — downgraded to stretch goal per §8, stubbed in `daemon/protocol/screen.py`. Added `tools/send_test_sysex.py` for live verification once hardware testing resumes.
