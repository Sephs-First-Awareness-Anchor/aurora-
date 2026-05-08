"""
aurora_pressure_ledger.py -- Universal behavioral experience recorder.

The same causal chain applied in every behavioral evolution subsystem:

    pursuing      -- what was being attempted (goal / intent at this layer)
    causal_action -- the specific operation that incurred the cost
    consequence   -- what that action produced (tension, gate failure, fitness drop)
    outcome       -- how it resolved relative to what was being pursued

Any subsystem that applies pressure to Aurora's behavior calls
PressureExperienceLedger.get().record(...).  The ledger persists every
experience to aurora_state/pressure_experiences.jsonl and bridges into OETS
concept nodes as UsageExamples -- so each concept accumulates real causal
history instead of developer-authored rules.

Integration points:
    turn_chain    -- N-axis cost pressure during conversational reasoning
    genealogy     -- Gate 2/4/5 rejection when promoting a constraint link
    dream_trainer -- lesson episode fitness below threshold
    lsv_template  -- expression template fitness drop
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# PressureExperience -- the universal causal record
# ---------------------------------------------------------------------------

@dataclass
class PressureExperience:
    """
    One causal experience recorded anywhere in Aurora's behavioral system.

    anchor        -- the concept / link / template under pressure
    meaning       -- what that anchor represents in this subsystem's context
    pursuing      -- what was being attempted
    causal_action -- the specific operation that incurred the cost
    consequence   -- what that action produced
    outcome       -- how it resolved relative to what was being pursued
    source        -- which subsystem generated this (turn_chain / genealogy /
                     dream_trainer / lsv_template / ...)
    """
    experience_id: str = field(
        default_factory=lambda: hashlib.md5(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:12]
    )
    timestamp:     float = field(default_factory=time.time)
    source:        str = ""
    anchor:        str = ""
    meaning:       str = ""
    pursuing:      str = ""
    causal_action: str = ""
    consequence:   Dict[str, Any] = field(default_factory=dict)
    outcome:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "experience_id": self.experience_id,
            "timestamp":     self.timestamp,
            "source":        self.source,
            "anchor":        self.anchor,
            "meaning":       self.meaning,
            "pursuing":      self.pursuing,
            "causal_action": self.causal_action,
            "consequence":   self.consequence,
            "outcome":       self.outcome,
        }

    def as_usage_text(self) -> str:
        """
        Compact record for OETS UsageExample.text.
        Encodes: what was attempted -> what it cost -> how it resolved.
        """
        resolved   = self.outcome.get("resolved", False)
        tone       = self.outcome.get("tone", "")
        resolution = f"{'resolved' if resolved else 'diverted'}:{tone}" if tone else (
            "resolved" if resolved else "diverted"
        )
        tension = self.consequence.get(
            "tension",
            self.consequence.get("belief_tension",
            self.consequence.get("cost_signal", 0.0))
        )
        return (
            f"[{self.source}] "
            f"action:[{self.causal_action}] "
            f"-> cost={tension:.3f} "
            f"-> {resolution}"
        )


# ---------------------------------------------------------------------------
# PressureExperienceLedger -- singleton collector + OETS bridge
# ---------------------------------------------------------------------------

class PressureExperienceLedger:
    """
    Collects PressureExperience records from any subsystem, persists them,
    and bridges the causal record into OETS concept nodes.
    """

    _LOG_PATH = "aurora_state/pressure_experiences.jsonl"
    _instance: Optional["PressureExperienceLedger"] = None

    def __init__(self) -> None:
        self._buffer: List[PressureExperience] = []
        try:
            os.makedirs("aurora_state", exist_ok=True)
        except Exception:
            pass

    @classmethod
    def get(cls) -> "PressureExperienceLedger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def record(
        self,
        anchor:        str,
        meaning:       str,
        pursuing:      str,
        causal_action: str,
        consequence:   Dict[str, Any],
        outcome:       Dict[str, Any],
        source:        str = "",
        oets:          Any = None,
    ) -> PressureExperience:
        """
        Record one causal experience and optionally bridge it into OETS.

        Parameters map directly to the five-part chain:
            pursuing -> causal_action -> consequence -> outcome
        anchored to a concept (anchor) with known meaning (meaning).
        """
        exp = PressureExperience(
            source=source,
            anchor=str(anchor or "").strip(),
            meaning=str(meaning or "").strip(),
            pursuing=str(pursuing or "").strip(),
            causal_action=str(causal_action or "").strip(),
            consequence=dict(consequence or {}),
            outcome=dict(outcome or {}),
        )
        self._buffer.append(exp)

        # Persist immediately -- atomic append to JSONL
        try:
            with open(self._LOG_PATH, "a") as f:
                f.write(json.dumps(exp.to_dict()) + "\n")
        except Exception:
            pass

        # Bridge into OETS if available
        if oets and exp.anchor:
            self._bridge_to_oets(exp, oets)

        return exp

    def flush_to_oets(self, oets: Any) -> int:
        """
        Bridge all buffered experiences that haven't been bridged yet.
        Call this when OETS becomes available (e.g. after boot).
        """
        bridged = 0
        for exp in self._buffer:
            if exp.anchor:
                self._bridge_to_oets(exp, oets)
                bridged += 1
        return bridged

    def recent(
        self,
        n: int = 20,
        source: str = "",
        anchor: str = "",
    ) -> List[PressureExperience]:
        """Return recent experiences, optionally filtered by source or anchor."""
        results = self._buffer
        if source:
            results = [e for e in results if e.source == source]
        if anchor:
            results = [e for e in results if e.anchor == anchor]
        return results[-n:]

    # ------------------------------------------------------------------
    # Variance analysis -- the distribution of outcomes IS the signal
    # ------------------------------------------------------------------

    def outcome_variance(
        self,
        anchor: str,
        causal_action: str = "",
    ) -> Dict[str, Any]:
        """
        For a given anchor (and optionally a specific causal_action), compute
        the variance in outcomes across all recorded experiences.

        Same action + different outcomes = conditional relationship.
        Same action + same outcome = reliable / rigid relationship.

        Returns:
            {
                "is_conditional":   bool   -- True if outcomes vary for same action
                "resolution_rate":  float  -- fraction of experiences that resolved
                "sample_count":     int    -- total experiences for this anchor
                "outcome_entropy":  float  -- 0=certain, 1=maximally uncertain
                "by_action": {             -- per-action breakdown
                    action_key: {
                        "resolved":   int,
                        "diverted":   int,
                        "rate":       float,
                        "is_conditional": bool,
                    }
                }
            }
        """
        candidates = [e for e in self._buffer if e.anchor == anchor]
        if causal_action:
            candidates = [e for e in candidates if e.causal_action == causal_action]

        if not candidates:
            return {
                "is_conditional": False,
                "resolution_rate": 0.0,
                "sample_count": 0,
                "outcome_entropy": 0.0,
                "by_action": {},
            }

        # Group by causal_action, count resolved vs diverted
        by_action: Dict[str, Dict[str, int]] = {}
        total_resolved = 0
        for exp in candidates:
            act = exp.causal_action[:60]  # normalize key length
            if act not in by_action:
                by_action[act] = {"resolved": 0, "diverted": 0}
            if exp.outcome.get("resolved", False):
                by_action[act]["resolved"] += 1
                total_resolved += 1
            else:
                by_action[act]["diverted"] += 1

        # Conditionality: any action that has BOTH resolved and diverted outcomes
        any_conditional = False
        action_summary: Dict[str, Any] = {}
        for act, counts in by_action.items():
            r = counts["resolved"]
            d = counts["diverted"]
            total = r + d
            rate = r / total if total else 0.0
            cond = r > 0 and d > 0  # same action, both outcomes seen
            if cond:
                any_conditional = True
            action_summary[act] = {
                "resolved": r,
                "diverted": d,
                "rate": round(rate, 4),
                "is_conditional": cond,
            }

        # Outcome entropy across all experiences for this anchor
        n = len(candidates)
        p_res = total_resolved / n if n else 0.0
        p_div = 1.0 - p_res
        import math
        entropy = 0.0
        if 0 < p_res < 1:
            entropy = -(p_res * math.log2(p_res) + p_div * math.log2(p_div))
        # Normalise to [0, 1] (max entropy for binary = 1.0 at p=0.5)

        return {
            "is_conditional":  any_conditional,
            "resolution_rate": round(p_res, 4),
            "sample_count":    n,
            "outcome_entropy": round(entropy, 4),
            "by_action":       action_summary,
        }

    def conditioning_signal(self, anchor: str) -> Dict[str, Any]:
        """
        High-level signal for the reasoning chain:
        does this concept have a conditional causal history?

        Returns a dict with:
            "conditional":      bool   -- should reasoning seek additional context?
            "certainty":        float  -- 1=certain, 0=maximally uncertain
            "sample_count":     int
            "varying_actions":  list   -- causal actions with split outcomes
            "note":             str    -- human-readable summary for chain injection
        """
        v = self.outcome_variance(anchor)
        varying = [
            act for act, info in v["by_action"].items()
            if info["is_conditional"]
        ]
        certainty = 1.0 - v["outcome_entropy"]  # high entropy = low certainty
        note = ""
        if v["is_conditional"]:
            note = (
                f"concept '{anchor}' has conditional outcomes "
                f"({v['resolution_rate']:.0%} resolved across {v['sample_count']} experiences): "
                f"same actions have produced different results -- "
                f"look for additional context before assuming fixed outcome"
            )
        elif v["sample_count"] >= 3:
            outcome_label = "resolved" if v["resolution_rate"] > 0.5 else "diverted"
            note = (
                f"concept '{anchor}' shows consistent {outcome_label} outcome "
                f"({v['resolution_rate']:.0%} across {v['sample_count']} experiences)"
            )
        return {
            "conditional":     v["is_conditional"],
            "certainty":       round(certainty, 4),
            "sample_count":    v["sample_count"],
            "varying_actions": varying,
            "outcome_entropy": v["outcome_entropy"],
            "note":            note,
        }

    # ------------------------------------------------------------------
    # OETS bridge
    # ------------------------------------------------------------------

    def _bridge_to_oets(self, exp: PressureExperience, oets: Any) -> None:
        """
        Write the causal experience into the OETS concept node for `anchor`.

        Three operations:
          1. UsageExample on the SemanticNode -- compact experiential record,
             annotated with conditionality if this action has split outcomes.
          2. Conditionality flag -- if outcomes now vary for this anchor,
             set uncertain_token=True on the node so all queries see it.
          3. StudyEvent in the study log -- full causal record.
        """
        try:
            from aurora_internal.aurora_ontological_scaffolding import (
                StudyEvent,
                UsageExample,
            )
        except ImportError:
            return

        # Check outcome variance BEFORE adding this experience, then after.
        # If adding this experience introduces new split outcomes for the same
        # causal_action, the node becomes conditional right now.
        variance_before = self.outcome_variance(exp.anchor, exp.causal_action)
        # (exp is already in _buffer, so variance includes this experience)
        variance_after  = self.outcome_variance(exp.anchor)

        # 1 -- UsageExample on the concept node, annotated with conditionality
        try:
            node = None
            if hasattr(oets, "web") and hasattr(oets.web, "get_node"):
                node = oets.web.get_node(exp.anchor.lower())
            if node is not None:
                tension = float(exp.consequence.get(
                    "tension",
                    exp.consequence.get("belief_tension",
                    exp.consequence.get("cost_signal", 0.1))
                ))
                usage_text = exp.as_usage_text()
                # Annotate with conditionality when the same action has produced
                # different outcomes -- this is the variance signal embedded in the record.
                action_info = variance_after["by_action"].get(exp.causal_action[:60], {})
                if action_info.get("is_conditional"):
                    r = action_info["resolved"]
                    d = action_info["diverted"]
                    usage_text += f" [conditional: {r}R/{d}D for this action]"
                ue = UsageExample(
                    text=usage_text,
                    context=f"pressure_experience:{exp.source}",
                    i_state="n_axis_cost",
                    fitness=min(1.0, tension * 2),
                )
                node.usage_examples.append(ue)
                node.usage_examples = node.usage_examples[-20:]
                node.times_encountered = getattr(node, "times_encountered", 0) + 1

                # 2 -- Conditionality flag: if the concept now has split outcomes,
                # mark it as uncertain so the reasoning chain knows to seek context.
                if variance_after["is_conditional"]:
                    node.uncertain_token = True
        except Exception:
            pass

        # 3 -- StudyEvent in the persistent study log, includes variance snapshot
        try:
            ev = StudyEvent(
                autonomy_mode="pressure_teaching",
                trigger_reason=f"{exp.source}: {exp.causal_action[:80]!r}",
                studied_items=[{
                    **exp.to_dict(),
                    "outcome_variance": variance_after,
                }],
                relations_added=0,
                memory_committed=False,
                why_not_committed="pressure_experience_pending_integration",
                announce_worthy=variance_after["is_conditional"],  # worth surfacing
            )
            if hasattr(oets, "log_study_event"):
                oets.log_study_event(ev)
        except Exception:
            pass
