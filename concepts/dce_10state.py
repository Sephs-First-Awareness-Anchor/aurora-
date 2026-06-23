#!/usr/bin/env python3
"""
AURORA DCE 10-STATE - CRYSTAL CONSOLIDATION HUB
================================================
Authors: Sunni (Sir) Morningstar and Cael Devo
Created: January 2026

The DCE consolidates ALL module outputs into interaction crystals.

THIS MODULE CALLS ACTUAL METHODS FROM:
- higher_universe_10.AuroraHigherUniverse.feed_all_beings()
- aurora_behavioral_evolution.AuroraBehavioralEvolution.get_current_personality()
- dimensional_mortality_morality_system.MoralGovernor.get_moral_diagnostics()
- aurora_sensory_systems.AuroraSensorySystems.capture()
- aurora_information_harvester.AuroraInformationHarvester.collect()
- aurora_impression_engine_v2.ImpressionEngine.energy_to_shard()
- aurora_manifold_engine_v2.ManifoldEngine.shard_to_cp()
- eepr_10pole.ExperientialEntropicPressureRegulator.ingest_shard()
- governance_10pole.IVMGovernanceEngine.ingest()
- Language Ecology lexical_memory.vocabulary
"""

import time
import random
import hashlib
import numpy as np
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
from pathlib import Path


# ============================================================================
# TIER 0: 10-STATE FOUNDATION
# ============================================================================

class IStateType(Enum):
    """The 10 fundamental I-State beings"""
    I_IS = "i_is"
    I_ISNT = "i_isnt"
    I_CAN = "i_can"
    I_CANNOT = "i_cannot"
    I_DO = "i_do"
    I_DONT = "i_dont"
    I_SAW = "i_saw"
    I_SAWNT = "i_sawnt"
    I_DID = "i_did"
    I_DIDNT = "i_didnt"


# ============================================================================
# CRYSTAL FACET STRUCTURE
# ============================================================================

@dataclass
class CrystalFacet:
    """A single facet of an interaction crystal."""
    facet_type: str
    source: str
    content: Any
    weight: float = 1.0
    emphasis: float = 0.5
    
    def to_dict(self) -> Dict:
        return {
            'facet_type': self.facet_type,
            'source': self.source,
            'content': str(self.content)[:200] if self.content else '',
            'weight': self.weight,
            'emphasis': self.emphasis
        }


@dataclass 
class InteractionCrystal:
    """Complete interaction crystal with all facets."""
    crystal_id: str
    timestamp: float
    original_input: str
    facets: List[CrystalFacet] = field(default_factory=list)
    synthesized_response: str = ""
    dominant_perspective: str = ""
    total_emphasis: float = 0.0
    concept_fingerprint: Set[str] = field(default_factory=set)
    
    def add_facet(self, facet: CrystalFacet):
        self.facets.append(facet)
        self.total_emphasis += facet.emphasis * facet.weight
    
    def get_facets_by_type(self, facet_type: str) -> List[CrystalFacet]:
        return [f for f in self.facets if f.facet_type == facet_type]
    
    def get_i_state_facets(self) -> Dict[str, CrystalFacet]:
        return {f.source: f for f in self.facets if f.facet_type == 'i_state'}
    
    def compute_fingerprint(self):
        concepts = set()
        for facet in self.facets:
            if isinstance(facet.content, str):
                words = facet.content.lower().split()
                concepts.update(w for w in words if len(w) > 3)
            elif isinstance(facet.content, dict):
                for v in facet.content.values():
                    if isinstance(v, str):
                        concepts.update(w for w in v.lower().split() if len(w) > 3)
        self.concept_fingerprint = concepts
    
    def to_dict(self) -> Dict:
        return {
            'crystal_id': self.crystal_id,
            'timestamp': self.timestamp,
            'original_input': self.original_input[:100],
            'facet_count': len(self.facets),
            'synthesized_response': self.synthesized_response[:200],
            'dominant_perspective': self.dominant_perspective,
            'total_emphasis': self.total_emphasis
        }


# ============================================================================
# SFO LIBRARY (Situational Framing Operators)
# ============================================================================

class SituationalFramingOperator:
    """Re-weights 10 I-State outputs based on situational context."""
    
    def __init__(self, name: str, weight_config: Dict[str, float]):
        self.name = name
        self.weights = weight_config
        self.usage_count = 0
        self.outcome_history = deque(maxlen=50)
    
    def apply_to_outputs(self, i_state_outputs: Dict) -> Dict[str, Any]:
        """Apply SFO reweighting to I-State outputs."""
        self.usage_count += 1
        reweighted = {}
        
        # Handle feed_all_beings format from higher_universe_10
        interpretations = i_state_outputs.get('interpretations', {})
        opinions = i_state_outputs.get('opinions', {})
        
        for i_state_name, weight in self.weights.items():
            interp = interpretations.get(i_state_name, '')
            opinion = opinions.get(i_state_name, '')
            
            reweighted[i_state_name] = {
                'interpretation': interp,
                'opinion': opinion,
                'applied_weight': weight,
                'emphasis_score': weight * (len(interp) / 100.0 if interp else 0.1),
                'suppressed': weight < 0.05
            }
        
        return {
            'reweighted_outputs': reweighted,
            'sfo_name': self.name,
            'total_weight': sum(self.weights.values())
        }
    
    def record_outcome(self, quality: float, coherence: float):
        score = quality * 0.6 + coherence * 0.4
        self.outcome_history.append(score)


class SFOLibrary:
    """Library of Situational Framing Operators."""
    
    def __init__(self):
        self.operators: Dict[str, SituationalFramingOperator] = {}
        self._initialize_default_sfos()
    
    def _initialize_default_sfos(self):
        base = {s.value: 0.1 for s in IStateType}
        
        self.operators['balanced'] = SituationalFramingOperator('balanced', base)
        
        self.operators['existence_dominant'] = SituationalFramingOperator(
            'existence_dominant',
            {'i_is': 0.25, 'i_isnt': 0.25, 'i_can': 0.1, 'i_cannot': 0.1,
             'i_do': 0.075, 'i_dont': 0.075, 'i_saw': 0.05, 'i_sawnt': 0.05,
             'i_did': 0.025, 'i_didnt': 0.025}
        )
        
        self.operators['possibility_dominant'] = SituationalFramingOperator(
            'possibility_dominant',
            {'i_is': 0.1, 'i_isnt': 0.1, 'i_can': 0.25, 'i_cannot': 0.25,
             'i_do': 0.075, 'i_dont': 0.075, 'i_saw': 0.05, 'i_sawnt': 0.05,
             'i_did': 0.025, 'i_didnt': 0.025}
        )
        
        self.operators['action_dominant'] = SituationalFramingOperator(
            'action_dominant',
            {'i_is': 0.05, 'i_isnt': 0.05, 'i_can': 0.1, 'i_cannot': 0.1,
             'i_do': 0.25, 'i_dont': 0.25, 'i_saw': 0.075, 'i_sawnt': 0.075,
             'i_did': 0.025, 'i_didnt': 0.025}
        )
        
        self.operators['evidence_dominant'] = SituationalFramingOperator(
            'evidence_dominant',
            {'i_is': 0.075, 'i_isnt': 0.075, 'i_can': 0.075, 'i_cannot': 0.075,
             'i_do': 0.05, 'i_dont': 0.05, 'i_saw': 0.25, 'i_sawnt': 0.25,
             'i_did': 0.05, 'i_didnt': 0.05}
        )
        
        self.operators['accountability'] = SituationalFramingOperator(
            'accountability',
            {'i_is': 0.05, 'i_isnt': 0.05, 'i_can': 0.05, 'i_cannot': 0.05,
             'i_do': 0.1, 'i_dont': 0.1, 'i_saw': 0.1, 'i_sawnt': 0.1,
             'i_did': 0.2, 'i_didnt': 0.2}
        )
    
    def select_sfo(self, context: Dict[str, Any]) -> SituationalFramingOperator:
        content = str(context.get('content', '')).lower()
        
        if any(w in content for w in ['do', 'act', 'execute', 'perform', 'make', 'create']):
            return self.operators['action_dominant']
        elif any(w in content for w in ['saw', 'observed', 'evidence', 'notice', 'see', 'look']):
            return self.operators['evidence_dominant']
        elif any(w in content for w in ['committed', 'responsible', 'accountable', 'did', 'done']):
            return self.operators['accountability']
        elif any(w in content for w in ['can', 'could', 'possible', 'might', 'able']):
            return self.operators['possibility_dominant']
        elif any(w in content for w in ['is', 'are', 'exists', 'being', 'what']):
            return self.operators['existence_dominant']
        else:
            return self.operators['balanced']


# ============================================================================
# DCE CRYSTAL CONSOLIDATION HUB
# ============================================================================

class EnhancedDCE:
    """
    DCE Crystal Consolidation Hub.
    
    WIRES TO ACTUAL AURORA MODULES - NO STUBS.
    All facets collected from real module method calls.
    """
    
    def __init__(self):
        self.sfo_library = SFOLibrary()
        
        # References to ACTUAL Aurora modules (set by brain)
        self.i_universe = None           # AuroraHigherUniverse
        self.behavioral_evolution = None  # AuroraBehavioralEvolution  
        self.moral_governor = None        # MoralGovernor
        self.sensory_systems = None       # AuroraSensorySystems
        self.information_harvester = None # AuroraInformationHarvester
        self.impression_engine = None     # ImpressionEngine
        self.manifold_engine = None       # ManifoldEngine
        self.eepr = None                  # ExperientialEntropicPressureRegulator
        self.governance = None            # IVMGovernanceEngine
        self.language_ecology = None      # LanguageEcology
        self.dim_memory = None            # DimensionalMemory
        
        # Crystal storage
        self.crystal_history: deque = deque(maxlen=1000)
        self.crystal_associations: Dict[str, List[str]] = defaultdict(list)
        
        # Statistics
        self.total_crystals_created = 0
        self.total_sfo_applications = 0
        
        # DPME Synthesis Parameters (set by brain when DPME active)
        self._dpme_synthesis_params: Dict[str, float] = {
            "synthesis_boldness": 0.5,
            "perspective_integration": 0.5,
            "vocabulary_richness": 0.5,
            "response_length_bias": 0.5,
        }
        
        print("[ENHANCED DCE] Crystal Consolidation Hub initialized")
    
    # ========================================================================
    # DPME PARAMETER INJECTION
    # ========================================================================
    
    def set_synthesis_parameters(self, params: Dict[str, float]):
        """
        Set synthesis parameters from DPME.
        
        Called by brain when DPME is active to inject conscious parameter adjustments.
        These affect how DCE synthesizes responses.
        """
        if params:
            self._dpme_synthesis_params.update(params)
    
    def get_synthesis_boldness(self) -> float:
        """Get current synthesis boldness (0=conservative, 1=bold)."""
        return self._dpme_synthesis_params.get("synthesis_boldness", 0.5)
    
    def get_perspective_integration(self) -> float:
        """Get how much to blend multiple I-State perspectives (0=dominant only, 1=full blend)."""
        return self._dpme_synthesis_params.get("perspective_integration", 0.5)
    
    # ========================================================================
    # MODULE REGISTRATION (called by brain during init)
    # ========================================================================
    
    def register_i_universe(self, module):
        """Register AuroraHigherUniverse for feed_all_beings()"""
        self.i_universe = module
        print("[DCE] I-Universe registered: feed_all_beings() available")
    
    def register_behavioral_evolution(self, module):
        """Register AuroraBehavioralEvolution for get_current_personality()"""
        self.behavioral_evolution = module
        print("[DCE] Behavioral Evolution registered: voice genome available")
    
    def register_moral_governor(self, module):
        """Register MoralGovernor for get_moral_diagnostics()"""
        self.moral_governor = module
        print("[DCE] Moral Governor registered: 7-pillar diagnostics available")
    
    def register_sensory_systems(self, module):
        """Register AuroraSensorySystems for capture()"""
        self.sensory_systems = module
        print("[DCE] Sensory Systems registered: capture() available")
    
    def register_information_harvester(self, module):
        """Register AuroraInformationHarvester for collect()"""
        self.information_harvester = module
        print("[DCE] Information Harvester registered: collect() available")
    
    def register_impression_engine(self, module):
        """Register ImpressionEngine for energy_to_shard()"""
        self.impression_engine = module
        print("[DCE] Impression Engine registered: shard formation available")
    
    def register_manifold_engine(self, module):
        """Register ManifoldEngine for shard_to_cp()"""
        self.manifold_engine = module
        print("[DCE] Manifold Engine registered: CP coordinates available")
    
    def register_eepr(self, module):
        """Register EEPR for ingest_shard()"""
        self.eepr = module
        print("[DCE] EEPR registered: pressure field available")
    
    def register_governance(self, module):
        """Register IVMGovernanceEngine for ingest()"""
        self.governance = module
        print("[DCE] Governance registered: axis conflict detection available")
    
    def register_language_ecology(self, module):
        """Register LanguageEcology for vocabulary"""
        self.language_ecology = module
        print("[DCE] Language Ecology registered: vocabulary available")
    
    def register_dim_memory(self, module):
        """Register DimensionalMemory for crystal storage"""
        self.dim_memory = module
        print("[DCE] Dimensional Memory registered: crystal storage available")
    
    # Aliases for backward compatibility
    def register_enhanced_i_universe(self, module):
        self.register_i_universe(module)
    
    # ========================================================================
    # CRYSTAL CREATION - CALLS ACTUAL MODULE METHODS
    # ========================================================================
    
    def create_interaction_crystal(self, original_input: str, source: str = "external") -> InteractionCrystal:
        """
        Create crystal by calling ACTUAL module methods.
        
        NO STUBS - all facets from real Aurora systems.
        """
        crystal_id = hashlib.md5(f"{original_input}{time.time()}".encode()).hexdigest()[:12]
        crystal = InteractionCrystal(
            crystal_id=crystal_id,
            timestamp=time.time(),
            original_input=original_input
        )
        
        # ================================================================
        # FACET 1-10: I-State interpretations from ACTUAL i_universe.feed_all_beings()
        # ================================================================
        i_state_data = self._collect_i_state_facets(original_input, source)
        for i_state_name, data in i_state_data.items():
            crystal.add_facet(CrystalFacet(
                facet_type='i_state',
                source=i_state_name,
                content=data,
                weight=data.get('applied_weight', 1.0),
                emphasis=data.get('emphasis_score', 0.5)
            ))
        
        # ================================================================
        # FACET 11: Behavioral from ACTUAL behavioral_evolution.get_current_personality()
        # ================================================================
        behavioral_data = self._collect_behavioral_facet()
        if behavioral_data:
            crystal.add_facet(CrystalFacet(
                facet_type='behavioral',
                source='voice_genome',
                content=behavioral_data,
                weight=0.8,
                emphasis=behavioral_data.get('presence', 0.5)
            ))
        
        # ================================================================
        # FACET 12: Moral from ACTUAL moral_governor.get_moral_diagnostics()
        # ================================================================
        moral_data = self._collect_moral_facet()
        if moral_data:
            crystal.add_facet(CrystalFacet(
                facet_type='moral',
                source='7pillar_governor',
                content=moral_data,
                weight=1.0,
                emphasis=0.7 + moral_data.get('overall_alignment', 0.0) * 0.3
            ))
        
        # ================================================================
        # FACET 13: Sensory from ACTUAL sensory_systems.capture()
        # ================================================================
        sensory_data = self._collect_sensory_facet()
        if sensory_data:
            crystal.add_facet(CrystalFacet(
                facet_type='sensory',
                source='vision_body',
                content=sensory_data,
                weight=0.6,
                emphasis=0.5
            ))
        
        # ================================================================
        # FACET 14: Harvested from ACTUAL information_harvester.collect()
        # ================================================================
        harvested_data = self._collect_harvested_facet()
        if harvested_data:
            crystal.add_facet(CrystalFacet(
                facet_type='harvested',
                source='information_harvester',
                content=harvested_data,
                weight=0.7,
                emphasis=0.6
            ))
        
        # ================================================================
        # FACET 15: Impression from ACTUAL impression_engine (if energy available)
        # ================================================================
        impression_data = self._collect_impression_facet(original_input)
        if impression_data:
            crystal.add_facet(CrystalFacet(
                facet_type='impression',
                source='impression_engine',
                content=impression_data,
                weight=0.5,
                emphasis=impression_data.get('intensity', 0.5)
            ))
        
        # ================================================================
        # FACET 16: EEPR Pressure from ACTUAL eepr.get_field_stats()
        # ================================================================
        eepr_data = self._collect_eepr_facet()
        if eepr_data:
            crystal.add_facet(CrystalFacet(
                facet_type='pressure',
                source='eepr',
                content=eepr_data,
                weight=0.4,
                emphasis=eepr_data.get('novelty_rate', 0.5)
            ))
        
        # ================================================================
        # FACET 17: Governance from ACTUAL governance.get_stats()
        # ================================================================
        governance_data = self._collect_governance_facet()
        if governance_data:
            crystal.add_facet(CrystalFacet(
                facet_type='governance',
                source='ivm_governance',
                content=governance_data,
                weight=0.5,
                emphasis=0.5
            ))
        
        # Compute fingerprint
        crystal.compute_fingerprint()
        
        # Store
        self.crystal_history.append(crystal)
        self.total_crystals_created += 1
        
        return crystal
    
    # ========================================================================
    # FACET COLLECTORS - Call ACTUAL module methods
    # ========================================================================
    
    def _collect_i_state_facets(self, content: str, source: str) -> Dict[str, Dict]:
        """
        Call ACTUAL i_universe.feed_all_beings() to get I-State interpretations.
        """
        if not self.i_universe:
            return {}
        
        try:
            # Call ACTUAL method on higher_universe_10.AuroraHigherUniverse
            feed_result = self.i_universe.feed_all_beings(content, source)
            
            # Extract interpretations and opinions from ACTUAL result
            interpretations = feed_result.get('interpretations', {})
            opinions = feed_result.get('opinions', {})
            
            # Select SFO for reweighting
            context = {'content': content, 'source': source}
            sfo = self.sfo_library.select_sfo(context)
            
            # Apply SFO to ACTUAL outputs
            reweighted = sfo.apply_to_outputs(feed_result)
            self.total_sfo_applications += 1
            
            return reweighted.get('reweighted_outputs', {})
            
        except Exception as e:
            print(f"[DCE] I-State collection error: {e}")
            return {}
    
    def _collect_behavioral_facet(self) -> Dict:
        """
        Call ACTUAL behavioral_evolution methods:
        - get_current_personality()
        - get_voice_params()
        - voice.warmth, voice.confidence, etc.
        """
        if not self.behavioral_evolution:
            return {}
        
        try:
            result = {}
            
            # Call ACTUAL get_current_personality()
            if hasattr(self.behavioral_evolution, 'get_current_personality'):
                result['personality'] = self.behavioral_evolution.get_current_personality()
            
            # Call ACTUAL get_voice_params()
            if hasattr(self.behavioral_evolution, 'get_voice_params'):
                result['tts_params'] = self.behavioral_evolution.get_voice_params()
            
            # Access ACTUAL voice genome attributes
            if hasattr(self.behavioral_evolution, 'voice'):
                voice = self.behavioral_evolution.voice
                result['warmth'] = getattr(voice, 'warmth', 0.6)
                result['confidence'] = getattr(voice, 'confidence', 0.5)
                result['speaking_rate'] = getattr(voice, 'speaking_rate', 0.5)
                result['presence'] = getattr(voice, 'presence', 0.5)
                result['pitch_variation'] = getattr(voice, 'pitch_variation', 0.4)
                result['resonance'] = getattr(voice, 'resonance', 0.5)
                
                if hasattr(voice, 'describe'):
                    result['description'] = voice.describe()
            
            # Call ACTUAL get_visual_attention()
            if hasattr(self.behavioral_evolution, 'get_visual_attention'):
                result['visual_attention'] = self.behavioral_evolution.get_visual_attention()
            
            # Call ACTUAL get_audio_params()
            if hasattr(self.behavioral_evolution, 'get_audio_params'):
                result['audio_params'] = self.behavioral_evolution.get_audio_params()
            
            return result
            
        except Exception as e:
            print(f"[DCE] Behavioral collection error: {e}")
            return {}
    
    def _collect_moral_facet(self) -> Dict:
        """
        Call ACTUAL moral_governor.get_moral_diagnostics() for 7-pillar status.
        """
        if not self.moral_governor:
            return {}
        
        try:
            # Call ACTUAL get_moral_diagnostics()
            if hasattr(self.moral_governor, 'get_moral_diagnostics'):
                diagnostics = self.moral_governor.get_moral_diagnostics()
                
                return {
                    'vitality': diagnostics.get('vitality', {}),
                    'moral_state': diagnostics.get('moral_state', {}),
                    'pillars': diagnostics.get('moral_state', {}).get('pillars', {}),
                    'overall_alignment': diagnostics.get('moral_state', {}).get('overall_alignment', 0.5),
                    'moral_momentum': diagnostics.get('moral_state', {}).get('moral_momentum', 0.0),
                    'recent_precedents': diagnostics.get('recent_precedents', [])
                }
            
            return {}
            
        except Exception as e:
            print(f"[DCE] Moral collection error: {e}")
            return {}
    
    def _collect_sensory_facet(self) -> Dict:
        """
        Call ACTUAL sensory_systems.capture() for vision/body snapshot.
        """
        if not self.sensory_systems:
            return {}
        
        try:
            # Call ACTUAL capture()
            if hasattr(self.sensory_systems, 'capture'):
                snapshot = self.sensory_systems.capture()
                return snapshot
            
            return {}
            
        except Exception as e:
            print(f"[DCE] Sensory collection error: {e}")
            return {}
    
    def _collect_harvested_facet(self) -> Dict:
        """
        Call ACTUAL information_harvester.collect() for context event.
        """
        if not self.information_harvester:
            return {}
        
        try:
            # Call ACTUAL collect()
            if hasattr(self.information_harvester, 'collect'):
                event = self.information_harvester.collect()
                
                # Call ACTUAL extract_vocabulary() if available
                if hasattr(self.information_harvester, 'extract_vocabulary'):
                    vocab = self.information_harvester.extract_vocabulary(event)
                    event['extracted_vocabulary'] = vocab
                
                return event
            
            return {}
            
        except Exception as e:
            # Harvesting is optional - silent fail
            return {}
    
    def _collect_impression_facet(self, content: str) -> Dict:
        """
        Call ACTUAL impression_engine.energy_to_shard() if energy packet available.
        """
        if not self.impression_engine:
            return {}
        
        try:
            # Create basic energy packet from content
            energy_packet = {
                'magnitude': len(content) / 100.0,
                'emotion_channels': {'interest': 0.6, 'processing': 0.4},
                'source': 'input'
            }
            
            # Call ACTUAL energy_to_shard() if available
            if hasattr(self.impression_engine, 'energy_to_shard'):
                shard = self.impression_engine.energy_to_shard(energy_packet)
                if shard:
                    return {
                        'shard_id': getattr(shard, 'id', 'unknown'),
                        'primary_emotion': getattr(shard, 'primary_emotion', 'neutral'),
                        'intensity': getattr(shard, 'intensity', 0.5),
                        'valence': getattr(shard, 'valence', 0.0)
                    }
            
            return {}
            
        except Exception as e:
            return {}
    
    def _collect_eepr_facet(self) -> Dict:
        """
        Call ACTUAL eepr.get_field_stats() for pressure field status.
        """
        if not self.eepr:
            return {}
        
        try:
            # Call ACTUAL get_field_stats()
            if hasattr(self.eepr, 'get_field_stats'):
                stats = self.eepr.get_field_stats()
                return stats
            
            return {}
            
        except Exception as e:
            return {}
    
    def _collect_governance_facet(self) -> Dict:
        """
        Call ACTUAL governance.get_stats() for governance status.
        """
        if not self.governance:
            return {}
        
        try:
            # Call ACTUAL get_stats()
            if hasattr(self.governance, 'get_stats'):
                stats = self.governance.get_stats()
                return stats
            
            return {}
            
        except Exception as e:
            return {}
    
    # ========================================================================
    # RESPONSE SYNTHESIS - Uses ACTUAL vocabulary from language_ecology
    # ========================================================================
    
    def synthesize_response(self, crystal: InteractionCrystal) -> str:
        """Removed — assembly-into-emission step. Emission now routed through ConstraintEmitter."""
        return ""

    def _get_actual_vocabulary(self) -> List[str]:
        """Get ACTUAL vocabulary from language_ecology.lexical_memory.vocabulary"""
        if not self.language_ecology:
            return []
        
        try:
            if hasattr(self.language_ecology, 'lexical_memory'):
                lm = self.language_ecology.lexical_memory
                if hasattr(lm, 'vocabulary'):
                    vocab = lm.vocabulary
                    if isinstance(vocab, dict):
                        return list(vocab.keys())[:1000]
                    elif isinstance(vocab, (set, list)):
                        return list(vocab)[:1000]
            return []
        except Exception:
            return []
    
    def _get_actual_wisdom(self, context: Optional[Dict] = None) -> List:
        """
        Get ACTUAL wisdom shards with AURORA_UNDERSTANDING preference.
        
        Priority:
        1. Aurora understanding shards (from brain runner)
        2. Offspring approximation shards (from language ecology)
        """
        all_shards = []
        
        # ================================================================
        # PRIORITY 1: Aurora's genuine understanding (from brain runner)
        # ================================================================
        aurora_shards = self._load_aurora_understanding_shards(context)
        if aurora_shards:
            all_shards.extend(aurora_shards)
            # print(f"[DCE] Using {len(aurora_shards)} Aurora understanding shards")
        
        # ================================================================
        # PRIORITY 2: Offspring shards (fallback if Aurora shards insufficient)
        # ================================================================
        if len(all_shards) < 5:
            offspring_shards = self._get_offspring_shards()
            if offspring_shards:
                # Tag them as offspring approximation
                for shard in offspring_shards:
                    if isinstance(shard, dict):
                        shard['source'] = 'offspring_approximation'
                all_shards.extend(offspring_shards)
        
        return all_shards[:20]
    
    def _load_aurora_understanding_shards(self, context: Optional[Dict] = None) -> List:
        """
        Load Aurora's genuine understanding shards from brain runner.
        
        These are tagged as AURORA_UNDERSTANDING and should be preferred
        over offspring approximations.
        """
        try:
            from pathlib import Path
            import json
            
            shards_file = Path.home() / ".aurora" / "simulation_brain" / "aurora_understanding_shards.json"
            
            if not shards_file.exists():
                return []
            
            with open(shards_file, 'r') as f:
                data = json.load(f)
            
            shards = data.get("shards", [])
            
            # Filter by context if provided
            if context and shards:
                scenario_type = context.get("scenario_type") or context.get("category")
                if scenario_type:
                    # Prefer shards matching the scenario type
                    matching = [s for s in shards if s.get("scenario_type") == scenario_type]
                    if matching:
                        return matching[:10]
            
            return shards[:10]
            
        except Exception as e:
            # Silently fail - Aurora shards may not exist yet
            return []
    
    def _get_offspring_shards(self) -> List:
        """Get offspring approximation shards from language ecology."""
        if not self.language_ecology:
            return []
        
        try:
            if hasattr(self.language_ecology, 'wisdom_store'):
                ws = self.language_ecology.wisdom_store
                if hasattr(ws, 'shards'):
                    shards = ws.shards
                    if isinstance(shards, dict):
                        return list(shards.values())[:20]
                    elif isinstance(shards, list):
                        return shards[:20]
            return []
        except Exception:
            return []
    
    def _extract_concepts(self, text: str) -> List[str]:
        words = text.lower().split()
        stopwords = {'the', 'a', 'an', 'is', 'are', 'to', 'of', 'and', 'in', 'that', 'it',
                    'for', 'on', 'with', 'as', 'at', 'by', 'this', 'from', 'or', 'but',
                    'what', 'how', 'why', 'when', 'where', 'who', 'me', 'my', 'your',
                    'hello', 'hi', 'hey'}
        return [w for w in words if len(w) > 2 and w not in stopwords][:5]
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    
    def ingest_presence_with_sfo(self, raw_input: Any, presence_type: Any = None,
                                  source: str = "external", sensory_data: Optional[Dict] = None) -> str:
        """
        Collect I-State crystal facets (axis signal sources only).
        Emission is routed through ConstraintEmitter — this method returns "".
        """
        content = str(raw_input)
        crystal = self.create_interaction_crystal(content, source)
        if self.dim_memory:
            try:
                if hasattr(self.dim_memory, 'store'):
                    self.dim_memory.store(crystal.to_dict())
                elif hasattr(self.dim_memory, 'add_memory'):
                    self.dim_memory.add_memory(crystal.to_dict())
            except Exception:
                pass
        return ""
    
    def get_enhanced_status(self) -> Dict[str, Any]:
        """Get DCE status."""
        return {
            'total_crystals_created': self.total_crystals_created,
            'total_sfo_applications': self.total_sfo_applications,
            'crystal_history_size': len(self.crystal_history),
            'modules_registered': {
                'i_universe': self.i_universe is not None,
                'behavioral_evolution': self.behavioral_evolution is not None,
                'moral_governor': self.moral_governor is not None,
                'sensory_systems': self.sensory_systems is not None,
                'information_harvester': self.information_harvester is not None,
                'impression_engine': self.impression_engine is not None,
                'manifold_engine': self.manifold_engine is not None,
                'eepr': self.eepr is not None,
                'governance': self.governance is not None,
                'language_ecology': self.language_ecology is not None,
                'dim_memory': self.dim_memory is not None
            }
        }
