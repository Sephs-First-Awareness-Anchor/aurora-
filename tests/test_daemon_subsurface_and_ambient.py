# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression tests for two local-daemon bugs found running Aurora on real
Linux hardware (2026-07-12):

1. Subsurface reaching out to the user directly. `run()` set
   systems["_auto_reach_out_enabled"] = True unconditionally at boot, with
   no check for runtime_profile -- unlike the sensory/voice-listener gating
   a few lines below it (surface_owned_sensory), which does check. A
   subsurface-profile boot (aurora_subsurface_daemon.py ->
   aurora_daemon.main(runtime_profile="subsurface")) therefore also enabled
   reach-out, and _reach_out_to_user() calls _speak()/_notify()/
   _save_message() -- genuinely user-facing output from a process that is
   supposed to stay entirely internal.

2. Responding to ambient audio. _classify_ambient() treated every
   overheard utterance as 'direct' address unless it was clearly
   third-person about her (she/her). A real, already-built direct-address
   classifier (_AURORA_DIRECT_RE -- name mention, second-person address, a
   question, a conversational opener) sat unused right above it. A TV, a
   podcast, or someone else's conversation in the room would trigger a real
   spoken response.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_daemon


def test_auto_reach_out_disabled_for_subsurface_profile():
    assert aurora_daemon._compute_auto_reach_out_enabled(
        {"runtime_profile": "subsurface"}
    ) is False


def test_auto_reach_out_enabled_for_full_profile():
    assert aurora_daemon._compute_auto_reach_out_enabled(
        {"runtime_profile": "full"}
    ) is True


def test_auto_reach_out_enabled_for_surface_profile():
    assert aurora_daemon._compute_auto_reach_out_enabled(
        {"runtime_profile": "surface"}
    ) is True


def test_auto_reach_out_disabled_when_profile_missing():
    """No runtime_profile key at all must default to the conservative side
    (disabled), matching the exact same default-to-subsurface convention
    the pre-existing surface_owned_sensory check already uses a few lines
    below this one in run()."""
    assert aurora_daemon._compute_auto_reach_out_enabled({}) is False


def test_ambient_third_person_mention_is_not_direct():
    role = aurora_daemon._classify_ambient("tell her I'll call back later")
    assert role == "mention"


def test_ambient_real_direct_address_is_direct():
    role = aurora_daemon._classify_ambient("Aurora, what do you think about this?")
    assert role == "direct"


def test_ambient_question_is_direct():
    role = aurora_daemon._classify_ambient("do you know what time it is?")
    assert role == "direct"


def test_ambient_background_speech_is_not_direct():
    """The exact real-world case: a TV, a podcast, someone else's phone
    call in the room -- speech with no evidence of address to her at all
    must not trigger a spoken response."""
    cases = [
        "the quarterly earnings report exceeded analyst expectations",
        "and now back to our regularly scheduled programming",
        "I can't believe traffic was that bad this morning",
        "the recipe calls for two cups of flour and a pinch of salt",
    ]
    for text in cases:
        assert aurora_daemon._classify_ambient(text) == "ambient", (
            f"{text!r} should be classified ambient, not direct"
        )
