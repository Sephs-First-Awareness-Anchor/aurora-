"""FIX-A113: the confluence -- every system feeds what she says, her live
abilities decide how.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""

from types import SimpleNamespace

import pytest

from aurora_grammar_engine import GrammarEngine, SlotFiller, StructuralMotif, TokenRole
from aurora_internal import aurora_confluence as C
import aurora_voice_gate as VG

R = TokenRole


def _engine(tmp_path, shapes=None, promoted=()):
    eng = GrammarEngine(state_dir=str(tmp_path))
    eng._lineage._motifs.clear()
    shapes = shapes if shapes is not None else [
        (R.AGENT, R.ACTION, R.OBJECT),
        (R.AGENT, R.ACTION, R.DESCRIPTOR),
        (R.AGENT, R.ACTION, R.DETERMINER, R.OBJECT),
        (R.AGENT, R.ACTION, R.OBJECT, R.DESCRIPTOR),
    ]
    for seq in shapes:
        m = eng._lineage.get_or_create(seq)
        m.success_count = 6
        m.contexts_seen = {"a", "b", "c"}
        m.promoted = seq in promoted
    return eng


def _ability(aid, axis, *tags):
    return SimpleNamespace(id=aid, axis=axis, effect_tags=tuple(tags))


def _abilities(*specs):
    table = {a.id: a for a in specs}
    return SimpleNamespace(abilities=table), [a.id for a in specs]


class _Rel:
    def __init__(self, s, kind, t, strength=0.8):
        self.source_word, self.target_word, self.strength, self.confidence = s, t, strength, 1.0
        self.relation_type = SimpleNamespace(value=kind)


def _web(*rels, roles=None):
    nodes, by_source, relations = {}, {}, {}
    for i, r in enumerate(rels):
        relations[f"r{i}"] = r
        by_source.setdefault(r.source_word, set()).add(f"r{i}")
        for w in (r.source_word, r.target_word):
            nodes[w] = SimpleNamespace(role=(roles or {}).get(w, "noun"))
    return SimpleNamespace(nodes=nodes, _relations_by_source=by_source, relations=relations)


def _systems(engine, abilities, *, form, salient=(), web=None, tone="curious", time_ref=""):
    genealogy, ids = abilities
    return {
        "grammar_engine": engine,
        "genealogy": genealogy,
        "_last_active_ability_ids": ids,
        "oets": SimpleNamespace(web=web) if web is not None else None,
        "_last_pipeline_state": {
            "constraint_semantic_state": {"relational_form": dict(form)},
            "salient_concepts": list(salient),
            "surface_reactive_emotion": {"tone_bias": tone},
            "utterance_meta": {"time_ref": time_ref},
            "response_obligation": {"operation": "evaluate_proposition"},
        },
    }


RIG = {"subject": "you", "relation": "want", "obj": "to start with the rig test", "question": True,
       "alternatives": [{"subject": "battery layout"}]}
HEARD = "Do you want to start with the rig test or the battery layout tonight?"

SHEAR_A = ("operator_action:operator_on_a", "purpose_lane:meaning", "complexity_axes:3",
           "complexity_slots:4", "generation_role:SHEAR", "overall_grade:0.6")


# -- the HOW comes from her live abilities ----------------------------------------

def test_how_reads_complexity_role_operator_and_lane():
    abil = _abilities(_ability("X:ONE", "X", *SHEAR_A, "purpose_lane:distinction_branching"))
    how = C.ability_how({"genealogy": abil[0], "_last_active_ability_ids": abil[1]})
    assert how["clauses"] == 2 and how["slots"] == 4
    assert how["generation_role"] == "SHEAR"
    assert how["axis_order"][0] == "A"          # operator_on_a leads
    assert how["axis_order"][1] == "B"          # distinction lane + SHEAR lean
    assert how["abilities"] == ["X:ONE"]


def test_primary_role_keeps_one_clause():
    abil = _abilities(_ability("A:P", "A", "operator_action:operator_on_a", "complexity_axes:3",
                               "generation_role:PRIMARY"))
    how = C.ability_how({"genealogy": abil[0], "_last_active_ability_ids": abil[1]})
    assert how["clauses"] == 1 and how["connector"] == ""


def test_no_live_abilities_means_no_preference():
    how = C.ability_how({"genealogy": SimpleNamespace(abilities={}), "_last_active_ability_ids": ["gone"]})
    assert how["abilities"] == [] and how["clauses"] == 1


# -- the WHAT comes from her systems, the HOW shapes it ---------------------------

def test_agency_then_affect(tmp_path):
    abil = _abilities(_ability("N:A", "N", "operator_action:operator_on_a", "operator_action:operator_on_n",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:ADJACENT"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG), HEARD)
    assert text == "I want to start with the rig test, and I am curious."
    assert [c["system"] for c in rec["clauses"]] == ["communication", "affect"]


def test_existence_operator_voices_her_knowledge_instead(tmp_path):
    web = _web(_Rel("rig", "has_a", "inverter"))
    abil = _abilities(_ability("X:G", "X", "operator_action:operator_on_a", "operator_action:operator_on_x",
                               "purpose_lane:admissibility_grounding", "complexity_axes:3",
                               "complexity_slots:4", "generation_role:BRIDGE"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, salient=["rig", "test"], web=web), HEARD)
    assert text == "I want to start with the rig test, so rig has a inverter."
    assert rec["clauses"][1]["system"] == "knowledge"


def test_distinction_chooses_the_option_she_knows_more_about(tmp_path):
    web = _web(_Rel("battery", "part_of", "rig"), _Rel("layout", "related_to", "wiring", 0.9))
    abil = _abilities(_ability("B:D", "B", "operator_action:operator_on_b", "operator_action:operator_on_a",
                               "purpose_lane:distinction_branching", "complexity_axes:3",
                               "complexity_slots:4", "generation_role:SHEAR"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, web=web), HEARD)
    # "battery part_of rig" is not new to the speaker (they said "rig");
    # "layout related_to wiring" is hers -- so the layout is what she knows more about.
    assert text.startswith("I want the battery layout")
    assert rec["clauses"][0]["role_sequence"] == ["agent", "action", "determiner", "object"]


def test_contrast_she_knows_joins_with_but(tmp_path):
    web = _web(_Rel("test", "opposite_of", "guess"))
    abil = _abilities(_ability("B:S", "B", "operator_action:operator_on_a", "operator_action:operator_on_b",
                               "complexity_axes:3", "complexity_slots:3", "generation_role:SHEAR"))
    form = dict(RIG, alternatives=[])
    text, _ = C.compose(_systems(_engine(tmp_path), abil, form=form, salient=["test"], web=web), HEARD)
    assert text == "I want to start with the rig, but test is opposite of guess."   # 3 slots: shorter object


def test_slots_from_abilities_limit_which_motifs_may_carry_a_clause(tmp_path):
    eng = _engine(tmp_path, shapes=[(R.AGENT, R.ACTION, R.OBJECT, R.DESCRIPTOR), (R.AGENT, R.ACTION, R.DESCRIPTOR)])
    wide = _abilities(_ability("A:W", "A", "operator_action:operator_on_a", "operator_action:operator_on_t",
                               "operator_action:operator_on_n",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:ADJACENT"))
    narrow = _abilities(_ability("A:N", "A", "operator_action:operator_on_a", "operator_action:operator_on_t",
                                 "operator_action:operator_on_n",
                                 "complexity_axes:3", "complexity_slots:3", "generation_role:ADJACENT"))
    text, _ = C.compose(_systems(eng, wide, form=RIG, time_ref="tonight"), HEARD)
    assert text == "I want to start with the rig test tonight, and I am curious."
    text, rec = C.compose(_systems(eng, narrow, form=RIG, time_ref="tonight"), HEARD)
    # 3 slots: no four-role shape may carry the stance; only her affect clause fits
    assert [c["system"] for c in rec["clauses"]] == ["affect"]


def test_promoted_motifs_come_first(tmp_path):
    eng = _engine(tmp_path, promoted=[(R.AGENT, R.ACTION, R.OBJECT, R.DESCRIPTOR)])
    abil = _abilities(_ability("A:T", "A", "operator_action:operator_on_a", "operator_action:operator_on_t",
                               "complexity_axes:2", "complexity_slots:4", "generation_role:PRIMARY"))
    _, rec = C.compose(_systems(eng, abil, form=RIG, time_ref="tonight"), HEARD)
    assert rec["clauses"][0]["promoted"] is True
    assert rec["clauses"][0]["role_sequence"] == ["agent", "action", "object", "descriptor"]
    assert rec["why"] == "echo"           # all of it was the speaker's own words: silence


def test_echo_alone_is_silence(tmp_path):
    abil = _abilities(_ability("A:P", "A", "operator_action:operator_on_a", "complexity_axes:2",
                               "complexity_slots:4", "generation_role:PRIMARY"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, tone=""), HEARD)
    assert text == "" and rec["why"] == "echo"


def test_internal_labels_never_spoken(tmp_path):
    abil = _abilities(_ability("N:E", "N", "operator_action:operator_on_n", "complexity_axes:2",
                               "complexity_slots:3", "generation_role:PRIMARY"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, tone="explain"), HEARD)
    assert "explain" not in text.lower()


# -- her filler: reference words stand in for entities only ------------------------

def test_reference_anchor_never_replaces_a_verb():
    m = StructuralMotif(pattern_id="p", role_sequence=(R.AGENT, R.ACTION, R.OBJECT),
                        reference_anchors=[(0, 1)])
    assert SlotFiller().fill(m, {R.AGENT: ["I"], R.ACTION: ["want"], R.OBJECT: ["music"]}) == "I want music"


def test_reference_anchor_still_resolves_an_entity():
    m = StructuralMotif(pattern_id="p", role_sequence=(R.AGENT, R.ACTION, R.OBJECT),
                        reference_anchors=[(0, 2)])
    assert SlotFiller().fill(m, {R.AGENT: ["rig"], R.ACTION: ["holds"], R.OBJECT: ["rig"]}) == "Rig holds it"


# -- the gate ----------------------------------------------------------------------

def test_gate_speaks_the_confluence_and_traces_her_motif(tmp_path):
    abil = _abilities(_ability("N:A", "N", "operator_action:operator_on_a", "operator_action:operator_on_n",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:ADJACENT"))
    systems = _systems(_engine(tmp_path), abil, form=RIG)
    resp = SimpleNamespace(content="Here is a scripted thing.", src="constraint_seek", emotional_tone="curious")
    out = VG.apply_voice_gate(systems, resp, HEARD, session_id="t")
    assert out.src == "confluence"
    assert out.content == "I want to start with the rig test, and I am curious."
    assert systems["_last_voice_gate"]["outcome"] == "confluence"
    assert systems["_last_voice_gate"]["abilities"] == ["N:A"]
    trace = systems["_last_grammar_trace"]
    assert trace["source"] == "confluence"
    assert systems["_last_pipeline_state"]["grammar_motif_id"] == trace["motif_id"]


def test_gate_without_grammar_engine_falls_back(tmp_path):
    systems = {"_last_pipeline_state": {"constraint_semantic_state": {"relational_form": dict(RIG)}}}
    resp = SimpleNamespace(content="", src="silence", emotional_tone="curious")
    VG.apply_voice_gate(systems, resp, HEARD, session_id="t2")
    assert systems["_last_voice_gate"]["outcome"] != "confluence"
    assert systems["_last_confluence"]["why"] == "no_grammar_engine"


def test_affect_clause_never_loses_the_quality_it_carries(tmp_path):
    eng = _engine(tmp_path, shapes=[(R.AGENT, R.ACTION), (R.AGENT, R.ACTION, R.OBJECT)])
    abil = _abilities(_ability("N:E", "N", "operator_action:operator_on_a", "operator_action:operator_on_n",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:ADJACENT"))
    text, rec = C.compose(_systems(eng, abil, form=RIG), HEARD)
    assert "I am," not in text and not text.endswith("I am.")
    assert [c["system"] for c in rec["clauses"]] == ["communication"]


def test_function_words_are_not_things_she_relates(tmp_path):
    web = _web(_Rel("already", "related_to", "connection"), _Rel("rig", "related_to", "both"),
               _Rel("rig", "causes", "heat", 0.6))
    abil = _abilities(_ability("X:G", "X", "operator_action:operator_on_a", "operator_action:operator_on_x",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:BRIDGE"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, salient=["already", "rig"], web=web), HEARD)
    assert text == "I want to start with the rig test, so rig causes heat."


def test_typed_knowledge_outranks_words_that_merely_occurred_together():
    web = _web(_Rel("rig", "related_to", "garage", 0.9), _Rel("rig", "has_a", "inverter", 0.6))
    web.relations["r0"].source_of_knowledge = "co-occurrence"
    known = C.knowledge({"oets": SimpleNamespace(web=web)}, ["rig"], "the rig", reach=1)
    assert [k["target"] for k in known] == ["inverter", "garage"]


def test_time_qualifies_what_she_said_she_would_do_not_her_knowledge(tmp_path):
    web = _web(_Rel("rig", "has_a", "inverter"))
    abil = _abilities(_ability("X:T", "X", "operator_action:operator_on_x", "operator_action:operator_on_t",
                               "complexity_axes:2", "complexity_slots:4", "generation_role:PRIMARY"))
    form = {"subject": "the rig", "relation": "", "obj": ""}
    _, rec = C.compose(_systems(_engine(tmp_path), abil, form=form, salient=["rig"], web=web, time_ref="tonight"),
                       "the rig tonight?")
    assert all("tonight" not in c["text"] for c in rec.get("clauses") or [])


def test_a_word_that_is_no_verb_to_her_is_not_her_act(tmp_path):
    form = {"subject": "you", "relation": "witch", "obj": "for the tattoo", "question": True}
    abil = _abilities(_ability("A:P", "A", "operator_action:operator_on_a", "complexity_axes:2",
                               "complexity_slots:4", "generation_role:PRIMARY"))
    _, rec = C.compose(_systems(_engine(tmp_path), abil, form=form),
                       "Which witch would you pick for the tattoo?")
    assert not rec["contributions"].get("stance")


def test_what_was_done_in_the_sentence_is_not_a_thing_she_relates():
    web = _web(_Rel("know", "related_to", "claims"), _Rel("meaning", "is_a", "relation"))
    known = C.knowledge({"oets": SimpleNamespace(web=web)}, ["know", "meaning"], "I know the meaning", reach=1)
    assert [k["source"] for k in known] == ["meaning"]
