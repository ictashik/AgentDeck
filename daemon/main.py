"""Entry point. Starts the HTTP server and MIDI I/O on background threads and
runs the rumps menu bar app on the main thread (rumps needs the Cocoa run loop
there).
"""

from __future__ import annotations

import threading

import uvicorn

from daemon import http_api, midi_io
from daemon.auth import get_or_create_token
from daemon.config import HTTP_HOST, HTTP_PORT, SLOT_COUNT
from daemon.menubar import AgentDeckApp
from daemon.state import SessionStore


def _run_http_server(store: SessionStore) -> None:
    http_api.store = store
    config = uvicorn.Config(http_api.app, host=HTTP_HOST, port=HTTP_PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    get_or_create_token()  # ensure ~/.agentdeck/token exists before hooks fire

    store = SessionStore(slot_count=SLOT_COUNT)

    http_thread = threading.Thread(target=_run_http_server, args=(store,), daemon=True)
    http_thread.start()

    midi_io.run_in_background(store)
    store.set_loading(False)  # stop the all-pads loading blink

    app = AgentDeckApp(store)
    app.run()


if __name__ == "__main__":
    main()
