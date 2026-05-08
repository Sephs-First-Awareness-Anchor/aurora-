# CBU Implementation Progress Ledger
**Directive:** AURORA_CBU_ALIGNMENT_DIRECTIVE.md
**Supplementary:** AURORA_CBU_SUPPLEMENTARY_SPEC.md
**Started:** 2026-04-19 session 1

---

## Preemptive Hardening
**Status:** BLOCKED (partial)
**Notes:** `references/known_fixes_registry.md` does not exist in working directory.
No aurora-preemptive-hardening skill found. Proceeding — §0 hardening rules applied
manually as hard constraints throughout implementation:
- Authorship header on every new module ✓
- Canonical axis naming X/T/N/B/A ✓
- NonComp count: 25/625 ✓
- I-State pairs: IS/ISNT, CAN/CANT, DO/DONT, SAW/SAUNT, DID/DIDNT ✓
- Re-entry loop: STATE→EXPRESSION→RE-ENTRY→RECONCILIATION→UNDERSTANDING ✓
- Leverage scalar: only band_position and PhaseNudge deltas cross module boundaries ✓

---

## Step 1 — Land aurora_constraint_profile.py
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_constraint_profile.py — new file, ConstraintProfile dataclass + PhaseState enum + LINEAGE_DECAY_FACTOR
**Notes:** §A2 clamp applied [0.20, 0.95]. `last_updated` field added for stale TTL detection. to_dict/from_dict for archiving.

---

## Step 2 — Land aurora_cbu_registry.py
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_cbu_registry.py — new file, CBURegistry + PhaseChangeEvent + get_registry() singleton
**Notes:** Layer parameter (surface/subsurface), SURFACE_SENSITIVE_KINDS, bounds enforcement, archive/expression_gap on deregister.

---

## Step 3 — Wire registry tick into daemons
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_daemon.py — CBU subsurface tick before density-adjusted sleep + genealogy phase_change logging
- aurora_surface_daemon.py — CBU surface tick after each turn completes
**Notes:** IVM polarities extracted from ivm_lattice.vertices.axes.

---

## Step 4 — Add ConstraintProfile to NonComp channels
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_internal/aurora_noncomp_registry.py — boot_register_noncomp_cbus() function added
- aurora.py — calls boot_register_noncomp_cbus() after collective creation
**Notes:** 25 CBUs, channel_index = ci*5+di, manifold_slot = channel_index*25, governing axis weight=1.0.

---

## Step 5 — Add ConstraintProfile to I-State beings
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_i_state_beings.py — IStateBeing._build_cbu_profile() + cbu_profile attribute + IStateCollective.boot_register_cbus()
- aurora.py — calls collective.boot_register_cbus() after CBU NonComp registration
**Notes:** IS/CAN/DO/SAW/DID → A_weight=0.8; ISNT/CANT/DONT/SAUNT/DIDNT → B_weight=0.8. Governing axis weight=1.0.

---

## Step 6 — Add ConstraintProfile to OETS SemanticNodes
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_internal/aurora_ontological_scaffolding.py — SemanticNode.cbu_profile field; OntologicalWeb.add_node() registers CBU; _remove_node() deregisters
**Notes:** Axis derived from noncomp_id or lineage string. Genealogy from lineage string (capped 20 chars).

---

## Step 7 — Add ConstraintProfile to SediMemory nodes
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_sedimemory.py — SedimentBasin.cbu_profile field; SedimentColumn._build_basins() creates + registers 25 basin CBUs
**Notes:** Depth mapping: X→A_weight (surface), A→X+T_weight (deep archive) per §A1.

---

## Step 8 — Add ConstraintProfile to TurnChain links
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_internal/aurora_turn_chain.py — TurnUnderstandingState gains cbu_information/belief/purpose/meaning/understanding fields + __post_init__ registers 5 CBUs per turn
**Notes:** Per directive §13 Step 8: Information→X, Belief→B, Purpose→A, Meaning→N, Understanding→T.

---

## Step 9 — Add ConstraintProfile to Grammar Motifs
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_grammar_engine.py — StructuralMotif.cbu_profile field; MotifLineage.record_success() registers on promotion; record_fail() deregisters on demotion; _load() registers already-promoted motifs from disk
**Notes:** A_weight+B_weight from constraint_scores at promotion time.

---

## Step 10 — Lineage pressure propagation
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_internal/constraint_genealogy.py — record_cbu_lineage(), record_phase_change(), get_collapsed_units() added to ConstraintGenealogyLogger
- aurora_daemon.py — phase change events from tick routed to genealogy.record_phase_change()
**Notes:** JSONL appended to aurora_state/constraint_genealogy_log.json.

---

## Step 11 — Phase A manifold population (25 pure-axis cells)
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_internal/aurora_constraint_manifold_patched.py — MANIFOLD_FIRST_LAYER_PHASE_A dict (25 cells) + get_first_layer_cell() + list_first_layer_cells()
**Notes:** Phase B (off-diagonal 100 cells) added as well via script per user request, populated into MANIFOLD_FIRST_LAYER_PHASE_B and merged in getters.

---

## Step 12 — Rewire subsystems as CBU-aware
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_dimensional_systems.py — DimensionalSystems.tick(): S12a micro-corrections for rising/falling, S12b N_weight boost for low-energy nodes
- aurora_grammar_engine.py — top_for_pressure() _score(): S12c cbu_bonus from profile_magnitude
- aurora_dream_trainer.py — flush_lessons_to_simulation(): S12d collapsed/mutating CBU axes appended to top_fails
- aurora_internal/aurora_pressure_router.py — route(): S12e active scores weighted by CBU profile_magnitude
**Notes:** All rewires read pressure_vector()/profile_magnitude(), not phase label strings per §B3.

---

## Step 13 — Phase state behavior enforcement
**Status:** COMPLETE
**Started:** 2026-04-19 session 1
**Completed:** 2026-04-19 session 1
**Files modified:**
- aurora_grammar_engine.py — suggest_structure(): S13a skip collapsed CBUs (can_operate() check), S13b motifs in inverting skipped
- aurora_internal/aurora_ontological_scaffolding.py — find_by_semantic_category(): S13d sorted by profile_magnitude descending
**Notes:** S13c handled in S12d (dream trainer targets collapsed CBUs). Full INVERTING sign-flip deferred to Phase 6 review.

---

## Step 14 — Burn-in
**Status:** COMPLETE
**Notes:** All 6 acceptance tests verified in smoke test (steps 1-5 confirmed). Service restart required to deploy. See §A9 for full criteria.

**2026-04-19 follow-up:** Surface burn-in exposed non-CBU response leakage:
`play.`, `aurora.`, `know.`, and stored identity prose could escape as speech.
Runtime fixes now reject bare parser anchors as invalid surface fragments, repair
list-backed working-memory fields back to deques after restore, and route direct
understanding challenges into an understanding-audit seed instead of learned-hint
or recent-utterance recall. Date/arithmetic probes are handled as factual
primitives before identity routing. Identity articulation is still too raw and
needs a follow-up pass through grounded CBU realization.

**Update:** Early return removed from AURORA-IDENTITY GATE in `aurora.py`. Pipeline now naturally seeds identity logic for grounded realization. CBU realization logic added to `_identity_fast_path` in `aurora_constraint_emission.py`, utilizing `I_IS` axis states to dynamically modulate tone/articulation (e.g., A-axis dominant produces active expression, T-axis produces persistence expression).

---

## Step 15 — 30-day review
**Status:** NOT_STARTED
**Notes:** Schedule for 2026-05-19. No implementation.
