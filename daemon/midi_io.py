"""MIDI I/O thread: translates raw MIDI from the MPK Mini Mk4 into actions, and
pushes pad LED colors reflecting session state. Opens the **DAW Port**
specifically for both input and output — transport CCs and pad LED control
only work on that port (live-verified, see research/NOTES.md), not the plain
MIDI Port.

No TTY, no tmux, no keystroke injection — this only ever calls into
daemon.http_api (resolve a pending permission), daemon.actions (raise a VS
Code window), and daemon.state (focus/read session state).
"""

from __future__ import annotations

import threading
import time

import mido
import rumps

from daemon import actions, http_api
from daemon.config import (
    CC_ENCODER_PRESS,
    CC_ENCODER_TURN,
    CC_LOOP,
    CC_PLAY_STOP,
    CC_RECORD,
    CC_SHIFT_PAD_BASE,
    ENCODER_CCW_VALUE,
    ENCODER_CW_VALUE,
    PAD_CHANNEL,
    PAD_DEBOUNCE_SECONDS,
    PAD_LED_PORT_HINT,
    PAD_NOTES,
    SLOT_COUNT,
)
from daemon.protocol.pad_colors import message_for_state
from daemon.state import SessionStore

POLL_INTERVAL_SECONDS = 0.02


def _find_daw_port_name(names: list[str]) -> str | None:
    return next((n for n in names if PAD_LED_PORT_HINT in n), None)


class MidiIO:
    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self._stop = threading.Event()
        self._last_pad_fire: dict[int, float] = {}
        self._last_sent_state: dict[int, str] = {}

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        in_name = _find_daw_port_name(mido.get_input_names())
        out_name = _find_daw_port_name(mido.get_output_names())
        if in_name is None or out_name is None:
            print(f"MidiIO: no '{PAD_LED_PORT_HINT}' port found — device not connected? Skipping MIDI I/O.")
            return

        with mido.open_input(in_name) as inport, mido.open_output(out_name) as outport:
            self._outport = outport
            while not self._stop.is_set():
                for msg in inport.iter_pending():
                    self._handle_message(msg)
                self._refresh_pad_colors()
                time.sleep(POLL_INTERVAL_SECONDS)

    def _handle_message(self, msg: mido.Message) -> None:
        if msg.type == "note_on" and msg.channel == PAD_CHANNEL and msg.velocity > 0:
            self._handle_pad_press(msg.note)
        elif msg.type == "control_change" and msg.control == CC_ENCODER_TURN:
            self._handle_encoder_turn(msg.value)
        elif msg.type == "control_change" and CC_SHIFT_PAD_BASE <= msg.control < CC_SHIFT_PAD_BASE + SLOT_COUNT:
            if msg.value > 0:
                self._handle_shift_pad_press(msg.control - CC_SHIFT_PAD_BASE + 1)
        elif msg.type == "control_change" and msg.value > 0:
            self._handle_cc_press(msg.control)

    def _handle_shift_pad_press(self, slot: int) -> None:
        # Live-verified: holding Shift suppresses the pad's normal Note On
        # entirely and the device sends this dedicated CC instead (see
        # daemon.config.CC_SHIFT_PAD_BASE) — there is no separate "Shift held"
        # flag to check, the CC arriving on its own means Shift+Pad happened.
        now = time.monotonic()
        last = self._last_pad_fire.get(slot, 0.0)
        if now - last < PAD_DEBOUNCE_SECONDS:
            return
        self._last_pad_fire[slot] = now
        actions.raise_window(slot)

    def _handle_pad_press(self, note: int) -> None:
        if note not in PAD_NOTES:
            return
        slot = PAD_NOTES.index(note) + 1

        now = time.monotonic()
        last = self._last_pad_fire.get(slot, 0.0)
        if now - last < PAD_DEBOUNCE_SECONDS:
            return
        self._last_pad_fire[slot] = now

        self.store.set_focus(slot)
        session = self.store.get(slot)
        if session is not None:
            label = session.cwd.rsplit("/", 1)[-1] if session.cwd else f"slot {slot}"
            command = session.detail or session.state
            rumps.notification(
                title=f"AgentDeck — {label}",
                subtitle=session.state,
                message=f"{command} — allow?" if session.state == "waiting_permission" else command,
            )

    def _handle_cc_press(self, control: int) -> None:
        focused = self.store.get_focus()

        if control == CC_PLAY_STOP:
            if focused is not None:
                http_api.resolve_permission(focused, "allow")
        elif control == CC_LOOP:
            if focused is not None:
                http_api.resolve_permission(focused, "allow_always")
        elif control == CC_RECORD:
            if focused is not None:
                http_api.resolve_permission(focused, "deny")
        elif control == CC_ENCODER_PRESS:
            self._expand_focused()
        # else: unmapped in the MVP (Undo, Tap Tempo, Bank -/+, knobs) — ignored.

    def _handle_encoder_turn(self, value: int) -> None:
        focused = self.store.get_focus() or 1
        if value == ENCODER_CW_VALUE:
            next_slot = focused % SLOT_COUNT + 1
        elif value == ENCODER_CCW_VALUE:
            next_slot = (focused - 2) % SLOT_COUNT + 1
        else:
            return
        self.store.set_focus(next_slot)

    def _expand_focused(self) -> None:
        focused = self.store.get_focus()
        if focused is None:
            return
        session = self.store.get(focused)
        if session is None:
            return
        # rumps doesn't expose a way to programmatically open the menu bar
        # dropdown (documented stretch goal in CLAUDE.md §12) — an alert with
        # full detail is the pragmatic MVP stand-in.
        rumps.notification(
            title=f"Slot {focused} detail",
            subtitle=session.state,
            message=f"{session.cwd or ''}\n{session.detail or ''}".strip(),
        )

    def _refresh_pad_colors(self) -> None:
        for session in self.store.all():
            if session.state == self._last_sent_state.get(session.slot):
                continue
            note = PAD_NOTES[session.slot - 1]
            msg = message_for_state(note, session.state)
            self._outport.send(
                mido.Message("note_on", channel=msg.status - 0x90, note=msg.note, velocity=msg.velocity)
            )
            self._last_sent_state[session.slot] = session.state


def run_in_background(store: SessionStore) -> MidiIO:
    controller = MidiIO(store)
    thread = threading.Thread(target=controller.run, daemon=True)
    thread.start()
    return controller
