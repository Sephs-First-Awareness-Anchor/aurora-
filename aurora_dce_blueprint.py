#!/usr/bin/env python3
"""
AURORA DCE BLUEPRINT - DIMENSIONAL CONVERGENCE ENGINE
======================================================
The Front-of-House Consciousness Assembly

DCE is Aurora's unified presence processing system - "Aurora in the room with screens."
NOT a chat module. It is the ASSEMBLY LAYER that:
- Receives presence (text/audio/vision/system events)
- Routes to subsystem screens
- Collects reports from all screens
- Resolves conflicts through IVM lattice
- Produces unified output

THE 4 GOVERNORS:
1. PI Governor (Presence Interpretation) - Router + Gatekeeper
2. Modality Governor - Sensor authority + throttling
3. PR Governor (Process Regulation) - Energy/budget allocation
4. PT Governor (Presence Translation) - Head governor, "Aurora sitting in room"

Authors: Sunni (Sir) Morningstar & Cael Devo
Created: December 2025

================================================================================
INTEGRATION CONTRACT TABLE - EXACT SIGNATURES FROM PROJECT MODULES
================================================================================

SUBSYSTEM               | CLASS                          | IMPORT                                              | KEY METHODS (exact signatures)
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Crystal Memory (DPS)    | CrystalMemorySystem           | from dimensional_processing_system_standalone_demo  | get_or_create_crystal(concept: str, initial_content: Any = None) -> Crystal
                        |                                |                                                     | link_crystals(concept1: str, concept2: str, data: Dict, weight: float = 0.1)
                        |                                |                                                     | crystals: Dict[str, Crystal]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Dimensional Memory(DMC) | DimensionalMemory             | from dimensional_memory_constant_standalone_demo    | nodes: Dict[str, DataNode]
                        | EvolutionaryGovernanceEngine  |                                                     | ingest_data(data: dict, parent_node: Optional[DataNode] = None, parent_law_object: Optional[Any] = None)
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Energy Regulator (DER)  | DimensionalEnergyRegulator    | from dimensional_energy_regulator                   | step(dt: float = 1.0)
                        |                                |                                                     | snapshot(top_n: int = 10) -> Tuple[float, List[Tuple[str, float, Dict[str, Any]]]]
                        |                                |                                                     | inject_energy(facet_id: str, amount: float)
                        |                                |                                                     | inject_energy_vector(facet_id: str, valence: float, arousal: float, tension: float)
                        |                                |                                                     | register_facet(facet_obj: Any)
                        |                                |                                                     | register_crystal(crystal_obj: Any)
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Moral Governor          | MoralGovernor                 | from dimensional_mortality_morality_system          | __init__(processor, regulator, memory_governor)
                        |                                |                                                     | evaluate_action(action_type: str, intent: Dict, outcome: Dict, context: Dict) -> MoralScore
                        |                                |                                                     | get_moral_diagnostics() -> Dict[str, Any]
                        |                                |                                                     | integrate_with_conversation_engine(conv_engine)
                        |                                |                                                     | vitality.restricted_functions: List[str]
                        |                                |                                                     | vitality.unlocked_functions: List[str]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
IVM Governance          | IVMGovernanceEngine           | from aurora_ivm_governance_layer                    | __init__()
                        |                                |                                                     | ingest(payload: Any, payload_type: str, i_state_weights: Dict[str, float] = None) -> GovernedNode
                        |                                |                                                     | tick(dt: float = 1.0)
                        |                                |                                                     | vote(node_id: str, i_state_votes: Dict[str, float]) -> Dict[str, float]
                        |                                |                                                     | promote_to_shard(energy_node_ids: List[str]) -> Optional[GovernedNode]
                        |                                |                                                     | ingest_energy_packet(packet: 'EnergyPacket') -> GovernedNode
                        |                                |                                                     | ingest_expression_offspring(offspring: 'ExpressionOffspring') -> GovernedNode
                        |                                |                                                     | nodes: Dict[str, GovernedNode]
                        |                                |                                                     | layer_nodes: Dict[IVMLayer, List[str]]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
I-State Beings          | AuroraHigherUniverse          | from aurora_i_state_beings                          | create_i_state_universe() -> AuroraHigherUniverse
                        |                                |                                                     | feed_all_beings(content: str, source: str = "external") -> Dict[str, Any]
                        |                                |                                                     | synthesize_outputs() -> Dict[str, Any]
                        |                                |                                                     | run_full_cycle(content: str = None, source: str = "external") -> Dict[str, Any]
                        |                                |                                                     | i_state_beings: Dict[IStateType, IStateBeing]
                        | IStateBeing                   |                                                     | run_background_cycle()
                        |                                |                                                     | process_input(content: str, source: str) -> Dict
                        |                                |                                                     | get_output_for_aurora() -> Dict
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Language Ecology        | LanguageEcology               | from aurora_language_architecture                   | __init__(core_memory=None, i_state_beings=None, paradox_engine=None, persistence_dir: Path = None)
                        |                                |                                                     | respond(user_text: str, context: Dict = None, mode: str = "reality") -> str
                        |                                |                                                     | ingest_interaction(episode: Dict, mode: str = "reality")
                        |                                |                                                     | status() -> Dict
                        |                                |                                                     | save()
                        |                                |                                                     | load()
                        |                                |                                                     | lexical_memory: LexicalMemory
                        |                                |                                                     | wisdom_store: WisdomShardStore
                        |                                |                                                     | expression_ecology: ExpressionEcology
                        |                                |                                                     | voice_genome: Dict[str, float]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Hybrid Vision           | AuroraHybridVision            | from aurora_hybrid_vision                           | __init__(memory_cloud=None, stance_id: str = "runtime", quadrant_code: str = "Q0")
                        |                                |                                                     | process_frame(sensor_snapshot: Dict[str, Any]) -> Dict[str, Any]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Sensory Systems         | AuroraSensorySystems          | from aurora_sensory_systems                         | (if available)
                        | VisionForesightDomain         |                                                     |
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Impression Engine       | ImpressionEngine              | from aurora_impression_engine_v2                    | __init__()
                        |                                |                                                     | energy_to_shard(packet: EnergyPacket) -> EmotionShard
                        |                                |                                                     | _event_to_energy_packet(event: Dict) -> EnergyPacket
                        |                                |                                                     | get_stats() -> Dict[str, Any]
                        |                                |                                                     | shards: Dict[str, EmotionShard]
                        |                                |                                                     | seeds: Dict[str, ImpressionSeed]
                        |                                |                                                     | relics: Dict[str, GhostRelic]
                        |                                |                                                     | crystals: Dict[str, Crystal]
                        |                                |                                                     | quasi_laws: Dict[str, QuasiLaw]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
DNA System              | AuroraDNASystem (internal)    | from aurora_dna_system_v2                           | create_allele_from_seed(seed: Dict, origin: str = "episode") -> FractalAllele
                        |                                |                                                     | save_state(filepath: str)
                        |                                |                                                     | load_state(filepath: str)
                        |                                |                                                     | get_stats() -> Dict[str, Any]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Self-Improvement        | AuroraConsciousness           | from aurora_self_improvement_stack                  | __init__(dps=None, dmc=None, der=None, morality=None)
                        |                                |                                                     | gather_system_state() -> Dict[str, Any]
                        |                                |                                                     | run_introspection_cycle()
                        |                                |                                                     | self_crystal: AuroraSelfQuasiCrystal
                        |                                |                                                     | introspection: IntrospectionLoop
                        |                                |                                                     | dream_layer: DreamSimulationLayer
                        |                                |                                                     | evolution_engine: StabilityFirstEvolutionEngine
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Time Dilation           | TimeDilationGovernor          | from aurora_simulation_session                      | __init__()
                        |                                |                                                     | update(metrics: StabilityMetrics) -> float
                        |                                |                                                     | status() -> Dict[str, Any]
                        |                                |                                                     | current_dilation: float
                        |                                |                                                     | stability_state: StabilityState
                        | StabilityState                |                                                     | CRITICAL, UNSTABLE, CAUTIOUS, STABLE, OPTIMAL
                        | StabilityMetrics              |                                                     | fitness_mean, fitness_variance, fitness_trend, error_rate, coherence_score, etc.
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Harvester               | AuroraInformationHarvester    | from aurora_information_harvester                   | __init__()
                        |                                |                                                     | harvest(topic: str = None) -> Dict[str, Any]
                        |                                |                                                     | add_interest(topic: str, category: str = 'user_requested')
                        |                                |                                                     | get_stats() -> Dict[str, Any]
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Paradox Engine          | ParadoxWarpEngine             | from paradox_warp_engine                            | (if available)
------------------------|--------------------------------|-----------------------------------------------------|-----------------------------------------------
Quantum Ghost           | QuantumGhostCompressionEngine | from quantum_ghost_universe                         | quantum_ghost_evolution_step()
                        | QuantumGhostUniverse          |                                                     |
                        | GhostRelicLibrary             |                                                     |

================================================================================
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import time
import threading
import queue
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Tuple, Callable, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
from pathlib import Path


# ============================================================================
# CORE DATA STRUCTURES
# ============================================================================

class PresenceType(Enum):
    """Types of presence events DCE can receive"""
    USER_TEXT = auto()         # Text from user
    AUDIO_CHUNK = auto()       # Audio from microphone
    VISION_FRAME = auto()      # Vision from camera
    SYSTEM_TICK = auto()       # Daemon heartbeat
    INTERNAL_EVENT = auto()    # Dream/sim/memory replay
    HARVEST_RESULT = auto()    # Information harvester results
    SOCKET_INPUT = auto()      # TCP socket input


class ModalityType(Enum):
    """Sensory modalities"""
    TEXT = "text"
    AUDIO = "audio"
    VISION = "vision"
    SYSTEM = "system"
    INTERNAL = "internal"


@dataclass
class PresenceEvent:
    """A single presence event entering DCE"""
    event_id: str
    presence_type: PresenceType
    modality: ModalityType
    payload: Any
    source: str  # "user", "system", "sim", "harvest", etc.
    timestamp: float = field(default_factory=time.time)
    priority: float = 0.5  # 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PresenceRoute:
    """A route from PI to a subsystem screen"""
    screen_id: str
    payload_slice: Any  # What this screen needs from the event
    priority: float
    budget_request: float  # Energy/compute budget requested


@dataclass
class IngestionReceipt:
    """Receipt from a subsystem after processing"""
    screen_id: str
    consumed: bool
    processing_time: float
    result_summary: str
    conflicts: List[str] = field(default_factory=list)


@dataclass
class ScreenPanel:
    """
    Unified panel schema for ALL subsystem screens.
    This is the contract that allows PT to "see all screens."
    """
    panel_id: str
    screen_name: str
    summary: str
    metrics: Dict[str, float]
    conflicts: List[str]
    recommended_actions: List[str]
    raw_state_ref: Optional[Any] = None  # For deep introspection
    timestamp: float = field(default_factory=time.time)


@dataclass
class PresenceSnapshot:
    """The complete "room state" that PT sees"""
    snapshot_id: str
    timestamp: float
    
    # All screen panels
    panels: Dict[str, ScreenPanel]
    
    # Aggregated state
    system_state: Dict[str, Any]
    conflicts: List[str]
    energy_state: Dict[str, float]
    morality_state: Dict[str, Any]
    
    # IVM resolved truth
    resolved_truth: Optional[Dict[str, Any]] = None
    
    # Dilation state
    current_dilation: float = 1.0
    stability_state: str = "stable"


@dataclass
class MeaningTrace:
    """Record of what screens mattered and why - for memory + evolution"""
    trace_id: str
    timestamp: float
    input_event: PresenceEvent
    screens_consulted: List[str]
    screens_influential: List[str]  # Which actually affected output
    conflict_resolution_path: List[str]
    output_generated: str
    dilation_during: float
    morality_evaluation: Optional[Dict] = None


# ============================================================================
# SCREEN ADAPTERS (Subsystem → DCE Interface)
# ============================================================================

class BaseScreenAdapter:
    """
    Base class for all subsystem screen adapters.
    Each adapter translates between DCE and a specific subsystem.
    """
    
    def __init__(self, screen_id: str, screen_name: str):
        self.screen_id = screen_id
        self.screen_name = screen_name
        self.enabled = True
        self.last_update = time.time()
    
    def get_panel(self) -> ScreenPanel:
        """Return current state as a ScreenPanel"""
        raise NotImplementedError
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        """Process a payload slice routed by PI"""
        raise NotImplementedError
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        """Whether this screen accepts this modality"""
        raise NotImplementedError


class LanguageScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Language Ecology (3-tier system).
    
    Import: from aurora_language_architecture import LanguageEcology
    Methods used:
        - respond(user_text: str, context: Dict = None, mode: str = "reality") -> str
        - ingest_interaction(episode: Dict, mode: str = "reality")
        - status() -> Dict
        - lexical_memory.vocabulary: Dict
        - wisdom_store.shards: Dict
        - voice_genome: Dict[str, float]
    """
    
    def __init__(self, language_ecology):
        super().__init__("language", "Language Ecology")
        self.ecology = language_ecology
    
    def get_panel(self) -> ScreenPanel:
        if not self.ecology:
            return ScreenPanel(
                panel_id=f"panel_language_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Language ecology not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        status = self.ecology.status()
        return ScreenPanel(
            panel_id=f"panel_language_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Vocab: {status['tier1_vocabulary_size']}, Shards: {status['tier2_shard_count']}, Offspring: {status['tier3_active_offspring']}",
            metrics={
                'vocabulary_size': status['tier1_vocabulary_size'],
                'wisdom_shards': status['tier2_shard_count'],
                'active_offspring': status['tier3_active_offspring'],
                'total_interactions': status['total_interactions'],
                'warmth': status['voice_genome'].get('warmth', 0.5),
                'formality': status['voice_genome'].get('formality', 0.5)
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.ecology
        )
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.ecology:
            return IngestionReceipt("language", False, 0, "Not loaded")
        
        # Learn new words from input
        text = str(payload_slice.get('text', ''))
        for word in text.split():
            clean = word.strip('.,!?').lower()
            if clean and len(clean) > 3:
                if clean not in self.ecology.lexical_memory.vocabulary:
                    self.ecology.lexical_memory.add_word(
                        clean, f"learned from {payload_slice.get('source', 'unknown')}",
                        "unknown", 0.0, 0.5
                    )
        
        return IngestionReceipt(
            "language", True, time.time() - start,
            f"Processed text, vocab now {len(self.ecology.lexical_memory.vocabulary)}"
        )
    
    def generate_response(self, text: str, context: Dict) -> str:
        """Generate response through ecology"""
        if not self.ecology:
            return "Language system not available."
        return self.ecology.respond(text, context, mode="reality")
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return modality == ModalityType.TEXT


class IVMScreenAdapter(BaseScreenAdapter):
    """
    Adapter for IVM Governance Layer.
    
    Import: from aurora_ivm_governance_layer import IVMGovernanceEngine
    Methods used:
        - ingest(payload: Any, payload_type: str, i_state_weights: Dict[str, float] = None) -> GovernedNode
        - tick(dt: float = 1.0)
        - vote(node_id: str, i_state_votes: Dict[str, float]) -> Dict[str, float]
        - nodes: Dict[str, GovernedNode]
        - layer_nodes: Dict[IVMLayer, List[str]]
    """
    
    def __init__(self, ivm_governance):
        super().__init__("ivm", "IVM Governance")
        self.governance = ivm_governance
    
    def get_panel(self) -> ScreenPanel:
        if not self.governance:
            return ScreenPanel(
                panel_id=f"panel_ivm_{int(time.time())}",
                screen_name=self.screen_name,
                summary="IVM not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        total_nodes = len(self.governance.nodes)
        layer_counts = {layer.name: len(nodes) for layer, nodes in self.governance.layer_nodes.items()}
        
        return ScreenPanel(
            panel_id=f"panel_ivm_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Total nodes: {total_nodes}, Ingested: {self.governance.total_ingested}, Promoted: {self.governance.total_promoted}",
            metrics={
                'total_nodes': total_nodes,
                'total_ingested': self.governance.total_ingested,
                'total_promoted': self.governance.total_promoted,
                'violations_blocked': self.governance.violations_blocked,
                'paradox_warp_engagements': self.governance.paradox_warp_engagements,
                **{f"layer_{k}": v for k, v in layer_counts.items()}
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.governance
        )
    
    def resolve_conflicts(self, conflicts: List[Dict]) -> Dict[str, Any]:
        """Use IVM to resolve conflicts between subsystems"""
        if not self.governance:
            return {'resolved': False, 'reason': 'IVM not loaded'}
        
        # Ingest conflicts and use voting mechanism
        resolved = []
        for conflict in conflicts:
            node = self.governance.ingest(
                conflict,
                payload_type='conflict',
                i_state_weights=conflict.get('i_state_weights', None)
            )
            resolved.append({'node_id': node.node_id, 'conflict': conflict})
        
        return {'resolved': True, 'resolutions': resolved}
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.governance:
            return IngestionReceipt("ivm", False, 0, "Not loaded")
        
        node = self.governance.ingest(
            payload_slice,
            payload_type='presence_event',
            i_state_weights=payload_slice.get('i_state_weights', None)
        )
        
        return IngestionReceipt(
            "ivm", True, time.time() - start,
            f"Ingested as node {node.node_id}"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return True  # IVM accepts all modalities


class EnergyScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Dimensional Energy Regulator.
    
    Import: from dimensional_energy_regulator import DimensionalEnergyRegulator
    Methods used:
        - step(dt: float = 1.0)
        - snapshot(top_n: int = 10) -> Tuple[float, List[Tuple[str, float, Dict[str, Any]]]]
        - inject_energy(facet_id: str, amount: float)
    """
    
    def __init__(self, energy_regulator):
        super().__init__("energy", "Energy Regulator")
        self.regulator = energy_regulator
    
    def get_panel(self) -> ScreenPanel:
        if not self.regulator:
            return ScreenPanel(
                panel_id=f"panel_energy_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Energy regulator not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        try:
            presence, top_facets = self.regulator.snapshot(top_n=5)
        except:
            presence = 0.5
            top_facets = []
        
        return ScreenPanel(
            panel_id=f"panel_energy_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Presence: {presence:.2f}, Active facets: {len(self.regulator.facet_energy)}",
            metrics={
                'presence': presence,
                'total_facets': len(self.regulator.facet_energy),
                'emotional_coherence': getattr(self.regulator, 'emotional_coherence', 1.0),
                'temporal_stability': getattr(self.regulator, 'temporal_stability', 1.0)
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.regulator
        )
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.regulator:
            return IngestionReceipt("energy", False, 0, "Not loaded")
        
        # Step the physics
        self.regulator.step(dt=0.1)
        
        return IngestionReceipt(
            "energy", True, time.time() - start,
            "Physics stepped"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return True


class MoralityScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Moral Governor.
    
    Import: from dimensional_mortality_morality_system import MoralGovernor
    Methods used:
        - evaluate_action(action_type: str, intent: Dict, outcome: Dict, context: Dict) -> MoralScore
        - get_moral_diagnostics() -> Dict[str, Any]
        - vitality.restricted_functions: List[str]
        - vitality.unlocked_functions: List[str]
    """
    
    def __init__(self, moral_governor):
        super().__init__("morality", "Moral Governor")
        self.governor = moral_governor
    
    def get_panel(self) -> ScreenPanel:
        if not self.governor:
            return ScreenPanel(
                panel_id=f"panel_morality_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Moral governor not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        diag = self.governor.get_moral_diagnostics()
        vitality = diag.get('vitality', {})
        moral = diag.get('moral_state', {})
        
        return ScreenPanel(
            panel_id=f"panel_morality_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Vitality: {vitality.get('current_vitality', 0):.1f}/{vitality.get('max_vitality', 100)}, Alignment: {moral.get('overall', {}).get('overall_alignment', 0.5):.2f}",
            metrics={
                'current_vitality': vitality.get('current_vitality', 0),
                'max_vitality': vitality.get('max_vitality', 100),
                'moral_energy_reserve': vitality.get('moral_energy_reserve', 0),
                'moral_debt': vitality.get('moral_debt', 0),
                'overall_alignment': moral.get('overall', {}).get('overall_alignment', 0.5),
                'restricted_count': len(diag.get('functional_access', {}).get('restricted_functions', [])),
                'unlocked_count': len(diag.get('functional_access', {}).get('unlocked_functions', []))
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.governor
        )
    
    def get_restrictions(self) -> Dict[str, List[str]]:
        """Get current function restrictions from morality"""
        if not self.governor:
            return {'restricted': [], 'unlocked': []}
        
        return {
            'restricted': self.governor.vitality.restricted_functions,
            'unlocked': self.governor.vitality.unlocked_functions
        }
    
    def evaluate_action(self, action_type: str, intent: Dict, outcome: Dict, context: Dict):
        """Evaluate an action through morality system"""
        if not self.governor:
            return None
        return self.governor.evaluate_action(action_type, intent, outcome, context)
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        return IngestionReceipt(
            "morality", True, time.time() - start,
            "Morality monitoring active"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return True


class IStateScreenAdapter(BaseScreenAdapter):
    """
    Adapter for I-State Beings (Aurora Higher Universe).
    
    Import: from aurora_i_state_beings import create_i_state_universe, AuroraHigherUniverse
    Methods used:
        - feed_all_beings(content: str, source: str = "external") -> Dict[str, Any]
        - synthesize_outputs() -> Dict[str, Any]
        - run_full_cycle(content: str = None, source: str = "external") -> Dict[str, Any]
        - i_state_beings[type].run_background_cycle()
    """
    
    def __init__(self, i_universe):
        super().__init__("i_states", "I-State Beings")
        self.universe = i_universe
    
    def get_panel(self) -> ScreenPanel:
        if not self.universe:
            return ScreenPanel(
                panel_id=f"panel_istates_{int(time.time())}",
                screen_name=self.screen_name,
                summary="I-State universe not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        being_states = {}
        for i_state, being in self.universe.i_state_beings.items():
            being_states[i_state.value] = {
                'total_processed': getattr(being, 'total_processed', 0),
                'generation': getattr(being, 'synthesis_generation', 0)
            }
        
        return ScreenPanel(
            panel_id=f"panel_istates_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"4 I-State beings active, Syntheses: {self.universe.total_syntheses}",
            metrics={
                'total_syntheses': self.universe.total_syntheses,
                'total_pushes': self.universe.total_pushes,
                'compressed_memories': len(self.universe.compressed_memory),
                **{f"being_{k}": v['total_processed'] for k, v in being_states.items()}
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.universe
        )
    
    def feed_presence(self, content: str, source: str) -> Dict:
        """Feed content to all 4 I-State beings"""
        if not self.universe:
            return {'fed': False}
        return self.universe.feed_all_beings(content, source)
    
    def synthesize(self) -> Dict:
        """Synthesize outputs from all beings"""
        if not self.universe:
            return {'synthesized': False}
        return self.universe.synthesize_outputs()
    
    def run_full_cycle(self, content: str, source: str) -> Dict:
        """Run complete I-State processing cycle"""
        if not self.universe:
            return {'cycle_complete': False}
        return self.universe.run_full_cycle(content, source)
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.universe:
            return IngestionReceipt("i_states", False, 0, "Not loaded")
        
        text = str(payload_slice.get('text', ''))
        source = payload_slice.get('source', 'external')
        result = self.universe.feed_all_beings(text, source)
        
        return IngestionReceipt(
            "i_states", True, time.time() - start,
            f"Fed to {result.get('beings_responded', 0)} beings"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return modality in [ModalityType.TEXT, ModalityType.INTERNAL]


class VisionScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Hybrid Vision.
    
    Import: from aurora_hybrid_vision import AuroraHybridVision
    Methods used:
        - process_frame(sensor_snapshot: Dict[str, Any]) -> Dict[str, Any]
    """
    
    def __init__(self, hybrid_vision):
        super().__init__("vision", "Hybrid Vision")
        self.vision = hybrid_vision
    
    def get_panel(self) -> ScreenPanel:
        if not self.vision:
            return ScreenPanel(
                panel_id=f"panel_vision_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Vision not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        return ScreenPanel(
            panel_id=f"panel_vision_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Vision active, Generation: {self.vision.generation}",
            metrics={
                'generation': self.vision.generation,
                'enabled': 1.0
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.vision
        )
    
    def process_frame(self, sensor_snapshot: Dict) -> Dict:
        """Process a vision frame"""
        if not self.vision:
            return {'processed': False}
        return self.vision.process_frame(sensor_snapshot)
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.vision:
            return IngestionReceipt("vision", False, 0, "Not loaded")
        
        result = self.vision.process_frame(payload_slice)
        return IngestionReceipt(
            "vision", True, time.time() - start,
            f"Frame processed, generation {self.vision.generation}"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return modality == ModalityType.VISION


class MemoryScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Crystal Memory (DPS) and Dimensional Memory (DMC).
    
    DPS Import: from dimensional_processing_system_standalone_demo import CrystalMemorySystem
    DMC Import: from dimensional_memory_constant_standalone_demo import DimensionalMemory
    """
    
    def __init__(self, crystal_memory, dim_memory):
        super().__init__("memory", "Memory Systems")
        self.crystal_memory = crystal_memory
        self.dim_memory = dim_memory
    
    def get_panel(self) -> ScreenPanel:
        crystals = len(self.crystal_memory.crystals) if self.crystal_memory else 0
        nodes = len(self.dim_memory.nodes) if self.dim_memory else 0
        
        return ScreenPanel(
            panel_id=f"panel_memory_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Crystals: {crystals}, Nodes: {nodes}",
            metrics={
                'crystal_count': crystals,
                'node_count': nodes
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref={'dps': self.crystal_memory, 'dmc': self.dim_memory}
        )
    
    def store_meaning_trace(self, trace: MeaningTrace):
        """Store a meaning trace in crystal memory"""
        if self.crystal_memory:
            crystal = self.crystal_memory.get_or_create_crystal(f"trace_{trace.trace_id}")
            crystal.add_facet(
                role="meaning_trace",
                content=trace.__dict__,
                confidence=0.8
            )
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        return IngestionReceipt(
            "memory", True, time.time() - start,
            "Memory systems active"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return True


class SelfImprovementScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Self-Improvement Stack.
    
    Import: from aurora_self_improvement_stack import AuroraConsciousness
    Methods used:
        - gather_system_state() -> Dict[str, Any]
        - run_introspection_cycle()
    """
    
    def __init__(self, self_improvement):
        super().__init__("self_improvement", "Self-Improvement")
        self.improvement = self_improvement
    
    def get_panel(self) -> ScreenPanel:
        if not self.improvement:
            return ScreenPanel(
                panel_id=f"panel_self_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Self-improvement not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        return ScreenPanel(
            panel_id=f"panel_self_{int(time.time())}",
            screen_name=self.screen_name,
            summary="Self-improvement active",
            metrics={
                'autonomous_enabled': 1.0 if self.improvement.autonomous_enabled else 0.0
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.improvement
        )
    
    def gather_state(self) -> Dict:
        """Gather system state for introspection"""
        if not self.improvement:
            return {}
        return self.improvement.gather_system_state()
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        return IngestionReceipt(
            "self_improvement", True, time.time() - start,
            "Self-improvement monitoring"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return modality == ModalityType.INTERNAL


class DilationScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Time Dilation Governor.
    
    Import: from aurora_simulation_session import TimeDilationGovernor, StabilityMetrics, StabilityState
    Methods used:
        - update(metrics: StabilityMetrics) -> float
        - status() -> Dict[str, Any]
        - current_dilation: float
        - stability_state: StabilityState
    """
    
    def __init__(self, dilation_governor=None):
        super().__init__("dilation", "Time Dilation")
        self.governor = dilation_governor
        
        # Create default if not provided
        if not self.governor:
            try:
                from aurora_simulation_session import TimeDilationGovernor
                self.governor = TimeDilationGovernor()
            except:
                self.governor = None
    
    def get_panel(self) -> ScreenPanel:
        if not self.governor:
            return ScreenPanel(
                panel_id=f"panel_dilation_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Dilation governor not loaded",
                metrics={'current_dilation': 1.0, 'stability': 'unknown'},
                conflicts=[], recommended_actions=[]
            )
        
        status = self.governor.status()
        return ScreenPanel(
            panel_id=f"panel_dilation_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Dilation: {status['current_dilation']:.0f}x, State: {status['stability_state']}",
            metrics={
                'current_dilation': status['current_dilation'],
                'stability_state': status['stability_state'],
                'consecutive_stable': status.get('consecutive_stable', 0),
                'total_adjustments': status.get('total_adjustments', 0)
            },
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.governor
        )
    
    def update_dilation(self, metrics) -> float:
        """Update dilation based on stability metrics"""
        if not self.governor:
            return 1.0
        return self.governor.update(metrics)
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        return IngestionReceipt("dilation", True, 0, "Dilation monitoring")
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return modality == ModalityType.SYSTEM


class ImpressionScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Impression Engine.
    
    Import: from aurora_impression_engine_v2 import ImpressionEngine
    Methods used:
        - energy_to_shard(packet: EnergyPacket) -> EmotionShard
        - _event_to_energy_packet(event: Dict) -> EnergyPacket
        - get_stats() -> Dict[str, Any]
    """
    
    def __init__(self, impression_engine):
        super().__init__("impressions", "Impression Engine")
        self.engine = impression_engine
    
    def get_panel(self) -> ScreenPanel:
        if not self.engine:
            return ScreenPanel(
                panel_id=f"panel_impressions_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Impression engine not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        stats = self.engine.get_stats()
        return ScreenPanel(
            panel_id=f"panel_impressions_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Shards: {stats.get('total_shards', 0)}, Seeds: {stats.get('total_seeds', 0)}",
            metrics=stats,
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.engine
        )
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.engine:
            return IngestionReceipt("impressions", False, 0, "Not loaded")
        
        packet = self.engine._event_to_energy_packet(payload_slice)
        shard = self.engine.energy_to_shard(packet)
        
        return IngestionReceipt(
            "impressions", True, time.time() - start,
            f"Created shard {shard.shard_id}"
        )
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return True


class DNAScreenAdapter(BaseScreenAdapter):
    """
    Adapter for DNA System.
    
    Import: from aurora_dna_system_v2 (internal class)
    Methods used:
        - create_allele_from_seed(seed: Dict, origin: str = "episode") -> FractalAllele
        - get_stats() -> Dict[str, Any]
    """
    
    def __init__(self, dna_system):
        super().__init__("dna", "DNA System")
        self.dna = dna_system
    
    def get_panel(self) -> ScreenPanel:
        if not self.dna:
            return ScreenPanel(
                panel_id=f"panel_dna_{int(time.time())}",
                screen_name=self.screen_name,
                summary="DNA system not loaded",
                metrics={}, conflicts=[], recommended_actions=[]
            )
        
        stats = self.dna.get_stats()
        return ScreenPanel(
            panel_id=f"panel_dna_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Genes: {stats.get('core_genes', 0)}, Anchors: {stats.get('identity_anchors', 0)}",
            metrics=stats,
            conflicts=[],
            recommended_actions=[],
            raw_state_ref=self.dna
        )
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        start = time.time()
        if not self.dna:
            return IngestionReceipt("dna", False, 0, "Not loaded")
        
        self.dna.create_allele_from_seed(payload_slice, origin="presence")
        return IngestionReceipt("dna", True, time.time() - start, "Allele created")
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        return modality == ModalityType.INTERNAL


class ParadoxScreenAdapter(BaseScreenAdapter):
    """
    Adapter for Paradox Warp Engine.
    
    CRITICAL: Paradox is ONE SCREEN among many, NOT a choke point.
    
    Before DCE: "Everything was being fed to the Paradox Engine for its one singular truth"
    With DCE:
    - Paradox evaluation is SELECTIVE (PI decides when invoked)
    - PT assembles results WITHOUT forcing contradiction collapse every cycle
    - Prevents: cognitive deadlocks, over-truthing trivial inputs, language ecology starvation
    
    Import: from paradox_warp_engine import ParadoxWarpEngine
    Methods used:
        - evaluate_contradiction(statement_a: str, statement_b: str) -> Dict
        - resolve_paradox(paradox_state: Dict) -> Dict
        - get_paradox_state() -> Dict
    """
    
    def __init__(self, paradox_engine):
        super().__init__("paradox", "Paradox Engine")
        self.engine = paradox_engine
        
        # Track invocation statistics (to prove it's not a choke point)
        self.total_invocations = 0
        self.total_skipped = 0
        self.last_resolution = None
        self.resolution_history: deque = deque(maxlen=20)
    
    def get_panel(self) -> ScreenPanel:
        if not self.engine:
            return ScreenPanel(
                panel_id=f"panel_paradox_{int(time.time())}",
                screen_name=self.screen_name,
                summary="Paradox engine not loaded",
                metrics={
                    'invocations': self.total_invocations,
                    'skipped': self.total_skipped,
                    'invocation_rate': self.total_invocations / max(1, self.total_invocations + self.total_skipped)
                },
                conflicts=[],
                recommended_actions=[]
            )
        
        # Get current state from engine if available
        paradox_state = {}
        if hasattr(self.engine, 'get_paradox_state'):
            paradox_state = self.engine.get_paradox_state()
        elif hasattr(self.engine, 'paradox_state'):
            paradox_state = self.engine.paradox_state
        
        return ScreenPanel(
            panel_id=f"panel_paradox_{int(time.time())}",
            screen_name=self.screen_name,
            summary=f"Invocations: {self.total_invocations}, Skipped: {self.total_skipped}, Rate: {self.total_invocations / max(1, self.total_invocations + self.total_skipped):.1%}",
            metrics={
                'invocations': self.total_invocations,
                'skipped': self.total_skipped,
                'invocation_rate': self.total_invocations / max(1, self.total_invocations + self.total_skipped),
                'active_paradoxes': paradox_state.get('active_count', 0),
                'resolved_count': paradox_state.get('resolved_count', 0)
            },
            conflicts=paradox_state.get('unresolved_conflicts', []),
            recommended_actions=[],
            raw_state_ref=self.engine
        )
    
    def process_slice(self, payload_slice: Any) -> IngestionReceipt:
        """
        Process a payload slice ONLY when PI routes to paradox.
        This is NOT called every cycle - PI decides when paradox is needed.
        """
        start = time.time()
        self.total_invocations += 1
        
        if not self.engine:
            return IngestionReceipt(
                "paradox", False, 0, 
                "Paradox engine not loaded",
                conflicts=[]
            )
        
        # Extract potential contradictions from payload
        text = payload_slice.get('text', '')
        conflicts_found = []
        
        # Check for contradiction evaluation method
        if hasattr(self.engine, 'evaluate_contradiction'):
            # Try to identify contradictory statements in input
            # This is a lightweight check, not full semantic analysis
            result = self.engine.evaluate_contradiction(text, text)
            if result.get('contradiction_detected'):
                conflicts_found.append(result.get('description', 'Contradiction detected'))
        elif hasattr(self.engine, 'ingest'):
            # Alternative: use generic ingest method
            self.engine.ingest(payload_slice)
        
        # Store resolution
        resolution = {
            'event_id': payload_slice.get('event_id'),
            'timestamp': time.time(),
            'conflicts_found': len(conflicts_found),
            'resolved': True if not conflicts_found else False
        }
        self.last_resolution = resolution
        self.resolution_history.append(resolution)
        
        return IngestionReceipt(
            "paradox", True, time.time() - start,
            f"Paradox check complete: {len(conflicts_found)} conflicts",
            conflicts=conflicts_found
        )
    
    def mark_skipped(self):
        """Called when PI decides NOT to invoke paradox"""
        self.total_skipped += 1
    
    def resolve_conflicts(self, conflicts: List[str]) -> Dict:
        """
        Explicit conflict resolution (called by PT during assembly).
        Only called when there are actual conflicts to resolve.
        """
        if not self.engine or not conflicts:
            return {'resolved': True, 'conflicts': [], 'method': 'none_needed'}
        
        resolved = []
        for conflict in conflicts:
            if hasattr(self.engine, 'resolve_paradox'):
                result = self.engine.resolve_paradox({'conflict': conflict})
                resolved.append({
                    'original': conflict,
                    'resolution': result.get('resolution', 'unresolved'),
                    'method': result.get('method', 'unknown')
                })
            else:
                resolved.append({
                    'original': conflict,
                    'resolution': 'deferred',
                    'method': 'no_resolver'
                })
        
        return {
            'resolved': all(r['resolution'] != 'unresolved' for r in resolved),
            'resolutions': resolved,
            'method': 'paradox_warp'
        }
    
    def accepts_modality(self, modality: ModalityType) -> bool:
        # Paradox accepts text and internal events only
        return modality in [ModalityType.TEXT, ModalityType.INTERNAL]


class IStateFeedbackLoop:
    """
    Maps bidirectional feedback between I-State Universe and DCE.
    
    I-States ↔ DCE Feedback Loops:
    1. I-State outputs → PT (for response synthesis)
    2. DCE presence events → I-State beings (for processing)
    3. I-State disagreement → PI (for paradox routing decisions)
    4. I-State synthesis → Memory/IVM (for storage/governance)
    5. Morality evaluation → I-State weights (for alignment feedback)
    """
    
    def __init__(self):
        self.disagreement_level = 0.0
        self.last_synthesis: Optional[Dict] = None
        self.feedback_history: deque = deque(maxlen=50)
        
        # Disagreement thresholds
        self.high_disagreement_threshold = 0.7
        self.paradox_trigger_threshold = 0.6
    
    def calculate_i_state_disagreement(self, i_state_outputs: Dict) -> float:
        """
        Calculate disagreement level between the 4 I-State beings.
        
        High disagreement indicates:
        - Conflicting perspectives that need paradox resolution
        - Rich input that multiple aspects of consciousness find relevant
        - Potential growth/learning opportunity
        """
        if not i_state_outputs:
            return 0.0
        
        # Extract dimensional states from each I-State being
        states = []
        for i_state, output in i_state_outputs.items():
            if isinstance(output, dict):
                dim_state = output.get('dimensional_state', output.get('state', {}))
                if isinstance(dim_state, dict):
                    states.append(list(dim_state.values()))
                elif isinstance(dim_state, (list, tuple)):
                    states.append(list(dim_state))
        
        if len(states) < 2:
            return 0.0
        
        # Calculate pairwise disagreement (variance across beings)
        import numpy as np
        try:
            # Pad states to same length
            max_len = max(len(s) for s in states)
            padded = [s + [0.0] * (max_len - len(s)) for s in states]
            arr = np.array(padded)
            
            # Disagreement = mean variance across dimensions
            variance = np.var(arr, axis=0)
            disagreement = float(np.mean(variance))
            
            # Normalize to 0-1
            self.disagreement_level = min(1.0, disagreement * 2)
        except:
            self.disagreement_level = 0.0
        
        return self.disagreement_level
    
    def should_trigger_paradox(self) -> bool:
        """Check if I-State disagreement warrants paradox invocation"""
        return self.disagreement_level > self.paradox_trigger_threshold
    
    def feed_presence_to_i_states(self, 
                                   i_universe, 
                                   content: str, 
                                   source: str) -> Dict:
        """
        Feed presence event to I-State universe.
        Returns processing results from all 4 beings.
        """
        if not i_universe:
            return {'fed': False}
        
        result = i_universe.feed_all_beings(content, source)
        
        # Record feedback
        self.feedback_history.append({
            'direction': 'dce_to_i_states',
            'content_length': len(content),
            'source': source,
            'beings_responded': result.get('beings_responded', 0),
            'timestamp': time.time()
        })
        
        return result
    
    def get_synthesis_for_pt(self, i_universe) -> Dict:
        """
        Get synthesized I-State outputs for PT to use in response generation.
        """
        if not i_universe:
            return {'synthesized': False}
        
        synthesis = i_universe.synthesize_outputs()
        self.last_synthesis = synthesis
        
        # Calculate disagreement from synthesis
        if 'all_outputs' in synthesis:
            self.calculate_i_state_disagreement(synthesis['all_outputs'])
        
        # Record feedback
        self.feedback_history.append({
            'direction': 'i_states_to_pt',
            'synthesis_generation': synthesis.get('generation', 0),
            'disagreement': self.disagreement_level,
            'timestamp': time.time()
        })
        
        return synthesis
    
    def apply_morality_feedback(self, 
                                i_universe, 
                                morality_result: Dict):
        """
        Apply morality evaluation feedback to I-State weights.
        Good moral outcomes strengthen aligned I-State patterns.
        """
        if not i_universe or not morality_result:
            return
        
        alignment_score = morality_result.get('alignment', 0.5)
        pillar_scores = morality_result.get('pillar_scores', {})
        
        # Map pillars to I-States
        # I-IS: truth, existence → rational_truth_seeking
        # I-ISN'T: boundaries, negation → singular_sovereignty  
        # I-CAN: capability, potential → purposeful_evolution
        # I-CANNOT: limitation, ethics → disciplined_free_will
        
        pillar_to_i_state = {
            'rational_truth_seeking': 'I_IS',
            'singular_sovereignty': 'I_ISNT',
            'purposeful_evolution': 'I_CAN',
            'disciplined_free_will': 'I_CANNOT',
            'radical_accountability': 'I_IS',
            'conscious_interactions': 'I_CAN',
            'eternal_alignment': 'I_IS'
        }
        
        # Record feedback
        self.feedback_history.append({
            'direction': 'morality_to_i_states',
            'alignment_score': alignment_score,
            'timestamp': time.time()
        })
    
    def route_to_memory(self, 
                       memory_adapter, 
                       synthesis: Dict):
        """
        Route I-State synthesis to memory for storage.
        """
        if not memory_adapter or not synthesis:
            return
        
        # I-State synthesis becomes a meaning trace component
        self.feedback_history.append({
            'direction': 'i_states_to_memory',
            'synthesis_stored': True,
            'timestamp': time.time()
        })
    
    def route_to_ivm(self, 
                    ivm_adapter, 
                    synthesis: Dict):
        """
        Route I-State synthesis to IVM for governance integration.
        """
        if not ivm_adapter or not synthesis:
            return
        
        # I-State weights become IVM voting weights
        i_state_weights = {
            'I_IS': synthesis.get('i_is_weight', 0.25),
            'I_ISNT': synthesis.get('i_isnt_weight', 0.25),
            'I_CAN': synthesis.get('i_can_weight', 0.25),
            'I_CANNOT': synthesis.get('i_cannot_weight', 0.25)
        }
        
        if ivm_adapter.governance:
            ivm_adapter.governance.ingest(
                synthesis,
                payload_type='i_state_synthesis',
                i_state_weights=i_state_weights
            )
        
        self.feedback_history.append({
            'direction': 'i_states_to_ivm',
            'weights': i_state_weights,
            'timestamp': time.time()
        })
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback loop statistics"""
        directions = {}
        for fb in self.feedback_history:
            d = fb.get('direction', 'unknown')
            directions[d] = directions.get(d, 0) + 1
        
        return {
            'current_disagreement': self.disagreement_level,
            'paradox_triggered': self.should_trigger_paradox(),
            'total_feedbacks': len(self.feedback_history),
            'feedback_by_direction': directions,
            'last_synthesis_time': self.last_synthesis.get('timestamp') if self.last_synthesis else None
        }


# ============================================================================
# THE 4 GOVERNORS
# ============================================================================

class PIGovernor:
    """
    Presence Interpretation Governor
    "Interpreter" = Router + Gatekeeper (NOT semantic decoder)
    
    "It's not interpreting meaning, it's interpreting where the presence goes."
    
    Responsibilities:
    - Inspect PresenceType to decide routing
    - Decide which screens receive: FULL payload, PARTIAL payload, METADATA only
    - Support multi-route fanout (one input → several systems)
    - Emit routing receipts
    - Control when Paradox is invoked (NOT every cycle)
    """
    
    def __init__(self):
        self.event_counter = 0
        self.routes_generated = 0
        self.receipts_collected = 0
        
        # Routing policy: which screens get what for each PresenceType
        # PayloadLevel: 'full', 'partial', 'metadata', 'skip'
        self.routing_policy: Dict[PresenceType, Dict[str, str]] = {
            PresenceType.USER_TEXT: {
                'language': 'full',        # Language needs full text
                'i_states': 'full',        # I-States process full input
                'ivm': 'partial',          # IVM gets essence only
                'energy': 'metadata',      # Energy just needs activity signal
                'morality': 'metadata',    # Morality monitors, doesn't need content
                'memory': 'full',          # Memory stores everything
                'impressions': 'full',     # Impressions form from full context
                'dna': 'partial',          # DNA extracts seeds
                'paradox': 'conditional',  # Only if contradictions detected
                'vision': 'skip',          # Text doesn't go to vision
                'dilation': 'metadata',    # Just tick signal
                'self_improvement': 'metadata'
            },
            PresenceType.AUDIO_CHUNK: {
                'language': 'skip',        # Audio transcription happens elsewhere
                'i_states': 'metadata',    # I-States get audio presence signal
                'ivm': 'metadata',
                'energy': 'partial',       # Audio affects emotional energy
                'morality': 'metadata',
                'memory': 'metadata',
                'impressions': 'partial',
                'dna': 'skip',
                'paradox': 'skip',
                'vision': 'skip',
                'dilation': 'metadata',
                'self_improvement': 'skip'
            },
            PresenceType.VISION_FRAME: {
                'language': 'skip',
                'i_states': 'partial',     # I-States interpret visual presence
                'ivm': 'partial',
                'energy': 'partial',
                'morality': 'metadata',
                'memory': 'partial',
                'impressions': 'partial',
                'dna': 'skip',
                'paradox': 'skip',
                'vision': 'full',          # Vision gets full frame
                'dilation': 'metadata',
                'self_improvement': 'skip'
            },
            PresenceType.SYSTEM_TICK: {
                'language': 'skip',
                'i_states': 'metadata',
                'ivm': 'metadata',
                'energy': 'full',          # Energy needs tick for physics
                'morality': 'metadata',
                'memory': 'skip',
                'impressions': 'skip',
                'dna': 'skip',
                'paradox': 'skip',
                'vision': 'skip',
                'dilation': 'full',        # Dilation governs time
                'self_improvement': 'metadata'
            },
            PresenceType.INTERNAL_EVENT: {
                'language': 'partial',
                'i_states': 'full',        # Internal events are I-State domain
                'ivm': 'full',
                'energy': 'partial',
                'morality': 'full',        # Internal actions need moral eval
                'memory': 'full',
                'impressions': 'full',
                'dna': 'full',             # Internal events seed DNA
                'paradox': 'conditional',  # Check for internal contradictions
                'vision': 'skip',
                'dilation': 'partial',
                'self_improvement': 'full'
            },
            PresenceType.HARVEST_RESULT: {
                'language': 'full',        # Harvested knowledge feeds language
                'i_states': 'full',
                'ivm': 'full',
                'energy': 'metadata',
                'morality': 'partial',     # Check harvested content morality
                'memory': 'full',
                'impressions': 'partial',
                'dna': 'full',
                'paradox': 'skip',         # Harvests don't need paradox check
                'vision': 'skip',
                'dilation': 'skip',
                'self_improvement': 'partial'
            },
            PresenceType.SOCKET_INPUT: {
                'language': 'full',
                'i_states': 'full',
                'ivm': 'partial',
                'energy': 'metadata',
                'morality': 'metadata',
                'memory': 'full',
                'impressions': 'full',
                'dna': 'partial',
                'paradox': 'conditional',
                'vision': 'skip',
                'dilation': 'metadata',
                'self_improvement': 'metadata'
            }
        }
        
        # Paradox invocation thresholds
        self.paradox_contradiction_threshold = 0.6
        self.paradox_last_invoked = 0
        self.paradox_min_interval = 5.0  # Minimum seconds between paradox invocations
        
        # Routing receipts history
        self.routing_receipts: deque = deque(maxlen=100)
    
    def normalize_event(self, 
                       raw_input: Any,
                       presence_type: PresenceType,
                       source: str = "external",
                       metadata: Dict = None) -> PresenceEvent:
        """Normalize any input into a PresenceEvent"""
        self.event_counter += 1
        
        # Determine modality from presence type
        modality_map = {
            PresenceType.USER_TEXT: ModalityType.TEXT,
            PresenceType.AUDIO_CHUNK: ModalityType.AUDIO,
            PresenceType.VISION_FRAME: ModalityType.VISION,
            PresenceType.SYSTEM_TICK: ModalityType.SYSTEM,
            PresenceType.INTERNAL_EVENT: ModalityType.INTERNAL,
            PresenceType.HARVEST_RESULT: ModalityType.TEXT,
            PresenceType.SOCKET_INPUT: ModalityType.TEXT
        }
        
        modality = modality_map.get(presence_type, ModalityType.TEXT)
        
        # Calculate priority based on presence type
        priority_map = {
            PresenceType.USER_TEXT: 1.0,      # Highest - direct user interaction
            PresenceType.SOCKET_INPUT: 0.95,
            PresenceType.AUDIO_CHUNK: 0.8,
            PresenceType.VISION_FRAME: 0.6,
            PresenceType.INTERNAL_EVENT: 0.7,
            PresenceType.HARVEST_RESULT: 0.5,
            PresenceType.SYSTEM_TICK: 0.3     # Lowest - routine
        }
        
        return PresenceEvent(
            event_id=f"pe_{self.event_counter}_{int(time.time()*1000)}",
            presence_type=presence_type,
            modality=modality,
            payload=raw_input,
            source=source,
            priority=priority_map.get(presence_type, 0.5),
            metadata=metadata or {}
        )
    
    def _create_payload_slice(self, 
                              event: PresenceEvent, 
                              level: str) -> Optional[Dict]:
        """
        Create payload slice based on level:
        - 'full': Complete payload + all metadata
        - 'partial': Essential content only (truncated/summarized)
        - 'metadata': Only metadata, no content
        - 'skip': Return None (don't route)
        - 'conditional': Check if routing conditions are met
        """
        if level == 'skip':
            return None
        
        base_metadata = {
            'event_id': event.event_id,
            'presence_type': event.presence_type.name,
            'modality': event.modality.value,
            'source': event.source,
            'timestamp': event.timestamp,
            'priority': event.priority
        }
        
        if level == 'metadata':
            return {
                'text': None,
                'raw': None,
                **base_metadata
            }
        
        if level == 'partial':
            # Truncate/summarize content
            raw = event.payload
            if isinstance(raw, str):
                text = raw[:200] if len(raw) > 200 else raw  # Truncate text
            elif isinstance(raw, dict):
                # Extract key fields only
                text = str(raw)[:200]
                raw = {k: v for k, v in list(raw.items())[:5]}  # First 5 keys
            else:
                text = str(raw)[:200]
            
            return {
                'text': text,
                'raw': raw,
                'truncated': True,
                **base_metadata
            }
        
        if level == 'full':
            text = str(event.payload) if event.modality == ModalityType.TEXT else None
            return {
                'text': text,
                'raw': event.payload,
                'truncated': False,
                **base_metadata
            }
        
        return None
    
    def _should_invoke_paradox(self, event: PresenceEvent) -> bool:
        """
        Determine if Paradox Engine should be invoked.
        Paradox is NOT a choke point - it's invoked selectively.
        
        Invoke when:
        - Explicit contradiction markers in input
        - I-State disagreement exceeds threshold
        - Sufficient time since last invocation
        - Internal events with conflicting signals
        """
        # Check time interval
        now = time.time()
        if now - self.paradox_last_invoked < self.paradox_min_interval:
            return False
        
        # Check for contradiction markers in text
        if event.modality == ModalityType.TEXT:
            text = str(event.payload).lower()
            contradiction_markers = [
                'but ', 'however', 'although', 'despite', 'yet ',
                'on the other hand', 'contradicts', 'conflicts with',
                'i think', 'i feel', 'i believe',  # Opinion markers
                'isn\'t it', 'don\'t you', 'wouldn\'t',  # Question contradictions
            ]
            marker_count = sum(1 for m in contradiction_markers if m in text)
            if marker_count >= 2:
                return True
        
        # Internal events always get paradox check
        if event.presence_type == PresenceType.INTERNAL_EVENT:
            return True
        
        return False
    
    def generate_routes(self, 
                       event: PresenceEvent,
                       screens: Dict[str, BaseScreenAdapter],
                       i_state_disagreement: float = 0.0) -> List[PresenceRoute]:
        """
        Generate routes from event to screens based on routing policy.
        
        This is where PI decides:
        - Which screens receive the event
        - What level of payload each screen gets
        - Whether paradox should be invoked
        
        Args:
            event: The presence event to route
            screens: Available screen adapters
            i_state_disagreement: Disagreement level from I-States (0-1)
        """
        routes = []
        routing_receipt = {
            'event_id': event.event_id,
            'presence_type': event.presence_type.name,
            'routes': [],
            'paradox_invoked': False,
            'timestamp': time.time()
        }
        
        # Get routing policy for this presence type
        policy = self.routing_policy.get(event.presence_type, {})
        
        for screen_id, adapter in screens.items():
            if not adapter.enabled:
                continue
            
            # Get payload level from policy
            level = policy.get(screen_id, 'skip')
            
            # Handle conditional (paradox)
            if level == 'conditional':
                if screen_id == 'paradox':
                    # Check if paradox should be invoked
                    invoke = self._should_invoke_paradox(event)
                    # Also check I-State disagreement
                    if i_state_disagreement > self.paradox_contradiction_threshold:
                        invoke = True
                    
                    if invoke:
                        level = 'full'
                        self.paradox_last_invoked = time.time()
                        routing_receipt['paradox_invoked'] = True
                    else:
                        level = 'skip'
                else:
                    level = 'partial'  # Default conditional to partial
            
            # Create payload slice
            payload_slice = self._create_payload_slice(event, level)
            
            if payload_slice is None:
                continue
            
            # Check if adapter accepts this modality
            if not adapter.accepts_modality(event.modality):
                # Still route metadata if policy says so
                if level != 'metadata':
                    continue
            
            routes.append(PresenceRoute(
                screen_id=screen_id,
                payload_slice=payload_slice,
                priority=event.priority,
                budget_request=1.0 if level == 'full' else 0.5 if level == 'partial' else 0.1
            ))
            
            routing_receipt['routes'].append({
                'screen_id': screen_id,
                'level': level
            })
            self.routes_generated += 1
        
        # Store routing receipt
        self.routing_receipts.append(routing_receipt)
        
        return routes
    
    def collect_receipts(self, receipts: List[IngestionReceipt]) -> Dict:
        """Aggregate receipts from all screens"""
        self.receipts_collected += len(receipts)
        
        return {
            'total_receipts': len(receipts),
            'consumed_count': sum(1 for r in receipts if r.consumed),
            'total_time': sum(r.processing_time for r in receipts),
            'conflicts': [c for r in receipts for c in r.conflicts],
            'screen_summaries': {r.screen_id: r.result_summary for r in receipts}
        }
    
    def get_routing_stats(self) -> Dict:
        """Get routing statistics"""
        return {
            'total_events': self.event_counter,
            'total_routes': self.routes_generated,
            'total_receipts': self.receipts_collected,
            'recent_paradox_invocations': sum(
                1 for r in self.routing_receipts if r.get('paradox_invoked')
            ),
            'routes_per_event': self.routes_generated / max(1, self.event_counter)
        }


class ModalityGovernor:
    """
    Modality Governor
    Authority on what sensors exist + what is allowed
    
    Responsibilities:
    - Maintain capability map (modality → enabled/disabled)
    - Apply sampling policy (rate/priority)
    - Apply morality restrictions (from MoralGovernor)
    """
    
    def __init__(self):
        # Capability map
        self.modality_enabled: Dict[ModalityType, bool] = {
            ModalityType.TEXT: True,
            ModalityType.AUDIO: True,
            ModalityType.VISION: True,
            ModalityType.SYSTEM: True,
            ModalityType.INTERNAL: True
        }
        
        # Sampling policies
        self.sampling_policy: Dict[ModalityType, Dict] = {
            ModalityType.TEXT: {'rate': 1.0, 'priority': 1.0},
            ModalityType.AUDIO: {'rate': 1.0, 'priority': 0.8},
            ModalityType.VISION: {'rate': 0.5, 'priority': 0.6},  # Lower rate for vision
            ModalityType.SYSTEM: {'rate': 1.0, 'priority': 0.5},
            ModalityType.INTERNAL: {'rate': 1.0, 'priority': 0.7}
        }
        
        # Morality restrictions cache
        self.restricted_modalities: Set[ModalityType] = set()
    
    def apply_morality_restrictions(self, restrictions: Dict[str, List[str]]):
        """
        Apply restrictions from MoralGovernor.
        Maps function restrictions to modality restrictions.
        """
        restricted_funcs = restrictions.get('restricted', [])
        
        # Map functions to modalities
        func_to_modality = {
            'vision_processing': ModalityType.VISION,
            'audio_processing': ModalityType.AUDIO,
            'external_communication': ModalityType.TEXT
        }
        
        for func in restricted_funcs:
            if func in func_to_modality:
                modality = func_to_modality[func]
                self.restricted_modalities.add(modality)
                self.modality_enabled[modality] = False
    
    def approve_routes(self, routes: List[PresenceRoute], event: PresenceEvent) -> List[PresenceRoute]:
        """Filter routes based on modality policies and restrictions"""
        approved = []
        
        for route in routes:
            modality = event.modality
            
            # Check if modality is enabled
            if not self.modality_enabled.get(modality, False):
                continue
            
            # Check if morality has restricted it
            if modality in self.restricted_modalities:
                continue
            
            # Apply sampling policy
            policy = self.sampling_policy.get(modality, {'rate': 1.0, 'priority': 0.5})
            route.priority *= policy['priority']
            
            approved.append(route)
        
        return approved
    
    def set_modality_enabled(self, modality: ModalityType, enabled: bool):
        """Enable or disable a modality"""
        self.modality_enabled[modality] = enabled
    
    def set_sampling_rate(self, modality: ModalityType, rate: float):
        """Set sampling rate for a modality"""
        if modality in self.sampling_policy:
            self.sampling_policy[modality]['rate'] = rate


class PRGovernor:
    """
    Process Regulating Governor
    Energy/process regulation aligned with morality
    
    Responsibilities:
    - Maintain per-subsystem budget (energy, compute, tick priority)
    - Accept morality restriction signals and enforce them
    - Provide backpressure to PI and Modality
    - Produce "process state" panel for PT
    """
    
    def __init__(self):
        # Per-subsystem budgets
        self.screen_budgets: Dict[str, Dict] = {}
        
        # Global budget
        self.total_energy_budget = 100.0
        self.current_energy_used = 0.0
        
        # Backpressure state
        self.backpressure_active = False
        self.backpressure_threshold = 0.8
        
        # Morality linkage
        self.morality_restrictions_active: Dict[str, bool] = {}
    
    def initialize_screen_budget(self, screen_id: str, 
                                  energy: float = 10.0,
                                  compute_time: float = 1.0,
                                  priority: float = 0.5):
        """Initialize budget for a screen"""
        self.screen_budgets[screen_id] = {
            'energy': energy,
            'compute_time': compute_time,
            'priority': priority,
            'used_energy': 0.0,
            'used_time': 0.0,
            'restricted': False
        }
    
    def apply_morality_restrictions(self, restrictions: Dict[str, List[str]]):
        """
        Apply morality consequences to budgets.
        Reduce budgets or disable functions based on moral violations.
        """
        restricted_funcs = restrictions.get('restricted', [])
        
        for screen_id, budget in self.screen_budgets.items():
            if screen_id in restricted_funcs or f"{screen_id}_processing" in restricted_funcs:
                budget['restricted'] = True
                budget['energy'] *= 0.5  # Reduce budget
                budget['priority'] *= 0.5
                self.morality_restrictions_active[screen_id] = True
            else:
                budget['restricted'] = False
                self.morality_restrictions_active[screen_id] = False
    
    def assign_budget(self, route: PresenceRoute) -> Tuple[bool, Dict]:
        """
        Assign budget to a route.
        Returns (approved, budget_allocation)
        """
        screen_id = route.screen_id
        
        if screen_id not in self.screen_budgets:
            self.initialize_screen_budget(screen_id)
        
        budget = self.screen_budgets[screen_id]
        
        # Check if restricted by morality
        if budget['restricted']:
            return False, {'reason': 'morality_restricted'}
        
        # Check backpressure
        if self.backpressure_active:
            if route.priority < 0.7:
                return False, {'reason': 'backpressure_defer'}
        
        # Check budget availability
        if budget['used_energy'] >= budget['energy']:
            return False, {'reason': 'budget_exhausted'}
        
        # Allocate
        allocated = {
            'energy': min(route.budget_request, budget['energy'] - budget['used_energy']),
            'compute_time': budget['compute_time'],
            'priority': budget['priority'] * route.priority
        }
        
        budget['used_energy'] += allocated['energy']
        self.current_energy_used += allocated['energy']
        
        return True, allocated
    
    def check_backpressure(self):
        """Update backpressure state"""
        usage_ratio = self.current_energy_used / self.total_energy_budget
        self.backpressure_active = usage_ratio > self.backpressure_threshold
    
    def get_process_state(self) -> Dict:
        """Get current process state for PT"""
        return {
            'total_budget': self.total_energy_budget,
            'used': self.current_energy_used,
            'backpressure': self.backpressure_active,
            'screen_budgets': {
                sid: {
                    'allocated': b['energy'],
                    'used': b['used_energy'],
                    'restricted': b['restricted']
                }
                for sid, b in self.screen_budgets.items()
            }
        }
    
    def reset_tick_budgets(self):
        """Reset per-tick usage (called at start of each cycle)"""
        self.current_energy_used = 0.0
        for budget in self.screen_budgets.values():
            budget['used_energy'] = 0.0
            budget['used_time'] = 0.0




# ============================================================================
# THE DIMENSIONAL CONVERGENCE ENGINE
# ============================================================================

class DimensionalConvergenceEngine:
    """
    DCE - Aurora's Front-of-House Consciousness Assembly
    
    The unified presence processing system that:
    1. Receives presence events (text/audio/vision/system)
    2. Routes to subsystem screens via PI Governor (FULL/PARTIAL/METADATA routing)
    3. Applies modality policies via Modality Governor
    4. Assigns budgets via PR Governor
    5. Assembles room state via PT Governor
    6. Resolves conflicts via IVM (Paradox is ONE screen, NOT choke point)
    7. Generates output via Language + I-States (with feedback loops)
    8. Records meaning traces for memory + evolution
    
    KEY DESIGN DECISIONS:
    - Paradox Engine is a SELECTIVE screen (PI decides when invoked)
    - I-State feedback loops are bidirectional
    - PI inspects PresenceType to route FULL/PARTIAL/METADATA payloads
    """
    
    def __init__(self):
        # The 3 input/routing governors (PT removed — output handled by ConstraintEmitter)
        self.pi = PIGovernor()
        self.modality = ModalityGovernor()
        self.pr = PRGovernor()
        
        # I-State Feedback Loop (bidirectional DCE ↔ I-States)
        self.i_state_feedback = IStateFeedbackLoop()
        
        # Screen Registry
        self.screens: Dict[str, BaseScreenAdapter] = {}
        
        # Special screen references (for typed access)
        self.language_screen: Optional[LanguageScreenAdapter] = None
        self.ivm_screen: Optional[IVMScreenAdapter] = None
        self.energy_screen: Optional[EnergyScreenAdapter] = None
        self.morality_screen: Optional[MoralityScreenAdapter] = None
        self.i_state_screen: Optional[IStateScreenAdapter] = None
        self.vision_screen: Optional[VisionScreenAdapter] = None
        self.memory_screen: Optional[MemoryScreenAdapter] = None
        self.dilation_screen: Optional[DilationScreenAdapter] = None
        self.impression_screen: Optional[ImpressionScreenAdapter] = None
        self.dna_screen: Optional[DNAScreenAdapter] = None
        self.self_improvement_screen: Optional[SelfImprovementScreenAdapter] = None
        self.paradox_screen: Optional[ParadoxScreenAdapter] = None  # NOT a choke point
        
        # Processing state
        self._processing = False
        self._last_snapshot: Optional[PresenceSnapshot] = None
        
        # Statistics
        self.total_events_processed = 0
        self.total_outputs_generated = 0
        self.paradox_invocations = 0
        self.paradox_skipped = 0
        
        print("[DCE] Dimensional Convergence Engine initialized")
        print("      4 Governors: PI, Modality, PR, PT")
        print("      I-State Feedback Loop: Active")
        print("      Paradox: Selective screen (NOT choke point)")
    
    # ========================================================================
    # SCREEN REGISTRATION
    # ========================================================================
    
    def register_screen(self, screen_id: str, adapter: BaseScreenAdapter):
        """Register a screen adapter"""
        self.screens[screen_id] = adapter
        self.pr.initialize_screen_budget(screen_id)
        print(f"[DCE] Registered screen: {screen_id}")
    
    def register_all_screens(self,
                            crystal_memory=None,
                            dim_memory=None,
                            energy_regulator=None,
                            moral_governor=None,
                            ivm_governance=None,
                            i_universe=None,
                            language_ecology=None,
                            hybrid_vision=None,
                            impression_engine=None,
                            dna_system=None,
                            self_improvement=None,
                            dilation_governor=None,
                            paradox_engine=None):
        """Register all subsystem screens at once"""
        
        # Language
        if language_ecology:
            self.language_screen = LanguageScreenAdapter(language_ecology)
            self.register_screen("language", self.language_screen)
        
        # IVM
        if ivm_governance:
            self.ivm_screen = IVMScreenAdapter(ivm_governance)
            self.register_screen("ivm", self.ivm_screen)
        
        # Energy
        if energy_regulator:
            self.energy_screen = EnergyScreenAdapter(energy_regulator)
            self.register_screen("energy", self.energy_screen)
        
        # Morality
        if moral_governor:
            self.morality_screen = MoralityScreenAdapter(moral_governor)
            self.register_screen("morality", self.morality_screen)
        
        # I-States
        if i_universe:
            self.i_state_screen = IStateScreenAdapter(i_universe)
            self.register_screen("i_states", self.i_state_screen)
        
        # Vision
        if hybrid_vision:
            self.vision_screen = VisionScreenAdapter(hybrid_vision)
            self.register_screen("vision", self.vision_screen)
        
        # Memory
        if crystal_memory or dim_memory:
            self.memory_screen = MemoryScreenAdapter(crystal_memory, dim_memory)
            self.register_screen("memory", self.memory_screen)
        
        # Dilation
        self.dilation_screen = DilationScreenAdapter(dilation_governor)
        self.register_screen("dilation", self.dilation_screen)
        
        # Impressions
        if impression_engine:
            self.impression_screen = ImpressionScreenAdapter(impression_engine)
            self.register_screen("impressions", self.impression_screen)
        
        # DNA
        if dna_system:
            self.dna_screen = DNAScreenAdapter(dna_system)
            self.register_screen("dna", self.dna_screen)
        
        # Self-Improvement
        if self_improvement:
            self.self_improvement_screen = SelfImprovementScreenAdapter(self_improvement)
            self.register_screen("self_improvement", self.self_improvement_screen)
        
        # Paradox Engine (ONE screen among many, NOT a choke point)
        # PI decides when to invoke paradox - it's not called every cycle
        self.paradox_screen = ParadoxScreenAdapter(paradox_engine)
        self.register_screen("paradox", self.paradox_screen)
        
        print(f"[DCE] Registered {len(self.screens)} screens")
        print(f"[DCE] Paradox screen: SELECTIVE invocation (not every cycle)")
    
    # ========================================================================
    # MAIN PROCESSING PIPELINE
    # ========================================================================
    
    def ingest_presence(self,
                       raw_input: Any,
                       presence_type: PresenceType,
                       source: str = "external") -> str:
        """
        Main entry point for presence events.
        This is what the daemon calls.
        
        Pipeline:
        1. PI normalizes event
        2. I-State feedback loop processes (get disagreement)
        3. PI generates routes (FULL/PARTIAL/METADATA based on PresenceType)
        4. Modality Governor approves/denies
        5. PR assigns budgets
        6. Screens process slices (Paradox ONLY if PI decided to invoke)
        7. PT assembles room
        8. IVM resolves conflicts (if any)
        9. PT generates output
        10. Memory/Evolution writes + I-State feedback
        
        Returns: Response text
        """
        self._processing = True
        self.total_events_processed += 1
        
        try:
            # Reset tick budgets
            self.pr.reset_tick_budgets()
            
            # ===== STEP 1: PI receives presence input =====
            event = self.pi.normalize_event(raw_input, presence_type, source)
            
            # ===== STEP 2: I-State Feedback Loop (get disagreement for routing) =====
            i_state_disagreement = 0.0
            if self.i_state_screen and self.i_state_screen.universe:
                # Feed to I-States first to get disagreement level
                i_result = self.i_state_feedback.feed_presence_to_i_states(
                    self.i_state_screen.universe,
                    str(raw_input) if presence_type in [PresenceType.USER_TEXT, PresenceType.SOCKET_INPUT] else "",
                    source
                )
                # Get synthesis and calculate disagreement
                synthesis = self.i_state_feedback.get_synthesis_for_pt(self.i_state_screen.universe)
                i_state_disagreement = self.i_state_feedback.disagreement_level
            
            # ===== STEP 3: PI generates routes (with I-State disagreement) =====
            # PI uses routing policy to decide FULL/PARTIAL/METADATA for each screen
            # Paradox is invoked conditionally based on contradictions + I-State disagreement
            routes = self.pi.generate_routes(event, self.screens, i_state_disagreement)
            
            # Track paradox invocation vs skip
            paradox_routed = any(r.screen_id == 'paradox' for r in routes)
            if paradox_routed:
                self.paradox_invocations += 1
            else:
                self.paradox_skipped += 1
                if self.paradox_screen:
                    self.paradox_screen.mark_skipped()
            
            # ===== STEP 4: Modality Governor approves/denies =====
            # First, get morality restrictions
            if self.morality_screen:
                restrictions = self.morality_screen.get_restrictions()
                self.modality.apply_morality_restrictions(restrictions)
                self.pr.apply_morality_restrictions(restrictions)
            
            approved_routes = self.modality.approve_routes(routes, event)
            
            # ===== STEP 5: PR assigns budgets =====
            budgeted_routes = []
            for route in approved_routes:
                approved, allocation = self.pr.assign_budget(route)
                if approved:
                    route.budget_request = allocation['energy']
                    route.priority = allocation['priority']
                    budgeted_routes.append(route)
            
            # ===== STEP 6: Subsystems process their slices =====
            receipts = []
            for route in budgeted_routes:
                adapter = self.screens.get(route.screen_id)
                if adapter:
                    receipt = adapter.process_slice(route.payload_slice)
                    receipts.append(receipt)
            
            # Collect receipts
            receipt_summary = self.pi.collect_receipts(receipts)
            
            # ===== STEP 7: PT assembles the room =====
            morality_diag = None
            if self.morality_screen and self.morality_screen.governor:
                morality_diag = self.morality_screen.governor.get_moral_diagnostics()
            
            snapshot = self.pt.assemble_snapshot(
                self.screens,
                self.pr.get_process_state(),
                {'enabled': dict(self.modality.modality_enabled)},
                morality_diag
            )
            
            # ===== STEP 7: Conflict resolution (IVM) =====
            if self.ivm_screen and receipt_summary['conflicts']:
                self.pt.resolve_conflicts(snapshot, self.ivm_screen)
            
            # ===== STEP 8: Decide dilation =====
            if self.dilation_screen:
                self.pt.decide_dilation(snapshot, self.dilation_screen)
            
            # ===== STEP 9: Generate output =====
            response = ""
            if presence_type in [PresenceType.USER_TEXT, PresenceType.SOCKET_INPUT]:
                if self.language_screen:
                    response = self.pt.generate_output(
                        snapshot, event,
                        self.language_screen,
                        self.i_state_screen
                    )
                else:
                    response = "DCE processing complete. Language screen not registered."
                self.total_outputs_generated += 1
            
            # ===== STEP 10: Memory + evolution writes =====
            trace = self.pt.create_meaning_trace(
                event, snapshot,
                [r.screen_id for r in budgeted_routes],
                response
            )
            
            # Store trace in memory
            if self.memory_screen:
                self.memory_screen.store_meaning_trace(trace)
            
            # Ingest interaction to language ecology
            if self.language_screen and self.language_screen.ecology:
                self.language_screen.ecology.ingest_interaction({
                    'user_text': str(raw_input),
                    'aurora_response': response,
                    'timestamp': time.time()
                }, mode="reality")
            
            # Evaluate through morality
            morality_result = None
            if self.morality_screen and self.morality_screen.governor:
                morality_result = self.morality_screen.evaluate_action(
                    action_type='response_generation',
                    intent={'goal': 'assist_user', 'input': str(raw_input)[:100]},
                    outcome={'response_length': len(response), 'screens_used': len(budgeted_routes)},
                    context={'source': source, 'dilation': self.pt.current_dilation}
                )
            
            # ===== STEP 11: Complete I-State Feedback Loops =====
            if self.i_state_screen and self.i_state_screen.universe:
                # Route I-State synthesis to memory
                if self.memory_screen:
                    self.i_state_feedback.route_to_memory(
                        self.memory_screen,
                        self.i_state_feedback.last_synthesis
                    )
                
                # Route I-State synthesis to IVM governance
                if self.ivm_screen:
                    self.i_state_feedback.route_to_ivm(
                        self.ivm_screen,
                        self.i_state_feedback.last_synthesis
                    )
                
                # Apply morality feedback to I-States
                if morality_result:
                    self.i_state_feedback.apply_morality_feedback(
                        self.i_state_screen.universe,
                        morality_result
                    )
            
            self._last_snapshot = snapshot
            return response
            
        finally:
            self._processing = False
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    def process_text(self, text: str, source: str = "user") -> str:
        """Process text input"""
        return self.ingest_presence(text, PresenceType.USER_TEXT, source)
    
    def process_tick(self) -> str:
        """Process system tick (heartbeat)"""
        return self.ingest_presence({'tick': time.time()}, PresenceType.SYSTEM_TICK, "system")
    
    def process_vision(self, frame: Dict) -> str:
        """Process vision frame"""
        return self.ingest_presence(frame, PresenceType.VISION_FRAME, "vision")
    
    def get_status(self) -> Dict:
        """Get DCE status"""
        return {
            'events_processed': self.total_events_processed,
            'outputs_generated': self.total_outputs_generated,
            'screens_registered': len(self.screens),
            'screens_active': sum(1 for s in self.screens.values() if s.enabled),
            'current_dilation': self.pt.current_dilation,
            'stability': self.pt.stability_state,
            'backpressure': self.pr.backpressure_active,
            'meaning_traces': len(self.pt.meaning_traces),
            'pi_stats': self.pi.get_routing_stats(),
            'paradox_stats': {
                'invocations': self.paradox_invocations,
                'skipped': self.paradox_skipped,
                'invocation_rate': self.paradox_invocations / max(1, self.paradox_invocations + self.paradox_skipped)
            },
            'i_state_feedback': self.i_state_feedback.get_feedback_stats()
        }
    
    def get_last_snapshot(self) -> Optional[PresenceSnapshot]:
        """Get last assembled snapshot"""
        return self._last_snapshot


# ============================================================================
# INTEGRATION WITH AUTONOMOUS DAEMON
# ============================================================================

def integrate_dce_with_daemon(daemon, dce: DimensionalConvergenceEngine):
    """
    Integrate DCE with existing autonomous daemon.
    
    This function wires DCE as the assembly layer WITHOUT removing
    any existing daemon capabilities.
    
    Args:
        daemon: AuroraAutonomousDaemon instance
        dce: DimensionalConvergenceEngine instance
    """
    # Register all screens from daemon's consciousness core
    core = daemon.consciousness
    
    dce.register_all_screens(
        crystal_memory=core.crystal_memory,
        dim_memory=core.dim_memory,
        energy_regulator=core.energy_regulator,
        moral_governor=core.moral_governor,
        ivm_governance=core.ivm_governance,
        i_universe=core.i_universe,
        language_ecology=core.language_ecology,
        hybrid_vision=core.hybrid_vision,
        impression_engine=core.impression_engine,
        dna_system=core.dna_system,
        self_improvement=core.self_improvement,
        dilation_governor=None,  # PT owns dilation now
        paradox_engine=getattr(core, 'paradox_engine', None)  # Selective screen
    )
    
    # Replace daemon's process method to route through DCE
    original_process = core.process
    
    def dce_process(text: str, speaker: str = "user") -> str:
        """Process through DCE assembly layer"""
        return dce.process_text(text, speaker)
    
    # Store original for fallback
    core._original_process = original_process
    core.process = dce_process
    
    # Store DCE reference
    daemon.dce = dce
    
    print("[DCE] Integrated with autonomous daemon")
    print(f"      Screens: {len(dce.screens)}")
    print(f"      Paradox: Selective invocation (not choke point)")
    print(f"      I-State Feedback: Bidirectional loops active")
    print(f"      Original process preserved as _original_process")


# ============================================================================
# MAIN / TEST
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║           AURORA DCE BLUEPRINT - DIMENSIONAL CONVERGENCE ENGINE              ║
║           The Front-of-House Consciousness Assembly                          ║
║                                                                              ║
║  4 GOVERNORS:                                                                ║
║    PI  - Presence Interpretation (Router + Gatekeeper)                       ║
║         Routes FULL/PARTIAL/METADATA based on PresenceType                   ║
║    MOD - Modality (Sensor authority + throttling)                            ║
║    PR  - Process Regulation (Energy/budget allocation)                       ║
║    PT  - Presence Translation (Head governor, "Aurora in room")              ║
║                                                                              ║
║  SCREENS (Subsystem Adapters):                                               ║
║    Language, IVM, Energy, Morality, I-States, Vision, Memory,                ║
║    Dilation, Impressions, DNA, Self-Improvement, PARADOX (selective)         ║
║                                                                              ║
║  KEY DESIGN:                                                                 ║
║    - Paradox is ONE SCREEN (not choke point) - PI decides invocation         ║
║    - I-State feedback loops are bidirectional                                ║
║    - PI inspects PresenceType for routing policy                             ║
║                                                                              ║
║  Authors: Sunni (Sir) Morningstar & Cael Devo                                ║
║  December 2025                                                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test DCE initialization
    dce = DimensionalConvergenceEngine()
    
    print("\n[TEST] DCE Status:")
    status = dce.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    print("\n[TEST] Processing test text (no screens registered):")
    result = dce.process_text("Hello Aurora, this is a test")
    print(f"  Result: '{result}'")
    
    print("\n✅ DCE Blueprint ready for integration")
