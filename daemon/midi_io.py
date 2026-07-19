"""MIDI I/O thread: translates raw MIDI from the MPK Mini Mk4 into actions, and
pushes pad LED colors reflecting session state. Opens the **DAW Port**
specifically for both input and output — transport CCs and pad LED control
only work on that port (live-verified, see research/NOTES.md), not the plain
MIDI Port.

No TTY, no tmux, no keystroke injection, no notifications — this only ever
calls into daemon.http_api (resolve a pending permission), daemon.actions
(raise the session's app window), and daemon.state (focus/read session
state, including the midi_connected flag for the SwiftUI widget's connection
glyph). All UI — including the peek/notification-equivalent — lives in the
separate widget/ app now; this module is headless.
"""

from __future__ import annotations

import threading
import time

import mido

from daemon import actions, http_api, pending_claim, slots
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
    PAD_HOLD_TO_RAISE_SECONDS,
    PAD_LED_PORT_HINT,
    PAD_NOTES,
    SLOT_COUNT,
    UNBIND_ARM_SECONDS,
)
from daemon.protocol.pad_colors import message_for_available, message_for_empty, message_for_state
from daemon.state import SessionStore

POLL_INTERVAL_SECONDS = 0.02

# How often to re-check for the DAW Port while the MPK isn't connected (at
# startup, or after being unplugged mid-session).
RECONNECT_POLL_SECONDS = 1.5


def _find_daw_port_name(names: list[str]) -> str | None:
    return next((n for n in names if PAD_LED_PORT_HINT in n), None)


class MidiIO:
    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self._stop = threading.Event()
        self._last_pad_fire: dict[int, float] = {}
        self._last_sent_state: dict[int, str] = {}
        self._unbind_armed_until: float = 0.0
        self._hold_timers: dict[int, threading.Timer] = {}
        self._hold_timer_lock = threading.Lock()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        """Outer loop that keeps retrying until the DAW Port shows up, and
        keeps retrying again if it disappears (unplugged) mid-session —
        rather than the previous one-shot check at startup, which meant
        connecting the MPK *after* the daemon was already running silently
        did nothing (the MIDI thread had already given up and exited)."""
        already_waiting = False
        while not self._stop.is_set():
            in_name = _find_daw_port_name(mido.get_input_names())
            out_name = _find_daw_port_name(mido.get_output_names())
            if in_name is None or out_name is None:
                self.store.set_midi_connected(False)
                if not already_waiting:
                    print(f"MidiIO: no '{PAD_LED_PORT_HINT}' port found — waiting for the device to be connected...")
                    already_waiting = True
                self._stop.wait(RECONNECT_POLL_SECONDS)
                continue
            already_waiting = False

            try:
                with mido.open_input(in_name) as inport, mido.open_output(out_name) as outport:
                    self._outport = outport
                    self.store.set_midi_connected(True)
                    # Force every pad's color to be sent fresh on (re)connect
                    # rather than trusting dedup state from before — the
                    # device always comes up with its LEDs off/default, so
                    # the current session state has to be reapplied in full
                    # even though nothing about the sessions changed.
                    self._last_sent_state.clear()
                    print(f"MidiIO: connected to '{PAD_LED_PORT_HINT}'.")
                    last_presence_check = time.monotonic()
                    while not self._stop.is_set():
                        for msg in inport.iter_pending():
                            self._handle_message(msg)
                        self._refresh_pad_colors()

                        # CoreMIDI/rtmidi does *not* reliably raise on a
                        # hot-unplug — live-observed: send()/iter_pending()
                        # on an already-open port just go quiet, no
                        # exception — so presence has to be actively polled
                        # rather than waited for as an error. Once it's
                        # gone, break back out to the outer loop, which
                        # closes these stale port handles (the `with`
                        # exiting) and starts polling for the device to
                        # come back.
                        now = time.monotonic()
                        if now - last_presence_check >= RECONNECT_POLL_SECONDS:
                            last_presence_check = now
                            still_present = (
                                _find_daw_port_name(mido.get_input_names()) == in_name
                                and _find_daw_port_name(mido.get_output_names()) == out_name
                            )
                            if not still_present:
                                print(f"MidiIO: '{PAD_LED_PORT_HINT}' disappeared — device unplugged?")
                                break

                        time.sleep(POLL_INTERVAL_SECONDS)
            except Exception as exc:  # noqa: BLE001 - belt-and-suspenders: if some
                # backend/platform combination *does* raise on unplug, fall
                # back to reconnect-polling instead of silently killing the
                # MIDI thread for the rest of the daemon's life, same as the
                # active presence-poll above handles the common case where
                # nothing gets raised at all.
                if not self._stop.is_set():
                    print(f"MidiIO: lost connection to '{PAD_LED_PORT_HINT}' ({exc}) — will retry.")
            finally:
                self.store.set_midi_connected(False)

    def _handle_message(self, msg: mido.Message) -> None:
        if msg.type == "note_on" and msg.channel == PAD_CHANNEL and msg.velocity > 0:
            self._handle_pad_press(msg.note)
        elif msg.type == "note_off" and msg.channel == PAD_CHANNEL:
            self._handle_pad_release(msg.note)
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

        # Record+Pad unbinds a slot (no long-press timing needed — Record has
        # no release message to hold-detect on, see daemon/config.py). Any
        # pad press consumes the arm window, hit or not, so a stray press
        # after the window lapses can't retroactively unbind something later.
        armed = self._unbind_armed_until > 0.0 and now < self._unbind_armed_until
        self._unbind_armed_until = 0.0

        if slots.get(slot) is None:
            self._handle_claim_press(slot)
            return

        if armed:
            self._handle_unbind_press(slot)
            return

        self.store.set_focus(slot)
        self._arm_hold_timer(slot)

    def _arm_hold_timer(self, slot: int) -> None:
        """Schedules the hold-to-raise fire PAD_HOLD_TO_RAISE_SECONDS from
        now, live while the pad is still held — see that constant's
        docstring for why this fires during the hold rather than being
        measured at release. Runs on its own thread (threading.Timer), not
        the MIDI thread; raise_window() has no thread affinity requirement,
        same as it being called from the HTTP thread for the widget's
        /raise and /unbind."""
        with self._hold_timer_lock:
            self._cancel_hold_timer_locked(slot)
            timer = threading.Timer(PAD_HOLD_TO_RAISE_SECONDS, self._fire_hold_raise, args=(slot,))
            timer.daemon = True
            self._hold_timers[slot] = timer
            timer.start()

    def _fire_hold_raise(self, slot: int) -> None:
        with self._hold_timer_lock:
            self._hold_timers.pop(slot, None)
        actions.raise_window(slot)

    def _cancel_hold_timer_locked(self, slot: int) -> None:
        timer = self._hold_timers.pop(slot, None)
        if timer is not None:
            timer.cancel()

    def _handle_pad_release(self, note: int) -> None:
        """Cancels the pending hold-to-raise timer if the pad was released
        before it fired — a plain quick press only focuses, per
        _handle_pad_press, and shouldn't retroactively raise a second later
        just because it happened to be pressed once."""
        if note not in PAD_NOTES:
            return
        slot = PAD_NOTES.index(note) + 1
        with self._hold_timer_lock:
            self._cancel_hold_timer_locked(slot)

    def _handle_claim_press(self, slot: int) -> None:
        claimed_cwd = pending_claim.claim(slot)
        if claimed_cwd is None:
            return  # unbound pad pressed but nothing is actually pending — no-op
        self.store.set_focus(slot)

    def _handle_unbind_press(self, slot: int) -> None:
        actions.raise_window(slot)  # raise first — needs the binding, which unassign below removes
        slots.unassign(slot)
        self.store.reset(slot)

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
            self._unbind_armed_until = time.monotonic() + UNBIND_ARM_SECONDS
        elif control == CC_ENCODER_PRESS:
            self._handle_encoder_press()
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

    def _handle_encoder_press(self) -> None:
        # "Expand" is now a click gesture in the SwiftUI widget (widget/) —
        # MIDI has no way to open a window in another process. Repurposed:
        # raise the focused slot's app window, same as Shift+pad.
        focused = self.store.get_focus()
        if focused is not None:
            actions.raise_window(focused)

    def _refresh_pad_colors(self) -> None:
        if self.store.is_loading():
            # Dedup key is the note number (36-43), which never collides with
            # the per-slot keys (1-8) the main loop below uses — so once
            # loading flips off, that loop sends every pad's real color fresh
            # rather than thinking it's already been sent.
            for note in PAD_NOTES:
                if self._last_sent_state.get(note) == "loading":
                    continue
                msg = message_for_available(note)  # white fast-blink, "hold on"
                self._outport.send(
                    mido.Message("note_on", channel=msg.status - 0x90, note=msg.note, velocity=msg.velocity)
                )
                self._last_sent_state[note] = "loading"
            return

        pending_cwd = pending_claim.current_pending_cwd()
        claimable = set(slots.free_slots()) if pending_cwd is not None else set()
        bound_slots = {int(s) for s in slots.load()}

        for session in self.store.all():
            note = PAD_NOTES[session.slot - 1]
            if session.slot in claimable:
                key = "available"
                msg = message_for_available(note)
            elif session.slot not in bound_slots:
                # Unbound, and nothing's actively queued to claim it right
                # now — OFF, distinct from a bound-but-idle session (dim
                # white). See message_for_empty's docstring.
                key = "empty"
                msg = message_for_empty(note)
            else:
                key = session.state
                msg = message_for_state(note, session.state)

            if self._last_sent_state.get(session.slot) == key:
                continue
            self._outport.send(
                mido.Message("note_on", channel=msg.status - 0x90, note=msg.note, velocity=msg.velocity)
            )
            self._last_sent_state[session.slot] = key


def run_in_background(store: SessionStore) -> MidiIO:
    controller = MidiIO(store)
    thread = threading.Thread(target=controller.run, daemon=True)
    thread.start()
    return controller
