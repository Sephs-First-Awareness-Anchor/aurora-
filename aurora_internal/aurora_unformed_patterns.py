#!/usr/bin/env python3
"""
aurora_unformed_patterns.py -- recognising what has yet to form.

Sunni, 2026-11-08: "provide her with the ability to recognize the missing
patterning outlier that separates all she represents currently from what it
is we discovered has yet to form."  Not a recogniser for any kind of message.
Nothing here names what is missing; it is computed.

COVERAGE
  Every turn already shows which of her representations engaged (a remembered
  path, a communication operation, her composer's draft) and whether what she
  holds could carry the turn: her own voice stood (own_voice / own_composition)
  or nothing she holds could (pressure-only articulation, silence, a scripted
  fallback).  A carried turn that a receiver then understands joins the
  REFERENCE: the distribution of everything she does represent.

SIGNATURE
  A turn is described only by her own outputs: which relational slots her
  parser filled and which stayed open, the unknown role, query type, stance,
  pragmatic signal roles, response obligation, meaning label, dominant axis,
  which representations engaged, and her axis activation.  No word of the
  message itself, no word list.

RESIDUE -- the separating pattern
  On an uncarried turn, every feature is scored by how far it departs from the
  reference (Laplace-smoothed absence among understood carried turns; axis
  activation by z-score).  The features that depart most are the residue: what
  separates this experience from everything she represents.

FORMATION
  Residues recur.  Similar residues (Jaccard on the pattern's core) collect
  into one FORMING PATTERN.  A one-off is noise; once a pattern has recurred
  RECUR times it is a gap in her, and each further occurrence is HANDED TO
  EVERY SYSTEM THAT ACCEPTS GAPS:
    * every WarpCapable system she has booted -- each checks the pattern's
      axis profile against ITS OWN coverage, read-only first, and only where
      it is a gap for that system is check_and_extend() called, so the system
      grows its own trial (a covered profile would otherwise reset that
      system's persistence counters for unrelated gaps);
    * the universal confession, warp_guard(MISSING_REPRESENTATION), keyed to
      the pattern so the warp field sees it recur.
  The profile is the occurrences' mean axis activation, sharpened along the
  axes where it departs from the reference.

FORMED
  When turns carrying a pattern's core start being carried AND understood, the
  pattern is covering; after COVERED_TO_FORM such turns it is FORMED and no
  longer handed off.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

UNFORMED_VERSION = "aurora_unformed_patterns_v1"
AXES = ("X", "T", "N", "B", "A")

CARRIED_OUTCOMES = ("own_voice", "own_composition")
REFERENCE_MIN = 12          # understood carried turns before departure is trusted
DEPARTURE_FLOOR = 0.80      # a feature belongs to the residue at or above this
AXIS_Z_FLOOR = 1.5
SMOOTH = 1.0
SIMILAR = 0.5               # Jaccard on cores to join a forming pattern
CORE_SHARE = 0.5            # a feature is core when in >= half of occurrences
RECUR = 3
COVERED_TO_FORM = 3
MAX_PATTERNS = 200
MAX_PENDING = 64
HANDOFF_SEVERITY = 0.6


def _f(v: Any) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0


def signature(pipeline_state: Mapping[str, Any], *, gate: Optional[Mapping[str, Any]] = None,
              engaged: Iterable[str] = ()) -> Tuple[Set[str], Dict[str, float]]:
    """(categorical features, axis activation) -- her own outputs only."""
    ps = dict(pipeline_state or {})
    form = dict(ps.get("relational_form") or {})
    parsed = dict(ps.get("parsed") or {})
    feats: Set[str] = set()
    for slot in ("subject", "relation", "obj", "complement"):
        feats.add(f"slot:{slot}:{'filled' if str(form.get(slot) or '').strip() else 'open'}")
    if form.get("unknown_role"):
        feats.add(f"unknown:{form.get('unknown_role')}")
    for flag in ("question", "directive", "interaction_event"):
        if form.get(flag):
            feats.add(f"form:{flag}")
    if parsed.get("query_type"):
        feats.add(f"query:{parsed.get('query_type')}")
    stance = ps.get("input_stance") or ps.get("user_stance")
    if stance:
        feats.add(f"stance:{stance}")
    for sig in list(ps.get("pragmatic_signals") or parsed.get("pragmatic_signals") or []):
        role = sig[0] if isinstance(sig, (list, tuple)) and sig else (sig.get("role") if isinstance(sig, Mapping) else None)
        if role:
            feats.add(f"signal:{role}")
    op = dict(ps.get("response_obligation") or {}).get("operation")
    if op:
        feats.add(f"obligation:{op}")
    if ps.get("meaning_label"):
        feats.add(f"meaning:{ps.get('meaning_label')}")
    if ps.get("dominant_axis"):
        feats.add(f"axis:{ps.get('dominant_axis')}")
    for name in engaged:
        feats.add(f"engaged:{name}")
    axes = {ax: _f(dict(ps.get("axis_activation") or {}).get(ax)) for ax in AXES}
    return feats, axes


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a or b) else 0.0


class UnformedPatterns:
    def __init__(self, *, state_dir: str = "aurora_state", persist: bool = True, clock=time.time) -> None:
        self.path = os.path.join(state_dir, "unformed_patterns.json")
        self.persist = persist
        self.clock = clock
        self._lock = threading.RLock()
        self.ref_n = 0
        self.ref_counts: Dict[str, int] = {}
        self.ref_axis_sum = {ax: 0.0 for ax in AXES}
        self.ref_axis_sq = {ax: 0.0 for ax in AXES}
        self.patterns: Dict[str, Dict[str, Any]] = {}
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.counters = {"turns": 0, "carried": 0, "uncarried": 0, "residues": 0,
                         "handoffs": 0, "system_extensions": 0, "formed": 0}
        self.last_residue: Dict[str, Any] = {}
        self.last_handoff: Dict[str, Any] = {}
        self._load()

    # -- persistence --------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh) or {}
        except Exception:
            return
        self.ref_n = int(raw.get("ref_n", 0) or 0)
        self.ref_counts = {str(k): int(v) for k, v in dict(raw.get("ref_counts") or {}).items()}
        self.ref_axis_sum.update({k: _f(v) for k, v in dict(raw.get("ref_axis_sum") or {}).items()})
        self.ref_axis_sq.update({k: _f(v) for k, v in dict(raw.get("ref_axis_sq") or {}).items()})
        self.patterns = {str(k): dict(v) for k, v in dict(raw.get("patterns") or {}).items()}
        self.counters.update({k: int(v) for k, v in dict(raw.get("counters") or {}).items()})
        self.last_residue = dict(raw.get("last_residue") or {})
        self.last_handoff = dict(raw.get("last_handoff") or {})

    def _save(self) -> None:
        if not self.persist:
            return
        try:
            from aurora_internal.aurora_turn_persistence import batch_defer
            if batch_defer(self):
                return
        except Exception:
            pass
        self.flush_write_batch()

    def flush_write_batch(self) -> None:
        if not self.persist:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with self._lock:
                data = json.dumps({"version": UNFORMED_VERSION, "ref_n": self.ref_n,
                                   "ref_counts": self.ref_counts, "ref_axis_sum": self.ref_axis_sum,
                                   "ref_axis_sq": self.ref_axis_sq, "patterns": self.patterns,
                                   "counters": self.counters, "last_residue": self.last_residue,
                                   "last_handoff": self.last_handoff})
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp, self.path)
        except Exception:
            pass

    # -- the reference: what she does represent ----------------------------------------

    def _add_reference(self, feats: Iterable[str], axes: Mapping[str, float]) -> None:
        self.ref_n += 1
        for f in feats:
            self.ref_counts[f] = self.ref_counts.get(f, 0) + 1
        for ax in AXES:
            v = _f(axes.get(ax))
            self.ref_axis_sum[ax] += v
            self.ref_axis_sq[ax] += v * v

    def _ref_mean_std(self, ax: str) -> Tuple[float, float]:
        n = max(1, self.ref_n)
        mean = self.ref_axis_sum[ax] / n
        var = max(0.0, self.ref_axis_sq[ax] / n - mean * mean)
        return mean, math.sqrt(var) or 1e-6

    def departure(self, feature: str) -> float:
        """1 - smoothed share of understood carried turns that showed it."""
        share = (self.ref_counts.get(feature, 0) + SMOOTH) / (self.ref_n + 2 * SMOOTH)
        return round(1.0 - share, 4)

    def residue(self, feats: Iterable[str], axes: Mapping[str, float]) -> List[str]:
        """What separates this turn from everything she represents."""
        feats = set(feats)
        if self.ref_n < REFERENCE_MIN:
            out = set(feats)              # nothing trusted yet: the whole signature is unexplained
        else:
            out = {f for f in feats if self.departure(f) >= DEPARTURE_FLOOR}
            for ax in AXES:
                mean, std = self._ref_mean_std(ax)
                z = (_f(axes.get(ax)) - mean) / std
                if abs(z) >= AXIS_Z_FLOOR:
                    out.add(f"axis_dev:{ax}{'+' if z > 0 else '-'}")
        return sorted(out)

    # -- forming patterns ---------------------------------------------------------------

    @staticmethod
    def core(pattern: Mapping[str, Any]) -> List[str]:
        n = max(1, int(pattern.get("occurrences", 0) or 0))
        return sorted(f for f, c in dict(pattern.get("feature_counts") or {}).items() if c / n >= CORE_SHARE)

    def _match(self, residue: List[str]) -> Optional[str]:
        best, best_j = None, 0.0
        for pid, p in self.patterns.items():
            if p.get("status") == "formed":
                continue
            j = _jaccard(residue, self.core(p) or p.get("feature_counts", {}).keys())
            if j > best_j:
                best, best_j = pid, j
        return best if best_j >= SIMILAR else None

    def _profile(self, pattern: Mapping[str, Any]) -> Dict[str, float]:
        n = max(1, int(pattern.get("occurrences", 0) or 0))
        mean = {ax: _f(dict(pattern.get("axis_sum") or {}).get(ax)) / n for ax in AXES}
        if self.ref_n >= REFERENCE_MIN:
            ref = {ax: self._ref_mean_std(ax)[0] for ax in AXES}
            mean = {ax: mean[ax] + max(0.0, mean[ax] - ref[ax]) for ax in AXES}
        top = max(mean.values()) or 1.0
        return {ax: round(max(0.0, v) / top, 4) for ax, v in mean.items()}

    def observe_turn(self, pipeline_state: Mapping[str, Any], *, gate: Optional[Mapping[str, Any]] = None,
                     engaged: Iterable[str] = (), response_id: str = "",
                     systems: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        feats, axes = signature(pipeline_state, gate=gate, engaged=engaged)
        outcome = str(dict(gate or {}).get("outcome") or "")
        carried = outcome in CARRIED_OUTCOMES
        record: Dict[str, Any] = {"carried": carried, "outcome": outcome}
        handoff: Dict[str, Any] = {}
        with self._lock:
            self.counters["turns"] += 1
            self.counters["carried" if carried else "uncarried"] += 1
            if response_id:
                self.pending[str(response_id)] = {"feats": sorted(feats), "axes": axes, "carried": carried}
                while len(self.pending) > MAX_PENDING:
                    self.pending.pop(next(iter(self.pending)))
            if not carried:
                res = self.residue(feats, axes)
                if res:
                    self.counters["residues"] += 1
                    pid = self._match(res)
                    if pid is None:
                        pid = "UP:" + hashlib.sha1(json.dumps(res).encode()).hexdigest()[:12]
                        self.patterns[pid] = {"feature_counts": {}, "occurrences": 0, "axis_sum": {ax: 0.0 for ax in AXES},
                                              "status": "forming", "first_at": self.clock(), "covered": 0,
                                              "handoffs": 0, "extended_by": {}}
                    p = self.patterns[pid]
                    p["occurrences"] += 1
                    p["last_at"] = self.clock()
                    for f in res:
                        p["feature_counts"][f] = p["feature_counts"].get(f, 0) + 1
                    for ax in AXES:
                        p["axis_sum"][ax] = _f(p["axis_sum"].get(ax)) + _f(axes.get(ax))
                    record.update({"pattern": pid, "residue": res, "occurrences": p["occurrences"]})
                    self.last_residue = {"pattern": pid, "residue": res[:12], "occurrences": p["occurrences"],
                                         "at": self.clock()}
                    if p["occurrences"] >= RECUR and p.get("status") == "forming":
                        handoff = {"pattern": pid, "profile": self._profile(p), "core": self.core(p)}
                    self._prune()
        if handoff:
            record["handoff"] = self.hand_off(systems or {}, handoff)
        self._save()
        return record

    def _prune(self) -> None:
        if len(self.patterns) <= MAX_PATTERNS:
            return
        ranked = sorted(self.patterns.items(),
                        key=lambda kv: (kv[1].get("status") == "forming", kv[1].get("occurrences", 0), kv[1].get("last_at", 0)))
        for pid, _ in ranked[: len(self.patterns) - MAX_PATTERNS]:
            self.patterns.pop(pid, None)

    # -- hand-off: every system that accepts gaps ----------------------------------------

    @staticmethod
    def _warp_capable_systems(systems: Mapping[str, Any]) -> List[Tuple[str, Any]]:
        try:
            from aurora_warp_protocol import WarpCapable
        except Exception:
            return []
        found: Dict[int, Tuple[str, Any]] = {}
        field = systems.get("warp_field")
        for name, sys_obj in dict(getattr(field, "_warp_capable_registry", {}) or {}).items():
            if isinstance(sys_obj, WarpCapable):
                found[id(sys_obj)] = (str(name), sys_obj)
        for name, sys_obj in systems.items():
            if isinstance(sys_obj, WarpCapable) and id(sys_obj) not in found:
                found[id(sys_obj)] = (str(name), sys_obj)
        return sorted(found.values(), key=lambda kv: kv[0])

    def hand_off(self, systems: Mapping[str, Any], handoff: Mapping[str, Any]) -> Dict[str, Any]:
        pid, profile = str(handoff["pattern"]), dict(handoff["profile"])
        results: Dict[str, str] = {}
        try:
            from aurora_warp_protocol import AxisCoverageChecker
        except Exception:
            AxisCoverageChecker = None  # type: ignore
        pattern = self.patterns.get(pid) or {}
        for name, sys_obj in self._warp_capable_systems(systems):
            try:
                # One open trial per pattern per system: while the trial this
                # pattern grew there is still being evaluated, the system is
                # left to its own promotion / dissolution -- otherwise a
                # persistent gap would keep spawning near-identical trials.
                open_trial = str(dict(pattern.get("extended_by") or {}).get(name) or "")
                if open_trial and open_trial in dict(getattr(sys_obj, "_warp_trials", {}) or {}):
                    results[name] = "trial_open"
                    continue
                profiles = dict(sys_obj._get_axis_profiles() or {})
                for comp in dict(getattr(sys_obj, "_warp_promoted", {}) or {}).values():
                    profiles[comp.component_id] = comp.axis_profile
                if AxisCoverageChecker is not None and profiles:
                    if AxisCoverageChecker(profiles).check(profile, source="unformed_patterns", tick=0) is None:
                        results[name] = "covered"
                        continue
                comp = sys_obj.check_and_extend(profile, source="unformed_patterns", tick=0,
                                                topology_gap_ref=pid)
                results[name] = f"extended:{comp.component_id}" if comp is not None else "gap_counted"
                if comp is not None:
                    self.counters["system_extensions"] += 1
            except Exception as exc:
                results[name] = f"error:{type(exc).__name__}"
        try:
            from aurora_warp_protocol import WarpTrigger, warp_guard
            warp_guard(source="unformed_patterns", layer="representation",
                       trigger=WarpTrigger.MISSING_REPRESENTATION, profile=profile,
                       severity=HANDOFF_SEVERITY, persistence_key=pid,
                       expected={"core": list(handoff.get("core") or [])[:12]})
            results["warp_field"] = "confessed"
        except Exception as exc:
            results["warp_field"] = f"error:{type(exc).__name__}"
        with self._lock:
            p = self.patterns.get(pid)
            if p is not None:
                p["handoffs"] = int(p.get("handoffs", 0)) + 1
                for name, res in results.items():
                    if res.startswith("extended:"):
                        p["extended_by"][name] = res.split(":", 1)[1]
            self.counters["handoffs"] += 1
            self.last_handoff = {"pattern": pid, "profile": profile, "results": results, "at": self.clock()}
        return results

    # -- verdicts --------------------------------------------------------------------------

    def record_receiver_outcome(self, response_id: str, outcome_kind: str) -> Dict[str, Any]:
        with self._lock:
            rec = self.pending.pop(str(response_id or ""), None)
            if rec is None or outcome_kind != "positive" or not rec.get("carried"):
                return {"matched": rec is not None, "effect": "none"}
            feats, axes = rec["feats"], rec["axes"]
            self._add_reference(feats, axes)
            effect = "reference"
            for pid, p in self.patterns.items():
                core = self.core(p)
                if p.get("status") == "forming" and core and set(core) <= set(feats) | {
                        f for f in core if f.startswith("axis_dev:")}:
                    p["covered"] = int(p.get("covered", 0)) + 1
                    effect = f"covering:{pid}"
                    if p["covered"] >= COVERED_TO_FORM:
                        p["status"] = "formed"
                        p["formed_at"] = self.clock()
                        self.counters["formed"] += 1
                        effect = f"formed:{pid}"
        self._save()
        return {"matched": True, "effect": effect}

    # -- what her clones found yet to form (FIX-A105) -------------------------------------

    def absorb_clone_patterns(self, harvest: Mapping[str, Any]) -> Dict[str, Any]:
        """Take in the reference turns and forming patterns her clones met.

        The reference is additive (more understood, carried turns she can
        compare against).  A clone pattern joins the forming pattern of hers
        whose core it shares (the same SIMILAR rule a live residue uses), so
        the same gap found by several clones -- and by her -- recurs as one
        pattern.  Hand-offs are not replayed: once a joined pattern has
        recurred, her next live occurrence hands it to every system."""
        ref = dict(harvest.get("reference") or {})
        joined, added = 0, 0
        with self._lock:
            self.ref_n += int(ref.get("n", 0) or 0)
            for f, c in dict(ref.get("counts") or {}).items():
                self.ref_counts[str(f)] = self.ref_counts.get(str(f), 0) + int(c or 0)
            for ax in AXES:
                self.ref_axis_sum[ax] += _f(dict(ref.get("axis_sum") or {}).get(ax))
                self.ref_axis_sq[ax] += _f(dict(ref.get("axis_sq") or {}).get(ax))
            for item in list(harvest.get("patterns") or []):
                counts = {str(k): int(v or 0) for k, v in dict(item.get("feature_counts") or {}).items()}
                occ = int(item.get("occurrences", 0) or 0)
                if not counts or occ <= 0:
                    continue
                probe = {"feature_counts": counts, "occurrences": occ}
                pid = self._match(self.core(probe) or sorted(counts))
                if pid is None:
                    pid = "UP:" + hashlib.sha1(json.dumps(sorted(counts)).encode()).hexdigest()[:12]
                    self.patterns[pid] = {"feature_counts": {}, "occurrences": 0, "axis_sum": {ax: 0.0 for ax in AXES},
                                          "status": "forming", "first_at": self.clock(), "covered": 0,
                                          "handoffs": 0, "extended_by": {}}
                    added += 1
                else:
                    joined += 1
                p = self.patterns[pid]
                p["occurrences"] = int(p.get("occurrences", 0)) + occ
                for f, c in counts.items():
                    p["feature_counts"][f] = p["feature_counts"].get(f, 0) + c
                for ax in AXES:
                    p["axis_sum"][ax] = _f(p["axis_sum"].get(ax)) + _f(dict(item.get("axis_sum") or {}).get(ax))
                p["covered"] = int(p.get("covered", 0)) + int(item.get("covered", 0) or 0)
                p["clones"] = int(p.get("clones", 0) or 0) + int(item.get("clones", 1) or 1)
                p["last_at"] = self.clock()
                if p.get("status") == "forming" and p["covered"] >= COVERED_TO_FORM:
                    p["status"] = "formed"
                    p["formed_at"] = self.clock()
                    self.counters["formed"] += 1
            self.counters["clone_patterns_joined"] = int(self.counters.get("clone_patterns_joined", 0)) + joined
            self.counters["clone_patterns_added"] = int(self.counters.get("clone_patterns_added", 0)) + added
            self._prune()
        self.flush_write_batch()
        return {"joined": joined, "added": added, "reference_turns": int(ref.get("n", 0) or 0)}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            forming = [p for p in self.patterns.values() if p.get("status") == "forming"]
            recurring = [p for p in forming if p.get("occurrences", 0) >= RECUR]
            top = sorted(forming, key=lambda p: -int(p.get("occurrences", 0)))[:1]
            return {"version": UNFORMED_VERSION, **self.counters, "reference_turns": self.ref_n,
                    "forming": len(forming), "recurring": len(recurring),
                    "formed_patterns": sum(1 for p in self.patterns.values() if p.get("status") == "formed"),
                    "top_core": self.core(top[0])[:6] if top else [],
                    "top_occurrences": int(top[0].get("occurrences", 0)) if top else 0,
                    "last_residue": dict(self.last_residue), "last_handoff": dict(self.last_handoff)}
