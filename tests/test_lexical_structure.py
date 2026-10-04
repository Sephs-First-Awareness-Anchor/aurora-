# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Word-level relational structure: classes of words discovered from the words themselves (not from the
five roots), manufactured into symbols the path machinery can hang distinctions on.
"""
import inspect
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_internal.aurora_lexical_structure import LexicalStructure  # noqa: E402
from aurora_internal.aurora_representation_crystals import RepresentationCrystals  # noqa: E402
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger  # noqa: E402

GREET, REPLY = ["hello", "hi", "hey"], ["hello", "hi", "hey", "there", "you"]
CONTENT = [f"w{i}" for i in range(300)]


def _exchanges(n, p_greet, seed=5):
    """Yield (user_tokens, reply_tokens).  Sizes/gaps are drawn by the caller, independent of greeting."""
    rng = random.Random(seed)
    for _ in range(n):
        if rng.random() < p_greet:
            yield [rng.choice(GREET)], rng.sample(REPLY, 2)
        else:
            yield rng.sample(CONTENT, 10), rng.sample(CONTENT, 20)


def test_observe_event_assigns_first_act_exactly_once():
    source = inspect.getsource(AuroraResolutionLedger.observe_event)
    assert source.count("first_act = actor not in st.episode_actors") == 1


def test_words_with_alike_distinctive_responses_form_a_class_and_bland_words_do_not():
    lex = LexicalStructure()
    for i, (user, reply) in enumerate(_exchanges(3000, 0.15)):
        lex.observe(user, "live", f"ep{i}")
        lex.observe(reply, "live", f"ep{i}")
    classes = lex.describe()
    assert classes, "a class of greeting words should have been discovered"
    members = set().union(*[set(m) for m in classes.values()])
    assert len(members & set(GREET)) >= 2
    assert not any(m.startswith("w") and m[1:].isdigit() for m in members)       # diffuse content words form nothing
    slot = next(k for k, m in enumerate(lex._members) if m & set(GREET))
    assert lex.bits(["hello"])[slot] == 1 and not any(lex.bits(["w1", "w2"]))


def test_a_language_with_no_distinctive_word_relations_yields_no_classes():
    lex = LexicalStructure()
    for i, (user, reply) in enumerate(_exchanges(3000, 0.0)):
        lex.observe(user, "live", f"ep{i}")
        lex.observe(reply, "live", f"ep{i}")
    assert lex.active_slots() == []


def test_the_lexical_state_round_trips():
    lex = LexicalStructure()
    for i, (user, reply) in enumerate(_exchanges(3000, 0.15)):
        lex.observe(user, "live", f"ep{i}")
        lex.note_waveform(lex.bits(user), [0.9, 0.1, 0.2, 0.3, 0.4])
        lex.observe(reply, "live", f"ep{i}")
    twin = LexicalStructure()
    twin.restore(lex.state())
    assert twin.describe() == lex.describe() and twin.coordinate(lex.active_slots()[0]) == lex.coordinate(lex.active_slots()[0])


def _ledger_run(lexical, n=6000, seed=9):
    """The five roots carry NO information about greetings: sizes and gaps are drawn independently of them."""
    rng = random.Random(seed)
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=2, lexical=lexical)
    index = 0
    for i, (user, reply) in enumerate(_exchanges(n, 0.15, seed)):
        for actor, tokens in (("external_user", user), ("responder", reply)):
            ledger.observe_event(event_index=index, event_id=f"e{index}", episode_id=f"ep{i}", actor=actor,
                                 text_length=int(rng.uniform(20, 800)), elapsed_seconds=rng.uniform(1, 600),
                                 episode_gap_seconds=rng.uniform(1, 600), tokens=tokens)
            index += 1
    return ledger


def test_word_classes_give_the_paths_a_distinction_the_roots_cannot():
    with_words = _ledger_run(True)
    assert with_words.status()["lexical_classes"]
    lexical_paths = {r["path"] for s in with_words.status()["subjects"] for r in with_words.discovered(s)
                     if any(p.startswith("L") for p in r["path"].split(">"))}
    assert lexical_paths, "a word-class path should be earned although the roots say nothing about greetings"
    without = _ledger_run(False)
    assert not any("L" in r["path"] for s in without.status()["subjects"] for r in without.discovered(s))


def test_a_word_class_representation_still_lands_on_a_crystal_by_where_its_events_sit():
    coordinate = RepresentationCrystals.coordinate("L0>L0", {"L0": {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}})
    assert all(abs(v - 0.2) < 1e-9 for v in coordinate.values())
    assert all(v == 0.0 for v in RepresentationCrystals.coordinate("L0>L0").values())      # without it: nowhere


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as exc:
                failures += 1; print("FAIL", name, type(exc).__name__, str(exc)[:300])
    sys.exit(1 if failures else 0)
