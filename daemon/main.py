"""Entry point. Headless as of the SwiftUI widget migration (widget/) — no
Cocoa run loop needed on the Python side anymore, so the HTTP hub runs
directly on the main thread, with MIDI I/O as the one background thread.
"""

from __future__ import annotations

import uvicorn

from daemon import http_api, midi_io
from daemon.auth import get_or_create_token
from daemon.config import HTTP_HOST, HTTP_PORT, SLOT_COUNT
from daemon.state import SessionStore


def main() -> None:
    get_or_create_token()  # ensure ~/.agentdeck/token exists before hooks fire

    store = SessionStore(slot_count=SLOT_COUNT)
    http_api.store = store

    midi_io.run_in_background(store)
    store.set_loading(False)  # stop the all-pads loading blink

    config = uvicorn.Config(http_api.app, host=HTTP_HOST, port=HTTP_PORT, log_level="warning")
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
