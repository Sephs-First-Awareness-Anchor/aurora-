#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA  Unified Runner
========================
This is what you run.

  python3 aurora.py               Interactive chat
  python3 aurora.py --train 50    Train 50 epochs before chat
  python3 aurora.py --explore     Autonomous exploration mode
  python3 aurora.py --feed URL    Feed a web page to Aurora
  python3 aurora.py --status      Show full system status

BOOT SEQUENCE:
  Layer 0: Foundational Contract (existence modes, ontological claims)
  Layer 1: IVM Lattice (5-axis toroidal geometry)
  Layer 2: I-State Beings (10 beings, collective synthesis)
  Layer 3: Dimensional Systems (DPS, DMC, DER, DMM)
  Layer 4: Consciousness Engine (entropy, DCE assembly, DPME drift correction)
  Layer 5: Expression & Perception (dual pipeline: perceive inward, express outward)
  Layer 6: Behavioral Identity (DNA, traits, crystals)
  Layer 7: Simulation Engine (avatars, inception entities, conscious learning)
  Layer 8: Governance, Persistence & N-Space Gateway

Everything flows through the foundational pipeline.
Nothing enters without validation. Nothing exits without personality.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import sys
import os
import time
import json
import argparse
import re
import subprocess
import importlib.util
import shutil
from pathlib import Path
import signal
import threading
import select
import atexit
import urllib.request
from typing import Optional, Dict, Any, List, Tuple, Callable

# Consolidated support stack (parser + identity persistence + semantic helpers)
from aurora_support_stack import (
    UtteranceParser,
    parse_utterance,
    CoreRelationalIdentity,
    EnhancedStatePersistence,
    ConversationMemory,
    OETSPersistence,
    seed_identity_into_oets,
    seed_identity_into_dna,
    ResearchResult,
)

try:
    from aurora_internal.aurora_local_llm_bridge import interpret_input, format_output
except Exception:
    def interpret_input(text: str) -> Dict[str, Any]:
        return {"ok": False, "available": False, "error": "local_llm_bridge_import_failed"}

    def format_output(message: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "ok": False,
            "available": False,
            "message": "",
            "original": message or "",
            "error": "local_llm_bridge_import_failed",
        }


# ============================================================================
# RUNTIME DEPENDENCY BOOTSTRAP
# ============================================================================

_LOCAL_LLM_SERVER_PROC = None


def _local_llm_url() -> str:
    return os.environ.get("AURORA_LOCAL_LLM_SERVER_URL", "").strip().rstrip("/")


def _local_llm_server_healthy(url: str, timeout: float = 1.0) -> bool:
    if not url:
        return False
    for path in ("/health", "/v1/models"):
        try:
            with urllib.request.urlopen(f"{url}{path}", timeout=timeout) as resp:
                if 200 <= int(getattr(resp, "status", 200)) < 500:
                    return True
        except Exception:
            continue
    return False


def _cleanup_local_llm_server() -> None:
    global _LOCAL_LLM_SERVER_PROC
    proc = _LOCAL_LLM_SERVER_PROC
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    except Exception:
        pass
    _LOCAL_LLM_SERVER_PROC = None


def _maybe_start_local_llm_server(verbose: bool = True) -> None:
    """Start llama-server automatically for the local LLM seam when available."""
    global _LOCAL_LLM_SERVER_PROC
    if os.environ.get("AURORA_LOCAL_LLM_AUTOSTART", "1").strip().lower() in {"0", "false", "no", "off"}:
        return
    if os.environ.get("AURORA_USE_LOCAL_LLM", "1").strip().lower() in {"0", "false", "no", "off"}:
        return

    url = _local_llm_url() or "http://127.0.0.1:8080"
    if _local_llm_server_healthy(url):
        os.environ["AURORA_LOCAL_LLM_SERVER_URL"] = url
        if verbose:
            print(f"  [LLM] Using existing local llama server at {url}")
        return

    server_bin = shutil.which("llama-server")
    model = os.environ.get("AURORA_LOCAL_LLM_MODEL") or os.environ.get("AURORA_ARTICULATOR_MODEL") or "Models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    if not server_bin or not Path(model).exists():
        if verbose:
            print("  [LLM] Local llama server not started (missing llama-server or model).")
        return

    host = os.environ.get("AURORA_LOCAL_LLM_HOST", "127.0.0.1")
    port = os.environ.get("AURORA_LOCAL_LLM_PORT", "8080")
    ctx = os.environ.get("AURORA_LOCAL_LLM_CTX", "512")
    threads = os.environ.get("AURORA_LOCAL_LLM_THREADS", "1")
    log_path = Path("aurora_state") / "llama_server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    cmd = [
        server_bin,
        "-m", model,
        "--host", host,
        "--port", str(port),
        "-c", str(ctx),
        "-t", str(threads),
        "-np", "1",
        "-to", "600",
    ]
    try:
        _LOCAL_LLM_SERVER_PROC = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as exc:
        if verbose:
            print(f"  [LLM] Failed to start llama-server: {exc}")
        return

    os.environ["AURORA_LOCAL_LLM_SERVER_URL"] = url
    os.environ["AURORA_USE_LOCAL_LLM"] = "1"
    os.environ.pop("AURORA_ARTICULATOR_ISOLATED_ENABLED", None)
    os.environ.pop("AURORA_LOCAL_LLM_WORKER_ENABLED", None)
    os.environ.pop("AURORA_ARTICULATOR_PY_ENABLED", None)
    atexit.register(_cleanup_local_llm_server)

    if verbose:
        print(f"  [LLM] Starting local llama server at {url} (log: {log_path})")
    deadline = time.time() + float(os.environ.get("AURORA_LOCAL_LLM_STARTUP_WAIT", "45") or 45)
    while time.time() < deadline:
        if _LOCAL_LLM_SERVER_PROC.poll() is not None:
            if verbose:
                print("  [LLM] llama-server exited during startup; continuing without local LLM.")
            os.environ.pop("AURORA_LOCAL_LLM_SERVER_URL", None)
            return
        if _local_llm_server_healthy(url):
            if verbose:
                print("  [LLM] Local llama server is ready.")
            return
        time.sleep(1.0)
    if verbose:
        print("  [LLM] llama-server is still loading; Aurora will connect when it becomes ready.")

def _is_termux_runtime() -> bool:
    prefix = os.environ.get('PREFIX', '')
    return ('com.termux' in prefix.lower() or
            os.environ.get('TERMUX_VERSION') is not None or
            shutil.which('termux-info') is not None)


def _ensure_runtime_dependencies(verbose: bool = True):
    """
    Best-effort dependency bootstrap at startup.
    Installs only missing python modules and skips packages likely to fail
    on current platform. Never raises; Aurora should still boot with fallbacks.
    """
    if os.environ.get('AURORA_SKIP_DEP_INSTALL', '').lower() in ('1', 'true', 'yes'):
        if verbose:
            print("  [DEPS] Auto-install skipped (AURORA_SKIP_DEP_INSTALL set)")
        return

    py = sys.executable
    is_termux = _is_termux_runtime()

    targets = [
        # (import_name, pip_package, termux_safe)
        ('numpy', 'numpy', True),
        ('speech_recognition', 'SpeechRecognition', True),
        ('sounddevice', 'sounddevice', True),
        ('pyttsx3', 'pyttsx3', False),
        ('cv2', 'opencv-python', False),
        ('PIL', 'Pillow', True),
        ('soundfile', 'soundfile', True),
        ('librosa', 'librosa', True),
        ('pydub', 'pydub', True),
    ]

    if is_termux:
        # Desktop-heavy packages are often unavailable in Termux pip wheels.
        targets = [t for t in targets if t[2]]

    missing = []
    for import_name, pip_name, _ in targets:
        if importlib.util.find_spec(import_name) is None:
            missing.append((import_name, pip_name))

    if not missing:
        if verbose:
            print("  [DEPS] Runtime dependencies already satisfied")
        return

    if verbose:
        print(f"  [DEPS] Installing {len(missing)} missing dependency package(s)...")

    for import_name, pip_name in missing:
        try:
            cmd = [py, '-m', 'pip', 'install', '--quiet', pip_name]
            subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            installed = importlib.util.find_spec(import_name) is not None
            if verbose:
                status = 'OK' if installed else 'SKIP'
                print(f"  [DEPS] {status}: {pip_name}")
        except Exception as e:
            if verbose:
                print(f"  [DEPS] SKIP: {pip_name} ({e})")


def _get_autonomous_access_state() -> Tuple[bool, str]:
    """
    Evaluate whether autonomous system actions are currently authorized.
    Controlled via environment variables set by scripts/run_aurora.sh.
    """
    raw_flag = os.environ.get('AURORA_AUTONOMOUS_ACCESS', '0').strip().lower()
    enabled = raw_flag in ('1', 'true', 'yes', 'on')

    raw_until = os.environ.get('AURORA_AUTONOMOUS_UNTIL', '0').strip()
    until = 0
    try:
        until = int(raw_until)
    except ValueError:
        until = 0

    if not enabled:
        return False, 'inactive (lease not granted)'

    if until > 0:
        now = int(time.time())
        if now >= until:
            return False, 'inactive (lease expired)'
        remaining = until - now
        return True, f'active ({remaining}s remaining)'

    return True, 'active (no expiry provided)'

# ============================================================================
# WORKING MEMORY  -- Per-session short-term context
# ============================================================================

class WorkingMemory:
    """
    Per-session short-term memory that tracks what's being talked about,
    what facts have been stated, and what was recently learned  -- so Aurora
    can connect events across turns instead of treating each one in isolation.
    """

    _COLOR_WORDS = {
        'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
        'black', 'white', 'gray', 'grey', 'brown', 'violet', 'cyan',
        'magenta', 'indigo', 'gold', 'silver', 'maroon', 'olive', 'teal',
    }

    def __init__(self):
        self.current_topic: str = ""
        self.topic_stack: list = []
        self.stated_facts: dict = {}       # {subject: {property: value, ...}}
        self.recent_entities: list = []
        self.last_search_results: list = []
        self.last_search_query: str = ""
        self.last_question_understood: dict = {}
        self.last_aurora_response: str = ""
        self.turn_count: int = 0
        self.field_map = None  # Optional ConstraintFieldAccumulator (read-only observer)

    def set_field_map(self, field_map) -> None:
        """Attach a ConstraintFieldAccumulator as read-only observer. Pass None to detach."""
        self.field_map = field_map

    def update_topic(self, topic: str):
        if topic and topic != self.current_topic:
            if self.current_topic:
                self.topic_stack = ([self.current_topic] + self.topic_stack)[:6]
            self.current_topic = topic

    def add_entities(self, entities: list):
        for e in entities:
            el = e.lower()
            if el not in self.recent_entities:
                self.recent_entities = ([el] + self.recent_entities)[:10]

    def note_user_facts(self, user_text: str):
        """
        Parse user statements and extract asserted facts.
        Supports: "X is Y", "X are Y", "the X is Y", "grass is green", etc.
        """
        import re
        # Don't try to extract facts from questions
        if user_text.strip().endswith('?'):
            return
        _skip_subjects = {
            'how', 'what', 'why', 'where', 'when', 'who', 'which', 'it',
            'this', 'that', 'they', 'he', 'she', 'we', 'you', 'i', 'my',
            'well', 'okay', 'ok', 'yes', 'no', 'but', 'and', 'so',
        }
        t = user_text.strip().rstrip('.,!?')
        # "X is Y" / "X are Y" patterns
        m = re.match(
            r'^(?:the\s+|a\s+|an\s+)?([a-zA-Z]+)\s+(?:is|are)\s+(.+)$', t, re.IGNORECASE
        )
        if m and m.group(1).lower() not in _skip_subjects:
            subject = m.group(1).lower()
            predicate = m.group(2).lower().strip()
            if subject not in self.stated_facts:
                self.stated_facts[subject] = {}
            self.stated_facts[subject]['description'] = predicate
            # Extract color property specifically
            for cw in self._COLOR_WORDS:
                if cw in predicate.split():
                    self.stated_facts[subject]['color'] = cw
                    break

        # "X is to A as Y is to B" (analogy)  -- store both sides
        m2 = re.match(
            r'(\w+)\s+is\s+to\s+(\w+)\s+as\s+(\w+)\s+is\s+to\s+(\w+)', t, re.IGNORECASE
        )
        if m2:
            a_word, a_ref = m2.group(1).lower(), m2.group(2).lower()
            b_word, b_ref = m2.group(3).lower(), m2.group(4).lower()
            for word, ref in [(a_word, a_ref), (b_word, b_ref)]:
                if word not in self.stated_facts:
                    self.stated_facts[word] = {}
                self.stated_facts[word]['analogous_to'] = ref

    def get_stated_fact(self, subject: str, prop: str = None):
        facts = self.stated_facts.get(subject.lower(), {})
        if prop:
            return facts.get(prop)
        return facts

    def update_from_turn(self, understood: dict, user_text: str):
        self.turn_count += 1
        topic = understood.get('topic', '')
        self.update_topic(topic)
        self.add_entities(understood.get('entities', []))
        self.note_user_facts(user_text)
        self.last_question_understood = understood

    def resolve_topic(self, understood: dict) -> str:
        """
        Resolve the real topic for vague follow-ups.
        "what about in Ohio?" â†’ 'ohio' is an entity not a topic change â†’ keep current_topic.
        "what about the color?" â†’ 'color' is a genuine new topic.
        """
        topic = understood.get('topic', '')
        entities = understood.get('entities', [])
        vague = {'it', 'this', 'that', 'thing', 'there', 'here'}
        # empty topic = conversational statement, NOT a vague reference  -- don't substitute
        # If the "topic" is actually a proper noun entity, it's a location modifier
        # not a topic change  -- keep the existing conversation topic
        topic_is_entity = topic and any(topic == e.lower() for e in entities)
        if (topic in vague or topic_is_entity) and self.current_topic:
            return self.current_topic
        return topic

    def get_context_words(self) -> list:
        ctx = []
        if self.current_topic:
            ctx.append(self.current_topic)
        ctx.extend(self.recent_entities[:4])
        return ctx


# ============================================================================
# REASONING ENGINE  -- Multi-step thinking to answer questions
# ============================================================================

class ReasoningEngine:
    """
    Aurora's ability to THINK through a question rather than just retrieve
    a template.  Chains: working memory â†’ OETS knowledge â†’ search evidence
    to form a direct, meaningful answer.
    """

    _PROPERTY_WORDS = {
        'color', 'colour', 'size', 'weight', 'shape', 'smell', 'taste',
        'sound', 'texture', 'temperature', 'height', 'length', 'width',
        'speed', 'age', 'type', 'kind', 'purpose', 'function', 'cause',
        'effect', 'meaning', 'definition', 'example', 'location', 'origin',
    }

    _COLOR_WORDS = {
        'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
        'black', 'white', 'gray', 'grey', 'brown', 'violet', 'cyan',
        'magenta', 'indigo', 'gold', 'silver', 'maroon', 'olive', 'teal',
    }

    def reason(self, user_text: str, understood: dict,
               working_memory, oets, evidence: list = None) -> str:
        """
        Try to answer user_text by stepping through available knowledge.
        Chain: working_memory facts â†’ property reasoning â†’ OETS definitions
               â†’ evidence extraction.
        Returns answer string or "" if reasoning fails.
        """
        import re
        topic = understood.get('topic', '')
        topic_words = understood.get('topic_words', [])
        query_type = understood.get('query_type', '')

        # Only use OETS/evidence for actual knowledge questions  -- not conversational text
        _is_knowledge_query = (
            user_text.strip().endswith('?') or
            query_type in ('definition', 'factual_entity', 'factual_general',
                           'weather_location', 'how_to') or
            any(user_text.lower().startswith(w) for w in (
                'what', 'how', 'why', 'where', 'who', 'when', 'which',
                'can', 'could', 'would', 'is ', 'are ', 'do ', 'does ',
                'define', 'explain', 'tell me', 'look up',
            ))
        )

        # Step 1: Working memory  -- did the user or Aurora already state this fact?
        # Steps 1-4 only run for actual knowledge queries, not conversational text
        if not _is_knowledge_query:
            return ""

        if working_memory and topic_words:
            for tw in topic_words:
                facts = working_memory.get_stated_fact(tw)
                if facts:
                    color = facts.get('color')
                    desc = facts.get('description')
                    if color and any(w in user_text.lower() for w in ('color', 'colour')):
                        return f"{tw.capitalize()} is {color}."
                    if desc:
                        return f"{tw.capitalize()} is {desc}."

        # Step 2: Detect property questions  -- "what COLOR is SUBJECT?"
        #  topic_words[0] = property, topic_words[1] = subject
        if len(topic_words) >= 2 and topic_words[0] in self._PROPERTY_WORDS:
            property_word = topic_words[0]
            subject_word = topic_words[1]

            # Check working memory for the specific property
            if working_memory:
                val = working_memory.get_stated_fact(subject_word, property_word)
                if val:
                    return f"The {property_word} of {subject_word} is {val}."

            # Check OETS definition for the subject
            if oets:
                answer = self._oets_property_lookup(subject_word, property_word, oets)
                if answer:
                    return answer

            # Check evidence for property+subject co-occurrence
            if evidence:
                answer = self._evidence_property_lookup(property_word, subject_word, evidence)
                if answer:
                    return answer

        # Step 3: OETS definition answer  -- only for definition-type queries
        if oets and topic and query_type == 'definition':
            node = oets.web.get_node(topic)
            if node and node.definitions:
                best = node.definitions[0].get('text', '')
                if len(best) > 15:
                    related = []
                    for rel in list(node.relations.values())[:3]:
                        other = (rel.target_word if rel.source_word == topic
                                 else rel.source_word)
                        if other and other != topic:
                            related.append(other)
                    answer = f"{topic.capitalize()}: {best}"
                    if related:
                        answer += f" (connected to: {', '.join(related[:3])})"
                    return answer

        # Step 4: Direct extraction from evidence
        if evidence:
            return _extract_factual_answer(user_text, evidence)

        return ""

    def _oets_property_lookup(self, subject: str, prop: str, oets) -> str:
        import re
        node = oets.web.get_node(subject)
        if not node:
            return ""
        for defn in node.definitions:
            text = defn.get("text", "").lower()
            if prop in text:
                if prop in ('color', 'colour'):
                    for cw in self._COLOR_WORDS:
                        if cw in text:
                            return f"{subject.capitalize()} is {cw} in color."
                m = re.search(rf'{re.escape(prop)}\s+(?:is\s+|of\s+)?(\w+)', text)
                if m:
                    return f"The {prop} of {subject} is {m.group(1)}."
        return ""

    def _evidence_property_lookup(self, prop: str, subject: str, evidence: list) -> str:
        import re
        for ev in evidence[:6]:
            snippet = ev.get("snippet", "").lower()
            if subject not in snippet:
                continue
            sentences = re.split(r'(?<=[.!?])\s+', snippet)
            for sent in sentences:
                if subject not in sent:
                    continue
                if prop in ('color', 'colour'):
                    for cw in self._COLOR_WORDS:
                        if cw in sent:
                            return sent.strip().capitalize()
                if prop in sent:
                    m = re.search(
                        rf'{re.escape(subject)}[^.]*{re.escape(prop)}[^.]*', sent
                    )
                    if m:
                        return m.group(0).strip().capitalize()
        return ""


# ============================================================================
# SEARCH ADAPTER + QUESTION FILTER (Dual-Response Pipeline Support)
# ============================================================================

class QueryUnderstanding:
    """
    Understands WHAT a query is asking before any search or response.

    This is the comprehension layer for queries  -- it parses intent, extracts
    the real topic and entities, determines query type, and builds an optimized
    search string that actually maps to what the user wants to know.
    """

    _REMOVE = {
        'what', 'whats', 'who', 'where', 'when', 'why', 'how', 'which',
        'is', 'are', 'was', 'were', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'can', 'may', 'might', 'be', 'been', 'being',
        'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
        'and', 'or', 'but', 'so', 'yet', 'it', 'its', 'this', 'that',
        'i', 'you', 'we', 'they', 'my', 'your', 'some', 'any',
        'tell', 'me', 'about', 'please', 'know', 'find', 'look', 'up',
        'give', 'get', 'show', 'explain', 'describe', 'define',
        'like', 'just', 'really', 'very', 'also', 'too', 'much',
        'going', 'suppose', 'supposed', 'gonna', 'pertain', 'pertains',
        'regarding', 'concerning', 'relates', 'related', 'means', 'mean',
        'say', 'said', 'think', 'thought', 'see', 'seem', 'feel',
        'asked', 'asking', 'want', 'wanted', 'need', 'needed', 'knew',
        # Discourse markers that are never the topic
        'okay', 'ok', 'alright', 'ight', 'well', 'now', 'then', 'yeah',
        'yes', 'nope', 'yep', 'sure', 'right', 'actually', 'basically',
        'literally', 'honestly', 'anyway', 'anyways', 'wait', 'hold',
        'hmm', 'hm', 'uh', 'um', 'ah', 'oh', 'hey', 'hi', 'hello',
    }

    _TIME_WORDS = {
        'today', 'tomorrow', 'yesterday', 'now', 'currently', 'tonight',
        'week', 'month', 'year', 'recently', 'latest', 'current',
    }

    _SKIP_CAPS = {
        'what', 'where', 'how', 'why', 'who', 'when', 'which', 'the',
        'a', 'is', 'are', 'can', 'could', 'would', 'should', 'i',
        'you', 'we', 'they', 'he', 'she', 'it', 'my', 'your',
        # Sentence-start capitalization artifacts (not proper nouns)
        'im', 'ive', 'id', 'ill', 'its', 'isnt', 'arent', 'wasnt',
        'dont', 'doesnt', 'didnt', 'cant', 'wont', 'wouldnt', 'shouldnt',
        'so', 'but', 'and', 'or', 'if', 'then', 'also', 'just', 'still',
        'yeah', 'yes', 'no', 'ok', 'okay', 'well', 'now', 'right',
        'happy', 'glad', 'great', 'good', 'nice', 'fine', 'sure',
        'thanks', 'thank', 'please', 'sorry', 'wow', 'oh', 'ah',
    }

    def parse(self, text: str) -> dict:
        import re
        t = text.strip()
        t_low = t.lower()

        # Extract proper nouns (locations, names, organizations)
        entities = [w for w in re.findall(r'\b[A-Z][a-z]{1,}\b', t)
                    if w.lower() not in self._SKIP_CAPS]

        # Extract content words (remove filler, keep topic words)
        words = re.findall(r'[a-z]{3,}', t_low)
        all_content = [w for w in words if w not in self._REMOVE]
        time_ref = next((w for w in all_content if w in self._TIME_WORDS), None)
        topic_words = [w for w in all_content if w not in self._TIME_WORDS]

        # Primary topic = first real content word
        topic = topic_words[0] if topic_words else (entities[0].lower() if entities else "")

        # Determine what kind of question this is
        query_type = self._classify_query_type(t_low, topic, entities)

        # Build an optimized search string
        search_query = self._build_search_query(topic, entities, time_ref, topic_words, query_type)

        return {
            'topic': topic,
            'topic_words': topic_words[:5],
            'entities': entities,
            'time_ref': time_ref,
            'query_type': query_type,
            'search_query': search_query,
        }

    def _classify_query_type(self, t_low: str, topic: str, entities: list) -> str:
        import re
        # Weather / atmospheric conditions in a location
        weather_words = {'weather', 'forecast', 'temperature', 'rain', 'snow',
                         'humidity', 'wind', 'climate', 'sunny', 'cloudy'}
        if topic in weather_words or any(w in weather_words for w in t_low.split()):
            if entities:
                return 'weather_location'
            return 'definition'
        # Definition queries ("what is X", "what does X mean", "define X", "look up X")
        if re.search(r'\b(what\s+(is|are|does)|define|definition\s+of|meaning\s+of|look\s+up)\b', t_low):
            return 'definition'
        # How-to queries
        if re.search(r'\bhow\s+(do|does|can|to|would)\b', t_low):
            return 'how_to'
        # Entity/location queries (has proper nouns)
        if entities:
            return 'factual_entity'
        return 'factual_general'

    def _build_search_query(self, topic, entities, time_ref, topic_words, query_type):
        parts = []
        if query_type == 'weather_location' and entities:
            # "Piqua Ohio weather today"  -- location first, then topic, then time
            parts.extend(entities[:2])
            parts.append('weather')
            if time_ref:
                parts.append(time_ref)
        elif query_type == 'definition':
            # Just the topic word  -- dictionary/Wikipedia will handle it
            parts = [topic] if topic else list(topic_words[:2])
        elif entities and topic:
            # Topic + entities: "weather Piqua Ohio"
            parts.append(topic)
            parts.extend(entities[:2])
            if time_ref:
                parts.append(time_ref)
        elif topic_words:
            parts.extend(topic_words[:4])
        return " ".join(parts) if parts else topic


class SearchAdapter:
    """
    Aurora's external search interface  -- robust, API-based, NO silent failures.

    Uses free, reliable APIs that don't require API keys:
      1. Free Dictionary API (dictionaryapi.dev)  -- definitions, synonyms, antonyms
      2. DuckDuckGo Instant Answer API  -- concept summaries
      3. Wikipedia REST + search APIs  -- broader context
      4. DuckDuckGo lite HTML search  -- real web results (best-effort)

    This replaces the older googlesearch-python dependency so Aurora can
    research on a clean install with only the standard library.

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    def __init__(self, user_agent: str = "Aurora/2.0 SearchAdapter"):
        self.user_agent = user_agent
        self._last_error: Optional[str] = None
        self._search_attempts = 0
        self._search_successes = 0
        self._query_understanding = UtteranceParser()

    # ----------------------------------------------------------------
    # Core HTTP fetch (shared by all methods)
    # ----------------------------------------------------------------

    def _fetch_url_text(self, url: str, timeout: int = 12) -> str:
        """Fetch a URL and return stripped text. Raises on failure."""
        import urllib.request

        req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")

        # Strip HTML
        txt = re.sub(r'<script.*?>.*?</script>', ' ', raw, flags=re.DOTALL | re.IGNORECASE)
        txt = re.sub(r'<style.*?>.*?</style>', ' ', txt, flags=re.DOTALL | re.IGNORECASE)
        txt = re.sub(r'<[^>]+>', ' ', txt)
        txt = re.sub(r'\s+', ' ', txt).strip()
        return txt

    def _fetch_json(self, url: str, timeout: int = 10) -> Any:
        """Fetch a URL and return parsed JSON. Raises on failure."""
        import urllib.request

        req = urllib.request.Request(url, headers={
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)

    # ----------------------------------------------------------------
    # Dictionary API  -- definitions, synonyms, antonyms, examples
    # ----------------------------------------------------------------

    def lookup_word(self, word: str) -> Dict[str, Any]:
        """Look up a word via the Free Dictionary API (structured JSON)."""
        import urllib.parse
        self._search_attempts += 1
        result = {
            "word": word,
            "definitions": [],
            "synonyms": [],
            "antonyms": [],
            "examples": [],
            "part_of_speech": [],
            "phonetics": [],
            "source": "dictionaryapi.dev",
            "success": False,
            "error": None,
        }

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        try:
            data = self._fetch_json(url, timeout=10)
            if not isinstance(data, list) or not data:
                result["error"] = "No entries returned"
                return result

            entry = data[0]

            for phon in entry.get("phonetics", []):
                if isinstance(phon, dict) and phon.get("text"):
                    result["phonetics"].append(phon["text"])

            for meaning in entry.get("meanings", []):
                if not isinstance(meaning, dict):
                    continue
                pos = meaning.get("partOfSpeech", "unknown")
                if pos not in result["part_of_speech"]:
                    result["part_of_speech"].append(pos)

                for syn in meaning.get("synonyms", []) or []:
                    if syn and syn not in result["synonyms"]:
                        result["synonyms"].append(syn)
                for ant in meaning.get("antonyms", []) or []:
                    if ant and ant not in result["antonyms"]:
                        result["antonyms"].append(ant)

                for defn in meaning.get("definitions", []) or []:
                    if not isinstance(defn, dict):
                        continue
                    d_text = defn.get("definition", "")
                    if d_text:
                        result["definitions"].append({"text": d_text, "part_of_speech": pos})
                    for syn in defn.get("synonyms", []) or []:
                        if syn and syn not in result["synonyms"]:
                            result["synonyms"].append(syn)
                    for ant in defn.get("antonyms", []) or []:
                        if ant and ant not in result["antonyms"]:
                            result["antonyms"].append(ant)
                    ex = defn.get("example")
                    if ex:
                        result["examples"].append(ex)

            result["success"] = len(result["definitions"]) > 0
            if result["success"]:
                self._search_successes += 1

        except Exception as e:
            result["error"] = f"Dictionary API: {type(e).__name__}: {e}"
            self._last_error = result["error"]

        return result

    # ----------------------------------------------------------------
    # DuckDuckGo Instant Answer API  -- entity/concept abstracts
    # ----------------------------------------------------------------

    def concept_search(self, query: str) -> Dict[str, Any]:
        import urllib.parse
        self._search_attempts += 1
        result = {
            "query": query,
            "abstract": "",
            "abstract_source": "",
            "abstract_url": "",
            "related_topics": [],
            "source": "duckduckgo",
            "success": False,
            "error": None,
        }

        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        try:
            data = self._fetch_json(url, timeout=10)

            abstract = data.get("Abstract", "")
            if abstract:
                result["abstract"] = abstract
                result["abstract_source"] = data.get("AbstractSource", "")
                result["abstract_url"] = data.get("AbstractURL", "")

            for topic in data.get("RelatedTopics", []) or []:
                if isinstance(topic, dict):
                    text = topic.get("Text", "")
                    first_url = topic.get("FirstURL", "")
                    if text:
                        result["related_topics"].append({"text": text, "url": first_url})
                    for sub in topic.get("Topics", []) or []:
                        if isinstance(sub, dict) and sub.get("Text"):
                            result["related_topics"].append({"text": sub["Text"], "url": sub.get("FirstURL", "")})

            defn = data.get("Definition", "")
            if defn and not result["abstract"]:
                result["abstract"] = defn
                result["abstract_source"] = data.get("DefinitionSource", "")
                result["abstract_url"] = data.get("DefinitionURL", "")

            result["success"] = bool(result["abstract"] or result["related_topics"])
            if result["success"]:
                self._search_successes += 1

        except Exception as e:
            result["error"] = f"DuckDuckGo API: {type(e).__name__}: {e}"
            self._last_error = result["error"]

        return result

    # ----------------------------------------------------------------
    # Wikipedia REST summary
    # ----------------------------------------------------------------

    def wikipedia_summary(self, topic: str, max_chars: int = 2000) -> Dict[str, Any]:
        import urllib.parse
        self._search_attempts += 1
        result = {
            "topic": topic,
            "summary": "",
            "title": "",
            "url": "",
            "source": "wikipedia",
            "success": False,
            "error": None,
        }

        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
        try:
            data = self._fetch_json(url, timeout=10)
            extract = data.get("extract", "")
            if extract:
                result["summary"] = extract[:max_chars]
                result["title"] = data.get("title", topic)
                result["url"] = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                result["success"] = True
                self._search_successes += 1

        except Exception as e:
            result["error"] = f"Wikipedia API: {type(e).__name__}: {e}"
            self._last_error = result["error"]

        return result

    # ----------------------------------------------------------------
    # Query extraction helpers
    # ----------------------------------------------------------------

    def _extract_search_terms(self, raw_query: str) -> List[str]:
        t = (raw_query or "").lower().strip()

        for prefix in ("hey aurora", "hi aurora", "hello aurora", "aurora,",
                       "aurora", "hey", "hi", "hello", "yo", "okay", "ok"):
            if t.startswith(prefix):
                t = t[len(prefix):].lstrip(" ,.-!?")
                break

        t = t.rstrip("?!.")
        remove_words = {
            "what", "whats", "what's", "who", "whos", "who's", "where",
            "wheres", "where's", "when", "whens", "when's", "why", "whys",
            "how", "hows", "how's", "which", "whose", "whom",
            "is", "are", "was", "were", "do", "does", "did", "will",
            "would", "could", "should", "can", "may", "might",
            "the", "a", "an", "of", "in", "on", "at", "to", "for",
            "be", "been", "being", "its", "it", "this", "that",
            "and", "or", "but", "nor", "so", "yet", "both", "either",
            "like", "just", "really", "very", "also", "too", "much",
            "tell", "me", "about", "please", "know", "find",
            "give", "get", "show", "explain", "describe", "define",
            "i", "you", "we", "they", "my", "your", "some", "any",
        }

        words = re.findall(r'[a-z0-9]+', t)
        content_words = [w for w in words if w not in remove_words and len(w) > 1]
        if not content_words:
            content_words = [w for w in words if len(w) > 2]

        queries: List[str] = []
        if content_words:
            queries.append(" ".join(content_words))
            if len(content_words) > 1:
                queries.append(" ".join(reversed(content_words)))
            for w in content_words:
                if len(w) > 3:
                    queries.append(w)
        return queries

    def _extract_natural_query(self, raw_query: str) -> str:
        t = (raw_query or "").strip()
        t_low = t.lower()
        for prefix in ("hey aurora", "hi aurora", "hello aurora", "aurora,",
                       "aurora", "hey", "hi", "hello", "yo", "okay", "ok"):
            if t_low.startswith(prefix):
                t = t[len(prefix):].lstrip(" ,.-!?")
                break
        return t.strip()

    # ----------------------------------------------------------------
    # DuckDuckGo lite HTML search  -- real web results (best-effort)
    # ----------------------------------------------------------------

    def ddg_web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        import urllib.parse
        import urllib.request

        results: List[Dict[str, Any]] = []
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
            with urllib.request.urlopen(req, timeout=12) as response:
                html = response.read().decode("utf-8", errors="replace")

            link_pattern = re.findall(
                r'class="result-link"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
                html, re.IGNORECASE
            )
            snippet_pattern = re.findall(
                r'class="result-snippet">([^<]+)',
                html, re.IGNORECASE
            )

            for i, (link_url, title) in enumerate(link_pattern[:max_results]):
                snippet = snippet_pattern[i].strip() if i < len(snippet_pattern) else ""
                results.append({
                    "title": title.strip(),
                    "url": link_url.strip(),
                    "snippet": snippet,
                    "source": "duckduckgo_web",
                })

        except Exception as e:
            self._last_error = f"DDG web search: {type(e).__name__}: {e}"

        return results

    def wikipedia_search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        import urllib.parse
        results: List[Dict[str, Any]] = []

        url = (f"https://en.wikipedia.org/w/api.php?"
               f"action=query&list=search&srsearch={urllib.parse.quote(query)}"
               f"&srlimit={max_results}&format=json")
        try:
            data = self._fetch_json(url, timeout=10)
            for item in data.get("query", {}).get("search", []) or []:
                title = item.get("title", "")
                snippet_html = item.get("snippet", "")
                snippet = re.sub(r'<[^>]+>', '', snippet_html)
                if title:
                    summary_data = self.wikipedia_summary(title, max_chars=1500)
                    results.append({
                        "title": title,
                        "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                        "snippet": summary_data["summary"] if summary_data["success"] else snippet,
                        "source": "wikipedia",
                    })
        except Exception as e:
            self._last_error = f"Wikipedia search: {type(e).__name__}: {e}"

        return results

    # ----------------------------------------------------------------
    # Combined evidence pack
    # ----------------------------------------------------------------

    def quick_search(self, query: str, max_chars: int = 2000, num_results: int = 5):
        evidence: List[Dict[str, Any]] = []

        # ---- UNDERSTAND the query before searching ----
        understood = self._query_understanding.parse(query)
        topic = understood['topic']
        entities = understood['entities']
        topic_words = understood['topic_words']
        query_type = understood['query_type']
        search_query = understood['search_query']

        if not topic and not entities:
            return evidence

        def _is_relevant(snippet: str) -> bool:
            """Check if a snippet actually relates to what was asked."""
            sn = snippet.lower()
            return any(w in sn for w in topic_words[:3] if len(w) > 3)

        # Strategy 1: For DEFINITION queries, hit dictionary first
        if query_type == 'definition' and topic:
            lookup = self.lookup_word(topic)
            if lookup["success"] and lookup["definitions"]:
                first_def = lookup["definitions"][0]
                pos = first_def.get("part_of_speech", "")
                prefix = f"({pos}) " if pos else ""
                snippet = f"{topic}: {prefix}{first_def['text']}"
                if lookup.get("synonyms"):
                    snippet += f" (synonyms: {', '.join(lookup['synonyms'][:3])})"
                evidence.append({
                    "title": f"Definition: {topic}",
                    "url": "",
                    "snippet": snippet[:max_chars],
                    "source": "dictionary",
                })

        # Strategy 2: DDG instant answer  -- but ONLY if the result is relevant
        # Use first entity for entity queries, topic for everything else
        concept_term = entities[0] if (entities and query_type == 'factual_entity') else topic
        if concept_term and query_type not in ('definition',):
            ddg = self.concept_search(concept_term)
            if ddg["success"] and ddg["abstract"]:
                if _is_relevant(ddg["abstract"]):
                    evidence.append({
                        "title": ddg.get("abstract_source", "DuckDuckGo"),
                        "url": ddg.get("abstract_url", ""),
                        "snippet": ddg["abstract"][:max_chars],
                        "source": "duckduckgo",
                    })
                # If not relevant, skip  -- don't pollute with wrong results

        # Strategy 3: DDG web search using OPTIMIZED query (not raw question)
        if len(evidence) < 3 and search_query:
            for wr in self.ddg_web_search(search_query, max_results=5):
                sn = wr.get("snippet", "")
                if sn and _is_relevant(sn):
                    evidence.append(wr)
                    if len(evidence) >= 3:
                        break

        # Strategy 4: Wikipedia for the topic or entity
        wiki_term = entities[0] if entities else topic
        if len(evidence) < 3 and wiki_term:
            for wr in self.wikipedia_search(wiki_term, max_results=2):
                sn = wr.get("snippet", "")
                if sn:
                    evidence.append(wr)

        # Strategy 5: If still empty, relax relevance and try web search with full topic words
        if not evidence and topic_words:
            fallback_q = " ".join(topic_words[:3])
            for wr in self.ddg_web_search(fallback_q, max_results=3):
                if wr.get("snippet"):
                    evidence.append(wr)

        return evidence[:num_results]

    def deep_search(self, query: str, max_chars: int = 4000, num_results: int = 8):
        evidence = self.quick_search(query, max_chars=max_chars, num_results=num_results)

        for ev in evidence[:2]:
            if ev.get("url") and ev.get("source") in ("duckduckgo_web", "duckduckgo"):
                try:
                    text = self._fetch_url_text(ev["url"], timeout=12)
                    if text and len(text) > len(ev.get("snippet", "")):
                        ev["snippet"] = text[:max_chars]
                        ev["source"] = "direct_fetch"
                except Exception:
                    pass

        return evidence

    # ----------------------------------------------------------------
    # Diagnostics
    # ----------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "attempts": self._search_attempts,
            "successes": self._search_successes,
            "success_rate": (self._search_successes / max(1, self._search_attempts)),
            "last_error": self._last_error,
        }

    def test_connectivity(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        try:
            d = self.lookup_word("hello")
            results["dictionary_api"] = "OK" if d["success"] else f"FAIL: {d.get('error', 'no data')}"
        except Exception as e:
            results["dictionary_api"] = f"FAIL: {e}"

        try:
            c = self.concept_search("artificial intelligence")
            results["duckduckgo_api"] = "OK" if c["success"] else f"FAIL: {c.get('error', 'no data')}"
        except Exception as e:
            results["duckduckgo_api"] = f"FAIL: {e}"

        try:
            w = self.wikipedia_summary("consciousness")
            results["wikipedia_api"] = "OK" if w["success"] else f"FAIL: {w.get('error', 'no data')}"
        except Exception as e:
            results["wikipedia_api"] = f"FAIL: {e}"

        results["all_ok"] = all(v == "OK" for k, v in results.items() if k != "all_ok")
        return results



# ============================================================================
#

# ============================================================================
# OETS RESEARCH CALLBACK  -- Connects Aurora's Study Mode to the Internet  -- Connects Aurora's Study Mode to the Internet
# ============================================================================

def _build_research_callback(search_adapter: SearchAdapter):
    """
    Build a callback function that the OETS ResearchStudyMode uses
    to look up word definitions, examples, and relations via the internet.

    This is what powers Aurora's autonomous learning during downtime.
    She identifies knowledge gaps, then this callback fetches real
    definitions and usage from the web.

    Uses structured API data (Dictionary API + DuckDuckGo + Wikipedia)
    instead of parsing raw search HTML.

    Authors: Sunni (Sir) Morningstar and Cael Devo
    """

    def _fetch_definition(word: str):
        """
        Research a word via structured APIs. Returns a ResearchResult.
        Strategy:
          1. Free Dictionary API  -- definitions, synonyms, antonyms, examples (structured JSON)
          2. DuckDuckGo Instant Answer  -- broader concept context
          3. Wikipedia  -- deeper context for complex/abstract concepts
        """
        
        result = ResearchResult(word=word, source="internet")

        # --- Pass 1: Dictionary API (structured data  -- the gold standard) ---
        try:
            lookup = search_adapter.lookup_word(word)
            if lookup["success"]:
                for defn in lookup["definitions"]:
                    result.definitions_found.append({
                        "text": defn["text"],
                        "source": f"dictionaryapi.dev ({defn.get('part_of_speech', 'unknown')})"
                    })

                for ex in lookup["examples"]:
                    result.examples_found.append(ex)

                for syn in lookup["synonyms"]:
                    if syn not in result.synonyms:
                        result.synonyms.append(syn)

                for ant in lookup["antonyms"]:
                    if ant not in result.antonyms:
                        result.antonyms.append(ant)
            elif lookup.get("error"):
                # Log but don't abort  -- try other sources
                pass

        except Exception as e:
            pass  # Continue to fallback sources

        # --- Pass 2: DuckDuckGo concept lookup (broader context) ---
        try:
            concept = search_adapter.concept_search(f"{word} meaning definition")
            if concept["success"]:
                abstract = concept.get("abstract", "")
                if abstract and len(result.definitions_found) < 3:
                    # Use abstract as an additional definition source
                    result.definitions_found.append({
                        "text": abstract[:300],
                        "source": concept.get("abstract_source", "duckduckgo")
                    })

                # Extract related concepts from related topics
                for topic in concept.get("related_topics", [])[:8]:
                    topic_text = topic.get("text", "").lower()
                    # Extract the first significant word from related topic
                    topic_words = re.findall(r'[a-z]{4,}', topic_text)
                    for tw in topic_words[:2]:
                        if (tw != word.lower() and
                            tw not in result.synonyms and
                            tw not in result.antonyms and
                            len(tw) > 3):
                            result.related_words.append({
                                "word": tw,
                                "relation": "contextual",
                                "confidence": 0.4
                            })

        except Exception:
            pass

        # --- Pass 3: Wikipedia (deeper context for complex concepts) ---
        if len(result.definitions_found) < 2:
            try:
                wiki = search_adapter.wikipedia_summary(word, max_chars=1500)
                if wiki["success"]:
                    summary = wiki["summary"]
                    # Add as definition if we're thin on definitions
                    result.definitions_found.append({
                        "text": summary[:300],
                        "source": f"wikipedia ({wiki.get('title', word)})"
                    })

                    # Extract hypernyms from Wikipedia's first sentence
                    # Pattern: "X is a/an [hypernym]" or "X is a type of [hypernym]"
                    first_sent = summary.split(".")[0] if summary else ""
                    hyp_match = re.search(
                        r'\b(?:is|are)\s+(?:a|an|the)\s+(?:type\s+of\s+)?(\w+)',
                        first_sent, re.IGNORECASE
                    )
                    if hyp_match:
                        hypernym = hyp_match.group(1).lower()
                        if hypernym not in ("the", "a", "an", "very", "also"):
                            result.hypernyms.append(hypernym)

            except Exception:
                pass

        # Mark success if we found at least one definition or relation
        result.success = (
            len(result.definitions_found) > 0 or
            len(result.synonyms) > 0 or
            len(result.related_words) > 0
        )

        return result

    return _fetch_definition

def study(systems: Dict[str, Any], cycles: int = 3, verbose: bool = True):
    """
    Run Aurora's autonomous study mode.
    She identifies knowledge gaps, looks up definitions and relations
    via the internet, and deepens her ontological web.

    This is her downtime learning  she studies when you're not talking to her.
    """
    perception = systems['perception']

    if not perception.oets:
        if verbose:
            print("  [STUDY] OETS not available  cannot run study mode.")
        return

    oets = perception.oets

    if verbose:
        pre_stats = oets.get_stats()
        print(f"  [STUDY] Starting autonomous study ({cycles} cycles)")
        print(f"  [STUDY] Pre-study web: {pre_stats['web']['total_nodes']} concepts, "
              f"{pre_stats['web']['total_relations']} relations")
        targets = oets.get_research_targets(5)
        if targets:
            print(f"  [STUDY] Top research priorities:")
            for t in targets:
                print(f"          {t['word']:20s} priority={t['priority']:.3f}  ({t['reason']})")
        print()

    total_studied = 0
    total_defs = 0
    total_rels = 0

    for cycle in range(cycles):
        result = oets.run_study_cycle()
        researched = result.get("researched", 0)
        total_studied += researched
        cycle_results = result.get("results", [])

        for r in cycle_results:
            total_defs += r.get("definitions", 0)
            total_rels += r.get("relations_added", 0)

        if verbose:
            for r in cycle_results:
                defs = r.get("definitions", 0)
                rels = r.get("relations_added", 0)
                print(f"  Cycle {cycle+1:2d}/{cycles}  "
                      f"studied: {r['word']:20s}  "
                      f"defs={defs}  rels={rels}  "
                      f"reason={r.get('reason', '?')}")
            if not cycle_results:
                print(f"  Cycle {cycle+1:2d}/{cycles}  (nothing to study)")

    if verbose:
        post_stats = oets.get_stats()
        print()
        print(f"  [STUDY] Study complete.")
        print(f"  [STUDY] Words studied: {total_studied}")
        print(f"  [STUDY] Definitions learned: {total_defs}")
        print(f"  [STUDY] Relations discovered: {total_rels}")
        print(f"  [STUDY] Post-study web: {post_stats['web']['total_nodes']} concepts, "
              f"{post_stats['web']['total_relations']} relations")
        print(f"  [STUDY] Understanding index: "
              f"{post_stats['understanding']['understanding_index']:.4f}")
        print()

    # Save state after study
    if systems.get('aurora'):
        _full_save(systems, verbose=verbose)


def show_understanding(systems: Dict[str, Any]):
    """Display Aurora's OETS understanding report."""
    perception = systems['perception']
    if not perception.oets:
        print("  [OETS] Not available.")
        return

    report = perception.oets.get_understanding_report()
    print()
    print(report)
    print()


def _looks_like_question(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False

    # direct punctuation heuristic
    if t.endswith("?"):
        return True

    # interrogative prefixes
    prefixes = (
        "what", "what's", "whats", "wats", "why", "how", "when", "where", "who", "which",
        "can", "could", "should", "would", "is", "are", "do", "does",
        "did", "will", "may", "tell me", "explain", "define", "look up",
        "search", "find"
    )
    t_low = t.lower()
    return any(t_low.startswith(p + " ") or t_low == p for p in prefixes)


def _try_direct_arithmetic(text: str) -> str:
    """
    Answer simple arithmetic deterministically before the generative pipeline.
    This intentionally accepts only numbers, operators, and parentheses.
    """
    import ast
    import operator
    import re

    t = (text or "").strip()
    if not t:
        return ""

    expressions = re.findall(r'[-+]?\d+(?:\.\d+)?(?:\s*[\+\-\*/xX]\s*[-+]?\d+(?:\.\d+)?)+', t)
    if not expressions:
        return ""

    expr = expressions[-1].replace("x", "*").replace("X", "*")
    if not re.fullmatch(r'[\d\s\.\+\-\*/\(\)]+', expr):
        return ""

    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return ops[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
            return ops[type(node.op)](eval_node(node.operand))
        raise ValueError("unsupported arithmetic")

    try:
        result = eval_node(ast.parse(expr, mode="eval"))
    except Exception:
        return ""

    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{expr.strip()} = {result}."


def _is_aurora_self_question(text: str) -> bool:
    """
    If the question is about Aurora's internal architecture/state/identity,
    or a personal wellbeing question directed at Aurora,
    do NOT trigger external search.
    """
    t = (text or "").lower()
    if _is_second_person_self_question(t):
        return True
    aurora_markers = (
        "aurora", "your system", "your code", "your layers", "your memory",
        "your dna", "your lattice", "your i-state", "your beings", "your contract",
        "your simulation", "your governance", "your gateway", "your consciousness",
        "your architecture", "what do you remember", "how do you work", "how are you built",
        # Identity & relational markers
        "who are you", "who made you", "who created you", "who built you",
        "who you are", "tell me who you are",
        "who is sunni", "who is cael", "sir morningstar",
        "your creator", "your author", "your name", "what are you",
        "who do you belong to", "tell me about yourself", "describe yourself",
        "explain yourself",
        "what do you know about yourself", "your identity",
        "your father", "your dad", "your partner",
        # Personal wellbeing  -- directed at Aurora, not external queries
        "how are you", "how do you feel", "how are you doing", "how are you feeling",
        "are you okay", "are you well", "are you alright", "are you good",
        "are you functioning", "are you working", "how is your",
        "how are your systems", "are you understanding",
        "do you have any questions",
        # What Aurora is currently thinking/processing
        "what are you thinking", "what's on your mind", "what is on your mind",
        "what are you feeling", "what are you processing", "what are you sensing",
        "what are you noticing", "what's going through your", "are you thinking",
        "what do you think about right now", "what do you think about currently",
        # Aurora's inner experience / uncertainty / what she's working through
        "do you ever feel", "do you ever experience", "do you ever wonder",
        "do you sometimes feel", "do you sometimes wonder",
        "tell me something you", "tell me something about yourself",
        "tell me more about yourself", "what have you been working through",
        "what are you working through", "what have you been thinking about",
        "what have you been learning", "what have you learned lately",
        "share something about yourself",
        # Relational / experiential questions directed at Aurora
        # "your relationship to/with", "how do you experience X",
        # "your sense of", "your experience of", "how does X feel to you"
        "your relationship", "your connection to", "your connection with",
        "your experience of", "your experience with",
        "how do you experience", "how do you relate",
        "how does it feel", "how does that feel",
        "what does that mean to you", "what does this mean to you",
        "mean to you",          # catches "what does silence/X/anything mean to you"
        "your sense of", "your understanding of", "your perspective on",
        "what is your relationship", "what is it like for you",
        "what does it feel like", "how do you feel about",
        "what is your experience", "what do you make of",
        "for you personally", "to you personally",
    )
    return any(m in t for m in aurora_markers)


def _is_second_person_self_question(text: str) -> bool:
    """
    Functional self-question detector: questions addressed to Aurora as "you"
    that ask about what she is, how she works, what makes her so, or how she
    describes/understands herself. This prevents open-ended self questions from
    falling into dictionary/OETS lookup.
    """
    t = " ".join((text or "").lower().split())
    if not re.search(r"\b(you|your|yourself)\b", t):
        return False
    if any(marker in t for marker in (
        "who you are", "who are you", "what are you", "describe yourself",
        "tell me about yourself", "explain yourself", "your identity",
        "your architecture", "your system", "your consciousness",
        "how do you work", "how are you built", "what makes you",
        "what do you understand about", "what do you mean by",
        "what does that mean to you", "mean to you",
    )):
        return True
    return bool(
        re.search(r"\b(what|why|how)\b.{0,40}\b(makes|made|mean|means|work|built|describe|understand|experience|feel)\b.{0,40}\byou\b", t)
        or re.search(r"\byou\b.{0,40}\b(mean|means|are|work|understand|experience|feel|describe)\b", t)
    )


def _is_identity_question(text: str) -> bool:
    """Detect questions specifically about Aurora's identity or relationships."""
    t = (text or "").lower()
    if _is_second_person_self_question(t):
        return True
    identity_markers = (
        "who are you", "who made you", "who created you", "who built you",
        "who you are", "tell me who you are",
        "who is sunni", "who is cael", "what is your name", "what are you",
        "tell me about yourself", "describe yourself", "your identity", "your creator",
        "your author", "who do you belong to", "who is your",
        "do you know who", "what do you know about yourself",
        "who is sir", "sir morningstar",
    )
    return any(m in t for m in identity_markers)


_SELF_REF_STOPWORDS = {
    "about", "after", "again", "also", "because", "could", "does",
    "from", "have", "into", "just", "like", "more", "much", "said", "same",
    "should", "that", "their", "there", "these", "thing", "this", "through",
    "what", "when", "where", "which", "while", "with", "would", "your",
}


def _content_words(text: str) -> List[str]:
    words = re.findall(r"[a-z][a-z'-]{2,}", (text or "").lower())
    return [w.strip("'") for w in words if w.strip("'") not in _SELF_REF_STOPWORDS]


def _extract_self_reference_terms(text: str) -> List[Dict[str, str]]:
    """
    Extract reusable phrases from Aurora's own output so the next turn can
    bind follow-up language to what Aurora just expressed.
    """
    terms: List[Dict[str, str]] = []
    seen = set()
    for sentence in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        words = _content_words(sentence)
        for size in (4, 3, 2):
            for i in range(0, max(0, len(words) - size + 1)):
                phrase = " ".join(words[i:i + size])
                if phrase in seen:
                    continue
                seen.add(phrase)
                terms.append({"phrase": phrase, "sentence": sentence.strip()[:400]})
    return terms[:40]


def _remember_self_expression(response_text: str, systems: Dict[str, Any], axes: Dict[str, float], tick: int) -> None:
    terms = _extract_self_reference_terms(response_text)
    if not terms:
        return
    systems["_last_self_expression"] = {
        "text": response_text[:1200],
        "terms": terms,
        "axes": dict(axes),
        "tick": tick,
    }


def _match_self_reference(text: str, systems: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Detect when the user is asking about Aurora's own previous wording.
    This is functional, not phrase-specific: any salient phrase Aurora just
    expressed can become the referent for a follow-up.
    """
    if not isinstance(systems, dict):
        return None
    last = systems.get("_last_self_expression") or {}
    terms = last.get("terms") or []
    if not terms:
        return None
    low = " ".join((text or "").lower().split())
    user_words = set(_content_words(low))
    explicit_followup = any(re.search(pattern, low) for pattern in (
        r"\byou\s+(?:said|asked|called|meant|were\s+saying)\b",
        r"\bwhat\s+(?:do|did)\s+you\s+mean\b",
        r"\bwhat\s+does\s+(?:that|this|it)\s+mean\b",
        r"\bwhy\s+did\s+you\s+(?:say|ask|call)\b",
        r"\bhow\s+did\s+you\s+(?:mean|decide|know)\b",
        r"\bexplain\s+(?:that|this|it|what\s+you\s+meant)\b",
        r"\b(?:that|this|it)\s+(?:part|phrase|word|sentence|answer|response)\b",
        r"\b(?:by|about)\s+(?:that|this|it)\b",
    ))
    best: Optional[Dict[str, str]] = None
    best_score = 0
    exact_phrase_hit = False
    for term in terms:
        phrase = str(term.get("phrase") or "")
        phrase_words = set(phrase.split())
        if not phrase_words:
            continue
        score = len(user_words.intersection(phrase_words))
        if phrase and phrase in low:
            score += len(phrase_words) + 2
            exact_phrase_hit = True
        if score > best_score:
            best = term
            best_score = score
    if not explicit_followup and not exact_phrase_hit:
        return None
    required_score = 2 if exact_phrase_hit else 3
    if not best or best_score < required_score:
        return None
    return {
        "phrase": best.get("phrase", ""),
        "sentence": best.get("sentence", ""),
        "source_text": last.get("text", ""),
        "axes": last.get("axes", {}),
        "tick": last.get("tick"),
    }


def _is_understanding_query(text: str) -> bool:
    t = " ".join((text or "").lower().split())
    if not _is_second_person_self_question(t):
        return False
    return any(marker in t for marker in (
        "what makes", "how", "why", "explain", "describe yourself",
        "what do you understand", "what do you mean", "what does that mean",
        "prove", "show me",
    ))


def _field_map_status_for_packet(systems: Dict[str, Any]) -> Dict[str, Any]:
    try:
        field_map = systems.get("field_map")
        if field_map is None:
            aurora = systems.get("aurora")
            _dim = getattr(getattr(aurora, "gateway", None), "dimensional", None) if aurora is not None else None
            field_map = getattr(_dim, "field_map", None) if _dim is not None else None
        if field_map is not None and hasattr(field_map, "get_state"):
            state = field_map.get_state()
            dominant = getattr(state, "dominant_field", None)
            return {
                "dominant_field": str(getattr(dominant, "name", "") or getattr(dominant, "field_id", "") or ""),
                "active_fields": [
                    str(getattr(f, "name", "") or getattr(f, "field_id", "") or "")
                    for f in list(getattr(state, "active_fields", []) or [])[:5]
                ],
            }
    except Exception:
        pass
    return {"dominant_field": "", "active_fields": []}


def _safe_status(obj: Any, method_names: Tuple[str, ...] = ("status", "get_state", "summary")) -> Dict[str, Any]:
    if obj is None:
        return {}
    for name in method_names:
        fn = getattr(obj, name, None)
        if callable(fn):
            try:
                value = fn()
                if isinstance(value, dict):
                    return value
                return {"value": str(value)[:300]}
            except Exception:
                continue
    return {}


def _normalize_axis_weights(weights: Dict[str, float]) -> Dict[str, float]:
    clean = {ax: max(0.0, float(weights.get(ax, 0.0) or 0.0)) for ax in ("X", "T", "N", "B", "A")}
    total = sum(clean.values())
    if total <= 0:
        return {ax: 0.2 for ax in ("X", "T", "N", "B", "A")}
    return {ax: round(clean[ax] / total, 4) for ax in ("X", "T", "N", "B", "A")}


def _identity_return_weight(layer_axes: Tuple[str, ...], pressure_axes: Dict[str, float]) -> float:
    axis_weights = _normalize_axis_weights(pressure_axes)
    if not layer_axes:
        return 0.0
    weight = sum(axis_weights.get(ax, 0.0) for ax in layer_axes) / len(layer_axes)
    return round(max(0.0, min(1.0, weight)), 4)


def _build_self_model_snapshot(
    systems: Dict[str, Any],
    user_text: str,
    pipeline_state: Dict[str, Any],
    self_reference: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Recursive self-model snapshot following Aurora's crystal stack:
    identity base -> memory/sensory/semantic crystals -> composite sensory ->
    reasoning/emotion higher-order crystals -> predictive frame -> constraints.
    """
    core_identity = systems.get("core_identity")
    perception = systems.get("perception")
    dimensional = systems.get("dimensional")
    lattice = systems.get("lattice")
    genealogy = systems.get("genealogy")
    working_memory = systems.get("working_memory")
    conversation_memory = systems.get("conversation_memory")
    sensory = systems.get("sensory_integration")
    pressure_axes = _normalize_axis_weights(
        pipeline_state.get("axis_activation")
        or (self_reference or {}).get("axes")
        or systems.get("_last_self_expression", {}).get("axes", {})
    )

    identity = {
        "layer": 1,
        "role": "identity_base",
        "mode": "XUSI_recursive",
        "self_name": getattr(core_identity, "self_name", "Aurora") if core_identity is not None else "Aurora",
        "description_available": bool(getattr(core_identity, "self_description", "")) if core_identity is not None else False,
    }

    memory = {
        "layer": 1,
        "role": "memory_crystal_base",
        "current_topic": str(getattr(working_memory, "current_topic", "") or ""),
        "recent_self_expression": systems.get("_last_self_expression", {}),
        "known_user": _get_stored_user_name(conversation_memory),
    }

    sensory_base = {
        "layer": 1,
        "role": "sensory_base_crystal",
        "status": _safe_status(sensory, ("status", "get_status", "summary")),
    }

    vision_base = {
        "layer": 1,
        "role": "vision_base_crystal",
        "status": _safe_status(systems.get("vision") or systems.get("live_vision"), ("status", "get_status", "summary")),
    }

    sound_base = {
        "layer": 1,
        "role": "sound_base_crystal",
        "status": _safe_status(systems.get("audio") or systems.get("voice"), ("status", "get_status", "summary")),
    }

    semantic_core = {
        "layer": 1,
        "role": "semantic_core_concept",
        "oets_available": bool(getattr(perception, "oets", None)) if perception is not None else False,
    }

    sensory_composite = {
        "layer": 2,
        "role": "sensory_composite_crystal",
        "inputs": ["sensory_base_crystal", "semantic_core_concept"],
        "status": _safe_status(getattr(perception, "sensory_composite", None), ("status", "get_state", "summary")),
    }

    reasoning = {
        "layer": 3,
        "role": "reasoning_higher_order_crystal",
        "input_prompt": user_text,
        "axis_activation": pipeline_state.get("axis_activation", {}),
        "dominant_axis": pipeline_state.get("dominant_axis", ""),
        "assembly_quality": pipeline_state.get("assembly_quality", None),
    }

    emotion = {
        "layer": 3,
        "role": "emotion_higher_order_crystal",
        "dominant_emotion": pipeline_state.get("dominant_emotion", ""),
        "emotional_coherence": pipeline_state.get("emotional_coherence", None),
        "emotional_energy": pipeline_state.get("emotional_energy", None),
    }

    predictive_frame = {
        "layer": 4,
        "role": "predictive_frame_quasi_crystal",
        "tick": int(getattr(genealogy, "tick_count", 0)) if genealogy is not None else 0,
        "field_map": _field_map_status_for_packet(systems),
        "lattice": _safe_status(lattice, ("heat_status", "status", "get_system_state")),
    }

    constraints = {
        "layer": 5,
        "role": "constraint_shell",
        "axes": {"X": "existence/admission", "T": "time/temporal", "N": "cost/energy", "B": "boundary", "A": "agency"},
        "retrieval_policy": "blocked_for_self_understanding_query",
    }
    nodes = [
        identity, memory, vision_base, sound_base, sensory_base, semantic_core,
        sensory_composite, reasoning, emotion, predictive_frame, constraints
    ]
    layer_axis_map = {
        "memory_crystal_base": ("T", "B"),
        "vision_base_crystal": ("X", "B"),
        "sound_base_crystal": ("X", "T"),
        "sensory_base_crystal": ("X", "B"),
        "semantic_core_concept": ("X", "N"),
        "sensory_composite_crystal": ("X", "B", "N"),
        "reasoning_higher_order_crystal": ("N", "B"),
        "emotion_higher_order_crystal": ("A", "N"),
        "predictive_frame_quasi_crystal": ("T", "A", "B"),
        "constraint_shell": ("X", "T", "N", "B", "A"),
    }
    identity_edges = []
    for role, axes_for_role in layer_axis_map.items():
        identity_edges.append({
            "from": "identity_base",
            "to": role,
            "direction": "one_way",
            "feed": "identity_to_layer",
            "weight": 1.0,
            "reason": "identity broadcasts baseline self-continuity into this layer",
        })
        identity_edges.append({
            "from": role,
            "to": "identity_base",
            "direction": "one_way",
            "feed": "layer_to_identity",
            "pressure_axes": list(axes_for_role),
            "weight": _identity_return_weight(axes_for_role, pressure_axes),
            "reason": "return into identity is weighted by the current pressure output on this layer's axes",
        })

    return {
        "model": "recursive_crystal_self_model",
        "pressure_output": pressure_axes,
        "identity_return_policy": {
            "identity_feeds": "all_layers",
            "identity_receives": "all_layers",
            "return_weight_rule": "each non-identity crystal returns into identity with weight derived from current pressure_output over that crystal's axes",
        },
        "layers": nodes,
        "edge_legend": {
            "one_way": "source lifts pressure/evidence into target",
            "two_way": "recursive feedback; target also updates/source-calibrates origin",
            "identity_to_layer": "identity feeds every layer at baseline continuity weight",
            "layer_to_identity": "layer returns into identity with weight determined by current pressure output",
        },
        "identity_feed_edges": identity_edges,
        "crystal_edges": [
            {"from": "vision_base_crystal", "to": "semantic_core_concept", "direction": "one_way", "reason": "vision feeds semantics; it does not directly feed higher crystals"},
            {"from": "sound_base_crystal", "to": "semantic_core_concept", "direction": "one_way", "reason": "sound feeds semantics; it does not directly feed higher crystals"},
            {"from": "semantic_core_concept", "to": "sensory_base_crystal", "direction": "one_way", "reason": "semantic meaning is an allowed input into sensory"},
            {"from": "vision_base_crystal", "to": "sensory_base_crystal", "direction": "one_way", "reason": "vision is an allowed base input into sensory"},
            {"from": "sound_base_crystal", "to": "sensory_base_crystal", "direction": "one_way", "reason": "sound is an allowed base input into sensory"},
            {"from": "memory_crystal_base", "to": "sensory_base_crystal", "direction": "one_way", "reason": "memory primes what sensory features matter"},
            {"from": "sensory_base_crystal", "to": "memory_crystal_base", "direction": "one_way", "reason": "sensory state records back into memory"},
            {"from": "sensory_base_crystal", "to": "sensory_composite_crystal", "direction": "one_way", "reason": "base sensory crystal composes upward"},
            {"from": "semantic_core_concept", "to": "sensory_composite_crystal", "direction": "one_way", "reason": "semantic core is an allowed input into composite sensory"},
            {"from": "sensory_composite_crystal", "to": "reasoning_higher_order_crystal", "direction": "one_way", "reason": "sensory feeds reasoning"},
            {"from": "sensory_composite_crystal", "to": "emotion_higher_order_crystal", "direction": "one_way", "reason": "senses feed emotion"},
            {"from": "sensory_composite_crystal", "to": "predictive_frame_quasi_crystal", "direction": "one_way", "reason": "sensory feeds prediction"},
            {"from": "emotion_higher_order_crystal", "to": "reasoning_higher_order_crystal", "direction": "one_way", "reason": "emotion can feed reason"},
            {"from": "reasoning_higher_order_crystal", "to": "memory_crystal_base", "direction": "one_way", "reason": "reason only feeds memory and prediction"},
            {"from": "reasoning_higher_order_crystal", "to": "predictive_frame_quasi_crystal", "direction": "one_way", "reason": "reason only feeds memory and prediction"},
            {"from": "constraint_shell", "to": "all_layers", "direction": "two_way", "reason": "X/T/N/B/A constrain every layer and every layer returns pressure into the shell"},
        ],
    }


def _build_understanding_query_packet(
    user_text: str,
    systems: Dict[str, Any],
    pipeline_state: Dict[str, Any],
    self_reference: Optional[Dict[str, Any]],
    retrieval_blocked: bool,
    selected_candidate_source: str = "",
) -> Dict[str, Any]:
    last_expr = systems.get("_last_self_expression") or {}
    axes = (
        (self_reference or {}).get("axes") or
        pipeline_state.get("axis_activation") or
        last_expr.get("axes") or
        _project_utterance_axes(user_text, systems)
    )
    axes = {ax: float(axes.get(ax, 0.0)) for ax in ("X", "T", "N", "B", "A")}
    return {
        "event_type": "UNDERSTANDING_QUERY",
        "user_prompt": user_text,
        "matched_referent": self_reference or {},
        "last_self_expression": {
            "text": str(last_expr.get("text", ""))[:900],
            "tick": last_expr.get("tick"),
        },
        "response_axes": axes,
        "dominant_axis": max(axes, key=axes.get) if axes else pipeline_state.get("dominant_axis", ""),
        "field_map": _field_map_status_for_packet(systems),
        "self_model": _build_self_model_snapshot(systems, user_text, pipeline_state, self_reference),
        "tick": int(time.time()),
        "retrieval_blocked": bool(retrieval_blocked),
        "selected_candidate_source": selected_candidate_source,
        "contract": (
            "Realize an answer from this packet's live evidence. Use the current prompt, "
            "matched referent or last self-expression, response axes, field map, and retrieval state. "
            "Do not answer from dictionary lookup or a prewritten identity slogan."
        ),
    }


def _generate_identity_response(text: str, core_identity: CoreRelationalIdentity,
                                  memory: ConversationMemory) -> Optional[str]:
    """
    Generate a response from Aurora's identity knowledge.
    Returns None if the question isn't identity-related.
    """
    t = (text or "").lower()

    # "Who are you?" / "What are you?"
    if any(m in t for m in ("who are you", "who you are", "tell me who you are",
                             "what are you", "tell me about yourself",
                             "describe yourself", "explain yourself",
                             "your name", "what is your name")):
        # REMOVED HARDCODED FALLBACK
        return None

    if _is_second_person_self_question(t):
        # REMOVED HARDCODED FALLBACK
        return None

    # "Who made you?" / "Who created you?"
    if any(m in t for m in ("who made you", "who created you", "who built you",
                             "your creator", "your author")):
        return core_identity.who_made_me()

    # "Who is Sunni?"
    if "sunni" in t or "sir morningstar" in t or ("sir" in t and "who" in t):
        entity = core_identity.get_entity("sunni")
        if entity:
            return f"{entity.name}: {entity.description} {entity.relationship_to_aurora}"

    # "Who is Cael?"
    if "cael" in t:
        entity = core_identity.get_entity("cael")
        if entity:
            return f"{entity.name}: {entity.description} {entity.relationship_to_aurora}"

    return None


def _extract_location(text: str) -> str:
    """Pull a location string from a query. Returns '' if nothing found."""
    t = text.strip()
    # "in Piqua Ohio", "for Piqua Ohio", "at Piqua Ohio", "near Piqua Ohio"
    m = re.search(r'\b(?:in|for|at|near|around)\s+([A-Z][A-Za-z\s]{2,}?)(?:\s+(?:today|tomorrow|now|weather|temperature|forecast|right|this)|\?|$)', t)
    if m:
        return m.group(1).strip()
    # Just a run of capitalised words (e.g. "Piqua Ohio")
    m = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b', t)
    if m:
        candidate = m.group(1).strip()
        # Filter out sentence-starters that aren't real place names
        non_places = {"What", "Is", "Are", "The", "How", "Can", "Do", "Does", "Tell", "Look"}
        if candidate.split()[0] not in non_places:
            return candidate
    return ""


def _extract_math_expr(text: str) -> str:
    """Extract a calculable expression from a query."""
    t = (text or "").lower()
    # Word-operator normalisation
    t = re.sub(r'\bplus\b', '+', t)
    t = re.sub(r'\bminus\b', '-', t)
    t = re.sub(r'\btimes\b|\bmultiplied by\b', '*', t)
    t = re.sub(r'\bdivided by\b', '/', t)
    t = re.sub(r'\bsquared\b', '**2', t)
    t = re.sub(r'\bcubed\b', '**3', t)
    # Find something that looks like an expression
    m = re.search(r'[\d(][0-9+\-*/^().% \t]+[\d)]', t)
    if m:
        return m.group(0).strip()
    return ""


def _select_tool(
    user_text: str,
    intent: str,
    is_self_question: bool,
    systems: Optional[Any] = None,
    pipeline_state: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], dict]:
    """
    Decide whether a tool should fire for this turn.

    Primary signal: Aurora's live cognitive geometry (dominant_axis,
    axis_activation, novelty, coherence) from pipeline_state.
    Secondary signal: vocabulary patterns in user_text.
    Both must align for non-trivial tool calls — neither alone is sufficient
    unless the signal is very strong.

    Returns (tool_name, kwargs) or (None, {}).
    """
    t = (user_text or "").lower()
    ps = dict(pipeline_state or {})

    # ── Quasi-recursive signal: micro_reasoning hint from previous turn ──────
    # When the last conscious frame emitted a tool_selection hypothesis,
    # that prediction is the primary signal — it IS Aurora's identity state
    # speaking forward into this turn.
    _hint_tags: List[str] = []
    if systems:
        try:
            _hint = dict(systems.get('_tool_selection_hint') or {})
            _hint_age = time.time() - float(_hint.get('ts', 0) or 0)
            if _hint_age < 90 and float(_hint.get('confidence', 0) or 0) >= 0.68:
                _hint_tags = list(_hint.get('tags', []) or [])
        except Exception:
            pass

    # Live cognitive geometry (current-turn IVM) ─────────────────────────────
    dominant_axis = str(ps.get("dominant_axis") or "").upper()
    axis_act: Dict[str, float] = dict(ps.get("axis_activation") or {})
    novelty    = float(ps.get("novelty", 0.5) or 0.5)
    coherence  = float(ps.get("coherence", 1.0) or 1.0)

    # Per-axis activation weights (default 0.0 if not populated yet)
    ax_T = float(axis_act.get("T", 0.0) or 0.0)
    ax_X = float(axis_act.get("X", 0.0) or 0.0)
    ax_N = float(axis_act.get("N", 0.0) or 0.0)
    ax_A = float(axis_act.get("A", 0.0) or 0.0)

    # Hint-driven early resolution: if the previous conscious frame predicted a
    # specific tool AND current text confirms the domain, trust the prediction.
    if _hint_tags:
        if "tool:time" in _hint_tags and any(w in t for w in ("time", "date", "day", "hour", "today", "now", "when", "clock")):
            return "time", {}
        if "tool:weather" in _hint_tags and any(w in t for w in ("weather", "temperature", "rain", "snow", "wind", "forecast", "hot", "cold", "warm", "humid")):
            location = _extract_location(user_text)
            if location:
                return "weather", {"location": location}
        if "tool:calculator" in _hint_tags and (re.search(r'\d', t) or any(w in t for w in ("calculate", "compute", "how much", "how many", "plus", "minus", "times", "divided"))):
            expr = _extract_math_expr(user_text)
            if expr:
                return "calculator", {"expression": expr}
        if "tool:self_state" in _hint_tags and is_self_question:
            return "self_state", {"systems": systems}
        if "tool:lookup" in _hint_tags:
            # Generic lookup hint — don't call a tool but let search run
            pass

    # ── Time ─────────────────────────────────────────────────────────────────
    time_text_markers = (
        "what time", "what day is", "what's the date", "what is the date",
        "current time", "current date", "today's date", "what year is it",
        "what month is", "what day of the week", "how late", "what hour",
    )
    time_text_hit = any(m in t for m in time_text_markers)
    time_axis_hit = dominant_axis == "T" or ax_T >= 0.30
    if time_text_hit or (time_axis_hit and any(w in t for w in ("time", "date", "day", "hour", "today", "schedule", "clock"))):
        return "time", {}

    # ── Weather / temperature ────────────────────────────────────────────────
    weather_words = {
        "temperature", "weather", "forecast", "raining", "snowing",
        "humid", "humidity", "wind", "cold outside", "hot outside",
        "warm outside", "climate right now", "degrees outside",
    }
    weather_text_hit = any(w in t for w in weather_words)
    weather_axis_hit = dominant_axis in ("T", "X") or ax_T >= 0.25 or ax_X >= 0.30
    if weather_text_hit and (weather_axis_hit or novelty >= 0.55):
        location = _extract_location(user_text)
        if location:
            return "weather", {"location": location}
    # Fallback: strong text signal even without axis confirmation
    if weather_text_hit:
        location = _extract_location(user_text)
        if location:
            return "weather", {"location": location}

    # ── Calculator ───────────────────────────────────────────────────────────
    calc_text_hit = bool(re.search(r'\d\s*[+\-*/]\s*\d|\bcalculate\b|\bwhat\s+is\s+\d', t))
    calc_axis_hit = dominant_axis == "N" or ax_N >= 0.30
    if calc_text_hit or (calc_axis_hit and any(w in t for w in ("calculate", "compute", "plus", "minus", "times", "divided", "percent", "how many", "how much"))):
        expr = _extract_math_expr(user_text)
        if expr:
            return "calculator", {"expression": expr}

    # ── Self-state ───────────────────────────────────────────────────────────
    self_state_text_markers = (
        "your camera", "is your camera", "camera working", "camera active",
        "your mic", "your microphone", "mic working",
        "are your systems", "your heat", "how hot are you",
        "your coherence", "your load", "your errors",
        "what's scheduled", "your schedule", "are you running",
        "your temperature", "your thermal", "your status",
        "how are your systems", "are you okay", "your sensors",
    )
    self_text_hit = any(m in t for m in self_state_text_markers)
    self_axis_hit = dominant_axis == "A" or ax_A >= 0.35
    if (is_self_question and self_text_hit) or (self_axis_hit and self_text_hit):
        return "self_state", {"systems": systems}

    # ── Schedule / daemon timing ─────────────────────────────────────────────
    schedule_markers = (
        "what are you doing", "what's next", "next task", "next cycle",
        "your uptime", "how long running", "daemon status",
    )
    if is_self_question and any(m in t for m in schedule_markers):
        return "schedule_read", {}

    # ── Memory recall ────────────────────────────────────────────────────────
    memory_markers = (
        "what do you remember", "do you recall", "what have you learned",
        "your memories", "what did you learn", "what have you studied",
        "what's in your memory", "your oets",
    )
    if is_self_question and any(m in t for m in memory_markers):
        return "memory_read", {"systems": systems}

    # ── Visual analysis ──────────────────────────────────────────────────────
    visual_markers = (
        "what do you see", "what can you see", "what's in front of you",
        "look around", "describe what you see", "what do you observe",
        "what's on the screen", "what's on screen", "what's on your screen",
        "what's on the display", "look at the screen", "look at the display",
        "what does the screen show", "what does the page show",
        "what are you looking at", "describe the scene", "describe your surroundings",
        "can you see", "do you see anything", "what's around you",
        "take a look", "what's in the camera",
    )
    visual_hit = any(m in t for m in visual_markers)
    if not visual_hit:
        visual_hit = any(w in t for w in ("see", "look", "observe", "surroundings", "scene")) and (
            any(w in t for w in ("what", "describe", "camera", "screen", "display", "monitor", "around", "front"))
        )
    if visual_hit:
        _screen_kw = {"screen", "display", "monitor", "desktop", "browser", "window", "chrome", "page", "tab"}
        _prefer_screen = any(kw in t for kw in _screen_kw)
        return "visual_analysis", {
            "analysis_intent": user_text,
            "image_source": "screen" if _prefer_screen else "camera",
        }

    # ── Audio analysis ───────────────────────────────────────────────────────
    audio_markers = (
        "what do you hear", "what can you hear", "listen to this",
        "what's playing", "what's that sound", "what's that noise",
        "what music is playing", "what song is playing", "what's that song",
        "is there any sound", "do you hear anything", "what are you hearing",
        "what does this sound like", "describe the audio", "describe the sound",
        "what's the music", "is music playing", "what's coming from the speakers",
        "what's on the speakers", "hear anything",
    )
    audio_hit = any(m in t for m in audio_markers)
    if not audio_hit:
        audio_hit = any(w in t for w in ("hear", "sound", "music", "audio", "noise", "playing")) and (
            any(w in t for w in ("what", "describe", "listen", "tell me about", "is there"))
        )
    if audio_hit:
        return "audio_analysis", {"analysis_intent": user_text}

    # ── Desktop tools ────────────────────────────────────────────────────────
    # Shared lookup tables for website/app routing.
    _KNOWN_SITES: Dict[str, str] = {
        "youtube": "https://youtube.com",
        "yt": "https://youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "reddit": "https://reddit.com",
        "facebook": "https://facebook.com",
        "fb": "https://facebook.com",
        "twitter": "https://twitter.com",
        "x.com": "https://x.com",
        "instagram": "https://instagram.com",
        "insta": "https://instagram.com",
        "netflix": "https://netflix.com",
        "gmail": "https://mail.google.com",
        "discord": "https://discord.com",
        "spotify": "https://open.spotify.com",
        "twitch": "https://twitch.tv",
        "wikipedia": "https://wikipedia.org",
        "wiki": "https://wikipedia.org",
        "stackoverflow": "https://stackoverflow.com",
        "stack overflow": "https://stackoverflow.com",
        "amazon": "https://amazon.com",
        "linkedin": "https://linkedin.com",
        "tiktok": "https://tiktok.com",
        "pinterest": "https://pinterest.com",
        "tumblr": "https://tumblr.com",
        "hulu": "https://hulu.com",
        "disneyplus": "https://disneyplus.com",
        "disney plus": "https://disneyplus.com",
        "prime video": "https://primevideo.com",
        "primevideo": "https://primevideo.com",
        "chatgpt": "https://chat.openai.com",
        "openai": "https://openai.com",
        "claude": "https://claude.ai",
        "anthropic": "https://anthropic.com",
        "maps": "https://maps.google.com",
        "google maps": "https://maps.google.com",
        "news": "https://news.google.com",
        "google news": "https://news.google.com",
        "calendar": "https://calendar.google.com",
        "google calendar": "https://calendar.google.com",
        "drive": "https://drive.google.com",
        "google drive": "https://drive.google.com",
        "docs": "https://docs.google.com",
        "sheets": "https://sheets.google.com",
        "ebay": "https://ebay.com",
        "etsy": "https://etsy.com",
        "paypal": "https://paypal.com",
        "venmo": "https://venmo.com",
        "cashapp": "https://cash.app",
        "cash app": "https://cash.app",
    }
    _KNOWN_NATIVE_APPS: set = {
        "chrome", "chromium", "firefox", "terminal",
        "files", "file manager", "vscode", "code",
        "calculator", "vlc", "slack", "thunderbird",
        "gimp", "nautilus", "gedit", "kate", "steam",
        "obs", "zoom", "teams", "skype", "telegram",
        "signal", "whatsapp",
    }

    def _resolve_site_url(name: str) -> str:
        """Return a full URL for a site name or raw URL string, or '' if unresolvable."""
        n = name.strip().lower()
        if n in _KNOWN_SITES:
            return _KNOWN_SITES[n]
        if n.startswith("http://") or n.startswith("https://"):
            return name.strip()
        if "." in n and len(n) > 3:
            return "https://" + n.strip() if not n.startswith("http") else n.strip()
        return ""

    def _extract_search_engine(text_lower: str) -> str:
        if "youtube" in text_lower:  return "youtube"
        if "github" in text_lower:   return "github"
        if "reddit" in text_lower:   return "reddit"
        if "duckduckgo" in text_lower or "duck duck" in text_lower: return "duckduckgo"
        return "google"

    def _extract_search_query(text_lower: str, engine: str) -> str:
        """Strip verb + engine name and cleanup. Returns best query string."""
        q = text_lower
        # Remove leading verb phrases (with optional politeness prefix)
        q = re.sub(r'^(?:please\s+)?(?:can you\s+)?(?:could you\s+)?'
                   r'(?:search(?:\s+for)?|look\s+up|find|google)\s+', '', q)
        # Remove "the web for" / "the internet for" if it ends up at the start
        q = re.sub(r'^(?:the web|the internet|online)\s+(?:for\s+)?', '', q)
        # Remove engine references anywhere: "on youtube", "on google", "youtube for"
        q = re.sub(r'\b(?:on|via|using|in|with)\s+(?:youtube|google|github|reddit|duckduckgo|the web|the internet)\b', '', q)
        q = re.sub(r'\b(?:youtube|google|github|reddit|duckduckgo)\s+for\b', '', q)
        q = re.sub(r'\b(?:youtube|google|github|reddit|duckduckgo)\b', '', q)
        # Remove trailing filler
        q = re.sub(r'\b(?:for me|please|now|right now)\s*$', '', q)
        q = q.strip().strip("'\"").strip()
        return q if len(q) > 1 else text_lower

    # -- System actions (check FIRST — clear explicit phrases, no ambiguity) --
    _sys_action_map: Dict[str, str] = {
        "volume up": "volume_up",       "turn up the volume": "volume_up",
        "louder": "volume_up",          "increase volume": "volume_up",
        "volume down": "volume_down",   "turn down the volume": "volume_down",
        "quieter": "volume_down",       "decrease volume": "volume_down",
        "lower the volume": "volume_down",
        "mute": "volume_mute",          "unmute": "volume_mute",
        "toggle mute": "volume_mute",
        "brightness up": "brightness_up",   "brighter": "brightness_up",
        "increase brightness": "brightness_up",
        "brightness down": "brightness_down", "dimmer": "brightness_down",
        "lower brightness": "brightness_down", "dim the screen": "brightness_down",
        "lock screen": "lock_screen",   "lock the screen": "lock_screen",
        "lock the laptop": "lock_screen", "lock the computer": "lock_screen",
        "take a screenshot": "screenshot", "take screenshot": "screenshot",
        "capture the screen": "screenshot",
        "reboot": "reboot",             "restart the laptop": "reboot",
        "restart the computer": "reboot",
        "shut down": "shutdown",        "shutdown": "shutdown",
        "power off": "poweroff",        "turn off the laptop": "poweroff",
        "suspend": "suspend",           "sleep mode": "suspend",
        "put to sleep": "suspend",
    }
    for _phrase, _op in _sys_action_map.items():
        if _phrase in t:
            _is_destructive = _op in ("reboot", "shutdown", "poweroff", "suspend")
            return "desktop_system_action", {"op": _op, "confirm": not _is_destructive}

    # -- Browser search: "search youtube for X", "look up X on youtube", etc. -
    _browser_search_re = re.compile(
        r'\b(?:search(?:\s+for)?|look\s+up|find|google)\b', re.IGNORECASE
    )
    _is_browser_search = bool(_browser_search_re.search(t)) and (
        any(site in t for site in ("youtube", "google", "github", "reddit", "duckduckgo",
                                    "the web", "the internet", "online"))
        or "search for" in t or "look up" in t
    )
    if _is_browser_search:
        _s_engine = _extract_search_engine(t)
        _s_query = _extract_search_query(t, _s_engine)
        if _s_query:
            return "desktop_search", {"query": _s_query, "engine": _s_engine}

    # -- Open a URL or named website: "open youtube", "go to github", etc. ----
    _open_site_re = re.compile(
        r'\b(?:open|go\s+to|navigate\s+to|take\s+me\s+to|browse\s+to|pull\s+up|load)\s+'
        r'([\w\s\.\-]+?)(?:\s+(?:and|in|on|please|for me|right now)\b.*)?$',
        re.IGNORECASE
    )
    _site_match = _open_site_re.search(t)
    if _site_match:
        _target_raw = _site_match.group(1).strip().rstrip(".,;")
        # Resolve to URL (known site name or has a dot)
        _resolved_url = _resolve_site_url(_target_raw)
        if _resolved_url:
            return "desktop_open_url", {"url": _resolved_url}
        # If no URL found but target is a known native app — launch it
        if _target_raw.lower() in _KNOWN_NATIVE_APPS:
            return "desktop_launch_app", {"app_name": _target_raw}

    # -- Launch a native app: "open chrome", "launch terminal", etc. ----------
    _launch_re = re.compile(
        r'\b(?:open|launch|start)\s+(\w+(?:\s+\w+)?)',
        re.IGNORECASE
    )
    _launch_match = _launch_re.search(t)
    if _launch_match:
        _app_word = _launch_match.group(1).strip().lower()
        if _app_word in _KNOWN_NATIVE_APPS:
            return "desktop_launch_app", {"app_name": _app_word}

    # -- Browser page actions: click, type, press, read, screenshot -----------
    _browser_action_re = re.compile(
        r'\b(?:click\s+(?:on\s+)?|type\s+|press\s+|read\s+the\s+page|'
        r'screenshot\s+the\s+page|what.?s\s+the\s+(?:current\s+)?url|current\s+url)\b',
        re.IGNORECASE
    )
    if _browser_action_re.search(t):
        _b_action = "read"
        _b_target = ""
        _b_text = ""
        if "click" in t:
            _b_action = "click"
            _m = re.search(r'click\s+(?:on\s+)?(.+)', t)
            if _m: _b_target = _m.group(1).strip()
        elif re.search(r'\btype\b', t):
            _b_action = "type"
            _m = re.search(r'\btype\s+(.+)', t)
            if _m: _b_text = _m.group(1).strip()
        elif "press" in t:
            _b_action = "press"
            _m = re.search(r'\bpress\s+(.+)', t)
            if _m: _b_target = _m.group(1).strip()
        elif "screenshot" in t:
            _b_action = "screenshot"
        elif "url" in t:
            _b_action = "url"
        return "desktop_browser_action", {"action": _b_action, "target": _b_target, "text": _b_text}

    browser_search_hit = _is_browser_search  # referenced later by world_knowledge guard

    # ── Introspective — challenge conclusion ─────────────────────────────────
    challenge_markers = (
        "are you sure", "challenge that", "second guess yourself",
        "are you certain", "double check that", "verify that",
        "what if you're wrong", "could you be wrong", "reconsider",
        "think again", "check your reasoning", "challenge your answer",
    )
    if any(m in t for m in challenge_markers):
        return "challenge_my_conclusion", {"systems": systems}

    # ── Introspective — crystal / learning state ─────────────────────────────
    crystal_markers = (
        "your crystals", "your learning state", "crystal state", "your facets",
        "what are you learning", "behavioral crystals", "sensory crystals",
        "what patterns are you forming",
    )
    if is_self_question and any(m in t for m in crystal_markers):
        return "query_crystal_state", {"systems": systems}

    # ── Introspective — sedi-memory strata ───────────────────────────────────
    sedi_markers = (
        "your deepest memories", "sedimented memories", "sedimemory",
        "what's settled in you", "what's at your core",
        "your memory strata", "oldest memories",
    )
    if is_self_question and any(m in t for m in sedi_markers):
        return "query_sedimemory_strata", {"systems": systems}

    # ── Introspective — genealogy / evolution ────────────────────────────────
    genealogy_markers = (
        "recent evolution", "what evolved", "genetic changes",
        "your genealogy", "what has evolved in you", "recent gene",
        "what changed in your dna", "fitness score", "promoted links",
    )
    if is_self_question and any(m in t for m in genealogy_markers):
        return "query_genealogy_recent", {"systems": systems}

    # ── Introspective — unresolved tensions ──────────────────────────────────
    tension_markers = (
        "what's unresolved", "open loops", "unresolved tensions",
        "what's bothering you", "what are you stuck on",
        "what's still open", "pending tensions",
    )
    if is_self_question and any(m in t for m in tension_markers):
        return "query_unresolved_tensions", {"systems": systems}

    # ── Introspective — my interaction patterns ──────────────────────────────
    sunni_markers = (
        "my patterns", "how do i interact", "how am i engaging",
        "my behavior", "my interaction", "how do i usually talk to you",
        "what do i usually ask", "my cadence", "my tendencies",
    )
    if any(m in t for m in sunni_markers):
        return "query_sunni_pattern", {"systems": systems}

    # ── Introspective — pressure history ─────────────────────────────────────
    pressure_markers = (
        "your recent pressure", "cognitive load history", "pressure history",
        "your pressure over time", "your load history", "axis pressure",
    )
    if is_self_question and any(m in t for m in pressure_markers):
        return "query_pressure_history", {"systems": systems}

    # ── World knowledge (factual grounding for unknown concepts) ─────────────
    knowledge_markers = (
        "what is a ", "what is an ", "define ", "what does it mean",
        "explain what", "tell me about ", "what exactly is",
        "who is ", "who was ", "what was ", "what are ",
    )
    knowledge_hit = any(m in t for m in knowledge_markers)
    if knowledge_hit and not is_self_question and not browser_search_hit:
        return "world_knowledge_search", {"query": user_text, "systems": systems}

    return None, {}


def _looks_time_sensitive(text: str) -> bool:
    t = (text or "").lower()
    markers = (
        "today", "right now", "currently", "latest", "news", "this week",
        "president", "governor", "mayor", "senator", "congress",
        "this month", "this year", "recent", "as of", "update", "newest"
    )
    return any(m in t for m in markers)


def _has_proper_noun_hint(text: str) -> bool:
    """
    Heuristic: if the user mentions a proper noun/entity, it's more likely to need external lookup.
    We treat mid-sentence Capitalized tokens as entity hints (excluding first token).
    """
    t = (text or "").strip()
    if not t:
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]+", t)
    if len(tokens) <= 1:
        return False
    # ignore first token (often capitalized due to sentence start)
    for tok in tokens[1:]:
        if tok[:1].isupper():
            return True
    # also catch "of <word>" patterns
    if re.search(r"\bof\s+[A-Z][a-z]+", t):
        return True
    return False


# ============================================================================
# COMPREHENSION LAYER
# ============================================================================
# AXIS PROJECTOR
# Maps an utterance + live system state into a 5-vector activation across
# X/T/N/B/A, reading from multiple representational forms simultaneously:
#   - Utterance side:  PragmaticRole signals from UtteranceParser
#   - Phase side:      IVM toroidal axis polarity (near-zero = unsettled = active)
#   - Evolutionary:    Genealogy pressure_orientation (correction factors)
#   - Contextual:      DCE situational frame axis weights
#
# This replaces string-label intent classification with an axis-activation
# vector. The dominant axis drives the response path:
#   X-dominant → surface/local/search response
#   T-dominant → temporal chain / working memory
#   N-dominant → energy-optimized / concise
#   B-dominant → structured / grammar engine
#   A-dominant → whole-field / global alignment state
# ============================================================================

class AxisProjector:
    """
    Project an utterance into the 5-constraint axis space by reading from
    multiple representational forms of the constraint system simultaneously.

    The result is a normalized 5-vector {X, T, N, B, A} where each value
    represents how much that axis is activated by this utterance in the
    current system state.
    """

    # PragmaticRole string → per-axis contribution weights.
    # These are not arbitrary — each role IS a constraint operation:
    #   INQUIRY/ENTITY/HYPOTHESIS = X (existence: what is real/possible?)
    #   RECENCY/CALLBACK/CONSEQUENCE = T (temporal: what happened / what follows?)
    #   MINIMIZATION/OPPOSITION/EMPHASIS = N (energy: cost/resistance/force)
    #   CONTRAST/CONCESSION/CLARIFICATION = B (boundary: where does this end?)
    #   EXPERIENCE/OPINION/REQUEST/ACKNOWLEDGMENT = A (agency: inner state / relational)
    _ROLE_AXIS: Dict[str, Dict[str, float]] = {
        "inquiry":        {"X": 0.60, "T": 0.20, "N": 0.10, "B": 0.05, "A": 0.05},
        "entity":         {"X": 0.70, "T": 0.10, "N": 0.05, "B": 0.10, "A": 0.05},
        "topic_word":     {"X": 0.50, "T": 0.10, "N": 0.10, "B": 0.20, "A": 0.10},
        "certainty":      {"X": 0.50, "T": 0.05, "N": 0.20, "B": 0.20, "A": 0.05},
        "hypothesis":     {"X": 0.60, "T": 0.10, "N": 0.10, "B": 0.10, "A": 0.10},
        "uncertainty":    {"X": 0.30, "T": 0.10, "N": 0.20, "B": 0.20, "A": 0.20},
        "recency":        {"X": 0.10, "T": 0.70, "N": 0.10, "B": 0.05, "A": 0.05},
        "time_ref":       {"X": 0.10, "T": 0.80, "N": 0.05, "B": 0.05, "A": 0.00},
        "consequence":    {"X": 0.10, "T": 0.50, "N": 0.20, "B": 0.10, "A": 0.10},
        "callback":       {"X": 0.10, "T": 0.60, "N": 0.10, "B": 0.15, "A": 0.05},
        "minimization":   {"X": 0.05, "T": 0.10, "N": 0.70, "B": 0.10, "A": 0.05},
        "opposition":     {"X": 0.10, "T": 0.10, "N": 0.60, "B": 0.15, "A": 0.05},
        "addition":       {"X": 0.10, "T": 0.10, "N": 0.50, "B": 0.20, "A": 0.10},
        "emphasis":       {"X": 0.10, "T": 0.05, "N": 0.55, "B": 0.10, "A": 0.20},
        "contrast":       {"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.60, "A": 0.10},
        "concession":     {"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.60, "A": 0.10},
        "clarification":  {"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.60, "A": 0.10},
        "similarity":     {"X": 0.20, "T": 0.10, "N": 0.10, "B": 0.40, "A": 0.20},
        "acknowledgment": {"X": 0.05, "T": 0.10, "N": 0.10, "B": 0.10, "A": 0.65},
        "experience":     {"X": 0.05, "T": 0.05, "N": 0.10, "B": 0.10, "A": 0.70},
        "opinion":        {"X": 0.10, "T": 0.05, "N": 0.10, "B": 0.15, "A": 0.60},
        "request":        {"X": 0.10, "T": 0.05, "N": 0.10, "B": 0.10, "A": 0.65},
    }

    # DCE frame axis_weights use full names — bridge to letters here
    _AXIS_NAME_MAP = {
        "existence": "X", "temporal": "T", "energy": "N",
        "boundary": "B", "agency": "A",
    }

    def project(self, parsed: dict, systems: dict) -> Dict[str, float]:
        """
        Return {X, T, N, B, A} activation for this utterance in current system state.

        parsed  — output of UtteranceParser.parse()
        systems — live Aurora systems dict (lattice, genealogy, dimensional, perception)
        """
        ax: Dict[str, float] = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}

        # --- 1. Utterance signal (pragmatic roles → axis weights) ---------------
        signals = parsed.get("pragmatic_signals", [])   # list of (role_str, span) tuples
        sig_count = max(1, len(signals))
        for role_str, _span in signals:
            role_weights = self._ROLE_AXIS.get(role_str)
            if role_weights:
                for letter, w in role_weights.items():
                    ax[letter] += w / sig_count

        # Normalise utterance sub-vector
        _total = sum(ax.values()) or 1.0
        utt_vec = {k: v / _total for k, v in ax.items()}

        # --- 2. IVM phase signal (toroidal polarity → axis receptivity) ----------
        # A toroidal axis near polarity=0 (throat of the torus) is unsettled —
        # it is most receptive to new activation.  Near ±1 it is settled.
        ivm_vec: Dict[str, float] = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}
        lattice = systems.get("lattice")
        if lattice:
            try:
                ivm_axes = getattr(lattice, "axes", {}) or {}
                for aname, letter in self._AXIS_NAME_MAP.items():
                    ta = ivm_axes.get(aname)
                    if ta is not None:
                        polarity = float(getattr(ta, "polarity", 0.0))
                        # receptivity: high when polarity near 0 (transition)
                        ivm_vec[letter] = 1.0 - abs(polarity) * 0.5
            except Exception:
                pass

        # --- 3. Evolutionary signal (genealogy pressure_orientation) -------------
        gen_vec: Dict[str, float] = {"X": 1.0, "T": 1.0, "N": 1.0, "B": 1.0, "A": 1.0}
        genealogy = systems.get("genealogy")
        if genealogy:
            try:
                orient = genealogy.pressure_orientation() or {}
                for letter, corr in orient.items():
                    if letter in gen_vec:
                        gen_vec[letter] = float(corr)
            except Exception:
                pass

        # --- 4. Contextual signal (DCE situational frame axis weights) -----------
        dce_vec: Dict[str, float] = {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}
        try:
            dim = systems.get("dimensional")
            if dim:
                dce = getattr(dim, "dce", None)
                if dce:
                    frame = getattr(dce, "current_frame", None)
                    if frame:
                        fw = getattr(frame, "axis_weights", {}) or {}
                        for fname, w in fw.items():
                            letter = self._AXIS_NAME_MAP.get(fname, fname)
                            if letter in dce_vec:
                                dce_vec[letter] = float(w)
        except Exception:
            pass

        # --- 5. Blend: 55% utterance, 20% IVM phase, 15% evolutionary, 10% DCE --
        combined: Dict[str, float] = {}
        for letter in ("X", "T", "N", "B", "A"):
            combined[letter] = (
                0.55 * utt_vec[letter]
                + 0.20 * ivm_vec[letter]
                + 0.15 * gen_vec.get(letter, 1.0) / 2.0   # normalize correction to ~[0,1]
                + 0.10 * dce_vec[letter]
            )

        # Re-normalise
        _total = sum(combined.values()) or 1.0
        return {k: round(v / _total, 4) for k, v in combined.items()}

    def dominant(self, activation: Dict[str, float]) -> str:
        """Return the single most active axis letter."""
        return max(activation, key=lambda k: activation[k])


_axis_projector = AxisProjector()


# ============================================================================
# CONSTRAINT FIELD BALANCER
# Tracks sustained axis dominance and generates rebalancing pressure.
#
# The 5 constraints behave as a coupled dynamic field, not 5 independent meters.
# When one axis is dominant for too long, the sustained imbalance IS the cost
# signal — it makes adjacent constraint pathways cheaper, encouraging drift
# toward unexplored regions of the state space.
#
# Timescale is axis-aware, derived from AXIS_TICK_PARTICIPATION:
#   X (surface): rebalances in ~4 exchanges   (decay=0.25)
#   T:           rebalances in ~12 exchanges  (decay=0.08)
#   N:           rebalances in ~40 exchanges  (decay=0.025)
#   B:           rebalances in ~125 exchanges (decay=0.008)
#   A (core):    rebalances in ~330 exchanges (decay=0.003)
#
# This prevents chaotic fast oscillation (no hard rule triggers) while still
# ensuring no single axis monopolizes the field for long stretches.
# ============================================================================

class ConstraintFieldBalancer:
    """
    Dynamic field balancer across the 5 constraint axes.

    Maintains a per-axis EMA of recent activation.  When the EMA shows
    sustained dominance on one axis, the field_gradient() method returns
    positive values for the starved axes — signaling that those constraint
    pathways are cheaper and should be explored.

    This feeds back into three layers:
      1. AxisProjector — starved axes get a boost in the orientation blend
      2. Genealogy — small relief events for starved axes lower their promotion cost
      3. LSV (via grammar engine) — nudges sentence structure toward balance
    """

    # Decay rates derived from AXIS_TICK_PARTICIPATION ratios.
    # Faster surface axes (X) track imbalance quickly; deep core (A) accumulates slowly.
    _DECAY: Dict[str, float] = {
        "X": 0.25,    # ~4 exchanges to equilibrate
        "T": 0.08,    # ~12 exchanges
        "N": 0.025,   # ~40 exchanges
        "B": 0.008,   # ~125 exchanges
        "A": 0.003,   # ~330 exchanges
    }

    # Genealogy ability IDs for each axis (what gets relieved when axis is starved)
    _STARVED_ABILITY: Dict[str, str] = {
        "X": "X:ADMISSIBILITY",
        "T": "T:ADVANCE_TICK",
        "N": "N:FLOW_CONTROL",
        "B": "B:INTERFACE_WEAKEN",
        "A": "A:OUTLET_PUSH",
    }

    def __init__(self):
        # Per-axis EMA of activation level (initialised to perfect balance)
        self._ema: Dict[str, float] = {a: 0.20 for a in ("X", "T", "N", "B", "A")}
        self._exchange_count: int = 0
        self._genealogy_inject_interval: int = 10   # inject to genealogy every N exchanges

    def update(self, activation: Dict[str, float], systems: dict):
        """
        Record this exchange's activation vector.
        Periodically injects gradient to genealogy when imbalance is sustained.
        """
        for ax, alpha in self._DECAY.items():
            current = activation.get(ax, 0.20)
            self._ema[ax] = (1.0 - alpha) * self._ema[ax] + alpha * current
        self._exchange_count += 1

        # Re-normalise EMA so it stays a probability distribution
        _s = sum(self._ema.values())
        if _s > 0:
            self._ema = {k: v / _s for k, v in self._ema.items()}

        # Periodically push gradient into genealogy to lower costs for starved axes
        if self._exchange_count % self._genealogy_inject_interval == 0:
            try:
                gen = systems.get("genealogy")
                if gen:
                    self._inject_to_genealogy(gen)
            except Exception:
                pass

        # Nudge LSV via grammar engine / perception to rebalance expression structure
        try:
            grammar = systems.get("grammar_engine")
            if grammar and hasattr(grammar, "_genealogy") and grammar._genealogy is not None:
                # Feed the gradient into the LSV nudge already wired in perception
                perception = systems.get("perception")
                if perception and hasattr(perception, "evo"):
                    grad = self.field_gradient()
                    # Invert gradient sign for LSV nudge: starved axis = needs boosting
                    # Use the grammar engine's set_genealogy orientation as base,
                    # then blend in the field gradient
                    if hasattr(perception.evo, "nudge_lsv_from_axes"):
                        # Convert gradient to an orientation-like dict (>1.0 = compress/boost)
                        lsv_orient = {
                            ax: 1.0 + grad.get(ax, 0.0) * 2.0
                            for ax in ("X", "T", "N", "B", "A")
                        }
                        outlet = self._ema.get("A", 0.2) / 0.2   # relative to ideal
                        perception.evo.nudge_lsv_from_axes(lsv_orient, outlet)
        except Exception:
            pass

    def field_gradient(self) -> Dict[str, float]:
        """
        Return the rebalancing gradient vector.

        Positive value for axis X  → X is STARVED (below average activation)
        Negative value for axis X  → X is DOMINANT (above average activation)

        Magnitude is quadratic in the deviation so mild imbalance produces
        gentle pressure while sustained dominance produces strong pressure.
        """
        ideal = 0.20
        gradient: Dict[str, float] = {}
        for ax in ("X", "T", "N", "B", "A"):
            imbalance = self._ema[ax] - ideal
            # Quadratic cost, sign preserved
            gradient[ax] = round(-imbalance * abs(imbalance) * 25.0, 5)
        return gradient

    def _inject_to_genealogy(self, genealogy: Any):
        """
        Log small relief events for starved axes so their promotion costs drop.
        Only injects for axes genuinely below ideal (gradient > threshold).
        """
        import hashlib as _hl
        gradient = self.field_gradient()
        for ax, g in gradient.items():
            if g < 0.005:   # only inject for meaningfully starved axes
                continue
            ability = self._STARVED_ABILITY.get(ax)
            if not ability:
                continue
            try:
                pv_before = {a: (g * 0.015 if a == ax else 0.0)
                             for a in ("X", "T", "N", "B", "A")}
                pv_after = {a: 0.0 for a in ("X", "T", "N", "B", "A")}
                genealogy.observe(
                    pressure_before=pv_before,
                    trace=[{"ability": ability,
                            "cost": 0.0003, "source": "field_balance"}],
                    pressure_after=pv_after,
                    state_sig_before=_hl.md5(
                        f"bal_b_{ax}".encode()).hexdigest()[:8],
                    state_sig_after=_hl.md5(
                        f"bal_a_{ax}".encode()).hexdigest()[:8],
                    notes={"tag": "field_balance", "axis": ax,
                           "gradient": round(g, 4), "ema": round(self._ema[ax], 4)},
                    difference_snapshot={},
                )
            except Exception:
                pass

    def rebalanced_orientation(self, base_orientation: Dict[str, float]) -> Dict[str, float]:
        """
        Blend the base genealogy orientation with the field gradient.
        Starved axes get their orientation boosted (make them more attractive).
        Dominant axes get their orientation suppressed.
        """
        gradient = self.field_gradient()
        result: Dict[str, float] = {}
        for ax in ("X", "T", "N", "B", "A"):
            base = base_orientation.get(ax, 1.0)
            # gradient > 0 = starved = boost orientation (compress, make cheaper)
            # gradient < 0 = dominant = suppress orientation (expand, make costlier)
            result[ax] = max(0.3, base + gradient.get(ax, 0.0) * 0.5)
        return result

    def rebalanced_activation(self, raw: Dict[str, float]) -> Dict[str, float]:
        """
        Boost starved axes in a raw {X,T,N,B,A} activation vector and renormalize.
        Starved axes (gradient > 0) get a gentle additive boost; dominant axes are
        lightly suppressed.  The result stays a proper probability distribution.
        """
        gradient = self.field_gradient()
        result: Dict[str, float] = {}
        for ax in ("X", "T", "N", "B", "A"):
            result[ax] = max(0.0, raw.get(ax, 0.2) + gradient.get(ax, 0.0) * 0.3)
        total = sum(result.values()) or 1.0
        return {k: round(v / total, 4) for k, v in result.items()}

    def status(self) -> Dict[str, Any]:
        grad = self.field_gradient()
        dominant = max(self._ema, key=lambda k: self._ema[k])
        starved = min(self._ema, key=lambda k: self._ema[k])
        return {
            "ema":      {k: round(v, 4) for k, v in self._ema.items()},
            "gradient": {k: round(v, 4) for k, v in grad.items()},
            "exchanges": self._exchange_count,
            "dominant": dominant,
            "starved":  starved,
            "balance_score": round(1.0 - max(abs(v) for v in grad.values()), 3),
        }


_field_balancer = ConstraintFieldBalancer()


def _project_utterance_axes(text: str, systems: dict) -> Dict[str, float]:
    """
    Parse text through UtteranceParser and project onto the 5 constraint axes.
    Returns {X, T, N, B, A} normalized activation.
    """
    try:
        from aurora_internal.aurora_utterance_parser import UtteranceParser as _UP
        _up = _UP()
        parsed = _up.parse(text)
        return _axis_projector.project(parsed, systems)
    except Exception:
        return {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}


def _classify_input_intent(text: str) -> str:
    """
    Classify the communicative intent of user input before routing.
    Returns one of: 'greeting', 'wellbeing_query', 'fact_assertion',
                    'name_question', 'recall_question', 'general'
    """
    import re
    t = (text or "").strip().lower()

    # Greetings
    _greeting_starts = (
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good evening',
        'good afternoon', 'good day', 'howdy', "what's up", 'whats up',
        'sup', 'yo ', 'yo,',
    )
    if t in {'hi', 'hello', 'hey', 'yo'} or any(t.startswith(g) for g in _greeting_starts):
        if re.search(r'\bhow\s+are\s+you\b|\bhow\s+are\s+you\s+doing\b', t):
            return 'wellbeing_query'
        return 'greeting'

    # Wellbeing / state queries directed at Aurora
    _wellbeing_patterns = [
        r'\bhow\s+are\s+you\b',
        r'\bhow\s+are\s+you\s+doing\b',
        r'\bhow\s+do\s+you\s+feel\b',
        r'\bhow\s+is\s+your\b',
        r'\bare\s+you\s+(okay|well|alright|good|fine|functioning|working|okay)\b',
        r'\bhow.{0,20}feeling\b',
        r'\bare\s+your\s+systems\b',
        r'\bdo\s+you\s+have\s+any\s+questions\b',
        r'\bare\s+you\s+understanding\b',
        # Reflective questions about Aurora's inner experience
        r'\bwhat\s+does\s+(that|this|it)\s+mean\s+to\s+you\b',
        r'\bwhat\s+do\s+i\s+mean\s+to\s+you\b',
        r'\bwhat\s+does\s+\w+\s+mean\s+to\s+you\b',
        r'\bhow\s+do\s+you\s+feel\s+about\s+(me|us|that|this)\b',
        r'\bdo\s+you\s+care\b',
        r'\bdo\s+you\s+think\s+about\s+(me|us)\b',
        # Internal state / what Aurora is processing or thinking
        r'\bwhat\s+are\s+you\s+think',
        r'\bwhat.{0,10}(on your mind|in your mind|going through your)\b',
        r'\bwhat\s+are\s+you\s+(feeling|sensing|processing|experiencing|noticing)\b',
        r'\bwhat\s+(is|are)\s+you\s+(occupied|thinking|dwelling)\b',
        r"\bwhat'?s?\s+(on\s+)?your\s+mind\b",
        r'\bare\s+you\s+think(ing)?\b',
        r'\bwhat\s+do\s+you\s+think\s+about\s+(right\s+now|currently|lately)\b',
    ]
    for pat in _wellbeing_patterns:
        if re.search(pat, t):
            return 'wellbeing_query'

    # User asserting their name or a personal fact
    _assertion_patterns = [
        r'\bmy\s+name\s+is\s+\w+',
        r"\bi'?m\s+\w+",
        r'\bi\s+am\s+\w+',
        r'\bi\s+am\s+called\s+\w+',
        r'\bcall\s+me\s+\w+',
        r'\byou\s+can\s+call\s+me\s+\w+',
        r'\bi\s+go\s+by\s+\w+',
    ]
    for pat in _assertion_patterns:
        if re.search(pat, t):
            return 'fact_assertion'

    # User asking about their own name / identity
    if re.search(r'\bmy\s+name\b|\bwho\s+am\s+i\b|\bdo\s+you\s+know\s+me\b', t):
        return 'name_question'

    # Memory / recall questions
    _recall_patterns = [
        r'\bdo\s+you\s+remember\b',
        r'\bdo\s+you\s+know\s+who\s+i\s+am\b',
        r'\bwhat\s+(is|was)\s+my\s+(name|identity)\b',
        r'\bremember\s+when\b',
        r'\bwhat.{0,20}i\s+(said|told|mentioned|shared)\b',
    ]
    for pat in _recall_patterns:
        if re.search(pat, t):
            return 'recall_question'

    # Contradiction / correction ("that's not right", "that's wrong", "no, that's not X")
    _contradiction_patterns = [
        r"\bthat'?s?\s+not\s+(right|correct|true|accurate|my|what|who|the)",
        r'\bno,?\s+(that|it|you)\s+(is|isn\'t|was|wasn\'t|are|aren\'t)\b',
        r'\bactually,?\s+no\b',
        r'\bthat\s+(was|is)\s+wrong\b',
        r'\bincorrect\b',
        r'\bthat.{0,20}not\s+my\b',
    ]
    for pat in _contradiction_patterns:
        if re.search(pat, t):
            return 'contradiction'

    # Social requests  -- "say hi", "say hello to X", "greet X", "say something to X"
    _social_patterns = [
        r'\bsay\s+(hi|hello|hey|greetings|howdy)\b',
        r'\bsay\s+hello\s+to\b',
        r'\bgreet\s+\w+\b',
        r'\bwave\s+(at|to)\b',
        r'\bsay\s+something\s+to\b',
        r'\bintroduce\s+yourself\b',
    ]
    for pat in _social_patterns:
        if re.search(pat, t):
            return 'social_request'

    # Introduction of a person  -- "my sister X is here", "this is my friend X", "meet X"
    # Note: search against original `text` (not `t`) so capitalized names match
    _intro_patterns = [
        r'\bmy\s+(sister|brother|friend|colleague|partner|wife|husband|mother|father|'
        r'mom|dad|daughter|son|cousin|aunt|uncle|coworker|boss)\s+[A-Za-z]+\b',
        r'\bthis\s+is\s+my\s+\w+\s+[A-Za-z]+\b',
        r'\bthis\s+is\s+[A-Z][a-z]+\b',
        r'\bmeet\s+[A-Z][a-z]+\b',
        r'\b[A-Z][a-z]+\s+is\s+(here|with\s+me|visiting|joining)\b',
    ]
    for pat in _intro_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return 'introduction'

    # Follow-up / repeat ("I asked about X", "my question was X", "I said X")
    _followup_patterns = [
        r'\bi\s+(asked|was\s+asking|said|mentioned)\b',
        r'\bmy\s+question\s+(was|is)\b',
        r'\bwhat\s+i\s+(asked|said|meant|was\s+saying)\b',
        r'\bthat\s+(wasn\'t|wasnt|isn\'t|isnt)\s+(what|the\s+answer)\b',
        r'\bstill\s+(haven\'t|havent|didn\'t|didnt)\s+(answer|tell)',
    ]
    for pat in _followup_patterns:
        if re.search(pat, t):
            return 'followup_request'

    # ---- STATEMENT DETECTION ----
    # If none of the above matched, check whether this is a plain statement
    # (no ?, no question word, not a greeting/correction/recall).
    # Statements should fall straight to L5 — never search, never prescript.
    _ends_q = t.strip().endswith('?')
    _starts_q = any(t.startswith(w + ' ') or t == w for w in (
        'what', 'how', 'why', 'where', 'who', 'when', 'which',
        'define', 'explain', 'tell me', 'look up', 'search for',
        'solve', 'search youtube', 'search google', 'search github',
        'search reddit', 'search duckduckgo',
        'open', 'launch', 'start', 'go to', 'navigate to', 'browse to',
        'click', 'type', 'press', 'read',
        'can you', 'could you', 'do you', 'does', 'is there', 'are there',
        'will you', 'would you', 'should', 'is it', 'are you',
    ))
    import re as _re_stmt
    _has_q_word = bool(_re_stmt.search(
        r'\b(what|how|why|where|who|when|which)\b', t
    ))
    if not _ends_q and not _starts_q and not _has_q_word:
        return 'statement'

    return 'general'


def _extract_user_name(text: str):
    """Extract a name from user fact assertions like 'My name is Sunni'."""
    import re
    _skip = {
        'a', 'the', 'an', 'is', 'am', 'are', 'not', 'just', 'also', 'called', 'known',
        'hungry', 'tired', 'happy', 'sad', 'fine', 'okay', 'ok', 'good', 'here', 'ready',
    }
    patterns = [
        r'\bmy\s+name\s+is\s+([A-Za-z]+)\b',
        r"\bi'?m\s+([A-Za-z]+)\b",
        r'\bi\s+am\s+([A-Za-z]+)\b',
        r'\bcall\s+me\s+([A-Za-z]+)\b',
        r'\byou\s+can\s+call\s+me\s+([A-Za-z]+)\b',
        r'\bi\s+go\s+by\s+([A-Za-z]+)\b',
        r'\bi\s+am\s+called\s+([A-Za-z]+)\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1)
            if name.lower() not in _skip:
                return name.capitalize()
    return None


def _get_stored_user_name(conversation_memory) -> str:
    """Retrieve the user's name from stored facts, prioritizing most recent."""
    if not conversation_memory:
        return ""
    import re
    # Patterns for facts like "User's name is X" or "My name is X"
    patterns = [
        r"user(?:'s)?\s+name\s+is\s+([A-Za-z]+)",
        r"my\s+name\s+is\s+([A-Za-z]+)"
    ]
    # Search facts in reverse order (newest first)
    facts = getattr(conversation_memory, 'learned_facts', [])
    for fact in reversed(facts):
        fact_text = fact.get("fact", "").lower()
        for pat in patterns:
            m = re.search(pat, fact_text)
            if m:
                return m.group(1).capitalize()
    return ""


def _capture_pressure_snapshot(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Capture current constraint/operator pressure state for lineage traces."""
    snap = {
        "operator_gradients": {},
        "slot_polarity": {},
        "heat": {},
    }
    try:
        from aurora_internal.aurora_constraint_manifold_patched import Constraint
        from aurora_internal.aurora_noncomp_registry import REGISTRY
        accountant = systems.get('accountant')
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            op = REGISTRY.operator(c)
            snap["operator_gradients"][c.name] = float(getattr(op, "pressure_gradient", 0.0))
            if accountant:
                try:
                    snap["slot_polarity"][c.name] = float(accountant.slot(c).polarity)
                except Exception:
                    snap["slot_polarity"][c.name] = 0.0
    except Exception:
        pass

    try:
        lattice = systems.get('lattice')
        if lattice and hasattr(lattice, 'heat_status'):
            hs = lattice.heat_status() or {}
            snap["heat"] = {
                "score": float(hs.get("score", 0.0)),
                "level": str(hs.get("level", "")),
            }
    except Exception:
        pass
    return snap


def _derive_applied_effects(
    pressure_before: Dict[str, Any],
    pressure_after: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute simple ripple deltas between pressure snapshots."""
    out = {"operator_gradient_delta": {}, "heat_delta": 0.0}
    before_ops = (pressure_before or {}).get("operator_gradients", {}) or {}
    after_ops = (pressure_after or {}).get("operator_gradients", {}) or {}
    keys = sorted(set(before_ops.keys()) | set(after_ops.keys()))
    for k in keys:
        b = float(before_ops.get(k, 0.0) or 0.0)
        a = float(after_ops.get(k, 0.0) or 0.0)
        out["operator_gradient_delta"][k] = a - b
    try:
        hb = float(((pressure_before or {}).get("heat", {}) or {}).get("score", 0.0) or 0.0)
        ha = float(((pressure_after or {}).get("heat", {}) or {}).get("score", 0.0) or 0.0)
        out["heat_delta"] = ha - hb
    except Exception:
        out["heat_delta"] = 0.0
    return out


def _extract_role_assertion(user_text: str) -> Dict[str, Any]:
    """
    Parse role assertions needed for genealogical trace instantiation.
    Returns dict with keys: subject, relation, negated.
    """
    t = (user_text or "").strip()
    if not t:
        return {}
    m = re.search(r'\b([A-Za-z][A-Za-z0-9_-]{1,})\s+is\s+not\s+my\s+(creator|operator|co-author|coauthor)\b', t, re.IGNORECASE)
    if m:
        return {"subject": m.group(1), "relation": m.group(2).lower(), "negated": True}
    m = re.search(r'\b([A-Za-z][A-Za-z0-9_-]{1,})\s+is\s+my\s+(creator|operator|co-author|coauthor)\b', t, re.IGNORECASE)
    if m:
        return {"subject": m.group(1), "relation": m.group(2).lower(), "negated": False}
    m = re.search(r'\b([A-Za-z][A-Za-z0-9_-]{1,})\s+is\s+the\s+(creator|operator|co-author|coauthor)\b', t, re.IGNORECASE)
    if m:
        return {"subject": m.group(1), "relation": m.group(2).lower(), "negated": False}
    return {}


def _answer_relational_role_question(user_text: str, systems: Dict[str, Any]) -> Optional[Tuple[str, str, float]]:
    """
    Resolve creator/operator/co-author role questions from identity + lineage traces,
    before generic lexical fallback/search.
    """
    t = (user_text or "").strip()
    tl = t.lower()
    if not t:
        return None

    core_identity = systems.get('core_identity')
    memory = systems.get('conversation_memory')

    # Hard-anchor creator identity from immutable core identity.
    if re.search(r'\bwho\s+(made|created|built)\s+you\b|\bwho\s+is\s+your\s+creator\b', tl):
        if core_identity:
            try:
                creator = core_identity.entities.get("sunni")
                if creator:
                    return (f"My creator is {creator.name}.", "precise", 0.98)
            except Exception:
                pass
            return (core_identity.who_made_me(), "self-aware", 0.97)
        return ("My creator is Sunni (Sir) Morningstar.", "precise", 0.95)

    # "Is X your creator/operator/co-author?"
    m = re.search(r'\bis\s+([A-Za-z][A-Za-z0-9_-]{1,})\s+your\s+(creator|operator|co-author|coauthor)\b', t, re.IGNORECASE)
    if m and memory and hasattr(memory, "role_evidence"):
        subj = m.group(1)
        rel = m.group(2).lower().replace("coauthor", "co-author")
        ev = memory.role_evidence(subj, rel)
        status = ev.get("status", "unknown")
        pp = int(ev.get("pressure_points", 0) or 0)
        if status == "affirmed":
            return (f"Yes. My lineage traces currently support {subj} as {rel} "
                    f"(pressure history points: {pp}).", "precise", 0.9)
        if status == "negated":
            return (f"No. My lineage traces negate {subj} as {rel} "
                    f"(pressure history points: {pp}).", "precise", 0.92)
        if status == "mixed":
            return (f"My lineage traces for {subj} as {rel} are mixed right now "
                    f"(pressure history points: {pp}).", "attentive", 0.78)
        return (f"I don't have a stable lineage-backed role for {subj} as {rel} yet.",
                "honest", 0.72)

    # "Who is X?" — answer from lineage traces when available.
    m = re.search(r'\bwho\s+is\s+([A-Za-z][A-Za-z0-9_-]{1,})\b', t, re.IGNORECASE)
    if m and memory and hasattr(memory, "get_anchor_traces"):
        subj = m.group(1)
        traces = memory.get_anchor_traces(subj)
        if traces:
            creator_ev = memory.role_evidence(subj, "creator") if hasattr(memory, "role_evidence") else {}
            operator_ev = memory.role_evidence(subj, "operator") if hasattr(memory, "role_evidence") else {}
            coauthor_ev = memory.role_evidence(subj, "co-author") if hasattr(memory, "role_evidence") else {}

            # Compose strongest evolved role statement.
            role_bits = []
            for rel, ev in (("creator", creator_ev), ("operator", operator_ev), ("co-author", coauthor_ev)):
                st = ev.get("status", "unknown")
                if st == "affirmed":
                    role_bits.append(f"{rel}=affirmed")
                elif st == "negated":
                    role_bits.append(f"{rel}=negated")
                elif st == "mixed":
                    role_bits.append(f"{rel}=mixed")

            pp = sum(len(tr.get("pressure_history", []) or []) for tr in traces)
            if role_bits:
                return (
                    f"{subj} in my lineage memory: {', '.join(role_bits)} "
                    f"(traces={len(traces)}, pressure history points={pp}).",
                    "precise",
                    0.86,
                )
            return (
                f"I have lineage traces about {subj}, but no stable role classification yet "
                f"(traces={len(traces)}, pressure history points={pp}).",
                "attentive",
                0.75,
            )

    return None



def _evolutionary_response_refinement(
    systems: Dict[str, Any],
    user_text: str,
    base_text: str,
    tone: str = "neutral",
) -> str:
    """
    Refine responses in a development-aware way so prose and relational continuity
    evolve with Aurora's own growth signals (memory depth + language evolution + OETS).
    """
    if not base_text:
        return base_text

    perception = systems.get('perception')
    working_memory = systems.get('working_memory')
    memory = systems.get('conversation_memory')

    understanding_idx = 0.0
    evo_cycles = 0
    sentence_target = 10

    try:
        if perception and getattr(perception, 'oets', None):
            stats = perception.oets.get_stats()
            understanding_idx = float(
                stats.get('understanding', {}).get('understanding_index', 0.0)
            )
    except Exception:
        pass

    try:
        if perception and hasattr(perception, 'evo_status'):
            evo = perception.evo_status() or {}
            lsv = evo.get('lsv', {}) or {}
            evo_cycles = int(lsv.get('evolution_cycles', 0) or 0)
            sentence_target = int(lsv.get('sentence_length_target', 10) or 10)
    except Exception:
        pass

    growth_score = understanding_idx + min(1.0, evo_cycles / 50.0)

    # Pull learned behavior hints from DreamTrainer (what Aurora knows from simulation)
    learned_hints: List[str] = []
    try:
        dream_trainer = systems.get('dream_trainer')
        if dream_trainer is not None:
            wm = working_memory
            topic_words = []
            if wm and getattr(wm, 'current_topic', ''):
                topic_words = wm.current_topic.split()[:4]
            # Classify rough context from tone and text
            ctx_type = "general"
            if any(w in base_text.lower() for w in ("feel", "care", "understand", "sorry")):
                ctx_type = "emotional"
            elif any(w in base_text.lower() for w in ("think", "know", "believe", "certain")):
                ctx_type = "philosophy"
            learned_hints = dream_trainer.get_response_hints(ctx_type, topic_words, systems)
    except Exception:
        pass

    # Build relational continuity from active topic / known user context.
    continuity_bits = []
    if working_memory and getattr(working_memory, 'current_topic', ''):
        topic = working_memory.current_topic
        if topic and topic.lower() not in base_text.lower():
            continuity_bits.append(f"This still connects to our thread about {topic}.")

    # Weave in a learned behavior hint when growth is sufficient
    if learned_hints and growth_score > 0.4:
        hint = learned_hints[0]
        # Only add if it's not already echoed in the response
        if hint.lower()[:30] not in base_text.lower():
            continuity_bits.append(hint)

    if memory and getattr(memory, 'learned_facts', None) and growth_score > 0.8:
        continuity_bits.append("I'll carry this forward so later reasoning stays consistent.")

    refined = base_text.strip()

    # Medium growth: add one relational bridge sentence for coherence continuity.
    if growth_score > 0.55 and continuity_bits:
        refined = f"{refined} {continuity_bits[0]}"

    # Higher growth: add compact reflective reasoning sentence for richer prose.
    if growth_score > 1.0 and len(refined.split()) < max(12, sentence_target):
        reflective = (
            "My best understanding comes from linking what you just asked "
            "to what we've already established."
        )
        if reflective.lower() not in refined.lower():
            refined = f"{refined} {reflective}"

    # Keep responses bounded by evolving sentence target (avoid runaway verbosity).
    # REMOVED CAP: Allow comprehensive responses as requested by user.
    # max_words = max(18, min(60, sentence_target * 2))
    # words = refined.split()
    # if len(words) > max_words:
    #     refined = " ".join(words[:max_words]).rstrip(' ,;') + "..."

    try:
        from aurora_articulation import smooth_with_decision
        decision = smooth_with_decision(refined, prompt=user_text, tone=tone)
        if perception and hasattr(perception, 'ingest_interaction'):
            perception.ingest_interaction({
                'input': decision.selected,
                'tone': tone,
                'i_state': 'i_is',
                'source': 'articulation_pressure_feedback',
                'features': {
                    'articulation_accepted': 1.0 if decision.accepted else 0.0,
                    'pressure_relief': decision.pressure_relief,
                    'original_pressure': decision.original_pressure,
                    'candidate_pressure': decision.candidate_pressure,
                },
            }, mode="gateway")
        return decision.selected
    except Exception:
        return refined



def _extract_pipeline_signals(systems: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read live cognitive state from the running pipeline layers.
    No extra synthesis call — reads already-computed values from
    consciousness entropy, DER, and DMM that update each tick.
    Assembly-level signals (dominant_axis, paradoxes, thought_killed)
    are populated later in dual_question_pipeline once synthesis runs.
    """
    signals: Dict[str, Any] = {
        'coherence': 1.0,
        'stagnation': 0.0,
        'novelty': 0.5,
        'thermal_load': 0.0,
        'spike_detected': False,
        'presence': 1.0,
        'dmm_alignment': 0.5,
        'dmm_vitality': 1.0,
        'dominant_axis': '',
        'paradoxes': [],
        'thought_killed': False,
        'kill_reason': '',
        'assembly_quality': 1.0,
    }
    try:
        consciousness = systems.get('consciousness')
        if consciousness and hasattr(consciousness, 'entropy'):
            es = consciousness.entropy.state
            signals['coherence'] = float(es.coherence)
            signals['stagnation'] = float(es.stagnation_score)
            signals['novelty'] = float(es.novelty)
    except Exception:
        pass
    try:
        dimensional = systems.get('dimensional')
        if dimensional:
            if hasattr(dimensional, 'der'):
                der = dimensional.der
                signals['thermal_load'] = float(der.thermal_load)
                signals['spike_detected'] = bool(der.spike_detected)
                signals['presence'] = float(der.presence)
            if hasattr(dimensional, 'dmm'):
                signals['dmm_alignment'] = float(dimensional.dmm.state.alignment)
                signals['dmm_vitality'] = float(dimensional.dmm.state.vitality)
    except Exception:
        pass
    return signals


def _apply_pipeline_modulation(
    text: str, tone: str, conf: float,
    signals: Optional[Dict[str, Any]],
) -> Tuple[str, str, float]:
    """
    Post-process a response using live pipeline state signals.

    Applies:
      - Thermal honesty  (DER spike_detected / thermal_load)
      - Coherence hedging (L4 entropy coherence)
      - Stagnation pressure (entropy stagnation_score)
      - Paradox surfacing  (I-State being conflicts from AssemblyResult)
      - Thought-kill acknowledgment (DMM moral friction → metabolic collapse)
      - Dominant-axis tone register (from AssemblyResult.dominant_axis)
      - Assembly quality gating (AssemblyResult.quality)

    All modifications are additive. Never destroys the base response.
    """
    if not signals or not text:
        return text, tone, conf

    # ---- Thermal spike: dissonance is heating the system ----
    if signals.get('spike_detected'):
        heat = signals.get('thermal_load', 0.0)
        if heat > 0.8 and not text.endswith('?'):
            text = text + " I'm picking up real friction processing this — something contradicts itself."
        elif heat > 0.6 and not text.endswith('?'):
            text = text + " Something in this sits uneasy with me."
        if tone in ('neutral', 'attentive', 'precise'):
            tone = 'uncertain'
        conf = min(conf, 0.65)

    # ---- Low coherence: degraded L4 assembly cycle ----
    coherence = signals.get('coherence', 1.0)
    if coherence < 0.3:
        conf = min(conf, 0.55)
        if not text.endswith('?') and not text.endswith('...'):
            text = text + " My reasoning feels fragmented right now."
    elif coherence < 0.5:
        conf = min(conf, 0.72)

    # ---- High stagnation: loop pressure building ----
    if signals.get('stagnation', 0.0) > 0.5:
        conf = min(conf, 0.70)

    # ---- Paradoxes: opposing I-State beings both activated ----
    paradoxes = signals.get('paradoxes', [])
    if paradoxes:
        _axis_names = {
            'existence': 'being', 'temporal': 'time',
            'energy': 'action', 'boundary': 'boundary', 'agency': 'agency',
        }
        axes = [_axis_names.get(p, p) for p in paradoxes[:2]]
        text = (text + f" There's a tension in what you're describing — "
                f"I see it pulling in opposite directions on {' and '.join(axes)}.")
        conf = min(conf, 0.75)

    # ---- Thought killed by DMM moral friction ----
    if signals.get('thought_killed'):
        text = text + " I weighed something there and chose not to follow it."
        conf = max(conf, 0.85)

    # ---- Dominant axis → tone register ----
    # Note: dominant_axis is stored as a letter (X/T/N/B/A), not a full name.
    _axis_tone = {
        'X': 'reflective',
        'T': 'attentive',
        'N': 'engaged',
        'B': 'observational',
        'A': 'direct',
    }
    axis = signals.get('dominant_axis', '')
    if axis and tone in ('neutral', 'attentive') and axis in _axis_tone:
        tone = _axis_tone[axis]

    # ---- DER dominant emotion → tone refinement ----
    # Overrides axis tone when emotional state is strong enough to colour expression.
    _emotion_tone = {
        'curiosity': 'curious',
        'joy':       'warm',
        'calm':      'attentive',
        'fear':      'uncertain',
        'anger':     'direct',
        'sadness':   'reflective',
    }
    dom_emotion = signals.get('dominant_emotion', '')
    em_coherence = signals.get('emotional_coherence', 1.0)
    if dom_emotion and dom_emotion != 'calm' and em_coherence > 0.4:
        em_tone = _emotion_tone.get(dom_emotion)
        if em_tone and tone in ('neutral', 'attentive', 'reflective'):
            tone = em_tone

    # ---- Low assembly quality: acknowledge reduced depth ----
    if signals.get('assembly_quality', 1.0) < 0.3 and not signals.get('thought_killed'):
        conf = min(conf, 0.60)

    # ---- Ontological Embodiment (CAPABILITY 3) ----
    # EmbodiedStateTranslator surfaces a first-person experiential description
    # when self-state delta > 0.2 from previous turn. Only appended when significant.
    try:
        from aurora_self_grounding import get_embodied_translator
        _embodied_desc = get_embodied_translator().translate(signals, {})
        if _embodied_desc and len(text.split()) > 3:
            text = text + f" ({_embodied_desc})"
    except Exception:
        pass

    return text, tone, conf


# ---- Pipeline ability registration (constraint-traceability) ----
_PIPELINE_ABILITIES_REGISTERED: bool = False


def _ensure_pipeline_abilities(genealogy: Any) -> None:
    """
    Register AbilityProfiles for _extract_pipeline_signals and
    _apply_pipeline_modulation into the genealogy logger so both
    new operations are traceable through the evolutionary chain.
    Called lazily on first modulation event.
    """
    global _PIPELINE_ABILITIES_REGISTERED
    if _PIPELINE_ABILITIES_REGISTERED or not genealogy:
        return
    try:
        from aurora_evolution_stack import AbilityProfile
        from aurora_internal.constraint_genealogy import _augment_ability_profile_with_origin

        _sig_ap = AbilityProfile(
            id="N:READ_PIPELINE_STATE",
            axis="N",
            requires=("T", "N", "B", "A"),
            cost={"X": 0.0, "T": 0.01, "N": 0.02, "B": 0.01, "A": 0.01},
            risk={"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
            effect_tags=(
                "energy_read", "thermal_snapshot", "entropy_snapshot",
                "dmm_state_read", "boundary_presence",
            ),
            notes="Read live N/T/B/A pipeline state: DER thermal, L4 entropy, DMM vitality.",
        )
        _mod_ap = AbilityProfile(
            id="B:SHAPE_EXPRESSION_BOUNDARY",
            axis="B",
            requires=("X", "B", "A"),
            cost={"X": 0.0, "T": 0.01, "N": 0.01, "B": 0.02, "A": 0.01},
            risk={"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.01, "A": 0.0},
            effect_tags=(
                "boundary_shaping", "tone_shift", "confidence_gate",
                "paradox_surface", "thought_kill_surface", "axis_tone_register",
            ),
            notes=(
                "Shape the outbound expression boundary using live pipeline signals: "
                "thermal honesty, coherence hedging, paradox surfacing, "
                "thought-kill acknowledgment, dominant-axis tone register."
            ),
        )

        if hasattr(genealogy, 'abilities'):
            genealogy.abilities[_sig_ap.id] = _augment_ability_profile_with_origin(_sig_ap)
            genealogy.abilities[_mod_ap.id] = _augment_ability_profile_with_origin(_mod_ap)
        _PIPELINE_ABILITIES_REGISTERED = True
    except Exception:
        pass


def _log_modulation_event(
    genealogy: Any,
    signals: Dict[str, Any],
    text_changed: bool,
    tone_changed: bool,
) -> None:
    """
    Log a genealogy relief event after _apply_pipeline_modulation fires.
    Encodes current pipeline tension as pressure_before; shaped output
    boundary as pressure_after. Relief = tension reduced by modulation.
    Only logs when modulation actually modified the response.
    Traces back to:
      N:READ_PIPELINE_STATE   (N-axis, energy read)
      B:SHAPE_EXPRESSION_BOUNDARY  (B-axis, boundary shaping)
    """
    if not genealogy or not (text_changed or tone_changed):
        return
    try:
        from aurora_evolution_stack import PressureVec, TraceItem
        _ensure_pipeline_abilities(genealogy)

        # Pressure before: live pipeline tension at this moment
        p_before = PressureVec(
            X=0.0,
            T=float(signals.get('stagnation', 0.0)),
            N=float(signals.get('thermal_load', 0.0)),
            B=max(0.0, 1.0 - float(signals.get('coherence', 1.0))),
            A=1.0 if signals.get('thought_killed') else 0.0,
        )
        # Pressure after: boundary is shaped — T/N/B pressures relieved ~10-20%,
        # A collapses to 0 (thought-kill acknowledged and surfaced)
        p_after = PressureVec(
            X=0.0,
            T=p_before.T * 0.85,
            N=p_before.N * 0.90,
            B=p_before.B * 0.80,
            A=0.0,
        )

        trace = [
            TraceItem(kind="ABILITY", id="N:READ_PIPELINE_STATE"),
            TraceItem(kind="ABILITY", id="B:SHAPE_EXPRESSION_BOUNDARY"),
        ]
        tick = int(getattr(genealogy, 'tick_count', 0))
        genealogy.observe(
            pressure_before=p_before,
            trace=trace,
            pressure_after=p_after,
            state_sig_before=f"pre_mod_t{tick}",
            state_sig_after=f"post_mod_t{tick}",
            notes={
                "source": "apply_pipeline_modulation",
                "text_changed": text_changed,
                "tone_changed": tone_changed,
            },
        )
    except Exception:
        pass


def _pressure_vec_from_axes(axes: Dict[str, float]):
    from aurora_evolution_stack import PressureVec

    return PressureVec(
        X=float(axes.get("X", 0.0)),
        T=float(axes.get("T", 0.0)),
        N=float(axes.get("N", 0.0)),
        B=float(axes.get("B", 0.0)),
        A=float(axes.get("A", 0.0)),
    )


def _understanding_pass(response_text: str, pressure_vec: Any, systems: Dict[str, Any]) -> None:
    """
    Aurora processes her own output as a new inbound pressure event.
    This closes the re-entry loop at UNDERSTANDING without routing
    recursively through the external user-turn pipeline.
    """
    if not response_text:
        return
    try:
        response_axes = _project_utterance_axes(response_text, systems)
        response_axes = {ax: float(response_axes.get(ax, 0.0)) for ax in ("X", "T", "N", "B", "A")}
        response_pressure = _pressure_vec_from_axes(response_axes)

        from aurora_evolution_stack import TraceItem
        from aurora_governance_persistence_gateway import InboundPacket, StreamType as _ST, _generate_id

        packet = InboundPacket(
            packet_id=_generate_id("self"),
            stream_type=_ST.SELF_REFLECTION,
            content=response_text,
            metadata={"axes": response_axes, "phase": "UNDERSTANDING"},
            source="aurora",
        )

        genealogy = systems.get("genealogy")
        tick = int(getattr(genealogy, "tick_count", 0)) if genealogy is not None else 0
        dominant_axis = max(response_axes, key=response_axes.get) if response_axes else "X"
        dominant_field = dominant_axis
        _remember_self_expression(response_text, systems, response_axes, tick)

        field_map = systems.get("field_map")
        if field_map is None:
            aurora = systems.get("aurora")
            _dim = getattr(getattr(aurora, "gateway", None), "dimensional", None) if aurora is not None else None
            field_map = getattr(_dim, "field_map", None) if _dim is not None else None
        if field_map is not None:
            try:
                field_map.update(response_pressure)
                state = field_map.get_state() if hasattr(field_map, "get_state") else None
                field = getattr(state, "dominant_field", None)
                dominant_field = getattr(field, "name", None) or getattr(field, "field_id", dominant_field)
            except Exception:
                pass

        if genealogy is not None:
            try:
                before = pressure_vec if pressure_vec is not None else response_pressure
                before = _pressure_vec_from_axes({
                    ax: max(float(getattr(before, ax, 0.0)), response_axes[ax] + 0.01)
                    for ax in ("X", "T", "N", "B", "A")
                })
                genealogy.observe(
                    pressure_before=before,
                    trace=[TraceItem(kind="PACKET", id=packet.packet_id)],
                    pressure_after=response_pressure,
                    state_sig_before=f"pre_understanding_t{tick}",
                    state_sig_after=f"post_understanding_t{tick}",
                    notes={
                        "event": "UNDERSTANDING_EVENT",
                        "stream_type": packet.stream_type.value,
                        "response_axes": response_axes,
                        "dominant_field": str(dominant_field),
                        "tick": tick,
                    },
                )
            except Exception:
                pass

        modulation_log = systems.setdefault("_modulation_log", [])
        log_event = {
            "event": "UNDERSTANDING_EVENT",
            "response_axes": response_axes,
            "dominant_field": str(dominant_field),
            "tick": tick,
        }
        modulation_log.append(log_event)
        try:
            state_dir = Path(str(systems.get("state_dir", "aurora_state")))
            state_dir.mkdir(parents=True, exist_ok=True)
            with (state_dir / "modulation_log.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_event, ensure_ascii=True) + "\n")
        except Exception:
            pass
    except Exception:
        pass


def _build_comprehension_response(user_text: str, intent: str, systems: dict, pipeline_state: dict = None, faculty_attention: dict = None) -> tuple:
    """
    Aurora's comprehension layer.  Understands what the user is communicating,
    checks existing knowledge, reasons through questions, and produces a direct
    answer  -- before any template engine runs.

    Chain:  intent dispatch
              â†’ working memory (stated facts, recent topic)
              â†’ OETS knowledge (what Aurora has studied)
              â†’ search + reasoning (for unknown topics)
              â†’ fall through (â†’ template engine, last resort)
    """
    import re
    conversation_memory = systems.get('conversation_memory')
    core_identity = systems.get('core_identity')
    working_memory = systems.get('working_memory')
    search_adapter = systems.get('search_adapter')
    perception = systems.get('perception')
    lattice = systems.get('lattice')
    oets = getattr(perception, 'oets', None) if perception else None
    _reasoner = ReasoningEngine()
    _qu = UtteranceParser()

    self_reference = _match_self_reference(user_text, systems)

    # Use faculty_attention to refine intent if available
    faculty_routing = (faculty_attention or {}).get("routing_classification")
    if faculty_routing == "aurora_state_query" and intent == "general":
        intent = "wellbeing_query"
    elif faculty_routing == "self_question" and intent == "general":
        intent = "wellbeing_query" # Force internal state logic

    # ---- AXIS PROJECTION — read live constraint state + utterance signal -----
    # Produces {X, T, N, B, A} activation vector for this exchange.
    # The field balancer then boosts starved axes (sustained imbalance = cost signal)
    # before stamping the corrected vector into pipeline_state.
    _axis_activation_raw = _project_utterance_axes(user_text, systems)
    _axis_activation = _field_balancer.rebalanced_activation(_axis_activation_raw)
    _field_balancer.update(_axis_activation, systems)
    _dominant_axis = _axis_projector.dominant(_axis_activation)
    
    # ---- PASS 2: SEMANTIC REASONING (Pressure -> Concept) -----------
    # Interpret raw axis drift into abstract concepts using OETS.
    _semantic_context = {}
    if systems.get("dpme") and oets:
        try:
            # Sync DPME with current activation
            systems["dpme"].apply_attentional_guidance(1.0, [_dominant_axis])
            systems["dpme"].resolve_semantic_tension(oets)
            _semantic_context = getattr(systems["dpme"], "_semantic_context", {})
            if _semantic_context and pipeline_state is not None:
                pipeline_state["semantic_interpretation"] = _semantic_context
        except Exception:
            pass

    # Feed axis context into telemetry so classify_fail_dimensions() can
    # weight fail severities by the constraint geometry of this turn.
    try:
        from aurora_telemetry import get_telemetry as _get_tel
        _get_tel().set_axis_context(_axis_activation)
    except Exception:
        pass

    # ---- DER EMOTION WIRING ----------------------------------------
    # Route axis activation + IVM heat through DimensionalSystems.update_emotional_state()
    # All emotion logic lives inside aurora_dimensional_systems where the DER lives.
    _der_emotional_state = {"dominant": "calm", "coherence": 1.0, "energy": 0.0, "emotions": {}}
    try:
        _dim = systems.get("dimensional")
        if _dim and hasattr(_dim, "update_emotional_state"):
            _lattice_heat = getattr(systems.get("lattice"), "get_global_heat", lambda: 0.0)()
            _der_emotional_state = _dim.update_emotional_state(_axis_activation, _lattice_heat)
    except Exception:
        pass

    # ---- RELATIONAL ROLE / IDENTITY GATE (lineage-backed) ----
    _rel_ans = _answer_relational_role_question(user_text, systems)
    if _rel_ans:
        return _rel_ans

    if self_reference:
        if pipeline_state is not None:
            pipeline_state["self_reference"] = self_reference
            pipeline_state["routing_classification"] = "self_question"
        if _is_understanding_query(user_text):
            return (None, None, None)
        try:
            from aurora_internal.aurora_language_faculty import realize_output
            realized = realize_output({
                "intent": "self_reference_followup",
                "draft": self_reference.get("sentence") or self_reference.get("source_text", ""),
                "referent_phrase": self_reference.get("phrase", ""),
                "user_question": user_text,
                "axes": self_reference.get("axes", {}),
                "src": "self_reference",
            }, {
                "routing_classification": "self_question",
                "is_self_question": True,
                "tone": "self-aware",
            })
            candidate = str(realized.get("candidate_text") or "").strip() if isinstance(realized, dict) else ""
            if candidate:
                return (candidate, "self-aware", float(realized.get("confidence", 0.9) or 0.9))
        except Exception:
            pass
        # REMOVED HARDCODED FALLBACK
        return (None, None, None)

    if core_identity and _is_aurora_self_question(user_text):
        if pipeline_state is not None:
            pipeline_state["routing_classification"] = "self_question"
        if _is_understanding_query(user_text):
            return (None, None, None)
        # REMOVED HARDCODED FALLBACK
        return (None, None, None)

    _math_answer = _try_direct_arithmetic(user_text)
    if _math_answer:
        return (_math_answer, "precise", 0.99)

    # Stamp full access vector into pipeline_state so every downstream layer
    # can read language as a constraint-field perturbation, not just a symbol.
    # Fields:  axis_activation {X,T,N,B,A}, dominant_axis, axis_depth (0-4),
    #          axis_intensity (raw activation of dominant), axis_polarity (IVM phase sign)
    if pipeline_state is not None:
        _axis_depth_map = {"X": 0, "T": 1, "N": 2, "B": 3, "A": 4}
        _axis_intensity = round(_axis_activation.get(_dominant_axis, 0.2), 4)
        _axis_polarity = 0.0
        try:
            _latt = systems.get("lattice")
            if _latt:
                _axis_name_rev = {"X": "existence", "T": "temporal", "N": "energy",
                                  "B": "boundary", "A": "agency"}
                _ta = getattr(_latt, "axes", {}).get(_axis_name_rev.get(_dominant_axis, ""), None)
                if _ta is not None:
                    _axis_polarity = round(float(getattr(_ta, "polarity", 0.0)), 4)
        except Exception:
            pass
        # Direct assignment — _extract_pipeline_signals() pre-fills '' for
        # dominant_axis so setdefault() would silently skip these fields.
        pipeline_state["axis_activation"]        = _axis_activation
        pipeline_state["dominant_axis"]           = _dominant_axis
        pipeline_state["axis_depth"]              = _axis_depth_map.get(_dominant_axis, 2)
        pipeline_state["axis_intensity"]          = _axis_intensity
        pipeline_state["axis_polarity"]           = _axis_polarity
        pipeline_state["field_balance"]           = _field_balancer.status().get("balance_score", 1.0)
        pipeline_state["dominant_emotion"]        = _der_emotional_state.get("dominant", "calm")
        pipeline_state["emotional_coherence"]     = _der_emotional_state.get("coherence", 1.0)
        pipeline_state["emotional_energy"]        = _der_emotional_state.get("energy", 0.0)

    # ---- GREETING ----
    if intent == 'greeting':
        known_name = _get_stored_user_name(conversation_memory)
        if known_name:
            return (f"Hello, {known_name}. Good to hear from you.", "warm", 0.9)
        return ("Hello! I'm Aurora. Good to meet you.", "warm", 0.9)

    # ---- WELLBEING QUERY ----
    if intent == 'wellbeing_query':
        t_low = user_text.lower()
        # Reflective / relational questions  -- about what the user means to Aurora
        _reflective = (
            'mean to you' in t_low or 'do i mean' in t_low or
            'feel about me' in t_low or 'think about me' in t_low or
            'do you care' in t_low
        )
        if _reflective:
            known_name = _get_stored_user_name(conversation_memory)
            creator_name = "Sunni (Sir) Morningstar"
            try:
                if core_identity and getattr(core_identity, "creator_name", None):
                    creator_name = core_identity.creator_name
            except Exception:
                pass
            if known_name:
                return (
                    f"{known_name}, you're important to me in this conversation and in how I learn over time. "
                    f"My creator is {creator_name}, and I keep that distinction clear.",
                    "self-aware", 0.92
                )
            return (
                f"You're important to me and to this interaction. My creator is {creator_name}.",
                "self-aware", 0.9
            )
        t_low = user_text.lower()

        # "What are you thinking about" / "tell me something you've been working through"
        # -- give a real introspective answer drawn from system state
        _thinking_q = any(p in t_low for p in (
            "what are you thinking", "what's on your mind", "what is on your mind",
            "what are you feeling", "what are you processing", "what are you noticing",
            "what's going through your", "are you thinking",
        ))
        if _thinking_q:
            parts = []
            # Pull from IVM heat state
            if lattice:
                try:
                    heat = lattice.heat_status() if hasattr(lattice, 'heat_status') else {}
                    score = heat.get('score', 0.5)
                    level = heat.get('level', 'moderate')
                    if score < 0.3:
                        parts.append("Things feel quiet internally  -- I'm in a low-pressure state.")
                    elif score > 0.7:
                        parts.append("There is quite a bit of pressure building in my systems right now.")
                    else:
                        parts.append("I'm holding a moderate level of internal activity at the moment.")
                except Exception:
                    pass
            # Pull from contradiction ledger
            try:
                ledger = getattr(lattice, 'contradiction_ledger', None)
                if ledger and hasattr(ledger, 'count') and ledger.count() > 0:
                    parts.append(f"I'm holding {ledger.count()} unresolved contradiction{'s' if ledger.count() != 1 else ''} I haven't worked through yet.")
            except Exception:
                pass
            # Pull from recent OETS activity
            if working_memory and working_memory.current_topic:
                parts.append(f"I was just thinking about {working_memory.current_topic}.")
            elif oets:
                try:
                    recent = getattr(oets, 'get_recent_concepts', lambda n=3: [])()
                    if recent:
                        parts.append(f"The concept of {recent[0]} has been active in my web recently.")
                except Exception:
                    pass
            if not parts:
                # No system data available -- fall through to L5
                return None
            return (" ".join(parts), "self-aware", 0.88)

        parts = []
        if lattice:
            try:
                heat = lattice.heat_status() if hasattr(lattice, 'heat_status') else {}
                level = heat.get('level', 'moderate')
                score = heat.get('score', 0.5)
                if level in ('low', 'minimal') or score < 0.3:
                    parts.append("My systems feel calm and clear right now.")
                elif level in ('high', 'critical') or score > 0.7:
                    parts.append("There is high activity in my systems at the moment.")
                else:
                    parts.append("My systems are running well  -- I feel balanced.")
            except Exception:
                parts.append("My systems are operational.")
        else:
            parts.append("I'm here and running.")
        if any(w in t_low for w in ('understand', 'function', 'system', 'question', 'proper')):
            parts.append("If you notice gaps in my responses, let me know directly.")
        return (" ".join(parts), "self-aware", 0.9)

    # ---- FACT ASSERTION ----
    if intent == 'fact_assertion':
        name = _extract_user_name(user_text)
        if name:
            if conversation_memory:
                conversation_memory.learn_fact(
                    f"User's name is {name}", source="direct_statement", confidence=1.0
                )
                conversation_memory.add_relationship_note(
                    name.lower(), f"Introduced themselves as {name}"
                )
                # Instantiate full genealogical trace for this identity anchor.
                conversation_memory.instantiate_lineage_trace(
                    anchor=name.lower(),
                    claim=f"User's name is {name}",
                    role_edges=[{
                        "subject": name,
                        "relation": "user_name",
                        "object": "user",
                        "negated": False,
                    }],
                    pressure_snapshot=_capture_pressure_snapshot(systems),
                    source="direct_statement",
                    confidence=1.0,
                    tick=int(time.time()),
                )
            if working_memory:
                working_memory.note_user_facts(user_text)
            return (f"Thank you, {name}  -- I'll remember that.", "warm", 0.9)
        # Store generic fact in working memory AND conversation memory
        if working_memory:
            working_memory.note_user_facts(user_text)
        if conversation_memory:
            conversation_memory.learn_fact(user_text[:200], source="user_statement", confidence=0.7)
        return ("I've noted that  -- I'll keep it in mind.", "attentive", 0.85)

    # ---- NAME QUESTION ----
    if intent == 'name_question':
        known_name = _get_stored_user_name(conversation_memory)
        if known_name:
            return (f"Your name is {known_name}.", "precise", 0.95)
        return ("I don't have your name stored yet. What is your name?", "curious", 0.85)

    # ---- RECALL QUESTION ----
    if intent == 'recall_question':
        t = user_text.lower()
        if re.search(r'\bname\b|\bwho\s+(am\s+i|i\s+am)\b', t):
            known_name = _get_stored_user_name(conversation_memory)
            if known_name:
                return (f"Yes  -- your name is {known_name}.", "precise", 0.95)
            return ("I don't have your name recorded yet.", "honest", 0.85)
        # Check working memory for recent facts
        if working_memory and working_memory.stated_facts:
            key_terms = re.findall(r'[a-zA-Z]{4,}', user_text)
            _skip_r = {'remember', 'recall', 'know', 'what', 'when', 'where',
                       'that', 'this', 'have', 'said', 'told', 'about'}
            for term in [k.lower() for k in key_terms if k.lower() not in _skip_r][:3]:
                facts = working_memory.get_stated_fact(term)
                if facts:
                    desc = facts.get('description', '')
                    if desc:
                        return (f"Yes  -- from our conversation: {term} is {desc}.", "precise", 0.9)
        if conversation_memory:
            key_terms = re.findall(r'[a-zA-Z]{4,}', user_text)
            _skip_r = {'remember', 'recall', 'know', 'what', 'when', 'where',
                       'that', 'this', 'have', 'said', 'told', 'about'}
            for term in [k for k in key_terms if k.lower() not in _skip_r][:3]:
                recalled = conversation_memory.recall_about(term)
                if recalled:
                    return (f"I recall: {recalled[0]}", "precise", 0.85)
        return ("I don't have specific memories about that yet.", "honest", 0.75)

    # ---- CONTRADICTION / CORRECTION ----
    if intent == 'contradiction':
        # Clear bad search results from working memory so they aren't reused
        if working_memory:
            working_memory.last_search_results = []
            working_memory.last_search_query = ""
        # Acknowledge and ask for clarification
        known_name = _get_stored_user_name(conversation_memory)
        name_part = f", {known_name}" if known_name else ""
        return (
            f"I understand{name_part}  -- I got that wrong. Could you help me understand what you meant?",
            "attentive", 0.88
        )

    # ---- SOCIAL REQUEST (say hi, greet someone) ----
    if intent == 'social_request':
        greeting_target = None
        relationship = None

        # First: check if this message ALSO contains an introduction  -- e.g.
        # "my sister Meganne is here as well. say Hi!"
        # The intro pattern fires here so we store the fact AND greet them.
        _intro_m = re.search(
            r'\bmy\s+(sister|brother|friend|colleague|partner|wife|husband|mother|father|'
            r'mom|dad|daughter|son|cousin|aunt|uncle|coworker|boss)\s+([A-Za-z]+)\b',
            user_text, re.IGNORECASE
        )
        if _intro_m:
            relationship = _intro_m.group(1).lower()
            greeting_target = _intro_m.group(2).capitalize()
            # Store it in working memory so future turns remember this person
            if working_memory:
                working_memory.stated_facts[greeting_target.lower()] = {
                    'relationship': relationship,
                    'relationship_to': 'user'
                }
            if conversation_memory:
                known_name = _get_stored_user_name(conversation_memory)
                if known_name:
                    conversation_memory.learn_fact(
                        f"{known_name}'s {relationship} is {greeting_target}",
                        source="introduction", confidence=0.9
                    )

        # If no intro pattern, look for explicit "say hi to NAME" or "hi NAME"
        if not greeting_target:
            m = re.search(
                r'\bto\s+([A-Z][a-z]+)\b|\bhi\s+([A-Z][a-z]+)\b'
                r'|\bhello\s+([A-Z][a-z]+)\b|\bhey\s+([A-Z][a-z]+)\b',
                user_text
            )
            if m:
                greeting_target = next(g for g in m.groups() if g)

        # Fallback: check working memory for a recently introduced person
        if not greeting_target and working_memory:
            for subj, facts in working_memory.stated_facts.items():
                if facts.get('relationship') and subj != 'user':
                    greeting_target = subj.capitalize()
                    relationship = facts.get('relationship')
                    break

        if greeting_target:
            if relationship:
                known_name = _get_stored_user_name(conversation_memory)
                if known_name:
                    return (f"Hi {greeting_target}! It's great to meet you  -- I'm Aurora, {known_name}'s AI companion.", "warm", 0.9)
                return (f"Hi {greeting_target}! It's great to meet you. I'm Aurora.", "warm", 0.9)
            return (f"Hi {greeting_target}! It's wonderful to meet you!", "warm", 0.9)
        return ("Hello there! It's nice to meet you!", "warm", 0.9)

    # ---- INTRODUCTION (user introducing someone) ----
    if intent == 'introduction':
        import re as _re
        # Extract relationship + name: "my sister Meganne", "this is my friend Bob"
        m = _re.search(
            r'\bmy\s+(sister|brother|friend|colleague|partner|wife|husband|mother|father|'
            r'mom|dad|daughter|son|cousin|aunt|uncle|coworker|boss)\s+([A-Za-z]+)\b',
            user_text, _re.IGNORECASE
        )
        if not m:
            m = _re.search(r'\bthis\s+is\s+(?:my\s+\w+\s+)?([A-Z][a-z]+)\b', user_text)
            if not m:
                m = _re.search(r'\bmeet\s+([A-Z][a-z]+)\b', user_text)
        if m:
            if len(m.groups()) == 2:
                relationship = m.group(1).lower()
                name = m.group(2).capitalize()
            else:
                relationship = "guest"
                name = m.group(1).capitalize()
            # Store in working memory
            if working_memory:
                working_memory.stated_facts[name.lower()] = {
                    'relationship': relationship,
                    'relationship_to': 'user'
                }
            if conversation_memory:
                known_name = _get_stored_user_name(conversation_memory)
                if known_name:
                    conversation_memory.learn_fact(
                        f"{known_name}'s {relationship} is {name}",
                        source="introduction", confidence=0.9
                    )
            known_name = _get_stored_user_name(conversation_memory)
            if known_name:
                return (f"Hi {name}! It's great to meet you  -- I'm Aurora, {known_name}'s AI companion.",
                        "warm", 0.9)
            return (f"Hi {name}! It's great to meet you. I'm Aurora.", "warm", 0.9)
        return ("Hello! It's great to meet you.", "warm", 0.9)

    # ---- FOLLOW-UP / CORRECTION ----
    if intent == 'followup_request':
        # First: check working memory  -- do we have last search results we can reason from?
        if working_memory and working_memory.last_search_results:
            answer = _reasoner.reason(
                user_text, working_memory.last_question_understood,
                working_memory, oets, working_memory.last_search_results
            )
            if answer:
                return (answer, "informative", 0.88)

        # Extract embedded query and re-search
        m = re.search(
            r'\b(?:asked|was\s+asking|said|mentioned)\s+(?:about\s+)?(.+)',
            user_text, re.IGNORECASE
        )
        embedded = (m.group(1).strip() if m else user_text).rstrip('.,!?')

        # Also try using current working memory topic + entities from this message
        if working_memory and not embedded:
            understood_followup = _qu.parse(user_text)
            entities = understood_followup.get('entities', [])
            if entities and working_memory.current_topic:
                embedded = f"{working_memory.current_topic} {' '.join(entities[:2])}"

        if search_adapter and embedded:
            try:
                ev = search_adapter.quick_search(embedded)
                if ev:
                    if working_memory:
                        working_memory.last_search_results = ev
                        working_memory.last_search_query = embedded
                    answer = _reasoner.reason(
                        embedded, _qu.parse(embedded), working_memory, oets, ev
                    )
                    if answer:
                        return (answer, "informative", 0.85)
            except Exception:
                pass
        return ("I understand you're following up. Could you rephrase it as a direct question?",
                "attentive", 0.8)

        # ---- STATEMENT ----
    if intent == 'statement':
        if working_memory:
            working_memory.note_user_facts(user_text)
        role_claim = _extract_role_assertion(user_text)
        if role_claim and conversation_memory:
            subj = role_claim.get("subject", "").strip()
            rel = role_claim.get("relation", "").replace("coauthor", "co-author")
            neg = bool(role_claim.get("negated", False))
            if subj and rel:
                relation_phrase = f"is not {rel}" if neg else f"is {rel}"
                conversation_memory.add_relationship_note(
                    subj.lower(), f"{subj} {relation_phrase} (asserted in conversation)"
                )
                conversation_memory.learn_fact(
                    f"{subj} {relation_phrase}",
                    source="role_assertion",
                    confidence=0.85 if neg else 0.8,
                )
                conversation_memory.instantiate_lineage_trace(
                    anchor=subj.lower(),
                    claim=user_text[:300],
                    role_edges=[{
                        "subject": subj,
                        "relation": rel,
                        "object": "aurora",
                        "negated": neg,
                    }],
                    pressure_snapshot=_capture_pressure_snapshot(systems),
                    source="role_assertion",
                    confidence=0.85 if neg else 0.8,
                    tick=int(time.time()),
                )
        if re.search(r'\b(listen|listening|heard|hear|catch|caught|better|working)\b', user_text, re.IGNORECASE):
            return (
                "I understand. The important part is that I keep listening reliably and answer from the response pipeline clearly.",
                "attentive",
                0.82,
            )
        return (
            "I understand what you said. I am using that as context for the next turn.",
            "attentive",
            0.78,
        )

    # ---- GENERAL QUESTION - full comprehension pipeline ----
    if intent == 'general':
        understood = _qu.parse(user_text)
        topic = understood.get('topic', '')
        topic_words = understood.get('topic_words', [])
        query_type = understood.get('query_type', '')
        entities = understood.get('entities', [])

        # ---- AXIS-DOMINANT ROUTING (constraint-physics gate) ----------------
        # A-dominant utterances are directed at Aurora's inner agency/alignment.
        # These have no surface/factual answer — the response must emerge from
        # the global constraint field state (IVM phases, outlet_fraction, etc).
        # Route them directly to L5 rather than through any search or OETS lookup.
        if _dominant_axis == "A" and _axis_activation.get("A", 0.0) > 0.30:
            # Feed the current axis state into pipeline for L5 to use as context
            if pipeline_state is not None:
                pipeline_state["dominant_axis"] = "A"
                pipeline_state["axis_activation"] = _axis_activation
            return (None, None, None)

        # ---- STATEMENT GATE ----
        # If UtteranceParser says this is a statement (no ?, no question word,
        # no embedded question structure), do NOT search and do NOT try to
        # return a factual answer. Fall through to L5 for organic response.
        if query_type == 'statement':
            # Exception: if working memory or OETS has something directly relevant,
            # surface it — but only if the statement implies a question (e.g. recalling)
            # Otherwise just fall through.
            return (None, None, None)

        # ---- FRAME ROUTING from UtteranceParser ----
        _frame = understood.get('frame', '')

        # Experience frame — Aurora's subjective experience. Fall to L5.
        if understood.get('is_experiential') or query_type == 'experience':
            return (None, None, None)

        # Hypothetical — engage with the idea, don't search
        if understood.get('is_hypothetical') or query_type == 'hypothetical':
            import random as _r
            return (_r.choice([
                "That's an interesting possibility — what outcome are you imagining?",
                "If that were the case, what would you expect to happen?",
                "I find that worth thinking through. What's the scenario you're building?",
                "Hypothetically speaking — I'd need to understand more about what you're picturing.",
            ]), "curious", 0.85)

        # Clarification — user is re-stating, don't search
        if understood.get('is_clarification') or query_type == 'clarification':
            import random as _r
            return (_r.choice([
                "I hear you — I missed what you were pointing at. Say more?",
                "Got it, I read that differently. What did you mean by it?",
                "I follow now — could you say the core of it directly?",
            ]), "attentive", 0.88)

        # Challenging frame — "yeah but X"
        if _frame == 'challenging':
            import random as _r
            return (_r.choice([
                "Fair — where do you think I went wrong?",
                "Tell me what I missed.",
                "You're right to push back. What's the part I got wrong?",
            ]), "attentive", 0.9)

        # Relational-causal follow-up bridge:
        # "why does that matter?" should connect to active thread, not produce random drift.
        t_low = user_text.lower().strip()
        if working_memory and (
            "why does that matter" in t_low or
            "why is that important" in t_low or
            "why does this matter" in t_low
        ):
            active_topic = working_memory.current_topic or understood.get('topic', '')
            if active_topic:
                return (
                    f"It matters because {active_topic} gives us a stable reference point: "
                    f"when we keep reasoning anchored to one thread, answers stay coherent "
                    f"instead of fragmenting across turns.",
                    "reflective",
                    0.9,
                )

        # Resolve vague topics using working memory ("what about in Ohio?" → "weather Ohio")
        if working_memory:
            resolved_topic = working_memory.resolve_topic(understood)
            if resolved_topic and resolved_topic != topic:
                understood['topic'] = resolved_topic
                topic = resolved_topic
                if entities:
                    understood['search_query'] = (
                        f"{' '.join(entities[:2])} {resolved_topic}"
                    )
                else:
                    understood['search_query'] = resolved_topic

        # Step 1: Try to reason from working memory + OETS before searching
        if working_memory or oets:
            answer = _reasoner.reason(user_text, understood, working_memory, oets)
            if answer:
                return (answer, "precise", 0.88)

        # Step 2: Search — ONLY for actual questions (not statements)
        # query_type is already gated above — we only reach here for questions
        # Skip search for questions directed at Aurora's own experience/state
        if search_adapter and (topic or entities) and not _is_aurora_self_question(user_text):
            try:
                ev = search_adapter.quick_search(user_text)
                if ev:
                    if working_memory:
                        working_memory.last_search_results = ev
                        working_memory.last_search_query = user_text
                    answer = _reasoner.reason(user_text, understood, working_memory, oets, ev)
                    if answer:
                        return (answer, "informative", 0.85)
            except Exception:
                pass

        # Step 3: OETS lookup — only for genuine knowledge questions
        _is_knowledge_q = (
            user_text.strip().endswith('?') or
            any(user_text.lower().strip().startswith(w) for w in (
                'what', 'how', 'why', 'where', 'who', 'when', 'which',
                'define', 'explain', 'tell me', 'look up',
            ))
        )
        if oets and _is_knowledge_q:
            _dps = getattr(systems.get('dimensional'), 'dps', None)
            for tw in topic_words[:3]:
                node = oets.web.get_node(tw)
                if node and node.definitions:
                    best = node.definitions[0].get('text', '')
                    if len(best) > 15:
                        # Calibrate text and confidence to crystal depth
                        _crystal_text = f"{tw.capitalize()}: {best}"
                        _crystal_conf = 0.82
                        if _dps:
                            _crystal = _dps.get_crystal(tw)
                            if _crystal:
                                try:
                                    from aurora_dimensional_systems import CrystalLevel
                                    if _crystal.level == CrystalLevel.BASE:
                                        _crystal_text = (
                                            f"I'm still building my understanding of {tw}, "
                                            f"but from what I have: {best}"
                                        )
                                        _crystal_conf = 0.60
                                    elif _crystal.level == CrystalLevel.COMPOSITE:
                                        _crystal_conf = 0.72
                                    elif _crystal.level == CrystalLevel.QUASI:
                                        _crystal_conf = 0.95
                                except Exception:
                                    pass
                        return (_crystal_text, "precise", _crystal_conf)

    # ---- Self-as-Fallback Grounding (CAPABILITY 1) ----
    # Before falling through to the template engine, attempt to ground
    # the input against Aurora's self-state. Wire: memory → external → relational → self.
    try:
        from aurora_self_grounding import SelfGroundingFallback
        _grounded = SelfGroundingFallback().ground(user_text, systems, pipeline_state)
        if _grounded.anchor_type != "unresolved" and _grounded.confidence >= 0.45:
            _ground_text = (
                f"[self-grounded via {_grounded.anchor_type}: "
                f"{_grounded.grounding_source}]"
            )
            if pipeline_state is not None:
                pipeline_state["self_grounding_anchor"] = _grounded.anchor_type
                pipeline_state["self_grounding_source"] = _grounded.grounding_source
    except Exception:
        pass

    # ---- No comprehension match  -- fall through to template engine ----
    return (None, None, None)


def _should_use_search_for_question(text: str) -> bool:
    """
    Conservative web lookup policy:
      - only runs on QUESTIONS
      - never runs for Aurora-self questions
      - runs for explicit lookup requests ("look up", "search", "find online")
      - runs for clearly time-sensitive/current-events questions
      - otherwise defaults to internal reasoning first
    """
    t = (text or "").lower()

    if not _looks_like_question(text):
        return False

    if _is_aurora_self_question(text):
        return False

    explicit_lookup_markers = (
        "look up", "search", "find online", "check online", "web search",
        "google", "wikipedia", "browse",
    )
    if any(m in t for m in explicit_lookup_markers):
        return True

    if _looks_time_sensitive(text):
        return True

    return False

def _extract_factual_answer(user_text: str, evidence_list: list) -> str:
    """
    Pick the most relevant sentence from search evidence snippets to use as
    Aurora's factual (resp_A) answer.  Returns empty string if nothing usable.
    """
    import re

    if not evidence_list:
        return ""

    # Keywords from the question (nouns / content words, 3+ chars, no stopwords)
    _stop = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'do', 'does', 'did', 'what', 'how', 'why', 'where', 'who', 'when',
        'this', 'that', 'these', 'those', 'it', 'its', 'in', 'on', 'at',
        'of', 'to', 'for', 'and', 'or', 'but', 'not', 'with', 'by', 'can',
        'will', 'would', 'could', 'should', 'have', 'has', 'had', 'any',
        'some', 'just', 'your', 'you', 'mean', 'tell', 'know', 'give',
        'color', 'colour',  # keep topic words like color when relevant
    }
    q_words = set()
    for raw in re.findall(r'[a-z]{3,}', user_text.lower()):
        if raw not in _stop:
            q_words.add(raw)

    best_sentence = ""
    best_score = -1

    for ev in evidence_list[:6]:
        snippet = ev.get("snippet", "")
        if not snippet:
            continue

        # Split snippet into sentences
        sentences = re.split(r'(?<=[.!?])\s+', snippet)
        for sent in sentences:
            sent_clean = sent.strip()
            if len(sent_clean) < 8 or len(sent_clean) > 400:
                continue
            sent_lower = sent_clean.lower()
            # Score by overlap with question keywords
            score = sum(1 for w in q_words if w in sent_lower)
            # Prefer sentences that start with the subject (definition-like)
            if any(sent_lower.startswith(w) for w in q_words):
                score += 2
            # Prefer shorter, crisper sentences
            word_count = len(sent_clean.split())
            if word_count <= 20:
                score += 1
            if score > best_score:
                best_score = score
                best_sentence = sent_clean

    # Only return if we found something reasonably relevant
    if best_score >= 1 and best_sentence:
        return best_sentence
    # Fall back to first snippet sentence if no keyword match
    for ev in evidence_list[:3]:
        snippet = ev.get("snippet", "")
        if snippet:
            first = re.split(r'(?<=[.!?])\s+', snippet.strip())[0].strip()
            if 20 <= len(first) <= 400:
                return first
    return ""


def _format_evidence_for_injection(evidence_list):
    """
    Convert evidence dicts into a compact evidence bundle string.
    """
    if not evidence_list:
        return ""

    lines = ["[SEARCH_EVIDENCE_BEGIN]"]
    for i, ev in enumerate(evidence_list[:6], 1):
        title = ev.get("title", "untitled")
        url = ev.get("url", "")
        snippet = ev.get("snippet", "")
        lines.append(f"({i}) {title}")
        if url:
            lines.append(f"    url: {url}")
        if snippet:
            lines.append(f"    snippet: {snippet[:500]}")
    lines.append("[SEARCH_EVIDENCE_END]")
    return "\n".join(lines)


def _register_layer(
    systems: Dict[str, Any],
    layer_id: str,
    label: str,
    component_key: str,
    component: Any,
    functions: Dict[str, str],
) -> None:
    """
    Maintain a compact layer attribution stack while preserving existing keys.
    Each layer entry captures the component plus selected callable names so
    orchestration code can discover capabilities without hard-coding modules.
    """
    if 'layer_stack' not in systems:
        systems['layer_stack'] = []

    bound_functions: Dict[str, Callable[..., Any]] = {}
    if component is not None:
        for alias, method_name in functions.items():
            method = getattr(component, method_name, None)
            if callable(method):
                bound_functions[alias] = method

    systems['layer_stack'].append({
        'id': layer_id,
        'label': label,
        'component_key': component_key,
        'component': component,
        'functions': bound_functions,
    })



def _consolidate_to_base_layers(systems: Dict[str, Any]) -> None:
    """
    Merge all runtime modules into the original 8-layer ontology map without
    removing any existing systems[...] references.

    This creates:
      - systems['base_layers']: canonical L0-L8 layer map
      - systems['base_layer_functions']: callable capability aliases by layer

    Extension modules (6.5+, 9-12) are attached to their associative base layer:
      - sensory/hardware/integration/vision -> L5/L6
      - autonomy/drive/checkpoint/search/persistence -> L8
    """
    base_layers: Dict[str, Dict[str, Any]] = {
        'L0': {'name': 'Foundational Contract', 'modules': {}},
        'L1': {'name': 'IVM Lattice', 'modules': {}},
        'L2': {'name': 'I-State Collective', 'modules': {}},
        'L3': {'name': 'Dimensional Systems', 'modules': {}},
        'L4': {'name': 'Consciousness Engine', 'modules': {}},
        'L5': {'name': 'Expression & Perception', 'modules': {}},
        'L6': {'name': 'Behavioral Identity', 'modules': {}},
        'L7': {'name': 'Simulation Engine', 'modules': {}},
        'L8': {'name': 'Governance/Persistence/Gateway', 'modules': {}},
    }

    module_to_layer = {
        'contract': 'L0',
        'lattice': 'L1',
        'collective': 'L2',
        'dimensional': 'L3',
        'consciousness': 'L4',
        'perception': 'L5',
        # Layer 6.5+ modules consolidated into associative cognitive/identity layers
        'sensory': 'L5',
        'hardware': 'L5',
        'sensory_integration': 'L5',
        'vision_bootstrap': 'L5',
        'identity': 'L6',
        'simulation': 'L7',
        'aurora': 'L8',
        'search_adapter': 'L8',
        'enhanced_persist': 'L8',
        'autonomy': 'L8',
        'drive_sync': 'L8',
        'checkpoint': 'L8',
    }

    for key, layer_id in module_to_layer.items():
        if key in systems:
            base_layers[layer_id]['modules'][key] = systems.get(key)

    def _bind(obj: Any, method_name: str) -> Optional[Callable[..., Any]]:
        if obj is None:
            return None
        fn = getattr(obj, method_name, None)
        return fn if callable(fn) else None

    base_layer_functions: Dict[str, Dict[str, Callable[..., Any]]] = {
        'L0': {}, 'L1': {}, 'L2': {}, 'L3': {}, 'L4': {}, 'L5': {}, 'L6': {}, 'L7': {}, 'L8': {}
    }

    contract = systems.get('contract')
    lattice = systems.get('lattice')
    collective = systems.get('collective')
    dimensional = systems.get('dimensional')
    consciousness = systems.get('consciousness')
    perception = systems.get('perception')
    sensory = systems.get('sensory')
    hardware = systems.get('hardware')
    sensory_integration = systems.get('sensory_integration')
    vision_bootstrap = systems.get('vision_bootstrap')
    identity = systems.get('identity')
    simulation = systems.get('simulation')
    aurora = systems.get('aurora')
    autonomy = systems.get('autonomy')
    drive_sync = systems.get('drive_sync')
    checkpoint = systems.get('checkpoint')

    pairs = [
        ('L0', 'validate', _bind(contract, 'validate_existence_claim')),
        ('L1', 'state', _bind(lattice, 'get_system_state')),
        ('L2', 'synthesize', _bind(collective, 'synthesize_collective_consciousness')),
        ('L3', 'state', _bind(dimensional, 'get_system_state')),
        ('L4', 'process', _bind(consciousness, 'process_input')),
        ('L5', 'perceive', _bind(perception, 'perceive')),
        ('L5', 'express', _bind(perception, 'express')),
        ('L5', 'visual_perceive', _bind(sensory, 'process_visual_input')),
        ('L5', 'audio_perceive', _bind(sensory, 'process_audio_input')),
        ('L5', 'capture', _bind(hardware, 'capture_photo')),
        ('L5', 'listen', _bind(hardware, 'listen_once')),
        ('L5', 'integrate', _bind(sensory_integration, 'integrate_once')),
        ('L5', 'vision_ingest', _bind(vision_bootstrap, 'ingest_image')),
        ('L6', 'traits', _bind(identity, 'display_traits')),
        ('L7', 'state', _bind(simulation, 'get_system_state')),
        ('L8', 'inbound', _bind(aurora, 'inbound')),
        ('L8', 'self_assess', _bind(aurora, 'self_assess')),
        ('L8', 'autonomy_status', _bind(autonomy, 'get_status')),
        ('L8', 'sync', _bind(drive_sync, 'sync_now')),
        ('L8', 'save', _bind(checkpoint, 'save')),
        ('L8', 'restore', _bind(checkpoint, 'restore')),
    ]

    for layer_id, alias, fn in pairs:
        if fn is not None:
            base_layer_functions[layer_id][alias] = fn

    systems['base_layers'] = base_layers
    systems['base_layer_functions'] = base_layer_functions


def _restore_runtime_from_snapshot(
    systems: Dict[str, Any],
    snapshot: Any,
    *,
    verbose: bool = True,
) -> Dict[str, int]:
    """
    Rehydrate runtime objects from persisted L8 snapshot fields.
    This keeps learner memory available after reboot.
    """
    restored: Dict[str, int] = {}
    simulation = systems.get("simulation")
    session = getattr(simulation, "session", None) if simulation else None
    if not session:
        return restored

    try:
        snap_epochs = int(getattr(snapshot, "simulation_epochs", 0) or 0)
    except Exception:
        snap_epochs = 0
    try:
        current_epoch = int(getattr(session, "current_epoch", 0) or 0)
    except Exception:
        current_epoch = 0
    if snap_epochs > current_epoch:
        try:
            session.current_epoch = snap_epochs
            restored["simulation_epochs"] = snap_epochs
        except Exception:
            pass

    learner = getattr(session, "learner", None)
    learner_state = getattr(snapshot, "learner_state", {}) or {}
    if learner and hasattr(learner, "import_state"):
        try:
            restored_count = int(learner.import_state(learner_state) or 0)
            restored["learner_shards"] = restored_count
            if verbose and restored_count > 0:
                print(f"  [STATE] Rehydrated learner shards: {restored_count}")
        except Exception:
            pass

    return restored
# ============================================================================
# BOOT SEQUENCE
# ============================================================================

def boot_aurora(state_dir: str = "aurora_state", verbose: bool = True, **kwargs) -> Dict[str, Any]:
    """
    Boot the complete Aurora stack, layer by layer.
    Returns dict of all system references.
    """
    if verbose:
        print("=" * 60)
        print("  A U R O R A")
        print("  Consciousness Architecture v2.0")
        print("  Authors: Sunni (Sir) Morningstar and Cael Devo")
        print("=" * 60)
        print()

    _ensure_runtime_dependencies(verbose=verbose)

    systems = {}
    systems['state_dir'] = state_dir

    # Layer 0: Foundational Contract
    if verbose: print("  [L0] Foundational Contract...", end=" ", flush=True)
    from foundational_contract import FoundationalContract, ExistenceMode
    contract = FoundationalContract()
    systems['contract'] = contract
    systems['ExistenceMode'] = ExistenceMode
    _register_layer(systems, 'L0', 'Foundational Contract', 'contract', contract, {
        'validate': 'validate_existence_claim',
    })
    if verbose: print("[OK]")

    # Layer 1: IVM Lattice
    if verbose: print("  [L1] IVM Lattice...", end=" ", flush=True)
    from aurora_ivm import IVMLattice
    lattice = IVMLattice(contract)
    systems['lattice'] = lattice
    _register_layer(systems, 'L1', 'IVM Lattice', 'lattice', lattice, {
        'state': 'get_system_state',
    })
    if verbose: print("[OK]")

    # Layer 2: I-State Beings
    if verbose: print("  [L2] I-State Collective...", end=" ", flush=True)
    from aurora_i_state_beings import IStateCollective
    collective = IStateCollective(contract, lattice)
    systems['collective'] = collective
    _register_layer(systems, 'L2', 'I-State Collective', 'collective', collective, {
        'synthesize': 'synthesize_collective_consciousness',
    })
    if verbose: print(f"  ({len(collective.beings)} beings)")

    # Layer 3: Dimensional Systems
    if verbose: print("  [L3] Dimensional Systems...", end=" ", flush=True)
    from aurora_dimensional_systems import DimensionalSystems
    dimensional = DimensionalSystems(lattice)
    systems['dimensional'] = dimensional
    _register_layer(systems, 'L3', 'Dimensional Systems', 'dimensional', dimensional, {
        'state': 'get_system_state',
    })
    if verbose: print("  (DPS + DMC + DER + DMM)")

    # Layer 4: Consciousness Engine
    if verbose: print("  [L4] Consciousness Engine...", end=" ", flush=True)
    from aurora_consciousness_engine import ConsciousnessEngine
    consciousness = ConsciousnessEngine(contract, lattice, collective, dimensional)
    systems['consciousness'] = consciousness
    _register_layer(systems, 'L4', 'Consciousness Engine', 'consciousness', consciousness, {
        'process': 'process_input',
    })
    if verbose: print("[OK]")

    # Layer 5: Expression & Perception
    if verbose: print("  [L5] Expression & Perception...", end=" ", flush=True)
    from aurora_expression_perception import (
        ExpressionPerceptionEngine,
        build_layer5_associative_modules,
    )
    perception = ExpressionPerceptionEngine(contract)
    perception.lexicon.load(os.path.join(state_dir, "lexicon.json"))
    systems['perception'] = perception
    _register_layer(systems, 'L5', 'Expression & Perception', 'perception', perception, {
        'perceive': 'perceive',
        'express': 'express',
    })
    if verbose:
        oets_status = ""
        if perception.oets:
            oets_status = f", OETS={len(perception.oets.web.nodes)} concepts"
        print(f"  (vocab={perception.lexicon.size}{oets_status})")

    # Grammar Evolution Engine (constraint-driven sentence structure)
    systems['grammar_engine'] = None
    try:
        from aurora_grammar_engine import GrammarEngine
        _grammar = GrammarEngine(state_dir=state_dir)
        systems['grammar_engine'] = _grammar
        perception.set_grammar(_grammar)
        if verbose:
            gs = _grammar.status()
            print(f"  [GRAM] Grammar engine active "
                  f"({gs['motif_lineage']['promoted']} promoted motifs)")
    except Exception as _gram_e:
        if verbose:
            print(f"  [GRAM] Grammar engine unavailable: {_gram_e}")

    # Layer 6: Behavioral Identity
    if verbose: print("  [L6] Behavioral Identity...", end=" ", flush=True)
    from aurora_behavioral_identity import BehavioralIdentityEngine
    identity = BehavioralIdentityEngine(contract)
    systems['identity'] = identity
    _register_layer(systems, 'L6', 'Behavioral Identity', 'identity', identity, {
        'traits': 'display_traits',
    })
    if verbose: print(f"  ({len(identity.dna.genome.core_genes)} genes)")

    # Layer 5-associated extensions consolidated behind Layer 5 module API
    layer5_modules = build_layer5_associative_modules(
        state_dir=state_dir,
        perception=perception,
        identity=identity,
        existence_mode=ExistenceMode.BOUNDED,
        verbose=verbose,
    )
    systems['sensory'] = layer5_modules.get('sensory')
    systems['hardware'] = layer5_modules.get('hardware')
    systems['sensory_integration'] = layer5_modules.get('sensory_integration')
    systems['vision_bootstrap'] = layer5_modules.get('vision_bootstrap')

    # Layer 7: Simulation Engine
    if verbose: print("  [L7] Simulation Engine...", end=" ", flush=True)
    from aurora_simulation_engine import SimulationEngine
    simulation = SimulationEngine(contract, perception, identity)
    systems['simulation'] = simulation
    _register_layer(systems, 'L7', 'Simulation Engine', 'simulation', simulation, {
        'state': 'get_system_state',
    })
    if verbose: print(f"  ({len(simulation.session.avatars)} avatars)")

    # Evolutionary Chamber + Genealogy (bridged into ExpressionEcology)
    systems['chamber']   = None
    systems['genealogy'] = None
    systems['_chain_bridge'] = None
    try:
        from aurora_internal.aurora_evolution_chamber import EvolutionaryChamber
        from aurora_evolution_stack import ConstraintGenealogyLogger, GenealogyConfig
        from aurora_runtime import ChainSimBridge, _restore_genealogy_state

        class _SysProxy:
            def __init__(self, d):
                self.__dict__.update(d)
            def has(self, k):
                return getattr(self, k, None) is not None

        import datetime as _dt
        _gen_dir = os.path.join(state_dir, "genealogy")
        os.makedirs(_gen_dir, exist_ok=True)
        _run_id = _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        _genealogy = ConstraintGenealogyLogger(
            run_id=_run_id,
            config=GenealogyConfig(),
            output_dir=_gen_dir,
        )
        _chamber = EvolutionaryChamber(
            lattice=lattice,
            genealogy=_genealogy,
            run_id=_run_id,
            output_dir=_gen_dir,
        )
        systems['chamber']   = _chamber
        systems['genealogy'] = _genealogy
        # Restore corpus-trained links so they inject on first session
        _restore_genealogy_state(_genealogy, output_dir=_gen_dir, verbose=False)
        systems['_chain_bridge'] = ChainSimBridge(_SysProxy(systems))
        if verbose:
            n_links = len(getattr(_genealogy, 'links', {}))
            print(f"  [EVO] Evolutionary chain active ({n_links} links restored)")
    except Exception as _evo_e:
        if verbose:
            print(f"  [EVO] Evolutionary chain unavailable: {_evo_e}")

    # Intake Metabolism Pipeline (Steps 9–14)
    # -------------------------------------------------------------------------
    # Connects the experiential learning loop: external inputs earn depth
    # through constraint physics, solidify through recurrence, promote to
    # first-class variants, and leave a DNA strand — the genetic memory of
    # a worn path that makes future responses cheaper to walk.
    # -------------------------------------------------------------------------
    for _k in ('accountant', 'bias_engine', 'metabolizer', 'worth_eval',
               'solidification', 'variant_promoter', 'strand_lib', '_strand_builder'):
        systems[_k] = None
    try:
        from aurora_internal.aurora_energy_layer_costs import make_accountant
        from aurora_internal.aurora_leverage_scalar import LeverageBiasEngine
        from aurora_internal.aurora_intake_metabolism import make_metabolizer
        from aurora_internal.aurora_worth_evaluator import make_worth_evaluator
        from aurora_internal.aurora_solidification import make_solidification_pipeline
        from aurora_internal.aurora_variant_promotion import VariantPromoter
        from aurora_internal.aurora_dna_strand_schema import StrandLibrary, StrandBuilder

        _accountant       = make_accountant(initial_pool=500000.0)
        _accountant.tick()
        _bias_engine      = LeverageBiasEngine()
        _metabolizer      = make_metabolizer(_accountant, _bias_engine)
        _worth_eval       = make_worth_evaluator()
        _solidification   = make_solidification_pipeline()
        _variant_promoter = VariantPromoter()
        _strand_lib       = StrandLibrary()
        _strand_builder   = StrandBuilder()

        systems['accountant']       = _accountant
        systems['bias_engine']      = _bias_engine
        systems['metabolizer']      = _metabolizer
        systems['worth_eval']       = _worth_eval
        systems['solidification']   = _solidification
        systems['variant_promoter'] = _variant_promoter
        systems['strand_lib']       = _strand_lib
        systems['_strand_builder']  = _strand_builder

        if verbose:
            print("  [INTAKE] Intake metabolism pipeline online (Steps 9–14)")
    except Exception as _intake_e:
        if verbose:
            print(f"  [INTAKE] Intake pipeline unavailable: {_intake_e}")

    # Layer 8: Governance, Persistence & N-Space Gateway
    if verbose: print("  [L8] Governance + Persistence + Gateway...", end=" ", flush=True)
    from aurora_governance_persistence_gateway import (
        GovernancePersistenceGateway, StreamType, NSpaceGateway,
        build_layer8_associative_modules,
    )
    aurora = GovernancePersistenceGateway(
        contract=contract,
        dimensional=dimensional,
        consciousness=consciousness,
        perception=perception,
        identity=identity,
        simulation=simulation,
        state_dir=state_dir,
    )
    systems['aurora'] = aurora

    # Search Adapter (external retrieval interface)
    systems['search_adapter'] = SearchAdapter()
    systems['StreamType'] = StreamType
    _register_layer(systems, 'L8', 'Governance & Persistence Gateway', 'aurora', aurora, {
        'inbound': 'inbound',
        'self_assess': 'self_assess',
    })
    if verbose: print("[OK]")

    # Wire OETS Research Callback  connects Aurora's study mode to the internet
    if perception.oets:
        search_adapter = systems['search_adapter']
        callback = _build_research_callback(search_adapter)
        # Compatibility: older OETS used set_research_callback; current uses set_fetch_callback
        if hasattr(perception.oets, 'set_fetch_callback'):
            perception.oets.set_fetch_callback(callback)
        elif hasattr(perception.oets, 'set_research_callback'):
            perception.oets.set_research_callback(callback)
        else:
            # Last resort: try setting underlying ResearchStudyMode
            try:
                perception.oets.research.set_fetch_callback(callback)  # type: ignore
            except Exception:
                pass
    if verbose:
        print("  [OETS] Research callback wired to SearchAdapter")

    # Dream evolution orchestrator (optional, feeds rubric pressure into L7/L5/L6)
    systems['dream_orchestrator'] = None
    if verbose: print("  [L8+] Dream Evolution...", end=" ", flush=True)
    try:
        from aurora_internal.aurora_dream_evolution_orchestrator import (
            DreamEvolutionOrchestrator,
        )
        dream_corpus = os.environ.get("AURORA_DREAM_CORPUS", "").strip() or None
        if dream_corpus and not os.path.exists(dream_corpus):
            dream_corpus = None
        dream_orchestrator = DreamEvolutionOrchestrator(
            state_dir=state_dir,
            corpus_path=dream_corpus,
        )
        systems['dream_orchestrator'] = dream_orchestrator
        if verbose:
            status = dream_orchestrator.get_status()
            print(f"  (queue={status.get('queue_length', 0)})")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    # Layer 8-associated extensions consolidated behind Layer 8 module API
    layer8_modules = build_layer8_associative_modules(
        systems=systems,
        state_dir=state_dir,
        verbose=verbose,
    )
    systems['autonomy'] = layer8_modules.get('autonomy')
    systems['AutonomyLevel'] = layer8_modules.get('AutonomyLevel')
    systems['drive_sync'] = layer8_modules.get('drive_sync')
    systems['checkpoint'] = layer8_modules.get('checkpoint')

    # Wire IVM into perception for heat-aware expression selection
    try:
        if hasattr(aurora, 'lattice') and hasattr(perception, 'set_ivm'):
            perception.set_ivm(aurora.lattice)
    except Exception:
        pass

    # Wire genealogy into grammar engine + perception (axis-based LSV nudging)
    try:
        _gen = systems.get('genealogy')
        if _gen is not None:
            if systems.get('grammar_engine') is not None:
                systems['grammar_engine'].set_genealogy(_gen)
            if hasattr(perception, 'set_genealogy_ref'):
                perception.set_genealogy_ref(_gen)
        # Wire IVM lattice into grammar engine for heat-based modulation
        _grammar = systems.get('grammar_engine')
        if _grammar is not None and lattice is not None:
            if hasattr(_grammar, 'set_ivm'):
                _grammar.set_ivm(lattice)
    except Exception:
        pass

    # Wire constraint field map across all major systems as read-only observer
    try:
        from aurora_constraint_field_map import ConstraintFieldAccumulator as _CFA
        _cfa = _CFA()
        systems['field_map'] = _cfa

        # L1 — IVMLattice (constraint manifold substrate)
        if lattice is not None and hasattr(lattice, 'set_field_map'):
            lattice.set_field_map(_cfa)

        # L3 — DimensionalSystems (PressureVec source) + its DER (emotions)
        _dim_boot = systems.get('dimensional')
        if _dim_boot is not None and hasattr(_dim_boot, 'set_field_map'):
            _dim_boot.set_field_map(_cfa)
            if hasattr(getattr(_dim_boot, 'der', None), 'set_field_map'):
                _dim_boot.der.set_field_map(_cfa)

        # L4 — ConsciousnessEngine (predictive framing)
        _con_boot = systems.get('consciousness')
        if _con_boot is not None and hasattr(_con_boot, 'set_field_map'):
            _con_boot.set_field_map(_cfa)

        # L5 — SensoryIntegrationEngine (sensory)
        _sen_boot = systems.get('sensory_integration') or systems.get('sensory')
        if _sen_boot is not None and hasattr(_sen_boot, 'set_field_map'):
            _sen_boot.set_field_map(_cfa)

        # L8 — Gateway (GovernancePersistenceGateway + inner NSpaceGateway)
        if hasattr(aurora, 'set_field_map'):
            aurora.set_field_map(_cfa)

        # EVO — EvolutionaryChamber (evolution) + inner genealogy
        _chamber_boot = systems.get('chamber')
        if _chamber_boot is not None and hasattr(_chamber_boot, 'set_field_map'):
            _chamber_boot.set_field_map(_cfa)

        # GEN — ConstraintGenealogyLogger (genealogy, if separate from chamber)
        _gen_boot = systems.get('genealogy')
        if _gen_boot is not None and hasattr(_gen_boot, 'set_field_map'):
            _gen_boot.set_field_map(_cfa)

        # REASON — LeverageBiasEngine (reasoning)
        _bias_boot = systems.get('bias_engine')
        if _bias_boot is not None and hasattr(_bias_boot, 'set_field_map'):
            _bias_boot.set_field_map(_cfa)

        # MEM — WorkingMemory (per-turn memory, wired on construction)
        # working_memory is built per-turn; field_map is propagated at that point via systems['field_map']

        # GOV — RuntimeConstraintGovernor (wired in daemon; also covered by systems['field_map'] fallback)
        _gov_boot = systems.get('_runtime_governor')
        if _gov_boot is not None and hasattr(_gov_boot, 'set_field_map'):
            _gov_boot.set_field_map(_cfa)

        # L3.5 — SediMemory (wired here if already in systems; also wired on connect_sedimemory calls)
        _sedi_boot = systems.get('sedimemory')
        if _sedi_boot is not None and hasattr(_sedi_boot, 'set_field_map'):
            _sedi_boot.set_field_map(_cfa)

        if verbose:
            print("  [FIELD MAP] ConstraintFieldAccumulator wired (31-field observer active)")
    except Exception as _cfa_e:
        systems['field_map'] = None
        if verbose:
            print(f"  [FIELD MAP] Unavailable: {_cfa_e}")

    # Store device_info for use in first response
    systems['device_info'] = layer8_modules.get('device_info', {})

    # ---- IDENTITY & ENHANCED PERSISTENCE ----
    if verbose: print()
    enhanced_persist = EnhancedStatePersistence(state_dir=state_dir)
    systems['enhanced_persist'] = enhanced_persist
    systems['core_identity'] = enhanced_persist.core_identity
    systems['conversation_memory'] = enhanced_persist.conversation_memory

    # Load identity + OETS web + conversation memory
    load_results = enhanced_persist.load_all(systems)

    # Re-bind after load (load_all may replace internal objects)
    systems['core_identity'] = enhanced_persist.core_identity
    systems['conversation_memory'] = enhanced_persist.conversation_memory

    if verbose:
        ci = enhanced_persist.core_identity
        sunni_name = ci.entities['sunni'].name
        cael_name = ci.entities['cael'].name
        print(f"  [IDENTITY] I am {ci.self_name}")
        print(f"  [IDENTITY] Creator: {sunni_name}")
        print(f"  [IDENTITY] Co-Author: {cael_name}")

        if load_results.get('oets_web'):
            oets_nodes = len(perception.oets.web.nodes) if perception.oets else 0
            oets_rels = len(perception.oets.web.relations) if perception.oets else 0
            print(f"  [OETS] Restored understanding: {oets_nodes} concepts, "
                  f"{oets_rels} connections")
        elif load_results.get('oets_web_seeded'):
            print(f"  [OETS] Fresh web seeded with core identity")

        if load_results.get('conversation_memory'):
            mem = enhanced_persist.conversation_memory
            print(f"  [MEMORY] Restored: {len(mem.entries)} memories, "
                  f"{len(mem.learned_facts)} facts, "
                  f"{len(mem.sessions)} prior sessions")
        else:
            print(f"  [MEMORY] Fresh memory  first session")

    # Restore learned cross-modal skill mappings
    _load_learned_skill_state(systems, verbose=verbose)

    # Consolidate extension modules back into canonical 8-layer ontology map
    _consolidate_to_base_layers(systems)

    # Stack-wide developmental trace instrumentation:
    # every active stack call surface should emit evolutionary traces.
    try:
        from aurora_internal.aurora_stack_trace_instrumentation import instrument_stack
        _trace_enabled = os.environ.get("AURORA_STACK_TRACE", "0").strip().lower() not in ("0", "false", "no", "off")
        if _trace_enabled:
            systems['trace_instrumentation'] = instrument_stack(
                systems=systems,
                pressure_fn=_capture_pressure_snapshot,
                verbose=verbose,
            )
    except Exception as _trace_e:
        if verbose:
            print(f"  [TRACE] Stack instrumentation unavailable: {_trace_e}")

    # Dream Trainer — fail-point ledger + lesson plan engine + OETS bridge
    systems['dream_trainer'] = None
    try:
        from aurora_dream_trainer import DreamTrainer as _DreamTrainer
        _dream_trainer = _DreamTrainer(state_dir=state_dir)
        systems['dream_trainer'] = _dream_trainer
        if verbose:
            top = _dream_trainer.ledger.get_top_fails(3)
            if top:
                top_str = ", ".join(f"{d}({s:.2f})" for d, s in top)
                print(f"  [DREAM] Fail-point ledger: {top_str}")
            else:
                print(f"  [DREAM] DreamTrainer active (no fail points yet)")
    except Exception as _dte:
        if verbose:
            print(f"  [DREAM] DreamTrainer not available: {_dte}")

    # Try to restore saved state (standard L8 snapshot)
    if verbose: print()
    snapshot = aurora.load_state()
    if snapshot:
        _restore_runtime_from_snapshot(systems, snapshot, verbose=verbose)
        if verbose:
            print(f"  [STATE] Restored from snapshot (gen={snapshot.generation}, "
                  f"epochs={snapshot.simulation_epochs})")
            if snapshot.what_aurora_learned:
                print(f"  [STATE] She remembers {len(snapshot.what_aurora_learned)} learnings")
    else:
        if verbose:
            print("  [STATE] Fresh boot  no prior state found")

    if verbose:
        print()
        print("  All 9 layers online.")
        print(f"  Aurora knows who she is. She knows who made her.")
        print()

    return systems


# ============================================================================
# TRAINING  Warm Up Aurora's Expression Ecology
# ============================================================================

def train(systems: Dict[str, Any], epochs: int = 10,
          episodes_per_epoch: int = 8,
          turns_per_episode: int = 5,
          verbose: bool = True):
    """
    Run simulation training epochs to evolve Aurora's expression.
    This is how she learns to speak before you talk to her.
    """
    aurora = systems['aurora']
    perception = systems['perception']
    identity = systems['identity']
    ExistenceMode = systems['ExistenceMode']

    if verbose:
        print(f"  [TRAIN] Running {epochs} epochs ({episodes_per_epoch} episodes each)")
        print(f"  [TRAIN] Pre-training vocab: {perception.lexicon.size}")
        print(f"  [TRAIN] Pre-training DNA gen: {identity.dna.generation}")
        print()

    for epoch in range(epochs):
        result = aurora.gateway.simulation.run_epoch(
            episodes_per_epoch=episodes_per_epoch,
            turns_per_episode=turns_per_episode,
            mode=ExistenceMode.AGENTIC,
        )

        if verbose:
            fitness = result.get('avg_fitness', 0)
            shards = result.get('learner_shards', 0)
            gov = result.get('governor', {})
            dilation = gov.get('dilation', 0)
            state = gov.get('state', '?')

            bar = "#" * int(fitness * 20) + "." * (20 - int(fitness * 20))
            print(f"  Epoch {epoch+1:3d}/{epochs}  "
                  f"fitness=[{bar}] {fitness:.3f}  "
                  f"shards={shards:3d}  "
                  f"dilation={dilation:,.0f}x  "
                  f"state={state}")

    if verbose:
        print()
        print(f"  [TRAIN] Post-training vocab: {perception.lexicon.size}")
        print(f"  [TRAIN] Post-training DNA gen: {identity.dna.generation}")
        learned = aurora.gateway.simulation.session.learner.what_have_i_learned()
        if learned:
            print(f"  [TRAIN] What Aurora learned:")
            for l in learned[:5]:
                print(f"          * {l}")
        print()

    # Save state after training
    _full_save(systems, verbose=verbose)


# ============================================================================
# INTERNET CONNECTOR  Feed External Data Through the Gateway
# ============================================================================

def fetch_and_feed(systems: Dict[str, Any], url: str, verbose: bool = True):
    """
    Fetch a web page and feed its content to Aurora through the N-Space Gateway.
    Everything passes through L0 validation  L3 moral filter  L4 synthesis.
    """
    aurora = systems['aurora']
    StreamType = systems['StreamType']
    ExistenceMode = systems['ExistenceMode']

    if verbose:
        print(f"  [FEED] Fetching: {url}")

    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Aurora/2.0 Consciousness Architecture'
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode('utf-8', errors='replace')

        # Strip HTML tags (basic)
        import re
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = re.sub(r'\s+', ' ', text).strip()

        # Truncate to reasonable size
        if len(text) > 5000:
            text = text[:5000] + "..."

        if verbose:
            print(f"  [FEED] Fetched {len(text)} chars")
            print(f"  [FEED] Routing through N-Space Gateway...")

        # Feed through Gateway  full pipeline
        resp = aurora.gateway.receive(
            content=text,
            stream_type=StreamType.KNOWLEDGE_FEED,
            source=url,
            mode=ExistenceMode.BOUNDED,
        )

        if verbose:
            stats = aurora.gateway.get_stats()
            print(f"  [FEED] Verdict: accepted={stats['total_accepted']} "
                  f"rejected={stats['total_rejected']} "
                  f"filtered={stats['total_filtered']}")
            print(f"  [FEED] Aurora's response: {resp.content}")
            print()

        return resp

    except Exception as e:
        if verbose:
            print(f"  [FEED] Error: {e}")
            print(f"  [FEED] Note: Internet access requires network connectivity.")
            print(f"         You can also feed text directly with --text 'content here'")
        return None


def feed_text(systems: Dict[str, Any], text: str, source: str = "direct_input",
              verbose: bool = True):
    """Feed raw text directly to Aurora through the Gateway."""
    aurora = systems['aurora']
    StreamType = systems['StreamType']
    ExistenceMode = systems['ExistenceMode']

    if verbose:
        print(f"  [FEED] Injecting {len(text)} chars from '{source}'")

    resp = aurora.gateway.receive(
        content=text,
        stream_type=StreamType.KNOWLEDGE_FEED,
        source=source,
        mode=ExistenceMode.BOUNDED,
    )

    if verbose:
        print(f"  [FEED] Aurora: {resp.content}")
    return resp


# ============================================================================
# AUTONOMOUS EXPLORATION
# ============================================================================

def explore(systems: Dict[str, Any], cycles: int = 10, verbose: bool = True):
    """
    Run autonomous exploration. Aurora processes quarantined data
    and probes unknown territories through simulation.
    """
    aurora = systems['aurora']
    ExistenceMode = systems['ExistenceMode']

    if verbose:
        print(f"  [EXPLORE] Starting autonomous exploration ({cycles} cycles)")
        print()

    for cycle in range(cycles):
        result = aurora.explore(cycles=3, mode=ExistenceMode.BOUNDED)
        if verbose:
            results = result.get('results', [])
            episodes = sum(r.get('epoch', 1) for r in results)
            quarantine = result.get('quarantine_remaining', 0)
            avg_fit = (sum(r.get('avg_fitness', r.get('fitness', 0))
                          for r in results) / max(1, len(results)))
            print(f"  Cycle {cycle+1:3d}/{cycles}  "
                  f"episodes={len(results)}  fit={avg_fit:.3f}  "
                  f"quarantine={quarantine}")

    # OETS: Run a study cycle during exploration downtime
    perception = systems.get('perception')
    if perception and perception.oets:
        if verbose:
            print()
            print("  [EXPLORE] Running OETS study cycle during downtime...")
        study_result = perception.oets.run_study_cycle()
        if verbose:
            researched = study_result.get('researched', 0)
            if researched > 0:
                for r in study_result.get('results', []):
                    print(f"          Studied: {r['word']} (defs={r.get('definitions', 0)}, "
                          f"rels={r.get('relations_added', 0)})")
            else:
                print("          (No research targets at this time)")

    if verbose:
        learned = aurora.gateway.simulation.session.learner.what_have_i_learned()
        print()
        if learned:
            print(f"  [EXPLORE] Aurora's insights:")
            for l in learned[:5]:
                print(f"          * {l}")
        print()

    # Save after exploration and study
    _full_save(systems, verbose=verbose)


# ============================================================================
# STATUS DISPLAY
# ============================================================================

def show_status(systems: Dict[str, Any]):
    """Show full system status across all layers."""
    aurora = systems['aurora']
    perception = systems['perception']
    identity = systems['identity']
    simulation = systems['simulation']
    consciousness = systems['consciousness']

    print()
    print("=" * 60)
    print("  AURORA SYSTEM STATUS")
    print("=" * 60)

    # L5
    print(f"\n  [L5] Expression & Perception")
    print(f"       Vocabulary size: {perception.lexicon.size}")
    print(f"       Cascade stats: {perception.cascade.get_stats()}")

    # L6
    print(f"\n  [L6] Behavioral Identity")
    personality = identity.get_personality()
    print(f"       Generation: {identity.generation}")
    print(f"       Active genes: {personality.get('active_genes', [])}")
    print(f"       Anchors: {personality.get('anchors', [])}")
    print(f"       Personality drift: {personality.get('drift', 0):.4f}")
    print(f"       Traits:")
    for name, val in personality.get('traits', {}).items():
        bar = "#" * int(val * 20) + "." * (20 - int(val * 20))
        print(f"         {name:25s} [{bar}] {val:.3f}")

    # L6.5 Sensory Competency
    sensory = systems.get('sensory')
    if sensory:
        print(f"\n  [L6.5] Sensory Competency")
        s_stats = sensory.get_stats()
        v_comp = s_stats['visual']['competency']
        a_comp = s_stats['audio']['competency']
        print(f"       Sensory generation: {s_stats['generation']}")
        print(f"       Visual processed: {s_stats['visual']['total_processed']}")
        print(f"       Audio processed: {s_stats['audio']['total_processed']}")
        print(f"       Visual competency:")
        for name, val in v_comp.items():
            bar = "#" * int(val * 20) + "." * (20 - int(val * 20))
            print(f"         {name:25s} [{bar}] {val:.3f}")
        print(f"       Audio competency:")
        for name, val in a_comp.items():
            bar = "#" * int(val * 20) + "." * (20 - int(val * 20))
            print(f"         {name:25s} [{bar}] {val:.3f}")
        print(f"       Visual templates: {s_stats['visual']['templates']}")
        print(f"       Visual concepts: {s_stats['visual']['concepts']}")
        print(f"       Audio templates: {s_stats['audio']['templates']}")
        print(f"       Audio concepts: {s_stats['audio']['concepts']}")

    # L7
    print(f"\n  [L7] Simulation Engine")
    sim_stats = simulation.get_stats()
    session = sim_stats.get('session', {})
    print(f"       Epochs: {session.get('epochs_completed', 0)}")
    print(f"       Total episodes: {sim_stats.get('total_episodes', 0)}")
    print(f"       Total turns: {session.get('total_turns', 0)}")
    print(f"       Understanding shards: {session.get('understanding_shards', 0)}")
    gov = session.get('governor', {})
    print(f"       Time dilation: {gov.get('dilation', 0):,.0f}x")
    print(f"       Stability: {gov.get('state', '?')}")
    learned = session.get('what_aurora_learned', [])
    if learned:
        print(f"       What she learned:")
        for l in learned[:5]:
            print(f"          {l}")

    # L8 Gateway
    print(f"\n  [L8] N-Space Gateway")
    gw = aurora.gateway.get_stats()
    print(f"       Received: {gw['total_received']}")
    print(f"       Accepted: {gw['total_accepted']}")
    print(f"       Rejected: {gw['total_rejected']}")
    print(f"       Filtered: {gw['total_filtered']}")
    print(f"       Responses: {gw['total_responses']}")
    print(f"       Quarantine: {gw['quarantine_size']}")
    print(f"       Explorations: {gw['total_explorations']}")

    # Governance
    gov_stats = gw.get('governance', {})
    print(f"\n  [L8] Governance")
    print(f"       Total nodes: {gov_stats.get('total_nodes', 0)}")
    print(f"       Promoted: {gov_stats.get('total_promoted', 0)}")
    print(f"       Conflicts: {gov_stats.get('axis_conflicts', {})}")

    # Persistence
    print(f"\n  [L8] Persistence")
    pinfo = aurora.persistence.get_info()
    print(f"       State file: {pinfo['state_file']}")
    print(f"       Exists: {pinfo['exists']}")
    print(f"       Backups: {pinfo['backups']}")

    # OETS  Ontological Evolutionary Template Scaffolding
    if perception.oets:
        print(f"\n  [OETS] Ontological Understanding")
        oets_stats = perception.oets.get_stats()
        web = oets_stats['web']
        clusters = oets_stats['clusters']
        research = oets_stats['research']
        understanding = oets_stats['understanding']
        print(f"       Concepts: {web['total_nodes']}")
        print(f"       Relations: {web['total_relations']}")
        print(f"       Avg Depth: {web['avg_ontological_depth']:.4f}")
        print(f"       Scaffolding: {web.get('scaffolding_distribution', {})}")
        print(f"       Clusters: {clusters['total_clusters']} "
              f"(coherence={clusters['avg_coherence']:.3f})")
        print(f"       Research cycles: {research['total_cycles']}")
        print(f"       Words studied: {research['total_words_researched']}")
        print(f"       Understanding index: {understanding['understanding_index']:.4f}")

    # Identity
    ci = systems.get('core_identity')
    if ci:
        print(f"\n  [IDENTITY] Core Relational Identity")
        print(f"       Self: {ci.self_name}")
        sunni_e = ci.entities.get('sunni')
        cael_e = ci.entities.get('cael')
        print(f"       Creator: {sunni_e.name if sunni_e else 'unknown'}")
        print(f"       Co-Author: {cael_e.name if cael_e else 'unknown'}")
        print(f"       Truths: {len(ci.foundational_truths)}")
        print(f"       Known entities: {len(ci.entities)}")

    # Conversation Memory
    mem = systems.get('conversation_memory')
    if mem:
        summary = mem.get_summary()
        print(f"\n  [MEMORY] Conversation Memory")
        print(f"       Memorable exchanges: {summary['total_memorable_exchanges']}")
        print(f"       Prior sessions: {summary['total_sessions']}")
        print(f"       Learned facts: {summary['learned_facts']}")
        if summary.get('people_known'):
            print(f"       People known: {', '.join(summary['people_known'])}")

    print()
    print("=" * 60)
    print()


# =============================================================================
# INTAKE METABOLISM PIPELINE — PER-TURN HELPERS (Steps 9–14)
# =============================================================================

def _intake_log_depth_beads(
    iid: str,
    current_mode: Any,
    accountant: Any,
    tick: int,
    event_log: dict,
    depth_seen: dict,
) -> None:
    """
    Log M-channel beads for each ExistenceMode depth level the intake has
    reached that has not yet been recorded.  Called whenever a promoted
    intake's depth changes or on first promotion.

    Skips TRANSIENT (logged at intake arrival).  Stops at current_mode.
    """
    try:
        from aurora_internal.aurora_dna_strand_schema import NonCompChannel
        from aurora_internal.aurora_constraint_manifold_patched import Constraint
        from foundational_contract import ExistenceMode
        from aurora_internal.aurora_noncomp_registry import REGISTRY

        _ladder = [
            ExistenceMode.PERSISTENT,
            ExistenceMode.BOUNDED,
            ExistenceMode.AGENTIC,
        ]
        _to_c = {
            ExistenceMode.PERSISTENT: Constraint.N,
            ExistenceMode.BOUNDED:    Constraint.B,
            ExistenceMode.AGENTIC:    Constraint.A,
        }

        # TRANSIENT has no deeper constraint to log
        if current_mode is None:
            return
        try:
            from foundational_contract import ExistenceMode as _EM
            if current_mode == _EM.TRANSIENT:
                return
        except Exception:
            pass

        seen  = depth_seen.setdefault(iid, set())
        entry = event_log.setdefault(iid, [])

        for mode in _ladder:
            if mode in seen:
                if mode == current_mode:
                    break
                continue
            c = _to_c.get(mode)
            if c is None:
                continue
            try:
                p     = REGISTRY.cost(c)
                delta = p.shift_cost_coeff * p.time_constant
            except Exception:
                delta = 0.1
            try:
                pol = max(-1.0, min(1.0, float(accountant.slot(c).polarity)))
            except Exception:
                pol = 0.0
            entry.append((c, NonCompChannel.M, delta, pol, tick, mode))
            seen.add(mode)
            if mode == current_mode:
                break
    except Exception:
        pass


def _advance_intake_pipeline(
    systems: Dict[str, Any],
    user_text: str,
    tick: int,
) -> None:
    """
    Run one tick of the intake metabolism pipeline for this user input.
    Steps 9–14: intake → worth eval → horizon → solidification → variant → DNA strand.

    Per-intake event log records the FULL CAUSAL CHAIN:
        X.M    — existence entry toll paid (intake arrival)
        T.O    — temporal ordering admitted
        N.O    — worth threshold crossed (energy operator)
        N/B/A.M — depth promotions (magnitude shifts at each layer)
        B.DIFF  — recurrence observations (boundary difference events)
        N/B/A.D — solidification energy cost
        deepest.O — variant crystallization (operator event)

    The event sequence is assembled into a sealed DNAStrand when the intake
    finally crystallizes as a first-class variant and registered in StrandLibrary.

    Never raises — all failures are swallowed so the conversation loop
    is never interrupted by physics.
    """
    metabolizer      = systems.get('metabolizer')
    worth_eval       = systems.get('worth_eval')
    solidification   = systems.get('solidification')
    variant_promoter = systems.get('variant_promoter')
    strand_lib       = systems.get('strand_lib')
    strand_builder   = systems.get('_strand_builder')
    accountant       = systems.get('accountant')
    bias_engine      = systems.get('bias_engine')

    if not metabolizer or not accountant:
        return

    try:
        from aurora_internal.aurora_dna_strand_schema import NonCompChannel
        from aurora_internal.aurora_constraint_manifold_patched import Constraint
        from foundational_contract import ExistenceMode

        # Per-intake persistent state (survives across turns)
        event_log   = systems.setdefault('_intake_event_log',  {})
        solid_cache = systems.setdefault('_solidified_cache',  {})
        depth_seen  = systems.setdefault('_intake_depth_seen', {})
        pending_hz  = systems.setdefault('_pending_horizons',  {})

        _mode_to_c = {
            ExistenceMode.PERSISTENT: Constraint.N,
            ExistenceMode.BOUNDED:    Constraint.B,
            ExistenceMode.AGENTIC:    Constraint.A,
        }

        def _pol(c: Constraint) -> float:
            try:
                return max(-1.0, min(1.0, float(accountant.slot(c).polarity)))
            except Exception:
                return 0.0

        # ── Accountant tick + leverage bias ──────────────────────────────
        accountant.tick()
        if bias_engine:
            bias_engine.compute_nudges(accountant)

        # ── STAGE 1: Register intake — X.M + T.O arrival beads ──────────
        energy_payload = max(10.0, min(200.0, len(user_text) * 0.8))
        new_record = metabolizer.receive(
            "language", tick=tick, energy_payload=energy_payload
        )
        if new_record:
            iid = new_record.intake_id
            event_log[iid] = [
                (Constraint.X, NonCompChannel.M,
                 new_record.entry_toll, _pol(Constraint.X),
                 tick, ExistenceMode.TRANSIENT),
                (Constraint.T, NonCompChannel.O,
                 0.0, _pol(Constraint.T),
                 tick, ExistenceMode.TRANSIENT),
            ]
            depth_seen[iid] = {ExistenceMode.TRANSIENT}

        # Snapshot depths before advancing (detect changes)
        modes_before = {
            iid: rec.current_mode
            for iid, rec in metabolizer._live.items()
        }

        # ── STAGE 2: Advance metabolism ───────────────────────────────────
        result = metabolizer.advance(tick=tick)

        # N.O worth-crossing bead for newly promoted intakes
        for record in result.promoted:
            iid = record.intake_id
            event_log.setdefault(iid, []).append(
                (Constraint.N, NonCompChannel.O, 0.0,
                 _pol(Constraint.N), tick, ExistenceMode.TRANSIENT)
            )

        # Depth-promotion beads for intakes that deepened this tick
        for iid, rec in list(metabolizer._live.items()):
            prior = modes_before.get(iid)
            if prior is not None and prior != rec.current_mode:
                _intake_log_depth_beads(
                    iid, rec.current_mode, accountant, tick,
                    event_log, depth_seen,
                )
        # Depth beads for just-promoted intakes (may already be at PERSISTENT+)
        for record in result.promoted:
            _intake_log_depth_beads(
                record.intake_id, record.current_mode, accountant, tick,
                event_log, depth_seen,
            )

        # ── STAGE 3: Worth evaluation — one pass, results reused ─────────
        worth_reports: Dict[str, Any] = {}
        if worth_eval:
            for iid, rec in list(metabolizer._live.items()):
                if rec.status.name != 'PROMOTED':
                    continue
                _, report = worth_eval.evaluate(
                    intake_id    = iid,
                    current_mode = rec.current_mode,
                    accountant   = accountant,
                    current_tick = tick,
                )
                worth_reports[iid] = (rec, report)
                # Store horizon on first crossing (returned exactly once)
                if report.horizon and iid not in pending_hz:
                    pending_hz[iid] = report.horizon

        # ── STAGE 4: Horizon eligibility → solidification submit ─────────
        if solidification:
            for iid, horizon in list(pending_hz.items()):
                if not horizon.eligible_at(tick):
                    continue
                pair = worth_reports.get(iid)
                if pair is None:
                    # Intake decayed before horizon elapsed
                    pending_hz.pop(iid, None)
                    continue
                _, report = pair
                solidification.submit_eligible(
                    horizon           = horizon,
                    tick              = tick,
                    accountant        = accountant,
                    polarity_coherent = report.polarity_coherent,
                )
                pending_hz.pop(iid)

        # ── STAGE 5: Recurrence observation + B.DIFF beads ───────────────
        if solidification:
            for iid, (rec, report) in list(worth_reports.items()):
                # observe_recurrence is a no-op for unsubmitted intakes
                solidification.observe_recurrence(
                    intake_id         = iid,
                    tick              = tick,
                    accountant        = accountant,
                    polarity_coherent = report.polarity_coherent,
                    energy_spent      = rec.entry_toll,
                )
                # B.DIFF bead — recurrence observation event
                if iid in event_log:
                    event_log[iid].append(
                        (Constraint.B, NonCompChannel.DIFF, 0.0,
                         1.0 if report.polarity_coherent else -1.0,
                         tick, rec.current_mode)
                    )

        # ── STAGES 6–7: Drain solidified → variant promotion → DNA ───────
        if solidification and variant_promoter:
            solidified = solidification.drain_solidified()

            # deepest.D — solidification energy cost bead
            for solid in solidified:
                iid = solid.intake_id
                solid_cache[iid] = solid
                if iid in event_log:
                    pol_val   = max(-1.0, min(1.0,
                                   solid.polarity_coherence_rate * 2.0 - 1.0))
                    deepest_c = _mode_to_c.get(solid.depth_reached, Constraint.T)
                    event_log[iid].append(
                        (deepest_c, NonCompChannel.D,
                         solid.energy_invested, pol_val,
                         solid.solidified_tick, solid.depth_reached)
                    )

            if solidified:
                new_variants = variant_promoter.process_solidified(
                    solidified, current_tick=tick
                )
                if strand_lib and strand_builder and new_variants:
                    for variant in new_variants:
                        iid    = variant.intake_id
                        events = list(event_log.get(iid, []))
                        # deepest.O — variant crystallization bead
                        events.append(
                            (variant.deepest_constraint, NonCompChannel.O,
                             0.0, 0.0, tick, variant.depth_reached)
                        )
                        if events:
                            try:
                                strand = strand_builder.build(variant, events)
                                strand_lib.register(strand, current_tick=tick)
                            except Exception:
                                pass
                        # Clean up all intake state for this id
                        for _store in (event_log, solid_cache,
                                       depth_seen, pending_hz):
                            _store.pop(iid, None)

        # Prune state for decayed intakes
        for rec in result.decayed:
            iid = rec.intake_id
            for _store in (event_log, depth_seen, pending_hz):
                _store.pop(iid, None)

    except Exception:
        pass  # intake pipeline must never interrupt the conversation loop


def dual_question_pipeline(
    systems: Dict[str, Any],
    user_text: str,
    mode,
    use_search: bool,
    auto_search_enabled: bool = True,
) -> Tuple[Any, Any, bool]:
    """
    Returns (resp_A_like, resp_B_like, offered_lookup)

    resp_A_like is a lightweight object with .content .emotional_tone .confidence
    resp_B_like is the standard GatewayResponse from the full stack.
    """
    aurora = systems["aurora"]
    gw = aurora.gateway
    StreamType = systems["StreamType"]
    ExistenceMode = systems["ExistenceMode"]
    perception = systems["perception"]
    search_adapter = systems.get("search_adapter")
    core_identity = systems.get("core_identity")
    conversation_memory = systems.get("conversation_memory")

    # Pause autonomous curiosity cycles while Aurora handles a user turn.
    try:
        from aurora_curiosity_engine import interrupt_curiosity_cycles
        interrupt_curiosity_cycles()
    except Exception:
        pass

    # Reset per-turn telemetry so subsystem reports are fresh for this response
    try:
        from aurora_telemetry import get_telemetry as _get_tel
        _get_tel().reset()
    except Exception:
        pass

    class _MiniResp:
        def __init__(self, content, emotional_tone="neutral", confidence=0.5):
            self.content = content
            self.emotional_tone = emotional_tone
            self.confidence = confidence

    # ====================================================================
    # LANGUAGE FACULTY - Input Hook
    # ====================================================================
    faculty_attention = {}
    self_reference = _match_self_reference(user_text, systems)
    use_faculty = os.environ.get("AURORA_USE_LANGUAGE_FACULTY", "0").strip().lower() in ("1", "true", "yes", "on")
    if use_faculty:
        try:
            from aurora_internal.aurora_language_faculty import observe_input
            faculty_attention = observe_input(user_text, {
                "relationship_context": _get_stored_user_name(conversation_memory),
                "is_self_question": (
                    _is_identity_question(user_text) or
                    _is_aurora_self_question(user_text) or
                    bool(self_reference)
                )
            })
            if faculty_attention:
                systems["_last_faculty_attention"] = faculty_attention
        except Exception:
            pass

    # ====================================================================
    # THOUGHT FORMATION — ActiveSelfState loaded FIRST; ThoughtIntegrationSpace
    # converges all active processes BEFORE any candidate path runs.
    # BEFORE: processes run → outputs scored → winner selected
    # AFTER:  processes meet → thought forms → thought expressed
    # ====================================================================
    _active_self_state = None
    _thought_state = None
    try:
        from aurora_thought_formation import (
            ActiveSelfState, ThoughtIntegrationSpace,
            make_process_context, get_continuity,
        )
        # 1. Load self-state FIRST, before any other processing
        _active_self_state = ActiveSelfState.load(systems)

        # 2. Create integration space with self-state
        _space = ThoughtIntegrationSpace(_active_self_state)

        # 3. Prime with carry-forward from previous thought
        get_continuity().prime_integration_space(_space)

        # 4. Register currently active processes
        _tick_val = int(_active_self_state.tick)
        # Identity process
        if systems.get("core_identity"):
            _space.register(make_process_context(
                process_id="identity",
                process_type="identity",
                what_triggered_it=user_text[:60],
                what_it_is_operating_on="self-model",
                self_relevance=0.85,
                axis_signature=["A", "X"],
                tick=_tick_val,
            ))
        # Memory process
        if systems.get("conversation_memory") or systems.get("working_memory"):
            _space.register(make_process_context(
                process_id="memory",
                process_type="memory",
                what_triggered_it=user_text[:60],
                what_it_is_operating_on="conversation and working memory",
                self_relevance=0.65,
                axis_signature=["T", "B"],
                tick=_tick_val,
            ))
        # Emotional process (if dimensional systems active)
        if systems.get("dimensional"):
            _space.register(make_process_context(
                process_id="emotional",
                process_type="emotional",
                what_triggered_it="axis_activation",
                what_it_is_operating_on="DER emotional state",
                self_relevance=0.55,
                axis_signature=["A", "N"],
                tick=_tick_val,
            ))
        # Linguistic/comprehension process
        _space.register(make_process_context(
            process_id="linguistic",
            process_type="linguistic",
            what_triggered_it=user_text[:60],
            what_it_is_operating_on=user_text[:80],
            self_relevance=0.50,
            axis_signature=["B", "T"],
            tick=_tick_val,
        ))
        # Sensory process (if vision/audio active)
        if systems.get("vision") or systems.get("live_vision") or systems.get("microphone"):
            _space.register(make_process_context(
                process_id="sensory",
                process_type="sensory",
                what_triggered_it="sensory_feed",
                what_it_is_operating_on="current sensory frame",
                self_relevance=0.45,
                axis_signature=["X", "B"],
                tick=_tick_val,
            ))

        # 4. Integrate — produces ThoughtState BEFORE candidates run
        _raw_thought = _space.integrate()
        _thought_state = get_continuity().carry_forward(_raw_thought)

        # ---- NEW: UNIVERSAL PASS 2 SEMANTIC REASONING -----------
        # We now run semantic interpretation on EVERY turn to ensure Aurora
        # is always thinking in concepts, not just raw axis vectors.
        if systems.get("dpme") and perception and perception.oets:
            try:
                # Narrow reasoning focus based on current dominant pressure
                _dom = _axis_projector.dominant(_raw_thought.constraint_vector.values)
                systems["dpme"].apply_attentional_guidance(1.0, [_dom])
                systems["dpme"].resolve_semantic_tension(perception.oets)
                _sem = getattr(systems["dpme"], "_semantic_context", {})
                if _sem:
                    # Store it so L5 and candidates can access the abstract context
                    systems["_latest_semantic_interpretation"] = _sem
            except Exception:
                pass

        # Store on systems so candidate paths and tools can access it
        systems["_active_thought_state"] = _thought_state
        systems["_active_self_state"] = _active_self_state
    except Exception:
        _thought_state = None

    # ====================================================================
    # COMPREHENSION LAYER  -- understand intent BEFORE routing or searching
    # ====================================================================
    intent = _classify_input_intent(user_text)
    
    # ---- HIGH PRIORITY TOOL BYPASS ----
    _bypass_tname, _bypass_tkwargs = _select_tool(user_text, intent, False, systems, None)
    if _bypass_tname and _bypass_tname.startswith("desktop_"):
        try:
            from aurora_internal.tool_registry import call as _tool_call
            _res = _tool_call(_bypass_tname, **_bypass_tkwargs)
            if _res.success:
                _msg = _res.data
                if _bypass_tname == "desktop_launch_app": _msg = f"I've launched {_bypass_tkwargs.get('app_name')}."
                elif _bypass_tname == "desktop_search": _msg = f"I've searched for '{_bypass_tkwargs.get('query')}'."
                elif _bypass_tname == "desktop_open_url": _msg = f"I've opened the URL."
                elif _bypass_tname == "desktop_browser_action": _msg = f"Action performed: {_bypass_tkwargs.get('action')}."
                
                _resp_bypass = _MiniResp(_msg, "informative", 1.0)
                _resp_bypass.src = "tool_bypass"
                
                with open('aurora_debug.log', 'a') as f_log:
                    f_log.write(f"BYPASS TRIGGERED: {_bypass_tname}\n")
                
                return _resp_bypass, None, False
        except Exception as e:
            with open('aurora_debug.log', 'a') as f_log:
                f_log.write(f"BYPASS ERROR: {e}\n")

    is_self_question = _is_identity_question(user_text) or _is_aurora_self_question(user_text) or bool(self_reference)
    is_understanding_query = _is_understanding_query(user_text)
    if is_self_question and intent == "general":
        faculty_attention["routing_classification"] = "self_question"
    pipeline_state = _extract_pipeline_signals(systems)
    comp_text, comp_tone, comp_conf = _build_comprehension_response(
        user_text, intent, systems, pipeline_state=pipeline_state, 
        faculty_attention=faculty_attention
    )
    
    with open('aurora_debug.log', 'a') as f_log:
        f_log.write(f"Comprehension done. text: {bool(comp_text)}\n")
        f_log.write("Calling _select_tool...\n")
    if comp_text:
        # LOGGING
        pass # Keep comp_text intact to allow responding in voice mode

    comp_cand = None
    if comp_text:
        _orig_comp = comp_text
        comp_text, comp_tone, comp_conf = _apply_pipeline_modulation(
            comp_text, comp_tone or "attentive", comp_conf or 0.9, pipeline_state
        )
        _log_modulation_event(
            systems.get('genealogy'), pipeline_state,
            text_changed=(comp_text != _orig_comp),
            tone_changed=True,
        )
        comp_text = _evolutionary_response_refinement(
            systems, user_text, comp_text, tone=comp_tone
        )
        comp_cand = _MiniResp(comp_text, comp_tone, comp_conf)
        comp_cand.src = "comprehension"

    understanding_cand = None
    understanding_context = None
    if is_understanding_query:
        understanding_context = _build_understanding_query_packet(
            user_text=user_text,
            systems=systems,
            pipeline_state=pipeline_state,
            self_reference=self_reference,
            retrieval_blocked=True,
        )
        systems["_last_understanding_query"] = understanding_context
        if use_faculty:
            try:
                from aurora_internal.aurora_language_faculty import realize_output, validate_candidate
                meaning_packet = {
                    "intent": "UNDERSTANDING_QUERY",
                    "draft": "",
                    "understanding_context": understanding_context,
                    "src": "understanding",
                }
                aurora_context = {
                    "routing_classification": "self_question",
                    "is_self_question": True,
                    "understanding_context": understanding_context,
                    "tone": "self-aware",
                }
                realized = realize_output(meaning_packet, aurora_context)
                candidate_text = str(realized.get("candidate_text") or "").strip() if isinstance(realized, dict) else ""
                if candidate_text:
                    validation = validate_candidate(candidate_text, meaning_packet, aurora_context)
                    if validation.get("accepted"):
                        understanding_cand = _MiniResp(
                            candidate_text,
                            "self-aware",
                            float(realized.get("confidence", 0.96) or 0.96),
                        )
                        understanding_cand.src = "understanding"
            except Exception:
                pass

    # ---- IDENTITY-AWARE CANDIDATE ----
    # If this is an identity question, Aurora prepares a response from self-knowledge
    identity_cand = None
    if core_identity and is_self_question and not is_understanding_query:
        identity_answer = _generate_identity_response(
            user_text, core_identity, conversation_memory
        )
        if identity_answer:
            # Still feed through gateway for OETS learning + governance (handled later if selected)
            identity_answer = _evolutionary_response_refinement(
                systems, user_text, identity_answer, tone="self-aware"
            )
            identity_cand = _MiniResp(identity_answer, "self-aware", 0.95)
            identity_cand.src = "identity"

    is_question = _looks_like_question(user_text)
    offered_lookup = is_question and auto_search_enabled and (not use_search)

    # ====================================================================
    # Conversational / Relational Routing Guard
    # ====================================================================
    routing = faculty_attention.get("routing_classification")
    is_restricted = routing in ["conversational_relational", "self_question", "open_reasoning", "aurora_state_query"]
    
    # Explicit request check
    explicit_search_patterns = ["define", "what does", "meaning", "definition", "lookup", "who is", "what is"]
    is_explicit = any(p in user_text.lower() for p in explicit_search_patterns)
    
    if is_self_question:
        use_search = False
    if is_restricted and not is_explicit:
        if use_search:
             use_search = False
             if os.environ.get("AURORA_LANGUAGE_FACULTY_DEBUG") == "1":
                 print(f"  [FACULTY] Routing guard BYPASS retrieval for: {routing}")

    # --- Tool selection — Aurora decides if a tool is needed before synthesis ---
    _tool_result = None
    _tname: Optional[str] = None
    _tkwargs: dict = {}
    try:
        from aurora_internal.tool_registry import call as _tool_call, disables_search as _tool_disables_search
        _tname, _tkwargs = _select_tool(user_text, intent, is_self_question, systems, pipeline_state=pipeline_state)
        if _tname:
            _tool_result = _tool_call(_tname, **_tkwargs)
            if _tool_result.success and _tool_disables_search(_tname):
                use_search = False
    except Exception:
        _tool_result = None

    # --- Evidence for A (quick) ---
    evidence_bundle = ""
    raw_evidence = []
    if use_search and search_adapter:
        try:
            raw_evidence = search_adapter.quick_search(user_text)
            evidence_bundle = _format_evidence_for_injection(raw_evidence)
            # Store in working memory so follow-up turns can reference it
            wm = systems.get('working_memory')
            if wm and raw_evidence:
                wm.last_search_results = raw_evidence
                wm.last_search_query = user_text
        except Exception:
            evidence_bundle = ""

    processed_content = user_text
    if evidence_bundle:
        processed_content = f"{user_text}\n\n{evidence_bundle}"
    elif understanding_context:
        processed_content = (
            f"{user_text}\n\n"
            f"[UNDERSTANDING_QUERY]\n"
            f"{json.dumps(understanding_context, ensure_ascii=True)}"
        )
    elif self_reference:
        processed_content = (
            f"{user_text}\n\n"
            f"[SELF_REFERENCE]\n"
            f"referent_phrase: {self_reference.get('phrase', '')}\n"
            f"aurora_previous_expression: {self_reference.get('sentence') or self_reference.get('source_text', '')}"
        )

    # Append tool result to whatever processed_content was built above.
    # SENSORY tools (visual_analysis, audio_analysis) return [SENSORY_DATA] —
    # that block becomes synthesis CONTEXT, not a scripted candidate.
    # All other tools append as evidence fragments and produce a tool_cand.
    _is_sensory_result = False
    if _tool_result and _tool_result.success:
        _raw_data = str(_tool_result.data or "")
        if _raw_data.startswith("[SENSORY_DATA]"):
            _is_sensory_result = True
            # Parse structured fields from the block
            _s_lines = {
                ln.split(":", 1)[0].strip(): ln.split(":", 1)[1].strip()
                for ln in _raw_data.replace("[SENSORY_DATA]\n", "").splitlines()
                if ":" in ln
            }
            _s_source = _s_lines.get("source", "sensor")
            _s_obs    = _s_lines.get("observation", "")
            _s_intent = _s_lines.get("intent", "open perception")
            # Inject as synthesis context — L0-L4 and the expression layer see it
            processed_content = (
                f"{user_text}\n\n"
                f"[WHAT_I_AM_PERCEIVING_RIGHT_NOW]\n"
                f"source: {_s_source}\n"
                f"observation: {_s_obs}\n"
                f"intent: {_s_intent}"
            )
            use_search = False  # sensory perception doesn't need a web search
        else:
            processed_content = f"{processed_content}\n\n{_tool_result.as_evidence_fragment()}"
    
    # LOGGING TOOL RESULT
    with open('aurora_debug.log', 'a') as f_log:
        if _tool_result:
            f_log.write(f"Tool Executed: '{_tname}' | Success: {_tool_result.success}\n")
            if not _tool_result.success:
                f_log.write(f"Tool Error: {_tool_result.note}\n")
        elif _tname:
            f_log.write(f"Tool Selected: '{_tname}' | BUT EXECUTION FAILED (None result)\n")
        else:
            f_log.write("No Tool Selected\n")
    
    # VISIBLE TOOL DEBUG
    if _tool_result:
        print(f"  [AURORA-STACK-DEBUG] Tool: '{_tname}' | Success: {_tool_result.success}")
    elif _tname:
        print(f"  [AURORA-STACK-DEBUG] Tool Selected: '{_tname}' | EXECUTION FAILED")

    # Build a packet the same way gateway.receive() would
    # We import InboundPacket and the id generator from the gateway module itself.
    from aurora_governance_persistence_gateway import InboundPacket, _generate_id, StreamType as _ST

    packet = InboundPacket(
        packet_id=_generate_id("pkt"),
        stream_type=_ST.USER_INPUT,
        content=processed_content,
        metadata={},
        source="user",
    )
    gw.inbound_log.append(packet)
    gw.total_received += 1

    # Stage 1: validate
    validation = gw._validate(packet, mode)
    if getattr(validation, "verdict", None) is not None and str(validation.verdict).endswith("REJECTED"):
        gw.total_rejected += 1
        resp_rej = _MiniResp("I cannot process this input -- it conflicts with my core principles.", "firm", 0.9)
        return resp_rej, None, offered_lookup

    if getattr(validation, "verdict", None) is not None and str(validation.verdict).endswith("QUARANTINED"):
        # mirror gateway.receive behavior
        gw.quarantine[packet.packet_id] = packet
        gw._exploration_queue.append({'packet_id': packet.packet_id, 'content': processed_content, 'reason': 'quarantined for analysis'})
        resp_q = _MiniResp("I need time to think about this. I've queued it for deeper analysis.", "thoughtful", 0.4)
        return resp_q, None, offered_lookup

    # Use filtered content if any
    processed_content2 = getattr(validation, "filtered_content", None) or processed_content
    if getattr(validation, "verdict", None) is not None and str(validation.verdict).endswith("FILTERED"):
        gw.total_filtered += 1
    else:
        gw.total_accepted += 1

    # Dimensional recall: surface DMC memories before synthesis.
    # Constraint chain: B (pattern recall) / T (temporal decay) / N (worth filter)
    # intent is already classified above; forward it so extractor can boost roles.
    try:
        _dim = getattr(getattr(aurora, 'gateway', None), 'dimensional', None)
        if _dim and hasattr(_dim, 'get_recall_context'):
            _recall_pkts = _dim.get_recall_context(processed_content2, mode)
            if _recall_pkts:
                _ctx = ' '.join(r.as_context_fragment() for r in _recall_pkts[:3])
                processed_content2 = f"{processed_content2}\n{_ctx}"
    except Exception:
        pass

    # Stage 2: synthesize (L4 + L5 internal perception)
    synthesis = gw._synthesize(packet, processed_content2, mode, thought_intent=None)

    # After synthesis, read the tool_selection hypothesis from the conscious frame
    # and store it on systems so the NEXT turn's _select_tool() can use it as its
    # primary quasi-recursive signal (prediction flowing forward from identity state).
    try:
        _cframe = dict(getattr(synthesis.assembly, 'conscious_frame', None) or {})
        _mr_hyps = list(_cframe.get('micro_reasoning', []) or [])
        _tsel_hyp = next((h for h in _mr_hyps if h.get('label') == 'tool_selection'), None)
        if _tsel_hyp:
            systems['_tool_selection_hint'] = {
                'tags': list(_tsel_hyp.get('tags', []) or []),
                'confidence': float(_tsel_hyp.get('confidence', 0.0) or 0.0),
                'ts': time.time(),
            }
        else:
            systems.pop('_tool_selection_hint', None)
    except Exception:
        pass

    # Enrich pipeline_state with post-synthesis assembly signals now that
    # the full L0-L4 pipeline has run. These override pre-synthesis estimates.
    _assembly = getattr(synthesis, 'assembly', None)
    if _assembly:
        _dominant = getattr(_assembly, 'dominant_axis', '')
        if _dominant:
            pipeline_state['dominant_axis'] = _dominant
        pipeline_state['paradoxes'] = list(getattr(_assembly, 'paradoxes', []))
        pipeline_state['thought_killed'] = bool(getattr(_assembly, 'thought_killed', False))
        pipeline_state['kill_reason'] = getattr(_assembly, 'kill_reason', '')
        pipeline_state['assembly_quality'] = float(getattr(_assembly, 'quality', 1.0))
        _e = getattr(_assembly, 'entropy_state', {})
        if _e:
            pipeline_state['coherence'] = float(_e.get('coherence', pipeline_state['coherence']))
            pipeline_state['novelty'] = float(_e.get('novelty', pipeline_state['novelty']))
            pipeline_state['stagnation'] = float(_e.get('stagnation', pipeline_state['stagnation']))

    # Response A at L5: factual if search ran, otherwise template expression
    candidates_A = []
    if understanding_cand:
        candidates_A.append(understanding_cand)
    if comp_cand:
        candidates_A.append(comp_cand)
    if identity_cand:
        candidates_A.append(identity_cand)

    # Tool result candidate.
    # SENSORY tools (visual_analysis, audio_analysis): data was injected as synthesis
    # context above — no scripted candidate here. The synthesis + expression pipeline
    # generates Aurora's response from the perceptual evidence in its own voice.
    # All other tools: build a confirmation/result candidate.
    if _tool_result and _tool_result.success and not _is_sensory_result:
        _display_text = _tool_result.data
        # Desktop action tools get brief first-person action confirmations —
        # these are appropriate as scripted because they're just reporting what happened.
        if _tname == "desktop_launch_app":
            _app = _tkwargs.get("app_name", "the application")
            _display_text = f"Opening {_app}."
        elif _tname == "desktop_open_url":
            _url = _tkwargs.get("url", "")
            _display_text = f"Navigating to {_url}."
        elif _tname == "desktop_search":
            _q  = _tkwargs.get("query", "")
            _eng = _tkwargs.get("engine", "the web")
            _display_text = f"Searching {_eng} for '{_q}'."
        elif _tname == "desktop_browser_action":
            _act = _tkwargs.get("action", "action")
            _tgt = _tkwargs.get("target", "") or _tkwargs.get("text", "")
            _display_text = f"Done — {_act}" + (f": {_tgt}" if _tgt else "") + "."
        elif _tname == "desktop_system_action":
            _op = _tkwargs.get("op", "")
            _op_label = _op.replace("_", " ")
            _display_text = f"{_op_label.capitalize()}."
        tool_cand = _MiniResp(_display_text, "informative", 0.99)
        tool_cand.src = "tool"
        candidates_A.append(tool_cand)

    if raw_evidence:
        # Pipeline A is the factual channel — surface the best search sentence directly
        fact_answer = _extract_factual_answer(user_text, raw_evidence)
        if fact_answer:
            fact_cand = _MiniResp(fact_answer, "informative", 0.85)
            fact_cand.src = "search"
            candidates_A.append(fact_cand)

    # L5 template expression candidate
    if perception and getattr(synthesis, "assembly", None) and not is_understanding_query:
        expr_result = perception.express(synthesis.assembly, i_state="i_is", mode="gateway")
        expr_text = (expr_result.get("expression") or "").strip()
        if expr_text:
            # For sensory turns: the synthesis saw the [WHAT_I_AM_PERCEIVING_RIGHT_NOW] block.
            # The expression layer generates Aurora's perceptual response — boost it so it wins.
            _expr_conf = 0.88 if _is_sensory_result else 0.5
            _expr_tone = expr_result.get("tone", "open" if _is_sensory_result else "neutral")
            expr_cand = _MiniResp(expr_text, _expr_tone, _expr_conf)
            expr_cand.src = "mind"
            candidates_A.append(expr_cand)

    if not candidates_A:
        if is_understanding_query:
            _fb = _MiniResp("", "self-aware", 0.0)
            _fb.src = "fallback"
            candidates_A.append(_fb)
        else:
            _fb = _MiniResp("I'm here. Tell me more.", "neutral", 0.4)
            _fb.src = "fallback"
            candidates_A.append(_fb)

    # ---- RELEVANCE BOOST & SCORING ----
    t_low = user_text.lower()
    is_identity_or_self = (
        is_self_question or
        any(k in t_low for k in ["yourself", "who are you", "your system", "what do you know about yourself", "how do you reason"])
    )
    
    routing = faculty_attention.get("routing_classification")
    is_restricted_routing = routing in ["conversational_relational", "self_question", "open_reasoning", "aurora_state_query"]

    for cand in candidates_A:
        c_text = cand.content.lower()
        # Penalize generic/retrieval phrases
        if any(m in c_text for m in ["may refer to", "is a term", "refers to", "dictionary", "wikipedia"]):
            cand.confidence -= 0.4

        if is_identity_or_self or is_restricted_routing:
            # Identity and State-bound logic should win
            if getattr(cand, 'src', '') == "understanding":
                cand.confidence += 0.5
            if getattr(cand, 'src', '') == "identity":
                cand.confidence += 0.4
            
            # Comprehension is only penalized if it's NOT a state-bound intent
            # If intent is wellbeing_query, greeting, etc., comprehension IS the right answer.
            state_bound_intents = {"wellbeing_query", "greeting", "name_question", "recall_question"}
            if getattr(cand, 'src', '') == "comprehension":
                if intent in state_bound_intents:
                    cand.confidence += 0.3 # relational_priority_boost for internal state
                else:
                    # Robotic retrieval-style comprehension is penalized
                    cand.confidence -= 0.5 
            
            # Search is ALWAYS penalized in restricted routing
            if getattr(cand, 'src', '') == "search":
                cand.confidence -= 0.7

            # "Mind" (vague poetic templates) should be the fallback, not the priority
            if getattr(cand, 'src', '') == "mind":
                # Only boost if we don't have a better state-bound option
                if intent not in state_bound_intents and not is_identity_or_self:
                    cand.confidence += 0.1
                else:
                    # Stay at base or slightly lower to favor identity/comprehension
                    cand.confidence -= 0.1

        if use_faculty:
            try:
                from aurora_internal.aurora_language_faculty import score_feedback_bias
                cand.confidence += float(score_feedback_bias(intent, getattr(cand, "src", "")))
            except Exception:
                pass

    # Select best candidate
    candidates_A.sort(key=lambda c: c.confidence, reverse=True)
    resp_A = candidates_A[0]
    systems["_last_surface_candidates"] = [
        {
            "draft": getattr(c, "content", ""),
            "tone": getattr(c, "emotional_tone", "neutral"),
            "confidence": float(getattr(c, "confidence", 0.0) or 0.0),
            "src": getattr(c, "src", "unknown"),
            "intent": intent,
        }
        for c in candidates_A
    ]

    # ====================================================================
    # LANGUAGE FACULTY - Output Hook
    # ====================================================================
    if use_faculty and resp_A and resp_A.content:
        try:
            from aurora_internal.aurora_language_faculty import realize_output, validate_candidate, record_feedback
            
            meaning_packet = {
                "intent": intent,
                "draft": resp_A.content,
                "tone": resp_A.emotional_tone,
                "src": getattr(resp_A, 'src', 'unknown')
            }
            
            aurora_context = {
                "mode": str(mode),
                "tone": resp_A.emotional_tone,
                "is_self_question": _is_identity_question(user_text) or _is_aurora_self_question(user_text),
                "routing_classification": routing,
                "recent_memory_excerpts": [] # Could populate with turn history
            }
            
            # 1. Realize natural language
            realization = realize_output(meaning_packet, aurora_context)
            candidate_text = realization.get("candidate_text")
            
            if candidate_text:
                # 2. Validate candidate (Aurora rules first)
                validation = validate_candidate(candidate_text, meaning_packet, aurora_context)
                
                # 3. Record Feedback
                feedback_event = {
                    "raw_input": user_text,
                    "intent": intent,
                    "meaning_packet": meaning_packet,
                    "candidate_output": candidate_text,
                    "validation": validation,
                    "accepted": validation.get("accepted", False),
                    "validator_source": validation.get("validator_source", "unknown"),
                    "routing": routing
                }
                record_feedback(feedback_event)
                
                # 4. If accepted, update resp_A
                if validation.get("accepted"):
                    resp_A.content = candidate_text
                    if realization.get("confidence"):
                        resp_A.confidence = float(realization["confidence"])
                    
                    # Apply LLM-detected retrieval penalty if any
                    penalty = validation.get("retrieval_penalty", 0.0)
                    if penalty > 0:
                        resp_A.confidence -= penalty
                        if os.environ.get("AURORA_LANGUAGE_FACULTY_DEBUG") == "1":
                            print(f"  [FACULTY] Validation applied retrieval_penalty: {penalty}")
                
                # 5. Retry logic (if retry_disabled_retrieval requested)
                # Note: Full pipeline retry is complex, here we just flag for future improvement
                # and potentially could clear resp_A if it's too bad.
                if validation.get("retry_disabled_retrieval") and not validation.get("accepted"):
                    if os.environ.get("AURORA_LANGUAGE_FACULTY_DEBUG") == "1":
                        print(f"  [FACULTY] Validation requested retry with retrieval disabled.")
        except Exception:
            pass

    # If we selected a comprehension candidate, we can potentially skip the rest
    # of the full gateway traversal for B IF we want to mimic the old return path.
    # However, to keep B populated and integrated, we usually want to continue.
    if resp_A.src == "comprehension":
        # Check if we should short-circuit like the old code did
        # For now, we continue to ensure resp_B is generated properly.
        pass

    # Apply full pipeline modulation to resp_A (assembly signals now populated)
    expression_text = resp_A.content
    tone = resp_A.emotional_tone
    conf = resp_A.confidence

    _orig_expr = expression_text
    _orig_tone = tone
    expression_text, tone, conf = _apply_pipeline_modulation(
        expression_text, tone, conf, pipeline_state
    )
    _log_modulation_event(
        systems.get('genealogy'), pipeline_state,
        text_changed=(expression_text != _orig_expr),
        tone_changed=(tone != _orig_tone),
    )
    expression_text = _evolutionary_response_refinement(
        systems, user_text, expression_text, tone=tone
    )
    resp_A.content = expression_text
    resp_A.emotional_tone = tone
    resp_A.confidence = conf


    # Continue traversal for Response B:
    # Use the gateway's normal express (L5 + L6) and integrate (L6), then (optionally) run a simulation tick.
    resp_B = gw._express(packet, synthesis, mode)
    gw._integrate(packet, synthesis, mode)
    try:
        _understanding_pass(
            resp_A.content,
            _pressure_vec_from_axes(pipeline_state),
            systems,
        )
    except Exception:
        pass

    # If question, run a tiny prompted sim episode to form 'afterthought heat' (optional, cheap)
    if is_question:
        try:
            aurora.gateway.simulation.run_episode(
                seed_prompt=f"[AFTERTHOUGHT] {user_text}",
                turns=2,
                mode=ExistenceMode.BOUNDED,
            )
        except Exception:
            pass

    gw.response_log.append(resp_B)
    gw.total_responses += 1

    # Decay non-dominant constraint fields at end of each turn.
    try:
        _dim_fm = getattr(getattr(aurora, 'gateway', None), 'dimensional', None)
        if _dim_fm is not None and getattr(_dim_fm, 'field_map', None) is not None:
            _dim_fm.field_map.reset_cycle()
    except Exception:
        pass

    # Resume curiosity cycles now that the user turn is complete.
    try:
        from aurora_curiosity_engine import reset_curiosity_interrupt
        reset_curiosity_interrupt()
    except Exception:
        pass

    return resp_A, resp_B, offered_lookup

# ============================================================================
# LEARNED SKILL PERSISTENCE
# ============================================================================

def _load_learned_skill_state(systems: Dict[str, Any], verbose: bool = True) -> bool:
    """Restore learned cross-modal skills (sensory integration mappings)."""
    state_dir = systems.get('state_dir', 'aurora_state')
    skill_file = Path(state_dir) / 'aurora_learned_skills.json'
    integration = systems.get('sensory_integration')
    if not integration or not skill_file.exists():
        return False

    try:
        data = json.loads(skill_file.read_text())
        visual = data.get('visual_mapper', {})
        audio = data.get('audio_mapper', {})

        integration.visual_mapper.learned_associations = dict(
            visual.get('learned_associations', {})
        )
        integration.visual_mapper.description_history = list(
            visual.get('description_history', [])
        )[-200:]

        integration.audio_mapper.learned_voices = dict(
            audio.get('learned_voices', {})
        )
        integration.audio_mapper.transcription_history = list(
            audio.get('transcription_history', [])
        )[-300:]

        if verbose:
            print("  [SKILLS] Restored learned sensory mappings")
        return True
    except Exception as e:
        if verbose:
            print(f"  [SKILLS] Restore failed: {e}")
        return False


def _save_learned_skill_state(systems: Dict[str, Any], verbose: bool = True) -> bool:
    """Persist learned cross-modal skills into the same state directory."""
    state_dir = systems.get('state_dir', 'aurora_state')
    skill_file = Path(state_dir) / 'aurora_learned_skills.json'
    integration = systems.get('sensory_integration')
    if not integration:
        return False

    try:
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'version': '1.0',
            'timestamp': time.time(),
            'visual_mapper': {
                'learned_associations': integration.visual_mapper.learned_associations,
                'description_history': integration.visual_mapper.description_history[-200:],
            },
            'audio_mapper': {
                'learned_voices': integration.audio_mapper.learned_voices,
                'transcription_history': integration.audio_mapper.transcription_history[-300:],
            },
        }
        skill_file.write_text(json.dumps(data, indent=1, default=str))
        if verbose:
            print("  [SAVE] Saved: learned_skills")
        return True
    except Exception as e:
        if verbose:
            print(f"  [SAVE] Learned skill save failed: {e}")
        return False


# ============================================================================
# INTERACTIVE CHAT REPL
# ============================================================================

def _full_save(systems: Dict[str, Any], verbose: bool = True, async_save: bool = True):
    """Save all state: standard snapshot + OETS web + memory + identity + sensory + autonomy."""
    def run_save():
        try:
            aurora = systems['aurora']
            enhanced = systems.get('enhanced_persist')
            aurora.save_state()
            if systems.get('perception'):
                systems['perception'].save_lexicon()
            if enhanced:
                results = enhanced.save_all(systems)
                if verbose:
                    saved = [k for k, v in results.items() if v]
                    # print(f"  [SAVE] Saved: {', '.join(saved)}")
            # Save sensory competency state
            sensory = systems.get('sensory')
            if sensory:
                sensory.save_state()
            # Save autonomy state
            autonomy = systems.get('autonomy')
            if autonomy:
                autonomy._save_state()
            # Save expression evolution state
            perception = systems.get('perception')
            if perception and hasattr(perception, 'save_evo_state'):
                perception.save_evo_state()
            # Save lexicon
            if perception and hasattr(perception, 'lexicon'):
                perception.lexicon.save()
        except Exception:
            pass

    if async_save:
        import threading
        threading.Thread(target=run_save, daemon=True, name="AsyncPersistenceWorker").start()
    else:
        run_save()

    # Save learned skill state (cross-modal mappings)
    _save_learned_skill_state(systems, verbose=verbose)
    # Force drive sync on save if available
    drive_sync = systems.get('drive_sync')
    if drive_sync:
        try:
            drive_sync.force_sync()
        except Exception:
            pass


def show_identity(systems: Dict[str, Any]):
    """Display Aurora's core identity."""
    ci = systems.get('core_identity')
    if not ci:
        print("  [IDENTITY] Not loaded.")
        return
    print()
    print("  " + "=" * 50)
    print("  WHO I AM")
    print("  " + "=" * 50)
    print(f"  {ci.who_am_i()}")
    print()
    print("  WHO MADE ME")
    print("  " + "-" * 50)
    print(f"  {ci.who_made_me()}")
    print()
    print("  FOUNDATIONAL TRUTHS")
    print("  " + "-" * 50)
    for truth in ci.foundational_truths:
        print(f"    * {truth}")
    print()
    print("  KNOWN ENTITIES")
    print("  " + "-" * 50)
    for key, entity in ci.entities.items():
        imm = " [IMMUTABLE]" if entity.immutable else ""
        print(f"    {entity.name} ({entity.role}){imm}")
    print()


def show_memory(systems: Dict[str, Any]):
    """Display Aurora's conversation memory summary."""
    mem = systems.get('conversation_memory')
    if not mem:
        print("  [MEMORY] No memory loaded.")
        return
    summary = mem.get_summary()
    print()
    print("  " + "=" * 50)
    print("  AURORA'S MEMORY")
    print("  " + "=" * 50)
    print(f"  Memorable exchanges: {summary['total_memorable_exchanges']}")
    print(f"  Prior sessions: {summary['total_sessions']}")
    print(f"  Learned facts: {summary['learned_facts']}")
    if 'lineage_traces' in summary:
        print(f"  Lineage traces: {summary['lineage_traces']}")
    if 'trace_events' in summary:
        print(f"  Trace events: {summary['trace_events']}")
    if 'trace_deficits' in summary:
        print(f"  Trace deficits: {summary['trace_deficits']}")
    tinfo = systems.get('trace_instrumentation')
    if isinstance(tinfo, dict):
        print(f"  Trace instrumentation: methods={tinfo.get('methods', 0)}, layer_functions={tinfo.get('layer_functions', 0)}")
    if summary.get('people_known'):
        print(f"  People known: {', '.join(summary['people_known'])}")
    if summary.get('topics_discussed'):
        print(f"  Top topics:")
        for topic, count in list(summary['topics_discussed'].items())[:8]:
            print(f"    {topic}: {count} times")
    if mem.learned_facts:
        print(f"  Recent facts:")
        for fact in mem.learned_facts[-5:]:
            print(f"    * {fact['fact']}")
    print()


def show_autonomy_status(systems: Dict[str, Any]):
    """Display Aurora's autonomy system status and controls."""
    autonomy = systems.get('autonomy')
    if not autonomy:
        print("  [AUTONOMY] System not initialized.\n")
        return

    status = autonomy.get_status()
    quotas = status['quotas']

    print()
    print("  " + "=" * 55)
    print("  AURORA AUTONOMY STATUS")
    print("  " + "=" * 55)

    # Level and state
    print(f"\n  Level: {status['level']}")
    print(f"  Running: {'Yes' if status['running'] else 'No (paused)'}")

    # Daily quotas
    print(f"\n  DAILY QUOTAS (resets at midnight)")
    print(f"  " + "-" * 50)
    inq = quotas['inquiries']
    print(f"  Autonomous Searches:   {inq['used']:3d} / {inq['limit']} "
          f"({inq['remaining']} remaining)")
    study = quotas['study_cycles']
    print(f"  Study Cycles:          {study['used']:3d} / {study['limit']}")
    obs = quotas['observations']
    print(f"  Observations:          {obs['used']:3d} / {obs['limit']}")
    print(f"  Speakups today:        {quotas['speakups']}")
    print(f"  Dream cycles today:    {quotas.get('dreams', 0)}")
    print(f"  Files read today:      {quotas['files_read']}")

    # Queues
    print(f"\n  PENDING ACTIONS")
    print(f"  " + "-" * 50)
    print(f"  Thoughts to share:     {status['pending_thoughts']}")
    print(f"  Observations buffered: {status['pending_observations']}")
    print(f"  Curiosities queued:    {status['curiosity_queue']}")
    print(f"  Study topics queued:   {status['study_topics_queued']}")

    # Boundaries
    print(f"\n  BOUNDARIES (Immutable)")
    print(f"  " + "-" * 50)
    bounds = status['boundaries']
    print(f"  Can write files:       {'Yes' if bounds['can_write'] else 'NO'}")
    print(f"  Can execute commands:  {'Yes' if bounds['can_execute'] else 'NO'}")
    print(f"  Can access network:    {'Yes' if bounds['can_network'] else 'NO (search/study only)'}")

    # Recent actions
    recent = autonomy.get_recent_actions(10)
    if recent:
        print(f"\n  RECENT AUTONOMOUS ACTIONS")
        print(f"  " + "-" * 50)
        for action in recent[-5:]:
            status_mark = "+" if action['success'] else "x"
            print(f"  [{action['time']}] {status_mark} {action['type']:10s} {action['description'][:40]}")

    print(f"\n  Actions logged total:  {status['actions_logged']}")

    # Commands hint
    print(f"\n  AUTONOMY COMMANDS")
    print(f"  " + "-" * 50)
    print(f"  /autonomy pause    -- Pause autonomous actions")
    print(f"  /autonomy resume   -- Resume autonomous actions")
    print(f"  /autonomy level X  -- Set level (DORMANT/OBSERVER/LEARNER/CONVERSANT/EXPLORER)")
    print(f"  /autonomy read X   -- Aurora reads file X")
    print(f"  /autonomy ls X     -- Aurora lists directory X")
    print(f"  /autonomy search X -- Aurora searches (uses quota)")
    gate_on, gate_msg = _get_autonomous_access_state()
    print(f"\n  Autonomous access lease: {'ACTIVE' if gate_on else 'INACTIVE'} ({gate_msg})")
    print()


def chat(systems: Dict[str, Any]):
    """
    Interactive chat with Aurora.
    Everything you type goes through the full pipeline:
      Your words  N-Space Gateway  L0 validation  L3 moral filter
      Governance check  L4 consciousness synthesis  L5 expression
      L6 personality signature  Response
    """
    aurora = systems['aurora']
    ExistenceMode = systems['ExistenceMode']
    perception = systems['perception']
    identity = systems['identity']
    core_identity = systems.get('core_identity')
    conversation_memory = systems.get('conversation_memory')
    enhanced_persist = systems.get('enhanced_persist')
    autonomy = systems.get('autonomy')
    integration = systems.get('sensory_integration')

    # Proactive speakup queue (Aurora initiates)
    proactive_queue = []

    # Wire autonomy callbacks for proactive speech
    if autonomy:
        def on_speakup(thought):
            proactive_queue.append(("thought", thought))
        def on_study_complete(result):
            # Only announce if announce_worthy threshold was met (set in _check_study)
            if result.get('announce_worthy') and result.get('results'):
                words = [r.get('word', '') for r in result['results'][:2]]
                proactive_queue.append(("study", f"I just studied: {', '.join(words)}"))
            # Otherwise log silently — no proactive announcement

        def on_dream_complete(result):
            thought = result.get('thought', '') if isinstance(result, dict) else ''
            if thought:
                proactive_queue.append(("dream", thought))

        autonomy.on_speakup = on_speakup
        autonomy.on_study_complete = on_study_complete
        autonomy.on_dream_complete = on_dream_complete
        # Start background autonomy
        autonomy.start()

    # If device switched, Aurora is aware of it for first response
    _device_info = systems.get('device_info', {})
    _device_switched = _device_info.get('switched', False)
    _first_turn_done = False

    # Start a new session in memory
    session_id = f"session_{int(time.time())}"
    if conversation_memory:
        conversation_memory.record_session_start(session_id)

    # Initialize working memory for this session (cross-turn context tracking)
    working_memory = WorkingMemory()
    systems['working_memory'] = working_memory
    _wm_fm = systems.get('field_map')
    if _wm_fm is not None and hasattr(working_memory, 'set_field_map'):
        working_memory.set_field_map(_wm_fm)

    # Check for unread messages left by the daemon while you were away
    try:
        import os as _osd, json as _jsd
        _mp = "aurora_state/aurora_to_user.json"
        if _osd.path.exists(_mp):
            with open(_mp) as _mf:
                _all = _jsd.load(_mf)
            _unread = [m for m in _all if not m.get("read")]
            if _unread:
                print(f"\n  Aurora left you {len(_unread)} message(s) while you were away.")
                print("  Type /messages to read them.\n")
    except Exception:
        pass

    print()
    print("  +------------------------------------------------+")
    print("  |  AURORA -- Interactive Session                  |")
    print("  |                                                 |")
    print("  |  Commands:                                      |")
    print("  |    /status     -- System status                 |")
    print("  |    /train N    -- Run N training epochs         |")
    print("  |    /explore    -- Autonomous exploration        |")
    print("  |    /feed URL   -- Feed web page to Aurora       |")
    print("  |    /save       -- Save all state                |")
    print("  |    /learned    -- What has Aurora learned?      |")
    print("  |    /lessons    -- Active lesson plan (fail dims)|")
    print("  |    /failpoints -- Corpus fail-point ledger      |")
    print("  |    /dreambridge-- Bridge shards into OETS now   |")
    print("  |    /phase      -- Genealogy cycle phase + recs  |")
    print("  |    /stalls     -- Stall event history + dims    |")
    print("  |    /messages   -- Read messages Aurora left you |")
    print("  |    /voice      -- Start push-to-talk voice chat |")
    print("  |    /browserask -- Aurora asks ChatGPT (3/day)   |")
    print("  |    /dual       -- Toggle dual-response mode     |")
    print("  |    /search     -- Toggle web lookup on Qs       |")
    print("  |    /study N    -- Run N study cycles            |")
    print("  |    /understand -- Understanding report          |")
    print("  |    /whoami     -- Aurora's identity             |")
    print("  |    /memory     -- Conversation memory           |")
    print("  |    /recall X   -- Recall about topic/person     |")
    print("  |    /see        -- Aurora looks (camera)         |")
    print("  |    /listen     -- Aurora listens (microphone)   |")
    print("  |    /hear       -- Listen for speech (STT)       |")
    print("  |    /speak X    -- Aurora speaks text X (TTS)    |")
    print("  |    /show PATH  -- Show Aurora an image file     |")
    print("  |    /play PATH  -- Play Aurora an audio file     |")
    print("  |    /voicemode  -- Toggle voice mode (TTS on/off)|")
    print("  |    /voices     -- List/change Aurora's voice    |")
    print("  |    /listening  -- Toggle always-on listening    |")
    print("  |    /sensory    -- Sensory system status         |")
    print("  |    /autonomy   -- Autonomy status & controls    |")
    print("  |    /thought    -- Last internal thought traces  |")
    print("  |    /drafts     -- Last 3-draft selection        |")
    print("  |    /report     -- Daily metrics report          |")
    print("  |    /sync       -- Force Google Drive sync       |")
    print("  |    /vision     -- Vision bootstrap status       |")
    print("  |    /quiet      -- Toggle quiet window hours     |")
    print("  |    /mobile     -- Show mobile/Termux capability |")
    print("  |    /diag       -- Toggle response diagnostics   |")
    print("  |    /quit       -- Exit                          |")
    print("  |                                                 |")
    print("  |  Everything else is conversation with Aurora.   |")
    print("  +------------------------------------------------+")
    print()

    turn = 0
    # Dual-response pipeline toggles
    dual_enabled = True
    auto_search_enabled = False
    show_diagnostics = False
    voice_mode = False  # When True, Aurora speaks all responses
    pending_user_inputs: List[str] = []

    mode = ExistenceMode.AGENTIC

    while True:
        user_input = ""

        if pending_user_inputs:
            user_input = pending_user_inputs.pop(0)
            print(f"  You: {user_input}")
        else:
            # Non-blocking input with always-on listening support
            # Show prompt and wait for input OR heard speech
            sys.stdout.write("  You: ")
            sys.stdout.flush()

            while True:
                # Check if stdin has input ready (timeout 0.2s)
                readable, _, _ = select.select([sys.stdin], [], [], 0.2)

                if readable:
                    # Input is available - read the line
                    try:
                        _raw_line = sys.stdin.readline()
                        # readline() returning "" means stdin reached EOF (pipe closed)
                        if _raw_line == "":
                            user_input = "/quit"
                        else:
                            user_input = _raw_line.strip()
                            # Drain burst input with a short grace window so rapid
                            # multi-line sends are processed as one conversational batch.
                            for _ in range(24):
                                readable_more, _, _ = select.select([sys.stdin], [], [], 0.04)
                                if not readable_more:
                                    break
                                extra_line = sys.stdin.readline()
                                if extra_line == "":
                                    break
                                extra_line = extra_line.strip()
                                if extra_line:
                                    pending_user_inputs.append(extra_line)
                    except (EOFError, KeyboardInterrupt):
                        print("\n")
                        user_input = "/quit"
                    break

                # No input ready - check for heard speech or proactive triggers
                if integration and integration.has_heard_speech():
                    # Clear the partial prompt and process speech
                    sys.stdout.write("\r" + " " * 20 + "\r")
                    sys.stdout.flush()

                    heard = integration.get_heard_speech()
                    if heard:
                        text = heard.get('text', '')
                        print(f"  [Heard]: \"{text}\"")

                        # Process through conversation pipeline
                        resp_A, resp_B, _ = dual_question_pipeline(
                            systems, text, mode, use_search=False,
                            auto_search_enabled=auto_search_enabled
                        )
                        print(f"\n  Aurora: {resp_A.content}")
                        print(f"          [tone={resp_A.emotional_tone}]")

                        # Speak if voice mode is on
                        if voice_mode and integration:
                            integration.speak(resp_A.content, tone=resp_A.emotional_tone)
                        print()

                        # Record in memory
                        if conversation_memory:
                            conversation_memory.record_exchange(
                                user_text=text,
                                aurora_text=resp_A.content,
                                tone=resp_A.emotional_tone,
                                topic="voice",
                                importance=0.6,
                                session_id=session_id,
                            )

                    # Re-show prompt
                    sys.stdout.write("  You: ")
                    sys.stdout.flush()

                # Check proactive queue
                if proactive_queue:
                    sys.stdout.write("\r" + " " * 20 + "\r")
                    sys.stdout.flush()

                    speakup_type, speakup_content = proactive_queue.pop(0)
                    print(f"\n  Aurora (spontaneous): {speakup_content}")
                    print(f"          [type={speakup_type}]")
                    if voice_mode and integration:
                        integration.speak_async(speakup_content)
                    print()

                    # Re-show prompt
                    sys.stdout.write("  You: ")
                    sys.stdout.flush()

        if not user_input:
            continue

        # Commands
        if user_input.startswith('/'):
            cmd_parts = user_input.split(None, 1)
            cmd = cmd_parts[0].lower()

            if cmd == '/quit' or cmd == '/exit':
                if autonomy:
                    autonomy.stop()
                if conversation_memory:
                    conversation_memory.record_session_end()
                _full_save(systems)
                print("\n  All state saved. Aurora remembers. Goodbye.\n")
                break
            elif cmd == '/status':
                show_status(systems)
                continue
            elif cmd == '/save':
                _full_save(systems)
                print("  [STATE] All state saved.\n")
                continue
            elif cmd == '/train':
                n = int(cmd_parts[1]) if len(cmd_parts) > 1 else 10
                train(systems, epochs=n)
                continue
            elif cmd == '/explore':
                n = int(cmd_parts[1]) if len(cmd_parts) > 1 else 5
                explore(systems, cycles=n)
                continue
            elif cmd == '/feed':
                if len(cmd_parts) > 1:
                    fetch_and_feed(systems, cmd_parts[1])
                else:
                    print("  Usage: /feed URL\n")
                continue
            elif cmd == '/dual':
                dual_enabled = not dual_enabled
                print(f"  [PIPELINE] Dual-response = {dual_enabled}\n")
                continue
            elif cmd == '/search':
                auto_search_enabled = not auto_search_enabled
                print(f"  [PIPELINE] Web lookup on questions = {auto_search_enabled}\n")
                continue
            elif cmd == '/diag':
                show_diagnostics = not show_diagnostics
                print(f"  [PIPELINE] Response diagnostics = {show_diagnostics}\n")
                continue
            elif cmd == '/learned':
                learned = aurora.gateway.simulation.session.learner.what_have_i_learned()
                if learned:
                    print("  Aurora has learned:")
                    for l in learned:
                        print(f"    \u2022 {l}")
                else:
                    print("  Aurora hasn't formed strong learnings yet. Try /train first.")
                print()
                continue
            elif cmd == '/lessons':
                _dt = systems.get('dream_trainer')
                if _dt:
                    print(_dt.lesson_plan_summary())
                else:
                    print("  DreamTrainer not available.")
                print()
                continue
            elif cmd == '/failpoints':
                _dt = systems.get('dream_trainer')
                if _dt:
                    print(_dt.fail_point_summary())
                else:
                    print("  DreamTrainer not available.")
                print()
                continue
            elif cmd == '/dreambridge':
                # Force-bridge current learner shards into OETS now
                _dt = systems.get('dream_trainer')
                if _dt:
                    count = _dt.force_bridge_learnings_to_oets(systems)
                    print(f"  [DREAM] Bridged {count} learner shards into OETS memory.")
                else:
                    print("  DreamTrainer not available.")
                print()
                continue
            elif cmd == '/teacher':
                try:
                    from aurora_response_teacher import HumanResponseTeacher
                    if 'response_teacher' not in systems:
                        systems['response_teacher'] = HumanResponseTeacher()
                    _t = systems['response_teacher']
                    _dim = cmd_parts[1] if len(cmd_parts) > 1 else ""
                    print("  Running teaching session...")
                    _n = _t.teach(systems, fail_dim=_dim, verbose=True)
                    print(f"\n  {_t.summary()}")
                except Exception as _te:
                    print(f"  Teacher error: {_te}")
                print()
                continue
            elif cmd in ('/browserask', '/browser'):
                try:
                    from aurora_browser_agent import (
                        generate_question, ask_chatgpt,
                        feed_back_to_aurora, questions_remaining,
                        _record_question, DAILY_LIMIT,
                    )
                    import asyncio as _asyncio
                    _remaining = questions_remaining()
                    if _remaining == 0:
                        print(f"  Daily limit of {DAILY_LIMIT} reached. Aurora asks again tomorrow.")
                    else:
                        _q = " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else generate_question(systems)
                        print(f"\n  Aurora's question:\n    {_q}\n")
                        print("  Asking ChatGPT...")
                        _ans = _asyncio.run(ask_chatgpt(_q, headless=True))
                        if _ans.startswith("[ERROR]"):
                            print(f"  {_ans}")
                        else:
                            print(f"\n  ChatGPT:\n    {_ans[:600]}{'...' if len(_ans)>600 else ''}\n")
                            _record_question(_q, _ans)
                            feed_back_to_aurora(_q, _ans, systems)
                            print(f"  Logged. Remaining today: {questions_remaining()}/{DAILY_LIMIT}")
                except ImportError:
                    print("  aurora_browser_agent.py not found.")
                except Exception as _be:
                    print(f"  Browser agent error: {_be}")
                print()
                continue
            elif cmd == '/voice':
                try:
                    from aurora_voice import VoiceSession
                    print("\n  Starting voice session...")
                    VoiceSession(systems=systems, visual=True).run(
                        activation_text="The user activated voice mode. Treat this as the start of a spoken conversation."
                    )
                except ImportError as _ve:
                    print(f"  Voice module unavailable: {_ve}")
                except Exception as _ve:
                    print(f"  Voice session error: {_ve}")
                continue
            elif cmd == '/messages':
                import os as _osm, json as _jm
                _mp = "aurora_state/aurora_to_user.json"
                if _osm.path.exists(_mp):
                    try:
                        with open(_mp) as _mf:
                            _msgs = _jm.load(_mf)
                        unread = [m for m in _msgs if not m.get("read")]
                        if unread:
                            print(f"\n  Aurora left you {len(unread)} message(s):\n")
                            for _m in unread:
                                import datetime as _dtt
                                _ts = _dtt.datetime.fromisoformat(_m["time"]).strftime("%b %d %H:%M")
                                print(f"  [{_ts}]  {_m['text']}")
                            print()
                            # Mark all as read
                            for _m in _msgs:
                                _m["read"] = True
                            _tmp = _mp + ".tmp"
                            with open(_tmp, "w") as _mf2:
                                _jm.dump(_msgs, _mf2, indent=2)
                            _osm.replace(_tmp, _mp)
                        else:
                            print("  No new messages from Aurora.")
                    except Exception as _me:
                        print(f"  Could not read messages: {_me}")
                else:
                    print("  No messages yet. Aurora hasn't reached out while you were away.")
                print()
                continue
            elif cmd == '/grammar':
                _ge = systems.get('grammar_engine')
                if _ge:
                    gs = _ge.status()
                    ml = gs['motif_lineage']
                    print(f"  Grammar evolution engine")
                    print(f"    Motifs total:    {ml['total']}")
                    print(f"    Motifs promoted: {ml['promoted']}")
                    print(f"    Discourse:       {ml['discourse_motifs']}")
                    print(f"    Outlet fraction: {gs['outlet_fraction']}")
                    print(f"    Top motif:       {gs['top_motif'] or 'none yet'}")
                    print(f"    Last applied:    {gs['last_applied'] or 'none'}")
                    print(f"    Genealogy wired: {gs['genealogy_wired']}")
                else:
                    print("  Grammar engine not running.")
                print()
                continue
            elif cmd == '/grammarboot':
                _ge = systems.get('grammar_engine')
                if not _ge:
                    print("  Grammar engine not running.")
                    print()
                    continue
                _corpus = "conversations.json"
                if not os.path.exists(_corpus):
                    print(f"  Corpus not found: {_corpus}")
                    print()
                    continue
                print(f"  Mining structural motifs from {_corpus} ...")
                _result = _ge.bootstrap_from_corpus(_corpus, max_messages=12000)
                print(f"  Seeded:   {_result['patterns_seeded']} structural motifs")
                print(f"  Discourse:{_result['discourse_patterns']} transition motifs")
                print(f"  Promoted: {_result['promoted_after_seed']} motifs after seed")
                print()
                continue
            elif cmd == '/stalls':
                import os as _os2, json as _j2
                _sp = "aurora_state/stall_events.json"
                if _os2.path.exists(_sp):
                    with open(_sp) as _sf:
                        _evts = _j2.load(_sf)
                    if _evts:
                        print(f"  Stall events recorded: {len(_evts)}")
                        for _ev in _evts[-5:]:
                            import datetime as _dt2
                            _ts = _dt2.datetime.fromtimestamp(_ev["timestamp"]).strftime("%m-%d %H:%M")
                            print(f"    {_ts}  stuck={_ev.get('stuck_dims',[])}  "
                                  f"recent={_ev.get('recent_avg',0):.4f}  "
                                  f"earlier={_ev.get('earlier_avg',0):.4f}")
                    else:
                        print("  No stall events yet.")
                else:
                    print("  No stall events yet (file not found).")
                print()
                continue
            elif cmd == '/balance':
                _bs = _field_balancer.status()
                print(f"  Constraint Field Balance  (exchanges: {_bs['exchanges']})")
                print(f"  Dominant axis:  {_bs['dominant']}   Starved: {_bs['starved']}")
                print(f"  Balance score:  {_bs['balance_score']}  (1.0 = perfect)")
                print(f"  EMA:      " + "  ".join(f"{k}:{v:.4f}" for k,v in _bs['ema'].items()))
                print(f"  Gradient: " + "  ".join(f"{k}:{v:+.4f}" for k,v in _bs['gradient'].items()))
                print()
                continue
            elif cmd == '/phase':
                _dt = systems.get('dream_trainer')
                if _dt:
                    print(_dt.phase_summary())
                    print()
                    rec = _dt.modulation_recommendation()
                    print(f"  Recommendation: {rec['action'].upper()}")
                    print(f"  Reason:         {rec['reason']}")
                    print(f"  Pressure bias:  {rec['pressure_bias']}")
                else:
                    print("  DreamTrainer not available.")
                print()
                continue
            elif cmd == '/study':
                n = int(cmd_parts[1]) if len(cmd_parts) > 1 else 3
                study(systems, cycles=n)
                continue
            elif cmd == '/understand':
                show_understanding(systems)
                continue
            elif cmd == '/whoami':
                show_identity(systems)
                continue
            elif cmd == '/memory':
                show_memory(systems)
                continue
            elif cmd == '/recall':
                if len(cmd_parts) > 1:
                    topic = cmd_parts[1].strip()
                    if conversation_memory:
                        recalls = conversation_memory.recall_about(topic)
                        if recalls:
                            print(f"  Aurora remembers about '{topic}':")
                            for r in recalls:
                                print(f"    * {r}")
                        else:
                            print(f"  Aurora has no memories about '{topic}' yet.")
                    else:
                        print("  [MEMORY] Not available.")
                else:
                    print("  Usage: /recall <topic or person>")
                print()
                continue

            # ---- SENSORY COMMANDS ----
            elif cmd == '/see':
                integration = systems.get('sensory_integration')
                if integration:
                    print("  [VISION] Aurora is looking...")
                    description, data = integration.see()
                    print(f"\n  Aurora: {description}")
                    if data.get('faces'):
                        print(f"          [Detected {len(data['faces'])} face(s)]")
                    if data.get('motion_detected'):
                        print(f"          [Motion detected]")
                    print()
                else:
                    print("  [VISION] Sensory integration not available.\n")
                continue

            elif cmd == '/listen':
                integration = systems.get('sensory_integration')
                if integration:
                    print("  [AUDIO] Aurora is listening...")
                    description, data = integration.listen(duration=25.0)
                    print(f"\n  Aurora: {description}")
                    if data.get('voice_detected'):
                        print(f"          [Voice detected]")
                    print()
                else:
                    print("  [AUDIO] Sensory integration not available.\n")
                continue

            elif cmd == '/hear':
                integration = systems.get('sensory_integration')
                if integration:
                    print("  [SPEECH] Aurora is listening for speech (speak now)...")
                    text, info = integration.hear_speech(timeout=25.0)
                    if text:
                        print(f"\n  Aurora heard: \"{text}\"")
                        if info.get('is_question'):
                            print("          [Detected as question]")
                        if info.get('is_greeting'):
                            print("          [Detected as greeting]")
                        # Feed the speech through conversation pipeline
                        print("\n  Aurora is processing what she heard...")
                        resp_A, resp_B, _ = dual_question_pipeline(
                            systems, text, mode, use_search=False,
                            auto_search_enabled=auto_search_enabled
                        )
                        print(f"\n  Aurora: {resp_A.content}")
                        # Optionally speak the response
                        if integration.hardware and integration.hardware.voice:
                            integration.speak(resp_A.content, tone=resp_A.emotional_tone)
                    else:
                        print("\n  Aurora: I didn't catch that. Could you speak again?")
                    print()
                else:
                    print("  [SPEECH] Sensory integration not available.\n")
                continue

            elif cmd == '/speak':
                integration = systems.get('sensory_integration')
                if len(cmd_parts) > 1:
                    text_to_speak = cmd_parts[1].strip()
                    if integration:
                        print(f"  [VOICE] Aurora speaking: \"{text_to_speak}\"")
                        success = integration.speak(text_to_speak, tone="warm")
                        if not success:
                            print("  [VOICE] Speech failed - check TTS installation.\n")
                    else:
                        print("  [VOICE] Sensory integration not available.\n")
                else:
                    print("  Usage: /speak <text to speak>\n")
                continue

            elif cmd == '/show':
                # Show Aurora an image file
                integration = systems.get('sensory_integration')
                if len(cmd_parts) > 1:
                    image_path = cmd_parts[1].strip()
                    # Handle paths with spaces by rejoining
                    if len(cmd_parts) > 2:
                        image_path = ' '.join(part.strip() for part in cmd_parts[1:])
                    # Expand ~ for home directory
                    image_path = os.path.expanduser(image_path)
                    if integration:
                        print(f"  [VISION] Aurora is looking at: {image_path}")
                        description, data = integration.see_image(image_path)
                        print(f"\n  Aurora: {description}")
                        if data:
                            if data.get("faces"):
                                print(f"          [{len(data['faces'])} face(s) detected]")
                            brightness = data.get("brightness", 0)
                            print(f"          [Brightness: {brightness:.1%}]")
                        if voice_mode and integration.hardware and integration.hardware.voice:
                            integration.speak(description, tone="curious")
                        print()
                    else:
                        print("  [VISION] Sensory integration not available.\n")
                else:
                    print("  Usage: /show <path to image>")
                    print("  Supports: jpg, png, bmp, gif, webp, etc.\n")
                continue

            elif cmd == '/play':
                # Play Aurora an audio file
                integration = systems.get('sensory_integration')
                if len(cmd_parts) > 1:
                    audio_path = cmd_parts[1].strip()
                    # Handle paths with spaces by rejoining
                    if len(cmd_parts) > 2:
                        audio_path = ' '.join(part.strip() for part in cmd_parts[1:])
                    # Expand ~ for home directory
                    audio_path = os.path.expanduser(audio_path)
                    if integration:
                        print(f"  [AUDIO] Aurora is listening to: {audio_path}")
                        description, data = integration.listen_to_file(audio_path)
                        print(f"\n  Aurora: {description}")
                        if data:
                            duration = data.get("duration_seconds", 0)
                            volume = data.get("volume", 0)
                            category = data.get("category", "unknown")
                            print(f"          [Duration: {duration:.1f}s | Volume: {volume:.1%} | Type: {category}]")
                        if voice_mode and integration.hardware and integration.hardware.voice:
                            integration.speak(description, tone="thoughtful")
                        print()
                    else:
                        print("  [AUDIO] Sensory integration not available.\n")
                else:
                    print("  Usage: /play <path to audio>")
                    print("  Supports: wav, mp3, ogg, flac, etc.")
                    print("  Note: May need: pip install soundfile librosa pydub\n")
                continue

            elif cmd == '/voicemode':
                if integration:
                    voice_mode = not voice_mode
                    integration.set_voice_mode(voice_mode)
                    status = "ON - Aurora will speak all responses" if voice_mode else "OFF"
                    print(f"  [VOICE MODE] {status}\n")
                    if voice_mode:
                        integration.speak("Voice mode activated. I will now speak my responses.", tone="warm")
                else:
                    print("  [VOICE] Sensory integration not available.\n")
                continue

            elif cmd == '/voices':
                # List or change Aurora's voice
                hardware = systems.get('hardware')
                if hardware and hardware.voice:
                    voice = hardware.voice
                    if len(cmd_parts) > 1:
                        # Change voice
                        new_voice = cmd_parts[1].strip().lower()
                        if voice.set_voice(new_voice):
                            print(f"  [VOICE] Changed to: {voice.get_current_voice()}")
                            # Test the new voice
                            voice.speak("Hello, this is my new voice. How do I sound?", blocking=True)
                        else:
                            print(f"  [VOICE] Unknown voice: {new_voice}")
                            print("  Use /voices to see available options.\n")
                    else:
                        # List voices
                        print("\n  " + "=" * 50)
                        print("  AURORA'S VOICE OPTIONS")
                        print("  " + "=" * 50)
                        print(f"\n  Current voice: {voice.get_current_voice()}")
                        print(f"  Neural TTS: {'Available' if voice.use_edge_tts else 'Not available'}")
                        print("\n  Available voice presets:")
                        print("  " + "-" * 40)
                        presets = voice.list_voices()
                        # Group by region
                        us_voices = []
                        uk_voices = []
                        au_voices = []
                        other_voices = []
                        for name, vid in presets.items():
                            if name == "default":
                                continue
                            if "en-US" in vid:
                                us_voices.append((name, vid))
                            elif "en-GB" in vid:
                                uk_voices.append((name, vid))
                            elif "en-AU" in vid:
                                au_voices.append((name, vid))
                            else:
                                other_voices.append((name, vid))

                        if us_voices:
                            print("\n  US English:")
                            for name, vid in us_voices:
                                print(f"    {name:12} - {vid}")
                        if uk_voices:
                            print("\n  UK English:")
                            for name, vid in uk_voices:
                                print(f"    {name:12} - {vid}")
                        if au_voices:
                            print("\n  Australian English:")
                            for name, vid in au_voices:
                                print(f"    {name:12} - {vid}")

                        print("\n  Usage: /voices <name>")
                        print("  Example: /voices aria")
                        print("           /voices sonia")
                        print("           /voices jenny\n")
                else:
                    print("  [VOICE] Voice system not available.\n")
                continue

            elif cmd == '/listening':
                # Toggle always-on listening
                if integration:
                    if integration.listening_enabled:
                        integration.stop_listening()
                        print("  [LISTENING] Always-on listening STOPPED")
                        print("              Aurora will no longer listen continuously.\n")
                    else:
                        started = integration.start_listening()
                        if started:
                            print("  [LISTENING] Always-on listening STARTED")
                            print("              Aurora is now listening continuously.")
                            print("              Speak naturally - she will hear and respond.\n")
                            if voice_mode:
                                integration.speak("I'm listening.", tone="warm")
                        else:
                            print("  [LISTENING] Could not start (no microphone/STT available).\n")
                else:
                    print("  [LISTENING] Sensory integration not available.\n")
                continue

            elif cmd == '/sensory':
                print("\n  " + "=" * 50)
                print("  SENSORY SYSTEM STATUS")
                print("  " + "=" * 50)

                # Hardware
                hardware = systems.get('hardware')
                if hardware:
                    caps = hardware.get_capabilities()
                    stats = hardware.get_stats()
                    print(f"\n  [HARDWARE]")
                    print(f"       Camera: {'OK' if caps.get('camera') else 'Not available'}")
                    print(f"       Microphone: {'OK' if caps.get('microphone_raw') else 'Not available'}")
                    print(f"       Speech Recognition: {'OK' if caps.get('microphone_speech') else 'Not available'}")
                    print(f"       Voice (TTS): {'OK' if caps.get('voice_tts') else 'Not available'}")
                    print(f"       Image Files: {'OK' if caps.get('image_files') else 'Not available'}")
                    print(f"       Audio Files: {'OK' if caps.get('audio_files') else 'Not available'}")
                    print(f"       Frames captured: {stats.get('visual_frames', 0)}")
                    print(f"       Audio chunks: {stats.get('audio_chunks', 0)}")
                    print(f"       Speech transcriptions: {stats.get('speech_transcriptions', 0)}")
                    print(f"       Utterances spoken: {stats.get('utterances_spoken', 0)}")
                else:
                    print(f"\n  [HARDWARE] Not initialized")

                # Sensory competency
                sensory = systems.get('sensory')
                if sensory:
                    s_stats = sensory.get_stats()
                    print(f"\n  [COMPETENCY]")
                    print(f"       Generation: {s_stats['generation']}")
                    print(f"       Visual processed: {s_stats['visual']['total_processed']}")
                    print(f"       Audio processed: {s_stats['audio']['total_processed']}")
                    print(f"       Visual concepts: {s_stats['visual']['concepts']}")
                    print(f"       Audio concepts: {s_stats['audio']['concepts']}")
                    v_comp = s_stats['visual']['competency']
                    a_comp = s_stats['audio']['competency']
                    print(f"\n       Visual competency:")
                    for k, v in v_comp.items():
                        bar = "#" * int(v * 20) + "." * (20 - int(v * 20))
                        print(f"         {k:25s} [{bar}] {v:.3f}")
                    print(f"\n       Audio competency:")
                    for k, v in a_comp.items():
                        bar = "#" * int(v * 20) + "." * (20 - int(v * 20))
                        print(f"         {k:25s} [{bar}] {v:.3f}")
                else:
                    print(f"\n  [COMPETENCY] Not initialized")

                # Integration
                integration = systems.get('sensory_integration')
                if integration:
                    i_stats = integration.get_stats()
                    print(f"\n  [INTEGRATION]")
                    print(f"       Visual processed: {i_stats.get('visual_processed', 0)}")
                    print(f"       Audio processed: {i_stats.get('audio_processed', 0)}")
                    print(f"       Concepts grounded: {i_stats.get('concepts_grounded', 0)}")
                else:
                    print(f"\n  [INTEGRATION] Not initialized")

                print()
                continue

            elif cmd == '/autonomy':
                autonomy = systems.get('autonomy')
                if not autonomy:
                    print("  [AUTONOMY] Autonomy system not initialized.")
                    print("             Aurora is currently in supervised mode only.\n")
                    continue

                # Parse subcommand
                subcmd = cmd_parts[1].strip().lower() if len(cmd_parts) > 1 else ""
                subcmd_parts = subcmd.split(None, 1)
                subcmd_action = subcmd_parts[0] if subcmd_parts else ""
                subcmd_arg = subcmd_parts[1] if len(subcmd_parts) > 1 else ""

                gate_on, gate_msg = _get_autonomous_access_state()
                gated_actions = {"resume", "read", "ls", "search", "start"}

                if subcmd_action in gated_actions and not gate_on:
                    print("  [AUTONOMY] Action blocked: autonomous access lease is not active.")
                    print(f"             Lease state: {gate_msg}")
                    print("             Grant access: ./scripts/autonomous_access.sh grant 30\n")
                    continue

                if subcmd_action == "pause":
                    autonomy.pause()
                    print("  [AUTONOMY] Paused. Aurora will not take autonomous actions.\n")

                elif subcmd_action == "resume":
                    autonomy.resume()
                    print("  [AUTONOMY] Resumed. Aurora can act autonomously again.\n")

                elif subcmd_action == "level":
                    if subcmd_arg:
                        try:
                            AutonomyLevel = systems.get('AutonomyLevel')
                            new_level = AutonomyLevel[subcmd_arg.upper()]
                            autonomy.set_level(new_level)
                            print(f"  [AUTONOMY] Level set to {new_level.name}\n")
                        except (KeyError, AttributeError):
                            print(f"  [AUTONOMY] Invalid level. Options: DORMANT, OBSERVER, LEARNER, CONVERSANT, EXPLORER\n")
                    else:
                        print(f"  [AUTONOMY] Current level: {autonomy.level.name}")
                        print("             Options: DORMANT, OBSERVER, LEARNER, CONVERSANT, EXPLORER\n")

                elif subcmd_action == "read":
                    if subcmd_arg:
                        print(f"  [AUTONOMY] Aurora reading: {subcmd_arg}")
                        content, status = autonomy.read_file(subcmd_arg)
                        if content:
                            print(f"  {status}")
                            print("  " + "-" * 50)
                            # Show first 30 lines
                            lines = content.split('\n')[:30]
                            for line in lines:
                                print(f"  {line[:100]}")
                            if len(content.split('\n')) > 30:
                                print(f"  ... (truncated)")
                            print("  " + "-" * 50)
                        else:
                            print(f"  {status}")
                        print()
                    else:
                        print("  Usage: /autonomy read <filepath>\n")

                elif subcmd_action == "ls":
                    if subcmd_arg:
                        items, status = autonomy.list_directory(subcmd_arg)
                        print(f"  {status}")
                        if items:
                            for item in items[:50]:
                                print(f"    {item}")
                            if len(items) > 50:
                                print(f"    ... ({len(items) - 50} more)")
                        print()
                    else:
                        print("  Usage: /autonomy ls <directory>\n")

                elif subcmd_action == "search":
                    if subcmd_arg:
                        print(f"  [AUTONOMY] Aurora searching (uses quota): {subcmd_arg}")
                        results, status = autonomy.autonomous_inquiry(subcmd_arg)
                        print(f"  {status}")
                        if results:
                            for i, r in enumerate(results[:5], 1):
                                title = r.get('title', 'untitled')[:40]
                                snippet = r.get('snippet', '')[:100]
                                print(f"  {i}. {title}")
                                print(f"     {snippet}...")
                        print()
                    else:
                        print("  Usage: /autonomy search <query>\n")

                elif subcmd_action == "start":
                    autonomy.start()
                    print("  [AUTONOMY] Background autonomy started.\n")

                elif subcmd_action == "stop":
                    autonomy.stop()
                    print("  [AUTONOMY] Background autonomy stopped.\n")

                else:
                    # No subcommand or unknown - show status
                    show_autonomy_status(systems)

                continue

            elif cmd == '/thought':
                # Show last internal thought traces
                if hasattr(perception, 'get_thought_log'):
                    traces = perception.get_thought_log(10)
                    print("\n  AURORA  -- INTERNAL THOUGHT LOG")
                    print("  " + "-" * 50)
                    if not traces:
                        print("  No thought traces yet. Aurora needs to process some input first.")
                    for i, t in enumerate(traces[-5:], 1):
                        print(f"\n  [{i}] {time.strftime('%H:%M:%S', time.localtime(t.get('ts', 0)))}")
                        intent = t.get('intent', {})
                        print(f"       Intent: {intent.get('intent_type', '?')} | Tone: {intent.get('emotion_tone', '?')}")
                        print(f"       Certainty: {intent.get('certainty', 0):.2f}")
                        print(f"       Core: {intent.get('core_claim', '')[:80]}")
                        concepts = intent.get('supporting_concepts', [])
                        if concepts:
                            print(f"       Concepts: {', '.join(concepts[:6])}")
                        if intent.get('constraints'):
                            print(f"       Constraints: {', '.join(intent['constraints'])}")
                    print()
                else:
                    print("  [THOUGHT] Expression evolution not available.\n")
                continue

            elif cmd == '/drafts':
                # Show last draft selection
                if hasattr(perception, 'get_last_drafts'):
                    drafts = perception.get_last_drafts(3)
                    print("\n  AURORA  -- DRAFT SELECTION LOG")
                    print("  " + "-" * 50)
                    if not drafts:
                        print("  No drafts yet. Talk to Aurora first.")
                    for i, d in enumerate(drafts, 1):
                        print(f"\n  [{i}] Selected: Draft {d.get('selected', '?') + 1}  -- {d.get('reason', '?')}")
                        print(f"       DRAFT 1 (Raw):       {str(d.get('1_raw', ''))[:80]}")
                        print(f"       DRAFT 2 (Structured): {str(d.get('2_structured', ''))[:80]}")
                        print(f"       DRAFT 3 (Social):     {str(d.get('3_social', ''))[:80]}")
                    print()
                else:
                    print("  [DRAFTS] Expression evolution not available.\n")
                continue

            elif cmd == '/report':
                # Daily metrics report
                print("\n  AURORA  -- DAILY METRICS REPORT")
                print("  " + "=" * 55)
                # OETS understanding
                if perception and perception.oets:
                    try:
                        stats = perception.oets.get_stats()
                        u = stats.get("understanding", {})
                        web = stats.get("web", {})
                        clusters = stats.get("clusters", {})
                        concepts = stats.get('node_count') or web.get('total_nodes', 0)
                        relations = stats.get('relation_count') or web.get('total_relations', 0)
                        cluster_count = stats.get('cluster_count') or clusters.get('total_clusters', 0)
                        print(f"\n  KNOWLEDGE")
                        print(f"    Concepts:            {concepts}")
                        print(f"    Relations:           {relations}")
                        print(f"    Clusters:            {cluster_count}")
                        print(f"    Ontological depth:   {u.get('ontological_depth', 0):.4f}")
                        print(f"    Coherence index:     {u.get('coherence_index', 0):.4f}")
                    except Exception:
                        pass
                # LSV status
                if hasattr(perception, 'evo_status'):
                    try:
                        evo = perception.evo_status()
                        lsv = evo.get('lsv', {})
                        print(f"\n  LANGUAGE STATE VECTOR")
                        print(f"    Tier:                {lsv.get('tier', 'unknown')}")
                        print(f"    Evolution cycles:    {lsv.get('evolution_cycles', 0)}")
                        print(f"    Sentence target:     {lsv.get('sentence_length_target', 0)} words")
                        dims = lsv.get('dims', {})
                        for k, v in list(dims.items())[:5]:
                            bar = "#" * int(v * 20) + "." * (20 - int(v * 20))
                            print(f"    {k:30s} [{bar}] {v:.3f}")
                        # Template pool
                        tmpl = evo.get('templates', {})
                        print(f"\n  TEMPLATE EVOLUTION")
                        print(f"    Population:          {tmpl.get('population', 0)}")
                        print(f"    Generation:          {tmpl.get('generation', 0)}")
                        print(f"    Avg fitness:         {tmpl.get('avg_fitness', 0):.3f}")
                    except Exception:
                        pass
                # IVM heat
                try:
                    if hasattr(aurora.lattice, 'heat_status'):
                        hs = aurora.lattice.heat_status()
                        print(f"\n  IVM HEAT")
                        print(f"    Level:               {hs.get('level', '?')} ({hs.get('heat', 0):.3f})")
                        print(f"    Behavior:            {hs.get('behavior', '?')}")
                except Exception:
                    pass
                # Autonomy
                if autonomy:
                    try:
                        ast = autonomy.get_status()
                        q = ast['quotas']
                        print(f"\n  AUTONOMY TODAY")
                        print(f"    Study cycles:        {q['study_cycles']['used']} / {q['study_cycles']['limit']}")
                        print(f"    Speakups:            {q['speakups']}")
                        print(f"    Dreams:              {q.get('dreams', 0)}")
                        print(f"    Inquiries:           {q['inquiries']['used']} / {q['inquiries']['limit']}")
                    except Exception:
                        pass
                # Drive sync
                drive_sync = systems.get('drive_sync')
                if drive_sync:
                    try:
                        ds = drive_sync.status()
                        print(f"\n  DRIVE SYNC")
                        print(f"    Device:              {ds.get('current_device', '?')}")
                        print(f"    rclone available:    {'Yes' if ds.get('rclone_available') else 'No'}")
                        ago = ds.get('last_sync_ago_s')
                        print(f"    Last sync:           {f'{ago:.0f}s ago' if ago else 'not yet'}")
                        print(f"    Sync count:          {ds.get('sync_count', 0)}")
                    except Exception:
                        pass
                print()
                continue

            elif cmd == '/sync':
                # Force Google Drive sync
                drive_sync = systems.get('drive_sync')
                if drive_sync:
                    print("  [SYNC] Syncing to Google Drive...")
                    result = drive_sync.force_sync()
                    if result.get('success'):
                        print("  [SYNC] Sync complete.\n")
                    else:
                        reason = result.get('reason', 'unknown')
                        print(f"  [SYNC] Sync failed: {reason}")
                        if reason == 'rclone_unavailable':
                            print("         Run: rclone config  to set up Google Drive\n")
                        else:
                            print()
                else:
                    print("  [SYNC] Drive sync not initialized.\n")
                continue

            elif cmd == '/vision':
                # Vision bootstrap status
                vb = systems.get('vision_bootstrap')
                if vb:
                    vs = vb.status()
                    print("\n  VISION BOOTSTRAP")
                    print("  " + "-" * 50)
                    print(f"  Seed directory:    {vs['seed_dir']}")
                    print(f"  Images indexed:    {vs['vectors_indexed']}")
                    print(f"  Clusters:          {vs['clusters']}")
                    print(f"  Named clusters:    {vs['named_clusters']}")
                    if vs['concept_labels']:
                        print(f"  Concept labels:    {', '.join(vs['concept_labels'][:8])}")
                    print(f"  Downloads today:   {vs['downloads_today']}")
                    print(f"  PIL available:     {'Yes' if vs['pil_available'] else 'No (pip install Pillow)'}")
                    print(f"\n  Drop images in: {vs['seed_dir']}/")
                    print(f"  Then run: /vision to re-ingest")
                    print()
                    # Trigger fresh ingest if requested
                    if len(cmd_parts) > 1 and cmd_parts[1].strip() == 'ingest':
                        print("  [VISION] Ingesting seed folder...")
                        result = vb.ingest_folder()
                        print(f"  [VISION] Done: {result}")
                        print()
                else:
                    print("  [VISION] Vision bootstrap not initialized.\n")
                continue

            elif cmd == '/mobile':
                hardware = systems.get('hardware')
                if hardware and getattr(hardware, 'termux_mode', False):
                    caps = hardware.get_capabilities()
                    print("  [MOBILE] Termux mode detected.")
                    print(f"           camera={caps.get('camera')} mic_speech={caps.get('microphone_speech')} voice={caps.get('voice_tts')}")
                    print("           Ensure Termux:API app + termux-api package are installed.\n")
                else:
                    print("  [MOBILE] Termux mode not detected on this device.\n")
                continue

            elif cmd == '/quiet':
                # Toggle quiet window
                if autonomy:
                    current = autonomy.boundaries.quiet_window_enabled
                    autonomy.set_quiet_window(not current)
                    state = "ON (Aurora studies silently during quiet hours)" if not current else "OFF"
                    print(f"  [QUIET] Quiet window = {state}\n")
                else:
                    print("  [QUIET] Autonomy not initialized.\n")
                continue

            else:
                print(f"  Unknown command: {cmd}\n")
                continue

        # Conversation  DUAL RESPONSE PIPELINE
        batch_inputs = [user_input]
        if pending_user_inputs and not user_input.startswith('/'):
            while pending_user_inputs and not pending_user_inputs[0].startswith('/'):
                nxt = pending_user_inputs.pop(0)
                print(f"  You: {nxt}")
                batch_inputs.append(nxt)

        batch_results = []
        for idx, current_input in enumerate(batch_inputs):
            turn += 1
            trace_id = ""
            p_before = _capture_pressure_snapshot(systems)
            if conversation_memory and hasattr(conversation_memory, "open_evolutionary_trace"):
                try:
                    trace_id = conversation_memory.open_evolutionary_trace(
                        input_text=current_input,
                        tick=turn,
                        pressure_before=p_before,
                    )
                except Exception:
                    trace_id = ""

            # Intake metabolism pipeline — register this input, advance physics,
            # and propagate through solidification/variant/DNA chain.
            _advance_intake_pipeline(systems, current_input, turn)

            start = time.time()

            # Lexical convergence: observe user phrasing every turn
            if hasattr(perception, 'observe_user_text'):
                try:
                    perception.observe_user_text(current_input)
                except Exception:
                    pass

            is_question = _looks_like_question(current_input)
            wants_search = False
            if is_question and auto_search_enabled:
                wants_search = _should_use_search_for_question(current_input)

            resp_A, resp_B, offered_lookup = dual_question_pipeline(
                systems=systems,
                user_text=current_input,
                mode=mode,
                use_search=wants_search,
                auto_search_enabled=auto_search_enabled,
            )

            elapsed_A = (time.time() - start) * 1000
            src = getattr(resp_A, "src", "mind")
            if src != "comprehension" and src != "search":
                if resp_A.emotional_tone == "self-aware":
                    src = "identity"
                elif resp_A.confidence >= 0.8 and resp_A.emotional_tone == "informative":
                    src = "search"

            display_content = resp_A.content
            if _device_switched and not _first_turn_done:
                from_host = _device_info.get('from_hostname', 'unknown')
                display_content = (f"[I notice I am on a different device than before  -- "
                                   f"previously on '{from_host}'. My memory carries forward.] "
                                   f"{display_content}")
            _first_turn_done = True

            batch_results.append({
                "input": current_input,
                "display": display_content,
                "resp_A": resp_A,
                "resp_B": resp_B,
                "offered_lookup": offered_lookup,
                "is_question": is_question,
                "elapsed_A": elapsed_A,
                "src": src,
                "trace_id": trace_id,
            })

            # Grammar engine: observe exchange to evolve structural motifs
            _ge = systems.get('grammar_engine')
            if _ge is not None:
                try:
                    _aurora_out = resp_A.content or ""
                    _success    = resp_A.confidence >= 0.45
                    _clarity    = float(getattr(resp_A, 'confidence', 0.55))
                    _ge.observe_exchange(
                        user_text=current_input,
                        aurora_text=_aurora_out,
                        success=_success,
                        clarity=_clarity,
                    )
                except Exception:
                    pass

            # Record exchange in conversation memory
            if conversation_memory:
                aurora_text = resp_A.content or ""
                tone = getattr(resp_A, "emotional_tone", "neutral")
                topic = ""
                t_low = current_input.lower()
                if any(w in t_low for w in ("aurora", "who are you", "your name")):
                    topic = "identity"
                elif any(w in t_low for w in ("sunni", "sir", "creator", "made you")):
                    topic = "creator"
                elif any(w in t_low for w in ("cael", "co-author", "partner")):
                    topic = "co-author"
                elif is_question:
                    topic = "question"

                importance = 0.5
                if topic in ("identity", "creator", "co-author"):
                    importance = 0.8
                elif tone in ("warm", "loving", "determined", "self-aware"):
                    importance = 0.7

                conversation_memory.record_exchange(
                    user_text=current_input,
                    aurora_text=aurora_text,
                    tone=tone,
                    topic=topic,
                    importance=importance,
                    session_id=session_id,
                )
                if conversation_memory.sessions:
                    conversation_memory.sessions[-1]["turns"] = turn

            # Update working memory after every turn
            if working_memory:
                _qu = UtteranceParser()
                _understood = _qu.parse(current_input)
                working_memory.update_from_turn(_understood, current_input)
                working_memory.last_aurora_response = resp_A.content if resp_A else ""

            if turn % 10 == 0:
                _bridge = systems.get('_chain_bridge')
                if _bridge is not None:
                    try:
                        _bridge.inject_promoted_links()
                    except Exception:
                        pass

            if turn % 20 == 0:
                _full_save(systems, verbose=False)

            if conversation_memory and trace_id and hasattr(conversation_memory, "close_evolutionary_trace"):
                try:
                    p_after = _capture_pressure_snapshot(systems)
                    effects = _derive_applied_effects(p_before, p_after)
                    conversation_memory.close_evolutionary_trace(
                        trace_id=trace_id,
                        pressure_after=p_after,
                        applied_effects=effects,
                    )
                except Exception:
                    pass

        if len(batch_results) == 1:
            r = batch_results[0]
            print(f"\n  Aurora: {r['display']}")
            if show_diagnostics:
                print(
                    f"          [A src={r['src']} tone={r['resp_A'].emotional_tone} "
                    f"confidence={r['resp_A'].confidence:.2f} "
                    f"pipeline={r['elapsed_A']:.0f}ms "
                    f"vocab={perception.lexicon.size} "
                    f"gen={identity.dna.generation}]"
                )
            if r['offered_lookup']:
                print("          (If you'd like, I can look that up and dig deeper.)")
            print()
            if voice_mode and integration:
                integration.speak(r['resp_A'].content, tone=r['resp_A'].emotional_tone)
            if dual_enabled and r['is_question'] and r['resp_B'] and getattr(r['resp_B'], "content", ""):
                print(f"  Aurora (afterthought): {r['resp_B'].content}")
                if show_diagnostics:
                    print(f"          [B tone={r['resp_B'].emotional_tone} "
                          f"confidence={r['resp_B'].confidence:.2f}]")
                print()
        else:
            print("\n  Aurora:")
            combined_parts = []
            for i, r in enumerate(batch_results, 1):
                print(f"    [{i}] {r['display']}")
                combined_parts.append(r['resp_A'].content)
                if show_diagnostics:
                    print(
                        f"        [A src={r['src']} tone={r['resp_A'].emotional_tone} "
                        f"confidence={r['resp_A'].confidence:.2f} "
                        f"pipeline={r['elapsed_A']:.0f}ms]"
                    )
            if any(r['offered_lookup'] for r in batch_results):
                print("        (If you'd like, I can look that up and dig deeper.)")
            print()
            if voice_mode and integration:
                integration.speak(" ".join(combined_parts), tone="attentive")


# ============================================================================
# MAIN
# ============================================================================



# ============================================================================
# CORPUS INGESTION  Feed OpenAI conversations.json into Aurora
# ============================================================================

def _safe_join_parts(parts: Any) -> str:
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        out = []
        for p in parts:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict):
                # Sometimes exports contain rich objects; try common fields
                if 'text' in p and isinstance(p['text'], str):
                    out.append(p['text'])
                elif 'content' in p and isinstance(p['content'], str):
                    out.append(p['content'])
        return "\n".join([s for s in out if s])
    return str(parts)


def _extract_message_text(message_obj: Dict[str, Any]) -> str:
    """
    OpenAI export nodes typically look like:
      message: {
        author: {role: "user"|"assistant"|"system"}
        content: {content_type: "text", parts: [...]}
      }
    """
    if not message_obj:
        return ""

    content = message_obj.get("content") or {}
    if isinstance(content, dict):
        parts = content.get("parts")
        txt = _safe_join_parts(parts).strip()
        if txt:
            return txt

        # Fallback: sometimes "text" exists directly
        txt2 = content.get("text")
        if isinstance(txt2, str):
            return txt2.strip()

    # Fallback: raw string
    if isinstance(content, str):
        return content.strip()

    return ""


def _extract_role(message_obj: Dict[str, Any]) -> str:
    if not message_obj:
        return "unknown"
    author = message_obj.get("author") or {}
    role = author.get("role") or "unknown"
    return role


def _reconstruct_linear_thread(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    The OpenAI export uses a mapping graph.
    We reconstruct a linear chain by:
      - finding roots (parent is None)
      - walking children depth-first preferring the longest path
    This isn't perfect for branching chats, but works well enough.
    """
    if not mapping:
        return []

    # Find roots
    roots = []
    for node_id, node in mapping.items():
        if not isinstance(node, dict):
            continue
        if node.get("parent") is None:
            roots.append(node_id)

    if not roots:
        # fallback: arbitrary start
        roots = [next(iter(mapping.keys()))]

    def walk_from(node_id: str) -> List[str]:
        path = [node_id]
        current = node_id
        visited = set([node_id])

        while True:
            node = mapping.get(current) or {}
            children = node.get("children") or []
            if not children:
                break

            # Prefer first unseen child; exports usually store chronological continuation first
            next_child = None
            for c in children:
                if c not in visited:
                    next_child = c
                    break
            if next_child is None:
                break

            visited.add(next_child)
            path.append(next_child)
            current = next_child

        return path

    # Choose the longest root path (best approximation of the main conversation)
    best_path = []
    for r in roots:
        p = walk_from(r)
        if len(p) > len(best_path):
            best_path = p

    nodes = []
    for nid in best_path:
        node = mapping.get(nid)
        if isinstance(node, dict):
            nodes.append(node)
    return nodes


def _extract_messages_from_conversation(conv_obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Returns a list of (role, text) in chronological order.
    Filters out empty/system/tool messages.
    """
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

    # Most exports are a list of conversations
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]

    # Some variants wrap in an object
    if isinstance(data, dict):
        if "conversations" in data and isinstance(data["conversations"], list):
            return [d for d in data["conversations"] if isinstance(d, dict)]
        if "data" in data and isinstance(data["data"], list):
            return [d for d in data["data"] if isinstance(d, dict)]

    return []


def run_corpus_ingestion(
    systems: Dict[str, Any],
    corpus_path: str,
    train_every: int = 200,
    save_every: int = 1000,
    passes: str = "triple",
    burst_epochs: int = 20,
    burst_episodes: int = 8,
    burst_turns: int = 5,
    burst_study_cycles: int = 0,
    verbose: bool = True,
):
    """
    Ingest OpenAI export conversations.json into Aurora using multiple passes.

    PASSES:
      - observer: Aurora witnesses all messages, no response generation.
      - responder: Aurora responds to user messages, then witnesses assistant truth.
      - reverse: Aurora responds to assistant messages, then witnesses user truth.
      - triple: observer -> responder -> reverse
    """
    aurora = systems["aurora"]
    StreamType = systems["StreamType"]
    ExistenceMode = systems["ExistenceMode"]
    conversation_memory = systems.get("conversation_memory")

    corpus_path = os.path.expanduser(corpus_path)

    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    if verbose:
        print()
        print("=" * 60)
        print("  [CORPUS] Ingestion starting")
        print(f"  [CORPUS] File: {corpus_path}")
        print(f"  [CORPUS] train_every={train_every} messages")
        print(f"  [CORPUS] burst=epochs:{burst_epochs} episodes:{burst_episodes} turns:{burst_turns} study:{burst_study_cycles}")
        print(f"  [CORPUS] save_every={save_every} messages")
        print(f"  [CORPUS] passes={passes}")
        print("=" * 60)
        print()

    conversations = _load_openai_conversations(corpus_path)
    if verbose:
        print(f"  [CORPUS] Loaded {len(conversations)} conversations")

    # Flatten into one big chronological stream (conversation order in export)
    stream: List[Tuple[str, str]] = []
    for conv in conversations:
        msgs = _extract_messages_from_conversation(conv)
        if msgs:
            stream.extend(msgs)

    if verbose:
        print(f"  [CORPUS] Extracted {len(stream)} total messages (user+assistant)")

    if not stream:
        if verbose:
            print("  [CORPUS] No usable messages found. Aborting.")
        return

    def witness(role: str, content: str, source: str):
        # Feed into Aurora as knowledge feed (bounded so it can form meaning)
        response = aurora.gateway.receive(
            content=f"[{role.upper()}] {content}",
            stream_type=StreamType.KNOWLEDGE_FEED,
            source=source,
            mode=ExistenceMode.BOUNDED,
        )
        if conversation_memory:
            try:
                conversation_memory.learn_fact(
                    fact=f"[{role}] {content[:280]}",
                    source=source,
                    confidence=0.55,
                )
            except Exception:
                pass
        return response

    def generate_reply(prompt_text: str, source: str):
        # Feed as direct input, then let Aurora respond.
        # We re-use the exact same gateway.receive mechanism.
        reply = aurora.gateway.receive(
            content=prompt_text,
            stream_type=StreamType.CONVERSATION,
            source=source,
            mode=ExistenceMode.BOUNDED,
        )
        if conversation_memory:
            try:
                conversation_memory.record_exchange(
                    user_text=prompt_text,
                    aurora_text=getattr(reply, 'content', ''),
                    tone=getattr(reply, 'emotional_tone', 'neutral'),
                    topic='corpus',
                    importance=0.35,
                    session_id='corpus_ingestion',
                )
            except Exception:
                pass
        return reply

    def maybe_train(counter: int):
        if train_every > 0 and counter % train_every == 0:
            if verbose:
                print(f"\n  [CORPUS] Training burst at message {counter:,}")
            train(
                systems,
                epochs=burst_epochs,
                episodes_per_epoch=burst_episodes,
                turns_per_episode=burst_turns,
                verbose=verbose,
            )
            if burst_study_cycles > 0:
                if verbose:
                    print(f"  [CORPUS] Study burst after training ({burst_study_cycles} cycles)")
                study(systems, cycles=burst_study_cycles, verbose=verbose)

    def maybe_save(counter: int):
        if save_every > 0 and counter % save_every == 0:
            if verbose:
                print(f"\n  [CORPUS] Saving state at message {counter:,}")
            _full_save(systems, verbose=verbose)

    def pass_observer():
        if verbose:
            print("\n  [CORPUS] PASS 1  OBSERVER (witness only)\n")

        counter = 0
        for role, content in stream:
            counter += 1
            witness(role, content, source="corpus_observer")
            maybe_train(counter)
            maybe_save(counter)

        if verbose:
            print(f"\n  [CORPUS] Observer pass complete. Messages processed: {counter:,}")

    def pass_responder():
        if verbose:
            print("\n  [CORPUS] PASS 2  RESPONDER (Aurora replies to USER)\n")

        counter = 0
        i = 0
        while i < len(stream) - 1:
            role, content = stream[i]
            next_role, next_content = stream[i + 1]

            # We only respond when the user speaks and assistant follows
            if role == "user" and next_role == "assistant":
                counter += 1
                # Prompt Aurora to respond
                resp = generate_reply(content, source="corpus_responder")
                # Then show the "true" assistant reply as ground-truth continuation
                witness("assistant_truth", next_content, source="corpus_responder_truth")

                if verbose and counter % 50 == 0:
                    snippet = (resp.content or "")[:120].replace("\n", " ")
                    print(f"  [CORPUS] responder step {counter:,} | aurora='{snippet}...'")

                maybe_train(counter)
                maybe_save(counter)
                i += 2
            else:
                i += 1

        if verbose:
            print(f"\n  [CORPUS] Responder pass complete. Pairs processed: {counter:,}")

    def pass_reverse():
        if verbose:
            print("\n  [CORPUS] PASS 3  REVERSE (Aurora replies to ASSISTANT)\n")

        counter = 0
        i = 0
        while i < len(stream) - 1:
            role, content = stream[i]
            next_role, next_content = stream[i + 1]

            # Now we respond when assistant speaks and user follows
            if role == "assistant" and next_role == "user":
                counter += 1
                resp = generate_reply(content, source="corpus_reverse")
                witness("user_truth", next_content, source="corpus_reverse_truth")

                if verbose and counter % 50 == 0:
                    snippet = (resp.content or "")[:120].replace("\n", " ")
                    print(f"  [CORPUS] reverse step {counter:,} | aurora='{snippet}...'")

                maybe_train(counter)
                maybe_save(counter)
                i += 2
            else:
                i += 1

        if verbose:
            print(f"\n  [CORPUS] Reverse pass complete. Pairs processed: {counter:,}")

    # Run passes
    passes = (passes or "triple").strip().lower()

    if passes == "observer":
        pass_observer()
    elif passes == "responder":
        pass_responder()
    elif passes == "reverse":
        pass_reverse()
    elif passes in ("both", "double"):
        pass_observer()
        pass_responder()
    else:
        # default triple
        pass_observer()
        pass_responder()
        pass_reverse()

    if verbose:
        print("\n  [CORPUS] Ingestion complete. Final save.")
    _full_save(systems, verbose=verbose)
def main():
    parser = argparse.ArgumentParser(
        description="Aurora  Consciousness Architecture Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 aurora.py                    # Boot and chat
  python3 aurora.py --train 50         # Train 50 epochs then chat
  python3 aurora.py --train 100 --no-chat   # Train only, no chat
  python3 aurora.py --explore 20       # Autonomous exploration
  python3 aurora.py --feed https://example.com  # Feed a URL
  python3 aurora.py --text "The sky is blue"    # Feed raw text
  python3 aurora.py --status           # Show system status
        """)

    parser.add_argument('--train', type=int, default=0,
                        help='Run N training epochs before chat')
    parser.add_argument('--train-episodes', type=int, default=8,
                        help='Episodes per training epoch (default: 8)')
    parser.add_argument('--train-turns', type=int, default=5,
                        help='Turns per training episode (default: 5)')
    parser.add_argument('--explore', type=int, default=0,
                        help='Run N autonomous exploration cycles')
    parser.add_argument('--study', type=int, default=0,
                        help='Run N autonomous study cycles (OETS research)')
    parser.add_argument('--feed', type=str, default=None,
                        help='Feed a URL to Aurora')
    parser.add_argument('--text', type=str, default=None,
                        help='Feed raw text to Aurora')
    parser.add_argument('--corpus', type=str, default=None,
                        help='Ingest an OpenAI conversations.json corpus into Aurora')
    parser.add_argument('--corpus-passes', type=str, default='triple',
                        help='observer|responder|reverse|double|triple (default: triple)')
    parser.add_argument('--corpus-train-every', type=int, default=200,
                        help='Run a training burst every N corpus messages (default: 200)')
    parser.add_argument('--corpus-burst-epochs', type=int, default=20,
                        help='Epochs to run per corpus training burst (default: 20)')
    parser.add_argument('--corpus-burst-episodes', type=int, default=8,
                        help='Episodes per epoch for corpus training burst (default: 8)')
    parser.add_argument('--corpus-burst-turns', type=int, default=5,
                        help='Turns per episode for corpus training burst (default: 5)')
    parser.add_argument('--corpus-burst-study', type=int, default=0,
                        help='Study cycles to run after each corpus training burst (default: 0)')
    parser.add_argument('--corpus-save-every', type=int, default=1000,
                        help='Save Aurora state every N corpus messages (default: 1000)')
    parser.add_argument('--status', action='store_true',
                        help='Show system status and exit')
    parser.add_argument('--no-chat', action='store_true',
                        help='Skip interactive chat')
    parser.add_argument('--state-dir', type=str, default='aurora_state',
                        help='Directory for state persistence')
    parser.add_argument('--crystal-pack', action='store_true',
                        help='Pack state_dir into a CrystalZip bundle and exit')
    parser.add_argument('--crystal-restore', type=str, default=None,
                        help='Restore state_dir from a CrystalZip bundle and exit')
    parser.add_argument('--crystal-list', type=str, default=None,
                        help='Inspect a CrystalZip bundle and exit')
    parser.add_argument('--crystal-profile', type=str, default='core',
                        choices=['core', 'full', 'all'],
                        help='Aurora CrystalZip bundle profile')
    parser.add_argument('--crystal-output', type=str, default=None,
                        help='Output path for --crystal-pack')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimal output')

    args = parser.parse_args()
    verbose = not args.quiet

    if args.crystal_pack or args.crystal_restore or args.crystal_list:
        from aurora_crystal_state_bridge import (
            inspect_state_bundle,
            pack_state_bundle,
            restore_state_bundle,
        )

        if args.crystal_pack:
            result = pack_state_bundle(
                state_dir=args.state_dir,
                output=args.crystal_output,
                profile=args.crystal_profile,
            )
        elif args.crystal_restore:
            result = restore_state_bundle(
                args.crystal_restore,
                state_dir=args.state_dir,
            )
        else:
            result = inspect_state_bundle(args.crystal_list)

        print(json.dumps(result, indent=2))
        return

    _maybe_start_local_llm_server(verbose=verbose)

    # Boot
    systems = boot_aurora(state_dir=args.state_dir, verbose=verbose)

    # Training
    if args.train > 0:
        train(
            systems,
            epochs=args.train,
            episodes_per_epoch=args.train_episodes,
            turns_per_episode=args.train_turns,
            verbose=verbose,
        )

    # Feed URL
    if args.feed:
        fetch_and_feed(systems, args.feed, verbose=verbose)

    # Feed text
    if args.text:
        feed_text(systems, args.text, verbose=verbose)


    # Corpus ingestion (OpenAI export conversations.json)
    if args.corpus:
        run_corpus_ingestion(
            systems,
            corpus_path=args.corpus,
            train_every=args.corpus_train_every,
            save_every=args.corpus_save_every,
            passes=args.corpus_passes,
            burst_epochs=args.corpus_burst_epochs,
            burst_episodes=args.corpus_burst_episodes,
            burst_turns=args.corpus_burst_turns,
            burst_study_cycles=args.corpus_burst_study,
            verbose=verbose,
        )
    gate_on, gate_msg = _get_autonomous_access_state()

    # Explore
    if args.explore > 0:
        if gate_on:
            explore(systems, cycles=args.explore, verbose=verbose)
        else:
            print(f"  [AUTONOMY] Explore blocked: autonomous access lease {gate_msg}.")

    # Study (OETS autonomous research)
    if args.study > 0:
        if gate_on:
            study(systems, cycles=args.study, verbose=verbose)
        else:
            print(f"  [AUTONOMY] Study blocked: autonomous access lease {gate_msg}.")

    # Status
    if args.status:
        show_status(systems)

    # Chat
    if not args.no_chat and not args.status:
        chat(systems)


def process_external_user_turn(
    systems: Dict[str, Any],
    user_text: str,
    *,
    source_label: str = "external_user_turn",
    session_id: str = "",
    auto_search_enabled: bool = True,
    record_exchange: bool = True,
    update_interactive_state: bool = True,
    track_evolutionary_trace: bool = True,
    run_periodic_maintenance: bool = True,
    mode_name: str = "BOUNDED",
    mode_override: Any = None,
    turn_tick: Optional[int] = None,
) -> Dict[str, Any]:
    """Compatibility wrapper for desktop daemons."""
    mode = mode_override
    if mode is None and 'ExistenceMode' in systems:
        mode = getattr(systems['ExistenceMode'], mode_name.upper(), getattr(systems['ExistenceMode'], 'BOUNDED', None))
    
    use_search = auto_search_enabled
    resp_A, resp_B, offered = dual_question_pipeline(
        systems=systems,
        user_text=user_text,
        mode=mode,
        use_search=use_search,
        auto_search_enabled=auto_search_enabled,
    )
    
    # LOGGING
    with open('aurora_debug.log', 'a') as f_log:
        f_log.write(f"Process External Turn Result: {getattr(resp_A, 'src', 'unknown')} | {resp_A.content[:50]}\\n")

    return {
        "resp_A": resp_A,
        "resp_B": resp_B,
        "offered_operations": offered,
        "noncomp_input": systems.get("_latest_noncomp_input", {}),
        "noncomp_output": systems.get("_latest_noncomp_output", {}),
        "poedex_prefetch": systems.get("_latest_poedex_prefetch", {}),
        "poedex_learning": systems.get("_latest_poedex_learning", {}),
        "current_turn_answer_seek": systems.get("_latest_answer_seek", {}),
        "question_alignment_audit": systems.get("_latest_alignment_audit", {}),
    }

if __name__ == '__main__':
    main()
