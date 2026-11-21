# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Her kept use of words: only conversation she took part in, bounded, saved, and what the crystal pass reads to find her function words."""
import json
import os
import re

from aurora_internal import aurora_word_use as U, crystal_runtime as R, crystal_substitutability as S
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger


def test_conversation_is_kept_as_use_and_text_that_is_not_conversation_is_turned_away(tmp_path):
    w = U.WordUse(str(tmp_path))
    assert w.observe_text("the bird sang and the dog ran", "live_user") == 7
    assert w.observe_text("a bird is a kind of animal", "dictionary") == 0          # reference text is never use
    assert w.observe_text("a bird is a kind of animal", "understanding_development") == 0
    assert w.observe_text("hello there", "") == 0
    assert w.turned_away == 3 and w.profiles.count("kind") == 0 and w.profiles.count("and") == 1


def test_small_words_and_repeats_are_kept_in_order_with_edges_so_their_use_can_be_compared(tmp_path):
    w = U.WordUse(str(tmp_path))
    w.observe_text("I saw a dog. A dog ran. a bird sang.", "live_aurora")
    assert w.profiles.count("a") == 3 and w.profiles.count("i") == 1 and w.profiles.count("dog") == 2
    assert w.profiles.state()["ctx"]["a"]["L"] == {"saw": 1, S.START: 2}              # a sentence start is an edge, not a neighbour


def test_it_survives_a_restart_and_only_writes_when_something_changed(tmp_path):
    t = [1000.0]
    w = U.WordUse(str(tmp_path))
    assert w.save(force=True, clock=lambda: t[0]) is True and not os.path.exists(w.path)       # nothing observed, nothing written
    w.observe_text("the dog ran", "live_user")
    w.save(clock=lambda: t[0])
    assert os.path.exists(w.path)
    mtime = os.path.getmtime(w.path)
    w.observe_text("the cat ran", "live_user")
    t[0] += 5
    w.save(clock=lambda: t[0])                                                           # inside the interval: not yet
    assert json.load(open(w.path))["profiles"]["n"].get("cat") is None
    t[0] += U.SAVE_EVERY
    w.save(clock=lambda: t[0])
    assert json.load(open(w.path))["profiles"]["n"]["cat"] == 1
    again = U.WordUse(str(tmp_path))
    assert again.profiles.count("ran") == 2 and again.profiles.count("the") == 2
    assert os.path.getmtime(w.path) >= mtime


def test_it_is_bounded(tmp_path):
    w = U.WordUse(str(tmp_path), max_words=40, max_contexts=6)
    for i in range(400):
        w.observe_text(f"w{i} the w{i + 1} and w{i + 2}", "live_user")
    assert len(w.profiles.vocabulary()) <= 40 + 10
    assert all(len(d["L"]) <= 6 + 1 and len(d["R"]) <= 6 + 1 for d in w.profiles.state()["ctx"].values())


def test_the_ledger_keeps_it_and_saves_it_whether_or_not_crystals_hold_its_record(tmp_path):
    led = AuroraResolutionLedger(state_dir=str(tmp_path), persist=True)
    assert led.note_word_use("the dog ran and the cat sat", "live_user") > 0
    assert led.note_word_use("a bird is a kind of animal", "dictionary") == 0
    led._crystals = object()                                                              # crystals own the ledger's record: no file of its own
    try:
        led.save(force=True)
    except Exception:
        pass
    assert U.load_profiles(str(tmp_path)).count("and") == 1


def test_the_ledger_never_raises_from_it(tmp_path):
    led = AuroraResolutionLedger(state_dir=str(tmp_path), persist=False)
    assert led.note_word_use(None, "live_user") == 0
    led.state_dir = None
    led._word_use = None
    assert led.note_word_use("x y", "live_user") in (0, 2)


def test_load_profiles_is_none_until_something_is_kept(tmp_path):
    assert U.load_profiles(str(tmp_path)) is None
    (tmp_path / U.FILENAME).write_text("not json")
    assert U.load_profiles(str(tmp_path)) is None


def test_the_pass_finds_her_function_words_from_her_kept_use(tmp_path):
    w = U.WordUse(str(tmp_path))
    nouns, verbs = ["dog", "cat", "bird", "fish", "frog", "bear"], ["ran", "sat", "sang", "swam", "hopped", "ate"]
    for i in range(30):
        for j, (n, v) in enumerate(zip(nouns, verbs)):
            for joiner in ("and", "or"):                                                    # both join the same kinds of things, in the same places
                w.observe_text(f"the {n} {v} {joiner} the {nouns[(j + i) % 6]} {verbs[(j + 2 * i) % 6]}", "live_user")
            w.observe_text(f"a {n} {v}", "live_user")
    w.save(force=True)
    prof = R.word_profiles({}, str(tmp_path))
    assert prof.count("and") > 100 and prof.count("a") > 100 and prof.count("or") > 100
    assert prof.function_likeness("the") > prof.function_likeness("bear")
    assert prof.similarity("and", "or") > prof.similarity("and", "bear")


def test_kept_use_is_not_counted_twice_when_the_lexical_feed_saw_the_same_turns(tmp_path):
    w = U.WordUse(str(tmp_path))
    w.observe_text("the dog ran", "live_user")
    w.save(force=True)

    class F:
        role, content = R.LEX_ROLE, json.dumps({"contexts": S.ContextProfiles().state() | {"n": {"dog": 99}, "ctx": {"dog": {"L": {"the": 99}, "R": {"ran": 99}}}}})

    class C:
        facets = {"f": F()}
    assert R.word_profiles({"c": C()}, str(tmp_path)).count("dog") == 1                  # kept use wins; the lexical feed is the fallback
    os.remove(os.path.join(str(tmp_path), U.FILENAME))
    assert R.word_profiles({"c": C()}, str(tmp_path)).count("dog") == 99


def test_durable_word_use_does_not_recount_a_turn_from_conversation_memory(tmp_path):
    w = U.WordUse(str(tmp_path))
    w.observe_text("the dog ran", "live_user")
    assert w.save(force=True)
    (tmp_path / "aurora_conversation_memory.json").write_text(
        json.dumps({"entries": [{"user_said": "the dog ran", "aurora_said": "the bird flew"}]})
    )
    # These records overlap.  WordUse is the primary evidence once present:
    # the saved conversation is not a second occurrence of the same turn.
    prof = R.word_profiles({}, str(tmp_path))
    assert prof.count("dog") == 1
    assert prof.count("bird") == 0

    # Older checkpoints with no durable WordUse still have their legacy fallback.
    os.remove(os.path.join(str(tmp_path), U.FILENAME))
    legacy = R.word_profiles({}, str(tmp_path))
    assert legacy.count("dog") == 1
    assert legacy.count("bird") == 1


def test_only_conversation_sources_reach_it_and_the_live_feed_names_them():
    base = os.path.join(os.path.dirname(__file__), "..", "aurora_internal")
    assert U.SOURCES == {"live_user", "live_aurora", "history_user", "history_aurora"}
    src = open(os.path.join(base, "aurora_live_experience.py"), encoding="utf-8").read()
    assert re.search(r'note_word_use\(text, f"live_', src)
    callers = [f for f in os.listdir(base) if f.endswith(".py") and "note_word_use(" in open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()]
    assert sorted(callers) == ["aurora_live_experience.py", "aurora_resolution_ledger.py"]


def test_merge_adds_counts_and_keeps_the_bounds():
    a, b = S.ContextProfiles(max_words=8, max_contexts=3), S.ContextProfiles()
    a.observe(["x", "y", "x"])
    for i in range(20):
        b.observe([f"q{i}", "x", f"r{i}"])
    a.merge(b.state())
    assert a.count("x") == 22 and len(a.vocabulary()) <= 8 + 2
    assert all(len(d["L"]) <= 3 + 1 for d in a.state()["ctx"].values())


def test_the_live_feed_names_who_spoke_and_hands_over_the_whole_text():
    from aurora_internal import aurora_live_experience as live

    class Ledger:
        def __init__(self):
            self.noted = []

        def observe_event(self, **kw):
            return {"observed": False}

        def note_word_use(self, text, source):
            self.noted.append((text, source))

    class Ex:
        def attach_systems(self, s):
            pass

        def register_consumer(self, *a):
            pass

    led = Ledger()
    systems = {"resolution_ledger": led, "representation_exchange": Ex()}
    live.observe_user_event(systems, "A dog ran and a cat sat.")
    live.observe_reply_event(systems, "The dog sat or the cat ran.")
    assert led.noted == [("A dog ran and a cat sat.", "live_user"), ("The dog sat or the cat ran.", "live_aurora")]


def test_merging_two_profiles_adds_what_each_saw_on_each_side():
    a, b = S.ContextProfiles(), S.ContextProfiles()
    a.observe(["the", "dog", "ran"])
    b.observe(["the", "dog", "sat"])
    b.observe(["the", "dog", "ran"])
    a.merge(b.state())
    st = a.state()["ctx"]["dog"]
    assert st["L"] == {"the": 3} and st["R"] == {"ran": 2, "sat": 1}
