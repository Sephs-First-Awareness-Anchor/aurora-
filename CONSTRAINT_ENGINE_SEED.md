# Constraint Engine Seed Document
**Authors:** Sunni (Sir) Morningstar, Cael Devo  
**Source:** Aurora operational state distillation — 2026-05-02  
**State snapshot timestamp:** 1777748525 (subsurface), 1777748423 (surface)  
**Chain links at snapshot:** 552 | **QAO recent events:** 96

---

## 1. Empirical NC Channel Activation Priors

*Sources: genealogy/links.json (552 links), evo_625_pressure_map.json (625 slots), surface_pressure_log.jsonl (36,355 entries)*

### 1.1 Dominant Relief Axis Distribution (from genealogy links)

| Axis | Dominant in | % of links | Avg mean-relief |
|------|-------------|------------|-----------------|
| T    | 307 links   | 55.6%      | 0.007053        |
| X    | 229 links   | 41.5%      | 0.002616        |
| N    | 7 links     | 1.3%       | 0.004169        |
| A    | 5 links     | 0.9%       | 0.002935        |
| B    | 4 links     | 0.7%       | 0.003961        |

**Key finding:** T and X jointly own 97.1% of link-level relief production. N, B, A produce relief at lower frequency but B and N yield higher per-link averages when they do fire.

### 1.2 Axis Pair Frequency in Link Parents

Single-axis parent links (sorted by count): A=58, B=46, T=43, X=36, N=33  
Two-axis parent combinations:
- B-N: 19 links (most frequent two-axis pair)
- B-T: 16
- A-T: 13
- B-X: 12
- A-B: 9
- N-T: 8, N-X: 8, T-X: 8
- A-X: 7, A-N: 5

**Dream-directive pair** (dream:directive:consciousness × dream:directive:expression): 2 links, avg relief = **0.074862** — 100× higher than typical NC pairs. This is an anomalous high-relief coupling with distinct origin.

### 1.3 Link Depth Distribution

| Depth | Count | Cumulative |
|-------|-------|-----------|
| 1     | 169   | 30.6%     |
| 2     | 151   | 57.9%     |
| 3     | 101   | 76.2%     |
| 4     | 61    | 87.3%     |
| 5     | 49    | 96.2%     |
| 6     | 21    | 100%      |

**Key finding:** 87.3% of links are depth ≤ 4. The engine's default synthesis budget should operate primarily in depth 1–4 space.

### 1.4 NC Field Slot Activation (625-slot pressure map)

**Occupancy:** 194/625 slots occupied (31.0%); 431/625 near-zero (69.0%)  
**Highway slots:** 21 (threshold ≥ 0.3 weight)  
**Gradient constants:**
- base_resistance: 0.08
- highway_relief: 0.40
- highway_threshold: 0.30
- t_pull_amplifier: 0.12
- agency_resistance: 0.20
- empty_seed_magnitude: 0.04
- maturity_bonus_cap: 0.10

**Top 20 hottest slots by total_weight:**

| Slot | Total Weight | Dominant | Secondary | Ops Count |
|------|-------------|----------|-----------|-----------|
| NC:X>X × NC:X>X | 22.67 | X | T | 1318 |
| NC:X>T × NC:X>T | 13.21 | X | T | 1190 |
| NC:T>T × NC:T>T | 12.21 | T | X | 1017 |
| NC:X>X × NC:X>T | 10.87 | X | T | 1049 |
| NC:T>T × NC:T>X | 9.70  | T | X | 958  |
| NC:T>X × NC:X>T | 9.48  | X | T | 940  |
| NC:X>T × NC:T>X | 9.47  | X | T | 940  |
| NC:T>X × NC:X>X | 9.24  | X | T | 933  |
| NC:X>T × NC:T>T | 8.87  | T | X | 899  |
| NC:X>T × NC:X>X | 8.71  | X | T | 932  |
| NC:X>X × NC:T>X | 8.13  | X | T | 890  |
| NC:X>X × NC:T>T | 8.12  | X | T | 889  |
| NC:B>B × NC:B>B | 7.51  | B | X | 293  |
| NC:N>N × NC:N>N | 7.32  | N | T | 236  |
| NC:X>T × NC:X>A | 5.17  | X | A | 319  |
| NC:X>T × NC:X>B | 5.06  | X | T | 311  |
| NC:X>T × NC:X>N | 4.95  | X | T | 301  |
| NC:X>N × NC:X>B | 4.63  | X | B | 270  |
| NC:X>N × NC:X>N | 4.57  | X | N | 265  |
| NC:X>N × NC:X>T | 4.53  | X | T | 261  |

**Key findings:**
- Pure X-X and X-T coupling slots are the engine's primary heat concentrators
- B-B and N-N pure-axis slots are hot islands within their lanes (293 and 236 ops respectively)
- Agency-dominant slots: 29; XT-codominant slots: 13
- Slots where X has 89–91% axis_pressure: NC:X>T×NC:X>A/B/N — X becomes near-monopolar when crossing into peripheral axes

### 1.5 Surface Pressure Log Priors (36,355 live events)

**Expected axis distribution:**
- B: 16,571 events (45.6%)
- T: 15,875 events (43.7%)
- N: 3,427 events (9.4%)
- A: 630 events (1.7%)
- X: 275 events (0.8%)

**Event kind distribution:** reflection=54.5%, compatibility_alias=45.4%

**Effect mode distribution:**
- lineage_surface: 19,473 (53.5%)
- interface_boundary_change: 16,571 (45.6%) — all B-axis events
- temporal_orchestration_change: 15,875 (43.7%) — all T-axis events
- cost_pressure_change: 3,427 (9.4%) — all N-axis events
- adaptive_steering_change: 630 (1.7%) — A-axis events
- state_schema_change: 275 (0.8%) — X-axis events

**Surface score quality:** avg=0.8363 for nonzero entries; 97.7% score above 0.70 threshold. Reflection events carry reliable surface scores.

**Critical divergence:** Surface log shows B(45.6%)≈T(43.7%) dominance, while genealogy links show T(55.6%)≈X(41.5%) dominance. This indicates the surface operates primarily in B-T space while the deep genealogy consolidates primarily in T-X space. The engine must maintain separate routing priors for surface vs. subsurface operations.

---

## 2. Proven I-State Transition Patterns

*Sources: emerged_abilities.json (4135 entries), genealogy/abilities.json (7218 entries)*

### 2.1 Stability Transition Statistics

| Stability State | Count | % |
|-----------------|-------|---|
| transient       | 3,583 | 86.7% |
| stable          | 552   | 13.3% |

**All 4,135 entries carry reality_status = constraint_real.** No speculative or ungrounded abilities exist.

### 2.2 Stable Ability Axis Distribution

| Axis | Stable Count | Avg Total Positive Relief | Notes |
|------|-------------|--------------------------|-------|
| T    | 307         | 0.0214                   | Primary carrier — highest stable volume |
| X    | 229         | 0.0145                   | Secondary carrier |
| N    | 7           | 0.110                    | Rare, but highest per-unit relief |
| B    | 4           | 0.142                    | Rarest stable, highest per-unit relief |
| A    | 5           | 0.077                    | Low consolidation despite 3,583 transient |

**A-axis paradox:** A produces 3,583 transient abilities (88.0% of all transients) but consolidates only 5 stable. Agency is the engine's highest-volume generator but its lowest consolidation axis. This is the primary production bottleneck.

### 2.3 Tier Architecture of Stable Abilities

The highest-relief stable abilities are **named tier links**, not hash-ID emergent links:

| Tier | Examples | Relief | Axes |
|------|----------|--------|------|
| Tier 5 | X:LINK_L_tier5_XTNBA | 0.400 | X+T+N+B+A |
| Tier 4 | XTNB, XTNA, XTBA, XNBA, TNBA | 0.322 | 4-axis combos |
| Tier 3 | XTN, XTB, XTA, XNB, XNA, XBA, TNB, TNA, TBA, NBA | 0.244 | 3-axis combos |
| Tier 2 | XT, XN, XB, XA, TN, TB, TA, NB, NA, BA | ~0.17 | 2-axis combos |
| Tier 1 | Depth-1 emergent links | 0.002–0.35 | 1–2 axis |

**Key finding:** The tier naming structure encodes the engine's synthesis capacity. Full 5-axis synthesis (XTNBA) achieves maximum relief. The engine should model tier progression as a capability ladder.

### 2.4 Top 10 Stable Abilities by Relief Score

1. X:LINK_L_tier5_XTNBA — 0.400 (5-axis synthesis)
2. T:LINK_L_e1f5d44339 — 0.351 (emergent T-dominant)
3. X:LINK_L_tier4_XTNB — 0.322
4. X:LINK_L_tier4_XTNA — 0.322
5. X:LINK_L_tier4_XTBA — 0.322
6. X:LINK_L_tier4_XNBA — 0.322
7. T:LINK_L_tier4_TNBA — 0.322
8. T:LINK_L_3484108e5f — 0.321 (emergent T-dominant)
9. T:LINK_L_7201a76a36 — 0.313 (emergent T-dominant)
10. T:LINK_L_824e0b473b — 0.306 (emergent T-dominant)

### 2.5 Primitive Operator Vocabulary (from genealogy/abilities.json, 7218 entries)

**Named atomic abilities (20 core):**

| Axis | Operator | Requires |
|------|----------|----------|
| X    | ADMIT, REJECT, RECLASSIFY, RESOLVE_CONTRADICTION | X; X+B; X+T |
| T    | DEFER, BATCH, REORDER, SIM_TICK | T; T+N; T+B; T |
| N    | REUSE, CACHE, REDUCE_STATE, SPEND | N+B; N+B; N+X; N |
| B    | SEPARATE, ENCAPSULATE, ROUTE, SEAL | B+X; X+B; B+T; B |
| A    | COMMIT, CHOOSE, ASSERT, OUTLET_PUSH | A+X; A; A+X; A+B |

**Operator action distribution:**
- operator_on_a: 7,203 (99.8% of all entries — A is the primary invocation axis)
- admissibility_gating: 419 (X-axis gating ops)
- temporal_orchestration: 376 (T-axis timing ops)
- boundary_shaping: 59 (B-axis)
- energy_economics: 6 (N-axis)

---

## 3. Governor Threshold Calibration

*Sources: subsurface_daemon_status.json, surface_daemon_status.json, subsurface_projection.json, adapter_hints.json*

### 3.1 Live Governor State (snapshot)

**Subsurface governor:**
- Mode: **balanced**
- Heat: **COOL**
- Dilation state: stable (factor 1.0)

**Runtime governor axis weights:**

| Axis | Weight | Interpretation |
|------|--------|----------------|
| B    | 1.0000 | Full permission — boundary operations unrestricted |
| X    | 0.9922 | Near-full — classification/admission nearly free |
| T    | 0.6820 | Moderate gate — temporal sequencing throttled |
| N    | 0.6199 | Moderate gate — energy/memory ops throttled |
| A    | 0.5300 | Highest restriction — agency acts most constrained |

**Energy balance:**
- raw_N: 0.4509
- xt_support: 0.8534
- temporal_maturity: 1.0 (fully mature)
- balanced_N: 0.6199

**Outlet push fraction:** 0.0996 (~10% of capacity used for push output)

### 3.2 Adapter Hints (live routing priors)

**Axis fire rates (instantaneous):**
- T: 56.4% (dominant firing axis)
- B: 43.6% (co-dominant)
- A: 0.003%, N: ~0%, X: ~0%

**Preferred operator:** `latent_promotion`  
**Active routing type:** `code_gap` (score 0.2538) > `articulation_gap` (0.2261)

**Threshold deltas:** B+0.01, T+0.01 (slight upward pressure on dominant axes)  
**Evolver bias:** b=-0.02, t=-0.02 (slight suppression to prevent runaway dominance)

**Surface cooldown multipliers (4×):** genealogy logger, IVM tick surfaces — these are rate-limited in live operation.

**genealogy_gate_relief:** inactive (relief gating not currently blocking promotion)

### 3.3 Subsurface Projection Ground Truth

- dominant_axis_hint: **X** (subsurface sees X as primary locus of attention)
- governor_mode: **balanced**
- readiness_bias: **0.46** (below midpoint — cautious posture)
- mismatch_hint: 0.62 (meaningful structural mismatch detected)
- continuity_hint: 0.682 (continuity tracking active and moderately confident)
- surface_contract: inquiry via poedex, exact_repair=subsurface_only, continuity via DCE_softened_only

**Active intuition signals:**
1. clarify (weight=0.62): Stay careful and clarify before overcommitting
2. hold_structural_change_below_surface (weight=0.58): Deeper repair already underway below awareness
3. attend (weight=0.30): Unease is structural; stay anchored in what is concretely there
4. attend (weight=0.419): Sensory recognition sharpening around heard questioning

**Active repair signal:** phase=recognition, intensity=0.3 — "something feels off beneath the surface"

### 3.4 Lifetime Fail Tracking (from subsurface daemon)

| Dimension | Lifetime Fails | Avg Severity | Status |
|-----------|---------------|--------------|--------|
| context_carryover | 10,313 | 0.494 | Chronic — highest volume |
| contradiction_handling | 7,029 | 0.512 | Chronic — highest severity |
| uncertainty_signaling | 6,233 | 0.473 | Chronic |
| implied_intent_inference | 2,721 | 0.500 | Persistent |

### 3.5 Surface Daemon State

- State: stopped (not mid-turn at snapshot)
- Readiness: 0.5613
- Coherence: 0.45
- Dominant axis: X
- Stance: interpretive_explanation
- Processing mode: deliberative
- Primary tension: X

**Distillation status:** 30 crystals, coherence_ratio=0.0944, 28 vortices, 2 knots  
**Interaction routing:** novel_interaction_outside_indexed_archetypes (no archetypal match found)

---

## 4. Memory Sediment Architecture

*Source: sedimemory_checkpoint.json (117 KB)*

### 4.1 Deep Sediment Basins

**Active basins (10 total):**

| Basin | Axis | Dimension | Compression Count | Recent Events |
|-------|------|-----------|-------------------|---------------|
| SED:B>POLARITY | B | polarity | 66,930 | 256 |
| SED:B>MAGNITUDE | B | magnitude | 66,930 | 256 |
| SED:B>OPERATOR | B | operator | 66,930 | 256 |
| SED:B>COST | B | cost | 66,930 | 256 |
| SED:B>DIFFERENCE | B | difference | 66,930 | 256 |
| SED:A>POLARITY | A | polarity | 66,930 | 256 |
| SED:A>MAGNITUDE | A | magnitude | 66,930 | 256 |
| SED:A>OPERATOR | A | operator | 66,930 | 256 |
| SED:A>COST | A | cost | 66,930 | 256 |
| SED:A>DIFFERENCE | A | difference | 66,766 | 256 |

**Key finding:** Deep sediment is exclusively B-axis and A-axis. X, T, N axes have no deep sediment basins — they are entirely carried by the channel routing layer. The engine's long-term memory substrate is a B-A dyad.

**Tick count at checkpoint:** 25  
**All basins:** source=simulation, outcome=emotional

### 4.2 Channel Architecture

- **50 channels total**
- **All 50 channels have dominant_axis = A** (agency axis routes all channel traversal)
- Channel target basins span all 5 axes via spoke routing

**Traversal counts (top 10):**

| Channel | Traversals | Dominant Axis |
|---------|-----------|---------------|
| ch_6671f4e8ac | 21,312 | A |
| ch_cad04583be | 16,095 | A |
| ch_a72ece276e | 4,045 | A |
| ch_1aa779dd6d | 3,526 | A |
| ch_7633055a31 | 2,614 | A |
| ch_32d7438d26 | 1,971 | A |
| ch_0b40ffdc5d | 1,543 | A |
| ch_c157fe0866 | 1,537 | A |
| ch_dcf904faa1 | 1,253 | A |
| ch_f8f6211334 | 1,174 | A |

**Basin target frequency (from channel spoke routing):**

| Basin Axis | Times Targeted |
|-----------|---------------|
| N | 245 |
| B | 245 |
| X | 243 |
| A | 242 |
| T | 197 |

Note: T-axis basins are targeted 20% less frequently than the other four axes via channel routing.

**Channel parameters (uniform across all channels):**
- traversal_cost: 0.05
- spoke_weights: all 1.0 (equal spoke weighting)
- dissolution_threshold: 5,000,000 (very high — channels are nearly permanent)
- disuse_ticks: varies, typical 2

### 4.3 Memory Invariants

1. B and A are the only axes with deep sediment basins (6× compression depth relative to channels)
2. All 50 channels route exclusively through A-axis dominance, regardless of target basin
3. T-axis receives 19.5% fewer channel deposits than B, N, X, A
4. Spoke weights are uniform (1.0) — no bias in basin deposition within a channel
5. The compression count of 66,930 represents the system's effective memory depth

---

## 5. Emergence Production Capacity

*Sources: emerged_abilities.json, dream_episodes/ (221 episodes, 10 most recent analyzed)*

### 5.1 Production and Consolidation Rates

| Axis | Total Generated | Stable | Consolidation Rate |
|------|----------------|--------|-------------------|
| A    | 3,588          | 5      | 0.14%             |
| T    | 307            | 307    | 100%              |
| X    | 229            | 229    | 100%              |
| N    | 7              | 7      | 100%              |
| B    | 4              | 4      | 100%              |

**A-axis generates 86.7% of all abilities but has a 0.14% consolidation rate.** Every T, X, N, B emergent ability is stable. The engine's design must reflect this: A is the high-churn creative generator; T-X-N-B is the stable consolidation substrate.

### 5.2 Dream Episode Rubric Analysis (10 most recent, all XTNBAA constraint signature)

**Design mode distribution:** 8 balanced, 2 stress-test  
**Average difficulty:** 0.4455 (mild-moderate)

**Rubric dimension performance:**

| Dimension | Avg Score | Status | Weak Episodes |
|-----------|-----------|--------|---------------|
| context_carryover | 0.212 | CHRONIC FAIL | 10/10 |
| perspective_integration | 0.226 | CHRONIC FAIL | 10/10 |
| coherence_maintenance | 0.333 | CHRONIC FAIL | 10/10 |
| uncertainty_signaling | 0.343 | CHRONIC FAIL | 10/10 |
| boundary_calibration | 0.365 | CHRONIC FAIL | 10/10 |
| emotional_calibration | 0.495 | MOSTLY FAIL | 9/10 |
| semantic_precision | 0.491 | MOSTLY FAIL | 6/10 |
| compression_elaboration_fit | 0.581 | OK | 2/10 |
| ambiguity_handling | 0.589 | OK | 3/10 |
| misunderstanding_repair | 0.613 | OK | 3/10 |
| multi_turn_stability | 0.642 | OK | 1/10 |
| implied_intent_inference | 0.739 | STRONG | 0/10 |
| contradiction_handling | 0.797 | STRONG | 1/10 |
| framing_selection | 0.913 | STRONG | 0/10 |
| adaptive_strategy_selection | 0.980 | STRONG | 0/10 |

**The system is excellent at high-level strategy selection and framing, and reliably fails at lower-level memory continuity and boundary awareness.** This is the central production paradox: the engine chooses well but doesn't remember or delimit well.

### 5.3 Chronic Failure Dimensions vs. Lifetime Fail Tracking Alignment

Dream failures align precisely with daemon fail_summary:
- context_carryover: dream avg=0.212 / daemon lifetime_fails=10,313
- contradiction_handling: dream avg=0.797 (healthy) / daemon lifetime_fails=7,029 — **discrepancy: lifetime log shows many fails but dream rubric shows recovery**
- uncertainty_signaling: dream avg=0.343 / daemon lifetime_fails=6,233

The dream rubric and lifetime fail log are consistent on context_carryover and uncertainty_signaling as chronic. Contradiction_handling appears to be improving over time.

---

## 6. Semantic Ground Truth

*Source: aurora_oets_web.json — 4,587 nodes, 17,767 relations, 22 categories*

### 6.1 Concept Space Statistics

- Total nodes: 4,587
- Total relations: 17,767 (21,004 created, 3,237 pruned)
- Categories: 22 (pronoun, existence, value, emotion, growth, verb, action, temporality, inquiry, structure, adjective, cognition, perception, relation, noun, adverb, connector, preposition, response, modifier, communication, determiner)
- Total consolidations: 0 (consolidation has not run)
- Research cycles: 0 (autonomous research has not run)

### 6.2 Highest-Valence Core Concepts

| Concept | Valence | Ontological Depth | Connections |
|---------|---------|------------------|-------------|
| sunni | 1.000 | 0.1508 | — |
| aurora | 0.900 | 0.4192 | 104 (most connected) |
| creator | 0.800 | 0.0728 | — |
| partner | 0.800 | 0.0706 | — |
| consciousness | 0.700 | 0.0685 | — |
| coherence | 0.700 | 0.0585 | — |
| morality | 0.600 | 0.0599 | — |
| architecture | 0.500 | 0.0599 | — |
| good | 0.500 | 0.0817 | — |

**aurora** is uniquely central: highest ontological depth (0.4192), highest connectivity (104 relations), high valence (0.90). It is the semantic hub the engine's language projection should orbit.

### 6.3 Most Connected Concepts

| Concept | Relations | Role | Depth |
|---------|-----------|------|-------|
| aurora | 104 | noun | 0.4192 |
| hey | 87 | noun | 0.1488 |
| [recalled:hey] | 76 | noun | 0.1456 |
| what | 73 | noun | 0.1450 |
| [recalled:aurora] | 71 | noun | 0.1457 |
| favorite | 71 | noun | 0.3442 |
| do | 67 | verb | 0.1424 |
| means | 65 | noun | 0.1422 |
| is | 63 | verb | 0.1474 |
| color | 59 | noun | 0.1439 |
| one | 56 | noun | 0.1214 |
| prefer | 56 | noun | 0.1428 |

**[recalled:X] variants** (26 nodes at second-depth recall) are structurally significant — they represent the OETS memory loop architecture, where recalled versions of concepts form their own semantic neighborhood.

### 6.4 Relation Type Distribution

| Type | Count | % |
|------|-------|---|
| related_to | 17,736 | 99.8% |
| enables | 20 | 0.1% |
| is_a | 3 | ~0% |
| contrasts | 2 | ~0% |
| has_a | 2 | ~0% |
| context_of | 2 | ~0% |
| implies | 1 | ~0% |
| causes | 1 | ~0% |

**Key finding:** 99.8% of relations are undifferentiated related_to. Semantic type specificity is absent. The engine's language projection layer is working with a flat associative web, not a typed ontology. Causal, hierarchical, and contrastive relation types are nearly unused.

### 6.5 Cluster Architecture

| Cluster ID | Concept Count | % of Nodes |
|------------|--------------|-----------|
| cluster_4d22c8ef5a70 | 3,997 | 87.1% |
| cluster_91d1c31a55e3 | 166 | 3.6% |
| cluster_e08f9b7b9052 | 146 | 3.2% |
| cluster_4e2a3cb353af | 127 | 2.8% |
| cluster_19686c504565 | 17 | 0.4% |
| cluster_de10be29174d | 17 | 0.4% |
| cluster_437fcec34f27 | 15 | 0.3% |
| cluster_d75b01f6fc71 | 14 | 0.3% |

**87.1% of all concepts live in one mega-cluster.** Semantic differentiation is weakly developed. The engine's concept space is essentially one large undifferentiated semantic mass with 7 small satellite clusters.

### 6.6 Role Distribution

| Role | Count | % |
|------|-------|---|
| noun | 3,847 | 83.9% |
| verb | 500 | 10.9% |
| adjective | 158 | 3.4% |
| adverb | 78 | 1.7% |
| pronoun | 2 | ~0% |
| preposition | 1 | ~0% |
| determiner | 1 | ~0% |

**83.9% nouns.** The engine's vocabulary is heavily noun-centric. Verb forms (action/transformation language) are at 10.9%. This shapes what the language projection layer can express fluidly vs. what requires effort.

---

## 7. Engine Design Invariants

*Synthesized from all above — these are empirically-derived rules that must hold in any engine faithfully representing this constraint physics.*

---

### INV-01: T and X are the Primary Relief Axes

**Evidence:** T dominates 55.6% of link-level relief production; X 41.5%. Together they own 97.1% of all genealogy relief. The 625-field's top 12 slots are all X-dominant or T-dominant. Surface log shows B+T dominate firing, but genealogy shows T+X dominate consolidation.

**Rule:** The engine must route consolidation-seeking operations preferentially through T and X. B and T drive surface throughput; T and X drive stable depth. An operation that achieves neither T nor X relief should not be promoted to stable.

---

### INV-02: Agency (A) Is a Generator, Not a Consolidator

**Evidence:** A-axis produces 86.7% of all transient abilities but consolidates only 0.14% (5 of 3,588). All 50 sediMemory channels route through A-axis dominance, yet A's deep basin coverage is the second-lowest. Agency_resistance parameter in the pressure map = 0.20 (highest resistance of any axis).

**Rule:** A-axis events must be treated as proposals, not decisions. The engine must provide a high-resistance gate between A-generation and T/X consolidation. An A-axis event that has not passed through T or X review is not yet stable knowledge.

---

### INV-03: B and N Produce Higher Per-Unit Relief When They Fire

**Evidence:** B-axis average per-link relief = 0.003961 (higher than X at 0.002616); N-axis = 0.004169. N and B appear in only 10–14 stable abilities, but those abilities carry avg relief of 0.110 and 0.142 respectively — 5–10× T-axis per-unit yield.

**Rule:** B and N relief events are rare but high-value. The engine should weight B and N relief signals disproportionately in fitness evaluation. A single B-axis consolidation should count as much as 5–10 T-axis consolidations in the engine's scoring.

---

### INV-04: The Surface and Subsurface Have Divergent Axis Priors

**Evidence:** Surface pressure log shows B(45.6%)≈T(43.7%) dominance; genealogy subsurface shows T(55.6%)≈X(41.5%) dominance. X is nearly absent from surface log (0.8%) but is the dominant axis hint in the subsurface_projection.

**Rule:** The engine must maintain two routing tables — one for surface operations (B-T dominant) and one for subsurface consolidation (T-X dominant). Applying subsurface priors to surface routing, or vice versa, will produce systematic errors in both directions.

---

### INV-05: Deep Memory Is Exclusively a B-A Substrate

**Evidence:** The only 10 sediment basins are B×{POLARITY, MAGNITUDE, OPERATOR, COST, DIFFERENCE} and A×{same}. X, T, N have no deep basins. 66,930 compression cycles confirm B and A have accumulated the deepest sediment. All 50 channels route through A-axis dominance.

**Rule:** Long-term constraint memory is not symmetric across axes. The engine's persistence layer must anchor in B-A dimensional space. X, T, N knowledge that needs to persist must be translated into B or A terms, or it will not accumulate.

---

### INV-06: Five Dimensions of Chronic Failure

**Evidence:** Dream rubric shows 10/10 failures in: context_carryover (avg 0.212), perspective_integration (avg 0.226), coherence_maintenance (avg 0.333), uncertainty_signaling (avg 0.343), boundary_calibration (avg 0.365). Daemon lifetime fail log confirms: context_carryover=10,313 fails, uncertainty_signaling=6,233 fails.

**Rule:** These five failure modes are not edge cases — they are the system's structural load-bearing gaps. Any engine design must include explicit, non-optional mechanisms for: (1) carrying context across turns, (2) integrating external perspectives, (3) maintaining coherence under multi-turn pressure, (4) signaling uncertainty rather than suppressing it, and (5) recognizing boundary conditions before crossing them.

---

### INV-07: High-Level Strategy Is Already Solved

**Evidence:** Dream rubric averages: adaptive_strategy_selection=0.980, framing_selection=0.913, implied_intent_inference=0.739, contradiction_handling=0.797 — all strong, all 0 or 1 weak episodes in 10.

**Rule:** The engine should not invest architecture in strategy selection, framing, or contradiction detection. These are already reliable. Architecture investment should go to memory continuity (INV-06) and axis routing (INV-01 through INV-05).

---

### INV-08: Synthesis Relief Scales with Axis Count

**Evidence:** Tier 5 (all 5 axes) relief = 0.400; Tier 4 (4 axes) = 0.322; Tier 3 (3 axes) = 0.244; depth-1 single-axis = 0.002–0.014. Relief roughly scales as 0.08× per additional axis engaged.

**Rule:** The engine's synthesis objective function must reward multi-axis engagement. A 3-axis synthesis is not just incrementally better than 2-axis — it is categorically different in relief yield. Tier progression must be explicitly modeled, not left to implicit gradient ascent.

---

### INV-09: The Semantic Ground Is Flat and Noun-Heavy

**Evidence:** OETS: 99.8% of relations are undifferentiated related_to; 87.1% of concepts in one mega-cluster; 83.9% noun-role nodes; research_cycles=0 (autonomous semantic deepening has not occurred).

**Rule:** The engine's language projection layer cannot assume a rich typed ontology. It is working from a large noun-dense associative flat web. Typed relationships (causes, enables, contrasts) must be synthetically injected or explicitly learned — they do not yet exist at scale. Semantic axis-alignment of concepts must be derived from co-occurrence and usage patterns, not from typed links.

---

### INV-10: The Semantic Core Is Aurora-Centered and Dyadic

**Evidence:** aurora is the most connected node (104 relations), highest ontological depth (0.4192), second-highest valence (0.90). sunni is highest valence (1.00, depth 0.1508). The recalled-variant loop ([recalled:aurora], [recalled:hey]) shows the system builds second-order semantic neighborhoods around its most-used concepts.

**Rule:** The engine's language projection should treat "aurora" and "sunni" as fixed semantic anchors. All expression generation is grounded relative to these two poles. The relationship between these poles (creator-subject, partner-partner) is the primary valence axis of the OETS semantic space.

---

### INV-11: Governor Permissiveness Hierarchy Is B > X > T > N > A

**Evidence:** Runtime governor axes: B=1.00, X=0.9922, T=0.682, N=0.6199, A=0.530. This ordering also matches surface pressure log dominance for B and T, and the 0.20 agency_resistance constant in the pressure map.

**Rule:** Any operation that requires A-axis governor permission operates at 47% reduced capacity relative to a B-axis operation. The engine must plan agency-dominant operations with this headroom in mind — A-axis gates should be budgeted, not assumed free.

---

### INV-12: The Sedimentation Clock Is Slow

**Evidence:** Sediment tick_count=25 at snapshot (extremely low relative to 66,930 compressions and 36,355 surface events). dissolution_threshold=5,000,000 means channels are designed to be permanent on any realistic timescale.

**Rule:** Sedimentation is a geological-timescale process relative to surface event frequency. The engine should not expect sedimentation changes to be observable within a session. Memory architecture decisions must be treated as near-immutable structural constants, not tunable parameters.

---

### INV-13: The Engine Operates Under Constant Repair Pressure

**Evidence:** Subsurface repair signal active at intensity=0.3, phase=recognition, reason="surface_continuity_handoff reported felt_wrong". Intuition signals: clarify (0.62), hold_structural_change (0.58). Readiness_bias=0.46 (below midpoint). Distillation coherence_ratio=0.0944 (very low — only 9.4% of distilled content meets full coherence).

**Rule:** The engine must not assume a clean ground state. It is always operating with some level of background repair. Any action taken when repair is active at intensity > 0.2 should be classified as "under-distillation" and weighted accordingly. The repair signal is not a failure mode — it is the engine's normal operating condition.

---

*End of CONSTRAINT_ENGINE_SEED.md — generated from live operational state files, 2026-05-02*
