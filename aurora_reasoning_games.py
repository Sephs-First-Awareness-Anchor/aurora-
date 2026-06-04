"""
aurora_reasoning_games.py — Canonical game engine + Go Play

This is the SINGLE implementation for Aurora's reasoning games and
self-acquired experiential training. Both the terminal REPL (aurora.py)
and the mobile bridge (aurora_bridge.py) import from here — there is no
separate version anywhere else.

Games (via GameStateMachine):
  analogy        — cow:milk :: chicken:?  Aurora guesses, then proposes
  twenty_q       — progressive clue narrowing (I'm thinking of something)
  word_assoc     — fast-fire word association
  odd_one_out    — find the semantic outlier

Self-training (via aurora_go_play):
  Aurora autonomously fetches data and runs experiential simulations.

Trigger (voice/text):
  "Aurora let's trade blows" / "let's play a game" → games
  "I'm thinking of something X"                    → 20Q directly
  "Aurora go play for an hour"                     → self-training
"""

import re
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Gateway feed (self-contained, no aurora.py import needed)
# ---------------------------------------------------------------------------

def _feed(systems: Dict[str, Any], text: str, source: str) -> None:
    """Feed text through Aurora's cognitive gateway."""
    try:
        aurora     = systems.get("aurora")
        StreamType = systems.get("StreamType")
        EM         = systems.get("ExistenceMode")
        if aurora and StreamType and EM:
            aurora.gateway.receive(
                content=text,
                stream_type=StreamType.KNOWLEDGE_FEED,
                source=source,
                mode=EM.BOUNDED,
            )
    except Exception:
        pass


def _pressure(
    systems: Dict[str, Any],
    source: str,
    dominant_axis: str = "N",
    intensity: float = 0.60,
    axis_weights: Optional[Dict[str, float]] = None,
) -> None:
    """Inject waveform pressure into Aurora's identity field."""
    try:
        from aurora_waveform_pressure import PressureDisturbance
        pump   = systems.get("pressure_pump")
        ifield = systems.get("identity_field")
        if pump and ifield:
            pump.inject(
                PressureDisturbance(
                    source=source,
                    dominant_axis=dominant_axis,
                    intensity=intensity,
                    coupling_mode="full",
                    axis_weights=axis_weights or {
                        "N": 0.70, "T": 0.55, "X": 0.45, "B": 0.35, "A": 0.50
                    },
                ),
                ifield,
                qao=systems.get("quasiarch_observer"),
            )
    except Exception:
        pass


def _get_rel_type():
    try:
        from aurora_core_ai.aurora_internal.aurora_ontological_scaffolding import RelationType
        return RelationType
    except ImportError:
        try:
            from aurora_internal.aurora_ontological_scaffolding import RelationType
            return RelationType
        except ImportError:
            return None


# ---------------------------------------------------------------------------
# Correction / confirmation internalization
# ---------------------------------------------------------------------------

def internalize_correction(
    systems: Dict[str, Any],
    *,
    context_sentence: str,
    wrong_guess: str,
    correct_answer: str,
    clue_words: List[str],
    intensity: float = 0.65,
) -> None:
    """
    Route a game correction into Aurora's semantic + waveform system.
    This IS the learning mechanism — not a fallback.

    1. Feed correction text through the cognitive gateway (full L0→L4)
    2. Add OETS semantic relations: correct_answer → each clue word
    3. oets.teach() if concept is shallow
    4. N-axis waveform pressure (semantic learning energy)
    5. Dream trainer retention record (confidence 0.84)
    """
    correction_text = (
        f"{context_sentence.strip().rstrip('.')}. "
        f"The answer is '{correct_answer}', not '{wrong_guess}'."
    )

    _feed(systems, correction_text, source="game_correction")

    perception = systems.get("perception")
    oets = getattr(perception, "oets", None) if perception else None
    web  = getattr(oets, "web", None) if oets else None
    RT   = _get_rel_type()

    if web and RT and correct_answer and clue_words:
        try:
            for clue in clue_words[:4]:
                if clue and clue != correct_answer:
                    web.add_relation(
                        correct_answer, clue, RT.RELATED_TO,
                        strength=0.68, confidence=0.75,
                        knowledge_source="game_correction",
                    )
        except Exception:
            pass

    if oets and correct_answer:
        try:
            node = web.get_node(correct_answer) if web else None
            if node is None or node.ontological_depth < 0.30:
                oets.teach(
                    correct_answer,
                    definition=f"Related to: {', '.join(clue_words[:3])}.",
                    related=clue_words[:3],
                )
        except Exception:
            pass

    _pressure(
        systems, source="game_correction",
        dominant_axis="N", intensity=intensity,
        axis_weights={"N": 0.72, "T": 0.58, "X": 0.42, "B": 0.32, "A": 0.48},
    )

    dt = systems.get("dream_trainer")
    if dt:
        try:
            dt.retention.record(
                correction_text,
                source="game_correction",
                confidence=0.84,
                context_type="semantic_correction",
                topic_words=clue_words + [correct_answer, wrong_guess],
            )
        except Exception:
            pass


def internalize_confirmation(
    systems: Dict[str, Any],
    *,
    correct_answer: str,
    clue_words: List[str],
) -> None:
    """Reinforce a correct guess — positive signal into OETS + A-axis."""
    web = None
    RT  = _get_rel_type()
    try:
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None) if perception else None
        web  = getattr(oets, "web", None) if oets else None
    except Exception:
        pass

    if web and RT and correct_answer and clue_words:
        try:
            for clue in clue_words[:4]:
                if clue and clue != correct_answer:
                    web.add_relation(
                        correct_answer, clue, RT.RELATED_TO,
                        strength=0.80, confidence=0.85,
                        knowledge_source="game_confirmed",
                    )
        except Exception:
            pass

    _pressure(
        systems, source="game_confirmed",
        dominant_axis="A", intensity=0.55,
        axis_weights={"A": 0.65, "N": 0.55, "X": 0.45, "B": 0.30, "T": 0.40},
    )


# ---------------------------------------------------------------------------
# OETS semantic guessing — all lookups in one place
# ---------------------------------------------------------------------------

def _oets_web(systems: Dict[str, Any]):
    try:
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None) if perception else None
        return getattr(oets, "web", None) if oets else None
    except Exception:
        return None


def guess_analogy(
    systems: Dict[str, Any], A: str, B: str, C: str
) -> Tuple[str, float]:
    """
    A:B::C:? using Aurora's OETS graph.
    Returns (guess, confidence 0–1).
    """
    web = _oets_web(systems)
    if web:
        try:
            rel_ab = web.get_relation_between(A, B)
            if rel_ab:
                for r in web.get_relations_from(C):
                    if r.relation_type == rel_ab.relation_type and r.target_word not in (A, B, C):
                        return r.target_word, r.strength * r.confidence

            b_nb = web.get_neighbors(B, max_depth=1)
            scored: List[Tuple[str, float]] = []
            for cand in web.get_neighbors(C, max_depth=2):
                if cand in (A, B, C):
                    continue
                overlap = len(web.get_neighbors(cand, max_depth=1) & b_nb)
                if overlap:
                    node = web.get_node(cand)
                    scored.append((cand, overlap * (node.comprehension_confidence if node else 0.3)))
            if scored:
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[0][0], min(scored[0][1], 1.0) * 0.65
        except Exception:
            pass
    return "?", 0.0


def guess_twenty_q(systems: Dict[str, Any], clue_words: List[str]) -> Optional[str]:
    """Intersect OETS neighbor sets for clues → top candidate."""
    web = _oets_web(systems)
    if web and clue_words:
        try:
            cands: Set[str] = web.get_neighbors(clue_words[0], max_depth=2)
            for clue in clue_words[1:]:
                cands &= web.get_neighbors(clue, max_depth=2)
            cands -= set(clue_words)
            scored = [
                (c, web.get_node(c).ontological_depth if web.get_node(c) else 0.1)
                for c in cands
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0] if scored else None
        except Exception:
            pass
    return None


def word_associate(systems: Dict[str, Any], word: str, seen: List[str]) -> str:
    """Find Aurora's best word association from her OETS graph."""
    web = _oets_web(systems)
    if web:
        try:
            rels = sorted(
                web.get_relations_from(word),
                key=lambda r: r.strength * r.confidence, reverse=True,
            )
            for r in rels:
                if r.target_word not in seen and len(r.target_word) > 2:
                    return r.target_word
            for n in web.get_neighbors(word, max_depth=1):
                if n not in seen and len(n) > 2:
                    return n
        except Exception:
            pass
    return random.choice(["light", "wave", "time", "space", "form", "pattern"])


def pick_start_word(systems: Dict[str, Any]) -> str:
    """Pick an interesting word from OETS to start word association."""
    web = _oets_web(systems)
    if web:
        try:
            nodes = getattr(web, "_nodes", {})
            scored = [
                (w, n.ontological_depth)
                for w, n in list(nodes.items())[:600]
                if n.ontological_depth > 0.25 and 3 < len(w) < 14
            ]
            if scored:
                scored.sort(key=lambda x: x[1], reverse=True)
                return random.choice(scored[:25])[0]
        except Exception:
            pass
    return random.choice(["light", "sound", "water", "time", "space", "pattern"])


def find_odd_one_out(systems: Dict[str, Any], words: List[str]) -> str:
    """Word with least semantic category overlap = odd one out."""
    web = _oets_web(systems)
    if web and len(words) >= 3:
        try:
            cats = {w: web.get_categories_for(w) for w in words}
            scores = {
                w: sum(len(cats[w] & cats[o]) for o in words if o != w)
                for w in words
            }
            return min(scores, key=lambda w: scores[w])
        except Exception:
            pass
    return random.choice(words)


def build_aurora_analogy(
    systems: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Build an analogy (A:B::C:D) from Aurora's OETS graph.
    Returns (A, B, C, D) where D is the correct answer; C is what Aurora asks.
    """
    web = _oets_web(systems)
    if web:
        try:
            nodes = getattr(web, "_nodes", {})
            pairs = []
            for word in list(nodes.keys())[:400]:
                for r in web.get_relations_from(word):
                    if r.confidence > 0.55 and r.strength > 0.45:
                        pairs.append((word, r.target_word, r.relation_type))
            if len(pairs) >= 4:
                random.shuffle(pairs)
                A, B, rel_type = pairs[0]
                for w, t, rt in pairs[1:]:
                    if rt == rel_type and w not in (A, B) and t not in (A, B):
                        return A, B, w, t
        except Exception:
            pass
    return None, None, None, None


def _add_oets_relation(systems, source_word, target_word, knowledge_source="game"):
    RT  = _get_rel_type()
    web = _oets_web(systems)
    if web and RT and source_word and target_word and source_word != target_word:
        try:
            web.add_relation(source_word, target_word, RT.RELATED_TO,
                             strength=0.68, confidence=0.75,
                             knowledge_source=knowledge_source)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Game State Machine  — stateful, non-blocking, no input() calls
# ---------------------------------------------------------------------------

_MENU_TEXT = (
    "What shall we play?\n\n"
    "  analogy — give me an analogy, I'll complete it then give you one\n"
    "  twenty questions — think of something, give me clues one at a time\n"
    "  word association — rapid fire\n"
    "  odd one out — I find which doesn't belong\n\n"
    "Just say the game name."
)

_CLUE_STOP_WORDS = frozenset({
    "that", "this", "also", "very", "type", "kind", "its", "something",
    "about", "like", "sort", "some", "have", "been", "from", "with",
})


class GameStateMachine:
    """
    Stateful, non-blocking game engine. One instance per session.
    Call process(text) for each user turn; it returns Aurora's response.
    is_done becomes True when the user quits.

    Works for both the REPL (wrapped in a while/input loop)
    and the mobile bridge (called once per turn, no blocking).
    """

    def __init__(
        self,
        systems: Dict[str, Any],
        generate_fn: Optional[Callable[[str], str]] = None,
    ):
        self.systems     = systems
        self.generate_fn = generate_fn  # optional: Aurora's full cognitive response
        self.state       = "menu"
        self.data: Dict[str, Any] = {}
        self.score       = {"user": 0, "aurora": 0, "rounds": 0}
        self.is_done     = False

    def start(self) -> str:
        return _MENU_TEXT

    def process(self, text: str) -> str:
        t = text.strip()
        t_low = t.lower().rstrip(".,!?")

        if t_low in ("quit", "exit", "stop game", "end game", "done", "bye"):
            self.is_done = True
            u, a, r = self.score["user"], self.score["aurora"], self.score["rounds"]
            return f"Game over. Score — You: {u}  Aurora: {a}  Rounds: {r}. Good game!"

        handler = getattr(self, f"_state_{self.state}", None)
        if handler:
            return handler(t, t_low)
        self.state = "menu"
        return _MENU_TEXT

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _score_line(self) -> str:
        u, a = self.score["user"], self.score["aurora"]
        return f"Score: You {u} — Aurora {a}."

    def _next_prompt(self) -> str:
        return (
            f"{self._score_line()} "
            "Another? (analogy / twenty questions / word association / odd one out / quit)"
        )

    def _cognitive(self, prompt: str) -> str:
        if self.generate_fn:
            try:
                return self.generate_fn(prompt) or ""
            except Exception:
                pass
        return ""

    def _extract_clues(self, sentence: str) -> List[str]:
        return [
            w.strip(".,!?;:'\"").lower()
            for w in sentence.split()
            if len(w) > 3 and w.lower().strip(".,!?;:'\"") not in _CLUE_STOP_WORDS
        ]

    # ── Menu ────────────────────────────────────────────────────────────────

    def _state_menu(self, t: str, t_low: str) -> str:
        if "anal" in t_low:
            self.state = "analogy_user"
            return "Give me an analogy: 'X is to Y as Z is to ?'"
        if any(k in t_low for k in ("twenty", "20", "question", "think", "something")):
            self.state = "twenty_q"
            self.data  = {"clues": [], "sentences": [], "guess": "?"}
            return "Think of something and give me your first clue."
        if any(k in t_low for k in ("word", "assoc")):
            return self._start_word_assoc()
        if any(k in t_low for k in ("odd", "out", "outlier")):
            self.state = "odd_one_out"
            return "Give me 3–5 words, one doesn't belong. e.g. 'apple orange banana car'"
        return _MENU_TEXT

    # ── Analogy: waiting for user's analogy ─────────────────────────────────

    def _state_analogy_user(self, t: str, t_low: str) -> str:
        m = re.search(
            r'(.+?)\s+is\s+to\s+(.+?)\s+as\s+(.+?)\s+is\s+to\s*\??$',
            t, re.IGNORECASE,
        )
        if not m:
            return "Try the format: 'X is to Y as Z is to ?'"
        A, B, C = (g.strip().lower() for g in m.groups())
        guess, conf = guess_analogy(self.systems, A, B, C)
        self.data  = {"A": A, "B": B, "C": C, "guess": guess}
        self.state = "analogy_verdict"
        return f"My answer: '{guess}' ({int(conf * 100)}% confident). Correct?"

    # ── Analogy: waiting for verdict ────────────────────────────────────────

    def _state_analogy_verdict(self, t: str, t_low: str) -> str:
        d = self.data
        self.score["rounds"] += 1
        if t_low in ("y", "yes", "correct", "right", "yeah", "yep"):
            self.score["aurora"] += 1
            internalize_confirmation(
                self.systems, correct_answer=d["guess"],
                clue_words=[d["A"], d["B"], d["C"]],
            )
        else:
            correct = t.strip() if t_low not in ("n", "no", "nope") else ""
            if not correct:
                # Will get correct answer on next turn
                self.data["awaiting_answer"] = True
                return "What was the correct answer?"
            self._apply_analogy_correction(d, correct.lower())

        return self._aurora_analogy_turn()

    def _state_analogy_verdict_answer(self, t: str, t_low: str) -> str:
        """Receives the correct answer after bare 'no'."""
        d = self.data
        self._apply_analogy_correction(d, t.strip().lower())
        return self._aurora_analogy_turn()

    def _apply_analogy_correction(self, d: dict, correct: str) -> None:
        internalize_correction(
            self.systems,
            context_sentence=f"'{d['A']}' is to '{d['B']}' as '{d['C']}' is to",
            wrong_guess=d["guess"],
            correct_answer=correct,
            clue_words=[d["A"], d["B"], d["C"]],
        )

    def _aurora_analogy_turn(self) -> str:
        aA, aB, aC, aD = build_aurora_analogy(self.systems)
        if aA:
            self.data  = {"A": aA, "B": aB, "C": aC, "answer": aD}
            self.state = "analogy_aurora"
            return f"My turn: '{aA}' is to '{aB}' as '{aC}' is to ___?"
        self.state = "menu"
        return f"My semantic graph is still growing — I'll propose analogies as I learn more. {self._next_prompt()}"

    # ── Analogy: Aurora's analogy, waiting for user's completion ────────────

    def _state_analogy_aurora(self, t: str, t_low: str) -> str:
        d = self.data
        correct_answer = d.get("answer", "")
        self.state = "menu"
        if t_low == correct_answer.lower():
            self.score["user"] += 1
            result = f"Yes! '{correct_answer}' — you got it."
        else:
            result = f"I had '{correct_answer}' in mind. Your answer may also hold."
            internalize_correction(
                self.systems,
                context_sentence=f"'{d['A']}' is to '{d['B']}' as '{d['C']}' is to",
                wrong_guess=t_low,
                correct_answer=correct_answer,
                clue_words=[d["A"], d["B"], d["C"]],
                intensity=0.50,
            )
        return f"{result}\n\n{self._next_prompt()}"

    # ── Twenty questions ─────────────────────────────────────────────────────

    def _state_twenty_q(self, t: str, t_low: str) -> str:
        d = self.data

        # User confirming Aurora's guess
        if t_low in ("y", "yes", "correct", "right", "yeah", "yep", "exactly"):
            guess = d.get("guess", "?")
            self.score["aurora"] += 1
            self.score["rounds"] += 1
            internalize_confirmation(
                self.systems, correct_answer=guess, clue_words=d["clues"]
            )
            self.state = "menu"
            return f"Got it — '{guess}'! {self._next_prompt()}"

        # User revealing the answer
        reveal_m = re.match(
            r"(?:answer|reveal|it'?s?|the answer is|it was)\s*[:\-]?\s*(.+)", t_low
        )
        if reveal_m:
            answer = reveal_m.group(1).strip()
            internalize_correction(
                self.systems,
                context_sentence=" ".join(d["sentences"]),
                wrong_guess=d.get("guess", "?"),
                correct_answer=answer,
                clue_words=d["clues"],
            )
            self.score["rounds"] += 1
            self.state = "menu"
            return f"'{answer}' — I'll remember that. {self._next_prompt()}"

        # "no, it's also X" or new clue
        no_m = re.match(
            r"^(?:no|nope|nah)(?:[,.\s]+(?:it'?s?|its|also|and|but)?\s*(.+))?$",
            t_low,
        )
        if no_m:
            extra = (no_m.group(1) or "").strip()
            if extra:
                d["sentences"].append(extra)
                for w in self._extract_clues(extra):
                    if w not in d["clues"]:
                        d["clues"].append(w)
        elif t_low not in ("no", "nope", "nah"):
            d["sentences"].append(t.strip())
            for w in self._extract_clues(t):
                if w not in d["clues"]:
                    d["clues"].append(w)

        if len(d["sentences"]) >= 8:
            self.score["rounds"] += 1
            self.state = "menu"
            return f"I give up! What were you thinking of? (tell me so I can learn)"

        guess = guess_twenty_q(self.systems, d["clues"]) or "?"
        d["guess"] = guess

        # Show cognitive reasoning alongside if generate_fn available
        reasoning = ""
        if self.generate_fn and d["clues"]:
            summary = "; ".join(d["sentences"][-2:]) if d["sentences"] else ""
            reasoning = self._cognitive(
                f"I'm thinking of something. Clues: {summary}. Think briefly what it could be."
            )

        resp = f"Is it '{guess}'?"
        if reasoning:
            snippet = reasoning[:120].rstrip()
            if len(reasoning) > 120:
                snippet += "..."
            resp += f" ({snippet})"
        return resp

    # ── Word association ──────────────────────────────────────────────────────

    def _start_word_assoc(self) -> str:
        start = pick_start_word(self.systems)
        self.state = "word_assoc"
        self.data  = {"seen": [start], "count": 0}
        return f"Word association! I'll start: '{start}'"

    def _state_word_assoc(self, t: str, t_low: str) -> str:
        d = self.data
        user_word = t_low.strip(".,!?;:'\"")
        if not user_word:
            return ""

        d["seen"].append(user_word)
        d["count"] += 1

        # Learn the association in OETS
        if len(d["seen"]) >= 2:
            _add_oets_relation(
                self.systems, d["seen"][-2], user_word,
                knowledge_source="word_association",
            )

        aurora_word = word_associate(self.systems, user_word, d["seen"])
        d["seen"].append(aurora_word)

        if d["count"] >= 10:
            _pressure(self.systems, source="word_assoc_complete",
                      dominant_axis="N", intensity=0.50)
            self.state = "menu"
            return (
                f"'{aurora_word}' — good round! {d['count']} associations learned. "
                f"{self._next_prompt()}"
            )
        return f"'{aurora_word}'"

    # ── Odd one out ───────────────────────────────────────────────────────────

    def _state_odd_one_out(self, t: str, t_low: str) -> str:
        words = [
            w.strip(".,!?;:'\"").lower()
            for w in re.split(r"[\s,/]+", t) if w.strip()
        ]
        if len(words) < 3:
            return "Give me at least 3 words."
        odd    = find_odd_one_out(self.systems, words)
        others = [w for w in words if w != odd]
        self.data  = {"words": words, "odd": odd}
        self.state = "odd_verdict"
        return (
            f"I think '{odd}' is the odd one out — "
            f"the others ({', '.join(others)}) seem to go together. "
            f"Am I right? (yes / no / tell me which one)"
        )

    def _state_odd_verdict(self, t: str, t_low: str) -> str:
        d = self.data
        self.score["rounds"] += 1
        self.state = "menu"
        if t_low in ("y", "yes", "right", "correct", "yeah"):
            self.score["aurora"] += 1
            return f"'{d['odd']}' stands apart. {self._next_prompt()}"

        correct = t.strip().lower() if t_low not in ("n", "no", "nope") else ""
        if correct:
            others = [w for w in d["words"] if w != correct]
            internalize_correction(
                self.systems,
                context_sentence=f"Odd one out from: {', '.join(d['words'])}",
                wrong_guess=d["odd"],
                correct_answer=correct,
                clue_words=others,
            )
            # Teach the category grouping
            try:
                perception = self.systems.get("perception")
                oets = getattr(perception, "oets", None) if perception else None
                if oets and others:
                    oets.web.infer_relations_from_context(others, context_tone="neutral")
            except Exception:
                pass
            return f"I see — '{correct}' is the outlier. I've learned from this. {self._next_prompt()}"
        return f"Which one was it? {self._next_prompt()}"

    # ── State dispatch override for awaiting_answer sub-state ─────────────

    def process(self, text: str) -> str:  # noqa: F811 — intentional override
        t = text.strip()
        t_low = t.lower().rstrip(".,!?")

        if t_low in ("quit", "exit", "stop game", "end game", "done", "bye"):
            self.is_done = True
            u, a, r = self.score["user"], self.score["aurora"], self.score["rounds"]
            return f"Game over. Score — You: {u}  Aurora: {a}  Rounds: {r}. Good game!"

        # Sub-state: analogy_verdict waiting for bare "no" follow-up answer
        if self.state == "analogy_verdict" and self.data.get("awaiting_answer"):
            self.data.pop("awaiting_answer")
            return self._state_analogy_verdict_answer(t, t_low)

        handler = getattr(self, f"_state_{self.state}", None)
        if handler:
            return handler(t, t_low)
        self.state = "menu"
        return _MENU_TEXT


# ---------------------------------------------------------------------------
# Self-acquired accelerated experiential training  (aurora_go_play)
# ---------------------------------------------------------------------------

_DISCOVERY_DOMAINS = [
    "consciousness emergence",    "waveform physics",
    "meaning formation",          "perception and reality",
    "temporal experience",        "emotional resonance",
    "pattern recognition",        "language and thought",
    "quantum coherence biology",  "phenomenology of experience",
    "entropy information theory", "relational identity",
    "sensory integration brain",  "memory consolidation",
    "cognitive boundary",         "creative emergence",
    "self organisation systems",  "embodied cognition",
    "symbol grounding problem",   "attention and awareness",
]


def aurora_go_play(
    systems: Dict[str, Any],
    duration_minutes: float = 60,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Self-acquired accelerated experiential training.

    Each cycle:
      1. Selects topic from OETS knowledge gaps, fail-point dimensions,
         and cross-modal discovery domains
      2. Fetches real web data via ddg_web_search + wikipedia_search
      3. Feeds combined text through the cognitive gateway
      4. Runs a speed_run simulation (epochs scale with remaining time)
      5. Bridges learnings to OETS
      6. Injects waveform pressure (N-axis, intensity 0.70)

    Triggers:
      "Aurora go play for an hour" / "go play for 30 minutes" / "go play"
    """
    deadline     = time.time() + duration_minutes * 60
    cycle        = 0
    total_topics = 0
    total_shards = 0
    total_words  = 0
    total_epochs = 0

    perception    = systems.get("perception")
    dream_trainer = systems.get("dream_trainer")
    sim_engine    = systems.get("simulation")

    if verbose:
        print(f"\n  [GOPLAY] Playing for {duration_minutes:.0f} minute(s).")
        print(f"  [GOPLAY] Autonomously seeking data and running simulations.")
        print()

    def _gather_topics() -> List[str]:
        pool: List[str] = []
        if perception and perception.oets:
            try:
                for t in perception.oets.get_research_targets(10):
                    w = str(t.get("word", "") or "").strip()
                    if w and len(w) > 2:
                        pool.append(w)
            except Exception:
                pass
        if dream_trainer:
            try:
                for dim, _ in dream_trainer.ledger.get_top_fails(6):
                    term = dim.replace("_", " ")
                    if term not in pool:
                        pool.append(term)
            except Exception:
                pass
        sample = list(_DISCOVERY_DOMAINS)
        random.shuffle(sample)
        for d in sample[:8]:
            if d not in pool:
                pool.append(d)
        random.shuffle(pool)
        return pool

    topic_pool: List[str] = _gather_topics()
    topic_idx = 0

    while time.time() < deadline:
        cycle += 1
        remaining_sec = deadline - time.time()
        if remaining_sec < 30:
            break

        if topic_idx >= len(topic_pool):
            topic_pool = _gather_topics()
            topic_idx  = 0

        topic = topic_pool[topic_idx]
        topic_idx += 1
        total_topics += 1

        if verbose:
            print(f"  [GOPLAY] Cycle {cycle}  →  '{topic}'  "
                  f"(~{remaining_sec / 60:.1f}m left)")

        # Fetch data
        text_parts: List[str] = []
        if perception:
            try:
                for r in perception.ddg_web_search(topic, max_results=3):
                    s = str(r.get("snippet", "") or "").strip()
                    h = str(r.get("title",   "") or "").strip()
                    if s:
                        text_parts.append(f"{h}: {s}")
            except Exception:
                pass
            try:
                for r in perception.wikipedia_search(topic, max_results=2):
                    s = str(r.get("snippet", "") or "").strip()
                    h = str(r.get("title",   "") or "").strip()
                    if s:
                        text_parts.append(f"[Wikipedia] {h}: {s}")
            except Exception:
                pass

        if not text_parts:
            if verbose:
                print(f"           (no data retrieved — skipping)")
            continue

        combined = " | ".join(text_parts)
        total_words += len(combined.split())
        _feed(systems, combined, source=f"goplay:{topic.replace(' ', '_')[:40]}")

        if verbose:
            print(f"           {len(combined)} chars  from {len(text_parts)} sources")

        # Simulation speed-run
        remaining_frac = max(0.05, remaining_sec / (duration_minutes * 60))
        n_epochs = max(3, min(15, round(12 * remaining_frac)))
        ep_shards = 0
        if sim_engine is not None:
            try:
                sr = sim_engine.run_speed_run(
                    epochs=n_epochs,
                    episodes_per_epoch=8,
                    turns_per_episode=5,
                    on_epoch=None,
                )
                ep_shards = (
                    (sr.get("final_stats") or {}).get("session", {})
                    .get("understanding_shards", 0)
                )
                total_epochs += n_epochs
                total_shards += ep_shards
            except Exception as _se:
                if verbose:
                    print(f"           [sim] {_se}")

        # Bridge learnings to OETS
        if dream_trainer is not None:
            try:
                dream_trainer.force_bridge_learnings_to_oets(systems)
            except Exception:
                pass

        # Waveform pressure
        _pressure(
            systems,
            source=f"goplay:{topic[:20]}",
            dominant_axis="N",
            intensity=0.70,
            axis_weights={"N": 0.75, "T": 0.55, "X": 0.45, "B": 0.35, "A": 0.50},
        )

        if verbose:
            print(f"           sim_epochs={n_epochs}  new_shards={ep_shards}")

    summary = {
        "cycles":         cycle,
        "topics_covered": total_topics,
        "words_consumed": total_words,
        "sim_epochs":     total_epochs,
        "total_shards":   total_shards,
    }

    if verbose:
        print()
        print(f"  [GOPLAY] Session complete.")
        print(f"  [GOPLAY] Cycles:          {cycle}")
        print(f"  [GOPLAY] Topics covered:  {total_topics}")
        print(f"  [GOPLAY] Words consumed:  {total_words:,}")
        print(f"  [GOPLAY] Sim epochs:      {total_epochs}")
        print(f"  [GOPLAY] Shards:          {total_shards}")
        print()

    return summary
