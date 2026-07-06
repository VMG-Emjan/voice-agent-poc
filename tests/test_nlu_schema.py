"""Intent/slot parsing + schema validation (invalid JSON, low confidence)."""

from __future__ import annotations

from datetime import datetime

from voice_agent.intents import parse
from voice_agent.schemas import Intent, NLUResult

NOW = datetime(2026, 7, 6, 10, 0, 0)


def test_parse_full_booking_sentence():
    r = parse("I want to book an appointment, my name is John Smith, on 2026-07-12 at 15:00", NOW)
    assert r.intent is Intent.BOOK_APPOINTMENT
    assert r.slots["name"] == "John Smith"
    assert r.slots["date"] == "2026-07-12"
    assert r.slots["time"] == "15:00"
    assert r.trusted


def test_parse_routing_department():
    r = parse("transfer me to billing please", NOW)
    assert r.intent is Intent.ROUTE_CALL
    assert r.slots["department"] == "billing"


def test_parse_cancel():
    assert parse("actually cancel that", NOW).intent is Intent.CANCEL


def test_parse_turkish_department_synonym():
    r = parse("beni satış birimine bağla", NOW)
    assert r.intent is Intent.ROUTE_CALL
    assert r.slots["department"] == "sales"


def test_invalid_llm_json_falls_back_safely():
    r = NLUResult.from_json("this is not json {oops")
    assert r.intent is Intent.UNKNOWN
    assert r.confidence == 0.0
    assert not r.trusted


def test_low_confidence_not_trusted():
    r = NLUResult(intent=Intent.BOOK_APPOINTMENT, confidence=0.1)
    assert not r.trusted


def test_unknown_intent_from_gibberish():
    r = parse("asdf qwer zxcv", NOW)
    assert r.intent is Intent.UNKNOWN
    assert not r.trusted


def test_schema_drops_unknown_slot_keys():
    payload = '{"intent":"faq","slots":{"date":"2026-07-12","evil":"x"},"confidence":0.9}'
    r = NLUResult.from_json(payload)
    assert "evil" not in r.slots
    assert set(r.slots) == {"date", "time", "name", "department"}
