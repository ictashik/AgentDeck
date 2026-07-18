#!/usr/bin/env python3
"""Self-service MIDI mapping tool. Runs a local web page (127.0.0.1 only) where
you press physical controls on the device and see exactly what MIDI message
comes through, live — no back-and-forth needed. Label each captured message,
then save the whole mapping to a JSON file for daemon/config.py.

Usage:
    python3 tools/mapping_ui.py
    # then open http://127.0.0.1:8766 in a browser

Every message from every input port is streamed to the page (polling, no
external JS deps) so you can freely press pads, transport buttons, the
encoder, or knobs and see raw messages appear in real time, independent of
whatever labels you've defined.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import mido
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

HOST = "127.0.0.1"
PORT = 8766
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "research" / "live_mapping.json"

app = FastAPI(title="AgentDeck MIDI mapping tool")

_lock = threading.Lock()
_messages: list[dict] = []
_next_id = 0


def _midi_listener() -> None:
    global _next_id
    names = mido.get_input_names()
    ports = [mido.open_input(n) for n in names]
    try:
        while True:
            for port, name in zip(ports, names):
                for msg in port.iter_pending():
                    is_press = (
                        (msg.type == "note_on" and msg.velocity > 0)
                        or (msg.type == "control_change" and msg.value > 0)
                        or msg.type in ("pitchwheel", "polytouch", "aftertouch")
                    )
                    with _lock:
                        entry = {
                            "id": _next_id,
                            "t": time.time(),
                            "port": name,
                            "raw": str(msg),
                            "type": msg.type,
                            "is_press": is_press,
                            "note": getattr(msg, "note", None),
                            "control": getattr(msg, "control", None),
                            "channel": getattr(msg, "channel", None),
                            "value": getattr(msg, "value", getattr(msg, "velocity", None)),
                        }
                        _next_id += 1
                        _messages.append(entry)
                        if len(_messages) > 500:
                            del _messages[: len(_messages) - 500]
            time.sleep(0.01)
    finally:
        for port in ports:
            port.close()


@app.get("/messages")
def get_messages(since: int = 0) -> JSONResponse:
    with _lock:
        new = [m for m in _messages if m["id"] > since]
    return JSONResponse(new)


class SavePayload(BaseModel):
    mapping: dict


@app.post("/save")
def save_mapping(payload: SavePayload) -> dict:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload.mapping, indent=2))
    return {"ok": True, "path": str(OUTPUT_PATH)}


PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AgentDeck MIDI Mapping</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
  h1 { font-size: 1.3rem; }
  .row { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid #333; }
  .row .label { flex: 0 0 220px; }
  .row .result { flex: 1; font-family: monospace; color: #8f8; min-height: 1.2em; }
  .row button { padding: 0.3rem 0.8rem; }
  .row.armed .result { color: #ff8; }
  .row.captured { opacity: 0.85; }
  #log { font-family: monospace; font-size: 0.85em; height: 200px; overflow-y: auto; background: #111; color: #ddd; padding: 0.5rem; margin-top: 1rem; white-space: pre-wrap; }
  #save { margin-top: 1rem; padding: 0.6rem 1.2rem; font-size: 1rem; }
  #saveStatus { margin-left: 1rem; }
</style>
</head>
<body>
<h1>AgentDeck MIDI Mapping</h1>
<p>Click "Learn" on a row, then press the physical control. It auto-captures the
first press-type message that arrives after you click. Press "Redo" to try again.
Raw stream of everything received is at the bottom regardless of learn state.</p>
<div id="rows"></div>
<button id="save">Save mapping</button><span id="saveStatus"></span>
<div id="log"></div>
<script>
const CONTROLS = [
  "Pad 1", "Pad 2", "Pad 3", "Pad 4", "Pad 5", "Pad 6", "Pad 7", "Pad 8",
  "Play/Stop", "Record", "Loop", "Fast Forward", "Undo",
  "Tap Tempo", "Shift", "Bank -", "Bank +",
  "Encoder turn CW", "Encoder turn CCW", "Encoder press",
];

let lastId = 0;
let armedRow = null;
let armedSince = 0;
const captured = {};

function makeRows() {
  const container = document.getElementById("rows");
  CONTROLS.forEach((name, i) => {
    const row = document.createElement("div");
    row.className = "row";
    row.id = "row-" + i;
    row.innerHTML = `
      <div class="label">${name}</div>
      <button onclick="arm(${i})">Learn</button>
      <div class="result" id="result-${i}">not captured</div>
    `;
    container.appendChild(row);
  });
}

function arm(i) {
  armedRow = i;
  armedSince = Date.now() / 1000;
  document.querySelectorAll(".row").forEach(r => r.classList.remove("armed"));
  document.getElementById("row-" + i).classList.add("armed");
  document.getElementById("result-" + i).textContent = "waiting for press...";
}

function poll() {
  fetch(`/messages?since=${lastId}`).then(r => r.json()).then(msgs => {
    const log = document.getElementById("log");
    msgs.forEach(m => {
      lastId = Math.max(lastId, m.id);
      log.textContent += `[${m.port}] ${m.raw}\\n`;
      if (armedRow !== null && m.is_press && m.t >= armedSince) {
        captured[CONTROLS[armedRow]] = m;
        const el = document.getElementById("result-" + armedRow);
        el.textContent = m.raw + "  (" + m.port + ")";
        document.getElementById("row-" + armedRow).classList.add("captured");
        document.getElementById("row-" + armedRow).classList.remove("armed");
        armedRow = null;
      }
    });
    log.scrollTop = log.scrollHeight;
  }).finally(() => setTimeout(poll, 150));
}

document.getElementById("save").onclick = () => {
  fetch("/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({mapping: captured}),
  }).then(r => r.json()).then(res => {
    document.getElementById("saveStatus").textContent = "Saved to " + res.path;
  });
};

makeRows();
poll();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


def main() -> None:
    listener = threading.Thread(target=_midi_listener, daemon=True)
    listener.start()
    print(f"Open http://{HOST}:{PORT} in a browser.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
