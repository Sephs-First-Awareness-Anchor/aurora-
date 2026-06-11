# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from aurora_internal.dual_strata.sensory_snapshot_channel import read_surface_snapshot


class TransientSensorySnapshotProxy:
    """
    Subsurface sensory processor fed by disposable surface snapshots.

    Surface owns the live feed. Subsurface reads snapshots, integrates the
    usable vectors into a durable sensory crystal for learning/growth, then
    discards the snapshot itself.
    """

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self._session_id = "subsurface_snapshot"
        self._last_snapshot_ts = 0.0
        self._last_snapshot_meta: Dict[str, Any] = {}
        self._growth_crystal = None

        try:
            from aurora_internal.aurora_sensory_crystal import build_aurora_sensory_crystal

            self._growth_crystal = build_aurora_sensory_crystal(state_dir=str(self.state_dir))
            self._growth_crystal.start_session(self._session_id)
        except Exception:
            self._growth_crystal = None

        self._audio: Dict[str, Any] = getattr(self._growth_crystal, "_audio", {}) if self._growth_crystal is not None else {}
        self._visual: Dict[str, Any] = getattr(self._growth_crystal, "_visual", {}) if self._growth_crystal is not None else {}
        self._semantic: Dict[str, Any] = getattr(self._growth_crystal, "_semantic", {}) if self._growth_crystal is not None else {}

    def __getattr__(self, name: str) -> Any:
        crystal = object.__getattribute__(self, "_growth_crystal")
        if crystal is not None and hasattr(crystal, name):
            return getattr(crystal, name)
        raise AttributeError(name)

    def _read_snapshot(self) -> Dict[str, Any]:
        snapshot = read_surface_snapshot(self.state_dir)
        return snapshot if isinstance(snapshot, dict) else {}

    def _vector(self, values: Any, length: int) -> List[float]:
        vec = [float(v or 0.0) for v in list(values or [])[:length]]
        if len(vec) < length:
            vec.extend([0.0] * (length - len(vec)))
        return vec

    def _consume_latest_snapshot(self, *, force: bool = False) -> Dict[str, Any]:
        snapshot = self._read_snapshot()
        snapshot_ts = float(snapshot.get("updated_at", 0.0) or 0.0)
        if not snapshot_ts:
            return snapshot
        if (not force) and snapshot_ts <= self._last_snapshot_ts:
            return snapshot

        self._last_snapshot_ts = snapshot_ts
        self._last_snapshot_meta = {
            "updated_at": snapshot_ts,
            "trigger": str(snapshot.get("trigger", "") or "interval"),
            "flagged": bool(snapshot.get("flagged", False)),
            "reason": str(snapshot.get("reason", "") or ""),
            "summary": str(snapshot.get("summary", "") or ""),
        }

        if self._growth_crystal is None:
            return snapshot

        vectors = dict(snapshot.get("sensory_vectors") or {})
        audio_vec = self._vector(vectors.get("audio_20d"), 20)
        visual_vec = self._vector(vectors.get("vision_57d"), 57)
        if any(audio_vec) or any(visual_vec):
            try:
                session_id = f"{self._session_id}_{int(snapshot_ts)}"
                self._growth_crystal.observe_frame(audio_vec, visual_vec, session_id=session_id)
            except Exception:
                pass
        return snapshot

    def get_state(self) -> Dict[str, Any]:
        snapshot = self._consume_latest_snapshot()
        state = {}
        if self._growth_crystal is not None and hasattr(self._growth_crystal, "get_state"):
            try:
                state = dict(self._growth_crystal.get_state() or {})
            except Exception:
                state = {}
        surface_state = dict(snapshot.get("sensory_state") or {})
        recent_surface = list(dict(surface_state.get("recognitions") or {}).get("recent") or [])
        growth_recognitions = list(dict(state.get("recognitions") or {}).get("recent") or [])
        merged_recent = growth_recognitions[:]
        for item in recent_surface:
            text = str(item or "").strip()
            if text and text not in merged_recent:
                merged_recent.append(text)
        recognitions = dict(state.get("recognitions") or {})
        recognitions["recent"] = merged_recent[:6]
        state["recognitions"] = recognitions
        state["summary"] = str(snapshot.get("summary", "") or state.get("summary", ""))
        state["source"] = "subsurface_growth_from_surface_snapshot"
        state["growth_owner"] = "subsurface"
        state["snapshot_trigger"] = str(snapshot.get("trigger", "") or "interval")
        state["snapshot_flagged"] = bool(snapshot.get("flagged", False))
        state["snapshot_reason"] = str(snapshot.get("reason", "") or "")
        state["updated_at"] = float(snapshot.get("updated_at", 0.0) or time.time())
        native_bundle = dict(snapshot.get("native_meaning_bundle") or {})
        native_meaning = dict(snapshot.get("native_meaning") or {})
        if native_bundle:
            state["native_meaning_bundle"] = dict(native_bundle)
            state["native_meaning"] = dict(native_meaning or native_bundle.get("primary") or {})
        elif native_meaning:
            state["native_meaning_bundle"] = {"primary": dict(native_meaning)}
            state["native_meaning"] = dict(native_meaning)
        return state

    def save(self) -> bool:
        self._consume_latest_snapshot()
        if self._growth_crystal is not None and hasattr(self._growth_crystal, "save"):
            try:
                self._growth_crystal.save()
                return True
            except Exception:
                return False
        return True

    def start_session(self, session_id: str | None = None) -> bool:
        self._session_id = str(session_id or "subsurface_snapshot")
        if self._growth_crystal is not None and hasattr(self._growth_crystal, "start_session"):
            try:
                self._growth_crystal.start_session(self._session_id)
            except Exception:
                return False
        return True

    def end_session(self) -> List[Dict[str, Any]]:
        self._consume_latest_snapshot(force=True)
        if self._growth_crystal is not None and hasattr(self._growth_crystal, "end_session"):
            try:
                return list(self._growth_crystal.end_session() or [])
            except Exception:
                return []
        return []


SurfaceSensoryProxy = TransientSensorySnapshotProxy
