#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_screen_apprenticeship.py -- her hands on the phone, and learning a
phone task by being shown it.

Sir asks her to open Spotify and play his liked playlist.  She can open
Spotify; what "play my liked playlist" means on that screen she has never
seen.  So the part she could not do stays open, and her attention stays on
the screen.  When he shows her ("once it's open you select Library, then
Liked Songs, then hit play"), each thing he names is looked for on the screen
she sees; she presses it herself, watches what changes, and goes on to the
next thing he named.  What she keeps is the pairing: his words, the place on
the screen they meant, what she did there and what the screen became.  The
next time he asks, the request means something to her, and she does it,
checking each step against what she sees.  If a step is no longer where it
was, she stops there, and the part she could not do is open again.

Nothing here is a macro for an app or a canned reply.  There is no list of
apps, buttons or phrases.  What anything means comes from three things she
perceives: his words, what is on the screen, and what changed after a press.

  grounding      a word means a place on the screen when that place's own
                 label carries the word (its text, its description, its
                 view id), weighed by how distinctive the word is on that
                 screen, plus what she has learned words mean there.  The
                 order he says things is the order she looks for them (T).
  meaning        each step teaches her what words point at: a word he said
                 next to a word that grounded attaches to the same place, so
                 "liked playlist" comes to mean the row labelled Liked Songs.
                 The words that lead into a step teach her what kind of act
                 it was (tap, hold, scroll, type).
  skill          a request's own words, the app it lives in, and the steps,
                 each with the place it acts on and what the screen became.
  confidence     how often doing it went as it did when she learned it.
                 It is a count of what happened, never a setting.

Each step is lived through the five constraint axes and the I-State pairs:
  X  the place exists on this screen (grounding strength)
  T  where the step stands in the order
  N  the effort it took (re-reads, scrolls, retries)
  B  a boundary met (another app in front, a refusal, a password box)
  A  whose act it was (hers, or Sir's own hands showing her)
  CAN/CANT the step could be grounded; SAW/SAUNT she saw the screen change;
  DID/DIDNT the act was accepted.

One state.  On a whole-mind phone (unpaired) she keeps what she learns here,
in screen_skills.json.  On a paired phone her deep learning lives at home:
what she lives here is held as present (strata_link/) and goes home through
the durable outbox; home keeps the skills and hands back down what she knows
(strata_link/screen_skills_from_home.json).  She uses both: what home knows,
and what she has lived since home last heard.  The home-owned store is
written only through aurora_persistence_utils.atomic_write_json, so the store
gate holds.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SKILLS_FILENAME = "screen_skills.json"                     # home-owned (whole mind)
HOME_COPY_FILENAME = "screen_skills_from_home.json"        # under strata_link/ on a surface
PENDING_FILENAME = "screen_skills_pending.json"            # under strata_link/ on a surface
DOWN_CHANNEL = "home_skills"

# How long a request she could not finish stays open with her attention on
# the screen, in Sir's turns that ground nothing, and in seconds.  The turn
# count is the bridge's own attention window (aurora_bridge._ATTENTION_TURNS).
ATTENTION_TURNS = 6
ATTENTION_SECONDS = 300.0
# After she has learned a task, a further instruction that grounds on the
# same screen within this window adds to it instead of starting another.
LINGER_SECONDS = 90.0
# Effort she spends on one step before it counts as not found.
SCROLL_TRIES = 3
SETTLE_TIMEOUT_S = 4.0
SETTLE_POLL_S = 0.25

_ACTIONS = ("tap", "long_press", "scroll_forward", "scroll_backward", "type")
_GLOBALS = ("back", "home", "recents", "notifications")
_OWN_PACKAGES = ("org.aurora.app", "com.aurora.app")


# ---------------------------------------------------------------------------
# Words
# ---------------------------------------------------------------------------

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def label_words(text: str) -> List[str]:
    """The words a screen label carries: 'Saved Items' -> saved, items;
    'save_button' -> save, button; 'ImageButton' -> image, button."""
    text = _CAMEL.sub(" ", str(text or ""))
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 2]


def utterance_words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


_PARSER = None


def content_words(text: str) -> List[str]:
    """Her own perception of which words carry content (the utterance
    parser's topic-word extraction, untruncated).  Falls back to words of
    three letters or more when the parser cannot load."""
    global _PARSER
    low = str(text or "").lower()
    try:
        if _PARSER is None:
            from aurora_internal.aurora_utterance_parser import UtteranceParser
            _PARSER = UtteranceParser()
        words, _ = _PARSER._extract_topic_words(low, set())
        return [w for w in words if w]
    except Exception:
        return [w for w in re.findall(r"[a-z0-9]+", low) if len(w) >= 3]


def word_match(a: str, b: str) -> float:
    """How strongly two words are the same word, by their letters alone."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) < 4:
        return 0.0
    prefix = 0
    for x, y in zip(short, long_):
        if x != y:
            break
        prefix += 1
    if prefix >= 4 and prefix >= 0.75 * len(short):
        return 0.7
    return 0.0


# ---------------------------------------------------------------------------
# What she sees
# ---------------------------------------------------------------------------

@dataclass
class ScreenNode:
    index: int
    text: str = ""
    desc: str = ""
    view_id: str = ""
    cls: str = ""
    clickable: bool = False
    long_clickable: bool = False
    scrollable: bool = False
    editable: bool = False
    checkable: bool = False
    checked: bool = False
    password: bool = False
    actionable_ancestor: bool = False
    depth: int = 0
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ScreenNode":
        b = list(d.get("bounds") or [0, 0, 0, 0])[:4]
        while len(b) < 4:
            b.append(0)
        return cls(
            index=int(d.get("i", d.get("index", 0)) or 0),
            text=str(d.get("text") or ""), desc=str(d.get("desc") or ""),
            view_id=str(d.get("view_id") or ""), cls=str(d.get("cls") or ""),
            clickable=bool(d.get("clickable")), long_clickable=bool(d.get("long_clickable")),
            scrollable=bool(d.get("scrollable")), editable=bool(d.get("editable")),
            checkable=bool(d.get("checkable")), checked=bool(d.get("checked")),
            password=bool(d.get("password")),
            actionable_ancestor=bool(d.get("actionable_ancestor")),
            depth=int(d.get("depth") or 0),
            bounds=(int(b[0]), int(b[1]), int(b[2]), int(b[3])),
        )

    @property
    def actionable(self) -> bool:
        return (self.clickable or self.long_clickable or self.scrollable or self.editable
                or self.checkable or self.actionable_ancestor)

    def weighted_labels(self) -> List[Tuple[str, float]]:
        """Each word of this place's own labels, with how much it says.
        Its text and description say most; its view id a little less; the
        kind of view (button, image) only a little."""
        out: List[Tuple[str, float]] = []
        for w in label_words(self.text) + label_words(self.desc):
            out.append((w, 1.0))
        vid = self.view_id.split("/", 1)[-1] if self.view_id else ""
        for w in label_words(vid):
            out.append((w, 0.8))
        for w in label_words(self.cls.rsplit(".", 1)[-1]):
            out.append((w, 0.35))
        return out

    def label(self) -> str:
        return (self.text or self.desc or self.view_id.split("/", 1)[-1] or self.cls.rsplit(".", 1)[-1])[:80]

    def signature(self) -> Dict[str, Any]:
        return {"text": self.text[:120], "desc": self.desc[:120], "view_id": self.view_id,
                "cls": self.cls, "editable": self.editable, "scrollable": self.scrollable}


@dataclass
class ScreenFrame:
    frame_id: int
    package: str
    nodes: List[ScreenNode]
    at: float = field(default_factory=time.time)
    size: Tuple[int, int] = (0, 0)

    @classmethod
    def from_json(cls, raw: Any) -> Optional["ScreenFrame"]:
        try:
            d = json.loads(str(raw)) if not isinstance(raw, Mapping) else dict(raw)
        except ValueError:
            return None
        if not isinstance(d, Mapping) or not d.get("ok", True):
            return None
        size = list(d.get("screen") or [0, 0])[:2] + [0, 0]
        return cls(frame_id=int(d.get("frame") or 0), package=str(d.get("package") or ""),
                   nodes=[ScreenNode.from_dict(n) for n in list(d.get("nodes") or [])],
                   at=float(d.get("at") or time.time()), size=(int(size[0]), int(size[1])))

    @property
    def is_own(self) -> bool:
        return self.package in _OWN_PACKAGES or "aurora" in self.package.lower()

    def presence(self) -> Dict[str, int]:
        """How many places on this screen carry each word."""
        counts: Dict[str, int] = {}
        for node in self.nodes:
            for w in {w for w, _ in node.weighted_labels()}:
                counts[w] = counts.get(w, 0) + 1
        return counts

    def label_set(self) -> set:
        return {f"{n.view_id}|{n.text}|{n.desc}" for n in self.nodes if (n.text or n.desc or n.view_id)}

    def signature(self) -> Dict[str, Any]:
        labels = sorted({n.label() for n in self.nodes if n.text or n.desc})[:40]
        return {"package": self.package, "labels": labels}

    def describe(self, limit: int = 30) -> str:
        lines = [f"package={self.package} frame={self.frame_id}"]
        for n in self.nodes:
            if len(lines) > limit:
                break
            if not (n.text or n.desc) and not n.actionable:
                continue
            acts = [a for a, on in (("tap", n.clickable or n.actionable_ancestor),
                                    ("hold", n.long_clickable), ("scroll", n.scrollable),
                                    ("type", n.editable and not n.password)) if on]
            lines.append(f"[{n.index}] {n.label()} ({'/'.join(acts) or 'see'})")
        return "\n".join(lines)


def frames_differ(a: Optional[ScreenFrame], b: Optional[ScreenFrame]) -> bool:
    if a is None or b is None:
        return a is not b
    return a.package != b.package or a.label_set() != b.label_set()


def signature_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    """How alike two screen signatures are: same app, and the share of
    labels they have in common."""
    if not a or not b:
        return 0.0
    if str(a.get("package") or "") != str(b.get("package") or ""):
        return 0.0
    la, lb = set(a.get("labels") or []), set(b.get("labels") or [])
    if not la and not lb:
        return 1.0
    return len(la & lb) / float(len(la | lb) or 1)


# ---------------------------------------------------------------------------
# Hands: the phone's accessibility service, or a stand-in (tests, desktop)
# ---------------------------------------------------------------------------

class AndroidScreenHands:
    """Her hands through ScreenObserverService (Kotlin), via Chaquopy."""

    def _svc(self):
        from java import jclass  # type: ignore
        return jclass("org.aurora.app.ScreenObserverService")

    def available(self) -> bool:
        try:
            return bool(self._svc().isRunning())
        except Exception:
            return False

    def read(self) -> Optional[ScreenFrame]:
        try:
            return ScreenFrame.from_json(str(self._svc().readScreen()))
        except Exception:
            return None

    def act(self, frame: ScreenFrame, index: int, action: str, text: str = "") -> Dict[str, Any]:
        try:
            return json.loads(str(self._svc().act(int(frame.frame_id), int(index), str(action), str(text or ""))))
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def global_action(self, name: str) -> Dict[str, Any]:
        try:
            return json.loads(str(self._svc().globalAction(str(name))))
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def bring_to_front(self, package: str) -> bool:
        try:
            from aurora_internal.tool_registry import _chaquopy_launch_app
            ok, _ = _chaquopy_launch_app(package)
            return bool(ok)
        except Exception:
            return False

    def wait(self, seconds: float) -> None:
        time.sleep(max(0.0, float(seconds)))


# ---------------------------------------------------------------------------
# What she keeps
# ---------------------------------------------------------------------------

@dataclass
class Step:
    words: List[str]                 # his words this step answered
    action: str                      # tap / long_press / scroll_* / type / a global key
    target: Dict[str, Any]           # the place, by its own labels
    package: str = ""
    text: str = ""                   # what was typed, when it was typing
    agent: str = "her"               # "her" when she did it, "sir" when his hands showed her
    before: Dict[str, Any] = field(default_factory=dict)
    after: Dict[str, Any] = field(default_factory=dict)
    axes: Dict[str, float] = field(default_factory=dict)
    istate: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"words": list(self.words), "action": self.action, "target": dict(self.target),
                "package": self.package, "text": self.text, "agent": self.agent,
                "before": dict(self.before), "after": dict(self.after),
                "axes": dict(self.axes), "istate": dict(self.istate)}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Step":
        return cls(words=list(d.get("words") or []), action=str(d.get("action") or "tap"),
                   target=dict(d.get("target") or {}), package=str(d.get("package") or ""),
                   text=str(d.get("text") or ""), agent=str(d.get("agent") or "her"),
                   before=dict(d.get("before") or {}), after=dict(d.get("after") or {}),
                   axes=dict(d.get("axes") or {}), istate=dict(d.get("istate") or {}))


@dataclass
class Skill:
    skill_id: str
    goal_words: List[str]
    package: str
    steps: List[Step]
    instructions: List[str] = field(default_factory=list)
    version: int = 1
    uses: int = 0
    successes: int = 0
    learned_at: float = field(default_factory=time.time)
    source: str = "sir_showed_her"
    lived_on: str = ""

    def confidence(self) -> float:
        """Her expectation that doing it goes as it did, from what happened:
        learning it once counts as one success."""
        return (1.0 + self.successes) / (2.0 + self.uses)

    def to_dict(self) -> Dict[str, Any]:
        return {"skill_id": self.skill_id, "goal_words": list(self.goal_words),
                "package": self.package, "steps": [s.to_dict() for s in self.steps],
                "instructions": list(self.instructions)[-12:], "version": self.version,
                "uses": self.uses, "successes": self.successes, "learned_at": self.learned_at,
                "source": self.source, "lived_on": self.lived_on}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Skill":
        return cls(skill_id=str(d.get("skill_id") or uuid.uuid4().hex),
                   goal_words=list(d.get("goal_words") or []), package=str(d.get("package") or ""),
                   steps=[Step.from_dict(s) for s in list(d.get("steps") or [])],
                   instructions=list(d.get("instructions") or []),
                   version=int(d.get("version") or 1), uses=int(d.get("uses") or 0),
                   successes=int(d.get("successes") or 0),
                   learned_at=float(d.get("learned_at") or time.time()),
                   source=str(d.get("source") or "sir_showed_her"),
                   lived_on=str(d.get("lived_on") or ""))


class ScreenMeaning:
    """What words have come to mean on screens: word -> label word -> weight,
    and word -> kind of act -> count.  Learned only from steps she lived."""

    def __init__(self, data: Optional[Mapping[str, Any]] = None) -> None:
        data = dict(data or {})
        self.labels: Dict[str, Dict[str, float]] = {k: dict(v) for k, v in dict(data.get("labels") or {}).items()}
        self.acts: Dict[str, Dict[str, int]] = {k: dict(v) for k, v in dict(data.get("acts") or {}).items()}

    def to_dict(self) -> Dict[str, Any]:
        return {"labels": self.labels, "acts": self.acts}

    def strengthen(self, word: str, label_word: str, amount: float = 0.5) -> None:
        if not word or not label_word or word == label_word:
            return
        row = self.labels.setdefault(word, {})
        row[label_word] = min(1.0, float(row.get(label_word, 0.0)) + amount)

    def learn_act(self, word: str, action: str) -> None:
        if word and action:
            row = self.acts.setdefault(word, {})
            row[action] = int(row.get(action, 0)) + 1

    def match(self, word: str, label_word: str) -> float:
        direct = word_match(word, label_word)
        learned = float(self.labels.get(word, {}).get(label_word, 0.0))
        return max(direct, learned)

    def act_lean(self, words: Iterable[str]) -> Dict[str, float]:
        lean: Dict[str, float] = {}
        for w in words:
            row = self.acts.get(w) or {}
            total = float(sum(row.values()) or 0)
            for a, n in row.items():
                if total:
                    lean[a] = lean.get(a, 0.0) + n / total
        return lean

    def merge(self, other: "ScreenMeaning") -> None:
        for w, row in other.labels.items():
            mine = self.labels.setdefault(w, {})
            for lw, v in row.items():
                mine[lw] = max(float(mine.get(lw, 0.0)), float(v))
        for w, row in other.acts.items():
            mine = self.acts.setdefault(w, {})
            for a, n in row.items():
                mine[a] = max(int(mine.get(a, 0)), int(n))


# ---------------------------------------------------------------------------
# Grounding
# ---------------------------------------------------------------------------

@dataclass
class Grounding:
    node: ScreenNode
    score: float
    first_pos: int
    last_pos: int
    matched: List[Tuple[int, str, str]]      # (position, his word, label word)


def ground(words: Sequence[Tuple[int, str]], frame: ScreenFrame, meaning: ScreenMeaning,
           *, content: Optional[set] = None) -> List[Grounding]:
    """Every place on the screen his words could mean, strongest evidence
    first by the order he said them.  A place is named by one run of his
    words (words a step or two apart), not by the same word said again
    later; and it needs one word in that run that is its own (a direct or
    learned match of at least 0.7) to be a candidate at all."""
    presence = frame.presence()
    out: List[Grounding] = []
    for node in frame.nodes:
        if not node.actionable or node.password:
            continue
        labels = node.weighted_labels()
        if not labels:
            continue
        hits: List[Tuple[int, str, str, float, bool]] = []
        for pos, w in words:
            if content is not None and w not in content:
                continue
            best, best_lw, own = 0.0, "", False
            for lw, lweight in labels:
                raw = meaning.match(w, lw)
                m = raw * lweight / math.sqrt(max(1, presence.get(lw, 1)))
                if m > best:
                    best, best_lw = m, lw
                    own = m >= 0.7 or (raw >= 0.7 and lweight >= 0.8 and presence.get(lw, 1) == 1)
            if best > 0.0:
                hits.append((pos, w, best_lw, best, own))
        if not hits:
            continue
        # The first run of his words that names this place.
        run = [hits[0]]
        for h in hits[1:]:
            if h[0] - run[-1][0] <= 2:
                run.append(h)
            else:
                break
        if not any(h[4] for h in run):
            continue
        out.append(Grounding(node=node, score=sum(h[3] for h in run), first_pos=run[0][0],
                             last_pos=run[-1][0], matched=[(h[0], h[1], h[2]) for h in run]))
    out.sort(key=lambda g: (g.first_pos, -g.score, g.node.bounds[1], g.node.index))
    return out


def find_target(target: Mapping[str, Any], frame: ScreenFrame) -> Tuple[Optional[ScreenNode], float]:
    """The place on this screen that is the one she acted on before, by its
    own labels: its view id first, then its words, then its kind."""
    want_words = set(label_words(target.get("text") or "") + label_words(target.get("desc") or ""))
    want_vid = str(target.get("view_id") or "")
    best, best_score = None, 0.0
    for node in frame.nodes:
        if node.password:
            continue
        score = 0.0
        if want_vid and node.view_id == want_vid:
            score += 1.0
        have = set(label_words(node.text) + label_words(node.desc))
        if want_words or have:
            score += len(want_words & have) / float(len(want_words | have) or 1)
        if target.get("cls") and node.cls == target.get("cls"):
            score += 0.2
        if bool(target.get("editable")) != node.editable:
            score -= 0.3
        if score > best_score:
            best, best_score = node, score
    # Its kind alone is not enough: a place is found by its id or its words.
    return (best, best_score) if best_score >= 0.5 else (None, best_score)


def coverage(goal: Sequence[str], heard: Sequence[str], meaning: ScreenMeaning) -> float:
    """The share of a skill's own goal words that this request carries."""
    goal = [w for w in goal if w]
    if not goal:
        return 0.0
    total = 0.0
    for g in goal:
        total += max([word_match(g, h) for h in heard] + [0.0]
                     + [float(meaning.labels.get(h, {}).get(g, 0.0)) for h in heard])
    return total / len(goal)


# ---------------------------------------------------------------------------
# An episode: a request she is being shown
# ---------------------------------------------------------------------------

@dataclass
class Episode:
    goal_text: str
    goal_words: List[str]
    package: str
    opened_at: float = field(default_factory=time.time)
    steps: List[Step] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    quiet_turns: int = 0
    base_skill_id: str = ""
    base_version: int = 0
    last_frame_sig: Dict[str, Any] = field(default_factory=dict)
    # His last turn grounded everything he named (nothing he said was left
    # unfound).  If his next turn names nothing more, what he showed is whole.
    last_turn_complete: bool = False

    def expired(self, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        return self.quiet_turns >= ATTENTION_TURNS or (now - self.opened_at) > ATTENTION_SECONDS * (1 + len(self.steps))


# ---------------------------------------------------------------------------
# The apprenticeship
# ---------------------------------------------------------------------------

class ScreenApprenticeship:
    def __init__(self, state_dir: Any, hands: Any = None, systems: Optional[Dict[str, Any]] = None,
                 *, clock: Callable[[], float] = time.time) -> None:
        self.state_dir = Path(str(state_dir or "aurora_state"))
        self.hands = hands
        self.systems = systems if systems is not None else {}
        self.clock = clock
        self._lock = threading.RLock()
        self.episode: Optional[Episode] = None
        self.lingering: Optional[Tuple[str, float]] = None     # (skill id, closed at)
        self.last_external: Optional[ScreenFrame] = None
        self._user_steps: List[Tuple[Dict[str, Any], str, float]] = []
        self.counts: Dict[str, int] = {}
        self.skills: Dict[str, Skill] = {}
        self.meaning = ScreenMeaning()
        self._pending: Dict[str, Any] = {"skills": {}, "uses": [], "meaning": {}}
        self._last_heard: Tuple[str, float] = ("", 0.0)
        self._load()

    # -- where she keeps it --------------------------------------------------
    def is_surface(self) -> bool:
        try:
            from aurora_internal.aurora_store_ownership import surface_only_root
            root = surface_only_root()
            return root is not None and Path(root).resolve() == self.state_dir.resolve()
        except Exception:
            return False

    def _link(self) -> Path:
        try:
            from aurora_internal.dual_strata.strata_link import link_dir
            return Path(link_dir(self.state_dir))
        except Exception:
            return self.state_dir / "strata_link"

    @staticmethod
    def _read(path: Path) -> Dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _write(path: Path, data: Mapping[str, Any]) -> bool:
        from aurora_persistence_utils import atomic_write_json
        return bool(atomic_write_json(path, dict(data), default=str))

    def _load(self) -> None:
        with self._lock:
            self.skills, self.meaning = {}, ScreenMeaning()
            if self.is_surface():
                home = self._read(self._link() / HOME_COPY_FILENAME)
                pend = self._read(self._link() / PENDING_FILENAME)
                self._pending = {"skills": dict(pend.get("skills") or {}),
                                 "uses": list(pend.get("uses") or []),
                                 "meaning": dict(pend.get("meaning") or {})}
                sources = [home, {"skills": self._pending["skills"], "meaning": self._pending["meaning"]}]
            else:
                sources = [self._read(self.state_dir / SKILLS_FILENAME)]
            for src in sources:
                for sid, d in dict(src.get("skills") or {}).items():
                    sk = Skill.from_dict(d)
                    have = self.skills.get(sid)
                    if have is None or sk.version >= have.version:
                        self.skills[sid] = sk
                self.meaning.merge(ScreenMeaning(src.get("meaning") or {}))
            if self.is_surface():
                for use in self._pending["uses"]:
                    sk = self.skills.get(str(use.get("skill_id") or ""))
                    if sk is not None and use.get("counted_in_version") != sk.version:
                        sk.uses += 1
                        sk.successes += 1 if use.get("success") else 0

    def _persist(self, learned: Optional[Skill] = None, use: Optional[Dict[str, Any]] = None) -> None:
        """Keep what she lived, where it belongs."""
        with self._lock:
            if not self.is_surface():
                self._write(self.state_dir / SKILLS_FILENAME, {
                    "skills": {k: v.to_dict() for k, v in self.skills.items()},
                    "meaning": self.meaning.to_dict(), "at": self.clock()})
                return
            # Her present on this device until home has it.
            if learned is not None:
                self._pending["skills"][learned.skill_id] = learned.to_dict()
            if use is not None:
                self._pending["uses"].append(use)
                self._pending["uses"] = self._pending["uses"][-200:]
            self._pending["meaning"] = self.meaning.to_dict()
            self._write(self._link() / PENDING_FILENAME, self._pending)
            try:
                from aurora_internal.dual_strata.strata_link import request_home
                if learned is not None:
                    request_home(self.state_dir, "screen_skill",
                                 {"skill": learned.to_dict(), "meaning": self.meaning.to_dict()})
                if use is not None:
                    request_home(self.state_dir, "screen_skill_use", dict(use))
            except Exception:
                pass                       # it waits in the pending file; the next pairing carries it

    def receive_from_home(self, payload: Mapping[str, Any]) -> str:
        """Surface: what home now knows.  What home has, she no longer holds
        as pending."""
        with self._lock:
            self._write(self._link() / HOME_COPY_FILENAME, dict(payload))
            home_skills = dict(payload.get("skills") or {})
            for sid in list(self._pending["skills"]):
                mine = int(dict(self._pending["skills"][sid]).get("version") or 0)
                if sid in home_skills and int(dict(home_skills[sid]).get("version") or 0) >= mine:
                    self._pending["skills"].pop(sid, None)
            seen = set(payload.get("uses_seen") or [])
            self._pending["uses"] = [u for u in self._pending["uses"] if u.get("use_id") not in seen]
            self._write(self._link() / PENDING_FILENAME, self._pending)
            self._load()
            return "applied"

    # -- senses ------------------------------------------------------------
    def read_frame(self) -> Optional[ScreenFrame]:
        if self.hands is None:
            return None
        frame = self.hands.read()
        if frame is not None and not frame.is_own and frame.package:
            self.last_external = frame
        return frame

    def settle(self, before: Optional[ScreenFrame], timeout: float = SETTLE_TIMEOUT_S) -> Optional[ScreenFrame]:
        """Watch until the screen has changed from ``before`` and holds still,
        or until it is clear nothing is going to change."""
        deadline = self.clock() + timeout
        last = None
        changed_once = False
        while True:
            self.hands.wait(SETTLE_POLL_S)
            frame = self.read_frame()
            if frame is not None and frames_differ(before, frame):
                changed_once = True
                if last is not None and not frames_differ(last, frame):
                    return frame
            last = frame
            if self.clock() >= deadline:
                return frame if (frame is not None or not changed_once) else last

    def observe_event(self, payload: Mapping[str, Any]) -> None:
        """A screen event from the accessibility service.  Sir's own press
        while she is being shown something is a step he is showing her."""
        node = payload.get("source_node")
        if not isinstance(node, Mapping):
            return
        pkg = str(payload.get("package") or "")
        if str(payload.get("agent") or "") != "user" or pkg in _OWN_PACKAGES:
            return
        etype = str(payload.get("event_type") or "")
        with self._lock:
            if self.episode is None:
                return
            if etype in ("view_clicked", "view_long_clicked"):
                act = "long_press" if etype == "view_long_clicked" else "tap"
                self._user_steps.append((dict(node), act, self.clock()))
            elif etype == "text_changed" and node.get("editable") and not node.get("password"):
                self._user_steps.append((dict(node, typed=str(payload.get("typed") or "")), "type",
                                         self.clock()))
            self._user_steps = self._user_steps[-12:]

    # -- attention -----------------------------------------------------------
    def wants_to_hear(self) -> bool:
        with self._lock:
            if self.episode is not None and self.episode.expired(self.clock()):
                self._expire()
            if self.episode is not None:
                return True
            return bool(self.lingering and self.clock() - self.lingering[1] < LINGER_SECONDS)

    def open_goal(self, goal_text: str, goal_words: Sequence[str], package: str = "",
                  *, base: Optional[Skill] = None, done_steps: int = 0) -> Episode:
        """The part of a request she could not do stays open, and her
        attention goes to the screen where it would be done."""
        with self._lock:
            ep = Episode(goal_text=str(goal_text)[:300], goal_words=[w for w in goal_words if w],
                         package=str(package or ""), opened_at=self.clock())
            if base is not None:
                ep.base_skill_id, ep.base_version = base.skill_id, base.version
                ep.steps = [Step.from_dict(s.to_dict()) for s in base.steps[:done_steps]]
                ep.instructions = list(base.instructions)
                ep.goal_words = list(base.goal_words) or ep.goal_words
                ep.package = ep.package or base.package
            self.episode = ep
            self.lingering = None
            self._user_steps = []
            self._count("goals_opened")
            return ep

    def _expire(self) -> Optional[Skill]:
        ep = self.episode
        self.episode = None
        if ep is not None and ep.steps:
            return self._close(ep)
        self._count("goals_left_open")
        return None

    def _goal_met(self, ep: Episode) -> bool:
        """Every word of what he asked for has been answered by a step: his
        own words at that step, or the label of the place it acted on.  Only
        the same word counts here (a near spelling is not an answer)."""
        goal = [w for w in ep.goal_words if w]
        if not goal or not ep.steps:
            return False
        answered = set()
        for st in ep.steps:
            answered.update(st.words)
            answered.update(label_words(st.target.get("text") or ""))
            answered.update(label_words(st.target.get("desc") or ""))
        for g in goal:
            if g in answered:
                continue
            if any(float(self.meaning.labels.get(g, {}).get(a, 0.0)) >= 0.7 for a in answered):
                continue
            return False
        return True

    def _count(self, key: str) -> None:
        self.counts[key] = int(self.counts.get(key, 0)) + 1

    # -- acting --------------------------------------------------------------
    def _ensure_front(self, package: str) -> Optional[ScreenFrame]:
        frame = self.read_frame()
        if not package or (frame is not None and frame.package == package):
            return frame
        if self.hands is not None and hasattr(self.hands, "bring_to_front"):
            if self.hands.bring_to_front(package):
                return self.settle(frame)
        return frame

    def _choose_action(self, node: ScreenNode, lead_in: Sequence[str], quoted: str) -> str:
        lean = self.meaning.act_lean(lead_in)
        affordances = []
        if node.editable and quoted:
            affordances.append("type")
        if node.clickable or node.actionable_ancestor or not node.editable:
            affordances.append("tap")
        if node.long_clickable:
            affordances.append("long_press")
        if node.scrollable:
            affordances += ["scroll_forward", "scroll_backward"]
        if not affordances:
            affordances = ["tap"]
        # What his lead-in words have meant before leans the choice; with no
        # history, the place's own first affordance stands.
        return max(affordances, key=lambda a: (lean.get(a, 0.0), -affordances.index(a)))

    def _act(self, frame: ScreenFrame, node: ScreenNode, action: str, text: str = "") -> Dict[str, Any]:
        out = self.hands.act(frame, node.index, action, text)
        if out.get("error") == "stale":
            fresh = self.read_frame()
            again, _ = find_target(node.signature(), fresh) if fresh is not None else (None, 0.0)
            if again is not None:
                out = self.hands.act(fresh, again.index, action, text)
        return out

    def _step_axes(self, *, grounding: float, position: int, total: int, effort: int,
                   boundary: bool, agent: str) -> Dict[str, float]:
        return {"X": round(min(1.0, grounding), 3),
                "T": round(position / float(max(1, total)), 3),
                "N": round(min(1.0, effort / float(SCROLL_TRIES + 1)), 3),
                "B": 1.0 if boundary else 0.0,
                "A": 1.0 if agent == "her" else 0.4}

    def _feel(self, axes: Mapping[str, float], source: str) -> None:
        """What happened enters her field as what it was (identity field)."""
        try:
            ifield = self.systems.get("identity_field")
            if ifield is not None and hasattr(ifield, "ingest_external_input"):
                ifield.ingest_external_input({k: float(axes.get(k, 0.5)) for k in ("X", "T", "N", "B", "A")},
                                             intensity=0.6, source=source)
        except Exception:
            pass

    # -- being shown ---------------------------------------------------------
    def hear(self, text: str) -> Dict[str, Any]:
        """One of Sir's turns while her attention is on the screen.  What he
        names is looked for on the screen, done, and watched; what he does
        with his own hands is paired with what he said."""
        with self._lock:
            if self.episode is None and self.lingering:
                sid, _ = self.lingering
                base = self.skills.get(sid)
                if base is not None:
                    self.open_goal(base.goal_words and " ".join(base.goal_words) or "",
                                   base.goal_words, base.package, base=base, done_steps=len(base.steps))
                    self.episode.quiet_turns = ATTENTION_TURNS - 1    # an extension, or nothing
            ep = self.episode
            if ep is None:
                return {"heard": False}
            ep.instructions.append(str(text)[:400])
            self._last_heard = (str(text), self.clock())
            words = list(enumerate(utterance_words(text)))
            content = set(content_words(text))
            quoted = " ".join(re.findall(r'"([^"]+)"|“([^”]+)”', str(text))[0]) \
                if re.search(r'"[^"]+"|“[^”]+”', str(text)) else ""
            quoted = quoted.strip()
            done: List[Step] = []
            uncertain: List[str] = []

            # 1. Steps his own hands showed her since the last turn.
            for node, act, _at in list(self._user_steps):
                matched = [(p, w) for p, w in words
                           if w in content and any(self.meaning.match(w, lw) >= 0.7
                                                   for lw in label_words(node.get("text", "")) + label_words(node.get("desc", "")))]
                for _, w in matched:
                    for lw in label_words(node.get("text", "")) + label_words(node.get("desc", "")):
                        if word_match(w, lw) < 0.7:
                            self.meaning.strengthen(w, lw, 0.25)
                step = Step(words=[w for _, w in matched], action=act,
                            target={k: node.get(k) for k in ("text", "desc", "view_id", "cls", "editable")},
                            package=ep.package, text=str(node.get("typed") or "") if act == "type" else "",
                            agent="sir")
                step.axes = self._step_axes(grounding=1.0, position=len(ep.steps) + 1,
                                            total=len(ep.steps) + 1, effort=0, boundary=False, agent="sir")
                step.istate = {"CAN": "CAN", "SAW": "SAW", "DID": "DID"}
                ep.steps.append(step)
                done.append(step)
                words = [(p, w) for p, w in words if (p, w) not in matched]
            self._user_steps = []

            # 2. What he names, she looks for and does, in the order he said it.
            frame = self._ensure_front(ep.package) if self.hands is not None else None
            remaining = list(words)
            effort = 0
            while remaining and frame is not None:
                candidates = ground(remaining, frame, self.meaning, content=content)
                if not candidates:
                    # Not on this screen.  If the screen can be moved, she
                    # looks further before deciding it is not here.
                    scroller = next((n for n in frame.nodes if n.scrollable), None)
                    if scroller is not None and effort < SCROLL_TRIES and any(w in content for _, w in remaining):
                        effort += 1
                        out = self._act(frame, scroller, "scroll_forward")
                        frame = self.settle(frame) if out.get("ok") else frame
                        if out.get("ok"):
                            continue
                    break
                g = candidates[0]
                lead_in = [w for p, w in remaining if p < g.first_pos and w in content]
                action = self._choose_action(g.node, [w for p, w in remaining if p < g.first_pos], quoted)
                before = frame
                out = self._act(frame, g.node, action, quoted if action == "type" else "")
                did = bool(out.get("ok"))
                after = self.settle(before) if did else frame
                saw = frames_differ(before, after)
                # What he said next to the word that grounded means the same place.
                matched_pos = {p for p, _, _ in g.matched}
                attached = [(p, w) for p, w in remaining
                            if w in content and p not in matched_pos
                            and any(abs(p - q) == 1 for q in matched_pos)
                            and p > g.first_pos]
                for _, w in attached:
                    for lw, lweight in g.node.weighted_labels():
                        if lweight >= 0.8 and word_match(w, lw) < 0.7 and not lw.isdigit():
                            self.meaning.strengthen(w, lw, 0.5)
                for w in lead_in:
                    self.meaning.learn_act(w, action)
                consumed_to = max([g.last_pos] + [p for p, _ in attached])
                step = Step(words=[w for p, w in remaining if p <= consumed_to and (w in content)],
                            action=action, target=g.node.signature(), package=frame.package,
                            text=quoted if action == "type" else "", agent="her",
                            before=before.signature(), after=after.signature() if after else {})
                step.axes = self._step_axes(grounding=g.score, position=len(ep.steps) + 1,
                                            total=len(ep.steps) + 1, effort=effort,
                                            boundary=not did, agent="her")
                step.istate = {"CAN": "CAN", "SAW": "SAW" if saw else "SAUNT", "DID": "DID" if did else "DIDNT"}
                self._feel(step.axes, "screen_step")
                if not did:
                    uncertain = [w for p, w in remaining if w in content]
                    break
                if action == "type":
                    quoted = ""
                ep.steps.append(step)
                done.append(step)
                remaining = [(p, w) for p, w in remaining if p > consumed_to]
                effort = 0
                frame = after
                if self._goal_met(ep):
                    # What he asked for is done; the rest of what he said
                    # restates it and is not another thing to press.
                    remaining = []
                    break
                if not saw:
                    # Pressed, accepted, and nothing changed: she does not
                    # assume it worked, and stops to see.
                    uncertain = [w for p, w in remaining if w in content]
                    break
            if remaining and not uncertain:
                uncertain = [w for p, w in remaining if w in content]

            if not done:
                skill = None
                if ep.steps and ep.last_turn_complete:
                    # He showed it all last turn and names nothing more now.
                    skill = self._close(ep)
                    self.episode = None
                else:
                    ep.quiet_turns += 1
                    if ep.expired(self.clock()):
                        skill = self._expire()
                return {"heard": True, "steps": 0, "watching": self.episode is not None,
                        "finished": skill is not None, "uncertain": uncertain,
                        "skill_id": skill.skill_id if skill else "",
                        "instructions": list(ep.instructions)}

            ep.quiet_turns = 0
            ep.last_frame_sig = frame.signature() if frame is not None else {}
            finished = self._goal_met(ep)
            ep.last_turn_complete = not uncertain
            skill = None
            if finished:
                skill = self._close(ep)
                self.episode = None
            return {"heard": True, "steps": len(done), "watching": self.episode is not None,
                    "finished": finished, "uncertain": uncertain,
                    "did": [s.target.get("text") or s.target.get("desc") or s.action for s in done],
                    "skill_id": skill.skill_id if skill else "",
                    "instructions": list(ep.instructions)}

    def _close(self, ep: Episode) -> Optional[Skill]:
        if not ep.steps:
            return None
        sid = ep.base_skill_id or uuid.uuid4().hex
        old = self.skills.get(sid)
        skill = Skill(skill_id=sid, goal_words=list(ep.goal_words), package=ep.package or ep.steps[0].package,
                      steps=list(ep.steps), instructions=list(ep.instructions),
                      version=(old.version + 1) if old else 1,
                      uses=old.uses if old else 0, successes=old.successes if old else 0,
                      lived_on=self._device())
        self.skills[sid] = skill
        self.lingering = (sid, self.clock())
        self._count("skills_learned" if old is None else "skills_revised")
        self._feel({"X": 0.8, "T": 1.0, "N": min(1.0, len(skill.steps) / 6.0), "B": 0.0, "A": 1.0},
                   "screen_skill_learned")
        self._persist(learned=skill)
        return skill

    def _device(self) -> str:
        if not self.is_surface():
            return "home" if self.systems.get("_strata_link_server") is not None else "phone"
        try:
            from aurora_internal.dual_strata.strata_link import surface_identity
            return str(surface_identity(self.state_dir) or "")
        except Exception:
            return ""

    # -- using what she knows -----------------------------------------------
    def recall(self, heard: Sequence[str], package: str = "") -> Tuple[Optional[Skill], float]:
        """The skill whose own words this request carries most, in the app
        named or in front."""
        best, best_cov = None, 0.0
        with self._lock:
            for sk in self.skills.values():
                if package and sk.package and sk.package != package:
                    continue
                cov = coverage(sk.goal_words, heard, self.meaning)
                if cov > best_cov:
                    best, best_cov = sk, cov
        return best, best_cov

    def perform(self, skill: Skill) -> Dict[str, Any]:
        """Do what she learned, checking each step against what she sees."""
        with self._lock:
            frame = self._ensure_front(skill.package)
            reached = 0
            saw_all = True
            failed_at = -1
            for i, step in enumerate(skill.steps):
                if frame is None:
                    failed_at = i
                    break
                if step.action in _GLOBALS:
                    out = self.hands.global_action(step.action)
                    frame = self.settle(frame) if out.get("ok") else frame
                    reached += 1 if out.get("ok") else 0
                    if not out.get("ok"):
                        failed_at = i
                        break
                    continue
                node, _ = find_target(step.target, frame)
                effort = 0
                while node is None and effort < SCROLL_TRIES:
                    scroller = next((n for n in frame.nodes if n.scrollable), None)
                    if scroller is None:
                        break
                    effort += 1
                    if not self._act(frame, scroller, "scroll_forward").get("ok"):
                        break
                    frame = self.settle(frame) or frame
                    node, _ = find_target(step.target, frame)
                # Another place that only shares his words is not the place
                # she learned; she stops here rather than press it.
                if node is None:
                    failed_at = i
                    break
                before = frame
                out = self._act(frame, node, step.action if step.action in _ACTIONS else "tap", step.text)
                if not out.get("ok"):
                    failed_at = i
                    break
                frame = self.settle(before)
                if step.after:
                    saw_all = saw_all and signature_overlap(step.after, frame.signature() if frame else {}) > 0.0
                else:
                    saw_all = saw_all and frames_differ(before, frame)
                reached += 1
            success = failed_at < 0
            use = {"use_id": uuid.uuid4().hex, "skill_id": skill.skill_id, "success": success,
                   "reached": reached, "of": len(skill.steps), "saw_as_learned": saw_all,
                   "at": self.clock(), "counted_in_version": skill.version}
            skill.uses += 1
            skill.successes += 1 if success else 0
            self._count("skills_done" if success else "skills_stopped")
            self._feel({"X": reached / float(max(1, len(skill.steps))), "T": 1.0,
                        "N": min(1.0, len(skill.steps) / 6.0), "B": 0.0 if success else 1.0,
                        "A": 1.0 if success else 0.3}, "screen_skill_used")
            self._persist(use=use)
            return {"success": success, "reached": reached, "of": len(skill.steps),
                    "failed_at": failed_at, "saw_as_learned": saw_all,
                    "did": [s.target.get("text") or s.target.get("desc") or s.action
                            for s in skill.steps[:reached]]}

    def take_request(self, user_text: str, *, launched_package: str = "",
                     consumed_words: Sequence[str] = ()) -> Dict[str, Any]:
        """A request to do something on the phone.  What she already did for
        it (an app opened) is given; what is left is matched against what she
        knows, done if she knows it, and held open if she does not."""
        if self._last_heard[0] == str(user_text) and self.clock() - self._last_heard[1] < 30.0:
            # This turn already reached her as something he was showing her.
            return {"state": "heard_as_shown"}
        if self.hands is None or (hasattr(self.hands, "available") and not self.hands.available()):
            return {"state": "no_screen"}
        heard = [w for w in content_words(user_text)
                 if w not in {c.lower() for c in consumed_words}]
        package = launched_package
        if not package and self.last_external is not None and self.clock() - self.last_external.at < 180.0:
            package = self.last_external.package
        if not heard:
            return {"state": "nothing_left"}
        skill, cov = self.recall(heard, package)
        if skill is not None and cov >= 0.5:
            # She knows this; how sure she is comes from what happened before
            # and from how much of it he asked for.
            result = self.perform(skill)
            result.update({"state": "done" if result["success"] else "stopped",
                           "skill_id": skill.skill_id, "coverage": round(cov, 3),
                           "unsure": cov < 0.75 or skill.confidence() < 0.5,
                           "package": skill.package})
            if not result["success"]:
                self.open_goal(user_text, skill.goal_words, skill.package, base=skill,
                               done_steps=max(0, result["failed_at"]))
            return result
        # She does not know it.  It opens only where there is a screen for it:
        # an app she just opened, or the one in front whose places his words touch.
        if launched_package or (package and self.last_external is not None
                                and ground(list(enumerate(heard)), self.last_external, self.meaning)):
            self.open_goal(user_text, heard, package)
            return {"state": "open", "unknown": heard, "package": package}
        return {"state": "not_a_phone_task"}

    def act_on(self, action: str, target: str, text: str = "") -> Dict[str, Any]:
        """A single act she chooses (the mobile_screen_act tool)."""
        if self.hands is None:
            return {"ok": False, "error": "screen hands not enabled"}
        if action in _GLOBALS:
            out = self.hands.global_action(action)
            return {"ok": bool(out.get("ok")), "data": action, "error": out.get("error", "")}
        frame = self.read_frame()
        if frame is None:
            return {"ok": False, "error": "nothing seen"}
        cands = ground(list(enumerate(utterance_words(target))), frame, self.meaning) if target else []
        if not cands:
            return {"ok": False, "error": f"not on this screen: {target}"}
        node = cands[0].node
        out = self._act(frame, node, action if action in _ACTIONS else "tap", text)
        return {"ok": bool(out.get("ok")), "data": f"{action} {node.label()}", "error": out.get("error", "")}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            ep = self.episode
            return {"skills": len(self.skills), "words_learned": len(self.meaning.labels),
                    "watching": ep is not None,
                    "open_goal": ep.goal_words if ep else [],
                    "steps_seen": len(ep.steps) if ep else 0,
                    "surface": self.is_surface(),
                    "pending_for_home": len(self._pending.get("skills") or {}) + len(self._pending.get("uses") or []),
                    "counts": dict(self.counts),
                    "known": [{"words": s.goal_words, "app": s.package, "steps": len(s.steps),
                               "confidence": round(s.confidence(), 2)} for s in self.skills.values()][:20]}


def _read_json_file(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# One per mind
# ---------------------------------------------------------------------------

_INSTANCE: Optional[ScreenApprenticeship] = None
_INSTANCE_LOCK = threading.Lock()


def get_apprenticeship(systems: Optional[Dict[str, Any]] = None) -> Optional[ScreenApprenticeship]:
    """Her apprenticeship on this device.  Hands exist only on the phone app;
    elsewhere it is None unless one was installed (tests, a stand-in)."""
    global _INSTANCE
    if isinstance(systems, dict) and isinstance(systems.get("screen_apprenticeship"), ScreenApprenticeship):
        return systems["screen_apprenticeship"]
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            import os
            if os.environ.get("AURORA_ANDROID") != "1":
                return None
            state_dir = (systems or {}).get("state_dir") if isinstance(systems, dict) else None
            state_dir = state_dir or os.environ.get("AURORA_STATE_DIR") or os.getcwd()
            _INSTANCE = ScreenApprenticeship(state_dir, AndroidScreenHands(), systems)
        if isinstance(systems, dict):
            systems["screen_apprenticeship"] = _INSTANCE
            _INSTANCE.systems = systems
        return _INSTANCE


def install(app: Optional[ScreenApprenticeship], systems: Optional[Dict[str, Any]] = None) -> None:
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = app
    if isinstance(systems, dict):
        if app is None:
            systems.pop("screen_apprenticeship", None)
        else:
            systems["screen_apprenticeship"] = app


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

class HomeScreenSkills:
    """Home's end: the skills her surface learned, kept here with the rest of
    her deep learning, and handed back down as what she knows."""

    def __init__(self, state_dir: Any) -> None:
        self.state_dir = Path(str(state_dir))
        data = _read_json_file(self.state_dir / SKILLS_FILENAME)
        self.skills: Dict[str, Dict[str, Any]] = dict(data.get("skills") or {})
        self.meaning = ScreenMeaning(data.get("meaning") or {})
        self.uses_seen: List[str] = list(data.get("uses_seen") or [])

    def _save(self) -> None:
        from aurora_persistence_utils import atomic_write_json
        atomic_write_json(self.state_dir / SKILLS_FILENAME, {
            "skills": self.skills, "meaning": self.meaning.to_dict(),
            "uses_seen": self.uses_seen[-500:], "at": time.time()}, default=str)

    def take(self, request: Mapping[str, Any]) -> str:
        kind = str(request.get("kind") or "")
        payload = dict(request.get("payload") or {})
        if kind == "screen_skill":
            skill = dict(payload.get("skill") or {})
            sid = str(skill.get("skill_id") or "")
            if not sid:
                return "unreadable"
            have = self.skills.get(sid)
            if have is None or int(skill.get("version") or 0) >= int(have.get("version") or 0):
                if have is not None:
                    # Uses home already counted stay counted.
                    skill["uses"] = max(int(skill.get("uses") or 0), int(have.get("uses") or 0))
                    skill["successes"] = max(int(skill.get("successes") or 0), int(have.get("successes") or 0))
                self.skills[sid] = skill
            self.meaning.merge(ScreenMeaning(payload.get("meaning") or {}))
            self._save()
            return "learned"
        if kind == "screen_skill_use":
            uid = str(payload.get("use_id") or "")
            sid = str(payload.get("skill_id") or "")
            if uid and uid not in self.uses_seen and sid in self.skills:
                sk = self.skills[sid]
                sk["uses"] = int(sk.get("uses") or 0) + 1
                sk["successes"] = int(sk.get("successes") or 0) + (1 if payload.get("success") else 0)
                self.uses_seen.append(uid)
                self._save()
            return "counted"
        return "not_screen_skill"

    def snapshot(self) -> Dict[str, Any]:
        return {"skills": self.skills, "meaning": self.meaning.to_dict(),
                "uses_seen": self.uses_seen[-500:], "at": time.time()}


def relay_down(state_dir: Any, outbox: Any, memo: Dict[str, Any]) -> int:
    """Home's downlink collector: when what she knows changed, the surface
    gets the whole of it (it is small)."""
    path = Path(str(state_dir)) / SKILLS_FILENAME
    if not path.exists():
        return 0
    try:
        stat = path.stat()
    except OSError:
        return 0
    stamp = f"{stat.st_mtime_ns}:{stat.st_size}"
    if memo.get("screen_skills_stamp") == stamp:
        return 0
    snap = HomeScreenSkills(state_dir).snapshot()
    digest = hashlib.sha256(json.dumps({k: snap[k] for k in ("skills", "meaning", "uses_seen")},
                                       sort_keys=True, default=str).encode()).hexdigest()
    memo["screen_skills_stamp"] = stamp
    if memo.get("screen_skills_digest") == digest:
        return 0
    outbox.append(DOWN_CHANNEL, "state", snap)
    memo["screen_skills_digest"] = digest
    return 1


def receive_down(state_dir: Any, payload: Mapping[str, Any]) -> str:
    """Surface side of the downlink channel."""
    app = _INSTANCE
    if app is not None and app.state_dir.resolve() == Path(str(state_dir)).resolve():
        return app.receive_from_home(payload)
    from aurora_persistence_utils import atomic_write_json
    try:
        from aurora_internal.dual_strata.strata_link import link_dir
        link = Path(link_dir(state_dir))
    except Exception:
        link = Path(str(state_dir)) / "strata_link"
    atomic_write_json(link / HOME_COPY_FILENAME, dict(payload), default=str)
    return "applied"
