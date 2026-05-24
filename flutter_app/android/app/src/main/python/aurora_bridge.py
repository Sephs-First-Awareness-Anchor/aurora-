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


# Phrases that signal the previous output was incoherent or a repeat.
# Your words ARE the fidelity measurement — no code pre-screening needed.
_CONFUSION_PATTERNS = re.compile(
    r"""
    ^(what\??|huh\??|pardon\??|sorry\??)$                  # bare confusion
    | \b(what\s+did\s+you\s+(just\s+)?say)                 # explicit re-ask
    | \b(that\s+(doesn.t|didn.t|doesn't|didn't|makes?\s+no|made\s+no)\s+make\s+sense)
    | \b(you.re\s+repeating|you\s+(already|just)\s+said)
    | \b(what\s+are\s+you\s+talking\s+about)
    | \b(i\s+(don.t|didn.t|don't|didn't)\s+understand)
    | \b(say\s+that\s+(again|differently|another\s+way))
    | \b(that\s+was(n.t|n't)\s+(clear|coherent|right))
    | ^no[,\s]+(i\s+said|i\s+was|i\s+asked|that.s\s+not)  # correction
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


def handle_message(text: str) -> str:
    """Process one user turn. Returns Aurora's text response."""
    global _systems, _last_response, _last_path_key
    print(f"AURORA_BRIDGE: Received message: {text}")
    if _systems is None:
        print("AURORA_BRIDGE: Systems not initialized")
        return "Aurora is still initializing — please wait a moment."
    _setup_paths()
    try:
        # ── Step 1: Read your response as fidelity on the previous crossing ──
        # Your confusion, correction, or re-ask IS the measurement.
        # No code pre-screening — your words tell the field whether the last
        # crossing succeeded or failed.
        if _last_response and _systems:
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
        response = _extract_response(result)

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

        _last_response = response
        _last_path_key = path_key
        print(f"AURORA_BRIDGE: Response: {response}")
        return response
    except Exception as exc:
        log.error("handle_message: %s\n%s", exc, traceback.format_exc())
        return "I encountered an error processing your request."


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
