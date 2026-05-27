"""
aurora_internal/dual_strata/predictive_stager.py

Authors: Sunni (Sir) Morningstar & Cael Devo

Lightweight PredictiveStager: Subsurface pushes hypothesis frames here after
each tick; Surface pops them ahead of live interactions so it never needs to
block-wait for Subsurface to finish a full cycle.

The Subsurface is computationally DENSE — for each Surface tick it runs
multiple internal perspective passes, one per active pressure lens from the
31-pressure constraint language framework [X·T·N·B·A].  The Subsurface's own
identity/weights/habits are slow to change; its OUTPUT per tick is high.

Design constraints:
- File-backed queue at aurora_state/predictive_frame_queue.json
- Max 8 staged frames (oldest discarded on overflow)
- All I/O is best-effort — any failure is silently swallowed so neither daemon crashes
- No dependencies on heavy Aurora systems; imports are local to each method
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_BASE_DIR = Path(__file__).parent.parent.parent  # aurora_strata/
_STATE_DIR = _BASE_DIR / "aurora_state"
_QUEUE_PATH = _STATE_DIR / "predictive_frame_queue.json"
_MAX_FRAMES = 8

# ---------------------------------------------------------------------------
# 31-pressure constraint language perspectives — all non-empty subsets of
# {X, T, N, B, A} enumerated in tier order (singles → pairs → triples →
# quads → full).  Each tuple is the set of axes that are "in focus" for that
# hypothesis pass; all other axes are attenuated to 20 % (not zeroed) so
# continuity of signal is preserved.
# ---------------------------------------------------------------------------
PRESSURE_PERSPECTIVES: List[Tuple[str, ...]] = [
    # Tier I — singles (5): directional forces, one-axis demand
    ("X",), ("T",), ("N",), ("B",), ("A",),
    # Tier II — pairs (10): tensions, two constraints pulling simultaneously
    ("X", "T"), ("X", "N"), ("X", "B"), ("X", "A"),
    ("T", "N"), ("T", "B"), ("T", "A"), ("N", "B"), ("N", "A"), ("B", "A"),
    # Tier III — triples (10): dynamics, emergent behaviors
    ("X", "T", "N"), ("X", "T", "B"), ("X", "T", "A"),
    ("X", "N", "B"), ("X", "N", "A"), ("X", "B", "A"),
    ("T", "N", "B"), ("T", "N", "A"), ("T", "B", "A"), ("N", "B", "A"),
    # Tier IV — quads (5): architecture, stable generative systems
    ("X", "T", "N", "B"), ("X", "T", "N", "A"),
    ("X", "T", "B", "A"), ("X", "N", "B", "A"), ("T", "N", "B", "A"),
    # Tier V — full (1): complete agency field / recursion threshold
    ("X", "T", "N", "B", "A"),
]

# Density ratios from aurora_noncomp_registry.LAYER_DENSITY_RATIO
_DENSITY_RATIO: Dict[str, float] = {
    "X": 1.0,
    "T": 7.0,
    "N": 10.0,
    "B": 40.0,
    "A": 150.0,
}

_AXIS_DOMAIN = {
    "existence": "X", "temporal": "T", "energy": "N",
    "boundary": "B", "agency": "A",
    "X": "X", "T": "T", "N": "N", "B": "B", "A": "A",
    "x": "X", "t": "T", "n": "N", "b": "B", "a": "A",
}

_COMMON_PREDICATE_WORDS = (
    "clarify", "hold", "steady", "attend", "observe", "research",
    "repair", "sense", "understand", "integrate", "prepare",
)


# ---------------------------------------------------------------------------
# Density → pass count
# ---------------------------------------------------------------------------

def n_passes_for_density(dominant_axis: str) -> int:
    """Number of perspective passes for one Subsurface tick given the dominant axis.

    Formula: round(1 + log10(ratio) * 2)
    Results: X→1, T→3, N→3, B→5, A→6
    """
    ratio = _DENSITY_RATIO.get(str(dominant_axis or "X").upper(), 1.0)
    return max(1, round(1.0 + math.log10(max(ratio, 1.0)) * 2))


# ---------------------------------------------------------------------------
# Pressure-lens transform
# ---------------------------------------------------------------------------

def _apply_pressure_lens(
    axis_snapshot: Dict[str, float],
    perspective: Tuple[str, ...],
) -> Dict[str, float]:
    """Keep in-perspective axes at full polarity; attenuate others to 20 %."""
    lens = {a.upper() for a in perspective}
    return {
        name: (val if _AXIS_DOMAIN.get(name, name) in lens else val * 0.20)
        for name, val in (axis_snapshot or {}).items()
    }


# ---------------------------------------------------------------------------
# Helpers unchanged from previous version
# ---------------------------------------------------------------------------

def _clean_token(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("token", "word", "concept", "name", "label", "anchor", "topic"):
            if value.get(key):
                value = value.get(key)
                break
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_ -]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > 40:
        return ""
    if text in {"none", "null", "unknown"}:
        return ""
    return text


def _as_items(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [value]
    try:
        return list(value)
    except Exception:
        return [value]


def _axis_code(name: Any) -> str:
    return _AXIS_DOMAIN.get(str(name or ""), "X")


def _dominant_axis(axis_snapshot: Dict[str, float]) -> str:
    best_axis = "X"
    best_abs = 0.0
    for name, value in (axis_snapshot or {}).items():
        axis = _axis_code(name)
        mag = abs(float(value or 0.0))
        if mag > best_abs:
            best_abs = mag
            best_axis = axis
    return best_axis


def _add_projection(
    projections: List[Dict[str, Any]],
    *,
    token: Any,
    roles: List[str],
    slot_kind: str,
    source: str,
    confidence: float,
    axis_focus: str,
    topic: str = "",
) -> None:
    clean = _clean_token(token)
    if not clean:
        return
    projections.append({
        "token": clean,
        "roles": list(roles),
        "slot_kind": slot_kind,
        "source": source,
        "confidence": round(max(0.0, min(1.0, float(confidence or 0.0))), 4),
        "axis_focus": axis_focus,
        "topic": _clean_token(topic),
    })


def _dedupe_projections(projections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[tuple, Dict[str, Any]] = {}
    for item in projections:
        key = (item.get("token"), tuple(item.get("roles") or ()), item.get("slot_kind"))
        if key not in best or float(item.get("confidence", 0.0) or 0.0) > float(best[key].get("confidence", 0.0) or 0.0):
            best[key] = item
    return sorted(best.values(), key=lambda row: float(row.get("confidence", 0.0) or 0.0), reverse=True)[:12]


def _extract_slot_projections(projection: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract explicit slot candidates from a staged subsurface frame."""
    axis_snapshot = dict(projection.get("axis_polarities") or projection.get("original_axis_polarities") or {})
    perspective_tuple = projection.get("pressure_perspective")
    if perspective_tuple:
        axis_focus = _axis_code(perspective_tuple[0]) if perspective_tuple else "X"
    else:
        axis_focus = _axis_code(projection.get("dominant_axis_hint") or _dominant_axis(axis_snapshot))
    base_conf = float(projection.get("perspective_confidence", 0.84) or 0.84)
    projections: List[Dict[str, Any]] = []

    wm = dict(projection.get("working_memory") or {})
    topic = _clean_token(
        wm.get("dominant_theme")
        or projection.get("topic_concept")
        or dict(projection.get("conscious_frame") or {}).get("focus_domain")
    )
    for source_key in ("active_concepts", "recent_frames"):
        for item in _as_items(wm.get(source_key)):
            _add_projection(
                projections,
                token=item,
                roles=["noun"],
                slot_kind="entity",
                source=f"working_memory.{source_key}",
                confidence=0.74 * base_conf,
                axis_focus=axis_focus,
                topic=topic,
            )
    for source_key in ("dominant_theme", "focus_domain"):
        value = wm.get(source_key) or dict(projection.get("conscious_frame") or {}).get(source_key)
        _add_projection(
            projections,
            token=value,
            roles=["noun"],
            slot_kind="entity",
            source=source_key,
            confidence=0.82 * base_conf,
            axis_focus=axis_focus,
            topic=topic,
        )

    for signal in _as_items(projection.get("intuition_signals")):
        if not isinstance(signal, dict):
            continue
        weight = float(signal.get("weight", 0.45) or 0.45)
        _add_projection(
            projections,
            token=signal.get("label"),
            roles=["verb"],
            slot_kind="predicate",
            source="intuition_signal.label",
            confidence=max(0.46, min(0.92, weight)) * base_conf,
            axis_focus=axis_focus,
            topic=topic,
        )

    guidance = " ".join([
        str(projection.get("surface_guidance") or ""),
        " ".join(str(x or "") for x in _as_items(projection.get("active_effects"))),
    ]).lower()
    for word in _COMMON_PREDICATE_WORDS:
        if word in guidance:
            _add_projection(
                projections,
                token=word,
                roles=["verb"],
                slot_kind="predicate",
                source="subsurface_guidance",
                confidence=0.66 * base_conf,
                axis_focus=axis_focus,
                topic=topic,
            )

    return _dedupe_projections(projections)


# ---------------------------------------------------------------------------
# Queue I/O
# ---------------------------------------------------------------------------

def _load_queue() -> List[Dict[str, Any]]:
    try:
        if _QUEUE_PATH.exists():
            return json.loads(_QUEUE_PATH.read_text()) or []
    except Exception:
        pass
    return []


def _save_queue(frames: List[Dict[str, Any]]) -> None:
    try:
        tmp = str(_QUEUE_PATH) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(frames, f, indent=2)
        os.replace(tmp, str(_QUEUE_PATH))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PredictiveStager
# ---------------------------------------------------------------------------

class PredictiveStager:
    """Static-method interface for the predictive frame queue.

    Subsurface calls stage_passes_for_tick() each tick — it runs
    n_passes_for_density() perspective cycles drawn from the 31 canonical
    pressure subsets and pushes each result to the queue.

    Surface calls pop_all_recent_frames() once before each user turn to
    collect the most-recent unconsumed frames and store them in
    systems["_staged_subsurface_frames"] for ConstraintEmitter to consume.
    """

    @staticmethod
    def push_staged_frame(projection: Dict[str, Any]) -> None:
        """Push a validated subsurface projection as a staged candidate frame."""
        frames = _load_queue()
        projection = dict(projection or {})
        projection.setdefault("slot_projections", _extract_slot_projections(projection))
        frame = {
            "ts": time.time(),
            "projection": projection,
            "consumed": False,
        }
        frames.append(frame)
        if len(frames) > _MAX_FRAMES:
            frames = frames[-_MAX_FRAMES:]
        _save_queue(frames)

    @staticmethod
    def pop_staged_frame(context_hash: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Pop the freshest unconsumed staged frame, optionally matching context_hash."""
        frames = PredictiveStager.pop_staged_frames(context_hash=context_hash, limit=1)
        return frames[0] if frames else None

    @staticmethod
    def pop_staged_frames(
        context_hash: Optional[str] = None,
        limit: int = _MAX_FRAMES,
    ) -> List[Dict[str, Any]]:
        """Pop up to limit freshest unconsumed staged frames."""
        frames = _load_queue()
        if not frames:
            return []
        selected: List[Dict[str, Any]] = []
        for i in range(len(frames) - 1, -1, -1):
            frame = frames[i]
            if frame.get("consumed"):
                continue
            if context_hash is not None:
                frame_hash = frame.get("projection", {}).get("context_hash")
                if frame_hash and frame_hash != context_hash:
                    continue
            frames[i]["consumed"] = True
            projection = frame.get("projection")
            if isinstance(projection, dict):
                selected.append(projection)
            if len(selected) >= max(1, int(limit or 1)):
                break
        if selected:
            _save_queue(frames)
        return selected

    @staticmethod
    def pop_all_recent_frames(max_frames: int = _MAX_FRAMES) -> List[Dict[str, Any]]:
        """Pop up to max_frames unconsumed frames (newest first).

        Called by Surface before each user turn to harvest all pending
        Subsurface perspective passes.
        """
        return PredictiveStager.pop_staged_frames(limit=max_frames)

    @staticmethod
    def stage_hypothesis(
        systems: Dict[str, Any],
        working_memory: Any,
        conscious_frame: Any,
        perspective_index: int = 0,
    ) -> bool:
        """Run one hypothesis cycle through the given pressure perspective and push the result.

        perspective_index selects from PRESSURE_PERSPECTIVES (wraps around).
        Returns True if a frame was staged, False otherwise.
        """
        try:
            lattice = systems.get("ivm_lattice")
            if lattice is None:
                return False

            perspective = PRESSURE_PERSPECTIVES[perspective_index % len(PRESSURE_PERSPECTIVES)]

            # Snapshot current IVM axis polarities
            vertices = getattr(lattice, "vertices", None)
            axes = getattr(vertices, "axes", {}) if vertices else {}
            axis_snapshot: Dict[str, float] = {
                _axis_code(name): float(getattr(ax, "polarity", 0.0))
                for name, ax in axes.items()
            }
            transformed_axes = _apply_pressure_lens(axis_snapshot, perspective)

            # Lightweight working memory excerpt
            wm_snapshot: Dict[str, Any] = {}
            if working_memory is not None:
                for attr in ("active_concepts", "recent_frames", "dominant_theme"):
                    val = getattr(working_memory, attr, None)
                    if val is not None:
                        try:
                            wm_snapshot[attr] = list(val) if hasattr(val, "__iter__") and not isinstance(val, str) else val
                        except Exception:
                            pass

            # Consciousness frame excerpt
            cf_snapshot: Dict[str, Any] = {}
            if conscious_frame is not None:
                for attr in ("mode", "intensity", "focus_domain"):
                    val = getattr(conscious_frame, attr, None)
                    if val is not None:
                        cf_snapshot[attr] = str(val)

            dominant = _dominant_axis(transformed_axes)
            # Tier label for the perspective
            n = len(perspective)
            tier = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}.get(n, str(n))

            projection = {
                "source": "predictive_stager",
                "ts": time.time(),
                "pressure_perspective": list(perspective),
                "pressure_tier": tier,
                "perspective_index": perspective_index % len(PRESSURE_PERSPECTIVES),
                "perspective_confidence": _perspective_confidence(n),
                "dominant_axis_hint": dominant,
                "axis_polarities": transformed_axes,
                "original_axis_polarities": axis_snapshot,
                "working_memory": wm_snapshot,
                "conscious_frame": cf_snapshot,
            }
            projection["slot_projections"] = _extract_slot_projections(projection)
            PredictiveStager.push_staged_frame(projection)
            return True
        except Exception:
            return False

    @staticmethod
    def stage_passes_for_tick(
        systems: Dict[str, Any],
        working_memory: Any,
        conscious_frame: Any,
        perspective_offset: int = 0,
    ) -> Tuple[int, int]:
        """Run all density-appropriate perspective passes for one Subsurface tick.

        Determines n_passes from the dominant axis, then steps through
        PRESSURE_PERSPECTIVES starting at perspective_offset, cycling as needed.

        Returns (staged_count, next_perspective_offset) so the caller can
        persist offset across ticks for continuous perspective cycling.
        """
        try:
            lattice = systems.get("ivm_lattice")
            if lattice is None:
                return 0, perspective_offset

            vertices = getattr(lattice, "vertices", None)
            axes = getattr(vertices, "axes", {}) if vertices else {}
            axis_snapshot: Dict[str, float] = {
                _axis_code(name): float(getattr(ax, "polarity", 0.0))
                for name, ax in axes.items()
            }
            dominant = _dominant_axis(axis_snapshot)
            n = n_passes_for_density(dominant)

            staged = 0
            offset = int(perspective_offset or 0)
            for i in range(n):
                idx = (offset + i) % len(PRESSURE_PERSPECTIVES)
                if PredictiveStager.stage_hypothesis(
                    systems, working_memory, conscious_frame,
                    perspective_index=idx,
                ):
                    staged += 1

            next_offset = (offset + n) % len(PRESSURE_PERSPECTIVES)
            return staged, next_offset
        except Exception:
            return 0, perspective_offset

    @staticmethod
    def stage_density_passes(
        systems: Dict[str, Any],
        working_memory: Any,
        conscious_frame: Any,
        passes: int,
    ) -> int:
        """Backward-compatible shim: run a fixed number of passes from offset 0."""
        staged, _ = PredictiveStager.stage_passes_for_tick(
            systems, working_memory, conscious_frame, perspective_offset=0,
        )
        return staged


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _perspective_confidence(tier_size: int) -> float:
    """Confidence scales with tier completeness — full field is most confident."""
    return round({1: 0.82, 2: 0.86, 3: 0.90, 4: 0.94, 5: 0.98}.get(tier_size, 0.84), 4)
