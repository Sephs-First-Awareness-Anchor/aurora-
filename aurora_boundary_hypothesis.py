"""
aurora_boundary_hypothesis.py
Sunni (Sir) Morningstar & Cael Devo

WHAT THIS CHANGES
------------------
_question_boundary_surface/_directive_boundary_surface (aurora_internal/
aurora_constraint_semantic_continuity.py) previously went straight to "I
do not yet have enough grounded information to answer it without
inventing one" the instant the reasoning chain reached an unresolved
relational boundary -- correct in spirit (never assert a fabricated fact
as settled), but it never attempted a real, checkable read of the
question first. Per Sunni's own standing direction (already applied to
referent/pronoun resolution in aurora_referent_hypothesis.py -- this
module mirrors that one's discipline for the boundary-surface fallback):
Aurora needs to try, be allowed to be wrong, and be correctable -- not
concede immediately every time with nothing for the user to correct.

WHY THIS IS NOT "INVENT A FACT"
---------------------------------
A boundary hypothesis never fabricates content the user didn't supply.
It reflects back exactly the subject/relation/object the relational-form
extractor already pulled from the user's own sentence, framed as a
checkable interpretation ("is that what you meant?") rather than a
description of Aurora's own confusion. The uncertainty is about
INTERPRETATION (did I parse your sentence correctly?), not about
FACTS (I am not guessing at unknown world knowledge here) -- so this
stays inside the same "never assert what isn't grounded" boundary the
abstention text was protecting, while giving the user something concrete
to correct instead of a bare admission of failure.

TRY, FAIL, CORRECT COURSE -- NOT TRY AND FORGET
---------------------------------------------------
Mirrors aurora_referent_hypothesis.py exactly: a hypothesis is phrased as
checkable, registered as pending, and check_and_resolve_pending_boundary_
hypothesis() (called at the same point in _run_live_response_turn as the
referent-hypothesis check, right beside it) looks for a real correction
signal in the next turn and logs the outcome -- confirmed or corrected --
via aurora_developmental_log.record_developmental_event, the same real
path that already turns this event into genuine i_did/A-axis pressure.
Reuses aurora_referent_hypothesis's own correction-marker detection
rather than duplicating it.
"""

from typing import Any, Dict, Optional

from aurora_referent_hypothesis import _BARE_NEGATIVE_LEAD, _CORRECTION_MARKERS


def attempt_boundary_hypothesis(
    systems: Optional[Dict[str, Any]],
    form: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Attempt a real, checkable interpretation of an unresolved relational
    question, built only from what the relational-form extractor already
    pulled from the user's own sentence. Returns None when there isn't
    even a subject or relation to reflect back (the honest "I don't
    understand this at all" case remains correct then), or when systems
    isn't available to register the pending hypothesis against (callers
    that don't have a live turn to check next turn against -- e.g.
    aurora_communication_emergence.py's own use of the same underlying
    candidate-derivation function).
    """
    if not isinstance(systems, dict):
        return None
    subject = str(form.get("subject", "") or "").strip()
    relation = str(form.get("relation", "") or "").strip()
    obj = str(form.get("obj", "") or "").strip()
    if not subject and not relation:
        return None
    hypothesis = {
        "subject": subject,
        "relation": relation,
        "obj": obj,
        "confidence": 0.5,  # a try, not an assertion
    }
    systems["_pending_boundary_hypothesis"] = dict(hypothesis)
    return hypothesis


def render_checkable_boundary_interpretation(hypothesis: Dict[str, Any]) -> str:
    """
    Phrase the hypothesis so it can be checked and corrected, never as
    settled fact. Quotes the raw words pulled from the user's own
    sentence rather than trying to reassemble them into a fully natural
    sentence -- that reconstruction is exactly what produced the earlier
    "the relation you described as be" bug (a normalized/lemma form read
    back as if it were the user's own word). Honest about being a read
    on the words, not a claim about their meaning.
    """
    subject = str(hypothesis.get("subject", "") or "").strip()
    relation = str(hypothesis.get("relation", "") or "").strip()
    obj = str(hypothesis.get("obj", "") or "").strip()
    parts = [p for p in (subject, relation, obj) if p]
    if not parts:
        return (
            "I understand you're asking me something, but I'm not sure "
            "I've caught the shape of it yet -- can you say it a "
            "different way?"
        )
    quoted = " / ".join(f"\"{p}\"" for p in parts)
    return (
        f"My best read on that is it's about {quoted}. Did I catch the "
        "right pieces? Tell me if I've got it wrong and I'll follow "
        "your lead instead."
    )


def check_and_resolve_pending_boundary_hypothesis(
    systems: Dict[str, Any],
    new_user_text: str,
) -> Optional[Dict[str, Any]]:
    """
    Call at the START of the next turn, before this turn builds any new
    hypothesis of its own -- same timing as aurora_referent_hypothesis's
    check_and_resolve_pending_hypothesis(), and meant to be called right
    beside it. Detects a real correction signal and logs the outcome --
    confirmed or corrected -- as genuine developmental pressure either
    way, so a wrong interpretation is preserved and learned from rather
    than silently dropped.
    """
    if not isinstance(systems, dict):
        return None
    pending = systems.get("_pending_boundary_hypothesis")
    if not pending:
        return None
    systems["_pending_boundary_hypothesis"] = None

    text_low = str(new_user_text or "").lower()
    was_corrected = (
        any(marker in text_low for marker in _CORRECTION_MARKERS)
        or bool(_BARE_NEGATIVE_LEAD.match(text_low))
    )

    outcome = dict(pending)
    outcome["corrected"] = was_corrected
    try:
        from aurora_developmental_log import record_developmental_event
        _pieces = " / ".join(
            f"{k}={pending.get(k)!r}" for k in ("subject", "relation", "obj") if pending.get(k)
        )
        record_developmental_event(
            systems,
            "boundary_hypothesis_corrected" if was_corrected else "boundary_hypothesis_confirmed",
            (f"guessed the shape of an unresolved question ({_pieces})"
             + (" -- corrected by user" if was_corrected else " -- accepted, no correction")),
            once=False,
        )
    except Exception:
        pass

    return outcome
