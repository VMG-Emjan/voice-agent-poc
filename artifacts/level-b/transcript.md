# Level-B transcript — synthetic-audio voice pipeline

- STT: faster-whisper:base
- TTS: piper (en_US-amy-medium.onnx)
- Input audio: SYNTHETIC (Piper). Not a human microphone.

**spoken>** I would like to book an appointment
**heard (STT)>** I would like to book an appointment.
**bot>** Sure — what name is the appointment under?

**spoken>** My name is John Smith
**heard (STT)>** My name is John Smith.
**bot>** What day would you like? (e.g. tomorrow, or 2026-07-12)

**spoken>** on 2026-07-12
**heard (STT)>** on 2026-07-12.
**bot>** What time works for you? (e.g. 14:30)

**spoken>** at 3 PM
**heard (STT)>** at 3 p.m.
**bot>** What time works for you? (e.g. 14:30)

**spoken>** yes
**heard (STT)>** Yes.
**bot>** What time works for you? (e.g. 14:30)

