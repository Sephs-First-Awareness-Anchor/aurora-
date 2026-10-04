"""
aurora_representation_exchange.py
=================================

The use-and-consequence loop for discovered representations, open to ANY
subject of representation.

A discovered (subject, axis-path) representation is only real to Aurora once
something uses it and the use has a consequence.  This module closes that loop
without naming any consumer.  The web, lexical grounding, communication
emergence, identity, WARP components, crystals, planners -- all of them are
just subjects of representation, and none is special here.

Protocol (duck-typed; a subject opts in with ONE method):

    accept_representation(rep: Mapping, context: Mapping) -> Optional[Mapping]

    ``rep``      a public view of the representation (id, subject, path,
                 target root, resolution, status, evidence so far)
    ``context``  use_id, event_index, subject, the expectation the
                 representation holds about the NEXT event, and its status
    return       None to decline; any mapping to accept (that is a "use").

A consumer that accepted a use may later report what happened in ITS OWN
domain with ``exchange.report_consequence(use_id, outcome_kind, score)``.
Consumers are discovered from ``systems`` by that one method, or registered
explicitly; nothing else about them is assumed, and a consumer that raises is
isolated from the loop.

The loop also closes with zero consumers.  Every discovered representation
holds an expectation about what follows the event that just arrived (what the
path says the next event's target root will do).  When the next event
arrives, the expectation is scored prospectively against the marginal, so a
representation is confirmed or refuted by experience whether or not anything
has adopted it.  That is the universal consequence, and it is domain
independent: history and live turns feed it identically.

Status is earned, never decreed:
    candidate   discovered, not yet adopted by any subject
    in_use      adopted by at least one subject
    earned      prospective consequence significantly positive (batch-means
                z) and no adopting subject reporting harm in its own domain
    dissolved   prospective consequence significantly negative

This module does not promote WARP components.  WARP's own promotion gate is
untouched ("never promote by decree"); the exchange supplies the use and
consequence evidence such gates have lacked.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import math
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional

from aurora_persistence_utils import atomic_write_json

AXES = ("X", "T", "N", "B", "A")  # canonical: existence, temporal, energy, boundary, agency
REC_DIMS = ("REC_SURFACE", "REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE")

SCHEMA = "aurora_representation_exchange_v1"
SYMBOLS = AXES + ("t", "n", "L0", "L1", "L2", "L3")   # roots, optional low-tail symbols of T and N, optional word classes
_BLOCK = 100            # batch-mean block (robust to serial dependence)
_MIN_BLOCKS = 5         # blocks before significance is read
_Z_SIGNIFICANT = 3.0    # conventional significance for earn / dissolve
_DOMAIN_MIN = 100       # a consumer's own-domain verdict is read after this many reports
_MAX_USES = 5000        # outstanding uses awaiting a domain report


def _clip(p: float) -> float:
    return min(1.0 - 1e-6, max(1e-6, float(p)))


def _clip01(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, out)) if math.isfinite(out) else 0.0


def _new_universal() -> Dict[str, float]:
    return {"n": 0.0, "gain": 0.0, "hits": 0.0, "blk_n": 0.0, "blk_sum": 0.0, "nb": 0.0, "bsum": 0.0, "bsq": 0.0}


def _z_of(universal: Mapping[str, float]) -> float:
    nb = float(universal.get("nb", 0.0))
    if nb < _MIN_BLOCKS:
        return 0.0
    mean = universal["bsum"] / nb
    var = max((universal["bsq"] / nb) - mean * mean, 1e-12) * nb / max(nb - 1.0, 1.0)
    return mean / math.sqrt(var / nb)


class RepresentationConsumerMixin:
    """Opt-in helper for any subject of representation.

    Records what it was offered and accepts.  Subclasses override
    ``use_representation`` to condition their own behaviour on the
    expectation, and may return None there to decline.
    """

    def accept_representation(self, rep: Mapping[str, Any], context: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
        result = self.use_representation(rep, context)
        if result is not None:
            log = self.__dict__.setdefault("_representation_uses", [])
            log.append({
                "use_id": context.get("use_id"),
                "representation_id": rep.get("id"),
                "expectation": dict(context.get("expectation") or {}),
            })
            del log[:-256]
        return result

    def use_representation(self, rep: Mapping[str, Any], context: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
        return {"accepted": True}

    def representation_uses(self) -> List[Dict[str, Any]]:
        return list(self.__dict__.get("_representation_uses", []))


class AuroraRepresentationExchange:
    """Offers discovered representations to any subject; scores every expectation."""

    def __init__(self, ledger: Any, *, state_dir: str = "aurora_state", persist: bool = True) -> None:
        self.ledger = ledger
        self.state_dir = str(state_dir or "aurora_state")
        self.persist = bool(persist)
        self.storage_path = Path(self.state_dir) / "representation_exchange.json"
        self._consumers: Dict[str, Any] = {}
        self._consumer_stats: Dict[str, Dict[str, int]] = {}
        self._reps: Dict[str, Dict[str, Any]] = {}
        self._pending: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._uses: Dict[str, Dict[str, Any]] = {}
        self._last_index: Dict[str, int] = {}
        self._word_cache: Dict[str, Any] = {}
        self._crystals: Any = None
        self._known_word: Any = None
        self._synced: Dict[str, List[float]] = {}
        # Only a tiny rolling window is needed to recognize a permanent
        # kernel (max path depth is REC_CORE).  No training examples live here.
        self._history: Dict[str, Deque[Dict[str, Any]]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Consumers: any subject of representation, found by one method
    # ------------------------------------------------------------------

    def register_consumer(self, name: str, consumer: Any) -> bool:
        if not callable(getattr(consumer, "accept_representation", None)):
            return False
        if any(existing is consumer for existing in self._consumers.values()):
            return True
        self._consumers[str(name)] = consumer
        self._consumer_stats.setdefault(str(name), {"offered": 0, "accepted": 0, "failed": 0})
        return True

    def attach_systems(self, systems: Mapping[str, Any]) -> int:
        """Adopt every system that implements ``accept_representation``."""
        added = 0
        for name, obj in dict(systems or {}).items():
            if obj is self or obj is self.ledger or str(name) in self._consumers:
                continue
            if type(obj).__module__.startswith("unittest.mock"):
                continue
            if self.register_consumer(str(name), obj):
                added += 1
        return added

    def consumers(self) -> List[str]:
        return sorted(self._consumers)

    # ------------------------------------------------------------------
    # The loop
    # ------------------------------------------------------------------

    @staticmethod
    def _add(universal: Dict[str, float], gain: float, hit: bool) -> None:
        universal["n"] += 1.0
        universal["gain"] += gain
        universal["hits"] += 1.0 if hit else 0.0
        universal["blk_n"] += 1.0
        universal["blk_sum"] += gain
        if universal["blk_n"] >= _BLOCK:
            mean = universal["blk_sum"] / universal["blk_n"]
            universal["nb"] += 1.0
            universal["bsum"] += mean
            universal["bsq"] += mean * mean
            universal["blk_n"] = 0.0
            universal["blk_sum"] = 0.0

    def _rep(self, subject: str, exp: Mapping[str, Any]) -> Dict[str, Any]:
        path = str(exp["path"])
        identity = self.ledger.representation_identity(path) if hasattr(self.ledger, "representation_identity") else path
        rep_id = f"REPR:{subject}:{identity}"
        rep = self._reps.get(rep_id)
        if rep is None:
            length = len(path.split(">"))
            rep = {
                "id": rep_id, "subject": subject, "path": path, "identity_path": identity, "target": str(exp["target"]),
                "length": length, "resolution": REC_DIMS[length],
                "offered": 0, "accepted": 0, "first_seen": time.time(),
                "universal": _new_universal(), "domain": {}, "kernel": None,
                "words": {"hi": {}, "lo": {}}, "word_n": {"hi": 0, "lo": 0},
            }
            # A candidate keeps only a compact, disposable seed of the
            # irreducible recognizer.  It is NOT permanent until consequence
            # earns the representation.  This protects the eventual kernel if
            # a developmental L-slot disappears on the very event that earns it.
            if hasattr(self.ledger, "recognition_kernel"):
                try:
                    seed = self.ledger.recognition_kernel(subject, path)
                except Exception:
                    seed = {}
                if seed and str(seed.get("identity_path")) == identity:
                    rep["_kernel_seed"] = seed
            self._reps[rep_id] = rep
        return rep

    @staticmethod
    def classify(universal: Mapping[str, float], accepted: int, domain: Mapping[str, Mapping[str, float]]) -> str:
        z = _z_of(universal)
        if z <= -_Z_SIGNIFICANT:
            return "dissolved"
        harmed = any(
            d.get("n", 0) >= _DOMAIN_MIN and d["sum"] / d["n"] < 0.5 for d in dict(domain or {}).values()
        )
        if z >= _Z_SIGNIFICANT and not harmed:
            return "earned"
        return "in_use" if accepted > 0 else "candidate"

    def status_of(self, rep: Mapping[str, Any]) -> str:
        return self.classify(rep["universal"], int(rep.get("accepted", 0)), rep.get("domain", {}))

    def public(self, rep: Mapping[str, Any]) -> Dict[str, Any]:
        uni = rep["universal"]
        return {
            "id": rep["id"], "subject": rep["subject"], "path": rep["path"],
            "identity_path": rep.get("identity_path", rep["path"]), "target": rep["target"],
            "length": rep["length"], "resolution": rep["resolution"], "status": self.status_of(rep),
            "recognition_kernel": (rep.get("kernel") or {}).get("id"),
            # X and B are positional by definition (episode entry, first act): structure found
            # only through them is real but definitional, not learning from experience.
            "positional": all(ax in ("X", "B") for ax in str(rep["path"]).split(">")),
            "expectations_scored": int(uni["n"]),
            "mean_gain_bits": round(uni["gain"] / uni["n"], 6) if uni["n"] else 0.0,
            "hit_rate": round(uni["hits"] / uni["n"], 6) if uni["n"] else 0.0,
            "z": round(_z_of(uni), 3),
            "offered": int(rep["offered"]), "accepted": int(rep["accepted"]),
            "domain": {
                name: {"reports": int(d["n"]), "mean_score": round(d["sum"] / d["n"], 6) if d["n"] else 0.0}
                for name, d in rep.get("domain", {}).items()
            },
        }

    @staticmethod
    def _unique_tokens(tokens: Optional[Iterable[str]], limit: int = 48) -> List[str]:
        return list(dict.fromkeys(str(t) for t in (tokens or []) if t))[:limit]

    @staticmethod
    def _note_words(rep: Dict[str, Any], high: bool, words: List[str]) -> None:
        """Which surface tokens sit at each pole of the target root, under this shape's context."""
        pole = "hi" if high else "lo"
        counts = rep.setdefault("word_n", {"hi": 0, "lo": 0})
        table = rep.setdefault("words", {"hi": {}, "lo": {}}).setdefault(pole, {})
        counts[pole] = counts.get(pole, 0) + 1
        for word in words:
            table[word] = table.get(word, 0) + 1
        if len(table) > 800:
            rep["words"][pole] = dict(sorted(table.items(), key=lambda kv: -kv[1])[:500])

    def shape_words(self, rep_id: str, top: int = 8, min_count: int = 5) -> List[Dict[str, Any]]:
        """Tokens that separate the two poles of this shape's target root (no gloss, no label).

        Association by act: a token is tied to a shape by where it occurs when the shape
        holds, never by what it is called.  Cached; refreshed every 100 new scored events.
        """
        rep = self._reps.get(str(rep_id))
        if rep is None:
            return []
        counts = rep.get("word_n", {"hi": 0, "lo": 0})
        total = int(counts.get("hi", 0)) + int(counts.get("lo", 0))
        cached = self._word_cache.get(rep["id"])
        if cached is not None and total - cached[0] < 100:
            return cached[1]
        hi, lo = rep.get("words", {}).get("hi", {}), rep.get("words", {}).get("lo", {})
        nh, nl = int(counts.get("hi", 0)), int(counts.get("lo", 0))
        out: List[Dict[str, Any]] = []
        if nh >= min_count and nl >= min_count:
            for word in set(hi) | set(lo):
                ch, cl = hi.get(word, 0), lo.get(word, 0)
                if ch + cl < min_count:
                    continue
                lift = math.log2(((ch + 0.5) / (nh + 1.0)) / ((cl + 0.5) / (nl + 1.0)))
                out.append({"word": word, "lift": round(lift, 4), "count": ch + cl})
            out = sorted(out, key=lambda r: -abs(r["lift"]))[:top]
        self._word_cache[rep["id"]] = (total, out)
        return out

    def _ensure_kernel(self, rep: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if rep.get("kernel") or self.status_of(rep) != "earned":
            return rep.get("kernel")
        kernel: Dict[str, Any] = {}
        if hasattr(self.ledger, "recognition_kernel"):
            try:
                kernel = dict(self.ledger.recognition_kernel(rep["subject"], rep["path"]) or {})
            except Exception:
                kernel = {}
        expected_identity = str(rep.get("identity_path", rep["path"]))
        if not kernel or str(kernel.get("identity_path")) != expected_identity:
            kernel = dict(rep.get("_kernel_seed") or {})
        # Guard against slot reuse between discovery and crystallization.
        if kernel and str(kernel.get("identity_path")) == expected_identity:
            rep["kernel"] = kernel
            rep.pop("_kernel_seed", None)
        return rep.get("kernel")

    @staticmethod
    def _kernel_bit(symbol: str, event: Mapping[str, Any], kernel: Mapping[str, Any]) -> int:
        symbol = str(symbol)
        if symbol.startswith("L"):
            info = dict(kernel.get("lexical", {}).get(symbol) or {})
            members = set(str(w) for w in (info.get("members") or []))
            words = set(str(w) for w in (event.get("tokens") or []))
            return 1 if members and not members.isdisjoint(words) else 0
        try:
            return int(tuple(event.get("bits") or ())[SYMBOLS.index(symbol)])
        except Exception:
            return 0

    def _kernel_expectation(self, rep: Mapping[str, Any], stream: str) -> Optional[Dict[str, Any]]:
        """Reactivate an earned dormant representation from its minimal kernel.

        Only lexical kernels need this path: root-only representations remain
        natively available through the live ledger.  Recognition requires an
        affirmative lexical source anchor, so a dormant concept is not woken
        merely by the absence of its words.
        """
        kernel = dict(rep.get("kernel") or {})
        path = str(kernel.get("path") or rep.get("path") or "")
        parts = path.split(">") if path else []
        need = len(parts) - 1
        hist = list(self._history.get(str(stream), ()))
        if need < 1 or len(hist) < need or not any(p.startswith("L") for p in parts[:-1]):
            return None
        events = hist[-need:]
        code, lex_positive = 0, False
        for i, symbol in enumerate(parts[:-1]):
            bit = self._kernel_bit(symbol, events[i], kernel)
            code |= int(bit) << i
            if symbol.startswith("L") and bit:
                lex_positive = True
        if not lex_positive:
            return None
        counts = list(dict(kernel.get("ctx") or {}).get(str(code)) or [])
        marg = list(kernel.get("marg") or [])
        if len(counts) != 2 or len(marg) != 2 or sum(counts) <= 0 or sum(marg) <= 0:
            return None
        p = (float(counts[1]) + 0.5) / (float(sum(counts)) + 1.0)
        pm = (float(marg[1]) + 0.5) / (float(sum(marg)) + 1.0)
        return {
            "subject": rep["subject"], "path": path, "target": parts[-1],
            "p_high": round(p, 6), "p_high_marginal": round(pm, 6),
            "support": int(sum(counts)), "dormant_reactivation": True,
            "recognition_kernel": kernel.get("id"),
        }

    def _target_bit(self, exp: Mapping[str, Any], bits: Iterable[int], words: List[str]) -> int:
        target = str(exp.get("target") or "")
        kernel = dict(exp.get("kernel") or {})
        if target.startswith("L") and kernel:
            return self._kernel_bit(target, {"bits": tuple(bits), "tokens": words}, kernel)
        try:
            return int(tuple(bits)[SYMBOLS.index(target)])
        except Exception:
            return 0

    def after_event(self, event_index: int, *, stream: str = "history",
                    tokens: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Call once per event of ``stream``, after the ledger observed it.  Idempotent on index."""
        stream = str(stream or "history")
        index = int(event_index)
        if index <= self._last_index.get(stream, -1):
            return {"processed": False, "event_index": index, "stream": stream}
        self._last_index[stream] = index
        subject_now, bits = self.ledger.last_bits(stream)
        words = self._unique_tokens(tokens)

        # 1. Consequence of the expectations made before this event arrived.
        scored = 0
        pending = self._pending.pop(stream, {})
        if bits:
            for rep_id, exp in pending.items():
                rep = self._reps.get(rep_id)
                if rep is None:
                    continue
                bit = self._target_bit(exp, bits, words)
                p, pm = _clip(exp["p_high"]), _clip(exp["p_marg"])
                gain = math.log2((p if bit else 1.0 - p) / (pm if bit else 1.0 - pm))
                self._add(rep["universal"], gain, (p > 0.5) == bool(bit))
                self._note_words(rep, bool(bit), words)
                self._ensure_kernel(rep)
                scored += 1

        # The permanent recognizer needs only the tiny path-depth window, never
        # the examples that originally trained it.  Append the current event
        # after scoring yesterday's expectations and before asking what follows.
        hist = self._history.setdefault(stream, deque(maxlen=len(REC_DIMS)))
        hist.append({"bits": tuple(bits), "tokens": list(words)})

        # 2. What every active discovered representation expects of the NEXT
        # event, plus earned dormant kernels that recognize the present shape.
        offered = 0
        fresh: Dict[str, Dict[str, Any]] = {}
        candidates: List[tuple] = []
        for exp in self.ledger.expectations(subject_now, stream):
            rep = self._rep(subject_now, exp)
            candidates.append((rep, dict(exp)))

        active_ids = {rep["id"] for rep, _ in candidates}
        for rep in list(self._reps.values()):
            if rep["id"] in active_ids or self.status_of(rep) != "earned" or not rep.get("kernel"):
                continue
            exp = self._kernel_expectation(rep, stream)
            if exp is not None:
                candidates.append((rep, exp))

        for rep, exp in candidates:
            use_ids: List[str] = []
            status = self.status_of(rep)
            shape_words = self.shape_words(rep["id"]) if status == "earned" else []
            for name, consumer in list(self._consumers.items()):
                use_id = f"USE:{rep['id']}:{stream}:{index}:{name}"
                context = {
                    "use_id": use_id, "event_index": index, "stream": stream, "subject": rep["subject"],
                    "expectation": dict(exp), "representation_id": rep["id"], "status": status,
                    "shape_words": shape_words, "recognition_kernel": (rep.get("kernel") or {}).get("id"),
                }
                stats = self._consumer_stats.setdefault(name, {"offered": 0, "accepted": 0, "failed": 0})
                stats["offered"] += 1
                rep["offered"] += 1
                offered += 1
                try:
                    result = consumer.accept_representation(self.public(rep), context)
                except Exception:
                    stats["failed"] += 1
                    continue
                if result is None:
                    continue
                stats["accepted"] += 1
                rep["accepted"] += 1
                use_ids.append(use_id)
                self._uses[use_id] = {"rep": rep["id"], "consumer": name, "event_index": index}
            fresh[rep["id"]] = {
                "target": exp["target"], "p_high": exp["p_high"], "p_marg": exp["p_high_marginal"],
                "use_ids": use_ids, "kernel": rep.get("kernel") if exp.get("dormant_reactivation") else None,
            }
        self._pending[stream] = fresh
        if len(self._uses) > _MAX_USES:
            for key in sorted(self._uses, key=lambda k: self._uses[k]["event_index"])[: len(self._uses) - _MAX_USES]:
                self._uses.pop(key, None)
        return {"processed": True, "event_index": index, "stream": stream,
                "expectations_scored": scored, "offered": offered}

    def report_consequence(self, use_id: str, outcome_kind: str = "indeterminate", score: float = 0.0) -> Dict[str, Any]:
        """A consumer reports what the use did in ITS OWN domain (score in [0, 1])."""
        use = self._uses.pop(str(use_id), None)
        if use is None:
            return {"matched": False, "use_id": str(use_id)}
        rep = self._reps.get(use["rep"])
        if rep is None:
            return {"matched": False, "use_id": str(use_id)}
        dom = rep["domain"].setdefault(use["consumer"], {"n": 0, "sum": 0.0, "ok": 0})
        dom["n"] += 1
        dom["sum"] += _clip01(score)
        dom["ok"] += 1 if str(outcome_kind) == "positive" else 0
        return {"matched": True, "representation_id": rep["id"], "consumer": use["consumer"]}

    # ------------------------------------------------------------------
    # Registry view
    # ------------------------------------------------------------------

    def representations(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        views = [self.public(rep) for rep in self._reps.values()]
        if status is not None:
            views = [v for v in views if v["status"] == status]
        return sorted(views, key=lambda v: (v["subject"], v["path"]))

    def status(self) -> Dict[str, Any]:
        views = self.representations()
        counts: Dict[str, int] = {}
        for view in views:
            counts[view["status"]] = counts.get(view["status"], 0) + 1
        return {
            "schema": SCHEMA, "last_event_index": dict(self._last_index),
            "consumers": self.consumers(), "consumer_stats": {k: dict(v) for k, v in self._consumer_stats.items()},
            "representations": len(views), "by_status": counts,
            "earned": [v["id"] for v in views if v["status"] == "earned"][:12],
            "storage_path": str(self.storage_path),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def attach_crystals(self, store: Any, known_word: Any = None) -> int:
        """Keep representation records INSIDE the crystals instead of in a file of our own.

        Restores every record the crystals already hold (nothing is recomputed) and from
        then on persists through them.  Returns the number of representations restored.
        """
        self._crystals = store
        self._known_word = known_word
        restored = 0
        for rec in store.load_all():
            rep_id = str(rec.get("id", ""))
            if not rep_id or rep_id in self._reps:
                continue
            path = str(rec["path"])
            length = len(path.split(">"))
            self._reps[rep_id] = {
                "id": rep_id, "subject": str(rec["subject"]), "path": path,
                "identity_path": str(rec.get("identity_path") or path), "target": str(rec["target"]),
                "length": length, "resolution": REC_DIMS[length], "offered": 0, "accepted": 0,
                "first_seen": rec.get("first_seen") or time.time(),
                "universal": {**_new_universal(), **{k: float(v) for k, v in dict(rec.get("uni") or {}).items()}},
                "domain": dict(rec.get("dom") or {}), "kernel": rec.get("kernel"),
                "words": {"hi": {}, "lo": {}}, "word_n": {"hi": 0, "lo": 0},
            }
            uni = self._reps[rep_id]["universal"]
            self._synced[rep_id] = [float(x) for x in (rec.get("sync") or [uni["n"], uni["hits"], uni["gain"]])]
            for stream_name, idx in dict(rec.get("li") or {}).items():       # never recount replayed events
                self._last_index[str(stream_name)] = max(self._last_index.get(str(stream_name), -1), int(idx))
            if hasattr(self.ledger, "adopt_table"):
                current_identity = self.ledger.representation_identity(path) if hasattr(self.ledger, "representation_identity") else path
                if current_identity == str(rec.get("identity_path") or path):
                    self.ledger.adopt_table(str(rec["subject"]), path, rec.get("tab") or {})
            restored += 1
        return restored

    def crystallize(self) -> int:
        """Write every representation that has earned its place onto its crystal.

        Positional shapes (X/B only) stay out: real but definitional.  A representation is
        recorded once it has been scored a block's worth or has earned its status, so
        consequence in progress is never lost.  Returns how many facets were written.
        """
        if self._crystals is None:
            return 0
        wrote = 0
        for rep in list(self._reps.values()):
            uni = rep["universal"]
            status = self.status_of(rep)
            if status == "dissolved" or self.public(rep)["positional"]:
                continue
            if uni["n"] < _BLOCK and status != "earned":
                continue
            if status == "earned":
                self._ensure_kernel(rep)
            words = []
            if status == "earned" and rep["subject"] == "external_user":      # the responder's words follow it
                words = list(self.shape_words(rep["id"]))        # both poles; each lands on its own pole crystal
            record = {
                "v": 2, "id": rep["id"], "subject": rep["subject"], "path": rep["path"],
                "identity_path": rep.get("identity_path", rep["path"]), "target": rep["target"],
                "status": status, "z": round(_z_of(uni), 3), "first_seen": rep.get("first_seen"),
                "kernel": rep.get("kernel"),
                "uni": {k: round(float(v), 6) for k, v in uni.items()},
                "dom": rep.get("domain", {}),
                "tab": self.ledger.table_of(rep["subject"], rep["path"]) if hasattr(self.ledger, "table_of") else {},
                "sync": [uni["n"], uni["hits"], uni["gain"]], "li": dict(self._last_index),
                "fam": self.ledger.family_of(rep["subject"], rep["path"]) if hasattr(self.ledger, "family_of") else [],
                "lexc": self.ledger.path_lexical_coordinates(rep["path"]) if hasattr(self.ledger, "path_lexical_coordinates") else {},
            }
            prev = self._synced.get(rep["id"], [0.0, 0.0, 0.0])
            delta = {"n": uni["n"] - prev[0], "hits": uni["hits"] - prev[1], "gain": uni["gain"] - prev[2]}
            if self._crystals.upsert(record, delta=delta, words=words, known_word=self._known_word):
                self._synced[rep["id"]] = record["sync"]
                wrote += 1
        return wrote

    def save(self) -> bool:
        if self._crystals is not None:
            return self.crystallize() >= 0          # the crystals ARE the record: no file of our own
        if not self.persist:
            return True
        payload = {
            "schema": SCHEMA, "last_index": self._last_index, "reps": self._reps,
            "pending": self._pending, "uses": self._uses,
            "consumer_stats": self._consumer_stats, "saved_at": time.time(),
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
        last = data.get("last_index", {})
        self._last_index = {"history": int(last)} if isinstance(last, int) else {str(k): int(v) for k, v in dict(last).items()}
        self._reps = dict(data.get("reps") or {})
        pending = dict(data.get("pending") or {})
        def _nested(p: Dict[str, Any]) -> bool:
            for v in p.values():
                return isinstance(v, dict) and all(isinstance(x, dict) for x in v.values())
            return True
        self._pending = pending if _nested(pending) else {"history": pending}
        self._uses = dict(data.get("uses") or {})
        self._consumer_stats = {str(k): dict(v) for k, v in dict(data.get("consumer_stats") or {}).items()}
