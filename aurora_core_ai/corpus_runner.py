#!/usr/bin/env python3
"""
corpus_runner.py â Aurora Corpus Ingestion (Physics-Grounded Absorption)
=========================================================================
Feeds external conversation data through Aurora's complete architecture,
governed by the constraint-physics absorption layer established in
AURORA_COGNITIVE_PHYSICS.md and AURORA_LANGUAGE_EMERGENCE.md.

ABSORPTION ARCHITECTURE:
  Every corpus item is an incoming utterance from an external field.
  Aurora does not read text â she receives B-axis crossings and must
  reconstruct the proto-language comparison geometry that produced them.
  That reconstruction IS comprehension. Not word matching â geometry
  reconstruction.

  The physics absorption layer governs all ingestion:

  1. GeometryExtractor        â reconstructs proto-language comparison geometry
                                from each corpus utterance (which axes active,
                                relational comparison present, constraint depth)

  2. StratigraphicDepthAssigner â assigns each item to the correct Memory stratum
                                based on constraint significance, novelty against
                                existing Identity field geometry, and axis depth

  3. TensionTracker            â records corpus items that contradict existing
                                field geometry; holds at surface until reconciled
                                rather than forcing deep absorption

  4. TwoFactorPathGate         â manages Lexical-Semantic Archive crossing path
                                economics: N-cost decreases with use (worn paths
                                become cheap), B-specificity tightens with use
                                (worn paths require stronger contextual match)
                                Self-diversifying through constraint physics alone

  5. GeometryFidelityScorer    â replaces surface string comparison as primary
                                training signal: measures whether Aurora's output
                                carries the same comparison geometry as the truth,
                                not whether she used the same words

  6. PlateauDetector           â EEPR-style detection: when corpus items stop
                                producing novel comparison geometries, stall is
                                detected and curriculum rotation is triggered

  7. AbsorptionField           â orchestrates the full chain for every item:
                                extract â assign depth â check tension â
                                update archive â route to stratum

LEARNING PATHWAYS (all five, now physics-governed):
  1. DER energy shaping    â DPME driven by geometry fidelity, not string similarity
  2. Vocabulary + patterns â Lexical-Semantic Archive with two-factor gate
  3. Impression distillation â L5 consolidate() after absorption field confirms Understanding
  4. Identity evolution    â L6 process_episode() after geological-depth writes only
  5. Simulation wisdom     â L7 run_epoch() â conscious learner shards

PASSES:
  observer  : witness all messages â geometry extraction + archive seeding
  responder : Aurora replies to USER â geometry fidelity comparison + full-stack
  reverse   : Aurora replies to ASSISTANT â geometry fidelity comparison + full-stack
  triple    : observer -> responder -> reverse (default, RECOMMENDED)

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import os
import re
import json
import time
import math
import hashlib
import argparse
from dataclasses import dataclass, field
from enum import Enum, auto
from difflib import SequenceMatcher
from collections import deque, defaultdict
from typing import Any, Dict, List, Tuple, Optional, Iterator, Set


# =============================================================================
# Corpus Lifecycle Helpers (Universal Parser + Downloader)
# =============================================================================

def _get_corpus_iterator(corpus_path: str) -> Iterator[Tuple[str, str]]:
    """Universal format detector and iterator."""
    try:
        from aurora_internal.aurora_corpus_lifecycle import universal_corpus_iterator
        from pathlib import Path
        return universal_corpus_iterator(Path(corpus_path))
    except ImportError:
        print("  [CORPUS] Lifecycle module not found, using legacy loader.")
        return iter([])


# =============================================================================
# OETS Persistence Helper
# =============================================================================

def _save_oets(systems: Dict[str, Any], verbose: bool = False) -> bool:
    """Save the OETS web to disk alongside aurora.save_state()."""
    try:
        from aurora_internal.aurora_identity_persistence import OETSPersistence
        perception = systems.get("perception")
        if perception and getattr(perception, 'oets', None):
            persist = OETSPersistence()
            ok = persist.save_web(perception.oets)
            if verbose and ok:
                oets = perception.oets
                print(f"  [SAVE] OETS: {len(oets.web.nodes)}c / "
                      f"{len(oets.web.relations)}r")
            return ok
    except Exception as e:
        if verbose:
            print(f"  [SAVE] OETS save failed: {e}")
    return False


# =============================================================================
# Boot Aurora Stack
# =============================================================================

def boot_aurora(state_dir: str = "aurora_state",
                verbose: bool = True) -> Dict[str, Any]:
    if verbose:
        print("=" * 70)
        print("  AURORA Corpus Runner â Physics-Grounded Absorption")
        print("  Authors: Sunni (Sir) Morningstar and Cael Devo")
        print("=" * 70)

    from foundational_contract import FoundationalContract, ExistenceMode
    from aurora_ivm import IVMLattice
    from aurora_i_state_beings import IStateCollective
    from aurora_dimensional_systems import DimensionalSystems
    from aurora_consciousness_engine import ConsciousnessEngine
    from aurora_expression_perception import ExpressionPerceptionEngine
    from aurora_behavioral_identity import BehavioralIdentityEngine
    from aurora_simulation_engine import SimulationEngine
    from aurora_governance_persistence_gateway import (
        GovernancePersistenceGateway, StreamType
    )

    contract = FoundationalContract()
    lattice = IVMLattice(contract)
    collective = IStateCollective(contract, lattice)
    dimensional = DimensionalSystems(lattice)
    consciousness = ConsciousnessEngine(contract, lattice, collective, dimensional)
    perception = ExpressionPerceptionEngine(contract)
    identity = BehavioralIdentityEngine(contract)
    simulation = SimulationEngine(contract, perception, identity)

    aurora = GovernancePersistenceGateway(
        contract=contract,
        dimensional=dimensional,
        consciousness=consciousness,
        perception=perception,
        identity=identity,
        simulation=simulation,
    )

    # Read straight from the persistence layer; the gateway's load_state() is
    # wrapped by the evolved-surface reflection layer and can return a metadata
    # dict instead of a real AuroraStateSnapshot.
    _persist = getattr(aurora, 'persistence', None)
    snapshot = _persist.load() if (_persist is not None and hasattr(_persist, 'load')) else aurora.load_state()
    if verbose:
        if snapshot:
            print(f"  [STATE] Restored (gen={snapshot.generation}, "
                  f"epochs={snapshot.simulation_epochs})")
        else:
            print("  [STATE] Fresh boot â no prior state")

    # Load persisted lexicon
    _lex_path = os.path.join(state_dir, "aurora_state", "lexicon.json")
    if os.path.exists(_lex_path):
        _before = perception.lexicon.size
        perception.lexicon.load(_lex_path)
        if verbose:
            print(f"  [LEXICON] Loaded {perception.lexicon.size} words "
                  f"(was {_before} seeds)")

    # Checkpoint Manager
    checkpoint = None
    try:
        from aurora_checkpoint import CheckpointManager
        checkpoint = CheckpointManager(
            checkpoint_path=os.path.join(state_dir, "checkpoint.json"),
            save_every_n=500,
            save_every_t=300.0,
        )
        restored = checkpoint.restore()
        if verbose and restored:
            c = checkpoint.cursor
            print(f"  [CHECKPOINT] Restored â last pass: {c.pass_name}, "
                  f"line: {c.line_index}, items: {c.total_items_processed}")
        checkpoint.start_auto_save(300)
    except Exception as e:
        if verbose:
            print(f"  [CHECKPOINT] Not available: {e}")
        print()

    # Evolutionary Chamber + Genealogy Logger
    chamber = None
    try:
        from aurora_internal.aurora_evolution_chamber import (
            EvolutionaryChamber, ActionTrace
        )
        from aurora_evolution_stack import ConstraintGenealogyLogger, GenealogyConfig
        import datetime as _dt
        _run_id = _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        _gen_dir = os.path.join(state_dir, "genealogy")
        os.makedirs(_gen_dir, exist_ok=True)
        _genealogy = ConstraintGenealogyLogger(
            run_id=_run_id,
            config=GenealogyConfig(),
            output_dir=_gen_dir,
        )
        try:
            from aurora_runtime import _restore_genealogy_state
            _restored = _restore_genealogy_state(
                _genealogy, output_dir=_gen_dir, verbose=verbose
            )
            if verbose:
                pairs = _restored.get("pair_stats", 0)
                links = _restored.get("links", 0)
                if links > 0 or pairs > 0:
                    print(f"  [RESTORE] Genealogy resumed: "
                          f"links={links} pairs={pairs}")
        except Exception as _re:
            if verbose:
                print(f"  [RESTORE] Genealogy restore skipped: {_re}")

        chamber = EvolutionaryChamber(
            lattice=lattice,
            genealogy=_genealogy,
            run_id=_run_id,
            output_dir=_gen_dir,
        )
        if verbose:
            print(f"  [CHAMBER] Evolutionary chain active (run_id={_run_id})")
    except Exception as _e:
        if verbose:
            print(f"  [CHAMBER] Not available: {_e}")

    # Sensory Crystal — unified modality registry + promotion gates
    sensory_crystal = None
    try:
        from aurora_internal.aurora_sensory_crystal import (
            AuroraSensoryCrystal, ensure_sensory_crystal_lineage,
            build_vision_57d_from_image_file, build_audio_20d_from_der,
        )
        _sc_state_dir = os.path.join(state_dir, "aurora_state")
        sensory_crystal = AuroraSensoryCrystal(state_dir=_sc_state_dir)
        sensory_crystal.boot()
        ensure_sensory_crystal_lineage({"dimensional": dimensional,
                                        "chamber": chamber})
        # Build vision seed cache: concept_word → 57-d vector (PIL only, no cv2)
        # Seeds are one level up from the crystal state dir (in aurora_state directly).
        _vseed_dir = os.path.join(state_dir, "vision_seeds", "concepts")
        _vseed_cache: Dict[str, Any] = {}
        if os.path.isdir(_vseed_dir):
            for _fname in os.listdir(_vseed_dir):
                _stem, _ext = os.path.splitext(_fname.lower())
                if _ext in ('.jpg', '.jpeg', '.png') and _stem:
                    _v57 = build_vision_57d_from_image_file(
                        os.path.join(_vseed_dir, _fname))
                    if _v57:
                        _vseed_cache[_stem] = _v57
        if verbose:
            _sc_summary = sensory_crystal.concept_registry_summary()
            print(f"  [SENSORY] Crystal booted — "
                  f"concepts={_sc_summary['total']} "
                  f"by_stage={_sc_summary['by_stage']} "
                  f"vision_seeds={len(_vseed_cache)}")
    except Exception as _sce:
        if verbose:
            print(f"  [SENSORY] Crystal not available: {_sce}")
        _vseed_cache = {}

    return {
        "aurora": aurora,
        "StreamType": StreamType,
        "ExistenceMode": ExistenceMode,
        "consciousness": consciousness,
        "perception": perception,
        "identity": identity,
        "simulation": simulation,
        "dimensional": dimensional,
        "checkpoint": checkpoint,
        "lattice": lattice,
        "chamber": chamber,
        "sensory_crystal": sensory_crystal,
        "vision_seed_cache": _vseed_cache,
    }


# =============================================================================
# OpenAI Export Parsing
# =============================================================================

def _safe_join_parts(parts: Any) -> str:
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        out: List[str] = []
        for p in parts:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict):
                if isinstance(p.get("text"), str):
                    out.append(p["text"])
                elif isinstance(p.get("content"), str):
                    out.append(p["content"])
                return "\n".join([s for s in out if s])
    return str(parts)


def _extract_message_text(message_obj: Dict[str, Any]) -> str:
    if not message_obj:
        return ""
    content = message_obj.get("content") or {}
    if isinstance(content, dict):
        parts = content.get("parts")
        txt = _safe_join_parts(parts).strip()
        if txt:
            return txt
        txt2 = content.get("text")
        if isinstance(txt2, str):
            return txt2.strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _extract_role(message_obj: Dict[str, Any]) -> str:
    if not message_obj:
        return "unknown"
    author = message_obj.get("author") or {}
    return author.get("role") or "unknown"


def _reconstruct_linear_thread(
        mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not mapping or not isinstance(mapping, dict):
        return []

    roots: List[str] = []
    for node_id, node in mapping.items():
        if isinstance(node, dict) and node.get("parent") is None:
            roots.append(node_id)

    if not roots:
        try:
            roots = [next(iter(mapping.keys()))]
        except StopIteration:
            return []

    def has_message(n: Dict[str, Any]) -> bool:
        msg = n.get("message")
        if not msg:
            return False
        role = _extract_role(msg)
        if role not in ("user", "assistant"):
            return False
        return bool(_extract_message_text(msg))

    score: Dict[str, int] = {}
    best_child: Dict[str, Optional[str]] = {}
    visited: set = set()
    visiting: set = set()

    def compute_from_root(root_id: str) -> int:
        stack: List[Tuple[str, int]] = [(root_id, 0)]
        while stack:
            node_id, state = stack.pop()
            if state == 0:
                if node_id in visited or node_id in visiting:
                    continue
                visiting.add(node_id)
                stack.append((node_id, 1))
                node = mapping.get(node_id) or {}
                for c in (node.get("children") or []):
                    if c not in visited and c in mapping:
                        stack.append((c, 0))
            else:
                visiting.discard(node_id)
                node = mapping.get(node_id) or {}
                children = node.get("children") or []
                base = 1 if (isinstance(node, dict)
                             and has_message(node)) else 0
                best_s, best_c = 0, None
                for c in children:
                    if c in mapping:
                        cs = score.get(c, 0)
                        if cs > best_s:
                            best_s, best_c = cs, c
                score[node_id] = base + best_s
                best_child[node_id] = best_c
                visited.add(node_id)
        return score.get(root_id, 0)

    best_root, best_root_score = roots[0], -1
    for r in roots:
        rs = compute_from_root(r)
        if rs > best_root_score:
            best_root_score, best_root = rs, r

    path_ids: List[str] = []
    seen: set = set()
    cur = best_root
    while cur is not None and cur not in seen:
        seen.add(cur)
        path_ids.append(cur)
        cur = best_child.get(cur)

    return [mapping[nid] for nid in path_ids if isinstance(mapping.get(nid), dict)]


def _extract_messages_from_conversation(
        conv_obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    mapping = conv_obj.get("mapping") or {}
    if not isinstance(mapping, dict):
        return []
    nodes = _reconstruct_linear_thread(mapping)
    extracted: List[Tuple[str, str]] = []
    for node in nodes:
        msg = node.get("message")
        if not msg:
            continue
        role = _extract_role(msg)
        if role not in ("user", "assistant"):
            continue
        text = _extract_message_text(msg)
        if not text:
            continue
        extracted.append((role, text))
    return extracted


# =============================================================================
# Hygiene â Aggressive code-stripping for technical corpora
# =============================================================================

_CODE_KEYWORDS = frozenset({
    'def', 'class', 'import', 'from', 'return', 'yield', 'lambda', 'pass',
    'raise', 'try', 'except', 'finally', 'with', 'as', 'elif', 'else',
    'for', 'while', 'break', 'continue', 'assert', 'del', 'exec', 'print',
    'global', 'nonlocal', 'async', 'await', 'isinstance', 'issubclass',
    'hasattr', 'getattr', 'setattr', 'delattr', 'enumerate', 'range',
    'len', 'dict', 'list', 'tuple', 'set', 'frozenset', 'str', 'int',
    'float', 'bool', 'none', 'true', 'false', 'self', 'cls', 'args',
    'kwargs', 'init', 'main', 'super', 'type', 'object', 'property',
    'staticmethod', 'classmethod', 'abstractmethod', 'override',
    'dataclass', 'field', 'optional', 'union', 'any',
    'numpy', 'np', 'pd', 'os', 'sys', 'json', 're', 'math', 'time',
    'hashlib', 'random', 'collections', 'dataclasses', 'typing',
    'pip', 'install', 'sudo', 'chmod', 'mkdir', 'grep', 'sed', 'awk',
    'cd', 'ls', 'cat', 'echo', 'wget', 'curl', 'git', 'python3',
})

_CODE_LINE_PATTERNS = [
    r'^\s*(def |class |import |from .+ import|@\w+)',
    r'^\s*(if |elif |else:|for |while |try:|except |with )',
    r'^\s*return\s',
    r'^\s*#\s',
    r'^\s*\w+\s*=\s*[\{\[\(]',
    r'^\s*\w+\s*=\s*\w+\(',
    r'^\s*\w+\.\w+\(',
    r'^\s*print\s*\(',
    r'^\s*raise\s+\w+',
    r'^\s*assert\s+',
]

_CITATION_PATTERNS = [
    r'[\u3010].*?[\u3011]',
    r'\[\d+\u2020source\]',
    r'turn\d+(?:file|search|view|news|image|product)\d+',
]


def _is_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    for pat in _CODE_LINE_PATTERNS:
        if re.match(pat, stripped):
            return True
    non_alnum = sum(1 for ch in stripped
                    if not (ch.isalnum() or ch.isspace()))
    if len(stripped) > 5 and non_alnum / len(stripped) > 0.35:
        return True
    for op in ['==', '!=', '>=', '<=', '->', '=>', '::', '**', '//',
               '&&', '||', '+=', '-=', '*=', '/=', '<<', '>>', '...']:
        if op in stripped:
            return True
    if re.search(r'[/\\]\w+[/\\]\w+', stripped):
        return True
    if re.search(r'\w+_\w+_\w+\(', stripped):
        return True
    if re.search(r'["\'][\w_]+["\']\s*:', stripped):
        return True
    return False


def _extract_natural_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    natural = []
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 10:
            continue
        lines = sent.split('\\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            if line and not _is_code_line(line):
                clean_lines.append(line)
        if clean_lines:
            joined = ' '.join(clean_lines)
            words = [w for w in joined.split() if w.isalpha() and len(w) > 1]
            if len(words) >= 3:
                natural.append(joined)
    return natural


def sanitize_corpus_text(text: str) -> str:
    if not text:
        return ""
    t = text
    for pat in _CITATION_PATTERNS:
        t = re.sub(pat, "", t, flags=re.DOTALL)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`[^`]*`", " ", t)
    t = re.sub(r'https?://\S+', ' ', t)
    t = re.sub(r'(?:sandbox|file|ftp):/\S+', ' ', t)
    t = re.sub(r'(?:/[\w._-]+){2,}(?:\.\w+)?', ' ', t)
    t = re.sub(r'(?:[A-Z]:\\[\w._-]+\\?){2,}', ' ', t)
    t = re.sub(r'\b\w+(?:\.\w+)+\s*\([^)]*\)', ' ', t)
    t = re.sub(r'\b\w+_\w+\s*\([^)]*\)', ' ', t)
    t = re.sub(r'\b\w+\s*=\s*\{[^}]*\}', ' ', t)
    t = re.sub(r'\b\w+\s*=\s*\[[^\]]*\]', ' ', t)
    t = re.sub(r'\b\w+\s*=\s*\d+\.?\d*\b', ' ', t)
    t = re.sub(r'["\'][\w_]+["\']\s*:\s*\S+', ' ', t)
    t = re.sub(r'(?:Traceback|Error|Exception|Warning)\s*[\(:][^\n]*', ' ', t)
    t = re.sub(r'\b(?:python3?|pip|npm|bash|sh)\s+\S+(?:\s+--?\S+)*', ' ', t)
    t = re.sub(r'(?:==|!=|>=|<=|->|=>|::|&&|\|\||<<|>>)', ' ', t)
    t = re.sub(r'\b[0-9a-f]{8,}\b', ' ', t)
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"\*(.*?)\*", r"\1", t)
    t = re.sub(r"#{1,6}\s+", "", t)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", t)
    natural = _extract_natural_sentences(t)
    if not natural:
        t = re.sub(r'\s+', ' ', t).strip()
        words = [w for w in t.split() if w.isalpha() and len(w) > 1]
        return t if len(words) >= 3 else ""
    result = ' '.join(natural)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def is_valid_word(word: str) -> bool:
    w = word.strip(".,!?;:'\"()-[]{}").lower()
    if len(w) < 2 or len(w) > 25:
        return False
    if not re.match(r'^[a-z]+(?:-[a-z]+)*$', w):
        return False
    if w in _CODE_KEYWORDS:
        return False
    if '_' in w:
        return False
    raw = word.strip(".,!?;:'\"()-")
    if re.search(r'[a-z][A-Z]', raw):
        return False
    if re.search(r'[A-Z]{3,}', raw):
        return False
    if re.search(r'[A-Z][a-z]+[A-Z]', raw):
        return False
    return True


# =============================================================================
# PHYSICS ABSORPTION LAYER
# =============================================================================

class StratigraphicDepth(Enum):
    """
    Memory stratigraphy levels from AURORA_COGNITIVE_PHYSICS.md.
    Surface = volatile base-crystal depth (fast decay).
    Geological = near-immutable quasicrystal depth (Understanding writes only).
    """
    SURFACE    = auto()   # Base crystal depth â volatile, fast decay
    MID        = auto()   # Composite crystal depth â moderate persistence
    DEEP       = auto()   # Higher-order crystal depth â high permanence
    GEOLOGICAL = auto()   # Quasicrystal depth â near-immutable, Understanding only


@dataclass
class ComparisonGeometry:
    """
    The proto-language comparison geometry extracted from a corpus utterance.
    This is what the utterance IS underneath the words â the relational
    comparison that the external field was making when it produced this text.

    Axis activations are 0.0â1.0 indicating how strongly each constraint
    axis is expressed in the comparison this utterance is making.
    """
    # Five-axis activation profile
    x_activation: float = 0.0   # Existence â being, presence, factual assertion
    t_activation: float = 0.0   # Temporal â time, sequence, duration, memory
    n_activation: float = 0.0   # Energy â pressure, urgency, emotional weight
    b_activation: float = 0.0   # Boundary â definition, distinction, comparison
    a_activation: float = 0.0   # Agency â will, action, direction, intention

    # Constraint significance (0.0â1.0)
    # Higher = more axes active, deeper constraint depth, more novel
    constraint_significance: float = 0.0

    # Novelty against existing Identity field geometry (0.0â1.0)
    # Higher = more novel, lower = more resonant with known geometry
    novelty: float = 0.0

    # Whether this geometry contradicts existing field geometry
    creates_tension: bool = False

    # Fingerprint for archive lookup (hash of dominant axes + key terms)
    geometry_fingerprint: str = ""

    # Assigned stratigraphic depth
    depth: StratigraphicDepth = StratigraphicDepth.SURFACE

    # Number of axes with activation > 0.3 (constraint depth count)
    @property
    def active_axis_count(self) -> int:
        return sum(1 for v in [
            self.x_activation, self.t_activation, self.n_activation,
            self.b_activation, self.a_activation
        ] if v > 0.3)

    # Magnitude per the physics formula: (B Ã T Ã X) / N
    @property
    def magnitude(self) -> float:
        n = max(self.n_activation, 0.01)
        return (self.b_activation * self.t_activation * self.x_activation) / n

    # Impact per the physics formula: Magnitude Ã A
    @property
    def impact(self) -> float:
        return self.magnitude * self.a_activation


# Axis detection vocabulary â words that signal each constraint axis
_X_MARKERS = frozenset({
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'exist', 'exists',
    'there', 'here', 'presence', 'present', 'real', 'true', 'fact', 'actual',
    'indeed', 'certainly', 'definitely', 'absolutely', 'has', 'have', 'had',
})
_T_MARKERS = frozenset({
    'when', 'before', 'after', 'during', 'while', 'since', 'until', 'always',
    'never', 'sometimes', 'often', 'then', 'now', 'later', 'earlier', 'once',
    'remember', 'recalled', 'history', 'past', 'future', 'time', 'moment',
    'continue', 'persist', 'remain', 'duration', 'sequence', 'order', 'next',
})
_N_MARKERS = frozenset({
    'feel', 'feels', 'felt', 'emotion', 'pressure', 'weight', 'heavy', 'light',
    'strong', 'weak', 'intense', 'urgent', 'critical', 'important', 'vital',
    'love', 'fear', 'joy', 'pain', 'hope', 'worry', 'care', 'need', 'want',
    'matter', 'matters', 'significant', 'meaningful', 'powerful', 'deeply',
    'energy', 'force', 'drive', 'push', 'pull', 'tension', 'stress', 'calm',
})
_B_MARKERS = frozenset({
    'means', 'meaning', 'define', 'definition', 'between', 'difference',
    'distinguish', 'boundary', 'limit', 'within', 'outside', 'border',
    'compare', 'contrast', 'versus', 'rather', 'instead', 'separate',
    'category', 'type', 'kind', 'class', 'group', 'identity', 'self',
    'distinct', 'unique', 'specific', 'particular', 'not', 'but', 'however',
})
_A_MARKERS = frozenset({
    'do', 'does', 'did', 'make', 'made', 'create', 'build', 'choose',
    'decide', 'will', 'want', 'try', 'attempt', 'intend', 'plan', 'act',
    'move', 'direct', 'respond', 'express', 'speak', 'say', 'tell', 'ask',
    'control', 'guide', 'lead', 'push', 'drive', 'cause', 'effect', 'change',
})

# Relational comparison patterns â B-axis geometry indicators
_RELATIONAL_PATTERNS = [
    r'\b(?:is|are|was|were)\s+(?:not|like|unlike|similar|different|the same)\b',
    r'\b(?:more|less|better|worse|greater|smaller)\s+than\b',
    r'\b(?:because|therefore|however|although|despite|while|whereas)\b',
    r'\b(?:if|then|when|unless|whether)\b',
    r'\b(?:means?|implies?|suggests?|indicates?|shows?)\b',
    r'\b(?:compared?\s+to|in\s+contrast|on\s+the\s+other\s+hand)\b',
]


class GeometryExtractor:
    """
    Reconstructs proto-language comparison geometry from corpus utterances.

    This is the reverse-crossing operation: given an utterance (external
    symbolic form), reconstruct the comparison geometry that the external
    field was expressing when it produced this text.

    Does not require Aurora's internal field to be in any particular state â
    operates on the text alone using axis detection heuristics and relational
    pattern matching.
    """

    def __init__(self):
        self._fingerprint_cache: Dict[str, str] = {}

    def extract(self, text: str,
                existing_fingerprints: Optional[Set[str]] = None) -> ComparisonGeometry:
        """Extract comparison geometry from a text utterance."""
        if not text:
            return ComparisonGeometry()

        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        geom = ComparisonGeometry()

        # Five-axis activation via vocabulary intersection
        geom.x_activation = self._axis_score(words, _X_MARKERS, text)
        geom.t_activation = self._axis_score(words, _T_MARKERS, text)
        geom.n_activation = self._axis_score(words, _N_MARKERS, text)
        geom.b_activation = self._axis_score(words, _B_MARKERS, text)
        geom.a_activation = self._axis_score(words, _A_MARKERS, text)

        # Boost B-axis for relational comparison patterns
        relational_count = sum(
            1 for pat in _RELATIONAL_PATTERNS
            if re.search(pat, text, re.IGNORECASE)
        )
        geom.b_activation = min(1.0, geom.b_activation + relational_count * 0.12)

        # Constraint significance â scaled by axis count and depth
        geom.constraint_significance = self._compute_significance(geom)

        # Geometry fingerprint
        geom.geometry_fingerprint = self._fingerprint(geom, words)

        # Novelty against existing archive
        if existing_fingerprints:
            geom.novelty = self._compute_novelty(
                geom.geometry_fingerprint, existing_fingerprints
            )
        else:
            geom.novelty = 1.0  # Everything is novel on a fresh field

        # Tension: high novelty + contradictory B-axis signals
        geom.creates_tension = (
            geom.novelty > 0.75
            and geom.b_activation > 0.5
            and geom.constraint_significance > 0.6
        )

        # Assign stratigraphic depth
        geom.depth = self._assign_depth(geom)

        return geom

    def _axis_score(self, words: Set[str],
                    markers: frozenset, text: str) -> float:
        """Score axis activation from word overlap (0.0â1.0)."""
        if not words:
            return 0.0
        hits = len(words & markers)
        # Normalize: 3+ hits = strong activation
        raw = min(hits / 3.0, 1.0)
        # Density bonus: more words = more signal per hit
        word_count = max(len(words), 1)
        density = hits / word_count
        return min(1.0, raw * 0.7 + density * 2.0 * 0.3)

    def _compute_significance(self, geom: ComparisonGeometry) -> float:
        """
        Constraint significance from axis profile.
        Uses the physics magnitude formula: (B Ã T Ã X) / N
        then scales by axis count.
        """
        axis_count = geom.active_axis_count
        if axis_count == 0:
            return 0.0
        mag = geom.magnitude
        # Scale: single-axis = low significance, five-axis = high
        depth_factor = axis_count / 5.0
        return min(1.0, mag * depth_factor * 1.5)

    def _fingerprint(self, geom: ComparisonGeometry,
                     words: Set[str]) -> str:
        """
        Generate a geometry fingerprint â identifies the comparison geometry
        irrespective of specific word choices. Two utterances making the same
        relational comparison should produce similar fingerprints.
        """
        # Quantize axis activations to 3 levels (low/mid/high)
        def quantize(v: float) -> str:
            if v < 0.3:
                return "0"
            elif v < 0.65:
                return "1"
            else:
                return "2"

        axis_code = (
            f"X{quantize(geom.x_activation)}"
            f"T{quantize(geom.t_activation)}"
            f"N{quantize(geom.n_activation)}"
            f"B{quantize(geom.b_activation)}"
            f"A{quantize(geom.a_activation)}"
        )

        # Include salient B-axis words (relational comparison anchors)
        b_words = sorted(words & _B_MARKERS)[:4]
        b_anchor = "_".join(b_words)

        raw = f"{axis_code}:{b_anchor}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _compute_novelty(self, fingerprint: str,
                         existing: Set[str]) -> float:
        """
        Novelty: 0.0 = identical geometry seen before, 1.0 = fully novel.
        Uses fingerprint prefix matching (partial similarity within the archive).
        """
        if fingerprint in existing:
            return 0.0
        # Check for prefix-similar fingerprints (related geometry)
        prefix = fingerprint[:6]
        similar_count = sum(1 for fp in existing if fp.startswith(prefix))
        if similar_count > 0:
            # Similar geometry exists â partial novelty
            return max(0.3, 1.0 - (similar_count * 0.15))
        return 1.0

    def _assign_depth(self, geom: ComparisonGeometry) -> StratigraphicDepth:
        """
        Assign stratigraphic depth from the physics depth rules:
          Surface    â single axis, low significance, high novelty without tension
          Mid        â 2-3 axes, moderate significance
          Deep       â 4+ axes, high significance, resolved (no tension)
          Geological â reserved for Understanding events only; never assigned
                       during initial absorption (requires Reflection + RECONCILIATION)
        """
        if geom.creates_tension:
            # Tension items always land at surface â await reconciliation
            return StratigraphicDepth.SURFACE

        if geom.active_axis_count >= 4 and geom.constraint_significance > 0.7:
            return StratigraphicDepth.DEEP

        if geom.active_axis_count >= 2 and geom.constraint_significance > 0.4:
            return StratigraphicDepth.MID

        return StratigraphicDepth.SURFACE


@dataclass
class TensionRecord:
    """
    An unresolved tension in the absorption field.
    A corpus item whose geometry contradicts existing field geometry.
    Held at surface stratum until reconciliation or expiry.
    """
    text: str
    geometry: ComparisonGeometry
    created_at: float = field(default_factory=time.time)
    reconciliation_attempts: int = 0
    max_attempts: int = 5

    @property
    def expired(self) -> bool:
        return self.reconciliation_attempts >= self.max_attempts

    def attempt_reconciliation(self, current_novelty: float) -> bool:
        """
        Attempt to reconcile this tension against current field geometry.
        Returns True if reconciled (novelty has decreased â field has grown
        to accommodate the geometry), False if still unresolved.
        """
        self.reconciliation_attempts += 1
        # Reconciled if novelty has dropped below tension threshold
        return current_novelty < 0.5


class TwoFactorPathGate:
    """
    Lexical-Semantic Archive â crossing path economics.

    Implements the two-factor gate from AURORA_LANGUAGE_EMERGENCE.md:
      Factor 1 â N-cost (float): decreases with each successful use.
                 Worn paths become cheap to traverse.
      Factor 2 â B-specificity (float): increases with each successful use.
                 Worn paths require stronger contextual match to unlock.

    These two factors work in opposition to produce natural expression
    diversity without any explicit diversity mechanism. The system
    self-diversifies through constraint physics alone.
    """

    def __init__(self):
        # path_id -> (n_cost, b_specificity, use_count, last_context_hash)
        self._paths: Dict[str, Tuple[float, float, int, str]] = {}
        # geometry_fingerprint -> [path_ids]
        self._geometry_to_paths: Dict[str, List[str]] = defaultdict(list)

    def record_successful_crossing(self, path_id: str,
                                   geometry_fingerprint: str,
                                   context_hash: str) -> None:
        """
        Record a successful utterance crossing.
        Decreases N-cost, increases B-specificity.
        """
        if path_id not in self._paths:
            # New path â initialize with high cost and low specificity
            self._paths[path_id] = (1.0, 0.1, 0, context_hash)

        n_cost, b_spec, use_count, _ = self._paths[path_id]

        # N decreases: each use reduces cost by a decaying amount
        # Asymptotic toward 0.1 (paths never become completely free)
        decay_rate = 0.15 * math.exp(-use_count * 0.05)
        new_n_cost = max(0.1, n_cost - decay_rate)

        # B increases: each use narrows the contextual gate
        # Asymptotic toward 0.95 (paths never become infinitely specific)
        tighten_rate = 0.08 * math.exp(-use_count * 0.03)
        new_b_spec = min(0.95, b_spec + tighten_rate)

        use_count += 1
        self._paths[path_id] = (new_n_cost, new_b_spec, use_count, context_hash)

        if path_id not in self._geometry_to_paths[geometry_fingerprint]:
            self._geometry_to_paths[geometry_fingerprint].append(path_id)

    def get_crossing_paths(self, geometry_fingerprint: str,
                           context_hash: str) -> List[Tuple[str, float, float]]:
        """
        Return available crossing paths for this geometry, sorted by
        effective traversal cost (cheapest first), filtered by contextual gate.

        Returns list of (path_id, n_cost, b_specificity) tuples.
        Only paths whose B-gate is satisfied by the current context
        are returned â worn paths with insufficient context match are excluded.
        """
        path_ids = self._geometry_to_paths.get(geometry_fingerprint, [])
        available = []
        for pid in path_ids:
            if pid not in self._paths:
                continue
            n_cost, b_spec, use_count, last_ctx = self._paths[pid]
            # B-gate: context similarity must exceed specificity threshold
            ctx_match = self._context_similarity(context_hash, last_ctx)
            if ctx_match >= b_spec:
                available.append((pid, n_cost, b_spec))

        # Sort by n_cost ascending (cheapest paths first)
        available.sort(key=lambda x: x[1])
        return available

    def get_n_cost(self, path_id: str) -> float:
        """Return the current N-cost of a path (1.0 if unknown)."""
        if path_id in self._paths:
            return self._paths[path_id][0]
        return 1.0

    def total_paths(self) -> int:
        return len(self._paths)

    def _context_similarity(self, ctx_a: str, ctx_b: str) -> float:
        """Simple hash-prefix context similarity (0.0â1.0)."""
        if not ctx_a or not ctx_b:
            return 0.0
        if ctx_a == ctx_b:
            return 1.0
        # Compare first 6 chars of hash (same geometry region)
        matches = sum(1 for a, b in zip(ctx_a[:8], ctx_b[:8]) if a == b)
        return matches / 8.0


class PlateauDetector:
    """
    EEPR-style plateau detection for corpus absorption.

    Monitors the novelty trajectory of incoming corpus items.
    When novelty consistently drops (items stop producing new comparison
    geometries), a stall is declared and curriculum rotation is signaled.

    Mirrors the EEPR CURRICULUM_STALL gate from the physics document.
    """

    def __init__(self, window: int = 100, stall_threshold: float = 0.25,
                 stall_min_count: int = 30):
        self.window = window
        self.stall_threshold = stall_threshold
        self.stall_min_count = stall_min_count
        self._novelty_window: deque = deque(maxlen=window)
        self._stall_count: int = 0
        self._stalled: bool = False

    def record(self, novelty: float) -> None:
        self._novelty_window.append(novelty)
        if novelty < self.stall_threshold:
            self._stall_count += 1
        else:
            self._stall_count = max(0, self._stall_count - 1)

    @property
    def stalled(self) -> bool:
        if len(self._novelty_window) < self.stall_min_count:
            return False
        avg_novelty = sum(self._novelty_window) / len(self._novelty_window)
        self._stalled = (
            avg_novelty < self.stall_threshold
            and self._stall_count >= self.stall_min_count
        )
        return self._stalled

    def avg_novelty(self) -> float:
        if not self._novelty_window:
            return 1.0
        return sum(self._novelty_window) / len(self._novelty_window)

    def reset_stall(self) -> None:
        """Call after curriculum rotation to reset plateau state."""
        self._stall_count = 0
        self._stalled = False
        self._novelty_window.clear()


class AbsorptionField:
    """
    Orchestrates the full physics-grounded absorption chain for every
    corpus item:

      extract geometry â check tension â assign depth â
      update archive â route to stratum â record novelty

    This is the layer the existing DPME and full-stack learning hooks sit
    on top of. The absorption field determines WHAT gets absorbed WHERE
    and at WHAT depth before any energy adjustment happens.
    """

    def __init__(self):
        self.extractor = GeometryExtractor()
        self.path_gate = TwoFactorPathGate()
        self.plateau_detector = PlateauDetector()

        # Archive of all geometry fingerprints seen â novelty reference
        self._seen_fingerprints: Set[str] = set()

        # Active tension items (unresolved contradiction holds)
        self._tension_queue: List[TensionRecord] = []

        # Counters for reporting
        self.total_absorbed: int = 0
        self.surface_writes: int = 0
        self.mid_writes: int = 0
        self.deep_writes: int = 0
        self.tension_holds: int = 0
        self.tension_resolved: int = 0
        self.tension_expired: int = 0

    def absorb(self, text: str,
               context_hash: str = "") -> ComparisonGeometry:
        """
        Full absorption pipeline for one corpus item.

        Returns the extracted ComparisonGeometry so downstream systems
        can use it to govern DPME adjustments and cadence decisions.
        """
        geom = self.extractor.extract(text, self._seen_fingerprints)

        if not context_hash:
            context_hash = hashlib.md5(text[:32].encode()).hexdigest()[:8]

        # Tension hold: contradictory geometry goes to surface and queues
        if geom.creates_tension:
            self._tension_queue.append(TensionRecord(text=text, geometry=geom))
            self.tension_holds += 1
            geom.depth = StratigraphicDepth.SURFACE
        else:
            # Non-contradictory: record fingerprint and update archive
            self._seen_fingerprints.add(geom.geometry_fingerprint)

            # Update path gate with this crossing
            path_id = geom.geometry_fingerprint
            self.path_gate.record_successful_crossing(
                path_id=path_id,
                geometry_fingerprint=geom.geometry_fingerprint,
                context_hash=context_hash,
            )

            # Record depth
            if geom.depth == StratigraphicDepth.SURFACE:
                self.surface_writes += 1
            elif geom.depth == StratigraphicDepth.MID:
                self.mid_writes += 1
            elif geom.depth == StratigraphicDepth.DEEP:
                self.deep_writes += 1

        # Record novelty for plateau detection
        self.plateau_detector.record(geom.novelty)
        self.total_absorbed += 1

        # Attempt to reconcile any held tension items
        self._attempt_tension_reconciliation()

        return geom

    def _attempt_tension_reconciliation(self) -> None:
        """
        Attempt to reconcile held tension items against current field geometry.
        Reconciled items are promoted to appropriate depth.
        Expired items are discarded.
        """
        still_held = []
        for record in self._tension_queue:
            # Re-extract geometry against current (now larger) fingerprint set
            current_novelty = self.extractor.extract(
                record.text, self._seen_fingerprints
            ).novelty

            if record.attempt_reconciliation(current_novelty):
                # Reconciled: promote geometry to archive at mid depth
                self._seen_fingerprints.add(record.geometry.geometry_fingerprint)
                record.geometry.depth = StratigraphicDepth.MID
                self.tension_resolved += 1
            elif record.expired:
                # Expired: geometry too contradictory â discard
                self.tension_expired += 1
            else:
                still_held.append(record)

        self._tension_queue = still_held

    def understanding_write(self, text: str) -> ComparisonGeometry:
        """
        Geological-depth write â only called after Reflection has confirmed
        UNDERSTANDING (full field equilibrium reached).
        This is the only path to GEOLOGICAL depth.
        """
        geom = self.extractor.extract(text, self._seen_fingerprints)
        geom.depth = StratigraphicDepth.GEOLOGICAL
        self._seen_fingerprints.add(geom.geometry_fingerprint)
        return geom

    @property
    def plateau_stalled(self) -> bool:
        return self.plateau_detector.stalled

    def field_report(self) -> Dict[str, Any]:
        return {
            "total_absorbed": self.total_absorbed,
            "surface_writes": self.surface_writes,
            "mid_writes": self.mid_writes,
            "deep_writes": self.deep_writes,
            "tension_holds": self.tension_holds,
            "tension_resolved": self.tension_resolved,
            "tension_expired": self.tension_expired,
            "pending_tension": len(self._tension_queue),
            "fingerprints_archived": len(self._seen_fingerprints),
            "crossing_paths": self.path_gate.total_paths(),
            "avg_novelty": self.plateau_detector.avg_novelty(),
            "plateau_stalled": self.plateau_stalled,
        }


# =============================================================================
# Geometry Fidelity Scorer
# Replaces composite_similarity as primary training signal.
# Measures whether Aurora's output carries the same comparison geometry
# as the truth â not whether she used the same words.
# =============================================================================

class GeometryFidelityScorer:
    """
    Measures fidelity between Aurora's output geometry and the truth geometry.

    This is the physics-grounded replacement for string similarity scoring.
    The question is not "did Aurora use the same words?" but "did Aurora's
    output make the same relational comparison the truth was making?"

    Fidelity = weighted geometric distance between the two axis profiles,
    adjusted for relational pattern overlap and axis depth alignment.

    Still includes a surface similarity component (words DO carry geometry)
    but it is no longer the primary signal.
    """

    def __init__(self, extractor: GeometryExtractor):
        self.extractor = extractor

    def score(self, generated: str, truth: str,
              seen_fingerprints: Optional[Set[str]] = None) -> Dict[str, float]:
        """
        Returns a dict with:
          geometry_fidelity  â primary signal (0.0â1.0)
          axis_alignment     â how well axis profiles match
          depth_alignment    â whether constraint depth matches
          surface_similarity â traditional string/vocab overlap (secondary)
          composite          â weighted composite of all signals
        """
        gen = (generated or "").strip()
        tr = (truth or "").strip()

        if not gen and not tr:
            return self._perfect_score()
        if not gen or not tr:
            return self._zero_score()

        gen_geom = self.extractor.extract(gen, seen_fingerprints)
        tr_geom = self.extractor.extract(tr, seen_fingerprints)

        axis_alignment = self._axis_alignment(gen_geom, tr_geom)
        depth_alignment = self._depth_alignment(gen_geom, tr_geom)
        surface_sim = self._surface_similarity(gen, tr)

        # Geometry fidelity: axis alignment weighted by depth
        geometry_fidelity = (
            axis_alignment * 0.65
            + depth_alignment * 0.20
            + surface_sim * 0.15
        )

        # Composite: geometry-first, surface as secondary support signal
        composite = (
            geometry_fidelity * 0.75
            + surface_sim * 0.25
        )

        return {
            "geometry_fidelity": round(geometry_fidelity, 4),
            "axis_alignment": round(axis_alignment, 4),
            "depth_alignment": round(depth_alignment, 4),
            "surface_similarity": round(surface_sim, 4),
            "composite": round(composite, 4),
            "gen_depth": gen_geom.depth.name,
            "truth_depth": tr_geom.depth.name,
            "gen_axes": gen_geom.active_axis_count,
            "truth_axes": tr_geom.active_axis_count,
        }

    def _axis_alignment(self, gen: ComparisonGeometry,
                        tr: ComparisonGeometry) -> float:
        """Cosine-like similarity between axis activation profiles."""
        axes_gen = [gen.x_activation, gen.t_activation, gen.n_activation,
                    gen.b_activation, gen.a_activation]
        axes_tr = [tr.x_activation, tr.t_activation, tr.n_activation,
                   tr.b_activation, tr.a_activation]

        dot = sum(a * b for a, b in zip(axes_gen, axes_tr))
        mag_gen = math.sqrt(sum(v ** 2 for v in axes_gen))
        mag_tr = math.sqrt(sum(v ** 2 for v in axes_tr))

        if mag_gen < 0.01 or mag_tr < 0.01:
            return 0.0
        return max(0.0, min(1.0, dot / (mag_gen * mag_tr)))

    def _depth_alignment(self, gen: ComparisonGeometry,
                         tr: ComparisonGeometry) -> float:
        """
        Depth alignment: does Aurora's output operate at the same constraint
        depth as the truth? Penalizes shallow responses to deep truth.
        """
        depth_order = {
            StratigraphicDepth.SURFACE: 1,
            StratigraphicDepth.MID: 2,
            StratigraphicDepth.DEEP: 3,
            StratigraphicDepth.GEOLOGICAL: 4,
        }
        gen_d = depth_order[gen.depth]
        tr_d = depth_order[tr.depth]
        if gen_d == tr_d:
            return 1.0
        diff = abs(gen_d - tr_d)
        # Depth mismatch penalty â worse when Aurora is shallower than truth
        if gen_d < tr_d:
            return max(0.0, 1.0 - diff * 0.35)  # Shallower = bigger penalty
        else:
            return max(0.0, 1.0 - diff * 0.20)  # Deeper = smaller penalty

    def _surface_similarity(self, gen: str, tr: str) -> float:
        """
        Surface string + vocabulary similarity (secondary signal).
        60/40 split: sequence match + vocabulary overlap.
        """
        gen_l = gen.lower()
        tr_l = tr.lower()
        seq = SequenceMatcher(None, gen_l, tr_l).ratio()
        words_gen = set(gen_l.split())
        words_tr = set(tr_l.split())
        if not words_gen and not words_tr:
            return 1.0
        if not words_gen or not words_tr:
            return 0.0
        intersection = words_gen & words_tr
        union = words_gen | words_tr
        voc = len(intersection) / len(union)
        return seq * 0.6 + voc * 0.4

    def _perfect_score(self) -> Dict[str, float]:
        return {"geometry_fidelity": 1.0, "axis_alignment": 1.0,
                "depth_alignment": 1.0, "surface_similarity": 1.0,
                "composite": 1.0, "gen_depth": "SURFACE",
                "truth_depth": "SURFACE", "gen_axes": 0, "truth_axes": 0}

    def _zero_score(self) -> Dict[str, float]:
        return {"geometry_fidelity": 0.0, "axis_alignment": 0.0,
                "depth_alignment": 0.0, "surface_similarity": 0.0,
                "composite": 0.0, "gen_depth": "SURFACE",
                "truth_depth": "SURFACE", "gen_axes": 0, "truth_axes": 0}


def artifact_ratio(text: str) -> float:
    """Symbol/garbage density."""
    if not text:
        return 0.0
    non = sum(1 for ch in text if not (ch.isalnum() or ch.isspace()))
    return non / max(len(text), 1)


# =============================================================================
# Coherence Gate (retained â now uses geometry fidelity as primary input)
# =============================================================================

class CoherenceGate:
    """
    Rolling coherence gate. Now gated on geometry fidelity (composite)
    rather than raw string similarity. Unlocks meaning/emotion adjustments
    only after stable geometric fidelity is established.
    """

    def __init__(self, window: int = 200, unlock_avg: float = 0.62,
                 unlock_min: float = 0.45):
        self.window = window
        self.unlock_avg = unlock_avg
        self.unlock_min = unlock_min
        self.scores: deque = deque(maxlen=window)

    def update(self, score: float) -> None:
        self.scores.append(float(score))

    def avg(self) -> float:
        return (sum(self.scores) / len(self.scores)) if self.scores else 0.0

    def min_recent(self) -> float:
        return min(self.scores) if self.scores else 0.0

    def unlocked(self) -> bool:
        if len(self.scores) < max(25, self.window // 4):
            return False
        return (self.avg() >= self.unlock_avg
                and self.min_recent() >= self.unlock_min)


# =============================================================================
# DPME Comparison + Adjustment (geometry-fidelity governed)
# =============================================================================

def dpme_adjust_from_geometry(
    systems: Dict[str, Any],
    fidelity_result: Dict[str, float],
    truth_geom: ComparisonGeometry,
    gate: CoherenceGate,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Physics-governed DPME adjustment.

    Adjustments are now driven by geometry fidelity and the truth geometry's
    constraint profile â not raw string similarity. The truth geometry tells
    us WHICH axes need energy reinforcement. The fidelity score tells us HOW
    MUCH adjustment is needed.

    Key principle: energy is routed to the axes that the truth geometry is
    most expressing, weighted by the mismatch at those axes.
    """
    consciousness = systems["consciousness"]
    dpme = consciousness.dpme

    composite = fidelity_result["composite"]
    axis_alignment = fidelity_result["axis_alignment"]
    depth_alignment = fidelity_result["depth_alignment"]
    art = artifact_ratio
    mismatch = 1.0 - composite
    art_ratio = artifact_ratio(str(fidelity_result.get("gen_depth", "")))

    unlocked = gate.unlocked() if gate is not None else False

    # Determine which axes the truth geometry is most expressing
    # â route energy to those facets
    dominant_axes = []
    if truth_geom.x_activation > 0.4:
        dominant_axes.append("cat_processing")   # X-axis â existence/grounding
    if truth_geom.t_activation > 0.4:
        dominant_axes.append("cat_memory")       # T-axis â temporal continuity
    if truth_geom.n_activation > 0.4:
        dominant_axes.append("cat_emotional")    # N-axis â energetic pressure
    if truth_geom.b_activation > 0.4:
        dominant_axes.append("cat_processing")   # B-axis â definition/reasoning
    if truth_geom.a_activation > 0.4:
        dominant_axes.append("cat_creative")     # A-axis â agency/expression

    adjustments = []
    intention = f"geometry-fidelity DPME: composite={composite:.3f} " \
                f"axis={axis_alignment:.3f} depth={depth_alignment:.3f}"

    if not unlocked:
        # Pre-coherence: reinforce structural axes, suppress expressive axes
        if mismatch > 0.70:
            adjustments.append(
                dpme.adjust("der", "cat_processing", 0.22, intention))
            adjustments.append(
                dpme.adjust("der", "cat_memory", 0.16, intention))
            adjustments.append(
                dpme.adjust("der", "presence", 0.08,
                            "stabilize expression channel"))
        elif mismatch > 0.45:
            adjustments.append(
                dpme.adjust("der", "cat_processing", 0.14, intention))
            adjustments.append(
                dpme.adjust("der", "cat_memory", 0.10, intention))
            adjustments.append(
                dpme.adjust("der", "presence", 0.05,
                            "stabilize expression channel"))
        elif mismatch > 0.25:
            adjustments.append(
                dpme.adjust("der", "cat_processing", 0.08, intention))
            adjustments.append(
                dpme.adjust("der", "cat_memory", 0.04, intention))

        # Suppress expressive axes until coherence stabilizes
        if mismatch > 0.35:
            adjustments.append(dpme.adjust(
                "der", "cat_emotional", -0.04,
                "suppress emotion until geometric coherence stabilizes"))
            adjustments.append(dpme.adjust(
                "der", "cat_creative", -0.05,
                "suppress creativity until geometric coherence stabilizes"))

    else:
        # Post-coherence: axis-targeted energy routing
        intention2 = (f"coherence established â route energy to truth geometry "
                      f"axes: {dominant_axes}")

        # Route to dominant axes from truth geometry
        for facet in set(dominant_axes):
            scale = 0.05 if mismatch < 0.3 else (0.10 if mismatch < 0.5 else 0.14)
            adjustments.append(dpme.adjust("der", facet, scale, intention2))

        # Depth mismatch: boost memory if Aurora is operating too shallow
        if depth_alignment < 0.6:
            adjustments.append(dpme.adjust(
                "der", "cat_memory", 0.08,
                "depth mismatch â reinforce temporal-constraint depth"))

        # Presence stabilization
        adjustments.append(dpme.adjust(
            "der", "presence", 0.02,
            "maintain stability while deepening geometry"))

        # If axis alignment is good but depth is off â emotional integration
        if axis_alignment > 0.65 and depth_alignment > 0.7 and mismatch < 0.3:
            adjustments.append(dpme.adjust(
                "der", "cat_emotional", 0.03,
                "geometry aligned â allow meaning integration"))

    adjustments = [a for a in adjustments if a is not None]
    for adj in adjustments:
        matched = composite >= (1.0 - mismatch)
        dpme.evaluate_adjustment(adj, quality=composite, matched=matched)

    if dpme.needs_correction():
        dpme.auto_correct()

    if verbose:
        phase = "UNLOCKED" if unlocked else "LOCKED"
        avg = gate.avg() if gate else 0.0
        mn = gate.min_recent() if gate else 0.0
        print(f"  [DPME] phase={phase} composite={composite:.3f} "
              f"axis={axis_alignment:.3f} depth={depth_alignment:.3f} "
              f"avg={avg:.3f} min={mn:.3f} adj={len(adjustments)} "
              f"truth_axes={truth_geom.active_axis_count} "
              f"dominant={dominant_axes}")

    return {
        "composite": composite,
        "geometry_fidelity": fidelity_result["geometry_fidelity"],
        "axis_alignment": axis_alignment,
        "depth_alignment": depth_alignment,
        "mismatch": mismatch,
        "adjustments": len(adjustments),
        "improved": composite >= (gate.avg() if gate and gate.scores else 0.5),
        "phase_unlocked": unlocked,
        "coherence_avg": gate.avg() if gate else 0.0,
        "coherence_min": gate.min_recent() if gate else 0.0,
    }


# =============================================================================
# DER â OETS Axis Pressure Bridge
# Keeps OETS relational comparisons grounded in Aurora's real constraint state.
# Without this, OETS uses flat {X:0.5 ...} defaults and comparisons are generic.
# =============================================================================

_DER_CAT_TO_AXIS = {
    "vitality":   "X",   # existence / grounding
    "memory":     "T",   # temporal continuity
    "emotional":  "N",   # energy / tension
    "processing": "B",   # boundary / definition
    "creative":   "A",   # agency / expression
}

def sync_der_to_oets(systems: Dict[str, Any]) -> Dict[str, float]:
    """
    Read DER's current category energies, map to X/T/N/B/A, and push them
    onto perception._pressure_vec so OETS comparisons use Aurora's real
    constraint topology instead of flat 0.5 defaults.

    Returns the pressure dict that was applied.
    """
    dimensional = systems.get("dimensional")
    perception  = systems.get("perception")
    if dimensional is None or perception is None:
        return {}

    # Try the rich pressure vec first (needs genealogy symbols)
    pv = None
    try:
        pv = dimensional._current_pressure_vec()
        if pv is not None:
            pressures = pv.to_dict() if hasattr(pv, "to_dict") else dict(pv)
            if pressures and all(k in pressures for k in ("X", "T", "N", "B", "A")):
                if "curriculum_tension" in systems:
                    systems["curriculum_tension"].apply_to_pressures(pressures)
        perception._pressure_vec = pressures
        if hasattr(perception, "oets") and perception.oets is not None:
            perception.oets._active_pressures = dict(pressures)
        return pressures
    except Exception:
        pass

    # Fallback: read category_energy directly from DER and normalise
    try:
        der = dimensional.der
        raw = {ax: der.category_energy(cat)
               for cat, ax in _DER_CAT_TO_AXIS.items()}
        total = sum(raw.values()) or 1.0
        # Keep values in [0.05, 0.95] so nothing is fully silenced
        pressures = {ax: max(0.05, min(0.95, v / total * len(raw) * 0.5))
                     for ax, v in raw.items()}
        if "curriculum_tension" in systems:
            systems["curriculum_tension"].apply_to_pressures(pressures)
        perception._pressure_vec = pressures
        if hasattr(perception, "oets") and perception.oets is not None:
            perception.oets._active_pressures = dict(pressures)
        return pressures
    except Exception:
        pass

    return {}


# =============================================================================
# Full-Stack Learning Hooks (physics-governed versions)
# =============================================================================

def heartbeat(systems: Dict[str, Any]):
    """One consciousness heartbeat. Entropy erodes coherence, DER disperses."""
    systems["consciousness"].tick()
    sync_der_to_oets(systems)   # keep OETS grounded after every energy tick


def physics_absorb_truth(
    systems: Dict[str, Any],
    absorption_field: AbsorptionField,
    truth_text: str,
    context_hash: str = "",
    tone: str = "neutral",
) -> ComparisonGeometry:
    """
    Physics-governed truth absorption.

    Routes truth text through the full absorption chain:
      1. GeometryExtractor reconstructs comparison geometry
      2. AbsorptionField assigns stratigraphic depth + manages tension
      3. Depth-appropriate routing to L5 composer
      4. TwoFactorPathGate updated with this crossing

    The L5 composer only receives text that has cleared geometry extraction
    at MID depth or above â surface-stratum items are vocabulary seeds only.
    """
    if not truth_text or len(truth_text.split()) < 3:
        return ComparisonGeometry()

    sync_der_to_oets(systems)   # ground OETS before truth absorption
    geom = absorption_field.absorb(truth_text, context_hash)
    perception = systems["perception"]

    # Vocabulary gate â always applies regardless of depth
    words = truth_text.split()
    clean_words = [w for w in words if is_valid_word(
        w.strip(".,!?;:'\"()-[]{}").lower())]
    clean_text = ' '.join(clean_words)

    if len(clean_text.split()) >= 3:
        if geom.depth in (StratigraphicDepth.MID,
                          StratigraphicDepth.DEEP,
                          StratigraphicDepth.GEOLOGICAL):
            # MID and above: full template absorption
            perception.composer.absorb(clean_text, tone)
        else:
            # SURFACE only: vocabulary seeding, no template absorption
            # (tension items and low-significance items don't template yet)
            # FIX-A010: words were stamped role="noun", meaning="absorbed"
            # with no valence — flattening every absorbed word into noun
            # slots and leaving it invisible to noncomp-driven selection.
            # Use the perception layer's own inference instead.
            from aurora_expression_perception import (
                infer_word_role,
                infer_word_valence,
            )
            for w in clean_words[:10]:  # Seed lexicon but don't template
                perception.lexicon.add_word(
                    w,
                    meaning=f"corpus:{w}",
                    role=infer_word_role(w),
                    valence=infer_word_valence(w, tone),
                    lineage="corpus",
                )
        # FIX-A009: persist vocabulary growth — without this every corpus
        # run's lexical gains evaporated at process exit.
        try:
            perception.lexicon.save()
        except Exception:
            pass

    return geom


def evolve_identity(systems: Dict[str, Any],
                    quality: float,
                    geom: Optional[ComparisonGeometry] = None,
                    mode=None):
    """
    Physics-governed identity evolution.
    Only called after DEEP or GEOLOGICAL depth absorption events â
    surface and mid absorptions don't trigger identity evolution.
    """
    if mode is None:
        from foundational_contract import ExistenceMode
        mode = ExistenceMode.BOUNDED

    # Build relic with geometry-informed emotional bias
    trust = 0.3 + quality * 0.4
    curiosity = 0.4 + (1.0 - quality) * 0.3

    manifold_pos = (quality, 0.5, 0.0, 0.0, 0.0)
    if geom is not None:
        # Map axis activations to manifold position
        manifold_pos = (
            geom.x_activation,
            geom.t_activation,
            geom.n_activation,
            geom.b_activation,
            geom.a_activation,
        )
        # N-axis â emotional weight
        trust = 0.3 + quality * 0.4 + geom.n_activation * 0.1
        curiosity = 0.4 + (1.0 - quality) * 0.3 + geom.b_activation * 0.1

    relics = [{
        'theme': 'corpus_geometry_absorption',
        'stability': min(quality, 0.9),
        'seed_ids': [f"corpus_{int(time.time()*1000)}"],
        'emotional_bias': {
            'trust': min(1.0, trust),
            'curiosity': min(1.0, curiosity),
        },
        'manifold_position': manifold_pos,
    }]

    pillar_scores = {
        'interaction': quality,
        'growth': 0.5 + quality * 0.3,
    }
    systems["identity"].process_episode(
        {'success_rate': quality, 'lessons_learned': []},
        relics, pillar_scores, mode,
    )


def evolve_voice(systems: Dict[str, Any], quality: float, matched: bool,
                 geom: Optional[ComparisonGeometry] = None):
    """Physics-governed voice evolution."""
    perception = systems["perception"]
    feedback = {
        'user_engaged': quality,
        'comfort': 0.5 + quality * 0.3,
    }
    if matched:
        feedback['resonance'] = 0.6 + quality * 0.2
    if geom is not None and geom.a_activation > 0.5:
        feedback['expressiveness'] = geom.a_activation
    perception.voice.evolve(feedback)


def consolidate(systems: Dict[str, Any]):
    """L5 impression distillation + OETS internal consolidation."""
    from foundational_contract import ExistenceMode
    systems["perception"].consolidate(min_mode=ExistenceMode.BOUNDED)
    oets = getattr(systems["perception"], 'oets', None)
    if oets:
        oets.consolidate()


def corpus_study_cycle(systems: Dict[str, Any], verbose: bool = False) -> None:
    """
    Aurora's in-training research pass.

    Flushes the study queue that the observer builds during deep/geological
    absorptions, queues those concepts into OETS's research engine, and runs
    one study cycle so Aurora actively builds relational maps around concepts
    she's encountering — not just absorbing them passively.

    Uses internal OETS graph traversal only (no network) so it works on a
    mobile hotspot.  The study cycle:
        1. Pops up to 20 deep-encountered concepts from systems["_study_queue"]
        2. Queues them as ResearchRequests (reason="corpus_deep_encounter")
        3. Calls oets.run_study_cycle() which:
           - Discovers 1-hop + 2-hop OETS neighbors
           - Infers synonym/antonym/hypernym candidates
           - Adds new relational edges to the web
           - Logs a StudyEvent
    """
    oets = getattr(systems.get("perception"), 'oets', None)
    if oets is None:
        return

    study_queue: List[str] = systems.get("_study_queue") or []
    if not study_queue:
        return

    # Drain up to 20 per consolidation interval
    batch, remainder = study_queue[:20], study_queue[20:]
    systems["_study_queue"] = remainder

    try:
        from aurora_internal.aurora_ontological_scaffolding import ResearchRequest
        import uuid as _uuid
        requests = [
            ResearchRequest(
                request_id=str(_uuid.uuid4()),
                word=w,
                priority=0.85,
                reason="corpus_deep_encounter",
            )
            for w in batch
            if w in (getattr(oets, "web", None) and oets.web.nodes or {})
        ]
        if requests and hasattr(oets, "research") and hasattr(oets.research, "queue_research"):
            oets.research.queue_research(requests)
            result = oets.run_study_cycle(trigger_reason="corpus_learning")
            if verbose:
                studied = result.get("researched", 0)
                rels    = result.get("results", [])
                new_rels = sum(r.get("relations_added", 0) for r in rels)
                print(f"  [STUDY] Researched {studied} concept(s) | "
                      f"+{new_rels} relations | "
                      f"queued={len(remainder)} remaining")
    except Exception as _se:
        if verbose:
            print(f"  [STUDY] Study cycle error: {_se}")


def simulation_burst(systems: Dict[str, Any],
                     episodes: int = 4,
                     verbose: bool = True):
    """L7 simulation training burst â avatars + inception + wisdom shards."""
    from foundational_contract import ExistenceMode
    result = systems["simulation"].run_epoch(
        episodes_per_epoch=episodes,
        turns_per_episode=3,
        mode=ExistenceMode.AGENTIC,
    )
    if verbose:
        fitness = result.get('avg_fitness', 0)
        shards = result.get('learner_shards', 0)
        print(f"  [SIM] burst: fitness={fitness:.3f} shards={shards}")
    return result


def evolve_chain(systems: Dict[str, Any],
                 ticks: int = 50,
                 truth_geom: Optional[ComparisonGeometry] = None,
                 verbose: bool = False):
    """
    Tick the EvolutionaryChamber with geometry-informed ActionTrace.
    Maps truth geometry's dominant axes to the constraint labels rather than
    using hardcoded defaults.
    """
    chamber = systems.get("chamber")
    if chamber is None:
        return

    try:
        from aurora_internal.aurora_evolution_chamber import ActionTrace
    except ImportError:
        return

    # Build constraint set from truth geometry if available
    constraints_used = {"boundary", "temporal"}  # Defaults
    if truth_geom is not None:
        if truth_geom.a_activation > 0.4:
            constraints_used.add("agency")
        if truth_geom.x_activation > 0.4:
            constraints_used.add("existence")
        if truth_geom.n_activation > 0.4:
            constraints_used.add("energy")
        if truth_geom.t_activation > 0.4:
            constraints_used.add("temporal")
        if truth_geom.b_activation > 0.4:
            constraints_used.add("boundary")

    action = ActionTrace(
        name="corpus_geometry_absorption",
        constraints_used=frozenset(constraints_used),
        meta={"source": "corpus_evolve",
              "depth": truth_geom.depth.name if truth_geom else "SURFACE"},
    )

    new_fossils = 0
    for _ in range(ticks):
        event = chamber.tick(action=action)
        if event is not None:
            new_fossils += 1

    chamber._genealogy.flush_files()

    if verbose:
        cr = chamber._genealogy.chain_report()
        print(f"  [CHAIN] ticks={ticks} fossils={new_fossils} "
              f"total_links={cr['total_links']} "
              f"outlet_fraction={cr['outlet_push_fraction']:.3f} "
              f"constraints={constraints_used}")


# =============================================================================
# Learning Cadence
# =============================================================================


class CurriculumTension:
    """
    Represents internal tension generated by curriculum failure.
    Wired into the N-axis (Energy) to drive B-axis (Boundary) tightening.
    """
    def __init__(self):
        self.tension_level: float = 0.0  # 0.0 to 1.0
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0

    def record_failure(self, fidelity: float):
        self.failure_count += 1
        # Tension = 1.0 - fidelity, weighted by repeat failures
        new_tension = (1.0 - fidelity) * (1.0 + (self.failure_count * 0.2))
        self.tension_level = min(1.0, self.tension_level + new_tension)
        self.last_failure_time = time.time()

    def decay(self, message_count: int = 1):
        # Tension decays as she studies (OBSERVER mode)
        # It takes ~500 messages to fully clear a major failure
        self.tension_level = max(0.0, self.tension_level - (message_count * 0.002))

    def apply_to_pressures(self, pressures: dict):
        """Wired feedback: Tension increases N-axis and B-axis pressure."""
        if self.tension_level <= 0:
            return
        # N-axis (Energy): URGENCY to resolve the mismatch
        pressures["N"] = min(0.95, pressures.get("N", 0.5) + (self.tension_level * 0.3))
        # B-axis (Boundary): TIGHTEN definition to prevent future error
        pressures["B"] = min(0.95, pressures.get("B", 0.5) + (self.tension_level * 0.4))
        # A-axis (Agency): REDUCE expressive confidence while tense
        pressures["A"] = max(0.05, pressures.get("A", 0.5) - (self.tension_level * 0.2))


class LearningCadence:
    """
    Orchestrates when each learning pathway fires.
    Identity evolution fires on DEEP/GEOLOGICAL events only.
    Plateau detection triggers curriculum stall logging.

    Defaults calibrated for technical corpora (~5k-75k messages):
      heartbeat:     every 5 messages
      identity:      every 50 messages (DEEP/GEOLOGICAL events only)
      voice:         every 50 messages
      consolidation: every 300 messages
      simulation:    every 500 messages
      save:          every 1000 messages
    """

    def __init__(self,
                 heartbeat_every: int = 5,
                 identity_every: int = 50,
                 voice_every: int = 50,
                 consolidation_every: int = 300,
                 simulation_every: int = 500,
                 save_every: int = 1000,
                 evolve_every: int = 100):
        self.heartbeat_every = heartbeat_every
        self.identity_every = identity_every
        self.voice_every = voice_every
        self.consolidation_every = consolidation_every
        self.simulation_every = simulation_every
        self.save_every = save_every
        self.evolve_every = evolve_every

    def should_heartbeat(self, n: int) -> bool:
        return self.heartbeat_every > 0 and n % self.heartbeat_every == 0

    def should_identity(self, n: int) -> bool:
        return self.identity_every > 0 and n % self.identity_every == 0

    def should_voice(self, n: int) -> bool:
        return self.voice_every > 0 and n % self.voice_every == 0

    def should_consolidate(self, n: int) -> bool:
        return self.consolidation_every > 0 and n % self.consolidation_every == 0

    def should_simulate(self, n: int) -> bool:
        return self.simulation_every > 0 and n % self.simulation_every == 0

    def should_save(self, n: int) -> bool:
        return self.save_every > 0 and n % self.save_every == 0

    def should_evolve(self, n: int) -> bool:
        return self.evolve_every > 0 and n % self.evolve_every == 0


# =============================================================================
# Corpus Ingestion â Physics-Grounded
# =============================================================================

def run_corpus_ingestion(
    systems: Dict[str, Any],
    corpus_path: str,
    cadence: Optional[LearningCadence] = None,
    passes: str = "triple",
    verbose: bool = True,
    dpme_verbose: bool = False,
    coherence_window: int = 200,
    unlock_avg: float = 0.62,
    unlock_min: float = 0.45,
    warmup_epochs: int = 3,
):
    aurora = systems["aurora"]
    StreamType = systems["StreamType"]
    ExistenceMode = systems["ExistenceMode"]

    if cadence is None:
        cadence = LearningCadence()

    corpus_path = os.path.expanduser(corpus_path)
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    # Initialize physics absorption field and geometry scorer
    absorption_field = AbsorptionField()
    fidelity_scorer = GeometryFidelityScorer(absorption_field.extractor)
    curriculum_tension = CurriculumTension()
    systems["curriculum_tension"] = curriculum_tension

    # ── FIXED-PATH WELD (FIX-A008/A011/A012) ────────────────────────────────
    # Every corpus ingestion — no matter who invokes it — now runs the same
    # learning write-paths as the live pipeline:
    #   _pulse        : TrainingPulse field energization (daemon cadence,
    #                   time-compressed) so attention/tension EMAs climb and
    #                   ignition can form during training.
    #   _grammar_weld : observe_exchange() on every pair, so motif fitness
    #                   accumulates toward promotion instead of staying dead.
    # Both are best-effort: a missing subsystem degrades gracefully and the
    # ingestion continues exactly as before.
    _pulse = None
    try:
        from aurora_training_pulse import TrainingPulse
        _pulse = TrainingPulse(systems)
        if verbose:
            print("  [CORPUS] Fixed-path weld active: TrainingPulse + grammar observation")
    except Exception:
        _pulse = None

    _grammar_weld = systems.get("grammar_engine")
    if _grammar_weld is not None and not hasattr(_grammar_weld, "observe_exchange"):
        _grammar_weld = None

    def _weld_observe(user_t: str, aurora_t: str, success: bool, clarity: float):
        """Feed one exchange into the motif lineage (FIX-A008 write path)."""
        if _grammar_weld is None or not aurora_t:
            return
        try:
            _grammar_weld.observe_exchange(
                str(user_t or ""), str(aurora_t), success=bool(success),
                clarity=max(0.0, min(1.0, float(clarity))),
            )
        except Exception:
            pass

    def _weld_pulse(text: str, cycles: int = 2, intensity: float = 0.6):
        """Energize the field around an exchange (FIX-A011 write path)."""
        if _pulse is None:
            return
        try:
            _pulse.energize(str(text or ""), "", cycles=cycles, intensity=intensity)
        except Exception:
            pass
    # ── end weld ─────────────────────────────────────────────────────────────

    if verbose:
        print("=" * 70)
        print("  [CORPUS] Physics-Grounded Absorption (geometry-first)")
        print(f"  [CORPUS] File: {corpus_path}")
        print(f"  [CORPUS] passes={passes}")
        print(f"  [CORPUS] coherence_window={coherence_window} "
              f"unlock_avg={unlock_avg} unlock_min={unlock_min}")
        print(f"  [CORPUS] Cadence: heartbeat/{cadence.heartbeat_every} "
              f"identity/{cadence.identity_every} voice/{cadence.voice_every} "
              f"consolidate/{cadence.consolidation_every} "
              f"simulate/{cadence.simulation_every} "
              f"save/{cadence.save_every}")
        print("=" * 70)

    if warmup_epochs > 0:
        if verbose:
            print(f"\n  [WARMUP] Running {warmup_epochs} simulation epochs")
        for _ in range(warmup_epochs):
            simulation_burst(systems, episodes=8, verbose=verbose)
        if verbose:
            vocab = systems["perception"].lexicon.size
            print(f"  [WARMUP] Complete. Vocabulary: {vocab}\n")

    # Load corpus
    if verbose:
        print(f"  [CORPUS] Initializing universal stream for: {corpus_path}")

    stream: List[Tuple[str, str]] = []
    dropped_count = 0

    for role_or_user, text_or_assistant in _get_corpus_iterator(corpus_path):
        clean_u = sanitize_corpus_text(role_or_user)
        if clean_u and len(clean_u.split()) >= 3:
            stream.append(("user", clean_u))
        else:
            dropped_count += 1

        clean_a = sanitize_corpus_text(text_or_assistant)
        if clean_a and len(clean_a.split()) >= 3:
            stream.append(("assistant", clean_a))
        else:
            dropped_count += 1

    if verbose:
        print(f"  [CORPUS] Extracted {len(stream)} messages "
              f"(dropped {dropped_count} invalid/code fragments)\n")

    if not stream:
        if verbose:
            print("  [CORPUS] No usable messages found. Aborting.\n")
        return

    # Sync DER axis pressures to OETS before each perception call
    # so relational comparisons use Aurora's real constraint topology.
    sync_der_to_oets(systems)

    # Core routing
    _crystal = systems.get("sensory_crystal")
    _vseed_cache = systems.get("vision_seed_cache") or {}
    # Import builder here so it's available inside closures without re-importing
    try:
        from aurora_internal.aurora_sensory_crystal import build_audio_20d_from_der as _build_a20
    except ImportError:
        _build_a20 = None
    _STOPWORDS = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "was",
        "had", "has", "have", "this", "that", "with", "from", "they", "will",
        "been", "were", "their", "what", "when", "which", "your", "there",
        "more", "also", "just", "into", "than", "then", "some", "its",
        "about", "would", "could", "should", "like", "very", "only", "even",
        "any", "our", "how", "who", "each", "does", "did", "get", "his",
        "her", "him", "she", "him", "they", "them", "those", "these",
    }

    def _feed_crystal_semantic(text: str, weight: float = 1.0) -> None:
        """Extract content words and register semantic modality in crystal."""
        if not _crystal:
            return
        words = text.lower().split()
        for raw in words:
            w = raw.strip(".,!?;:'\"()-[]{}«»")
            if len(w) >= 4 and w.isalpha() and w not in _STOPWORDS:
                _crystal.observe_semantic(w, weight=weight)

    def _feed_crystal_visual_and_audio(
            text: str, weight: float = 1.0, depth_name: str = "SURFACE") -> None:
        """Feed visual (vision seeds) and audio (DER synthesis) into crystal."""
        if not _crystal:
            return
        words = text.lower().split()
        content_words = []
        for raw in words:
            w = raw.strip(".,!?;:'\"()-[]{}«»")
            if len(w) >= 4 and w.isalpha() and w not in _STOPWORDS:
                content_words.append(w)

        # --- Visual: for each content word that has a vision seed image ---
        for w in content_words:
            v57 = _vseed_cache.get(w)
            if v57 is None:
                continue
            try:
                _crystal.observe_frame(
                    [0.0] * 20, v57,
                    session_id=f"corpus:vis:{w}",
                    visual_conf=weight,
                )
                _crystal._register_concept_visual(w, f"seed:{w}")
            except Exception:
                pass

        # --- Audio: synthesize from DER axis pressures (once per message) ---
        # Only for MID+ depth — surface is too shallow to carry acoustic meaning
        if _build_a20 and depth_name in ("MID", "DEEP", "GEOLOGICAL"):
            _axes = getattr(systems.get("perception"), "_pressure_vec", None) or {}
            if not _axes:
                # Fall back to a neutral profile so audio facets still get signal
                _axes = {"X": 0.4, "T": 0.4, "N": 0.35, "B": 0.4, "A": 0.3}
            try:
                a20 = _build_a20(
                    float(_axes.get("X", 0.4)),
                    float(_axes.get("T", 0.4)),
                    float(_axes.get("N", 0.35)),
                    float(_axes.get("B", 0.4)),
                    float(_axes.get("A", 0.3)),
                )
                # One audio frame per message to exercise audio facets
                _crystal.observe_frame(
                    a20, [0.0] * 57,
                    session_id=f"corpus:aud",
                    audio_conf=weight * 0.65,  # DER-synthesised = lower confidence
                )
                # Register audio modality for all content words in this message
                for w in content_words:
                    _crystal._register_concept_audio(w, f"der:corpus")
            except Exception:
                pass

    def witness(tag: str, content: str, source: str,
                context_hash: str = ""):
        """
        Witness a corpus message.
        Routes through physics absorption field before gateway receive.
        One bad message must never abort the entire training run.
        """
        if not content or len(content.split()) < 3:
            return None, ComparisonGeometry()
        try:
            geom = absorption_field.absorb(content, context_hash)
            sync_der_to_oets(systems)   # ground OETS in current constraint state
            # Weight deeper absorptions more strongly in the concept registry
            _depth_name = getattr(geom.depth, "name", "SURFACE")
            _sem_weight = {
                "SURFACE": 0.4, "MID": 0.7, "DEEP": 0.9, "GEOLOGICAL": 1.0
            }.get(_depth_name, 0.4)
            _feed_crystal_semantic(content, weight=_sem_weight)
            _feed_crystal_visual_and_audio(content, weight=_sem_weight,
                                           depth_name=_depth_name)
            # Queue deep/geological concepts for OETS study cycle
            if _depth_name in ("DEEP", "GEOLOGICAL"):
                _sq = systems.setdefault("_study_queue", [])
                _seen_sq = set(_sq)
                for _raw in content.lower().split():
                    _sw = _raw.strip(".,!?;:'\"()-[]{}«»")
                    if (len(_sw) >= 4 and _sw.isalpha()
                            and _sw not in _STOPWORDS
                            and _sw not in _seen_sq
                            and len(_sq) < 500):
                        _sq.append(_sw)
                        _seen_sq.add(_sw)
            result = aurora.gateway.receive(
                content=f"[{tag}] {content}",
                stream_type=StreamType.KNOWLEDGE_FEED,
                source=source,
                mode=ExistenceMode.BOUNDED,
            )
            return result, geom
        except Exception as _we:
            if verbose:
                print(f"  [WITNESS] skipped ({_we.__class__.__name__}: {_we})")
            return None, ComparisonGeometry()

    def generate_reply(prompt_text: str, source: str):
        if not prompt_text or len(prompt_text.split()) < 3:
            return None
        try:
            return aurora.gateway.receive(
                content=prompt_text,
                stream_type=StreamType.USER_INPUT,
                source=source,
                mode=ExistenceMode.BOUNDED,
            )
        except Exception as _ge:
            if verbose:
                print(f"  [REPLY] skipped ({_ge.__class__.__name__}: {_ge})")
            return None

    _checkpoint = systems.get("checkpoint")

    # Last truth geometry for cadence propagation
    _last_geom: ComparisonGeometry = ComparisonGeometry()

    def run_cadence(counter: int, quality: float = 0.5,
                    matched: bool = False,
                    geom: Optional[ComparisonGeometry] = None):
        nonlocal _last_geom
        if geom is not None:
            _last_geom = geom

        if cadence.should_heartbeat(counter):
            heartbeat(systems)

        # Identity evolution: only for DEEP/GEOLOGICAL depth absorptions
        if cadence.should_identity(counter):
            if _last_geom.depth in (StratigraphicDepth.DEEP,
                                    StratigraphicDepth.GEOLOGICAL):
                evolve_identity(systems, quality,
                                geom=_last_geom,
                                mode=ExistenceMode.BOUNDED)

        if cadence.should_voice(counter):
            evolve_voice(systems, quality, matched, geom=_last_geom)

        if cadence.should_consolidate(counter):
            consolidate(systems)
            corpus_study_cycle(systems, verbose=verbose)
            # Tick concept promotions so semantic+audio pairs advance to composite
            # and composite+visual pairs advance to higher_order each cycle.
            if systems.get("sensory_crystal"):
                try:
                    _promoted = systems["sensory_crystal"].tick_concept_promotions()
                    if _promoted and verbose:
                        print(f"  [CRYSTAL] Promoted {len(_promoted)} concept(s) "
                              f"this cycle")
                except Exception:
                    pass
            if verbose:
                vocab = systems["perception"].lexicon.size
                gen = systems["identity"].generation
                report = absorption_field.field_report()
                oets_info = ""
                sc_info = ""
                if systems["perception"].oets:
                    oets = systems["perception"].oets
                    oets_info = (f" oets={len(oets.web.nodes)}c/"
                                 f"{len(oets.web.relations)}r")
                if systems.get("sensory_crystal"):
                    _sc_sum = systems["sensory_crystal"].concept_registry_summary()
                    sc_info = (f" | concepts={_sc_sum['total']}"
                               f" {_sc_sum['by_stage']}")
                print(
                    f"  [CONSOLIDATE] at {counter:,} "
                    f"vocab={vocab} gen={gen}{oets_info} | "
                    f"surface={report['surface_writes']} "
                    f"mid={report['mid_writes']} "
                    f"deep={report['deep_writes']} "
                    f"tension={report['pending_tension']} "
                    f"novelty={report['avg_novelty']:.3f}"
                    f"{sc_info}"
                )

        if cadence.should_simulate(counter):
            if verbose:
                print(f"  [SIM] Training burst at message {counter:,}")
            simulation_burst(systems, episodes=4, verbose=verbose)

        if cadence.should_evolve(counter):
            evolve_chain(
                systems, ticks=50,
                truth_geom=_last_geom,
                verbose=verbose
            )

        # Plateau detection ÃÂ¢Ã¢âÂ¬Ã¢â¬Â log stall if detected
        if absorption_field.plateau_stalled and counter % 50 == 0:
            if verbose:
                report = absorption_field.field_report()
                print(
                    f"  [PLATEAU] CURRICULUM_STALL detected at {counter:,} "
                    f"avg_novelty={report['avg_novelty']:.3f} ÃÂ¢Ã¢âÂ¬Ã¢â¬Â "
                    f"consider rotating corpus"
                )
            absorption_field.plateau_detector.reset_stall()

        if cadence.should_save(counter):
            if verbose:
                print(f"  [SAVE] at message {counter:,}")
            aurora.save_state()
            _save_oets(systems, verbose=verbose)
            if systems.get("perception"):
                systems["perception"].save_lexicon()

    # PASS: OBSERVER
    def pass_observer(break_on_stall: bool = False,
                      min_messages: int = 0) -> str:
        if verbose:
            extra = ' + study mandate' if min_messages > 0 else ''
            print(f"  [CORPUS] PASS â OBSERVER "
                  f"(geometry extraction + archive seeding{extra})\n")
        counter = 0
        start_line = 0

        if _checkpoint:
            start_line = _checkpoint.cursor.line_index
            if verbose and start_line > 0:
                print(f"  [CHECKPOINT] Resuming observer from line {start_line}")

        _last_user_obs: str = ""
        for line_idx, (role, content) in enumerate(stream):
            if line_idx < start_line:
                continue
            counter += 1
            ctx_hash = hashlib.md5(content[:32].encode()).hexdigest()[:8]

            # Witness: geometry-governed
            _, geom = witness(role.upper(), content,
                              source="corpus_observer",
                              context_hash=ctx_hash)

            # ── FIXED-PATH WELD: observer pass ──────────────────────────
            # Assistant exemplars are successful structural evidence even
            # in pure absorption mode — feed the motif lineage so observer
            # runs build promotion pressure, and pulse the field on a
            # light cadence so absorption happens in a live manifold.
            if role == "user":
                _last_user_obs = content
            elif role == "assistant" and _last_user_obs:
                _weld_observe(_last_user_obs, content, success=True,
                              clarity=0.65)
            if counter % 8 == 0:
                _weld_pulse(content, cycles=1, intensity=0.55)
            # ── end weld ────────────────────────────────────────────────

            curriculum_tension.decay(1)
            run_cadence(counter, geom=geom)

            if (break_on_stall and counter >= min_messages 
                and absorption_field.plateau_stalled):
                if verbose:
                    print(f"  [PLATEAU] Stall detected at {counter:,}. "
                          f"Transitioning to RESPONDER practice...")
                # Advance checkpoint before returning
                if _checkpoint:
                    _checkpoint.advance(
                        line_index=line_idx,
                        item_hash=ctx_hash,
                        pass_name="observer",
                        file_path=corpus_path,
                    )
                return "STALLED"

            if _checkpoint and counter % 500 == 0:
                _checkpoint.advance(
                    line_index=line_idx,
                    item_hash=ctx_hash,
                    pass_name="observer",
                    file_path=corpus_path,
                )
                if _crystal:
                    try:
                        _crystal.save()
                    except Exception:
                        pass

            if verbose and counter % 500 == 0:
                vocab = systems["perception"].lexicon.size
                facets = len(systems["dimensional"].der.registered_facets)
                report = absorption_field.field_report()
                oets_info = ""
                if systems["perception"].oets:
                    oets = systems["perception"].oets
                    oets_info = (f" oets={len(oets.web.nodes)}c/"
                                 f"{len(oets.web.relations)}r")
                print(
                    f"  [OBSERVER] {counter:,} processed "
                    f"vocab={vocab} facets={facets}{oets_info} | "
                    f"mid={report['mid_writes']} "
                    f"deep={report['deep_writes']} "
                    f"tension={report['pending_tension']} "
                    f"paths={report['crossing_paths']} "
                    f"novelty={report['avg_novelty']:.3f}"
                )

        if verbose:
            report = absorption_field.field_report()
            print(f"  [OBSERVER] Complete. Messages: {counter:,} | "
                  f"Archive: {report['fingerprints_archived']} geometries | "
                  f"Paths: {report['crossing_paths']}\n")

    # PASS: RESPONDER
    def pass_responder(break_on_failure: bool = False) -> str:
        if verbose:
            print("  [CORPUS] PASS â RESPONDER (geometry fidelity + full-stack)\n")


        gate = CoherenceGate(window=coherence_window,
                             unlock_avg=unlock_avg,
                             unlock_min=unlock_min)
        counter = 0
        start_i = 0

        if _checkpoint:
            start_i = _checkpoint.cursor.line_index
            if verbose and start_i > 0:
                print(f"  [CHECKPOINT] Resuming responder from line {start_i}")

        i = start_i
        last_composite: Optional[float] = None

        while i < len(stream) - 1:
            role, content = stream[i]
            next_role, next_content = stream[i + 1]

            if role == "user" and next_role == "assistant":
                counter += 1
                ctx_hash = hashlib.md5(content[:32].encode()).hexdigest()[:8]

                if break_on_failure and counter >= coherence_window:
                    # Only fail if truly lost (not just early-training poor performance)
                    _fail_floor = max(0.15, unlock_min - 0.30)
                    if gate.avg() < _fail_floor:
                        if verbose:
                            print(f"  [CURRICULUM] Poor performance detected "
                                  f"(avg={gate.avg():.3f} < floor={_fail_floor:.3f}). "
                                  f"Forcing back to OBSERVER mode...")
                        if _checkpoint:
                            _checkpoint.advance(
                                line_index=i,
                                item_hash=ctx_hash,
                                pass_name="responder",
                                file_path=corpus_path,
                            )
                        return "FAILED"

                if _checkpoint and counter % 500 == 0:
                    _checkpoint.advance(
                        line_index=i,
                        item_hash=ctx_hash,
                        pass_name="responder",
                        file_path=corpus_path,
                    )

                resp = generate_reply(content, source="corpus_responder")

                witness("ASSISTANT_TRUTH", next_content,
                        source="corpus_responder_truth",
                        context_hash=ctx_hash)

                # Physics-governed truth absorption
                truth_geom = physics_absorb_truth(
                    systems, absorption_field, next_content,
                    context_hash=ctx_hash, tone="neutral"
                )

                # Geometry fidelity scoring (replaces composite_similarity)
                fidelity_result = fidelity_scorer.score(
                    generated=(resp.content if resp else ""),
                    truth=next_content,
                    seen_fingerprints=absorption_field._seen_fingerprints,
                )

                # ── FIXED-PATH WELD: learning write-paths per pair ──────────
                # Field energization (light — heavy pulses every 4th pair to
                # keep throughput) so tension/salience EMAs accumulate.
                if counter % 4 == 0:
                    _weld_pulse(content, cycles=2, intensity=0.6)
                # Truth exemplar → motif lineage as a SUCCESS with clarity
                # from its geometry fidelity context: this is what teaches
                # her the structural shapes inside Sunni's corpora.
                _weld_observe(content, next_content, success=True,
                              clarity=fidelity_result["geometry_fidelity"]
                              if fidelity_result.get("geometry_fidelity") is not None
                              else 0.65)
                # Her own attempt → motif lineage with success gated on the
                # fidelity she actually achieved: closes her self-learning
                # loop so structures that WORK get promoted, ones that fail
                # accumulate demotion pressure.
                if resp and getattr(resp, "content", ""):
                    _gf = float(fidelity_result.get("geometry_fidelity", 0.0) or 0.0)
                    _weld_observe(content, resp.content,
                                  success=_gf >= unlock_min, clarity=_gf)
                # ── end weld ────────────────────────────────────────────────

                # DPME governed by geometry fidelity
                dpme_result = dpme_adjust_from_geometry(
                    systems=systems,
                    fidelity_result=fidelity_result,
                    truth_geom=truth_geom,
                    gate=gate,
                    verbose=dpme_verbose,
                )

                gate.update(dpme_result["composite"])
                last_composite = dpme_result["composite"]

                run_cadence(counter,
                            quality=dpme_result["composite"],
                            matched=dpme_result["improved"],
                            geom=truth_geom)

                if verbose and counter % 100 == 0:
                    snippet = ((resp.content if resp else "") or "")[:80]
                    snippet = snippet.replace("\n", " ")
                    phase = "UNLOCKED" if dpme_result["phase_unlocked"] \
                            else "LOCKED"
                    vocab = systems["perception"].lexicon.size
                    presence = systems["dimensional"].der.presence
                    print(
                        f"  [RESP] {counter:,} | "
                        f"geo={fidelity_result['geometry_fidelity']:.3f} "
                        f"ax={fidelity_result['axis_alignment']:.3f} "
                        f"dp={fidelity_result['depth_alignment']:.3f} "
                        f"composite={last_composite:.3f} phase={phase} "
                        f"avg={dpme_result['coherence_avg']:.3f} | "
                        f"vocab={vocab} presence={presence:.2f} | "
                        f"truth_depth={fidelity_result['truth_depth']} "
                        f"truth_axes={fidelity_result['truth_axes']} | "
                        f"'{snippet}...'"
                    )

                i += 2
            else:
                i += 1

        if verbose:
            print(f"  [RESPONDER] Complete. Pairs: {counter:,}\n")

    # PASS: REVERSE
    def pass_reverse():
        if verbose:
            print("  [CORPUS] PASS â REVERSE (geometry fidelity, reverse direction)\n")


        gate = CoherenceGate(window=coherence_window,
                             unlock_avg=unlock_avg,
                             unlock_min=unlock_min)
        counter = 0
        i = 0
        last_composite: Optional[float] = None

        while i < len(stream) - 1:
            role, content = stream[i]
            next_role, next_content = stream[i + 1]

            if role == "assistant" and next_role == "user":
                counter += 1
                ctx_hash = hashlib.md5(content[:32].encode()).hexdigest()[:8]

                resp = generate_reply(content, source="corpus_reverse")

                witness("USER_TRUTH", next_content,
                        source="corpus_reverse_truth",
                        context_hash=ctx_hash)

                truth_geom = physics_absorb_truth(
                    systems, absorption_field, next_content,
                    context_hash=ctx_hash, tone="neutral"
                )

                fidelity_result = fidelity_scorer.score(
                    generated=(resp.content if resp else ""),
                    truth=next_content,
                    seen_fingerprints=absorption_field._seen_fingerprints,
                )

                dpme_result = dpme_adjust_from_geometry(
                    systems=systems,
                    fidelity_result=fidelity_result,
                    truth_geom=truth_geom,
                    gate=gate,
                    verbose=dpme_verbose,
                )

                gate.update(dpme_result["composite"])
                last_composite = dpme_result["composite"]

                run_cadence(counter,
                            quality=dpme_result["composite"],
                            matched=dpme_result["improved"],
                            geom=truth_geom)

                if verbose and counter % 100 == 0:
                    snippet = ((resp.content if resp else "") or "")[:80]
                    snippet = snippet.replace("\n", " ")
                    phase = "UNLOCKED" if dpme_result["phase_unlocked"] \
                            else "LOCKED"
                    print(
                        f"  [REV] {counter:,} | "
                        f"geo={fidelity_result['geometry_fidelity']:.3f} "
                        f"composite={last_composite:.3f} phase={phase} "
                        f"avg={dpme_result['coherence_avg']:.3f} | "
                        f"'{snippet}...'"
                    )

                i += 2
            else:
                i += 1

        if verbose:
            print(f"  [REVERSE] Complete. Pairs: {counter:,}\n")

    # Execute passes
    passes = (passes or "triple").strip().lower()

    if passes == "observer":
        pass_observer()
    elif passes == "responder":
        pass_responder()
    elif passes == "reverse":
        pass_reverse()
    elif passes == "dynamic":
        if verbose:
            print("  [DYNAMIC] Starting physics-grounded dynamic curriculum")
            print("  [DYNAMIC] Loop: OBSERVER (until stall) -> RESPONDER (until success/fail)")
        
        study_mandate = 0
        while True:
            obs_status = pass_observer(break_on_stall=True, min_messages=study_mandate)
            if obs_status == "STALLED":
                resp_status = pass_responder(break_on_failure=True)
                if resp_status == "FAILED":
                    # Force 250 messages of study before next practice attempt
                    curriculum_tension.record_failure(0.0)
                    study_mandate = 250
                    absorption_field.plateau_detector.reset_stall()
                    continue
                else:
                    # Finished responder or succeeded
                    break
            else:
                # Finished observer pass without stall
                pass_responder()
                break
    elif passes in ("double", "both"):
        pass_observer()
        pass_responder()
    else:
        pass_observer()
        pass_responder()
        pass_reverse()

    # Final consolidation + save
    if verbose:
        print("  [CORPUS] Final consolidation...")
    consolidate(systems)

    if verbose:
        vocab = systems["perception"].lexicon.size
        gen = systems["identity"].generation
        facets = len(systems["dimensional"].der.registered_facets)
        links = len(systems["dimensional"].der.facet_to_facet_links)
        presence = systems["dimensional"].der.presence
        report = absorption_field.field_report()
        oets_info = ""
        if systems["perception"].oets:
            oets = systems["perception"].oets
            understanding = oets.metrics.compute()
            scaff = systems["perception"].composer.get_stats().get(
                'scaffolding', {})
            u_idx = understanding.get('understanding_index', 0.0) \
                if isinstance(understanding, dict) \
                else getattr(understanding, 'understanding_index', 0.0)
            oets_info = (
                f"\n  [CORPUS] OETS: {len(oets.web.nodes)} concepts "
                f"{len(oets.web.relations)} relations "
                f"understanding={u_idx:.3f} "
                f"scaffolded_fills={scaff.get('scaffolded_fills', 0)}"
            )
        print(
            f"  [CORPUS] Final state: vocab={vocab} gen={gen} "
            f"facets={facets} links={links} presence={presence:.3f}"
            f"{oets_info}"
        )
        print(
            f"  [CORPUS] Absorption field: "
            f"total={report['total_absorbed']} "
            f"surface={report['surface_writes']} "
            f"mid={report['mid_writes']} "
            f"deep={report['deep_writes']} "
            f"tension_resolved={report['tension_resolved']} "
            f"tension_expired={report['tension_expired']} "
            f"archived={report['fingerprints_archived']} "
            f"paths={report['crossing_paths']} "
            f"avg_novelty={report['avg_novelty']:.3f}"
        )
        print("  [CORPUS] Saving state...")

    aurora.save_state()
    _save_oets(systems, verbose=verbose)
    if systems.get("sensory_crystal"):
        try:
            # Final promotion tick before saving so all eligible concepts advance.
            _final_promoted = systems["sensory_crystal"].tick_concept_promotions()
            if _final_promoted and verbose:
                print(f"  [SENSORY] Final tick: promoted {len(_final_promoted)} concept(s)")
            systems["sensory_crystal"].save()
            if verbose:
                _sc = systems["sensory_crystal"].concept_registry_summary()
                print(f"  [SENSORY] Crystal saved — "
                      f"concepts={_sc['total']} by_stage={_sc['by_stage']}")
        except Exception as _scse:
            if verbose:
                print(f"  [SENSORY] Crystal save failed: {_scse}")
    if systems.get("perception"):
        _perc = systems["perception"]
        _lex_save_path = "aurora_state/lexicon.json"
        _disk_count = 0
        try:
            import json as _j
            _disk_count = len(
                _j.load(open(_lex_save_path)).get("entries", {}))
        except Exception:
            pass
        if _perc.lexicon.size >= _disk_count:
            _perc.save_lexicon()
        elif verbose:
            print(f"  [LEXICON] Save skipped ÃÂ¢Ã¢âÂ¬Ã¢â¬Â "
                  f"memory({_perc.lexicon.size}) < disk({_disk_count})")
        # FIX-A008: final motif lineage flush — the weld accumulated
        # success/demotion pressure all run; ensure the last increments
        # hit disk so they carry forward to her next boot.
        try:
            _ge_flush = systems.get("grammar_engine")
            _lin = getattr(_ge_flush, "_lineage", None) if _ge_flush else None
            if _lin is not None and hasattr(_lin, "save"):
                _lin.save()
                if verbose:
                    _promoted_n = (len(_lin.get_promoted())
                                   if hasattr(_lin, "get_promoted") else "?")
                    print(f"  [GRAMMAR] Motif lineage flushed "
                          f"({len(getattr(_lin, '_motifs', {}) or {})} patterns, "
                          f"{_promoted_n} promoted)")
        except Exception:
            pass
        print("  [CORPUS] Ingestion complete.\n")



# =============================================================================
# CLI
# =============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Aurora corpus runner ÃÂ¢Ã¢âÂ¬Ã¢â¬Â physics-grounded geometry absorption",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 corpus_runner.py --corpus conversations.json
  python3 corpus_runner.py --corpus conversations.json --passes triple
  python3 corpus_runner.py --corpus conversations.json --dpme-verbose

IMPORTANT: Always use --passes triple (default) for first runs.
  Observer builds geometry archive and crossing paths before
  responder/reverse test fidelity. Running responder or reverse
  alone on a fresh system produces shallow absorption.
        """)

    ap.add_argument("--corpus", type=str,
                    help="Path to corpus file (JSON, JSONL, CSV, TXT)")
    ap.add_argument("--url", type=str,
                    help="URL to download corpus from")
    ap.add_argument("--passes", type=str, default="triple",
                    help="observer|responder|reverse|double|triple|dynamic (default: triple)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--dpme-verbose", action="store_true")
    ap.add_argument("--warmup", type=int, default=3)

    ap.add_argument("--coherence-window", type=int, default=200)
    ap.add_argument("--unlock-avg", type=float, default=0.62)
    ap.add_argument("--unlock-min", type=float, default=0.45)

    ap.add_argument("--heartbeat-every", type=int, default=5)
    ap.add_argument("--identity-every", type=int, default=50)
    ap.add_argument("--voice-every", type=int, default=50)
    ap.add_argument("--consolidation-every", type=int, default=300)
    ap.add_argument("--simulation-every", type=int, default=500)
    ap.add_argument("--save-every", type=int, default=1000)
    ap.add_argument("--evolve-every", type=int, default=100)

    ap.add_argument("--state-dir", type=str, default="aurora_state")

    args = ap.parse_args()
    verbose = not args.quiet

    corpus_path = args.corpus
    if args.url:
        try:
            from aurora_internal.aurora_corpus_lifecycle import download_new_corpus
            downloaded = download_new_corpus(args.url)
            if downloaded:
                corpus_path = str(downloaded)
                if verbose:
                    print(f"  [CORPUS] Using downloaded file: {corpus_path}")
            else:
                print("  [CORPUS] Download failed. Aborting.")
                return
        except ImportError:
            print("  [CORPUS] Lifecycle module missing. Cannot download.")
            return

    if not corpus_path:
        print("  [ERROR] Either --corpus or --url must be provided.")
        return

    cadence = LearningCadence(
        heartbeat_every=args.heartbeat_every,
        identity_every=args.identity_every,
        voice_every=args.voice_every,
        consolidation_every=args.consolidation_every,
        simulation_every=args.simulation_every,
        save_every=args.save_every,
        evolve_every=args.evolve_every,
    )

    systems = boot_aurora(state_dir=args.state_dir, verbose=verbose)

    run_corpus_ingestion(
        systems=systems,
        corpus_path=corpus_path,
        cadence=cadence,
        passes=args.passes,
        verbose=verbose,
        dpme_verbose=args.dpme_verbose,
        coherence_window=args.coherence_window,
        unlock_avg=args.unlock_avg,
        unlock_min=args.unlock_min,
        warmup_epochs=args.warmup,
    )


if __name__ == "__main__":
    main()
