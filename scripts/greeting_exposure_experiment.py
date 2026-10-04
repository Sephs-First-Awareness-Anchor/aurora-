#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Repeated-exposure experiment: does a greeting become a represented pattern?

A measurement harness, not part of Aurora's cognition.  It exposes the real pipeline
(resolution ledger with hypotheses on crystals -> representation exchange -> representations
and word facets on crystals, over a real CrystalProcessingSystem store) to a curriculum of
conversations in which a fraction open with a greeting exchange (a brief greeting answered
by a brief reply).  Nothing in the pipeline is told what a greeting is.

For each exposure level it reports, over the window since the last checkpoint:
  * how many earned (non-positional) representations target the energy root (N);
  * at OPENING exchanges, the mean expectation (P[reply is high-N]) split by whether the
    opening was a greeting, and how often the expectation was right;
  * which greeting-vocabulary words became `word` facets, on which POLE crystal.

Controls: no greetings at all; and greeting exchanges scrambled to random positions (the
words and brevity remain, the opening structure is destroyed).

Usage:  python3 scripts/greeting_exposure_experiment.py --p-greet 0.05 [--scramble] --episodes 2500
"""
import argparse
import json
import math
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker  # noqa: E402
from aurora_internal.aurora_representation_crystals import HypothesisCrystals, RepresentationCrystals  # noqa: E402
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange  # noqa: E402
from aurora_internal.aurora_resolution_ledger import AXES, SYMBOLS, AuroraResolutionLedger  # noqa: E402
from concept_crystal import ConceptCrystalRegistry  # noqa: E402

GREET = ["hello", "hi", "hey"]
REPLY = ["hello", "hi", "hey", "there", "you"]
CONTENT = [f"w{i}" for i in range(300)]
GREETING_WORDS = set(GREET) | set(REPLY)


def _content_exchange(rng):
    return [
        {"actor": "external_user", "len": rng.randint(40, 600), "tokens": rng.sample(CONTENT, 12)},
        {"actor": "responder", "len": rng.randint(100, 1200), "tokens": rng.sample(CONTENT, 30)},
    ]


def _greeting_exchange(rng):
    return [
        {"actor": "external_user", "len": rng.randint(3, 12), "tokens": [rng.choice(GREET)]},
        {"actor": "responder", "len": rng.randint(8, 40), "tokens": rng.sample(REPLY, 2)},
    ]


def episode(rng, greeting, scramble):
    """One conversation.  The gap before it is drawn from the SAME distribution for every kind."""
    body = [ex for _ in range(rng.randint(2, 6)) for ex in _content_exchange(rng)]
    if greeting and not scramble:
        events = _greeting_exchange(rng) + body                      # opens with the greeting
    elif greeting and scramble:
        at = 2 * rng.randint(1, max(1, len(body) // 2 - 1))
        events = _content_exchange(rng) + body[:at] + _greeting_exchange(rng) + body[at:]
    else:
        events = _content_exchange(rng) + body
    events[0] = dict(events[0], gap=math.exp(rng.gauss(10.0, 1.5)))
    return events


def pole_words(registry):
    """Greeting-vocabulary `word` facets and the pole of the crystal they sit on."""
    found = {}
    for crystal in registry.all_crystals():
        sig = getattr(crystal, "constraint_signature", None) or {}
        for facet in crystal.facets.values():
            if facet.role == "word" and str(facet.content) in GREETING_WORDS:
                pole = "-".join(f"{ax}{'-' if float(sig.get(ax, 0)) < 0 else '+'}" for ax in AXES if float(sig.get(ax, 0)) != 0)
                found.setdefault(str(facet.content), set()).add(pole)
    return {w: sorted(p) for w, p in sorted(found.items())}


def run(episodes, p_greet, seed, scramble, checkpoints, tail=False, lexical=False):
    rng = random.Random(seed)
    tsym = "n" if tail else "N"          # the symbol whose pole separates a brief reply from an ordinary one
    cps = CrystalProcessingSystem(EvolutionTracker())
    registry = ConceptCrystalRegistry()
    registry.bind(cps.crystals, cps.concept_index)
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=3, tail=tail, lexical=lexical)
    ledger.attach_crystals(HypothesisCrystals(registry))
    exchange = AuroraRepresentationExchange(ledger, state_dir=tempfile.mkdtemp(), persist=False)
    exchange.attach_crystals(RepresentationCrystals(registry), known_word=lambda w: True)

    window = {"greeting": [], "other": []}
    snapshots, greetings_seen, index = [], 0, 0
    for e in range(episodes):
        is_greeting = rng.random() < p_greet
        greetings_seen += 1 if is_greeting else 0
        prediction = None
        for j, ev in enumerate(episode(rng, is_greeting, scramble)):
            ledger.observe_event(
                event_index=index, event_id=f"e{index}", episode_id=f"ep{e}", actor=ev["actor"],
                text_length=ev["len"], elapsed_seconds=ev.get("gap", 20.0), episode_gap_seconds=ev.get("gap"), tokens=ev["tokens"],
            )
            exchange.after_event(index, tokens=ev["tokens"])
            if j == 0:                                       # the opening user event just arrived
                qualifying = {
                    v["path"] for v in exchange.representations(status="earned") if not v["positional"] and v["target"] == tsym
                }
                exps = [x for x in ledger.expectations("external_user") if x["path"] in qualifying and x["target"] == tsym]
                prediction = sum(x["p_high"] for x in exps) / len(exps) if exps else None
            elif j == 1 and prediction is not None:         # ...and now the reply
                bit = ledger.last_bits()[1][SYMBOLS.index(tsym)]
                window["greeting" if is_greeting else "other"].append((prediction, bit))
            index += 1
        if (e + 1) in checkpoints:
            def summarize(rows):
                if not rows:
                    return {"n": 0}
                return {"n": len(rows), "mean_p_high": round(sum(p for p, _ in rows) / len(rows), 3),
                        "right": round(sum(1 for p, b in rows if (p > 0.5) == bool(b)) / len(rows), 3)}
            ledger.sync_crystals(force=True)         # what the environment's checkpoint and the live runtime do
            exchange.crystallize()
            earned = [v for v in exchange.representations(status="earned") if not v["positional"]]
            snapshots.append({
                "episodes": e + 1, "greeting_episodes_seen": greetings_seen,
                "earned_nonpositional": len(earned), "earned_targeting_N": sum(1 for v in earned if v["target"] == tsym),
                "openings_greeting": summarize(window["greeting"]), "openings_other": summarize(window["other"]),
                "greeting_word_facets": pole_words(registry),
                "lexical_classes": ledger.status().get("lexical_classes"),
                "lexical_paths": [v["path"] for v in exchange.representations(status="earned") if any(p.startswith("L") for p in v["path"].split(">"))],
            })
            window = {"greeting": [], "other": []}
    return snapshots


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episodes", type=int, default=2500)
    parser.add_argument("--p-greet", type=float, default=0.05)
    parser.add_argument("--scramble", action="store_true")
    parser.add_argument("--tail", action="store_true", help="enable the low-tail symbols (rare-brief resolution)")
    parser.add_argument("--lexical", action="store_true", help="enable word-class symbols discovered from the words themselves")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    marks = sorted({100, 250, 500, 1000, 2000, args.episodes})
    snaps = run(args.episodes, args.p_greet, args.seed, args.scramble, set(marks), args.tail, args.lexical)
    label = f"p_greet={args.p_greet}{' scrambled' if args.scramble else ''}{' tail' if args.tail else ''}"
    print(json.dumps({"condition": label, "snapshots": snaps}, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps({"condition": label, "snapshots": snaps}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
