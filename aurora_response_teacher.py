#!/usr/bin/env python3
"""
aurora_response_teacher.py — Human Response Teaching System
============================================================
A dedicated teacher that collects real human communication from multiple
public sources and synthesizes targeted lessons for Aurora based on her
current fail points.

Aurora never touches these sources directly — the teacher acts as
intermediary, extracting patterns and delivering them through her
existing learning systems (OETS, dream trainer, gateway).

Sources:
  - Reddit     — conversational, informal, multi-voice
  - HackerNews — intellectual, structured, argument-driven
  - Wikipedia  — deep knowledge, precise language
  - DuckDuckGo — broad topic search, real-world context

Lesson delivery:
  - OETS concept nodes (natural expression patterns)
  - Dream trainer fail-point examples
  - Gateway witnesses (examples of natural human exchange)
  - HumannessScorer benchmarks (what does a 0.9 human message look like?)

Usage:
  # Standalone — run a teaching session
  python3 aurora_response_teacher.py

  # Show lesson history
  python3 aurora_response_teacher.py --history

  # Teach from a specific source
  python3 aurora_response_teacher.py --source reddit
"""

from __future__ import annotations

import json
import time
import random
import re
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR     = Path(__file__).parent
_STATE_DIR    = _BASE_DIR / "aurora_state"
_LESSON_LOG   = _STATE_DIR / "teacher_lesson_log.json"

# ---------------------------------------------------------------------------
# Humanness scorer (reuse from browser agent if available)
# ---------------------------------------------------------------------------

def _get_scorer():
    try:
        from aurora_browser_agent import HumannessScorer
        return HumannessScorer()
    except ImportError:
        return None


# ===========================================================================
# SOURCE COLLECTORS
# All use public APIs or JSON endpoints — no login, no browser needed.
# ===========================================================================

def _safe_fetch(url: str, timeout: int = 8) -> Optional[str]:
    """Fetch URL and return text, or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


class RedditCollector:
    """
    Pulls top comments from public subreddits via Reddit's JSON API.
    No authentication required for public subreddits.
    Target subreddits: conversational, philosophical, advice-oriented.
    """

    SUBREDDITS = [
        "CasualConversation",
        "AskReddit",
        "TrueOffMyChest",
        "philosophy",
        "self",
        "Showerthoughts",
        "ChangeMyView",
        "SeriousConversation",
    ]

    def collect(self, n: int = 10, topic_hint: str = "") -> List[Dict[str, str]]:
        """
        Pull top posts + top comment from random subreddits.
        Returns list of {source, title, content, score} dicts.
        """
        sub = random.choice(self.SUBREDDITS)
        url = f"https://www.reddit.com/r/{sub}/top.json?limit=25&t=week"
        raw = _safe_fetch(url)
        if not raw:
            return []

        results = []
        try:
            data = json.loads(raw)
            posts = data.get("data", {}).get("children", [])
            for post in posts[:n]:
                pd = post.get("data", {})
                title   = pd.get("title", "")
                selftext = pd.get("selftext", "")
                if len(selftext.split()) < 8:
                    continue
                results.append({
                    "source": f"reddit/r/{sub}",
                    "title": title,
                    "content": selftext[:800],
                    "score": pd.get("score", 0),
                })
        except Exception:
            pass

        return results


class HackerNewsCollector:
    """
    Pulls top HN comments via the public Firebase API.
    HN comments tend to be precise, intellectual, and varied in tone.
    """

    def collect(self, n: int = 8, topic_hint: str = "") -> List[Dict[str, str]]:
        raw = _safe_fetch("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not raw:
            return []

        results = []
        try:
            story_ids = json.loads(raw)[:30]
            random.shuffle(story_ids)
            for sid in story_ids[:12]:
                story_raw = _safe_fetch(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                )
                if not story_raw:
                    continue
                story = json.loads(story_raw)
                # Get first comment
                kids = story.get("kids", [])
                if not kids:
                    continue
                comment_raw = _safe_fetch(
                    f"https://hacker-news.firebaseio.com/v0/item/{kids[0]}.json"
                )
                if not comment_raw:
                    continue
                comment = json.loads(comment_raw)
                text = re.sub(r"<[^>]+>", "", comment.get("text", ""))
                if len(text.split()) < 10:
                    continue
                results.append({
                    "source": "hackernews",
                    "title": story.get("title", ""),
                    "content": text[:800],
                    "score": story.get("score", 0),
                })
                if len(results) >= n:
                    break
        except Exception:
            pass

        return results


class WikipediaCollector:
    """
    Pulls Wikipedia article summaries on topics relevant to Aurora's
    current fail dimensions or OETS gaps.
    Provides precise, well-structured long-form language.
    """

    _DIM_TOPICS = {
        "coherence_maintenance":    ["Working memory", "Narrative", "Stream of consciousness"],
        "context_carryover":        ["Episodic memory", "Continuity of consciousness"],
        "ambiguity_handling":       ["Ambiguity", "Semantic ambiguity", "Pragmatics"],
        "uncertainty_signaling":    ["Epistemic humility", "Uncertainty quantification"],
        "emotional_calibration":    ["Emotional intelligence", "Affect (psychology)"],
        "framing_selection":        ["Framing effect", "Conceptual framing"],
        "semantic_precision":       ["Semantics", "Word sense disambiguation"],
        "perspective_integration":  ["Theory of mind", "Empathy"],
        "multi_turn_stability":     ["Dialogue", "Conversation analysis"],
    }

    def collect(self, n: int = 3,
                topic_hint: str = "",
                fail_dim: str = "") -> List[Dict[str, str]]:
        topics = self._DIM_TOPICS.get(fail_dim, [])
        if not topics:
            topics = ["Consciousness", "Language", "Learning", "Memory", "Emotion"]
        if topic_hint:
            topics = [topic_hint] + topics

        results = []
        for topic in random.sample(topics, min(n, len(topics))):
            encoded = urllib.parse.quote(topic.replace(" ", "_"))
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
            raw = _safe_fetch(url)
            if not raw:
                continue
            try:
                data = json.loads(raw)
                extract = data.get("extract", "")
                if len(extract.split()) < 20:
                    continue
                results.append({
                    "source": f"wikipedia/{topic}",
                    "title": data.get("title", topic),
                    "content": extract[:1000],
                    "score": 1,
                })
            except Exception:
                continue
        return results


class DuckDuckGoCollector:
    """
    Uses DuckDuckGo's instant answer API for topic searches.
    Provides real-world context on any query Aurora is curious about.
    """

    def collect(self, n: int = 5, topic_hint: str = "") -> List[Dict[str, str]]:
        if not topic_hint:
            topic_hint = random.choice([
                "what does it mean to understand something",
                "human conversation patterns",
                "how people express uncertainty",
                "natural language informal speech",
                "empathy in communication",
            ])
        encoded = urllib.parse.quote(topic_hint)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        raw = _safe_fetch(url)
        if not raw:
            return []

        results = []
        try:
            data = json.loads(raw)
            # Abstract
            abstract = data.get("AbstractText", "")
            if len(abstract.split()) > 15:
                results.append({
                    "source": "duckduckgo/abstract",
                    "title": data.get("Heading", topic_hint),
                    "content": abstract[:800],
                    "score": 2,
                })
            # Related topics
            for rt in data.get("RelatedTopics", [])[:n]:
                text = rt.get("Text", "")
                if len(text.split()) > 10:
                    results.append({
                        "source": "duckduckgo/related",
                        "title": topic_hint,
                        "content": text[:400],
                        "score": 1,
                    })
        except Exception:
            pass
        return results


# ===========================================================================
# LESSON SYNTHESIZER
# ===========================================================================

@dataclass
class Lesson:
    """A synthesized teaching unit for Aurora."""
    dimension: str              # which fail dimension this targets
    source: str                 # where the example came from
    example: str                # the raw human text example
    humanness_score: float      # how human the example is (0-1)
    pattern_notes: List[str]    # what makes this example natural
    teaching_text: str          # the full lesson as delivered to Aurora


class LessonSynthesizer:
    """
    Takes raw collected content and synthesizes targeted lessons.
    Scores examples, extracts what makes them natural, and builds
    teaching text tailored to Aurora's current fail dimensions.
    """

    _PATTERN_EXTRACTORS = [
        (r"\b(?:because|therefore|thus|so|hence|as a result|which leads|consequently)\b",
         "Causal bridging — shows how one state leads to another so the meaning arrow stays directed."),
        (r"\b(?:as (?:I|we) (?:mentioned|noted|said)|back to|again|returning to|that idea|that thread)\b",
         "Referent retention — drags previous anchors forward so the boundary keeps its resolution."),
        (r"\b(?:this thread|continuing|following up|next step|looping back|picking up|keep this thread)\b",
         "Topic thread continuity — keeps the same topic surface alive across turns, which deepens the structural meaning."),
        (r"\b(?:that means|which means|that is|i\.e\.|in other words|defined as|redefined as)\b",
         "Definition reuse — restates or reuses a precise definition so the boundary map stays coherent."),
        (r"\?",
         "Ends with or contains a question — keeps the signal open, inviting the next energy flow."),
    ]

    def synthesize(
        self,
        items: List[Dict[str, str]],
        fail_dim: str,
        scorer=None,
    ) -> List[Lesson]:
        """
        Score collected items and build lessons from the best examples.
        """
        lessons = []
        for item in items:
            content = item.get("content", "")
            if len(content.split()) < 15:
                continue

            # Score humanness
            h_score = 0.7
            if scorer:
                h_score = scorer.score(content)

            # Only teach from genuinely human examples
            if h_score < 0.45:
                continue

            # Extract patterns present in this example
            patterns = []
            for pattern, note in self._PATTERN_EXTRACTORS:
                if re.search(pattern, content, re.IGNORECASE):
                    patterns.append(note)

            if not patterns:
                continue

            # Build teaching text
            source = item.get("source", "unknown")
            teaching = self._build_teaching_text(
                content, patterns, fail_dim, source, h_score
            )

            lessons.append(Lesson(
                dimension=fail_dim,
                source=source,
                example=content[:400],
                humanness_score=h_score,
                pattern_notes=patterns,
                teaching_text=teaching,
            ))

        # Sort by humanness score — teach from best examples first
        lessons.sort(key=lambda l: -l.humanness_score)
        return lessons[:5]

    def _build_teaching_text(
        self,
        example: str,
        patterns: List[str],
        dimension: str,
        source: str,
        score: float,
    ) -> str:
        dim_readable = dimension.replace("_", " ")
        lines = [
            f"[LESSON: {dim_readable}]",
            f"Source: {source} | Humanness: {score:.2f}",
            "",
            "Here is an example of natural human communication:",
            f"---",
            example[:300],
            f"---",
            "",
            f"What makes this natural (patterns present):",
        ]
        for i, p in enumerate(patterns[:4], 1):
            lines.append(f"  {i}. {p}")
        lines += [
            "",
            f"Apply these patterns when expressing yourself. Natural communication "
            f"is not about sounding correct — it is about sounding present. "
            f"The patterns above signal that a mind is actively thinking, "
            f"not reciting.",
        ]
        return "\n".join(lines)


# ===========================================================================
# LESSON DELIVERER
# ===========================================================================

class LessonDeliverer:
    """
    Feeds synthesized lessons into Aurora's learning systems.
    """

    def deliver(self, lessons: List[Lesson], systems: Dict[str, Any]) -> int:
        """Deliver lessons to Aurora's systems. Returns count delivered."""
        count = 0
        for lesson in lessons:
            try:
                self._deliver_one(lesson, systems)
                count += 1
            except Exception:
                pass
        return count

    def _deliver_one(self, lesson: Lesson, systems: Dict[str, Any]) -> None:
        # 1. Gateway witness — Aurora hears the example as knowledge feed
        try:
            from aurora_governance_persistence_gateway import StreamType
            from aurora_constraint_engine import ExistenceMode
            gw = getattr(systems.get("aurora"), "gateway", None)
            if gw:
                gw.receive(
                    content=lesson.teaching_text[:600],
                    stream_type=StreamType.KNOWLEDGE_FEED,
                    source="human_response_teacher",
                    mode=ExistenceMode.BOUNDED,
                )
        except Exception:
            pass

        # 2. Dream trainer — record the example as a truth target
        dt = systems.get("dream_trainer")
        if dt is not None:
            try:
                # The lesson example IS what natural looks like — mismatch drives learning
                dt.record_corpus_fail_from_comparison(
                    generated="",   # Aurora has no generated version yet
                    truth=lesson.example,
                    mismatch=1.0 - lesson.humanness_score,
                )
            except Exception:
                pass

        # 3. OETS — log as a study event
        try:
            perception = systems.get("perception")
            oets = getattr(perception, "oets", None) if perception else None
            if oets and hasattr(oets, "log_study_event"):
                oets.log_study_event(
                    trigger=f"lesson:{lesson.dimension}",
                    content=lesson.teaching_text[:400],
                    source="human_response_teacher",
                )
        except Exception:
            pass


# ===========================================================================
# TEACHING SESSION ORCHESTRATOR
# ===========================================================================

class HumanResponseTeacher:
    """
    Orchestrates the full teaching cycle:
      collect → synthesize → deliver → log

    Called during training consolidation or on demand.
    """

    def __init__(self, state_dir: str = str(_STATE_DIR)):
        self.state_dir = Path(state_dir)
        self.reddit    = RedditCollector()
        self.hn        = HackerNewsCollector()
        self.wiki      = WikipediaCollector()
        self.ddg       = DuckDuckGoCollector()
        self.synth     = LessonSynthesizer()
        self.deliverer = LessonDeliverer()
        self.scorer    = _get_scorer()
        self._lesson_count = 0

    def teach(
        self,
        systems: Dict[str, Any],
        fail_dim: str = "",
        topic_hint: str = "",
        verbose: bool = False,
    ) -> int:
        """
        Run one teaching session. Collects from all sources, synthesizes
        lessons targeting fail_dim, delivers to Aurora's systems.
        Returns number of lessons delivered.
        """
        if not fail_dim:
            # Auto-select from dream trainer's top fail
            dt = systems.get("dream_trainer")
            if dt:
                top = dt.ledger.get_top_fails(n=1)
                fail_dim = top[0][0] if top else "emotional_calibration"
            else:
                fail_dim = "emotional_calibration"

        if verbose:
            print(f"  [TEACHER] Teaching session — dimension: {fail_dim}")

        # Collect from all sources (parallel-ish via sequential calls)
        items: List[Dict[str, str]] = []
        for collector, kwargs in [
            (self.reddit, {"n": 6}),
            (self.hn,     {"n": 5}),
            (self.wiki,   {"n": 3, "fail_dim": fail_dim}),
            (self.ddg,    {"n": 4, "topic_hint": topic_hint or fail_dim.replace("_", " ")}),
        ]:
            try:
                collected = collector.collect(**kwargs)
                items.extend(collected)
                if verbose:
                    src = type(collector).__name__.replace("Collector","").lower()
                    print(f"  [TEACHER] {src}: {len(collected)} items collected")
            except Exception as e:
                if verbose:
                    print(f"  [TEACHER] {type(collector).__name__} error: {e}")

        if not items:
            if verbose:
                print("  [TEACHER] No items collected — skipping session.")
            return 0

        # Synthesize lessons
        lessons = self.synth.synthesize(items, fail_dim, scorer=self.scorer)
        if verbose:
            print(f"  [TEACHER] Synthesized {len(lessons)} lessons "
                  f"(from {len(items)} items)")

        # Deliver
        delivered = self.deliverer.deliver(lessons, systems)
        self._lesson_count += delivered

        # Log
        self._log_session(fail_dim, lessons, delivered)

        if verbose and lessons:
            best = lessons[0]
            print(f"  [TEACHER] Best example (score={best.humanness_score:.2f}, "
                  f"src={best.source}):")
            print(f"    {best.example[:120]}...")
            print(f"  [TEACHER] Patterns: {best.pattern_notes[:2]}")

        return delivered

    def _log_session(
        self,
        dimension: str,
        lessons: List[Lesson],
        delivered: int,
    ) -> None:
        import datetime
        log = []
        if _LESSON_LOG.exists():
            try:
                log = json.loads(_LESSON_LOG.read_text())
            except Exception:
                pass
        log.append({
            "time": datetime.datetime.now().isoformat(),
            "dimension": dimension,
            "lessons_delivered": delivered,
            "sources": list({l.source.split("/")[0] for l in lessons}),
            "avg_humanness": (
                sum(l.humanness_score for l in lessons) / len(lessons)
                if lessons else 0
            ),
        })
        log = log[-200:]   # keep last 200 sessions
        _LESSON_LOG.write_text(json.dumps(log, indent=2))

    def summary(self) -> str:
        if not _LESSON_LOG.exists():
            return "No teaching sessions yet."
        try:
            log = json.loads(_LESSON_LOG.read_text())
        except Exception:
            return "Could not read lesson log."
        if not log:
            return "No sessions logged."
        total = sum(s.get("lessons_delivered", 0) for s in log)
        avg_h = sum(s.get("avg_humanness", 0) for s in log) / len(log)
        dims  = {}
        for s in log:
            d = s.get("dimension", "unknown")
            dims[d] = dims.get(d, 0) + 1
        top_dim = max(dims, key=dims.get) if dims else "none"
        return (
            f"Teaching sessions: {len(log)} | "
            f"Total lessons: {total} | "
            f"Avg humanness of examples: {avg_h:.2f} | "
            f"Most-taught dimension: {top_dim}"
        )


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Aurora Human Response Teacher")
    parser.add_argument("--history", action="store_true",
                        help="Show teaching session history")
    parser.add_argument("--source",  type=str, default="",
                        help="Collect from specific source: reddit/hn/wiki/ddg")
    parser.add_argument("--dim",     type=str, default="",
                        help="Target a specific fail dimension")
    parser.add_argument("--topic",   type=str, default="",
                        help="Topic hint for search")
    args = parser.parse_args()

    teacher = HumanResponseTeacher()

    if args.history:
        print(teacher.summary())
        if _LESSON_LOG.exists():
            log = json.loads(_LESSON_LOG.read_text())
            print(f"\nLast 5 sessions:")
            for s in log[-5:]:
                print(f"  [{s['time']}] dim={s['dimension']} "
                      f"delivered={s['lessons_delivered']} "
                      f"sources={s['sources']}")
        sys.exit(0)

    # Standalone test — run without full Aurora systems
    print("Running teaching session (standalone — no Aurora systems)...")
    teacher.teach(systems={}, verbose=True,
                  fail_dim=args.dim or "emotional_calibration",
                  topic_hint=args.topic)
    print(f"\n{teacher.summary()}")
