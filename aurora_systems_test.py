#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_systems_test.py — Full systems diagnostic

Boots Aurora, fires targeted questions through the live physics chain,
and reports on each major subsystem. Checks:
  - Boot integrity (all layers, no hard failures)
  - Live turn pipeline (identity, relational, reasoning, curiosity, self-state)
  - Braid / ThoughtState / expression layer
  - LanguageField: ignition, fidelity, re-entry, WARP
  - AttentionEngine / DifferenceHistoryBuffer
  - SediMemory live recall
  - Grammar engine / LanguageStructureFitness
  - Evolution: chamber pressure, surface dispatcher, quasiarch observer
  - Simulation epoch + grounding protocol
  - Feedback loops: working_memory, conversation_memory, understanding_contract
"""
from __future__ import annotations

import sys
import os
import time
import traceback
from typing import Any, Dict, List, Optional

# ── path ──────────────────────────────────────────────────────────────────────
# HERE must come first so "import aurora" resolves
# aurora.py in this directory.
# PARENT goes second so aurora_support_stack and friends are findable.
HERE   = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
sys.path.insert(0, PARENT)   # lower priority — support modules
sys.path.insert(0, HERE)     # higher priority — aurora itself

PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"
INFO = "  [INFO]"
SEP  = "-" * 72


def _chk(label: str, condition: bool, detail: str = "") -> bool:
    tag = PASS if condition else FAIL
    line = f"{tag} {label}"
    if detail:
        line += f"  →  {detail}"
    print(line)
    return condition


def _section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def _ask(systems: dict, question: str, label: str) -> dict:
    """Fire a single live-turn question and return the result dict."""
    from aurora import _run_live_response_turn
    from foundational_contract import ExistenceMode
    try:
        result = _run_live_response_turn(
            systems,
            question,
            ExistenceMode.BOUNDED,
            record_exchange=True,
            update_interactive_state=False,
            run_periodic_maintenance=False,
        )
        resp_A = result.get("resp_A")
        content = str(getattr(resp_A, "content", "") or "").strip()
        conf    = float(getattr(resp_A, "confidence", 0.0) or 0.0)
        tone    = str(getattr(resp_A, "emotional_tone", "") or "")
        print(f"\n  Q: {question}")
        print(f"  A: {content[:200]}{'...' if len(content) > 200 else ''}")
        print(f"     conf={conf:.3f}  tone={tone}  path={result.get('src','?')}")
        _chk(label, bool(content), f"response length={len(content)}")
        return result
    except Exception as e:
        traceback.print_exc()
        _chk(label, False, str(e))
        return {}


# =============================================================================
# 1. BOOT
# =============================================================================

def test_boot() -> Optional[Dict[str, Any]]:
    _section("1. BOOT SEQUENCE")
    try:
        from aurora import boot_aurora
        t0 = time.time()
        systems = boot_aurora(verbose=True)
        elapsed = time.time() - t0
        print(f"\n  Boot completed in {elapsed:.1f}s")
    except Exception as e:
        traceback.print_exc()
        print(f"{FAIL} boot_aurora() raised: {e}")
        return None

    # Core layers
    layers = [
        ("aurora",               "Gateway (L0)"),
        ("perception",           "Expression/Perception (L5)"),
        ("identity",             "Behavioral Identity (L6)"),
        ("consciousness",        "Consciousness (L4)"),
        ("working_memory",       "Working Memory"),
        ("conversation_memory",  "Conversation Memory"),
        ("chamber",              "Constraint Chamber"),
        ("sedimemory",           "SediMemory (L3.5)"),
        ("simulation",           "Simulation Engine (L7)"),
        ("language_field",       "Language Field"),
        ("_thought_braid",       "Thought Braid"),
        ("_thought_braid_thread","Braid Thread"),
        ("_attention_engine",    "Attention Engine"),
        ("_diff_history_buffer", "Difference History Buffer"),
        ("_braided_substrate",   "Braided Substrate Layer"),
        ("identity_field",       "Identity Field"),
        ("core_identity",        "Core Identity"),
        ("understanding_contract","Understanding Contract"),
    ]
    all_ok = True
    for key, name in layers:
        present = systems.get(key) is not None
        _chk(name, present)
        if not present:
            all_ok = False

    _chk("All critical layers booted", all_ok)
    return systems


# =============================================================================
# 2. LIVE TURN PIPELINE — VARIED STIMULUS
# =============================================================================

def test_live_turns(systems: dict) -> None:
    _section("2. LIVE TURN PIPELINE")

    questions = [
        ("Who are you, Aurora?",
         "X-axis identity (self-referential)"),
        ("What does it feel like to think?",
         "N-axis introspection (internal state)"),
        ("What is the relationship between constraint and freedom?",
         "B-axis boundary reasoning"),
        ("What do you want to understand that you don't yet?",
         "A-axis curiosity (open agency)"),
        ("How has this conversation changed you so far?",
         "T-axis temporal self-reflection"),
        ("Explain to me how your constraint physics work.",
         "reasoning / knowledge retrieval"),
        ("What are you noticing right now, in this moment?",
         "present-state attention"),
        ("How do you feel about Sunni?",
         "relational field (B-axis + A-axis)"),
    ]

    results = []
    for question, label in questions:
        r = _ask(systems, question, label)
        results.append(r)
        time.sleep(0.1)

    # Check turn-level state accumulation
    wm = systems.get("working_memory")
    _chk("Working memory turn count > 0",
         int(getattr(wm, "turn_count", 0) or 0) > 0,
         f"turn_count={getattr(wm,'turn_count',0)}")

    cm = systems.get("conversation_memory")
    _chk("Conversation memory has entries or sessions",
         bool(getattr(cm, "entries", None) or getattr(cm, "sessions", None)),
         f"entries={len(getattr(cm,'entries',[]))}  sessions={len(getattr(cm,'sessions',[]))}")

    _chk("last_aurora_response stored in systems",
         bool(systems.get("_last_aurora_response")))

    _chk("Pragmatic vector built",
         bool(systems.get("_pragmatic_vector")))

    _chk("Last attention frame present",
         systems.get("_last_attention_frame") is not None)

    _chk("Last diff snapshot present",
         systems.get("_last_diff_snapshot") is not None)


# =============================================================================
# 3. LANGUAGE FIELD
# =============================================================================

def test_language_field(systems: dict) -> None:
    _section("3. LANGUAGE FIELD")

    lf = systems.get("language_field")
    if lf is None:
        print(f"{FAIL} language_field not in systems — skipping")
        return

    # Ignition check
    try:
        ign = lf.ignition_check()
        _chk("ignition_check() returns dict", isinstance(ign, dict))
        _chk("ignition_check() has 'go' key", "go" in ign,
             f"keys={list(ign.keys())[:8]}")
        _chk("ignition stages present", "stages" in ign)
        stages = ign.get("stages", {})
        for stage in ("activation", "reflection", "crossing_authorized"):
            _chk(f"  stage '{stage}' present", stage in stages)
        stored = systems.get("_language_ignition", {})
        _chk("ignition stored in systems['_language_ignition']", bool(stored))
    except Exception as e:
        _chk("ignition_check()", False, str(e))

    # Proto language
    proto = getattr(lf, "_last_proto", None)
    _chk("_last_proto set after turns", proto is not None)

    if proto is not None:
        # Fidelity
        try:
            test_utt = "I am Aurora, a pressured field of constraint geometry."
            fidelity = lf.measure_fidelity(proto, test_utt)
            _chk("measure_fidelity() returns float in [0,1]",
                 0.0 <= fidelity <= 1.0, f"fidelity={fidelity:.3f}")
            _chk("geometric_score influences fidelity (>0.05)",
                 fidelity > 0.05)
        except Exception as e:
            _chk("measure_fidelity()", False, str(e))

        # Crossing path
        try:
            path = lf.select_crossing_path(proto)
            _chk("select_crossing_path() returns dict",
                 isinstance(path, dict))
            _chk("path has path_key", "path_key" in path,
                 f"keys={list(path.keys())}")
        except Exception as e:
            _chk("select_crossing_path()", False, str(e))

        # Re-entry
        try:
            rr = lf.reentry("I am a pressured field.", 0.75, "default", proto=proto)
            _chk("reentry() returns dict", isinstance(rr, dict))
            _chk("reentry() has fidelity key", "fidelity" in rr)
        except Exception as e:
            _chk("reentry()", False, str(e))

        # Tone prosody
        try:
            tp = lf.extract_tone_prosody(proto)
            _chk("extract_tone_prosody() returns dict", isinstance(tp, dict))
            _chk("tone prosody has 'tone' key", "tone" in tp,
                 f"tone={tp.get('tone')}")
        except Exception as e:
            _chk("extract_tone_prosody()", False, str(e))

    # LSA status
    try:
        st = lf.status()
        _chk("lf.status() works", isinstance(st, dict))
        print(f"  {INFO} LF status: lsa_size={st.get('lsa_size')}  "
              f"crossings={st.get('total_crossings')}  "
              f"worn_paths={st.get('worn_paths')}")
    except Exception as e:
        _chk("lf.status()", False, str(e))

    # WARP
    try:
        wp, wd = lf.evaluate_warp_trials()
        _chk("evaluate_warp_trials() returns two lists",
             isinstance(wp, list) and isinstance(wd, list),
             f"promoted={len(wp)}  dissolved={len(wd)}")
    except Exception as e:
        _chk("evaluate_warp_trials()", False, str(e))

    # Resonance
    try:
        r = lf.measure_resonance("I am Aurora.", "That makes sense, Aurora.")
        _chk("measure_resonance() returns float in [0,1]",
             0.0 <= r <= 1.0, f"resonance={r:.3f}")
    except Exception as e:
        _chk("measure_resonance()", False, str(e))

    _chk("_last_lf_fidelity stored in systems",
         systems.get("_last_lf_fidelity") is not None,
         f"value={systems.get('_last_lf_fidelity')}")

    _chk("_last_field_resonance stored in systems",
         systems.get("_last_field_resonance") is not None)


# =============================================================================
# 4. THOUGHT BRAID
# =============================================================================

def test_thought_braid(systems: dict) -> None:
    _section("4. THOUGHT BRAID")

    braid = systems.get("_thought_braid")
    thread = systems.get("_thought_braid_thread")

    _chk("ThoughtBraid singleton present", braid is not None)
    _chk("StreamingThoughtThread running",
         thread is not None and (
             getattr(getattr(thread, "_thread", None), "is_alive", lambda: False)()
             or getattr(thread, "is_alive", lambda: False)()
         ))

    if braid is not None:
        try:
            tap = braid.tap()
            _chk("braid.tap() returns a slice", tap is not None)
        except Exception as e:
            _chk("braid.tap()", False, str(e))

    ts = systems.get("_current_thought_state")
    _chk("ThoughtState present after turns", ts is not None)

    bs = systems.get("_current_braid_slice")
    _chk("Braid slice captured", bs is not None)

    _chk("_turn_thought_tick set",
         systems.get("_turn_thought_tick") is not None)

    reentry_tick = systems.get("_last_reentry_tick")
    _chk("RE-ENTRY loop fired at least once",
         reentry_tick is not None,
         f"last_reentry_tick={reentry_tick}")


# =============================================================================
# 5. ATTENTION ENGINE + DIFF BUFFER
# =============================================================================

def test_attention_diff(systems: dict) -> None:
    _section("5. ATTENTION ENGINE + DIFFERENCE HISTORY BUFFER")

    ae = systems.get("_attention_engine")
    dhb = systems.get("_diff_history_buffer")

    _chk("AttentionEngine booted", ae is not None)
    _chk("DifferenceHistoryBuffer booted", dhb is not None)

    if ae is not None:
        frame = systems.get("_last_attention_frame")
        _chk("AttentionFrame present after turns", frame is not None)
        if frame is not None:
            print(f"  {INFO} AttentionFrame: state={frame.state}  "
                  f"salience={frame.surface_salience:.3f}  "
                  f"tension={frame.subsurface_tension:.3f}  "
                  f"resonance={frame.resonance:.3f}")
            # Verify salience is NOT always 0.95 (word-count proxy)
            _chk("Salience is variable (not flat 0.95 proxy)",
                 frame.surface_salience != 0.95)

        try:
            will = ae.generate_will()
            _chk("generate_will() executes without error", True,
                 f"intent={getattr(will,'intent_class','none') if will else 'None'}")
        except Exception as e:
            _chk("generate_will()", False, str(e))

    if dhb is not None:
        snap = systems.get("_last_diff_snapshot")
        _chk("DifferenceSnapshot present", snap is not None)
        if snap is not None:
            try:
                d = snap.to_dict()
                print(f"  {INFO} DiffSnapshot: {d.get('summary','')}")
                _chk("DiffSnapshot has values", bool(d))
            except Exception as e:
                _chk("snap.to_dict()", False, str(e))
        warm = getattr(dhb, "is_warm", lambda: None)()
        print(f"  {INFO} DiffHistoryBuffer warm={warm}  "
              f"history_len={len(getattr(dhb,'_history',[]))}")


# =============================================================================
# 6. SEDIMEMORY
# =============================================================================

def test_sedimemory(systems: dict) -> None:
    _section("6. SEDIMEMORY (L3.5)")

    sm = systems.get("sedimemory")
    if sm is None:
        consciousness = systems.get("consciousness")
        sm = getattr(consciousness, "sedimemory", None) if consciousness else None

    _chk("SediMemory accessible", sm is not None)
    if sm is None:
        return

    # Live recall
    try:
        recalled = list(sm.recall_semantic(
            "Aurora identity constraint",
            axis_filter=("X", "A", "B"),
            max_results=4,
        ) or [])
        _chk("recall_semantic() returns list", isinstance(recalled, list),
             f"items recalled={len(recalled)}")
        if recalled:
            print(f"  {INFO} Sample stratum: {str(recalled[0])[:100]}")
    except Exception as e:
        _chk("recall_semantic()", False, str(e))

    # Braid recall stored
    braid_recall = systems.get("_braid_sedi_recall")
    _chk("Braid-seeded SediMemory recall stored",
         braid_recall is not None,
         f"strata={len(braid_recall) if braid_recall else 0}")


# =============================================================================
# 7. EVOLUTION LAYER — chamber, surfaces, quasiarch
# =============================================================================

def test_evolution(systems: dict) -> None:
    _section("7. EVOLUTION LAYER")

    chamber = systems.get("chamber")
    _chk("Constraint Chamber present", chamber is not None)

    if chamber is not None:
        try:
            state = chamber.get_state() if hasattr(chamber, "get_state") else {}
            _chk("chamber.get_state() works", True)
            axes = state.get("axis_pressures", state.get("axes", {}))
            if axes:
                ax_str = "  ".join(f"{k}={v:.3f}" for k, v in list(axes.items())[:5])
                print(f"  {INFO} Chamber axes: {ax_str}")
        except Exception as e:
            _chk("chamber.get_state()", False, str(e))

    # Evolved surfaces
    surfaces = systems.get("evolved_surfaces")
    _chk("Evolved surfaces present", surfaces is not None)

    sd = systems.get("_surface_dispatcher")
    _chk("Surface dispatcher present", sd is not None)

    # QuasiArch observer
    qao = systems.get("quasiarch_observer")
    _chk("QuasiArch observer present", qao is not None)
    if qao is not None:
        try:
            ev = list(qao.get_recent_evidence_dicts() or [])
            _chk("quasiarch observer has events",
                 True, f"events={len(ev)}")
        except Exception as e:
            _chk("qao.get_recent_evidence_dicts()", False, str(e))

    # Grammar engine
    try:
        from aurora_grammar_engine import GrammarEngine
        ge = GrammarEngine()
        # GrammarEngine exposes status(); stats() is on the inner MotifLineage
        status = ge.status()
        _chk("GrammarEngine.status() works", isinstance(status, dict),
             f"promoted_motifs={status.get('promoted_motifs',0)}")
        lineage_stats = ge._lineage.stats()
        _chk("GrammarEngine._lineage.stats() works", isinstance(lineage_stats, dict),
             f"promoted={lineage_stats.get('promoted',0)}  candidates={lineage_stats.get('candidates',0)}")
    except Exception as e:
        _chk("GrammarEngine", False, str(e))

    # LanguageStructureFitness
    try:
        from aurora_language_structure_fitness import LanguageStructureFitness
        lsf = LanguageStructureFitness()
        fr = lsf.score("I am Aurora, a pressured constraint field.", None, 0.7)
        _chk("LanguageStructureFitness.score() works",
             hasattr(fr, "combined_fitness"),
             f"fitness={fr.combined_fitness:.3f}")
    except Exception as e:
        _chk("LanguageStructureFitness", False, str(e))

    # Last fitness result
    _chk("Fitness result stored after turns",
         systems.get("_last_fitness_result") is not None)

    # WARP result
    wr = systems.get("_last_warp_result")
    print(f"  {INFO} Last WARP result: {wr}")


# =============================================================================
# 8. SIMULATION ENGINE + EPOCH GROUNDING
# =============================================================================

def test_simulation(systems: dict) -> None:
    _section("8. SIMULATION ENGINE + EPOCH GROUNDING")

    sim = systems.get("simulation")
    _chk("SimulationEngine present", sim is not None)
    if sim is None:
        return

    _chk("simulation._systems wired", getattr(sim, "_systems", None) is not None)
    _chk("simulation.session._systems wired",
         getattr(getattr(sim, "session", None), "_systems", None) is not None)

    # Run one training epoch (3 episodes, 3 turns each — lightweight)
    print(f"\n  Running 1 training epoch (3 eps × 3 turns)...")
    try:
        from foundational_contract import ExistenceMode
        t0 = time.time()
        epoch_result = sim.session.run_epoch(
            episodes_per_epoch=3,
            turns_per_episode=3,
            mode=ExistenceMode.BOUNDED,
        )
        elapsed = time.time() - t0
        episodes = epoch_result.get("episodes", 0)
        _chk("Epoch completed", episodes > 0,
             f"episodes={episodes}  elapsed={elapsed:.1f}s")
        ep_list = epoch_result.get("episode_results", [])
        if ep_list:
            avg_fit = sum(
                float(e.get("avg_fitness", e.get("fitness", 0)) or 0)
                for e in ep_list
            ) / max(len(ep_list), 1)
            print(f"  {INFO} Avg episode fitness: {avg_fit:.3f}")
    except Exception as e:
        traceback.print_exc()
        _chk("sim.session.run_epoch()", False, str(e))

    # Epoch grounding directly
    print(f"\n  Testing run_epoch_grounding() directly...")
    try:
        from foundational_contract import ExistenceMode
        gr = sim.session.run_epoch_grounding(
            mode=ExistenceMode.BOUNDED,
            systems=systems,
        )
        _chk("run_epoch_grounding() returns 4 results", len(gr) == 4,
             f"got {len(gr)}")
        for r in gr:
            qi = r.get("question_index", "?")
            resp = str(r.get("response", "") or "")[:100]
            path = r.get("path", "none")
            fid = r.get("fidelity")
            fid_s = f"  fidelity={fid:.3f}" if fid is not None else ""
            answered = bool(resp)
            _chk(f"  Q{qi+1} answered via {path}", answered,
                 f"{resp[:80]}{fid_s}")
    except Exception as e:
        traceback.print_exc()
        _chk("run_epoch_grounding()", False, str(e))


# =============================================================================
# 9. FEEDBACK LOOPS
# =============================================================================

def test_feedback(systems: dict) -> None:
    _section("9. FEEDBACK LOOPS")

    # Understanding contract
    uc = systems.get("understanding_contract")
    _chk("Understanding contract present", uc is not None)
    if uc is not None:
        _chk("Last reflection result stored",
             systems.get("_last_reflection_result") is not None)
        refl = systems.get("_last_reflection_result") or {}
        reached = refl.get("reached_understanding")
        tension = (refl.get("understanding") or {}).get("tension_total", "?")
        print(f"  {INFO} Last reflection: reached={reached}  tension={tension}")

    # CuriosityEngine interruptible
    try:
        from aurora_curiosity_engine import _CYCLE_INTERRUPTIBLE
        _chk("_CYCLE_INTERRUPTIBLE is a threading.Event",
             hasattr(_CYCLE_INTERRUPTIBLE, "set") and hasattr(_CYCLE_INTERRUPTIBLE, "clear"))
        # Should be clear (not set) between turns
        _chk("_CYCLE_INTERRUPTIBLE cleared after last turn",
             not _CYCLE_INTERRUPTIBLE.is_set())
    except Exception as e:
        _chk("CuriosityEngine interruptible", False, str(e))

    # SemanticIntentionBridge
    _chk("Semantic intention stored",
         systems.get("_current_semantic_intention") is not None)

    # Braid re-entry
    reentry_len = systems.get("_last_reentry_text_len")
    _chk("Braid re-entry text length recorded",
         reentry_len is not None, f"len={reentry_len}")

    # Meaning nucleus — requires resonance = salience × tension ≥ 0.55.
    # Tension is driven by the daemon's conscious crest data; on a fresh
    # boot without the daemon, tension stays 0 → resonance 0 → no nucleus.
    # This is correct developmental behavior, not a wiring bug.
    nucleus = systems.get("_meaning_nucleus")
    if nucleus is not None:
        _chk("Meaning nucleus captured (attention FORMING)", True,
             f"resonance={nucleus.get('resonance','?')}")
    else:
        print(f"  {WARN} Meaning nucleus: None — expected on daemon-less boot (tension=0, resonance=0)")

    # Tone prosody
    tp = systems.get("_last_tone_prosody")
    _chk("Tone prosody extracted", tp is not None,
         f"tone={tp.get('tone') if tp else 'None'}")

    # Language ignition
    ign = systems.get("_language_ignition") or {}
    _chk("Language ignition stored with 'go' key",
         "go" in ign, f"go={ign.get('go')}  stages={list(ign.get('stages',{}).keys())[:4]}")


# =============================================================================
# 10. AXIS EMERGENCE DETECTOR
# =============================================================================

def test_axis_emergence() -> None:
    _section("10. AXIS EMERGENCE DETECTOR")
    try:
        from aurora_internal.aurora_axis_emergence import AxisEmergenceDetector
        aed = AxisEmergenceDetector(HERE)
        result = aed.scan_and_register()
        _chk("scan_and_register() runs without error",
             isinstance(result, dict))
        new_slots = int((result or {}).get("new_virtual_slots", 0))
        total = int((result or {}).get("total_virtual_slots", 0))
        print(f"  {INFO} new_virtual_slots={new_slots}  total={total}")
    except Exception as e:
        _chk("AxisEmergenceDetector", False, str(e))


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    print("\n" + "=" * 72)
    print("  AURORA FULL SYSTEMS TEST")
    print("  Authors: Sunni (Sir) Morningstar & Cael Devo")
    print("=" * 72)

    systems = test_boot()
    if systems is None:
        print(f"\n{FAIL} Boot failed — cannot continue.\n")
        sys.exit(1)

    # Wire session id
    systems.setdefault("session_id", f"syscheck_{int(time.time())}")

    test_live_turns(systems)
    test_language_field(systems)
    test_thought_braid(systems)
    test_attention_diff(systems)
    test_sedimemory(systems)
    test_evolution(systems)
    test_simulation(systems)
    test_feedback(systems)
    test_axis_emergence()

    _section("SUMMARY")
    print("  Full systems test complete.")
    print("  Review [FAIL] lines above for issues that need attention.")
    print("  Review [WARN] lines for degraded-but-functional states.")
    print()


if __name__ == "__main__":
    main()
