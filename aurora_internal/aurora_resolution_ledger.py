"""
aurora_resolution_ledger.py
===========================

Representations as (subject, axis-path) pairs.

Resolution is not a time window and not a vocabulary tier.  It is the length of
the path of root constraints a subject is seen through, exactly as Aurora's
own substrate is built:

    length 0   the event itself                          REC_SURFACE
    length 1   X, T, N, B, A                  (5)        REC_SHALLOW
    length 2   X>X, X>T ... A>A               (25)       REC_MODERATE   (NC channels)
    length 3   X>X>X ... A>A>A                (125)      REC_DEEP       (axis triples)
    length 4   channel through channel        (625)      REC_CORE       (NC interaction slots)

Each level is the previous level crossed with the five roots, so the ladder is
defined by composition and not by name, and it lands on the five recursion
depths Aurora already carries (IVM ``RecursionLevel``, WARP ``REC_*``).

What a path means on an event stream.  An event contributes five raw,
label-free facts, one asked of each root (X presence change, T elapsed, N
extent, B nearness to an opening boundary, A handoff of the acting party), each
read as high or low against its own running natural split.  (B is a participation
boundary: an actor's first act inside the episode.  It is deliberately not a
position counter, which would make every path through B trivially persistent.)  A path ``a1>a2>...>ad`` is
a chain of transitions: the root ``a_i`` as it stood ``d-i`` events ago, read
through to the root ``a_d`` of the event that just arrived.  ``X>T`` asks what
existence did to time; ``T>X`` asks what time did to existence; ``T>T>N`` asks
how two successive temporal states carried through to energy.

Discovery.  Every (subject, path) predictor is scored prequentially against a
permutation null built with the same estimator.  Length-2 paths must beat the
null; a deeper path must beat the BEST shallower path for the same target root
on the same events (its baseline), so a deeper resolution is only kept where
every shallower one was not enough and a path cannot ride on a stronger
shallower path it merely contains.  Significance uses batch means (robust to serial
dependence) and a correction for the number of paths at that length.  A level
activates once the subject has been observed often enough to fill that
level's context cells.  A path is confessed to WARP only after it survives
consecutive looks, so a transient crossing of the threshold is never reported.

Doctrine: no label, phrase list, intent class or gloss is stored; a discovered
representation is an axis path plus lineage.  When a path is discovered the
ledger confesses a MISSING_REPRESENTATION demand to WARP whose REC_* coordinate
is the path length.

Stage 1 scope: sensing, per-subject path discovery, WARP emission, and a
registry of discovered (subject, path) representations linked by composition.
Landing them as referents the web/grounding can use, the use-and-consequence
loop, and live-turn wiring are later stages.

Time and position are read from the stream itself, never from the future, so a
live turn and a replayed historical turn feed this ledger identically.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import bisect
import hashlib
import itertools
import json
import math
import os
import random
import time
from collections import deque
from pathlib import Path
from statistics import NormalDist
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional, Tuple

from aurora_persistence_utils import atomic_write_json
from aurora_warp_protocol import WarpDemand, WarpTrigger

# Canonical five-axis order: existence, temporal, energy, boundary, agency.
AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
# Optional TAIL resolution.  For the continuous roots (T, N) a second symbol that is 1 when the
# value sits in the extreme-LOW tail of its subject's own distribution: a rare brief cluster
# (a greeting among ordinary content) that one coarse split cannot isolate.  Off by default;
# enable with AuroraResolutionLedger(tail=True) or AURORA_RESOLUTION_TAIL=1.
TAIL_SYMBOLS: Tuple[str, ...] = ("t", "n")
# Optional LEXICAL symbols: classes of words discovered from the words themselves (see
# aurora_lexical_structure).  A class bit is 1 when the event contains any member, which lets paths
# hang on distinctions the five roots cannot express.  Off by default; AURORA_LEXICAL_SYMBOLS=1 or lexical=True.
LEX_SYMBOLS: Tuple[str, ...] = ("L0", "L1", "L2", "L3")
SYMBOLS: Tuple[str, ...] = AXES + TAIL_SYMBOLS + LEX_SYMBOLS
_TAIL_ETA = 0.8                  # Otsu separability of the lower class (0..1) that counts as a real second mode
_TAIL_MIN = 20                   # a tail must be a cluster of at least this many samples, not noise
# Representational irreducibility: two paths with the same target are ONE family when their
# predictions over the same observed events differ by less than this fraction of the distinction
# either one makes.  A deeper composition must make a distinction no other path already makes.
_EQUIV_TOL = 0.1
_EQUIV_MIN = 64                  # observed events needed before a family can be judged

# Resolution axis = Aurora's existing recursion depths (IVM RecursionLevel).
REC_DIMS: Tuple[str, ...] = ("REC_SURFACE", "REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE")
MAX_PATH: int = len(REC_DIMS) - 1      # REC_CORE: channel through channel (625)
MIN_PREDICTIVE_PATH: int = 2           # a path needs a source and a target to predict
# Depth 4 (the 625 slots) is implemented but NOT validated: under a global-shuffle control it
# discovered 250 length-4 paths (all tiny, all targeting X).  Production runs depth 3 until a
# stricter criterion is in place; callers opt into 4 explicitly.
DEFAULT_MAX_PATH: int = 3

# WARP polarity names (negative = deficit pressure, positive = affirmative).
_NEGATIVE_ISTATE = {"X": "I_ISNT", "T": "I_CANNOT", "N": "I_DONOT", "B": "I_SOUGHT", "A": "I_DIDNT"}
_POSITIVE_ISTATE = {"X": "I_IS", "T": "I_CAN", "N": "I_DO", "B": "I_SAW", "A": "I_DID"}

SCHEMA = "aurora_resolution_ledger_v2"
_HYP_SYNC_EVERY = 500            # observations between writes of the research state onto the crystals
_SKETCH = 512                    # running distributions are carried as this many quantiles
_KT_ALPHA = 0.5                  # Krichevsky-Trofimov estimator (binary)
_RESERVOIR = 4096                # running-distribution memory (rank); long enough that a sticky signal cannot drag its own median
_NULL_MEMORY = 256               # past histories available to the permutation null
_OBS_PER_CONTEXT = 100           # a level activates once each context cell can be seen ~this often
_SPLIT_EVERY = 100                # the high/low split is held between recomputations
_BLOCK = 100                     # batch-mean block (robust to serial dependence)
_MIN_BLOCKS = 5                  # blocks before significance is read
_ALPHA = 0.05                    # family-wise error across the paths of one length
_EVAL_EVERY = 200                # per-subject evaluation cadence (a tick, not a threshold on meaning)
_CONFIRM_LOOKS = 2               # a path is confessed to WARP only after surviving this many consecutive looks
_MAX_SEVERITY = 0.88             # a known five-root deficiency, never a sixth-axis claim


def _path_key(path: Tuple[int, ...]) -> str:
    return ">".join(SYMBOLS[i] for i in path)


def _path_from_key(key: str) -> Tuple[int, ...]:
    return tuple(SYMBOLS.index(part) for part in key.split(">"))


def _alphabet(indices: Iterable[int]) -> Tuple[Dict[int, List[Tuple[int, ...]]], Dict[int, float]]:
    """All paths per length over the ACTIVE symbol indices, and the family-wise critical z per length."""
    indices = list(indices)
    paths = {
        length: list(itertools.product(indices, repeat=length))
        for length in range(MIN_PREDICTIVE_PATH, MAX_PATH + 1)
    }
    crit = {
        length: NormalDist().inv_cdf(1.0 - _ALPHA / (2.0 * len(group)))
        for length, group in paths.items()
    }
    return paths, crit


def _clip01(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(out):
        return 0.0
    return max(0.0, min(1.0, out))


def _stable_seed(*parts: Any) -> int:
    acc = 1469598103934665603
    for part in parts:
        for ch in str(part):
            acc = ((acc ^ ord(ch)) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return acc


class _Running:
    """Parameter-free running distribution with a natural two-class split.

    A median is a poor threshold for a signal with two modes in unequal
    proportion (it lands inside the larger mode and turns some of its values
    into coin flips), so the split is the one that maximises between-class
    variance (Otsu).  It is recomputed on a fixed cadence and held between
    recomputations, so a run of similar events cannot drag its own threshold.
    """

    def __init__(self, state: Optional[Mapping[str, Any]] = None) -> None:
        state = dict(state or {})
        self.values: List[float] = sorted(float(v) for v in (state.get("values") or []))
        self.adds: int = int(state.get("adds", 0) or 0)
        thr = state.get("thr")
        self.thr: Optional[float] = None if thr is None else float(thr)
        tail = state.get("tail")
        self.tail_thr: Optional[float] = None if tail is None else float(tail)

    def state(self) -> Dict[str, Any]:
        return {"values": self.values, "adds": self.adds, "thr": self.thr, "tail": self.tail_thr}

    def high(self, x: float) -> int:
        return 1 if (self.thr is not None and x > self.thr) else 0

    def rank(self, x: float) -> float:
        """Position of x in this subject's own running distribution (0..1; 0.5 until there is one)."""
        n = len(self.values)
        if n == 0:
            return 0.5
        return ((bisect.bisect_left(self.values, x) + bisect.bisect_right(self.values, x)) / 2.0) / n

    def _split(self) -> Optional[float]:
        v, n = self.values, len(self.values)
        if n < 2 or v[0] == v[-1]:
            return v[0] if n else None
        total, csum, best, best_t = sum(v), 0.0, -1.0, v[0]
        for k in range(1, n):
            csum += v[k - 1]
            if v[k] == v[k - 1]:
                continue
            w0, w1 = k, n - k
            gap = csum / w0 - (total - csum) / w1
            score = w0 * w1 * gap * gap
            if score > best:
                best, best_t = score, (v[k - 1] + v[k]) / 2.0
        return best_t

    def add(self, x: float, rng: random.Random) -> None:
        if len(self.values) >= _RESERVOIR:
            self.values.pop(rng.randrange(len(self.values)))
        bisect.insort(self.values, float(x))
        self.adds += 1
        if self.thr is None or self.adds % _SPLIT_EVERY == 0:
            self.thr = self._split()
            self.tail_thr = self._tail_split()

    @staticmethod
    def _otsu(v: List[float]) -> Tuple[Optional[float], float]:
        """(best split, separability eta in 0..1) of a sorted sample."""
        n = len(v)
        if n < 2 or v[0] == v[-1]:
            return None, 0.0
        total = sum(v)
        mean = total / n
        var = sum((x - mean) ** 2 for x in v) / n
        csum, best, best_t = 0.0, -1.0, None
        for k in range(1, n):
            csum += v[k - 1]
            if v[k] == v[k - 1]:
                continue
            w0, w1 = k, n - k
            gap = csum / w0 - (total - csum) / w1
            score = w0 * w1 * gap * gap
            if score > best:
                best, best_t = score, (v[k - 1] + v[k]) / 2.0
        eta = (best / (n * n)) / var if var > 0.0 and best > 0.0 else 0.0
        return best_t, min(1.0, eta)

    def _tail_split(self) -> Optional[float]:
        """The lowest clearly separate mode of the LOWER class, when there is one."""
        if self.thr is None:
            return None
        lower = self.values[: bisect.bisect_right(self.values, self.thr)]
        if len(lower) < 2 * _TAIL_MIN:
            return None
        cut, eta = self._otsu(lower)
        if cut is None or eta < _TAIL_ETA or bisect.bisect_right(lower, cut) < _TAIL_MIN:
            return None
        return cut

    def tail_high(self, x: float) -> int:
        return 1 if (self.tail_thr is not None and x <= self.tail_thr) else 0


def _bit_prob(counts: Optional[List[int]], bit: int) -> float:
    n0, n1 = counts or [0, 0]
    return ((n1 if bit else n0) + _KT_ALPHA) / (n0 + n1 + 2 * _KT_ALPHA)


def _bump(counts: Optional[List[int]], bit: int) -> List[int]:
    out = list(counts or [0, 0])
    out[1 if bit else 0] += 1
    return out


def _context(path: Tuple[int, ...], hist: Tuple[Tuple[int, ...], ...]) -> int:
    """Pack the source bits of ``path`` from the events preceding the target.

    ``hist`` is oldest..newest; path step i (0-based, excluding the target) is
    read from the event ``len(path)-1-i`` steps before the arriving one.
    """
    need = len(path) - 1
    code = 0
    for i in range(need):
        code |= hist[len(hist) - need + i][path[i]] << i
    return code


_USER_ROLES = {"user", "historical_user", "external_user", "human"}
_RESPONDER_ROLES = {"assistant", "historical_other_assistant", "responder", "aurora", "aurora_self", "self"}


def role_subject(actor: Any) -> str:
    """Subject key by ROLE in the exchange, so history and live turns share subjects.

    The party that opens/addresses is ``external_user`` whether it spoke in the
    archive or live; the party that answers is ``responder`` whether it was another
    assistant in the archive or Aurora herself.  That equivalence is the
    apprenticeship framing the historical environment already rests on.
    """
    raw = str(actor or "").strip().lower()
    if raw in _USER_ROLES:
        return "external_user"
    if raw in _RESPONDER_ROLES:
        return "responder"
    return str(actor or "")


class _Stream:
    """Context of one event stream (history replay, live conversation, ...)."""

    def __init__(self, state: Optional[Mapping[str, Any]] = None) -> None:
        state = dict(state or {})
        self.next_index = int(state.get("next_index", 0) or 0)
        self.last_episode_id = str(state.get("last_episode_id", "") or "")
        self.last_actor = str(state.get("last_actor", "") or "")
        self.episode_actors = set(str(a) for a in (state.get("episode_actors") or []))
        self.hist: Deque[Tuple[int, ...]] = deque(maxlen=MAX_PATH - 1)
        for vec in list(state.get("hist") or []):
            self.hist.append(tuple(int(x) for x in vec))
        self.hist_subject = str(state.get("hist_subject", "") or "")

    def state(self) -> Dict[str, Any]:
        return {
            "next_index": self.next_index, "last_episode_id": self.last_episode_id,
            "last_actor": self.last_actor, "episode_actors": sorted(self.episode_actors),
            "hist": [list(v) for v in self.hist], "hist_subject": self.hist_subject,
        }


class AuroraResolutionLedger:
    """Per-subject discovery of the axis paths a subject must be seen through."""

    def __init__(self, *, state_dir: str = "aurora_state", persist: bool = True, max_path: int = DEFAULT_MAX_PATH,
                 tail: Optional[bool] = None, lexical: Optional[bool] = None) -> None:
        self.max_path = max(MIN_PREDICTIVE_PATH, min(MAX_PATH, int(max_path)))
        self.tail = bool(os.environ.get("AURORA_RESOLUTION_TAIL") == "1") if tail is None else bool(tail)
        self._symbols: Tuple[str, ...] = (AXES + TAIL_SYMBOLS) if self.tail else AXES
        self.lexical = bool(os.environ.get("AURORA_LEXICAL_SYMBOLS") == "1") if lexical is None else bool(lexical)
        self._lex: Any = None
        if self.lexical:
            from aurora_internal.aurora_lexical_structure import LexicalStructure
            self._lex = LexicalStructure()
        self._lex_epochs: Tuple[int, ...] = self._lex.epoch_vector() if self._lex is not None else ()
        self._active_idx: List[int] = []
        self._paths_by_length, self._z_crit = {}, {}
        self._refresh_active()
        self.state_dir = str(state_dir or "aurora_state")
        self.persist = bool(persist)
        self.storage_path = Path(self.state_dir) / "resolution_ledger.json"

        self._streams: Dict[str, _Stream] = {}
        self._raw: Dict[str, _Running] = {}      # "<subject>:<root>" -> that subject's own running distribution
        self._ring: Dict[str, List[Tuple[Tuple[int, ...], ...]]] = {}
        self._n_obs: Dict[str, int] = {}
        self._loads: Dict[str, Dict[str, List[int]]] = {}
        # tables[subject][path_key] = {"ctx": {code: [n0, n1]}, "null": {...}, "marg": [n0, n1]}
        self._tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # stats[subject][path_key] = running sums + batch means of the decisive difference
        self._stats: Dict[str, Dict[str, Dict[str, float]]] = {}
        # best shallower path per (length, target), refreshed each block; and the baseline each path was held to
        self._best: Dict[str, Dict[str, List[Any]]] = {}
        self._baseline_used: Dict[str, Dict[str, str]] = {}
        self._streak: Dict[str, Dict[str, int]] = {}
        self._disc_cache: Dict[str, Tuple[int, List[str]]] = {}
        self._adopted: Dict[str, set] = {}      # paths whose expectation table was taken over from a crystal
        self._crystals: Any = None
        self._last_sync = 0
        self._last_waveform: Tuple[float, ...] = ()
        self._family_cache: Dict[str, Tuple[Any, List[List[Dict[str, Any]]]]] = {}
        self._emitted = 0
        self._unsubmitted = 0
        self._last_emission: Dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Facts: one raw, label-free question per root constraint
    # ------------------------------------------------------------------

    def _facts(self, *, boundary: bool, actor: str, text_length: int, elapsed: Optional[float],
               first_act: bool, last_actor: str = "") -> Dict[str, float]:
        gap = 0.0
        if elapsed is not None:
            try:
                value = float(elapsed)
                gap = max(0.0, value) if math.isfinite(value) else 0.0
            except Exception:
                gap = 0.0
        return {
            "X": 1.0 if boundary else 0.0,                                   # did presence change?
            "T": math.log1p(gap),                                            # how long after what came before?
            "N": math.log1p(max(0, int(text_length))),                       # what did the act cost?
            "B": 1.0 if first_act else 0.0,                                  # did this actor cross into the boundary?
            "A": 1.0 if (last_actor and actor != last_actor) else 0.0,  # did the actor change?
        }

    def _bits(self, facts: Mapping[str, float], rng: random.Random, subject: str,
              lex_bits: Tuple[int, ...] = ()) -> Tuple[int, ...]:
        """Each root read against the ACTING SUBJECT's own distribution.

        Pooling every actor into one distribution gives a split that means nothing for any of
        them (a brief message from one party and a brief one from another sit at different
        scales), and a rare brief cluster is swallowed by ordinary short content.
        """
        bits: List[int] = []
        tails: Dict[str, int] = {}
        ranks: List[float] = []
        for ax in AXES:
            run = self._raw.setdefault(f"{subject}:{ax}", _Running())
            value = float(facts[ax])
            bits.append(run.high(value))
            tails[ax] = run.tail_high(value)
            ranks.append(run.rank(value))
            run.add(value, rng)
        self._last_waveform = tuple(ranks)
        for sym in self._symbols[len(AXES):]:                 # tail symbols: 1 = in the extreme-low tail
            bits.append(tails[sym.upper()])
        if self._lex is not None:            # full fixed layout: roots, tail slots (0 when off), then the word classes
            bits.extend([0] * (len(AXES) + len(TAIL_SYMBOLS) - len(bits)))
            bits.extend(list(lex_bits)[: len(LEX_SYMBOLS)])
            bits.extend([0] * (len(AXES) + len(TAIL_SYMBOLS) + len(LEX_SYMBOLS) - len(bits)))
        return tuple(bits)

    # ------------------------------------------------------------------
    # Scoring (prequential, permutation null, paired against the parent)
    # ------------------------------------------------------------------

    def _stat(self, subject: str, key: str) -> Dict[str, float]:
        per = self._stats.setdefault(subject, {})
        return per.setdefault(key, {
            "n": 0.0, "gain": 0.0, "null": 0.0,
            "blk_n": 0.0, "blk_sum": 0.0, "nb": 0.0, "bsum": 0.0, "bsq": 0.0, "dsum": 0.0,
        })

    def _score(self, subject: str, hist: Tuple[Tuple[int, ...], ...], null_hist: Tuple[Tuple[int, ...], ...],
               bits_now: Tuple[int, ...]) -> None:
        tables = self._tables.setdefault(subject, {})
        obs = self._n_obs.get(subject, 0)
        step: Dict[Tuple[int, ...], float] = {}
        for length in range(MIN_PREDICTIVE_PATH, self.max_path + 1):
            if len(hist) < length - 1 or obs < _OBS_PER_CONTEXT * (2 ** (length - 1)):
                break
            for path in self._paths_by_length[length]:
                key = _path_key(path)
                tab = tables.setdefault(key, {"ctx": {}, "null": {}, "marg": [0, 0]})
                bit = bits_now[path[-1]]
                ctx = _context(path, hist)
                nctx = _context(path, null_hist) if len(null_hist) >= length - 1 else ctx
                p_marg = _bit_prob(tab["marg"], bit)
                cond = tab["ctx"].get(str(ctx))
                nul = tab["null"].get(str(nctx))
                gain = math.log2(_bit_prob(cond, bit) / p_marg)
                null = math.log2(_bit_prob(nul, bit) / p_marg)
                tab["ctx"][str(ctx)] = _bump(cond, bit)
                tab["null"][str(nctx)] = _bump(nul, bit)
                tab["marg"] = _bump(tab["marg"], bit)
                lift = gain - null
                step[path] = lift
                if length == MIN_PREDICTIVE_PATH:
                    diff = lift
                else:
                    base = self._baseline(subject, length, path[-1])
                    diff = lift - (step.get(_path_from_key(base), 0.0) if base else 0.0)
                    if base:
                        self._baseline_used.setdefault(subject, {})[key] = base
                st = self._stat(subject, key)
                st["n"] += 1.0
                st["gain"] += gain
                st["null"] += null
                st["dsum"] += diff
                st["blk_n"] += 1.0
                st["blk_sum"] += diff
                if st["blk_n"] >= _BLOCK:
                    mean = st["blk_sum"] / st["blk_n"]
                    st["nb"] += 1.0
                    st["bsum"] += mean
                    st["bsq"] += mean * mean
                    st["blk_n"] = 0.0
                    st["blk_sum"] = 0.0

    def _baseline(self, subject: str, length: int, target: int) -> str:
        """Best shallower path (any length below ``length``) for this target root."""
        best_key, best_mean = "", float("-inf")
        for shorter in range(MIN_PREDICTIVE_PATH, length):
            entry = self._best.get(subject, {}).get(f"{shorter}:{target}")
            if entry and float(entry[1]) > best_mean:
                best_key, best_mean = str(entry[0]), float(entry[1])
        return best_key

    def _refresh_best(self, subject: str) -> None:
        """Re-pick the best path per (length, target) from the running lifts."""
        best: Dict[str, List[Any]] = {}
        for key, st in self._stats.get(subject, {}).items():
            if not self._path_is_current(key):
                continue
            path = _path_from_key(key)
            if st.get("n", 0.0) < 2 * _BLOCK:
                continue
            mean = (st["gain"] - st["null"]) / st["n"]
            slot = f"{len(path)}:{path[-1]}"
            if slot not in best or mean > float(best[slot][1]):
                best[slot] = [key, mean]
        self._best[subject] = best

    @staticmethod
    def _z(st: Mapping[str, float]) -> Tuple[float, float]:
        nb = st.get("nb", 0.0)
        if nb < _MIN_BLOCKS:
            return 0.0, 0.0
        mean = st["bsum"] / nb
        var = max((st["bsq"] / nb) - mean * mean, 1e-12) * nb / max(nb - 1.0, 1.0)
        return mean, mean / math.sqrt(var / nb)

    def _significant(self, subject: str) -> List[Dict[str, Any]]:
        """Paths that beat the null (length 2) or the best shallower path (deeper): necessary, not sufficient."""
        out: List[Dict[str, Any]] = []
        for key, st in self._stats.get(subject, {}).items():
            path = _path_from_key(key)
            length = len(path)
            mean, z = self._z(st)
            if mean > 0.0 and z >= self._z_crit[length]:
                n = max(st["n"], 1.0)
                out.append({
                    "path": key,
                    "length": length,
                    "resolution": REC_DIMS[length],
                    "target": SYMBOLS[path[-1]],
                    "diff_bits": round(mean, 6),
                    "lift_bits": round((st["gain"] - st["null"]) / n, 6),
                    "z": round(z, 3),
                    "baseline": self._baseline_used.get(subject, {}).get(key) if length > MIN_PREDICTIVE_PATH else None,
                    "extension": SYMBOLS[path[0]],
                })
        return sorted(out, key=lambda r: -r["diff_bits"])

    # ------------------------------------------------------------------
    # Irreducibility: equivalence families
    # ------------------------------------------------------------------

    @staticmethod
    def _same_family(pa: List[float], pb: List[float]) -> bool:
        """Do two paths make essentially the same distinction over the same observed events?"""
        n = len(pa)
        if n < _EQUIV_MIN or n != len(pb):
            return False
        ma, mb = sum(pa) / n, sum(pb) / n
        spread_a = sum(abs(x - ma) for x in pa) / n
        spread_b = sum(abs(x - mb) for x in pb) / n
        gap = sum(abs(x - y) for x, y in zip(pa, pb)) / n
        return gap <= _EQUIV_TOL * max(spread_a, spread_b, 1e-9)

    def _predictions(self, subject: str, key: str) -> List[float]:
        """What this path predicts for each observed event (a reservoir sample of this subject's history)."""
        tab = self._tables.get(subject, {}).get(key)
        if not tab:
            return []
        path = _path_from_key(key)
        return [
            _bit_prob(tab["ctx"].get(str(_context(path, hist))), 1)
            for hist in self._ring.get(subject, []) if len(hist) >= len(path) - 1
        ]

    def _families(self, subject: str, found: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group significant paths into equivalence families (same target, same predictions).

        Within a family the canonical member is the simplest (shortest, then strongest); the rest
        share its ancestry and are held provisionally: they become independent the moment
        experience distinguishes them, because families are re-derived from current evidence.
        """
        preds = {rec["path"]: self._predictions(subject, rec["path"]) for rec in found}
        parent = {rec["path"]: rec["path"] for rec in found}

        def root(p: str) -> str:
            while parent[p] != p:
                parent[p] = parent[parent[p]]
                p = parent[p]
            return p

        for i, a in enumerate(found):
            for b in found[i + 1:]:
                if a["target"] == b["target"] and self._same_family(preds[a["path"]], preds[b["path"]]):
                    parent[root(a["path"])] = root(b["path"])
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for rec in found:
            groups.setdefault(root(rec["path"]), []).append(rec)
        families = [sorted(g, key=lambda r: (r["length"], -r["diff_bits"], r["path"])) for g in groups.values()]
        return sorted(families, key=lambda fam: -fam[0]["diff_bits"])

    def discovered(self, subject: str, include_aliases: bool = False) -> List[Dict[str, Any]]:
        """Irreducible representations: one canonical path per equivalence family.

        A path that merely re-divides the observations another path already divides (its extra
        axis can be removed or substituted without changing the prediction) is not a separate
        discovery.  Aliases are returned only on request, tagged with the canonical path.
        """
        found = self._significant(subject)
        key = (self._n_obs.get(subject, 0) // _BLOCK, tuple(r["path"] for r in found))
        cached = self._family_cache.get(subject)
        if cached is not None and cached[0] == key:
            families = cached[1]
        else:
            families = self._families(subject, found)
            self._family_cache[subject] = (key, families)
        out: List[Dict[str, Any]] = []
        for fam in families:
            head = dict(fam[0])
            head["canonical"] = True
            head["family"] = [r["path"] for r in fam[1:]]
            out.append(head)
            if include_aliases:
                for rec in fam[1:]:
                    out.append({**rec, "canonical": False, "alias_of": fam[0]["path"]})
        return sorted(out, key=lambda r: -r["diff_bits"])

    def family_of(self, subject: str, path_key: str) -> List[str]:
        """The paths held as aliases of this canonical representation (its shared ancestry)."""
        for rec in self.discovered(subject):
            if rec["path"] == path_key:
                return list(rec.get("family") or [])
        return []

    def natural_resolution(self, subject: str) -> Dict[str, int]:
        """Per target root: the deepest path length that earned its keep (0 = none did)."""
        natural = {ax: 0 for ax in AXES}
        for rec in self.discovered(subject):
            if rec["target"].upper() in natural:       # a word-class target is not a root
                natural[rec["target"].upper()] = max(natural[rec["target"].upper()], int(rec["length"]))
        return natural

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def _stream(self, name: str) -> _Stream:
        return self._streams.setdefault(str(name or "history"), _Stream())

    def observe_event(
        self,
        *,
        event_index: Optional[int] = None,
        event_id: str = "",
        episode_id: str = "",
        actor: str = "",
        text_length: int = 0,
        elapsed_seconds: Optional[float] = None,
        episode_gap_seconds: Optional[float] = None,
        warp_field: Any = None,
        stream: str = "history",
        tokens: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Admit one event into ``stream``.  Idempotent on ``event_index`` per stream.

        Streams keep their own context (previous events, episode, actor) but share
        every distribution, table and statistic: what history teaches applies to
        live turns, and live turns add to the same evidence.
        """
        name = str(stream or "history")
        st = self._stream(name)
        index = st.next_index if event_index is None else int(event_index)
        if index < st.next_index:
            return {"observed": False, "reason": "already_observed", "event_index": index, "stream": name}
        st.next_index = index + 1

        actor = str(actor or "")
        episode_id = str(episode_id or "")
        boundary = bool(episode_id != st.last_episode_id)
        if boundary:
            st.episode_actors = set()
        first_act = actor not in st.episode_actors
        elapsed = episode_gap_seconds if (boundary and episode_gap_seconds is not None) else elapsed_seconds

        rng = random.Random(_stable_seed(name, index, actor, event_id))
        lex_bits: Tuple[int, ...] = ()
        lex_changed = False
        if self._lex is not None:                  # the words of the event, related to the words around it
            lex_bits, lex_changed = self._lex.observe(list(tokens or []), name, episode_id)
        bits_now = self._bits(
            self._facts(boundary=boundary, actor=actor, text_length=text_length, elapsed=elapsed,
                        first_act=first_act, last_actor=st.last_actor), rng, actor, lex_bits
        )
        if self._lex is not None:
            self._lex.note_waveform(lex_bits, self._last_waveform)
            if lex_changed:
                new_epochs = self._lex.epoch_vector()
                self._retire_reused_lexical_slots(self._lex_epochs, new_epochs)
                self._lex_epochs = new_epochs
                self._refresh_active()

        # Length 1: the subject's own coordinate on each root (descriptive).
        loads = self._loads.setdefault(actor, {ax: [0, 0] for ax in AXES})
        for i, ax in enumerate(AXES):
            loads[ax][0] += bits_now[i]
            loads[ax][1] += 1

        # Score every active path against what actually arrived.
        subject = st.hist_subject
        hist = tuple(st.hist)
        scored = False
        if subject and hist:
            ring = self._ring.setdefault(subject, [])
            null_hist = ring[rng.randrange(len(ring))] if ring else hist
            self._n_obs[subject] = self._n_obs.get(subject, 0) + 1
            self._score(subject, hist, null_hist, bits_now)
            scored = True
            if len(hist) == MAX_PATH - 1:
                if len(ring) >= _NULL_MEMORY:
                    ring.pop(rng.randrange(len(ring)))
                ring.append(hist)

        st.hist.append(bits_now)
        st.hist_subject = actor
        st.last_actor = actor
        st.last_episode_id = episode_id
        st.episode_actors.add(actor)

        if scored and self._n_obs[subject] % _BLOCK == 0:
            self._refresh_best(subject)
        emitted = None
        if scored and self._n_obs[subject] % _EVAL_EVERY == 0:
            emitted = self._evaluate(subject, warp_field)
        return {"observed": True, "event_index": index, "subject": subject, "emitted": emitted, "stream": name}

    # ------------------------------------------------------------------
    # Gap -> WARP
    # ------------------------------------------------------------------

    def _profile(self, subject: str, found: Mapping[str, Any]) -> Dict[str, float]:
        path = _path_from_key(str(found["path"]))
        weight = {ax: 0.0 for ax in AXES}
        for i in path:
            self._add_weight(weight, SYMBOLS[i])
        self._add_weight(weight, SYMBOLS[path[-1]])          # the target root carries the pressure
        scale = sum(weight.values()) or 1.0
        profile: Dict[str, float] = {}
        for ax in AXES:
            magnitude = weight[ax] / scale
            profile[_NEGATIVE_ISTATE[ax]] = round(magnitude, 6)
            profile[_POSITIVE_ISTATE[ax]] = round(magnitude * 0.18, 6)
        by_length: Dict[int, float] = {}
        for rec in self.discovered(subject):
            by_length[int(rec["length"])] = max(by_length.get(int(rec["length"]), 0.0), float(rec["diff_bits"]))
        peak = max(by_length.values()) if by_length else 0.0
        for level, dim in enumerate(REC_DIMS):
            profile[dim] = round(by_length.get(level, 0.0) / peak, 6) if peak > 0 else 0.0
        profile[REC_DIMS[int(found["length"])]] = 1.0
        return profile

    def _evaluate(self, subject: str, warp_field: Any) -> Optional[Dict[str, Any]]:
        current = self.discovered(subject)
        streak = self._streak.setdefault(subject, {})
        seen = {rec["path"] for rec in current}
        for key in list(streak):
            if key not in seen:
                streak.pop(key)
        for key in seen:
            streak[key] = streak.get(key, 0) + 1
        found_all = [rec for rec in current if streak.get(rec["path"], 0) >= _CONFIRM_LOOKS]
        if not found_all:
            return None
        found = found_all[0]
        lift = float(found["lift_bits"])
        share = _clip01(float(found["diff_bits"]) / lift) if lift > 0.0 else 0.0
        demand = WarpDemand(
            source="resolution_ledger",
            layer="experience_resolution",
            trigger=WarpTrigger.MISSING_REPRESENTATION,
            unresolved_text=(
                f"subject {subject}: root {found['target']} follows from the path "
                f"{found['path']} ({found['resolution']}); no shallower path for that root sufficed"
            )[:600],
            expected={"path": found["path"], "resolution": found["resolution"], "diff_bits": found["diff_bits"]},
            actual={"discovered": found_all[:8]},
            participants=["event_stream", "resolution_ledger"],
            profile=self._profile(subject, found),
            local_attempts=["event_level_prediction", "shallower_path_prediction"],
            severity=min(_MAX_SEVERITY, share),
            persistence_key=f"resolution:{subject}:{found['path']}",
        )
        record = {"subject": subject, "path": found["path"], "length": found["length"],
                  "diff_bits": found["diff_bits"], "time": time.time()}
        self._last_emission = record
        if warp_field is not None and hasattr(warp_field, "submit"):
            try:
                warp_field.submit(demand)
                self._emitted += 1
                return record
            except Exception:
                pass
        self._unsubmitted += 1
        return record

    # ------------------------------------------------------------------
    # Registry of (subject, axis-path) representations
    # ------------------------------------------------------------------

    def representations(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for subject in sorted(set(self._loads) | set(self._stats)):
            for ax in AXES:
                high, n = self._loads.get(subject, {}).get(ax, [0, 0])
                out.append({
                    "subject": subject, "path": ax, "length": 1, "resolution": REC_DIMS[1],
                    "kind": "coordinate", "observations": int(n),
                    "load": round(high / n, 6) if n else 0.0,
                })
            for rec in self.discovered(subject):
                out.append({"subject": subject, "kind": "path", "identity_path": self.representation_identity(rec["path"]), **rec})
        return out

    def last_bits(self, stream: str = "history") -> Tuple[str, Tuple[int, ...]]:
        """(actor of the newest event in ``stream``, its five high/low bits in X,T,N,B,A order)."""
        st = self._streams.get(str(stream or "history"))
        if st is None:
            return "", ()
        return st.hist_subject, (st.hist[-1] if st.hist else ())

    def expectations(self, subject: str, stream: str = "history") -> List[Dict[str, Any]]:
        """What each discovered path of ``subject`` expects of the NEXT event in ``stream``.

        Valid for the subject whose event just arrived (``last_bits(stream)[0]``).  The
        discovered set is refreshed on the block cadence, not per event.
        """
        n_obs = self._n_obs.get(subject, 0)
        cached = self._disc_cache.get(subject)
        if cached is None or n_obs - cached[0] >= _BLOCK:
            cached = (n_obs, [rec["path"] for rec in self.discovered(subject)])
            self._disc_cache[subject] = cached
        hist = tuple(self._stream(stream).hist)
        out: List[Dict[str, Any]] = []
        for key in list(cached[1]) + [k for k in sorted(self._adopted.get(subject, set())) if k not in cached[1]]:
            path = _path_from_key(key)
            tab = self._tables.get(subject, {}).get(key)
            if tab is None or len(hist) < len(path) - 1:
                continue
            counts = tab["ctx"].get(str(_context(path, hist)), [0, 0])
            out.append({
                "subject": subject, "path": key, "target": SYMBOLS[path[-1]],
                "p_high": round(_bit_prob(counts, 1), 6),
                "p_high_marginal": round(_bit_prob(tab["marg"], 1), 6),
                "support": int(sum(counts)),
            })
        return out

    def table_of(self, subject: str, path_key: str) -> Dict[str, Any]:
        """The expectation table of one path (what a crystal facet records)."""
        tab = self._tables.get(subject, {}).get(path_key)
        if not tab:
            return {}
        return {"ctx": {k: list(v) for k, v in tab["ctx"].items()}, "marg": list(tab["marg"])}

    def adopt_table(self, subject: str, path_key: str, tab: Mapping[str, Any]) -> None:
        """Resume a path from the table a crystal already holds, instead of recomputing it.

        Only where this ledger has no table of its own; the adopted path keeps being
        scored and updated from then on.
        """
        if not tab or path_key in self._tables.get(subject, {}):
            return
        self._tables.setdefault(subject, {})[path_key] = {
            "ctx": {str(k): list(v) for k, v in dict(tab.get("ctx") or {}).items()},
            "null": {}, "marg": list(tab.get("marg") or [0, 0]),
        }
        self._adopted.setdefault(subject, set()).add(path_key)

    def _retire_reused_lexical_slots(self, old: Tuple[int, ...], new: Tuple[int, ...]) -> None:
        """Close developmental evidence when an L-slot acquires a new identity.

        Earned knowledge survives separately as a crystal recognition kernel.
        Candidate statistics belong to the slot occupant that generated them
        and must never leak into a later occupant of the same temporary handle.
        """
        changed = {k for k in range(min(len(old), len(new))) if old[k] != new[k]}
        if not changed:
            return
        labels = {f"L{k}" for k in changed}
        def touches(key: str) -> bool:
            return any(part in labels for part in str(key).split(">"))
        for subject in set(self._tables) | set(self._stats) | set(self._streak) | set(self._baseline_used):
            for mapping in (self._tables.get(subject, {}), self._stats.get(subject, {}),
                            self._streak.get(subject, {}), self._baseline_used.get(subject, {})):
                for key in list(mapping):
                    if touches(key):
                        mapping.pop(key, None)
            adopted = self._adopted.get(subject)
            if adopted:
                self._adopted[subject] = {key for key in adopted if not touches(key)}
            self._disc_cache.pop(subject, None)
            self._family_cache.pop(subject, None)
        self._best.clear()  # baselines may have pointed at a retired path

    def _path_is_current(self, key: str) -> bool:
        if self._lex is None:
            return not any(part.startswith("L") for part in str(key).split(">"))
        active = {f"L{k}" for k in self._lex.active_slots()}
        return all((not part.startswith("L")) or part in active for part in str(key).split(">"))

    def representation_identity(self, path_key: str) -> str:
        """Epoch-stamped identity for a path while keeping its live path compact."""
        parts: List[str] = []
        for part in str(path_key).split(">"):
            if part.startswith("L") and part[1:].isdigit() and self._lex is not None:
                parts.append(self._lex.identity(int(part[1:])))
            else:
                parts.append(part)
        return ">".join(parts)

    def lexical_kernel(self, symbol: str) -> Dict[str, Any]:
        if self._lex is None or not str(symbol).startswith("L") or not str(symbol)[1:].isdigit():
            return {}
        return self._lex.kernel(int(str(symbol)[1:]))

    def recognition_kernel(self, subject: str, path_key: str) -> Dict[str, Any]:
        """Smallest persisted recognizer for an earned irreducible representation.

        The canonical path is already the shortest member of its equivalence
        family.  We retain only that path, aggregate expectation counts, and
        compact lexical anchors/coordinates needed to recognize it later.
        No training examples or event history are copied into the kernel.
        """
        identity = self.representation_identity(path_key)
        lexical: Dict[str, Any] = {}
        for part in str(path_key).split(">"):
            if part.startswith("L") and part not in lexical:
                item = self.lexical_kernel(part)
                if item:
                    lexical[part] = item
        tab = self.table_of(subject, path_key)
        marg = list(tab.get("marg") or [0, 0])
        compact_ctx: Dict[str, List[int]] = {}
        for ctx, counts in dict(tab.get("ctx") or {}).items():
            vals = [int(counts[0]), int(counts[1])]
            if sum(vals) > 0:
                compact_ctx[str(ctx)] = vals
        kid = hashlib.sha256(f"{subject}|{identity}".encode("utf-8")).hexdigest()[:20]
        return {
            "v": 1, "id": f"RK:{kid}", "subject": str(subject),
            "path": str(path_key), "identity_path": identity,
            "source": str(path_key).split(">")[:-1], "target": str(path_key).split(">")[-1],
            "lexical": lexical, "ctx": compact_ctx, "marg": marg,
            "coordinate": self.path_lexical_coordinates(path_key),
            "family": self.family_of(subject, path_key),
        }

    def _refresh_active(self) -> None:
        """The alphabet paths are drawn from: the roots, the tail symbols if enabled, and every class discovered so far."""
        base = list(range(len(AXES))) + (list(range(len(AXES), len(AXES) + len(TAIL_SYMBOLS))) if self.tail else [])
        lex = [len(AXES) + len(TAIL_SYMBOLS) + k for k in (self._lex.active_slots() if self._lex is not None else [])]
        self._active_idx = base + lex
        self._paths_by_length, self._z_crit = _alphabet(self._active_idx)
        if hasattr(self, "_family_cache"):          # not yet built while the constructor is still running
            self._family_cache.clear()

    def _add_weight(self, weight: Dict[str, float], symbol: str) -> None:
        root = symbol.upper()
        if root in weight:
            weight[root] += 1.0
        elif symbol.startswith("L") and self._lex is not None:
            for k, v in self._lex.coordinate(int(symbol[1:])).items():
                weight[k] += abs(float(v))

    def lexical_coordinate(self, symbol: str) -> Dict[str, float]:
        if self._lex is None or not str(symbol).startswith("L"):
            return {}
        return self._lex.coordinate(int(str(symbol)[1:]))

    def path_lexical_coordinates(self, path_key: str) -> Dict[str, Dict[str, float]]:
        """Roots-coordinates of the word classes in a path, so its representation still lands on a crystal."""
        return {s: self.lexical_coordinate(s) for s in str(path_key).split(">") if s.startswith("L")}

    def last_waveform(self) -> Tuple[float, ...]:
        """The newest event's position on each root (X,T,N,B,A) in its actor's own distribution.

        This is the input's waveform distribution: what crystals are stamped with, instead of a
        mode default.
        """
        return self._last_waveform

    def next_event_index(self, stream: str = "history") -> int:
        """First event index ``stream`` has not yet observed (resume cursor)."""
        return self._stream(stream).next_index

    def status(self) -> Dict[str, Any]:
        subjects = sorted(set(self._loads) | set(self._stats))
        return {
            "schema": SCHEMA,
            "events_observed_through_index": self._stream("history").next_index,
            "streams": {n: s.next_index for n, s in self._streams.items()},
            "subjects": subjects,
            "observations": {s: int(self._n_obs.get(s, 0)) for s in subjects},
            "active_path_length": {
                s: max([MIN_PREDICTIVE_PATH - 1] + [
                    length for length in range(MIN_PREDICTIVE_PATH, self.max_path + 1)
                    if self._n_obs.get(s, 0) >= _OBS_PER_CONTEXT * (2 ** (length - 1))
                ]) for s in subjects
            },
            "natural_resolution": {s: self.natural_resolution(s) for s in subjects},
            "discovered": {s: self.discovered(s)[:6] for s in subjects},
            "demands_submitted": self._emitted,
            "demands_unsubmitted": self._unsubmitted,
            "last_emission": dict(self._last_emission),
            "lexical_classes": self._lex.describe() if self._lex is not None else {},
            "storage_path": str(self.storage_path),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Hypotheses on the crystals (no log of our own)
    # ------------------------------------------------------------------

    def attach_crystals(self, store: Any) -> int:
        """Keep the research state ON the crystals as hypotheses.

        Restores whatever the crystals already hold so discovery continues where it stood.  A
        state that still lives in an older file is migrated at the first sync.  Returns the
        number of hypotheses restored.
        """
        self._crystals = store
        calibration, hypotheses = store.read()
        if self._lex is not None and hasattr(store, "read_lexical"):
            lex_state = store.read_lexical()
            if lex_state:
                self._lex.restore(lex_state)
                self._lex_epochs = self._lex.epoch_vector()
                self._refresh_active()
        if calibration:
            self._restore(calibration, hypotheses)
        return len(hypotheses) if calibration else 0

    @staticmethod
    def _sketch(values: List[float]) -> List[float]:
        n = len(values)
        return list(values) if n <= _SKETCH else [values[min(n - 1, (i * n) // _SKETCH)] for i in range(_SKETCH)]

    def _calibration_record(self) -> Dict[str, Any]:
        return {
            "v": 1, "schema": SCHEMA,
            "raw": {ax: {"values": self._sketch(run.values), "adds": run.adds, "thr": run.thr}
                    for ax, run in self._raw.items()},
            "streams": {n: s.state() for n, s in self._streams.items()},
            "n_obs": dict(self._n_obs), "loads": self._loads,
            "ring": {s: [[list(v) for v in h] for h in hs[-_NULL_MEMORY:]] for s, hs in self._ring.items()},
            "best": self._best, "streak": self._streak, "baseline_used": self._baseline_used,
            "emitted": self._emitted, "unsubmitted": self._unsubmitted, "last_emission": self._last_emission,
        }

    def sync_crystals(self, force: bool = False) -> int:
        """Write calibration and every path under test (>= one block of evidence) as hypotheses."""
        if self._crystals is None:
            return 0
        total = sum(self._n_obs.values())
        if not force and total - self._last_sync < _HYP_SYNC_EVERY:
            return 0
        records: List[Dict[str, Any]] = []
        for subject, per in self._stats.items():
            for key, st in per.items():
                tab = self._tables.get(subject, {}).get(key)
                if tab is None or st.get("n", 0.0) < _BLOCK:
                    continue
                records.append({"subject": subject, "path": key, "identity_path": self.representation_identity(key), "st": st,
                                "tab": {"ctx": tab["ctx"], "null": tab["null"], "marg": tab["marg"]},
                                "lexc": self.path_lexical_coordinates(key)})
        wrote = self._crystals.write(self._calibration_record(), records)
        if self._lex is not None and hasattr(self._crystals, "write_lexical"):
            self._crystals.write_lexical(self._lex.state())
        self._last_sync = total
        return wrote

    def _restore(self, calibration: Mapping[str, Any], hypotheses: List[Mapping[str, Any]]) -> None:
        for key, state in dict(calibration.get("raw") or {}).items():
            self._raw[str(key)] = _Running(state)
        self._streams = {str(n): _Stream(v) for n, v in dict(calibration.get("streams") or {}).items()}
        self._n_obs = {str(k): int(v) for k, v in dict(calibration.get("n_obs") or {}).items()}
        self._loads = {s: {ax: list(v) for ax, v in per.items()} for s, per in dict(calibration.get("loads") or {}).items()}
        self._ring = {
            s: [tuple(tuple(int(x) for x in v) for v in h) for h in hs]
            for s, hs in dict(calibration.get("ring") or {}).items()
        }
        self._best = dict(calibration.get("best") or {})
        self._streak = {str(k): {str(a): int(b) for a, b in dict(v).items()} for k, v in dict(calibration.get("streak") or {}).items()}
        self._baseline_used = {str(k): dict(v) for k, v in dict(calibration.get("baseline_used") or {}).items()}
        self._emitted = int(calibration.get("emitted", 0) or 0)
        self._unsubmitted = int(calibration.get("unsubmitted", 0) or 0)
        self._last_emission = dict(calibration.get("last_emission") or {})
        for rec in hypotheses:
            subject, key = str(rec["subject"]), str(rec["path"])
            identity = str(rec.get("identity_path") or key)
            if "@" in identity and identity != self.representation_identity(key):
                continue
            if not self._path_is_current(key):
                continue
            tab = dict(rec.get("tab") or {})
            self._tables.setdefault(subject, {})[key] = {
                "ctx": {str(k): list(v) for k, v in dict(tab.get("ctx") or {}).items()},
                "null": {str(k): list(v) for k, v in dict(tab.get("null") or {}).items()},
                "marg": list(tab.get("marg") or [0, 0]),
            }
            self._stats.setdefault(subject, {})[key] = {k: float(v) for k, v in dict(rec.get("st") or {}).items()}
        self._last_sync = sum(self._n_obs.values())

    def save(self, force: bool = False) -> bool:
        if self._crystals is not None:
            self.sync_crystals(force=force)
            return True                      # the crystals are the record: no file of our own
        if not self.persist:
            return True
        payload = {
            "schema": SCHEMA,
            "streams": {n: s.state() for n, s in self._streams.items()},
            "raw": {ax: run.state() for ax, run in self._raw.items()},
            "ring": {s: [[list(v) for v in h] for h in hs] for s, hs in self._ring.items()},
            "n_obs": self._n_obs,
            "loads": self._loads,
            "tables": self._tables,
            "stats": self._stats,
            "best": self._best,
            "streak": self._streak,
            "baseline_used": self._baseline_used,
            "emitted": self._emitted,
            "unsubmitted": self._unsubmitted,
            "last_emission": self._last_emission,
            "saved_at": time.time(),
        }
        try:
            return bool(atomic_write_json(self.storage_path, payload, indent=0))
        except Exception:
            return False

    def _load(self) -> None:
        if not self.persist or not self.storage_path.exists():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            return
        self._streams = {str(n): _Stream(v) for n, v in dict(data.get("streams") or {}).items()}
        for key, state in dict(data.get("raw") or {}).items():
            self._raw[str(key)] = _Running(state)
        self._ring = {
            s: [tuple(tuple(int(x) for x in v) for v in h) for h in hs]
            for s, hs in dict(data.get("ring") or {}).items()
        }
        self._n_obs = {str(k): int(v) for k, v in dict(data.get("n_obs") or {}).items()}
        self._loads = {s: {ax: list(v) for ax, v in per.items()} for s, per in dict(data.get("loads") or {}).items()}
        self._tables = dict(data.get("tables") or {})
        self._stats = dict(data.get("stats") or {})
        self._best = dict(data.get("best") or {})
        self._streak = {str(k): {str(a): int(b) for a, b in dict(v).items()} for k, v in dict(data.get("streak") or {}).items()}
        self._baseline_used = {str(k): dict(v) for k, v in dict(data.get("baseline_used") or {}).items()}
        self._emitted = int(data.get("emitted", 0) or 0)
        self._unsubmitted = int(data.get("unsubmitted", 0) or 0)
        self._last_emission = dict(data.get("last_emission") or {})
