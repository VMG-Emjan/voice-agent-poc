"""End-to-end dialog scenarios: booking, corrections, cancellation, routing.

All run against a tmp data dir + fixed clock (see conftest).
"""

from __future__ import annotations

from conftest import read_appointments
from voice_agent.state import DialogState

DATE = "2026-07-12"       # free afternoon slots per calendar.example.json
FREE_TIME = "15:00"
BLOCKED_TIME = "14:00"    # blocked on 2026-07-12 in the fixture


def drive(agent, turns):
    reply = None
    for t in turns:
        reply = agent.handle(t)
    return reply


def test_full_booking_single_sentence(agent, appointments_file):
    r = agent.handle(f"book an appointment, my name is John Smith, on {DATE} at {FREE_TIME}")
    assert r.state is DialogState.AWAITING_CONFIRMATION  # never books before confirm
    r = agent.handle("yes")
    assert r.state is DialogState.BOOKED
    booked = read_appointments(appointments_file)
    assert booked and booked[0]["datetime"] == f"{DATE}T{FREE_TIME}"
    assert booked[0]["name"] == "John Smith"


def test_asks_for_missing_date(agent):
    r = agent.handle(f"book an appointment, my name is Alice, at {FREE_TIME}")
    assert r.state is DialogState.COLLECTING_SLOTS
    assert "day" in r.text.lower()
    r = agent.handle(DATE)
    assert r.state is DialogState.AWAITING_CONFIRMATION


def test_asks_for_missing_time(agent):
    r = agent.handle(f"book an appointment, my name is Bob, on {DATE}")
    assert r.state is DialogState.COLLECTING_SLOTS
    assert "time" in r.text.lower()
    r = agent.handle(FREE_TIME)
    assert r.state is DialogState.AWAITING_CONFIRMATION


def test_asks_for_missing_name(agent):
    r = agent.handle(f"book an appointment on {DATE} at {FREE_TIME}")
    assert r.state is DialogState.COLLECTING_SLOTS
    assert "name" in r.text.lower()
    r = agent.handle("My name is Carol")
    assert r.state is DialogState.AWAITING_CONFIRMATION


def test_correction_before_confirmation(agent, appointments_file):
    agent.handle(f"book an appointment, my name is Dave, on {DATE} at {FREE_TIME}")
    r = agent.handle("actually make it 16:00")
    assert r.state is DialogState.AWAITING_CONFIRMATION
    agent.handle("yes")
    booked = read_appointments(appointments_file)
    assert booked[0]["datetime"] == f"{DATE}T16:00"


def test_cancel_before_confirmation(agent, appointments_file):
    agent.handle(f"book an appointment, my name is Eve, on {DATE} at {FREE_TIME}")
    r = agent.handle("cancel")
    assert r.state is DialogState.CANCELLED
    assert read_appointments(appointments_file) == []


def test_unavailable_slot_offers_alternatives(agent):
    r = agent.handle(f"book an appointment, my name is Frank, on {DATE} at {BLOCKED_TIME}")
    assert r.state is DialogState.COLLECTING_SLOTS
    assert "available" in r.text.lower()
    # An alternative time is suggested.
    assert any(alt in r.text for alt in ("13:30", "14:30", "15:00"))


def test_booking_writes_file(agent, appointments_file):
    assert not appointments_file.exists()
    agent.handle(f"book an appointment, my name is Grace, on {DATE} at {FREE_TIME}")
    agent.handle("yes")
    assert appointments_file.exists()
    assert read_appointments(appointments_file)[0]["name"] == "Grace"


def test_double_booking_prevented_in_dialog(agent, appointments_file):
    agent.handle(f"book an appointment, my name is Heidi, on {DATE} at {FREE_TIME}")
    agent.handle("yes")
    # Fresh conversation, same slot -> agent must NOT create a second record.
    agent2_first = agent.handle(f"book an appointment, my name is Ivan, on {DATE} at {FREE_TIME}")
    assert agent2_first.state is not DialogState.BOOKED
    assert len(read_appointments(appointments_file)) == 1


def test_route_known_department(agent):
    r = agent.handle("please connect me to support")
    assert r.state is DialogState.ROUTED
    assert r.data["department"] == "support"
    assert r.data["mode"] == "routing-decision-simulation"


def test_route_asks_when_department_missing(agent):
    r = agent.handle("I need to transfer my call")
    assert r.state is DialogState.COLLECTING_SLOTS
    r = agent.handle("billing")
    assert r.state is DialogState.ROUTED


def test_route_unknown_department(agent):
    r = agent.handle("transfer me to the astronaut department")
    # No known department parsed -> agent asks rather than routing wrongly.
    assert r.state is not DialogState.ROUTED


def test_turkish_booking_preserves_characters(agent, appointments_file):
    agent.handle(f"randevu almak istiyorum, adım Çağrı, {DATE} saat {FREE_TIME}")
    r = agent.handle("evet")
    assert r.state is DialogState.BOOKED
    assert read_appointments(appointments_file)[0]["name"] == "Çağrı"


def test_gibberish_gives_safe_fallback(agent):
    r = agent.handle("asdf qwer zxcv")
    assert r.state is DialogState.IDLE
    assert "book" in r.text.lower() or "route" in r.text.lower()
