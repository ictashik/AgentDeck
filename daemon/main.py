"""Entry point. Starts the HTTP server on a background thread and runs the
rumps menu bar app on the main thread (rumps needs the Cocoa run loop there).

MIDI I/O (daemon/midi_io.py) is Day 2 scope per CLAUDE.md §13 — not wired in
yet. Everything here works purely off hook-driven HTTP events for now.
"""

from __future__ import annotations

import threading

import uvicorn

from daemon import http_api
from daemon.config import HTTP_HOST, HTTP_PORT, SLOT_COUNT
from daemon.menubar import AgentDeckApp
from daemon.state import SessionStore


def _run_http_server(store: SessionStore) -> None:
    http_api.store = store
    config = uvicorn.Config(http_api.app, host=HTTP_HOST, port=HTTP_PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    store = SessionStore(slot_count=SLOT_COUNT)

    http_thread = threading.Thread(target=_run_http_server, args=(store,), daemon=True)
    http_thread.start()

    app = AgentDeckApp(store)
    app.run()


if __name__ == "__main__":
    main()
