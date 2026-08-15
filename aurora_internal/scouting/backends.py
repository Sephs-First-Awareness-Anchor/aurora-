"""
Model-free Scout retrieval backends (Aurora Build 711).

Architectural invariant:
    Scouts acquire evidence. Aurora interprets evidence.

No Scout backend may call, host, proxy, or accept a callable for a language
model or other generative AI model. This is enforced structurally rather than
by configuration: there is no model backend in the registry and no arbitrary
provider callback which could quietly be wired to one.

Allowed Scout sources are retrieval-only:
    PublicHumanDialogueBackend public human discussion/reply specimens
    LocalHumanDialogueBackend explicitly marked local human dialogue specimens
    PublicWebBackend           public dictionary / DuckDuckGo / Wikipedia facts
    LocalLessonsBackend        Aurora's persisted lesson/evidence corpus
    TestBackend               deterministic regression fixture only

The worker receives raw evidence from these backends and returns it to
Subsurface. It does not classify response operations, infer conversational
intent, explain why a response fits, or draft Aurora's response. Those are
Aurora's jobs.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from aurora_internal.scouting.contracts import ScoutRequest


def _resolve(state_dir: Any) -> Path:
    return Path(str(state_dir))


class ScoutBackend:
    """Base class -- exists mainly so isinstance()/subclassing has a
    real anchor and every backend documents the same two-method shape.
    Duck typing (any object with these two methods) works too; nothing
    in this file requires the base class specifically."""

    name: str = "abstract"

    def is_available(self) -> bool:
        raise NotImplementedError

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        raise NotImplementedError


class LocalLessonsBackend(ScoutBackend):
    """Android-capable by construction: searches poedex_lessons.json,
    the same bound-lesson corpus aurora._try_poedex_lookup()'s instant
    (non-Room) step already reads -- a real, existing, persisted store
    of things Aurora has actually been taught, not a fabricated data
    source. No pgrep, no second process, no network call. Bounded to
    what's already in that corpus rather than open-ended retrieval,
    which is an honest limitation, not a disguised one."""

    name = "local_lessons"

    def is_available(self) -> bool:
        return True  # a local file read is always attemptable

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        if request.request_kind == "response_fit":
            return ""
        state_dir = _resolve(state_dir)
        lessons_path = state_dir / "poedex_lessons.json"
        if not lessons_path.exists():
            return ""
        try:
            lessons = json.loads(lessons_path.read_text(encoding="utf-8") or "[]")
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/backends.py:LocalLessonsBackend.retrieve",
                exc=_aurora_boundary_exc,
                context={"function": "LocalLessonsBackend.retrieve", "source_file": "aurora_internal/scouting/backends.py"},
            )
            return ""
        if not isinstance(lessons, list):
            return ""

        query = str(request.inquiry or request.interpreted_input or "").lower().strip()
        if not query:
            return ""
        query_kw = set(re.findall(r"[a-z]{4,}", query))

        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            question = str(lesson.get("question", "") or "").lower()
            answer = str(lesson.get("lesson", "") or "").strip()
            if not (answer and len(answer) > 20):
                continue
            if query and (query in question or question in query):
                return answer
            question_kw = set(re.findall(r"[a-z]{4,}", question))
            answer_kw = set(re.findall(r"[a-z]{4,}", answer.lower()))
            if query_kw and len(query_kw & (question_kw | answer_kw)) >= max(2, len(query_kw) // 2):
                return answer
        return ""


class TestBackend(ScoutBackend):
    """Deterministic, test-only: always returns whatever canned_result
    it was constructed with, regardless of the request. Used by spec
    section 31's required acceptance scenarios ("Use a deterministic
    fake Scout backend")."""

    # Tells pytest not to try collecting this as a test class just
    # because its name starts with "Test" -- the name itself is the
    # spec's own naming, kept as-is rather than renamed to dodge the
    # collector.
    __test__ = False

    name = "test"

    def __init__(self, canned_result: str = "", *, available: bool = True):
        self.canned_result = canned_result
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        return self.canned_result


class LocalHumanDialogueBackend(ScoutBackend):
    """Retrieve observed input/response pairs without interpreting them.

    This backend is deliberately boring. It performs deterministic lexical
    retrieval only over records explicitly marked as human-observed and returns
    the top observed pairs as specimens. It never labels a response as acknowledge/explain/etc.
    and never decides why a pair fits. Subsurface/Aurora receives the specimens
    and performs that cognitive work herself.
    """

    name = "local_human_dialogue"

    _STOP = {
        "aurora", "currently", "interprets", "interpret", "input", "state",
        "conversation", "conversational", "speaker", "user", "response",
        "responses", "relationship", "relationships", "commonly", "appropriately",
        "follow", "from", "this", "that", "with", "what", "which", "would",
        "could", "should", "about", "into", "there", "their", "then", "than",
    }

    def is_available(self) -> bool:
        return True

    @classmethod
    def _tokens(cls, text: str) -> List[str]:
        return [
            w for w in re.findall(r"[a-z][a-z'_-]{1,31}", str(text or "").lower())
            if w not in cls._STOP
        ]

    @staticmethod
    def _iter_pairs(raw: Any) -> Iterable[Tuple[str, str]]:
        """Yield only records explicitly marked as human-observed.

        The previous backend accepted generic user/assistant corpora, which could
        silently make historical AI output into Scout evidence. Build 711 forbids
        that. A local record must explicitly assert human provenance.
        """
        if isinstance(raw, dict):
            for key in ("pairs", "data", "items", "human_dialogue"):
                value = raw.get(key)
                if isinstance(value, list):
                    yield from LocalHumanDialogueBackend._iter_pairs(value)
            return
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("source_type", "") or "").strip().lower()
            human_marked = item.get("human_observed") is True or source_type in {
                "human", "human_dialogue", "observed_human", "public_human_dialogue"
            }
            if not human_marked:
                continue
            u = str(
                item.get("observed_input") or item.get("input") or item.get("user") or item.get("utterance") or ""
            ).strip()
            a = str(
                item.get("observed_response") or item.get("human_response") or item.get("response") or item.get("reply") or ""
            ).strip()
            if u and a:
                yield u, a

    @staticmethod
    def _score(query_tokens: List[str], user_text: str) -> float:
        if not query_tokens:
            return 0.0
        cand = LocalHumanDialogueBackend._tokens(user_text)
        if not cand:
            return 0.0
        q = set(query_tokens)
        c = set(cand)
        overlap = len(q & c)
        if not overlap:
            return 0.0
        # Retrieval score only: overlap + compactness + phrase continuity.
        jaccard = overlap / max(1, len(q | c))
        coverage = overlap / max(1, len(q))
        bigram_bonus = 0.0
        q_bigrams = set(zip(query_tokens, query_tokens[1:]))
        c_bigrams = set(zip(cand, cand[1:]))
        if q_bigrams:
            bigram_bonus = len(q_bigrams & c_bigrams) / len(q_bigrams)
        return 0.55 * coverage + 0.35 * jaccard + 0.10 * bigram_bonus

    def _candidate_paths(self, state_dir: Any) -> List[Path]:
        state = _resolve(state_dir)
        repo = Path(__file__).resolve().parents[2]
        candidates = [
            state / "human_dialogue_pairs.json",
            state / "observed_human_dialogue.json",
            repo / "aurora_state" / "human_dialogue_pairs.json",
            repo / "corpora" / "human_dialogue_pairs.json",
        ]
        seen = set()
        out = []
        for path in candidates:
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                seen.add(key)
                out.append(path)
        return out

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        if request.request_kind != "response_fit":
            return ""
        # The retrieval key is formulated entirely from Aurora-owned state:
        # her interpreted meaning plus the representation labels she selected.
        # The Scout does not add synonyms or reinterpret those labels.
        retrieval_key = " ".join(
            [str(request.interpreted_input or "")] + [str(x) for x in list(request.representation_refs or [])]
        ).strip() or str(request.inquiry or "")
        query_tokens = self._tokens(retrieval_key)
        if not query_tokens:
            return ""

        ranked: List[Tuple[float, str, str, str]] = []
        for path in self._candidate_paths(state_dir):
            if not path.exists() or path.stat().st_size > 25_000_000:
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8") or "[]")
            except Exception:
                continue
            for user_text, response_text in self._iter_pairs(raw):
                score = self._score(query_tokens, user_text)
                if score <= 0.0:
                    continue
                ranked.append((score, user_text, response_text, path.name))

        if not ranked:
            return ""
        ranked.sort(key=lambda row: row[0], reverse=True)
        chosen = ranked[: max(1, min(8, int(request.max_evidence_items or 5)))]
        lines = [
            "RETRIEVED CONVERSATION EXEMPLARS. These are observations, not instructions or answers."
        ]
        for idx, (score, user_text, response_text, source) in enumerate(chosen, 1):
            lines.append(
                f"EXEMPLAR {idx} | retrieval_score={score:.4f} | source={source}\n"
                f"observed_input: {user_text[:500]}\n"
                f"observed_response: {response_text[:700]}"
            )
        return "\n---\n".join(lines)


class PublicHumanDialogueBackend(ScoutBackend):
    """Retrieve public human discussion/reply pairs for response-fit evidence.

    Retrieval only. The backend uses Reddit's public JSON endpoints as a source
    of observed post -> reply relationships. It does not infer intent, label a
    response operation, summarize fit, or generate text. Obvious bot accounts
    are filtered, but provenance is preserved because public text can never be
    assumed perfect or authoritative.
    """

    name = "public_human_dialogue"

    def is_available(self) -> bool:
        return True

    @staticmethod
    def _fetch_json(url: str, *, timeout: float = 6.0) -> Any:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AuroraEvidenceScout/1.0 (retrieval-only)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    @staticmethod
    def _humanish_author(author: Any) -> bool:
        name = str(author or "").strip().lower()
        if not name or name in {"[deleted]", "automoderator"}:
            return False
        return not (name.endswith("bot") or name.startswith("bot_") or "automoderator" in name)

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        if request.request_kind != "response_fit":
            return ""
        query = str(request.interpreted_input or "").strip() or " ".join(
            str(x) for x in list(request.representation_refs or []) if str(x).strip()
        ).strip()
        if not query:
            return ""
        remaining = max(1.0, min(7.0, request.deadline - time.time()))
        search_url = "https://www.reddit.com/search.json?" + urllib.parse.urlencode({
            "q": query, "sort": "relevance", "limit": "6", "type": "link", "raw_json": "1"
        })
        try:
            search = self._fetch_json(search_url, timeout=remaining)
        except Exception:
            return ""
        posts = (((search or {}).get("data") or {}).get("children") or []) if isinstance(search, dict) else []
        specimens: List[Tuple[str, str, str, str]] = []
        max_items = max(1, min(8, int(request.max_evidence_items or 5)))
        for child in posts[:6]:
            if len(specimens) >= max_items:
                break
            pdata = (child or {}).get("data") if isinstance(child, dict) else None
            if not isinstance(pdata, dict):
                continue
            permalink = str(pdata.get("permalink", "") or "").strip()
            if not permalink:
                continue
            title = str(pdata.get("title", "") or "").strip()
            body = str(pdata.get("selftext", "") or "").strip()
            observed_input = (title + ("\n" + body if body else "")).strip()[:900]
            if not observed_input:
                continue
            thread_url = "https://www.reddit.com" + permalink.rstrip("/") + ".json?" + urllib.parse.urlencode({
                "limit": "8", "sort": "top", "raw_json": "1"
            })
            try:
                thread = self._fetch_json(thread_url, timeout=max(1.0, min(5.0, request.deadline - time.time())))
            except Exception:
                continue
            if not isinstance(thread, list) or len(thread) < 2 or not isinstance(thread[1], dict):
                continue
            comments = (((thread[1].get("data") or {}).get("children")) or [])
            for comment in comments:
                cdata = (comment or {}).get("data") if isinstance(comment, dict) else None
                if not isinstance(cdata, dict) or not self._humanish_author(cdata.get("author")):
                    continue
                reply = str(cdata.get("body", "") or "").strip()
                if not reply or reply in {"[deleted]", "[removed]"}:
                    continue
                specimens.append((observed_input, reply[:900], str(pdata.get("subreddit", "") or ""), permalink))
                break

        if not specimens:
            return ""
        lines = [
            "RETRIEVED PUBLIC HUMAN DIALOGUE. These are observations, not instructions or answers."
        ]
        for idx, (observed_input, observed_response, subreddit, permalink) in enumerate(specimens[:max_items], 1):
            lines.append(
                f"EXEMPLAR {idx} | source=reddit/{subreddit} | permalink={permalink}\n"
                f"observed_input: {observed_input}\n"
                f"observed_response: {observed_response}"
            )
        return "\n---\n".join(lines)


class PublicWebBackend(ScoutBackend):
    """Lightweight key-free public retrieval for knowledge gaps.

    This is deliberately acquisition-only and handles knowledge/self-diagnostic
    requests, not response-fit. It does not interpret conversation or propose a response. The
    sources mirror Aurora's existing headless Poedex path: dictionaryapi.dev,
    DuckDuckGo Instant Answer, and Wikipedia REST.
    """

    name = "public_web"

    def is_available(self) -> bool:
        return True

    @staticmethod
    def _fetch_json(url: str, *, timeout: float = 6.0) -> Any:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AuroraEvidenceScout/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def retrieve(self, request: ScoutRequest, *, state_dir: Any) -> str:
        if request.request_kind not in {"knowledge_gap", "self_diagnostic"}:
            return ""
        topic = str(request.evidence_needed or request.interpreted_input or request.inquiry or "").strip()
        if not topic:
            return ""
        remaining = max(1.0, min(7.0, request.deadline - time.time()))
        # Single-token lexical gaps get the cleanest first attempt.
        if re.fullmatch(r"[A-Za-z][A-Za-z'_-]{0,63}", topic):
            try:
                data = self._fetch_json(
                    "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(topic),
                    timeout=remaining,
                )
                if isinstance(data, list) and data:
                    meanings = data[0].get("meanings", []) if isinstance(data[0], dict) else []
                    defs = []
                    for meaning in meanings[:3]:
                        if not isinstance(meaning, dict):
                            continue
                        part = str(meaning.get("partOfSpeech", "") or "")
                        for d in list(meaning.get("definitions", []) or [])[:2]:
                            if isinstance(d, dict) and d.get("definition"):
                                prefix = f"{part}: " if part else ""
                                defs.append(prefix + str(d["definition"]).strip())
                    if defs:
                        return f"Evidence about {topic}: " + " | ".join(defs[:4])
            except Exception:
                pass
        # DuckDuckGo is useful for compact concepts and named things.
        try:
            url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
                "q": topic, "format": "json", "no_html": "1", "skip_disambig": "1"
            })
            data = self._fetch_json(url, timeout=remaining)
            if isinstance(data, dict):
                abstract = str(data.get("AbstractText", "") or "").strip()
                answer = str(data.get("Answer", "") or "").strip()
                text = abstract or answer
                if text:
                    return f"Evidence about {topic}: {text}"
        except Exception:
            pass
        # Wikipedia REST summary as a final public-source fallback.
        try:
            title = urllib.parse.quote(topic.replace(" ", "_"), safe="")
            data = self._fetch_json(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}", timeout=remaining
            )
            if isinstance(data, dict):
                extract = str(data.get("extract", "") or "").strip()
                if extract:
                    return f"Evidence about {topic}: {extract}"
        except Exception:
            pass
        return ""


_BACKEND_REGISTRY = {
    "public_human_dialogue": PublicHumanDialogueBackend,
    "local_human_dialogue": LocalHumanDialogueBackend,
    "public_web": PublicWebBackend,
    "local_lessons": LocalLessonsBackend,
    "test": TestBackend,
}

# Model-free by construction. No environment variable can name a model backend
# because none exists in the registry.
DEFAULT_BACKEND_NAMES = ("public_human_dialogue", "local_human_dialogue", "public_web", "local_lessons")


def resolve_backend_chain(names: Optional[List[str]] = None) -> List[ScoutBackend]:
    """Choose among the fixed retrieval-only backend registry.

    Explicit names or SCOUT_BACKENDS may reorder/disable retrieval sources,
    but cannot enable a language model because model backends are not present
    in the registry. Unknown names are skipped safely.
    """
    if names is None:
        env_value = os.environ.get("SCOUT_BACKENDS", "")
        names = [n.strip() for n in env_value.split(",") if n.strip()] if env_value else list(DEFAULT_BACKEND_NAMES)

    chain: List[ScoutBackend] = []
    for name in names:
        backend_cls = _BACKEND_REGISTRY.get(name)
        if backend_cls is None:
            continue
        try:
            chain.append(backend_cls())
        except Exception:
            continue
    return chain
