# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_representation_exchange: a use-and-consequence loop that is
open to ANY subject of representation.

The consumers below are deliberately unlike one another and none is the web or
lexical grounding: the loop only knows the one-method protocol.  It must also
close with no consumers at all.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from aurora_internal.aurora_representation_exchange import (  # noqa: E402
    AuroraRepresentationExchange,
    RepresentationConsumerMixin,
)
from aurora_internal.aurora_resolution_ledger import AXES, AuroraResolutionLedger  # noqa: E402
from test_resolution_ledger import _stream  # noqa: E402


class _Collector:                       # a store: keeps whatever it is offered
    def __init__(self):
        self.seen = {}

    def accept_representation(self, rep, context):
        self.seen[rep["id"]] = context["expectation"]
        return {"accepted": True}


class _Planner:                         # an actor: bets on the expectation, learns the outcome in its own domain
    def __init__(self):
        self.pending = {}

    def accept_representation(self, rep, context):
        exp = context["expectation"]
        self.pending[context["use_id"]] = (exp["target"], exp["p_high"] > 0.5)
        return {"bet": exp["p_high"] > 0.5}


class _Decliner:
    def accept_representation(self, rep, context):
        return None


class _Raiser:
    def accept_representation(self, rep, context):
        raise RuntimeError("a misbehaving subject must not break the loop")


class _OptedIn(RepresentationConsumerMixin):
    pass


def _loop(mode, consumers=None, n=9000, directory=None, events=None, ledger=None, exchange=None):
    ledger = ledger or AuroraResolutionLedger(state_dir=directory or tempfile.mkdtemp(), persist=bool(directory), max_path=3)
    exchange = exchange or AuroraRepresentationExchange(ledger, state_dir=directory or tempfile.mkdtemp(), persist=bool(directory))
    for name, consumer in (consumers or {}).items():
        exchange.register_consumer(name, consumer)
    planner = (consumers or {}).get("planner")
    for ev in (events if events is not None else _stream(n, mode)):
        ledger.observe_event(**ev)
        if planner is not None:                       # the planner's own-domain consequence of the previous bet
            _, bits = ledger.last_bits()
            for use_id, (target, bet) in list(planner.pending.items()):
                hit = bool(bits[AXES.index(target)]) == bet
                exchange.report_consequence(use_id, "positive" if hit else "negative", 1.0 if hit else 0.0)
                planner.pending.pop(use_id)
        exchange.after_event(ev["event_index"])
    return ledger, exchange


def test_loop_closes_with_no_consumers_at_all():
    _, exchange = _loop("pair")
    earned = {v["path"] for v in exchange.representations(status="earned")}
    assert "T>N" in earned, exchange.representations()
    rep = next(v for v in exchange.representations() if v["path"] == "T>N")
    assert rep["z"] >= 3.0 and rep["mean_gain_bits"] > 0 and rep["hit_rate"] > 0.8, rep
    assert rep["accepted"] == 0


def test_no_dependence_means_no_representation_is_earned():
    _, exchange = _loop("null")
    assert exchange.representations(status="earned") == []


def test_any_subject_of_representation_can_use_it_and_the_loop_stays_open():
    store, planner, decliner, raiser, opted = _Collector(), _Planner(), _Decliner(), _Raiser(), _OptedIn()
    systems = {"a_store": store, "an_actor": planner, "refuser": decliner, "faulty": raiser,
               "opted_in": opted, "not_a_consumer": object()}
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3)
    exchange = AuroraRepresentationExchange(ledger, state_dir=tempfile.mkdtemp(), persist=False)
    assert exchange.attach_systems(systems) == 5 and "not_a_consumer" not in exchange.consumers()
    planner_registered = {"planner": planner}
    exchange.register_consumer("planner", planner)
    _, exchange = _loop("pair", consumers=planner_registered, ledger=ledger, exchange=exchange)

    stats = exchange.status()["consumer_stats"]
    assert stats["a_store"]["accepted"] > 0 and stats["opted_in"]["accepted"] > 0
    assert stats["refuser"]["offered"] > 0 and stats["refuser"]["accepted"] == 0
    assert stats["faulty"]["failed"] > 0 and stats["faulty"]["accepted"] == 0
    assert any(k.endswith(":T>N") for k in store.seen)
    assert opted.representation_uses()
    earned = exchange.representations(status="earned")
    assert any(v["path"] == "T>N" for v in earned), exchange.representations()
    rep = next(v for v in earned if v["path"] == "T>N")
    assert rep["domain"]["an_actor"]["reports"] > 100 and rep["domain"]["an_actor"]["mean_score"] > 0.8  # one object, registered once (identity dedupe)


def test_a_consumer_reporting_harm_in_its_own_domain_blocks_earning():
    uni = {"n": 1000.0, "nb": 10.0, "bsum": 2.0, "bsq": 0.4002}
    ok = {"c": {"n": 200, "sum": 150.0, "ok": 150}}
    harmed = {"c": {"n": 200, "sum": 50.0, "ok": 10}}
    assert AuroraRepresentationExchange.classify(uni, 1, ok) == "earned"
    assert AuroraRepresentationExchange.classify(uni, 1, harmed) == "in_use"
    assert AuroraRepresentationExchange.classify(uni, 0, harmed) == "candidate"
    assert AuroraRepresentationExchange.classify(dict(uni, bsum=-2.0), 1, ok) == "dissolved"
    assert AuroraRepresentationExchange.classify({"n": 30.0, "nb": 0.0, "bsum": 0.0, "bsq": 0.0}, 1, {}) == "in_use"


def test_after_event_is_idempotent_on_event_index():
    ledger, exchange = _loop("pair", n=600)
    before = exchange.representations()
    assert exchange.after_event(10)["processed"] is False
    assert exchange.representations() == before


def test_resume_is_equivalent_to_uninterrupted_run():
    events = list(_stream(4000, "pair"))
    _, whole = _loop("pair", events=events)
    directory = tempfile.mkdtemp()
    ledger1, exchange1 = _loop("pair", directory=directory, events=events[:2000])
    assert ledger1.save() and exchange1.save()
    ledger2 = AuroraResolutionLedger(state_dir=directory, max_path=3)
    exchange2 = AuroraRepresentationExchange(ledger2, state_dir=directory)
    _loop("pair", events=events[2000:], ledger=ledger2, exchange=exchange2)
    strip = lambda views: [{k: v for k, v in x.items() if k not in ("offered", "accepted")} for x in views]
    assert strip(exchange2.representations()) == strip(whole.representations())


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as exc:
                failures += 1
                print("FAIL", name, str(exc)[:300])
    sys.exit(1 if failures else 0)
