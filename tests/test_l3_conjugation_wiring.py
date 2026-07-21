# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.3 L3: wire the orphaned conjugation table into the delivered path.

_CONJUGATIONS/_conjugate_verb already existed and worked -- but were only
ever called from _fill_template(), which nothing calls since FIX-A016
retired template-string composition in favor of _compose_from_motif's
"template-free" assembly. This left "I is." live in production while a
correct conjugator sat unused two methods away. _conjugate_for_subject is
the shared core, factored out of _conjugate_verb so the delivered
word-list path (which always knows its subject directly -- agent is
always exactly "I" or "you") can call it without a template string to
scan.
"""
from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome


def _make_composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


def test_conjugate_for_subject_i_corrects_copula():
    c = _make_composer()
    assert c._conjugate_for_subject("is", "I") == "am"
    assert c._conjugate_for_subject("was", "I") == "was"
    assert c._conjugate_for_subject("are", "I") == "am"


def test_conjugate_for_subject_i_strips_third_person_s():
    c = _make_composer()
    assert c._conjugate_for_subject("goes", "I") == "go"
    assert c._conjugate_for_subject("wants", "I") == "want"
    assert c._conjugate_for_subject("plays", "I") == "play"


def test_conjugate_for_subject_you_corrects_copula_and_aux():
    c = _make_composer()
    assert c._conjugate_for_subject("is", "you") == "are"
    assert c._conjugate_for_subject("was", "you") == "were"
    assert c._conjugate_for_subject("has", "you") == "have"
    assert c._conjugate_for_subject("does", "you") == "do"


def test_conjugate_for_subject_unrecognized_subject_passes_through():
    c = _make_composer()
    assert c._conjugate_for_subject("is", "she") == "is"
    assert c._conjugate_for_subject("plays", "aurora") == "plays"


def test_conjugate_verb_legacy_template_path_still_works_via_delegation():
    """_conjugate_verb keeps its old template-string-scanning signature
    and behavior -- it now delegates to _conjugate_for_subject, but its
    existing (if dormant) callers see no change."""
    c = _make_composer()
    assert c._conjugate_verb("is", "I {V} here", "{V}") == "am"
    assert c._conjugate_verb("is", "You {V} here", "{V}") == "are"
    assert c._conjugate_verb("is", "She {V} here", "{V}") == "is"


def test_compose_from_motif_conjugates_copula_for_i_subject():
    """The mini-gate's literal regression case: 'I is.' must become
    'I am.' on the delivered path.

    N2.1 (2026-07-16) switched F5 exploration ON, and _select_with_
    temperature's hard invariant (never select below the register's
    relevance floor) means word selection is no longer a lucky-uniform-
    top-4 draw once live -- with no real input_text, "is" (a 2-char
    word, structurally excluded from ever becoming a direct anchor by
    build_relevance_anchor_set's own >=3-char token regex) never
    reliably wins selection anymore, deterministic or not. That's F5.2's
    invariant working correctly, not a conjugation regression -- this
    test's actual purpose is conjugation-on-the-delivered-path, so it
    forces "is" as the selected action word directly rather than hoping
    selection dynamics happen to pick it, keeping the real conjugation
    step (the thing L3 actually wired) genuinely exercised."""
    c = _make_composer()
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    from aurora_grammar_engine import StructuralMotif, TokenRole

    motif = StructuralMotif(
        pattern_id="agent_action_test",
        role_sequence=(TokenRole.AGENT, TokenRole.ACTION),
    )

    orig_select = c._select_constraint_word

    def _force_is_for_action(role, *a, **kw):
        if role == "action":
            return "is"
        return orig_select(role, *a, **kw)

    c._select_constraint_word = _force_is_for_action

    sent = c._compose_from_motif(
        motif, {"X": 1.0, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5},
        0.3, "i_is", 0, input_text="",
    )
    assert "I is" not in sent, f"unconjugated copula leaked through: {sent!r}"
    assert sent.strip().rstrip(".") == "I am", (
        f"expected 'is' to be conjugated to 'am' on the delivered path, got {sent!r}"
    )


def test_compose_from_motif_leaves_non_i_you_subjects_alone():
    """Only the agent role's own word (always 'I'/'you' by construction)
    drives conjugation -- no other role should ever trigger it."""
    c = _make_composer()
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    from aurora_grammar_engine import StructuralMotif, TokenRole

    motif = StructuralMotif(
        pattern_id="object_only_test",
        role_sequence=(TokenRole.OBJECT, TokenRole.OBJECT),
    )
    sent = c._compose_from_motif(
        motif, {"X": 0.5, "T": 0.5, "N": 1.0, "B": 0.5, "A": 0.5},
        0.0, "i_is", 0, input_text="",
    )
    # No agent role present in this skeleton -> current_subject stays None
    # for the whole sentence -> nothing gets conjugated (no crash either).
    assert isinstance(sent, str)
