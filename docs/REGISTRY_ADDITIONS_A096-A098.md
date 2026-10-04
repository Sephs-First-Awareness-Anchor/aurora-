# Registry additions A096-A098 (resolution ledger)

**Authors:** Sunni (Sir) Morningstar & Cael Devo

### FIX-A096: Resolution Defined by Time Window
**Category:** ARCHITECTURAL
**Pattern:** A representational "resolution" ladder built from event-window sizes (1, 2, 4, 8, 16 events) and mapped onto REC_*.
**Correct Form:** Resolution is axis-path length, composed by crossing the previous level with the five roots: 0 event (REC_SURFACE), 1 roots X/T/N/B/A (REC_SHALLOW, 5), 2 transitions X>X..A>A (REC_MODERATE, 25 NC channels), 3 axis triples (REC_DEEP, 125), 4 channel-through-channel (REC_CORE, 625 interaction slots).
**Why:** A window ladder bakes T into the resolution axis itself; T is one of the five questions asked at every resolution, not the ladder.
**First Seen:** `aurora_resolution_ledger.py` first cut

### FIX-A097: Unstable Fact Binarization (Position Counter / Median Split)
**Category:** ARCHITECTURAL
**Pattern:** An event fact that is a monotone function of position (e.g. 1/(1+pos) for "boundary") or a running-median threshold on a bimodal signal.
**Correct Form:** Boundary is a participation fact (an actor's first act inside the episode). High/low splits use a natural two-class split (maximum between-class variance) held between fixed-cadence recomputations.
**Why:** A position counter makes every path through B trivially persistent and survives a within-episode shuffle; a median of an imbalanced bimodal signal lands inside the larger mode and turns its values into coin flips, creating spurious higher-order dependence (measured: 5.7% bit disagreement, a false N>N>N).
**First Seen:** `aurora_resolution_ledger.py` real-archive replay

### FIX-A098: Deeper Path Beating Only Its Parent
**Category:** ARCHITECTURAL
**Pattern:** A deeper axis path kept because it beats its own suffix parent, so B>X>B "wins" over X>B by carrying B>B at another lag.
**Correct Form:** A deeper path must beat the BEST shallower path for the same target root on the same events, and a path is confessed to WARP only after surviving consecutive looks.
**Why:** Path position encodes lag, so containing a strong shallower predictor is not new information.
**First Seen:** `aurora_resolution_ledger.py` real-archive replay

### FIX-A099: Use-and-Consequence Loop Tied to Named Consumers
**Category:** ARCHITECTURAL
**Pattern:** A discovered representation that can only be used by (or scored through) a specific subject such as the web or lexical grounding.
**Correct Form:** Subjects of representation opt in through one duck-typed method, `accept_representation(rep, context) -> Optional[Mapping]`, found in `systems` or registered explicitly. The loop also closes with zero consumers: every discovered representation holds an expectation about the next event and is scored prospectively against the marginal.
**Why:** The web and grounding are two of many subjects of representation; a loop wired to them would reproduce the vocabulary ceiling one layer up.
**First Seen:** `aurora_representation_exchange.py`

### FIX-A100: History and Live Fed as One Counter
**Category:** ARCHITECTURAL
**Pattern:** One event-index cursor shared by archive replay and live turns, or subjects keyed by "historical_*" actor labels, so live events are skipped, pollute history's context, or never meet what history taught.
**Correct Form:** The ledger keeps per-stream context (`history`, `live`) with every table and statistic shared. Subjects are roles via `role_subject()` (`external_user`, `responder`). The user's live event is observed BEFORE generation and Aurora's reply AFTER, through `aurora_live_experience`.
**Why:** What history teaches must apply to the turn about to be answered, and live turns must add to the same evidence without disturbing history's chain context.
**First Seen:** `aurora_live_experience.py`

### FIX-A101: Closed Relation Vocabulary With Unusable Trials
**Category:** ARCHITECTURAL
**Pattern:** A promoted discovered relation type silently falls through to RELATED_TO because selection and reload resolve only `RelationType` members, and trial `uses`/`successes` are never incremented.
**Correct Form:** `DiscoveredRelationKind` is first-class beside the seed enum (selection, persistence reload, `_open_kinds`). `record_relation_trial_use` / `record_relation_trial_outcome` are the increment paths; a consequence source must call the latter.
**Why:** A seed vocabulary is a starting point, not a ceiling, and a trial that can never be used can never be scored.
**First Seen:** `aurora_ontological_scaffolding.py`

### FIX-A102: Representation Records Kept Outside the Crystals
**Category:** ARCHITECTURAL
**Pattern:** Discovered representations, their consequence counters and word associations persisted in separate JSON files, then recomputed on every load.
**Correct Form:** A representation is a facet (`lsa:res:<subject>:<path>`) on the crystal at its path's coordinate in the ONE crystal store; its content is the computed record (expectation table, consequence sums, status), restored on boot instead of recomputed; consequence goes through `record_receiver_outcome`; shape words are `word` facets (lexicon words, high pole only) that composition already reads.
**Why:** Crystals already carry depth (level), use, consequence and persistence; a parallel record keeper duplicates them and keeps composition blind to what it learned.
**First Seen:** `aurora_representation_crystals.py`

### FIX-A103: Facts Normalized Across Actors; Research State Kept in a Log
**Category:** ARCHITECTURAL
**Pattern:** Each root's high/low split taken from one distribution pooled over every actor; candidate paths and calibration persisted in a file of the ledger's own.
**Correct Form:** Each root is read against the ACTING SUBJECT's own running distribution (`"<subject>:<root>"`), and discovery research lives on the crystals as `hyp:` facets (`hyp:res:<subject>:<path>`, `hyp:cal:ledger`), written with a touched `last_accessed` so decay never fades it. `hyp:` is never the registry's `lsa:` prefix, so hypotheses never count as semantic grounding.
**Why:** A pooled split means nothing for any party, and a parallel log duplicates what crystals already persist and decay.
**First Seen:** `aurora_resolution_ledger.py`, greeting exposure experiment

### FIX-A104: Single Binary Split Per Root Cannot Isolate a Rare Tail
**Category:** ARCHITECTURAL
**Pattern:** Expecting a one-bit-per-root fact to represent a rare extreme (a brief greeting among ordinary content).
**Correct Form:** Root resolution must deepen where the coarse split fails: Otsu prefers splitting the bulk (between-class variance ~0.45) over a 2.6% tail (~0.21), so brevity-at-openings is unrepresentable until greetings are ~20%+ of a subject's events. A nested/tail split per root, spawned only where the coarse bit fails to explain, is the open work.
**Why:** Verified by exposure experiment: 15% of conversations opening with a greeting gives opening-brevity expectations that are 0% right; 50% gives 100% right.
**First Seen:** `scripts/greeting_exposure_experiment.py`

### FIX-A105: Crystal Selection Ignoring the Waveform Distribution
**Category:** ARCHITECTURAL
**Pattern:** Composition picking crystals by the dominant axis's share of the signature alone, taking every word facet regardless of strength or fade.
**Correct Form:** `_crystal_waveform_match` scores the WHOLE distribution (axis share kept as the floor, cosine against `self._axis_activation`), vetoes an opposite pole only when the live activation carries sign, breaks near ties toward the more integrated (higher-level) crystal, and `_crystal_word_facets` returns word facets strongest first (confidence x coherence) and skips RELIC.
**Why:** A crystal is a view of several waveforms at once; selecting on one axis discards the distribution it exists to carry.
**First Seen:** `aurora_expression_perception.py`

### FIX-A106: Tail Resolution (opt-in)
**Category:** ARCHITECTURAL
**Pattern:** One coarse split per root, so a rare extreme-low cluster is unrepresentable.
**Correct Form:** Optional tail symbols `t`, `n` (1 = in the extreme-low mode of the subject's own distribution, detected only when the lower class is clearly bimodal, eta >= 0.8, >= 20 samples). A tail symbol is the LOW pole of its root: a negative coordinate component. Enable with `AURORA_RESOLUTION_TAIL=1` or `tail=True`; default off.
**Why:** Greeting brevity is unrepresentable at realistic prevalence under one split (see FIX-A104).
**First Seen:** `aurora_resolution_ledger.py`

### FIX-A107: Lexicon Channels Kept Apart From the Crystals
**Category:** ARCHITECTURAL
**Pattern:** Word-to-channel membership (`noncomp_id`) held only in the lexicon, with composition running a primary channel lookup and a separate secondary crystal lookup.
**Correct Form:** A channel word is a `word` facet on the crystal at its axis coordinate (character in the facet id, `_wc_<CHARACTER>_`); `find_by_noncomp`/`concept_words` read through `LexicalCrystals`, `associate` moves facets, and the channel view is rebuilt from crystals on attach.
**Why:** One place a word's channel lives; the crystals are the source composition derives from.
**First Seen:** `aurora_lexical_crystals.py`

### FIX-A108: Crystals Stamped With the Mode Default Instead of the Input's Waveform
**Category:** ARCHITECTURAL
**Pattern:** Thousands of crystals sharing (0.7, 0.7, 0.7, 0.7, 0.0): the BOUNDED default, because the signal builder weighted every concept from fixed defaults.
**Correct Form:** `ConceptExtractor.extract` blends each concept's own weights equally with the input's waveform (its rank on each root in the ACTOR'S own distribution, `ledger.last_waveform()`) when `input_waveform_provider` is wired (gated to history witnessing and live turns); existing flat signatures are cleared by `repair_flat_signatures` (original kept as `meta:flat_signature`).
**Why:** A flat signature carries no waveform information and can resonate with nothing in particular.
**First Seen:** `aurora_dimensional_systems.py`

### FIX-A109: Relation Trials With No Use and No Outcome Source
**Category:** ARCHITECTURAL
**Pattern:** Trial relation kinds that can never be selected (so never scored) and counters nothing increments.
**Correct Form:** A trial kind is used where the closed vocabulary had no answer (the RELATED_TO fallback, cosine >= threshold); outcome comes from the web's own consequences: success when a typed relation is independently re-observed (`_note_trial_reinforcement`), failure when `register_selection_failure` contradicts it.
**Why:** Use and consequence are what the WARP trial gate scores; both must exist for a trial to be promoted or dissolved.
**First Seen:** `aurora_ontological_scaffolding.py`

### FIX-A110: Representational Irreducibility (equivalence families)
**Category:** ARCHITECTURAL
**Pattern:** Every significant path counted as its own discovery, so X>A>t, B>A>t and X>B>t (or N>X>N, N>B>N, N>A>N) were "fourteen discoveries" that all divide the observations the same way.
**Correct Form:** A path is irreducible only if its composition makes a distinction no other path already makes. Paths with the same target whose predictions over the same observed events differ by less than 10% of the distinction either makes are ONE family (`_same_family`); `discovered()` returns one canonical member (shortest, then strongest) carrying the rest as shared ancestry (`family`, `family_of`); aliases are held provisionally and re-derived from current evidence, so they become independent the moment experience distinguishes them. Removal is tested by the baseline (must beat the best shallower path); substitution is tested by the family.
**Why:** A depth-3 representation merely beating depth 2 does not show its particular composition matters.
**First Seen:** `aurora_resolution_ledger.py` (real archive: 15 significant -> 9 irreducible for external_user)

### FIX-A111: Lexical Layer Inheriting Meaning Only From the Roots
**Category:** ARCHITECTURAL
**Pattern:** Words get meaning only by hanging off X/T/N/B/A through a discovered representation, so when the roots say nothing distinctive no new distinction can be manufactured (a greeting at 5% prevalence was unrepresentable).
**Correct Form:** `LexicalStructure` learns each word's RESPONSE PROFILE (which words follow it in the next event of the same episode), compares it with the background by positive PMI so bland words form nothing, and clusters words with distinctive, alike profiles into at most four classes. A class is a manufactured symbol (`L0`..`L3`, bit = event contains a member) the ledger hangs paths on (`L0>L0`), and its coordinate is where its events sit on the roots (so its representations still land on a crystal). Followers count only when >= 5 and 4 sigma above chance; a class unconfirmed for two discovery rounds is dropped. Opt-in: `AURORA_LEXICAL_SYMBOLS=1` or `lexical=True`. State is kept on the crystals as `hyp:lex:structure`.
**Why:** Distinctions that live in the language itself must be discoverable without borrowing the five roots.
**First Seen:** `aurora_lexical_structure.py` (roots-uninformative control: class {hello,hey,hi} found at 5% prevalence; `L0>L0` earned)
