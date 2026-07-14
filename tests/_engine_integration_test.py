#!/usr/bin/env python3
"""
aurora_constraint_engine — live stack integration test
Verifies engine-native types flow correctly through the real modules,
not just through the self-test harness.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import sys, math
sys.path.insert(0, ".")

if __name__ == "__main__":

    _PASS = "  ✓"
    _FAIL = "  ✗"
    failures = []

    print("=" * 62)
    print("CONSTRAINT ENGINE — STACK INTEGRATION TEST")
    print("=" * 62)


    # ── 1. Engine types are concrete and usable ──────────────────────
    print("\n[1] Engine core types import and construct correctly...")
    try:
        from aurora_constraint_engine import (
            ConstraintVector, ExistenceMode, GovernorWeights,
            FoundationalContract, ManifoldViolation,
            ConstraintEngine, EngineRuntime, GovernorDecision,
        )
        cv = ConstraintVector(X=0.9922, T=0.682, N=0.6199, B=1.0, A=0.53)
        assert cv.magnitude() > 0
        assert cv.span_check() == {"X","T","N","B","A"}
        try:
            ConstraintVector(X=0.0, T=1.0, N=1.0, B=1.0, A=1.0)
            failures.append("Engine types: X=0 should raise ManifoldViolation")
        except ManifoldViolation:
            pass
        fc = FoundationalContract()
        proj = fc.language_projection(ExistenceMode.AGENTIC)
        assert proj["existence_mode"] == "AGENTIC"
        assert proj["anchor_pole"] == "aurora"
        assert "dominant_channel" not in proj   # engine does not inject this — callers do
        print(f"{_PASS} Engine core types")
    except Exception as e:
        failures.append(f"Engine types: {e}")
        print(f"{_FAIL} Engine types — {e}")


    # ── 2. foundational_contract.py — engine methods fire correctly ──
    print("\n[2] foundational_contract.FoundationalContract — engine methods...")
    try:
        from foundational_contract import FoundationalContract as FC
        fc = FC()
        cp = fc.constraint_profile()
        # Must return a ConstraintVector
        assert isinstance(cp, ConstraintVector), \
            f"constraint_profile() must return ConstraintVector; got {type(cp)}"
        assert cp.X > 0, "X invariant violated"
        rr = fc.runtime_regime()
        assert "dominant_axis" in rr, f"runtime_regime missing dominant_axis: {rr}"
        assert rr["dominant_axis"] in ("X","T","N","B","A")
        assert "governor_weight" in rr
        lp = fc.language_projection()
        assert "existence_mode" in lp
        assert "language_register" in lp
        ur = fc.universal_representation()
        assert "constraint_vector" in ur, f"universal_representation keys: {list(ur.keys())}"
        assert "runtime_regime" in ur
        print(f"{_PASS} foundational_contract.FoundationalContract")
    except Exception as e:
        failures.append(f"foundational_contract: {e}")
        print(f"{_FAIL} foundational_contract — {e}")


    # ── 3. aurora_constraint_manifold — re-exports engine types ──────
    print("\n[3] aurora_constraint_manifold — re-exports ConstraintVector...")
    try:
        from aurora_constraint_manifold import ConstraintVector as CV2
        assert CV2 is ConstraintVector, \
            "aurora_constraint_manifold must re-export the engine's ConstraintVector"
        print(f"{_PASS} aurora_constraint_manifold re-export")
    except Exception as e:
        failures.append(f"aurora_constraint_manifold: {e}")
        print(f"{_FAIL} aurora_constraint_manifold — {e}")


    # ── 4. aurora_constraint_manifold_router — _RouterProfile live ───
    print("\n[4] aurora_constraint_manifold_router — _RouterProfile + routing...")
    try:
        import aurora_constraint_manifold_router as router

        # Confirm _RouterProfile is the live type (not ConstraintProfile)
        assert hasattr(router, "_RouterProfile"), "Missing _RouterProfile"
        assert not hasattr(router, "ConstraintProfile"), \
            "ConstraintProfile should not be exported from the router"

        # Build a SlotCoord — 5 fields only; slot_id/is_diagonal/is_resonant are properties
        sc = router.SlotCoord("X", "T", "POLARITY", "N", "COST")
        prof = router._coord_profile(sc, evolution_grade=0.75, phase_state="stable")
        assert isinstance(prof, router._RouterProfile), \
            f"_coord_profile must return _RouterProfile; got {type(prof)}"
        assert prof.phase_state == "stable"         # string, not enum
        assert prof.lineage_pressure == 0.75
        assert 0.0 <= prof.X <= 1.0

        # weighted_signature returns a string of axis characters
        sig = prof.weighted_signature()
        assert isinstance(sig, str) and len(sig) >= 1
        assert all(c in "XTNBA" for c in sig if c.isupper())

        # profile_similarity is [0,1]
        sim = prof.profile_similarity(router._RouterProfile(X=0.2,T=0.2,N=0.2,B=0.2,A=0.2))
        assert 0.0 <= sim <= 1.0, f"profile_similarity out of range: {sim}"

        # pressure_compatibility returns [0,1]
        compat = prof.pressure_compatibility({"X":0.3,"T":0.2,"N":0.2,"B":0.2,"A":0.1})
        assert 0.0 <= compat <= 1.0

        # lineage_affinity is [0,1]
        aff = prof.lineage_affinity("XTNBA")
        assert 0.0 <= aff <= 1.0

        # _resolve_source_profile accepts dict, _RouterProfile, or None
        r = router.ManifoldRouter(index=router.RouteIndex({}))
        sig_in = router.RouteSignal(
            source=sc, intent="integration_test", strength=0.75,
            source_profile={"X": 0.4, "T": 0.2, "N": 0.1, "B": 0.2, "A": 0.1},
        )
        resolved = r._resolve_source_profile(sig_in)
        assert isinstance(resolved, router._RouterProfile), \
            f"_resolve_source_profile(dict) must return _RouterProfile; got {type(resolved)}"

        # None source_profile falls back to coord-derived
        sig_none = router.RouteSignal(source=sc, intent="test", strength=0.5)
        resolved2 = r._resolve_source_profile(sig_none)
        assert isinstance(resolved2, router._RouterProfile)

        print(f"{_PASS} aurora_constraint_manifold_router")
    except Exception as e:
        failures.append(f"aurora_constraint_manifold_router: {e}")
        print(f"{_FAIL} aurora_constraint_manifold_router — {e}")


    # ── 5. aurora_runtime_constraint_governor — engine-native methods ─
    print("\n[5] aurora_runtime_constraint_governor — constraint methods...")
    try:
        from aurora_internal.aurora_runtime_constraint_governor import RuntimeConstraintGovernor
        gov = RuntimeConstraintGovernor()
        cp = gov.constraint_profile()
        assert isinstance(cp, ConstraintVector), \
            f"RuntimeConstraintGovernor.constraint_profile() must return ConstraintVector; got {type(cp)}"
        assert cp.X > 0
        rr = gov.runtime_regime()
        assert "dominant_axis" in rr
        lp = gov.language_projection()
        assert "existence_mode" in lp
        ur = gov.universal_representation()
        assert "constraint_vector" in ur, f"universal_representation keys: {list(ur.keys())}"
        # Internal _constraint_signature returns a string of axis chars
        sig = gov._constraint_signature({"X": 0.5, "T": 0.3, "N": 0.1, "B": 0.05, "A": 0.05})
        assert isinstance(sig, str) and len(sig) >= 1
        assert all(c in "XTNBA" for c in sig)
        print(f"{_PASS} aurora_runtime_constraint_governor")
    except Exception as e:
        failures.append(f"aurora_runtime_constraint_governor: {e}")
        print(f"{_FAIL} aurora_runtime_constraint_governor — {e}")


    # ── 6. aurora_conversation_episode_compiler — engine call sites ───
    print("\n[6] aurora_conversation_episode_compiler — engine derivations...")
    try:
        import aurora_internal.aurora_conversation_episode_compiler as _cec
        from aurora_internal.aurora_conversation_episode_compiler import (
            ConversationEpisodeCompiler, DreamEpisodePack, _derive_signature,
        )
        # _derive_signature must return axis-char string using engine axes
        sig = _derive_signature({"X": 0.5, "T": 0.3, "N": 0.1, "B": 0.05, "A": 0.05})
        assert isinstance(sig, str) and len(sig) >= 1, f"bad sig: {sig!r}"
        assert all(c in "XTNBA" for c in sig if c.isupper()), f"sig has non-axis chars: {sig}"

        # DreamEpisodePack carries engine-derived fields — construct it properly
        lp_dict = dict(FoundationalContract().language_projection(ExistenceMode.AGENTIC))
        pack = DreamEpisodePack(
            episode_id="test-ep-001",
            conversation_ids=["conv-1"],
            design_mode="balanced",
            constraint_signature=sig,
            runtime_regime={"dominant_axis": "X", "governor_weight": GovernorWeights.X},
            language_projection=lp_dict,
        )
        d = pack.to_dict()
        assert "constraint_signature" in d
        assert "runtime_regime" in d
        assert "language_projection" in d
        assert d["language_projection"]["existence_mode"] == "AGENTIC"

        # _FC in compiler module is the same FoundationalContract from engine
        assert hasattr(_cec, "_FC"), "compiler module must have _FC (engine FoundationalContract)"
        fc_proj = _cec._FC.language_projection(_cec._ExistenceMode.AGENTIC)
        assert fc_proj["anchor_pole"] == "aurora"

        print(f"{_PASS} aurora_conversation_episode_compiler")
    except Exception as e:
        failures.append(f"aurora_conversation_episode_compiler: {e}")
        print(f"{_FAIL} aurora_conversation_episode_compiler — {e}")


    # ── 7. EngineRuntime end-to-end through feed_evidence + govern ───
    print("\n[7] EngineRuntime — feed_evidence → govern round-trip...")
    try:
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            rt = EngineRuntime(state_path=os.path.join(td, "state.json"))
            obs = {
                "ontological_depth":    0.4192,
                "emotional_valence":    0.90,
                "connections":          104,
                "coherence":            0.50,
                "uncertainty":          0.05,
                "external_perspective": "integration_test",
                "routing_mode":         "surface",
                "primary_axis":         "B",
            }
            result = rt.tick(obs)
            assert isinstance(result, ConstraintEngine.__class__) or hasattr(result, "decision"), \
                f"tick() must return GovernorResult; got {type(result)}"
            assert result.decision in (
                GovernorDecision.PERMITTED,
                GovernorDecision.DEFERRED,
                GovernorDecision.REJECTED,
            )
            # State persisted
            assert rt._state.total_evidence_fed == 1
            assert rt._state.total_govern_calls == 1
            assert os.path.exists(os.path.join(td, "state.json"))

            # 4 more ticks → dominant_pattern returns a real axis
            for _ in range(4):
                rt.tick(obs)
            pattern = rt.dominant_pattern()
            assert pattern in ("X","T","N","B","A"), \
                f"dominant_pattern() must be a valid axis; got {pattern!r}"
            trend = rt.coherence_trend()
            assert trend in ("rising","stable","falling")

        print(f"{_PASS} EngineRuntime end-to-end")
    except Exception as e:
        failures.append(f"EngineRuntime: {e}")
        print(f"{_FAIL} EngineRuntime — {e}")


    # ── 8. GovernorWeights flow into real runtime_regime calls ───────
    print("\n[8] GovernorWeights constants flow into runtime_regime outputs...")
    try:
        from foundational_contract import FoundationalContract as FC2
        fc2 = FC2()
        rr = fc2.runtime_regime()
        ax = rr["dominant_axis"]
        gw = rr["governor_weight"]
        expected = GovernorWeights.AS_DICT.get(ax)
        assert abs(gw - expected) < 1e-9, \
            f"governor_weight mismatch for {ax}: got {gw}, expected {expected}"
        print(f"{_PASS} GovernorWeights → runtime_regime (dominant={ax}, weight={gw})")
    except Exception as e:
        failures.append(f"GovernorWeights flow: {e}")
        print(f"{_FAIL} GovernorWeights flow — {e}")


    # ── 9. No stale old-stack types bleed through ────────────────────
    print("\n[9] Zero old-stack types in live router/governor objects...")
    try:
        import aurora_constraint_manifold_router as amr
        import aurora_internal.aurora_runtime_constraint_governor as arcg

        for mod, name in [(amr, "router"), (arcg, "governor")]:
            for attr in ("ConstraintProfile", "PhaseState"):
                assert not hasattr(mod, attr), \
                    f"{name} module still exports {attr} — old-stack bleed"
        print(f"{_PASS} Zero old-stack type bleed")
    except Exception as e:
        failures.append(f"Old-stack bleed check: {e}")
        print(f"{_FAIL} Old-stack bleed check — {e}")


    # ── Final verdict ─────────────────────────────────────────────────
    print("\n" + "=" * 62)
    if failures:
        print(f"INTEGRATION TEST FAILED  ({len(failures)} failure(s))")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print("INTEGRATION TEST PASSED  (9/9)")
    print("=" * 62)
