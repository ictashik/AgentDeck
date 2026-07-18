"""rumps.App subclass: 8 menu items (one per slot) + Accept/Reject, per
CLAUDE.md §12. Runs on the main thread; polls the shared SessionStore on a
rumps.Timer since MIDI/HTTP threads mutate it independently.
"""

from __future__ import annotations

import rumps

from daemon import http_api
from daemon.state import SessionState, SessionStore

STATE_EMOJI = {
    "idle": "⚪️",
    "thinking": "🔵",
    "running_tool": "🟣",
    "waiting_permission": "🔴",
    "waiting_input": "🟡",
    "done": "🟢",
    "error": "🟠",
}

REFRESH_INTERVAL_SECONDS = 1.0
BLINK_INTERVAL_SECONDS = 0.6


def _slot_title(session: SessionState) -> str:
    emoji = STATE_EMOJI.get(session.state, "⚪️")
    label = session.cwd.rsplit("/", 1)[-1] if session.cwd else (session.agent or "unassigned")
    return f"{emoji} Slot {session.slot} — {label} ({session.state})"


class AgentDeckApp(rumps.App):
    def __init__(self, store: SessionStore) -> None:
        super().__init__("AgentDeck", title="◌")
        self.store = store
        self._blink_on = True

        self.slot_items = [rumps.MenuItem(f"Slot {i}", callback=self._make_focus_handler(i))
                            for i in range(1, len(store.all()) + 1)]
        self.accept_item = rumps.MenuItem("Accept", callback=self._on_accept)
        self.reject_item = rumps.MenuItem("Reject", callback=self._on_reject)

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
                    title=f"Session {slot}",
                    subtitle=session.state,
                    message=session.detail or session.cwd or "",
                )
            self._refresh()

        return handler

    def _on_accept(self, _sender: rumps.MenuItem) -> None:
        self._resolve_focused("allow")

    def _on_reject(self, _sender: rumps.MenuItem) -> None:
        self._resolve_focused("deny")

    def _resolve_focused(self, decision: str) -> None:
        slot = self.store.get_focus()
        if slot is None:
            return
        http_api.resolve_permission(slot, decision)
        self.store.update(slot, state="thinking")
        self._refresh()

    def _refresh(self, _timer: rumps.Timer | None = None) -> None:
        for item, session in zip(self.slot_items, self.store.all()):
            if session.is_blinking() and not self._blink_on:
                item.title = f"⚫️ Slot {session.slot} — waiting on you"
            else:
                item.title = _slot_title(session)

        self.title = "🔴" if self.store.any_waiting_permission() and self._blink_on else "◌"

    def _blink(self, _timer: rumps.Timer) -> None:
        self._blink_on = not self._blink_on
        self._refresh()
