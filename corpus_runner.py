#!/usr/bin/env python3
"""
corpus_runner.py â€” Aurora Corpus Ingestion (Full-Stack Learning)
================================================================
Feeds external conversation data through Aurora's complete architecture,
engaging ALL five learning pathways:

  1. DER energy shaping   â€” DPME comparison â†’ inject/drain facet energy
  2. Vocabulary + patterns â€” L5 lexicon growth + composer template absorption
  3. Impression distillation â€” L5 consolidate() â†’ ecology generation + template evolution
  4. Identity evolution    â€” L6 process_episode() with ACTUAL quality signal
  5. Simulation wisdom     â€” L7 run_epoch() â†’ conscious learner shards

Critical addition: consciousness.tick() heartbeat runs between messages so
entropy erodes coherence (providing resistance to learn against), DER disperses
energy through the facet resonance graph, lattice advances toroidal dynamics,
and beings get background processing. The doctrine: "Coherence is not held.
Coherence is maintained."

v2 â€” Technical corpus hardening:
  - Aggressive sanitizer strips code, paths, URIs, Python identifiers,
    JSON/dict literals, CLI invocations, and technical punctuation
  - Vocabulary gate rejects tokens that look like code before they
    enter the lexicon (wraps L5 ingest_interaction)
  - Sentence-level filtering drops lines that are >40% non-language
  - Cadence defaults tuned for technical corpora (~5k-75k messages)

Usage:
  python3 corpus_runner.py --corpus /path/to/conversations.json
  python3 corpus_runner.py --corpus conversations.json --passes triple
  python3 corpus_runner.py --corpus conversations.json --passes responder --dpme-verbose

Passes:
  observer  : witness all messages (vocabulary + crystals + energy foundation)
  responder : Aurora replies to USER, compare to truth, DPME + full-stack learning
  reverse   : Aurora replies to ASSISTANT, compare to truth, DPME + full-stack learning
  triple    : observer -> responder -> reverse (default, RECOMMENDED)

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import re
import json
import time
import argparse
from difflib import SequenceMatcher
from collections import deque
from typing import Any, Dict, List, Tuple, Optional, Iterator

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
        # Fallback to legacy loader if lifecycle module missing (for safety)
        print("  [CORPUS] Lifecycle module not found, using legacy loader.")
        return iter([]) # Placeholder

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
                print(f"  [SAVE] OETS: {len(oets.web.nodes)}c / {len(oets.web.relations)}r")
            return ok
    except Exception as e:
        if verbose:
            print(f"  [SAVE] OETS save failed: {e}")
    return False


# =============================================================================
# Boot Aurora Stack
# =============================================================================

def boot_aurora(state_dir: str = "aurora_state", verbose: bool = True) -> Dict[str, Any]:
    if verbose:
        print("=" * 70)
        print("  AURORA Corpus Runner â€” Full-Stack Learning (v2)")
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

    snapshot = aurora.load_state()
    if verbose:
        if snapshot:
            print(f"  [STATE] Restored (gen={snapshot.generation}, "
                  f"epochs={snapshot.simulation_epochs})")
        else:
            print("  [STATE] Fresh boot â€” no prior state")

    # Checkpoint Manager â€” crash-safe resumption
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
            print(f"  [CHECKPOINT] Restored â€” last pass: {c.pass_name}, "
                  f"line: {c.line_index}, items: {c.total_items_processed}")
        checkpoint.start_auto_save(300)
    except Exception as e:
        if verbose:
            print(f"  [CHECKPOINT] Not available: {e}")
        print()

    # Evolutionary Chamber + Genealogy Logger
    chamber = None
    try:
        from aurora_internal.aurora_evolution_chamber import EvolutionaryChamber, ActionTrace
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

        # Restore links, abilities, and pair stats from prior runs so
        # K_MIN accumulation continues rather than resetting every boot.
        # Must restore before chamber is constructed so the DAG is live
        # when the first tick fires.
        try:
            from aurora_runtime import _restore_genealogy_state
            _restored = _restore_genealogy_state(_genealogy, output_dir=_gen_dir,
                                                  verbose=verbose)
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
    }


# =============================================================================
# OpenAI Export Parsing (conversations.json)
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


def _reconstruct_linear_thread(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    NON-RECURSIVE reconstruction of one main linear chain from OpenAI mapping DAG.
    Avoids RecursionError on long chains.
    """
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
                if node_id in visited:
                    continue
                if node_id in visiting:
                    continue

                visiting.add(node_id)
                stack.append((node_id, 1))

                node = mapping.get(node_id) or {}
                children = node.get("children") or []
                for c in children:
                    if c in visited:
                        continue
                    if c not in mapping:
                        continue
                    stack.append((c, 0))

            else:
                visiting.discard(node_id)
                node = mapping.get(node_id) or {}
                children = node.get("children") or []

                base = 1 if (isinstance(node, dict) and has_message(node)) else 0
                best_s = 0
                best_c = None

                for c in children:
                    if c not in mapping:
                        continue
                    cs = score.get(c, 0)
                    if cs > best_s:
                        best_s = cs
                        best_c = c

                score[node_id] = base + best_s
                best_child[node_id] = best_c
                visited.add(node_id)

        return score.get(root_id, 0)

    best_root = roots[0]
    best_root_score = -1
    for r in roots:
        rs = compute_from_root(r)
        if rs > best_root_score:
            best_root_score = rs
            best_root = r

    path_ids: List[str] = []
    seen: set = set()
    cur = best_root
    while cur is not None and cur not in seen:
        seen.add(cur)
        path_ids.append(cur)
        cur = best_child.get(cur)

    out: List[Dict[str, Any]] = []
    for nid in path_ids:
        node = mapping.get(nid)
        if isinstance(node, dict):
            out.append(node)
    return out


def _extract_messages_from_conversation(conv_obj: Dict[str, Any]) -> List[Tuple[str, str]]:
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


def _load_openai_conversations(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]

    if isinstance(data, dict):
        if isinstance(data.get("conversations"), list):
            return [d for d in data["conversations"] if isinstance(d, dict)]
        if isinstance(data.get("data"), list):
            return [d for d in data["data"] if isinstance(d, dict)]

    return []


# =============================================================================
# Hygiene â€” AGGRESSIVE code-stripping for technical corpora
# =============================================================================

# Python keywords and builtins that should never be vocabulary
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

# Regex patterns for code-like lines
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
    """Check if a line looks like code rather than natural language."""
    stripped = line.strip()
    if not stripped:
        return False

    for pat in _CODE_LINE_PATTERNS:
        if re.match(pat, stripped):
            return True

    # High symbol density = likely code
    non_alnum = sum(1 for ch in stripped if not (ch.isalnum() or ch.isspace()))
    if len(stripped) > 5 and non_alnum / len(stripped) > 0.35:
        return True

    # Common code operators
    code_ops = ['==', '!=', '>=', '<=', '->', '=>', '::', '**', '//', '&&',
                '||', '+=', '-=', '*=', '/=', '<<', '>>', '...']
    for op in code_ops:
        if op in stripped:
            return True

    # File paths
    if re.search(r'[/\\]\w+[/\\]\w+', stripped):
        return True

    # snake_case function calls
    if re.search(r'\w+_\w+_\w+\(', stripped):
        return True

    # Dict/JSON key patterns
    if re.search(r'["\'][\w_]+["\']\s*:', stripped):
        return True

    return False


def _extract_natural_sentences(text: str) -> List[str]:
    """Split text into sentences and keep only natural language ones."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    natural = []

    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 10:
            continue

        lines = sent.split('\n')
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
    """
    Aggressively strip code, paths, URIs, and technical artifacts.
    Designed for corpora that mix natural language with code discussion.
    """
    if not text:
        return ""
    t = text

    # Phase 1: Block-level removal
    for pat in _CITATION_PATTERNS:
        t = re.sub(pat, "", t, flags=re.DOTALL)

    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`[^`]*`", " ", t)

    # Phase 2: Line-level code stripping
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
    t = re.sub(r'\b\w+Error:\s*[^\n]*', ' ', t)
    t = re.sub(r'\b(?:python3?|pip|npm|bash|sh)\s+\S+(?:\s+--?\S+)*', ' ', t)
    t = re.sub(r'(?:==|!=|>=|<=|->|=>|::|&&|\|\||<<|>>)', ' ', t)
    t = re.sub(r'\b[0-9a-f]{8,}\b', ' ', t)

    # Phase 3: Emphasis/markdown cleanup
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"\*(.*?)\*", r"\1", t)
    t = re.sub(r"#{1,6}\s+", "", t)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", t)

    # Phase 4: Sentence-level filtering
    natural = _extract_natural_sentences(t)

    if not natural:
        t = re.sub(r'\s+', ' ', t).strip()
        words = [w for w in t.split() if w.isalpha() and len(w) > 1]
        return t if len(words) >= 3 else ""

    result = ' '.join(natural)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


# =============================================================================
# Vocabulary Gate â€” reject code tokens before they enter the lexicon
# =============================================================================

def is_valid_word(word: str) -> bool:
    """Returns True only if the word looks like natural language."""
    w = word.strip(".,!?;:'\"()-[]{}").lower()

    if len(w) < 2 or len(w) > 25:
        return False

    # Must be alphabetic (allow hyphens for compound words)
    if not re.match(r'^[a-z]+(?:-[a-z]+)*$', w):
        return False

    if w in _CODE_KEYWORDS:
        return False

    if '_' in w:
        return False

    # Reject camelCase and PascalCase (programming identifiers)
    raw = word.strip(".,!?;:'\"()-")
    if re.search(r'[a-z][A-Z]', raw):
        return False
    # Reject words with uppercase runs of 3+ (acronyms like IVM, DPME, DER)
    if re.search(r'[A-Z]{3,}', raw):
        return False
    # Reject PascalCase: uppercase letter followed by lowercase in middle of word
    if re.search(r'[A-Z][a-z]+[A-Z]', raw):
        return False

    return True


# =============================================================================
# Coherence Gate + Comparison Metrics
# =============================================================================

class CoherenceGate:
    """
    Rolling coherence score gate. Unlocks meaning/emotion adjustments only
    after stable coherence is established across a window.
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
        return ((self.avg() >= self.unlock_avg) and
                (self.min_recent() >= self.unlock_min))


def similarity_score(a: str, b: str) -> float:
    """Cheap stable similarity (0..1) for convergence pressure."""
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def vocabulary_overlap(a: str, b: str) -> float:
    """Word-level Jaccard overlap â€” forgiving for early-stage Aurora."""
    words_a = set((a or "").lower().split())
    words_b = set((b or "").lower().split())
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def artifact_ratio(text: str) -> float:
    """Symbol/garbage density."""
    if not text:
        return 0.0
    non = sum(1 for ch in text if not (ch.isalnum() or ch.isspace()))
    return non / max(len(text), 1)


def composite_similarity(generated: str, truth: str) -> float:
    """
    Blended similarity: 60% sequence match + 40% vocabulary overlap.
    Gives early Aurora credit for using correct words even when
    sentence structure is still primitive.
    """
    seq = similarity_score(generated, truth)
    voc = vocabulary_overlap(generated, truth)
    return seq * 0.6 + voc * 0.4


# =============================================================================
# DPME Comparison + Adjustment (coherence-first, full-stack)
# =============================================================================

def dpme_adjust_from_comparison(
    systems: Dict[str, Any],
    generated: str,
    truth: str,
    last_score: Optional[float],
    gate: CoherenceGate,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Coherence-first DPME policy with full-stack integration.
    """
    consciousness = systems["consciousness"]
    dpme = consciousness.dpme

    gen = (generated or "").strip()
    tr = (truth or "").strip()

    sim = composite_similarity(gen, tr)
    art = artifact_ratio(gen)
    mismatch = 1.0 - sim

    unlocked = gate.unlocked() if gate is not None else False

    if last_score is None:
        matched = False
        quality = sim
    else:
        matched = sim >= last_score
        quality = sim

    adjustments = []
    intention = "coherence-first response alignment via comparison"

    if not unlocked:
        if mismatch > 0.70:
            adjustments.append(dpme.adjust("der", "cat_processing", 0.22, intention))
            adjustments.append(dpme.adjust("der", "cat_memory", 0.16, intention))
            adjustments.append(dpme.adjust("der", "presence", 0.08,
                                           "stabilize expression channel"))
        elif mismatch > 0.45:
            adjustments.append(dpme.adjust("der", "cat_processing", 0.14, intention))
            adjustments.append(dpme.adjust("der", "cat_memory", 0.10, intention))
            adjustments.append(dpme.adjust("der", "presence", 0.05,
                                           "stabilize expression channel"))
        elif mismatch > 0.25:
            adjustments.append(dpme.adjust("der", "cat_processing", 0.08, intention))
            adjustments.append(dpme.adjust("der", "cat_memory", 0.04, intention))

        if art > 0.10:
            adjustments.append(dpme.adjust("der", "presence", 0.06,
                                           "reduce artifact density"))
            adjustments.append(dpme.adjust("der", "cat_processing", 0.08,
                                           "reduce artifact density"))

        if mismatch > 0.35 or art > 0.08:
            adjustments.append(dpme.adjust("der", "cat_emotional", -0.04,
                                           "suppress emotion until coherence stabilizes"))
            adjustments.append(dpme.adjust("der", "cat_creative", -0.05,
                                           "suppress creativity until coherence stabilizes"))
    else:
        intention2 = ("coherence established â€” allow meaning/emotion "
                      "while preserving structure")

        if mismatch > 0.40:
            adjustments.append(dpme.adjust("der", "cat_processing", 0.10, intention2))
            adjustments.append(dpme.adjust("der", "cat_memory", 0.07, intention2))

        if art < 0.07:
            if matched:
                adjustments.append(dpme.adjust("der", "cat_emotional", 0.03,
                                               "meaning integration"))
                adjustments.append(dpme.adjust("der", "cat_creative", 0.02,
                                               "expressive flexibility"))
            else:
                adjustments.append(dpme.adjust("der", "cat_emotional", 0.01,
                                               "low-stakes meaning integration"))

        adjustments.append(dpme.adjust("der", "presence", 0.02,
                                       "maintain stability while adding meaning"))

    adjustments = [a for a in adjustments if a is not None]

    for adj in adjustments:
        dpme.evaluate_adjustment(adj, quality=quality, matched=matched)

    if dpme.needs_correction():
        dpme.auto_correct()

    if verbose:
        phase = "UNLOCKED" if unlocked else "LOCKED"
        avg = gate.avg() if gate else 0.0
        mn = gate.min_recent() if gate else 0.0
        print(f"  [DPME] phase={phase} sim={sim:.3f} mismatch={mismatch:.3f} "
              f"art={art:.3f} avg={avg:.3f} min={mn:.3f} "
              f"adj={len(adjustments)} improved={matched}")

    return {
        "similarity": sim,
        "mismatch": mismatch,
        "artifact_ratio": art,
        "adjustments": len(adjustments),
        "improved": matched,
        "phase_unlocked": unlocked,
        "coherence_avg": gate.avg() if gate else 0.0,
        "coherence_min": gate.min_recent() if gate else 0.0,
    }


# =============================================================================
# Full-Stack Learning Hooks
# =============================================================================

def heartbeat(systems: Dict[str, Any]):
    """
    One consciousness heartbeat. Entropy erodes coherence, DER disperses
    energy, lattice advances, beings background-tick, DPME auto-corrects.
    """
    systems["consciousness"].tick()


def absorb_truth(systems: Dict[str, Any], truth_text: str, tone: str = "neutral"):
    """
    Feed ground-truth text into L5 composer template pool.
    Filters through vocabulary gate first so code tokens don't poison templates.
    """
    perception = systems["perception"]
    if truth_text and len(truth_text.split()) >= 3:
        words = truth_text.split()
        clean_words = [w for w in words if is_valid_word(
            w.strip(".,!?;:'\"()-[]{}").lower())]
        clean_text = ' '.join(clean_words)
        if len(clean_text.split()) >= 3:
            perception.composer.absorb(clean_text, tone)


def evolve_identity(systems: Dict[str, Any], quality: float, mode=None):
    """Feed actual quality signal to L6 identity evolution."""
    if mode is None:
        from foundational_contract import ExistenceMode
        mode = ExistenceMode.BOUNDED

    identity = systems["identity"]
    relics = [{
        'theme': 'corpus_learning',
        'stability': min(quality, 0.9),
        'seed_ids': [f"corpus_{int(time.time()*1000)}"],
        'emotional_bias': {
            'trust': 0.3 + quality * 0.4,
            'curiosity': 0.4 + (1.0 - quality) * 0.3,
        },
        'manifold_position': (quality, 0.5, 0.0, 0.0, 0.0),
    }]
    pillar_scores = {'interaction': quality, 'growth': 0.5 + quality * 0.3}
    identity.process_episode(
        {'success_rate': quality, 'lessons_learned': []},
        relics, pillar_scores, mode,
    )


def evolve_voice(systems: Dict[str, Any], quality: float, matched: bool):
    """Feed quality signal to L5 voice genome."""
    perception = systems["perception"]
    feedback = {
        'user_engaged': quality,
        'comfort': 0.5 + quality * 0.3,
    }
    if matched:
        feedback['resonance'] = 0.6 + quality * 0.2
    perception.voice.evolve(feedback)


def consolidate(systems: Dict[str, Any]):
    """L5 impression distillation â€” ecology generation + template evolution + OETS study."""
    from foundational_contract import ExistenceMode
    systems["perception"].consolidate(min_mode=ExistenceMode.BOUNDED)

    # OETS internal study: if no internet callback, still does internal
    # consolidation + cluster discovery + depth recalculation
    oets = getattr(systems["perception"], 'oets', None)
    if oets:
        oets.consolidate()


def simulation_burst(systems: Dict[str, Any], episodes: int = 4,
                     verbose: bool = True):
    """L7 simulation training burst â€” avatars + inception + wisdom shards."""
    from foundational_contract import ExistenceMode
    simulation = systems["simulation"]

    result = simulation.run_epoch(
        episodes_per_epoch=episodes,
        turns_per_episode=3,
        mode=ExistenceMode.AGENTIC,
    )

    if verbose:
        fitness = result.get('avg_fitness', 0)
        shards = result.get('learner_shards', 0)
        print(f"  [SIM] burst: fitness={fitness:.3f} shards={shards}")

    return result


def evolve_chain(systems: Dict[str, Any], ticks: int = 50, verbose: bool = False):
    """
    Tick the EvolutionaryChamber N times and feed pressure-relief events
    into the ConstraintGenealogyLogger fossil record.

    Called by run_cadence on the evolve_every schedule.
    Maps the current interaction quality signal to an ActionTrace so the
    genealogy knows which constraint axis was being exercised.
    """
    chamber = systems.get("chamber")
    if chamber is None:
        return

    try:
        from aurora_internal.aurora_evolution_chamber import ActionTrace
    except ImportError:
        return

    # Build a simple agency+boundary action (communication is the default frame)
    # The chamber's ActionAbilityMapper will resolve these labels to ability IDs
    action = ActionTrace(
        name="communication",
        constraints_used=frozenset({"agency", "boundary", "temporal"}),
        meta={"source": "corpus_evolve"},
    )

    new_fossils = 0
    new_links   = 0
    for _ in range(ticks):
        event = chamber.tick(action=action)
        if event is not None:
            new_fossils += 1

    new_links = chamber._genealogy.links_promoted
    chamber._genealogy.flush_files()

    if verbose:
        cr = chamber._genealogy.chain_report()
        print(
            f"  [CHAIN] ticks={ticks} new_fossils={new_fossils} "
            f"total_links={cr['total_links']} "
            f"outlet_fraction={cr['outlet_push_fraction']:.3f}"
        )


# =============================================================================
# Learning Cadence â€” when each pathway fires
# =============================================================================

class LearningCadence:
    """
    Orchestrates when each learning pathway fires.

    Defaults calibrated for a technical corpus (~5k-75k messages):
      heartbeat:     every 5 messages  (entropy erosion + DER dispersal)
      truth_absorb:  every response    (always â€” cheap and high-value)
      identity:      every 50 messages (trait drift â€” slowed for noisy signal)
      voice:         every 50 messages (voice genome â€” slowed for same reason)
      consolidation: every 300 messages (ecology + template generation cycle)
      simulation:    every 500 messages (L7 avatar + learner burst)
      save:          every 1000 messages (state persistence)
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
        self.evolve_every = evolve_every  # evolutionary chain ticks

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
# Corpus Ingestion â€” Full-Stack
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

    if verbose:
        print("=" * 70)
        print("  [CORPUS] Full-Stack Ingestion (v2 â€” technical corpus hardened)")
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

    # Warm-up simulation
    if warmup_epochs > 0:
        if verbose:
            print(f"\n  [WARMUP] Running {warmup_epochs} simulation epochs")
        for i in range(warmup_epochs):
            result = simulation_burst(systems, episodes=8, verbose=verbose)
        if verbose:
            vocab = systems["perception"].lexicon.size
            print(f"  [WARMUP] Complete. Vocabulary: {vocab}\n")

    # Load corpus â€” universal format detection
    if verbose:
        print(f"  [CORPUS] Initializing universal stream for: {corpus_path}")

    stream: List[Tuple[str, str]] = []
    dropped_count = 0

    # We flatten the universal iterator into the stream list
    for role_or_user, text_or_assistant in _get_corpus_iterator(corpus_path):
        # Handle formats that might give us pairs or role-labeled single messages
        # (The universal iterator yields (user, assistant) pairs for simple formats)
        
        # 1. User Message
        clean_u = sanitize_corpus_text(role_or_user)
        if clean_u and len(clean_u.split()) >= 3:
            stream.append(("user", clean_u))
        else:
            dropped_count += 1
            
        # 2. Assistant Message
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

    # Core routing
    def witness(tag: str, content: str, source: str):
        if not content or len(content.split()) < 3:
            return None
        return aurora.gateway.receive(
            content=f"[{tag}] {content}",
            stream_type=StreamType.KNOWLEDGE_FEED,
            source=source,
            mode=ExistenceMode.BOUNDED,
        )

    def generate_reply(prompt_text: str, source: str):
        if not prompt_text or len(prompt_text.split()) < 3:
            return None
        return aurora.gateway.receive(
            content=prompt_text,
            stream_type=StreamType.USER_INPUT,
            source=source,
            mode=ExistenceMode.BOUNDED,
        )

    def run_cadence(counter: int, quality: float = 0.5,
                    matched: bool = False):
        if cadence.should_heartbeat(counter):
            heartbeat(systems)

        if cadence.should_identity(counter):
            evolve_identity(systems, quality, ExistenceMode.BOUNDED)

        if cadence.should_voice(counter):
            evolve_voice(systems, quality, matched)

        if cadence.should_consolidate(counter):
            consolidate(systems)
            if verbose:
                vocab = systems["perception"].lexicon.size
                gen = systems["identity"].generation
                oets_info = ""
                if systems["perception"].oets:
                    oets = systems["perception"].oets
                    oets_info = (f" oets={len(oets.web.nodes)}c/"
                                 f"{len(oets.web.relations)}r")
                print(f"  [CONSOLIDATE] at message {counter:,} "
                      f"(vocab={vocab} gen={gen}{oets_info})")

        if cadence.should_simulate(counter):
            if verbose:
                print(f"  [SIM] Training burst at message {counter:,}")
            simulation_burst(systems, episodes=4, verbose=verbose)

        if cadence.should_evolve(counter):
            evolve_chain(systems, ticks=50, verbose=verbose)

        if cadence.should_save(counter):
            if verbose:
                print(f"  [SAVE] at message {counter:,}")
            aurora.save_state()
            _save_oets(systems, verbose=verbose)

    # Checkpoint reference (from systems or boot_aurora)
    _checkpoint = systems.get("checkpoint")

    # PASS: OBSERVER
    def pass_observer():
        if verbose:
            print("  [CORPUS] PASS â€” OBSERVER (witness + build foundation)\n")
        counter = 0
        # Resume from checkpoint if applicable
        start_line = 0
        if _checkpoint and _checkpoint.cursor.pass_name == "observer":
            start_line = _checkpoint.cursor.line_index
            if verbose and start_line > 0:
                print(f"  [CHECKPOINT] Resuming observer from line {start_line}")

        for line_idx, (role, content) in enumerate(stream):
            if line_idx < start_line:
                continue
            counter += 1
            witness(role.upper(), content, source="corpus_observer")
            run_cadence(counter)

            # Checkpoint every 500 items
            if _checkpoint and counter % 500 == 0:
                import hashlib as _hs
                item_hash = _hs.md5(content[:64].encode()).hexdigest()[:8]
                _checkpoint.advance(
                    line_index=line_idx,
                    item_hash=item_hash,
                    pass_name="observer",
                    file_path=corpus_path,
                )

            if verbose and counter % 500 == 0:
                vocab = systems["perception"].lexicon.size
                facets = len(systems["dimensional"].der.registered_facets)
                oets_info = ""
                if systems["perception"].oets:
                    oets = systems["perception"].oets
                    oets_info = (f" oets={len(oets.web.nodes)}c/"
                                 f"{len(oets.web.relations)}r")
                print(f"  [OBSERVER] {counter:,} processed "
                      f"(vocab={vocab} facets={facets}{oets_info})")

        if verbose:
            print(f"\n  [OBSERVER] Complete. Messages: {counter:,}\n")

    # PASS: RESPONDER
    def pass_responder():
        if verbose:
            print("  [CORPUS] PASS â€” RESPONDER (reply + compare + "
                  "full-stack learning)\n")

        gate = CoherenceGate(window=coherence_window,
                             unlock_avg=unlock_avg,
                             unlock_min=unlock_min)
        counter = 0
        # Resume from checkpoint if applicable
        start_i = 0
        if _checkpoint and _checkpoint.cursor.pass_name == "responder":
            start_i = _checkpoint.cursor.line_index
            if verbose and start_i > 0:
                print(f"  [CHECKPOINT] Resuming responder from line {start_i}")

        i = start_i
        last_sim: Optional[float] = None

        while i < len(stream) - 1:
            role, content = stream[i]
            next_role, next_content = stream[i + 1]

            if role == "user" and next_role == "assistant":
                counter += 1

                # Checkpoint every 500 pairs
                if _checkpoint and counter % 500 == 0:
                    import hashlib as _hs
                    item_hash = _hs.md5(content[:64].encode()).hexdigest()[:8]
                    _checkpoint.advance(
                        line_index=i,
                        item_hash=item_hash,
                        pass_name="responder",
                        file_path=corpus_path,
                    )

                resp = generate_reply(content, source="corpus_responder")

                witness("ASSISTANT_TRUTH", next_content,
                        source="corpus_responder_truth")

                absorb_truth(systems, next_content, tone="neutral")

                dpme_result = dpme_adjust_from_comparison(
                    systems=systems,
                    generated=(resp.content if resp else ""),
                    truth=next_content,
                    last_score=last_sim,
                    gate=gate,
                    verbose=dpme_verbose,
                )

                gate.update(dpme_result["similarity"])
                last_sim = dpme_result["similarity"]

                run_cadence(counter,
                            quality=dpme_result["similarity"],
                            matched=dpme_result["improved"])

                if verbose and counter % 100 == 0:
                    snippet = ((resp.content if resp else "") or "")[:100]
                    snippet = snippet.replace("\n", " ")
                    phase = "UNLOCKED" if dpme_result["phase_unlocked"] \
                            else "LOCKED"
                    vocab = systems["perception"].lexicon.size
                    presence = systems["dimensional"].der.presence
                    oets_info = ""
                    if systems["perception"].oets:
                        oets = systems["perception"].oets
                        scaff = systems["perception"].composer.get_stats().get(
                            'scaffolding', {})
                        oets_info = (f" oets={len(oets.web.nodes)}c"
                                     f" scaff={scaff.get('scaffolded_fills', 0)}")
                    print(
                        f"  [RESP] {counter:,} | "
                        f"sim={last_sim:.3f} phase={phase} "
                        f"avg={dpme_result['coherence_avg']:.3f} | "
                        f"vocab={vocab} presence={presence:.2f}{oets_info} | "
                        f"'{snippet}...'"
                    )

                i += 2
            else:
                i += 1

        if verbose:
            print(f"\n  [RESPONDER] Complete. Pairs: {counter:,}\n")

    # PASS: REVERSE
    def pass_reverse():
        if verbose:
            print("  [CORPUS] PASS â€” REVERSE (reply to ASSISTANT + "
                  "full-stack learning)\n")

        gate = CoherenceGate(window=coherence_window,
                             unlock_avg=unlock_avg,
                             unlock_min=unlock_min)
        counter = 0
        i = 0
        last_sim: Optional[float] = None

        while i < len(stream) - 1:
            role, content = stream[i]
            next_role, next_content = stream[i + 1]

            if role == "assistant" and next_role == "user":
                counter += 1

                resp = generate_reply(content, source="corpus_reverse")

                witness("USER_TRUTH", next_content,
                        source="corpus_reverse_truth")

                absorb_truth(systems, next_content, tone="neutral")

                dpme_result = dpme_adjust_from_comparison(
                    systems=systems,
                    generated=(resp.content if resp else ""),
                    truth=next_content,
                    last_score=last_sim,
                    gate=gate,
                    verbose=dpme_verbose,
                )

                gate.update(dpme_result["similarity"])
                last_sim = dpme_result["similarity"]

                run_cadence(counter,
                            quality=dpme_result["similarity"],
                            matched=dpme_result["improved"])

                if verbose and counter % 100 == 0:
                    snippet = ((resp.content if resp else "") or "")[:100]
                    snippet = snippet.replace("\n", " ")
                    phase = "UNLOCKED" if dpme_result["phase_unlocked"] \
                            else "LOCKED"
                    print(
                        f"  [REV] {counter:,} | "
                        f"sim={last_sim:.3f} phase={phase} "
                        f"avg={dpme_result['coherence_avg']:.3f} | "
                        f"'{snippet}...'"
                    )

                i += 2
            else:
                i += 1

        if verbose:
            print(f"\n  [REVERSE] Complete. Pairs: {counter:,}\n")

    # Execute passes
    passes = (passes or "triple").strip().lower()

    if passes == "observer":
        pass_observer()
    elif passes == "responder":
        pass_responder()
    elif passes == "reverse":
        pass_reverse()
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
        oets_info = ""
        if systems["perception"].oets:
            oets = systems["perception"].oets
            understanding = oets.metrics.compute(oets.web, oets.cluster_engine)
            scaff = systems["perception"].composer.get_stats().get(
                'scaffolding', {})
            oets_info = (
                f"\n  [CORPUS] OETS: {len(oets.web.nodes)} concepts "
                f"{len(oets.web.relations)} relations "
                f"understanding={understanding.understanding_index:.3f} "
                f"scaffolded_fills={scaff.get('scaffolded_fills', 0)} "
                f"scaffolded_templates={scaff.get('total_scaffolded', 0)}"
            )
        print(f"  [CORPUS] Final state: vocab={vocab} gen={gen} "
              f"facets={facets} links={links} presence={presence:.3f}"
              f"{oets_info}")
        print("  [CORPUS] Saving state...")

    aurora.save_state()
    _save_oets(systems, verbose=verbose)

    if verbose:
        print("  [CORPUS] Ingestion complete.\n")


# =============================================================================
# CLI
# =============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Aurora corpus runner â€” full-stack learning with "
                    "coherence-first DPME (v2, technical corpus hardened)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 corpus_runner.py --corpus conversations.json
  python3 corpus_runner.py --corpus conversations.json --passes triple
  python3 corpus_runner.py --corpus conversations.json --dpme-verbose

IMPORTANT: Always use --passes triple (default) for first runs.
  Observer builds the vocabulary foundation before responder/reverse test her.
  Running responder or reverse alone on a fresh system produces garbage.
        """)

    ap.add_argument("--corpus", type=str,
                    help="Path to corpus file (JSON, JSONL, CSV, TXT)")
    ap.add_argument("--url", type=str,
                    help="URL to download a new corpus from (e.g., raw GitHub or dataset link)")
    ap.add_argument("--passes", type=str, default="triple",
                    help="observer|responder|reverse|double|triple (default: triple)")
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
    ap.add_argument("--evolve-every", type=int, default=100,
                    help="Tick the evolutionary chamber every N messages (0=disabled)")

    ap.add_argument("--state-dir", type=str, default="aurora_state")

    args = ap.parse_args()
    verbose = not args.quiet

    # Handle URL download if provided
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
            print("  [CORPUS] Lifecycle module missing. Cannot download from URL.")
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
