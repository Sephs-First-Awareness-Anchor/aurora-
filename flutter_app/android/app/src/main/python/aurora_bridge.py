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

# Axis state cache — updated after each turn; read by OverlayService every 2 s.
_last_axis_state: dict = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5, "speaking": False}
_axis_state_lock = threading.Lock()
_last_screen_observation: dict = {}

# Curiosity session control
_curiosity_session_active = threading.Event()


# ---------------------------------------------------------------------------
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
    global _systems
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

        # Start the autonomous curiosity engine as a background daemon thread.
        # It runs 3-cycle idle batches (45 s between batches on mobile to be
        # battery-friendly) and pauses automatically the moment a user turn
        # arrives (interrupt_curiosity_cycles is called in dual_question_pipeline).
        _start_curiosity_engine(_systems)

        log.info("Aurora boot complete")
        return "ready"
    except Exception as exc:
        tb = traceback.format_exc()
        log.error("boot_aurora failed: %s\n%s", exc, tb)
        last_line = [l.strip() for l in tb.splitlines() if l.strip()][-1]
        return f"error: {last_line}"


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


def _sanitize_response(response: str, user_text: str) -> str:
    """
    Strip pipeline leaks from Aurora's generated response.

    1. De-duplicate repeated phrase prefixes ("I understand I understand" → "I understand").
    2. If the user asked "can you hear me" and the response claims audio is offline,
       replace with the correct answer — the user's voice WAS heard via STT.
    3. Remove bare "audio/camera feed offline" sentences that leaked from the
       sensory-grounding handler when the ambient background monitor isn't running.
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

    return response


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

    # ── Camera ────────────────────────────────────────────────────────────────
    hw = systems.get("hardware")
    if hw and hasattr(hw, "capture_visual"):
        try:
            cam = hw.capture_visual()
            if cam and isinstance(cam, dict):
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
            _act  = str(_d.get("activity", "ambient"))
            _rms  = float(_d.get("rms_db", -60.0))
            audio_obs     = f"{_act}, {_rms:.0f} dB"
            audio_novelty = 0.50 if _act in ("speech", "music") else 0.10
    except Exception:
        pass

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


def handle_message(text: str) -> str:
    """Process one user turn. Returns Aurora's text response."""
    global _systems, _last_response, _last_path_key
    global _pending_example_concept, _pending_example_asked
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
        # ── Step 1: Read your response as fidelity / teaching data ───────────
        if _last_response and _systems:
            # If Aurora asked a genuine question last turn and there's a gap
            # concept pending, your reply is either an answer or a can't-answer.
            if _pending_example_concept:
                if _CANT_ANSWER_PATTERNS.search(text):
                    # You don't know — fall back to Aurora's search tools.
                    _search_for_gap(_pending_example_concept)
                else:
                    # You answered — ingest what you said as learning data.
                    _ingest_example(text, _pending_example_concept)
                _pending_example_concept = ""
                _pending_example_asked   = ""
            # Your confusion or correction = fidelity 0 on the previous path.
            _apply_response_fidelity(text, _last_response, _last_path_key)

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
            except Exception:
                pass

        # ── Step 4: Track natural questions Aurora generated ─────────────────
        # If the curiosity engine raised gap pressure for a concept and Aurora's
        # response came out as a question, arm the concept so your next reply
        # is treated as learning data (or triggers a search if you can't answer).
        # No scripted strings — we only check whether she naturally asked something.
        if _systems:
            gap_concept = _systems.get("_gap_seeking_concept") or ""
            if gap_concept and not _pending_example_concept:
                if response and response.rstrip().endswith("?"):
                    # She asked something — your next turn is the answer
                    _pending_example_concept = gap_concept
                    _pending_example_asked   = response
                    _systems["_gap_seeking_concept"] = None
                    log.info("Gap question detected for concept: %r", gap_concept)

        _last_response = response
        _last_path_key = path_key

        # Refresh overlay axis cache after every turn
        _refresh_axis_state_from_systems()
        with _axis_state_lock:
            _last_axis_state["speaking"] = bool(response)

        # Prepend any completed curiosity session report
        pending_report = (_systems or {}).pop("_pending_autonomous_report", None)
        if pending_report:
            response = f"{pending_report}\n\n{response}" if response else pending_report

        print(f"AURORA_BRIDGE: Response: {response}")
        return response
    except Exception as exc:
        log.error("handle_message: %s\n%s", exc, traceback.format_exc())
        return "I encountered an error processing your request."


def _search_for_gap(concept: str) -> None:
    """
    Trigger Aurora's search tools for a concept the user couldn't explain.
    Runs in a background thread so it doesn't block the current response.
    """
    if not _systems or not concept:
        return
    def _run():
        try:
            from aurora_core_ai.aurora_internal.tool_registry import call as _tool_call  # type: ignore
            # World knowledge search first — fastest
            r1 = _tool_call("world_knowledge_search", query=concept, systems=_systems)
            log.info("Gap search (world_knowledge) for %r: success=%s", concept, r1.success)
            # If that resolved something, ingest the result as learning data
            if r1.success and r1.data:
                _ingest_example(r1.data, concept)
            else:
                # Fall back to corpus hunter — finds raw datasets on the topic
                _tool_call("corpus_hunter", topic=concept, systems=_systems)
                log.info("Gap search (corpus_hunter) triggered for %r", concept)
        except Exception as exc:
            log.warning("_search_for_gap failed for %r: %s", concept, exc)
    import threading as _threading
    _threading.Thread(target=_run, daemon=True, name=f"gap_search:{concept[:20]}").start()


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
                    if hasattr(engine, "run_one_cycle"):
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
    The observation is compacted into the sensory snapshot and identity field
    so the next response traversal can use it as present surface context.
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
        package = str(payload.get("package", "") or "")
        event_type = str(payload.get("event_type", "") or "screen_event")
        app_label = package.rsplit(".", 1)[-1] if package else "phone"
        visible_summary = ", ".join(visible[:3])
        summary = f"{app_label} {event_type}"
        if visible_summary:
            summary = f"{summary}: {visible_summary}"

        observation = {
            "source": "screen_observer",
            "observed_at": float(payload.get("observed_at", _time.time()) or _time.time()),
            "package": package,
            "class": str(payload.get("class", "") or ""),
            "event_type": event_type,
            "visible_text": visible,
            "summary": summary[:360],
        }
        _last_screen_observation = observation

        if _systems is None:
            return

        _systems["_screen_observation"] = observation
        _systems["_ambient_perceptual"] = {
            "observation": f"screen: {observation['summary']}",
            "source": "screen_observer",
        }

        ifield = _systems.get("identity_field")
        if ifield is not None:
            if hasattr(ifield, "ingest_external_input"):
                ifield.ingest_external_input(
                    {"X": 0.52, "T": 0.66, "N": 0.50, "B": 0.58, "A": 0.44},
                    intensity=0.58,
                    source="screen_observer",
                )
            if hasattr(ifield, "ingest_sensory_event"):
                ifield.ingest_sensory_event(
                    "screen", intensity=0.58, novelty=0.42, valence=0.0
                )

        state_dir = str((_systems or {}).get("state_dir") or os.getcwd() or "aurora_state")
        try:
            from aurora_core_ai.aurora_internal.dual_strata.sensory_snapshot_channel import (  # type: ignore
                read_surface_snapshot,
                write_surface_snapshot,
            )
        except Exception:
            from aurora_internal.dual_strata.sensory_snapshot_channel import (  # type: ignore
                read_surface_snapshot,
                write_surface_snapshot,
            )

        current = read_surface_snapshot(state_dir)
        sensory_state = dict(current.get("sensory_state") or {})
        recognitions = dict(sensory_state.get("recognitions") or {})
        recent = list(recognitions.get("recent") or [])
        recent = (["screen", app_label, event_type] + visible[:4] + recent)[:12]
        recognitions["recent"] = list(dict.fromkeys(str(x) for x in recent if str(x).strip()))
        sensory_state["recognitions"] = recognitions
        sensory_state["total_frames"] = int(sensory_state.get("total_frames", 0) or 0) + 1
        sensory_state["maturity"] = min(1.0, float(sensory_state.get("maturity", 0.0) or 0.0) + 0.01)

        sensory_context = dict(current.get("sensory_context") or {})
        sensory_context["screen"] = observation["summary"]
        sensory_context["screen_package"] = package
        sensory_context["screen_event_type"] = event_type
        sensory_context["concepts_active"] = list(dict.fromkeys(
            [app_label, event_type] + visible[:6] + list(sensory_context.get("concepts_active") or [])
        ))[:10]

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
            trigger="screen_observer",
            flagged=False,
            reason="surface_action_observed",
            summary=f"Phone surface action observed. {observation['summary']}",
        )
    except Exception as exc:
        log.warning("provide_screen_observation: %s", exc)
