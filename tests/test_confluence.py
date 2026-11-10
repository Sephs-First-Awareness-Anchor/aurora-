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


def _said(*statements, speaker="sunni", listener="aurora"):
    """Her web after hearing these statements: (subject, relation, object[, negated])."""
    from aurora_internal.aurora_propositional_understanding import integrate_form
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb
    web = OntologicalWeb()
    for st in statements:
        subj, rel, obj = st[:3]
        integrate_form(web, {"subject": subj, "relation": rel, "obj": obj, "negated": bool(st[3:] and st[3])},
                       heard="", speaker=speaker, listener=listener,
                       profile={"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2})
    return web


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

SAY_N = ("operator_action:operator_on_a", "operator_action:operator_on_n",
         "complexity_axes:3", "complexity_slots:4", "generation_role:ADJACENT")


def test_agency_then_what_was_said(tmp_path):
    web = _said(("the inverter", "overheats", "the cables"))
    abil = _abilities(_ability("N:A", "N", *SAY_N))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, salient=["inverter"], web=web), HEARD)
    assert text == "I want to start with the rig test, and inverter overheats cables."
    assert [c["system"] for c in rec["clauses"]] == ["communication", "knowledge"]


def test_no_feeling_frame_and_no_relation_labels(tmp_path):
    web = _web(_Rel("rig", "has_a", "inverter"), _Rel("test", "related_to", "garage"))  # nobody said these
    abil = _abilities(_ability("N:A", "N", *SAY_N, "operator_action:operator_on_x"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, salient=["rig", "test"], web=web,
                                   tone="curious"), HEARD)
    assert "curious" not in text and "related" not in text and "has a" not in text
    assert text == "" and rec["why"] == "echo"      # only the speaker's own words were left: silence


def test_choosing_follows_what_was_said_about_an_option(tmp_path):
    web = _said(("the battery", "overheats", "the inverter"))
    abil = _abilities(_ability("N:A", "N", *SAY_N, "operator_action:operator_on_b"))
    text, _ = C.compose(_systems(_engine(tmp_path), abil, form=RIG, salient=["battery"], web=web), HEARD)
    assert text == "I want the battery layout, and battery overheats inverter."


def test_she_says_who_holds_it(tmp_path):
    web = _said(("I", "love", "old soul records"))
    abil = _abilities(_ability("X:G", "X", "operator_action:operator_on_x", "complexity_axes:2",
                               "complexity_slots:4", "generation_role:PRIMARY"))
    form = {"subject": "you", "relation": "think", "obj": "about records", "question": True}
    text, _ = C.compose(_systems(_engine(tmp_path), abil, form=form, salient=["records"], web=web),
                        "What do you think about records?", session_id="live")
    assert text == "You love records."


def test_a_denial_is_said_as_a_denial_and_contrasts(tmp_path):
    web = _said(("the battery", "overheats", "the inverter", True), ("the battery", "overheats", "the inverter", True))
    abil = _abilities(_ability("B:S", "B", "operator_action:operator_on_a", "operator_action:operator_on_b",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:SHEAR"))
    form = dict(RIG, alternatives=[])
    text, _ = C.compose(_systems(_engine(tmp_path), abil, form=form, salient=["battery"], web=web), HEARD)
    assert text == "I want to start with the rig test, but battery does not overheat inverter."


def test_distinction_chooses_the_option_she_knows_more_about(tmp_path):
    web = _said(("the layout", "feeds", "the wiring"))
    abil = _abilities(_ability("B:D", "B", "operator_action:operator_on_b", "operator_action:operator_on_a",
                               "purpose_lane:distinction_branching", "complexity_axes:3",
                               "complexity_slots:4", "generation_role:SHEAR"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, web=web), HEARD)
    assert text.startswith("I want the battery layout")
    assert rec["clauses"][0]["role_sequence"] == ["agent", "action", "determiner", "object"]


def test_slots_from_abilities_limit_which_motifs_may_carry_a_clause(tmp_path):
    web = _said(("the inverter", "overheats", "the cables"))
    eng = _engine(tmp_path, shapes=[(R.AGENT, R.ACTION, R.OBJECT, R.DESCRIPTOR), (R.AGENT, R.ACTION, R.OBJECT)])
    spec = ("operator_action:operator_on_a", "operator_action:operator_on_t", "operator_action:operator_on_n",
            "complexity_axes:3", "generation_role:ADJACENT")
    wide = _abilities(_ability("A:W", "A", *spec, "complexity_slots:4"))
    narrow = _abilities(_ability("A:N", "A", *spec, "complexity_slots:3"))
    text, _ = C.compose(_systems(eng, wide, form=RIG, salient=["inverter"], web=web, time_ref="tonight"), HEARD)
    assert text == "I want to start with the rig test tonight, and inverter overheats cables."
    _, rec = C.compose(_systems(eng, narrow, form=RIG, salient=["inverter"], web=web, time_ref="tonight"), HEARD)
    assert all("tonight" not in c["text"] for c in rec["clauses"])     # no four-role shape fits 3 slots


def test_promoted_motifs_come_first(tmp_path):
    eng = _engine(tmp_path, promoted=[(R.AGENT, R.ACTION, R.OBJECT, R.DESCRIPTOR)])
    abil = _abilities(_ability("A:T", "A", "operator_action:operator_on_a", "operator_action:operator_on_t",
                               "complexity_axes:2", "complexity_slots:4", "generation_role:PRIMARY"))
    _, rec = C.compose(_systems(eng, abil, form=RIG, time_ref="tonight"), HEARD)
    assert rec["clauses"][0]["promoted"] is True
    assert rec["clauses"][0]["role_sequence"] == ["agent", "action", "object", "descriptor"]
    assert rec["why"] == "echo"           # all of it was the speaker's own words: silence


def test_time_qualifies_what_she_said_she_would_do_not_her_knowledge(tmp_path):
    web = _said(("the rig", "powers", "the inverter"))
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


def test_echo_alone_is_silence(tmp_path):
    abil = _abilities(_ability("A:P", "A", "operator_action:operator_on_a", "complexity_axes:2",
                               "complexity_slots:4", "generation_role:PRIMARY"))
    text, rec = C.compose(_systems(_engine(tmp_path), abil, form=RIG, tone=""), HEARD)
    assert text == "" and rec["why"] == "echo"


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
    web = _said(("the inverter", "overheats", "the cables"))
    abil = _abilities(_ability("N:A", "N", *SAY_N))
    systems = _systems(_engine(tmp_path), abil, form=RIG, salient=["inverter"], web=web)
    resp = SimpleNamespace(content="Here is a scripted thing.", src="constraint_seek", emotional_tone="curious")
    out = VG.apply_voice_gate(systems, resp, HEARD, session_id="t")
    assert out.src == "confluence"
    assert out.content == "I want to start with the rig test, and inverter overheats cables."
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


def test_what_was_done_in_the_sentence_is_not_a_thing_she_relates():
    assert "know" in C._acts_in("I know the meaning")


def test_what_she_voiced_rests_before_it_is_voiced_again(tmp_path):
    web = _said(("the inverter", "overheats", "the cables"))
    abil = _abilities(_ability("N:A", "N", *SAY_N))
    systems = _systems(_engine(tmp_path), abil, form=RIG, salient=["inverter"], web=web)
    first, _ = C.compose(systems, HEARD)
    assert first.endswith("inverter overheats cables.")
    again, rec = C.compose(systems, HEARD)
    assert again == "" and rec["why"] == "echo"          # the statement rests; only the speaker's words remain
    salient = systems["_last_pipeline_state"]["salient_concepts"]
    systems["_last_pipeline_state"]["salient_concepts"] = []
    for _ in range(C.REST_TURNS):
        C.compose(systems, "something else entirely")
    systems["_last_pipeline_state"]["salient_concepts"] = salient
    assert C.compose(systems, HEARD)[0] == first


def test_the_other_speakers_words_turn_over_with_perspective():
    assert C._phrase("what I mean", limit=3, to_her=True) == "what you mean"
    assert C._phrase("your rig", limit=3, to_her=True) == "my rig"


def test_a_modal_said_is_kept():
    from aurora_internal.aurora_propositional_understanding import lexicalize_assertion
    web = _said()
    from aurora_internal.aurora_propositional_understanding import integrate_form
    integrate_form(web, {"subject": "the mechanism", "relation": "slot", "obj": "the engine", "modality": "could"},
                   heard="", speaker="sunni", listener="aurora", profile={"X": 1})
    rel = next(iter(web.relations.values()))
    assert lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")["action"] == "could slot"
