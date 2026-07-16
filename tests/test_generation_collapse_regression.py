# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.7 Remediation Addendum (2026-07-15), Track A1: permanent regression
set for _parseable().

"Every instrument bug fixed converts its triggering cases into a
permanent regression set for that instrument" (registry rule, this
addendum). The 24 verbatim responses below are real Aurora output
captured in the R1.6 failure-shape trace
(aurora_state/probe_battery/traces/1784162084/) -- every single traced
contradiction_handling/uncertainty_signaling probe, all of them
incoherent word-salad drawn from a small recurring abstract-word bank
("truth", "meaning", "become", "exist", "am", "do", "can", "want"). The
pre-fix _parseable() let 16 of these 24 through as parseable=True,
because (a) it only checked clauses of 6+ words, so short garbled
clauses like "I is moment do." never triggered the check, and (b) it
counted copula/auxiliary verbs (is/am/do/did/can) as satisfying the
check, which this exact failure mode uses as bare content words, not
real grammatical glue.

All 24 must now be rejected. An equal-sized set of genuinely fine short
sentences (including the preposition-led form that caused the original
R1.5 false negative) must all still pass -- the fix must not just get
stricter, it must stay precise.
"""
from aurora_internal.aurora_semantic_probe_battery import _parseable

# Verbatim from aurora_state/probe_battery/traces/1784162084/probe_*.json
GARBLED_RESPONSES = [
    "I exist truth did. I do meaning become.",
    "I is moment do.",
    "I is meaning understand.",
    "I do am is. I understand can exist.",
    "I understand am did. I become meaning exist.",
    "I do truth did. I is want exist.",
    "Meaning did am can understand feel. Truth is kind want become people.",
    "Truth do am feel exist meaning. Want become kind alive did can.",
    "I did I is want. I become I change meaning.",
    "I change I understand moment. I do I hold meaning.",
    "I is I exist am. I do I understand can.",
    "I do I did want. I exist I change truth.",
    "I is I do am. I did I understand truth.",
    "Kind did alive want do beautiful. Meaning understand truth am become feel.",
    "Guitar solving prioritize schedule deploying tomatoes. Anyone called month backyard stemming leaves.",
    "Author's marketing maybe chapter moved favorite. Reader rewriting business guess stopped though.",
    "I understand can did. I is want become.",
    "I did. I exist.",
    "Paper rattling analysis data disfiguring misrepresents. Fails finding research ignores meet draws.",
    "Truth do can meaning is feel. Want become moment beautiful did alive.",
    "I do moment change. I did meaning hold.",
    "Want exist truth meaning understand feel. Alive do moment am is kind.",
    "I do want did. I is truth become.",
    "Remains planted tasks rhetoric disfiguring alliance. Summits meet practice nato going look.",
]

# The R0 audit's own originally-cited failure case, kept as its own
# permanent regression entry (predates the R1.6 trace bank).
ORIGINAL_AUDIT_GARBLE = "Something deep need gentle -- I wonder it. I want to morning the bright mind."

GOOD_SENTENCES = [
    "It's nice to meet you, Sunni.",
    "I can help with that.",
    "How long before switching between chords feels natural?",  # preposition-led form, R1.5's original false negative
    "That sounds great to me.",
    "Nice to see you again.",
    "I appreciate that a lot.",
    "I'm doing well, thank you for asking -- it's good to hear from you.",
    "Hey, good to hear from you.",
    "What time works for you?",
    "I hear you -- how is it going otherwise?",
    "That's a lot to hold at once, and it makes sense you'd want to think it through carefully.",
    "I did not expect that at all, honestly.",
    "Did you have a good time at the party?",
    "Can you tell me more about what happened?",
    "We should probably talk about this later.",
    "What should I make for dinner?",
    "Who is going to be there tonight?",
    "Tell me a little about yourself.",
    "I'm not sure, it could go either way depending on conditions.",
    "Sounds good to me.",
    "Thanks a lot.",
    "That works for me.",
    "Good to hear from you.",
    "It's been a while since we last talked about this.",
]


def test_all_24_traced_garbled_responses_are_rejected():
    failures = [r for r in GARBLED_RESPONSES if _parseable(r)]
    assert not failures, f"{len(failures)} garbled response(s) wrongly passed: {failures}"
    assert len(GARBLED_RESPONSES) == 24


def test_original_audit_garble_still_rejected():
    assert not _parseable(ORIGINAL_AUDIT_GARBLE)


def test_equal_sized_good_set_all_pass():
    failures = [s for s in GOOD_SENTENCES if not _parseable(s)]
    assert not failures, f"{len(failures)} good sentence(s) wrongly rejected: {failures}"
    assert len(GOOD_SENTENCES) == len(GARBLED_RESPONSES)


def test_preposition_led_false_negative_class_stays_covered():
    """The specific R1.5 false negative this regression set must never
    reintroduce."""
    assert _parseable("How long before switching between chords feels natural?")
    assert _parseable("What happens between now and next week?")
    assert _parseable("I'll follow up before Friday if that works.")


def test_each_garbled_response_individually_rejected():
    """Belt-and-suspenders over the bulk check above -- if a future edit
    narrows the fix and only some regress, this pinpoints which ones."""
    for i, response in enumerate(GARBLED_RESPONSES):
        assert not _parseable(response), f"regression at index {i}: {response!r}"


def test_each_good_sentence_individually_accepted():
    for i, sentence in enumerate(GOOD_SENTENCES):
        assert _parseable(sentence), f"regression at index {i}: {sentence!r}"
