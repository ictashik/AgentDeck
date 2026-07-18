#!/usr/bin/env python3
"""MIDI-learn helper: waits for exactly one "press" message (Note On with
velocity>0, or CC with value>0) across all input ports, prints it, and exits.

One invocation per control avoids the timing races of a fixed-duration
capture window — the caller announces which physical control to press *before*
starting this, then this blocks until it actually sees something.

Usage:
    python3 tools/midi_learn.py "Play/Stop" [--timeout 30]
"""

from __future__ import annotations

import argparse
import sys
import time

import mido


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", help="human label for what's being learned, shown in the prompt")
    parser.add_argument("--timeout", type=float, default=30, help="seconds to wait before giving up")
    args = parser.parse_args()

    names = mido.get_input_names()
    if not names:
        print("No MIDI input ports found. Is the device connected?", file=sys.stderr)
        sys.exit(1)

    ports = [mido.open_input(n) for n in names]
    print(f"Press: {args.label}  (waiting up to {args.timeout:.0f}s)")

    end = time.time() + args.timeout
    try:
        while time.time() < end:
            for port, name in zip(ports, names):
                for msg in port.iter_pending():
                    is_press = (
                        (msg.type == "note_on" and msg.velocity > 0)
                        or (msg.type == "control_change" and msg.value > 0)
                    )
                    if is_press:
                        print(f"CAPTURED  port={name}  {msg}")
                        return
            time.sleep(0.01)
        print("TIMEOUT — no press message received.", file=sys.stderr)
        sys.exit(2)
    finally:
        for port in ports:
            port.close()


if __name__ == "__main__":
    main()
