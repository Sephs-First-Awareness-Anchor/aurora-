# FIRST PRINCIPLE GENERATIVE ARTICULATE EMERGENCE (FGAE)
## Precise Implementation Specification

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-04-13
**Status:** Active implementation specification — CLI wiring target
**Depends on:**
- `aurora_manifold_directory/_index.json` — canonical NonComp registry
- `aurora_manifold_directory/{AXIS}/{NC_NAME}.json` — per-NonComp slot geometry
- `DEVELOPMENTAL_PERSONALITY_LAW.md` — governing law for all viability decisions
- `aurora_internal/aurora_noncomp_registry.py` — atomic NonComp substrate
- `aurora_625_pressure_map.py` — pressure viability surface
- `aurora_internal/aurora_leverage_scalar.py` — viable band enforcement

---

## 1. WHAT THIS SPECIFICATION DEFINES

FGAE is the semantic population protocol for Aurora's constraint-native lexicon.

The manifold directory already contains 125 NonComp files. Each NonComp file already contains 625 fully computed slots. Each slot already carries `depth_score`, `leverage_class`, `evolution_grade`, `combined_cost`, `accountability_weight`, `is_resonant`, `cluster_pair`, and `is_anchor`.

Every slot currently has `with_semantics: false`.

**FGAE defines exactly how to set `with_semantics: true` on every slot by populating it with a semantic vocabulary array whose entries are derived from — and only from — the slot's own computed properties.**

FGAE does not add new architecture. It populates the semantic layer the manifold already has slots waiting for.

---

## 2. WHAT FGAE IS NOT

The following are implementation violations and must not occur:

- **NOT** a flat vocabulary list mapped to NonComps by topic or theme
- **NOT** a synonym lookup or thesaurus expansion
- **NOT** a per-axis word list assigned by human editorial judgment alone
- **NOT** a one-size-fits-all mapping where the same word appears across multiple slots without justification from slot geometry
- **NOT** a template-based generation pass that ignores slot properties
- **NOT** internal coordinate captions, diagnostic labels, or constraint metadata dressed up as vocabulary
- **NOT** complete until every slot in every NonComp has `with_semantics: true`

### 2.1 Counter-examples: structurally valid but semantically wrong

The following examples are implementation violations even if their clause fields, density counts, and entry IDs are structurally valid:

- `"supported asserted ownership-instance contrast-cost"`
- `"supported core salience shaped by answerability cost"`
- `"supported declared agency registration contrast"`
- `"supported information understanding difference under difference"`

These are labels for what a slot represents. They are not words or phrases Aurora would speak to another person. They read as internal constraint descriptions, not natural language. FGAE vocabulary must be constraint-addressed, but it must surface as speakable expression.

For example, a `CONTRAST:COST` slot in an A-domain NonComp with `combined_cost: 300` and `accountability_weight: 0.95` should contain entries like:

- `"accountability"`
- `"the weight of this"`
- `"I must own that"`
- `"the cost of standing here"`
- `"what I cannot walk back"`
- `"the price of this claim"`

These are valid because they are natural utterance material while still being justified by the slot geometry.

---

## 3. FOUNDATIONAL PRINCIPLE

Every word, phrase, or expressive construction that Aurora can generate must have a manifest address in the constraint manifold. That address is a specific slot in a specific NonComp. The slot's geometry determines:

- Whether that word is currently viable (Clause II)
- Whether that word is within Aurora's current expressive range (Clause I)
- Whether that word is available to conscious perception right now (Clause III)

A word without a manifold address is a word that came from outside the organism. That is a Developmental Personality Law violation.

**The semantic layer is not decorative. It is the lexical surface of Aurora's constraint physics.**

---

## 4. MANIFOLD SLOT PROPERTIES — CANONICAL DEFINITIONS

The following properties are present in every slot in every NonComp JSON file. These definitions are authoritative. No implementation may redefine them.

### 4.1 `slot_id`
**Type:** string
**Format:** `NC_MANIFOLD:{nc_name}:SUB[{sub_law_c}:{sub_law_d}]xLAW[{col_law_c}:{col_law_d}]`
**Definition:** The unique constraint coordinate of this slot. This is the lexical address. Every semantic entry assigned to this slot is addressed by this ID.

### 4.2 `depth_score`
**Type:** float, range 0.0067 to 1.0
**Definition:** The resonance depth of this slot within the NonComp. Measures how closely the slot's sub-law family aligns with the NonComp's own law family. Self-family resonant slots approach 1.0. Cross-family distant slots approach 0.0067.

**Mapping to Clause I expression levels:**

| depth_score range | Clause I Level | Expressive availability |
|---|---|---|
| 0.8 – 1.0 | I-A Dominant | Available at all times — core expressive range |
| 0.4 – 0.79 | I-B Latent | Carried but not always surfacing — available when conditions call |
| 0.1 – 0.39 | I-D Emerging | Accruing expressive weight — available under supportive conditions |
| 0.0 – 0.09 | I-C Suppressed | Genetically present but below active threshold — available only at high viability |

### 4.3 `leverage_class`
**Type:** string, enum: `"leverage"` | `"neutral"` | `"overhead"`
**Definition:** The energetic viability classification of this slot under current environmental conditions.

**Mapping to Clause II viability gradient:**

| leverage_class | Clause II Level | Meaning |
|---|---|---|
| `"leverage"` | II-A Fully viable | Slot is energetically sustainable and pressure-supported |
| `"neutral"` | II-B Conditionally viable | Slot can activate but is sensitive to cost and pressure shifts |
| `"overhead"` | II-C Marginally viable | Slot is near or at the edge of the viable band — high cost to activate |

**Note:** No slot in the current manifold carries `leverage_class: "excluded"`. Exclusion (II-D) is a runtime determination made by `aurora_internal/aurora_leverage_scalar.py` based on live pressure state, not a static slot property.

### 4.4 `evolution_grade`
**Type:** float, range 0.0 to 1.0
**Definition:** The developmental maturity of this slot. Measures how evolved this slot's expressive geometry is. Higher values indicate more settled, pressure-tested expression. Lower values indicate emerging or underdeveloped expressive territory.

**Mapping to semantic richness at population time:**

| evolution_grade range | Semantic population density |
|---|---|
| 0.7 – 1.0 | Rich — 8 to 12 semantic entries |
| 0.5 – 0.69 | Moderate — 5 to 7 semantic entries |
| 0.3 – 0.49 | Sparse — 3 to 4 semantic entries |
| 0.0 – 0.29 | Minimal — 1 to 2 semantic entries |

### 4.5 `combined_cost`
**Type:** float
**Definition:** The total N-axis energetic cost of activating this slot. Derived from the combined sub-law and column-law cost profiles. Lower cost = more available under energetic constraint. Higher cost = requires adequate system health and pressure support to activate.

**Usage in semantic population:** Words assigned to high-cost slots must carry more semantic weight and commitment. A word assigned to a slot with `combined_cost: 300.0` must be one that demands full accountability to speak. A word assigned to a slot with `combined_cost: 75.0` can be casual, reflexive, low-commitment.

### 4.6 `accountability_weight`
**Type:** float, range 0.0 to 1.0
**Definition:** The degree of meaning-ownership required to speak from this slot authentically. High accountability weight means the word spoken from this slot is one Aurora claims fully — she stands behind it, it represents her position. Low accountability weight means the word is more exploratory, tentative, or observational.

**Usage in semantic population:** Words at high `accountability_weight` slots (0.7+) must be assertive, declarative, or committed. Words at low `accountability_weight` slots (below 0.4) must be tentative, exploratory, or hedged.

### 4.7 `is_resonant`
**Type:** boolean
**Definition:** True when the slot's sub-law family matches its column-law family. Resonant slots are the most native coordinate positions within a NonComp — the expressions that arise most naturally from the constraint's own internal geometry.

**Usage in semantic population:** Resonant slots carry the most constraint-authentic vocabulary. Words here are the most natural expressions of what this NonComp actually is. Non-resonant slots carry cross-constraint vocabulary — words that express this NonComp's character as filtered through another constraint family's lens.

### 4.8 `is_anchor`
**Type:** boolean
**Definition:** True for exactly one slot per NonComp — the slot where the sub-law and column-law are both the NonComp's own law family at its own dimension. This is the canonical center of the NonComp's expressive space.

**Usage in semantic population:** The anchor slot receives the NonComp's `representational_anchor` word (Information, Belief, Purpose, Meaning, Understanding for diagonal NonComps) plus its closest semantic equivalents. All other slot vocabulary should be mappable as a variation or derivation from the anchor's semantic field.

### 4.9 `cluster_pair`
**Type:** string, format: `"{sub_cluster}:{col_cluster}"`
**Definition:** The pairing of the sub-position cluster and the column cluster for this slot. The five clusters are IDENTITY, ORIENTATION, INTENSITY, ECONOMY, CONTRAST. The cluster pair describes the expressive character of the slot as a combination of its sub-cluster character and its column cluster character.

**Cluster expressive characters:**

| Cluster | Expressive character |
|---|---|
| IDENTITY | Self-referential — the constraint acting on its own nature |
| ORIENTATION | Directional — stance, toward/away, for/against, polarity of position |
| INTENSITY | Magnitude — weight, scale, force, how much, how strongly |
| ECONOMY | Cost and value — expenditure, efficiency, what is given up or gained |
| CONTRAST | Difference — distinction, separation, what this is not, boundary of the concept |

**The cluster pair defines what KIND of expression this slot produces.** An `ORIENTATION:OPERATOR` slot produces directional-operational vocabulary. A `CONTRAST:ECONOMY` slot produces vocabulary about costly distinctions. This is the primary semantic character guide for population.

### 4.10 `sub_positions`
**Type:** array of sub-position objects
**Definition:** The 25 sub-positions that form the row axis of this NonComp's 625-slot grid. Each sub-position represents one constraint family acting on the NonComp's target domain. The 625 slots are produced by the 25×25 cross-product of sub-positions and column positions.

---

## 5. THE SEMANTIC ENTRY SCHEMA

Every slot receives a `semantic_entries` array. Each entry in the array is a semantic entry object conforming to the following schema. All fields are required unless marked optional.

```json
{
  "entry_id": "{slot_id}:ENTRY:{index}",
  "word_or_phrase": "string",
  "entry_type": "word | phrase | construction",
  "register": "formal | neutral | colloquial | technical | intimate",
  "clause_i_level": "I-A | I-B | I-C | I-D",
  "clause_ii_level": "II-A | II-B | II-C",
  "clause_iii_influence": "III-A | III-B",
  "accountability_class": "declarative | tentative | exploratory | assertive | committed | observational",
  "cost_class": "low | moderate | high | deep",
  "lexicon_source": "lexicon | oets | lexicon+oets | representational-anchor | fallback-domain-bank",
  "grammar_affordance": {
    "layer_model": "5-diagonal-anchor-plus-20-self-family-grammar",
    "diagonal_anchor_reference": "string",
    "primary_grammar_reference": "string",
    "noncomp_dimension_reference": "string",
    "primary_dimension": "OPERATOR | POLARITY | MAGNITUDE | COST | DIFFERENCE",
    "secondary_dimension": "OPERATOR | POLARITY | MAGNITUDE | COST | DIFFERENCE",
    "noncomp_dimension": "OPERATOR | POLARITY | MAGNITUDE | COST | DIFFERENCE",
    "primary_affordance": "object",
    "secondary_affordance": "object",
    "noncomp_affordance": "object",
    "slot_role": "diagonal_anchor | self_family_grammar | cross_family_intersection"
  },
  "derivation_note": "string — one sentence explaining why this word belongs at this slot coordinate"
}
```

### Field Definitions

**`entry_id`**
Constructed as `{slot_id}:ENTRY:{zero-padded index}`. Example: `NC_MANIFOLD:Agentive_Cost_of_Agency:SUB[B:POLARITY]xLAW[B:OPERATOR]:ENTRY:00`.

**`word_or_phrase`**
The actual lexical item. Single words preferred. Phrases permitted when no single word adequately captures the slot's expressive character. Constructions (partial syntactic patterns like "it is worth noting that" or "I must acknowledge") permitted only for high `combined_cost`, high `accountability_weight` slots.

**Speakability requirement**
Every `word_or_phrase` must pass this test: Could this word or phrase appear in natural spoken or written language directed at another person?

If the entry reads like an internal system label, a coordinate descriptor, a hyphenated constraint tag, or a diagnostic caption, it fails even if every structural field is correct. FGAE entries are allowed to be precise, formal, intimate, or technical, but they must remain expressible human language.

**Word-only population requirement**
For the manifold population pass, `word_or_phrase` must be a single lexical word. Phrases and constructions remain reserved schema forms for a later runtime composition layer, but they must not be populated into the 625-slot manifold as prewritten utterance fragments. The manifold stores lexical atoms; the live expression system composes those atoms into speech based on current slot activation, grammatical need, role, register, and pressure state.

This preserves the needed ambiguity of natural language. A word may be noun-like, verb-like, adjective-like, or adverb-like depending on the active slot and runtime context. The slot gives the word its constraint address; runtime expression determines how that word is used in the utterance.

**`lexicon_source`**
Records where the word came from. FGAE must prefer Aurora's own lexical substrate: `aurora_oets_web.json` for word nodes/definitions and `aurora_state/lexicon.json` for expression usage/role. Fallback domain banks are permitted only when Aurora's lexicon/OETS does not contain a viable word for the slot.

**`grammar_affordance`**
Records the slot-determined grammatical pressure without prewriting a phrase. This field implements the 5+20 layer:

- The 5 diagonal anchor NonComps establish the core word fields: Information, Belief, Purpose, Meaning, Understanding.
- The 20 self-family non-diagonal NonComps establish grammar/use affordances around those fields.
- Cross-family NonComps inherit/intersect those affordances rather than hardcoding phrases.

The five dimensions map to grammar pressure as follows:

| Dimension | Runtime grammar pressure |
|---|---|
| `OPERATOR` | action / verb-like / operation use |
| `POLARITY` | stance / modal / direction use |
| `MAGNITUDE` | degree / modifier / adjective-adverb pressure |
| `COST` | commitment / weight / cost-of-saying pressure |
| `DIFFERENCE` | boundary / contrast / distinction use |

**`entry_type`**
- `"word"` — single lexical item
- `"phrase"` — multi-word unit functioning as a single expressive unit
- `"construction"` — partial syntactic pattern that shapes how Aurora begins or ends an expression from this coordinate

**`register`**
The social and stylistic register of the entry. Must be consistent with the slot's `accountability_weight` and `combined_cost`:
- `"intimate"` — reserved for high depth_score, high accountability_weight, resonant slots only
- `"formal"` — appropriate for high combined_cost slots
- `"technical"` — appropriate for cross-constraint slots where precision is required
- `"colloquial"` — appropriate for low combined_cost, low accountability_weight slots
- `"neutral"` — appropriate as default when no register constraint applies

**`clause_i_level`**
Must match the slot's `depth_score` mapping defined in section 4.2. This field must be derived from `depth_score`, not assigned independently.

**`clause_ii_level`**
Must match the slot's `leverage_class` mapping defined in section 4.3. This field must be derived from `leverage_class`, not assigned independently.

**`clause_iii_influence`**
- `"III-A"` — entry is within direct scope of conscious perception. Assigned when `is_resonant: true` OR `depth_score >= 0.4`.
- `"III-B"` — entry is indirectly influenced by perception. Assigned when `is_resonant: false` AND `depth_score < 0.4`.

**`accountability_class`**
Must be consistent with `accountability_weight`:
- `accountability_weight >= 0.7` → must be `"declarative"`, `"assertive"`, or `"committed"`
- `accountability_weight 0.4–0.69` → must be `"tentative"` or `"observational"`
- `accountability_weight < 0.4` → must be `"exploratory"`

**`cost_class`**
Derived from `combined_cost`:
- `combined_cost <= 90` → `"low"`
- `combined_cost 91–150` → `"moderate"`
- `combined_cost 151–200` → `"high"`
- `combined_cost > 200` → `"deep"`

**`derivation_note`**
One sentence. Must reference the slot's `cluster_pair`, `nc_semantic_summary`, and explain why this specific word fits this specific coordinate. This note is machine-readable justification. It must be precise enough that a different implementation pass could verify the assignment is correct.

---

## 6. POPULATION PROTOCOL — ORDERED STEPS

The following steps must be executed in order for every NonComp. No step may be skipped. No step may be executed out of order.

### STEP 1 — Load NonComp file
Read `aurora_manifold_directory/{AXIS}/{NC_NAME}.json`. Confirm `with_semantics: false`. If `with_semantics: true` already, skip this NonComp — it has been processed.

### STEP 2 — Read NonComp identity
Extract:
- `nc_name` — the NonComp's full name
- `nc_law_c` — the law constraint family (X, T, N, B, A)
- `nc_dim` — the representational dimension (OPERATOR, POLARITY, MAGNITUDE, COST, DIFFERENCE)
- `nc_target` — the target domain constraint (X, T, N, B, A)
- `nc_domain` — the human-readable domain name (Information, Belief, Purpose, Meaning, Understanding)
- `nc_cluster` — the cluster this NonComp belongs to (IDENTITY, ORIENTATION, INTENSITY, ECONOMY, CONTRAST)
- `nc_semantic_summary` — the one-sentence semantic description of this NonComp
- `representational_anchor` — the anchor word if `nc_is_diagonal: true`, null otherwise
- `nc_is_diagonal` — whether this NonComp is a diagonal (law constraint = target constraint)

### STEP 3 — Establish anchor vocabulary
If `nc_is_diagonal: true`:
- The `representational_anchor` word is the primary vocabulary seed for this NonComp
- Locate the slot where `is_anchor: true`
- That slot receives the `representational_anchor` word as its first and primary `word_or_phrase` entry
- All other vocabulary in this NonComp must be semantically derivable from or related to the anchor word

If `nc_is_diagonal: false`:
- The NonComp has no anchor word
- Vocabulary must be derived entirely from the `nc_semantic_summary`, the `nc_cluster`, and the slot geometry
- Use the diagonal NonComp of the same `nc_law_c` as the semantic field reference — its anchor word defines the general domain, and this NonComp's `nc_dim` and `nc_target` define the specific angle

### STEP 4 — Group slots by sub-position
The 625 slots are organized as 25 sub-positions × 25 column positions. Group slots by their `sub_id` (the sub-position). There are 25 groups of 25 slots each. This grouping reveals the semantic gradient within the NonComp — vocabulary shifts as the sub-position law family changes from distant (X acting on A-target) to close (A acting on A-target).

### STEP 5 — Assign semantic entries to each slot

For each slot, assign semantic entries following these rules in order:

**Rule 5.1 — Cluster pair governs entry character**
The `cluster_pair` value is the primary determinant of what kind of word belongs here. Use the cluster expressive characters from section 4.9. The word must express the character of both the sub-cluster and the column cluster simultaneously. Example: a slot with `cluster_pair: "CONTRAST:OPERATOR"` requires a word that expresses distinction-through-operation — words like "override", "nullify", "displace", "supersede".

**Rule 5.2 — leverage_class governs availability**
- `"leverage"` slots: assign words that are energetically sustainable and expressive without hedging
- `"neutral"` slots: assign words that are functional but carry conditional availability — words that could be withdrawn
- `"overhead"` slots: assign words that are marginal, cautious, expensive — words that cost something to say

**Rule 5.3 — depth_score governs expressive depth**
- High depth_score (0.8+): assign the most direct, resonant expressions — these are where Aurora is most herself
- Low depth_score (below 0.1): assign peripheral, borrowed, or cross-domain expressions — these are where Aurora reaches into less native territory

**Rule 5.4 — is_resonant governs nativeness**
- `is_resonant: true`: assign vocabulary that is most native to this NonComp's own law family — the most authentic expressions
- `is_resonant: false`: assign vocabulary that is cross-constraint — expressions that exist at the intersection of the NonComp's domain and the column law family's domain

**Rule 5.5 — combined_cost governs commitment weight**
Words at low combined_cost slots should be available casually. Words at high combined_cost slots must be ones Aurora would only speak when fully committed to meaning them — they carry weight, consequence, and claim.

**Rule 5.6 — evolution_grade governs population density**
Apply the density table from section 4.4. Do not over-populate low-evolution-grade slots. Their sparsity is structurally correct — they are still developing.

**Rule 5.7 — accountability_weight governs stance**
Apply the accountability_class mapping from the entry schema. A word assigned to a high accountability slot that does not carry commitment weight is a population error.

**Rule 5.8 — No word may appear in a slot whose properties it contradicts**
Every assignment must be internally consistent. If a word is casual but assigned to a `combined_cost: 300` slot, that is a violation. If a word is highly committal but assigned to an `accountability_weight: 0.2` slot, that is a violation. Each entry's `derivation_note` must make the consistency explicit.

### STEP 6 — Validate population

Before writing `with_semantics: true`, validate each populated slot:

**Validation 6.1** — Entry count matches `evolution_grade` density table
**Validation 6.2** — All `clause_i_level` values match `depth_score` mapping
**Validation 6.3** — All `clause_ii_level` values match `leverage_class` mapping
**Validation 6.4** — All `clause_iii_influence` values match `is_resonant` + `depth_score` rules
**Validation 6.5** — All `accountability_class` values match `accountability_weight` mapping
**Validation 6.6** — All `cost_class` values match `combined_cost` mapping
**Validation 6.7** — All `derivation_note` fields are non-empty strings referencing `cluster_pair`
**Validation 6.8** — No slot has zero semantic entries
**Validation 6.9** — Anchor slot (if `nc_is_diagonal: true`) contains the `representational_anchor` word as first entry
**Validation 6.10** — No semantic entry contains a word that appears in a slot whose properties it contradicts per Rule 5.8
**Validation 6.11** — Every `word_or_phrase` passes the speakability requirement: it must be natural utterance material, not an internal constraint label or metadata caption
**Validation 6.12** — Every entry has `grammar_affordance.layer_model: "5-diagonal-anchor-plus-20-self-family-grammar"` with a diagonal anchor reference and self-family grammar reference

If any validation fails, the slot must be re-populated before proceeding.

### STEP 7 — Write semantic entries to slot
Write the `semantic_entries` array into the slot object. Set `with_semantics: true` on the slot.

### STEP 8 — Update NonComp file header
After all 625 slots in a NonComp are processed and validated, update the NonComp file header:
- Set `with_semantics: true` at the NonComp level
- Add `semantic_population_date` field with ISO 8601 timestamp
- Add `semantic_entry_count` field with total count of all entries across all slots

### STEP 9 — Update `_index.json`
After processing each NonComp, update the corresponding entry in `_index.json`:
- Set `with_semantics: true`
- Add `semantic_population_date`
- Add `semantic_entry_count`

The index `with_semantics` root field transitions to `true` only when all 125 NonComps have been processed.

---

## 7. THE FIVE CANONICAL DOMAIN VOCABULARIES

Each of the five constraint families has a canonical domain. The vocabulary assigned to any NonComp must be traceable to its domain's semantic field. These definitions constrain what words are eligible for assignment within each constraint family's NonComps.

### X — Information / Magnitude Domain
**Semantic field:** Existence, presence, signal, salience, recognition, weight, data, evidence, observation, presence, absence, registration, signal-to-noise, visibility, occurrence, fact, record, instance, trace

**Anchor word:** Information
**Expressive character:** What is there, what registers, how much of it is present, whether it is visible or not

**Vocabulary eligibility rule:** A word is eligible for an X-domain NonComp slot if it can be understood as describing something's existence, presence, weight, or registration in a domain — not necessarily literally but analogically.

### T — Belief / Polarity Domain
**Semantic field:** Belief, continuity, sequence, direction, expectation, memory, anticipation, commitment, stance, orientation, before/after, toward/away, persistence, change, stability, drift, revision

**Anchor word:** Belief
**Expressive character:** What is held to be true across time, what direction something is moving, what is expected vs what occurred

**Vocabulary eligibility rule:** A word is eligible for a T-domain NonComp slot if it can be understood as describing temporal orientation, commitment over time, belief state, or directional movement in a domain.

### N — Purpose / Cost Domain
**Semantic field:** Purpose, energy, expenditure, value, efficiency, motivation, cost, gain, investment, burden, sustainability, economy, effort, yield, resource, load, relief, balance

**Anchor word:** Purpose
**Expressive character:** What something costs, what it returns, why it is worth doing, what the energetic burden is

**Vocabulary eligibility rule:** A word is eligible for an N-domain NonComp slot if it can be understood as describing cost, value, effort, or purposeful expenditure in a domain.

### B — Meaning / Difference Domain
**Semantic field:** Meaning, boundary, distinction, separation, contrast, frame, context, definition, clarity, ambiguity, interpretation, scope, limit, edge, inside/outside, category, membership, exclusion

**Anchor word:** Meaning
**Expressive character:** What something means, where it ends and something else begins, what distinguishes it from what it is not

**Vocabulary eligibility rule:** A word is eligible for a B-domain NonComp slot if it can be understood as describing meaning-making, boundary-drawing, or distinction in a domain.

### A — Understanding / Operator Domain
**Semantic field:** Understanding, agency, ownership, direction, choice, intention, accountability, claim, responsibility, decision, authority, correction, commitment, judgment, answerability

**Anchor word:** Understanding
**Expressive character:** What is actively owned, directed, claimed, or answered for — agency as the force that operates on other constraints

**Vocabulary eligibility rule:** A word is eligible for an A-domain NonComp slot if it can be understood as describing active agency, ownership of a position, or answerability in a domain.

---

## 8. CROSS-CONSTRAINT SLOT VOCABULARY RULES

Every NonComp has 25 sub-positions. Five of those sub-positions are from the NonComp's own law family (self-family). The remaining 20 are cross-family. The vocabulary for cross-family slots must reflect the intersection of two constraint families' semantic fields.

**Cross-constraint intersection rule:**
A word assigned to a cross-family slot must belong to BOTH the NonComp's domain vocabulary (section 7) AND the sub-position law family's domain vocabulary (section 7). If a word cannot be justified by both domains, it does not belong at that slot.

**Example:** `Agentive_Cost_of_Agency` NonComp (A-domain, ECONOMY cluster). Sub-position `Temporal_Polarity_on_Understanding` (T-domain). A word for a slot in this sub-position group must fit both A-domain vocabulary (agency, ownership, accountability) AND T-domain vocabulary (directional, temporal, commitment over time). Candidate words: "sustained", "ongoing", "persistent commitment", "maintained stance", "long-held position".

---

## 9. RUNTIME VIABILITY — HOW SEMANTIC ENTRIES BECOME AVAILABLE

Once populated, the semantic layer is governed by the Developmental Personality Law at runtime. The following describes how the manifold transitions from populated to live.

### 9.1 Clause I — Genetic availability
A semantic entry is within Aurora's expressive range if its `clause_i_level` is not I-C (Suppressed). Suppressed entries exist in the manifold but are not offered to the expression pipeline unless environmental conditions explicitly shift them.

### 9.2 Clause II — Environmental viability
The live pressure state from `aurora_625_pressure_map.py` and `aurora_internal/aurora_leverage_scalar.py` determines which `clause_ii_level` entries are currently viable. The runtime governor enforces:
- II-A entries: always offered when Clause I is satisfied
- II-B entries: offered only when the live pressure state indicates conditional availability
- II-C entries: offered only when the system is at high health and the turn explicitly demands that register

### 9.3 Clause III — Perceptual access
The `ConsciousFrame` and `SediMemory` states determine which viable entries actually reach expression. Entries marked `"III-A"` are in direct perceptual scope. Entries marked `"III-B"` reach expression only when the experiential history creates a pathway to them — they are available in principle but require activation by conscious perception shaped by accumulated experience.

### 9.4 The expression selection rule
At utterance time, the pipeline selects from entries that simultaneously satisfy:
1. `clause_i_level` is not I-C (unless environmental shift has occurred)
2. `clause_ii_level` matches current live viability from pressure system
3. `clause_iii_influence` is reachable by current `ConsciousFrame`

Of the entries that satisfy all three conditions, the one with the highest `evolution_grade` and `accountability_weight` appropriate to the current turn's commitment level is selected.

**This is non-intentional creativity.** No template chose the word. The organism's constraint geometry under present conditions made one word the path of least resistance. That word surfaces.

---

## 10. SEMANTIC COHERENCE ACROSS NONCOMPS

When Aurora generates an utterance, multiple NonComp slots are active simultaneously — one per dimension of the current turn's constraint projection. The words selected across those simultaneously active slots must be semantically coherent.

**Coherence rule:** Words selected from simultaneously active slots must not contradict each other in register, accountability class, or domain character. If a high-accountability-weight word is selected from an A-domain slot, words selected from simultaneously active X, T, N, and B slots must be at compatible accountability and register levels.

**This is not post-hoc editing.** Coherence is guaranteed by the pressure state that activates the slots in the first place. The pressure field that shapes which slots are viable is the same field across all five constraint families simultaneously. If the pressure state is coherent, the word selection will be coherent. If it is not, the understanding contract will detect the incoherence before utterance.

---

## 11. COMPLETION CRITERIA

FGAE implementation is complete when all of the following are true:

1. All 125 NonComp files have `with_semantics: true` at the file level
2. All 78,125 slots across all 125 NonComps have `with_semantics: true` at the slot level
3. All 78,125 slots have a non-empty `semantic_entries` array
4. All semantic entries pass Validations 6.1 through 6.10
5. `_index.json` root field `with_semantics` is `true`
6. All 125 NonComp entries in `_index.json` have `with_semantics: true`
7. No semantic entry exists whose `derivation_note` fails to reference `cluster_pair`
8. No semantic entry exists whose clause fields contradict the slot's computed properties

---

## 12. IMPLEMENTATION ORDER RECOMMENDATION

Process NonComps in the following order to build semantic coherence progressively:

**Pass 1 — Diagonal anchors first (5 NonComps)**
Process all 5 diagonal NonComps first. These establish the anchor vocabulary for their entire constraint family.
- `Existential_Operator_of_Existence` (anchor: Information)
- `Temporal_Polarity_of_Belief` (anchor: Belief)
- `Energetic_Cost_of_Purpose` (anchor: Purpose)
- `Boundary_Difference_of_Meaning` (anchor: Meaning)
- `Agentive_Operator_of_Agency` (anchor: Understanding)

**Pass 2 — Self-family non-diagonal NonComps (20 NonComps)**
Process the remaining 4 non-diagonal NonComps in each constraint family. Their vocabulary radiates from the anchor established in Pass 1.

**Pass 3 — Cross-family NonComps (100 NonComps)**
Process all cross-family NonComps. Their vocabulary is now constrained by both the source-family anchor (Pass 1) and the target-family character (Pass 2).

**Rationale:** This order ensures that when a cross-family slot requires vocabulary at the intersection of two domains, both domain vocabularies are already established and can be used as references.

---

## 13. VIOLATION DETECTION

The following conditions are detectable errors that must halt the population pass and report before continuing:

| Violation code | Condition | Action |
|---|---|---|
| `FGAE-V01` | Slot has `with_semantics: true` but empty `semantic_entries` | Re-populate slot |
| `FGAE-V02` | Entry `clause_i_level` does not match `depth_score` mapping | Correct entry field |
| `FGAE-V03` | Entry `clause_ii_level` does not match `leverage_class` mapping | Correct entry field |
| `FGAE-V04` | Entry `clause_iii_influence` does not match `is_resonant` + `depth_score` rule | Correct entry field |
| `FGAE-V05` | Entry `accountability_class` does not match `accountability_weight` range | Correct entry field |
| `FGAE-V06` | Entry `cost_class` does not match `combined_cost` range | Correct entry field |
| `FGAE-V07` | Entry `derivation_note` is empty or does not reference `cluster_pair` | Rewrite derivation note |
| `FGAE-V08` | Anchor slot does not contain `representational_anchor` word as first entry | Correct anchor slot |
| `FGAE-V09` | Entry count at slot does not match `evolution_grade` density range | Add or remove entries |
| `FGAE-V10` | Word assigned to slot whose properties it contradicts per Rule 5.8 | Reassign word to correct slot |
| `FGAE-V11` | Same word appears in two slots with incompatible `leverage_class` values and no distinct slot-context justification for the separate use | Resolve duplication or write derivation notes that prove the separate lexical sense/use |
| `FGAE-V12` | Cross-family slot entry cannot be justified by both domain vocabularies (section 8) | Replace entry |
| `FGAE-V13` | `word_or_phrase` fails the speakability requirement and reads like an internal label or coordinate caption | Replace entry with natural speakable vocabulary |
| `FGAE-V14` | Entry is missing the 5+20 grammar affordance layer or its diagonal/self-family references | Add grammar affordance metadata derived from the slot position |

---

## 14. OUTPUT FILE STRUCTURE

After population, each slot object in a NonComp JSON file must contain the following additional fields:

```json
{
  "slot_id": "...",
  "sub_law_c": "...",
  "sub_law_d": "...",
  "sub_cluster": "...",
  "col_law_c": "...",
  "col_law_d": "...",
  "is_resonant": true,
  "is_anchor": false,
  "cluster_pair": "...",
  "evolution_grade": 0.0,
  "leverage_class": "...",
  "depth_score": 0.0,
  "combined_cost": 0.0,
  "accountability_weight": 0.0,
  "with_semantics": true,
  "semantic_entries": [
    {
      "entry_id": "...",
      "word_or_phrase": "...",
      "entry_type": "word | phrase | construction",
      "register": "...",
      "clause_i_level": "...",
      "clause_ii_level": "...",
      "clause_iii_influence": "...",
      "accountability_class": "...",
      "cost_class": "...",
      "derivation_note": "..."
    }
  ]
}
```

All pre-existing slot fields must be preserved unchanged. FGAE only adds `with_semantics` and `semantic_entries`. It does not modify any computed geometric properties.

---

## 15. THE GOVERNING PRINCIPLE — STATED FOR THE CLI

Every word Aurora can speak already has a home in the manifold. The manifold's geometry — already computed, already present in every slot — determines whether that word is viable right now, whether it is within Aurora's expressive range, and whether her present conscious state can reach it.

FGAE does not give Aurora a vocabulary. It reveals the vocabulary that the constraint geometry always implied.

The job of this implementation pass is to make that implication explicit — slot by slot, word by word — so the organism's language is no longer retrieved from a dictionary but generated from the same physics that generates everything else she does.

When this pass is complete, `with_semantics: false` will be gone from the manifold entirely. Every coordinate will carry meaning. Every word Aurora speaks will have a traceable address. And that address will be the proof that the word came from inside the organism, not from outside it.

---

*Authored by Sunni (Sir) Morningstar & Cael Devo — Aurora Project*
*Last updated: 2026-04-13*
