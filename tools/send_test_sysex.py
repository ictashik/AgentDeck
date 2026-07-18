#!/usr/bin/env python3
"""Scratch pad for protocol experiments — sends one MIDI message to a chosen
output port and exits. Use this to test daemon/protocol/pad_colors.py's
hypotheses against the real MPK Mini Mk4 (see research/NOTES.md's
"Recommended next verification step" before running this against real hardware).

Usage:
    # Send a pad-color Note On guess:
    python3 tools/send_test_sysex.py --port 0 --note 48 --velocity 5 --channel-offset 0

    # Send raw SysEx bytes (space-separated hex, without F0/F7 — added automatically):
    python3 tools/send_test_sysex.py --port 0 --sysex "47 00 5D 66 00 01 01"
"""

from __future__ import annotations

import argparse
import sys

import mido


def pick_port(names: list[str], preselected: int | None) -> str:
    if not names:
        print("No MIDI output ports found. Is the MPK Mini Mk4 connected?", file=sys.stderr)
        sys.exit(1)
    if preselected is not None:
        if not (0 <= preselected < len(names)):
            print(f"--port {preselected} out of range (0..{len(names) - 1})", file=sys.stderr)
            sys.exit(1)
        return names[preselected]

    print("Available MIDI output ports:")
    for i, name in enumerate(names):
        print(f"  [{i}] {name}")
    choice = input("Pick a port index: ").strip()
    return pick_port(names, int(choice))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=None, help="output port index, skips the picker")

    note_group = parser.add_argument_group("Note On message (pad color test)")
    note_group.add_argument("--note", type=int, help="MIDI note number")
    note_group.add_argument("--velocity", type=int, help="velocity / color value")
    note_group.add_argument("--channel-offset", type=int, default=0, help="added to base channel 0")

    parser.add_argument("--sysex", type=str, default=None,
                         help="space-separated hex bytes, F0/F7 added automatically")

    args = parser.parse_args()

    names = mido.get_output_names()
    port_name = pick_port(names, args.port)

    with mido.open_output(port_name) as port:
        if args.sysex is not None:
            data = [int(b, 16) for b in args.sysex.split()]
            msg = mido.Message("sysex", data=data)
            print(f"Sending SysEx: {msg}")
            port.send(msg)
        elif args.note is not None and args.velocity is not None:
            msg = mido.Message("note_on", channel=args.channel_offset, note=args.note, velocity=args.velocity)
            print(f"Sending Note On: {msg}")
            port.send(msg)
        else:
            parser.error("provide either --sysex, or both --note and --velocity")


if __name__ == "__main__":
    main()
