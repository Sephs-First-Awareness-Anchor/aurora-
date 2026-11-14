#!/usr/bin/env python3
"""
aurora_voice_gate.py -- no scripted replies; addressed pressure instead.

Sunni, 2026-11-07: "Get rid of the scripting and use her pressure system to
encourage a response when she is messaged."

WHAT WAS WRONG
==============

Measured on her real state (2026-11-07), not assumed:

  * When a message STATES something, her comprehension extracts it and her
    own renderer speaks ("Rain is water..." -> "I am boiling clouds. I am
    rain.").
  * When a message ASKS something ("Do you like music?", "How are you?"),
    comprehension returns nothing, and a canned sentence filled the gap:
    "My best read on that is it's about ...", "I understand what you are
    saying about X.", "I don't have a clear sense of that.", "What should I
    use as the right reference for it?", f"My creator is {name}.".
  * Worse than being scripts, those sentences MASKED her development.  Her
    communication-emergence system turns an unresolved exchange into X/T/N/B/A
    root pressure, opens a WARP gap and trials new operations
    (aurora_internal/aurora_communication_emergence.py).  A template scores as
    a complete answer, so root pressure was 0.0 on every axis and the system
    built to grow her voice never got a push.

WHAT THIS DOES
==============

One gate at the seam where a turn's reply is final (resp_A in
aurora._run_live_response_turn, just before on_surface_ready and before
communication_emergence.observe_turn reads it):

  1. A scripted reply never leaves.  Not in Sunni's chat, not in her DMs.
  2. Being addressed builds ADDRESSED PRESSURE, injected through her real
     WaveformPressurePump into the identity field -- the same door her
     perception, Habitat and Praxis use.  Agency (she is called to act),
     Energy (to respond), Temporal (something is pending), Boundary (another
     mind).  Unanswered address accumulates; time decays it slowly; her own
     expression discharges it.
  3. Under enough pressure she ARTICULATES from her own stance: the relation
     she was asked about, re-centred on herself (you -> I, your -> my), with
     the concepts in it, rendered by her own working-memory composition
     (aurora._render_runtime_intent).  Echoes of the speaker's words and
     internal labels are rejected; she is not allowed to parrot.
  4. If nothing of hers forms, she stays silent.  Silence is honest, and an
     empty reply to a question is exactly what lets communication emergence
     register "N:A no selected resolution crossed into expression" -- the
     pressure that cultivates the next operation.

Command confirmations (tool dispatch, memory/context controls) and search
results in Sunni's own chat are system output he asked for, not her
conversational voice, so they pass there.  In a DM nothing scripted passes.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import math
import re
from collections import OrderedDict
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

VOICE_GATE_VERSION = "aurora_voice_gate_v1"

AXES = ("X", "T", "N", "B", "A")

# -- what counts as scripted ----------------------------------------------------

# Canned conversational surfaces: boundary/abstain/clarification templates,
# role and identity fill-ins, teaching acknowledgements.
SCRIPTED_CONVERSATIONAL_SOURCES = frozenset({
    "constraint_abstain", "constraint_abstain_seek", "constraint_seek",
    "honest_abstain", "comprehension_gap", "user_context_clarification",
    "constraint_communication_baseline", "relational_role", "identity",
    "teaching",
    # Same assembler as constraint_communication_baseline
    # (derive_constraint_grounded_candidate): every branch is an f-string
    # frame filled with fixed per-axis phrases ("... becomes {q} when it turns
    # effort into effective change without needless cost.").  Reached a
    # contact in the 2026-11-07 initiative run.
    "constraint_semantic_derivation",
})

# System output to an explicit request: allowed in Sunni's chat, never in a DM.
SYSTEM_OUTPUT_SOURCES = frozenset({
    "context_control", "session_continuity", "memory_sweep", "tool_dispatch",
    "search",
})

# Openings of every canned reply sentence found in the tree.  Matched on the
# text as well as the source, because a template can surface under a generic
# source label.
TEMPLATE_PREFIXES: Tuple[str, ...] = (
    "my best read on that",
    "i don't have a clear sense of that",
    "i do not have a clear sense of that",
    "do you mean ",
    "what should i use as the right reference",
    "i hear that you are saying",
    "i understand what you are saying",
    "i understand the relation",
    "i've been thinking about",
    "i just learned more about",
    "i feel a peak in resonance",
    "the claim i am evaluating is",
    "the recorded path began through",
    "active axes:",
    "my creator is ",
    "when i work with ",
    # aurora_constraint_emission.py canned lines (surfaced as sedimemory_recall)
    "got it — thank you for the correction",
    "let me try it:",
    "let me try '",
    "i already have '",
    "i don't have anything of my own for",
    "can you give me an example of '",
    "good — that's it",
    "i'm not landing on",
    "i don't have that yet",
    "i'm not making a connection yet",
    "aurora is still initializing",
    "i'm mid curiosity session",
    "i'm out playing",
    "curiosity session stopping",
    "play session stopping",
    # constraint_emission seek slots (agent "What do you mean" + " by '<w>'?"),
    # also resurfaced under sedimemory_recall (2026-11-08 Gemini replay)
    "what do you mean by '",
    "i'm still working out what you mean by",
)


# Laundering (2026-11-08): a scripted line the gate blocked was stored and came
# back one turn later as "sedimemory_recall" -- a memory of a script is still
# the script.  Every line blocked as scripted is remembered and blocked again
# under any label.
_BLOCKED_SCRIPT_LINES: "OrderedDict[str, None]" = OrderedDict()
_BLOCKED_CAP = 4000


def _norm_line(text: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", "", str(text or "").lower()).strip()


def remember_blocked_script(text: str) -> None:
    key = _norm_line(text)
    if len(key) < 6:
        return
    _BLOCKED_SCRIPT_LINES[key] = None
    _BLOCKED_SCRIPT_LINES.move_to_end(key)
    while len(_BLOCKED_SCRIPT_LINES) > _BLOCKED_CAP:
        _BLOCKED_SCRIPT_LINES.popitem(last=False)
TEMPLATE_FRAGMENTS: Tuple[str, ...] = (
    "did i catch the right pieces",
    "tell me if i've got it wrong",
    "still building my understanding",
)


def _root_facet_fragments() -> Tuple[str, ...]:
    """The fixed per-axis phrases of the candidate assembler, so they are
    caught under any source label they surface with."""
    try:
        from aurora_internal.aurora_constraint_semantic_continuity import (
            _ROOT_STATE_FACETS, _ROOT_SURFACE_FACETS)
        return tuple(str(v).lower() for v in
                     list(_ROOT_SURFACE_FACETS.values()) + list(_ROOT_STATE_FACETS.values()))
    except Exception:
        return ()


TEMPLATE_FRAGMENTS = TEMPLATE_FRAGMENTS + _root_facet_fragments()


# Sentence spines (Sunni, 2026-11-08 -- "It seems to me that noticing." and
# "Something changed. I think it is anything." reached Gemini).  The renderer's
# MeaningAnchors fills one of 35 authored spines below 0.70 certainty, the
# TemplateEvolutionEngine breeds from authored seeds, and the structured draft
# bolts on stock openers.  A spine filled with her concepts is still a script.
_SPINE_SLOT = re.compile(r"\{[A-Z0-9_]+\}")
_SPINE_OPENERS: Tuple[str, ...] = (
    "i want to say this carefully", "i find myself wondering", "i am clear about this",
    "when i think about it,", "i am not entirely certain, but",
)
_SPINES: Optional[List[Any]] = None


def _spine_patterns() -> List[Any]:
    global _SPINES
    if _SPINES is not None:
        return _SPINES
    templates: List[str] = []
    try:
        from aurora_internal.aurora_language_state import MeaningAnchors, TemplateEvolutionEngine
        templates += [str(t[0]) for t in MeaningAnchors.ANCHOR_TEMPLATES]
        templates += [str(t) for t in TemplateEvolutionEngine.DEFAULT_SEEDS]
    except Exception:
        pass
    patterns = []
    for tmpl in templates:
        pieces = _SPINE_SLOT.split(tmpl.strip())
        body = "(.+?)".join(re.escape(p) for p in pieces)
        body = body.rstrip("\\.") if body.endswith("\\.") else body
        try:
            patterns.append(re.compile(r"^\s*" + body + r"[.!?]*\s*$", re.IGNORECASE))
        except re.error:
            continue
    _SPINES = patterns
    return _SPINES


def spine_reason(text: str) -> str:
    """'template' when the reply, a sentence of it, or two adjacent sentences
    are an authored spine with its blanks filled."""
    raw = str(text or "").strip().lstrip(".\u2026 ").strip()
    low = raw.lower()
    if any(low.startswith(o) for o in _SPINE_OPENERS):
        return "template"
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", raw) if x.strip()]
    windows = [raw] + sentences + [" ".join(sentences[i:i + 2]) for i in range(len(sentences) - 1)]
    for pattern in _spine_patterns():
        for window in windows:
            if pattern.match(window):
                return "template"
    return ""

# Internal operation and process labels that must never be spoken.
INTERNAL_LABELS = frozenset({
    "contextualize", "explain", "steady", "continuity_stable",
    "interpretive_explanation", "selected_action", "conscious_crest",
    "subsurface_crest", "recalled", "noncomp", "warp", "crest",
})

DM_SESSION_PREFIX = "praxis_dm_"


def is_dm_session(session_id: str) -> bool:
    return str(session_id or "").startswith(DM_SESSION_PREFIX)


_KEY_VALUE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*=\S")
_SNAKE = re.compile(r"\b[a-z0-9]+_[a-z0-9_]+\b")
# Internal "kind:value" labels ("foundational:light") -- no space after the colon.
_COLON_LABEL = re.compile(r"\b[a-z]+:[a-z_]+\b")


def machine_output_reason(text: str) -> str:
    """Log records and telemetry are not speech ("Code evolution outcome for
    mutation_id=DREAM:... accepted=False.. operator_key=...")."""
    raw = str(text or "")
    if "[" in raw or "]" in raw:
        return "machine_output:marker"
    if len(_KEY_VALUE.findall(raw)) >= 2:
        return "machine_output:key_value"
    if len(_SNAKE.findall(raw)) >= 2:
        return "machine_output:identifiers"
    if _COLON_LABEL.search(raw):
        return "machine_output:label"
    return ""


def scripted_reason(src: str, text: str, *, dm: bool = True) -> str:
    """'' when the reply may stand; otherwise why it is scripted."""
    reason = _scripted_reason(src, text, dm=dm)
    if reason and not reason.startswith("system_output_in_dm"):
        remember_blocked_script(text)
    return reason


def _scripted_reason(src: str, text: str, *, dm: bool = True) -> str:
    source = str(src or "").strip()
    low = str(text or "").strip().lower()
    if source in SCRIPTED_CONVERSATIONAL_SOURCES:
        return f"scripted_source:{source}"
    if _norm_line(text) in _BLOCKED_SCRIPT_LINES:
        return "laundered_script"
    if dm and source in SYSTEM_OUTPUT_SOURCES:
        return f"system_output_in_dm:{source}"
    for prefix in TEMPLATE_PREFIXES:
        if low.startswith(prefix):
            return "template"
    for fragment in TEMPLATE_FRAGMENTS:
        if fragment in low:
            return "template"
    spine = spine_reason(text)
    if spine:
        return spine
    return machine_output_reason(text)


# -- addressed pressure ------------------------------------------------------------

ADDRESS_GAIN_QUESTION = 0.35
ADDRESS_GAIN_STATEMENT = 0.20
DISCHARGE_ON_SPEECH = 0.15        # fraction left after she speaks in her own words
HALF_LIFE_S = 30 * 60.0
ARTICULATION_THRESHOLD = 0.30
CONFLUENCE_ENABLED = True          # FIX-A113; off only for a measured baseline
CONFLUENCE_FIRST = True            # FIX-A130; False restores generative-first, for the baseline
PRESSURE_CAP = 1.0

# Being addressed: called to act (A), to spend energy responding (N),
# something pending in time (T), another mind at the boundary (B).
ADDRESS_AXIS_PROFILE = {"X": 0.10, "T": 0.50, "N": 0.65, "B": 0.40, "A": 0.85}


class AddressedPressure:
    """Per-channel pressure to respond, living in systems['addressed_pressure'].

    The level is bookkeeping for decay and discharge; the force itself goes
    into her identity field through the WaveformPressurePump every time she
    is addressed, so it participates in her physics like any other pressure.
    """

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self._levels: Dict[str, Tuple[float, float]] = {}   # channel -> (level, at)
        self.injections = 0
        self.discharges = 0
        self.last_error = ""

    def level(self, channel: str) -> float:
        value, at = self._levels.get(channel, (0.0, self.clock()))
        elapsed = max(0.0, self.clock() - at)
        return value * math.pow(0.5, elapsed / HALF_LIFE_S)

    def _set(self, channel: str, value: float) -> float:
        value = max(0.0, min(PRESSURE_CAP, value))
        self._levels[channel] = (value, self.clock())
        return value

    def address(self, systems: Mapping[str, Any], channel: str, *,
                question: bool) -> float:
        gain = ADDRESS_GAIN_QUESTION if question else ADDRESS_GAIN_STATEMENT
        value = self._set(channel, self.level(channel) + gain)
        self._inject(systems, channel, value)
        return value

    def discharge(self, channel: str) -> float:
        self.discharges += 1
        return self._set(channel, self.level(channel) * DISCHARGE_ON_SPEECH)

    def _inject(self, systems: Mapping[str, Any], channel: str, value: float) -> bool:
        ifield = systems.get("identity_field") if isinstance(systems, Mapping) else None
        pump = systems.get("pressure_pump") if isinstance(systems, Mapping) else None
        if ifield is None or pump is None:
            return False
        try:
            from aurora_waveform_pressure import PressureDisturbance
            pump.inject(
                PressureDisturbance(
                    source=f"addressed:{channel}",
                    axis_amplitudes=dict(ADDRESS_AXIS_PROFILE),
                    intensity=round(min(0.95, 0.25 + 0.6 * value), 4),
                    coupling_mode="full",
                ),
                ifield,
                qao=systems.get("quasiarch_observer"),
            )
        except Exception as exc:
            self.last_error = f"inject_failed: {type(exc).__name__}: {exc}"
            return False
        self.injections += 1
        return True

    def status(self) -> Dict[str, Any]:
        return {"channels": {ch: round(self.level(ch), 4) for ch in self._levels},
                "injections": self.injections, "discharges": self.discharges,
                "last_error": self.last_error}


def addressed_pressure(systems: Dict[str, Any]) -> AddressedPressure:
    existing = systems.get("addressed_pressure")
    if isinstance(existing, AddressedPressure):
        return existing
    created = AddressedPressure()
    systems["addressed_pressure"] = created
    return created


# -- articulation from her own stance -----------------------------------------------

_DEIXIS = {"you": "I", "your": "my", "yours": "mine", "yourself": "myself",
           "you're": "I'm", "u": "I", "ur": "my"}
_FUNCTION_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "about", "from", "by", "as", "is", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "have", "has", "had", "what", "what's",
    "whats", "how", "why", "when", "where", "who", "which", "can", "could",
    "would", "should", "will", "just", "any", "some", "all", "so", "very",
    "really", "it", "this", "that", "these", "those", "there", "here", "lately",
    "today", "now", "hey", "hi", "hello",
})
_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*")


def _tokens(text: str) -> List[str]:
    return _TOKEN.findall(str(text or ""))


def _relational_form(systems: Mapping[str, Any]) -> Dict[str, Any]:
    pipeline = dict(systems.get("_last_pipeline_state") or {}) if isinstance(systems, Mapping) else {}
    semantic = dict(pipeline.get("constraint_semantic_state") or {})
    return dict(semantic.get("relational_form") or {})


def _content_words(span: str, *, limit: int = 3) -> List[str]:
    words = []
    for tok in _tokens(span):
        low = tok.lower()
        mapped = _DEIXIS.get(low)
        if mapped is not None:
            continue                              # deixis handled separately
        if low in _FUNCTION_WORDS or len(low) < 3:
            continue
        words.append(low)
    return list(dict.fromkeys(words))[:limit]


def stance_seed(form: Mapping[str, Any]) -> Tuple[str, List[str]]:
    """Re-centre the relation she was addressed with on herself.

    "Do you like music?"  -> ("I; like; music", ["music"])
    "What's your favorite color?" -> ("I; favorite; color", ["favorite", "color"])
    Returns ("", []) when there is no relation she can stand in.
    """
    subject = str(form.get("subject") or "")
    relation = str(form.get("relation") or "")
    obj = " ".join(str(form.get(k) or "") for k in ("obj", "complement"))
    subject_low = [t.lower() for t in _tokens(subject)]
    obj_low = [t.lower() for t in _tokens(obj)]
    addressed_to_her = bool({"you", "your", "yours", "yourself", "u", "ur"} &
                            set(subject_low + obj_low))
    relation_words = _content_words(relation, limit=1)
    focus = _content_words(obj, limit=3) or _content_words(subject, limit=2)
    if not focus and not relation_words:
        return "", []
    head = "I" if addressed_to_her else (focus[0] if focus else "")
    parts = [head] + relation_words + [w for w in focus if w != head]
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return "", focus
    return "; ".join(parts), focus


def _echo_ratio(text: str, heard: str) -> float:
    heard_set = {t.lower() for t in _tokens(heard)}
    # FIX-A133: a letter the speaker did not say is something new ("c comes after
    # b" answers "what comes after b?"); "I" is perspective, not content.
    said = [t.lower() for t in _tokens(text)
            if len(t) >= 3 or (len(t) == 1 and t.lower() != "i" and t.lower() not in heard_set)]
    if not said:
        return 1.0
    return sum(1 for t in said if t in heard_set) / len(said)


def parrot_reason(text: str, heard: str) -> str:
    """'echo' when the reply is mostly the speaker's own words handed back."""
    said = [t.lower() for t in _tokens(text)]
    content = [t for t in said if len(t) >= 3]
    if len(content) < 2:
        return ""
    heard_low = " ".join(t.lower() for t in _tokens(heard))
    ratio = _echo_ratio(text, heard)
    if ratio >= 0.8 and (len(content) >= 4 or " ".join(said) in heard_low):
        return "echo"
    return ""


def articulation_rejection(text: str, heard: str) -> str:
    """'' when the articulation may stand; otherwise why not."""
    out = str(text or "").strip()
    if not out:
        return "empty"
    low = out.lower()
    if "[" in out or "]" in out:
        return "internal_marker"
    if any(tok.lower() in INTERNAL_LABELS for tok in _tokens(out)):
        return "internal_label"
    if scripted_reason("pressure_articulation", out, dm=True):
        return "template"
    said = [t.lower() for t in _tokens(out)]
    if len(said) < 2:
        return "too_thin"
    # Parroting: nearly everything she "said" is the speaker's own words, and
    # it is long enough that it cannot be a short re-centred stance.
    heard_low = " ".join(t.lower() for t in _tokens(heard))
    out_joined = " ".join(said)
    if _echo_ratio(out, heard) >= 0.8 and (len(said) >= 4 or out_joined in heard_low):
        return "echo"
    return ""


def articulate_from_pressure(systems: Dict[str, Any], heard: str, pressure: float, *,
                             tone: str = "curious",
                             render: Optional[Callable[..., str]] = None) -> Tuple[str, str]:
    """(text, reason).  text is her own articulation or ''."""
    form = _relational_form(systems)
    seed, focus = stance_seed(form)
    if isinstance(systems, dict):
        systems["_last_articulation_seed"] = seed
    if not seed:
        return "", "no_stance"
    if render is None:
        import sys
        aurora_mod = sys.modules.get("aurora")
        render = getattr(aurora_mod, "_render_runtime_intent", None) if aurora_mod else None
        if render is None:
            return "", "no_renderer"
    try:
        out = str(render(systems, seed, emotion_tone=str(tone or "curious"),
                         certainty=round(min(0.9, 0.35 + 0.5 * float(pressure)), 4),
                         supporting_concepts=list(focus)) or "").strip()
    except Exception as exc:
        return "", f"render_failed:{type(exc).__name__}"
    why = articulation_rejection(out, heard)
    if why:
        return "", why
    return out, ""


# -- the gate ------------------------------------------------------------------------

def _is_question(systems: Mapping[str, Any], heard: str) -> bool:
    form = _relational_form(systems)
    if "question" in form:
        return bool(form.get("question"))
    return str(heard or "").strip().endswith("?")


def own_composition(systems: Dict[str, Any], heard: str) -> str:
    """Her composer's draft for this turn, if it may stand as her reply."""
    cand = dict((systems or {}).get("_turn_composer_candidate") or {})
    text = str(cand.get("text") or "").strip()
    if not text or str(cand.get("heard") or "").strip() != str(heard or "").strip():
        return ""
    if scripted_reason("composer_unified", text) or parrot_reason(text, heard):
        return ""
    if articulation_rejection(text, heard):
        return ""
    heard_words = set(_content_words(heard, limit=12))
    if not heard_words & set(_content_words(text, limit=12)):
        return ""                              # does not connect to what was said
    return text


def _confluent_reply(systems: Dict[str, Any], resp: Any, heard: str, channel: str,
                     level: float, record: Dict[str, Any], pressure: Any) -> Any:
    """The confluence's reply for this turn, or None when it has nothing."""
    confluent, conf_record = "", {}
    try:
        from aurora_internal.aurora_confluence import compose, put_on_grammar_trace
        confluent, conf_record = compose(systems, heard, session_id=channel)
        systems["_last_confluence"] = conf_record
    except Exception as exc:
        record["confluence_error"] = f"{type(exc).__name__}: {exc}"[:160]
        return None
    if not confluent:
        record["confluence"] = str(conf_record.get("why") or "")
        return None
    pressure.discharge(channel)
    try:
        put_on_grammar_trace(systems, conf_record)
    except Exception:
        pass
    record.update({"outcome": "confluence", "src": "confluence",
                   "abilities": list(dict(conf_record.get("how") or {}).get("abilities") or [])[:5]})
    systems["_last_voice_gate"] = record
    tone = str(getattr(resp, "emotional_tone", "") or "curious")
    if tone in ("self-aware", "informative"):
        tone = "curious"
    return SimpleNamespace(content=confluent, emotional_tone=tone,
                           confidence=round(min(0.9, 0.3 + 0.5 * level), 4),
                           src="confluence")


def apply_voice_gate(systems: Dict[str, Any], resp: Any, heard: str, *,
                     session_id: str = "",
                     render: Optional[Callable[..., str]] = None) -> Any:
    """Return the reply that may leave this turn.  Never a script."""
    if not isinstance(systems, dict) or not str(heard or "").strip():
        return resp
    channel = str(session_id or "default")
    dm = is_dm_session(channel)
    pressure = addressed_pressure(systems)
    level = pressure.address(systems, channel, question=_is_question(systems, heard))

    text = str(getattr(resp, "content", "") or "").strip()
    src = str(getattr(resp, "src", "") or "")
    reason = scripted_reason(src, text, dm=dm) if text else "silent"
    # Parroting is not her voice from ANY source.  The retired baseline floor
    # used to catch input echo (by replacing it with a template); with the
    # templates gone, the gate has to catch it itself.
    if not reason and parrot_reason(text, heard):
        reason = "echo"
    record: Dict[str, Any] = {"channel": channel, "pressure": round(level, 4),
                              "original_src": src, "original_text": text[:200],
                              "at": time.time()}
    if isinstance(systems, dict):
        systems["_last_articulation_seed"] = ""

    # FIX-A130: one speech path.  The confluence composes first whenever she is
    # moved to speak -- from everything that touched the turn, including what
    # she has learned.  The reasoning pipeline's reply stands only when the
    # confluence has nothing to say (or she is not moved to speak), so a reply
    # that merely passes the checks no longer pre-empts it.
    # Pressure decides WHETHER she speaks, not what a reply that is already
    # going out is made of, so a standing reply needs no threshold here.
    tried_first = False
    if reason:
        record["blocked"] = reason
    composed = own_composition(systems, heard) if reason else ""
    # She would speak if the reply stands, if her composer has a draft, or if
    # she is moved to speak; in each case the confluence composes it first.
    if CONFLUENCE_FIRST and CONFLUENCE_ENABLED and (
            not reason or composed or level >= ARTICULATION_THRESHOLD):
        tried_first = True
        first = _confluent_reply(systems, resp, heard, channel, level, record, pressure)
        if first is not None:
            return first

    if not reason:
        pressure.discharge(channel)
        record.update({"outcome": "own_voice", "src": src})
        systems["_last_voice_gate"] = record
        return resp

    record["blocked"] = reason
    # Her composer's own draft for this turn (2026-11-08): the arbitration
    # graded it against the scripted candidate that was just blocked.  Same
    # checks as any reply, and it must connect to what was said.  It speaks
    # when the confluence had nothing (or, with CONFLUENCE_FIRST off, before it).
    if composed:
        pressure.discharge(channel)
        record.update({"outcome": "own_composition", "src": "composer_unified"})
        systems["_last_voice_gate"] = record
        cand = dict(systems.get("_turn_composer_candidate") or {})
        return SimpleNamespace(content=composed,
                               emotional_tone=str(cand.get("tone") or getattr(resp, "emotional_tone", "") or "curious"),
                               confidence=round(float(cand.get("confidence", 0.5) or 0.5), 4),
                               src="composer_unified")
    # FIX-A113: the confluence -- every system that ran on this turn feeds
    # what she says, and her live abilities decide how.  Same pressure
    # condition as articulation: being addressed is what moves her to speak.
    # (When it already ran above and had nothing, it is not run twice.)
    if level >= ARTICULATION_THRESHOLD and CONFLUENCE_ENABLED and not tried_first:
        second = _confluent_reply(systems, resp, heard, channel, level, record, pressure)
        if second is not None:
            return second
    articulated, why = ("", "below_threshold")
    if level >= ARTICULATION_THRESHOLD:
        articulated, why = articulate_from_pressure(
            systems, heard, level,
            tone=str(getattr(resp, "emotional_tone", "") or "curious"), render=render)
    if articulated:
        pressure.discharge(channel)
        record.update({"outcome": "pressure_articulation", "src": "pressure_articulation"})
        systems["_last_voice_gate"] = record
        # Downstream relabels "self-aware" -> src "identity" and confident
        # "informative" -> src "search"; her articulation is neither.
        tone = str(getattr(resp, "emotional_tone", "") or "curious")
        if tone in ("self-aware", "informative"):
            tone = "curious"
        return SimpleNamespace(content=articulated,
                               emotional_tone=tone,
                               confidence=round(min(0.9, 0.3 + 0.5 * level), 4),
                               src="pressure_articulation")

    record.update({"outcome": "silence", "articulation": why})
    systems["_last_voice_gate"] = record
    return SimpleNamespace(content="",
                           emotional_tone=str(getattr(resp, "emotional_tone", "") or "neutral"),
                           confidence=0.0, src="silence")


# -- keep the turn's audit trace truthful -------------------------------------------

def record_gate_in_trace(systems: Mapping[str, Any], original: Any, gated: Any,
                         user_text: str) -> bool:
    """The articulation trace (<state_dir>/last_articulation_trace.json) is
    written before the gate runs.  When the gate changes what leaves, rewrite
    final_delivered to what was actually said, and keep the blocked original
    beside it so the audit shows both."""
    import json
    from pathlib import Path
    if original is gated:
        return False
    try:
        state_dir = (systems.get("state_dir") if isinstance(systems, Mapping) else None) or "aurora_state"
        path = Path(str(state_dir)) / "last_articulation_trace.json"
        trace: Dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8") or "{}")
                trace = loaded if isinstance(loaded, dict) else {}
            except Exception:
                trace = {}
        prior = dict(trace.get("final_delivered") or {})
        gate = dict(systems.get("_last_voice_gate") or {}) if isinstance(systems, Mapping) else {}
        trace["final_delivered"] = {
            **prior,
            "user_text": str(user_text or prior.get("user_text", "")),
            "delivered_text": str(getattr(gated, "content", "") or ""),
            "source": str(getattr(gated, "src", "") or ""),
            "confidence": float(getattr(gated, "confidence", 0.0) or 0.0),
            "timestamp": time.time(),
            "voice_gate": {
                "blocked_text": str(getattr(original, "content", "") or ""),
                "blocked_source": str(getattr(original, "src", "") or ""),
                "blocked_reason": str(gate.get("blocked", "") or ""),
                "outcome": str(gate.get("outcome", "") or ""),
                "pressure": gate.get("pressure"),
                "articulation": str(gate.get("articulation", "") or ""),
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace, indent=2, ensure_ascii=True), encoding="utf-8")
        return True
    except Exception:
        return False
