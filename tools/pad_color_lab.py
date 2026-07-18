#!/usr/bin/env python3
"""Self-service pad LED color test bench. Runs a local web page (127.0.0.1
only) with buttons that send a single Note On to a chosen pad on a chosen
"channel offset" — testing the hypothesis from research/NOTES.md that pad LED
color/brightness/blink mode is set via a plain Note On (no SysEx), where the
MIDI channel selects brightness/blink and velocity selects color.

There's no way to read an LED's state back over MIDI, so this can't
self-verify like tools/mapping_ui.py did — you still have to look at the pad
and report what you see. But it removes the chat-relay timing problem: every
button click sends instantly, no round-trip capture window to race against.

Usage:
    python3 tools/pad_color_lab.py
    # then open http://127.0.0.1:8767 in a browser
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import mido
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from daemon.config import PAD_NOTES
from daemon.protocol.pad_colors import (
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_GREEN,
    COLOR_GREY,
    COLOR_OFF,
    COLOR_RED,
    COLOR_WHITE,
    NOTE_ON_STATUS,
)

HOST = "127.0.0.1"
PORT = 8767
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "research" / "pad_color_findings.json"

app = FastAPI(title="AgentDeck pad color lab")

_lock = threading.Lock()
_open_ports: dict[str, mido.ports.BaseOutput] = {}
_log: list[str] = []


@app.get("/ports")
def get_ports() -> list[str]:
    return mido.get_output_names()


def _get_port(name: str) -> mido.ports.BaseOutput:
    with _lock:
        if name not in _open_ports:
            _open_ports[name] = mido.open_output(name)
        return _open_ports[name]


class SendPayload(BaseModel):
    note: int
    channel: int
    velocity: int
    port: str
    raw_sysex: str | None = None  # optional: space-separated hex, F0/F7 added automatically


@app.post("/send")
def send(payload: SendPayload) -> dict:
    port = _get_port(payload.port)
    if payload.raw_sysex:
        data = [int(b, 16) for b in payload.raw_sysex.split()]
        msg = mido.Message("sysex", data=data)
    else:
        msg = mido.Message(
            "note_on",
            channel=payload.channel,
            note=payload.note,
            velocity=payload.velocity,
        )
    port.send(msg)
    with _lock:
        status_note = f" (status=0x{NOTE_ON_STATUS + payload.channel:02x})" if msg.type == "note_on" else ""
        _log.append(f"[{payload.port}] sent {msg}{status_note}")
    return {"ok": True, "port": payload.port}


@app.get("/log")
def get_log(since: int = 0) -> JSONResponse:
    with _lock:
        return JSONResponse(_log[since:])


class SavePayload(BaseModel):
    findings: dict


@app.post("/save")
def save(payload: SavePayload) -> dict:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload.findings, indent=2))
    return {"ok": True, "path": str(OUTPUT_PATH)}


COLORS = {
    "OFF (0)": COLOR_OFF,
    "GREY (1)": COLOR_GREY,
    "WHITE (3)": COLOR_WHITE,
    "RED (5)": COLOR_RED,
    "AMBER (9)": COLOR_AMBER,
    "GREEN (21)": COLOR_GREEN,
    "BLUE (45)": COLOR_BLUE,
}

PAGE = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AgentDeck Pad Color Lab</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.3rem; }}
  .controls {{ display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #444; padding: 0.4rem; text-align: center; }}
  th {{ background: #222; }}
  button.fire {{ padding: 0.3rem 0.6rem; cursor: pointer; }}
  input.note {{ width: 100%; box-sizing: border-box; }}
  #log {{ font-family: monospace; font-size: 0.8em; height: 160px; overflow-y: auto; background: #111; color: #ddd; padding: 0.5rem; margin-top: 1rem; white-space: pre-wrap; }}
  #save {{ margin-top: 1rem; padding: 0.6rem 1.2rem; font-size: 1rem; }}
</style>
</head>
<body>
<h1>AgentDeck Pad Color Lab</h1>
<p>Pick a pad note, then click any (channel, color) cell to fire a single Note
On instantly. Watch the physical pad. Type what you observe into that cell's
box (e.g. "steady red", "off", "blinking amber"), then Save when done sweeping.</p>
<div class="controls">
  <label>Output port: <select id="port"></select></label>
  <label>Pad note: <input id="note" type="number" value="{PAD_NOTES[0]}" style="width:5rem"></label>
  <button class="fire" onclick="allOff()">All channels off (this note)</button>
</div>
<div class="controls">
  <label>Raw SysEx (hex, no F0/F7): <input id="sysex" style="width:20rem" placeholder="e.g. 47 00 5D 25"></label>
  <button class="fire" onclick="fireSysex()">Send SysEx</button>
</div>
<table id="grid"></table>
<button id="save">Save findings</button><span id="saveStatus"></span>
<div id="log"></div>
<script>
const COLORS = {json.dumps(COLORS)};
const CHANNELS = Array.from({{length: 16}}, (_, i) => i);
const findings = {{}};

function noteVal() {{ return parseInt(document.getElementById("note").value, 10); }}
function portVal() {{ return document.getElementById("port").value; }}

function loadPorts() {{
  fetch("/ports").then(r => r.json()).then(ports => {{
    const sel = document.getElementById("port");
    sel.innerHTML = ports.map(p => `<option value="${{p}}">${{p}}</option>`).join("");
    const midiPort = ports.find(p => p.includes("MIDI") && !p.includes("DAW") && !p.includes("Plugin"));
    if (midiPort) sel.value = midiPort;
  }});
}}

function fire(channel, velocity) {{
  fetch("/send", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{note: noteVal(), channel, velocity, port: portVal()}}),
  }});
}}

function fireSysex() {{
  fetch("/send", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{note: 0, channel: 0, velocity: 0, port: portVal(), raw_sysex: document.getElementById("sysex").value}}),
  }});
}}

function allOff() {{
  CHANNELS.forEach(ch => fire(ch, 0));
}}

function buildGrid() {{
  const table = document.getElementById("grid");
  const header = document.createElement("tr");
  header.innerHTML = "<th>Channel</th>" + Object.keys(COLORS).map(c => `<th>${{c}}</th>`).join("");
  table.appendChild(header);

  CHANNELS.forEach(ch => {{
    const row = document.createElement("tr");
    let cells = `<td><b>${{ch}}</b> <button class="fire" onclick="fire(${{ch}}, 0)">off</button></td>`;
    Object.entries(COLORS).forEach(([name, vel]) => {{
      const id = `note-${{ch}}-${{vel}}`;
      cells += `<td>
        <button class="fire" onclick="fire(${{ch}}, ${{vel}}); document.getElementById('${{id}}').focus()">fire</button>
        <input class="note" id="${{id}}" placeholder="observed..."
          oninput="findings['ch'+${{ch}}+'_'+'${{name}}'] = {{channel: ${{ch}}, color_name: '${{name}}', velocity: ${{vel}}, observed: this.value}}">
      </td>`;
    }});
    row.innerHTML = cells;
    table.appendChild(row);
  }});
}}

let lastLog = 0;
function pollLog() {{
  fetch(`/log?since=${{lastLog}}`).then(r => r.json()).then(lines => {{
    const log = document.getElementById("log");
    lines.forEach(l => {{ log.textContent += l + "\\n"; lastLog++; }});
    log.scrollTop = log.scrollHeight;
  }}).finally(() => setTimeout(pollLog, 300));
}}

document.getElementById("save").onclick = () => {{
  fetch("/save", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{findings}}),
  }}).then(r => r.json()).then(res => {{
    document.getElementById("saveStatus").textContent = "Saved to " + res.path;
  }});
}};

loadPorts();
buildGrid();
pollLog();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


def main() -> None:
    print(f"Open http://{HOST}:{PORT} in a browser.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
