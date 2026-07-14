# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/mtsl_acceptance_report.py
=========================================================
MTSL Phase 8 (2026-07-13) -- Acceptance & Success Metrics (directive
section 9). The directive has no separate implementation section for
"Phase 8": section 9 says the external spec's section 30 acceptance
battery is adopted "verbatim as the completion contract" and section
31's success metrics "are measured from the Phase 3 shadow-comparison
log." The external spec's actual section 30/31 tables were not
available to this implementation (same gap as spec sections 12/17/22
elsewhere in this codebase). Fabricating a battery of checks against
criteria this implementation has never seen would not be "no stubs" --
it would be worse than a stub, a false completion claim.

What IS real and concrete: the directive's own words that MTSL "earns
authority from that ledger or it stays an observer" -- section 6's
gate for the log itself is literal ("no articulation change yet"), and
every phase after it (4-7) deliberately left every live-behavior-
changing wire disconnected, gated behind MTSL_AUTHORITY_STAGE
(default 1, cers_regulator.py). Someone deciding whether to advance
that stage needs to be able to READ the evidence ledger honestly.
This module is that reader: it parses aurora_state/mtsl_shadow_comparison.jsonl
(written by both TopologicalSemanticCoordinator._log_shadow_comparison()
and SemanticIntentionBridge._log_shift()) and produces a plain summary
-- turn counts, ambiguity rate, strategy-shift counts and their
distribution, variant-creation rate. It computes and reports; it does
not decide, gate, or recommend a stage change -- "Stage advancement is
a manual, evidence-cited decision — never automatic" (directive
section 7), and that discipline extends to this reader: it is
read-only over a log two OTHER modules already write, and it never
writes anything itself.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List

from .topological_semantic_coordinator import SHADOW_COMPARISON_FILENAME


def read_shadow_comparison_log(state_dir: str) -> List[Dict[str, Any]]:
    """Every parseable line from mtsl_shadow_comparison.jsonl, in file
    order. Missing file or unparseable lines degrade to an empty/
    partial result -- never an exception, matching the rest of MTSL's
    "skip, never fake" posture."""
    path = os.path.join(state_dir, SHADOW_COMPARISON_FILENAME)
    entries: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return entries


@dataclass(frozen=True)
class AcceptanceSummary:
    total_entries: int
    coordinator_observations: int
    strategy_shifts: int
    semantic_ambiguity_count: int
    semantic_ambiguity_rate: float
    variant_created_count: int
    variant_created_rate: float
    strategy_shift_distribution: Dict[str, int]
    applied_strategy_shift_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "coordinator_observations": self.coordinator_observations,
            "strategy_shifts": self.strategy_shifts,
            "semantic_ambiguity_count": self.semantic_ambiguity_count,
            "semantic_ambiguity_rate": self.semantic_ambiguity_rate,
            "variant_created_count": self.variant_created_count,
            "variant_created_rate": self.variant_created_rate,
            "strategy_shift_distribution": dict(self.strategy_shift_distribution),
            "applied_strategy_shift_count": self.applied_strategy_shift_count,
        }


def summarize(entries: List[Dict[str, Any]]) -> AcceptanceSummary:
    """Pure function over already-read log entries. Two entry shapes
    share this one log file: coordinator observations (top-level keys
    like turn_id/semantic_ambiguity/dominant_semantic_variant, written
    by TopologicalSemanticCoordinator._log_shadow_comparison()) and
    strategy shifts (a single "strategy_shift" key wrapping an
    IntentionDecision.to_dict(), written by
    SemanticIntentionBridge._log_shift()). Distinguished by the
    presence of that one key -- never by entry order or count, since
    the two writers interleave independently."""
    coordinator_entries = [e for e in entries if "strategy_shift" not in e]
    shift_entries = [e["strategy_shift"] for e in entries if "strategy_shift" in e]

    ambiguity_count = sum(1 for e in coordinator_entries if bool(e.get("semantic_ambiguity")))
    variant_created_count = sum(
        1 for e in coordinator_entries if e.get("dominant_semantic_variant") is not None
    )
    n_coord = len(coordinator_entries)

    shift_distribution = Counter(str(s.get("strategy", "")) for s in shift_entries)
    applied_count = sum(1 for s in shift_entries if bool(s.get("applied")))

    return AcceptanceSummary(
        total_entries=len(entries),
        coordinator_observations=n_coord,
        strategy_shifts=len(shift_entries),
        semantic_ambiguity_count=ambiguity_count,
        semantic_ambiguity_rate=(round(ambiguity_count / n_coord, 4) if n_coord else 0.0),
        variant_created_count=variant_created_count,
        variant_created_rate=(round(variant_created_count / n_coord, 4) if n_coord else 0.0),
        strategy_shift_distribution=dict(shift_distribution),
        applied_strategy_shift_count=applied_count,
    )


def acceptance_summary(state_dir: str) -> AcceptanceSummary:
    """Convenience wrapper: read the log for state_dir, then
    summarize(). The two-step form (read_shadow_comparison_log() +
    summarize()) is exposed separately so a caller who already has
    entries in hand (e.g. a test, or a caller aggregating across
    multiple state dirs) never re-reads the file."""
    return summarize(read_shadow_comparison_log(state_dir))
