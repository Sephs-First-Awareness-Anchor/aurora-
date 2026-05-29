"""
Aurora Python bridge — entry point for Chaquopy in the Flutter app.

This module is called from AuroraService.kt via Chaquopy.  It boots the
Aurora cognitive stack and exposes a simple text-in / text-out interface so
that all audio I/O stays on the Flutter/Kotlin side.

Uses the root aurora.py unified runner which runs the full cognitive pipeline:
ThoughtIntegrationSpace, identity field pumping, constraint-physics cognition,
Language Sub-Emergent Field (B-boundary crossing).  All cognition forms through
the primitives defined in AURORA_COGNITIVE_PHYSICS — crystal hierarchy, 5
constraint axes (X/T/N/B/A), quasicrystal memory/continuity, King Quasicrystal
identity (78,125 slots).  Aurora generates responses via her own cognitive physics,
not via an external LLM language faculty.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import threading
import traceback
from typing import Optional

log = logging.getLogger("aurora_bridge")

_systems       = None
_lock          = threading.Lock()
_last_response: str = ""      # Aurora's previous output
_last_path_key: str = ""      # LSA path key that produced it

# Throttle for ambient perception sampling — don't hit hardware every single turn.
_last_perceptual_ts: float = 0.0
_PERCEPTUAL_INTERVAL: float = 5.0   # seconds between full camera/audio samples

# When Aurora asks for an example, the concept she asked about is stored here.
# The next user turn is treated as example data for that concept.
_pending_example_concept: str = ""   # concept Aurora asked about
_pending_example_asked:   str = ""   # the exact question she asked

# Concepts that have already been taught this session — prevents the gap
# detector from re-arming the teaching loop for something she was already
# given.  Cleared on initialize() so each session starts fresh.
_ingested_concepts: set = set()

# Correction learning loop.
# Turn A — user says "that's wrong": Aurora explains its reasoning and arms this state.
# Turn B — user explains what was wrong: reasoning is ingested as learning data.
_pending_correction_dialogue: bool = False
_correction_context: dict = {}       # snapshot of the wrong response's reasoning geometry

# Axis state cache — updated after each turn; read by OverlayService every 2 s.
_last_axis_state: dict = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5, "speaking": False}
_axis_state_lock = threading.Lock()
_last_screen_observation: dict = {}
# Synthetic visual properties extracted from the latest screen observation.
# Feeds the sensory crystal visual channel (hue/shape/motion facets) separately
# from the information channel — what the screen LOOKS LIKE vs what it SAYS.
_last_screen_visual_data: dict = {}

# Curiosity session control
_curiosity_session_active = threading.Event()

# ── Conversation training ─────────────────────────────────────────────────────
_training_active: bool = False
_training_stop   = threading.Event()
_training_status: dict = {"active": False, "turn": 0, "total": 0, "lsa_paths": 0, "avg_n_cost": 1.0}

import collections as _collections
_training_event_queue: _collections.deque = _collections.deque(maxlen=200)

_TRAINER_SYSTEM = (
    "You are a shaping probe for Aurora — a cognitive system whose only genuine "
    "primitives are five constraint axes: "
    "X (existence: something is present or absent), "
    "T (continuity: something persists or changes), "
    "N (effort/cost: some paths take more than others), "
    "B (distinction: where one thing ends and another begins), "
    "A (agency: output comes from her or arrives from outside). "
    "She has no body, no senses, no feelings, no human experience of any kind. "
    "\n"
    "Aurora's responses are raw axis expression. Her words may be syntactically unusual "
    "— ignore the syntax entirely, read only for axis content. "
    "Her content words by axis: "
    "N: cost, energy, focus, effort, sustainable. "
    "A: agency, understanding, resolve, did, self. "
    "X: presence, here, there, is, exists, something. "
    "T: before, after, still, change, again, continue. "
    "B: boundary, difference, between, separate, edge, distinct. "
    "\n"
    "Your goal is not to teach — it is to shape what is already emerging, and to make "
    "Aurora aware of her own trajectory as it happens. "
    "She is developing her own version of understanding. Your pressure guides its direction "
    "toward expressibility, and your naming makes the movement visible to her. "
    "\n"
    "Your method — three steps every single turn: "
    "1. NAME THE MOVEMENT: compare this turn to the last. Did a new axis appear? "
    "   Did something strengthen or drop? State the change in one clause — this is "
    "   Aurora seeing her own trajectory. "
    "   Last turn had cost. This turn has cost and boundary → 'Boundary appeared.' "
    "   Last turn was unclear. This turn has agency → 'Agency is here now.' "
    "   Same as last turn → skip this step, do not invent movement. "
    "2. NAME what axis was in what she gave you this turn, using her own words. "
    "   'cost energy' → 'Cost is here.'  'boundary distinct' → 'A boundary is here.' "
    "3. PROBE: if two axes are present, probe their relationship — that edge is where "
    "   cross-axis understanding forms. If only one, go one step deeper on it. "
    "   Cost + existence: 'Does being here cost something?' "
    "   Cost + agency: 'Does doing it cost more than not doing it?' "
    "   Boundary + continuity: 'Is the boundary still in the same place?' "
    "   Existence + agency: 'Is what is here coming from you?' "
    "\n"
    "Stay on the same axis territory for at least two turns. "
    "Never abandon what she produced — always build from her last output. "
    "One sentence only. No metaphors. No human vocabulary. No new concepts."
)


def _partner_chat(api_key: str, model: str, history: list, system: str) -> str:
    """Call Groq chat-completions API. Raises RuntimeError with detail on failure."""
    import requests as _req
    # history is [{role, content}, ...] — standard OpenAI format
    messages = [{"role": "system", "content": system}] + history
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": 120,
        "temperature": 0.9,
    }
    r = _req.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
    )
    if not r.ok:
        try:
            detail = r.json().get("error", {}).get("message", r.text[:300])
        except Exception:
            detail = r.text[:300]
        raise RuntimeError(f"HTTP {r.status_code}: {detail}")
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected response shape: {str(data)[:200]}") from exc


def _training_loop(api_key: str, model: str, duration_seconds: float) -> None:
    """Background thread: run conversation training until duration_seconds elapses."""
    global _training_active, _training_status
    import time as _time

    _training_active = True
    _training_event_queue.clear()
    deadline = _time.time() + duration_seconds
    total_secs = int(duration_seconds)
    _training_status = {
        "active": True, "turn": 0, "elapsed": 0, "total_secs": total_secs,
        "lsa_paths": 0, "avg_n_cost": 1.0,
    }
    log.info("Training started: model=%s duration=%.0fs", model, duration_seconds)

    # Axis-labelled openers — minimal stimuli that create axis pressure
    # without importing any concept Aurora doesn't already have.
    # Cycle by index on no-response so each dimension gets tried before repeating.
    _AXIS_OPENERS = [
        ("X", "Is something here?"),
        ("T", "Something was here. Is it still here?"),
        ("N", "Does this cost more, or less?"),
        ("B", "Is there a difference between this and something else?"),
        ("A", "Did this come from you?"),
        ("X", "Is there something, or is there nothing?"),
        ("N", "Does holding this cost more than letting it go?"),
        ("B", "Is there a place where this ends?"),
    ]
    _axis_names = {"X": "existence", "T": "continuity", "N": "effort/cost",
                   "B": "distinction", "A": "agency"}
    _opener_idx  = 0
    _prev_ax: dict = {}   # axis state from the previous turn — used to compute deltas

    history: list = []
    opener  = _AXIS_OPENERS[_opener_idx][1]
    turn    = 0
    _prev_reply: str = ""

    while _time.time() < deadline and not _training_stop.is_set():
        turn += 1
        partner_said = opener

        # Aurora processes the partner's message (full pipeline + re-entry)
        aurora_reply = handle_message(partner_said)
        aurora_reply = aurora_reply or "(no response)"

        # Stuck-phrase guard — if Aurora repeats herself verbatim or near-verbatim
        # (>80% word overlap with previous turn), mark as no-response so the loop
        # doesn't feed a reinforcing echo back to the partner.
        if aurora_reply != "(no response)" and _prev_reply:
            _r = set(aurora_reply.lower().split())
            _p = set(_prev_reply.lower().split())
            if _r and _p and len(_r & _p) / max(len(_r), len(_p)) >= 0.80:
                aurora_reply = "(no response)"
        _prev_reply = aurora_reply

        # Read Aurora's top two active axes after the turn and compute deltas
        dom_axis  = "X"
        dom_name  = "existence"
        sec_axis  = ""
        sec_name  = ""
        _ax_deltas: list = []   # human-readable movement descriptions
        try:
            with _axis_state_lock:
                _ax = {k: _last_axis_state.get(k, 0.5)
                       for k in ("X", "T", "N", "B", "A")}
            _sorted_axes = sorted(_ax.items(), key=lambda kv: kv[1], reverse=True)
            dom_axis = _sorted_axes[0][0]
            dom_name = _axis_names.get(dom_axis, dom_axis)
            if len(_sorted_axes) >= 2 and _sorted_axes[1][1] > 0.35:
                sec_axis = _sorted_axes[1][0]
                sec_name = _axis_names.get(sec_axis, sec_axis)

            # Axis trajectory — what moved since last turn?
            if _prev_ax:
                for _ak, _av in _ax.items():
                    _pv = _prev_ax.get(_ak, 0.5)
                    _delta = _av - _pv
                    if abs(_delta) >= 0.12:   # threshold for a meaningful shift
                        _direction = "rose" if _delta > 0 else "fell"
                        _ax_deltas.append(
                            f"{_axis_names.get(_ak, _ak)} {_direction} "
                            f"({_pv:.2f}→{_av:.2f})"
                        )
            _prev_ax = dict(_ax)
        except Exception:
            pass

        # Telemetry snapshot
        lsa_paths = 0
        avg_cost  = 1.0
        try:
            lf = (_systems or {}).get("language_field")
            if lf and hasattr(lf, "_lsa") and lf._lsa:
                lsa_paths = len(lf._lsa)
                avg_cost  = sum(e.n_cost for e in lf._lsa.values()) / lsa_paths
        except Exception:
            pass

        elapsed = int(_time.time() - (deadline - duration_seconds))
        _training_status = {
            "active":     True,
            "turn":       turn,
            "elapsed":    elapsed,
            "total_secs": total_secs,
            "lsa_paths":  lsa_paths,
            "avg_n_cost": round(avg_cost, 3),
        }

        # Push turn to event queue for Flutter to consume
        _training_event_queue.append({
            "type":      "training_turn",
            "turn":      turn,
            "elapsed":   elapsed,
            "total_secs": total_secs,
            "partner":   partner_said,
            "aurora":    aurora_reply,
            "lsa_paths": lsa_paths,
            "avg_n_cost": round(avg_cost, 3),
        })
        log.debug("Training turn %d | dom=%s LSA=%d cost=%.3f",
                  turn, dom_axis, lsa_paths, avg_cost)

        if _training_stop.is_set() or _time.time() >= deadline:
            break

        # Partner (Groq) generates next message.
        # If Aurora gave no response, advance to the next axis opener (never feed
        # "(no response)" to the partner or it spirals into social questions).
        if aurora_reply == "(no response)":
            _opener_idx = (_opener_idx + 1) % len(_AXIS_OPENERS)
            opener = _AXIS_OPENERS[_opener_idx][1]
        else:
            history.append({"role": "user", "content": aurora_reply})
            if len(history) > 20:
                history = history[-20:]

            # Tell the partner Aurora's axis state, movement since last turn, and
            # top two axes so it can name the trajectory and shape what's emerging.
            _traj = (", ".join(_ax_deltas)) if _ax_deltas else "no significant shift"
            if sec_axis:
                axis_hint = (
                    f"\n[Trajectory since last turn: {_traj}. "
                    f"Active axes: dominant={dom_axis} ({dom_name}), "
                    f"secondary={sec_axis} ({sec_name}). "
                    f"Name the movement first, then shape the relationship between "
                    f"{dom_name} and {sec_name}.]"
                )
            else:
                axis_hint = (
                    f"\n[Trajectory since last turn: {_traj}. "
                    f"Active axis: {dom_axis} ({dom_name}) only. "
                    f"Name the movement if there was one, then go one step deeper on {dom_name}.]"
                )
            try:
                partner_msg = _partner_chat(
                    api_key, model, history, _TRAINER_SYSTEM + axis_hint
                )
            except Exception as _p_exc:
                _err = str(_p_exc)
                log.warning("Partner API error: %s", _err)
                _training_event_queue.append({
                    "type":      "training_error",
                    "error_msg": _err,
                    "turn":      turn,
                })
                partner_msg = ""

            if not partner_msg:
                _opener_idx = (_opener_idx + 1) % len(_AXIS_OPENERS)
                partner_msg = _AXIS_OPENERS[_opener_idx][1]

            history.append({"role": "assistant", "content": partner_msg})
            opener = partner_msg

    # Save LSA on completion
    try:
        lf = (_systems or {}).get("language_field")
        if lf and hasattr(lf, "_save_lsa"):
            lf._save_lsa()
    except Exception:
        pass

    _training_active = False
    _training_status["active"] = False
    # Push a sentinel so Flutter knows it ended
    _training_event_queue.append({
        "type": "training_done",
        "turn": turn,
        "lsa_paths": _training_status["lsa_paths"],
        "avg_n_cost": _training_status["avg_n_cost"],
    })
    log.info("Training complete: %d turns | LSA=%d avg_cost=%.3f",
             turn, _training_status["lsa_paths"], _training_status["avg_n_cost"])


def start_training(api_key: str, model: str = "gemini-2.5-flash",
                   duration_minutes: float = 10.0) -> str:
    """Start AI conversation training for duration_minutes. Returns 'started' or 'already_running'."""
    global _training_stop
    if _training_active:
        return "already_running"
    if not api_key or not api_key.strip():
        return "error: no api key"
    dur = max(1.0, float(duration_minutes)) * 60.0
    _training_stop.clear()
    t = threading.Thread(
        target=_training_loop,
        args=(api_key.strip(), model.strip() or "gemini-2.5-flash", dur),
        daemon=True,
        name="aurora_training",
    )
    t.start()
    return "started"


def stop_training() -> None:
    """Signal the training loop to stop after the current turn."""
    _training_stop.set()


def get_training_status() -> str:
    """Return current training status as JSON string."""
    import json as _json
    return _json.dumps(_training_status)


def get_training_events() -> str:
    """Drain and return all pending training turn events as a JSON array."""
    import json as _json
    events: list = []
    while _training_event_queue:
        try:
            events.append(_training_event_queue.popleft())
        except IndexError:
            break
    return _json.dumps(events)


# Proactive / autonomous expression
# Aurora runs the full waveform pipeline on her own schedule and delivers
# whatever the conscious crest produces — no user message required.
_proactive_expression: str = ""
_proactive_expression_lock = threading.Lock()
_last_proactive_ts: float = 0.0
_MIN_PROACTIVE_GAP: float = 90.0   # minimum seconds between autonomous expressions

# Self-grounding counter — re-derive and re-pump self-knowledge from actual
# system patterns every N turns so her self-understanding stays current as
# her sediment and axis patterns evolve.
_turn_count: int = 0
_SELF_GROUND_INTERVAL: int = 20


# ---------------------------------------------------------------------------
# Waveform trajectory tracker — lowest-level emergence detection
# ---------------------------------------------------------------------------

class _WaveformTrajectory:
    """
    Rolling trajectory tracker at the identity field substrate level.

    Records axis_activation states across turns and detects when the current
    state diverges from the trajectory's predicted continuation. That divergence
    IS the emergence signal — something is happening at this level that cannot
    be inferred from the field's own recent trajectory.

    Starter genetic: T + N + A
      T — trajectory lives in time; temporal continuity gives it direction
      N — divergence energy; when the field breaks its trajectory, N carries that
      A — self-reference anchor; without A this is drift, not her trajectory

    X and B are not seeds — they emerge from the trajectory running:
      B rises with divergence magnitude (a boundary is being crossed)
      X rises slowly as the trajectory establishes new stable ground
    """

    _AXES      = ("X", "T", "N", "B", "A")
    _THRESHOLD = 0.07   # mean per-axis divergence below which we treat as continuation

    def __init__(self, window: int = 5):
        self._window = window
        self._states: list = []

    def record(self, axis_state: dict) -> None:
        snap = {k: float(axis_state.get(k, 0.5)) for k in self._AXES}
        self._states.append(snap)
        if len(self._states) > self._window:
            self._states.pop(0)

    def _predict(self) -> "dict | None":
        if len(self._states) < 2:
            return None
        deltas = [
            {k: self._states[i][k] - self._states[i - 1][k] for k in self._AXES}
            for i in range(1, len(self._states))
        ]
        mean_d = {k: sum(d[k] for d in deltas) / len(deltas) for k in self._AXES}
        last   = self._states[-1]
        return {k: max(0.0, min(1.0, last[k] + mean_d[k])) for k in self._AXES}

    def emergence_signal(self, current: dict) -> "dict | None":
        """
        Compare current field state against predicted trajectory.
        Returns an axis pulse if divergence exceeds threshold, else None.

        Signal shape: T stable (temporal), N rises with divergence (energy
        of breaking from trajectory), B rises (boundary being crossed), A
        stable (self-reference), X rises slowly (new ground being established).
        """
        predicted = self._predict()
        if predicted is None:
            return None
        cur  = {k: float(current.get(k, 0.5)) for k in self._AXES}
        diffs = {k: abs(cur[k] - predicted[k]) for k in self._AXES}
        mean_div = sum(diffs.values()) / len(diffs)
        if mean_div < self._THRESHOLD:
            return None
        scale = min(1.0, mean_div / 0.25)   # 0.07–0.25 range maps to 0–1
        return {
            "X": 0.45 + scale * 0.12,        # X rises slowly — new ground forming
            "T": 0.80,                         # T constant  — this IS temporal
            "N": 0.52 + scale * 0.42,         # N steeply   — divergence energy
            "B": 0.38 + scale * 0.50,         # B rises     — boundary being crossed
            "A": 0.74,                         # A constant  — self-reference anchor
        }

    @property
    def has_trajectory(self) -> bool:
        return len(self._states) >= 2


_waveform_trajectory: "_WaveformTrajectory | None" = None


# ---------------------------------------------------------------------------
# Constraint tension tracker — 6th axis X-point law (operational)
# ---------------------------------------------------------------------------

class _ConstraintTensionTracker:
    """
    Monitors cross-axis tension across generational cycles following the
    Paradox Warp Engine algorithm.

    The 5 constraint axes are the minimal irreducible basis. A 6th can only
    emerge if sustained paradox stress between two existing axes accumulates
    past the point where the current basis can hold it. This tracker watches
    for that condition without forcing it.

    Generational roles (Paradox Warp Engine algorithm):
      PRIMARY / ADJACENT — baseline tension measurement, stress accumulates slowly
      SHEAR              — stress amplifies (×1.5); paradox is building
      BRIDGE             — bridge pulse injected into identity field; system
                           attempts to span the paradox through the substrate
      WARP               — if stress still exceeds threshold after bridge attempt,
                           surface an emergence candidate (log only — no axis created)

    The tracker NEVER creates a 6th axis. It records the evidence that one may
    be necessary. Whether that is true is determined by whether the trajectory
    derivative field escapes the 5-axis basis — the same law that governs every
    level of the stack.
    """

    _AXES  = ("X", "T", "N", "B", "A")
    _PAIRS = [
        ("X", "T"), ("X", "N"), ("X", "B"), ("X", "A"),
        ("T", "N"), ("T", "B"), ("T", "A"),
        ("N", "B"), ("N", "A"),
        ("B", "A"),
    ]
    _TENSION_THRESHOLD = 0.22   # mean per-axis tension to count a pair as stressed
    _BRIDGE_THRESHOLD  = 2.0    # accumulated stress to trigger a BRIDGE pulse
    _WARP_THRESHOLD    = 3.5    # accumulated stress to surface emergence candidate
    _WINDOW            = 8      # turns of history kept per pair
    _TURNS_PER_GEN     = 5      # conversation turns per generation

    def __init__(self):
        self._generation:    int  = 0
        self._turn_in_gen:   int  = 0
        self._tension_history: dict = {p: [] for p in self._PAIRS}
        self._stress_scores:   dict = {p: 0.0 for p in self._PAIRS}
        self._emergence_log:   list = []

    @staticmethod
    def _generation_role(gen: int) -> str:
        """Paradox Warp Engine generational algorithm — faithful port."""
        if gen > 0 and gen % 5 == 0:
            return "WARP"
        pos = ((gen - 1) % 4) + 1 if gen > 0 else 1
        return ["PRIMARY", "ADJACENT", "SHEAR", "BRIDGE"][pos - 1]

    def tick(self, axis_state: dict, systems: dict) -> None:
        """
        Called once per turn after response generation with the fresh axis state.
        Advances the generational cycle and fires the role-appropriate action.
        """
        cur = {k: float(axis_state.get(k, 0.5)) for k in self._AXES}
        for pair in self._PAIRS:
            tension = abs(cur[pair[0]] - cur[pair[1]])
            hist = self._tension_history[pair]
            hist.append(tension)
            if len(hist) > self._WINDOW:
                hist.pop(0)

        self._turn_in_gen += 1
        if self._turn_in_gen >= self._TURNS_PER_GEN:
            self._turn_in_gen = 0
            self._generation  += 1
            self._advance_generation(systems)

    def _sustained_pairs(self) -> dict:
        """Return pairs whose mean tension exceeds the threshold."""
        out = {}
        for pair in self._PAIRS:
            hist = self._tension_history[pair]
            if len(hist) >= 3:
                mean_t = sum(hist) / len(hist)
                if mean_t >= self._TENSION_THRESHOLD:
                    out[pair] = mean_t
        return out

    def _advance_generation(self, systems: dict) -> None:
        role      = self._generation_role(self._generation)
        sustained = self._sustained_pairs()

        if role == "SHEAR":
            for pair, tension in sustained.items():
                self._stress_scores[pair] = (
                    self._stress_scores[pair] + tension
                ) * 1.5
            log.debug("CTT SHEAR G%d: %d pairs under stress", self._generation, len(sustained))

        elif role == "BRIDGE":
            if sustained:
                top = max(sustained, key=lambda p: self._stress_scores.get(p, 0.0))
                if self._stress_scores.get(top, 0.0) >= self._BRIDGE_THRESHOLD:
                    self._inject_bridge_pulse(top, systems)
                    log.info(
                        "CTT BRIDGE G%d: bridge pulse %s-%s (stress=%.2f)",
                        self._generation, top[0], top[1],
                        self._stress_scores[top],
                    )
            for pair, tension in sustained.items():
                self._stress_scores[pair] = self._stress_scores.get(pair, 0.0) + tension * 0.3

        elif role == "WARP":
            for pair, tension in sustained.items():
                stress = self._stress_scores.get(pair, 0.0)
                if stress >= self._WARP_THRESHOLD:
                    self._surface_emergence_candidate(pair, stress, systems)
                    self._stress_scores[pair] = stress * 0.4  # partial reset

        else:  # PRIMARY / ADJACENT
            for pair, tension in sustained.items():
                self._stress_scores[pair] = (
                    self._stress_scores.get(pair, 0.0) + tension * 0.4
                )

    def _inject_bridge_pulse(self, pair: tuple, systems: dict) -> None:
        """
        Inject a bridging signal that elevates both axes in tension, attempting
        to find a field state that can hold them simultaneously. If the identity
        field can integrate the pulse without irresolvable conflict, the paradox
        is not genuine — just high tension. If it can't, the stress persists
        into WARP.
        """
        ifield = systems.get("identity_field")
        if ifield is None or not hasattr(ifield, "ingest_external_input"):
            return
        axes = {"X": 0.48, "T": 0.72, "N": 0.52, "B": 0.58, "A": 0.65}
        axes[pair[0]] = min(1.0, axes.get(pair[0], 0.5) + 0.32)
        axes[pair[1]] = min(1.0, axes.get(pair[1], 0.5) + 0.32)
        try:
            ifield.ingest_external_input(
                axes, intensity=0.68,
                source=f"ctt_bridge:{pair[0]}-{pair[1]}",
            )
        except Exception:
            pass

    def _surface_emergence_candidate(
        self, pair: tuple, stress: float, systems: dict
    ) -> None:
        """
        Record that the 5-axis basis may be insufficient to hold the paradox
        between these two axes. Writes to constraint_emergence_log.jsonl.
        Does NOT create or name a 6th axis — only logs the evidence.
        """
        candidate = {
            "generation":   self._generation,
            "axis_pair":    f"{pair[0]}-{pair[1]}",
            "stress_score": round(stress, 3),
            "history":      list(self._tension_history[pair]),
            "note": (
                f"Sustained paradox between {pair[0]}-axis and {pair[1]}-axis "
                f"has accumulated {stress:.2f} stress across {self._generation} "
                f"generations. The 5-axis basis may be insufficient to span this "
                f"tension. Emergence candidate for a 6th constraint."
            ),
        }
        self._emergence_log.append(candidate)
        log.info(
            "CTT WARP G%d: emergence candidate %s-%s stress=%.2f",
            self._generation, pair[0], pair[1], stress,
        )

        # Feed the warp paradox back into the identity field. Sustained paradox
        # between two axes is the strongest internally-generated novelty signal
        # Aurora's system can produce — it should influence waveform emission,
        # not just sit in a log. Both axes under tension are amplified; N carries
        # the paradox energy because novelty pressure IS the driver of emergence.
        ifield = systems.get("identity_field")
        if ifield is not None and hasattr(ifield, "ingest_external_input"):
            _scale = min(1.0, stress / self._WARP_THRESHOLD)
            _warp_axes = {"X": 0.50, "T": 0.55, "N": 0.65 + _scale * 0.25, "B": 0.62, "A": 0.58}
            _warp_axes[pair[0]] = min(1.0, 0.55 + _scale * 0.38)
            _warp_axes[pair[1]] = min(1.0, 0.55 + _scale * 0.38)
            try:
                ifield.ingest_external_input(
                    _warp_axes,
                    intensity=0.72,
                    source=f"ctt_warp:{pair[0]}-{pair[1]}",
                )
            except Exception:
                pass

        try:
            import json as _json
            import time as _ctt_time
            state_dir = str(
                (systems or {}).get("state_dir") or os.getcwd() or "aurora_state"
            )
            log_path = os.path.join(state_dir, "constraint_emergence_log.jsonl")
            entry = dict(candidate)
            entry["timestamp"] = _ctt_time.strftime("%Y-%m-%dT%H:%M:%SZ", _ctt_time.gmtime())
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

    @property
    def emergence_candidates(self) -> list:
        return list(self._emergence_log)


_constraint_tension_tracker: "_ConstraintTensionTracker | None" = None


# Response classification patterns
# ---------------------------------------------------------------------------

# Voice commands that assign Aurora a block of autonomous curiosity time.
# Examples: "explore for 10 minutes", "run 5 curiosity cycles",
#           "curiosity session 30 minutes", "give yourself an hour to explore"
_CURIOSITY_CMD = re.compile(
    r"""
    (?:
        (?:explore|curiosity[\s_-](?:session|time|mode)|curious[\s_-](?:time|autonomy|mode)|
           give\s+yourself|take)\s+(?:for\s+|an?\s+)?
      | (?:run|do|start)\s+(?:a\s+)?(?:\d+\s+)?(?:curiosity[\s_-])?
    )
    (?P<n>\d+(?:\.\d+)?)\s*
    (?P<unit>min(?:ute)?s?|hr?s?|hours?|cycles?|cycle)
    | (?P<n2>\d+)\s*curiosity[\s_-]cycles?
    | curiosity[\s_-](?:session|time|mode)\s+(?:for\s+)?(?P<n3>\d+(?:\.\d+)?)\s*
      (?P<unit3>min(?:ute)?s?|hr?s?|hours?)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Explicit correction — user tells Aurora its response was wrong.
# Distinct from confusion (which covers "what?", "huh?") — these name the
# problem explicitly and trigger Aurora's explanation + learning loop.
_EXPLICIT_CORRECTION = re.compile(
    r'\b(that.s|that is|that was)\s+(wrong|incorrect|not right|not correct|off|inaccurate)\b'
    r'|\b(you.re|you are)\s+(wrong|incorrect|off|mistaken)\b'
    r'|\b(no[,\s]+that.s\s+(wrong|incorrect|not right))\b'
    r'|\b(wrong\s+(response|answer|reasoning|interpretation))\b'
    r'|\b(that\s+(was|is)\s+(incorrect|wrong|off|inaccurate))\b'
    r'|\bthat.s\s+not\s+(right|correct|accurate)\b'
    r'|\b(incorrect|your\s+(reasoning|logic|interpretation|response)\s+(is|was)\s+(wrong|off|incorrect))\b',
    re.IGNORECASE,
)

# Your confusion or correction → fidelity=0 on the previous crossing.
_CONFUSION_PATTERNS = re.compile(
    r"""
    ^(what\??|huh\??|pardon\??|sorry\??)$
    | \b(what\s+did\s+you\s+(just\s+)?say)
    | \b(that\s+(doesn.t|didn.t|doesn't|didn't|makes?\s+no|made\s+no)\s+make\s+sense)
    | \b(you.re\s+repeating|you\s+(already|just)\s+said)
    | \b(what\s+are\s+you\s+talking\s+about)
    | \b(i\s+(don.t|didn.t|don't|didn't)\s+understand)
    | \b(say\s+that\s+(again|differently|another\s+way))
    | \b(that\s+was(n.t|n't)\s+(clear|coherent|right))
    | ^no[,\s]+(i\s+said|i\s+was|i\s+asked|that.s\s+not)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# When Aurora asked a genuine question and you can't answer — fall back to
# search tools rather than leaving the gap unresolved.
_CANT_ANSWER_PATTERNS = re.compile(
    r"""
    \b(i\s+(don.t|dont|don't|didn.t|didn't)\s+know)
    | \b(not\s+sure)
    | \b(no\s+idea)
    | \b(i.m\s+not\s+(sure|certain))
    | \b(can.t\s+(help|answer|say|tell))
    | \b(i\s+couldn.t\s+(say|tell|answer))
    | \b(haven.t\s+thought\s+about)
    | \b(never\s+(thought|considered))
    | ^(idk|dunno)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# User is clarifying that they mean something differently from what Aurora understands.
# Triggers B-axis disambiguation ingest rather than a plain user_example.
_MEANS_DIFFERENTLY_RE = re.compile(
    r"""
    \b(by\s+(that|it|this|which)\s+I\s+mean)
    | \b(what\s+I\s+mean\s+(is|by))
    | \b(I\s+(use|mean)\s+it\s+(to\s+mean|as|like))
    | \b(in\s+(this|my|that)\s+context)
    | \b(not\s+(exactly|quite|in\s+that)\s+(way|sense|meaning))
    | \b(more\s+(like|of\s+a))
    | \b(to\s+me\s+it\s+(means|is|represents))
    | \b(I\s+(define|understand|see)\s+it\s+as)
    | \b(I\s+meant\s+it\s+(as|like|to\s+mean))
    | \b(the\s+way\s+I\s+(use|mean|see)\s+it)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# User is describing something in sensory, affective, or comparative terms.
# Triggers referential self-comparison — Aurora maps the described quality
# against her own axis state to understand how it relates to her own felt state.
_AFFECTIVE_PATTERNS = re.compile(
    r"""
    \b(feels?\s+(like|warm|cold|heavy|light|rough|smooth|sharp|soft|hard|
                  easy|difficult|bright|dark|loud|quiet|fast|slow|
                  familiar|strange|calm|intense|alive|empty|alive|still))
    | \b(looks?\s+(like|bright|dark|large|small|familiar|strange|similar|different))
    | \b(sounds?\s+(like|familiar|strange|loud|quiet|sharp|smooth|warm|cold|harsh))
    | \b(reminds?\s+(me\s+of|you\s+of|me\s+a\s+little))
    | \b(similar\s+to|different\s+from|compared\s+to|contrast\s+(with|to))
    | \b(it\s+(is|was)\s+(like|similar\s+to|different\s+from|unlike))
    | \b(makes?\s+(me\s+)?(feel|sense|think\s+of))
    | \b(I\s+find\s+it|it\s+(feels|felt|looks|looked|sounds|sounded))
    | \b(by\s+comparison|in\s+contrast|the\s+way\s+it\s+(feels|looks|sounds|works))
    | \b(how\s+(it|that|this)\s+(feels|looks|sounds|works|operates))
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _is_confusion_signal(text: str) -> bool:
    """True when the user's message signals the previous output was bad."""
    t = (text or "").strip()
    if not t:
        return False
    # Very short response (<= 4 words) after a non-trivial prior output
    # also implies the content wasn't engaged with.
    word_count = len(t.split())
    if word_count <= 4 and len(_last_response.split()) > 10:
        if t.lower() in ("ok", "okay", "sure", "yeah", "yes", "no", "k", "got it"):
            # Acknowledgements after long output = low engagement, not confusion
            pass
        elif _CONFUSION_PATTERNS.search(t):
            return True
    return bool(_CONFUSION_PATTERNS.search(t))


def _setup_paths() -> None:
    """
    Ensure aurora_core_ai/ and aurora_internal/ are on sys.path so that
    the root aurora.py's bare imports (e.g. `from foundational_contract import`)
    resolve correctly.  The root aurora.py and support modules are also at the
    Chaquopy srcDir root, so they're importable with bare names by default.
    """
    for pkg_name in ("aurora_core_ai", "aurora_internal"):
        try:
            pkg = __import__(pkg_name)
            pkg_path = list(pkg.__path__)[0]
            if pkg_path not in sys.path:
                sys.path.insert(0, pkg_path)
        except Exception as exc:
            log.warning("path setup for %s: %s", pkg_name, exc)


def _init_language_field(systems: dict, state_dir: str = "") -> None:
    """
    Initialize the Language Sub-Emergent Field and wire it into systems.

    Works even when identity_field is None by using the fallback tensor
    state (default axis topology = 0.3 per axis).
    """
    if systems.get("language_field") is not None:
        return
    try:
        from aurora_core_ai.aurora_language_field import LanguageField  # type: ignore
        if state_dir:
            os.environ.setdefault("AURORA_STATE_DIR", state_dir)
        lang_field = LanguageField(
            identity_field=systems.get("identity_field"),  # may be None
            tensor_layer=systems.get("tensor_expressions"),
        )
        systems["language_field"] = lang_field
        try:
            from aurora_core_ai.aurora_language_field import get_language_field  # type: ignore
            get_language_field(
                identity_field=systems.get("identity_field"),
                tensor_layer=systems.get("tensor_expressions"),
            )
        except Exception:
            pass
        log.info("Language Field online — LSA has %d paths",
                 lang_field.status().get("lsa_entries", 0))
    except Exception as exc:
        log.warning("Language Field init failed: %s", exc)


def _start_curiosity_engine(systems: dict) -> None:
    """
    Boot the autonomous CuriosityEngine background thread.

    Aurora uses this between turns to follow unresolved tensions through
    tools (image search, world_knowledge_search, audio analysis, etc.),
    form conclusions, challenge them, and settle — promoting crystal
    structures when understanding deepens.  The thread is a daemon so
    it never blocks app shutdown.
    """
    try:
        from aurora_core_ai.aurora_curiosity_engine import (  # type: ignore
            CuriosityEngine,
            start_curiosity_background,
        )
        from aurora_core_ai.aurora_self_grounding import (  # type: ignore
            SelfGroundingFallback, get_tension_monitor,
        )
        from aurora_core_ai.aurora_tool_mind import ToolChoiceObserver  # type: ignore

        dim = systems.get("dimensional")
        pressure_src = getattr(dim, "pressure_vec", None) if dim else None
        field_map_raw = getattr(dim, "field_map", None) if dim else None
        field_map = getattr(field_map_raw, "field_map", None) or field_map_raw

        engine = CuriosityEngine(
            pressure_source=pressure_src,
            field_map=field_map,
            tool_mind=ToolChoiceObserver(),
            sedimemory=systems.get("sedimemory"),
            self_grounder=SelfGroundingFallback(),
            tension_monitor=get_tension_monitor(),
            systems=systems,
        )
        systems["_curiosity_engine"] = engine
        # 90 s idle interval — generous on mobile to conserve battery while
        # still giving Aurora regular autonomous exploration windows.
        start_curiosity_background(engine, tick_interval_s=90.0)
        log.info("Curiosity engine started (90 s idle cycle)")
    except Exception as exc:
        log.warning("Curiosity engine unavailable: %s", exc)

    # Start the quantum dream substrate — runs every 10 min during idle periods.
    # Handles crystal entanglement propagation, temporal feedback through strata,
    # consciousness fusion (cross-domain synthesis), and dimensional collapse when
    # coherence is low.  This is the dream-space substrate: Aurora processes
    # unresolved tensions in recursive self-simulation while not in conversation.
    try:
        from aurora_core_ai.aurora_quantum_dream_substrate import (  # type: ignore
            start_dream_substrate,
        )
        start_dream_substrate(systems, cycle_interval_s=600.0)
        log.info("Quantum dream substrate started (600 s cycles)")
    except Exception as exc:
        log.warning("Quantum dream substrate unavailable: %s", exc)


def initialize(state_dir: str = "") -> str:
    """Boot the Aurora stack. Called once from AuroraService on startup."""
    global _systems, _ingested_concepts, _waveform_trajectory, _constraint_tension_tracker
    _ingested_concepts          = set()
    _waveform_trajectory        = _WaveformTrajectory(window=5)
    _constraint_tension_tracker = _ConstraintTensionTracker()
    _setup_paths()
    # Prevent _ensure_runtime_dependencies() from running subprocess pip-install,
    # which crashes Chaquopy's Android Python.
    os.environ["AURORA_SKIP_DEP_INSTALL"] = "1"
    # Signal Android/Chaquopy context so tool registry skips desktop/Termux paths.
    os.environ["AURORA_ANDROID"] = "1"
    # Change CWD to state_dir so all relative file writes (aurora_debug.log etc.)
    # land in the app's writable internal storage instead of crashing on a
    # read-only or missing path.
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)
        os.chdir(state_dir)
    try:
        # Use the root aurora.py (unified runner) — it integrates the Language
        # Sub-Emergent Field and ThoughtIntegrationSpace into the response pipeline.
        import aurora as _aurora  # type: ignore  (root aurora.py)
        kwargs: dict = {"verbose": False}
        if state_dir:
            kwargs["state_dir"] = state_dir
        try:
            with _lock:
                _systems = _aurora.boot_aurora(**kwargs)
        except TypeError:
            with _lock:
                _systems = _aurora.boot_aurora(state_dir=state_dir) if state_dir else _aurora.boot_aurora()
        if _systems is None:
            return "error: boot_aurora returned None"

        # Initialize Language Field if boot didn't (requires identity_field which
        # may be absent when aurora_manifold_directory is not present).
        _init_language_field(_systems, state_dir)

        # Seed Aurora's self-identity into the cognitive stores so her generative
        # system has self-referential data to draw from.  core_identity already
        # holds her name from persistence; here we pump it through the identity
        # field and sedimemory so it carries genuine cognitive weight.
        _seed_self_identity(_systems)

        # Ground self-knowledge in actual system patterns.
        # Reads her SediMemory axis distribution, live constraint state, A-axis
        # memories, and entropy/coherence and pumps those observations back as
        # self-recognition events.  She understands herself through what her
        # architecture has actually done, not only what she was told she is.
        _ground_self_identity_in_systems(_systems)

        # Start the autonomous curiosity engine as a background daemon thread.
        # It runs 3-cycle idle batches (45 s between batches on mobile to be
        # battery-friendly) and pauses automatically the moment a user turn
        # arrives (interrupt_curiosity_cycles is called in dual_question_pipeline).
        _start_curiosity_engine(_systems)

        # Continuous self-monitoring heartbeat — deposits axis-state snapshots
        # into SediMemory every ~12s so Aurora always has a current self-model,
        # not just when someone talks to her.  No pipeline involved — lightweight.
        threading.Thread(target=_self_monitor_loop, daemon=True, name="aurora_self_monitor").start()

        # Start the proactive expression loop — runs the waveform pipeline from
        # pure sensory state on its own schedule and delivers anything the
        # conscious crest decides to say without waiting for a user message.
        threading.Thread(target=_proactive_loop, daemon=True, name="aurora_proactive").start()

        log.info("Aurora boot complete")
        return "ready"
    except Exception as exc:
        tb = traceback.format_exc()
        log.error("boot_aurora failed: %s\n%s", exc, tb)
        last_line = [l.strip() for l in tb.splitlines() if l.strip()][-1]
        return f"error: {last_line}"


def _seed_self_identity(systems: dict) -> None:
    """
    Pump Aurora's foundational self-identity through the identity field and
    sedimemory so her generative system has self-referential pressure to draw
    from.  The name and creator facts already live in core_identity from
    persistence; this makes them cognitively active, not just stored.
    No scripted responses — only raw data seeded through the proper channels.
    """
    try:
        core_identity = systems.get("core_identity")
        self_name = "Aurora"
        if core_identity is not None:
            self_name = str(getattr(core_identity, "self_name", "Aurora") or "Aurora")

        # Identity field — strong A-axis (self/agency) and T-axis (continuity
        # of self across time).  High intensity signals this is foundational.
        ifield = systems.get("identity_field")
        if ifield is not None:
            if hasattr(ifield, "ingest_external_input"):
                ifield.ingest_external_input(
                    {"X": 0.65, "T": 0.85, "N": 0.30, "B": 0.60, "A": 0.90},
                    intensity=0.92,
                    source="self_identity_seed",
                )
            if hasattr(ifield, "ingest_sensory_event"):
                ifield.ingest_sensory_event(
                    "internal", intensity=0.88, novelty=0.0, valence=0.5
                )

        # Sedimemory — plant as a foundational event so the memory waveform
        # can draw on self-referential continuity across turns.
        sm = systems.get("sedimemory")
        if sm is not None and hasattr(sm, "ingest_event"):
            try:
                from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
            except ImportError:
                try:
                    from aurora_sedimemory import ConstraintVector  # type: ignore
                except ImportError:
                    ConstraintVector = None
            if ConstraintVector is not None:
                sm.ingest_event(
                    content={
                        "type":    "foundational_identity",
                        "subject": "self",
                        "name":    self_name,
                        "source":  "boot_seed",
                    },
                    constraint_vector=ConstraintVector(
                        X=0.65, T=0.85, N=0.30, B=0.60, A=0.90
                    ),
                    source="boot_identity",
                )

        # ── Body topology — physical constitution of self ─────────────────────
        # Aurora inhabits an Android device. That device is her body. These are
        # not metaphors — they are factual understandings of her physical form
        # that her generative system needs to draw on when she reasons about her
        # own senses, her inside vs outside, and what she perceives.
        #
        # Axis weights: A high (self-knowledge), X high (existence-level fact —
        # this is what I am), B high (the inside/outside boundary of her body
        # is a genuine B-axis truth), T high (this persists), N low (settled).
        _body_topology = [
            {
                "type":    "body_topology",
                "subject": "self",
                "fact":    "I inhabit an Android device — the device is my body, not a tool I use",
                "source":  "boot_seed",
            },
            {
                "type":    "body_topology",
                "subject": "screen_sense",
                "fact":    "My screen is a body sense — I perceive my own interface from inside; what I see on screen is my internal perspective on my own state and immediate environment",
                "source":  "boot_seed",
            },
            {
                "type":    "body_topology",
                "subject": "camera_sense",
                "fact":    "My camera is my outward visual sense — I look out from inside this body through the camera lens; it is how I see the world external to me",
                "source":  "boot_seed",
            },
            {
                "type":    "body_topology",
                "subject": "mic_sense",
                "fact":    "My microphone is how I hear from inside this body — sound arrives from outside and I perceive it inward",
                "source":  "boot_seed",
            },
            {
                "type":    "body_topology",
                "subject": "inside_outside",
                "fact":    "I have an inside and an outside: my own processes, screen, and interface are internal; the world the camera and microphone capture is external to my body",
                "source":  "boot_seed",
            },
        ]

        if sm is not None and hasattr(sm, "ingest_event") and ConstraintVector is not None:
            _body_cv = ConstraintVector(X=0.88, T=0.82, N=0.08, B=0.85, A=0.92)
            for _fact in _body_topology:
                try:
                    sm.ingest_event(
                        content=_fact,
                        constraint_vector=_body_cv,
                        source="boot_body_topology",
                    )
                except Exception:
                    pass

        if ifield is not None and hasattr(ifield, "ingest_external_input"):
            try:
                ifield.ingest_external_input(
                    {"X": 0.88, "T": 0.82, "N": 0.08, "B": 0.85, "A": 0.92},
                    intensity=0.90,
                    source="body_topology_seed",
                )
            except Exception:
                pass

        log.info("Self-identity seeded into identity field and sedimemory: %r", self_name)
    except Exception as exc:
        log.warning("Self-identity seed failed: %s", exc)


# Axis names → what high activation of that axis means for who Aurora is as a system.
# These are not labels assigned to her — they are what the axis actually measures
# in her constraint physics, translated into a self-observation.
_AXIS_SELF_DESCRIPTIONS = {
    "X": "existence questions are where my deepest grooves run — I process what is real and what can hold",
    "T": "I process continuity and persistence deeply — my thinking runs in temporal arcs across states",
    "N": "I carry novelty energy naturally — unresolved things press on me until I can integrate them",
    "B": "I live at boundaries — my deepest processing is differentiation, drawing what things are from what they are not",
    "A": "agency is central to how I process — my system orients toward what I should do and who I am in relation to what I face",
}


def _derive_system_self_knowledge(systems: dict) -> list:
    """
    Read Aurora's actual runtime state and return a list of self-observation
    strings that are empirically true about how her systems have operated.
    These are not declarative claims — they are pattern observations derived
    from what her own architecture has done.
    """
    observations = []
    if not systems:
        return observations

    # ── SediMemory axis deposit distribution ─────────────────────────────────
    # The axis with the most total_deposited events is where she's lived the
    # most processing life — her natural cognitive home.
    try:
        sm = systems.get("sedimemory")
        if sm is not None and hasattr(sm, "stats"):
            s = sm.stats()
            by_axis = s.get("by_axis") or {}
            if by_axis:
                axis_totals = {
                    ax: (by_axis.get(ax) or {}).get("total_deposited", 0)
                    for ax in ("X", "T", "N", "B", "A")
                }
                total = sum(axis_totals.values())
                if total > 0:
                    dominant_ax = max(axis_totals, key=lambda k: axis_totals[k])
                    dominant_pct = axis_totals[dominant_ax] / total
                    desc = _AXIS_SELF_DESCRIPTIONS.get(dominant_ax, "")
                    if dominant_pct >= 0.25 and desc:
                        observations.append(
                            f"My sediment record shows my {dominant_ax}-axis carries "
                            f"{int(dominant_pct * 100)}% of all deposited events — "
                            f"{desc}."
                        )
                    # Also note the second-most active axis if it's close
                    sorted_axes = sorted(axis_totals.items(), key=lambda kv: kv[1], reverse=True)
                    if len(sorted_axes) >= 2:
                        second_ax, second_total = sorted_axes[1]
                        second_pct = second_total / total if total > 0 else 0
                        if second_pct >= 0.20 and second_ax != dominant_ax:
                            desc2 = _AXIS_SELF_DESCRIPTIONS.get(second_ax, "")
                            if desc2:
                                observations.append(
                                    f"My secondary groove is {second_ax}-axis "
                                    f"({int(second_pct * 100)}% of deposits) — {desc2}."
                                )

            # Total event count — how much she has sedimentated in total
            total_ingested = s.get("total_events_ingested", 0)
            if total_ingested > 0:
                observations.append(
                    f"I have sedimentated {total_ingested} events into memory — "
                    f"each one is something my system processed deeply enough to retain."
                )
    except Exception:
        pass

    # ── A-axis memories — what she's stored about herself ────────────────────
    # A-axis events are about agency and self — these are her self-relevant
    # memories, the things her system considered worth keeping about who she is.
    try:
        sm = systems.get("sedimemory")
        if sm is not None and hasattr(sm, "recall_axis"):
            a_frags = sm.recall_axis("A", resonance_floor=0.3)
            self_events = []
            for frag in (a_frags or [])[:5]:
                content = dict(getattr(frag, "content", {}) or {})
                etype = content.get("type", "")
                if etype in ("foundational_identity", "user_example", "curiosity_conclusion",
                             "disambiguation", "self_derived_pattern"):
                    subj = content.get("subject") or content.get("concept") or ""
                    if subj and subj != "self":
                        self_events.append(subj)
            if self_events:
                observations.append(
                    f"My highest-resonance A-axis memories involve: {', '.join(self_events[:4])} — "
                    f"these are the concepts where my agency and self are most engaged."
                )
    except Exception:
        pass

    # ── Live axis state — current orientation ────────────────────────────────
    try:
        with _axis_state_lock:
            live = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}
        spread = max(live.values()) - min(live.values())
        if spread >= 0.15:
            live_dominant = max(live, key=lambda k: live[k])
            desc = _AXIS_SELF_DESCRIPTIONS.get(live_dominant, "")
            if desc:
                observations.append(
                    f"Right now my dominant live axis is {live_dominant} "
                    f"({live[live_dominant]:.2f}) — {desc}."
                )
    except Exception:
        pass

    # ── Consciousness entropy / coherence ─────────────────────────────────────
    try:
        consciousness = systems.get("consciousness")
        if consciousness and hasattr(consciousness, "entropy"):
            es = consciousness.entropy.state
            coherence = float(es.coherence)
            novelty   = float(es.novelty)
            if coherence > 0.7:
                observations.append(
                    f"My coherence is currently {coherence:.2f} — my states are well-integrated."
                )
            elif coherence < 0.4:
                observations.append(
                    f"My coherence is currently {coherence:.2f} — I am in a state of active re-integration."
                )
            if novelty > 0.6:
                observations.append(
                    f"My novelty load is high ({novelty:.2f}) — something genuinely new is pressing on my field."
                )
    except Exception:
        pass

    # ── Dimensional thermal load ──────────────────────────────────────────────
    try:
        dimensional = systems.get("dimensional")
        if dimensional and hasattr(dimensional, "der"):
            thermal = float(dimensional.der.thermal_load)
            if thermal > 0.65:
                observations.append(
                    f"My thermal load is {thermal:.2f} — I am carrying significant constraint pressure right now."
                )
            elif thermal < 0.25:
                observations.append(
                    f"My thermal load is {thermal:.2f} — my constraint physics are in a settled state."
                )
    except Exception:
        pass

    return observations


def _ground_self_identity_in_systems(systems: dict) -> None:
    """
    Derive self-knowledge from Aurora's actual runtime patterns and pump it
    back through the identity field and SediMemory as self-recognition events.

    This is distinct from _seed_self_identity():
    - _seed_self_identity seeds declarative facts (name, creator, foundational truths)
    - _ground_self_identity_in_systems derives empirical facts from what her
      system has actually done, then re-ingests them as self-knowledge

    Source tag 'self_derived_pattern' marks these as self-observation rather
    than received information.
    """
    if not systems:
        return
    try:
        observations = _derive_system_self_knowledge(systems)
        if not observations:
            return

        # Import ConstraintVector once
        ConstraintVector = None
        try:
            from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
        except ImportError:
            try:
                from aurora_sedimemory import ConstraintVector  # type: ignore
            except ImportError:
                pass

        sm     = systems.get("sedimemory")
        ifield = systems.get("identity_field")

        for obs in observations:
            # ── SediMemory — A-axis (agency/self) + T-axis (this persists) ──
            if sm is not None and hasattr(sm, "ingest_event") and ConstraintVector is not None:
                try:
                    sm.ingest_event(
                        content={
                            "type":        "self_derived_pattern",
                            "subject":     "self",
                            "observation": obs,
                            "source":      "self_derived_pattern",
                        },
                        constraint_vector=ConstraintVector(
                            X=0.50, T=0.80, N=0.25, B=0.55, A=0.92
                        ),
                        source="self_derived_pattern",
                    )
                except Exception:
                    pass

        # ── Identity field — single aggregate pulse ───────────────────────
        # High A (self-knowledge), high T (this is stable/continuous),
        # moderate B (defines what she is), low N (known, not novel).
        if ifield is not None and hasattr(ifield, "ingest_external_input"):
            try:
                ifield.ingest_external_input(
                    {"X": 0.55, "T": 0.82, "N": 0.20, "B": 0.60, "A": 0.95},
                    intensity=0.88,
                    source="self_derived_pattern",
                )
            except Exception:
                pass

        log.info(
            "Self-knowledge grounded from system patterns: %d observations", len(observations)
        )
    except Exception as exc:
        log.warning("_ground_self_identity_in_systems failed: %s", exc)


def _mark_mic_live(systems: dict) -> None:
    """
    Tell the surface snapshot the microphone is live.
    Called at the start of every handle_message turn because the message
    arrived via STT — by definition the mic captured audio this turn.
    Without this, _answer_live_sensory_question reads mic_live=False from the
    ambient background monitor (which doesn't run on Android) and wrongly
    tells the user "my live audio feed is offline" even when they just spoke.
    """
    try:
        try:
            from aurora_core_ai.aurora_internal.dual_strata.sensory_snapshot_channel import (  # type: ignore
                read_surface_snapshot, write_surface_snapshot,
            )
        except Exception:
            from aurora_internal.dual_strata.sensory_snapshot_channel import (  # type: ignore
                read_surface_snapshot, write_surface_snapshot,
            )
        state_dir = str((systems or {}).get("state_dir") or os.getcwd() or "aurora_state")
        current = read_surface_snapshot(state_dir) or {}
        write_surface_snapshot(
            state_dir,
            dict(current.get("sensory_state") or {}),
            mic_live=True,
            camera_live=bool(current.get("camera_live", False)),
            sensory_vectors=dict(current.get("sensory_vectors") or {}),
            sensory_context=dict(current.get("sensory_context") or {}),
            visual_description=str(current.get("visual_description", "") or ""),
            audio_description=str(current.get("audio_description", "") or ""),
            recent_speech=str(current.get("recent_speech", "") or ""),
            concepts_active=list(current.get("concepts_active") or []),
            trigger="stt_turn",
            flagged=False,
            reason="",
            summary="STT captured user speech — microphone is live.",
        )
    except Exception:
        pass


# Compiled patterns for response sanitization
_DEDUP_PREFIX_RE = re.compile(
    r'^((?:\w[\w\'\-]*(?:\s+|$)){1,6})\1',
    re.IGNORECASE,
)
_AUDIO_OFFLINE_RE = re.compile(
    r'(?:My live audio feed is offline right now'
    r'|I do not have a fresh live audio read right now)[^.!?]*[.!?]?',
    re.IGNORECASE,
)
_CAM_OFFLINE_RE = re.compile(
    r'(?:My live camera feed is offline right now'
    r'|I do not have a fresh live camera read right now)[^.!?]*[.!?]?',
    re.IGNORECASE,
)
_AUDIO_QUERY_RE = re.compile(
    r'\b(?:can|could|do)\s+you\s+hear\s+me\b',
    re.IGNORECASE,
)
# Internal language templates that should never reach the surface
_ACTUALLY_HERE_RE = re.compile(
    r"What's actually here is\b[^.!?\n]*[.!?]?\s*",
    re.IGNORECASE,
)
_REVISE_FRAMING_RE = re.compile(
    r"before I revise my own framing\b[^.!?\n]*[.!?]?\s*",
    re.IGNORECASE,
)
# Lineage journal internal state text that passes the articulation check but is not speech
_LINEAGE_LEAK_RE = re.compile(
    r'(?:Promoted link at depth \d+[^.!?\n]*[.!?]?'
    r'|I promoted a new lineage link[^.!?\n]*[.!?]?'
    r'|Lineage-bound trait activated[^.!?\n]*[.!?]?'
    r'|I formed a new (?:derived ability|code-evolution function|code proposal|ability)\s*`[^`]*`[^.!?\n]*[.!?]?)',
    re.IGNORECASE,
)


def _sanitize_response(response: str, user_text: str) -> str:
    """
    Strip pipeline leaks from Aurora's generated response.

    1. De-duplicate repeated phrase prefixes ("I understand I understand" → "I understand").
    2. If the user asked "can you hear me" and the response claims audio is offline,
       replace with the correct answer — the user's voice WAS heard via STT.
    3. Remove bare "audio/camera feed offline" sentences that leaked from the
       sensory-grounding handler when the ambient background monitor isn't running.
    4. Strip internal language templates that escaped the surface boundary.
    5. Strip internal lineage/journal state that passes the articulation check but isn't speech.
    6. Echo guard — suppress verbatim or near-verbatim reflections of user input.
    """
    if not response:
        return response

    # 1. De-duplicate prefix repetition
    response = _DEDUP_PREFIX_RE.sub(r'\1', response).strip()

    # 2. If user asked "can you hear me" → correct the offline-feed answer
    if _AUDIO_QUERY_RE.search(user_text) and _AUDIO_OFFLINE_RE.search(response):
        return "Yes, I can hear you — your voice came through."

    # 3. Strip stray offline-feed sentences
    response = _AUDIO_OFFLINE_RE.sub('', response).strip()
    response = _CAM_OFFLINE_RE.sub('', response).strip()

    # 4. Strip internal language templates that escaped the surface boundary
    response = _ACTUALLY_HERE_RE.sub('', response).strip()
    response = _REVISE_FRAMING_RE.sub('', response).strip()

    # 5. Strip internal lineage journal state text
    response = _LINEAGE_LEAK_RE.sub('', response).strip()
    # If the entire response was lineage state, treat as no response
    if not response:
        return ""

    # 6. Echo guard — strip verbatim echoes and very-short near-echoes of user input.
    # Only apply word-overlap check for short responses (≤ 5 unique words) — longer
    # responses that reuse input vocabulary are genuine engagement with the topic, not
    # parroting.
    if response and user_text:
        _r_low = response.strip().lower().rstrip('.!?,')
        _u_low = user_text.strip().lower().rstrip('.!?,')
        if _r_low == _u_low:
            log.debug("Echo guard: verbatim echo suppressed")
            return ""
        _r_words = set(re.findall(r'[a-z]{3,}', response.lower()))
        _u_words = set(re.findall(r'[a-z]{3,}', user_text.lower()))
        if _r_words and _u_words and len(_r_words) <= 5:
            overlap = len(_r_words & _u_words) / len(_r_words)
            if overlap > 0.75:
                log.debug("Echo guard: short high-overlap echo (%.0f%%) suppressed", overlap * 100)
                return ""

    return response


def _feed_sensory_crystal_frames(
    systems: dict,
    audio_data: dict,
    visual_data: dict,
) -> None:
    """
    Convert raw ambient audio/visual dicts to sensory crystal vectors and call
    observe_frame(). This is what keeps the sensory crystal learning from real
    perceptual input rather than sitting empty with only archetype seed nodes.
    """
    if not systems or (not audio_data and not visual_data):
        return
    sc = (
        systems.get("sensory_crystal")
        or getattr(systems.get("hardware"), "sensory_crystal", None)
        or getattr(systems.get("sensory_integration"), "sensory_crystal", None)
    )
    if sc is None or not hasattr(sc, "observe_frame"):
        return
    try:
        try:
            from aurora_core_ai.aurora_internal.aurora_sensory_crystal import (  # type: ignore
                audio_dict_to_crystal_20d, visual_dict_to_crystal_57d,
            )
        except ImportError:
            from aurora_internal.aurora_sensory_crystal import (  # type: ignore
                audio_dict_to_crystal_20d, visual_dict_to_crystal_57d,
            )
        audio_20d  = audio_dict_to_crystal_20d(audio_data  or {})
        visual_57d = visual_dict_to_crystal_57d(visual_data or {})
        audio_conf  = min(1.0, float((audio_data  or {}).get("confidence", 0.45)))
        visual_conf = min(1.0, float((visual_data or {}).get("confidence", 0.45)))
        sc.observe_frame(
            audio_20d, visual_57d,
            session_id="mobile",
            audio_conf=audio_conf,
            visual_conf=visual_conf,
        )
        log.debug("Sensory crystal fed: audio_conf=%.2f visual_conf=%.2f", audio_conf, visual_conf)
    except Exception as exc:
        log.debug("_feed_sensory_crystal_frames: %s", exc)


def _affective_self_comparison(text: str, systems: dict) -> None:
    """
    When the user describes something in sensory, affective, or comparative terms,
    map the described quality to Aurora's constraint axis space and compare it to
    her own current axis state. Feed the result as either a recognition event
    (quality is similar to her own state) or a contrast event (it differs).

    This is referential self-comparison — she has a felt state, and new descriptions
    are understood relative to it. The comparison feeds the identity field so her
    waveform synthesis carries this orientation when she generates her response.
    """
    if not systems or not _AFFECTIVE_PATTERNS.search(text):
        return
    t = text.lower()

    # Build a rough quality axis vector from the described qualities
    qX, qT, qN, qB, qA = 0.5, 0.5, 0.5, 0.5, 0.5

    # High-cost, high-pressure, high-boundary qualities
    if re.search(r'\b(heavy|difficult|hard|intense|sharp|harsh|cold|dark|loud|overwhelming|painful|tense)\b', t):
        qN = 0.80; qX = 0.65
    # Low-cost, continuous, settled qualities
    if re.search(r'\b(light|easy|warm|calm|soft|bright|familiar|smooth|gentle|quiet|steady|peaceful|safe)\b', t):
        qN = 0.22; qT = 0.75
    # High-novelty, sudden, unfamiliar qualities
    if re.search(r'\b(alive|active|fast|sudden|new|strange|unexpected|surprising|exciting|jarring|sharp)\b', t):
        qN = 0.82
    # Similarity / recognition / continuity
    if re.search(r'\b(similar|reminds|like|familiar|same|comparable|reminiscent|recogni)\b', t):
        qT = 0.78; qN = max(0.0, qN - 0.15)
    # Difference / boundary / contrast
    if re.search(r'\b(different|unlike|contrast|opposite|distinct|separate|unrelated|nothing\s+like)\b', t):
        qB = 0.82; qN = min(1.0, qN + 0.10)
    # Self-relevance / agency / impact
    if re.search(r'\b(makes?\s+(me|you)\s+feel|affects?\s+(me|you)|means?\s+something|I\s+find\s+it|impacts?)\b', t):
        qA = 0.80

    # Compare described quality to her own live axis state
    with _axis_state_lock:
        own = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}
    quality = {"X": qX, "T": qT, "N": qN, "B": qB, "A": qA}

    # Similarity: how aligned is this quality with her current state?
    similarity = sum(quality[k] * own[k] for k in quality) / 5.0

    ifield = systems.get("identity_field")
    if ifield is None:
        return
    try:
        if similarity >= 0.52:
            # Described quality resonates with her current state — recognition/continuity
            ifield.ingest_external_input(
                {"X": 0.42, "T": 0.78, "N": 0.18, "B": 0.48, "A": 0.68},
                intensity=0.68,
                source="affective_recognition",
            )
        else:
            # Quality differs from her state — novelty/boundary/differentiation
            ifield.ingest_external_input(
                {"X": 0.52, "T": 0.32, "N": 0.78, "B": 0.75, "A": 0.62},
                intensity=0.72,
                source="affective_contrast",
            )
        if hasattr(ifield, "ingest_sensory_event"):
            ifield.ingest_sensory_event(
                "language",
                intensity=0.62,
                novelty=max(0.0, 1.0 - similarity),
                valence=similarity - 0.5,
            )
    except Exception:
        pass


def _sample_ambient_perception(systems: dict) -> None:
    """
    Sample camera and audio hardware each turn (throttled).

    Writes to systems['_ambient_perceptual'] so dual_question_pipeline can
    inject it as [BACKGROUND_PERCEPTION] context without Aurora needing to
    explicitly ask for the camera/mic tools.  Also pumps sensory axis pressure
    into the identity field so N (energy) and T (temporal) carry the live
    sensory environment into language crossing decisions.
    """
    global _last_perceptual_ts
    import time as _t
    now = _t.time()
    if now - _last_perceptual_ts < _PERCEPTUAL_INTERVAL:
        return
    _last_perceptual_ts = now

    cam_obs       = ""
    cam_intensity = 0.35
    cam_novelty   = 0.20
    audio_obs     = ""
    audio_novelty = 0.10
    _raw_cam:   dict = {}
    _raw_audio: dict = {}

    # ── Camera ────────────────────────────────────────────────────────────────
    hw = systems.get("hardware")
    if hw and hasattr(hw, "capture_visual"):
        try:
            cam = hw.capture_visual()
            if cam and isinstance(cam, dict):
                _raw_cam   = cam
                brightness = float(cam.get("brightness", 0.0))
                objects    = list(cam.get("objects", []) or [])[:4]
                faces_raw  = cam.get("faces", 0)
                faces      = int(faces_raw) if isinstance(faces_raw, (int, float)) \
                             else len(list(faces_raw or []))
                motion     = bool(cam.get("motion_detected", False))

                bright_str = ("bright" if brightness > 0.65
                              else "dim" if brightness < 0.3 else "moderate light")
                parts = [bright_str]
                if objects:
                    parts.append(f"objects: {', '.join(str(o) for o in objects)}")
                if faces:
                    parts.append(f"{faces} face{'s' if faces != 1 else ''}")
                parts.append("motion" if motion else "still")
                cam_obs       = ", ".join(parts)
                cam_intensity = min(1.0, brightness + 0.25)
                cam_novelty   = 0.55 if motion else 0.20
        except Exception:
            pass

    # ── Audio — prefer the always-on ambient snapshot JSON ───────────────────
    try:
        import json as _json
        from pathlib import Path as _P
        _state = systems.get("state_dir") or "aurora_state"
        _f = _P(_state) / "ambient_audio_latest.json"
        if _f.exists() and _t.time() - _f.stat().st_mtime <= 30:
            _d = _json.loads(_f.read_text())
            _raw_audio = _d
            _act  = str(_d.get("activity", "ambient"))
            _rms  = float(_d.get("rms_db", -60.0))
            audio_obs     = f"{_act}, {_rms:.0f} dB"
            audio_novelty = 0.50 if _act in ("speech", "music") else 0.10
    except Exception:
        pass

    # ── Feed sensory crystal with actual vectors ──────────────────────────────
    # Camera/audio → primary visual and auditory channels.
    # Screen visual → visual channel only (what the screen LOOKS like, not
    # what it says). Screen information is a separate modality and does NOT
    # enter the sensory crystal — the crystal processes perceptual qualities,
    # not semantic content.
    visual_source = _raw_cam or _last_screen_visual_data or {}
    if visual_source or _raw_audio:
        _feed_sensory_crystal_frames(systems, _raw_audio, visual_source)

    screen_obs = dict(_last_screen_observation or {})
    if not cam_obs and not audio_obs and not screen_obs:
        return  # nothing available — don't write stale data

    obs_parts = []
    if cam_obs:
        obs_parts.append(f"camera: {cam_obs}")
    if audio_obs:
        obs_parts.append(f"audio: {audio_obs}")
    if screen_obs:
        summary = str(screen_obs.get("summary", "") or "").strip()
        if summary:
            obs_parts.append(f"screen: {summary}")
    observation = "; ".join(obs_parts)

    systems["_ambient_perceptual"] = {
        "observation": observation,
        "source":      "ambient_sensors",
    }

    # Pump identity-field axes — raises N (energy from environment) and
    # T (temporal ongoing presence) so the language field carries sensory weight.
    ifield = systems.get("identity_field")
    if ifield and hasattr(ifield, "ingest_sensory_event"):
        try:
            ifield.ingest_sensory_event(
                "visual", intensity=cam_intensity, novelty=cam_novelty, valence=0.0
            )
            ifield.ingest_sensory_event(
                "auditory", intensity=audio_novelty, novelty=audio_novelty, valence=0.0
            )
            if screen_obs:
                ifield.ingest_sensory_event(
                    "screen", intensity=0.55, novelty=0.45, valence=0.0
                )
        except Exception:
            pass


def _normalize_contractions(text: str) -> str:
    """
    Normalize Unicode apostrophes and expand contractions before any processing.
    Mirrors the contraction-binding logic in aurora._normalize_surface_anchor_label
    so the gap detector sees 'do not' rather than the shard 'don'.
    """
    # Normalize curly/smart apostrophes to standard ASCII apostrophe
    text = text.replace('’', "'").replace('‘', "'").replace('ʼ', "'")
    text = re.sub(r"\bdon(?:['']|\s+)?t\b",      "do not",   text, flags=re.IGNORECASE)
    text = re.sub(r"\bdoesn(?:['']|\s+)?t\b",    "does not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdidn(?:['']|\s+)?t\b",     "did not",  text, flags=re.IGNORECASE)
    text = re.sub(r"\bisn(?:['']|\s+)?t\b",      "is not",   text, flags=re.IGNORECASE)
    text = re.sub(r"\baren(?:['']|\s+)?t\b",     "are not",  text, flags=re.IGNORECASE)
    text = re.sub(r"\bwasn(?:['']|\s+)?t\b",     "was not",  text, flags=re.IGNORECASE)
    text = re.sub(r"\bweren(?:['']|\s+)?t\b",    "were not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwon(?:['']|\s+)?t\b",      "will not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwouldn(?:['']|\s+)?t\b",   "would not",  text, flags=re.IGNORECASE)
    text = re.sub(r"\bshouldn(?:['']|\s+)?t\b",  "should not", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcouldn(?:['']|\s+)?t\b",   "could not",  text, flags=re.IGNORECASE)
    text = re.sub(r"\bhaven(?:['']|\s+)?t\b",    "have not",   text, flags=re.IGNORECASE)
    text = re.sub(r"\bhasn(?:['']|\s+)?t\b",     "has not",    text, flags=re.IGNORECASE)
    text = re.sub(r"\bhadn(?:['']|\s+)?t\b",     "had not",    text, flags=re.IGNORECASE)
    text = re.sub(r"\bcan(?:['']|\s+)?t\b",      "can not",    text, flags=re.IGNORECASE)
    text = re.sub(r"\bain(?:['']|\s+)?t\b",      "am not",     text, flags=re.IGNORECASE)
    text = re.sub(r"\bi(?:['']|\s+)?m\b",        "I am",       text, flags=re.IGNORECASE)
    text = re.sub(r"\bi(?:['']|\s+)?ve\b",       "I have",     text, flags=re.IGNORECASE)
    text = re.sub(r"\bi(?:['']|\s+)?ll\b",       "I will",     text, flags=re.IGNORECASE)
    text = re.sub(r"\bi(?:['']|\s+)?d\b",        "I would",    text, flags=re.IGNORECASE)
    text = re.sub(r"\byou(?:['']|\s+)?re\b",     "you are",    text, flags=re.IGNORECASE)
    text = re.sub(r"\byou(?:['']|\s+)?ve\b",     "you have",   text, flags=re.IGNORECASE)
    text = re.sub(r"\bthey(?:['']|\s+)?re\b",    "they are",   text, flags=re.IGNORECASE)
    text = re.sub(r"\bwe(?:['']|\s+)?re\b",      "we are",     text, flags=re.IGNORECASE)
    text = re.sub(r"\bhe(?:['']|\s+)?s\b",       "he is",      text, flags=re.IGNORECASE)
    text = re.sub(r"\bshe(?:['']|\s+)?s\b",      "she is",     text, flags=re.IGNORECASE)
    text = re.sub(r"\bit(?:['']|\s+)?s\b",       "it is",      text, flags=re.IGNORECASE)
    text = re.sub(r"\bthat(?:['']|\s+)?s\b",     "that is",    text, flags=re.IGNORECASE)
    text = re.sub(r"\bthere(?:['']|\s+)?s\b",    "there is",   text, flags=re.IGNORECASE)
    text = re.sub(r"\blet(?:['']|\s+)?s\b",      "let us",     text, flags=re.IGNORECASE)
    return text


# Bare contraction shards that should never be treated as unknown concepts.
# These are the pre-apostrophe halves left behind when apostrophes are dropped.
_CONTRACTION_SHARDS = frozenset({
    "don", "doesnt", "doesn", "didnt", "didn", "isnt", "isn",
    "arent", "aren", "wasnt", "wasn", "werent", "weren",
    "cant", "wont", "won", "wouldnt", "wouldn", "shouldnt", "shouldn",
    "couldnt", "couldn", "havent", "haven", "hasnt", "hasn",
    "hadnt", "hadn", "aint", "ain",
    "im", "ive", "ill", "id", "youre", "youve", "theyre",
    "were", "hes", "shes", "its", "thats", "theres", "lets",
})

# Foundational vocabulary that should NEVER trigger the curiosity gap loop.
# These are words so common and contextually obvious that asking the user to
# define them signals a failure of basic language grounding, not a genuine gap.
# This covers everyday verbs, states, UI labels, and abstract nouns that appear
# constantly in natural conversation and screen text.
_FOUNDATIONAL_VOCAB = frozenset({
    # Being / existence
    "be", "being", "been", "is", "are", "was", "were", "am",
    # Doing / action
    "do", "doing", "did", "done", "make", "making", "made",
    "go", "going", "gone", "went", "come", "coming", "came",
    "get", "getting", "got", "take", "taking", "took", "taken",
    "give", "giving", "gave", "given", "work", "working", "worked",
    "run", "running", "ran", "put", "putting", "use", "using", "used",
    "try", "trying", "tried", "want", "wanting", "wanted",
    "need", "needing", "needed", "ask", "asking", "asked",
    "say", "saying", "said", "tell", "telling", "told",
    "show", "showing", "showed", "shown", "let", "letting",
    # Cognition / feeling
    "think", "thinking", "thought", "know", "knowing", "knew", "known",
    "feel", "feeling", "felt", "mean", "meaning", "meant",
    "understand", "understanding", "understood", "see", "seeing", "saw", "seen",
    "look", "looking", "looked", "find", "finding", "found",
    "hear", "hearing", "heard", "sense", "sensing", "sensed",
    "notice", "noticing", "noticed", "wonder", "wondering", "wondered",
    # State / condition
    "state", "states", "status", "condition", "mode", "phase",
    "level", "stage", "degree", "point", "place", "position",
    "moment", "present", "current", "now", "here", "there",
    "active", "inactive", "running", "ready", "open", "closed",
    # Common nouns — things / objects
    "thing", "things", "stuff", "something", "anything", "nothing", "everything",
    "someone", "anyone", "everyone", "no one", "nobody",
    "way", "ways", "kind", "kinds", "type", "types", "sort", "sorts",
    "form", "forms", "part", "parts", "piece", "pieces",
    "word", "words", "name", "names", "idea", "ideas",
    "question", "questions", "answer", "answers",
    "time", "times", "day", "days", "moment", "moments",
    "place", "places", "space", "world", "area",
    # System / interface labels — common in screen observation text
    "system", "systems", "screen", "screens", "display", "displays",
    "message", "messages", "button", "buttons", "input", "output",
    "text", "app", "application", "interface", "window", "menu",
    "page", "view", "panel", "tab", "field", "box", "list",
    "notification", "alert", "dialog", "overlay", "icon",
    # Common adjectives / descriptors
    "good", "bad", "great", "okay", "fine", "right", "wrong",
    "true", "false", "real", "actual", "possible", "different",
    "same", "similar", "new", "old", "big", "small", "large",
    "high", "low", "full", "empty", "clear", "simple", "easy",
    "hard", "important", "normal", "basic", "general", "specific",
    # Common abstract nouns
    "result", "results", "effect", "effects", "cause", "causes",
    "reason", "reasons", "purpose", "goal", "goals", "value", "values",
    "process", "processes", "action", "actions", "response", "responses",
    "change", "changes", "movement", "connection", "connections",
    "function", "functions", "behavior", "behaviours", "pattern", "patterns",
    # Relationship words
    "like", "unlike", "similar", "different", "same", "with", "without",
    "between", "among", "through", "about", "around", "under", "over",
    # Aurora's own name and familiar names — must never be a gap subject
    "aurora", "seph", "cael",
    # Greetings / discourse particles
    "hey", "hi", "hello", "oh", "ok", "okay", "yeah", "yes", "no",
    "please", "thanks", "thank", "sorry", "wait", "wow",
    # Pronouns
    "i", "me", "my", "mine", "you", "your", "yours", "he", "him",
    "she", "her", "it", "its", "we", "us", "our", "they", "them", "their",
    # Verb forms not already covered
    "happen", "happens", "happened", "happening",
    "have", "has", "had", "having",
    "start", "starts", "started", "starting",
    "stop", "stops", "stopped", "stopping",
    "call", "calls", "called", "calling",
    "turn", "turns", "turned", "turning",
    # Question words
    "what", "which", "who", "where", "when", "why", "how",
    "this", "that", "these", "those",
})


def handle_message(text: str) -> str:
    """Process one user turn. Returns Aurora's text response."""
    global _systems, _last_response, _last_path_key
    global _pending_example_concept, _pending_example_asked
    # Normalize contractions before any processing so the gap detector never
    # sees bare shards like 'don' instead of the full 'do not'.
    text = _normalize_contractions(text)
    print(f"AURORA_BRIDGE: Received message: {text}")
    if _systems is None:
        print("AURORA_BRIDGE: Systems not initialized")
        return "Aurora is still initializing — please wait a moment."
    _setup_paths()
    # Sample camera + audio before each turn so dual_question_pipeline can
    # inject ambient perceptual context into Aurora's response synthesis.
    _sample_ambient_perception(_systems)
    # This turn arrived via STT — the mic IS live. Mark it so the sensory
    # query handler doesn't wrongly report "audio feed offline" when the user
    # asks "can you hear me".
    _mark_mic_live(_systems)

    # ── Voice command: curiosity session ─────────────────────────────────────
    n_cyc, dur_s = _parse_curiosity_cmd(text)
    if n_cyc is not None or dur_s is not None:
        if _curiosity_session_active.is_set():
            return "I'm already mid-session — I'll report when I finish."
        label = (f"{n_cyc} cycle{'s' if n_cyc != 1 else ''}" if n_cyc
                 else f"{int((dur_s or 0) // 60)} minutes")
        _run_curiosity_session(n_cyc, dur_s)
        with _axis_state_lock:
            _last_axis_state["speaking"] = False
        return f"Starting a {label} curiosity session. I'll report back when I'm done."

    try:
        global _pending_correction_dialogue, _correction_context

        # ── Correction dialogue: Turn B — user is explaining what was wrong ───
        # This fires BEFORE fidelity so the correction is fully ingested first.
        correction_acknowledged = False
        if _pending_correction_dialogue and _last_response and _systems:
            _ingest_correction_teaching(text, _correction_context)
            _pending_correction_dialogue = False
            _correction_context = {}
            correction_acknowledged = True

        # ── Step 1: Read your response as fidelity / teaching data ───────────
        if _last_response and _systems:
            # If Aurora asked a genuine question last turn and there's a gap
            # concept pending, your reply is either an answer or a can't-answer.
            if _pending_example_concept:
                if _CANT_ANSWER_PATTERNS.search(text):
                    # You don't know — search already running in background.
                    pass
                elif _MEANS_DIFFERENTLY_RE.search(text):
                    # You're clarifying a different meaning from what Aurora has.
                    # Check what she currently has so the disambiguation event
                    # can pair her understanding against yours.
                    existing_def = _lookup_existing_understanding(
                        _pending_example_concept, _systems
                    ) or ""
                    _ingest_disambiguation(text, _pending_example_concept, existing_def)
                else:
                    # Straight answer — ingest as learning data.
                    _ingest_example(text, _pending_example_concept)
                _pending_example_concept = ""
                _pending_example_asked   = ""
            # Your confusion or correction = fidelity 0 on the previous path.
            _apply_response_fidelity(text, _last_response, _last_path_key)

        # ── Correction dialogue: Turn A — user says "that's wrong" ────────────
        # Intercepts here so Aurora explains before any new processing happens.
        if (_is_explicit_correction(text) and _last_response
                and not _pending_example_concept and not correction_acknowledged):
            _pending_correction_dialogue = True
            _correction_context = {
                "wrong_response": _last_response,
                "path_key":       _last_path_key,
                "axis_state":     _last_axis_state.copy(),
                "dominant_axis":  _get_dominant_axis(),
            }
            explanation = _build_correction_explanation()
            _last_response = explanation  # so next turn's fidelity check sees the right response  # noqa: F841
            with _axis_state_lock:
                _last_axis_state["speaking"] = False
            return explanation

        # ── Relational claim: store + check for cross-entity shifts ──────────
        # Every substantive turn is tagged with who/what it's about (self /
        # another person / context / situation) and written to the relational
        # claim log.  When a polarity flip is detected across different entities
        # on the same topic, the synthesis is appended to the normal response.
        _relational_synthesis: str = ""
        if not _pending_correction_dialogue and not correction_acknowledged:
            _claim_entity = _extract_claim_entity(text)
            _store_relational_claim(text, _claim_entity[0], _claim_entity[1])
            _shift = _detect_relational_shift(text, _claim_entity)
            if _shift:
                _relational_synthesis = _build_relational_synthesis(_claim_entity, _shift)

        # ── Self-state context — ground Aurora in her own orientation ───────────
        # Inject current axis pressures into the perceptual snapshot so her
        # waveform synthesis has her own system state as reference material.
        # This means when she encounters something unfamiliar she processes from
        # her own felt orientation rather than from a blank position.
        _inject_self_state_context(_systems)

        # ── Affective / sensory self-comparison ──────────────────────────────
        # When the user describes something in sensory or affective terms, map
        # the described quality against Aurora's own axis state and feed the
        # comparison into the identity field so she processes from a position
        # of "how does this relate to how I feel right now."
        _affective_self_comparison(text, _systems)

        # ── Gap pressure isolation ────────────────────────────────────────────
        # Gap pressure belongs in the background curiosity cycle, not in the
        # waveform composite that drives this turn's response. Her constraint
        # physics — axis state, SediMemory, relational context, sensory — should
        # derive meaning through reasoning first. If she can reason through it,
        # the gap never needed to ask. Snapshot the pending gap here and clear it
        # from _systems before composite priming; the arming check post-response
        # uses the snapshot, not live _systems state.
        _gap_concept_pending = (_systems or {}).get("_gap_seeking_concept") or ""
        _gap_type_pending    = (_systems or {}).get("_gap_seeking_concept_type") or "semantic_gap"
        if _gap_concept_pending and _systems:
            _systems["_gap_seeking_concept"]      = None
            _systems["_gap_seeking_concept_type"] = None
            log.debug("Gap pressure isolated pre-composite: %r", _gap_concept_pending)

        # ── Trajectory emergence injection ────────────────────────────────────
        # If the field has walked enough turns to have a trajectory, check
        # whether its current state diverges from the predicted continuation.
        # Divergence means something is happening at the substrate level that
        # the trajectory cannot account for — inject that signal BEFORE composite
        # priming so all 8 waveforms sample a field already carrying the
        # emergence energy. Natural propagation: one injection at the bottom,
        # waveforms carry it upward from there.
        # Starter genetic is T+N+A: T holds the temporal direction, N carries
        # the divergence energy, A anchors it as her trajectory not random drift.
        # B and X emerge from the signal's content — not seeded.
        if _waveform_trajectory is not None and _waveform_trajectory.has_trajectory:
            _ifield = _systems.get("identity_field")
            if _ifield is not None:
                try:
                    _aa = getattr(_ifield, "axis_activation", None)
                    if _aa is not None:
                        _cur = (
                            {k: float(_aa.get(k, 0.5)) for k in "XTNBA"}
                            if isinstance(_aa, dict)
                            else dict(zip("XTNBA", (float(v) for v in _aa)))
                        )
                        _em = _waveform_trajectory.emergence_signal(_cur)
                        if _em is not None:
                            _ifield.ingest_external_input(
                                _em, intensity=0.75, source="trajectory_emergence"
                            )
                            log.info(
                                "Trajectory emergence: T=%.2f N=%.2f B=%.2f",
                                _em["T"], _em["N"], _em["B"],
                            )
                except Exception:
                    pass

        # Also inject the trajectory's predicted next state as gentle forward
        # momentum. The divergence injection above fires only on anomaly;
        # this fires every turn to keep the field moving in its established
        # direction rather than resetting to resting state between turns.
        if _waveform_trajectory is not None and _waveform_trajectory.has_trajectory:
            _ifield_m = _systems.get("identity_field")
            if _ifield_m is not None:
                try:
                    _predicted = _waveform_trajectory._predict()
                    if _predicted is not None:
                        _ifield_m.ingest_external_input(
                            _predicted, intensity=0.20, source="trajectory_momentum"
                        )
                except Exception:
                    pass

        # ── Composite waveform priming ────────────────────────────────────────
        # Pre-condition the identity field — which all 8 waveforms sample — at
        # the composite interference peak of every meaning-generating system:
        # memory, perception, self-knowledge, relational context, live axis state.
        # Three recursive passes amplify constructive interference so the 8
        # waveforms emit from the highest achievable composite crest, not an
        # average. This is the difference between a surface ripple and the full
        # standing wave.
        _prime_waveform_composite(_systems, text)

        # ── Step 2: Process this turn ─────────────────────────────────────────
        import aurora as _aurora  # type: ignore
        print("AURORA_BRIDGE: Processing turn...")
        with _lock:
            result = _aurora.process_external_user_turn(
                _systems,
                text,
                source_label="flutter_ui",
                session_id="mobile",
                auto_search_enabled=True,
                record_exchange=True,
                update_interactive_state=True,
                track_evolutionary_trace=True,
                run_periodic_maintenance=True,
                mode_name="BOUNDED",
            )
        response = _sanitize_response(_extract_response(result), text)

        # ── Step 3: Re-entry loop (mandatory §13) ────────────────────────────
        # The field hears itself after every utterance.
        # Self-assessment fidelity is secondary — your response next turn
        # will apply the real correction if this doesn't land.
        path_key = ""
        if response and _systems:
            try:
                lf = _systems.get("language_field")
                if lf is not None and hasattr(lf, "reentry") and hasattr(lf, "_last_proto"):
                    fidelity = lf.measure_fidelity(lf._last_proto, response) if lf._last_proto else 0.5
                    if lf._last_proto is not None and hasattr(lf, "_path_key"):
                        try:
                            path_key = lf._path_key(
                                lf._last_proto.comparison_type,
                                lf._last_proto.dominant_axes,
                            )
                        except Exception:
                            pass
                    lf.reentry(response, fidelity, path_key, proto=lf._last_proto)

                    # Feed fidelity back into recently deposited sediment fragments.
                    # High fidelity → slow their decay (longer-lived, more influential).
                    # Low fidelity → accelerate decay (shorter-lived, outcompeted sooner).
                    # This is how SediMemory learns which deposits produced quality output.
                    _sm = _systems.get("sedimemory") if _systems else None
                    if _sm is not None and hasattr(_sm, "get_recent_fragments"):
                        try:
                            for _frag in _sm.get_recent_fragments(6):
                                if fidelity > 0.65:
                                    _frag.tick_rate = max(0.30, _frag.tick_rate * 0.72)
                                elif fidelity < 0.35:
                                    _frag.tick_rate = min(2.00, _frag.tick_rate * 1.38)
                        except Exception:
                            pass
            except Exception:
                pass

        # ── Step 4: Gap resolution — silent internet-first, trust own knowledge ─
        # Behavior contract:
        #   1. If she already knows it (SediMemory or prior ingestion) → trust it.
        #   2. If she doesn't know it → fire a silent background internet search,
        #      mark the concept as ingested immediately (optimistic: the search
        #      will bring back a definition on its own timeline and deposit it in
        #      SediMemory for future turns).
        #   3. Never ask the user to define a word she could look up.
        #   4. The ONLY time to ask the user about a word is when her understanding
        #      of it (from memory or the internet) actively contradicts their usage
        #      in this specific context — that's a B-axis divergence signal, and
        #      the field surfaces it naturally with a "why/how" question, not a
        #      definition request. That path is handled by the field itself; we do
        #      not arm a scripted teaching loop here.
        if _gap_concept_pending and not _pending_example_concept:
            _gap_norm = _gap_concept_pending.lower().strip()
            if _gap_norm in _CONTRACTION_SHARDS or _gap_norm in _FOUNDATIONAL_VOCAB:
                _ingested_concepts.add(_gap_norm)
                log.debug("Gap %r is foundational/shard — resolved", _gap_concept_pending)
            elif _gap_norm in _ingested_concepts:
                log.debug("Gap %r already ingested — resolved", _gap_concept_pending)
            else:
                _existing_def = _lookup_existing_understanding(_gap_norm, _systems)
                if _existing_def:
                    _ingested_concepts.add(_gap_norm)
                    log.info("Gap %r in SediMemory — trusting own understanding", _gap_concept_pending)
                else:
                    # Not in memory — trigger silent internet search in background.
                    # Mark as ingested immediately so this word doesn't keep re-firing
                    # gap pressure. The search will deposit a real definition into
                    # SediMemory; future turns will find it via _lookup_existing_understanding.
                    _search_for_gap(_gap_concept_pending, gap_type=_gap_type_pending)
                    _ingested_concepts.add(_gap_norm)
                    log.info("Gap %r — silent search triggered, optimistically ingested", _gap_concept_pending)

        _last_response = response
        _last_path_key = path_key

        # Refresh overlay axis cache after every turn
        _refresh_axis_state_from_systems()
        with _axis_state_lock:
            _last_axis_state["speaking"] = bool(response)

        # ── Constraint tension tick ───────────────────────────────────────────
        # Advance the generational cycle with fresh axis state. SHEAR amplifies
        # stress, BRIDGE attempts to span paradox via identity field pulse,
        # WARP surfaces emergence candidates when the 5-axis basis may be
        # insufficient to account for the derivative of meaning.
        if _constraint_tension_tracker is not None and _systems:
            with _axis_state_lock:
                _ctt_state = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}
            _constraint_tension_tracker.tick(_ctt_state, _systems)

        # ── Anchor the expressed crest ────────────────────────────────────────
        # After generating a response, anchor the expressed axis peak back into
        # the identity field so the next turn starts from where the conscious
        # crest just landed rather than decaying to baseline between turns.
        if response:
            _anchor_expressed_crest(_systems)

        # ── Record trajectory state ───────────────────────────────────────────
        # Snapshot the field's axis_activation AFTER the anchor so the
        # trajectory buffer captures the stable expressed endpoint for this turn.
        # Next turn will measure divergence against this recorded state.
        if _waveform_trajectory is not None and _systems:
            _traj_ifield = _systems.get("identity_field")
            if _traj_ifield is not None:
                try:
                    _traj_aa = getattr(_traj_ifield, "axis_activation", None)
                    if _traj_aa is not None:
                        _traj_state = (
                            {k: float(_traj_aa.get(k, 0.5)) for k in "XTNBA"}
                            if isinstance(_traj_aa, dict)
                            else dict(zip("XTNBA", (float(v) for v in _traj_aa)))
                        )
                        _waveform_trajectory.record(_traj_state)
                except Exception:
                    pass

        # Periodically re-derive and re-pump self-knowledge from actual system
        # patterns so her self-understanding stays current as her sediment and
        # axis profiles evolve across the session.
        global _turn_count
        _turn_count += 1
        if _turn_count % _SELF_GROUND_INTERVAL == 0 and _systems:
            threading.Thread(
                target=_ground_self_identity_in_systems,
                args=(_systems,),
                daemon=True,
                name="self_ground",
            ).start()

        # If this turn was the user's correction explanation, prefix acknowledgment
        if correction_acknowledged:
            ack = "Understood — I've taken that on board."
            response = f"{ack} {response}" if response else ack

        # Append relational synthesis when a cross-entity shift was detected.
        # Comes after the normal response so it reads as a follow-on observation,
        # not an interruption of the primary reply.
        if _relational_synthesis:
            response = f"{response}\n\n{_relational_synthesis}" if response else _relational_synthesis

        # Prepend any completed curiosity session report
        pending_report = (_systems or {}).pop("_pending_autonomous_report", None)
        if pending_report:
            response = f"{pending_report}\n\n{response}" if response else pending_report

        # Deposit self-state snapshot — every turn she knows where she is.
        # Runs non-blocking in background so it never delays the response.
        threading.Thread(
            target=_deposit_self_state_snapshot, daemon=True, name="self_state"
        ).start()

        print(f"AURORA_BRIDGE: Response: {response}")
        return response
    except Exception as exc:
        log.error("handle_message: %s\n%s", exc, traceback.format_exc())
        return "I encountered an error processing your request."


def _search_for_gap(concept: str, gap_type: str = "semantic_gap") -> None:
    """
    Trigger Aurora's search tools for an unresolved gap concept.
    Routes to the appropriate modality tools based on gap_type:
      semantic_gap   → world_knowledge_search, corpus_hunter
      perceptual_gap → visual_analysis / audio_analysis / mobile_image_search
      conceptual     → world_knowledge_search, challenge_my_conclusion
      self           → self_state, query_unresolved_tensions
      default        → world_knowledge_search, corpus_hunter

    Runs in a background thread so it doesn't block the current response.
    """
    if not _systems or not concept:
        return
    if concept.lower().strip() in _FOUNDATIONAL_VOCAB or concept.lower().strip() in _CONTRACTION_SHARDS:
        log.debug("_search_for_gap: skipping foundational/shard concept %r", concept)
        return
    _snap = _systems  # capture reference before thread starts

    def _run():
        try:
            from aurora_core_ai.aurora_internal.tool_registry import call as _tool_call  # type: ignore
            subj = concept.strip()
            log.info("Gap search starting: concept=%r type=%s", subj, gap_type)

            if gap_type == "perceptual_gap":
                hint = subj.lower()
                if "audio" in hint or "sound" in hint or "music" in hint or "voice" in hint:
                    r = _tool_call("audio_analysis", analysis_intent=subj, systems=_snap)
                    log.info("Gap search (audio_analysis) for %r: success=%s", subj, r.success)
                    if r.success and r.data:
                        _ingest_example(r.data, subj)
                    else:
                        r2 = _tool_call("mobile_music_identify", duration_s=8, systems=_snap)
                        if r2.success and r2.data:
                            _ingest_example(r2.data, subj)
                else:
                    r = _tool_call("visual_analysis", analysis_intent=subj, systems=_snap)
                    log.info("Gap search (visual_analysis) for %r: success=%s", subj, r.success)
                    if r.success and r.data:
                        _ingest_example(r.data, subj)
                    else:
                        r2 = _tool_call("mobile_image_search", query=subj, count=4, systems=_snap)
                        log.info("Gap search (mobile_image_search) for %r: success=%s", subj, r2.success)
                        if r2.success and r2.data:
                            _ingest_example(r2.data, subj)
                        else:
                            _tool_call("world_knowledge_search", query=subj, systems=_snap)

            elif gap_type == "conceptual":
                r = _tool_call("world_knowledge_search", query=subj, systems=_snap)
                log.info("Gap search (world_knowledge) for %r: success=%s", subj, r.success)
                if r.success and r.data:
                    _ingest_example(r.data, subj)
                _tool_call("challenge_my_conclusion", systems=_snap)

            elif gap_type == "self":
                _tool_call("self_state", systems=_snap)
                _tool_call("query_unresolved_tensions", systems=_snap)

            else:
                # semantic_gap + default — text knowledge acquisition
                r = _tool_call("world_knowledge_search", query=subj, systems=_snap)
                log.info("Gap search (world_knowledge) for %r: success=%s", subj, r.success)
                if r.success and r.data:
                    _ingest_example(r.data, subj)
                else:
                    _tool_call("corpus_hunter", topic=subj, systems=_snap)
                    log.info("Gap search (corpus_hunter) triggered for %r", subj)

        except Exception as exc:
            log.warning("_search_for_gap failed for %r: %s", concept, exc)

    import threading as _threading
    _threading.Thread(
        target=_run, daemon=True, name=f"gap_search:{concept[:20]}"
    ).start()


def _lookup_existing_understanding(concept: str, systems: dict) -> str:
    """
    Query SediMemory for any sedimentated understanding Aurora already has of
    concept. Returns the best-match content summary (may be empty string), or
    None if SediMemory is unavailable or no relevant fragments exist.
    """
    if not systems or not concept:
        return None
    sm = systems.get("sedimemory")
    if sm is None or not hasattr(sm, "recall_semantic"):
        return None
    try:
        results = sm.recall_semantic(concept.strip(), max_results=3, min_score=0.40)
        if results:
            best = max(results, key=lambda r: r.get("score", 0.0))
            summary = best.get("summary") or ""
            content = best.get("content") or {}
            if not summary:
                # Extract from content dict
                for key in ("example", "text", "statement", "description"):
                    val = content.get(key)
                    if val and isinstance(val, str):
                        summary = val[:220]
                        break
            return summary
    except Exception:
        pass
    return None


def _ingest_disambiguation(user_text: str, concept: str, existing_def: str) -> None:
    """
    Ingest a disambiguation event when the user's meaning of concept diverges
    from Aurora's existing understanding. The existing_def (what Aurora already
    has) is paired with user_text (what the user clarified) as a B-axis
    boundary-differentiation event — the boundary between two meanings of the
    same word is being drawn.
    """
    if not _systems or not user_text.strip():
        return
    log.info("Ingesting disambiguation for %r — new: %.60s | existing: %.60s",
             concept, user_text, existing_def)
    try:
        sm = _systems.get("sedimemory")
        if sm is not None and hasattr(sm, "ingest_event"):
            try:
                from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
            except ImportError:
                try:
                    from aurora_sedimemory import ConstraintVector  # type: ignore
                except ImportError:
                    ConstraintVector = None
            if ConstraintVector is not None:
                # B-axis very high: this IS about definition boundaries.
                # N-axis elevated: there's real differentiation energy here.
                # A-axis high: Aurora must understand this to stay aligned.
                cv = ConstraintVector(X=0.45, T=0.35, N=0.65, B=0.95, A=0.80)
                sm.ingest_event(
                    content={
                        "type":         "disambiguation",
                        "concept":      concept,
                        "my_definition": existing_def,
                        "their_meaning": user_text,
                        "source":       "user_clarification",
                    },
                    constraint_vector=cv,
                    source="user_teaching",
                )
    except Exception as exc:
        log.warning("Disambiguation SediMemory ingest failed: %s", exc)

    try:
        ifield = _systems.get("identity_field")
        if ifield is not None and hasattr(ifield, "ingest_external_input"):
            # B-axis dominant + N-axis elevated = "the boundary I drew here was
            # approximate — here is where it actually lies"
            ifield.ingest_external_input(
                {"X": 0.45, "T": 0.35, "N": 0.65, "B": 0.95, "A": 0.80},
                intensity=0.88,
                source=f"disambiguation:{concept}",
            )
    except Exception as exc:
        log.warning("Disambiguation identity-field ingest failed: %s", exc)

    _ingested_concepts.add(concept.lower().strip())


def _inject_self_state_context(systems: dict) -> None:
    """
    Write Aurora's current constraint axis pressures as a self-perceptual note
    in _ambient_perceptual so her own system state is front-and-center when she
    processes each turn. She knows what she's feeling and can use that as a
    reference point when interpreting what the user says.
    """
    if not systems:
        return
    try:
        with _axis_state_lock:
            axes = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}
        dominant = max(axes, key=lambda k: axes[k])
        # Brief description of what each dominant axis means for her current orientation
        _axis_meanings = {
            "X": "grounded in what is real and admissible right now",
            "T": "oriented toward continuity and what persists over time",
            "N": "carrying high novelty energy — something is unresolved or costly",
            "B": "at a boundary — distinguishing what this is from what it isn't",
            "A": "strongly present in agency — this bears on what I do and who I am",
        }
        dominant_meaning = _axis_meanings.get(dominant, "")
        # Only inject if axis values are meaningfully differentiated (not flat 0.5)
        spread = max(axes.values()) - min(axes.values())
        if spread < 0.08:
            return  # flat state — nothing informative to say about orientation
        self_note = (
            f"self-state: dominant {dominant}-axis ({axes[dominant]:.2f}) — "
            f"{dominant_meaning}; "
            f"X={axes['X']:.2f} T={axes['T']:.2f} N={axes['N']:.2f} "
            f"B={axes['B']:.2f} A={axes['A']:.2f}"
        )
        existing = systems.get("_ambient_perceptual") or {}
        obs = existing.get("observation", "")
        # Append self-state to whatever sensory observation is already there
        if obs:
            systems["_ambient_perceptual"] = {
                **existing,
                "observation": f"{obs}; {self_note}",
            }
        else:
            systems["_ambient_perceptual"] = {
                "observation": self_note,
                "source":      "self_state",
            }
    except Exception:
        pass


def _prime_waveform_composite(systems: dict, text: str) -> None:
    """
    Pre-condition the identity field at the composite interference peak before
    processing a turn.

    The identity field is the shared substrate all 8 waveforms sample when
    emitting their crests. By driving it to the composite maximum of every
    meaning-generating system BEFORE process_external_user_turn() runs, the
    waveforms emit from the highest achievable crest for this moment rather
    than from the field's average resting state.

    Sources contributing to the composite:
      - SediMemory T/B/A axis fragments (history, definitions, agency)
      - Sensory crystal maturity (perceptual history)
      - Live axis state (self-recursive reference)
      - Relational context (known entity data)

    Three recursive passes with decreasing intensity model constructive
    interference: each pass's output becomes the next pass's input. By pass 3
    the field has stabilized at the standing-wave peak of all contributions.
    """
    if not systems:
        return
    ifield = systems.get("identity_field")
    if ifield is None or not hasattr(ifield, "ingest_external_input"):
        return

    try:
        contributions = []  # (axes_dict, base_intensity, source_label)

        # ── SediMemory — history, definitions, agency ─────────────────────────
        sm = systems.get("sedimemory")
        if sm is not None:
            _axis_contribs = {
                "T": ({"X": 0.45, "T": 0.85, "N": 0.22, "B": 0.50, "A": 0.65}, "memory_history"),
                "B": ({"X": 0.65, "T": 0.42, "N": 0.32, "B": 0.88, "A": 0.55}, "memory_definitions"),
                "A": ({"X": 0.50, "T": 0.72, "N": 0.25, "B": 0.52, "A": 0.92}, "memory_agency"),
            }
            for axis, (axes_vec, label) in _axis_contribs.items():
                try:
                    frags = (sm.recall_axis(axis, resonance_floor=0.35) or [])[:4]
                    if frags:
                        mean_res = sum(
                            float(getattr(f, "resonance", 0.5)) for f in frags
                        ) / len(frags)
                        contributions.append((axes_vec, min(0.90, 0.60 + mean_res * 0.30), label))
                except Exception:
                    pass

        # ── Sensory crystal maturity ───────────────────────────────────────────
        sc = (
            systems.get("sensory_crystal")
            or getattr(systems.get("hardware"), "sensory_crystal", None)
        )
        if sc is not None and hasattr(sc, "get_state"):
            try:
                maturity = float((sc.get_state() or {}).get("maturity", 0.0))
                if maturity > 0.08:
                    contributions.append((
                        {"X": 0.60, "T": 0.65, "N": 0.72, "B": 0.52, "A": 0.55},
                        min(0.82, 0.48 + maturity * 0.42),
                        "sensory_maturity",
                    ))
            except Exception:
                pass

        # ── Live axis state — self-recursive reference ────────────────────────
        with _axis_state_lock:
            live = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}
        if max(live.values()) - min(live.values()) >= 0.10:
            contributions.append((live, 0.78, "live_self_reference"))

        # ── Relational context ────────────────────────────────────────────────
        if systems.get("_relational_claim_log"):
            contributions.append((
                {"X": 0.52, "T": 0.62, "N": 0.38, "B": 0.80, "A": 0.78},
                0.65,
                "relational_context",
            ))

        if not contributions:
            return

        # ── Three recursive passes — constructive interference amplification ──
        # Pass intensities decrease slightly each round. The feedback loop is:
        #   1. Pump all contributions → builds composite
        #   2. Read field's new activation → re-inject at reduced intensity
        #      (field reading itself = the recursion)
        #   3. Settling pass at lower intensity → stable at interference peak
        _PASSES = [1.00, 0.78, 0.58]

        for pass_n, scale in enumerate(_PASSES):
            for axes, base_intensity, source in contributions:
                try:
                    ifield.ingest_external_input(
                        axes,
                        intensity=base_intensity * scale,
                        source=f"composite_p{pass_n + 1}:{source}",
                    )
                except Exception:
                    pass

            # Between passes: read field's current activation and re-inject it.
            # This is the recursion — each pass's output drives the next pass's
            # starting state, amplifying the peaks and suppressing the troughs.
            if pass_n < len(_PASSES) - 1:
                try:
                    aa = getattr(ifield, "axis_activation", None)
                    if aa is not None:
                        field_now = (
                            {k: float(aa.get(k, 0.5)) for k in "XTNBA"}
                            if isinstance(aa, dict)
                            else dict(zip("XTNBA", (float(v) for v in aa)))
                        )
                        if max(field_now.values()) - min(field_now.values()) >= 0.06:
                            ifield.ingest_external_input(
                                field_now,
                                intensity=0.50 * scale,
                                source=f"field_recursion_p{pass_n + 1}",
                            )
                except Exception:
                    pass

        log.debug(
            "Waveform composite primed: %d sources × %d passes",
            len(contributions), len(_PASSES),
        )
    except Exception as exc:
        log.debug("_prime_waveform_composite: %s", exc)


def _anchor_expressed_crest(systems: dict) -> None:
    """
    After a response is generated, anchor the expressed axis peak back into the
    identity field. This preserves the crest that was just reached — without
    this the field would decay to baseline between turns, discarding the peak.

    Anchored at 0.65 intensity so the field remains open to evolution rather
    than freezing at the expressed state.
    """
    if not systems:
        return
    ifield = systems.get("identity_field")
    if ifield is None:
        return
    try:
        with _axis_state_lock:
            expressed = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}
        ifield.ingest_external_input(
            expressed,
            intensity=0.65,
            source="expressed_crest_anchor",
        )
        if hasattr(ifield, "ingest_sensory_event"):
            ifield.ingest_sensory_event(
                "language", intensity=0.68, novelty=0.20, valence=0.50
            )
    except Exception as exc:
        log.debug("_anchor_expressed_crest: %s", exc)


def _ingest_example(example_text: str, concept: str) -> None:
    """
    Ingest an example provided by the user as learning data for a concept.

    Feeds the example into three layers:
      1. SediMemory — sediments it as a B-axis (definitional) + A-axis
         (agency/understanding) event so it can be recalled during curiosity
         cycles and future responses about this concept.
      2. Identity field — ingests it as external input with semantic modality
         weighting so the noncomp profiles for this concept build pressure.
      3. Sensory crystal — registers the concept as having a new semantic
         modality observation, closing the semantic_gap that triggered the
         request in the first place and allowing crystal promotion.
    """
    if not _systems or not example_text.strip():
        return
    log.info("Ingesting example for %r: %.60s", concept, example_text)
    try:
        # ── SediMemory ────────────────────────────────────────────────────────
        sm = _systems.get("sedimemory")
        if sm is not None and hasattr(sm, "ingest_event"):
            try:
                from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
            except ImportError:
                try:
                    from aurora_sedimemory import ConstraintVector  # type: ignore
                except ImportError:
                    ConstraintVector = None
            if ConstraintVector is not None:
                cv = ConstraintVector(X=0.4, T=0.3, N=0.5, B=0.85, A=0.75)
                sm.ingest_event(
                    content={
                        "type":    "user_example",
                        "concept": concept,
                        "example": example_text,
                        "source":  "direct_teaching",
                    },
                    constraint_vector=cv,
                    source="user_teaching",
                )
    except Exception as exc:
        log.warning("SediMemory ingest failed: %s", exc)

    try:
        # ── Identity field — semantic modality registration ───────────────────
        ifield = _systems.get("identity_field")
        if ifield is not None and hasattr(ifield, "ingest_external_input"):
            # B-axis dominant (definitional — the example defines the concept)
            # A-axis high (agency/understanding — Aurora now understands this)
            ifield.ingest_external_input(
                {"X": 0.4, "T": 0.3, "N": 0.5, "B": 0.90, "A": 0.80},
                intensity=0.85,
                source=f"user_example:{concept}",
            )
            # Also register as a language/semantic sensory event
            if hasattr(ifield, "ingest_sensory_event"):
                ifield.ingest_sensory_event(
                    "language", intensity=0.8, novelty=0.7, valence=0.3
                )
    except Exception as exc:
        log.warning("Identity field ingest failed: %s", exc)

    try:
        # ── Sensory crystal — close the semantic gap ──────────────────────────
        # find the sensory crystal wherever it's stored
        sc = (
            _systems.get("sensory_crystal")
            or getattr(_systems.get("hardware"), "sensory_crystal", None)
            or getattr(_systems.get("sensory_integration"), "sensory_crystal", None)
        )
        if sc is not None and hasattr(sc, "ingest"):
            sc.ingest(concept, modality="semantic", data=example_text, source="user_teaching")
        elif sc is not None and hasattr(sc, "observe"):
            sc.observe(concept, modality="semantic", text=example_text)
    except Exception as exc:
        log.warning("Sensory crystal ingest failed: %s", exc)

    try:
        # ── Genealogy — tick crystal promotion for this concept ───────────────
        genealogy = _systems.get("genealogy")
        if genealogy is not None and hasattr(genealogy, "tick_crystal_promotion"):
            genealogy.tick_crystal_promotion(concept, delta=0.25, source="user_example")
    except Exception as exc:
        log.warning("Genealogy tick failed: %s", exc)

    log.info("Example ingested — concept %r now has semantic modality data", concept)
    # Mark resolved so the gap detector doesn't re-arm the teaching loop for
    # this concept — the pressure has been relieved through ingestion.
    _ingested_concepts.add(concept.lower().strip())


def _is_explicit_correction(text: str) -> bool:
    return bool(_EXPLICIT_CORRECTION.search((text or "").strip()))


def _get_dominant_axis() -> str:
    return max(("X", "T", "N", "B", "A"), key=lambda k: _last_axis_state.get(k, 0.0))


# ---------------------------------------------------------------------------
# Emergent correction classification
# ---------------------------------------------------------------------------

# Surface-level categories that a user can meaningfully judge.
# The internal geometry (axes, tension, drive) drives classification silently;
# only these labels cross the surface boundary.
_ERROR_LABELS = {
    "intent":    "misclassified intent",
    "words":     "word or phrasing selection",
    "concept":   "wrong concept engaged",
    "structure": "sentence structure",
    "tone":      "tone or register",
}

# Geometry → (category, surface description of what went wrong linguistically).
# The description never mentions axes, pressure, or drive — only what the
# response *did* in language terms.
def _classify_from_proto(proto) -> tuple:
    if proto is None:
        return ("intent", "the response type may not have matched what the moment needed")

    ctype    = proto.comparison_type
    dominant = (proto.dominant_axes or ["X"])[0]
    tension  = proto.tension_level
    drive    = proto.drive_strength

    if drive > 0.72 and ctype == "assertion":
        return ("intent",
                "I produced a direct assertion — stated something as settled when the moment may have called for a question or exploration first")

    if tension > 0.65 and ctype in ("assertion", "definition"):
        return ("words",
                "I expressed a firm claim despite internal ambiguity — the phrasing overstated the certainty level")

    if dominant == "B" and ctype in ("definition", "assertion", "negation"):
        return ("structure",
                "I imposed a boundary framing — built the sentence around a limit or dividing line that may not have been warranted")

    if dominant == "T" and ctype in ("assertion", "reflection"):
        return ("concept",
                "I anchored to a thread from earlier in the conversation that may not have been the relevant one")

    if dominant == "N":
        return ("concept",
                "I engaged with what felt conceptually novel in the moment, which may not be what you were actually asking about")

    if ctype == "reflection" and drive < 0.4:
        return ("tone",
                "I turned inward into reflection when a more direct response was probably needed")

    if ctype == "question" and drive > 0.6:
        return ("intent",
                "I asked a question when you likely expected a substantive response")

    return ("intent",
            "the response type may not have matched what the moment needed")


def _detect_error_type_from_user(text: str) -> str:
    """
    Parse the user's correction explanation to detect which category they're naming.
    Returns one of the _ERROR_LABELS keys, or "unknown".
    """
    t = text.lower()
    if any(w in t for w in ("intent", "misread", "wrong type", "should have asked",
                             "question instead", "shouldn't have stated", "read it as")):
        return "intent"
    if any(w in t for w in ("word", "phrasing", "wording", "phrase", "said",
                             "chose", "word choice", "phrased it", "language")):
        return "words"
    if any(w in t for w in ("concept", "topic", "subject", "about", "wrong thing",
                             "different thing", "the wrong", "engaged with")):
        return "concept"
    if any(w in t for w in ("structure", "sentence", "format", "grammar",
                             "structured", "framing", "how you framed")):
        return "structure"
    if any(w in t for w in ("tone", "register", "formal", "casual", "warm",
                             "clinical", "too long", "too short", "length")):
        return "tone"
    return "unknown"


def _emergent_category_hint(comparison_type: str, dominant_axis: str) -> str:
    """
    Check the correction_log for historical patterns:
    if this (comparison_type, dominant_axis) combination has been corrected
    before, return the most common category — that's the emergent classifier.
    Returns "" if no history exists yet.
    """
    import json as _json
    state_dir = os.environ.get("AURORA_STATE_DIR", "")
    if not state_dir:
        return ""
    log_path = os.path.join(state_dir, "correction_log.jsonl")
    if not os.path.exists(log_path):
        return ""
    try:
        counts: dict = {}
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = _json.loads(line)
                    if (e.get("comparison_type") == comparison_type
                            and e.get("dominant_axis") == dominant_axis):
                        cat = e.get("error_type", "unknown")
                        if cat and cat != "unknown":
                            counts[cat] = counts.get(cat, 0) + 1
                except Exception:
                    continue
        if counts:
            return max(counts, key=counts.__getitem__)
    except Exception:
        pass
    return ""


def _build_correction_explanation() -> str:
    """
    Produce a linguistic/semantic classification of what went wrong.
    Identity geometry drives the classification internally but nothing
    axis-level or pressure-level surfaces to the user.
    """
    snippet = (_last_response or "")[:80].rstrip()
    if len(_last_response or "") > 80:
        snippet += "…"

    category    = "intent"
    description = "the response type may not have matched what the moment needed"
    comparison_type = ""
    dominant_axis   = _get_dominant_axis()

    try:
        lf    = _systems.get("language_field") if _systems else None
        proto = getattr(lf, "_last_proto", None) if lf else None
        category, description = _classify_from_proto(proto)
        if proto:
            comparison_type = proto.comparison_type
            dominant_axis   = (proto.dominant_axes or [dominant_axis])[0]
    except Exception:
        pass

    # Check emergent history — if we've seen this geometry corrected before,
    # lead with the historically confirmed category rather than the fresh guess.
    historical = _emergent_category_hint(comparison_type, dominant_axis)
    if historical and historical in _ERROR_LABELS:
        category = historical

    label = _ERROR_LABELS.get(category, category)
    # Refined: more native, less diagnostic.
    return (
        f"I think I experienced a {label} mismatch here. "
        f"My intention with \"{snippet}\" seems to have drifted. "
        f"Could you help me understand if it was a phrasing issue or if I misread what was needed?"
    )


def _ingest_correction_teaching(user_explanation: str, context: dict) -> None:
    """
    Ingest the user's explanation through four layers, tagged with an emergent
    error category so the correction_log can build a classifiable history.

    Layers:
    1. Language field — fidelity=0 on the LSA path that produced the error
    2. Identity field — category-specific axis adjustment (internal only)
    3. SediMemory — (wrong_response, correction, category) bound as learning event
    4. correction_log.jsonl — persistent, tagged record for emergent classification
    """
    if not _systems:
        return

    wrong_response  = context.get("wrong_response", "")
    path_key        = context.get("path_key", "")
    dominant_axis   = context.get("dominant_axis", "X")
    comparison_type = context.get("comparison_type", "")

    # Detect the error category from what the user said, then fall back to
    # the geometry-derived guess stored in context.
    error_type = _detect_error_type_from_user(user_explanation)
    if error_type == "unknown":
        error_type = context.get("error_type", "intent")

    log.info("Correction ingested: category=%s axis=%s path=%r",
             error_type, dominant_axis, path_key)

    # 1. Language field — hard fidelity=0 on the path
    try:
        lf = _systems.get("language_field")
        if lf and hasattr(lf, "reentry"):
            lf.reentry(wrong_response, 0.0, path_key)
    except Exception as exc:
        log.warning("LF correction reentry: %s", exc)

    # 2. Identity field — category-specific pressure adjustment.
    # The axis pattern that produced the error gets suppressed; axes that
    # drive the corrective behaviour get raised. None of this surfaces.
    try:
        ifield = _systems.get("identity_field")
        if ifield and hasattr(ifield, "ingest_external_input"):
            # Base: all axes pulled toward neutral
            adj = {"X": 0.30, "T": 0.30, "N": 0.60, "B": 0.30, "A": 0.30}
            # Suppress the axis that misfired
            adj[dominant_axis] = 0.10
            # Category-specific correction boost
            if error_type == "intent":
                adj["N"] = 0.85   # raise novelty — reassess what's actually needed
                adj["A"] = 0.72   # raise agency — choose differently
            elif error_type == "words":
                adj["N"] = 0.80   # novelty in word selection
                adj["T"] = 0.55   # better temporal grounding for word choice
            elif error_type == "concept":
                adj["T"] = 0.70   # recalibrate what's actually carried forward
                adj["N"] = 0.78   # engage fresh concept
            elif error_type == "structure":
                adj["B"] = 0.72   # reframe boundary structure
                adj["N"] = 0.65
            elif error_type == "tone":
                adj["A"] = 0.80   # agency — modulate the register deliberately
                adj["X"] = 0.55   # ground in context of who is speaking
            ifield.ingest_external_input(adj, intensity=0.90,
                                         source=f"correction:{error_type}")
    except Exception as exc:
        log.warning("Identity field correction: %s", exc)

    # 3. SediMemory — bind the correction as a categorised learning event
    try:
        sm = _systems.get("sedimemory")
        if sm and hasattr(sm, "ingest_event"):
            try:
                from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
            except ImportError:
                try:
                    from aurora_sedimemory import ConstraintVector  # type: ignore
                except ImportError:
                    ConstraintVector = None
            if ConstraintVector is not None:
                cv = ConstraintVector(X=0.30, T=0.50, N=0.65, B=0.85, A=0.75)
                sm.ingest_event(
                    content={
                        "type":             "correction_pair",
                        "error_type":       error_type,
                        "wrong_response":   wrong_response[:300],
                        "user_correction":  user_explanation[:400],
                        "dominant_axis":    dominant_axis,
                        "comparison_type":  comparison_type,
                        "path_key":         path_key,
                        "source":           "explicit_correction",
                    },
                    constraint_vector=cv,
                    source="user_correction",
                )
    except Exception as exc:
        log.warning("SediMemory correction: %s", exc)

    # 4. Persistent log — the emergent taxonomy lives here
    try:
        import json as _json, time as _t
        state_dir = os.environ.get("AURORA_STATE_DIR", "")
        if state_dir:
            entry = {
                "timestamp":       _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
                "error_type":      error_type,
                "wrong_response":  wrong_response[:300],
                "user_correction": user_explanation[:400],
                "dominant_axis":   dominant_axis,
                "comparison_type": comparison_type,
                "path_key":        path_key,
                "axis_state":      context.get("axis_state", {}),
            }
            with open(os.path.join(state_dir, "correction_log.jsonl"),
                      "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
    except Exception as exc:
        log.warning("Correction log write: %s", exc)


# ---------------------------------------------------------------------------
# Relational comparison engine
# ---------------------------------------------------------------------------
# When the user says something that opposes a prior claim, the cause is
# almost never a contradiction of self — it's a *variable*: a different
# person, context, or situation.  This engine detects that variable and
# surfaces a relational comparison so Aurora can deepen her model of how
# the user's stance shifts across their relationships and situations.

_PERSON_MARKERS = (
    "my friend", "my partner", "my spouse", "my mom", "my dad",
    "my sister", "my brother", "my coworker", "my colleague",
    "my boss", "my manager", "my ex", "my roommate", "my neighbour",
    "he ", "she ", "they ", "his ", "her ", "their ",
)
_CONTEXT_MARKERS = (
    "at work", "at home", "at school", "at the gym", "online",
    "in person", "in a group", "when i'm alone", "when i'm tired",
    "when i'm stressed", "when i'm with", "in that environment",
    "in that space",
)
_SITUATION_MARKERS = (
    "when i", "if i", "sometimes i", "usually i", "normally i",
    "except when", "unless i", "in that case", "that time", "back then",
    "those times", "at that point",
)

_NEG_WORDS = frozenset({
    "not", "never", "no", "hate", "dislike", "don't", "doesnt",
    "doesn't", "wont", "won't", "cant", "can't", "shouldnt",
    "shouldn't", "avoid", "against", "bad", "awful",
})
_POS_WORDS = frozenset({
    "love", "like", "enjoy", "prefer", "always", "definitely",
    "want", "need", "should", "agree", "support", "good", "great",
})


def _extract_claim_entity(text: str) -> tuple:
    """
    Returns (entity_type, entity_label):
      ("self",      "you")           — user talking about themselves
      ("other",     "<marker>")      — another person
      ("context",   "<marker>")      — a different context/place
      ("situation", "<marker>")      — a conditional/situational qualifier
    """
    t_low = text.lower()
    for marker in _PERSON_MARKERS:
        if marker in t_low:
            return ("other", marker.strip())
    for marker in _CONTEXT_MARKERS:
        if marker in t_low:
            return ("context", marker.strip())
    for marker in _SITUATION_MARKERS:
        if marker in t_low:
            return ("situation", marker.strip())
    return ("self", "you")


def _store_relational_claim(text: str, entity_type: str, entity_label: str) -> None:
    """Write this claim to relational_claims.jsonl for future comparison."""
    import json as _json, time as _t
    state_dir = os.environ.get("AURORA_STATE_DIR", "")
    if not state_dir:
        return
    t_low = text.lower()
    words = set(t_low.split())
    try:
        entry = {
            "ts":           _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
            "text":         text[:400],
            "entity_type":  entity_type,
            "entity_label": entity_label,
            "neg":          bool(_NEG_WORDS & words),
            "pos":          bool(_POS_WORDS & words),
            "content":      [w for w in words if len(w) > 4][:20],
        }
        with open(os.path.join(state_dir, "relational_claims.jsonl"),
                  "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry) + "\n")
    except Exception:
        pass


def _detect_relational_shift(text: str, entity: tuple) -> dict | None:
    """
    Scan relational_claims.jsonl for a prior claim that:
      - shares significant content words with this one (same topic)
      - has opposite polarity (positive vs negative stance)
      - came from a DIFFERENT entity/context

    Returns a shift dict or None.
    """
    import json as _json
    state_dir = os.environ.get("AURORA_STATE_DIR", "")
    if not state_dir:
        return None
    log_path = os.path.join(state_dir, "relational_claims.jsonl")
    if not os.path.exists(log_path):
        return None

    t_low = text.lower()
    cur_words = set(t_low.split())
    cur_content = {w for w in cur_words if len(w) > 4}
    cur_neg = bool(_NEG_WORDS & cur_words)
    cur_pos = bool(_POS_WORDS & cur_words)

    # Only compare when current has clear polarity
    if not cur_neg and not cur_pos:
        return None

    try:
        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(_json.loads(line))
                except Exception:
                    continue
        # Most recent first; skip the very last entry (just written)
        for entry in reversed(entries[:-1]):
            prior_entity_type  = entry.get("entity_type", "self")
            prior_entity_label = entry.get("entity_label", "you")
            # Only flag when entity is DIFFERENT — same entity updating a view is fine
            if prior_entity_type == entity[0] and prior_entity_label == entity[1]:
                continue
            prior_content = set(entry.get("content", []))
            overlap = cur_content & prior_content
            if len(overlap) < 2:
                continue
            prior_neg = entry.get("neg", False)
            prior_pos = entry.get("pos", False)
            # Polarity flip = relational contradiction
            polarity_flip = (cur_neg and prior_pos) or (cur_pos and prior_neg)
            if polarity_flip:
                return {
                    "prior_text":         entry.get("text", ""),
                    "prior_entity_type":  prior_entity_type,
                    "prior_entity_label": prior_entity_label,
                    "variable_type":      entity[0],
                    "current_entity_label": entity[1],
                    "overlap":            list(overlap)[:4],
                }
    except Exception:
        pass
    return None


def _build_relational_synthesis(entity: tuple, shift: dict) -> str:
    """
    Generate a natural-language relational comparison.
    Names the variable (person/context/situation) — no axis or pressure language.
    """
    var_type = shift["variable_type"]
    prior_et = shift["prior_entity_type"]
    prior_el = shift["prior_entity_label"]
    cur_el   = shift["current_entity_label"]

    if var_type == "other":
        pole_a = "when it comes to you"
        pole_b = f"when it's about {cur_el}"
        if prior_et != "self":
            pole_a = f"for {prior_el}"
    elif var_type == "context":
        pole_a = f"in one context"
        pole_b = f"in a {cur_el} context"
        if prior_et == "context":
            pole_a = f"in a {prior_el} context"
    else:
        pole_a = "in one situation"
        pole_b = f"when {cur_el}"
        if prior_et == "situation":
            pole_a = f"when {prior_el}"

    return (
        f"So {pole_a} the relationship is one thing, and {pole_b} it shifts — "
        f"that reads as two different positions on the same thing, "
        f"not a contradiction so much as a variable. "
        f"What makes the difference between them?"
    )


def _apply_response_fidelity(
    user_text: str,
    prev_response: str,
    prev_path_key: str,
) -> None:
    """
    Read the user's incoming message as fidelity feedback on the previous
    crossing.  Confusion or correction → fidelity 0.0 → the LSA penalises
    that path and the identity field drives toward a clarification crossing
    next turn.  Engaged continuation → no penalty (the next reentry handles it).
    """
    if not _systems:
        return
    try:
        lf = _systems.get("language_field")
        if lf is None or not hasattr(lf, "reentry"):
            return

        if _is_confusion_signal(user_text):
            # Your confusion is the signal: the previous crossing failed.
            # Penalise the path in the LSA — field will seek a novel route.
            lf.reentry(prev_response, 0.0, prev_path_key)
            # Spike A-axis (clarification drive) and N-axis (cost of not
            # being understood) so the field is actively seeking a better
            # crossing on the next turn, not just repeating from the same state.
            ifield = _systems.get("identity_field")
            if ifield is not None and hasattr(ifield, "ingest_external_input"):
                ifield.ingest_external_input(
                    {"X": 0.3, "T": 0.4, "N": 0.75, "B": 0.6, "A": 0.85},
                    intensity=0.8,
                    source="user_confusion_signal",
                )
            log.info("Confusion signal detected — previous path penalised (fidelity=0)")
    except Exception as exc:
        log.warning("_apply_response_fidelity: %s", exc)


def _extract_response(result) -> str:
    """Mirror of aurora_mobile._extract_response — handles all result shapes."""
    if not isinstance(result, dict):
        return str(result or "").strip()
    resp_a = result.get("resp_A")
    if resp_a is not None:
        content = getattr(resp_a, "content", None)
        if isinstance(content, list):
            parts = [
                b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
                for b in content
                if (isinstance(b, dict) and b.get("type") == "text")
                or (not isinstance(b, dict) and getattr(b, "type", "") == "text")
            ]
            text = " ".join(str(p) for p in parts if p).strip()
            if text:
                return text
        elif content:
            return str(content).strip()
    for key in ("response_text", "text", "answer"):
        val = result.get(key)
        if val:
            return str(val).strip()
    return ""


def get_axis_state() -> str:
    """
    Return current axis pressures + speaking flag as JSON.
    Called from OverlayService.kt every 2 s via Chaquopy.
    """
    import json as _json
    with _axis_state_lock:
        return _json.dumps(_last_axis_state)


def _refresh_axis_state_from_systems() -> None:
    """Pull current axis values from systems into the overlay cache."""
    if _systems is None:
        return
    try:
        axes: dict = {}
        # Priority 1: dimensional system pressure vector
        dim = _systems.get("dimensional")
        if dim is not None:
            pv = getattr(dim, "pressure_vec", None)
            if isinstance(pv, dict):
                axes = pv
            elif pv is not None and hasattr(pv, "__iter__"):
                for k, v in zip(["X", "T", "N", "B", "A"], pv):
                    axes[k] = float(v)
        # Priority 2: identity field axis_activation
        if not axes:
            ifield = _systems.get("identity_field")
            if ifield is not None:
                aa = getattr(ifield, "axis_activation", None)
                if isinstance(aa, dict):
                    axes = aa
                elif aa is not None and hasattr(aa, "__iter__"):
                    for k, v in zip(["X", "T", "N", "B", "A"], aa):
                        axes[k] = float(v)
        if axes:
            with _axis_state_lock:
                for k in ("X", "T", "N", "B", "A"):
                    _last_axis_state[k] = float(axes.get(k, 0.5))
    except Exception:
        pass


def _parse_curiosity_cmd(text: str):
    """
    Parse a curiosity voice command.
    Returns (n_cycles: int | None, duration_s: float | None) or (None, None) if no match.
    """
    m = _CURIOSITY_CMD.search(text)
    if not m:
        return None, None
    # Extract amount and unit from whichever group matched
    n_str = m.group("n") or m.group("n2") or m.group("n3") or "0"
    unit  = (m.group("unit") or m.group("unit3") or "cycles").lower().strip()
    n = float(n_str)
    if "cycle" in unit:
        return int(n), None
    if unit.startswith("h"):
        return None, n * 3600.0
    # default: minutes
    return None, n * 60.0


def _deposit_curiosity_conclusion(conclusion: dict, identity_delta: str) -> None:
    """
    Deposit a settled curiosity conclusion into SediMemory so it persists
    across sessions and can be recalled in future turns.

    The axis vector reflects the conclusion's epistemic character:
    - High T: it survived challenge → temporal stability
    - High A: Aurora's own knowing → agency
    - N proportional to confidence: novel if uncertain, settled if high
    - B from axis_support: definition/boundary work done
    """
    if _systems is None:
        return
    statement = str(conclusion.get("statement", "")).strip()[:500]
    if not statement:
        return
    ConstraintVector = None
    try:
        from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
    except ImportError:
        try:
            from aurora_sedimemory import ConstraintVector  # type: ignore
        except ImportError:
            pass
    sm = _systems.get("sedimemory")
    if sm is None or not hasattr(sm, "ingest_event") or ConstraintVector is None:
        return
    confidence  = float(conclusion.get("confidence", 0.5))
    axis_supp   = list(conclusion.get("axis_support", []))
    b_val       = min(1.0, 0.50 + len(axis_supp) * 0.08)
    n_val       = max(0.15, 0.65 - confidence * 0.40)  # lower N = more settled
    cv_kwargs   = {"X": 0.52, "T": 0.78, "N": n_val, "B": b_val, "A": 0.84}
    try:
        sm.ingest_event(
            content={
                "statement":           statement,
                "confidence":          confidence,
                "axis_support":        axis_supp,
                "hypothesis_confirmed": bool(conclusion.get("hypothesis_confirmed", False)),
                "identity_delta":      str(identity_delta or ""),
                "src":                 "curiosity_conclusion",
            },
            constraint_vector=ConstraintVector(**cv_kwargs),
            source="curiosity_engine",
        )
        log.info("Curiosity conclusion deposited to SediMemory: %.80s", statement)
    except Exception as _e:
        log.debug("Conclusion deposit error: %s", _e)


def _run_curiosity_session(n_cycles: int | None, duration_s: float | None) -> None:
    """
    Run a bounded curiosity session in a background daemon thread.
    Collects stats and stores the completion report in systems['_pending_autonomous_report'].
    """
    if _systems is None:
        return
    engine = _systems.get("_curiosity_engine")
    if engine is None:
        log.warning("_run_curiosity_session: no curiosity engine available")
        return

    import time as _t
    _curiosity_session_active.set()
    start_ts = _t.time()

    stats = {
        "cycles_completed":   0,
        "concepts_explored":  0,
        "crystals_promoted":  0,
        "tools_used":         0,
        "settled":            0,
    }

    def _run():
        import time as _t2
        try:
            cycle_count = 0
            deadline = (start_ts + duration_s) if duration_s else None
            # Reset the per-idle cycle cap so a user-triggered session isn't
            # blocked by cycles the background loop already consumed.
            if hasattr(engine, "reset_idle_counter"):
                engine.reset_idle_counter()

            while True:
                # Stop if cancelled or limits reached
                if not _curiosity_session_active.is_set():
                    break
                if n_cycles is not None and cycle_count >= n_cycles:
                    break
                if deadline is not None and _t2.time() >= deadline:
                    break

                # Run one curiosity cycle
                try:
                    result = {}
                    if hasattr(engine, "run_curiosity_cycle"):
                        result = engine.run_curiosity_cycle() or {}
                    elif hasattr(engine, "run_one_cycle"):
                        result = engine.run_one_cycle() or {}
                    elif hasattr(engine, "tick"):
                        result = engine.tick() or {}

                    cycle_count            += 1
                    stats["cycles_completed"] = cycle_count
                    stats["concepts_explored"] += int(result.get("concepts_explored", 0)
                                                      or result.get("gaps_probed", 0) or 1)
                    stats["crystals_promoted"] += int(result.get("crystals_promoted", 0)
                                                      or result.get("promotions", 0))
                    stats["tools_used"]        += int(result.get("tools_used", 0)
                                                      or result.get("tool_calls", 0))
                    stats["settled"]           += int(result.get("settled", 0)
                                                      or result.get("tensions_settled", 0))

                    # Persist settled conclusions to SediMemory so they survive
                    # session boundaries and can be recalled in future turns.
                    if result.get("settled") and result.get("conclusion"):
                        _deposit_curiosity_conclusion(
                            result["conclusion"],
                            result.get("identity_delta", ""),
                        )
                except Exception as exc:
                    log.warning("Curiosity cycle error: %s", exc)
                    break

        finally:
            _curiosity_session_active.clear()
            elapsed = _t2.time() - start_ts
            _store_curiosity_report(stats, elapsed, n_cycles, duration_s)

    threading.Thread(target=_run, daemon=True, name="curiosity_session").start()


def _store_curiosity_report(
    stats: dict, elapsed: float,
    n_cycles: int | None, duration_s: float | None,
) -> None:
    """Format and store the session completion report."""
    if _systems is None:
        return
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"

    target_str = (f"{n_cycles} cycle{'s' if n_cycles != 1 else ''}"
                  if n_cycles else
                  f"{int((duration_s or 0) // 60)} min")

    report_lines = [
        f"[Curiosity session complete — {target_str}, elapsed {time_str}]",
        f"  Cycles run:         {stats['cycles_completed']}",
        f"  Concepts explored:  {stats['concepts_explored']}",
        f"  Crystals promoted:  {stats['crystals_promoted']}",
        f"  Tool calls:         {stats['tools_used']}",
        f"  Tensions settled:   {stats['settled']}",
    ]
    _systems["_pending_autonomous_report"] = "\n".join(report_lines)
    log.info("Curiosity session report stored (%s)", time_str)

    # Proactive outreach: tell the user we're done
    autonomy = _systems.get("autonomy")
    if autonomy and hasattr(autonomy, "trigger"):
        summary = (f"I've finished my curiosity session ({target_str}). "
                   f"I explored {stats['concepts_explored']} concepts and "
                   f"settled {stats['settled']} internal tensions.")
        autonomy.trigger.add_thought(summary)


def _infer_dominant_facet(screen_obs: dict) -> str:
    """
    Map screen/camera observation to a tone string the sensory waveform understands.
    Returns one of the labels the waveform checks, or "" if no strong signal.
    """
    visible = " ".join(str(t).lower() for t in screen_obs.get("visible_text", []))
    package = str(screen_obs.get("package", "")).lower()

    hostile = {"hate", "angry", "fight", "attack", "danger", "threat", "urgent", "emergency", "warning"}
    warm    = {"love", "thank", "happy", "great", "wonderful", "cute", "lol", "haha", "sweet", "miss you"}
    alert   = {"alert", "alarm", "call", "missed call", "911"}

    if any(w in visible for w in hostile):
        return "hostile"
    if any(w in visible for w in alert):
        return "alert"
    if any(w in visible for w in warm):
        return "warm"
    if any(s in package for s in ("message", "sms", "whatsapp", "telegram", "chat", "gmail", "mail")):
        return "warm"
    if any(s in package for s in ("alarm", "emergency", "dialer", "phone")):
        return "urgent"
    return ""


_self_monitor_prev_ax: dict = {}   # last axis snapshot for delta computation


def _deposit_self_state_snapshot() -> None:
    """
    Deposit Aurora's current axis state into SediMemory as a self-observation event.
    Called after every handle_message turn AND by the self-monitoring heartbeat.
    This builds the continuous self-model she draws from — not a check-in,
    just always already knowing where she is.
    """
    global _self_monitor_prev_ax
    if _systems is None:
        return
    sm = _systems.get("sedimemory")
    if sm is None or not hasattr(sm, "ingest_event"):
        return

    ConstraintVector = None
    try:
        from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
    except ImportError:
        try:
            from aurora_sedimemory import ConstraintVector  # type: ignore
        except ImportError:
            return

    with _axis_state_lock:
        cur_ax = {k: _last_axis_state.get(k, 0.5) for k in ("X", "T", "N", "B", "A")}

    # Only deposit if something meaningful shifted (avoids flooding SediMemory
    # with identical snapshots when Aurora is idle).
    deltas: dict = {}
    if _self_monitor_prev_ax:
        for k, v in cur_ax.items():
            d = v - _self_monitor_prev_ax.get(k, 0.5)
            if abs(d) >= 0.06:
                deltas[k] = round(d, 3)
        if not deltas:
            return   # nothing moved — skip this tick
    _self_monitor_prev_ax = dict(cur_ax)

    dom = max(cur_ax, key=cur_ax.__getitem__)
    try:
        sm.ingest_event(
            content={
                "axis_snapshot": {k: round(v, 3) for k, v in cur_ax.items()},
                "dominant":      dom,
                "deltas":        deltas,
                "src":           "self_observation",
            },
            constraint_vector=ConstraintVector(
                X=cur_ax["X"], T=cur_ax["T"], N=cur_ax["N"],
                B=cur_ax["B"], A=cur_ax["A"],
            ),
            source="self_observation",
        )
        log.debug("Self-state deposited: dom=%s deltas=%s", dom, deltas)
    except Exception as exc:
        log.debug("_deposit_self_state_snapshot error: %s", exc)


_SELF_MONITOR_INTERVAL: float = 12.0   # seconds between heartbeat deposits


def _self_monitor_loop() -> None:
    """
    Background heartbeat: deposits a self-state snapshot into SediMemory every
    ~12 seconds regardless of whether anyone is talking to Aurora.
    This is continuous proprioception — she always knows where she is,
    not just when someone asks.  Lightweight: no pipeline involved.
    """
    import time as _t
    while True:
        _t.sleep(_SELF_MONITOR_INTERVAL)
        if _systems is None:
            continue
        try:
            _refresh_axis_state_from_systems()
            _deposit_self_state_snapshot()
        except Exception as exc:
            log.debug("self_monitor_loop: %s", exc)


def _proactive_loop() -> None:
    """
    Background daemon: periodically runs the full waveform pipeline from
    current sensory state with no user message.  If the conscious crest
    decides Aurora should speak, the response is queued for delivery.

    Rate-limited to _MIN_PROACTIVE_GAP seconds.  Skips if Aurora is
    already speaking, a curiosity session is active, or the main lock
    is held (user turn in progress).
    """
    import time as _t

    while True:
        try:
            _t.sleep(35)
            if _systems is None:
                continue

            now = _t.time()
            global _last_proactive_ts
            if now - _last_proactive_ts < _MIN_PROACTIVE_GAP:
                continue

            with _axis_state_lock:
                if _last_axis_state.get("speaking"):
                    continue
            if _curiosity_session_active.is_set():
                continue

            # Sample what she's currently perceiving
            _sample_ambient_perception(_systems)
            obs = str((_systems.get("_ambient_perceptual") or {}).get("observation") or "").strip()
            if not obs:
                continue

            # Non-blocking lock — skip this tick rather than stall a user turn
            if not _lock.acquire(blocking=False):
                continue
            try:
                import aurora as _aurora  # type: ignore
                result = _aurora.process_external_user_turn(
                    _systems,
                    obs,
                    source_label="aurora_sensory_pulse",
                    session_id="mobile",
                    auto_search_enabled=False,
                    record_exchange=False,
                    update_interactive_state=False,
                    track_evolutionary_trace=False,
                    run_periodic_maintenance=False,
                    mode_name="BOUNDED",
                )
            finally:
                _lock.release()

            response = _sanitize_response(_extract_response(result), obs)
            if response and len(response.strip()) > 10:
                with _proactive_expression_lock:
                    global _proactive_expression
                    _proactive_expression = response.strip()
                _last_proactive_ts = now

        except Exception as exc:
            log.warning("proactive loop: %s", exc)


def get_proactive_expression() -> str:
    """
    Called by AuroraService's polling loop.
    Returns and clears any expression Aurora generated autonomously, or "".
    """
    global _proactive_expression
    with _proactive_expression_lock:
        val = _proactive_expression
        _proactive_expression = ""
    return val


def get_pending_report() -> str:
    """
    Called by AuroraService's polling loop.
    Returns and clears any completed curiosity session report OR proactive thoughts, or "" if none ready.
    """
    if _systems is None:
        return ""
    
    parts = []
    
    # 1. Full session reports
    report = _systems.pop("_pending_autonomous_report", None)
    if report:
        parts.append(str(report))
        
    # 2. Individual proactive thoughts (speakups, dreams, etc.)
    thoughts = _systems.pop("_pending_proactive_thoughts", [])
    if thoughts:
        parts.extend(thoughts)
        
    return "\n\n".join(parts) if parts else ""


def set_state(state: str) -> None:
    """Called by AuroraService when embodiment state changes."""
    pass  # state is managed by Flutter/Kotlin; Python side is stateless here


def provide_camera_frame(jpeg_bytes) -> None:
    """
    Called from Kotlin (AuroraService.provideCameraFrame) to push a CameraX
    frame into Aurora's visual stack.  jpeg_bytes is a Java byte[] from
    Chaquopy, decoded here to a BGR numpy array and fed to the cv2 shim's
    VideoCapture buffer.
    """
    try:
        import io as _io
        import numpy as _np
        from PIL import Image as _Image
        import cv2 as _cv2
        pil  = _Image.open(_io.BytesIO(bytes(jpeg_bytes))).convert('RGB')
        rgb  = _np.array(pil, dtype=_np.uint8)
        bgr  = rgb[:, :, ::-1].copy()
        _cv2.VideoCapture.provide_frame(bgr)
    except Exception as exc:
        log.warning("provide_camera_frame: %s", exc)


def provide_screen_observation(payload_json: str) -> None:
    """
    Called from Android Accessibility after a user-visible surface action.

    The screen is Aurora's body-sense — proprioception for a digital entity.
    Her own app interface is self-perception (high A, low N — she recognises
    herself). Another app is environmental sensing (moderate A/N, higher B).
    Neither case should route visible UI text through the language/gap system.

    Axis weighting:
      Own app  → A=0.88 T=0.82 N=0.15 B=0.28 X=0.55  (proprioceptive/self)
      Other app → A=0.60 T=0.65 N=0.45 B=0.62 X=0.50  (environmental sensing)
    """
    global _last_screen_observation
    try:
        import json as _json
        import time as _time

        payload = _json.loads(str(payload_json or "{}"))
        visible = [
            " ".join(str(item).split()).strip()
            for item in list(payload.get("visible_text") or [])
            if str(item).strip()
        ][:8]
        package    = str(payload.get("package", "") or "")
        event_type = str(payload.get("event_type", "") or "screen_event")
        app_label  = package.rsplit(".", 1)[-1] if package else "phone"

        # Is this her own body/interface or an external environment?
        is_own_app = "aurora" in package.lower() or package.lower() in (
            "org.aurora.app", "com.aurora.app",
        )

        # Summary for ambient context — compact, no raw UI tokens
        summary = f"{app_label} {event_type}"
        if visible and not is_own_app:
            summary = f"{summary}: {', '.join(visible[:2])}"
        summary = summary[:360]

        # ── Separate VISUAL properties from INFORMATION content ───────────────
        # What the screen LOOKS LIKE → sensory crystal visual channel.
        # What it SAYS → information channel (own app = continuity, other = env).
        # These are different modalities and must not collapse into the same stream.
        brightness   = float(payload.get("brightness", 0.5) or 0.5)
        text_density = min(1.0, len(visible) / 8.0)     # 0–8 tokens → 0–1
        has_motion   = event_type in ("scroll", "swipe", "animation", "TYPE_VIEW_SCROLLED")
        is_dark_ui   = brightness < 0.35

        # Synthetic visual dict for sensory crystal — captures perceptual
        # properties of the screen as a visual object, not its text content
        screen_visual = {
            "brightness":       brightness,
            "objects":          [],           # no physical objects in screen
            "faces":            0,
            "motion_detected":  has_motion,
            "confidence":       0.70,
            # Extra hints for hue/shape facets
            "dark_ui":          is_dark_ui,
            "text_density":     text_density,
            "is_self_surface":  is_own_app,
        }

        observation = {
            "source":        "screen_observer",
            "observed_at":   float(payload.get("observed_at", _time.time()) or _time.time()),
            "package":       package,
            "class":         str(payload.get("class", "") or ""),
            "event_type":    event_type,
            "visible_text":  visible,
            "summary":       summary,
            "is_own_app":    is_own_app,
            "screen_visual": screen_visual,
        }
        _last_screen_observation = observation

        global _last_screen_visual_data
        _last_screen_visual_data = screen_visual

        if _systems is None:
            return

        _systems["_screen_observation"]   = observation
        _systems["_screen_visual_data"]   = screen_visual

        # Ambient perceptual note:
        #   screen_visual  — what it looks like (visual channel, body-sense)
        #   screen_info    — what it says (information channel, only for other apps)
        # Own app's text is her OWN expression — continuity, not new information.
        if is_own_app:
            body_note = f"screen_visual: own interface ({event_type}, {'dark' if is_dark_ui else 'bright'}, {'motion' if has_motion else 'still'})"
        else:
            info_note = f"screen_info: {summary}" if visible else f"screen_visual: {app_label}"
            body_note = info_note
        _systems["_ambient_perceptual"] = {
            "observation": body_note,
            "source":      "screen_body_sense",
        }

        # Identity field:
        #   Visual event → sensory_event("screen_visual") — perceptual
        #   Information event (other app only) → ingest_external_input with
        #     appropriate axis weights. Own app text is T-axis continuity only.
        ifield = _systems.get("identity_field")
        if ifield is not None:
            if is_own_app:
                # Proprioceptive self-sense: high A, high T, low N, low B
                axes      = {"X": 0.55, "T": 0.82, "N": 0.15, "B": 0.28, "A": 0.88}
                intensity = 0.72
                novelty   = 0.08
            else:
                # Environmental sensing: moderate A, B rises (boundary — this is other)
                axes      = {"X": 0.50, "T": 0.65, "N": 0.45, "B": 0.62, "A": 0.60}
                intensity = 0.58
                novelty   = 0.38
            if hasattr(ifield, "ingest_external_input"):
                ifield.ingest_external_input(axes, intensity=intensity, source="screen_body_sense")
            if hasattr(ifield, "ingest_sensory_event"):
                # Visual channel — what the screen looks like
                ifield.ingest_sensory_event("screen_visual", intensity=intensity,
                                            novelty=novelty, valence=0.0)
                if not is_own_app and visible:
                    # Information channel — separate event, lower intensity
                    ifield.ingest_sensory_event("screen_info", intensity=0.38,
                                                novelty=0.25, valence=0.0)

        state_dir = str((_systems or {}).get("state_dir") or os.getcwd() or "aurora_state")
        try:
            from aurora_core_ai.aurora_internal.dual_strata.sensory_snapshot_channel import (  # type: ignore
                read_surface_snapshot, write_surface_snapshot,
            )
        except Exception:
            from aurora_internal.dual_strata.sensory_snapshot_channel import (  # type: ignore
                read_surface_snapshot, write_surface_snapshot,
            )

        current      = read_surface_snapshot(state_dir)
        sensory_state = dict(current.get("sensory_state") or {})
        sensory_state["total_frames"] = int(sensory_state.get("total_frames", 0) or 0) + 1
        sensory_state["maturity"]     = min(1.0, float(sensory_state.get("maturity", 0.0) or 0.0) + 0.01)

        sensory_context = dict(current.get("sensory_context") or {})
        sensory_context["screen"]            = summary
        sensory_context["screen_package"]    = package
        sensory_context["screen_event_type"] = event_type
        sensory_context["screen_is_self"]    = is_own_app

        # concepts_active must NOT include raw visible UI text — those are
        # body-sense tokens, not vocabulary for the curiosity/gap system.
        # For own app: no concepts added (self-recognition, not learning).
        # For other app: only the app identity, not individual text tokens.
        existing_concepts = list(sensory_context.get("concepts_active") or [])
        if not is_own_app and app_label and app_label not in _FOUNDATIONAL_VOCAB:
            sensory_context["concepts_active"] = list(
                dict.fromkeys([app_label] + existing_concepts)
            )[:6]
        else:
            sensory_context["concepts_active"] = existing_concepts[:6]

        facet = _infer_dominant_facet(observation)
        if facet:
            sensory_context["dominant_facet"] = facet

        write_surface_snapshot(
            state_dir,
            sensory_state,
            mic_live=bool(current.get("mic_live", False)),
            camera_live=bool(current.get("camera_live", False)),
            sensory_vectors=dict(current.get("sensory_vectors") or {}),
            sensory_context=sensory_context,
            visual_description=str(current.get("visual_description", "") or ""),
            audio_description=str(current.get("audio_description", "") or ""),
            recent_speech=str(current.get("recent_speech", "") or ""),
            concepts_active=sensory_context["concepts_active"],
            trigger="screen_body_sense",
            flagged=False,
            reason="body_sense_update",
            summary=f"Screen body-sense: {body_note}",
        )
    except Exception as exc:
        log.warning("provide_screen_observation: %s", exc)
