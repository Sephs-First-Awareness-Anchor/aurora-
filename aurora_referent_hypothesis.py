"""
aurora_referent_hypothesis.py
Sunni (Sir) Morningstar & Cael Devo

WHAT THIS CHANGES
------------------
_render_user_context_clarification (aurora.py) previously went straight to
asking "what should I use as the right reference for {target}?" the instant
a private/unresolved pronoun was detected -- correct behavior when there is
truly nothing to go on, but it never even attempted a real guess first.
Per Sunni's direction: Aurora needs to try, be allowed to fail, and be able
to correct course -- not concede immediately every time.

This module wires that in using machinery that already exists and already
runs every turn: aurora_internal.aurora_attention_engine.AttentionEngine's
per-turn AttentionFrame.anchors (populated in aurora.py's live-turn tick
from the parsed utterance's own topic tags -- confirmed real and already
running; NOT invented for this module). Walking AttentionEngine.history
backward gives a genuine, already-tracked record of what was recently
salient, which is exactly the candidate pool a referent guess should draw
from.

REMEMBERING THE GENERATIVE RULE
---------------------------------
This deliberately does NOT implement a hand-written coreference-resolution
algorithm (POS tagging, dependency parsing, hard-coded pronoun rules, etc).
That would be scripting an answer Aurora's own architecture should be able
to develop. Instead, this wires her existing, already-running salience
history into the one place that never consulted it, and lets that real
signal (or its real absence) decide whether a guess is even offered.

TRY, FAIL, CORRECT COURSE -- NOT TRY AND FORGET
---------------------------------------------------
A guess is always phrased as checkable ("Do you mean X?"), never asserted
as settled fact -- this preserves error, it doesn't erase or hide it. The
next turn's check_and_resolve_pending_hypothesis() looks for a real
correction signal in the user's reply and logs the outcome -- confirmed or
corrected -- via aurora_developmental_log.record_developmental_event, which
is already the real, existing path that turns a discrete event into
genuine i_did/A-axis experiential pressure through EEPR. This avoids
fabricating a constraint_genealogy PressureVec just to force a "learning"
event into existence -- the same discipline applied to the resolver module
built earlier this session.

A SEPARATE FINDING, NOT FIXED HERE
--------------------------------------
While tracing genealogy call sites for this work, aurora.py's
_sediment_validated_fact was found to gate its constraint-genealogy write
on `hasattr(gen, "log_relief")` -- but no `log_relief` method exists
anywhere in this codebase (confirmed via full-repo search). That gate is
therefore always False, and that grounding step has been silently
no-op-ing. Flagging for the known_fixes_registry; out of scope for this
change.
"""

import re
from typing import Any, Dict, List, Optional

from aurora_constraint_emission import _ANCHOR_TOKEN_STOPWORDS

_CORRECTION_MARKERS = (
    "no,", "not that", "not what i meant", "that's not it",
    "i meant", "actually i", "wrong", "that's wrong",
)

# Codex review, PR #176: _CORRECTION_MARKERS' only bare-negative entry is
# "no," -- a plain "No." or "No" (the single most common way to reject a
# checkable guess) has no trailing comma, so none of the markers matched
# and the reply fell through to "confirmed", logging a rejected guess as
# accepted. Word-boundary match "no" as the reply's leading word instead,
# independent of what punctuation (if any) follows it.
_BARE_NEGATIVE_LEAD = re.compile(r"^\s*no\b")


def gather_recent_anchor_candidates(
    systems: Dict[str, Any],
    max_candidates: int = 5,
) -> List[str]:
    """
    Real candidate pool, drawn only from AttentionEngine.history's already-
    populated AttentionFrame.anchors (topic-tag words from parsed
    utterances, most recent turn first). Returns [] honestly when there's
    nothing real to offer -- the caller must fall back to asking, not guess
    anyway.
    """
    ae = systems.get('_attention_engine') if isinstance(systems, dict) else None
    if ae is None:
        return []
    # Only prior turns can meaningfully inform a referent guess. tick()
    # appends its own just-computed frame straight into history (see
    # AttentionEngine.tick -> self._record_history(frame)), so history[-1]
    # is THIS turn's own tick, not a separate "current" frame -- confirmed
    # live: including it produced "matter" as a guess for "why did that
    # matter to me", drawn from the very sentence containing the pronoun.
    # Prior-turns-only means history[:-1].
    frames = list(getattr(ae, 'history', []) or [])[:-1]

    candidates: List[str] = []
    seen = set()
    for frame in reversed(frames):
        for anchor in list(getattr(frame, 'anchors', []) or []):
            word = str(anchor).strip().lower()
            if not word or word in seen or word in _ANCHOR_TOKEN_STOPWORDS:
                continue
            seen.add(word)
            candidates.append(word)
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def attempt_referent_hypothesis(
    systems: Dict[str, Any],
    target_pronoun: str,
) -> Optional[Dict[str, Any]]:
    """
    Attempt a real, checkable guess for what target_pronoun refers to.
    Returns None when there is genuinely nothing to draw on (the honest
    clarifying question remains correct in that case, unchanged). Returns a
    hypothesis dict, and registers it as pending, when a real candidate
    exists.
    """
    candidates = gather_recent_anchor_candidates(systems)
    if not candidates:
        return None
    hypothesis = {
        'target': target_pronoun,
        'guess': candidates[0],
        'alternatives': candidates[1:3],
        'confidence': 0.55,  # a try, not an assertion
    }
    if isinstance(systems, dict):
        systems['_pending_referent_hypothesis'] = dict(hypothesis)
    return hypothesis


def render_checkable_hypothesis_clarification(hypothesis: Dict[str, Any]) -> str:
    """
    Phrase the hypothesis so it can be checked and corrected, never as
    settled fact.
    """
    guess = str(hypothesis.get('guess', '') or '').strip()
    target = str(hypothesis.get('target', '') or '').strip() or 'that'
    if not guess:
        return f"What should I use as the right reference for {target}?"
    return f"Do you mean {guess}? If not, tell me what {target} actually refers to."


def check_and_resolve_pending_hypothesis(
    systems: Dict[str, Any],
    new_user_text: str,
) -> Optional[Dict[str, Any]]:
    """
    Call at the START of the next turn, before this turn builds any new
    hypothesis of its own. Detects a real correction signal and logs the
    outcome -- confirmed or corrected -- as genuine developmental pressure
    either way, so a wrong guess is preserved and learned from rather than
    silently dropped.
    """
    if not isinstance(systems, dict):
        return None
    pending = systems.get('_pending_referent_hypothesis')
    if not pending:
        return None
    systems['_pending_referent_hypothesis'] = None

    text_low = str(new_user_text or '').lower()
    was_corrected = (
        any(marker in text_low for marker in _CORRECTION_MARKERS)
        or bool(_BARE_NEGATIVE_LEAD.match(text_low))
    )

    outcome = dict(pending)
    outcome['corrected'] = was_corrected
    try:
        from aurora_developmental_log import record_developmental_event
        record_developmental_event(
            systems,
            'referent_hypothesis_corrected' if was_corrected else 'referent_hypothesis_confirmed',
            (f"guessed '{pending.get('guess')}' for '{pending.get('target')}'"
             + (" -- corrected by user" if was_corrected else " -- accepted, no correction")),
            once=False,
        )
    except Exception:
        pass

    # Wire the outcome to where ConstraintEmitter.emit() can actually see
    # it. EmissionContext carries working_memory, not the raw systems
    # dict -- without this, the outcome was logged but invisible to
    # emit(), so a stale open seeking flag (e.g. an unrelated vocabulary
    # gap from an earlier turn) could still win this turn's response via
    # its own anchor-guard, exactly as happened live: correcting a
    # referent guess got answered with a vocabulary re-ask instead.
    wm = systems.get('working_memory')
    if wm is not None:
        try:
            wm._last_referent_correction = dict(outcome)
        except Exception:
            pass

    return outcome
