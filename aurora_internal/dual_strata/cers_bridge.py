# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERSBridge — Conscious Experiential Regulation System, shadow subsurface.

This is the parallel-shadow module described in the ERS conceptual spec
(ERS_Experiential_Regulation_System_Concept_Spec.md, Section 8): it completes
the exact same functional outputs as DualStrataBridge.build_snapshot()
(dce_bridge.py), through CERS-native convergence, without modifying or
replacing the existing subsurface in any way.

CERSBridge.build_snapshot() has the identical call signature to
DualStrataBridge.build_snapshot() so it can be called in parallel, on the
same turn, with no changes required to any existing caller. It writes to its
own state files (cers_snapshot.json, cers_detail.json) — it never touches
subsurface_snapshot.json or subsurface_detail.json.

Every tick it also logs an equivalence comparison against what legacy
convergence would have produced from the same sub_crests. That comparison
log is the substrate for recognizing, over time, whether CERS and the
legacy subsurface are converging on the same answers — the self-observation
mechanism the parallel-shadow strategy depends on. Nothing here decides to
merge or deprecate anything; it only produces the evidence that decision
would be made from.
"""
from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional, Tuple

from .conscious_frame import ConsciousFrame
from .contextual_overlay import ContextualOverlay
from .crest import Crest
from .dce_bridge import (
    DualStrataSnapshot,
    _extract_adjusted_axes,
    _extract_pressure_snapshot,
    build_contextual_overlay,
    converge_for_surface,
    derive_surface_behavior,
)
from .micro_reasoning import generate_micro_reasoning
from .prediction_field import build_prediction_signal
from .subsurface_state import AXES, SubsurfaceState, clip01, normalize_axis_map
from .subsystem_waveforms import emit_subsystem_crests

from .cers_regulator import CERSVerdict, PotentialTracker, cers_converge
from .cers_deprecation import DeprecationRecommendation, SubsystemDeprecationLedger
from .cers_potential_trial import PotentialTrialBoard
from .cers_tensor_locator import resolve_pressure_coordinate, record_tensor_trace, compute_salience


class CERSBridge:
    """Crest convergence orchestrator — CERS-governed, run in parallel with
    DualStrataBridge. Same call signature as DualStrataBridge.build_snapshot()."""

    def __init__(self, state_dir: Optional[str] = None):
        base = Path(state_dir) if state_dir else (Path(__file__).resolve().parents[2] / "aurora_state")
        self.state_dir = Path(base)
        self._frame_log: Deque[Dict[str, Any]] = deque(maxlen=50)
        self._equivalence_log: Deque[Dict[str, Any]] = deque(maxlen=50)
        self._tracker = PotentialTracker()
        self._trial_board = PotentialTrialBoard()
        self.deprecation_ledger = SubsystemDeprecationLedger()

    def build_snapshot(
        self,
        assembly_result: Any,
        *,
        payload: Any,
        payload_type: str,
        evidence: Optional[Dict[str, Any]] = None,
        contract_snapshot: Optional[Dict[str, Any]] = None,
        requested_frame: str = "balanced",
        thought_intent: Optional[Dict[str, Any]] = None,
        recursion_weights: Optional[Dict[str, float]] = None,
        precomputed_sub_crests: Optional[Tuple[Crest, ...]] = None,
        dps: Optional[Any] = None,
    ) -> DualStrataSnapshot:
        """
        precomputed_sub_crests: pass the sub_crests tuple already produced by
        a legacy DualStrataBridge.build_snapshot() call THIS SAME TICK (they
        are exposed on the returned snapshot's subsurface_state["sub_crests"]
        as plain dicts — reconstruct with Crest(**d) first). This is required
        when running CERSBridge and DualStrataBridge in true parallel on one
        tick: emit_subsystem_crests() drives a module-level WARP CrestRegistry
        singleton (subsystem_waveforms.py) with its own gap-persistence and
        trial-promotion counters. Calling it twice per tick — once from each
        bridge — would tick that singleton's internal state twice per turn
        and desynchronize WARP trial timing from the rest of the runtime.
        Passing the already-computed tuple keeps both bridges reading the
        exact same evidence for a true apples-to-apples equivalence test,
        and keeps the shared WARP registry ticking once per turn as designed.

        dps: CrystalProcessingSystem (systems["dimensional"].dps), used only
        for the tensor-trace pass (cers_tensor_locator.py) -- resolves this
        tick's live pressure onto a real SlotCoord in the constraint
        manifold and records the visit onto that coordinate's crystal in
        the SAME registry every other concept already lives in. Optional:
        the tensor pass is skipped (not faked) when dps is unavailable,
        same graceful-degradation posture as the rest of CERS.
        """
        evidence = dict(evidence or {})
        contract_snapshot = dict(contract_snapshot or {})
        adjusted_axes = _extract_adjusted_axes(assembly_result)

        # 1. Present overlay — unchanged, reused from dce_bridge.py
        sensory_context = dict(getattr(assembly_result, "sensory_context", {}) or {})
        overlay = build_contextual_overlay(payload, evidence, contract_snapshot, sensory_context)

        # 2. Prediction detail — unchanged, reused from prediction_field.py
        prediction_signal = build_prediction_signal(
            payload=payload,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            sensory_context=sensory_context,
            entropy_state=getattr(assembly_result, "entropy_state", None),
        )

        # 3. Subsystem crests — reused from subsystem_waveforms.py UNLESS
        # already provided by the caller (see precomputed_sub_crests above).
        if precomputed_sub_crests is not None:
            sub_crests = precomputed_sub_crests
        else:
            pressure_snapshot = _extract_pressure_snapshot(dict(evidence.get("pressure_snapshot") or {}))
            projection = dict(evidence.get("subsurface_projection") or {})

            sub_crests = emit_subsystem_crests(
                assembly_result=assembly_result,
                payload=payload,
                evidence=evidence,
                contract_snapshot=contract_snapshot,
                prediction_signal=prediction_signal,
                projection=projection,
                sensory_context=sensory_context,
                adjusted_axes=adjusted_axes,
                pressure_snapshot=pressure_snapshot,
                recursion_weights=recursion_weights,
            )

        # 4. CERS-governed convergence — THE upgrade. Everything above this
        # line is identical to DualStrataBridge.build_snapshot(); everything
        # below reuses legacy helpers again for surface derivation, which
        # stays unchanged because ERS's authority is subsurface-native, not
        # a surface-layer concern (per ERS spec Section 6).
        subsurface_crest, verdict = cers_converge(sub_crests, self._tracker, self._trial_board)

        # 4b. Tensor-trace pass (Phase 1 of the tensor-recursion upgrade) —
        # locate this tick's live pressure in the real constraint manifold
        # and record the visit onto that coordinate's crystal (same
        # registry every other concept lives in, no separate trace file).
        # Read-only w.r.t. everything above: never changes subsurface_crest
        # or verdict, only adds detail for downward traversal / eventual
        # compressed surfacing. Isolated in its own try/except so a failure
        # here can never take out the rest of an otherwise-good snapshot.
        tensor_trace: Dict[str, Any] = {}
        try:
            if dps is not None:
                coord = resolve_pressure_coordinate(adjusted_axes, sub_crests)
                if coord is not None:
                    worst_conflict = max((c.severity for c in verdict.conflicts), default=0.0)
                    crystal, distortion, is_new = record_tensor_trace(
                        dps, coord,
                        adjusted_axes=adjusted_axes,
                        label=str(subsurface_crest.label or "steady"),
                        severity=worst_conflict,
                    )
                    if crystal is not None:
                        tensor_trace = {
                            "coord": coord.slot_id,
                            "distortion": round(distortion, 4),
                            "is_new_coordinate": is_new,
                            "salience": compute_salience(
                                crystal, distortion=distortion, is_new=is_new, severity=worst_conflict,
                            ),
                        }
        except Exception:
            tensor_trace = {}

        # 5. Raw mechanism detail for downward traversal only
        _raw_coherence = getattr(assembly_result, "coherence", None)
        if _raw_coherence is None:
            _es = getattr(assembly_result, "entropy_state", {}) or {}
            _raw_coherence = float(_es.get("coherence", 0.45))
        _assembly_coherence = clip01(float(_raw_coherence or 0.45))

        _subsurface_detail: Dict[str, Any] = {
            "sub_crests": [c.to_dict() for c in sub_crests],
            "coherence": round(_assembly_coherence, 4),
            "cers_verdict": verdict.to_dict(),
            "governed_by": "cers_regulator.cers_converge",
            "tensor_trace": tensor_trace,
        }

        subsurface = SubsurfaceState(
            subsurface_crest=subsurface_crest,
            sub_crests=sub_crests,
            dominant_axis=subsurface_crest.axis,
            frame_request=str(requested_frame or "balanced"),
            overlay=overlay,
            _subsurface_detail=_subsurface_detail,
        )

        # 5b. Micro-reasoning — unchanged, reused from micro_reasoning.py
        _mr_hypotheses = generate_micro_reasoning(
            subsurface,
            assembly_result=assembly_result,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
        )
        _subsurface_detail["micro_reasoning"] = [h.to_dict() for h in _mr_hypotheses]

        # 6. Surface convergence — unchanged, reused from dce_bridge.py.
        # CERS only governs what the subsurface hands up; the surface
        # consumes it exactly as it would consume the legacy subsurface_crest.
        surface_input = dict(evidence.get("surface_input") or {})
        user_turn_present = bool(
            str(surface_input.get("raw_text", "") or "").strip()
            or str(surface_input.get("full_phrase", "") or "").strip()
            or str(surface_input.get("source_text", "") or "").strip()
            or str(payload or "").strip()
        )
        conscious_crest = converge_for_surface(
            subsurface_crest=subsurface_crest,
            overlay=overlay,
            coherence=_assembly_coherence,
            user_turn_present=user_turn_present,
        )

        stance, action, should_speak, processing_mode = derive_surface_behavior(
            conscious_crest, subsurface_crest, overlay, coherence=_assembly_coherence
        )

        conscious = ConsciousFrame(
            conscious_crest=conscious_crest,
            subsurface_crest=subsurface_crest,
            overlay=overlay,
            stance=stance,
            selected_action=action,
            should_speak=should_speak,
            readiness=round(_assembly_coherence, 4),
            coherence=round(_assembly_coherence, 4),
            dominant_axis=conscious_crest.axis,
            processing_mode=processing_mode,
        )

        snapshot = DualStrataSnapshot(
            subsurface_state=subsurface.to_dict(),
            conscious_frame=conscious.to_dict(),
        )
        self.persist(snapshot, verdict)
        self.persist_cers_detail(_subsurface_detail)
        return snapshot

    def persist(self, snapshot: DualStrataSnapshot, verdict: CERSVerdict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = snapshot.to_dict()
        payload["saved_at"] = time.time()
        snapshot_path = self.state_dir / "cers_snapshot.json"
        snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")

        log_entry = {
            "ts": payload["saved_at"],
            "conscious_crest": payload.get("conscious_frame", {}).get("conscious_crest", {}).get("label", ""),
            "stance": payload.get("conscious_frame", {}).get("stance", ""),
            "selected_action": payload.get("conscious_frame", {}).get("selected_action", ""),
            "should_speak": bool(payload.get("conscious_frame", {}).get("should_speak", False)),
            "processing_mode": payload.get("conscious_frame", {}).get("processing_mode", ""),
            "dominant_axis": payload.get("conscious_frame", {}).get("dominant_axis", ""),
            "readiness": payload.get("conscious_frame", {}).get("readiness", 0.0),
        }
        self._frame_log.append(log_entry)

        equivalence_entry = {
            "ts": payload["saved_at"],
            "legacy_label": verdict.legacy_label,
            "cers_label": verdict.cers_label,
            "agrees_with_legacy": verdict.agrees_with_legacy,
            "conflicts": [c.to_dict() for c in verdict.conflicts],
            "unused_potential": list(verdict.unused_potential),
            "actively_trialing_potential": list(verdict.actively_trialing_potential),
            "confirmed_potential_benefits": dict(verdict.confirmed_potential_benefits),
            "confirmed_inert_potential": list(verdict.confirmed_inert_potential),
        }
        self._equivalence_log.append(equivalence_entry)
        self.deprecation_ledger.record(equivalence_entry)

    def persist_cers_detail(self, detail: Dict[str, Any]) -> None:
        """Write CERS detail to a private file, mirroring subsurface_detail.json's
        role but kept entirely separate. Never read by the surface daemon."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        detail_path = self.state_dir / "cers_detail.json"
        detail = dict(detail)
        detail["saved_at"] = time.time()
        detail["deprecation_recommendation"] = self.deprecation_ledger.evaluate().to_dict()
        detail_path.write_text(json.dumps(detail, indent=2, ensure_ascii=True, sort_keys=True, default=str), encoding="utf-8")

    def equivalence_summary(self) -> Dict[str, Any]:
        """Rolling equivalence read against the legacy subsurface, over the
        in-memory window. This is the evidence a higher layer would consult
        before ever deciding to merge or deprecate either path."""
        if not self._equivalence_log:
            return {"frames": 0, "agreement_rate": None, "conflicts_flagged": 0}
        frames = list(self._equivalence_log)
        agree_count = sum(1 for f in frames if f.get("agrees_with_legacy"))
        conflict_count = sum(len(f.get("conflicts", [])) for f in frames)
        return {
            "frames": len(frames),
            "agreement_rate": round(agree_count / len(frames), 4),
            "conflicts_flagged": conflict_count,
        }

    def deprecation_recommendation(self) -> Dict[str, Any]:
        """The actual auto-deprecation test result. Hard-gated by unused
        potential — see cers_deprecation.py. Never an action, only a read."""
        return self.deprecation_ledger.evaluate().to_dict()
