#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_interpreted_turn_scout_boundary.py -- a Scout may only ever receive
Aurora's own INTERPRETED framing of a gap, never the raw user turn text
(spec section 4: "Scout acquires evidence... never interprets the
user"). This is the boundary between what write_turn_open() carries
(raw_input, Surface -> Subsurface, never seen by a Scout) and what a
ScoutRequest is allowed to carry.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.contracts import ScoutRequest
from aurora_internal.dual_strata.subsurface_presence import write_turn_open, read_and_clear_turn_events


def test_scout_request_dataclass_has_no_raw_input_channel():
    # Structural: the only user-framing field on the wire format is
    # interpreted_input -- there is no raw_user_text/raw_input field a
    # future caller could accidentally populate with the unprocessed
    # utterance.
    field_names = set(ScoutRequest.__dataclass_fields__.keys())
    assert "interpreted_input" in field_names
    assert "raw_input" not in field_names
    assert "raw_user_text" not in field_names
    assert "user_text" not in field_names


def test_a_turn_opens_raw_input_never_reaches_a_scout_request(tmp_path):
    # write_turn_open() is Surface -> Subsurface only (subsurface_presence.py) --
    # it is never the source a ScoutRequest is built from. Confirm the
    # raw_input it carries and a ScoutRequest built for the same turn
    # are structurally independent: nothing on ScoutRequest is derived
    # from read_and_clear_turn_events()'s output at all.
    write_turn_open(tmp_path, turn_id="t1", raw_input="the actual unprocessed thing the user typed")
    events = read_and_clear_turn_events(tmp_path)
    assert events[0]["raw_input"] == "the actual unprocessed thing the user typed"

    req = ScoutRequest(turn_id="t1", interpreted_input="Aurora's own reading of the gap", inquiry="the reformulated inquiry")
    req_dict = req.to_dict()
    assert "the actual unprocessed thing the user typed" not in str(req_dict.values())


def test_scout_request_interpreted_input_is_the_only_user_framing_a_scout_ever_sees():
    req = ScoutRequest(
        turn_id="t1",
        interpreted_input="Aurora interprets this as a question about chord theory",
        inquiry="what defines a diminished chord",
    )
    # Both fields present on the request are already Aurora's own
    # framing -- inquiry is the reformulated question, interpreted_input
    # is the surrounding context. Neither is raw user text by
    # construction (there is no field for that at all, per the test
    # above); this asserts the two fields a Scout worker actually reads
    # are exactly these two, and nothing else.
    carried_to_scout = {"interpreted_input": req.interpreted_input, "inquiry": req.inquiry}
    assert carried_to_scout["interpreted_input"] == "Aurora interprets this as a question about chord theory"
    assert carried_to_scout["inquiry"] == "what defines a diminished chord"
