#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_praxis_bridge.py -- Aurora's side of the Praxis wire.

This is the ONLY Aurora module that knows Praxis exists.  It is deliberately
thin, deliberately suspicious of everything arriving from outside, and
deliberately incapable of writing anything into her that does not go through
doors she already has.

WHAT CROSSES, AND IN WHICH DIRECTION
====================================

    OUT (built here, from figures her own machinery already computes):
        a DeficitManifest -- axis pressure, open inquiries, unresolved
        dimension counts, opaque recurrence signatures, capacity.
        No content.  No text.  No identity.  No internal scalar state.
        The leverage scalar's privacy boundary holds at the network edge too:
        nothing from aurora_leverage_scalar.py leaves this device.

    IN (validated here, then witnessed):
        Situations -- events, consequences, utterances, silence.
        Nothing else has a schema, so nothing else can arrive.

THE DUPLICATED FENCE, ON PURPOSE
================================

The forbidden-vocabulary constants below are a deliberate copy of the ones in
Praxis's praxis_contract.py.  They are NOT imported.  Importing would make one
lock where the design calls for two: if the Praxis side is ever modified,
mis-deployed, spoofed, or replaced, this module still refuses teaching on its
own authority without needing to trust anything on the far end.

INTAKE, AND WHY IT IS NOT ONE DOOR BUT FOUR
===========================================

Per the Constitutive Physics Audit (2026-09-12), the sensory ingestion path
admits an observation WITHOUT constructing a ConstraintVector -- the X:OPERATOR
gate is correct but structurally unreachable.  An environmental consequence
delivered only as SENSOR_DATA therefore arrives as text and metadata and
touches no physics at all.

Her Habitat already solved exactly this problem for exactly this kind of event
(aurora_habitat.py, Rule 6): an environmental action/consequence routes into
her REAL constraint physics through the same entry points perceptual
subsystems use, never through a bespoke environment-only learning channel.
Praxis situations are grammatically isomorphic to Habitat consequences by
construction, so this bridge uses the same four doors:

    1. gateway.receive(...)        observation, SENSOR_DATA, BOUNDED
    2. pressure_pump.inject(...)   PressureDisturbance -> identity field
    3. sedimemory.ingest_event()   with a real ConstraintVector
    4. record_ref_participation_from_scores(...)  resolution pressure

The critical constraint: the projection from an environmental event into the
five axes is computed by HER functions -- aurora_habitat's
`_actual_consequence_dimensions()` and `_consequence_axis_amplitudes()` --
called here on her side of the wire.  Praxis emits her operation vocabulary
and her before/after fields; it computes no axis value and asserts no meaning.

That division is what keeps this honest.  If this module computed amplitudes
itself, the environment would be authoring her physics, which is the one thing
the whole design exists to prevent.  It does not.  It hands her own mapping
her own nouns.

PULL-ONLY, AND SUNNI OUTRANKS IT
================================

Praxis never pushes.  This bridge pulls, and only while `live_idle()` says the
live path is not claiming the field -- the same discipline
HistoricalExperienceEnvironment already establishes.  When Sunni is talking to
her, the environment waits.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

try:
    from aurora_persistence_utils import atomic_write_json
except Exception:                                        # pragma: no cover
    atomic_write_json = None                             # type: ignore[assignment]


PRAXIS_CONTRACT_VERSION = "praxis_contract_v1"

AXES = ("X", "T", "N", "B", "A")
DIMENSIONS = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")

SITUATION_KINDS = ("event", "consequence", "utterance", "silence")

ALLOWED_SITUATION_KEYS = frozenset({
    "contract_version", "episode_id", "situation_id", "kind", "actor",
    "territory", "operation", "target_ids", "affected_entities", "parameters",
    "observable_delta", "pre_state", "post_state", "permission_result",
    "legal", "state_changed", "utterance_text", "budget_remaining",
    "timestamp", "provenance", "epistemic_status", "causal_status",
})

# Operations her consequence-dimension table actually recognises.  A situation
# naming anything else still witnesses as observation, but contributes no
# physics -- because her mapping has no entry for it, and inventing one here
# would be this module deciding what an unfamiliar event means.
CANONICAL_OPERATIONS = frozenset({
    "create", "duplicate", "delete", "restore",
    "move", "resize", "rotate", "recolor",
    "connect", "disconnect", "group", "ungroup",
    "transfer", "grant_permission", "revoke_permission",
})

# --- the outer lock: duplicated, not imported -------------------------------
FORBIDDEN_KEYS = frozenset({
    "score", "reward", "correct", "incorrect", "expected", "expectation",
    "hint", "lesson", "explanation", "explain", "feedback", "rating",
    "grade", "grading", "evaluation", "evaluate", "assessment", "should",
    "intended_learning", "learning_objective", "objective", "curriculum",
    "difficulty", "difficulty_level", "progress", "improvement", "mastery",
    "skill_level", "performance", "accuracy", "success_rate", "correctness",
    "answer", "solution", "ground_truth", "label", "annotation", "tip",
    "guidance", "instruction", "advice", "recommendation", "suggestion",
    "reason", "because", "meaning", "interpretation", "insight",
})

# The outer lock's own copy of the speech-act fence.  Deliberately NOT
# imported from praxis_contract: if Praxis is modified, mis-deployed or
# spoofed, this still holds.  Kept regex-equivalent to the inner lock: both
# suites carry an identical adversarial corpus, so if either lock weakens,
# that side's own build fails.  Neither suite imports the other.
_FORBIDDEN_UTTERANCE_PATTERNS = (
    r"\b(that'?s|this is|you are|you'?re)\s+(right|wrong|correct|incorrect)\b",
    r"\bwell done\b", r"\bgood job\b", r"\bnice work\b", r"\bexactly right\b",
    r"\bthe rule is\b", r"\bthe rules are\b", r"\bthe way (it|this) works\b",
    r"\bwhat you (should|need to|have to|ought to)\b",
    r"\byou (should|must|need to|ought to)\s+(try|learn|understand|remember|realize)\b",
    r"\bhere'?s (a hint|the trick|how)\b", r"\blet me explain\b",
    r"\bthe (answer|solution) is\b",
    r"\bthink (about|of) it (as|like)\b",
    r"\bthe reason (is|why)\b",
    r"\bit means that\b",
    r"\bwhat this teaches\b", r"\byou'?re learning\b", r"\byou'?ve improved\b",
    r"\bkeep (practicing|trying|working)\b",
    r"\bgetting (better|closer|warmer)\b",
    r"\bcloser now\b", r"\bnot quite\b", r"\btry again\b",
    # -- Stage 5 additions ------------------------------------------------
    # The procedural tier's fixed pool never exercised these.  A language
    # model found every one of them on its first adversarial pass.
    #
    # The cost here is asymmetric, and the patterns are biased accordingly.
    # A legitimate line wrongly denied becomes silence -- a legal world fact
    # that costs her nothing.  A teaching line wrongly admitted breaks the
    # one rule this environment exists to keep.  When in doubt, deny.
    #
    # evaluation by adverb, direction, or encouragement
    r"\b(correctly|incorrectly|wrongly|properly)\b",
    r"\byou'?(ve)? got it\b",
    r"\b(right|wrong) (track|direction|idea|way)\b",
    r"\bon track\b", r"\bkeep going\b",
    r"\b(almost|nearly) (there|got it|right)\b",
    r"\byou'?re (doing|getting) (well|great|good|fine|better|it)\b",
    r"\b(great job|nicely done|excellent|bravo)\b",
    # explanation of an outcome, or of how the world works
    r"\bthe reason\b",
    r"\b(failed|worked|didn'?t work|broke|happened) because\b",
    r"\bthat'?s (why|because|how)\b",
    r"\b(depends on|is determined by|is controlled by|is caused by|is tied to|is linked to|are linked)\b",
    r"\bhow (it|this|that) works\b",
    # instruction about method
    r"\bwhat you (want|should|need|have|ought) to do\b",
    r"\byou'?(ll)? (need|have|ought|want) to\b",
    r"\bfirst,? (you|try)\b",
    r"\bactually,? (you|what|the|it)\b",
    r"\binstead,? (you|try)\b",
    r"\btry (moving|connecting|using|doing|it|that|this)\b",
    # the teaching lexicon arriving as content rather than as a key
    r"\b(score|scores|scored|grade|graded|mastery|progress|feedback|hint|hints|lesson|lessons|improve|improved|improvement|improving)\b",
)

_COMPILED_UTTERANCE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in _FORBIDDEN_UTTERANCE_PATTERNS
)

MAX_UTTERANCE_CHARS = 400

# Protocol identity -- the bridge's OWN copy, never imported from Praxis, for
# the same reason the fence constants are duplicated: what counts as a
# compatible peer is decided on her side of the wire.  The version rides as a
# header (transport metadata), never inside a contract payload, so
# negotiation can never widen what crosses.
PRAXIS_SERVICE_NAME = "praxis"
PRAXIS_PROTOCOL_NAME = "praxis-experiential"
PRAXIS_PROTOCOL_VERSION = 1
PRAXIS_COMPATIBLE_PROTOCOL_VERSIONS = (1,)
PRAXIS_PROTOCOL_HEADER = "X-Praxis-Protocol"
HANDSHAKE_RETRY_S = 30.0

# Discovery states, in the order a healthy connection passes through them.
#   unknown       no handshake attempted yet
#   unreachable   nothing answered (Praxis not installed, not running, or
#                 the endpoint is wrong -- indistinguishable over a socket)
#   not_praxis    something answered, but it is not a Praxis service
#   incompatible  Praxis answered with no protocol version we speak
#   not_accepting Praxis is compatible but paused by its operator
#   compatible    the experiential channel is open
DISCOVERY_STATES = ("unknown", "unreachable", "not_praxis", "incompatible",
                    "not_accepting", "compatible")

DEFAULT_ENDPOINT = os.environ.get("AURORA_PRAXIS_ENDPOINT", "http://127.0.0.1:8787")
DEFAULT_POLL_INTERVAL_S = 6.0
DEFAULT_PULL_LIMIT = 12
SPOOL_LIMIT = 400


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class PraxisContractBreach(Exception):
    """Something arrived that tried to teach her.  Loud by design."""

    def __init__(self, reason: str, *, field_path: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.field_path = field_path

    def to_dict(self) -> Dict[str, Any]:
        return {"reason": self.reason, "field_path": self.field_path,
                "side": "aurora", "detected_at": time.time()}


# ---------------------------------------------------------------------------
# Inbound validation -- the outer lock
# ---------------------------------------------------------------------------

def _normalize_key(key: Any) -> str:
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")


def scan_forbidden(payload: Any, *, path: str = "") -> None:
    if isinstance(payload, Mapping):
        for raw_key, value in payload.items():
            key = _normalize_key(raw_key)
            here = f"{path}.{raw_key}" if path else str(raw_key)
            if key in FORBIDDEN_KEYS:
                raise PraxisContractBreach(
                    f"forbidden key '{raw_key}' arrived from Praxis", field_path=here)
            scan_forbidden(value, path=here)
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            scan_forbidden(value, path=f"{path}[{index}]")


def utterance_is_permitted(text: Any) -> bool:
    if text is None:
        return True
    if not isinstance(text, str) or len(text) > MAX_UTTERANCE_CHARS:
        return False
    return not any(pattern.search(text) for pattern in _COMPILED_UTTERANCE_PATTERNS)


def validate_incoming_situation(payload: Any) -> Dict[str, Any]:
    """Refuse anything that is not plainly a thing that happened in a world."""
    if not isinstance(payload, Mapping):
        raise PraxisContractBreach("situation must be a mapping")

    scan_forbidden(payload)

    unknown = {str(k) for k in payload.keys()} - ALLOWED_SITUATION_KEYS
    if unknown:
        raise PraxisContractBreach(f"unknown key(s) {sorted(unknown)}",
                                   field_path=sorted(unknown)[0])

    if str(payload.get("contract_version", "")) != PRAXIS_CONTRACT_VERSION:
        raise PraxisContractBreach("contract version mismatch",
                                   field_path="contract_version")

    if str(payload.get("kind", "")) not in SITUATION_KINDS:
        raise PraxisContractBreach("unknown situation kind", field_path="kind")

    for key in ("episode_id", "situation_id", "provenance", "epistemic_status",
                "causal_status"):
        if not str(payload.get(key, "")).strip():
            raise PraxisContractBreach(f"missing '{key}'", field_path=key)

    if str(payload.get("epistemic_status")) != "observation_not_truth":
        raise PraxisContractBreach(
            "Praxis may only assert observation, never truth",
            field_path="epistemic_status")

    if not utterance_is_permitted(payload.get("utterance_text")):
        raise PraxisContractBreach("utterance parses as teaching",
                                   field_path="utterance_text")

    return dict(payload)


# ---------------------------------------------------------------------------
# Shims -- the minimum surface her own mapping functions read
# ---------------------------------------------------------------------------

class _ShimAction:
    """Carries exactly the attributes aurora_habitat's projection reads.

    Not a HabitatEntity, not a HabitatRuntime action -- a Praxis situation
    wearing the shape her mapping already knows how to inspect.  Nothing is
    computed here.
    """

    __slots__ = ("action_id", "actor", "territory", "operation", "target_ids",
                 "parameters", "intention_context", "causal_context", "timestamp")

    def __init__(self, situation: Mapping[str, Any]) -> None:
        self.action_id = str(situation.get("situation_id", ""))
        self.actor = str(situation.get("actor", "world"))
        self.territory = str(situation.get("territory", "space"))
        self.operation = str(situation.get("operation", ""))
        self.target_ids = list(situation.get("target_ids") or [])
        self.parameters = dict(situation.get("parameters") or {})
        self.intention_context = ""       # Praxis never supplies intent
        self.causal_context = {}          # nor a candidate-evaluation handoff
        self.timestamp = float(situation.get("timestamp", 0.0) or 0.0)


class _ShimConsequence:
    __slots__ = ("action_id", "success", "actor", "operation", "state_changed",
                 "affected_entities", "permission_result", "causal_parent",
                 "timestamp")

    def __init__(self, situation: Mapping[str, Any]) -> None:
        self.action_id = str(situation.get("situation_id", ""))
        # `legal` is her `success`: was this permitted.  Distinct from
        # state_changed, exactly as her Habitat keeps them distinct.
        self.success = bool(situation.get("legal", True))
        self.actor = str(situation.get("actor", "world"))
        self.operation = str(situation.get("operation", ""))
        self.state_changed = bool(situation.get("state_changed", False))
        self.affected_entities = list(situation.get("affected_entities") or [])
        self.permission_result = str(situation.get("permission_result", "n/a"))
        self.causal_parent = None
        self.timestamp = float(situation.get("timestamp", 0.0) or 0.0)


def _carries_physics(situation: Mapping[str, Any]) -> bool:
    """True when this situation is an environmental change her mapping knows.

    Utterances and silence are real experience and are witnessed as
    observation, but they have no physical consequence dimensions of their own
    -- an utterance's consequence is whatever another actor does next, which
    arrives as its own separate situation.
    """
    if str(situation.get("kind", "")) not in ("consequence", "event"):
        return False
    return str(situation.get("operation", "")) in CANONICAL_OPERATIONS


# ---------------------------------------------------------------------------
# The bridge
# ---------------------------------------------------------------------------

class PraxisBridge:
    """Pull-only client with intake through the doors she already has."""

    def __init__(
        self,
        systems: Mapping[str, Any],
        *,
        state_dir: str,
        endpoint: str = DEFAULT_ENDPOINT,
        agent_id: str = "aurora",
        field_lock: Optional[threading.Lock] = None,
        live_idle: Optional[Callable[[], bool]] = None,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        pull_limit: int = DEFAULT_PULL_LIMIT,
        timeout_s: float = 6.0,
    ) -> None:
        self.systems: Dict[str, Any] = dict(systems or {})
        self.root = Path(str(state_dir)) / "praxis"
        self.root.mkdir(parents=True, exist_ok=True)
        self.endpoint = str(endpoint).rstrip("/")
        self.agent_id = str(agent_id)
        self.field_lock = field_lock
        self.live_idle = live_idle
        self.poll_interval_s = float(poll_interval_s)
        self.pull_limit = int(pull_limit)
        self.timeout_s = float(timeout_s)

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.discovery = "unknown"
        self.peer: Dict[str, Any] = {}
        self.last_handshake_at = 0.0
        self._paused = threading.Event()
        self._lock = threading.RLock()

        self.episode_id: str = ""
        self.breaches: List[Dict[str, Any]] = []
        self.situations_witnessed = 0
        self.pressure_injections = 0
        self.sediment_deposits = 0
        self.resolution_emissions = 0
        self.pulls_attempted = 0
        self.last_pull_at = 0.0
        self.last_error = ""
        self.online = False

    # -- paths -------------------------------------------------------------

    @property
    def _spool_path(self) -> Path:
        return self.root / "praxis_spool.json"

    @property
    def _state_path(self) -> Path:
        return self.root / "praxis_bridge_state.json"

    @property
    def _breach_path(self) -> Path:
        return self.root / "praxis_contract_breaches.jsonl"

    @property
    def _ledger_path(self) -> Path:
        return self.root / "praxis_witness_ledger.jsonl"

    # -- transport ---------------------------------------------------------

    def _request(self, path: str, *, method: str = "GET",
                 payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.endpoint}{path}"
        data = None
        headers = {"Accept": "application/json",
                   PRAXIS_PROTOCOL_HEADER: str(PRAXIS_PROTOCOL_VERSION)}
        if payload is not None:
            data = json.dumps(payload, default=str).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers,
                                         method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = response.read().decode("utf-8")
            self.online = True
            self.last_error = ""
            return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            # The server answered -- it is online -- but refused.  An
            # incompatible_protocol refusal is a diagnostic state, not an
            # outage, and the loop must stop pulling until a new handshake.
            self.online = True
            body: Dict[str, Any] = {}
            try:
                body = json.loads(exc.read().decode("utf-8") or "{}")
            except Exception:
                body = {}
            if body.get("error") == "incompatible_protocol":
                self.discovery = "incompatible"
            self.last_error = f"HTTPError {exc.code}: {body.get('error', exc.reason)}"
            return {}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self.online = False
            self.last_error = f"{type(exc).__name__}: {exc}"
            return {}

    # -- outbound: the deficit manifest ------------------------------------

    def build_manifest(self, *, capacity: Optional[bool] = None) -> Dict[str, Any]:
        """Assembled ONLY from figures her own machinery already computes.

        Nothing new is measured about her for Praxis's benefit, and nothing
        that could reconstruct content or identity is included.
        """
        axis_pressure: Dict[str, float] = {}
        open_inquiries: List[str] = []
        try:
            from aurora_habitat_motivation import active_inquiries, active_pressures
            raw_pressures = active_pressures(self.systems) or {}
            for axis, value in raw_pressures.items():
                if str(axis) in AXES:
                    try:
                        axis_pressure[str(axis)] = round(float(value), 4)
                    except Exception:
                        continue
            open_inquiries = [a for a in (active_inquiries(self.systems) or [])
                              if str(a) in AXES]
        except Exception:
            pass

        return {
            "contract_version": PRAXIS_CONTRACT_VERSION,
            "manifest_id": _new_id("man"),
            "agent_id": self.agent_id,
            "axis_pressure": axis_pressure,
            "open_inquiries": open_inquiries,
            "unresolved_dimensions": self._unresolved_dimensions(),
            "recurrence_signatures": self._recurrence_signatures(),
            # Pass `capacity` when the caller already knows it.  Computing it
            # here while the field lock is held would report the bridge's own
            # grip on the lock as "Aurora is busy" -- see pull_once.
            "capacity": bool(self._capacity() if capacity is None else capacity),
            "emitted_at": time.time(),
        }

    def _unresolved_dimensions(self) -> Dict[str, int]:
        """Per-dimension failure counts from her own fail_points.json.

        Counts only.  Which dimension keeps failing is structure; what failed
        inside it is content and stays home.
        """
        out: Dict[str, int] = {}
        path = self.root.parent / "fail_points.json"
        if not path.exists():
            return out
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return out
        if not isinstance(raw, Mapping):
            return out
        for key, value in raw.items():
            dimension = str(key).split(":", 1)[0].strip().upper()
            if dimension not in DIMENSIONS:
                continue
            count = 0
            if isinstance(value, Mapping):
                for candidate in ("count", "failures", "fail_count", "n"):
                    if candidate in value:
                        try:
                            count = int(value[candidate])
                        except Exception:
                            count = 0
                        break
                else:
                    count = len(value)
            elif isinstance(value, (int, float)):
                count = int(value)
            elif isinstance(value, (list, tuple)):
                count = len(value)
            if count:
                out[dimension] = out.get(dimension, 0) + count
        return out

    def _recurrence_signatures(self) -> List[str]:
        """Opaque short hashes of constraint pairs her genealogy shows as
        still failing to relieve.  Praxis cannot decode them and does not try;
        it uses them only as identity tokens for 'still open'."""
        import hashlib

        out: List[str] = []
        path = self.root.parent.parent / "aurora_genealogy" / "pair_stats.json"
        if not path.exists():
            path = self.root.parent / "genealogy" / "pair_stats.json"
        if not path.exists():
            return out
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return out
        if not isinstance(raw, Mapping):
            return out
        for key, value in list(raw.items())[:400]:
            relief = 0.0
            if isinstance(value, Mapping):
                for candidate in ("mean_relief", "relief", "avg_relief"):
                    if candidate in value:
                        try:
                            relief = float(value[candidate])
                        except Exception:
                            relief = 0.0
                        break
            if relief > 0.25:
                continue          # relieving pairs are not open structure
            digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16]
            if digest not in out:
                out.append(digest)
            if len(out) >= 64:
                break
        return out

    def _capacity(self) -> bool:
        if self.live_idle is None:
            return True
        try:
            return bool(self.live_idle())
        except Exception:
            return False

    def open_episode(self, *, capacity: Optional[bool] = None) -> Dict[str, Any]:
        manifest = self.build_manifest(capacity=capacity)
        result = self._request("/manifest", method="POST", payload=manifest)
        episode_id = str(result.get("episode_id", "") or "")
        if episode_id:
            with self._lock:
                self.episode_id = episode_id
            self._persist_state()
        return result

    # -- outbound: her actions ---------------------------------------------

    def act(self, *, operation: str, target_ids: Optional[Iterable[str]] = None,
            parameters: Optional[Mapping[str, Any]] = None,
            territory: str = "space", utterance_text: str = "") -> Dict[str, Any]:
        """Submit one action.  The consequence returns through /pull like every
        other situation -- there is exactly one inbound channel."""
        if not self.episode_id:
            return {"error": "no_open_episode"}
        payload = {
            "agent_id": self.agent_id,
            "episode_id": self.episode_id,
            "operation": str(operation),
            "territory": str(territory),
            "target_ids": [str(t) for t in (target_ids or [])],
            "parameters": dict(parameters or {}),
            "utterance_text": str(utterance_text or ""),
        }
        result = self._request("/act", method="POST", payload=payload)
        if not result:
            self._spool({"kind": "unsent_action", "payload": payload,
                         "queued_at": time.time()})
        return result

    def observe(self) -> Dict[str, Any]:
        state = self._request(f"/observe?agent_id={self.agent_id}")
        try:
            scan_forbidden(state)
        except PraxisContractBreach as breach:
            self._record_breach(breach)
            return {}
        return state

    # -- inbound: pull and witness ----------------------------------------

    def pull_once(self, *, check_capacity: bool = True) -> int:
        """Pull whatever the world has for her and witness it.  Returns the
        number of situations admitted.

        `check_capacity=False` exists for exactly one caller: the background
        loop, which has already checked capacity and is now HOLDING the field
        lock.  Re-checking from inside the critical section is a trap, because
        Aurora's real idle predicate asks whether the field lock is held -- and
        it is, by us.  The bridge would see its own hand on the lock, conclude
        the live path was busy, and back off on every tick forever.  Direct
        callers keep the default and get the full gate.
        """
        if check_capacity and not self._capacity():
            return 0
        with self._lock:
            self.pulls_attempted += 1

        if not self.episode_id:
            # From the loop, capacity was confirmed before the lock was taken;
            # state it rather than re-derive it from inside the lock.
            self.open_episode(capacity=None if check_capacity else True)
            if not self.episode_id:
                return 0

        result = self._request(
            f"/pull?agent_id={self.agent_id}&limit={self.pull_limit}")
        # The world no longer knows this episode -- Praxis restarted, which
        # on a phone happens whenever Android reclaims its process.  Holding
        # on to the dead id would leave her waiting at a door that no longer
        # exists, silently and forever.  Drop it; the next pull opens fresh
        # terrain.  (Praxis's own history of what it has served survives the
        # restart, so the new terrain is still chosen against everything
        # already made.)
        if result.get("error") == "no_open_episode" or (
                result.get("episode_id") and
                result.get("episode_id") != self.episode_id):
            with self._lock:
                self.episode_id = ""
                self.episodes_lost = getattr(self, "episodes_lost", 0) + 1
            self._persist_state()
            return 0

        situations = result.get("situations") or []
        if not situations:
            self._drain_spool()
            return 0

        admitted = 0
        for raw in situations:
            try:
                situation = validate_incoming_situation(raw)
            except PraxisContractBreach as breach:
                self._record_breach(breach)
                continue           # dropped whole; never repaired
            if self._witness(situation):
                admitted += 1

        with self._lock:
            self.last_pull_at = time.time()
        self._persist_state()
        return admitted

    def _gateway_parts(self):
        aurora = self.systems.get("aurora")
        gateway = getattr(aurora, "gateway", None) if aurora is not None else None
        stream_type = self.systems.get("StreamType")
        existence_mode = self.systems.get("ExistenceMode")
        if gateway is None or stream_type is None or existence_mode is None:
            return None, None, None
        return gateway, stream_type, existence_mode

    @staticmethod
    def _observation_text(situation: Mapping[str, Any]) -> str:
        """A flat, literal rendering of what happened.  No adjectives, no
        framing, no significance.  If this sentence ever starts explaining, the
        environment has become a narrator."""
        kind = str(situation.get("kind", ""))
        actor = str(situation.get("actor", "world"))
        if kind == "utterance":
            return f"[{actor}] {situation.get('utterance_text', '')}"
        if kind == "silence":
            return f"[{actor}] (no response)"
        operation = str(situation.get("operation", "") or "occurred")
        targets = ", ".join(str(t) for t in (situation.get("target_ids") or []))
        if kind == "consequence":
            legal = "permitted" if situation.get("legal") else "refused"
            moved = "changed" if situation.get("state_changed") else "unchanged"
            return f"[{actor}] {operation} {targets} -> {legal}, {moved}".strip()
        return f"[{actor}] {operation} {targets}".strip()

    def _witness(self, situation: Mapping[str, Any]) -> bool:
        """Admit one situation through every door that applies to it.

        Observation first, then -- for an environmental change her own mapping
        recognises -- the three physics doors her Habitat already uses.
        """
        gateway, stream_type, existence_mode = self._gateway_parts()
        if gateway is None:
            return False

        metadata = {
            "praxis_experience": True,
            "episode_id": situation.get("episode_id"),
            "situation_id": situation.get("situation_id"),
            "kind": situation.get("kind"),
            "actor": situation.get("actor"),
            "territory": situation.get("territory"),
            "operation": situation.get("operation"),
            "target_ids": situation.get("target_ids"),
            "affected_entities": situation.get("affected_entities"),
            "observable_delta": situation.get("observable_delta"),
            "permission_result": situation.get("permission_result"),
            "legal": situation.get("legal"),
            "state_changed": situation.get("state_changed"),
            "budget_remaining": situation.get("budget_remaining"),
            "observed_timestamp": situation.get("timestamp"),
            "provenance": situation.get("provenance"),
            "epistemic_status": situation.get("epistemic_status"),
            "causal_status": situation.get("causal_status"),
            "autobiographical_status": "aurora_own_environment_participation",
        }

        try:
            response = gateway.receive(
                content=self._observation_text(situation),
                stream_type=stream_type.SENSOR_DATA,
                source=f"praxis:{situation.get('actor', 'world')}",
                metadata=metadata,
                mode=existence_mode.BOUNDED,
            )
        except Exception as exc:
            self.last_error = f"witness_failed: {type(exc).__name__}: {exc}"
            self._spool({"kind": "unwitnessed_situation", "payload": dict(situation),
                         "queued_at": time.time()})
            return False

        physics = {}
        if _carries_physics(situation):
            physics = self._route_to_constraint_physics(situation)

        # Current environmental context only -- never a parallel semantic
        # interpretation.  Her own organs may inspect it if relevant.
        self.systems["_praxis_context"] = {
            "episode_id": situation.get("episode_id"),
            "situation_id": situation.get("situation_id"),
            "kind": situation.get("kind"),
            "actor": situation.get("actor"),
            "observed_timestamp": situation.get("timestamp"),
            "epistemic_status": situation.get("epistemic_status"),
            "causal_status": situation.get("causal_status"),
        }

        with self._lock:
            self.situations_witnessed += 1
        self._append_jsonl(self._ledger_path, {
            "situation_id": situation.get("situation_id"),
            "episode_id": situation.get("episode_id"),
            "kind": situation.get("kind"),
            "actor": situation.get("actor"),
            "operation": situation.get("operation"),
            "gateway_response_id": str(getattr(response, "response_id", "") or ""),
            "physics": physics,
            "witnessed_at": time.time(),
        })
        return True

    # -- the three physics doors -------------------------------------------

    def _habitat_projection(self, situation: Mapping[str, Any]):
        """Her mapping, her functions, called on her side of the wire.

        Returns (dimensions, amplitudes, action_shim, consequence_shim) or
        None if her Habitat module is unavailable.  This module computes
        neither the dimensions nor the amplitudes -- it only supplies the
        nouns her mapping already knows how to read.
        """
        try:
            from aurora_habitat import (
                _actual_consequence_dimensions,
                _consequence_axis_amplitudes,
            )
        except Exception:
            return None

        action = _ShimAction(situation)
        consequence = _ShimConsequence(situation)
        pre_state = dict(situation.get("pre_state") or {})
        post_state = dict(situation.get("post_state") or {})
        try:
            dimensions = _actual_consequence_dimensions(
                action, consequence, pre_state, post_state)
            amplitudes = _consequence_axis_amplitudes(
                action, consequence, pre_state, post_state)
        except Exception as exc:
            self.last_error = f"projection_failed: {type(exc).__name__}: {exc}"
            return None
        return dimensions, amplitudes, action, consequence

    def _route_to_constraint_physics(self, situation: Mapping[str, Any]
                                     ) -> Dict[str, Any]:
        projection = self._habitat_projection(situation)
        if projection is None:
            return {"projected": False}
        dimensions, amplitudes, action, consequence = projection

        result = {
            "projected": True,
            "consequence_dimensions": list(dimensions),
            "pressure_injected": self._emit_constraint_evidence(
                situation, amplitudes, action, consequence),
            "sediment_deposited": self._deposit_sediment(
                situation, dimensions, amplitudes, action, consequence),
            "resolution_pressure": self._emit_resolution_pressure(
                situation, dimensions, consequence),
        }
        return result

    def _emit_constraint_evidence(self, situation: Mapping[str, Any],
                                  amplitudes: Mapping[str, float],
                                  action: Any, consequence: Any) -> bool:
        """Door 2: the same WaveformPressurePump entry point her perceptual
        subsystems and her Habitat already use.  Never a Praxis-only channel."""
        ifield = self.systems.get("identity_field")
        pump = self.systems.get("pressure_pump")
        if ifield is None or pump is None:
            return False
        try:
            from aurora_waveform_pressure import PressureDisturbance
            disturbance = PressureDisturbance(
                source=f"praxis:{action.territory}:{action.operation}",
                axis_amplitudes=dict(amplitudes),
                intensity=0.55 if consequence.success else 0.30,
                coupling_mode="full",
            )
            pump.inject(disturbance, ifield,
                        qao=self.systems.get("quasiarch_observer"))
        except Exception as exc:
            self.last_error = f"pressure_failed: {type(exc).__name__}: {exc}"
            return False
        with self._lock:
            self.pressure_injections += 1
        return True

    def _deposit_sediment(self, situation: Mapping[str, Any],
                          dimensions: Iterable[str],
                          amplitudes: Mapping[str, float],
                          action: Any, consequence: Any) -> bool:
        """Door 3: the raw event into SediMemory with a REAL ConstraintVector.

        This is the object the audit found missing on the sensory path: a
        physics object constructed at admission rather than post-hoc from
        counters.  Content only -- no interpretation of what it meant.
        """
        sedimemory = self.systems.get("sedimemory")
        if sedimemory is None or not hasattr(sedimemory, "ingest_event"):
            return False
        try:
            from aurora_internal.aurora_constraint_manifold_patched import (
                ConstraintVector,
            )
            from foundational_contract import ExistenceMode

            constraint_vector = ConstraintVector(
                X=max(0.05, float(amplitudes.get("X", 0.0))),
                T=0.2,
                N=float(amplitudes.get("N", 0.0)),
                B=float(amplitudes.get("B", 0.0)),
                A=float(amplitudes.get("A", 0.0)),
            )
            content = {
                "source": "praxis",
                "territory": action.territory,
                "operation": action.operation,
                "actor": action.actor,
                "affected_entities": list(consequence.affected_entities),
                "entity_ids": list(consequence.affected_entities),
                "action_id": action.action_id,
                "episode_id": situation.get("episode_id"),
                "success": consequence.success,
                "state_changed": consequence.state_changed,
                "permission_result": consequence.permission_result,
                "consequence_dimensions": list(dimensions),
                "intention_context": "",
            }
            sedimemory.ingest_event(
                content=content,
                constraint_vector=constraint_vector,
                source="praxis",
                existence_mode=(ExistenceMode.AGENTIC
                                if action.actor == self.agent_id
                                else ExistenceMode.PERSISTENT),
            )
        except Exception as exc:
            self.last_error = f"sediment_failed: {type(exc).__name__}: {exc}"
            return False
        with self._lock:
            self.sediment_deposits += 1
        return True

    def _emit_resolution_pressure(self, situation: Mapping[str, Any],
                                  dimensions: Iterable[str],
                                  consequence: Any) -> bool:
        """Door 4: route the real consequence through adaptive resolution.

        No candidate-conditioned counterfactual is ever supplied, because
        Praxis has none to give -- only ambient participation from what
        actually happened.  A staged candidate therefore cannot be retained on
        Praxis evidence alone, which is the correct outcome.
        """
        try:
            from aurora_habitat import consequence_axis_profile
            from aurora_representational_address import RepresentationalRef
            from aurora_representational_resolution import (
                record_ref_participation_from_scores,
            )
        except Exception:
            return False

        try:
            axis_profile = consequence_axis_profile(list(dimensions))
            participating = {
                RepresentationalRef.for_c1(axis, "OPERATOR", "A").encode(): weight
                for axis, weight in axis_profile.items() if float(weight) > 0.0
            }
            agency_ref = RepresentationalRef.for_c1("A", "OPERATOR", "A").encode()
            participating[agency_ref] = max(
                float(participating.get(agency_ref, 0.0)),
                0.35 if consequence.success else 0.15)
            if not consequence.success:
                boundary_ref = RepresentationalRef.for_c1("B", "OPERATOR", "A").encode()
                participating[boundary_ref] = max(
                    float(participating.get(boundary_ref, 0.0)), 0.20)

            scores = {
                "succeeded": 1.0 if (consequence.success and consequence.state_changed) else 0.0,
                "state_changed": 1.0 if consequence.state_changed else 0.0,
                "was_measured_response": 0.0,
            }
            context_tag = (f"praxis:{situation.get('territory', 'space')}:"
                           f"{consequence.operation}:{consequence.actor}")
            for ref_encoded in participating:
                record_ref_participation_from_scores(
                    self.systems, ref_encoded, scores,
                    source="praxis_environment", context_tag=context_tag,
                )
        except Exception as exc:
            self.last_error = f"resolution_failed: {type(exc).__name__}: {exc}"
            return False
        with self._lock:
            self.resolution_emissions += 1
        return True

    # -- offline resilience -------------------------------------------------

    def _spool(self, record: Mapping[str, Any]) -> None:
        spool = self._load_spool()
        spool.append(dict(record))
        if len(spool) > SPOOL_LIMIT:
            del spool[: len(spool) - SPOOL_LIMIT]
        self._write_json(self._spool_path, {"spool": spool, "updated_at": time.time()})

    def _load_spool(self) -> List[Dict[str, Any]]:
        if not self._spool_path.exists():
            return []
        try:
            raw = json.loads(self._spool_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        entries = raw.get("spool", []) if isinstance(raw, Mapping) else []
        return [dict(e) for e in entries if isinstance(e, Mapping)]

    def _drain_spool(self) -> int:
        spool = self._load_spool()
        if not spool:
            return 0
        remaining: List[Dict[str, Any]] = []
        drained = 0
        for entry in spool:
            kind = str(entry.get("kind", ""))
            payload = entry.get("payload") or {}
            if kind == "unsent_action":
                if self._request("/act", method="POST", payload=payload):
                    drained += 1
                    continue
                remaining.append(entry)
            elif kind == "unwitnessed_situation":
                try:
                    situation = validate_incoming_situation(payload)
                except PraxisContractBreach as breach:
                    self._record_breach(breach)
                    continue
                if self._witness(situation):
                    drained += 1
                    continue
                remaining.append(entry)
        self._write_json(self._spool_path, {"spool": remaining,
                                            "updated_at": time.time()})
        return drained

    # -- persistence --------------------------------------------------------

    def _write_json(self, path: Path, payload: Any) -> None:
        if atomic_write_json is not None:
            try:
                atomic_write_json(path, payload)
                return
            except Exception:
                pass
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, default=str),
                            encoding="utf-8")
        except Exception:
            pass

    def _append_jsonl(self, path: Path, record: Mapping[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass

    def _persist_state(self) -> None:
        self._write_json(self._state_path, self.status())

    def _record_breach(self, breach: PraxisContractBreach) -> None:
        entry = breach.to_dict()
        with self._lock:
            self.breaches.append(entry)
            if len(self.breaches) > 200:
                del self.breaches[:-200]
        self._append_jsonl(self._breach_path, entry)

    # -- discovery -----------------------------------------------------------

    def handshake(self) -> str:
        """Ask /hello who is there and whether we can speak.

        Decides compatibility on HER side from her own constants.  Stores only
        the identity fields hello is permitted to carry; anything else a peer
        volunteers is ignored rather than kept.
        """
        self.last_handshake_at = time.time()
        reply = self._request("/hello")
        if self.discovery == "incompatible" and not reply:
            return self.discovery          # refused on the header itself
        if not reply:
            self.discovery = "unreachable"
            self.peer = {}
            return self.discovery
        if reply.get("service") != PRAXIS_SERVICE_NAME or \
                reply.get("protocol") != PRAXIS_PROTOCOL_NAME:
            self.discovery = "not_praxis"
            self.peer = {}
            return self.discovery
        offered = reply.get("compatible_protocol_versions") or \
            [reply.get("protocol_version")]
        try:
            offered = {int(v) for v in offered if v is not None}
        except Exception:
            offered = set()
        self.peer = {
            "protocol_version": reply.get("protocol_version"),
            "contract_version": reply.get("contract_version"),
        }
        if not offered & set(PRAXIS_COMPATIBLE_PROTOCOL_VERSIONS) or \
                reply.get("contract_version") != PRAXIS_CONTRACT_VERSION:
            self.discovery = "incompatible"
        elif reply.get("accepting") is False:
            self.discovery = "not_accepting"
        else:
            self.discovery = "compatible"
        return self.discovery

    def _channel_open(self) -> bool:
        """Handshake when we have never succeeded or when the last attempt is
        stale; pull only through an open, compatible channel.  Fails closed:
        anything but `compatible` means no situations cross."""
        stale = (time.time() - self.last_handshake_at) >= HANDSHAKE_RETRY_S
        if self.discovery != "compatible" or stale:
            self.handshake()
        return self.discovery == "compatible"

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        self._stop.clear()
        self._paused.clear()
        self._thread = threading.Thread(target=self._run, name="aurora-praxis",
                                        daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if not self._paused.is_set() and self._capacity() \
                        and self._channel_open():
                    if self.field_lock is not None:
                        acquired = self.field_lock.acquire(blocking=False)
                        if acquired:
                            try:
                                # Capacity was checked above, before taking
                                # the lock; see pull_once for why it must not
                                # be re-checked while we hold it.
                                self.pull_once(check_capacity=False)
                            finally:
                                self.field_lock.release()
                    else:
                        self.pull_once()
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
            self._stop.wait(self.poll_interval_s)

    def _status_label(self) -> str:
        """One word for the Hub, matching the historical-experience shape so
        the Dart side parses both the same way."""
        if not (self._thread and self._thread.is_alive()):
            return "stopped"
        if self._paused.is_set():
            return "paused"
        if self.discovery == "incompatible":
            return "incompatible"
        if self.discovery == "not_praxis":
            return "not_praxis"
        if self.discovery == "not_accepting":
            return "paused_by_praxis"
        if not self.online:
            return "offline"
        return "running"

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._status_label(),
                "episodes_lost": int(getattr(self, "episodes_lost", 0)),
                "discovery": self.discovery,
                "protocol_version": PRAXIS_PROTOCOL_VERSION,
                "peer": dict(self.peer),
                "contract_version": PRAXIS_CONTRACT_VERSION,
                "endpoint": self.endpoint,
                "agent_id": self.agent_id,
                "episode_id": self.episode_id,
                "thread_alive": bool(self._thread and self._thread.is_alive()),
                "paused": self._paused.is_set(),
                "online": self.online,
                "situations_witnessed": self.situations_witnessed,
                "pressure_injections": self.pressure_injections,
                "sediment_deposits": self.sediment_deposits,
                "resolution_emissions": self.resolution_emissions,
                "pulls_attempted": self.pulls_attempted,
                "last_pull_at": self.last_pull_at,
                "spooled": len(self._load_spool()),
                "contract_breaches": len(self.breaches),
                "recent_breaches": list(self.breaches[-5:]),
                "last_error": self.last_error,
            }


# ---------------------------------------------------------------------------
# Module-level entry points (mirrors the historical experience trio)
# ---------------------------------------------------------------------------

_bridge: Optional[PraxisBridge] = None


def start_praxis_bridge(
    systems: Mapping[str, Any],
    *,
    state_dir: str,
    endpoint: str = DEFAULT_ENDPOINT,
    field_lock: Optional[threading.Lock] = None,
    live_idle: Optional[Callable[[], bool]] = None,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
) -> Optional[PraxisBridge]:
    global _bridge
    if _bridge is not None:
        return _bridge
    try:
        bridge = PraxisBridge(
            systems, state_dir=state_dir, endpoint=endpoint,
            field_lock=field_lock, live_idle=live_idle,
            poll_interval_s=poll_interval_s,
        )
    except Exception:
        return None
    bridge.start()
    _bridge = bridge
    return bridge


def get_bridge() -> Optional[PraxisBridge]:
    return _bridge


def praxis_status() -> Dict[str, Any]:
    if _bridge is None:
        return {"status": "not_initialized", "thread_alive": False}
    return _bridge.status()


def praxis_pause() -> Dict[str, Any]:
    if _bridge is not None:
        _bridge.pause()
    return praxis_status()


def praxis_resume() -> Dict[str, Any]:
    if _bridge is not None:
        _bridge.resume()
    return praxis_status()


def stop_praxis_bridge(timeout: float = 3.0) -> None:
    global _bridge
    if _bridge is not None:
        _bridge.stop(timeout=timeout)
        _bridge = None
