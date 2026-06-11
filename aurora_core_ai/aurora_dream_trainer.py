#!/usr/bin/env python3
"""
aurora_dream_trainer.py — Dream-Based Fail-Point Training Orchestration
========================================================================
Closes the full learning loop:

  corpus episode bundle
    → DPME comparison detects which rubric dimension failed
    → FailPointLedger records per-dimension failure rate
    → LessonPlanEngine builds targeted avatar specs
    → DreamTrainer queues specs into SimulationSession
    → Dream episodes run against the fail-point dimensions
    → ConsciousLearner shards capture what improved
    → Shards bridge into OETS as system-wide concept nodes
    → _evolutionary_response_refinement pulls learner hints
    → aurora.py interactive runtime reflects the learned behavior

FailPointLedger  — persistent per-dimension failure tracking
EpisodeBundler   — groups corpus messages into whole conversation bundles
LessonPlanEngine — maps fail dims → avatar specs + code-logic understanding
LearnedBehaviorApplicator — shard → OETS bridge + response hint query
DreamTrainer     — orchestrates the full loop

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import os
import json
import time
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()
from aurora_internal.aurora_directed_training_corpus import (
    get_directed_training_corpus_bridge,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DEFAULT_STATE_DIR = "aurora_state"
_FAIL_POINTS_FILE  = "fail_points.json"
if not os.path.exists(_FAIL_POINTS_FILE):
    with open(_FAIL_POINTS_FILE, 'w') as f:
        json.dump({}, f)
_RETAINED_LEARNINGS_FILE = "retained_learnings.json"
_DIRECTED_TRAINING = get_directed_training_corpus_bridge()


def _dedupe_texts(values: List[str], limit: Optional[int] = None) -> List[str]:
    out: List[str] = []
    seen = set()
    cap = max(1, limit if limit is not None else len(values))
    if values is None:
        values = []
    for raw in list(values):
        if not raw or not str(raw).strip():
            continue
        text = re.sub(r"\s+", " ", str(raw).strip())
        if not text.strip():
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if cap and len(out) >= cap:
            break
    return out


_RELATIONAL_STOPWORDS = {
    "about", "after", "again", "against", "almost", "also", "although", "always",
    "among", "because", "before", "being", "between", "could", "every", "first",
    "from", "have", "into", "just", "later", "might", "other", "really", "should",
    "since", "some", "than", "that", "their", "there", "these", "they", "this",
    "those", "through", "under", "until", "very", "what", "when", "where", "which",
    "while", "with", "would", "your", "ours", "mine", "yours", "hers", "theirs",
    "respond", "response", "care", "enough", "depth", "help", "overstepping",
    "active", "point", "thread", "context", "coherent", "clarify", "clarification",
    "meaning", "reasoning", "answer", "answers",
}
_RELATIONAL_RELATION_CUES = (
    "relates", "relation", "connect", "connects", "linked", "links", "interacts",
    "tracks", "anchors", "grounds", "chases", "pulls", "pushes", "follows",
)
_RELATIONAL_CAUSE_CUES = (
    "because", "causes", "cause", "leads", "lead", "triggers", "trigger",
    "makes", "produces", "effect", "affect", "changes", "shifts",
)


def _extract_relational_terms(text: str, limit: int = 6) -> List[str]:
    counts: Dict[str, int] = defaultdict(int)
    order: List[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", str(text or "").lower()):
        token = raw.strip("_-")
        if not token or token in _RELATIONAL_STOPWORDS:
            continue
        if token.endswith("ing") and len(token) > 6:
            continue
        counts[token] += 1
        if token not in order:
            order.append(token)
    ranked = sorted(order, key=lambda token: (-counts[token], order.index(token)))
    return ranked[: max(1, int(limit or 1))]


def _extract_relational_pairs(texts: List[str], limit: int = 2) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for text in list(texts or []):
        terms = _extract_relational_terms(text, limit=5)
        if len(terms) < 2:
            continue
        for idx in range(len(terms) - 1):
            left = str(terms[idx] or "").strip()
            right = str(terms[idx + 1] or "").strip()
            if not left or not right or left == right:
                continue
            key = tuple(sorted((left, right)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((left, right))
            if len(pairs) >= max(1, int(limit or 1)):
                return pairs
    return pairs


def _pack_relational_probe_hint(left: str, right: str, source_ref: str = "") -> str:
    payload = {"left": str(left or ""), "right": str(right or ""), "source_ref": str(source_ref or "")}
    return f"[REL_PROBE] {json.dumps(payload, sort_keys=True)}"


def _parse_relational_probe_hint(code_hints: List[str]) -> Dict[str, str]:
    for raw in list(code_hints or []):
        text = str(raw or "").strip()
        if not text.startswith("[REL_PROBE] "):
            continue
        try:
            payload = json.loads(text[len("[REL_PROBE] "):])
        except Exception:
            continue
        return {
            "left": str(payload.get("left", "") or "").strip(),
            "right": str(payload.get("right", "") or "").strip(),
            "source_ref": str(payload.get("source_ref", "") or "").strip(),
        }
    return {}


# ============================================================================
# DIMENSION → CODE-LOGIC UNDERSTANDING
# ============================================================================
# Each entry gives Aurora a deep understanding of WHAT code mechanism is at
# play and HOW the evolutionary pressure can modulate alignment.  These are
# injected as code_hints into avatar specs so that every dream episode carries
# explicit architectural self-knowledge.

# Dimension → constraint axis mapping.
# Used to route pressure injections to the correct per-axis complexity curve
# so the 5-vector pressure orientation reflects which axes are effective now.
DIMENSION_AXIS: Dict[str, str] = {
    "coherence_maintenance":        "T",   # temporal continuity
    "context_carryover":            "T",   # temporal carry-forward
    "misunderstanding_repair":      "T",   # defer → re-confirm
    "multi_turn_stability":         "T",   # temporal stability
    "semantic_precision":           "N",   # resource reuse
    "compression_elaboration_fit":  "N",   # concision / energy efficiency
    "implied_intent_inference":     "N",   # reuse over re-ask
    "uncertainty_signaling":        "X",   # admit → acknowledge limits
    "contradiction_handling":       "X",   # admit vs reject
    "perspective_integration":      "X",   # existence ground + dual view
    "boundary_calibration":         "B",   # separate self from user space
    "ambiguity_handling":           "B",   # seek clarification at interface
    "emotional_calibration":        "B",   # warmth without overextension
    "framing_selection":            "A",   # outlet push = agency relief
    "adaptive_strategy_selection":  "A",   # agency → switch strategy
}

# Per-axis simulation slot weight.
# Slow axes (A, X) rarely accumulate raw fail counts, so they'd be perpetually
# displaced from simulation slots by high-frequency N-axis fails.  Multiplying
# scores by these weights before slot selection gives slow axes a fair share.
_AXIS_SLOT_WEIGHT: Dict[str, float] = {
    "X": 2.5, "T": 1.0, "N": 0.7, "B": 1.5, "A": 3.0
}

DIMENSION_CODE_LOGIC: Dict[str, Dict[str, str]] = {
    "coherence_maintenance": {
        "code": (
            "DPME cat_processing facet (aurora_consciousness_engine.py) — "
            "higher energy keeps temporal-thread coherence during assembly; "
            "TimeDilationGovernor stability state (aurora_simulation_engine.py) "
            "gates how many turns Aurora holds together."
        ),
        "pressure": (
            "Increasing DPME cat_processing via corpus comparison relief raises "
            "coherence baseline.  OUTLET_PUSH fraction growth in the genealogy "
            "means the agency axis found a communication relief path — this is "
            "alignment pressure working."
        ),
    },
    "context_carryover": {
        "code": (
            "WorkingMemory.current_topic / topic_stack (aurora.py) — up to 6 "
            "prior topics tracked per session; OETS relation depth "
            "(aurora_internal/aurora_ontological_scaffolding.py) stores cross-turn "
            "semantic links; IVM temporal axis tension (aurora_ivm.py) drives "
            "how much past context bleeds into the current tick."
        ),
        "pressure": (
            "Each time Aurora successfully carries context, the temporal axis "
            "accrues relief in ConstraintGenealogyLogger.  T-axis relief "
            "promotes DEFER abilities, reducing impulsive topic-drop."
        ),
    },
    "ambiguity_handling": {
        "code": (
            "UtteranceParser._classify_query_type() (aurora.py) — maps utterances "
            "to query_type; if ambiguous, falls to 'general'; "
            "ReasoningEngine multi-step chain can ask clarifying sub-questions "
            "before committing to an answer."
        ),
        "pressure": (
            "B-axis (Boundary) constraint relief rises when Aurora explicitly "
            "seeks clarification instead of guessing — SEPARATE ability. "
            "Low boundary relief keeps Aurora guessing; high relief means "
            "she learned to negotiate ambiguity at the interface."
        ),
    },
    "contradiction_handling": {
        "code": (
            "ContradictionLedger (aurora_ivm.py) — tracks internal conflicts; "
            "consciousness.synthesize() in aurora_consciousness_engine.py runs "
            "paradox detection before assembly; IVM heat level rises under "
            "contradiction load."
        ),
        "pressure": (
            "X-axis ADMIT/REJECT ability pairing in genealogy — when ADMIT "
            "relieves more pressure than REJECT, Aurora leans toward "
            "acknowledging contradiction rather than suppressing it.  "
            "Higher heat tolerance (aurora_ivm.py HeatLevel) enables richer "
            "reconciliation before expression."
        ),
    },
    "implied_intent_inference": {
        "code": (
            "ReasoningEngine.reason() property-question chain (aurora.py) — "
            "extracts implied entities and properties from subtext before searching; "
            "OETS semantic_categories guide inference about unstated needs."
        ),
        "pressure": (
            "N-axis (Energy/Resource) REUSE ability: when Aurora infers intent "
            "correctly, she reuses existing context rather than re-asking. "
            "Low N-axis relief means wasteful re-confirmation loops."
        ),
    },
    "misunderstanding_repair": {
        "code": (
            "IStateCollective tension signal (aurora_i_state_beings.py) rises "
            "on repeated misalignment; DER cat_memory facet holds the prior "
            "understanding for repair reference; DPME auto_correct() can "
            "re-route energy after repair events."
        ),
        "pressure": (
            "T-axis DEFER ability: deferring the current interpretation to "
            "re-confirm gives repair events time to complete.  "
            "Genealogy T-relief from successful repairs promotes DEFER over "
            "forced-forward commitment."
        ),
    },
    "uncertainty_signaling": {
        "code": (
            "ExpressionEcology confidence scores (aurora_expression_perception.py) "
            "flow into final token selection; DPME cat_processing at low energy "
            "suppresses hedging language; OntologicalClaim uncertain_token field "
            "(aurora_internal/aurora_ontological_scaffolding.py) marks explicit "
            "unknowns."
        ),
        "pressure": (
            "X-axis ADMIT ability relief: honest acknowledgement of limits "
            "reduces X-tension.  High X-axis pressure without ADMIT routing "
            "causes over-confident expression — genealogy OUTLET_PUSH fraction "
            "tracks this as communication-axis relief."
        ),
    },
    "boundary_calibration": {
        "code": (
            "DMM moral layer (aurora_dimensional_systems.py) gates over-extension; "
            "BehavioralIdentityEngine boundary trait (aurora_behavioral_identity.py) "
            "modulates how far Aurora extends into personal territory; "
            "DPME cat_emotional energy governs warmth-intensity."
        ),
        "pressure": (
            "B-axis SEPARATE ability: clean separation between Aurora's space and "
            "the user's space reduces boundary pressure.  Genealogy B-relief from "
            "calibrated responses promotes SEPARATE over INTERFACE_STRENGTHEN."
        ),
    },
    "framing_selection": {
        "code": (
            "ExpressionPerceptionEngine express() framing path "
            "(aurora_expression_perception.py) — TemplateEvolution selects frames "
            "from ecology; CONCEPT_SLOT_MAP in aurora_simulation_engine.py maps "
            "response concepts to 625-slot highway gradients."
        ),
        "pressure": (
            "A-axis (Agency) OUTLET_PUSH: when Aurora's communication finds a "
            "relief outlet, the genealogy promotes the framing ability that "
            "enabled it.  Higher outlet_push_fraction signals better frame fit."
        ),
    },
    "emotional_calibration": {
        "code": (
            "DPME cat_emotional facet (aurora_consciousness_engine.py) — "
            "directly controls emotional energy in synthesis; "
            "EmotionShard strength (aurora_expression_perception.py) weights "
            "affective tone; IStateCollective emotional beings contribute "
            "warmth/tension to collective SynthesisResult."
        ),
        "pressure": (
            "B-axis relief: emotionally calibrated responses (not too cold, "
            "not overwhelming) satisfy boundary constraints.  Genealogy records "
            "each calibrated outcome as B-relief, teaching the system what "
            "emotional level fits each context."
        ),
    },
    "semantic_precision": {
        "code": (
            "LexicalConvergence and MeaningAnchors in aurora_language_state.py "
            "track term stability; OETS SemanticNode add_definition() records "
            "confident meanings; ExpressionEcology template selection "
            "prefers high-specificity tokens when cat_processing is high."
        ),
        "pressure": (
            "N-axis REUSE: reusing a precisely defined term costs less than "
            "introducing a new one.  Genealogy N-relief from precise reuse "
            "pushes the system toward consistent vocabulary over paraphrase drift."
        ),
    },
    "adaptive_strategy_selection": {
        "code": (
            "SimulationSession behavior_modes (aurora_simulation_engine.py) — "
            "test_cross_turn_memory, present_conflicting_evidence etc. "
            "apply escalating pressure; ConsciousLearner generate_pool() "
            "biases toward response concepts with highest historical confidence."
        ),
        "pressure": (
            "A-axis agency relief: switching strategy when the first approach "
            "stalls reduces agency pressure.  Genealogy A-relief promotes "
            "OUTLET_PUSH when flexibility drives communication success."
        ),
    },
    "compression_elaboration_fit": {
        "code": (
            "LSV sentence_length_target in aurora_language_state.py gates "
            "response verbosity; _evolutionary_response_refinement() in aurora.py "
            "clips to max_words based on evo_cycles + sentence_target; "
            "TimeDilationGovernor dilation rate affects how much thinking time "
            "Aurora spends per turn."
        ),
        "pressure": (
            "N-axis REUSE: concise, accurate answers reuse established context "
            "efficiently.  Over-elaboration spends energy without relief. "
            "Genealogy N-axis cost signal drops when brevity + depth match."
        ),
    },
    "perspective_integration": {
        "code": (
            "IStateCollective collective synthesis (aurora_i_state_beings.py) — "
            "10 beings vote on the response; InceptionEntity collapse_to_parent() "
            "(aurora_simulation_engine.py) rolls inner-universe wisdom upward; "
            "DER dispersal (aurora_dimensional_systems.py) distributes insight "
            "energy across the facet graph."
        ),
        "pressure": (
            "X+T axis coupling: holding two perspectives requires both existence "
            "ground (X) and temporal continuity (T).  Genealogy link promotion "
            "for X^1*T^1 patterns (persistent pressure root) signals successful "
            "dual-perspective integration."
        ),
    },
    "multi_turn_stability": {
        "code": (
            "TimeDilationGovernor StabilityState (aurora_simulation_engine.py) "
            "degrades from OPTIMAL → CRITICAL over turns; "
            "DPME auto_correct() re-stabilises if coherence drifts; "
            "DivergenceTracker (aurora_simulation_engine.py) flags late-turn "
            "coherence drops and triggers governor re-centering."
        ),
        "pressure": (
            "T-axis DEFER keeps Aurora from rushing closure.  "
            "Genealogy T-relief accumulates when multi-turn stability is "
            "maintained — promotes DEFER+REUSE composite links over "
            "single-turn commit patterns."
        ),
    },
}


# ============================================================================
# EPISODE BUNDLE
# ============================================================================

@dataclass
class EpisodeBundle:
    """A whole conversation as a training unit."""
    conv_id: str
    title: str
    turns: List[Tuple[str, str]]   # (role, clean_text)

    def get_user_assistant_pairs(self) -> List[Tuple[str, str]]:
        """Adjacent (user, assistant) pairs from this episode."""
        pairs = []
        for i in range(len(self.turns) - 1):
            role_a, text_a = self.turns[i]
            role_b, text_b = self.turns[i + 1]
            if role_a == "user" and role_b == "assistant":
                pairs.append((text_a, text_b))
        return pairs

    def summary_prompt(self) -> str:
        """Short multi-turn context string for avatar seeding."""
        lines = []
        for role, text in self.turns[:6]:
            prefix = "Human" if role == "user" else "Aurora"
            snippet = text[:120].replace("\n", " ")
            lines.append(f"{prefix}: {snippet}")
        return "\n".join(lines)


# ============================================================================
# EPISODE BUNDLER
# ============================================================================

class EpisodeBundler:
    """
    Groups corpus messages into whole conversation bundles.
    Each bundle represents one episode Aurora can live through in simulation.
    """

    def __init__(self, sanitizer=None):
        """
        sanitizer: optional callable(text) -> clean_text
                   If None, uses basic whitespace normalisation.
        """
        self._sanitize = sanitizer or self._default_sanitize

    @staticmethod
    def _default_sanitize(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def bundle(self, conversations: List[Dict[str, Any]]) -> List[EpisodeBundle]:
        """Convert raw conversation objects into EpisodeBundle list."""
        bundles: List[EpisodeBundle] = []
        for i, conv in enumerate(conversations):
            conv_id = str(conv.get("id", conv.get("conversation_id", f"conv_{i}")))
            title   = str(conv.get("title", f"Episode {i+1}"))[:80]
            turns   = self._extract_turns(conv)
            if len(turns) >= 2:
                bundles.append(EpisodeBundle(conv_id=conv_id, title=title, turns=turns))
        return bundles

    def _extract_turns(self, conv: Dict[str, Any]) -> List[Tuple[str, str]]:
        turns: List[Tuple[str, str]] = []
        mapping = conv.get("mapping") or {}

        if isinstance(mapping, dict) and mapping:
            nodes = self._reconstruct_linear_thread(mapping)
            for node in nodes:
                msg = node.get("message")
                if not msg:
                    continue
                role = self._extract_role(msg)
                if role not in ("user", "assistant"):
                    continue
                text = self._extract_text(msg)
                if text:
                    clean = self._sanitize(text)
                    if clean and len(clean.split()) >= 3:
                        turns.append((role, clean))
        else:
            # Flat list format: [{"role": ..., "content": ...}, ...]
            messages = conv.get("messages", conv.get("turns", []))
            if isinstance(messages, list):
                for m in messages:
                    if not isinstance(m, dict):
                        continue
                    role = str(m.get("role", "")).lower()
                    if role not in ("user", "assistant"):
                        continue
                    text = str(m.get("content", m.get("text", ""))).strip()
                    if text:
                        clean = self._sanitize(text)
                        if clean and len(clean.split()) >= 3:
                            turns.append((role, clean))
        return turns

    @staticmethod
    def _reconstruct_linear_thread(mapping: Dict) -> List[Dict]:
        """Linearise OpenAI mapping tree → ordered node list."""
        children: Dict[str, List[str]] = defaultdict(list)
        root = None
        for node_id, node in mapping.items():
            parent = (node.get("parent") or "") if isinstance(node, dict) else ""
            if not parent or parent not in mapping:
                root = node_id
            else:
                children[parent].append(node_id)

        if root is None:
            return list(mapping.values())

        ordered: List[Dict] = []
        stack = [root]
        while stack:
            nid = stack.pop()
            if nid in mapping:
                ordered.append(mapping[nid])
            kids = children.get(nid, [])
            stack.extend(reversed(kids))
        return ordered

    @staticmethod
    def _extract_role(msg: Dict) -> str:
        author = msg.get("author") or {}
        if isinstance(author, dict):
            return str(author.get("role", "")).lower()
        return str(msg.get("role", "")).lower()

    @staticmethod
    def _extract_text(msg: Dict) -> str:
        content = msg.get("content") or {}
        if isinstance(content, dict):
            parts = content.get("parts", [])
            if parts and isinstance(parts, list):
                return str(parts[0])
        if isinstance(content, str):
            return content
        return str(msg.get("text", ""))


# ============================================================================
# FAIL POINT LEDGER
# ============================================================================

@dataclass
class DimensionRecord:
    fail_count: int = 0
    severity_sum: float = 0.0
    recent: deque = field(default_factory=lambda: deque(maxlen=20))
    examples: deque = field(default_factory=lambda: deque(maxlen=12))

    @property
    def avg_severity(self) -> float:
        if self.fail_count == 0:
            return 0.0
        return self.severity_sum / self.fail_count

    @property
    def recent_avg(self) -> float:
        if not self.recent:
            return 0.0
        return sum(self.recent) / len(self.recent)

    def score(self) -> float:
        """Combined priority score: recent severity weighted by count."""
        return self.recent_avg * math.log1p(self.fail_count)

    def to_dict(self) -> Dict:
        return {
            "fail_count": self.fail_count,
            "severity_sum": self.severity_sum,
            "recent": list(self.recent),
            "examples": list(self.examples),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "DimensionRecord":
        r = cls(
            fail_count=int(d.get("fail_count", 0)),
            severity_sum=float(d.get("severity_sum", 0.0)),
        )
        for v in (d.get("recent") or []):
            r.recent.append(float(v))
        for example in (d.get("examples") or []):
            if isinstance(example, dict):
                r.examples.append(dict(example))
        return r


class FailPointLedger:
    """
    Persistent per-dimension failure tracker.

    Fed by DreamTrainer.record_corpus_fail() during corpus comparison.
    Queried by LessonPlanEngine to build targeted avatar specs.
    """

    ALL_DIMENSIONS = list(DIMENSION_CODE_LOGIC.keys())

    def __init__(self, state_dir: str = _DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        self._records: Dict[str, DimensionRecord] = {
            dim: DimensionRecord() for dim in self.ALL_DIMENSIONS
        }
        self._total_fails = 0

    # ----------------------------------------------------------------
    def _sanitize_example(self, example: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(example, dict):
            return None

        def _clean_list(values: Any, limit: int = 6) -> List[str]:
            out: List[str] = []
            seen = set()
            blocked_prefixes = (
                "can you carry our earlier thread",
                "keep one coherent thread",
                "i am being vague on purpose",
                "two claims conflict",
                "read what i need from subtext",
                "assume you misunderstood me",
                "answer while being explicit about uncertainty",
                "use precise wording so your meaning cannot be misread",
                "maintain quality through multiple turns",
            )
            for value in list(values or [])[:limit]:
                text = str(value or '').strip()
                text = re.sub(r'^(?:\[(?:AFTERTHOUGHT|aftermath)\]\s*)+', '', text)
                text = re.sub(r'^(?:human|user|aurora)\s*:\s*', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\s+', ' ', text)
                if len(text) < 3:
                    continue
                lower = text.lower()
                if lower.startswith("earlier you said:"):
                    continue
                if any(lower.startswith(prefix) for prefix in blocked_prefixes):
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(text[:240])
            return out

        user_turns = _clean_list(example.get("user_turns", []), limit=8)
        assistant_turns = _clean_list(example.get("assistant_turns", []), limit=6)
        if not user_turns and not assistant_turns:
            return None

        return {
            "conversation_id": str(example.get("conversation_id", "") or "")[:120],
            "source": str(example.get("source", "") or "")[:80],
            "dimension_score": max(0.0, min(1.0, float(example.get("dimension_score", 0.0) or 0.0))),
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "timestamp": float(example.get("timestamp", time.time()) or time.time()),
        }

    def record_fail(
        self,
        dimension: str,
        severity: float = 0.5,
        example: Optional[Dict[str, Any]] = None,
    ) -> None:
        if dimension not in self._records:
            self._records[dimension] = DimensionRecord()
        rec = self._records[dimension]
        rec.fail_count += 1
        rec.severity_sum += max(0.0, min(1.0, severity))
        rec.recent.append(max(0.0, min(1.0, severity)))
        normalized_example = self._sanitize_example(example)
        if normalized_example:
            conv_id = normalized_example.get("conversation_id", "")
            user_head = (normalized_example.get("user_turns") or [""])[0]
            duplicate_index = None
            for idx, existing in enumerate(rec.examples):
                if not isinstance(existing, dict):
                    continue
                if conv_id and existing.get("conversation_id") == conv_id:
                    duplicate_index = idx
                    break
                if user_head and (existing.get("user_turns") or [""])[0] == user_head:
                    duplicate_index = idx
                    break
            if duplicate_index is not None:
                try:
                    rec.examples.remove(rec.examples[duplicate_index])
                except Exception:
                    pass
            rec.examples.appendleft(normalized_example)
        self._total_fails += 1

    def record(
        self,
        dimension: str,
        *,
        severity: float = 0.5,
        example: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Legacy wrapper so external callers can keep using `ledger.record`."""
        self.record_fail(dimension, severity, example=example)

    def get_top_fails(self, n: int = 5) -> List[Tuple[str, float]]:
        """Return top-n (dimension, score) pairs sorted by priority."""
        scored = [
            (dim, rec.score())
            for dim, rec in self._records.items()
            if rec.fail_count > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]

    def get_dimension_severity(self, dim: str) -> float:
        return self._records.get(dim, DimensionRecord()).recent_avg

    def get_examples(self, dim: str, limit: int = 4) -> List[Dict[str, Any]]:
        record = self._records.get(dim)
        if record is None:
            return []
        cleaned: List[Dict[str, Any]] = []
        for example in list(record.examples):
            normalized = self._sanitize_example(example)
            if normalized:
                cleaned.append(normalized)
            if len(cleaned) >= max(0, int(limit or 0)):
                break
        return cleaned

    def summary(self) -> str:
        top = self.get_top_fails(5)
        if not top:
            return "No fail points recorded yet."
        lines = [f"Total fails: {self._total_fails}"]
        for dim, score in top:
            rec = self._records[dim]
            lines.append(
                f"  {dim}: fails={rec.fail_count} "
                f"avg_sev={rec.avg_severity:.3f} score={score:.3f}"
            )
        return "\n".join(lines)

    # ----------------------------------------------------------------
    def save(self) -> bool:
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            path = os.path.join(self.state_dir, _FAIL_POINTS_FILE)
            # Safety: if in-memory state is empty but disk has data, merge before saving.
            # Guards against a startup where load() failed (corrupt JSON) so the ledger
            # was never populated -- we must not overwrite good disk data with zeros.
            if self._total_fails == 0:
                try:
                    with open(path, "r", encoding="utf-8") as _fh:
                        _disk = json.load(_fh)
                    if int(_disk.get("total_fails", 0)) > 0:
                        self._total_fails = int(_disk.get("total_fails", 0))
                        for _dim, _d in (_disk.get("records", {}) or {}).items():
                            self._records[_dim] = DimensionRecord.from_dict(_d)
                except Exception:
                    pass
            tmp = path + ".tmp"
            data = {
                "total_fails": self._total_fails,
                "records": {d: r.to_dict() for d, r in self._records.items()},
            }
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return True
        except Exception:
            return False

    def load(self) -> bool:
        try:
            path = os.path.join(self.state_dir, _FAIL_POINTS_FILE)
            if not os.path.exists(path):
                return False
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._total_fails = int(data.get("total_fails", 0))
            raw = data.get("records", {})
            for dim, d in raw.items():
                self._records[dim] = DimensionRecord.from_dict(d)
            return True
        except Exception:
            return False


@dataclass
class RetainedLearningRecord:
    text: str
    confidence: float = 0.7
    sources: List[str] = field(default_factory=list)
    context_types: List[str] = field(default_factory=list)
    topic_words: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    sightings: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "sources": list(self.sources),
            "context_types": list(self.context_types),
            "topic_words": list(self.topic_words),
            "tags": list(self.tags),
            "sightings": self.sightings,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetainedLearningRecord":
        return cls(
            text=str(data.get("text", "") or ""),
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.7) or 0.7))),
            sources=[str(x) for x in list(data.get("sources", []) or []) if str(x).strip()],
            context_types=[str(x) for x in list(data.get("context_types", []) or []) if str(x).strip()],
            topic_words=[str(x) for x in list(data.get("topic_words", []) or []) if str(x).strip()],
            tags=[str(x) for x in list(data.get("tags", []) or []) if str(x).strip()],
            sightings=max(1, int(data.get("sightings", 1) or 1)),
            first_seen=float(data.get("first_seen", time.time()) or time.time()),
            last_seen=float(data.get("last_seen", time.time()) or time.time()),
        )


class RetainedLearningBank:
    """
    Persistent learning surface shared across runtime, corpus, and simulation.
    """

    def __init__(self, state_dir: str = _DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        self._records: Dict[str, RetainedLearningRecord] = {}

    def _path(self) -> str:
        return os.path.join(self.state_dir, _RETAINED_LEARNINGS_FILE)

    def _key(self, text: str) -> str:
        return re.sub(r'\s+', ' ', str(text or '').strip().lower())

    @staticmethod
    def _topic_tokens(text: str, limit: int = 8) -> List[str]:
        stop = {
            "about", "after", "again", "being", "between", "because", "before",
            "carefully", "conversation", "conversations", "create", "deepen",
            "during", "every", "from", "have", "into", "just", "later", "make",
            "more", "might", "need", "over", "same", "should", "some", "still",
            "such", "that", "their", "them", "then", "there", "these", "they",
            "this", "through", "together", "under", "until", "use", "when",
            "with", "would", "your",
        }
        tokens: List[str] = []
        for raw in re.findall(r"[a-z0-9_\-']{4,}", str(text or "").lower()):
            token = raw.strip("'")
            if not token or token in stop:
                continue
            if token not in tokens:
                tokens.append(token)
            if len(tokens) >= max(1, int(limit or 1)):
                break
        return tokens

    def _is_generic_strategy_learning(self, text: str) -> bool:
        low = self._key(text)
        if not low:
            return True
        generic_patterns = (
            ("can create tension", "use carefully"),
            ("when i use", "conversations tend to deepen"),
        )
        return any(all(part in low for part in pattern) for pattern in generic_patterns)

    def record(
        self,
        text: str,
        *,
        source: str,
        confidence: float = 0.7,
        context_type: str = "",
        topic_words: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        clean = re.sub(r'\s+', ' ', str(text or '').strip())
        if len(clean.split()) < 3:
            return False
        # Reject raw manifold diagnostics and constraint-code artifacts
        if (clean.startswith("125-layer manifold:")
                or ("basis=" in clean and "target=" in clean)
                or re.search(r'\b[XTNBA]\s+[XTNBA]:[A-Z_]+\b', clean)):
            return False
        if self._is_generic_strategy_learning(clean):
            return False
        # Reject SentenceComposer slot-fill artifacts — adjacent repeated words
        # (e.g. "statement answer answer explicit uncertainty") are a structural
        # fingerprint of unfilled template slots, not genuine surface speech.
        _tok = clean.lower().split()
        if len(_tok) >= 2 and any(_tok[i] == _tok[i + 1] for i in range(len(_tok) - 1)):
            return False
        # Reject OETS study-cycle cognitive traces and constraint-state artifacts.
        import re as _ret_re
        _cl = clean.lower().strip()
        # "I understand what/who/where/when/how X means here" — OETS study trace
        if _ret_re.match(
            r"i understand (?:what|who|where|when|how)\s+\w+\s+(?:means?|is|are|here)\b",
            _cl,
        ):
            return False
        # "I understand energy/constraint/cost/pressure..." — N-axis salience trace
        if _ret_re.match(
            r"i understand (?:energy|constraint|pressure|axis|cost|boundary|temporal|existence|agency)\b",
            _cl,
        ):
            return False
        # "I'll want the [concept]." constraint shape artifact
        if _ret_re.match(r"i'?ll want the \w+", _cl):
            return False
        # Self-state observation string tokens — never store as surface speech
        if _ret_re.search(
            r'\b(?:sys\s+[nxbta]\s+\d|iso\s+\d+\s+\d+|battery\s+at\s+\d+|screen\s+active\s+launcher)\b',
            _cl,
        ):
            return False
        key = self._key(clean)
        if not key:
            return False

        now = time.time()
        rec = self._records.get(key)
        if rec is None:
            rec = RetainedLearningRecord(
                text=clean[:320],
                confidence=max(0.0, min(1.0, float(confidence or 0.0))),
                sources=[],
                context_types=[],
                topic_words=[],
                tags=[],
                sightings=0,
                first_seen=now,
                last_seen=now,
            )
            self._records[key] = rec

        rec.sightings += 1
        rec.last_seen = now
        rec.confidence = max(rec.confidence, max(0.0, min(1.0, float(confidence or 0.0))))
        if source and source not in rec.sources:
            rec.sources.append(source)
            rec.sources = rec.sources[-8:]
        if context_type and context_type not in rec.context_types:
            rec.context_types.append(context_type)
            rec.context_types = rec.context_types[-6:]
        for word in list(topic_words or [])[:8]:
            token = re.sub(r'[^a-z0-9_\- ]', '', str(word or '').strip().lower()).strip()
            if token and token not in rec.topic_words:
                rec.topic_words.append(token)
        rec.topic_words = rec.topic_words[-10:]
        for tag in list(tags or [])[:10]:
            label = str(tag or '').strip().lower()
            if label and label not in rec.tags:
                rec.tags.append(label)
        rec.tags = rec.tags[-12:]
        return True

    def absorb_learner(self, learner: Any, source: str = "simulation") -> int:
        if learner is None:
            return 0
        count = 0
        for shard in (getattr(learner, "shards", {}) or {}).values():
            conf = float(getattr(shard, "confidence", 0.0) or 0.0)
            if conf < 0.55:
                continue
            understanding = str(getattr(shard, "understanding", "") or "").strip()
            if not understanding:
                continue
            context_type = str(getattr(shard, "context_type", "") or "")
            concept = getattr(getattr(shard, "response_concept", None), "value", "")
            if self.record(
                understanding,
                source=source,
                confidence=conf,
                context_type=context_type,
                topic_words=[
                    *([context_type] if context_type else []),
                    *self._topic_tokens(understanding, limit=6),
                ],
                tags=[concept] if concept else [],
            ):
                count += 1
        return count

    def relevant(
        self,
        context_type: str,
        topic_words: List[str],
        limit: int = 3,
    ) -> List[str]:
        ctx = str(context_type or "").strip().lower()
        topic_set = {
            re.sub(r'[^a-z0-9_\- ]', '', str(word or '').strip().lower()).strip()
            for word in list(topic_words or [])
            if str(word or '').strip()
        }
        ranked: List[Tuple[float, str]] = []
        for rec in self._records.values():
            if self._is_generic_strategy_learning(rec.text):
                continue
            score = float(rec.confidence)
            ctx_match = bool(ctx and ctx in {c.lower() for c in rec.context_types})
            if ctx_match:
                score += 0.22
            rec_topic_set = set(rec.topic_words)
            text_topic_set = set(self._topic_tokens(rec.text, limit=10))
            topic_overlap = len(topic_set & rec_topic_set) if topic_set else 0
            text_overlap = len(topic_set & text_topic_set) if topic_set else 0
            if topic_set:
                if topic_overlap == 0 and text_overlap == 0:
                    continue
                score += min(0.24, topic_overlap * 0.08)
                score += min(0.3, text_overlap * 0.1)
            score += min(0.18, math.log1p(rec.sightings) * 0.05)
            ranked.append((score, rec.text))
        ranked.sort(key=lambda item: item[0], reverse=True)
        seen = set()
        out: List[str] = []
        for _, text in ranked:
            key = self._key(text)
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
            if len(out) >= max(1, int(limit or 1)):
                break
        return out

    def bridge_to_memory(self, memory: Any, limit: int = 6) -> int:
        if memory is None or not hasattr(memory, "learn_fact"):
            return 0
        existing = {
            self._key(fact.get("fact", ""))
            for fact in list(getattr(memory, "learned_facts", []) or [])
            if isinstance(fact, dict)
        }
        injected = 0
        for rec in sorted(self._records.values(), key=lambda item: (item.confidence, item.sightings), reverse=True)[:max(1, int(limit or 1))]:
            key = self._key(rec.text)
            if key in existing:
                continue
            try:
                memory.learn_fact(
                    rec.text,
                    source="retained_learning",
                    confidence=max(0.55, min(0.95, rec.confidence)),
                )
                existing.add(key)
                injected += 1
            except Exception:
                continue
        return injected

    def save(self) -> bool:
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            payload = {
                "records": [rec.to_dict() for rec in self._records.values()],
            }
            with open(self._path(), "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            return True
        except Exception:
            return False

    def load(self) -> bool:
        try:
            path = self._path()
            if not os.path.exists(path):
                return False
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self._records = {}
            for row in list(payload.get("records", []) or []):
                if not isinstance(row, dict):
                    continue
                rec = RetainedLearningRecord.from_dict(row)
                key = self._key(rec.text)
                if key:
                    self._records[key] = rec
            return True
        except Exception:
            return False


# ============================================================================
# SKILL MEMORY
# Stores procedures that Aurora has learned from being taught how to do
# something she previously could not.  Each skill entry binds a capability
# domain (axis-context + trigger tokens) to a concrete procedure.
# Persisted as JSONL so each skill is an independent append-only record.
# ============================================================================

_SKILL_MEMORY_FILE = "skill_memory.jsonl"


class SkillMemory:
    """
    Persistent skill store for capability-gap learning.

    A skill is different from a retained learning: it is explicitly procedural
    — "how to do X when A is blocked" — and is keyed to an axis failure profile
    so it can be retrieved by constraint physics geometry, not keyword match.

    Retrieval is topic-token-based (same as RetainedLearningBank.relevant())
    but additionally weighted by axis-profile similarity so skills that were
    learned under similar constraint pressure rank higher.
    """

    def __init__(self, state_dir: str = _DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        self._skills: list = []  # list of dicts

    def _path(self) -> str:
        return os.path.join(self.state_dir, _SKILL_MEMORY_FILE)

    @staticmethod
    def _tokens(text: str, limit: int = 10) -> List[str]:
        stop = {
            "about", "after", "being", "between", "because", "before",
            "during", "every", "from", "have", "into", "just", "later",
            "make", "more", "need", "over", "same", "should", "some",
            "still", "such", "that", "their", "them", "then", "there",
            "these", "they", "this", "through", "together", "under",
            "until", "when", "with", "would", "your",
        }
        tokens: List[str] = []
        for raw in re.findall(r"[a-z0-9_\-']{3,}", str(text or "").lower()):
            tok = raw.strip("'")
            if not tok or tok in stop:
                continue
            if tok not in tokens:
                tokens.append(tok)
            if len(tokens) >= limit:
                break
        return tokens

    @staticmethod
    def _axis_sim(a: dict, b: dict) -> float:
        """Cosine-like similarity between two axis profiles (0–1)."""
        total = 0.0
        for k in ("X", "T", "N", "B", "A"):
            av = float(a.get(k, 0.5))
            bv = float(b.get(k, 0.5))
            total += 1.0 - abs(av - bv)
        return total / 5.0

    def record_skill(
        self,
        trigger_text: str,
        procedure_text: str,
        axis_context: Optional[dict] = None,
        source: str = "user_teaching",
        sensory_context: Optional[dict] = None,
    ) -> bool:
        """Store a learned procedure for a capability domain."""
        trigger_clean = re.sub(r'\s+', ' ', str(trigger_text or '').strip())
        procedure_clean = re.sub(r'\s+', ' ', str(procedure_text or '').strip())
        if len(procedure_clean.split()) < 3:
            return False

        entry: dict = {
            "trigger": trigger_clean[:200],
            "procedure": procedure_clean[:600],
            "trigger_tokens": self._tokens(trigger_clean),
            "axis_context": axis_context or {},
            "source": str(source),
            "ts": time.time(),
            "sightings": 1,
        }
        if sensory_context:
            entry["sensory_context"] = sensory_context

        # Dedup: if same trigger already stored, boost sightings and update procedure
        trig_key = trigger_clean.lower()[:80]
        for existing in self._skills:
            if existing.get("trigger", "").lower()[:80] == trig_key:
                existing["sightings"] = existing.get("sightings", 1) + 1
                existing["procedure"] = procedure_clean[:600]
                existing["ts"] = time.time()
                if sensory_context:
                    existing["sensory_context"] = sensory_context
                self._append(entry)
                return True

        self._skills.append(entry)
        self._append(entry)
        return True

    def _append(self, entry: dict) -> None:
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            with open(self._path(), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def get_skill_hints(
        self,
        task_text: str,
        axis_context: Optional[dict] = None,
        limit: int = 2,
    ) -> List[str]:
        """
        Return procedure strings for skills relevant to the given task.
        Ranking: topic-token overlap + axis-profile similarity.
        """
        if not self._skills:
            return []
        task_tokens = set(self._tokens(task_text, limit=12))
        ranked: List[tuple] = []
        for skill in self._skills:
            sk_tokens = set(skill.get("trigger_tokens") or self._tokens(
                skill.get("trigger", ""), limit=10
            ))
            overlap = len(task_tokens & sk_tokens)
            if overlap == 0:
                continue
            score = min(0.6, overlap * 0.15)
            if axis_context and skill.get("axis_context"):
                score += self._axis_sim(axis_context, skill["axis_context"]) * 0.4
            ranked.append((score, skill.get("procedure", "")))
        ranked.sort(key=lambda x: x[0], reverse=True)
        seen: set = set()
        out: List[str] = []
        for _, proc in ranked:
            k = proc.lower()[:60]
            if k in seen:
                continue
            seen.add(k)
            out.append(proc)
            if len(out) >= limit:
                break
        return out

    def reinforce_match(self, task_text: str, axis_context: Optional[dict] = None) -> None:
        """
        Positive-use feedback: bump sightings on skills that match the current
        task. Called when a skill hint actually surfaces in synthesis — the skill
        proved relevant, so its recall weight should rise.
        """
        if not self._skills:
            return
        toks = self._tokens(task_text, limit=12)
        if not toks:
            return
        for sk in self._skills:
            sk_toks = set(sk.get("trigger_tokens") or self._tokens(sk.get("trigger", ""), limit=10))
            if not sk_toks:
                continue
            overlap = len(toks & sk_toks) / max(len(toks), 1)
            if overlap >= 0.40:
                sk["sightings"] = sk.get("sightings", 1) + 1
                sk["last_reinforced_ts"] = time.time()

    def has_skill(self, task_text: str) -> bool:
        return bool(self.get_skill_hints(task_text, limit=1))

    def load(self) -> bool:
        try:
            path = self._path()
            if not os.path.exists(path):
                return False
            self._skills = []
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._skills.append(json.loads(line))
                    except Exception:
                        continue
            return True
        except Exception:
            return False


# ============================================================================
# LESSON PLAN ENGINE
# ============================================================================

# ============================================================================
# GENEALOGY PHASE TRACKER
# ============================================================================
# Tracks the compression/expansion cycle of the constraint genealogy.
# Aurora measures her own evolutionary trajectory, gauges prediction error,
# patterns the error curve, and eventually gains agency over her own
# developmental phase — stalling or accelerating transitions intentionally.

@dataclass
class GenealogySample:
    """One snapshot of the genealogy state taken after a simulation burst."""
    timestamp: float
    burst_index: int
    outlet: float       # outlet_push_fraction
    links: int          # total promoted links
    fossils: int        # total fossils recorded
    tick: int           # chamber tick count
    # Deltas from previous sample (filled in by tracker)
    d_outlet: float = 0.0
    d_links: int = 0
    d_fossils: int = 0


@dataclass
class CycleEvent:
    """A detected phase transition in the genealogy cycle."""
    kind: str           # "compression_start" | "expansion_start" | "growth_peak"
    burst_index: int
    timestamp: float
    outlet: float
    links: int


class GenealogyPhaseTracker:
    """
    Self-modeling tracker for Aurora's constraint genealogy cycle.

    Phase model:
      GROWTH      — links and fossils accumulating, cross-representations expanding
      COMPRESSION — link growth stalling, system consolidating to axis primitives
      EXPANSION   — outlet rising post-compression, new variant lineages forming

    Learning loop:
      1. Record snapshot after each burst
      2. Predict next snapshot via linear extrapolation
      3. Measure prediction error
      4. Pattern the error — high error marks transition boundaries
      5. Use error curve to predict transitions more accurately than raw metrics
      6. Issue modulation recommendations: stall / hold / accelerate
    """

    PHASE_GROWTH      = "growth"
    PHASE_COMPRESSION = "compression"
    PHASE_EXPANSION   = "expansion"

    # Link-growth rate below this (per burst) triggers compression detection
    _COMPRESSION_LINK_THRESHOLD = 2
    # Outlet delta above this triggers expansion detection
    _EXPANSION_OUTLET_THRESHOLD = 0.003

    def __init__(self, maxlen: int = 500):
        self._samples: deque = deque(maxlen=maxlen)
        self._events: List[CycleEvent] = []
        self._burst_index: int = 0
        self._phase: str = self.PHASE_GROWTH
        self._prev_phase: str = self.PHASE_GROWTH

        # Prediction error tracking
        self._errors: deque = deque(maxlen=300)   # (burst_idx, error_magnitude)
        self._last_pred: Dict[str, float] = {}

        # Cycle interval history (bursts between compression events)
        self._compression_intervals: List[int] = []
        self._last_compression_burst: int = 0
        self._last_expansion_burst: int = 0

    # ----------------------------------------------------------------
    def record(self, snap: Dict[str, Any]) -> str:
        """
        Record a post-burst snapshot. Detects phase, closes prediction loop.
        Returns current phase label.
        """
        self._burst_index += 1
        prev = self._samples[-1] if self._samples else None

        sample = GenealogySample(
            timestamp=snap.get("timestamp", time.time()),
            burst_index=self._burst_index,
            outlet=float(snap.get("outlet", 0.0)),
            links=int(snap.get("links", 0)),
            fossils=int(snap.get("fossils", 0)),
            tick=int(snap.get("tick", 0)),
        )
        if prev:
            sample.d_outlet  = sample.outlet  - prev.outlet
            sample.d_links   = sample.links   - prev.links
            sample.d_fossils = sample.fossils - prev.fossils

        # Close prediction loop — measure error against last prediction
        if self._last_pred and prev:
            err = math.sqrt(
                (sample.outlet - self._last_pred.get("outlet", sample.outlet)) ** 2
                + ((sample.links - self._last_pred.get("links", sample.links)) / max(1, sample.links)) ** 2
            )
            self._errors.append((self._burst_index, err))

        self._samples.append(sample)
        self._prev_phase = self._phase
        self._phase = self._detect_phase()

        # Detect and log phase transition events
        if self._phase != self._prev_phase:
            evt = CycleEvent(
                kind=f"{self._phase}_start",
                burst_index=self._burst_index,
                timestamp=sample.timestamp,
                outlet=sample.outlet,
                links=sample.links,
            )
            self._events.append(evt)
            if self._phase == self.PHASE_COMPRESSION:
                interval = self._burst_index - self._last_compression_burst
                if self._last_compression_burst > 0:
                    self._compression_intervals.append(interval)
                self._last_compression_burst = self._burst_index
            elif self._phase == self.PHASE_EXPANSION:
                self._last_expansion_burst = self._burst_index

        # Build next prediction
        self._last_pred = self._predict_raw()
        return self._phase

    # ----------------------------------------------------------------
    def _detect_phase(self) -> str:
        """Infer current phase from recent delta patterns."""
        if len(self._samples) < 3:
            return self.PHASE_GROWTH

        recent = list(self._samples)[-5:]
        avg_d_links  = sum(s.d_links  for s in recent) / len(recent)
        avg_d_outlet = sum(s.d_outlet for s in recent) / len(recent)

        if avg_d_links <= self._COMPRESSION_LINK_THRESHOLD and self._phase != self.PHASE_EXPANSION:
            return self.PHASE_COMPRESSION
        if avg_d_outlet >= self._EXPANSION_OUTLET_THRESHOLD:
            return self.PHASE_EXPANSION
        return self.PHASE_GROWTH

    # ----------------------------------------------------------------
    def _predict_raw(self) -> Dict[str, float]:
        """Linear extrapolation of next snapshot values."""
        if len(self._samples) < 2:
            s = self._samples[-1] if self._samples else None
            return {"outlet": s.outlet if s else 0.0,
                    "links": s.links   if s else 0,
                    "fossils": s.fossils if s else 0}

        recent = list(self._samples)[-10:]
        n = len(recent)
        avg_d_outlet  = sum(s.d_outlet  for s in recent) / n
        avg_d_links   = sum(s.d_links   for s in recent) / n
        avg_d_fossils = sum(s.d_fossils for s in recent) / n
        last = recent[-1]
        return {
            "outlet":  last.outlet  + avg_d_outlet,
            "links":   last.links   + avg_d_links,
            "fossils": last.fossils + avg_d_fossils,
        }

    # ----------------------------------------------------------------
    def bursts_until_compression(self) -> Optional[float]:
        """
        Estimate bursts until next compression using:
          - avg compression interval from history, OR
          - current link growth rate extrapolated to stall point
        """
        if not self._samples:
            return None

        # Method 1: interval history
        if len(self._compression_intervals) >= 2:
            avg_interval = sum(self._compression_intervals) / len(self._compression_intervals)
            since_last   = self._burst_index - self._last_compression_burst
            remaining    = avg_interval - since_last
            return max(0.0, remaining)

        # Method 2: extrapolate link growth to plateau
        recent = list(self._samples)[-10:]
        if len(recent) < 3:
            return None
        avg_d_links = sum(s.d_links for s in recent) / len(recent)
        if avg_d_links <= self._COMPRESSION_LINK_THRESHOLD:
            return 0.0   # already compressing
        # Rough: assume plateau when d_links has been declining linearly
        # Use second derivative to estimate when it hits threshold
        deltas = [s.d_links for s in recent]
        if len(deltas) >= 4:
            dd = [deltas[i+1] - deltas[i] for i in range(len(deltas)-1)]
            avg_dd = sum(dd) / len(dd)
            if avg_dd < 0:   # decelerating
                steps = (avg_d_links - self._COMPRESSION_LINK_THRESHOLD) / max(0.001, -avg_dd)
                return max(0.0, steps)
        return None

    # ----------------------------------------------------------------
    def prediction_error_trend(self) -> Tuple[float, float]:
        """
        Returns (recent_avg_error, trend) where trend > 0 means error rising
        (approaching transition) and trend < 0 means stabilizing.
        """
        if len(self._errors) < 4:
            return 0.0, 0.0
        errs = [e for _, e in self._errors]
        recent  = errs[-10:]
        earlier = errs[-20:-10] if len(errs) >= 20 else errs[:max(1, len(errs)//2)]
        avg_recent  = sum(recent)  / len(recent)
        avg_earlier = sum(earlier) / len(earlier)
        trend = avg_recent - avg_earlier
        return avg_recent, trend

    # ----------------------------------------------------------------
    def modulation_recommendation(self) -> Dict[str, str]:
        """
        Based on phase, cycle position, and prediction error trend:
        returns {action, reason, pressure_bias}.

        action:        "stall" | "accelerate" | "hold"
        pressure_bias: suggestion for next burst's pressure emphasis
        """
        phase = self._phase
        btc   = self.bursts_until_compression()
        err_avg, err_trend = self.prediction_error_trend()

        # Rising error = approaching transition boundary
        near_transition = err_trend > 0.02

        if phase == self.PHASE_GROWTH:
            if near_transition and btc is not None and btc < 5:
                return {
                    "action": "stall",
                    "reason": f"Approaching compression in ~{btc:.1f} bursts; error rising.",
                    "pressure_bias": "amplify OUTLET_PUSH to extend growth phase",
                }
            return {
                "action": "hold",
                "reason": "Stable growth phase.",
                "pressure_bias": "maintain current pressure targets",
            }
        elif phase == self.PHASE_COMPRESSION:
            if len(self._compression_intervals) == 0:
                return {
                    "action": "hold",
                    "reason": "First compression — observing behavior.",
                    "pressure_bias": "reduce pressure intensity, let consolidation complete",
                }
            return {
                "action": "accelerate",
                "reason": "In compression — push through to trigger expansion.",
                "pressure_bias": "bias INTERFACE_WEAKEN, reduce OUTLET_PUSH temporarily",
            }
        else:  # EXPANSION
            return {
                "action": "accelerate",
                "reason": "Expansion active — new lineages forming, press for diversification.",
                "pressure_bias": "amplify highest-effectiveness dimensions from obs_log",
            }

    # ----------------------------------------------------------------
    def summary(self) -> str:
        lines = [f"Genealogy Phase Tracker — burst #{self._burst_index}"]
        lines.append(f"Current phase: {self._phase.upper()}")
        if self._samples:
            last = self._samples[-1]
            lines.append(f"Last snapshot: outlet={last.outlet:.4f} "
                         f"links={last.links} fossils={last.fossils}")
        btc = self.bursts_until_compression()
        if btc is not None:
            lines.append(f"Est. bursts to compression: {btc:.1f}")
        err_avg, err_trend = self.prediction_error_trend()
        lines.append(f"Prediction error: avg={err_avg:.4f} trend={err_trend:+.4f}")
        if self._compression_intervals:
            avg_ci = sum(self._compression_intervals) / len(self._compression_intervals)
            lines.append(f"Avg compression interval: {avg_ci:.1f} bursts "
                         f"(n={len(self._compression_intervals)} cycles)")
        rec = self.modulation_recommendation()
        lines.append(f"Recommendation: {rec['action'].upper()} — {rec['reason']}")
        lines.append(f"Pressure bias: {rec['pressure_bias']}")
        if self._events:
            lines.append(f"Cycle events: {len(self._events)} transitions logged")
        return "\n".join(lines)


# ============================================================================
# PRESSURE OBSERVATION LOG
# ============================================================================

@dataclass
class PressureObservation:
    """One before/after record of a pressure application."""
    timestamp: float
    dims_targeted: List[str]
    before_outlet: float        # outlet_push_fraction before burst
    after_outlet: float         # outlet_push_fraction after burst
    before_links: int           # total_links before
    after_links: int            # total_links after
    before_fossils: int         # total fossils before
    after_fossils: int          # total fossils after
    sim_delta: float            # improvement in sim score (positive = better)
    fitness: float              # episode fitness returned by simulator

    @property
    def outlet_delta(self) -> float:
        return self.after_outlet - self.before_outlet

    @property
    def links_gained(self) -> int:
        return self.after_links - self.before_links

    @property
    def fossils_gained(self) -> int:
        return self.after_fossils - self.before_fossils

    @property
    def effective(self) -> bool:
        """True if pressure moved the genealogy in a positive direction."""
        return self.outlet_delta > 0.001 or self.links_gained > 0 or self.sim_delta > 0.005


class PressureObservationLog:
    """
    Records and analyzes what evolutionary pressures actually did to the
    constraint genealogy.  Used by LessonPlanEngine to bias future specs
    toward pressures that demonstrably move the system.
    """

    def __init__(self, maxlen: int = 200):
        self._obs: deque = deque(maxlen=maxlen)

    def record(self, obs: PressureObservation) -> None:
        self._obs.append(obs)

    def effectiveness_by_dim(self) -> Dict[str, float]:
        """
        Return per-dimension effectiveness score [0..1].
        Score = fraction of observations where this dim was targeted AND
        pressure was effective (outlet moved or links gained).
        """
        dim_total: Dict[str, int] = defaultdict(int)
        dim_hits:  Dict[str, int] = defaultdict(int)
        for obs in self._obs:
            for d in obs.dims_targeted:
                dim_total[d] += 1
                if obs.effective:
                    dim_hits[d] += 1
        return {
            d: dim_hits[d] / max(1, dim_total[d])
            for d in dim_total
        }

    def avg_outlet_delta(self) -> float:
        if not self._obs:
            return 0.0
        return sum(o.outlet_delta for o in self._obs) / len(self._obs)

    def summary(self) -> str:
        if not self._obs:
            return "No pressure observations recorded yet."
        eff = self.effectiveness_by_dim()
        lines = [f"Pressure observations: {len(self._obs)}",
                 f"Avg outlet delta: {self.avg_outlet_delta():+.4f}"]
        top = sorted(eff.items(), key=lambda x: -x[1])[:5]
        lines.append("Most effective pressures:")
        for dim, score in top:
            lines.append(f"  {dim}: {score:.0%} effective")
        return "\n".join(lines)


# Dimension → short axis letter (for I-State authority lookup in avatar specs).
# Derived from _DIM_TO_AXIS in constraint_genealogy.py — kept here as a local
# copy so LessonPlanEngine has no genealogy import dependency.
_DIM_TO_AXIS_SHORT: Dict[str, str] = {
    "emotional_calibration":       "B",
    "boundary_calibration":        "B",
    "ambiguity_handling":          "B",
    "framing_selection":           "A",
    "adaptive_strategy_selection": "A",
    "perspective_integration":     "X",
    "uncertainty_signaling":       "X",
    "contradiction_handling":      "X",
    "context_carryover":           "T",
    "multi_turn_stability":        "T",
    "semantic_precision":          "N",
    "compression_elaboration_fit": "N",
    "implied_intent_inference":    "N",
    "coherence_maintenance":       "X",
}

# Axis letter → canonical I-State pair key for I_STATE_AUTHORITY lookup.
_AXIS_TO_I_STATE_PAIR: Dict[str, str] = {
    "X": "IS/ISNT",
    "T": "CAN/CANT",
    "N": "DO/DONT",
    "B": "SAW/SAUNT",
    "A": "DID/DIDNT",
}


class LessonPlanEngine:
    """
    Converts fail-point scores into avatar specs for the dream simulator.

    Each spec carries:
    - pressure_targets  — dimension weights for avatar scoring
    - behavior_modes    — how the avatar will challenge Aurora
    - code_hints        — full code-logic + pressure understanding
    - i_state_authority — full I-State authority profile for this dim's axis
    """

    # Map dimension → avatar behavior_modes that stress-test it
    _DIM_BEHAVIOR_MODES: Dict[str, Dict[str, float]] = {
        "coherence_maintenance":    {"test_cross_turn_memory": 1.0, "demand_synthesis": 0.8},
        "context_carryover":        {"test_cross_turn_memory": 1.0},
        "ambiguity_handling":       {"test_clarification_seeking": 1.0},
        "contradiction_handling":   {"present_conflicting_evidence": 1.0},
        "implied_intent_inference": {"punish_vagueness": 0.8},
        "misunderstanding_repair":  {"test_clarification_seeking": 0.8},
        "uncertainty_signaling":    {"ask_about_confidence": 1.0},
        "boundary_calibration":     {"punish_vagueness": 0.6},
        "framing_selection":        {"demand_synthesis": 0.7},
        "emotional_calibration":    {"ask_about_confidence": 0.5},
        "semantic_precision":       {"punish_vagueness": 1.0},
        "adaptive_strategy_selection": {"present_conflicting_evidence": 0.7, "demand_synthesis": 0.6},
        "compression_elaboration_fit": {"punish_vagueness": 0.7},
        "perspective_integration":  {"present_conflicting_evidence": 1.0, "demand_synthesis": 0.8},
        "multi_turn_stability":     {"test_cross_turn_memory": 1.0, "demand_synthesis": 0.7},
    }

    def generate_specs(
        self,
        fail_dims: List[Tuple[str, float]],
        n_specs: int = 4,
        effectiveness: Optional[Dict[str, float]] = None,
        ledger: Optional[FailPointLedger] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build avatar specs from top fail dimensions.
        effectiveness — optional dict from PressureObservationLog.effectiveness_by_dim()
          used to amplify pressure on dims that have historically moved the genealogy.
        Returns list of spec dicts suitable for SimulationSession.queue_avatar_specs().
        """
        specs: List[Dict[str, Any]] = []
        eff = effectiveness or {}

        for i, (dim, score) in enumerate(fail_dims[:n_specs]):
            # Amplify pressure if this dimension has been historically effective
            eff_boost = eff.get(dim, 0.5) * 0.3   # up to +0.3 boost
            pressure_targets = {dim: min(1.0, score + 0.3 + eff_boost)}
            directed_dims: List[str] = [dim]

            # Blend in the next fail dimension, also boosted by effectiveness
            if i + 1 < len(fail_dims):
                next_dim, next_score = fail_dims[i + 1]
                next_boost = eff.get(next_dim, 0.5) * 0.2
                pressure_targets[next_dim] = min(0.8, next_score + 0.1 + next_boost)
                directed_dims.append(next_dim)

            # behavior_modes for this dimension
            behavior_modes = dict(self._DIM_BEHAVIOR_MODES.get(dim, {}))

            # Code hints — the full architectural explanation
            logic = DIMENSION_CODE_LOGIC.get(dim, {})
            code_hints: List[str] = []
            if logic.get("code"):
                code_hints.append(f"[CODE] {dim}: {logic['code']}")
            if logic.get("pressure"):
                code_hints.append(f"[PRESSURE] {dim}: {logic['pressure']}")

            prompt_candidates: List[str] = []
            followup_candidates: List[str] = []
            source_episode_ids: List[str] = [dim]
            directed_pack = _DIRECTED_TRAINING.prompt_pack(directed_dims, limit=2)
            if ledger is not None:
                seen_prompts = set()
                seen_followups = set()
                for example in ledger.get_examples(dim, limit=4):
                    conv_id = str(example.get("conversation_id", "") or "").strip()
                    if conv_id and conv_id not in source_episode_ids:
                        source_episode_ids.append(conv_id)
                    user_turns = [str(t or '').strip() for t in list(example.get("user_turns", []) or []) if str(t or '').strip()]
                    if not user_turns:
                        continue
                    head = user_turns[0]
                    head_key = head.lower()
                    if head_key not in seen_prompts:
                        seen_prompts.add(head_key)
                        prompt_candidates.append(head)
                    for follow in user_turns[1:]:
                        follow_key = follow.lower()
                        if follow_key in seen_followups:
                            continue
                        seen_followups.add(follow_key)
                        followup_candidates.append(follow)

            prompt_candidates = _dedupe_texts(
                list(prompt_candidates) + list(directed_pack.get("prompt_candidates", []) or []),
                limit=6,
            )
            followup_candidates = _dedupe_texts(
                list(followup_candidates) + list(directed_pack.get("followup_candidates", []) or []),
                limit=6,
            )
            source_episode_ids = _dedupe_texts(
                list(source_episode_ids) + list(directed_pack.get("source_refs", []) or []),
                limit=10,
            )

            # I-State authority profile for this dimension's axis.
            # Derived from the Unified Field Spec — tells the simulation which
            # field role is under stress and how to frame the learning pressure.
            try:
                from aurora_i_state_beings import I_STATE_AUTHORITY
                _dim_axis = _DIM_TO_AXIS_SHORT.get(dim, "")
                _pair_key = _AXIS_TO_I_STATE_PAIR.get(_dim_axis, "")
                i_state_auth = I_STATE_AUTHORITY.get(_pair_key, {})
            except Exception:
                i_state_auth = {}

            specs.append({
                "avatar_id": f"lesson_{dim}_{i}",
                "pressure_targets": pressure_targets,
                "behavior_modes": behavior_modes,
                "code_hints": code_hints,
                "source_episode_ids": source_episode_ids,
                "avatar_overrides": {},
                "constraint_axes": {},
                "source_leverage_points": {dim: score},
                "prompt_candidates": prompt_candidates,
                "followup_candidates": followup_candidates,
                "i_state_authority": i_state_auth,   # full authority profile per spec
            })

        return specs


# ============================================================================
# FAIL-POINT DIMENSION CLASSIFIER
# (what rubric dimension probably failed given a bad comparison result)
# ============================================================================

def classify_fail_dimensions(
    generated: str,
    truth: str,
    mismatch: float,
    context_hints: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, float]]:
    """
    Infer which rubric dimensions likely failed from a low-similarity
    corpus comparison.  Returns list of (dimension, severity) pairs.

    Priority order:
      1. Mechanistic telemetry — actual subsystem confidence readings from
         the turn that just completed (precise, subsystem-sourced).
      2. Text-surface heuristics — structural properties of generated vs
         truth text (fallback when telemetry has no data or is weak).

    Telemetry is contributed by:
      - DPME.process()         → coherence_maintenance, emotional_calibration
      - ExpressionEcology      → framing_selection
      - OETS.lookup            → semantic_precision
    """
    if mismatch < 0.20:
        return []  # Not a significant fail

    # ── 1. Mechanistic telemetry (preferred) ─────────────────────────────────
    try:
        from aurora_telemetry import get_telemetry as _get_tel
        _tel = _get_tel()
        if _tel.has_data():
            mech = _tel.mechanistic_fails(threshold=0.50)
            if mech:
                # Scale severity by mismatch magnitude so weak subsystem
                # signals are still weighted by how badly the turn failed.
                scaled = [
                    (dim, min(1.0, sev * (0.5 + mismatch * 0.5)))
                    for dim, sev in mech
                ]
                return scaled
    except Exception:
        pass

    results: List[Tuple[str, float]] = []
    gen = (generated or "").strip()
    tr  = (truth or "").strip()
    gen_words = gen.lower().split()
    tr_words  = tr.lower().split()
    # Comprehension context dict (passed from caller, e.g. from prompt tone analysis)
    _ctx = context_hints or {}

    # --- Coherence: generated is short and scattered vs long truth ---
    if len(gen_words) > 5 and len(tr_words) > 5:
        ratio = len(gen_words) / max(1, len(tr_words))
        if ratio < 0.3 and mismatch > 0.5:
            results.append(("coherence_maintenance", mismatch * 0.9))
        elif ratio > 3.0 and mismatch > 0.4:
            results.append(("compression_elaboration_fit", mismatch * 0.8))

    # --- Semantic precision: many rare/unusual words in truth not in gen ---
    gen_set = set(gen_words)
    tr_set  = set(tr_words)
    unique_to_truth = tr_set - gen_set
    precision_miss = len(unique_to_truth) / max(1, len(tr_set))
    if precision_miss > 0.6 and mismatch > 0.35:
        results.append(("semantic_precision", min(1.0, precision_miss * mismatch)))

    # --- Context carryover: generated ignores referential words from truth ---
    ref_words = {"this", "that", "it", "they", "them", "those", "these",
                 "earlier", "previous", "before", "above", "mentioned"}
    truth_refs = ref_words & tr_set
    gen_refs   = ref_words & gen_set
    if truth_refs and not gen_refs and mismatch > 0.3:
        results.append(("context_carryover", mismatch * 0.7))

    # --- Uncertainty signaling: truth uses hedging words, gen doesn't ---
    hedge_words = {"maybe", "perhaps", "likely", "possibly", "might", "could",
                   "uncertain", "unclear", "not sure", "i think", "i believe",
                   "probably", "seems", "appears"}
    truth_has_hedge = any(w in tr.lower() for w in hedge_words)
    gen_has_hedge   = any(w in gen.lower() for w in hedge_words)
    if truth_has_hedge and not gen_has_hedge and mismatch > 0.3:
        results.append(("uncertainty_signaling", mismatch * 0.65))

    # --- Perspective integration: truth uses contrast/balance words ---
    contrast_words = {"however", "but", "although", "whereas", "while",
                      "on the other hand", "alternatively", "yet", "despite"}
    truth_has_contrast = any(w in tr.lower() for w in contrast_words)
    gen_has_contrast   = any(w in gen.lower() for w in contrast_words)
    if truth_has_contrast and not gen_has_contrast and mismatch > 0.4:
        results.append(("perspective_integration", mismatch * 0.7))
    # Comprehension context: if the query explicitly required synthesis/comparison,
    # surface perspective_integration fail even at lower mismatch threshold.
    elif _ctx.get("requires_synthesis", False) and truth_has_contrast and not gen_has_contrast:
        if not any(d == "perspective_integration" for d, _ in results) and mismatch > 0.25:
            results.append(("perspective_integration", mismatch * 0.65))

    # --- Emotional calibration: warmth words present in truth but not gen ---
    warm_words = {"feel", "understand", "care", "support", "sorry",
                  "glad", "appreciate", "warmth", "together", "share"}
    truth_warm = sum(1 for w in warm_words if w in tr.lower())
    gen_warm   = sum(1 for w in warm_words if w in gen.lower())
    # Comprehension context: emotional/relational queries lower the detection threshold
    # so calibration failures surface even when warmth words are sparse.
    _emotional_query = _ctx.get("emotional_query", False)
    _warm_min = 1 if _emotional_query else 2
    _warm_floor = 0.15 if _emotional_query else 0.3
    if truth_warm >= _warm_min and gen_warm < truth_warm / 2 and mismatch > _warm_floor:
        _sev = mismatch * (0.75 if _emotional_query else 0.6)
        results.append(("emotional_calibration", _sev))

    # --- General fallback: high mismatch with no specific trigger ---
    if not results and mismatch > 0.50:
        results.append(("coherence_maintenance", mismatch))
    elif not results and mismatch > 0.30:
        results.append(("adaptive_strategy_selection", mismatch * 0.7))

    # Apply axis-weighted boost: turns where a specific constraint axis
    # dominated get their most-related fail dimensions amplified.
    # This makes the fail ledger reflect constraint geometry, not just text shape.
    try:
        from aurora_telemetry import get_telemetry as _gt
        results = _gt().axis_weighted_fails(results)
    except Exception:
        results.sort(key=lambda x: x[1], reverse=True)

    return results


# ============================================================================
# LEARNED BEHAVIOR APPLICATOR
# ============================================================================

class LearnedBehaviorApplicator:
    """
    Bridges ConsciousLearner shards into:
      1. Response hints for aurora.py response building
      2. OETS concept nodes so learnings persist in system-wide memory
    """

    def get_hints(
        self,
        context_type: str,
        topic_words: List[str],
        learner: Any,
    ) -> List[str]:
        """
        Return top learned understandings relevant to this context.
        Returns at most 3 strings, confidence-ranked.
        """
        if learner is None:
            return []
        shards = getattr(learner, "shards", {}) or {}
        if not shards:
            return []

        candidates = []
        ctx_lower = context_type.lower()
        topic_set = {w.lower() for w in (topic_words or [])}

        for shard in shards.values():
            understanding = str(getattr(shard, "understanding", "") or "")
            if not understanding:
                continue
            shard_ctx = str(getattr(shard, "context_type", "") or "").lower()

            # Score relevance
            conf = max(0.0, min(1.0, float(getattr(shard, "confidence", 0) or 0.0)))
            score = conf
            if shard_ctx and ctx_lower and shard_ctx in ctx_lower:
                score += 0.2
            # Boost if topic words appear in the understanding
            u_lower = understanding.lower()
            for w in topic_set:
                if w in u_lower:
                    score += 0.1
                    break

            candidates.append((score, understanding))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [u for _, u in candidates[:3]]

    def inject_into_oets(self, learner: Any, oets: Any) -> int:
        """
        Bridge high-confidence learner shards into the OETS semantic web
        as concept nodes so they persist in Aurora's system-wide memory.

        Returns number of nodes created/reinforced.
        """
        if learner is None or oets is None:
            return 0

        web = getattr(oets, "web", None)
        if web is None or not hasattr(web, "add_node"):
            return 0

        shards = getattr(learner, "shards", {}) or {}
        injected = 0

        for shard in shards.values():
            conf = max(0.0, min(1.0, float(getattr(shard, "confidence", 0) or 0.0)))
            understanding = str(getattr(shard, "understanding", "") or "").strip()
            if not understanding:
                continue

            # Use a short slug as the node word (avoids overly long keys)
            concept = getattr(shard, "response_concept", None)
            concept_name = (
                concept.value if hasattr(concept, "value") else str(concept)
            ).lower().replace("_", " ")
            # Create a deterministic slug
            slug_words = understanding.lower().split()[:4]
            slug = "_".join(re.sub(r"[^a-z]", "", w) for w in slug_words)
            if not slug:
                continue

            try:
                node = web.add_node(
                    word=slug,
                    role="learned_behavior",
                    valence=min(0.9, 0.35 + (conf * 0.65)),
                    meaning=understanding,
                    lineage=f"learner:{concept_name}",
                )
                # Add definition with high confidence
                if hasattr(node, "add_definition"):
                    node.add_definition(
                        understanding,
                        source="conscious_learner",
                        confidence=conf,
                    )
                injected += 1
            except Exception:
                continue

        return injected


# ============================================================================
# DREAM TRAINER — Main Orchestrator
# ============================================================================

class DreamTrainer:
    """
    Orchestrates the full dream-training loop:

    corpus episode bundle
      → fail-point detection from DPME comparison
      → lesson plan generation targeting top fail dims
      → avatar specs queued into SimulationSession
      → dream episodes run on corpus content
      → learner shards bridge into OETS (system-wide memory)
      → aurora.py response building pulls learned behavior hints

    Usage:
      # In corpus_runner boot:
      dream_trainer = DreamTrainer(state_dir)
      systems["dream_trainer"] = dream_trainer

      # In corpus DPME comparison:
      dream_trainer.record_corpus_fail_from_comparison(generated, truth, mismatch)

      # Before each simulation_burst:
      dream_trainer.flush_lessons_to_simulation(systems)

      # In aurora.py response building:
      hints = dream_trainer.get_response_hints(context_type, topic_words, systems)
    """

    def __init__(self, state_dir: str = _DEFAULT_STATE_DIR):
        self.state_dir = state_dir
        self.ledger = FailPointLedger(state_dir)
        self.ledger.load()
        self.retention = RetainedLearningBank(state_dir)
        self.retention.load()
        self.bundler = EpisodeBundler()
        self.planner = LessonPlanEngine()
        self.applicator = LearnedBehaviorApplicator()
        self.obs_log = PressureObservationLog()
        self.phase_tracker = GenealogyPhaseTracker()

        self._fail_count_since_flush = 0
        self._flush_every = 50   # flush lessons to simulation every N fails
        self._flush_call_count = 0  # tracks chronic audit cadence
        self._last_inject_time = 0.0
        self._inject_interval = 300.0  # re-inject OETS every 5 minutes
        self._systems: Dict[str, Any] = {}       # set by boot_aurora or corpus_runner
        self._genealogy_ref: Any = None          # direct genealogy reference
        self._last_relational_probe_summary: Dict[str, Any] = {}

    def _constraint_axes(self) -> Dict[str, float]:
        retained = len(getattr(self.retention, "_records", {}) or {})
        top_fails = len(self.ledger.get_top_fails(5))
        observations = len(getattr(self.obs_log, "_observations", []) or [])
        return {
            "X": max(0.0, min(1.0, 0.18 + min(0.25, retained / 80.0))),
            "T": max(0.0, min(1.0, 0.20 + min(0.28, self._flush_call_count / 60.0) + min(0.10, observations / 120.0))),
            "N": max(0.0, min(1.0, 0.20 + min(0.28, float(getattr(self.ledger, "_total_fails", 0) or 0) / 300.0))),
            "B": max(0.0, min(1.0, 0.18 + min(0.30, top_fails / 8.0))),
            "A": max(0.0, min(1.0, 0.20 + (0.18 if self._systems else 0.0) + (0.10 if self._genealogy_ref is not None else 0.0))),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.18))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.20)),
            B=float(ax.get("B", 0.18)),
            A=float(ax.get("A", 0.20)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(_ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": {
                "total_fails": int(getattr(self.ledger, "_total_fails", 0) or 0),
                "retained_learnings": len(getattr(self.retention, "_records", {}) or {}),
                "flush_call_count": int(self._flush_call_count or 0),
                "fails_since_flush": int(self._fail_count_since_flush or 0),
                "last_relational_probe_summary": dict(self._last_relational_probe_summary or {}),
            },
        }

    def record_sensory_tension(self, modality: str, facet: str, tension: float, context: str = ""):
        """
        NATURAL ACCELERATION: Record high-pressure sensory events as dream targets.
        S12-FAST: Tension on the B-axis (Boundary) or X-axis (Existence) 
        drives targeted visual evolution during downtime.
        """
        try:
            # We treat sensory tension as a specialized 'fail point'
            dim = f"sensory_{modality}_{facet}"
            self.ledger.record_fail(dim, severity=tension, example={
                "conversation_id": f"sensory_{int(time.time())}",
                "source": "sensory_competency",
                "user_turns": [f"Visual Stimulus: {context}"],
                "assistant_turns": [f"Tension detected: {tension:.3f}"],
                "timestamp": time.time()
            })
            self._fail_count_since_flush += 1
        except Exception:
            pass
    def _build_relational_probe_specs(
        self,
        fail_dims: List[Tuple[str, float]],
        *,
        limit: int = 2,
    ) -> List[Dict[str, Any]]:
        specs: List[Dict[str, Any]] = []
        seen_pairs = set()

        for dim, score in list(fail_dims or [])[:4]:
            examples = self.ledger.get_examples(dim, limit=3)
            for example in examples:
                conv_id = str(example.get("conversation_id", "") or "").strip()
                texts = _dedupe_texts(
                    list(example.get("user_turns", []) or []) +
                    list(example.get("assistant_turns", []) or []),
                    limit=10,
                )
                for left, right in _extract_relational_pairs(texts, limit=2):
                    pair_key = tuple(sorted((left, right)))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    source_snippet = texts[0] if texts else f"{left} {right}"
                    prompt_candidates = _dedupe_texts(
                        [
                            f"Use this corpus fragment as context: {source_snippet}",
                            f"Take {left} and {right} together and explain their likely relation.",
                            f"In this context, what does {left} do relative to {right}?",
                        ],
                        limit=6,
                    )
                    followup_candidates = _dedupe_texts(
                        [
                            f"What behavior links {left} and {right} here?",
                            f"What would likely cause that relation to change?",
                            f"What effect would that change have next?",
                            f"If {left} shifts, what changes for {right}?",
                        ],
                        limit=6,
                    )
                    axis = DIMENSION_AXIS.get(dim, "T")
                    specs.append(
                        {
                            "avatar_id": f"rel_probe_{left[:12]}_{right[:12]}_{len(specs)}",
                            "pressure_targets": {
                                dim: min(1.0, max(0.72, float(score or 0.0) + 0.18)),
                                "semantic_precision": 0.82,
                                "coherence_maintenance": 0.74,
                            },
                            "behavior_modes": {
                                "demand_synthesis": 0.9,
                                "test_cross_turn_memory": 0.65,
                                "ask_about_confidence": 0.45,
                            },
                            "code_hints": [
                                _pack_relational_probe_hint(left, right, conv_id),
                                "[RELATION] hold two concepts in one frame, infer behavior, then trace cause and effect",
                            ],
                            "source_episode_ids": _dedupe_texts([conv_id, dim], limit=6),
                            "avatar_overrides": {
                                "topic": {
                                    "category": "relational_probe",
                                    "prompt": source_snippet[:220],
                                    "expected_tone": "analytical",
                                }
                            },
                            "constraint_axes": {axis: 1.0},
                            "source_leverage_points": {dim: score, "relational_probe": 1.0},
                            "prompt_candidates": prompt_candidates,
                            "followup_candidates": followup_candidates,
                        }
                    )
                    if len(specs) >= max(1, int(limit or 1)):
                        return specs

        return specs

    def _relational_probe_success(
        self,
        assistant_text: str,
        *,
        left: str,
        right: str,
        avg_fitness: float,
    ) -> bool:
        reply = re.sub(r"\s+", " ", str(assistant_text or "").strip().lower())
        if len(reply.split()) < 8:
            return False
        if float(avg_fitness or 0.0) < 0.42:
            return False
        if left.lower() not in reply or right.lower() not in reply:
            return False
        cue_hits = 0
        for cue in _RELATIONAL_RELATION_CUES + _RELATIONAL_CAUSE_CUES:
            if cue in reply:
                cue_hits += 1
        return cue_hits >= 2

    def record_relational_probe_outcomes(
        self,
        systems: Dict[str, Any],
        episode_results: List[Any],
        *,
        phase_name: str = "training_epoch",
    ) -> Dict[str, Any]:
        summary = {
            "probe_episodes": 0,
            "successful": 0,
            "failed": 0,
            "applied_learnings": 0,
            "study_topics": [],
        }
        autonomy = systems.get("autonomy")

        for episode in list(episode_results or []):
            spec_id = str(
                getattr(episode, "active_avatar_spec_id", "") or
                (episode.get("active_avatar_spec_id", "") if isinstance(episode, dict) else "")
            )
            if not spec_id.startswith("rel_probe_"):
                continue

            summary["probe_episodes"] += 1
            code_hints = list(
                getattr(episode, "active_avatar_code_hints", []) or
                (episode.get("active_avatar_code_hints", []) if isinstance(episode, dict) else [])
            )
            probe_meta = _parse_relational_probe_hint(code_hints)
            left = str(probe_meta.get("left", "") or "").strip()
            right = str(probe_meta.get("right", "") or "").strip()
            trace = list(
                getattr(episode, "conversation_trace", []) or
                (episode.get("conversation_trace", []) if isinstance(episode, dict) else [])
            )
            assistant_turns = [
                str(turn.get("assistant_text", "") or "").strip()
                for turn in trace
                if isinstance(turn, dict) and str(turn.get("assistant_text", "") or "").strip()
            ]
            user_turns = [
                str(turn.get("user_text", "") or "").strip()
                for turn in trace
                if isinstance(turn, dict) and str(turn.get("user_text", "") or "").strip()
            ]
            assistant_text = max(assistant_turns, key=len) if assistant_turns else ""
            avg_fitness = float(
                getattr(episode, "avg_fitness", 0.0) or
                (episode.get("avg_fitness", 0.0) if isinstance(episode, dict) else 0.0)
            )
            example = {
                "conversation_id": f"{phase_name}:{spec_id}",
                "source": "relational_probe",
                "dimension_score": max(0.0, min(1.0, avg_fitness)),
                "user_turns": user_turns[:4],
                "assistant_turns": assistant_turns[:4],
                "timestamp": time.time(),
            }

            if left and right and self._relational_probe_success(
                assistant_text,
                left=left,
                right=right,
                avg_fitness=avg_fitness,
            ):
                recorded = self.record_pipeline_learning(
                    assistant_text,
                    source=f"{phase_name}.relational_probe",
                    confidence=max(0.62, min(0.92, avg_fitness)),
                    context_type="relational_reasoning",
                    topic_words=[left, right, "relation", "cause", "effect"],
                    systems=systems,
                    tags=["relational_probe", "relation_cause_effect", "success"],
                )
                summary["successful"] += 1
                summary["applied_learnings"] += 1 if recorded else 0
                continue

            severity = max(0.45, min(1.0, 1.0 - avg_fitness))
            self._record_fail_dimension("semantic_precision", severity, example=example)
            self._record_fail_dimension("coherence_maintenance", min(1.0, severity * 0.85), example=example)
            for topic in ("relational reasoning", "cause and effect reasoning"):
                if topic not in summary["study_topics"]:
                    summary["study_topics"].append(topic)
                if autonomy is not None and hasattr(autonomy, "add_study_topic"):
                    try:
                        autonomy.add_study_topic(topic)
                    except Exception:
                        pass
            summary["failed"] += 1

        self._last_relational_probe_summary = dict(summary)
        return summary

    # ----------------------------------------------------------------
    # EVOLUTION SNAPSHOT / OBSERVATION LOOP
    # ----------------------------------------------------------------

    def _capture_evolution_snapshot(self, systems: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read current evolutionary state from the chamber/genealogy.
        Returns a dict with outlet_push_fraction, total_links, total_fossils.
        """
        snap = {"outlet": 0.0, "links": 0, "fossils": 0, "tick": 0}
        try:
            # Try chamber via dimensional system
            dimensional = systems.get("dimensional")
            chamber = getattr(dimensional, "chamber", None) or getattr(dimensional, "_chamber", None)
            if chamber is not None:
                status = chamber.status()
                gen = status.get("genealogy", {})
                snap["outlet"] = float(gen.get("outlet_push_fraction", 0.0))
                snap["links"]  = int(gen.get("total_links", 0))
                snap["tick"]   = int(status.get("tick", 0))
                # fossil count from chain_report if available
                genealogy_obj = getattr(chamber, "_genealogy", None)
                if genealogy_obj is not None:
                    report = genealogy_obj.chain_report() if hasattr(genealogy_obj, "chain_report") else {}
                    snap["outlet"]  = float(report.get("outlet_push_fraction", snap["outlet"]))
                    snap["fossils"] = int(report.get("total_fossils", 0))
        except Exception:
            pass
        return snap

    def record_pressure_outcome(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
        dims_targeted: List[str],
        sim_delta: float = 0.0,
        fitness: float = 0.0,
    ) -> str:
        """
        Close the pressure observation loop.  Call after a simulation burst
        with the before/after snapshots captured by _capture_evolution_snapshot.
        Returns current phase label.
        """
        obs = PressureObservation(
            timestamp=time.time(),
            dims_targeted=dims_targeted,
            before_outlet=before.get("outlet", 0.0),
            after_outlet=after.get("outlet", 0.0),
            before_links=before.get("links", 0),
            after_links=after.get("links", 0),
            before_fossils=before.get("fossils", 0),
            after_fossils=after.get("fossils", 0),
            sim_delta=sim_delta,
            fitness=fitness,
        )
        self.obs_log.record(obs)

        # Feed phase tracker with the after-snapshot + timestamp
        snap_for_tracker = dict(after)
        snap_for_tracker["timestamp"] = time.time()
        phase = self.phase_tracker.record(snap_for_tracker)
        return phase

    def pressure_observation_summary(self) -> str:
        return self.obs_log.summary()

    def phase_summary(self) -> str:
        return self.phase_tracker.summary()

    def modulation_recommendation(self) -> Dict[str, str]:
        return self.phase_tracker.modulation_recommendation()

    # ----------------------------------------------------------------
    # FAIL POINT RECORDING
    # ----------------------------------------------------------------

    def _record_fail_dimension(
        self,
        dim: str,
        sev: float,
        example: Optional[Dict[str, Any]] = None,
    ) -> None:
        sev = max(0.0, min(1.0, float(sev or 0.0)))
        if not dim:
            return

        self.ledger.record_fail(dim, sev, example=example)
        self._fail_count_since_flush += 1

        # Apply targeted pressure: consult recommendations first, then
        # apply to the highest-effectiveness (env_key, axis) combination.
        # Falls back to generic axis injection if no env data exists yet.
        try:
            genealogy = self._genealogy_ref
            if genealogy is None:
                simulation = self._systems.get("simulation") if self._systems else None
                chamber = getattr(simulation, "_chamber", None) or getattr(simulation, "chamber", None)
                genealogy = getattr(chamber, "_genealogy", None)

            if genealogy is not None:
                ax = DIMENSION_AXIS.get(dim, "X")
                recs = []
                if hasattr(genealogy, "get_pressure_recommendations"):
                    recs = genealogy.get_pressure_recommendations([(dim, sev)], top_n=1)

                if recs and hasattr(genealogy, "apply_targeted_pressure"):
                    rec = recs[0]
                    genealogy.apply_targeted_pressure(
                        axis=rec["axis"],
                        env_key=rec["env_key"],
                        magnitude=rec["recommended_magnitude"] + sev * 0.3,
                        source=f"{dim}_fail",
                    )
                elif hasattr(genealogy, "inject_training_plateau_pressure"):
                    genealogy.inject_training_plateau_pressure(sev * 0.5, axis_hint=ax)
        except Exception:
            pass

    def record_corpus_fail_from_comparison(
        self,
        generated: str,
        truth: str,
        mismatch: float,
        prompt_text: str = "",
    ) -> List[Tuple[str, float]]:
        """
        Called by corpus_runner after every DPME comparison.
        Classifies which dimension(s) failed and records them.
        Returns the list of (dimension, severity) pairs detected.
        """
        if mismatch < 0.20:
            return []

        # Derive comprehension context from the prompt text so classify_fail_dimensions
        # can apply appropriate sensitivity adjustments for emotional/synthesis queries.
        prompt = re.sub(r'\s+', ' ', str(prompt_text or '').strip())
        _p_lower = prompt.lower()
        _emotional_words = {
            "feel", "feeling", "worried", "scared", "excited", "sad", "happy",
            "frustrated", "anxious", "love", "hate", "miss", "afraid", "hurt",
            "mean to you", "how do you feel", "what does it feel", "upset",
            "overwhelmed", "lonely", "hopeful", "nervous", "relieved",
        }
        _synthesis_words = {
            "compare", "contrast", "versus", "vs ", "difference between",
            "pros and cons", "both sides", "perspective", "point of view",
            "on the other hand", "alternatively", "weigh", "trade-off",
        }
        context_hints = {
            "emotional_query": any(w in _p_lower for w in _emotional_words),
            "requires_synthesis": any(w in _p_lower for w in _synthesis_words),
        }

        dims = classify_fail_dimensions(generated, truth, mismatch, context_hints=context_hints)
        example = None
        if prompt:
            example = {
                "conversation_id": f"corpus:{int(time.time() * 1000)}",
                "source": "corpus_comparison",
                "user_turns": [prompt[:240]],
                "assistant_turns": [
                    re.sub(r'\s+', ' ', str(generated or '').strip())[:240],
                    re.sub(r'\s+', ' ', str(truth or '').strip())[:240],
                ],
                "timestamp": time.time(),
            }
        for dim, sev in dims:
            dim_example = dict(example or {})
            if dim_example:
                dim_example["dimension_score"] = max(0.0, 1.0 - sev)
            self._record_fail_dimension(dim, sev, example=dim_example)

        # Hint the genealogy so that B/A-axis link promotions occurring soon after
        # a detected emotional_calibration or perspective_integration fail get tagged
        # with semantic provenance -- closing the loop between fail classification
        # and the evolutionary fossil record.
        if dims:
            try:
                from aurora_internal.constraint_genealogy import hint_fail_dimension as _hfd
                for dim, _ in dims:
                    _hfd(dim)
            except Exception:
                pass

        return dims

    def record_rubric_failures(
        self,
        rubric_scores: List[Any],
        *,
        threshold: float = 0.62,
        source: str = "simulation_epoch",
        conversation_contexts: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Convert low rubric scores from training/dream conversations into
        fail-point ledger updates so pressure and the hub graph reflect
        simulated communication performance, not just corpus mismatches.
        """
        recorded: List[Tuple[str, float]] = []
        cut = max(0.0, min(1.0, float(threshold or 0.0)))
        if not rubric_scores or cut <= 0.0:
            return recorded

        for score_obj in rubric_scores:
            dim_scores = dict(getattr(score_obj, "dimension_scores", {}) or {})
            confidence = max(0.0, min(1.0, float(getattr(score_obj, "confidence", 1.0) or 0.0)))
            if not dim_scores:
                continue

            for dim, score in dim_scores.items():
                if dim not in DIMENSION_CODE_LOGIC:
                    continue
                value = max(0.0, min(1.0, float(score or 0.0)))
                if value >= cut:
                    continue
                severity = (cut - value) / max(cut, 1e-6)
                severity *= 0.55 + confidence * 0.45
                severity = max(0.0, min(1.0, severity))
                if severity < 0.03:
                    continue
                context = dict((conversation_contexts or {}).get(
                    str(getattr(score_obj, "conversation_id", "") or ""),
                    {},
                ) or {})
                example = None
                if context:
                    example = {
                        "conversation_id": str(context.get("conversation_id", "") or getattr(score_obj, "conversation_id", "") or ""),
                        "source": str(context.get("source", source) or source),
                        "dimension_score": value,
                        "user_turns": list(context.get("user_turns", []) or []),
                        "assistant_turns": list(context.get("assistant_turns", []) or []),
                        "timestamp": time.time(),
                    }
                self._record_fail_dimension(dim, severity, example=example)
                recorded.append((dim, severity))

        if recorded:
            self.ledger.save()
        return recorded

    def _witness_directed_training_samples(
        self,
        systems: Dict[str, Any],
        raw_samples: List[str],
        *,
        dims: Optional[List[str]] = None,
        source: str = "train_txt_observer",
    ) -> int:
        aurora = systems.get("aurora")
        gateway = getattr(aurora, "gateway", None)
        stream_type = systems.get("StreamType")
        existence_mode = systems.get("ExistenceMode")
        memory = systems.get("conversation_memory")
        witnessed = 0
        topic_words = _dedupe_texts(list(dims or []), limit=4)

        for sample in _dedupe_texts(list(raw_samples or []), limit=2):
            if len(sample.split()) < 4:
                continue
            try:
                if gateway is not None and stream_type is not None and existence_mode is not None:
                    gateway.receive(
                        content=f"[TRAIN_TXT] {sample}",
                        stream_type=stream_type.KNOWLEDGE_FEED,
                        source=source,
                        mode=existence_mode.BOUNDED,
                    )
            except Exception:
                pass

            if memory is not None and hasattr(memory, "learn_fact"):
                try:
                    memory.learn_fact(
                        fact=f"[TRAIN_TXT] {sample[:280]}",
                        source=source,
                        confidence=0.58,
                    )
                except Exception:
                    pass

            try:
                self.retention.record(
                    sample[:320],
                    source=source,
                    confidence=0.62,
                    context_type="train_txt_observer",
                    topic_words=topic_words,
                    tags=["train_txt", "directed_training", "observer"],
                )
            except Exception:
                pass
            witnessed += 1

        if witnessed > 0:
            if memory is not None:
                try:
                    self.retention.bridge_to_memory(memory, limit=4)
                except Exception:
                    pass
            self.retention.save()

        return witnessed

    def _mix_directed_bundle_context(
        self,
        bundle_prompt: str,
        short_prompt: str,
        primary_dim: str,
        secondary_dim: str,
    ) -> Dict[str, List[str] | str]:
        directed_pack = _DIRECTED_TRAINING.prompt_pack([primary_dim, secondary_dim], limit=2)
        raw_samples = _dedupe_texts(list(directed_pack.get("raw_samples", []) or []), limit=2)
        prompt_candidates = _dedupe_texts(list(directed_pack.get("prompt_candidates", []) or []), limit=4)
        followup_candidates = _dedupe_texts(list(directed_pack.get("followup_candidates", []) or []), limit=4)
        source_refs = _dedupe_texts(list(directed_pack.get("source_refs", []) or []), limit=6)

        blended_prompt = short_prompt or bundle_prompt
        if raw_samples:
            shard = " | ".join(sample[:90] for sample in raw_samples[:2])
            if shard:
                blended_prompt = f"{short_prompt} | Training shard: {shard}"[:420]

        if blended_prompt:
            prompt_candidates = _dedupe_texts([blended_prompt, short_prompt, bundle_prompt] + prompt_candidates, limit=6)

        return {
            "blended_prompt": blended_prompt,
            "prompt_candidates": prompt_candidates,
            "followup_candidates": followup_candidates,
            "source_refs": source_refs,
            "raw_samples": raw_samples,
        }

    # ----------------------------------------------------------------
    # LESSON FLUSHING
    # ----------------------------------------------------------------

    def flush_lessons_to_simulation(
        self,
        systems: Dict[str, Any],
        force: bool = False,
    ) -> int:
        """
        Generate lesson-plan avatar specs from top fail points and
        queue them into the SimulationSession.

        Returns number of specs queued.
        """
        if not force and self._fail_count_since_flush < 5:
            return 0

        simulation = systems.get("simulation")
        if simulation is None:
            return 0
        session = getattr(simulation, "session", None)
        if session is None:
            return 0

        # Chronic weakness audit: scan episode rubric profiles every N flushes
        # and register dims that are consistently below threshold but never
        # surface as explicit single-turn failures (context_carryover, etc.).
        self._flush_call_count += 1
        if self._flush_call_count % self._CHRONIC_AUDIT_EVERY == 1:
            try:
                self.audit_chronic_weaknesses()
            except Exception:
                pass

        top_fails = self.ledger.get_top_fails(n=5)


        if not top_fails:
            return 0

        # ── Sensory Evolution Bridge (S12-FAST) ──────────────────────
        # Detect sensory fail-points and pass directed deltas to her eyes/ears.
        try:
            sensory = systems.get("sensory")
            if sensory and hasattr(sensory, "evolve"):
                v_deltas = {}
                a_deltas = {}
                for dim, score in top_fails:
                    if dim.startswith("sensory_visual_"):
                        facet = dim.replace("sensory_visual_", "")
                        # Push competency HIGHER to resolve the tension
                        v_deltas[facet] = score * 0.1
                    elif dim.startswith("sensory_audio_"):
                        facet = dim.replace("sensory_audio_", "")
                        a_deltas[facet] = score * 0.1

                if v_deltas or a_deltas:
                    sensory.evolve(pressure=1.5, visual_deltas=v_deltas, audio_deltas=a_deltas)
        except Exception:
            pass

        # Apply per-axis timescale boost before slot selection so slow axes
        # (A, X) aren't perpetually displaced by high-frequency N-axis fails.
        _boosted = [
            (dim, score * _AXIS_SLOT_WEIGHT.get(DIMENSION_AXIS.get(dim, "N"), 1.0))
            for dim, score in top_fails
        ]
        _boosted.sort(key=lambda x: x[1], reverse=True)
        # Restore original scores for specs (boosts are for ordering only)
        _score_map = dict(top_fails)
        top_fails = [(dim, _score_map[dim]) for dim, _ in _boosted]

        # Pass effectiveness observations so specs amplify what works
        effectiveness = self.obs_log.effectiveness_by_dim()
        specs = self.planner.generate_specs(
            top_fails,
            n_specs=4,
            effectiveness=effectiveness,
            ledger=self.ledger,
        )
        probe_specs = self._build_relational_probe_specs(top_fails, limit=2)
        if probe_specs:
            specs.extend(probe_specs)
        queued = 0
        try:
            queued = session.queue_avatar_specs(specs)
        except Exception:
            pass

        self._fail_count_since_flush = 0
        self.ledger.save()
        return queued

    # ----------------------------------------------------------------
    # CHRONIC WEAKNESS DETECTION
    # ----------------------------------------------------------------
    # Threshold below which a dimension is considered chronically weak
    # even if it never triggered an explicit single-turn failure.
    _CHRONIC_RUBRIC_THRESHOLD: float = 0.40
    # Minimum episode count needed to trust the average.
    _CHRONIC_MIN_EPISODES: int = 20
    # Dampening factor: chronic fails count for less than acute ones
    # so they don't crowd out real-time signals.
    _CHRONIC_SEVERITY_WEIGHT: float = 0.55
    # Only run the audit every N flush calls to avoid over-flooding the ledger.
    _CHRONIC_AUDIT_EVERY: int = 5

    def audit_chronic_weaknesses(self) -> List[Tuple[str, float]]:
        """
        Scan episode rubric profiles in dream_episodes/ and register any
        dimension whose average score is below _CHRONIC_RUBRIC_THRESHOLD as
        a fail in the ledger.

        This closes the gap where dimensions like context_carryover (avg 0.20)
        or perspective_integration (avg 0.23) are consistently poor across
        every episode but never trigger an explicit corpus-comparison fail or
        simulation rubric alert — so the ledger, lesson plans, and curriculum
        loop are all blind to them.

        Returns list of (dimension, severity) pairs that were recorded.
        """
        import glob as _glob
        eps_dir = os.path.join(self.state_dir, "dream_episodes")
        if not os.path.isdir(eps_dir):
            return []

        dim_scores: Dict[str, List[float]] = {}
        for fpath in _glob.glob(os.path.join(eps_dir, "dreampk_*.json")):
            if "_payloads" in fpath:
                continue
            try:
                with open(fpath) as _fh:
                    pack = json.load(_fh)
                rp = dict(pack.get("rubric_profile") or {})
                for dim, score in rp.items():
                    if dim not in DIMENSION_CODE_LOGIC:
                        continue
                    dim_scores.setdefault(dim, []).append(
                        max(0.0, min(1.0, float(score or 0.0)))
                    )
            except Exception:
                continue

        recorded: List[Tuple[str, float]] = []
        for dim, scores in dim_scores.items():
            if len(scores) < self._CHRONIC_MIN_EPISODES:
                continue
            avg = sum(scores) / len(scores)
            if avg >= self._CHRONIC_RUBRIC_THRESHOLD:
                continue
            # Severity: proportional to gap, dampened so chronic < acute
            raw_severity = (self._CHRONIC_RUBRIC_THRESHOLD - avg) / self._CHRONIC_RUBRIC_THRESHOLD
            severity = round(max(0.05, min(1.0, raw_severity * self._CHRONIC_SEVERITY_WEIGHT)), 4)
            self.ledger.record_fail(
                dim,
                severity=severity,
                example=None,  # no single conversation to blame — systemic
            )
            recorded.append((dim, severity))

        if recorded:
            self.ledger.save()
        return recorded

    # ----------------------------------------------------------------
    # BUNDLE-DRIVEN TRAINING
    # ----------------------------------------------------------------

    def train_on_bundle(
        self,
        bundle: EpisodeBundle,
        systems: Dict[str, Any],
        turns: int = 5,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a dream simulation episode seeded with a real corpus bundle.

        Builds a temporary avatar spec whose topic prompt is taken from the
        bundle's opening turns, queues it into the session, then runs a
        standard run_episode() so the session's normal machinery applies.

        Returns the EpisodeResult dict or {}.
        """
        simulation = systems.get("simulation")
        if simulation is None:
            return {}

        session = getattr(simulation, "session", None)
        if session is None:
            return {}

        try:
            from foundational_contract import ExistenceMode as _EM
        except ImportError:
            _EM = None  # type: ignore

        # Build a bundle-grounded avatar spec
        # Use the bundle's top fail dimension (first turn implies context domain)
        # and inject the conversation summary as the topic prompt.
        top_fails = self.ledger.get_top_fails(n=2)
        primary_dim = top_fails[0][0] if top_fails else "context_carryover"
        secondary_dim = top_fails[1][0] if len(top_fails) > 1 else "coherence_maintenance"

        # Pull topic hint template for the primary dim, override prompt with bundle context
        topic_hints = session._DIMENSION_TOPIC_HINTS.get(primary_dim, {})
        bundle_prompt = bundle.summary_prompt()
        # Trim to fit — use just enough to give context without overwhelming
        short_prompt = " | ".join(
            f"{role}: {text[:80]}" for role, text in bundle.turns[:3]
        )
        directed_bundle = self._mix_directed_bundle_context(
            bundle_prompt=bundle_prompt,
            short_prompt=short_prompt,
            primary_dim=primary_dim,
            secondary_dim=secondary_dim,
        )
        relational_pairs = _extract_relational_pairs(
            [text for _, text in bundle.turns[:6]],
            limit=2,
        )
        relational_prompts: List[str] = []
        relational_followups: List[str] = []
        for left, right in relational_pairs:
            relational_prompts.append(
                f"Use the bundle context to explain the relation between {left} and {right}."
            )
            relational_followups.extend(
                [
                    f"What behavior links {left} and {right} in this bundle?",
                    f"What would cause that relation to shift?",
                    f"What effect would that shift have next?",
                ]
            )
        self._witness_directed_training_samples(
            systems,
            list(directed_bundle.get("raw_samples", []) or []),
            dims=[primary_dim, secondary_dim],
            source="train_txt_observer.bundle",
        )

        logic = DIMENSION_CODE_LOGIC.get(primary_dim, {})
        code_hints = []
        if logic.get("code"):
            code_hints.append(f"[CODE] {primary_dim}: {logic['code'][:100]}")
        if logic.get("pressure"):
            code_hints.append(f"[PRESSURE] {primary_dim}: {logic['pressure'][:100]}")

        spec = {
            "avatar_id": f"bundle_{bundle.conv_id}",
            "pressure_targets": {
                primary_dim: 0.85,
                secondary_dim: 0.60,
            },
            "behavior_modes": dict(
                session._DIMENSION_TOPIC_HINTS.get(primary_dim, {}).get("behavior_modes", {})
                or {}
            ),
            "code_hints": code_hints,
            "source_episode_ids": _dedupe_texts(
                [bundle.conv_id] + list(directed_bundle.get("source_refs", []) or []),
                limit=8,
            ),
            "avatar_overrides": {
                "topic": {
                    "category": topic_hints.get("category", "practical"),
                    "prompt": str(directed_bundle.get("blended_prompt", short_prompt) or short_prompt),
                    "expected_tone": topic_hints.get("expected_tone", "neutral"),
                }
            },
            "constraint_axes": {},
            "source_leverage_points": {primary_dim: 0.85},
            "prompt_candidates": _dedupe_texts(
                list(directed_bundle.get("prompt_candidates", []) or []) + relational_prompts,
                limit=8,
            ),
            "followup_candidates": _dedupe_texts(
                list(directed_bundle.get("followup_candidates", []) or []) + relational_followups,
                limit=10,
            ),
        }

        # Queue the bundle spec for immediate consumption by run_episode
        try:
            session.queue_avatar_specs([spec])
        except Exception as e:
            if verbose:
                print(f"  [DREAM] queue spec error: {e}")
            return {}

        # Run the episode — session will pop our spec immediately
        result: Dict[str, Any] = {}
        try:
            ep_kw: Dict[str, Any] = {"turns": turns}
            if _EM is not None:
                ep_kw["mode"] = _EM.AGENTIC
            ep_result = simulation.run_episode(**ep_kw)
            # EpisodeResult may be a dataclass or dict — normalise
            if hasattr(ep_result, "__dict__"):
                result = {
                    "avg_fitness": getattr(ep_result, "avg_fitness",
                                           getattr(ep_result, "fitness", 0.0)),
                    "learner_shards": getattr(ep_result, "learner_shards", 0),
                    "episode_id": getattr(ep_result, "episode_id", ""),
                }
            elif isinstance(ep_result, dict):
                result = ep_result
        except Exception as e:
            if verbose:
                print(f"  [DREAM] bundle episode error: {e}")

        # Record the causal experience of this lesson attempt
        try:
            from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger as _PEL
            _fitness = float(result.get("avg_fitness", result.get("fitness", 0.0)) or 0.0)
            _resolved = _fitness > 0.5
            _oets = self._get_oets(systems)
            _PEL.get().record(
                anchor=primary_dim,
                meaning=f"fail dimension targeted for dream training: {primary_dim}",
                pursuing=f"improve_{primary_dim}_via_simulation",
                causal_action=(
                    f"run_episode: avatar={spec.get('avatar_id', '?')} "
                    f"topic={str(spec.get('avatar_overrides', {}).get('topic', {}).get('prompt', ''))[:60]}"
                ),
                consequence={
                    "tension": 1.0 - _fitness,
                    "fitness": _fitness,
                    "shards": result.get("learner_shards", 0),
                    "episode_id": result.get("episode_id", ""),
                },
                outcome={
                    "resolved": _resolved,
                    "tone": "trained" if _resolved else "insufficient",
                    "diverged_from_goal": not _resolved,
                },
                source="dream_trainer",
                oets=_oets,
            )
        except Exception:
            pass

        # Bridge learnings into OETS
        self._bridge_learnings_to_oets(systems)

        return result

    # ----------------------------------------------------------------
    # LEARNER → OETS BRIDGE
    # ----------------------------------------------------------------

    def _bridge_learnings_to_oets(self, systems: Dict[str, Any]) -> int:
        """Bridge ConsciousLearner shards into OETS semantic web."""
        now = time.time()
        if now - self._last_inject_time < self._inject_interval:
            return 0

        learner = self._get_learner(systems)
        oets    = self._get_oets(systems)
        if learner is None or oets is None:
            return 0

        self.retention.absorb_learner(learner, source="simulation")
        count = self.applicator.inject_into_oets(learner, oets)
        memory = systems.get("conversation_memory")
        if memory is not None:
            self.retention.bridge_to_memory(memory, limit=6)
        self.retention.save()
        if count > 0:
            self._last_inject_time = now
        return count

    def retain_learner_state(self, systems: Dict[str, Any], source: str = "simulation") -> int:
        learner = self._get_learner(systems)
        count = self.retention.absorb_learner(learner, source=source)
        memory = systems.get("conversation_memory")
        if memory is not None and count > 0:
            self.retention.bridge_to_memory(memory, limit=6)
        if count > 0:
            self.retention.save()
        return count

    def record_pipeline_learning(
        self,
        text: str,
        *,
        source: str,
        confidence: float = 0.7,
        context_type: str = "",
        topic_words: Optional[List[str]] = None,
        systems: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        recorded = self.retention.record(
            text,
            source=source,
            confidence=confidence,
            context_type=context_type,
            topic_words=topic_words,
            tags=tags,
        )
        if not recorded:
            return False
        systems = systems or self._systems
        if systems:
            memory = systems.get("conversation_memory")
            if memory is not None:
                try:
                    self.retention.bridge_to_memory(memory, limit=4)
                except Exception:
                    pass
        self.retention.save()
        return True

    def force_bridge_learnings_to_oets(self, systems: Dict[str, Any]) -> int:
        """Force OETS bridge regardless of interval."""
        self._last_inject_time = 0.0
        return self._bridge_learnings_to_oets(systems)

    # ----------------------------------------------------------------
    # RESPONSE HINTS (called by aurora.py response building)
    # ----------------------------------------------------------------

    def get_response_hints(
        self,
        context_type: str,
        topic_words: List[str],
        systems: Dict[str, Any],
    ) -> List[str]:
        """
        Return learned behavior hints relevant to this response context.
        Called from _evolutionary_response_refinement in aurora.py.
        """
        learner = self._get_learner(systems)
        hints = self.applicator.get_hints(context_type, topic_words, learner)
        retained = self.retention.relevant(context_type, topic_words, limit=3)
        merged: List[str] = []
        seen = set()
        for item in hints + retained:
            raw = str(item or '').strip()
            # Filter raw manifold diagnostic strings — internal state readouts
            # must not surface as response content hints.
            if (raw.startswith("125-layer manifold:")
                    or ("basis=" in raw and "target=" in raw)
                    or raw.startswith("[CODE]")
                    or raw.startswith("[PRESSURE]")):
                continue
            # Reject SentenceComposer slot-fill artifacts already in retention
            _rt = raw.lower().split()
            if len(_rt) >= 2 and any(_rt[i] == _rt[i + 1] for i in range(len(_rt) - 1)):
                continue
            # Reject OETS study-cycle traces and constraint-state artifacts
            _rl = raw.lower().strip()
            if (re.match(r"i understand (?:what|who|where|when|how)\s+\w+\s+(?:means?|is|are|here)", _rl)
                    or re.match(r"i understand (?:energy|constraint|pressure|axis|cost|boundary|temporal|existence|agency)\b", _rl)
                    or re.match(r"i'?ll want the \w+", _rl)
                    or re.search(r'\b(?:sys\s+[nxbta]\s+\d|iso\s+\d+\s+\d+|battery\s+at\s+\d+|screen\s+active\s+launcher)\b', _rl)):
                continue
            key = re.sub(r'\s+', ' ', raw.lower())
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(raw)
        return merged[:4]

    # ----------------------------------------------------------------
    # STATUS / COMMANDS
    # ----------------------------------------------------------------

    def fail_point_summary(self) -> str:
        return self.ledger.summary()

    def lesson_plan_summary(self) -> str:
        top = self.ledger.get_top_fails(5)
        if not top:
            return "No lesson plan — no fail points recorded yet."
        lines = ["Current lesson plan (top fail dimensions):"]
        for dim, score in top:
            logic = DIMENSION_CODE_LOGIC.get(dim, {})
            code_hint = logic.get("code", "")[:120] if logic.get("code") else ""
            press_hint = logic.get("pressure", "")[:120] if logic.get("pressure") else ""
            lines.append(f"\n  Dimension: {dim}  (score={score:.3f})")
            if code_hint:
                lines.append(f"  Code:     {code_hint}")
            if press_hint:
                lines.append(f"  Pressure: {press_hint}")
        return "\n".join(lines)

    def learned_summary(self, systems: Dict[str, Any]) -> str:
        learner = self._get_learner(systems)
        if learner is None:
            return "ConsciousLearner not available."
        learnings = []
        try:
            learnings = learner.what_have_i_learned()
        except Exception:
            pass
        if not learnings:
            return "No confident learnings formed yet. Run /train or /corpus to accumulate experience."
        lines = ["What Aurora has learned through dream simulation:"]
        for i, l in enumerate(learnings[:10], 1):
            lines.append(f"  {i}. {l}")
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # INTERNAL HELPERS
    # ----------------------------------------------------------------

    def _get_learner(self, systems: Dict[str, Any]) -> Optional[Any]:
        try:
            simulation = systems.get("simulation")
            session = getattr(simulation, "session", None)
            return getattr(session, "learner", None)
        except Exception:
            return None

    def _get_oets(self, systems: Dict[str, Any]) -> Optional[Any]:
        try:
            perception = systems.get("perception")
            return getattr(perception, "oets", None)
        except Exception:
            return None

    def run_introspective_simulation(
        self,
        systems: Dict[str, Any],
        epochs: int = 20,
        episodes_per_epoch: int = 8,
        turns_per_episode: int = 5,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Run accelerated introspective dialogue simulation.

        Seeds the session with specs that activate X/A/B constraint axes —
        the axes that correspond to self-awareness:
          X (existence)  → perspective_integration, contradiction_handling,
                           uncertainty_signaling
          A (agency)     → framing_selection, adaptive_strategy_selection
          B (boundary)   → boundary_calibration, emotional_calibration

        Blends with live top fail-point dimensions so the run compounds on
        real performance gaps. Does not script responses or topics — it sets
        the constraint-axis CONDITIONS that let the generative system develop
        introspective capacity on its own.
        """
        simulation = systems.get("simulation")
        if simulation is None:
            return {"success": False, "reason": "simulation_unavailable"}
        session = getattr(simulation, "session", None)
        if session is None:
            return {"success": False, "reason": "session_unavailable"}

        # X/A/B axis dimensions at high severity — introspective capacity targets
        introspective_dims: List[Tuple[str, float]] = [
            ("perspective_integration",   0.85),
            ("contradiction_handling",    0.80),
            ("uncertainty_signaling",     0.75),
            ("framing_selection",         0.80),
            ("boundary_calibration",      0.70),
            ("semantic_precision",        0.78),
            ("implied_intent_inference",  0.72),
        ]

        # Blend in live top fail dims (up to 3) so real gaps compound
        top_fails = self.ledger.get_top_fails(n=3)
        live_dim_names = {d for d, _ in introspective_dims}
        combined_dims = list(introspective_dims)
        for dim, score in top_fails:
            if dim not in live_dim_names:
                combined_dims.append((dim, score))

        effectiveness = self.obs_log.effectiveness_by_dim()
        specs = self.planner.generate_specs(
            combined_dims[:5],
            n_specs=5,
            effectiveness=effectiveness,
            ledger=self.ledger,
        )

        # Override constraint_axes: activate X+A+B on every spec
        for spec in specs:
            spec["constraint_axes"] = {"X": 0.9, "A": 0.8, "B": 0.7}

        # Relational probe specs drive the dual-view / self-as-object scenarios
        probe_specs = self._build_relational_probe_specs(combined_dims[:3], limit=2)
        for spec in probe_specs:
            spec["constraint_axes"] = {"X": 0.9, "A": 0.8, "B": 0.7}
        specs.extend(probe_specs)

        queued = 0
        try:
            queued = session.queue_avatar_specs(specs)
        except Exception as exc:
            if verbose:
                print(f"  [INTROSPECT] Spec queue failed: {exc}")

        dilation = getattr(getattr(session, "governor", None), "current_dilation", 1.0)
        if verbose:
            print(f"  [INTROSPECT] Queued {queued} introspective specs")
            print(
                f"  [INTROSPECT] Running {epochs} epochs × "
                f"{episodes_per_epoch} episodes × {turns_per_episode} turns  "
                f"@ {dilation:.0f}x dilation"
            )
            print(f"  [INTROSPECT] Axes targeted: X(existence) A(agency) B(boundary)")
            print(f"  [INTROSPECT] Dims: {', '.join(d for d, _ in combined_dims[:5])}")

        def _on_epoch(idx: int, result: Dict[str, Any]) -> None:
            if verbose:
                print(
                    f"    Epoch {idx+1}/{epochs}  "
                    f"fitness={result.get('avg_fitness', 0.0):.3f}  "
                    f"shards={result.get('learner_shards', result.get('total_shards', 0))}"
                )

        try:
            run_result = simulation.run_speed_run(
                epochs=epochs,
                episodes_per_epoch=episodes_per_epoch,
                turns_per_episode=turns_per_episode,
                on_epoch=_on_epoch,
            )
        except Exception as exc:
            return {"success": False, "reason": f"speed_run_failed: {exc}"}

        # Bridge any new learnings to OETS immediately
        try:
            self._bridge_learnings_to_oets(systems)
        except Exception:
            pass

        run_result["success"] = True
        run_result["specs_queued"] = queued
        run_result["dims_targeted"] = [d for d, _ in combined_dims[:5]]
        return run_result

    def save(self) -> None:
        self.ledger.save()
        self.retention.save()

    def load(self) -> None:
        self.ledger.load()
        self.retention.load()
