# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tensor_occupancy_warp_bridge.py

Feeds FieldSlot occupancy events (aurora_state/tensor_occupancy.jsonl, written
by tensor_occupancy_hook.py) into WARP's coverage-gap / 6th-axis anomaly
pipeline (aurora_warp_protocol.py), so a deposited pressure vector that
doesn't resonate with any known manifold noncomp has somewhere real to
register that fact -- not just a `resolved_nc_name: null` in a log nobody
reads.

IMPORTANT DISTINCTION -- this checks a different thing than
tensor_occupancy_hook.resolve_field_slot_signature() does:

  resolve_field_slot_signature()  -- does this deposit's (constraint, comp,
                                      state) LABEL COMBINATION match one of
                                      the 125 known (law, dim, target)
                                      identities? (a label-scheme lookup)

  check_and_extend() here          -- does this deposit's actual DEPOSITED
                                      VECTOR (the X/T/N/B/A pressure weights)
                                      resonate, in 15D I-state+recursion
                                      space, with what any known noncomp's
                                      own identity would look like as a
                                      pressure profile? (a coverage check)

A deposit can resolve its label combination cleanly (label lookup succeeds)
and still carry a pressure vector that covers no known profile well -- that
second case is the genuine WARP situation, and it's what this module checks
for. FieldSlot's label space is also a fixed 5x5x5x5 shape today (see
tensor_occupancy_hook.py's own note), so resolve_field_slot_signature()
returning None currently only means a malformed call, not a live 6th value --
this module is where an actually novel *pressure pattern* gets a real chance
to surface, regardless of whether its labels resolved.

KNOWN-PROFILE CONSTRUCTION (a defined convention, like tensor_occupancy_hook's
label mapping -- not verified ground truth): each of the 125 manifold
noncomps is turned into a 15D profile by spreading equal weight across its
own (nc_law_c, nc_target, DIMENSION_ROLE[nc_dim]) axis set, scaled by its
formula_coefficient, then run through aurora_warp_protocol.axes_to_istates()
-- the same 5D-to-15D recipe aurora_warp_protocol.py already uses elsewhere
(_search_genealogy's ConstraintLink relief). Noncomps carry no recursion
depth of their own, so their recursion dimensions are left at 0 -- a real
modeling limitation (see module docstring below), not swept under the rug.

Cross-run limitation: WarpGenerator's anomaly log and WarpCapable's gap-
persistence counter are in-memory only. Each occupancy entry processed
within one run of scripts/bridge_tensor_occupancy_to_warp.py contributes to
gap-persistence debounce (GAP_PERSISTENCE_REQUIRED consecutive matching
gaps), but that state does not currently survive between separate runs of
the script. A gap that occurs twice today and once next week will not be
caught by the persistence check today; it would need cross-run
serialization of WarpGenerator/WarpCapable state, which this pass does not
add. Flagged here rather than silently assumed away.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from aurora_constraint_signature_resolver import DIMENSION_ROLE
import aurora_manifold_lookup
from aurora_warp_protocol import (
    WarpCapable,
    WarpComponent,
    axes_to_istates,
    _ALL_AXES,
    _RECURSION_DIMS,
)

# FieldSlot.RECURSION_LABELS ("depth_0".."depth_4") map directly, 1:1, onto
# aurora_warp_protocol's recursion dims -- FieldSlot's own docstring says its
# RecursionLevel indices already "map directly to IVM RecursionLevel enum
# (SURFACE=0 through CORE=4)", which is exactly what REC_SURFACE..REC_CORE
# are. Unlike Law/Dimension, this one needed no invention.
_DEPTH_LABEL_TO_RECURSION_DIM: Dict[str, str] = {
    "depth_0": "REC_SURFACE",
    "depth_1": "REC_SHALLOW",
    "depth_2": "REC_MODERATE",
    "depth_3": "REC_DEEP",
    "depth_4": "REC_CORE",
}

_MIN_PROFILE_WEIGHT = 0.05  # floor so a near-zero formula_coefficient doesn't zero out a whole profile
_RECURSION_BASELINE = 0.3   # uniform "not tied to a depth" prior -- see _noncomp_axis_profile


def _noncomp_axis_profile(data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Build a 15D I-state+recursion profile for one manifold noncomp, from its
    own (law, target, dimension-role-axis) identity and formula_coefficient.
    Returns None if the noncomp's identity fields are missing/invalid.
    """
    law = str(data.get("nc_law_c", "") or "").upper()
    target = str(data.get("nc_target", "") or "").upper()
    role_axis = DIMENSION_ROLE.get(str(data.get("nc_dim", "") or "").upper())

    active_axes = sorted({a for a in (law, target, role_axis) if a in _ALL_AXES})
    if not active_axes:
        return None

    coeff = float(data.get("formula_coefficient", 0.0) or 0.0)
    weight_each = max(_MIN_PROFILE_WEIGHT, coeff) / len(active_axes)
    # axes_to_istates() defaults a MISSING key to 0.5, not 0.0 (it expects a
    # full 5-key dict, e.g. _search_genealogy's {ax: relief.get(ax, 0.0) for
    # ax in _ALL_AXES}) -- so inactive axes must be explicit 0.0 here, or
    # they'd silently inflate every "uninvolved" I-state to ~0.25.
    axis_weights = {a: (weight_each if a in active_axes else 0.0) for a in _ALL_AXES}

    profile = axes_to_istates(axis_weights, ivm_polarity=None)

    # Noncomps carry no recursion depth of their own. Leaving recursion dims
    # at hard 0.0 was tried first and rejected: since every real occupancy
    # deposit carries some recursion label (FieldSlot always logs one),
    # measured cosine similarity against a 0.0-recursion known profile
    # crashes for EVERY deposit regardless of how well its axes match --
    # verified directly (a clean single-axis match with a recursion label
    # dropped from best_coverage ~1.0 to ~0.44 purely from the recursion
    # term). That would flood the gap/anomaly pipeline with noise instead of
    # signal, defeating GAP_PERSISTENCE_REQUIRED/ANOMALY_CANDIDATE_THRESHOLD's
    # whole purpose.
    #
    # A low uniform baseline across all 5 recursion dims says "this identity
    # isn't tied to one depth over another" without claiming a specific one.
    # No baseline value fully restores coverage, though -- worked out the
    # closed form for a perfect axis match: cosine peaks around b~=0.095 for
    # that case and *falls* again above it (known-profile norm grows
    # quadratically with b while the dot product only grows linearly), so
    # there's no single "right" b that reconciles a one-hot recursion signal
    # against a uniform one. 0.3 was chosen to land a clean axis match around
    # ~0.5 coverage -- comfortably above ANOMALY_THRESHOLD (won't falsely
    # read as a 6th-axis candidate) but still a real, honestly-earned gap,
    # since the static manifold genuinely has no opinion on live recursion
    # depth. Trial components spawned from that gap dissolve rather than
    # promote (_score_trial is fixed below PROMOTION_SCORE), so this
    # surfaces as an observable signal, not a false claim of full coverage.
    for rec_dim in _RECURSION_DIMS:
        profile[rec_dim] = _RECURSION_BASELINE
    return profile


def _load_all_noncomp_profiles() -> Dict[str, Dict[str, float]]:
    """
    Load all 125 manifold noncomps and build their coverage-space profiles.
    Returns {} (not raise) if the manifold directory/index isn't available --
    matches aurora_manifold_lookup's own graceful-miss contract.
    """
    profiles: Dict[str, Dict[str, float]] = {}
    for name in aurora_manifold_lookup.all_noncomp_names():
        data = aurora_manifold_lookup.load_noncomp(name)
        if data is None:
            continue
        profile = _noncomp_axis_profile(data)
        if profile is not None:
            profiles[name] = profile
    return profiles


class TensorOccupancyWarpBridge(WarpCapable):
    """
    WarpCapable host for FieldSlot occupancy events. Not a running behavioral
    system the way DimensionalSystems/ConsciousnessEngine are -- there is no
    "integrate this component into live behavior" step at this raw-tensor
    layer, so _integrate_warp/_dissolve_warp just track presence (in memory
    and in a small visibility log) rather than wiring into any downstream
    consumer. _score_trial has no real usage signal to score against at this
    layer either, so it returns a fixed, deliberately-sub-promotion-threshold
    score -- components observed here get logged as evidence, not silently
    auto-promoted into permanent structure without a real quality signal.
    """

    STATUS_LOG_PATH = "aurora_state/tensor_occupancy_warp_components.jsonl"

    def __init__(self, genealogy: Any = None) -> None:
        self._init_warp(genealogy=genealogy)
        self._known_profiles: Dict[str, Dict[str, float]] = _load_all_noncomp_profiles()
        self._integrated: List[WarpComponent] = []
        self._tick = 0

    # ── WarpCapable required overrides ────────────────────────────────────────

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        return dict(self._known_profiles)

    def _warp_level_name(self) -> str:
        return "tensor_occupancy"

    def _integrate_warp(self, component: WarpComponent) -> None:
        self._integrated.append(component)
        try:
            import json
            from pathlib import Path
            path = Path(self.STATUS_LOG_PATH)
            path.parent.mkdir(exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps({
                    "timestamp":     time.time(),
                    "component_id":  component.component_id,
                    "name":          component.name,
                    "parent_ids":    list(component.parent_ids or []),
                    "profile":       component.axis_profile,
                    "sixth_axis_signal": component.sixth_axis_signal,
                }) + "\n")
        except Exception:
            pass  # visibility log is best-effort; never break Warp lifecycle on it

    def _score_trial(self, component: WarpComponent) -> float:
        # No downstream usage signal exists at this raw-tensor layer -- return
        # a fixed score deliberately below PROMOTION_SCORE (0.60) so a
        # component observed here dissolves after TRIAL_TICKS rather than
        # being falsely promoted without real evidence of usefulness.
        return 0.5

    def _dissolve_warp(self, component_id: str) -> None:
        self._integrated = [c for c in self._integrated if c.component_id != component_id]

    # ── public interface ───────────────────────────────────────────────────────

    def process_entry(self, entry: Dict[str, Any]) -> Optional[WarpComponent]:
        """
        Check one tensor_occupancy.jsonl entry's deposited vector against the
        known-noncomp coverage space. Returns the new WarpComponent if a
        persistent gap fires one, None otherwise (covered, not yet
        persistent, or a pure 6th-axis anomaly -- logged via
        anomaly_summary(), not returned).
        """
        vec = entry.get("vector")
        if not vec:
            return None

        axis_weights = {a: float(vec.get(a, 0.0) or 0.0) for a in _ALL_AXES}
        profile = axes_to_istates(axis_weights, ivm_polarity=None)

        rec_dim = _DEPTH_LABEL_TO_RECURSION_DIM.get(entry.get("recursion_label") or "")
        if rec_dim:
            profile[rec_dim] = 1.0

        self._tick += 1
        return self.check_and_extend(profile, source="tensor_occupancy", tick=self._tick)

    def run_cycle(self) -> None:
        """Score/promote/dissolve any accumulated trial components. Call once
        per batch of processed entries (see scripts/bridge_tensor_occupancy_to_warp.py)."""
        self.evaluate_warp_trials()
