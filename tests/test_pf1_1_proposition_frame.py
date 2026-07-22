# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF1.1: PropositionFrame builder. Fail-quiet derivation ladder
(thought -> claim -> anchor -> None), no live wiring yet -- these are
pure unit tests over the ladder, matching the phase's own gate.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_proposition_frame import (  # noqa: E402
    build_frame, PropositionFrame,
)


class _FakeThoughtState:
    def __init__(self, unified_interpretation="", self_application="",
                 confidence=0.5, unresolved=None, skipped=False,
                 dominant_thread=None):
        self.unified_interpretation = unified_interpretation
        self.self_application = self_application
        self.confidence = confidence
        self.unresolved = unresolved or []
        self.skipped = skipped
        self.dominant_thread = dominant_thread or []


class _FakeProcessContext:
    def __init__(self, process_type, what_it_is_operating_on):
        self.process_type = process_type
        self.what_it_is_operating_on = what_it_is_operating_on


class _FakeSubstrate:
    def __init__(self, nodes):
        self.nodes = nodes

    def score_claim(self, node):
        return float(node.get("confidence", 0.0) or 0.0)


class _FakeWorkingMemory:
    def __init__(self, turn_count=0, proposition_substrate=None):
        self.turn_count = turn_count
        self.proposition_substrate = proposition_substrate


class _FakeState:
    def __init__(self, noncomp_input_state=None):
        self.noncomp_input_state = noncomp_input_state or {}


# ── Rung 1: thought ──────────────────────────────────────────────────

def test_frame_from_thought_state():
    thought = _FakeThoughtState(
        unified_interpretation="I need to help with the water project",
        self_application="",
        confidence=0.72,
        unresolved=["tension_a"],
    )
    systems = {"_current_thought_state": thought}
    state = _FakeState()
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.source == "thought"
    assert frame.subject == "need"
    assert frame.relation == "help"
    assert frame.obj == "water"
    assert frame.negated is False
    assert frame.stance == 0.72
    assert frame.unresolved == ["tension_a"]


def test_frame_from_thought_state_detects_negation():
    thought = _FakeThoughtState(unified_interpretation="I do not need the water project")
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is not None
    assert frame.source == "thought"
    assert frame.negated is True


def test_thought_state_skipped_falls_through():
    thought = _FakeThoughtState(unified_interpretation="I need to help with water", skipped=True)
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    # No claim/anchor available either -> falls all the way to None
    assert frame is None


def test_thought_state_with_no_text_falls_through():
    thought = _FakeThoughtState(unified_interpretation="", self_application="")
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is None


# ── W1 fix (PF1.6 residue characterization, 2026-07-21): the real     ──
# ── turn text lives in a "linguistic" ProcessContext in dominant_     ──
# ── thread, not in unified_interpretation/self_application, which are ──
# ── ALWAYS internal telemetry for any successful (non-skipped)        ──
# ── integration -- confirmed live, 0/60 probes ever reached this rung ──
# ── through the old text-only path.                                   ──

def test_frame_from_thought_state_reads_linguistic_context_when_present():
    thought = _FakeThoughtState(
        # Real shape: unified_interpretation is telemetry, never prose.
        unified_interpretation=(
            "Operating on: X=0.50 T=0.50; sedi_ambient | Active processes: "
            "constraint, memory, identity | Dominant pressure: X-axis (0.50)"
        ),
        self_application="This touches how I understand myself.",
        confidence=0.72,
        dominant_thread=[
            _FakeProcessContext("memory", "sedi_ambient"),
            _FakeProcessContext("identity", "identity_predicates"),
            _FakeProcessContext("linguistic", "I need to help with the water project"),
        ],
    )
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is not None
    assert frame.source == "thought"
    assert frame.subject == "need"
    assert frame.relation == "help"
    assert frame.obj == "water"
    assert frame.stance == 0.72


def test_frame_from_thought_state_telemetry_text_alone_no_longer_blocks_when_linguistic_context_absent():
    """Regression guard for the W1 finding itself: telemetry-shaped
    unified_interpretation with NO linguistic context anywhere in
    dominant_thread correctly falls through to None (via the fallback
    path, still gated by the telemetry guard) -- this is the exact
    real-world shape that produced 0/60 thought-rung fires before the
    fix, preserved here so a future regression can't silently reappear."""
    thought = _FakeThoughtState(
        unified_interpretation=(
            "Operating on: X=0.50 T=0.50 N=0.50 B=0.50 A=0.50; sedi_ambient; "
            "identity_predicates | Active processes: constraint, memory, "
            "identity, predictive | Triggered by: user_turn, continuous_braid | "
            "Unresolved tension: 4 conflict(s) between processes | Background: "
            "session pressure: 0.00 | Dominant pressure: X-axis (0.50)"
        ),
        self_application="This touches how I understand myself. My X-axis pressure (0.50) shapes this.",
        confidence=0.40,
        dominant_thread=[
            _FakeProcessContext("memory", "sedi_ambient"),
            _FakeProcessContext("identity", "identity_predicates"),
        ],
    )
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is None


def test_frame_from_thought_state_linguistic_context_with_unusable_text_falls_through():
    """The linguistic context's own text still goes through the normal
    topic-extraction path -- garbage/empty content there still yields
    no frame (fail-quiet all the way), not a forced pass."""
    thought = _FakeThoughtState(
        dominant_thread=[_FakeProcessContext("linguistic", "")],
    )
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is None


def test_frame_from_thought_state_excludes_contractions_from_relation_and_obj():
    """Live-fire finding: once real turn text started flowing through
    the linguistic context, contractions ("he's", "what's", "i'm")
    surfaced as spurious relation/obj candidates -- infer_word_role has
    no apostrophe-aware rule, so an unrecognized contraction defaults to
    "noun" and would otherwise bind straight into a content slot ("I am
    planning he's."). Confirmed live on the 60-probe battery; this is
    the regression guard."""
    thought = _FakeThoughtState(
        dominant_thread=[_FakeProcessContext(
            "linguistic", "He's a bit nervous around new people.")],
    )
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    if frame is not None:
        assert "'" not in frame.relation
        assert "'" not in frame.obj


# ── Real-shape regression: unified_interpretation is internal         ──
# ── telemetry (aurora_thought_formation._reason_through_dominant /    ──
# ── _partial_interpretation), never a sentence -- PF1.4's own         ──
# ── live-boot run caught this literally landing in delivered text     ──
# ── ("I triggered x=0.50.") because PF1.1's original fixtures were    ──
# ── all hand-written natural language, never the real generated shape.──

def test_pipe_joined_telemetry_thought_text_is_rejected():
    telemetry = (
        "Operating on: something | Active processes: memory, curiosity | "
        "Triggered by: warp_coverage_extension, x=0.50 | "
        "Dominant pressure: A-axis (0.62)"
    )
    thought = _FakeThoughtState(unified_interpretation=telemetry, confidence=0.7)
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is None


def test_partial_interpretation_prefix_is_rejected():
    thought = _FakeThoughtState(unified_interpretation="[partial] water; project", confidence=0.4)
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is None


def test_telemetry_thought_falls_through_to_claim_rung():
    telemetry = "Triggered by: warp_coverage_extension, x=0.50 | Dominant pressure: A-axis (0.62)"
    thought = _FakeThoughtState(unified_interpretation=telemetry, confidence=0.7)
    substrate = _FakeSubstrate({
        "n1": {"subject": "meeting", "relation": "is", "object": "thursday",
               "negated": False, "turn": 1, "confidence": 0.9},
    })
    wm = _FakeWorkingMemory(turn_count=1, proposition_substrate=substrate)
    systems = {"_current_thought_state": thought, "working_memory": wm}
    frame = build_frame(systems, _FakeState())
    assert frame is not None
    assert frame.source == "claim"


def test_stray_key_value_token_never_becomes_relation_or_object():
    """Defense-in-depth per-token guard, independent of the whole-text
    telemetry check -- no genuine spoken word ever contains '='."""
    thought = _FakeThoughtState(
        unified_interpretation="I need to help with activation=0.75 water",
        confidence=0.6,
    )
    systems = {"_current_thought_state": thought}
    frame = build_frame(systems, _FakeState())
    assert frame is not None
    assert "=" not in frame.relation
    assert "=" not in frame.obj


# ── Rung 2: claim ────────────────────────────────────────────────────

def test_frame_from_claims_when_no_thought_state():
    substrate = _FakeSubstrate({
        "n1": {"subject": "meeting", "relation": "is", "object": "tuesday",
               "negated": False, "turn": 3, "confidence": 0.4},
        "n2": {"subject": "meeting", "relation": "is", "object": "thursday",
               "negated": False, "turn": 3, "confidence": 0.9},
        "n3": {"subject": "other", "relation": "is", "object": "wrong_turn",
               "negated": False, "turn": 2, "confidence": 0.99},
    })
    wm = _FakeWorkingMemory(turn_count=3, proposition_substrate=substrate)
    systems = {"working_memory": wm}
    frame = build_frame(systems, _FakeState())
    assert frame is not None
    assert frame.source == "claim"
    # highest-scoring CURRENT-turn claim wins (n2, not n3 which is turn 2)
    assert frame.subject == "meeting"
    assert frame.obj == "thursday"
    assert frame.stance == 0.9


def test_frame_from_claims_no_current_turn_claims_falls_through():
    substrate = _FakeSubstrate({
        "n1": {"subject": "meeting", "relation": "is", "object": "tuesday",
               "negated": False, "turn": 1, "confidence": 0.9},
    })
    wm = _FakeWorkingMemory(turn_count=5, proposition_substrate=substrate)
    systems = {"working_memory": wm}
    frame = build_frame(systems, _FakeState())
    assert frame is None


def test_thought_takes_priority_over_claim():
    thought = _FakeThoughtState(unified_interpretation="I create beautiful things", confidence=0.6)
    substrate = _FakeSubstrate({
        "n1": {"subject": "should_not_win", "relation": "is", "object": "x",
               "negated": False, "turn": 1, "confidence": 0.99},
    })
    wm = _FakeWorkingMemory(turn_count=1, proposition_substrate=substrate)
    systems = {"_current_thought_state": thought, "working_memory": wm}
    frame = build_frame(systems, _FakeState())
    assert frame is not None
    assert frame.source == "thought"


# ── Rung 3: anchor ───────────────────────────────────────────────────

def test_frame_from_anchor_when_nothing_else_available():
    state = _FakeState(noncomp_input_state={"anchor": "guitar"})
    systems = {}
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.source == "anchor"
    assert frame.subject == "self"
    assert frame.obj == "guitar"
    assert frame.relation == ""


def test_claim_takes_priority_over_anchor():
    substrate = _FakeSubstrate({
        "n1": {"subject": "meeting", "relation": "is", "object": "tuesday",
               "negated": False, "turn": 1, "confidence": 0.5},
    })
    wm = _FakeWorkingMemory(turn_count=1, proposition_substrate=substrate)
    systems = {"working_memory": wm}
    state = _FakeState(noncomp_input_state={"anchor": "should_not_win"})
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.source == "claim"


# ── Rung 4: all absent ───────────────────────────────────────────────

def test_all_rungs_absent_returns_none():
    frame = build_frame({}, _FakeState())
    assert frame is None


def test_empty_anchor_string_falls_through_to_none():
    state = _FakeState(noncomp_input_state={"anchor": ""})
    frame = build_frame({}, state)
    assert frame is None


# ── Degrades gracefully on garbage ──────────────────────────────────

def test_build_frame_never_raises_on_malformed_systems():
    class _Explode:
        def __getattr__(self, item):
            raise RuntimeError("boom")

    frame = build_frame({"_current_thought_state": _Explode(), "working_memory": _Explode()}, _Explode())
    assert frame is None


def test_proposition_frame_dataclass_defaults():
    f = PropositionFrame()
    assert f.subject == ""
    assert f.negated is False
    assert f.stance == 0.5
    assert f.unresolved == []
    assert f.source == ""
