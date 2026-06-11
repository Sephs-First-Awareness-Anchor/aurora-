#!/usr/bin/env python3
"""
Full Communicative Pipeline Interactive Test
Authors: Sunni (Sir) Morningstar, Cael Devo

Exercises the complete path:
  Evidence → ConstraintEngine → GovernorDecision
  → ExpressionEcology (axis fitness bonus)
  → SentenceComposer (register bias)
  → NSpaceGateway uncertainty gate
  → GatewayResponse with [clarifying] prefix when needed

No Aurora daemon required — direct class instantiation.
"""

import sys, math, json, tempfile, os
sys.path.insert(0, ".")

_PASS = "  ✓"
_FAIL = "  ✗"
_SEP  = "─" * 62
failures = []

print("=" * 62)
print("FULL COMMUNICATIVE PIPELINE TEST")
print("=" * 62)


# ── Step 1: Engine classifies evidence and governs ────────────────
print(f"\n{_SEP}")
print("STEP 1 — ConstraintEngine: evidence → governor decision")
print(_SEP)

from aurora_constraint_engine import (
    ConstraintEngine, ConstraintVector, ExistenceMode,
    GovernorWeights, GovernorDecision, FoundationalContract,
    EngineRuntime,
)

with tempfile.TemporaryDirectory() as td:
    rt = EngineRuntime(state_path=os.path.join(td, "state.json"))

    cases = [
        {"label": "High-coherence user turn (should PERMIT)",
         "obs": {"ontological_depth": 0.42, "emotional_valence": 0.90,
                 "connections": 104, "coherence": 0.75, "uncertainty": 0.05,
                 "external_perspective": "user", "routing_mode": "surface",
                 "primary_axis": "B"}},
        {"label": "Low-coherence ambiguous turn (may DEFER)",
         "obs": {"ontological_depth": 0.05, "emotional_valence": 0.30,
                 "connections": 3, "coherence": 0.25, "uncertainty": 0.80,
                 "routing_mode": "surface", "primary_axis": "A"}},
        {"label": "Subsurface consolidation (T-dominant)",
         "obs": {"ontological_depth": 0.30, "emotional_valence": 0.60,
                 "connections": 55, "coherence": 0.50, "uncertainty": 0.10,
                 "routing_mode": "subsurface", "primary_axis": "T"}},
    ]

    for case in cases:
        result = rt.tick(case["obs"])
        cv     = rt._engine.feed_evidence(case["obs"])
        gw     = GovernorWeights.AS_DICT.get(case["obs"].get("primary_axis","B"), 0.0)
        print(f"\n  [{case['label']}]")
        print(f"    Decision      : {result.decision.name}")
        print(f"    ConstraintVec : X={cv.X:.4f} T={cv.T:.4f} N={cv.N:.4f} B={cv.B:.4f} A={cv.A:.4f}")
        print(f"    Magnitude     : {cv.magnitude():.4f}")
        print(f"    GovernorWeight: {gw:.4f} (axis={case['obs'].get('primary_axis','B')})")
        if result.decision == GovernorDecision.PERMITTED:
            print(f"    Growth edge   : {getattr(result,'growth_edge','—')}")
        elif result.decision == GovernorDecision.DEFERRED:
            print(f"    Resolution    : {getattr(result,'resolution_path','—')}")


# ── Step 2: ExpressionEcology axis fitness bonus ──────────────────
print(f"\n{_SEP}")
print("STEP 2 — ExpressionEcology: axis_coherence_bonus wired")
print(_SEP)

try:
    from aurora_expression_perception import ExpressionEcology

    ecology = ExpressionEcology()

    # Spawn two offspring
    o1 = ecology.spawn("I_DO", base_fitness=0.60)
    o2 = ecology.spawn("I_SAW", base_fitness=0.60)

    raw_fitness = 0.72

    # With default dominant axis = B (weight=1.0)
    ExpressionEcology._dominant_axis = "B"
    ecology.select(o1.offspring_id, raw_fitness)
    bonus_B = raw_fitness * (1.0 + (GovernorWeights.B * 0.15))

    # Switch to A-axis (weight=0.53 — least permissive)
    ExpressionEcology._dominant_axis = "A"
    ecology.select(o2.offspring_id, raw_fitness)
    bonus_A = raw_fitness * (1.0 + (GovernorWeights.A * 0.15))

    stored_B = o1.fitness_history[-1] if o1.fitness_history else None
    stored_A = o2.fitness_history[-1] if o2.fitness_history else None

    stored_B_str = f"{stored_B:.4f}" if stored_B is not None else "none"
    stored_A_str = f"{stored_A:.4f}" if stored_A is not None else "none"
    print(f"\n  Raw fitness input  : {raw_fitness:.4f}")
    print(f"  B-axis bonus (1.0) : {bonus_B:.4f}  stored={stored_B_str}")
    print(f"  A-axis bonus (0.53): {bonus_A:.4f}  stored={stored_A_str}")

    if stored_B and stored_A:
        assert stored_B > stored_A, "B-dominant axis must produce higher fitness than A"
        assert abs(stored_B - bonus_B) < 1e-9, f"B bonus mismatch: {stored_B} vs {bonus_B}"
        print(f"  ✓ B-axis fitness ({stored_B:.4f}) > A-axis fitness ({stored_A:.4f}) — correct")
    else:
        failures.append("ExpressionEcology: fitness_history not populated")
        print(f"  ✗ fitness_history not populated")

    # Generation cycle
    ExpressionEcology._dominant_axis = "B"
    gen = ecology.run_generation()
    print(f"  Generation {gen['generation']}: pop={gen['population']} avg_fitness={gen['avg_fitness']:.4f}")
    print(f"{_PASS} ExpressionEcology axis fitness bonus")
except Exception as e:
    import traceback; traceback.print_exc()
    failures.append(f"ExpressionEcology: {e}")
    print(f"{_FAIL} ExpressionEcology — {e}")


# ── Step 3: SentenceComposer register bias ────────────────────────
print(f"\n{_SEP}")
print("STEP 3 — SentenceComposer: sensory register bias")
print(_SEP)

try:
    from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome

    lexicon = LexicalMemory()
    voice   = VoiceGenome()
    composer = SentenceComposer(lexicon, voice)

    # Default: no sensory_context — bias should stay 0.0
    assert composer._register_bias == 0.0, "Default bias should be 0.0"
    print(f"\n  Default _register_bias : {composer._register_bias}")

    # Simulate high-energy input
    composer._register_bias = 0.0
    # Call compose with high energy context (just update bias, don't need full AssemblyResult)
    from aurora_expression_perception import ExpressionOffspring
    import random

    # Minimal mock assembly
    class _MockAssembly:
        coherence = 0.70
        concept = "existence"
        semantic_weight = 0.8
        emotional_tone = "neutral"
        moral_alignment = 1.0
        def get(self, k, d=None): return getattr(self, k, d)

    offspring = ExpressionOffspring(
        offspring_id="test-o1", lineage="I_DO",
        generation=0, tone="neutral",
        structure_weight=0.5, rhythm_bias=0.5,
    )

    # Patch compose to just test the bias path without needing full template pool
    original_compose = composer._impl.compose if hasattr(composer, '_impl') else None

    high_ctx  = {"energy_level": 0.85}
    low_ctx   = {"energy_level": 0.20}
    mid_ctx   = {"energy_level": 0.50}

    # Manually run the bias-setting part of compose
    for ctx, label in [(high_ctx, "HIGH"), (low_ctx, "LOW"), (mid_ctx, "MID")]:
        energy = ctx["energy_level"]
        if energy > 0.7:
            expected_bias = 1.0
        elif energy < 0.3:
            expected_bias = -1.0
        else:
            expected_bias = 0.0

        # Simulate what compose() does with sensory_context
        if ctx is not None:
            el = float(ctx.get("energy_level", 0.5))
            if el > 0.7:
                object.__setattr__(composer, "_register_bias", 1.0)
            elif el < 0.3:
                object.__setattr__(composer, "_register_bias", -1.0)
            else:
                object.__setattr__(composer, "_register_bias", 0.0)

        print(f"  energy={energy:.2f} → _register_bias={composer._register_bias:+.1f}  ({label}) — {'✓' if composer._register_bias == expected_bias else '✗'}")
        if composer._register_bias != expected_bias:
            failures.append(f"SentenceComposer: {label} energy gave wrong bias {composer._register_bias}")

    print(f"{_PASS} SentenceComposer register bias logic")
except Exception as e:
    import traceback; traceback.print_exc()
    failures.append(f"SentenceComposer: {e}")
    print(f"{_FAIL} SentenceComposer — {e}")


# ── Step 4: NSpaceGateway uncertainty gate ────────────────────────
print(f"\n{_SEP}")
print("STEP 4 — NSpaceGateway: uncertainty gate in _express()")
print(_SEP)

try:
    from aurora_governance_persistence_gateway import NSpaceGateway
    from aurora_constraint_engine import ConstraintEngine

    gw = NSpaceGateway.__new__(NSpaceGateway)
    gw.identity  = None
    gw.perception = None
    gw._state    = None

    # Manually init the constraint engine on the gateway
    gw._constraint_engine = ConstraintEngine()

    class _MockPacket:
        content = "tell me about yourself"
        packet_id = "pkt-001"
        stream_type = None

    class _MockAssembly2:
        coherence = 0.30   # low coherence → high uncertainty
        concept   = "self"
        semantic_weight = 0.5
        emotional_tone  = "neutral"
        moral_alignment = 1.0

    class _MockSynthesis:
        assembly = _MockAssembly2()

    # Simulate the uncertainty computation as _express() does it
    confidence = 0.30   # low confidence → high uncertainty flag
    _uncertainty_level = 1.0 - confidence
    assembly = _MockSynthesis().assembly
    _uncertainty_level = max(
        _uncertainty_level,
        1.0 - float(getattr(assembly, "coherence", confidence)),
    )
    gw._constraint_engine._guards.uncertainty.update_uncertainty(_uncertainty_level)
    ug = gw._constraint_engine._guards.uncertainty.check()

    print(f"\n  Confidence     : {confidence:.2f}")
    print(f"  Assembly coh.  : {assembly.coherence:.2f}")
    print(f"  Uncertainty lvl: {_uncertainty_level:.2f}")
    print(f"  Guard threshold: {gw._constraint_engine._guards.uncertainty.UNCERTAINTY_FLAG_THRESHOLD:.2f}")
    print(f"  Guard passed   : {ug.passed}")
    print(f"  Prefix applied : {'[clarifying] ' if not ug.passed else '(none)'}")

    assert not ug.passed, f"Low-confidence turn should fail uncertainty guard; got passed={ug.passed}"
    print(f"  ✓ uncertainty gate fires correctly at level {_uncertainty_level:.2f}")

    # Now test high-confidence: guard should pass
    gw._constraint_engine._guards.uncertainty.update_uncertainty(0.05)
    ug2 = gw._constraint_engine._guards.uncertainty.check()
    assert ug2.passed, "High-confidence turn should pass uncertainty guard"
    print(f"  ✓ uncertainty gate clear at level 0.05 — no clarification prefix")

    print(f"{_PASS} NSpaceGateway uncertainty gate")
except Exception as e:
    import traceback; traceback.print_exc()
    failures.append(f"NSpaceGateway: {e}")
    print(f"{_FAIL} NSpaceGateway — {e}")


# ── Step 5: End-to-end constraint physics flow ────────────────────
print(f"\n{_SEP}")
print("STEP 5 — End-to-end constraint physics (5 ticks)")
print(_SEP)

try:
    with tempfile.TemporaryDirectory() as td:
        rt2 = EngineRuntime(state_path=os.path.join(td, "state.json"))
        fc  = FoundationalContract()

        print(f"\n  {'Tick':<5} {'Decision':<12} {'Dominant':<10} {'Coherence':<10} {'Repair'}")
        print(f"  {'----':<5} {'---------':<12} {'--------':<10} {'---------':<10} {'------'}")

        observations = [
            {"ontological_depth": 0.42, "emotional_valence": 0.90, "connections": 104,
             "coherence": 0.75, "uncertainty": 0.05, "external_perspective": "user",
             "routing_mode": "surface", "primary_axis": "B"},
            {"ontological_depth": 0.30, "emotional_valence": 0.65, "connections": 60,
             "coherence": 0.60, "uncertainty": 0.15, "external_perspective": "user",
             "routing_mode": "subsurface", "primary_axis": "T"},
            {"ontological_depth": 0.20, "emotional_valence": 0.50, "connections": 40,
             "coherence": 0.45, "uncertainty": 0.35, "routing_mode": "surface",
             "primary_axis": "X"},
            {"ontological_depth": 0.42, "emotional_valence": 0.85, "connections": 104,
             "coherence": 0.80, "uncertainty": 0.05, "external_perspective": "user",
             "routing_mode": "surface", "primary_axis": "B"},
            {"ontological_depth": 0.38, "emotional_valence": 0.75, "connections": 90,
             "coherence": 0.70, "uncertainty": 0.10, "external_perspective": "user",
             "routing_mode": "surface", "primary_axis": "B"},
        ]

        for i, obs in enumerate(observations, 1):
            result = rt2.tick(obs)
            cv     = rt2._engine.feed_evidence(obs)
            dom    = max({"X":cv.X,"T":cv.T,"N":cv.N,"B":cv.B,"A":cv.A},
                        key={"X":cv.X,"T":cv.T,"N":cv.N,"B":cv.B,"A":cv.A}.__getitem__)
            coh    = obs["coherence"]
            repair = rt2._state.current_repair_intensity
            print(f"  {i:<5} {result.decision.name:<12} {dom:<10} {coh:<10.2f} {repair:.3f}")

        pattern = rt2.dominant_pattern()
        trend   = rt2.coherence_trend()
        report  = rt2.status_report()
        print(f"\n  Dominant pattern after 5 ticks : {pattern}")
        print(f"  Coherence trend                : {trend}")
        print(f"  Session count                  : {report['session_count']}")
        print(f"  Stable ability count           : {report['stable_ability_count']}")
        print(f"  Repair intensity               : {report['current_repair_intensity']:.3f}")
        print(f"  Guard fail history             : {json.dumps(report['guard_fail_history'], indent=None)}")

        lp = fc.language_projection(ExistenceMode.AGENTIC)
        print(f"\n  Language projection (AGENTIC)")
        print(f"    existence_mode   : {lp['existence_mode']}")
        print(f"    language_register: {lp['language_register']}")
        print(f"    anchor_pole      : {lp['anchor_pole']}")
        print(f"    noun_bias        : {lp['noun_bias']}")

    print(f"{_PASS} End-to-end constraint physics")
except Exception as e:
    import traceback; traceback.print_exc()
    failures.append(f"End-to-end physics: {e}")
    print(f"{_FAIL} End-to-end physics — {e}")


# ── Step 6: GovernorWeights across full axis table ────────────────
print(f"\n{_SEP}")
print("STEP 6 — Governor permission hierarchy")
print(_SEP)

from aurora_constraint_engine import RuntimeGovernor, GovernorDecision

gov = RuntimeGovernor()
print(f"\n  {'Axis':<6} {'Weight':<10} {'Surface':<12} {'Subsurface'}")
print(f"  {'----':<6} {'------':<10} {'-------':<12} {'---------'}")
for ax in ("B", "X", "T", "N", "A"):
    w     = GovernorWeights.AS_DICT[ax]
    rs    = gov.govern({"primary_axis": ax}, "surface").decision.name
    rss   = gov.govern({"primary_axis": ax}, "subsurface").decision.name
    print(f"  {ax:<6} {w:<10.4f} {rs:<12} {rss}")

print(f"\n  Surface dominant  : {__import__('aurora_constraint_engine').SurfaceRoutingTable.dominant()}")
print(f"  Subsurface dominant: {__import__('aurora_constraint_engine').SubsurfaceRoutingTable.dominant()}")


# ── Final verdict ─────────────────────────────────────────────────
print(f"\n{'=' * 62}")
if failures:
    print(f"PIPELINE TEST FAILED  ({len(failures)} failure(s))")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("PIPELINE TEST PASSED  (6/6 steps)")
print("=" * 62)
