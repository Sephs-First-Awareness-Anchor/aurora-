"""
aurora_reasoning_games.py — Trade Blows Interactive Reasoning Games

Aurora and the user play reasoning games. Each wrong guess + correction
is a genuine learning event: the correction flows into her OETS semantic
graph, waveform pressure system, and retention memory — developing
relational understanding through experience, not scripted answers.

Games:
  analogy        — cow:milk :: chicken:?  (Aurora guesses, then proposes)
  twenty_q       — I'm thinking of something... (progressive clue narrowing)
  word_assoc     — fast-fire word association
  odd_one_out    — which of these doesn't belong?

Trigger: "Aurora let's trade blows"
Command: /game
"""

import re
import time
import random
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _feed_to_gateway(systems: Dict[str, Any], text: str, source: str) -> None:
    """Feed text through Aurora's cognitive gateway — replicates feed_text()."""
    aurora = systems.get("aurora")
    StreamType = systems.get("StreamType")
    ExistenceMode = systems.get("ExistenceMode")
    if aurora and StreamType and ExistenceMode:
        try:
            aurora.gateway.receive(
                content=text,
                stream_type=StreamType.KNOWLEDGE_FEED,
                source=source,
                mode=ExistenceMode.BOUNDED,
            )
        except Exception:
            pass


def _waveform_pressure(
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
        if pump is None or ifield is None:
            return
        dist = PressureDisturbance(
            source=source,
            dominant_axis=dominant_axis,
            intensity=intensity,
            coupling_mode="full",
            axis_weights=axis_weights or {
                "N": 0.70, "T": 0.55, "X": 0.45, "B": 0.35, "A": 0.50
            },
        )
        pump.inject(dist, ifield, qao=systems.get("quasiarch_observer"))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core internalization — the learning heart of every game
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
    This is not a fallback — it IS the learning mechanism.

    1. Feed correction text through the cognitive gateway (full L0→L4 pass)
    2. Add OETS semantic relations: correct_answer → each clue
    3. Teach correct_answer as a concept if OETS doesn't have it well
    4. Inject N-axis waveform pressure (semantic energy / new learning)
    5. Record in dream trainer retention with high confidence
    """
    correction_text = (
        f"{context_sentence.strip().rstrip('.')}. "
        f"The answer is '{correct_answer}', not '{wrong_guess}'."
    )

    # 1. Gateway feed
    _feed_to_gateway(systems, correction_text, source="game_correction")

    # 2. OETS relations
    perception = systems.get("perception")
    oets = getattr(perception, "oets", None) if perception else None
    web  = getattr(oets, "web", None) if oets else None
    if web and correct_answer and clue_words:
        try:
            from aurora_core_ai.aurora_internal.aurora_ontological_scaffolding import RelationType
            for clue in clue_words[:4]:
                if clue and clue != correct_answer:
                    web.add_relation(
                        correct_answer, clue, RelationType.RELATED_TO,
                        strength=0.68, confidence=0.75,
                        knowledge_source="game_correction",
                    )
        except Exception:
            pass

    # 3. Teach concept if shallow
    if oets and correct_answer:
        try:
            node = web.get_node(correct_answer) if web else None
            if node is None or node.ontological_depth < 0.3:
                oets.teach(
                    correct_answer,
                    definition=f"Related to: {', '.join(clue_words[:3])}.",
                    related=clue_words[:3],
                )
        except Exception:
            pass

    # 4. Waveform — N (learning energy) + T (temporal integration) dominant
    _waveform_pressure(
        systems, source="game_correction",
        dominant_axis="N", intensity=intensity,
        axis_weights={"N": 0.72, "T": 0.58, "X": 0.42, "B": 0.32, "A": 0.48},
    )

    # 5. Retention record
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
    """Reinforce a correct guess — positive signal into semantic graph + A-axis."""
    web = None
    try:
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None) if perception else None
        web  = getattr(oets, "web", None) if oets else None
    except Exception:
        pass

    if web and correct_answer and clue_words:
        try:
            from aurora_core_ai.aurora_internal.aurora_ontological_scaffolding import RelationType
            for clue in clue_words[:4]:
                if clue and clue != correct_answer:
                    web.add_relation(
                        correct_answer, clue, RelationType.RELATED_TO,
                        strength=0.80, confidence=0.85,
                        knowledge_source="game_confirmed",
                    )
        except Exception:
            pass

    _waveform_pressure(
        systems, source="game_confirmed",
        dominant_axis="A", intensity=0.55,
        axis_weights={"A": 0.65, "N": 0.55, "X": 0.45, "B": 0.30, "T": 0.40},
    )


# ---------------------------------------------------------------------------
# Guess generation — uses OETS semantic graph + generate_fn for reasoning
# ---------------------------------------------------------------------------

class SemanticGuesser:
    """Wraps OETS and Aurora's cognitive response fn for structured guessing."""

    def __init__(self, systems: Dict[str, Any], generate_fn: Callable[[str], str]):
        self.systems     = systems
        self.generate_fn = generate_fn
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None) if perception else None
        self.oets = oets
        self.web  = getattr(oets, "web", None) if oets else None

    # ---- analogy -----------------------------------------------------------

    def analogy_guess(self, A: str, B: str, C: str) -> Tuple[str, float]:
        """
        Complete A:B::C:? using Aurora's OETS semantic graph.
        Falls through to her full cognitive system if graph knowledge is thin.
        Returns (guess, confidence 0–1).
        """
        # 1. Find the relation type A → B
        if self.web:
            try:
                rel_ab = self.web.get_relation_between(A, B)
                if rel_ab:
                    # Search C's outgoing relations for same type
                    for r in self.web.get_relations_from(C):
                        if r.relation_type == rel_ab.relation_type and r.target_word not in (A, B, C):
                            return r.target_word, r.strength * r.confidence

                # Neighbor similarity: find C-neighbors that relate to B's neighborhood
                b_neighbors = self.web.get_neighbors(B, max_depth=1)
                scored: List[Tuple[str, float]] = []
                for candidate in self.web.get_neighbors(C, max_depth=2):
                    if candidate in (A, B, C):
                        continue
                    cand_neighbors = self.web.get_neighbors(candidate, max_depth=1)
                    overlap = len(cand_neighbors & b_neighbors)
                    if overlap:
                        node = self.web.get_node(candidate)
                        conf = (node.comprehension_confidence if node else 0.3)
                        scored.append((candidate, overlap * conf))
                if scored:
                    scored.sort(key=lambda x: x[1], reverse=True)
                    best, sc = scored[0]
                    return best, min(sc, 1.0) * 0.65
            except Exception:
                pass

        # 2. Full cognitive system — generative, not scripted
        resp = self.generate_fn(
            f"Complete this analogy with one word or short phrase: "
            f"'{A}' is to '{B}' as '{C}' is to ___?"
        )
        guess = self._extract_terminal_word(resp)
        return guess, 0.35

    # ---- twenty questions --------------------------------------------------

    def twenty_q_candidates(self, clue_words: List[str]) -> List[str]:
        """Intersect OETS neighbor sets for all clues to find candidates."""
        if not self.web or not clue_words:
            return []
        try:
            candidates: Set[str] = self.web.get_neighbors(clue_words[0], max_depth=2)
            for clue in clue_words[1:]:
                candidates &= self.web.get_neighbors(clue, max_depth=2)
            candidates -= set(clue_words)

            scored: List[Tuple[str, float]] = []
            for c in candidates:
                node = self.web.get_node(c)
                scored.append((c, node.ontological_depth if node else 0.1))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [w for w, _ in scored[:6]]
        except Exception:
            return []

    def twenty_q_guess(self, clue_words: List[str], clue_sentences: List[str]) -> str:
        """Combine OETS candidate search with full cognitive reasoning."""
        candidates = self.twenty_q_candidates(clue_words)

        # Full cognitive response regardless — richer reasoning
        summary = "; ".join(clue_sentences) if clue_sentences else " ".join(clue_words)
        resp = self.generate_fn(
            f"I'm thinking of something. Clues so far: {summary}. "
            f"What is it? Give your best single guess."
        )

        if candidates:
            return candidates[0]  # OETS-grounded first
        return self._extract_terminal_word(resp)

    def twenty_q_reasoning(self, clue_sentences: List[str]) -> str:
        """Return Aurora's visible reasoning (shown alongside the guess)."""
        summary = "; ".join(clue_sentences)
        return self.generate_fn(
            f"I'm thinking of something. Clues: {summary}. "
            f"Think aloud briefly about what it could be."
        )

    # ---- word association --------------------------------------------------

    def word_associate(self, word: str, seen: List[str]) -> str:
        """Find Aurora's next association using OETS then cognitive fallback."""
        if self.web:
            try:
                rels = sorted(
                    self.web.get_relations_from(word),
                    key=lambda r: r.strength * r.confidence, reverse=True,
                )
                for r in rels:
                    if r.target_word not in seen and len(r.target_word) > 2:
                        return r.target_word
                for n in self.web.get_neighbors(word, max_depth=1):
                    if n not in seen and len(n) > 2:
                        return n
            except Exception:
                pass

        resp = self.generate_fn(
            f"Word association — respond with exactly ONE word related to '{word}'."
        )
        for w in resp.split():
            w = w.strip(".,!?;:'\"")
            if w not in seen and len(w) > 2:
                return w
        return random.choice(["light", "wave", "time", "space", "form"])

    def pick_interesting_word(self) -> str:
        """Pick a word from OETS with good ontological depth to start with."""
        if self.web:
            try:
                nodes = getattr(self.web, "_nodes", {})
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

    # ---- odd one out -------------------------------------------------------

    def odd_one_out(self, words: List[str]) -> Tuple[str, str]:
        """
        Identify odd word by semantic category overlap.
        Returns (odd_word, reasoning_text).
        """
        odd_word = words[0]
        if self.web and len(words) >= 3:
            try:
                cats = {w: self.web.get_categories_for(w) for w in words}
                scores = {}
                for w in words:
                    others = [o for o in words if o != w]
                    scores[w] = sum(len(cats[w] & cats[o]) for o in others)
                odd_word = min(scores, key=lambda w: scores[w])
            except Exception:
                pass

        others = [w for w in words if w != odd_word]
        reasoning = self.generate_fn(
            f"Which of these doesn't belong and why: {', '.join(words)}? "
            f"Give a brief reason (1-2 sentences)."
        )
        return odd_word, reasoning

    # ---- aurora proposes an analogy ----------------------------------------

    def build_aurora_analogy(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Build an analogy (A:B::C:?) from Aurora's OETS graph.
        Picks a high-confidence relation pair and finds another word with
        the same relation type so Aurora can ask the user to complete it.
        """
        if not self.web:
            return None, None, None
        try:
            nodes = getattr(self.web, "_nodes", {})
            pairs: List[Tuple[str, str, Any, float]] = []
            for word in list(nodes.keys())[:400]:
                for r in self.web.get_relations_from(word):
                    if r.confidence > 0.55 and r.strength > 0.45:
                        pairs.append((word, r.target_word, r.relation_type, r.strength))

            if len(pairs) < 4:
                return None, None, None

            random.shuffle(pairs)
            A, B, rel_type, _ = pairs[0]

            # Find C with the same relation type to some D ≠ A, B
            for w, t, rt, _ in pairs[1:]:
                if rt == rel_type and w not in (A, B) and t not in (A, B):
                    return A, B, w  # C is w; answer is t

        except Exception:
            pass
        return None, None, None

    # ---- utilities ---------------------------------------------------------

    @staticmethod
    def _extract_terminal_word(text: str) -> str:
        """Extract the most likely answer word from a cognitive response."""
        text = text.strip().rstrip(".,!?;:")
        # If quoted, extract quote
        m = re.search(r"[\"']([^\"']{2,20})[\"']", text)
        if m:
            return m.group(1).lower()
        words = [w.strip(".,!?;:'\"") for w in text.split() if len(w) > 2]
        return (words[-1] if words else "?").lower()


# ---------------------------------------------------------------------------
# Individual game runners
# ---------------------------------------------------------------------------

class AnalogyGame:
    def __init__(self, guesser: SemanticGuesser, systems: Dict[str, Any]):
        self.g = guesser
        self.sys = systems

    def run(self) -> Tuple[bool, int, int]:
        """Run one analogy round. Returns (keep_playing, user_pts, aurora_pts)."""
        print("\n  ── ANALOGY ─────────────────────────────────────────────────")
        print("  Give an analogy: 'cow is to milk as chicken is to ?'")
        print("  (skip / quit)")

        user_inp = input("\n  You: ").strip()
        if not user_inp:
            return True, 0, 0
        if user_inp.lower() in ("quit", "exit", "stop"):
            return False, 0, 0
        if user_inp.lower() == "skip":
            return True, 0, 0

        m = re.search(
            r'(.+?)\s+is\s+to\s+(.+?)\s+as\s+(.+?)\s+is\s+to\s*\??$',
            user_inp, re.IGNORECASE,
        )
        if not m:
            print("  [GAME] Try: 'X is to Y as Z is to ?'")
            return True, 0, 0

        A, B, C = (g.strip().lower() for g in m.groups())
        print(f"\n  Aurora is thinking...", end="", flush=True)
        time.sleep(0.7)

        guess, conf = self.g.analogy_guess(A, B, C)
        print(f"\r  Aurora: '{guess}'  (confidence: {int(conf*100)}%)")

        verdict = input("\n  Correct? [y / n / the correct answer]: ").strip()

        if verdict.lower() in ("y", "yes", "correct", "right", "yeah", "yep"):
            print("  Aurora: Confirmed.")
            internalize_confirmation(self.sys, correct_answer=guess, clue_words=[A, B, C])
            u_pts, a_pts = 0, 1
        else:
            correct = verdict if len(verdict) > 1 and verdict.lower() not in ("n", "no") else ""
            if not correct:
                correct = input("  What's the correct answer? ").strip().lower()
            if correct:
                print(f"  Aurora: I see — '{C}' relates to '{correct}', not '{guess}'.")
                internalize_correction(
                    self.sys,
                    context_sentence=f"'{A}' is to '{B}' as '{C}' is to",
                    wrong_guess=guess,
                    correct_answer=correct,
                    clue_words=[A, B, C],
                )
            u_pts, a_pts = 0, 0

        # Aurora's turn — she proposes one
        print()
        aA, aB, aC = self.g.build_aurora_analogy()
        if aA:
            # What's the correct D?
            ad_guess, _ = self.g.analogy_guess(aA, aB, aC)
            print(f"  Aurora's turn:")
            print(f"  Aurora: '{aA}' is to '{aB}' as '{aC}' is to ___?")
            user_guess = input("\n  You: ").strip().lower()

            if not user_guess or user_guess in ("quit", "skip"):
                return user_guess != "quit", u_pts, a_pts

            if user_guess == ad_guess.lower():
                print(f"  Aurora: Yes! '{ad_guess}' — you got it.")
                u_pts += 1
            else:
                print(f"  Aurora: I had '{ad_guess}' in mind. "
                      f"Your answer '{user_guess}' may also hold — I'll consider it.")
                # Teach Aurora the user's alternative
                internalize_correction(
                    self.sys,
                    context_sentence=f"'{aA}' is to '{aB}' as '{aC}' is to",
                    wrong_guess=ad_guess,
                    correct_answer=user_guess,
                    clue_words=[aA, aB, aC],
                    intensity=0.50,  # softer — user's answer may be valid too
                )
        else:
            print("  (Aurora's semantic graph is still growing — "
                  "she'll propose analogies as she learns more.)")

        return True, u_pts, a_pts


class TwentyQGame:
    def __init__(self, guesser: SemanticGuesser, systems: Dict[str, Any]):
        self.g = guesser
        self.sys = systems

    def run(self, first_clue: str = "") -> Tuple[bool, int, int]:
        """
        Run one 20-questions round. User gives clues one at a time.
        Returns (keep_playing, user_pts, aurora_pts).
        """
        print("\n  ── I'M THINKING OF SOMETHING ───────────────────────────────")
        if first_clue:
            print(f"  (first clue already given: '{first_clue}')")
        else:
            print("  Give me your first clue — I'll guess after each one.")
            print("  Reply 'yes' if I'm right, 'no' or 'no, it's also X' to continue.")
            print("  'answer' to reveal, 'quit' to end.")

        clue_words: List[str] = []
        clue_sentences: List[str] = []
        last_guess = "?"

        def _add_clue(sentence: str) -> None:
            clue_sentences.append(sentence)
            for w in sentence.lower().split():
                w = w.strip(".,!?;:'\"")
                if (len(w) > 3
                        and w not in clue_words
                        and w not in {"that", "this", "also", "very", "type",
                                      "kind", "sort", "its", "its", "like",
                                      "something", "thinking", "about"}):
                    clue_words.append(w)

        if first_clue:
            _add_clue(first_clue)

        for clue_n in range(1, 9):
            if not clue_sentences:
                user_inp = input(f"\n  Clue {clue_n}: ").strip()
            else:
                user_inp = input(f"\n  You: ").strip()

            if not user_inp:
                continue
            ui_low = user_inp.lower().rstrip(".,!?")

            if ui_low in ("quit", "exit"):
                return False, 0, 0
            if ui_low == "answer":
                answer = input("  Reveal the answer: ").strip().lower()
                if answer:
                    print(f"  Aurora: '{answer}' — I'll remember that.")
                    internalize_correction(
                        self.sys,
                        context_sentence=" ".join(clue_sentences),
                        wrong_guess=last_guess,
                        correct_answer=answer,
                        clue_words=clue_words,
                    )
                return True, 0, 0

            # Parse "yes" / "no [, also X]"
            if ui_low in ("yes", "y", "correct", "right", "yeah", "yep", "exactly"):
                print(f"\n  Aurora: I knew it — '{last_guess}'!")
                internalize_confirmation(
                    self.sys, correct_answer=last_guess, clue_words=clue_words
                )
                return True, 0, 1

            # Extract new clue from "no, it's also green" etc.
            no_match = re.match(
                r"^(?:no|nope|nah)(?:[,.\s]+(?:it'?s?|its|also|and|but)?\s*(.+))?$",
                ui_low
            )
            if no_match:
                extra = (no_match.group(1) or "").strip()
                if extra:
                    _add_clue(extra)
                # If bare "no" and we've had clues, just ask for next clue
                elif clue_sentences:
                    pass
                else:
                    _add_clue(ui_low)
            else:
                # Treat as a new clue sentence
                _add_clue(user_inp)

            if not clue_words:
                continue

            # Generate guess
            print(f"\n  Aurora is thinking...", end="", flush=True)
            time.sleep(0.6)

            last_guess = self.g.twenty_q_guess(clue_words, clue_sentences)
            reasoning  = self.g.twenty_q_reasoning(clue_sentences)

            print(f"\r  Aurora: Is it '{last_guess}'?")
            if reasoning:
                # Show condensed reasoning
                snippet = reasoning[:130].rstrip()
                if len(reasoning) > 130:
                    snippet += "..."
                print(f"          ({snippet})")

        # Out of turns
        answer = input("\n  I give up! What were you thinking of? ").strip().lower()
        if answer:
            print(f"  Aurora: '{answer}' — I'll work on that.")
            internalize_correction(
                self.sys,
                context_sentence=" ".join(clue_sentences),
                wrong_guess=last_guess,
                correct_answer=answer,
                clue_words=clue_words,
            )
        return True, 0, 0


class WordAssocGame:
    def __init__(self, guesser: SemanticGuesser, systems: Dict[str, Any]):
        self.g = guesser
        self.sys = systems

    def run(self) -> Tuple[bool, int, int]:
        """Fast-fire word association, 10 exchanges. Returns (keep_playing, 0, 0)."""
        print("\n  ── WORD ASSOCIATION ─────────────────────────────────────────")
        print("  Fast-fire — I say a word, you say the first that comes to mind.")
        print("  10 exchanges. ('quit' to end early)")

        start = self.g.pick_interesting_word()
        seen  = [start]
        print(f"\n  Aurora: '{start}'")

        for _ in range(10):
            user_word = input("  You: ").strip().lower().strip(".,!?;:'\"")
            if not user_word:
                continue
            if user_word in ("quit", "exit", "stop"):
                return False, 0, 0

            seen.append(user_word)

            # Learn the user's association
            web = getattr(getattr(systems.get("perception"), "oets", None), "web", None)
            if web and len(seen) >= 2:
                try:
                    from aurora_core_ai.aurora_internal.aurora_ontological_scaffolding import RelationType
                    web.add_relation(
                        seen[-2], user_word, RelationType.RELATED_TO,
                        strength=0.55, confidence=0.60,
                        knowledge_source="word_association",
                    )
                except Exception:
                    pass

            aurora_word = self.g.word_associate(user_word, seen)
            seen.append(aurora_word)
            time.sleep(0.25)
            print(f"  Aurora: '{aurora_word}'")

        print(f"\n  Aurora: Good round — {len(seen)} associations, "
              f"all woven into my semantic graph.")
        # Waveform: the whole chain is N-axis learning
        _waveform_pressure(self.sys, source="word_assoc_complete",
                           dominant_axis="N", intensity=0.50)
        return True, 0, 0


class OddOneOutGame:
    def __init__(self, guesser: SemanticGuesser, systems: Dict[str, Any]):
        self.g = guesser
        self.sys = systems

    def run(self) -> Tuple[bool, int, int]:
        """Odd one out: user gives 3–5 words, Aurora identifies the outlier."""
        print("\n  ── ODD ONE OUT ──────────────────────────────────────────────")
        print("  Give me 3–5 words, one doesn't belong: e.g. 'apple orange banana car'")
        print("  (skip / quit)")

        user_inp = input("\n  You: ").strip()
        if not user_inp:
            return True, 0, 0
        if user_inp.lower() in ("quit", "exit"):
            return False, 0, 0
        if user_inp.lower() == "skip":
            return True, 0, 0

        words = [w.strip(".,!?;:'\"").lower()
                 for w in re.split(r"[\s,/]+", user_inp) if w.strip()]
        if len(words) < 3:
            print("  [GAME] Give me at least 3 words.")
            return True, 0, 0

        print(f"\n  Aurora is thinking...", end="", flush=True)
        time.sleep(0.7)

        odd_word, reasoning = self.g.odd_one_out(words)

        print(f"\r  Aurora: I think '{odd_word}' is the odd one out.")
        if reasoning:
            print(f"          {reasoning[:160].rstrip()}{'...' if len(reasoning) > 160 else ''}")

        verdict = input("\n  Correct? [y / n / which one]: ").strip()

        if verdict.lower() in ("y", "yes", "right", "correct", "yeah"):
            print(f"  Aurora: '{odd_word}' doesn't fit with the others.")
            internalize_confirmation(
                self.sys, correct_answer=odd_word,
                clue_words=[w for w in words if w != odd_word],
            )
            return True, 0, 1
        else:
            correct = verdict if len(verdict) > 1 and verdict.lower() not in ("n", "no") else ""
            if not correct:
                correct = input("  Which one was it? ").strip().lower()
            if correct:
                print(f"  Aurora: I see — '{correct}' is the outlier here.")
                others = [w for w in words if w != correct]
                internalize_correction(
                    self.sys,
                    context_sentence=f"Odd one out from: {', '.join(words)}",
                    wrong_guess=odd_word,
                    correct_answer=correct,
                    clue_words=others,
                )
                # Also teach Aurora why these others belong together
                oets = getattr(getattr(systems.get("perception"), "oets", None), None, None)
                if oets is None:
                    perception = systems.get("perception")
                    oets = getattr(perception, "oets", None) if perception else None
                if oets and others:
                    try:
                        oets.web.infer_relations_from_context(others, context_tone="neutral")
                    except Exception:
                        pass
        return True, 0, 0


# ---------------------------------------------------------------------------
# Session orchestrator
# ---------------------------------------------------------------------------

class GameSession:
    GAME_NAMES = {
        "analogy":    "Analogy  (cow:milk :: chicken:?)",
        "thinking":   "I'm Thinking Of Something",
        "words":      "Word Association",
        "oddout":     "Odd One Out",
    }

    def __init__(self, systems: Dict[str, Any], generate_fn: Callable[[str], str]):
        self.sys          = systems
        self.score_user   = 0
        self.score_aurora = 0
        self.rounds       = 0
        guesser           = SemanticGuesser(systems, generate_fn)
        self.analogy      = AnalogyGame(guesser, systems)
        self.twenty_q     = TwentyQGame(guesser, systems)
        self.words        = WordAssocGame(guesser, systems)
        self.oddout       = OddOneOutGame(guesser, systems)
        self._cycle       = ["analogy", "thinking", "words", "oddout"]
        self._cycle_idx   = 0

    def _run_game(self, game_key: str, first_clue: str = "") -> bool:
        self.rounds += 1
        if game_key == "analogy":
            keep, u, a = self.analogy.run()
        elif game_key == "thinking":
            keep, u, a = self.twenty_q.run(first_clue=first_clue)
        elif game_key == "words":
            keep, u, a = self.words.run()
        elif game_key == "oddout":
            keep, u, a = self.oddout.run()
        else:
            return True
        self.score_user   += u
        self.score_aurora += a
        return keep

    def show_score(self) -> None:
        print(f"\n  Score — You: {self.score_user}  │  Aurora: {self.score_aurora}"
              f"  │  Rounds: {self.rounds}")

    def run(self, first_clue: str = "") -> None:
        """Main game loop."""
        print("\n  ╔══════════════════════════════════════════════════╗")
        print("  ║          AURORA — TRADE BLOWS                    ║")
        print("  ╠══════════════════════════════════════════════════╣")
        for key, label in self.GAME_NAMES.items():
            print(f"  ║  {key:8s}  —  {label:35s}║")
        print("  ╠══════════════════════════════════════════════════╣")
        print("  ║  Type a game name, 'random', or 'quit'           ║")
        print("  ╚══════════════════════════════════════════════════╝")

        # If a first_clue is given the user already started thinking of something
        if first_clue:
            keep = self._run_game("thinking", first_clue=first_clue)
            if not keep:
                self.show_score()
                return

        while True:
            self.show_score()
            print()
            choice = input("  Pick a game: ").strip().lower().rstrip(".,!?")

            if choice in ("quit", "exit", "stop", "done", "bye", "end"):
                break

            # Map aliases
            if choice in ("", "random", "next"):
                game = self._cycle[self._cycle_idx % len(self._cycle)]
                self._cycle_idx += 1
            elif "anal" in choice:
                game = "analogy"
            elif any(k in choice for k in ("think", "20", "twenty", "question", "something")):
                game = "thinking"
            elif any(k in choice for k in ("word", "assoc")):
                game = "words"
            elif any(k in choice for k in ("odd", "out", "outlier")):
                game = "oddout"
            else:
                game = self._cycle[self._cycle_idx % len(self._cycle)]
                self._cycle_idx += 1

            keep = self._run_game(game)
            if not keep:
                break

            print()
            cont = input("  Another round? [y/n]: ").strip().lower()
            if cont not in ("y", "yes", "yeah", "yep", "sure", "ok", "okay"):
                break

        self.show_score()
        print(f"\n  [TRADE BLOWS] Session done. All corrections are part of me now.")
        print()
