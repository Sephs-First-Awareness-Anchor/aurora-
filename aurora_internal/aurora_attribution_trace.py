"""
RW7 (Architecture Wiring Audit, 2026-07-20) -- attribution capture for the
delivered-path relevance question: does the measured relevance score
actually reflect SentenceComposer.compose()'s word selection, or does it
reflect the waterfall chain's own anchor-injection repair functions
(_repair_unproductive_echo / _repair_unanswered_question / _repair_
discourse_coherence), which never touch the composer at all?

Read-only observer, same contract as every other shadow/diagnostic hook
this campaign has built (Tier-2, B1.1, Track CP): capture only, zero
behavioral effect, gated behind an explicit opt-in flag so a normal live
boot pays nothing for this and nothing changes about what gets said.

Single-turn scratch slot, not a queue -- this pipeline is synchronous and
single-threaded per turn (matches _conn_cache-style module globals already
used elsewhere in this codebase, e.g. aurora_offline_resilience.py).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from typing import Any, Dict, Optional

_ENABLED = False
_composer_raw: Optional[str] = None
_word_sources: Optional[Dict[str, Any]] = None
_motif_summaries: Optional[list] = None
_log: list = []


def enable_capture() -> None:
    global _ENABLED
    _ENABLED = True


def disable_capture() -> None:
    global _ENABLED, _composer_raw, _word_sources, _motif_summaries
    _ENABLED = False
    _composer_raw = None
    _word_sources = None
    _motif_summaries = None


def is_capture_enabled() -> bool:
    return _ENABLED


def record_composer_raw(text: Any) -> None:
    """Called from ExpressionPerceptionEngine._build_expression immediately
    after SentenceComposer.compose() returns -- the composer's own byte
    output, before any gateway-side articulation smoothing or D2.1
    unification can touch it."""
    global _composer_raw
    if not _ENABLED:
        return
    try:
        if isinstance(text, dict):
            text = text.get("expression", "")
        _composer_raw = str(text or "")
    except Exception:
        pass


def pop_composer_raw() -> Optional[str]:
    """Consume the current turn's composer-raw capture. Returns None if
    capture is disabled or compose() was never reached this turn (e.g.
    resp_A's own chain already produced content and gw._express() short-
    circuited before compose(), if that path exists)."""
    global _composer_raw
    val = _composer_raw
    _composer_raw = None
    return val


def record_word_sources_and_motifs(composer: Any) -> None:
    """PF1.0 (Directive PF1, 2026-07-20): called alongside record_composer_raw,
    same hook, same turn. Snapshots composer._last_word_sources (word ->
    {tag, candidate_source, usage_count_at_selection}) and a compact summary
    of composer._last_motifs_used (role sequence + identity per motif this
    turn) -- settles RW7's open side-channel question (fresh-word usage_
    count=0 tiebreak vs. DPS-crystal resonance) and baselines motif
    diversity per turn."""
    global _word_sources, _motif_summaries
    if not _ENABLED:
        return
    try:
        _word_sources = dict(getattr(composer, "_last_word_sources", {}) or {})
    except Exception:
        _word_sources = None
    try:
        motifs = list(getattr(composer, "_last_motifs_used", []) or [])
        summaries = []
        for m in motifs:
            try:
                roles = [getattr(r, "value", str(r)) for r in getattr(m, "role_sequence", [])]
            except Exception:
                roles = []
            summaries.append({
                "motif_id": str(getattr(m, "pattern_id", id(m))),
                "role_sequence": roles,
            })
        _motif_summaries = summaries
    except Exception:
        _motif_summaries = None


def pop_word_sources_and_motifs():
    """Consume the current turn's word-source/motif capture. Returns
    (word_sources_dict_or_None, motif_summaries_list_or_None)."""
    global _word_sources, _motif_summaries
    ws, ms = _word_sources, _motif_summaries
    _word_sources, _motif_summaries = None, None
    return ws, ms


def record_turn(probe_id: str, dimension: str, user_text: str,
                 composer_raw: Optional[str], branch: str,
                 resp_b_content: Optional[str], final_delivered: str) -> None:
    """Append one completed turn's full attribution record. `branch` is
    one of: 'composer_unified' (resp_A's words became resp_B's, i.e. the
    composer's voice reached the delivered text), 'chain_own_content'
    (composer produced nothing usable, resp_A's own waterfall chain
    content was kept), 'abstain' (neither produced anything, the honest-
    abstain crash net fired)."""
    if not _ENABLED:
        return
    try:
        _log.append({
            "probe_id": probe_id,
            "dimension": dimension,
            "user_text": user_text,
            "composer_raw": composer_raw,
            "branch": branch,
            "resp_b_content": resp_b_content,
            "final_delivered": final_delivered,
            "composer_reached_delivery": bool(
                composer_raw and final_delivered and composer_raw.strip() == final_delivered.strip()
            ),
        })
    except Exception:
        pass


def get_log() -> list:
    return list(_log)


def clear_log() -> None:
    global _log
    _log = []
