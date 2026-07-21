# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.8/R1.8.1/R1.9.1 Track C: governance liveness inventory, automated.

"verify_*() green != wired. Every module claiming a runtime role must show
boot-path reachability; claimed-but-unwired modules live in an explicit
quarantine manifest so their status is a decision, never an accident."
(liveness rule, R1.7 addendum)

R1.9.1 correction (backward-attribution rule): reachability from
boot_aurora() is necessary but NOT sufficient to claim a module produces
delivered output. R1.8.1 Step 3 forward-inferred from aurora.py's boot
comment ("Constraint emitter -- replaces ... SentenceComposer emission
path") that ConstraintEmitter was live and SentenceComposer was dead. Both
halves of that claim were wrong: SentenceComposer is still reachable and
IS what produces resp_B (the text run_probe_battery.py actually scores),
while ConstraintEmitter, though genuinely live and executing, sits on a
parallel path whose output is not what gets delivered. R1.9.1 fixed this
by tracing backward from the actual delivered artifact (instrumenting the
real return chain) instead of forward from architecture/comments -- see
test_delivered_output_attribution_traces_to_sentence_composer below.

This encodes the C1 inventory's verdicts as regression checks against
aurora.py's source, mirroring the pattern already established by
tests/test_flow_audit_and_tcl_wiring.py. A module regressing from LIVE to
unwired fails CI; a module quietly becoming reachable without updating the
quarantine manifest is exactly as much a decision that should be visible.
"""
import os
import shutil
import sys
import tempfile
from typing import Dict

AURORA_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora.py")
REPO_ROOT = os.path.dirname(AURORA_PY)


def _aurora_source() -> str:
    with open(AURORA_PY, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# QUARANTINE MANIFEST -- modules confirmed claimed-but-not-live (C1 verdicts).
# Each entry is a decision, not an accident: if one of these becomes wired,
# move it to the LIVE section below (and celebrate) rather than deleting the
# check. If a LIVE module regresses to here, that is exactly the failure
# mode this file exists to catch.
# ---------------------------------------------------------------------------
QUARANTINE_STALE: Dict[str, str] = {}

# N5 item 1 (R1 Campaign Closure, 2026-07-16), ratified by Sunni's decision
# memo (2026-07-16, "N2/N4/N5 Open Items"): FailureGuardSuite is
# RECLASSIFIED, not integrated -- a permanent classification, distinct from
# QUARANTINE_STALE's "confirmed dead, no plan yet" framing. Kept as
# documented historical guard-rail design (real, tested code -- not
# deleted), superseded by this campaign's generation-time fixes (relevance-
# primary selection, POS-gating, skeleton validity, grounded fitness),
# which land as post-hoc corrections INSIDE SentenceComposer's generation
# process rather than as pre-expression guard-blocking on a separately-
# computed signal.
QUARANTINE_SPEC_REFERENCE = {
    "aurora_constraint_engine.FailureGuardSuite": (
        "RECLASSIFIED (ratified 2026-07-16, decision memo N2/N4/N5, "
        "Decision 3): thresholds calibrated to pre-campaign signals -- "
        "'dream avg=0.343, 10/10 episodes fail' for uncertainty, 'dream "
        "avg=0.365, 10/10 episodes fail' for boundary -- both predating "
        "this remediation's fixes. Integration against the now-honest "
        "battery would be liveness theater, not a real gate (N5 item 1's "
        "dossier, known_fixes_registry.md). "
        "Revisit trigger (recorded, not scheduled -- decision point "
        "returns to Sunni with N6 data, not decided here): the suite's "
        "five guard concepts (uncertainty, boundary, context-carryover, "
        "perspective-integration, coherence-maintenance) map onto "
        "dimensions N6's honest classroom re-verdict measured for the "
        "first time (2026-07-16, 45 lessons, all 15 canonical dimensions). "
        "N6 data: divergence mean 0.1116, per-dimension range 0.0725-"
        "0.1375 -- no dimension flat-lined near zero across its 3 lessons. "
        "episode_avg_fitness for uncertainty_signaling specifically stayed "
        "close to flat (0.0893 here vs R1.4's pre-fix 0.0871) -- the one "
        "dimension with a directly comparable prior number, and the "
        "smallest movement of any metric this campaign recorded. "
        "Suggestive, not conclusive: fitness is a distinct subsystem "
        "metric from divergence, and N=1 directly-comparable dimension is "
        "thin evidence for 'training demonstrably cannot move this.' "
        "Flagged per the trigger's own text; Sunni decides whether this "
        "clears the bar for guard-concept reimplementation."
    ),
}

# Modules with genuine call sites in aurora.py, but only reachable when
# boot_aurora() runs a NON-"surface" runtime_profile. Every probe-battery
# run and trace this entire R0-R1.8 campaign has produced used
# runtime_profile="surface" (see run_probe_battery.py), so these have never
# actually participated in any measurement this campaign has taken, despite
# being real, non-dead code.
QUARANTINE_PROFILE_GATED = {
    "aurora_internal.aurora_worth_evaluator": (
        "Instantiated + called (worth_eval.evaluate(...) at aurora.py "
        "L22920) only when NOT booted with runtime_profile='surface'. "
        "run_probe_battery.py boots with runtime_profile='surface' "
        "unconditionally, so this has been unreachable in every measurement "
        "R0-R1.8 took. N5 item 3 (R1 Campaign Closure, 2026-07-16) verdict: "
        "NOT dead -- 'surface' is a deliberate fast-boot performance profile "
        "this campaign's own tooling chose for speed, not the profile real "
        "entry points default to. boot_aurora()'s own signature defaults "
        "runtime_profile to 'full', and that is what aurora_daemon.py, the "
        "Flutter mobile bridge (aurora_bridge.py), run_gauntlet.py, and "
        "most training scripts actually call with no override -- this tier "
        "runs for real, every turn, in normal production use. R1.9.2's G4 "
        "gate (FIX-A039) already ran a stratified probe subset under "
        "runtime_profile='full' and confirmed the whole intake-metabolism "
        "tier (worth_evaluator, VariantPromoter, accountant, bias_engine, "
        "solidification) executes with no exceptions and no material "
        "behavior shift to delivered text beyond the expected ~10x per-turn "
        "slowdown (it's a separate depth/solidification subsystem, "
        "decoupled from the SentenceComposer path this campaign's grammar "
        "work targeted). Quarantined here for a real, already-evidenced "
        "reason -- the full 60-probe battery times out at 600s under "
        "'full' -- not because the tier is unused or broken."
    ),
    "aurora_internal.aurora_variant_promotion.VariantPromoter": (
        "Same gating as worth_evaluator (aurora.py L22988, "
        "variant_promoter.process_solidified(...)); same N5 item 3 verdict."
    ),
}

# Referenced by separate runtime entry points (aurora_runtime.py,
# aurora_daemon.py) but not by aurora.py's boot_aurora() -- the path this
# entire investigation's probe battery and traces exercise. Not verified
# live or dead under those other entry points; simply out of this
# investigation's reach.
QUARANTINE_ALTERNATE_ENTRYPOINT_ONLY = {
    "aurora_internal.aurora_entropy_detector": (
        "Not referenced in aurora.py. Referenced by aurora_runtime.py and "
        "aurora_daemon.py, which this investigation did not boot or trace."
    ),
}

# U1 (R1.9.2): scheduled quarantine, not indefinite dual-alive -- resolved.
# ConstraintEmitter's dual-alive review closed on 2026-07-16 (decision
# memo, Decision 2): narrowed to a permanent role, not left pending. See
# LIVE_FALLBACK below. Empty now that the one entry it ever held resolved;
# a future dual-alive path would land here again with its own dated plan.
QUARANTINE_SCHEDULED_REVIEW: Dict[str, Dict[str, str]] = {}

# N4 (decision memo, ratified 2026-07-16, Decision 2): ConstraintEmitter is
# LIVE_FALLBACK -- narrowed from LIVE_PARALLEL (genuinely executing, not
# delivering) to a single, permanent, documented role: the crash net at
# the emission chokepoint (_emit_honest_abstain_and_seek), firing
# exclusively when the main composition path (SentenceComposer) returns
# literally nothing. All other call sites (the proactive "primary
# emission path" chain-step, the "IVM pressure lens" seeking/fallback
# block, the redundant "constraint_fallback" last-resort) retired --
# "one voice, one documented net." Riders: (a) reachability test below
# proves the net catches a synthetic empty-output failure (safe-path
# rule); (b) every catch logs {turn_id, trigger, output} to
# aurora_state/constraint_fallback_log.jsonl via _log_constraint_fallback
# (silent-fallback rule -- a net that catches silently is a
# scripted-response violation in costume). U1's migration-completion rule
# is now satisfied: this is a decided, dated resolution, not indefinite
# dual-alive.
LIVE_FALLBACK = {
    "aurora_constraint_emission.ConstraintEmitter": (
        "Narrowed to crash-net-only (decision memo Decision 2, "
        "2026-07-16). Reachable exclusively via _emit_honest_abstain_"
        "and_seek(), called from the two points a genuine content gap can "
        "surface: mid-chain (_chain_down5_understanding's terminal-gap "
        "fallback, trigger='mid_chain') and the true emission chokepoint "
        "(_enforce_emission_discipline, trigger='emission_chokepoint'). "
        "Both call sites already existed pre-narrowing; what changed is "
        "that ConstraintEmitter no longer has any OTHER call site "
        "competing to set response content before this net's gate is "
        "reached. This is the one piece of ConstraintEmitter's original "
        "role N4's own dossier found to be a genuine, non-redundant "
        "safety net rather than dead-weight parallel machinery."
    ),
}

LIVE_CONFIRMED = {
    "ContradictionLedger": (
        "Instantiated at boot (aurora.py L20452-20453), wired to "
        "working_memory at both initial wiring and the final re-assert pass."
    ),
    "attention_engine": (
        "'.tick()' and '.get_meaning_nucleus()' called every turn inside "
        "_run_live_response_turn."
    ),
    "CERSBridge": (
        "Instantiated and called in aurora.py (CERS shadow pass). "
        "Explicitly documented as read-only/advisory/non-authoritative by "
        "design -- this is a design decision, not staleness."
    ),
    "aurora_toroidal_circulation.ToroidalCirculationLayer": (
        "N5 item 2 (R1 Campaign Closure, 2026-07-16) correction: this entry "
        "was WRONGLY filed under QUARANTINE_STALE. Re-investigation found "
        "the module fully live -- just not where the original 'zero "
        "references in aurora.py' check looked. MTSL Phase 3 (2026-07-13, "
        "FIX-A011, predates this campaign) moved TCL ownership out of "
        "aurora.py and into TopologicalSemanticCoordinator "
        "(aurora_internal/dual_strata/topological_semantic_coordinator.py): "
        "constructed + seeded from the surface log in the coordinator's own "
        "__init__, observed/saved every turn inside observe_turn(), called "
        "from exactly one site (aurora_consciousness_engine.py's "
        "_attach_dual_strata_snapshot, the single-observer law) to prevent "
        "a real double-tick that direct dual-call-site wiring would cause. "
        "aurora.py correctly only READS the coordinator's cached, "
        "compressed toroidal_signature -- it was never supposed to "
        "reference ToroidalCirculationLayer directly again. The failing "
        "test (test_flow_audit_and_tcl_wiring.py::test_aurora_py_wires_"
        "toroidal_layer_into_cers_snapshot_pass) was asserting the "
        "superseded pre-Phase-3 pattern, not a genuine regression -- fixed "
        "by rewriting the test to check the current (correct) wiring."
    ),
}

# R1.9.1 correction: two verdict tiers replace the single LIVE bucket for
# these two, because reachability and delivered-output attribution turned
# out to diverge -- exactly the case the backward-attribution rule exists
# to catch.
#
# ConstraintEmitter WAS here (LIVE_PARALLEL: genuinely executing via
# _field_frame_compress and _emit_honest_abstain_and_seek, but not what
# reaches resp_B) from R1.9.1 through N4's own dossier. Decision memo
# Decision 2 (2026-07-16) resolved that dual-alive status by narrowing
# ConstraintEmitter to a single permanent role -- moved to LIVE_FALLBACK
# below. Bucket kept (even though currently empty) as the live category
# for any future reachable-but-not-delivering finding.
LIVE_PARALLEL: Dict[str, str] = {}

LIVE_DELIVERING = {
    "aurora_expression_perception.SentenceComposer": (
        "R1.8.1 Step 3 called this 'orphaned dead code, bypassed since "
        "2026-06-30' based on aurora.py's boot comment. That was WRONG: "
        "instantiated at aurora_expression_perception.py L3296 "
        "(self.composer = SentenceComposer(...)), reachable via "
        "gateway._express() -> ExpressionPerceptionEngine.express() -> "
        "self.composer.compose(). R1.9.1 confirmed via backward-instrumented "
        "live trace that gateway._express()'s returned .content is BYTE-FOR-"
        "BYTE what ends up in resp_B.content -- the exact field "
        "run_probe_battery.py scores. This is the actual delivered-output "
        "mechanism; the 6/30 'replacement' migration never removed or "
        "quarantined it, leaving both paths alive (migration-completion "
        "rule, R1.9.1)."
    ),
}


def test_quarantine_stale_modules_remain_unreferenced_in_aurora_py():
    """QUARANTINE_STALE is currently empty (FailureGuardSuite, its only
    prior entry, was reclassified to QUARANTINE_SPEC_REFERENCE on
    2026-07-16 -- see that manifest's own unreferenced-check). Any future
    QUARANTINE_STALE entry's short module name must stay unreferenced in
    aurora.py; if one gains a real reference, it graduated out of
    quarantine -- update this file's manifest deliberately rather than
    letting the assertion silently start failing."""
    source = _aurora_source()
    for qualified_name in QUARANTINE_STALE:
        short_name = qualified_name.rsplit(".", 1)[-1]
        assert short_name not in source, (
            f"{short_name} now appears in aurora.py -- if this is real "
            f"wiring, move it out of QUARANTINE_STALE and add a LIVE "
            f"assertion; if it's an incidental string match, this "
            f"assertion needs updating."
        )


def test_toroidal_circulation_layer_is_live_via_the_coordinator():
    """N5 item 2 correction: TCL is live, just not by direct reference in
    aurora.py -- TopologicalSemanticCoordinator owns it exclusively (FIX-
    A011, single-observer law). aurora.py must keep reading the cached
    signature and must never reference ToroidalCirculationLayer directly
    again (that would reintroduce the double-tick bug the coordinator was
    built to eliminate). See test_flow_audit_and_tcl_wiring.py for the
    full structural proof of the coordinator-side wiring."""
    aurora_source = _aurora_source()
    assert "ToroidalCirculationLayer" not in aurora_source
    assert '_mtsl_coordinator.latest_snapshot.toroidal_signature' in aurora_source

    coord_path = os.path.join(
        REPO_ROOT, "aurora_internal", "dual_strata", "topological_semantic_coordinator.py"
    )
    with open(coord_path, "r", encoding="utf-8") as f:
        coord_source = f.read()
    assert "from aurora_toroidal_circulation import ToroidalCirculationLayer" in coord_source
    assert "self._tcl.observe(intensity)" in coord_source


def test_constraint_emitter_is_wired_at_boot_as_live_fallback():
    """N4 (decision memo, 2026-07-16): reachable and executing, but now as
    LIVE_FALLBACK -- a single, narrow, permanent crash-net role, not the
    LIVE_PARALLEL (genuinely executing but non-delivering, competing-path)
    status this test asserted before the narrowing. See
    test_delivered_output_attribution_traces_to_sentence_composer for the
    actual delivered-path proof (SentenceComposer, unaffected by this
    narrowing)."""
    source = _aurora_source()
    assert "from aurora_constraint_emission import ConstraintEmitter" in source
    assert "constraint_emitter" in source
    assert len(LIVE_FALLBACK) >= 1


def test_constraint_emitter_non_abstain_call_sites_are_retired():
    """The three retired call sites (proactive chain-step "primary
    emission path," the "IVM pressure lens" seeking/fallback block, the
    redundant "constraint_fallback" last-resort) must not reappear --
    _emit_abstain is the only ConstraintEmitter method aurora.py may call
    now; .emit() itself must not be called directly from aurora.py."""
    source = _aurora_source()
    assert "_ce.emit(" not in source
    assert "_emitter.emit(" not in source
    assert "response_src = \"constraint_emission\"" not in source
    assert "response_src = \"comprehension_gap_ask\"" not in source
    assert "response_src = \"constraint_fallback\"" not in source
    assert "_emitter._emit_abstain(" in source


def test_constraint_emitter_fallback_net_catches_synthetic_empty_output():
    """Safe-path rule: the narrowed crash net must actually catch a
    synthetic empty-output failure, not just look narrowed in source.
    Drives _emit_honest_abstain_and_seek directly against a minimal fake
    emitter and confirms it fills response_content and logs the catch."""
    import json
    import sys
    import tempfile
    from types import SimpleNamespace

    sys.path.insert(0, os.path.dirname(AURORA_PY))
    import aurora

    class _FakeAbstainResult:
        text = "I don't have a clear sense of that."

    class _FakeEmitter:
        def _emit_abstain(self, ctx):
            return _FakeAbstainResult()

    with tempfile.TemporaryDirectory() as scratch:
        systems = {"constraint_emitter": _FakeEmitter(), "state_dir": scratch}
        state = SimpleNamespace(parsed={}, response_content="")

        aurora._emit_honest_abstain_and_seek(
            "a synthetic empty-output turn", systems, state, trigger="test_synthetic"
        )

        assert state.response_content.strip() != ""
        assert state.response_src == "constraint_abstain"

        log_path = os.path.join(scratch, "constraint_fallback_log.jsonl")
        assert os.path.exists(log_path), "fallback catch was not logged (silent-fallback rule)"
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        entry = lines[0]
        assert entry["trigger"] == "test_synthetic"
        assert entry["output"].strip() != ""
        assert "turn_id" in entry and entry["turn_id"]


def test_sentence_composer_is_reachable_from_gateway_express():
    """SentenceComposer was wrongly quarantined as dead in R1.8.1. Source-level
    reachability check; the byte-for-byte delivered-output proof is the live
    trace test below."""
    with open(
        os.path.join(REPO_ROOT, "aurora_expression_perception.py"),
        "r", encoding="utf-8",
    ) as f:
        aep_source = f.read()
    assert "self.composer = SentenceComposer(self.lexicon, self.voice)" in aep_source
    with open(
        os.path.join(REPO_ROOT, "aurora_governance_persistence_gateway.py"),
        "r", encoding="utf-8",
    ) as f:
        gw_source = f.read()
    assert "self.perception.express(" in gw_source


def test_delivered_output_attribution_traces_to_sentence_composer():
    """R1.9.1 Step 2: backward attribution, not forward inference. Boots a
    real (throwaway-copy-isolated) Aurora instance, instruments the actual
    return chain, and asserts gateway._express()'s returned .content is
    IDENTICAL to resp_B.content for a real turn -- proving byte-for-byte
    which stage the delivered/scored text actually comes from, rather than
    inferring liveness from a boot comment or import graph (the exact
    methodology error that produced the R1.8.1 orphaned-composer mistake)."""
    sys.path.insert(0, REPO_ROOT)
    import aurora_governance_persistence_gateway as agpg
    import inspect

    target_cls = None
    for _name, obj in vars(agpg).items():
        if inspect.isclass(obj) and "_express" in getattr(obj, "__dict__", {}):
            target_cls = obj
            break
    assert target_cls is not None, "no class in aurora_governance_persistence_gateway defines _express"

    captured = {"calls": []}
    orig_express = target_cls._express

    def _patched(self, packet, synthesis, mode):
        result = orig_express(self, packet, synthesis, mode)
        captured["calls"].append(result.content)
        return result

    target_cls._express = _patched
    scratch = tempfile.mkdtemp(prefix="aurora_liveness_attribution_")
    try:
        shutil.copytree(
            os.path.join(REPO_ROOT, "aurora_state"),
            os.path.join(scratch, "aurora_state"),
        )
        import aurora as A
        systems = A.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)
        systems["_session_turn_buffer"] = []
        result = A.process_external_user_turn(
            systems, "Hi Aurora, how are you doing today?",
            source_label="liveness_attribution_test",
        )
        resp_b = result.get("resp_B")
        assert resp_b is not None, "process_external_user_turn returned no resp_B"
        assert captured["calls"], "gateway._express() was never called for this turn"
        # gateway._express() can be called more than once per turn (e.g. a
        # discarded earlier draft) -- resp_B is attributed to SentenceComposer
        # if it matches ANY call's returned content, not necessarily the
        # first. If it matches none, the attribution genuinely doesn't hold.
        assert resp_b.content in captured["calls"], (
            f"resp_B.content matched none of the {len(captured['calls'])} "
            "gateway._express() call(s) captured this turn -- the delivered-"
            "output attribution no longer holds and this test's "
            "LIVE_DELIVERING verdict for SentenceComposer needs "
            f"re-verification. resp_B.content={resp_b.content!r} "
            f"captured_calls={captured['calls']!r}"
        )
    finally:
        target_cls._express = orig_express
        shutil.rmtree(scratch, ignore_errors=True)


def test_contradiction_ledger_is_wired_at_boot():
    source = _aurora_source()
    assert "from aurora_ivm import ContradictionLedger" in source
    assert "contradiction_ledger" in source


def test_worth_evaluator_and_variant_promotion_are_profile_gated_not_dead():
    """Confirms these are real call sites (not literally dead code), while
    documenting that run_probe_battery.py's surface-profile boot never
    reaches them -- see QUARANTINE_PROFILE_GATED above."""
    source = _aurora_source()
    assert "worth_eval.evaluate(" in source
    assert "variant_promoter.process_solidified(" in source
    with open(
        os.path.join(os.path.dirname(AURORA_PY), "run_probe_battery.py"),
        "r", encoding="utf-8",
    ) as f:
        rpb_source = f.read()
    assert 'runtime_profile="surface"' in rpb_source, (
        "run_probe_battery.py no longer boots with runtime_profile='surface' "
        "-- if so, worth_evaluator/variant_promotion may now be reachable "
        "from probe-battery runs; update QUARANTINE_PROFILE_GATED."
    )


def test_quarantine_manifest_is_non_empty_and_documented():
    """The manifest existing and having reasons attached is itself the
    check -- an empty or undocumented quarantine is a silent accident."""
    all_quarantined = {
        **QUARANTINE_STALE,
        **QUARANTINE_PROFILE_GATED,
        **QUARANTINE_ALTERNATE_ENTRYPOINT_ONLY,
        **QUARANTINE_SPEC_REFERENCE,
    }
    assert len(all_quarantined) >= 4
    for name, reason in all_quarantined.items():
        assert isinstance(reason, str) and len(reason) > 20, (
            f"{name} is quarantined without a real documented reason"
        )


def test_spec_reference_modules_remain_unreferenced_in_aurora_py():
    """FailureGuardSuite's RECLASSIFY (N5 item 1, ratified 2026-07-16) is a
    permanent classification, not a pending integration -- it should stay
    unreferenced in aurora.py exactly like QUARANTINE_STALE entries, just
    for a different (decided, not accidental) reason."""
    source = _aurora_source()
    assert "FailureGuardSuite" not in source, (
        "FailureGuardSuite now appears in aurora.py -- this contradicts its "
        "RECLASSIFIED-as-spec-reference status (N5 item 1); if this is real "
        "new wiring, that's a deliberate un-reclassification decision that "
        "needs its own ratification, not a silent drift."
    )
    assert len(QUARANTINE_SPEC_REFERENCE) >= 1


def test_scheduled_quarantine_entries_have_a_real_review_date():
    """R1.9.2 U1: dual-alive paths are only compliant with a DATED
    resolution plan (migration-completion rule) -- an entry here without a
    real review_by date is exactly the indefinite-limbo state that rule
    exists to forbid. Currently empty (ConstraintEmitter's review resolved
    2026-07-16, decision memo Decision 2) -- that IS compliant; the rule
    forbids indefinite dual-alive, not zero pending reviews. Any future
    entry must still carry a real date."""
    import datetime

    for name, entry in QUARANTINE_SCHEDULED_REVIEW.items():
        assert "review_by" in entry, f"{name} has no review_by date"
        # Must parse as a real date -- catches placeholder/malformed values.
        datetime.date.fromisoformat(entry["review_by"])
        assert isinstance(entry.get("reason"), str) and len(entry["reason"]) > 20, (
            f"{name} is scheduled for review without a real documented reason"
        )
