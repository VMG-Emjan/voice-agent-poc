"""Dialog state machine.

Drives booking + routing. The NLU provider only PROPOSES intent/slots; this class
decides which tool to call and never books before explicit confirmation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime

from .logging import EventLog
from .schemas import Intent, NLUResult
from .state import DialogState, Reply
from .tools import Tools

# Order in which missing booking slots are requested.
_BOOKING_SLOT_ORDER = ("name", "date", "time")

_YES_RE = re.compile(r"\b(yes|yeah|yep|correct|confirm|evet|onayl|tamam|olur|doğru|dogru)\b", re.I)
_NO_RE = re.compile(r"\b(no|nope|wrong|change|hayır|hayir|yanlış|yanlis|değiştir|degistir)\b", re.I)

NLUProvider = Callable[[str, datetime], NLUResult]


class DialogManager:
    def __init__(
        self,
        nlu: NLUProvider,
        tools: Tools,
        log: EventLog | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self.nlu = nlu
        self.tools = tools
        self.log = log or EventLog()
        self._now = now_provider or datetime.now
        self.state = DialogState.IDLE
        self.slots: dict[str, str | None] = {"date": None, "time": None, "name": None,
                                             "department": None}
        self.active_intent: Intent = Intent.UNKNOWN

    # -- public ---------------------------------------------------------------
    def handle(self, text: str) -> Reply:
        now = self._now()
        result = self.nlu(text, now)
        self.log.emit("nlu", input=text, result=result.to_dict())

        # Cancellation is honored from any state.
        if result.intent is Intent.CANCEL:
            return self._finish(DialogState.CANCELLED, "Okay, cancelled. Anything else?")

        if self.state == DialogState.AWAITING_CONFIRMATION:
            return self._on_confirmation(text, result)

        self._merge_slots(result)

        if self.active_intent is Intent.UNKNOWN:
            self.active_intent = result.intent

        if self.active_intent is Intent.ROUTE_CALL:
            return self._drive_routing()
        if self.active_intent is Intent.BOOK_APPOINTMENT:
            return self._drive_booking()
        if result.intent is Intent.FAQ:
            return Reply("We're open 09:00–18:00, Mon–Fri. How can I help — booking or a transfer?",
                         DialogState.IDLE)

        return Reply(
            "I can book an appointment or route your call to a department. Which would you like?",
            DialogState.IDLE,
        )

    # -- booking --------------------------------------------------------------
    def _drive_booking(self) -> Reply:
        missing = self._missing_booking_slot()
        if missing:
            self.state = DialogState.COLLECTING_SLOTS
            return Reply(self._ask_for(missing), self.state)

        date_iso, time_hhmm = self.slots["date"], self.slots["time"]
        avail = self.tools.check_availability(date_iso)
        self.log.emit("tool", name="check_availability", result=avail.data)
        self.state = DialogState.CHECKING_AVAILABILITY

        if time_hhmm not in avail.data["free"]:
            alts = self.tools.suggest_alternatives(date_iso, time_hhmm)
            self.slots["time"] = None  # force re-pick
            self.state = DialogState.COLLECTING_SLOTS
            if not alts:
                return Reply(f"Sorry, {date_iso} is fully booked. What other day?", self.state)
            return Reply(
                f"{time_hhmm} on {date_iso} isn't available. Nearest free: "
                f"{', '.join(alts)}. Which time works?",
                self.state,
            )

        self.state = DialogState.AWAITING_CONFIRMATION
        return Reply(
            f"Confirm: booking for {self.slots['name']} on {date_iso} at {time_hhmm}. "
            "Shall I book it? (yes/no)",
            self.state,
        )

    def _on_confirmation(self, text: str, result: NLUResult) -> Reply:
        # A correction (new date/time/name) overrides a plain yes/no.
        has_correction = any(result.slots.get(k) for k in ("date", "time", "name"))
        if has_correction and not _YES_RE.search(text):
            self._merge_slots(result, overwrite=True)
            return self._drive_booking()

        if _NO_RE.search(text) and not _YES_RE.search(text):
            self.state = DialogState.COLLECTING_SLOTS
            return Reply("No problem — what would you like to change (date, time, or name)?",
                         self.state)

        if _YES_RE.search(text):
            return self._commit_booking()

        return Reply("Please confirm with yes or no.", DialogState.AWAITING_CONFIRMATION)

    def _commit_booking(self) -> Reply:
        self.state = DialogState.BOOKING
        res = self.tools.book_slot(
            self.slots["name"], self.slots["date"], self.slots["time"], self.slots["department"]
        )
        self.log.emit("tool", name="book_slot", ok=res.ok, result=res.data)
        if not res.ok:
            return self._finish(DialogState.FAILED, f"Couldn't book: {res.message}")
        return self._finish(
            DialogState.BOOKED,
            f"Done. {self.slots['name']}, you're booked for "
            f"{self.slots['date']} at {self.slots['time']}.",
            data=res.data,
        )

    # -- routing --------------------------------------------------------------
    def _drive_routing(self) -> Reply:
        if not self.slots["department"]:
            self.state = DialogState.COLLECTING_SLOTS
            return Reply("Which department — sales, support, billing, or reception?", self.state)
        self.state = DialogState.ROUTING
        res = self.tools.route_call(self.slots["department"])
        self.log.emit("tool", name="route_call", ok=res.ok, result=res.data)
        if not res.ok:
            self.slots["department"] = None
            self.state = DialogState.COLLECTING_SLOTS
            return Reply(f"{res.message} Try sales, support, billing, or reception.", self.state)
        return self._finish(DialogState.ROUTED, res.message, data=res.data)

    # -- helpers --------------------------------------------------------------
    def _missing_booking_slot(self) -> str | None:
        for slot in _BOOKING_SLOT_ORDER:
            if not self.slots[slot]:
                return slot
        return None

    def _ask_for(self, slot: str) -> str:
        return {
            "name": "Sure — what name is the appointment under?",
            "date": "What day would you like? (e.g. tomorrow, or 2026-07-12)",
            "time": "What time works for you? (e.g. 14:30)",
        }[slot]

    def _merge_slots(self, result: NLUResult, overwrite: bool = False) -> None:
        for k, v in result.slots.items():
            if v and (overwrite or not self.slots.get(k)):
                self.slots[k] = v

    def _finish(self, state: DialogState, text: str, data: dict | None = None) -> Reply:
        self.state = state
        self.log.emit("state", state=state.value, slots=dict(self.slots))
        return Reply(text, state, done=True, data=data or {})
