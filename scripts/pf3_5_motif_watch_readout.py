#!/usr/bin/env python3
"""
PF3.5 -- motif promotion watch, weekly readout.

Directive PF3 (Sunni & Cael, 2026-07-21): developmental-gate rule
stands -- no seeding while the window is open. This script is the
"observation" half of the watch: it reports, it does not act. Two
signals, both "does she have enough ways to say things":

  (a) Promoted, clause-valid motif count and shape distribution from
      aurora_state/grammar_motifs.json (read-only -- this is the SAME
      file MotifLineage persists to and reads from live; no scratch
      copy needed for a read-only report). "Clause-valid" reuses
      aurora_grammar_engine.is_valid_clause_shape's own L1 whitelist
      (_VALID_CLAUSE_SHAPES) -- the same eligibility gate composition
      itself is bound by, not a separate metric invented for this
      readout.

  (b) Cluster-E-style repetition share: the same-role-filled-twice
      frequency PF3.4's characterization named and PF3.4a's motif-
      thinning guard targets. Computed from an existing characterize_
      pf16_residue.py output (pass --characterization <path>) rather
      than re-running the live battery here -- this script is meant to
      run cheaply and often; a fresh battery run is its own separate,
      already-established step (scripts/characterize_pf16_residue.py).

Trigger (not automated here, a human call per the directive): if at
window close promoted clause-valid count is still 3 AND/OR repetition
share hasn't materially improved, seed candidate shapes through
MotifLineage.seed_motifs (aurora_grammar_engine.py:796) -- feed-the-
mechanism, candidates enter the same fitness competition as everything
else, no direct promotion. This script does not call seed_motifs.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aurora_grammar_engine import TokenRole, is_valid_clause_shape  # noqa: E402

DEFAULT_MOTIFS_PATH = REPO_ROOT / "aurora_state" / "grammar_motifs.json"

# PF3.5 window (directive PF3): 14 days of live, thought-fed, carryover-
# corrected operation FROM PF3.1's LANDING (not PF2's) -- PF3.1
# materially changed what content motifs receive, so the window
# restarts from its own commit date.
_WINDOW_START = datetime(2026, 7, 21, tzinfo=timezone.utc)
_WINDOW_DAYS = 14
_WINDOW_TURNS = 500


def _role_sequence_from_strings(role_strings):
    try:
        return tuple(TokenRole(r) for r in role_strings)
    except ValueError:
        return None


def _motif_readout(motifs_path: Path) -> dict:
    with open(motifs_path) as f:
        data = json.load(f)
    motifs = data.get("motifs", {})

    promoted = [m for m in motifs.values() if m.get("promoted")]
    clause_valid_promoted = []
    for m in promoted:
        seq = _role_sequence_from_strings(m.get("role_sequence", []))
        if seq is not None and is_valid_clause_shape(seq):
            clause_valid_promoted.append(m)

    shape_distribution = Counter(
        "_".join(m.get("role_sequence", [])) for m in clause_valid_promoted
    )

    return {
        "total_motifs": len(motifs),
        "total_promoted": len(promoted),
        "promoted_clause_valid_count": len(clause_valid_promoted),
        "clause_valid_shapes": dict(shape_distribution),
        "saved_at": data.get("saved_at"),
    }


def _repetition_share(characterization_path: Path) -> dict:
    """Same-role-filled-twice frequency: within a single delivered
    response, the same content word appearing as the fill for the SAME
    role position in more than one clause. Approximated the same way
    PF3.3/PF3.4's own analysis did -- direct inspection of the
    delivered text's repeated tokens across its own sentences, since
    per-clause role assignment isn't persisted in the characterization
    JSON (only the whole response + motif id list)."""
    with open(characterization_path) as f:
        data = json.load(f)
    records = data.get("records", [])

    def is_residue(r):
        coh = r.get("coherent")
        adeq = r.get("adequacy")
        return (isinstance(coh, bool) and not coh) or (
            isinstance(adeq, (int, float)) and adeq < 0.55)

    residue = [r for r in records if is_residue(r)]
    repeated_clause_count = 0
    for r in residue:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', r.get("delivered", "")) if s.strip()]
        if len(sentences) < 2:
            continue
        token_sets = [
            set(w for w in re.findall(r"[a-zA-Z']+", s.lower()) if len(w) >= 3)
            for s in sentences
        ]
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                if token_sets[i] & token_sets[j]:
                    repeated_clause_count += 1
                    break
            else:
                continue
            break

    return {
        "total_records": len(records),
        "residue_records": len(residue),
        "repeated_clause_records": repeated_clause_count,
        "repetition_share_of_residue": (
            repeated_clause_count / len(residue) if residue else None
        ),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--motifs", default=str(DEFAULT_MOTIFS_PATH),
                     help="Path to grammar_motifs.json (default: live aurora_state/)")
    ap.add_argument("--characterization", default=None,
                     help="Path to a characterize_pf16_residue.py output JSON, "
                          "for the repetition-share readout. Omit to skip (a)-only readout.")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    elapsed_days = (now - _WINDOW_START).days
    window_open = elapsed_days < _WINDOW_DAYS

    print(f"[PF3.5 motif watch readout] {now.isoformat()}")
    print(f"  window: started {_WINDOW_START.date()}, {_WINDOW_DAYS} days or {_WINDOW_TURNS} turns "
          f"(whichever first) -- {elapsed_days} days elapsed, "
          f"{'OPEN' if window_open else 'CLOSED -- trigger check due'}")
    print()

    motif_report = _motif_readout(Path(args.motifs))
    print("  (a) motif promotion:")
    print(f"      total motifs tracked:        {motif_report['total_motifs']}")
    print(f"      total promoted:               {motif_report['total_promoted']}")
    print(f"      promoted AND clause-valid:    {motif_report['promoted_clause_valid_count']}")
    print(f"      clause-valid shape distribution:")
    for shape, count in sorted(motif_report["clause_valid_shapes"].items()):
        print(f"        {shape}: {count}")
    print()

    if args.characterization:
        rep_report = _repetition_share(Path(args.characterization))
        print("  (b) Cluster-E-style repetition share:")
        print(f"      residue records:              {rep_report['residue_records']}/{rep_report['total_records']}")
        print(f"      records with repeated cross-clause tokens: {rep_report['repeated_clause_records']}")
        if rep_report["repetition_share_of_residue"] is not None:
            print(f"      share of residue:              {100*rep_report['repetition_share_of_residue']:.1f}%")
    else:
        print("  (b) Cluster-E-style repetition share: skipped (pass --characterization <path>)")
    print()

    if not window_open:
        print("  TRIGGER CHECK DUE: if promoted_clause_valid_count is still 3 and/or")
        print("  repetition share hasn't materially improved, seed via")
        print("  MotifLineage.seed_motifs (aurora_grammar_engine.py:796) -- human call,")
        print("  not automated by this script.")


if __name__ == "__main__":
    main()
