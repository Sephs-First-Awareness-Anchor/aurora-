#!/usr/bin/env python3
"""
AURORA DREAM EVOLUTION ORCHESTRATOR
========================================
Ties together the full dream-coupled structural evolution pipeline:

  compile -> queue -> execute -> diagnose -> steer -> bridge -> evolve

This orchestrator is the single integration point between the existing
AutonomyEngine dream path and the new diagnostic/steering/genealogy
modules. It keeps the AutonomyEngine modifications minimal.

Runtime flow:
  1. pre_compile()  — compile corpus into episode packs (run once or on demand)
  2. build_seed()   — get next dream seed from curriculum queue
  3. post_episode() — full diagnostic pipeline after dream episode completes
  4. apply()        — push steering/evidence into DPME, genealogy, expression

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

logger = logging.getLogger("aurora.dream_evolution")

# ---- Import all dream evolution modules ----
from aurora_internal.aurora_conversation_rubric_engine import (
    ConversationRubricEngine,
    ConversationRubricScore,
    RUBRIC_DIMENSIONS,
)
from aurora_internal.aurora_conversation_episode_compiler import (
    ConversationEpisodeCompiler,
    DreamEpisodePack,
)
from aurora_internal.aurora_dream_curriculum_queue import (
    DreamCurriculumQueue,
)
from aurora_internal.aurora_episode_slip_profiler import (
    EpisodeSlipProfiler,
    EpisodeRubricSummary,
)
from aurora_internal.aurora_rubric_influence_graph import (
    RubricInfluenceGraph,
)
from aurora_internal.aurora_specialized_avatar_synthesizer import (
    SpecializedAvatarSynthesizer,
    PressureSpecializedAvatarSpec,
)
from aurora_internal.aurora_structural_pressure_steering import (
    StructuralPressureSteering,
    StructuralPressureDirective,
)
from aurora_internal.aurora_dream_genealogy_bridge import (
    DreamGenealogyBridge,
    DreamEvidenceRecord,
    ExpressionWritebackHint,
)


class DreamEvolutionOrchestrator:
    """
    Single integration point for the dream-coupled structural evolution pipeline.

    Designed to be attached to the AutonomyEngine with minimal changes.
    The AutonomyEngine calls:
      - orchestrator.build_seed()    in _build_dream_seed()
      - orchestrator.post_episode()  in _check_dreams() after run_episode
      - orchestrator.apply()         to push results into live systems
    """

    def __init__(
        self,
        state_dir: str = _STATE_ROOT,
        corpus_path: Optional[str] = None,
    ):
        episode_dir = os.path.join(state_dir, "dream_episodes")
        steering_dir = os.path.join(state_dir, "dream_steering")
        genealogy_dir = os.path.join(state_dir, "dream_genealogy")
        avatar_dir = os.path.join(state_dir, "dream_avatar_policy")

        # Core modules
        self.rubric_engine = ConversationRubricEngine()
        self.curriculum_queue = DreamCurriculumQueue(storage_dir=episode_dir)
        self.slip_profiler = EpisodeSlipProfiler()
        self.avatar_synthesizer = SpecializedAvatarSynthesizer(
            storage_dir=avatar_dir
        )
        self.pressure_steering = StructuralPressureSteering(storage_dir=steering_dir)
        self.genealogy_bridge = DreamGenealogyBridge(storage_dir=genealogy_dir)

        # State
        self._corpus_path = corpus_path
        self._current_pack: Optional[DreamEpisodePack] = None
        self._last_summary: Optional[EpisodeRubricSummary] = None
        self._previous_summary: Optional[EpisodeRubricSummary] = None
        self._episode_summaries: List[EpisodeRubricSummary] = []
        self._pending_directives: List[StructuralPressureDirective] = []
        self._pending_avatar_specs: List[PressureSpecializedAvatarSpec] = []
        self._pending_evidence: List[DreamEvidenceRecord] = []
        self._pending_expression_hints: List[ExpressionWritebackHint] = []
        self._pending_learner_observations: List[Dict[str, Any]] = []
        self._last_code_evolution_refs: List[Dict[str, Any]] = []
        self._compiled = False
        self._episodes_processed: int = 0
        self._last_policy_feedback: Dict[str, Any] = {}

        logger.info("[DREAM-EVO] Orchestrator initialized")

    # ================================================================
    # STAGE: COMPILE (run once or on demand)
    # ================================================================

    def pre_compile(
        self,
        corpus_path: Optional[str] = None,
        max_conversations: int = 500,
    ) -> int:
        """
        Compile conversation corpus into dream episode packs.
        Run this once when corpus is available, or on-demand.
        Returns number of packs compiled.
        """
        path = corpus_path or self._corpus_path
        if not path or not os.path.exists(path):
            logger.debug("[DREAM-EVO] No corpus path available for compilation")
            return 0

        try:
            count = self.curriculum_queue.compile_from_corpus(
                path, max_conversations
            )
            self._compiled = count > 0
            logger.info(
                f"[DREAM-EVO] Compiled {count} episode packs from corpus"
            )
            return count
        except Exception as e:
            logger.error(f"[DREAM-EVO] Compilation failed: {e}")
            return 0

    # ================================================================
    # STAGE: BUILD SEED (replaces generic dream seed when packs exist)
    # ================================================================

    def build_seed(self) -> Optional[str]:
        """
        Get the next dream seed from curriculum queue.

        Returns seed string if a pack is available, None otherwise
        (caller falls back to original _build_dream_seed logic).
        """
        # Try to compile on first call if not done yet
        if not self._compiled and self._corpus_path:
            self.pre_compile()

        pack = self.curriculum_queue.next_pack()
        if pack is None:
            return None

        self._current_pack = pack
        seed = self.curriculum_queue.get_seed_from_pack(pack)
        logger.info(
            f"[DREAM-EVO] Serving pack {pack.episode_id} "
            f"(mode={pack.design_mode}, difficulty={pack.difficulty_estimate:.2f})"
        )
        return seed

    def get_current_pack(self) -> Optional[DreamEpisodePack]:
        """Return the current active dream episode pack."""
        return self._current_pack

    def _extract_generated_threads(
        self,
        episode_result: Any,
    ) -> List[tuple[str, List[tuple[str, str]]]]:
        """
        Build rubric-ready conversation threads from the generated dream episode.

        Preference is always the generated trace (Aurora vs avatar dynamics),
        not static corpus payloads.
        """
        trace = getattr(episode_result, "conversation_trace", None)
        if trace is None and isinstance(episode_result, dict):
            trace = episode_result.get("conversation_trace")
        if not isinstance(trace, list) or not trace:
            return []

        episode_id = "dream_generated"
        if hasattr(episode_result, "episode_id"):
            episode_id = str(getattr(episode_result, "episode_id") or episode_id)
        elif isinstance(episode_result, dict):
            episode_id = str(episode_result.get("episode_id") or episode_id)

        pairs: List[tuple[str, str]] = []
        for row in trace:
            if not isinstance(row, dict):
                continue
            user_text = str(row.get("user_text", "") or "").strip()
            asst_text = str(row.get("assistant_text", "") or "").strip()
            if user_text and asst_text:
                pairs.append((user_text, asst_text))

        if not pairs:
            return []

        threads: List[tuple[str, List[tuple[str, str]]]] = []

        # Full episode thread preserves multi-turn continuity signals.
        full_messages: List[tuple[str, str]] = []
        for user_text, asst_text in pairs:
            full_messages.append(("user", user_text))
            full_messages.append(("assistant", asst_text))
        threads.append((f"{episode_id}:generated_full", full_messages))

        # Add 2-turn windows to give profiler enough thread count for significance.
        if len(pairs) >= 2:
            for i in range(len(pairs) - 1):
                msgs: List[tuple[str, str]] = []
                for user_text, asst_text in pairs[i:i + 2]:
                    msgs.append(("user", user_text))
                    msgs.append(("assistant", asst_text))
                threads.append((f"{episode_id}:generated_window_{i}", msgs))

        return threads

    def _extract_active_pressure_targets(
        self,
        episode_result: Any,
    ) -> Dict[str, float]:
        """
        Extract the pressure profile that was active during the episode, if any.

        This is fed back into the avatar synthesizer policy so pressure tuning
        is owned by Aurora's architecture, not manual operator tweaks.
        """
        raw_targets: Any = {}
        if hasattr(episode_result, "active_avatar_pressure_targets"):
            raw_targets = getattr(episode_result, "active_avatar_pressure_targets", {})
        elif isinstance(episode_result, dict):
            raw_targets = episode_result.get("active_avatar_pressure_targets", {})

        if not isinstance(raw_targets, dict):
            return {}

        out: Dict[str, float] = {}
        for k, v in raw_targets.items():
            try:
                key = str(k).strip()
                if not key:
                    continue
                x = max(0.0, min(1.0, float(v)))
                out[key] = x
            except Exception:
                continue
        return out

    # ================================================================
    # STAGE: POST-EPISODE (full diagnostic pipeline)
    # ================================================================

    def post_episode(
        self,
        episode_result: Any,
        seed: str = "",
    ) -> Optional[EpisodeRubricSummary]:
        """
        Run the full diagnostic pipeline after a dream episode completes.

        This is the main integration call. It:
        1. Scores the episode through rubric (if pack-based)
        2. Profiles slips and identifies leverage candidates
        3. Generates specialized avatar specs
        4. Generates structural pressure directives
        5. Generates genealogical evidence
        6. Generates expression writeback hints

        All results are held in pending queues until apply() is called.

        Args:
            episode_result: EpisodeResult from SimulationEngine.run_episode()
            seed: The dream seed string used

        Returns:
            EpisodeRubricSummary if diagnostic ran, None otherwise
        """
        pack = self._current_pack

        # Extract fitness from episode result
        episode_fitness = 0.0
        episode_id = seed[:20] or f"dream_{int(time.time())}"
        if hasattr(episode_result, 'avg_fitness'):
            episode_fitness = episode_result.avg_fitness
            episode_id = getattr(episode_result, 'episode_id', episode_id)
        elif isinstance(episode_result, dict):
            episode_fitness = episode_result.get('avg_fitness', 0.0)
            episode_id = episode_result.get('episode_id', episode_id)

        # ---- Score through rubric ----
        rubric_scores: List[ConversationRubricScore] = []

        generated_threads = self._extract_generated_threads(episode_result)
        if generated_threads:
            # Primary source: generated dream interactions from this episode.
            for conv_id, messages in generated_threads:
                if messages:
                    score = self.rubric_engine.score_conversation(conv_id, messages)
                    rubric_scores.append(score)
        elif pack and pack.payloads:
            # Fallback only when generated trace is unavailable.
            for payload in pack.payloads:
                conv_id = payload.get("conversation_id", "unknown")
                messages = [
                    (m.get("role", "user"), m.get("text", ""))
                    for m in payload.get("messages", [])
                ]
                if messages:
                    score = self.rubric_engine.score_conversation(conv_id, messages)
                    rubric_scores.append(score)

        if not rubric_scores:
            # No pack data — generate a minimal summary from episode fitness
            # This still feeds the pipeline with what we have
            summary = EpisodeRubricSummary(
                episode_id=episode_id,
                episode_fitness=episode_fitness,
                thread_count=1,
                confidence=0.2,
            )
            self._record_completion(pack, episode_fitness)
            self._current_pack = None
            return summary

        # ---- Profile slips ----
        summary = self.slip_profiler.profile(
            episode_id=episode_id,
            rubric_scores=rubric_scores,
            episode_fitness=episode_fitness,
        )

        # Update adaptive pressure policy from actual episode outcomes.
        previous_summary = self._last_summary
        active_targets = self._extract_active_pressure_targets(episode_result)
        try:
            self._last_policy_feedback = self.avatar_synthesizer.register_episode_feedback(
                summary=summary,
                previous_summary=previous_summary,
                applied_pressure_targets=active_targets,
                episode_fitness=episode_fitness,
            )
        except Exception as e:
            self._last_policy_feedback = {"updated": False, "reason": f"policy_feedback_error: {e}"}

        # ---- Generate avatar specs ----
        if summary.is_significant():
            avatar_specs = self.avatar_synthesizer.synthesize_from_summary(summary)
            self._pending_avatar_specs.extend(avatar_specs)

            # ---- Generate pressure directives ----
            directives = self.pressure_steering.generate_directives(summary)
            self._pending_directives.extend(directives)

            # ---- Generate genealogical evidence ----
            evidence = self.genealogy_bridge.generate_evidence(
                summary=summary,
                directives=directives,
                previous_summary=self._previous_summary,
            )
            self._pending_evidence.extend(evidence)

            # ---- Generate expression hints ----
            hints = self.genealogy_bridge.generate_expression_hints(summary)
            self._pending_expression_hints.extend(hints)

            # ---- Generate learner observations ----
            observations = self.genealogy_bridge.generate_learner_observations(summary)
            self._pending_learner_observations.extend(observations)

        # Track summaries for accumulative analysis
        self._previous_summary = self._last_summary
        self._last_summary = summary
        self._episode_summaries.append(summary)
        self._episodes_processed += 1

        # ---- Accumulative analysis every 5 episodes ----
        if len(self._episode_summaries) >= 5 and len(self._episode_summaries) % 5 == 0:
            self._run_accumulative_analysis()

        # Record completion in queue
        self._record_completion(pack, episode_fitness)
        self._current_pack = None

        logger.info(
            f"[DREAM-EVO] Episode {episode_id} diagnosed: "
            f"fitness={episode_fitness:.2f}, "
            f"leverage={len(summary.leverage_candidates)}, "
            f"directives={len(self._pending_directives)}"
        )

        return summary

    def _record_completion(
        self,
        pack: Optional[DreamEpisodePack],
        fitness: float,
    ):
        """Record pack completion in curriculum queue."""
        if pack is None:
            return
        summary = self._last_summary
        weakness_dims = []
        improvement = False
        if summary:
            weakness_dims = list(summary.primary_deficits.keys())[:5]
            if self._previous_summary:
                prev_fitness = self._previous_summary.episode_fitness
                improvement = fitness > prev_fitness + 0.02
        self.curriculum_queue.record_completion(
            episode_id=pack.episode_id,
            mean_fitness=fitness,
            weakness_dimensions=weakness_dims,
            improvement_detected=improvement,
        )

    def _run_accumulative_analysis(self):
        """Run cross-episode accumulative analysis for persistent weaknesses."""
        recent = self._episode_summaries[-10:]
        analysis = self.slip_profiler.profile_accumulative(recent)

        persistent = analysis.get("persistent_weaknesses", {})
        if persistent:
            episode_ids = [s.episode_id for s in recent]

            # Accumulated avatar specs (more aggressive)
            acc_specs = self.avatar_synthesizer.synthesize_from_accumulation(
                analysis, episode_ids
            )
            self._pending_avatar_specs.extend(acc_specs)

            # Accumulated directives (stronger confidence)
            acc_directives = self.pressure_steering.generate_from_accumulation(
                analysis, episode_ids
            )
            self._pending_directives.extend(acc_directives)

            logger.info(
                f"[DREAM-EVO] Accumulative analysis: "
                f"{len(persistent)} persistent weaknesses, "
                f"{len(acc_specs)} avatar specs, "
                f"{len(acc_directives)} directives"
            )

    # ================================================================
    # STAGE: APPLY (push into live systems)
    # ================================================================

    def apply(self, systems: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push all pending results into live Aurora systems.

        This is called with the systems dict from AutonomyEngine.
        It applies:
        1. Specialized avatar specs (rubric feedback -> next dream pressure)
        2. DPME pressure guidance (structural steering -> DPME)
        3. Genealogy evidence (bridge -> genealogy logger)
        4. Expression writeback (hints -> ExpressionEcology/VoiceGenome)
        5. Learner observations (bridge -> ConsciousLearner)
        6. Code evolution config (steering -> code evolution chamber)

        Returns summary of what was applied.
        """
        applied: Dict[str, Any] = {
            "avatar_specs_applied": 0,
            "dpme_guidance": False,
            "genealogy_entries": 0,
            "expression_hints": 0,
            "voice_updates": 0,
            "learner_observations": 0,
            "code_evolution_entries": 0,
            "code_evolution_refs": [],
        }

        # ---- 1. Specialized avatar specs ----
        applied["avatar_specs_applied"] = self._apply_avatar_specs(systems)

        # ---- 2. DPME pressure guidance ----
        applied["dpme_guidance"] = self._apply_dpme(systems)

        # ---- 3. Genealogy evidence ----
        applied["genealogy_entries"] = self._apply_genealogy(systems)

        # ---- 4. Expression writeback ----
        applied["expression_hints"] = self._apply_expression(systems)

        # ---- 5. Voice genome ----
        applied["voice_updates"] = self._apply_voice(systems)

        # ---- 6. Learner observations ----
        applied["learner_observations"] = self._apply_learner(systems)

        # ---- 7. Code evolution ----
        applied["code_evolution_entries"] = self._apply_code_evolution(systems)
        applied["code_evolution_refs"] = [dict(ref) for ref in self._last_code_evolution_refs]

        # Clear pending queues
        self._pending_directives.clear()
        self._pending_evidence.clear()
        self._pending_expression_hints.clear()
        self._pending_learner_observations.clear()
        # Avatar specs are consumed by _apply_avatar_specs() when simulation supports it.

        # Expire old directives
        self.pressure_steering.expire_old_directives()

        logger.info(f"[DREAM-EVO] Applied: {applied}")
        return applied

    def _apply_avatar_specs(self, systems: Dict[str, Any]) -> int:
        """
        Push pending pressure-specialized avatar specs into SimulationSession.

        This is the critical rubric->avatar feedback loop that ensures the next
        dream episode is pressured on the dimensions where Aurora struggled.
        """
        if not self._pending_avatar_specs:
            return 0

        simulation = systems.get("simulation")
        session = getattr(simulation, "session", None) if simulation else None
        if session is None:
            return 0

        queue_fn = getattr(session, "queue_avatar_specs", None)
        if not callable(queue_fn):
            return 0

        try:
            pending = list(self._pending_avatar_specs)
            count = int(queue_fn(pending) or 0)
            if count > 0:
                # Preserve any specs that were not accepted (if queue_fn partially consumed).
                if count >= len(self._pending_avatar_specs):
                    self._pending_avatar_specs.clear()
                else:
                    del self._pending_avatar_specs[:count]
            return count
        except Exception as e:
            logger.debug(f"[DREAM-EVO] Avatar spec application skipped: {e}")
            return 0

    def _apply_dpme(self, systems: Dict[str, Any]) -> bool:
        """Push structural pressure directives into DPME."""
        if not self._pending_directives:
            return False

        guidance = self.pressure_steering.apply_to_dpme(self._pending_directives)
        if not guidance:
            return False

        try:
            # Import and call the global function
            from aurora_consciousness_engine import set_external_pressure_guidance
            set_external_pressure_guidance(guidance)
            logger.debug(
                f"[DREAM-EVO] DPME guidance applied: "
                f"primary={guidance.get('primary_channel')}, "
                f"score={guidance.get('score', 0):.2f}"
            )
            return True
        except Exception as e:
            logger.debug(f"[DREAM-EVO] DPME guidance skipped: {e}")
            return False

    def _apply_genealogy(self, systems: Dict[str, Any]) -> int:
        """Push dream evidence into genealogy logger."""
        if not self._pending_evidence:
            return 0

        genealogy = systems.get('genealogy')
        if not genealogy:
            # Try accessing through runtime systems
            runtime_systems = systems.get('_runtime_systems')
            if runtime_systems and hasattr(runtime_systems, 'genealogy'):
                genealogy = runtime_systems.genealogy

        if not genealogy or not hasattr(genealogy, 'observe'):
            return 0

        entries = self.genealogy_bridge.format_for_genealogy(self._pending_evidence)
        count = 0

        for entry in entries:
            try:
                # Build PressureVec-compatible objects
                p_before = entry["pressure_before"]
                p_after = entry["pressure_after"]
                trace = entry["trace"]
                notes = entry.get("notes", {})

                # The genealogy logger expects PressureVec objects
                # Try to use its constructor
                if hasattr(genealogy, '_PressureVec'):
                    PVec = genealogy._PressureVec
                else:
                    # Import directly
                    try:
                        from aurora_internal.constraint_genealogy import PressureVec
                        PVec = PressureVec
                    except ImportError:
                        continue

                # Build TraceItem objects
                try:
                    from aurora_internal.constraint_genealogy import TraceItem
                    trace_items = [
                        TraceItem(kind=t["kind"], id=t["id"])
                        for t in trace
                    ]
                except ImportError:
                    continue

                pv_before = PVec(
                    X=p_before.get("X", 0.0),
                    T=p_before.get("T", 0.0),
                    N=p_before.get("N", 0.0),
                    B=p_before.get("B", 0.0),
                    A=p_before.get("A", 0.0),
                )
                pv_after = PVec(
                    X=p_after.get("X", 0.0),
                    T=p_after.get("T", 0.0),
                    N=p_after.get("N", 0.0),
                    B=p_after.get("B", 0.0),
                    A=p_after.get("A", 0.0),
                )

                genealogy.observe(
                    pressure_before=pv_before,
                    trace=trace_items,
                    pressure_after=pv_after,
                    state_sig_before=entry.get("state_sig_before", ""),
                    state_sig_after=entry.get("state_sig_after", ""),
                    notes=notes,
                )
                count += 1
            except Exception as e:
                logger.debug(f"[DREAM-EVO] Genealogy entry skipped: {e}")

        return count

    def _apply_expression(self, systems: Dict[str, Any]) -> int:
        """Push expression hints into ExpressionEcology."""
        if not self._pending_expression_hints:
            return 0

        perception = systems.get('perception')
        if not perception:
            return 0

        ecology = getattr(perception, 'ecology', None)
        if not ecology:
            return 0

        count = 0
        for hint in self._pending_expression_hints:
            try:
                if hint.direction == "reinforce":
                    # Spawn a biased expression offspring with higher base fitness
                    offspring = ecology.spawn(
                        i_state="i_is",
                        base_fitness=0.5 + hint.strength * 0.3,
                    )
                    if offspring:
                        ecology.select(offspring.offspring_id, 0.6 + hint.strength * 0.2)
                        count += 1
                elif hint.direction == "attenuate":
                    # Run a generation cycle to cull weak patterns
                    # (only if enough population exists)
                    if hasattr(ecology, 'population') and len(ecology.population) > 10:
                        ecology.run_generation()
                        count += 1
            except Exception as e:
                logger.debug(f"[DREAM-EVO] Expression hint skipped: {e}")

        return count

    def _apply_voice(self, systems: Dict[str, Any]) -> int:
        """Push dream performance into VoiceGenome evolution."""
        if not self._last_summary:
            return 0

        # Preferred path: simulation session learner voice genome
        voice = None
        simulation = systems.get('simulation')
        session = getattr(simulation, 'session', None) if simulation else None
        learner = getattr(session, 'learner', None) if session else None
        candidate = getattr(learner, 'voice_genome', None) if learner else None
        if candidate and hasattr(candidate, 'evolve'):
            voice = candidate

        # Fallback path for stacks where voice lives in Layer 5 perception.
        if voice is None:
            perception = systems.get('perception')
            candidate = getattr(perception, 'voice', None) if perception else None
            if candidate and hasattr(candidate, 'evolve'):
                voice = candidate

        if voice is None:
            return 0

        summary = self._last_summary
        mean = sum(summary.mean_scores.values()) / max(len(summary.mean_scores), 1)

        try:
            voice.evolve({
                'user_engaged': min(1.0, mean * 1.5),
                'comfort': min(1.0, summary.episode_fitness * 1.2),
            })
            return 1
        except Exception as e:
            logger.debug(f"[DREAM-EVO] Voice evolution skipped: {e}")
            return 0

    def _apply_learner(self, systems: Dict[str, Any]) -> int:
        """Push dream observations into ConsciousLearner."""
        if not self._pending_learner_observations:
            return 0

        simulation = systems.get('simulation')
        if not simulation:
            return 0

        session = getattr(simulation, 'session', None)
        if not session:
            return 0
        learner = getattr(session, 'learner', None)
        if not learner or not hasattr(learner, 'observe_outcome'):
            return 0

        count = 0
        for obs_data in self._pending_learner_observations:
            try:
                # Build ConversationObservation from obs_data
                from aurora_simulation_engine import (
                    ConversationObservation,
                    ConceptualResponse,
                    ResponseConcept,
                )

                observation = ConversationObservation(
                    avatar_engaged=obs_data.get("avatar_engaged", False),
                    avatar_opened_up=obs_data.get("avatar_opened_up", False),
                    avatar_asked_followup=obs_data.get("avatar_asked_followup", False),
                    avatar_pulled_back=obs_data.get("avatar_pulled_back", False),
                    conversation_deepened=obs_data.get("conversation_deepened", False),
                    connection_felt_stronger=obs_data.get("connection_felt_stronger", False),
                    tension_arose=obs_data.get("tension_arose", False),
                    flow_maintained=obs_data.get("flow_maintained", False),
                )

                # Create a minimal ConceptualResponse for the learner
                primary = (
                    getattr(ResponseConcept, "REFLECTIVE_INSIGHT", None)
                    or getattr(ResponseConcept, "THOUGHTFUL_REFLECTION", None)
                )
                if primary is None:
                    raise ValueError("No compatible ResponseConcept for dream observation")
                selected = ConceptualResponse(
                    primary_concept=primary,
                    intensity=0.5,
                    intention=obs_data.get("understanding_text", "dream observation"),
                )

                context_type = obs_data.get("context_type", "dream")
                learner.observe_outcome(selected, observation, context_type)
                count += 1
            except Exception as e:
                logger.debug(f"[DREAM-EVO] Learner observation skipped: {e}")

        return count

    def _apply_code_evolution(self, systems: Dict[str, Any]) -> int:
        """Push dream evidence into code evolution system."""
        self._last_code_evolution_refs = []
        if not self._pending_evidence:
            return 0

        # Try to find the code evolution chamber
        code_chamber = systems.get('code_chamber')
        if not code_chamber:
            code_chamber = systems.get('chamber')
        if not code_chamber:
            runtime_systems = systems.get('_runtime_systems')
            if runtime_systems and hasattr(runtime_systems, 'chamber'):
                code_chamber = runtime_systems.chamber

        outcomes = self.genealogy_bridge.format_for_code_evolution(
            self._pending_evidence
        )
        pressure_profile = self.pressure_steering.get_evolution_pressure_config(
            self._pending_directives
        )
        policy_snapshot = self.avatar_synthesizer.policy_snapshot()
        if outcomes:
            for outcome in outcomes:
                notes = dict(outcome.get("notes", {}) or {})
                if pressure_profile:
                    notes["pressure_profile"] = dict(pressure_profile)
                    outcome["pressure_profile"] = dict(pressure_profile)
                if policy_snapshot:
                    notes["avatar_policy"] = {
                        "samples": int(policy_snapshot.get("samples", 0) or 0),
                        "global": dict(policy_snapshot.get("global", {}) or {}),
                        "axis": dict(policy_snapshot.get("axis", {}) or {}),
                        "top_pressure_dimensions": list(
                            policy_snapshot.get("top_pressure_dimensions", []) or []
                        ),
                    }
                outcome["notes"] = notes
        count = 0

        def _record_ref(
            outcome: Dict[str, Any],
            registration: Dict[str, Any],
            *,
            source: str,
            operation_lineage_id: str = "",
            mutation_id: str = "",
        ) -> None:
            notes = dict(outcome.get("notes", {}) or {})
            evidence_id = str(notes.get("evidence_id", "") or "").strip()
            ref = {
                "source": str(source or "unknown"),
                "source_episode_id": str(notes.get("episode_id", "") or "").strip(),
                "seed_lineage_id": str(notes.get("seed_lineage_id", "") or "").strip(),
                "evidence_id": evidence_id,
                "mutation_name": str(outcome.get("mutation_name", "") or "").strip(),
                "mutation_id": str(mutation_id or registration.get("mutation_id", "") or "").strip(),
                "operator_key": str(registration.get("operator_key", "") or "").strip(),
                "ability_id": str(registration.get("ability_id", "") or "").strip(),
                "operation_lineage_id": str(operation_lineage_id or "").strip(),
                "registered": bool(registration.get("registered", False)),
                "accepted": bool(registration.get("accepted", outcome.get("checks_passed", False))),
                "constraints": [
                    str(item) for item in (outcome.get("constraints_used", []) or []) if str(item)
                ],
                "target_files": [
                    str(item) for item in (outcome.get("target_files", []) or []) if str(item)
                ],
            }
            self._last_code_evolution_refs.append(ref)

        # Prefer direct chamber ingestion when available.
        if code_chamber:
            for outcome in outcomes:
                try:
                    # Register as an observation if the chamber supports it
                    if hasattr(code_chamber, 'observe_external_evidence'):
                        applied = code_chamber.observe_external_evidence(outcome)
                        if isinstance(applied, dict):
                            reg = dict(applied.get("genealogy_registration", {}) or {})
                            _record_ref(
                                outcome,
                                reg,
                                source="code_chamber",
                                operation_lineage_id=str(applied.get("operation_lineage_id", "") or ""),
                                mutation_id=str(applied.get("mutation_id", "") or ""),
                            )
                            if bool(applied.get("applied", False)) or bool(reg.get("registered", False)):
                                count += 1
                        else:
                            count += 1
                except Exception as e:
                    logger.debug(f"[DREAM-EVO] Code evolution entry skipped: {e}")

        if count > 0:
            return count

        # Fallback path: register code-evolution outcomes into genealogy when
        # chamber-level ingestion hook is unavailable in this runtime.
        genealogy = systems.get('genealogy')
        if not genealogy:
            runtime_systems = systems.get('_runtime_systems')
            if runtime_systems and hasattr(runtime_systems, 'genealogy'):
                genealogy = runtime_systems.genealogy
        if not genealogy or not hasattr(genealogy, 'register_code_evolution_outcome'):
            return 0

        last_fitness = 0.0
        if self._last_summary is not None:
            last_fitness = float(getattr(self._last_summary, "episode_fitness", 0.0) or 0.0)

        def _clamp01(v: Any) -> float:
            try:
                x = float(v)
            except Exception:
                x = 0.0
            return max(0.0, min(1.0, x))

        for outcome in outcomes:
            try:
                notes = dict(outcome.get("notes", {}) or {})
                evidence_id = str(notes.get("evidence_id", "") or "").strip()
                evidence_type = str((notes.get("evidence_type") or outcome.get("mutation_name", "dream_evidence"))).strip()
                mutation_id = f"DREAM:{evidence_id}" if evidence_id else f"DREAM:{int(time.time() * 1000)}"

                pressure_before = dict(outcome.get("pressure_before", {}) or {})
                pressure_after = dict(outcome.get("pressure_after", {}) or {})
                pressure_delta = 0.0
                for axis in ("X", "T", "N", "B", "A"):
                    b = float(pressure_before.get(axis, 0.0) or 0.0)
                    a = float(pressure_after.get(axis, 0.0) or 0.0)
                    pressure_delta += abs(b - a)
                pressure_score = _clamp01(pressure_delta)

                payload = {
                    "mutation_id": mutation_id,
                    "operator_key": f"dream_{evidence_type}",
                    "accepted": bool(outcome.get("checks_passed", False)),
                    "constraints": [str(c) for c in (outcome.get("constraints_used", []) or []) if str(c)],
                    "target_files": [str(p) for p in (outcome.get("target_files", []) or []) if str(p)],
                    "changed_files": [],
                    "change_count": 0,
                    "score": _clamp01(notes.get("confidence", 0.0)),
                    "avg_fitness": float(last_fitness),
                    "genealogy_pressure": pressure_score,
                    "compile_failures": 0,
                    "conflicts_delta": 0.0,
                    "rewrite_profile": "dream_evidence",
                    "effect_modes": [str(outcome.get("mutation_name", "dream_evidence"))],
                    "apply_duration_s": 0.0,
                    "agency_time_credit": 0.0,
                    "temporal_overhead_penalty": 0.0,
                }
                res = dict(genealogy.register_code_evolution_outcome(payload) or {})
                _record_ref(
                    outcome,
                    res,
                    source="genealogy_fallback",
                    mutation_id=mutation_id,
                )
                if bool(res.get("registered", False)):
                    count += 1
            except Exception as e:
                logger.debug(f"[DREAM-EVO] Genealogy fallback code-evolution entry skipped: {e}")

        return count

    # ================================================================
    # AVATAR SPEC ACCESS (for SimulationSession integration)
    # ================================================================

    def get_avatar_specs(self) -> List[PressureSpecializedAvatarSpec]:
        """
        Consume pending avatar specs (fallback/manual path).
        Preferred path is apply()->SimulationSession.queue_avatar_specs().
        """
        specs = list(self._pending_avatar_specs)
        self._pending_avatar_specs.clear()
        return specs

    # ================================================================
    # STATUS / DIAGNOSTICS
    # ================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive status for monitoring."""
        return {
            "compiled": self._compiled,
            "episodes_processed": self._episodes_processed,
            "queue_length": self.curriculum_queue.queue_length,
            "completed_packs": self.curriculum_queue.completed_count,
            "active_directives": self.pressure_steering.active_directive_count,
            "total_directives_generated": self.pressure_steering.directives_generated,
            "avatar_specs_pending": len(self._pending_avatar_specs),
            "total_avatar_specs": self.avatar_synthesizer.specs_generated,
            "avatar_policy": self.avatar_synthesizer.policy_snapshot(),
            "last_policy_feedback": dict(self._last_policy_feedback or {}),
            "evidence_records": self.genealogy_bridge.records_generated,
            "slip_profiles": self.slip_profiler.profiles_generated,
            "rubric_scores": self.rubric_engine.scored_count,
            "last_episode_fitness": (
                self._last_summary.episode_fitness
                if self._last_summary else None
            ),
            "current_pack": (
                self._current_pack.episode_id
                if self._current_pack else None
            ),
        }
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
