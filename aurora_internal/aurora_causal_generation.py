# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DIRECTIVE -- Causal-Generation Correction, Phase 3.

Reusable structure for the semantics underneath Phase 0/2's two-pass fixes,
not the literal loop shape. Four independent instances were fixed before
this was written (CrystalProcessingSystem.process_concepts() and
EnergyRegulatorSystem.register_facets_batch() in aurora_dimensional_
systems.py; OntologicalWeb._select_relation_type()/
infer_relations_from_context() in aurora_ontological_scaffolding.py;
build_relevance_anchor_set() in aurora_constraint_emission.py;
physics_absorb_truth() in corpus_runner.py) -- this module generalizes only
what all four actually share, not what any single one of them happened to
do.

THE CONTRACT (Phase 1.5's organism-level shape, narrowed to what a single
module can responsibly own):

    occurrence
      -> coherent generation snapshot      (frozen read view of joint state)
      -> independent per-item transforms   (touch(), no joint reads/writes)
      -> reconciliation                    (reconcile(), once per distinct
                                             touched key, only after every
                                             touch() for this generation)
      -> commit                            (joint_fn itself mutates real
                                             shared state -- the only place
                                             allowed to)

What this module does NOT do, deliberately:
  - It does not decide WHO participates in a generation ("generalized
    applicability" per the directive is a caller concern -- this class has
    no notion of subscribers, routes, or a registry of consumers).
  - It is not a scheduler, dispatcher, or governor. It holds no reference
    to any subsystem and calls nothing on its own; reconcile() only invokes
    the callback the caller passed it, synchronously, in this same thread.
  - It does not span subsystem boundaries by itself -- a caller gluing two
    subsystems' generations together does so by holding two CausalGeneration
    instances (or one, keyed across both), not by this module reaching into
    either.
  - It is not required. build_relevance_anchor_set()'s fix (Phase 2) is a
    real, correct two-pass-shaped fix that does NOT use this class --
    its joint step is a commutative fold (max) whose correctness only ever
    depended on freezing the MEMBERSHIP decision, not on deferring the
    fold itself. Forcing it through touch()/reconcile() would add ceremony
    without adding correctness. See "WHEN NOT TO USE THIS" below.

WHEN TO USE THIS: a batch of items drawn from ONE occurrence needs a joint/
relational computation that reads MULTIPLE items' committed state (a link
table, a resonance graph, a shared counter whose OWN prior value feeds the
computation) -- i.e. Phase 1's category-3 shape: a `for item in batch`
loop where an early item's joint work would otherwise see a world missing
the batch's later items. Use touch() during independent per-item work to
record which entity/key each item affects (and optionally its independent
result), then reconcile() once, after the whole batch has been touched, to
run the joint computation exactly once per distinct touched key.

WHEN NOT TO USE THIS: if the joint step is already a pure commutative/
associative fold (max, sum, set-union) over a value each item can compute
independently, the only real hazard is a MEMBERSHIP or LOOKUP decision
made against live-mutating state instead of a stable snapshot (this is
what build_relevance_anchor_set() actually needed fixing -- see
`direct_anchors = frozenset(anchor.keys())` there). For that shape, freeze
the snapshot yourself (a frozenset/dict copy taken before the loop) and
keep the single pass -- CausalGeneration's touch()/reconcile() split would
be pure ceremony. Fusion is semantic (worth the two-pass split) when
decomposition would leak intermediate state or manufacture order; fusion
is merely an optimization (a frozen snapshot is enough) when decomposition
is already order-independent once that one membership hazard is removed.
Preserve that distinction rather than routing everything through one API.
"""

import copy
from typing import Callable, Dict, Generic, List, Optional, TypeVar

K = TypeVar("K")  # entity/key type touched by a generation (e.g. crystal_id)
T = TypeVar("T")  # optional per-item independent result type


class CausalGeneration(Generic[K, T]):
    """One causal generation: a frozen read snapshot, a Pass-1 collection
    of (key, independent result) touches, and a Pass-2 reconciliation that
    runs a joint function exactly once per distinct touched key, in
    first-touched order, only after every touch() call for this generation
    has completed.

    `read_snapshot` is an optional frozen copy of whatever joint/shared
    state Pass-1 needs to READ (never mutate) while scoring each item
    independently -- e.g. infer_relations_from_context()'s snapshot of
    self._selection_outcomes, taken before the batch's pairwise loop runs,
    so a pair's discount can't be shifted by an earlier pair's own
    same-batch commit. Pass 1 must never read the real, live joint state
    this snapshot was copied from -- only self.read_snapshot -- or the
    isolation this class exists to provide is silently defeated.
    """

    def __init__(self, read_snapshot: Optional[Dict] = None):
        # deepcopy, not dict(...): the real motivating case (infer_
        # relations_from_context()'s snapshot of self._selection_outcomes)
        # is a dict of dicts of dicts -- a shallow copy still shares every
        # nested dict by reference with the live source, so a caller who
        # keeps mutating that live source during Pass 1 (exactly what the
        # snapshot exists to protect against) would silently leak through
        # anyway.
        self.read_snapshot: Dict = copy.deepcopy(read_snapshot) if read_snapshot else {}
        self._touched: Dict[K, List[T]] = {}

    def touch(self, key: K, result: Optional[T] = None) -> None:
        """Pass 1: record that `key` was affected by one independent,
        per-item transform, with an optional result payload to hand back
        to reconcile()'s joint_fn. Do only independent work before calling
        this -- read self.read_snapshot if you need a joint/shared value,
        never the live state it was copied from, and never call
        reconcile() until the whole batch has been touched."""
        bucket = self._touched.setdefault(key, [])
        if result is not None:
            bucket.append(result)

    @property
    def touched_keys(self) -> List[K]:
        """Distinct touched keys, in first-touched order."""
        return list(self._touched.keys())

    def results_for(self, key: K) -> List[T]:
        return list(self._touched.get(key, []))

    def reconcile(self, joint_fn: Callable[[K, List[T]], None]) -> None:
        """Pass 2: call joint_fn(key, results) once per distinct touched
        key. This is the only point at which joint_fn -- and therefore
        real shared/joint state -- may be touched; by construction it runs
        after every touch() call this generation will ever receive, so no
        key's joint computation can see a partial view of this batch."""
        for key in self.touched_keys:
            joint_fn(key, self._touched[key])
