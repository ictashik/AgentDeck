"""rumps.App subclass: 8 menu items (one per slot) + Accept/Reject, per
CLAUDE.md §12. Runs on the main thread; polls the shared SessionStore on a
rumps.Timer since MIDI/HTTP threads mutate it independently.
"""

from __future__ import annotations

from functools import partial

import rumps

from daemon import http_api, slots
from daemon.state import SessionState, SessionStore

STATE_EMOJI = {
    "idle": "⚪️",
    "thinking": "🔵",
    "running_tool": "🟣",
    "waiting_permission": "🔴",
    "waiting_question": "🟣",
    "waiting_input": "🟡",
    "done": "🟢",
    "error": "🟠",
}

REFRESH_INTERVAL_SECONDS = 1.0
BLINK_INTERVAL_SECONDS = 0.6


def _label_for(session: SessionState) -> str:
    binding = slots.get(session.slot)
    if binding is not None:
        return binding["label"]
    if session.cwd:
        return session.cwd.rsplit("/", 1)[-1]
    return f"slot {session.slot}"


def _slot_title(session: SessionState) -> str:
    emoji = STATE_EMOJI.get(session.state, "⚪️")
    label = _label_for(session)
    detail = f" — {session.detail}" if session.detail else ""
    return f"{emoji} {label} ({session.state}){detail}"


def _notification_message(session: SessionState) -> str:
    label = _label_for(session)
    command = session.detail or session.state
    if session.state == "waiting_permission":
        return f"{label} · {command} — allow?"
    return f"{label} · {command}"


class AgentDeckApp(rumps.App):
    def __init__(self, store: SessionStore) -> None:
        super().__init__("AgentDeck", title="◌")
        self.store = store
        self._blink_on = True

        self.slot_items: list[rumps.MenuItem] = []
        for i in range(1, len(store.all()) + 1):
            item = rumps.MenuItem(f"Slot {i}", callback=self._make_focus_handler(i))
            item.add(rumps.MenuItem("Allow", callback=partial(self._resolve_slot, i, "allow")))
            item.add(rumps.MenuItem("Allow Always", callback=partial(self._resolve_slot, i, "allow_always")))
            item.add(rumps.MenuItem("Deny", callback=partial(self._resolve_slot, i, "deny")))
            self.slot_items.append(item)

        self.accept_item = rumps.MenuItem("Accept (focused)", callback=lambda _: self._resolve_focused("allow"))
        self.reject_item = rumps.MenuItem("Reject (focused)", callback=lambda _: self._resolve_focused("deny"))

        self.menu = [*self.slot_items, None, self.accept_item, self.reject_item]

        self._refresh_timer = rumps.Timer(self._refresh, REFRESH_INTERVAL_SECONDS)
        self._refresh_timer.start()
        self._blink_timer = rumps.Timer(self._blink, BLINK_INTERVAL_SECONDS)
        self._blink_timer.start()

    def _make_focus_handler(self, slot: int):
        def handler(_sender: rumps.MenuItem) -> None:
            self.store.set_focus(slot)
            session = self.store.get(slot)
            if session is not None:
                rumps.notification(
                    title=f"AgentDeck — slot {slot}",
                    subtitle=session.state,
                    message=_notification_message(session),
                )
            self._refresh()

        return handler

    def _resolve_slot(self, slot: int, decision: str, _sender: rumps.MenuItem) -> None:
        http_api.resolve_permission(slot, decision)
        self._refresh()

    def _resolve_focused(self, decision: str) -> None:
        slot = self.store.get_focus()
        if slot is None:
            return
        self._resolve_slot(slot, decision, None)

    def _refresh(self, _timer: rumps.Timer | None = None) -> None:
        for item, session in zip(self.slot_items, self.store.all()):
            if session.is_blinking() and not self._blink_on:
                item.title = f"⚫️ {_label_for(session)} — waiting on you"
            else:
                item.title = _slot_title(session)

        self.title = "🔴" if self.store.any_blinking() and self._blink_on else "◌"

    def _blink(self, _timer: rumps.Timer) -> None:
        self._blink_on = not self._blink_on
        self._refresh()
