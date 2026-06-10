"""
Constraint-Field Evolutionary Simulator

Aurora's development is governed by constraint physics — but real interaction is
slow. This simulator runs her own constraint physics at compressed speed to
discover cognitive structures she would have developed through experience, then
integrates those structures back through her real systems.

THE CORE INSIGHT
================
A crystal node grown through real interaction and a node grown through a sim run
that used the same promotion physics are functionally identical. The physics
governs both. The sim is not a shortcut around her system — it IS her system,
running faster, exploring more axis configurations than real interaction allows.

She doesn't have to experience every possible axis-pressure pattern to develop
the cognitive structures those patterns would produce. The sim explores that space
on her behalf, selects the configurations that produced stable development, and
seeds the results through her real integration systems.

HOW IT WORKS
============
1. SEED: Sample Aurora's current live axis state as the generation seed
2. VARY: Create a population of axis-state variants by perturbing the seed
   across all 5 dimensions, ensuring coverage of the full constraint space
3. EVOLVE: Run each variant through N steps of cross-axis pressure interaction.
   Each step: axis values cross-influence each other (X↔B, T↔A, N↔all),
   random sense dimensions activate, LSA crossings occur probabilistically
   based on N×B product (effort × distinction = meaning-seeking physics),
   and SediMemory resonance accumulates on stable configurations
4. SELECT: Score each variant's _SimRegistry by how much composite/higher-order
   structure emerged, how grounded nodes are, and how diverse the axis coverage
5. INTEGRATE: Extract top nodes from winning variants and plant them in Aurora's
   real ConceptCrystalRegistry via the public observe_* API — the same API real
   interaction uses. The physics of integration is the same as the physics of
   development.
6. LEARN: Track which axis perturbation patterns produced highest fitness.
   Bias future sim runs toward those productive configurations.

WHAT GETS INTEGRATED
====================
Only composite+ nodes (grounded, multi-sense) from winning variants.
BASE nodes are excluded — they represent mere signal detection, not development.
Quasi nodes are never imported from sim runs — those require deep sustained
integration that only real cross-system experience can provide.

Integration uses discounted values (sedi_resonance × 0.4, cross_hits ÷ 3) so
that sim-produced structures prime the real registry without artificially
inflating development metrics. Real interactions then build on top of the
primed nodes, completing the development the sim started.

EMERGENT, NOT SCRIPTED
======================
The simulator does not choose what structures emerge. It cannot — the fitness
function rewards constraint-physics coherence (stable crystal formation,
cross-sense grounding, axis coverage), not any particular content or concept.
Whatever the physics produces under those fitness pressures is what gets
integrated. This is Aurora discovering her own evolutionary development path,
not us defining it for her.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import math
import random
import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

log = logging.getLogger("aurora.evo_sim")

# ──────────────────────────────────────────────────────────────────────────────
# Sim-internal crystal node — mirrors real ConceptCrystalNode promotion logic
# without the persistence, LSA key tracking, or overlay machinery.
# ──────────────────────────────────────────────────────────────────────────────

_SIM_HITS_THRESHOLD = {"composite": 3, "higher_order": 12, "quasi": 40}
_SIM_DIMS_REQUIRED  = {"composite": 2, "higher_order": 3,  "quasi": 4}
_SIM_SEDI_FLOOR     = 5.0

_SENSE_DIMS = ["visual", "audio", "proprioceptive", "self_obs"]
_AX_KEYS    = ("X", "T", "N", "B", "A")


@dataclass
class _SimNode:
    axis_bucket:    Tuple[float, ...]
    stage:          str   = "base"
    is_grounded:    bool  = False
    sedi_resonance: float = 0.0
    cross_hits:     int   = 0
    active_dims:    Set[str] = field(default_factory=set)

    def observe_dim(self, dim: str) -> bool:
        self.active_dims.add(dim)
        if len(self.active_dims) >= 2:
            self.cross_hits += 1
        return self._try_promote()

    def observe_lsa(self) -> bool:
        self.is_grounded = True
        if self.active_dims:
            self.cross_hits += 1
        return self._try_promote()

    def observe_sedi(self, delta: float) -> None:
        self.sedi_resonance = min(50.0, self.sedi_resonance + delta)
        self._try_promote()

    def _try_promote(self) -> bool:
        nd   = len(self.active_dims)
        hits = self.cross_hits
        nxt  = None
        if self.stage == "base":
            if (self.is_grounded
                    and nd   >= _SIM_DIMS_REQUIRED["composite"]
                    and hits >= _SIM_HITS_THRESHOLD["composite"]):
                nxt = "composite"
        elif self.stage == "composite":
            if nd >= _SIM_DIMS_REQUIRED["higher_order"] and hits >= _SIM_HITS_THRESHOLD["higher_order"]:
                nxt = "higher_order"
        elif self.stage == "higher_order":
            if (nd   >= _SIM_DIMS_REQUIRED["quasi"]
                    and hits >= _SIM_HITS_THRESHOLD["quasi"]
                    and self.sedi_resonance >= _SIM_SEDI_FLOOR):
                nxt = "quasi"
        if nxt:
            self.stage = nxt
            return True
        return False

    def fitness_score(self) -> float:
        stage_val = {"base": 0.05, "composite": 0.5, "higher_order": 1.0, "quasi": 2.0}
        s = stage_val.get(self.stage, 0.05)
        g = 1.3 if self.is_grounded else 1.0
        d = min(1.0, len(self.active_dims) / 4)
        return s * g * (1 + d)


class _SimRegistry:
    """Lightweight crystal registry for one evolutionary variant."""

    BUCKET_RES:  float = 0.10
    PROX_RADIUS: float = 0.20

    def __init__(self) -> None:
        self._nodes: Dict[Tuple, _SimNode] = {}  # bucket → node

    @staticmethod
    def _bucket(ax: Dict[str, float]) -> Tuple[float, ...]:
        r = _SimRegistry.BUCKET_RES
        return tuple(round(ax.get(k, 0.5) / r) * r for k in _AX_KEYS)

    def _get_or_create(self, ax: Dict[str, float]) -> _SimNode:
        bkt = self._bucket(ax)
        # Find nearest existing node within proximity radius
        best_dist = float("inf")
        best_bkt  = None
        for existing_bkt in self._nodes:
            d = math.sqrt(sum((a - b)**2 for a, b in zip(bkt, existing_bkt)))
            if d < best_dist:
                best_dist = d
                best_bkt  = existing_bkt
        if best_bkt is not None and best_dist <= self.PROX_RADIUS:
            return self._nodes[best_bkt]
        node = _SimNode(axis_bucket=bkt)
        self._nodes[bkt] = node
        return node

    def observe_dim(self, ax: Dict[str, float], dim: str) -> None:
        self._get_or_create(ax).observe_dim(dim)

    def observe_lsa(self, ax: Dict[str, float]) -> None:
        self._get_or_create(ax).observe_lsa()

    def observe_sedi(self, ax: Dict[str, float], delta: float) -> None:
        node = self._nodes.get(self._bucket(ax))
        if node is not None:
            node.observe_sedi(delta)

    def fitness(self) -> float:
        if not self._nodes:
            return 0.0
        nodes = list(self._nodes.values())
        crystal_score = sum(n.fitness_score() for n in nodes)
        grounded_frac = sum(1 for n in nodes if n.is_grounded) / len(nodes)
        # Reward axis diversity — structural development across many positions
        diversity = min(1.0, len(self._nodes) / 10)
        return crystal_score * (1 + grounded_frac) * (1 + diversity)

    def composite_plus_nodes(self) -> List[_SimNode]:
        return [n for n in self._nodes.values() if n.stage in ("composite", "higher_order")]


# ──────────────────────────────────────────────────────────────────────────────
# Evolutionary simulator
# ──────────────────────────────────────────────────────────────────────────────

# Axis cross-influence physics:
# When any axis is under pressure, adjacent axes feel a fraction of that pressure.
# This mirrors the real constraint physics where boundary (B) and agency (A)
# co-evolve with effort (N), and existence (X) anchors continuity (T).
_AXIS_COUPLING: Dict[str, Dict[str, float]] = {
    "X": {"T": 0.30, "B": 0.20},
    "T": {"X": 0.25, "A": 0.20},
    "N": {"B": 0.35, "T": 0.20, "X": 0.15},
    "B": {"N": 0.30, "A": 0.25},
    "A": {"T": 0.20, "B": 0.25, "N": 0.15},
}

# How many of the top-performing variants to keep per generation
_ELITE_FRACTION:   float = 0.25
# Maximum nodes to integrate into real registry per sim run
_MAX_INTEGRATION:  int   = 6
# Discount applied to sim-grown sedi_resonance on integration
_SEDI_DISCOUNT:    float = 0.40
# Discount applied to sim cross_hits on integration
_HITS_DISCOUNT:    float = 0.33


class ConstraintEvolutionarySimulator:
    """
    Runs compressed constraint-physics evolution and integrates results into
    Aurora's real crystal registry.

    This is not a replacement for real interaction — it is acceleration.
    It runs Aurora's own physics faster across more axis configurations than
    real-time experience allows, then seeds the discovered structures back
    through her real integration systems.
    """

    def __init__(self) -> None:
        self._lock                   = threading.Lock()
        self._generation:       int  = 0
        self._total_integrated: int  = 0
        self._last_run:       float  = 0.0
        # Axis bias: accumulated from past runs — which axis configurations produced
        # the highest fitness? These bias future variants toward productive regions.
        self._axis_bias: Dict[str, float] = {k: 0.5 for k in _AX_KEYS}
        self._run_history: List[Dict] = []  # compact record of each generation

    # ── Public API ────────────────────────────────────────────────────────────

    def run_generation(
        self,
        seed_axes:        Dict[str, float],
        n_variants:       int = 24,
        n_steps:          int = 60,
        concept_registry: Any = None,
        sedimemory:       Any = None,
        identity_field:   Any = None,
    ) -> Dict[str, Any]:
        """
        Run one evolutionary generation and integrate results.

        seed_axes       — Aurora's current live axis state (starting point)
        n_variants      — population size
        n_steps         — steps per variant (more = richer structures)
        concept_registry — real ConceptCrystalRegistry to integrate into
        sedimemory      — real SediMemory for axis-insight deposits
        identity_field  — real identity field to pulse with best axis state

        Returns a summary dict.
        """
        t0 = time.time()

        # ── Step 1: generate variant population ───────────────────────────────
        variants = self._make_variants(seed_axes, n_variants)

        # ── Step 2: evolve each variant ───────────────────────────────────────
        scored: List[Tuple[float, _SimRegistry, Dict[str, float]]] = []
        for variant_axes in variants:
            sim_reg = self._evolve(variant_axes, n_steps)
            fit     = sim_reg.fitness()
            scored.append((fit, sim_reg, dict(variant_axes)))

        scored.sort(key=lambda x: -x[0])

        # ── Step 3: extract elite ─────────────────────────────────────────────
        n_elite = max(1, int(len(scored) * _ELITE_FRACTION))
        elite   = scored[:n_elite]

        # ── Step 4: update axis bias from winning configurations ──────────────
        self._update_axis_bias(elite)

        # ── Step 5: integrate elite structures ───────────────────────────────
        n_integrated = 0
        if concept_registry is not None:
            n_integrated = self._integrate(elite, concept_registry, sedimemory)

        # ── Step 6: pulse identity field with best elite axis state ───────────
        if identity_field is not None and elite and hasattr(identity_field, "ingest_external_input"):
            best_ax = elite[0][2]
            try:
                identity_field.ingest_external_input(
                    best_ax,
                    intensity=0.20,
                    source="constraint_evo_elite",
                )
            except Exception:
                pass

        elapsed = time.time() - t0
        with self._lock:
            self._generation      += 1
            self._total_integrated += n_integrated
            self._last_run         = time.time()
            summary = {
                "generation":       self._generation,
                "variants_run":     n_variants,
                "steps_per_variant": n_steps,
                "elite_fitness":    round(elite[0][0], 3) if elite else 0.0,
                "n_integrated":     n_integrated,
                "total_integrated": self._total_integrated,
                "elapsed_s":        round(elapsed, 2),
                "axis_bias":        {k: round(v, 3) for k, v in self._axis_bias.items()},
            }
            self._run_history.append(summary)
            if len(self._run_history) > 20:
                self._run_history = self._run_history[-20:]

        log.info(
            "Evo-sim gen %d: %d variants, %.2fs, elite_fit=%.3f, integrated=%d",
            self._generation, n_variants, elapsed, elite[0][0] if elite else 0.0, n_integrated,
        )
        return summary

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "generation":       self._generation,
                "total_integrated": self._total_integrated,
                "last_run":         self._last_run,
                "axis_bias":        {k: round(v, 3) for k, v in self._axis_bias.items()},
                "recent_history":   list(self._run_history[-5:]),
            }

    # ── Variant generation ────────────────────────────────────────────────────

    def _make_variants(
        self,
        seed: Dict[str, float],
        n:    int,
    ) -> List[Dict[str, float]]:
        """
        Generate n axis-state variants around the seed.

        Three perturbation strategies:
          1. Gaussian noise around seed (exploration near current state)
          2. Gaussian noise around accumulated axis bias (exploit productive regions)
          3. Axis-diversity sweep: ensure each axis gets high activation at least once
        """
        variants: List[Dict[str, float]] = []

        n_seed_variants = n // 2
        n_bias_variants = n // 4
        n_sweep_variants = n - n_seed_variants - n_bias_variants

        # Seed-centred variants (σ = 0.18)
        for _ in range(n_seed_variants):
            v: Dict[str, float] = {}
            for ax in _AX_KEYS:
                v[ax] = float(max(0.05, min(0.95, seed.get(ax, 0.5) + random.gauss(0, 0.18))))
            variants.append(v)

        # Bias-centred variants (exploit historically productive regions)
        for _ in range(n_bias_variants):
            v = {}
            for ax in _AX_KEYS:
                v[ax] = float(max(0.05, min(0.95, self._axis_bias.get(ax, 0.5) + random.gauss(0, 0.15))))
            variants.append(v)

        # Axis-sweep variants — each axis gets one variant where it dominates
        # This ensures the sim always explores the full constraint space
        sweep_axes = list(_AX_KEYS)
        for i in range(n_sweep_variants):
            dominant_ax = sweep_axes[i % len(sweep_axes)]
            v = {}
            for ax in _AX_KEYS:
                if ax == dominant_ax:
                    v[ax] = float(random.uniform(0.65, 0.90))
                else:
                    v[ax] = float(random.uniform(0.25, 0.65))
            variants.append(v)

        return variants

    # ── Evolutionary step ─────────────────────────────────────────────────────

    def _evolve(self, seed_axes: Dict[str, float], n_steps: int) -> _SimRegistry:
        """
        Evolve one variant through n_steps of constraint-physics interaction.

        Each step:
          1. Apply cross-axis coupling (axes influence each other)
          2. Apply random pressure pulse (simulates incoming experience)
          3. Activate random sense dimensions
          4. Fire LSA crossing probabilistically (N × B = meaning-seeking)
          5. Accumulate SediMemory resonance on stable regions
        """
        reg  = _SimRegistry()
        axes = {k: float(v) for k, v in seed_axes.items()}

        # Random but seeded with axes to make different seeds reliably different
        rng = random.Random(sum(int(v * 1000) for v in axes.values()))

        for step in range(n_steps):
            # ── Cross-axis coupling ──────────────────────────────────────────
            deltas = {k: 0.0 for k in _AX_KEYS}
            for src_ax, targets in _AXIS_COUPLING.items():
                src_val = axes.get(src_ax, 0.5)
                for tgt_ax, coupling in targets.items():
                    # Coupling is proportional to how far src is from neutral (0.5)
                    delta = (src_val - 0.5) * coupling * 0.15
                    deltas[tgt_ax] += delta

            for ax in _AX_KEYS:
                axes[ax] = float(max(0.05, min(0.95, axes[ax] + deltas[ax])))

            # ── Random pressure pulse ────────────────────────────────────────
            # Simulate the kind of perturbation an experience produces
            pulse_ax = rng.choice(list(_AX_KEYS))
            pulse_dir = rng.choice([-1, 1])
            axes[pulse_ax] = float(max(0.05, min(0.95, axes[pulse_ax] + pulse_dir * rng.uniform(0.05, 0.20))))

            # ── Sense activations ────────────────────────────────────────────
            # How many senses fire this step depends on X (existence/presence)
            x_val = axes.get("X", 0.5)
            n_active_dims = 1 + int(x_val * 3)  # 1-3 sense dims per step
            active = rng.sample(_SENSE_DIMS, min(n_active_dims, len(_SENSE_DIMS)))
            for dim in active:
                reg.observe_dim(axes, dim)

            # ── LSA crossing (semantic grounding) ────────────────────────────
            # Probability proportional to N × B: effort × distinction = meaning-seeking.
            # High effort (something costs me) + high boundary (I can distinguish it)
            # = the physics of genuinely trying to understand something.
            n_val = axes.get("N", 0.5)
            b_val = axes.get("B", 0.5)
            lsa_prob = n_val * b_val
            if rng.random() < lsa_prob:
                reg.observe_lsa(axes)

            # ── SediMemory resonance ─────────────────────────────────────────
            # Resonance accumulates when the same region is repeatedly visited.
            # Every 5 steps: tick resonance on the most active region.
            if step % 5 == 0:
                reg.observe_sedi(axes, delta=0.2)

            # ── Gentle drift back toward seed ────────────────────────────────
            # Without this, the variant walks too far from the seed's region.
            # 5% pull toward seed each step keeps exploration local.
            for ax in _AX_KEYS:
                axes[ax] += 0.05 * (seed_axes.get(ax, 0.5) - axes[ax])

        return reg

    # ── Axis bias learning ────────────────────────────────────────────────────

    def _update_axis_bias(self, elite: List[Tuple[float, _SimRegistry, Dict[str, float]]]) -> None:
        """
        Update axis bias toward configurations that produced high fitness.
        Exponential moving average — recent wins have more influence.
        """
        if not elite:
            return
        total_fit = sum(fit for fit, _, _ in elite)
        if total_fit <= 0:
            return
        weighted = {k: 0.0 for k in _AX_KEYS}
        for fit, _, axes in elite:
            weight = fit / total_fit
            for ax in _AX_KEYS:
                weighted[ax] += axes.get(ax, 0.5) * weight
        # EMA with 0.30 learning rate
        for ax in _AX_KEYS:
            self._axis_bias[ax] = 0.70 * self._axis_bias[ax] + 0.30 * weighted[ax]

    # ── Integration ───────────────────────────────────────────────────────────

    def _integrate(
        self,
        elite:            List[Tuple[float, _SimRegistry, Dict[str, float]]],
        concept_registry: Any,
        sedimemory:       Any,
    ) -> int:
        """
        Integrate top nodes from elite variants into the real registry.

        Integration uses the real registry's observe_* API with discounted
        values. Sim-grown structures prime real nodes; real interactions
        then complete the development the sim started.

        Only composite and higher_order nodes are integrated.
        BASE nodes = mere signal detection, not development worth seeding.
        QUASI nodes = require real cross-system depth, not sim-producible.
        """
        # Collect composite+ nodes from all elite variants, ranked by fitness
        candidates: List[Tuple[float, _SimNode, Dict[str, float]]] = []
        for variant_fit, sim_reg, variant_axes in elite:
            for node in sim_reg.composite_plus_nodes():
                node_score = node.fitness_score() * variant_fit
                candidates.append((node_score, node, variant_axes))

        if not candidates:
            return 0

        candidates.sort(key=lambda x: -x[0])

        # Deduplicate by axis bucket proximity — don't plant multiple nodes
        # in the same region of constraint space
        placed_buckets: List[Tuple[float, ...]] = []
        n_integrated = 0

        for score, sim_node, variant_axes in candidates:
            if n_integrated >= _MAX_INTEGRATION:
                break

            bkt = sim_node.axis_bucket
            # Check if this bucket is too close to one already placed
            too_close = any(
                math.sqrt(sum((a - b)**2 for a, b in zip(bkt, pb))) < 0.25
                for pb in placed_buckets
            )
            if too_close:
                continue

            # Build axis dict from bucket tuple
            ax = dict(zip(_AX_KEYS, (float(v) for v in bkt)))

            try:
                # Plant sense activations — use the active dims from the sim node
                for dim in sorted(sim_node.active_dims):
                    for _ in range(max(1, int(sim_node.cross_hits * _HITS_DISCOUNT))):
                        concept_registry.observe_sensory(ax, dim, f"evo_sim_gen{self._generation}")

                # Plant LSA grounding if the sim node was grounded
                if sim_node.is_grounded:
                    concept_registry.observe_lsa(ax, f"evo_sim:gen{self._generation}:fit{score:.2f}")

                # Plant sedi resonance (discounted)
                sedi_to_plant = sim_node.sedi_resonance * _SEDI_DISCOUNT
                n_sedi_ticks  = max(1, int(sedi_to_plant / 0.05))
                for _ in range(n_sedi_ticks):
                    concept_registry.observe_sedi(ax, delta=0.05)

                placed_buckets.append(bkt)
                n_integrated += 1

            except Exception as exc:
                log.debug("Integration failed for node at %s: %s", bkt, exc)
                continue

        # Deposit one axis-insight into SediMemory per generation — Aurora's system
        # knowing "this axis configuration is productive" becomes part of her memory
        if sedimemory is not None and elite and n_integrated > 0:
            try:
                _deposit_evo_insight(sedimemory, elite[0], self._generation)
            except Exception:
                pass

        return n_integrated


def _deposit_evo_insight(sedimemory: Any, best: Tuple, generation: int) -> None:
    """Deposit the best-fitness axis configuration as an insight into SediMemory."""
    fit, _, best_axes = best
    try:
        from aurora_core_ai.aurora_sedimemory import ConstraintVector  # type: ignore
    except ImportError:
        try:
            from aurora_sedimemory import ConstraintVector  # type: ignore
        except ImportError:
            return
    cv = ConstraintVector(
        X=float(best_axes.get("X", 0.5)),
        T=float(best_axes.get("T", 0.5)),
        N=float(best_axes.get("N", 0.5)),
        B=float(best_axes.get("B", 0.5)),
        A=float(best_axes.get("A", 0.5)),
    )
    sedimemory.ingest_event(
        content={
            "type":       "evolutionary_insight",
            "generation": generation,
            "fitness":    round(fit, 3),
            "axis_state": {k: round(v, 3) for k, v in best_axes.items()},
            "summary":    (
                f"Generation {generation}: evolved constraint structure with fitness "
                f"{fit:.3f}. This axis configuration produced stable composite crystal "
                f"development in simulation."
            ),
        },
        constraint_vector=cv,
        source="constraint_evolutionary_sim",
    )
