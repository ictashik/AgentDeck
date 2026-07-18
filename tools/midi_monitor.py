#!/usr/bin/env python3
"""Raw MIDI logger. Lists available ports, then prints every message received
on a chosen input port. Use this first to confirm the MPK Mini Mk4's actual
note numbers (pads) and CC numbers (transport/encoder) — don't trust numbers
from someone else's preset dump.

Usage:
    python3 tools/midi_monitor.py            # interactive port picker
    python3 tools/midi_monitor.py --port 0   # skip the picker
"""

from __future__ import annotations

import argparse
import sys

import mido


def pick_port(names: list[str], preselected: int | None) -> str:
    if not names:
        print("No MIDI input ports found. Is the MPK Mini Mk4 connected?", file=sys.stderr)
        sys.exit(1)

    if preselected is not None:
        if not (0 <= preselected < len(names)):
            print(f"--port {preselected} out of range (0..{len(names) - 1})", file=sys.stderr)
            sys.exit(1)
        return names[preselected]

    print("Available MIDI input ports:")
    for i, name in enumerate(names):
        print(f"  [{i}] {name}")

    choice = input("Pick a port index: ").strip()
    try:
        idx = int(choice)
    except ValueError:
        print("Not a number.", file=sys.stderr)
        sys.exit(1)
    return pick_port(names, idx)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=None, help="input port index, skips the picker")
    args = parser.parse_args()

    names = mido.get_input_names()
    port_name = pick_port(names, args.port)

    print(f"\nListening on: {port_name}")
    print("Press pads, turn knobs, hit transport buttons. Ctrl-C to quit.\n")

    with mido.open_input(port_name) as port:
        try:
            for msg in port:
                print(msg)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
