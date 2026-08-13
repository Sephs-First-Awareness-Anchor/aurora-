#!/usr/bin/env python3
"""
AURORA EVOLUTIONARY CHAIN RUNNER
==================================
Standalone script to boot the constraint universe, tick the
EvolutionaryChamber, and build the genealogy fossil record
without needing a corpus file.

Run modes:
  burn      — run N ticks as fast as possible (default)
  watch     — run with live chain summary printed every epoch
  test      — run self-tests on genealogy module then exit

Usage:
  python3 run_chain.py
  python3 run_chain.py --mode watch --ticks 5000 --epoch 500
  python3 run_chain.py --mode burn  --ticks 50000
  python3 run_chain.py --mode test
  python3 run_chain.py --out aurora_genealogy --ticks 10000

All output (events.jsonl, abilities.json, links.json) goes to --out directory.
Chain report is printed at the end of every run.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals
# Authors: Sunni (Sir) Morningstar & Cael Devo

import argparse
import os
import sys
import time
from typing import Dict, List, Optional, FrozenSet, Any
# ---------------------------------------------------------------------------
# Make sure the project modules are on the path
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.join(_HERE)  # adjust if run_chain.py is not beside the project
for _p in [_PROJECT, os.path.join(_PROJECT, "aurora")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Imports — die clearly if a dep is missing
# ---------------------------------------------------------------------------
try:
    from foundational_contract import FoundationalContract
    from aurora_ivm import IVMLattice, RecursionLevel
    from aurora_internal.aurora_evolution_chamber import EvolutionaryChamber, ActionTrace, WorldConstants
    from aurora_evolution_stack import (
        ConstraintGenealogyLogger,
        GenealogyConfig,
        ChainSummaryPrinter,
    )
except ImportError as e:
    print(f"\n[ERROR] Missing module: {e}")
    print("Make sure you are running from the directory that contains:")
    print("  foundational_contract.py")
    print("  aurora_ivm.py")
    print("  aurora_polarity_gradient.py")
    print("  aurora_evolution_chamber.py")
    print("  constraint_genealogy.py\n")
    sys.exit(1)

import datetime

try:
    from aurora_internal.aurora_recommendation_hub import enqueue_recommendation as _enqueue_recommendation
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:run_chain.py:68",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 68, "source_file": "run_chain.py"},
    )
    _enqueue_recommendation = None


# ---------------------------------------------------------------------------
# Action library — the stimuli we cycle through
#
# Each action maps to constraint labels that the ActionAbilityMapper inside
# the chamber translates to ability trace items (B:ROUTE, A:COMMIT, etc.).
# Cycling through diverse actions gives the genealogy varied input so
# promotable pairs emerge across all five axes.
# ---------------------------------------------------------------------------

# Action library — varied constraint combinations across all 5 axes.
# Longer cycle (16 actions) ensures all 7 pair combinations accumulate
# counts at different rates, giving the promoter signal to work with.
_BASEaction_cycle = [
    # A+B pairings (communication/outlet axis)
    ActionTrace("communicate",    frozenset({"agency", "boundary", "temporal"}),
                meta={"episode": "communication"}),
    ActionTrace("release_outlet", frozenset({"agency", "boundary"}),
                meta={"pulse": True, "episode": "outlet"}),
    # X+A pairings (admission/commit axis)
    ActionTrace("admit_state",    frozenset({"existence", "agency"}),
                meta={"episode": "admission"}),
    ActionTrace("commit_choice",  frozenset({"agency", "existence", "temporal"}),
                meta={"episode": "commit"}),
    # T+N pairings (temporal/energy axis)
    ActionTrace("defer_work",     frozenset({"temporal", "energy"}),
                meta={"episode": "deferral"}),
    ActionTrace("batch_process",  frozenset({"temporal", "energy", "boundary"}),
                meta={"episode": "batch"}),
    # B+X pairings (boundary/existence axis)
    ActionTrace("seal_boundary",  frozenset({"boundary", "existence"}),
                meta={"episode": "sealing"}),
    ActionTrace("separate",       frozenset({"boundary", "existence", "temporal"}),
                meta={"episode": "separation"}),
    # N+B pairings (energy/boundary axis)
    ActionTrace("reuse_cache",    frozenset({"energy", "boundary"}),
                meta={"episode": "reuse"}),
    ActionTrace("spend_energy",   frozenset({"energy", "agency"}),
                meta={"episode": "spend"}),
    # X+T pairings (admissibility/time axis)
    ActionTrace("reorder",        frozenset({"existence", "temporal"}),
                meta={"episode": "reorder"}),
    ActionTrace("resolve",        frozenset({"existence", "temporal", "boundary"}),
                meta={"episode": "resolve"}),
    # All-axis stimulation
    ActionTrace("full_assert",    frozenset({"existence","temporal","energy","boundary","agency"}),
                meta={"pulse": True, "episode": "assert"}),
    ActionTrace("full_commit",    frozenset({"existence","temporal","energy","boundary","agency"}),
                meta={"episode": "full_commit"}),
    # Single-axis probes (isolate individual constraint dynamics)
    ActionTrace("pure_agency",    frozenset({"agency"}),
                meta={"episode": "agency_probe"}),
    ActionTrace("pure_boundary",  frozenset({"boundary"}),
                meta={"episode": "boundary_probe"}),
]


# ---------------------------------------------------------------------------
# Variant action support
# ---------------------------------------------------------------------------

_AXIS_TO_IVM_LABEL = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}

def _ability_axes(ability_id: str) -> List[str]:
    """Extract axis letter from IDs like 'T:DEFER' or 'V:abcd' (V returns empty)."""
    if not isinstance(ability_id, str) or ":" not in ability_id:
        return []
    ax = ability_id.split(":", 1)[0].strip().upper()
    return [ax] if ax in _AXIS_TO_IVM_LABEL else []

def build_action_cycle_from_abilities(abilities: Dict[str, Any], max_variants: int = 8) -> List["ActionTrace"]:
    """
    Returns the base action cycle plus executable Variant actions (V:*).
    Variant actions are encoded as ActionTrace(name=<V:id>, constraints_used=<axes from expansion>).
    The chamber's ActionAbilityMapper will log the V:* in the trace, and lattice stimulus
    will be injected via the derived IVM constraint labels.

    This DOES NOT invent variants; it only uses those already present in abilities.
    """
    cycle = list(_BASEaction_cycle)

    # Collect variants
    v_ids = [aid for aid in abilities.keys() if isinstance(aid, str) and aid.startswith("V:")]
    if not v_ids:
        return cycle

    # Prefer most "mature" variants if stats exist
    def _variant_score(aid: str) -> float:
        a = abilities.get(aid, {})
        stats = a.get("stats", {}) if isinstance(a, dict) else {}
        return float(stats.get("count", 0.0)) + 0.5 * float(stats.get("net_gain_mean", 0.0))

    v_ids.sort(key=_variant_score, reverse=True)
    v_ids = v_ids[: max(1, int(max_variants))]

    for vid in v_ids:
        a = abilities.get(vid, {})
        expansion = []
        if isinstance(a, dict):
            expansion = a.get("expansion") or a.get("chain") or a.get("parents") or []
        if not isinstance(expansion, list):
            expansion = []

        labels = set()
        for step in expansion:
            for ax in _ability_axes(step):
                labels.add(_AXIS_TO_IVM_LABEL[ax])

        # If we couldn't infer labels, at least include a safe minimal label set
        if not labels:
            labels = {"temporal"}  # tick-local, low-risk

        cycle.append(ActionTrace(
            vid,
            frozenset(labels),
            meta={"episode": "variant", "variant_id": vid, "expansion_len": len(expansion)}
        ))

    return cycle


def _make_run_id() -> str:
    return datetime.datetime.now().strftime("chain_%Y-%m-%d_%H%M%S")


def _boot(out_dir: str, run_id: str, cfg_overrides: Optional[Dict[str, Any]] = None) -> tuple:
    """Boot the minimal stack needed to run the chamber."""
    print(f"  [BOOT] Initializing constraint universe...")
    contract = FoundationalContract()
    lattice  = IVMLattice(contract)

    # Seed the lattice with nodes across all 5 existence modes.
    # Without nodes: energy = 0, polarity = 0, no flux transitions.
    # PressureBridge reads all zeros → no pressure delta → nothing logs.
    from aurora_constraint_engine import ExistenceMode as _EM
    _seed_spec = [
        (_EM.REFERENCE,  "seed_ref",        8),
        (_EM.TRANSIENT,  "seed_transient",  10),
        (_EM.PERSISTENT, "seed_persistent", 14),
        (_EM.BOUNDED,    "seed_bounded",    10),
        (_EM.AGENTIC,    "seed_agentic",    8),
    ]
    _n_seeded = 0
    for _mode, _ptype, _count in _seed_spec:
        for _i in range(_count):
            try:
                lattice.admit_at_mode(
                    payload=f"{_ptype}_{_i}",
                    payload_type=_ptype,
                    mode=_mode,
                    scale=_i % 5,
                )
                _n_seeded += 1
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:run_chain.py:230",
                    exc=_aurora_boundary_exc,
                    context={"function": "_boot", "handler_line": 230, "source_file": "run_chain.py"},
                )
                pass
    print(f"  [BOOT] Lattice seeded with {_n_seeded} nodes across all 5 modes")

    os.makedirs(out_dir, exist_ok=True)

    # Use GenealogyConfig defaults — they are now calibrated for toroidal
    # IVM signal scale (relief ≈ 1e-4 to 1e-3 per tick).
    # Short-run tuned defaults: promote continuity + let stagnation regulator engage
    # in practical run lengths without waiting extremely long no-promotion spans.
    cfg_kwargs: Dict[str, Any] = {
        "K_MIN": 22,
        "STAGNATION_WINDOW": 260,
        "STAGNATION_HARD_WINDOW": 1200,
        "STAGNATION_BOOTSTRAP_RATIO": 0.55,
    }
    if isinstance(cfg_overrides, dict):
        for k, v in cfg_overrides.items():
            if v is not None:
                cfg_kwargs[str(k)] = v

    genealogy = ConstraintGenealogyLogger(
        run_id=run_id,
        config=GenealogyConfig(**cfg_kwargs),
        output_dir=out_dir,
    )
    restored_links = 0
    restored_pairs = 0
    try:
        links_path = os.path.join(out_dir, getattr(genealogy.cfg, "LINKS_FILE", "links.json"))
        if os.path.exists(links_path):
            import json
            from aurora_internal.constraint_genealogy import constraint_link_from_dict
            with open(links_path, "r", encoding="utf-8") as fh:
                raw_links = json.load(fh) or {}
            links_loaded = {}
            links_by_parents = {}
            max_created = 0
            for lid, rec in (raw_links or {}).items():
                if not isinstance(rec, dict):
                    continue
                link = constraint_link_from_dict(rec, fallback_id=str(lid))
                links_loaded[link.id] = link
                if len(link.parents) == 2:
                    links_by_parents[(link.parents[0], link.parents[1])] = link.id
                if link.created_at_tick > max_created:
                    max_created = int(link.created_at_tick)
            if links_loaded:
                genealogy.links = links_loaded
                genealogy._links_by_parents = links_by_parents
                genealogy.links_promoted = len(links_loaded)
                genealogy._last_promotion_tick = int(max_created)
                reg_link_ability = getattr(genealogy, "_register_link_ability", None)
                if callable(reg_link_ability):
                    for lnk in links_loaded.values():
                        try:
                            reg_link_ability(lnk)
                        except Exception as _aurora_boundary_exc:
                            _aurora_record_exception_from_locals(
                                locals(),
                                module=__name__,
                                operation="exception_handler:run_chain.py:300",
                                exc=_aurora_boundary_exc,
                                context={"function": "_boot", "handler_line": 300, "source_file": "run_chain.py"},
                            )
                            continue
                restored_links = len(links_loaded)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:run_chain.py:303",
            exc=_aurora_boundary_exc,
            context={"function": "_boot", "handler_line": 303, "source_file": "run_chain.py"},
        )
        restored_links = 0
    try:
        import json
        couplings_path = os.path.join(out_dir, getattr(genealogy.cfg, "COUPLINGS_FILE", "couplings.json"))
        if os.path.exists(couplings_path):
            with open(couplings_path, "r", encoding="utf-8") as fh:
                raw_couplings = json.load(fh) or {}
            roots = raw_couplings.get("roots", {}) if isinstance(raw_couplings, dict) else {}
            origins = raw_couplings.get("origin_counts", {}) if isinstance(raw_couplings, dict) else {}
            relations = raw_couplings.get("representation_relations", {}) if isinstance(raw_couplings, dict) else {}
            collisions = raw_couplings.get("representation_collisions", {}) if isinstance(raw_couplings, dict) else {}
            if isinstance(roots, dict):
                genealogy._coupling_roots = {str(k): dict(v) for k, v in roots.items() if isinstance(v, dict)}
            if isinstance(origins, dict):
                genealogy._coupling_origin_counts.update({str(k): int(v or 0) for k, v in origins.items()})
            if isinstance(relations, dict):
                genealogy._representation_relations = {str(k): dict(v) for k, v in relations.items() if isinstance(v, dict)}
            if isinstance(collisions, dict):
                genealogy._representation_collisions = {str(k): dict(v) for k, v in collisions.items() if isinstance(v, dict)}
            genealogy._coupling_events = int(raw_couplings.get("coupling_events", 0) or 0)
            genealogy._persistent_pressure_root_ema = float(raw_couplings.get("persistent_pressure_root_ema", 0.0) or 0.0)
            # Additive (schema v2): native representational inquiry and
            # experimentation runtime state (Sunni & Cael). Missing key on
            # older couplings.json files is a no-op -- logger already
            # initializes empty defaults for all of these.
            inquiry_runtime = raw_couplings.get("representation_inquiry_runtime", {}) if isinstance(raw_couplings, dict) else {}
            if isinstance(inquiry_runtime, dict):
                active_stages = inquiry_runtime.get("active_stages", {})
                if isinstance(active_stages, dict):
                    genealogy._representation_experiment_stages = {
                        str(k): dict(v) for k, v in active_stages.items() if isinstance(v, dict)
                    }
                history = inquiry_runtime.get("history", [])
                if isinstance(history, list):
                    genealogy._representation_experiment_history = [
                        dict(h) for h in history if isinstance(h, dict)
                    ]
                # FIX (Sunni & Cael, Section XXI): renamed from "consumer_ticks"
                # -- this stores per-consumer engagement CYCLE counts, not
                # genealogy tick_count. Read the old key too so a
                # pre-rename couplings.json still restores without loss.
                consumer_cycles = inquiry_runtime.get(
                    "consumer_cycles", inquiry_runtime.get("consumer_ticks", {})
                )
                if isinstance(consumer_cycles, dict):
                    genealogy._representation_inquiry_consumer_cycle = {
                        str(k): int(v or 0) for k, v in consumer_cycles.items()
                    }
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:run_chain.py:restore_couplings",
            exc=_aurora_boundary_exc,
            context={"function": "_boot", "source_file": "run_chain.py"},
        )
    if hasattr(genealogy, "restore_pair_stats"):
        try:
            restored_pairs = int(genealogy.restore_pair_stats() or 0)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:run_chain.py:308",
                exc=_aurora_boundary_exc,
                context={"function": "_boot", "handler_line": 308, "source_file": "run_chain.py"},
            )
            restored_pairs = 0
    chamber = EvolutionaryChamber(
        lattice=lattice,
        genealogy=genealogy,
        run_id=run_id,
        output_dir=out_dir,
    )
    printer = ChainSummaryPrinter(genealogy)

    action_cycle = build_action_cycle_from_abilities(genealogy.abilities)

    print(f"  [BOOT] Stack ready. Run ID: {run_id}")
    print(f"  [BOOT] Output directory: {os.path.abspath(out_dir)}")
    print(
        "  [BOOT] Genealogy tuning: "
        f"K_MIN={int(getattr(genealogy.cfg, 'K_MIN', 0))} "
        f"STAGNATION_WINDOW={int(getattr(genealogy.cfg, 'STAGNATION_WINDOW', 0))} "
        f"HARD_WINDOW={int(getattr(genealogy.cfg, 'STAGNATION_HARD_WINDOW', 0))} "
        f"BOOTSTRAP={float(getattr(genealogy.cfg, 'STAGNATION_BOOTSTRAP_RATIO', 0.0)):.2f}"
    )
    if restored_links > 0 or restored_pairs > 0:
        print(f"  [BOOT] Restored continuity: links={restored_links} pair_stats={restored_pairs}")
    return chamber, genealogy, printer, action_cycle
# ---------------------------------------------------------------------------
# MODES
# ---------------------------------------------------------------------------

def mode_burn(
    chamber,
    genealogy,
    printer,
    ticks: int,
    epoch: int,
    verbose: bool,
    action_cycle,
    target_links: Optional[int] = None,
    target_new_links: Optional[int] = None,
):
    """Run as fast as possible. Print summary at end."""
    print(f"\n[BURN] {ticks:,} ticks — {len(action_cycle)} action types cycling\n")
    t0 = time.time()
    start_links = int(len(getattr(genealogy, "links", {}) or {}))
    stop_reason = ""
    ran_ticks = 0
    for i in range(ticks):
        action = action_cycle[i % len(action_cycle)]
        chamber.tick(action=action)
        ran_ticks += 1
        current_links = int(len(getattr(genealogy, "links", {}) or {}))
        new_links = max(0, current_links - start_links)
        if target_links is not None and int(target_links) > 0 and current_links >= int(target_links):
            stop_reason = f"target links reached ({current_links}/{int(target_links)})"
            break
        if target_new_links is not None and int(target_new_links) > 0 and new_links >= int(target_new_links):
            stop_reason = f"target new links reached ({new_links}/{int(target_new_links)})"
            break

    elapsed = time.time() - t0
    genealogy.flush_files()
    # Crystallize stable links into new primitive variant abilities (V:*)
    try:
        from aurora_evolution_engine import crystallize_variants_from_links
        import os
        abilities_path = os.path.join(genealogy.output_dir, 'abilities.json')
        links_path = os.path.join(genealogy.output_dir, 'links.json')
        crystallize_variants_from_links(abilities_path, links_path, min_count=20, min_mean_net=0.0, max_new=50)
    except Exception as _e:
        if verbose:
            print(f'[WARN] Variant crystallization skipped: {_e}')
    _print_final(chamber, genealogy, printer, elapsed, ran_ticks, out_dir=genealogy.output_dir, stop_reason=stop_reason)


def mode_watch(
    chamber,
    genealogy,
    printer,
    ticks: int,
    epoch: int,
    verbose: bool,
    action_cycle,
    target_links: Optional[int] = None,
    target_new_links: Optional[int] = None,
):
    """Run with live epoch summaries."""
    print(f"\n[WATCH] {ticks:,} ticks, epoch every {epoch:,}\n")
    t0 = time.time()
    done = 0
    start_links = int(len(getattr(genealogy, "links", {}) or {}))
    stop_reason = ""
    while done < ticks:
        batch = min(epoch, ticks - done)
        hit_target = False
        for _ in range(batch):
            action = action_cycle[done % len(action_cycle)]
            chamber.tick(action=action)
            done += 1
            current_links = int(len(getattr(genealogy, "links", {}) or {}))
            new_links = max(0, current_links - start_links)
            if target_links is not None and int(target_links) > 0 and current_links >= int(target_links):
                stop_reason = f"target links reached ({current_links}/{int(target_links)})"
                hit_target = True
                break
            if target_new_links is not None and int(target_new_links) > 0 and new_links >= int(target_new_links):
                stop_reason = f"target new links reached ({new_links}/{int(target_new_links)})"
                hit_target = True
                break
        printer.print_epoch(chamber_tick=chamber.tick_count)
        genealogy.flush_files()
        if hit_target:
            break

    elapsed = time.time() - t0
    _print_final(chamber, genealogy, printer, elapsed, done, out_dir=genealogy.output_dir, stop_reason=stop_reason)


def mode_test(out_dir: str):
    """Run the genealogy module's built-in invariant checks."""
    print("\n[TEST] Running constraint_genealogy invariant checks...\n")
    # The self-test is in constraint_genealogy.__main__
    import subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(_PROJECT, "constraint_genealogy.py")],
        capture_output=False,
    )
    sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

def _print_final(
    chamber,
    genealogy,
    printer,
    elapsed: float,
    ticks: int,
    out_dir: Optional[str] = None,
    stop_reason: str = "",
):
    cr  = genealogy.chain_report()
    gs  = genealogy.summary()
    gov = gs["governor"]["gov"]

    print("\n" + "=" * 60)
    print("  EVOLUTIONARY CHAIN COMPLETE")
    print("=" * 60)
    print(f"  Ticks run            : {ticks:,}")
    print(f"  Wall time            : {elapsed:.1f}s  ({ticks/max(elapsed,0.001):.0f} ticks/s)")
    print(f"  Relief events logged : {gs['relief_events']:,}")
    print(f"  Links promoted (DAG) : {cr['total_links']}")
    print(f"  By dominant axis     : {cr['by_dominant_axis']}")
    print(f"  Depth distribution   : {cr['depth_distribution']}")
    print(f"  Outlet-push fraction : {cr['outlet_push_fraction']:.3f}")
    print(f"  Governor final state : {gov['state']}  ({gov['dilation']:.0f}x dilation)")
    print(f"  Fossil record        : events.jsonl")
    print(f"  Ability registry     : abilities.json")
    print(f"  Link DAG             : links.json")
    pstats = dict(cr.get("promotion_stats", {}) or {})
    if pstats:
        print(
            "  Promotion gates      : "
            f"kmin={int(pstats.get('reject_k_min_dynamic', 0) or 0)} "
            f"net={int(pstats.get('reject_net_min', 0) or 0)} "
            f"xrisk={int(pstats.get('reject_x_risk', 0) or 0)} "
            f"depth={int(pstats.get('reject_depth_cap', 0) or 0)} "
            f"near_pass={int(pstats.get('kmin_near_miss_pass', 0) or 0)} "
            f"promoted={int(pstats.get('promoted', 0) or 0)}"
        )
    print("=" * 60)
    if stop_reason:
        print(f"  Stop reason          : {stop_reason}")

    if cr['total_links'] == 0:
        print("\n  NOTE: No links promoted yet.")
        print(f"  Need {GenealogyConfig().K_MIN} repeated relief events per pair.")
        print("  Run more ticks or lower --k-min in GenealogyConfig.")
    else:
        print(f"\n  Top links by dominant axis:")
        for lnk in sorted(
            genealogy.links.values(),
            key=lambda l: sum(l.mean_relief.values()),
            reverse=True
        )[:5]:
            print(
                f"    {lnk.id}  depth={lnk.depth}  "
                f"axis={lnk.dominant_relief_axis}  "
                f"count={lnk.count}  "
                f"parents={lnk.parents}"
            )

    try:
        if _enqueue_recommendation is not None:
            total_links = int(cr.get('total_links', 0) or 0)
            outlet_push = float(cr.get('outlet_push_fraction', 0.0) or 0.0)
            priority = 0.20
            if total_links == 0:
                priority += 0.30
            if outlet_push < 0.10:
                priority += 0.20
            priority = max(0.0, min(1.0, priority))
            _enqueue_recommendation(
                output_dir=os.path.abspath("aurora_runtime_output"),
                source='run_chain._print_final',
                run_type='run_chain',
                title='Post-run chain recommendation',
                body=(
                    f"Chain run complete: links={total_links}, outlet_push_fraction={outlet_push:.3f}. "
                    f"Aurora can note this, discuss tuning, or dismiss."
                ),
                priority=float(priority),
                context={
                    'ticks': int(ticks),
                    'total_links': int(total_links),
                    'outlet_push_fraction': float(outlet_push),
                    'run_output_dir': os.path.abspath(out_dir or getattr(genealogy, 'output_dir', '')),
                },
            )
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:run_chain.py:527",
            exc=_aurora_boundary_exc,
            context={"function": "_print_final", "handler_line": 527, "source_file": "run_chain.py"},
        )
        pass

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Aurora Evolutionary Chain Runner — build the genealogy fossil record",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_chain.py                          # 10,000 ticks, burn mode
  python3 run_chain.py --ticks 50000            # longer burn
  python3 run_chain.py --mode watch --ticks 5000 --epoch 500
  python3 run_chain.py --mode test              # run invariant checks
  python3 run_chain.py --out my_fossil_dir      # custom output directory
        """
    )
    ap.add_argument("--mode",   choices=["burn", "watch", "test"], default="burn")
    ap.add_argument("--ticks",  type=int,  default=10_000,
                    help="Total ticks to run (default: 10000)")
    ap.add_argument("--epoch",  type=int,  default=1_000,
                    help="Ticks per watch-mode epoch (default: 1000)")
    ap.add_argument("--out",    type=str,  default="aurora_genealogy",
                    help="Output directory for fossil files (default: aurora_genealogy)")
    ap.add_argument("--quiet",  action="store_true")
    ap.add_argument("--k-min", type=int, default=None,
                    help="Override genealogy K_MIN (promotion evidence threshold)")
    ap.add_argument("--stagnation-window", type=int, default=None,
                    help="Override STAGNATION_WINDOW (pressure ramp horizon)")
    ap.add_argument("--stagnation-hard-window", type=int, default=None,
                    help="Override STAGNATION_HARD_WINDOW (deep relaxation horizon)")
    ap.add_argument("--stagnation-bootstrap-ratio", type=float, default=None,
                    help="Override STAGNATION_BOOTSTRAP_RATIO [0..1]")
    ap.add_argument("--target-links", type=int, default=None,
                    help="Stop early when total promoted links >= this count")
    ap.add_argument("--target-new-links", type=int, default=None,
                    help="Stop early when new links in this run >= this count")

    args = ap.parse_args()
    verbose = not args.quiet

    print("=" * 60)
    print("  AURORA EVOLUTIONARY CHAIN RUNNER")
    print("  Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("  Axes: X / T / N / B / A")
    print("=" * 60)

    if args.mode == "test":
        mode_test(args.out)
        return

    run_id = _make_run_id()
    cfg_overrides = {
        "K_MIN": args.k_min,
        "STAGNATION_WINDOW": args.stagnation_window,
        "STAGNATION_HARD_WINDOW": args.stagnation_hard_window,
        "STAGNATION_BOOTSTRAP_RATIO": args.stagnation_bootstrap_ratio,
    }
    chamber, genealogy, printer, action_cycle = _boot(args.out, run_id, cfg_overrides=cfg_overrides)

    if args.mode == "burn":
        mode_burn(
            chamber, genealogy, printer, args.ticks, args.epoch, verbose, action_cycle,
            target_links=args.target_links, target_new_links=args.target_new_links,
        )
    elif args.mode == "watch":
        mode_watch(
            chamber, genealogy, printer, args.ticks, args.epoch, verbose, action_cycle,
            target_links=args.target_links, target_new_links=args.target_new_links,
        )


if __name__ == "__main__":
    main()

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:run_chain.py:611",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 611, "source_file": "run_chain.py"},
    )
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:run_chain.py:616",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 616, "source_file": "run_chain.py"},
    )
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'run_chain'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'_ability_axes': {'ability_hits': 19,
                   'alignment_gap': 0.391,
                   'alignment_target_score': 0.972,
                   'best_coupling_signature': 'T^2*B^1',
                   'constraints': ['temporal'],
                   'contract_profile': {'accepts_payload': False,
                                        'async_callable': False,
                                        'callable': True,
                                        'class_target': False,
                                        'constraint_density': 1,
                                        'contract_mode': 'stateless',
                                        'doc_hint': "Extract axis letter from IDs like 'T:DEFER' "
                                                    "or 'V:abcd' (V returns empty).",
                                        'effect_density': 2,
                                        'kwonly_args': 0,
                                        'optional_args': 0,
                                        'required_args': 1,
                                        'return_hint': 'List',
                                        'signature_text': '(ability_id: str) -> List[str]',
                                        'stateful_owner': False,
                                        'target_kind': 'function',
                                        'varargs': False,
                                        'varkw': False},
                   'coupling_similarity': 1.0,
                   'cross_diversity_links': 2,
                   'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                   'effect_phrases': ['function growth reflected through run_chain',
                                      '_ability_axes changed downstream system pressure'],
                   'genealogy_pressure': 0.809108,
                   'inheritance_breach_count': 1,
                   'kind': 'reflection',
                   'link_hits': 36,
                   'module': 'run_chain',
                   'op_id': 'run_chain._ability_axes',
                   'origin_activity': 0,
                   'persistence_tax_factor': 1.955393,
                   'representation_score': 0.519331,
                   'rewrite_bias': 'generic',
                   'rewrite_feedback': {'acceptance_rate': 0.0,
                                        'accepted_count': 0,
                                        'adaptation_mode': 'conservative',
                                        'adoption_count': 0,
                                        'confidence': 0.36,
                                        'mean_mutation_score': 0.25,
                                        'rejected_count': 2,
                                        'rejection_rate': 1.0,
                                        'timing_credit': 0.0,
                                        'timing_penalty': 0.0,
                                        'trial_count': 2},
                   'rewrite_profile': 'generic',
                   'signature': 'T^2*B^1',
                   'surface_score': 0.581,
                   'sustainability_score': 0.405355,
                   'target_kind': 'function'},
 '_make_run_id': {'ability_hits': 19,
                  'alignment_gap': 0.391,
                  'alignment_target_score': 0.972,
                  'best_coupling_signature': 'T^2*B^1',
                  'constraints': ['temporal'],
                  'contract_profile': {'accepts_payload': False,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': False,
                                       'constraint_density': 1,
                                       'contract_mode': 'stateless',
                                       'doc_hint': '',
                                       'effect_density': 2,
                                       'kwonly_args': 0,
                                       'optional_args': 0,
                                       'required_args': 0,
                                       'return_hint': 'str',
                                       'signature_text': '() -> str',
                                       'stateful_owner': False,
                                       'target_kind': 'function',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 2,
                  'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                  'effect_phrases': ['function growth reflected through run_chain',
                                     '_make_run_id changed downstream system pressure'],
                  'genealogy_pressure': 0.809108,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 36,
                  'module': 'run_chain',
                  'op_id': 'run_chain._make_run_id',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.955393,
                  'representation_score': 0.519331,
                  'rewrite_bias': 'generic',
                  'rewrite_feedback': {'acceptance_rate': 0.0,
                                       'accepted_count': 0,
                                       'adaptation_mode': 'conservative',
                                       'adoption_count': 0,
                                       'confidence': 0.36,
                                       'mean_mutation_score': 0.25,
                                       'rejected_count': 2,
                                       'rejection_rate': 1.0,
                                       'timing_credit': 0.0,
                                       'timing_penalty': 0.0,
                                       'trial_count': 2},
                  'rewrite_profile': 'generic',
                  'signature': 'T^2*B^1',
                  'surface_score': 0.581,
                  'sustainability_score': 0.405355,
                  'target_kind': 'function'},
 '_print_final': {'ability_hits': 19,
                  'alignment_gap': 0.391,
                  'alignment_target_score': 0.972,
                  'best_coupling_signature': 'T^2*B^1',
                  'constraints': ['temporal'],
                  'contract_profile': {'accepts_payload': False,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': False,
                                       'constraint_density': 1,
                                       'contract_mode': 'stateless',
                                       'doc_hint': '',
                                       'effect_density': 2,
                                       'kwonly_args': 0,
                                       'optional_args': 2,
                                       'required_args': 5,
                                       'return_hint': 'generic_record',
                                       'signature_text': '(chamber, genealogy, printer, elapsed: '
                                                         'float, ticks: int, out_dir: '
                                                         'Optional[str] = None, stop_reason: str = '
                                                         "'')",
                                       'stateful_owner': False,
                                       'target_kind': 'function',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 2,
                  'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                  'effect_phrases': ['function growth reflected through run_chain',
                                     '_print_final changed downstream system pressure'],
                  'genealogy_pressure': 0.809108,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 36,
                  'module': 'run_chain',
                  'op_id': 'run_chain._print_final',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.955393,
                  'representation_score': 0.519331,
                  'rewrite_bias': 'generic',
                  'rewrite_feedback': {'acceptance_rate': 0.0,
                                       'accepted_count': 0,
                                       'adaptation_mode': 'conservative',
                                       'adoption_count': 0,
                                       'confidence': 0.36,
                                       'mean_mutation_score': 0.25,
                                       'rejected_count': 2,
                                       'rejection_rate': 1.0,
                                       'timing_credit': 0.0,
                                       'timing_penalty': 0.0,
                                       'trial_count': 2},
                  'rewrite_profile': 'generic',
                  'signature': 'T^2*B^1',
                  'surface_score': 0.581,
                  'sustainability_score': 0.405355,
                  'target_kind': 'function'},
 'main': {'ability_hits': 19,
          'alignment_gap': 0.391,
          'alignment_target_score': 0.972,
          'best_coupling_signature': 'T^2*B^1',
          'constraints': ['temporal'],
          'contract_profile': {'accepts_payload': False,
                               'async_callable': False,
                               'callable': True,
                               'class_target': False,
                               'constraint_density': 1,
                               'contract_mode': 'stateless',
                               'doc_hint': '',
                               'effect_density': 2,
                               'kwonly_args': 0,
                               'optional_args': 0,
                               'required_args': 0,
                               'return_hint': 'generic_record',
                               'signature_text': '()',
                               'stateful_owner': False,
                               'target_kind': 'function',
                               'varargs': False,
                               'varkw': False},
          'coupling_similarity': 1.0,
          'cross_diversity_links': 2,
          'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
          'effect_phrases': ['function growth reflected through run_chain',
                             'main changed downstream system pressure'],
          'genealogy_pressure': 0.809108,
          'inheritance_breach_count': 1,
          'kind': 'reflection',
          'link_hits': 36,
          'module': 'run_chain',
          'op_id': 'run_chain.main',
          'origin_activity': 0,
          'persistence_tax_factor': 1.955393,
          'representation_score': 0.519331,
          'rewrite_bias': 'generic',
          'rewrite_feedback': {'acceptance_rate': 0.0,
                               'accepted_count': 0,
                               'adaptation_mode': 'conservative',
                               'adoption_count': 0,
                               'confidence': 0.36,
                               'mean_mutation_score': 0.25,
                               'rejected_count': 2,
                               'rejection_rate': 1.0,
                               'timing_credit': 0.0,
                               'timing_penalty': 0.0,
                               'trial_count': 2},
          'rewrite_profile': 'generic',
          'signature': 'T^2*B^1',
          'surface_score': 0.581,
          'sustainability_score': 0.405355,
          'target_kind': 'function'},
 'mode_burn': {'ability_hits': 19,
               'alignment_gap': 0.391,
               'alignment_target_score': 0.972,
               'best_coupling_signature': 'T^2*B^1',
               'constraints': ['temporal'],
               'contract_profile': {'accepts_payload': False,
                                    'async_callable': False,
                                    'callable': True,
                                    'class_target': False,
                                    'constraint_density': 1,
                                    'contract_mode': 'stateless',
                                    'doc_hint': 'Run as fast as possible. Print summary at end.',
                                    'effect_density': 2,
                                    'kwonly_args': 0,
                                    'optional_args': 2,
                                    'required_args': 7,
                                    'return_hint': 'generic_record',
                                    'signature_text': '(chamber, genealogy, printer, ticks: int, '
                                                      'epoch: int, verbose: bool, action_cycle, '
                                                      'target_links: Optional[int] = None, '
                                                      'target_new_links: Optional[int] = None)',
                                    'stateful_owner': False,
                                    'target_kind': 'function',
                                    'varargs': False,
                                    'varkw': False},
               'coupling_similarity': 1.0,
               'cross_diversity_links': 2,
               'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
               'effect_phrases': ['function growth reflected through run_chain',
                                  'mode_burn changed downstream system pressure'],
               'genealogy_pressure': 0.809108,
               'inheritance_breach_count': 1,
               'kind': 'reflection',
               'link_hits': 36,
               'module': 'run_chain',
               'op_id': 'run_chain.mode_burn',
               'origin_activity': 0,
               'persistence_tax_factor': 1.955393,
               'representation_score': 0.519331,
               'rewrite_bias': 'generic',
               'rewrite_feedback': {'acceptance_rate': 0.0,
                                    'accepted_count': 0,
                                    'adaptation_mode': 'conservative',
                                    'adoption_count': 0,
                                    'confidence': 0.36,
                                    'mean_mutation_score': 0.25,
                                    'rejected_count': 2,
                                    'rejection_rate': 1.0,
                                    'timing_credit': 0.0,
                                    'timing_penalty': 0.0,
                                    'trial_count': 2},
               'rewrite_profile': 'generic',
               'signature': 'T^2*B^1',
               'surface_score': 0.581,
               'sustainability_score': 0.405355,
               'target_kind': 'function'},
 'mode_test': {'ability_hits': 19,
               'alignment_gap': 0.391,
               'alignment_target_score': 0.972,
               'best_coupling_signature': 'T^2*B^1',
               'constraints': ['temporal'],
               'contract_profile': {'accepts_payload': False,
                                    'async_callable': False,
                                    'callable': True,
                                    'class_target': False,
                                    'constraint_density': 1,
                                    'contract_mode': 'stateless',
                                    'doc_hint': "Run the genealogy module's built-in invariant "
                                                'checks.',
                                    'effect_density': 2,
                                    'kwonly_args': 0,
                                    'optional_args': 0,
                                    'required_args': 1,
                                    'return_hint': 'generic_record',
                                    'signature_text': '(out_dir: str)',
                                    'stateful_owner': False,
                                    'target_kind': 'function',
                                    'varargs': False,
                                    'varkw': False},
               'coupling_similarity': 1.0,
               'cross_diversity_links': 2,
               'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
               'effect_phrases': ['function growth reflected through run_chain',
                                  'mode_test changed downstream system pressure'],
               'genealogy_pressure': 0.809108,
               'inheritance_breach_count': 1,
               'kind': 'reflection',
               'link_hits': 36,
               'module': 'run_chain',
               'op_id': 'run_chain.mode_test',
               'origin_activity': 0,
               'persistence_tax_factor': 1.955393,
               'representation_score': 0.519331,
               'rewrite_bias': 'generic',
               'rewrite_feedback': {'acceptance_rate': 0.0,
                                    'accepted_count': 0,
                                    'adaptation_mode': 'conservative',
                                    'adoption_count': 0,
                                    'confidence': 0.36,
                                    'mean_mutation_score': 0.25,
                                    'rejected_count': 2,
                                    'rejection_rate': 1.0,
                                    'timing_credit': 0.0,
                                    'timing_penalty': 0.0,
                                    'trial_count': 2},
               'rewrite_profile': 'generic',
               'signature': 'T^2*B^1',
               'surface_score': 0.581,
               'sustainability_score': 0.405355,
               'target_kind': 'function'},
 'mode_watch': {'ability_hits': 19,
                'alignment_gap': 0.391,
                'alignment_target_score': 0.972,
                'best_coupling_signature': 'T^2*B^1',
                'constraints': ['temporal'],
                'contract_profile': {'accepts_payload': False,
                                     'async_callable': False,
                                     'callable': True,
                                     'class_target': False,
                                     'constraint_density': 1,
                                     'contract_mode': 'stateless',
                                     'doc_hint': 'Run with live epoch summaries.',
                                     'effect_density': 2,
                                     'kwonly_args': 0,
                                     'optional_args': 2,
                                     'required_args': 7,
                                     'return_hint': 'generic_record',
                                     'signature_text': '(chamber, genealogy, printer, ticks: int, '
                                                       'epoch: int, verbose: bool, action_cycle, '
                                                       'target_links: Optional[int] = None, '
                                                       'target_new_links: Optional[int] = None)',
                                     'stateful_owner': False,
                                     'target_kind': 'function',
                                     'varargs': False,
                                     'varkw': False},
                'coupling_similarity': 1.0,
                'cross_diversity_links': 2,
                'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                'effect_phrases': ['function growth reflected through run_chain',
                                   'mode_watch changed downstream system pressure'],
                'genealogy_pressure': 0.809108,
                'inheritance_breach_count': 1,
                'kind': 'reflection',
                'link_hits': 36,
                'module': 'run_chain',
                'op_id': 'run_chain.mode_watch',
                'origin_activity': 0,
                'persistence_tax_factor': 1.955393,
                'representation_score': 0.519331,
                'rewrite_bias': 'generic',
                'rewrite_feedback': {'acceptance_rate': 0.0,
                                     'accepted_count': 0,
                                     'adaptation_mode': 'conservative',
                                     'adoption_count': 0,
                                     'confidence': 0.36,
                                     'mean_mutation_score': 0.25,
                                     'rejected_count': 2,
                                     'rejection_rate': 1.0,
                                     'timing_credit': 0.0,
                                     'timing_penalty': 0.0,
                                     'trial_count': 2},
                'rewrite_profile': 'generic',
                'signature': 'T^2*B^1',
                'surface_score': 0.581,
                'sustainability_score': 0.405355,
                'target_kind': 'function'}}

from aurora_internal.aurora_evolution_hook import (
    assign_target as _aurora_evolution_hook_assign_target,
    get_target as _aurora_evolution_hook_get_target,
    bind_owner_attribute as _aurora_evolution_hook_bind_owner_attribute,
    target_strategy as _aurora_evolution_hook_target_strategy,
    target_feedback as _aurora_evolution_hook_target_feedback,
    store_reflection as _aurora_store_reflection,
    store_owner_state as _aurora_store_owner_state,
    apply_result_rewrite as _aurora_evolution_hook_apply_result_rewrite,
    make_override as _aurora_evolution_hook_make_override,
    make_latent_binding as _aurora_evolution_hook_make_latent_binding,
)


def _aurora_target_strategy(target_key):
    return _aurora_evolution_hook_target_strategy(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_target_feedback(target_key):
    return _aurora_evolution_hook_target_feedback(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_assign_target(chain, value):
    return _aurora_evolution_hook_assign_target(globals(), chain, value)


def _aurora_get_target(chain):
    return _aurora_evolution_hook_get_target(globals(), chain)


def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    return _aurora_evolution_hook_bind_owner_attribute(globals(), owner_chain, attr_name, value)


def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    return _aurora_evolution_hook_apply_result_rewrite(
        _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES, target_key, result, reflection, args, kwargs,
    )


def _aurora_make_override(export_name, target_key):
    return _aurora_evolution_hook_make_override(
        globals(), _AURORA_NATIVE_EVOLVED_ORIGINALS, _AURORA_NATIVE_EVOLVED_LAST,
        _aurora_native_evolved_engine, _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES,
        export_name, target_key,
    )


def _aurora_make_latent_binding(export_name, target_key):
    return _aurora_evolution_hook_make_latent_binding(
        globals(), _AURORA_NATIVE_EVOLVED_LAST, export_name, target_key,
    )


def ability_axes_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain._ability_axes', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_ability_axes')(payload=payload, **kwargs)

def make_run_id_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain._make_run_id', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_make_run_id')(payload=payload, **kwargs)

if _aurora_get_target(['_make_run_id']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['_make_run_id'] = _aurora_get_target(['_make_run_id'])
    _aurora_assign_target(['_make_run_id'], _aurora_make_override('make_run_id_evolved', '_make_run_id'))
    _AURORA_NATIVE_EVOLVED_LAST['_make_run_id'] = {'alignment_gap': 0.391, 'override_active': True}

def print_final_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain._print_final', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_print_final')(payload=payload, **kwargs)

def main_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain.main', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_main')(payload=payload, **kwargs)

if _aurora_get_target(['main']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['main'] = _aurora_get_target(['main'])
    _aurora_assign_target(['main'], _aurora_make_override('main_evolved', 'main'))
    _AURORA_NATIVE_EVOLVED_LAST['main'] = {'alignment_gap': 0.391, 'override_active': True}

def mode_burn_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain.mode_burn', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_mode_burn')(payload=payload, **kwargs)

if _aurora_get_target(['mode_burn']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['mode_burn'] = _aurora_get_target(['mode_burn'])
    _aurora_assign_target(['mode_burn'], _aurora_make_override('mode_burn_evolved', 'mode_burn'))
    _AURORA_NATIVE_EVOLVED_LAST['mode_burn'] = {'alignment_gap': 0.391, 'override_active': True}

def mode_test_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain.mode_test', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_mode_test')(payload=payload, **kwargs)

if _aurora_get_target(['mode_test']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['mode_test'] = _aurora_get_target(['mode_test'])
    _aurora_assign_target(['mode_test'], _aurora_make_override('mode_test_evolved', 'mode_test'))
    _AURORA_NATIVE_EVOLVED_LAST['mode_test'] = {'alignment_gap': 0.391, 'override_active': True}

def mode_watch_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'run_chain.mode_watch', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_run_chain_mode_watch')(payload=payload, **kwargs)

if _aurora_get_target(['mode_watch']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['mode_watch'] = _aurora_get_target(['mode_watch'])
    _aurora_assign_target(['mode_watch'], _aurora_make_override('mode_watch_evolved', 'mode_watch'))
    _AURORA_NATIVE_EVOLVED_LAST['mode_watch'] = {'alignment_gap': 0.391, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'run_chain._ability_axes': 'ability_axes_evolved',
 'run_chain._make_run_id': 'make_run_id_evolved',
 'run_chain._print_final': 'print_final_evolved',
 'run_chain.main': 'main_evolved',
 'run_chain.mode_burn': 'mode_burn_evolved',
 'run_chain.mode_test': 'mode_test_evolved',
 'run_chain.mode_watch': 'mode_watch_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'run_chain._make_run_id': {'export': 'make_run_id_evolved',
                            'mode': 'callable_override',
                            'target': '_make_run_id'},
 'run_chain.main': {'export': 'main_evolved', 'mode': 'callable_override', 'target': 'main'},
 'run_chain.mode_burn': {'export': 'mode_burn_evolved',
                         'mode': 'callable_override',
                         'target': 'mode_burn'},
 'run_chain.mode_test': {'export': 'mode_test_evolved',
                         'mode': 'callable_override',
                         'target': 'mode_test'},
 'run_chain.mode_watch': {'export': 'mode_watch_evolved',
                          'mode': 'callable_override',
                          'target': 'mode_watch'}}
# AURORA_EVOLVED_NATIVE_END
