"""Dialog states and the reply value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DialogState(str, Enum):
    IDLE = "idle"
    COLLECTING_SLOTS = "collecting_slots"
    CHECKING_AVAILABILITY = "checking_availability"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    BOOKING = "booking"
    BOOKED = "booked"
    ROUTING = "routing"
    ROUTED = "routed"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL = {DialogState.BOOKED, DialogState.ROUTED, DialogState.CANCELLED, DialogState.FAILED}


@dataclass
class Reply:
    """One agent turn: what to say + resulting state + whether the dialog is done."""

    text: str
    state: DialogState
    done: bool = False
    data: dict = field(default_factory=dict)
