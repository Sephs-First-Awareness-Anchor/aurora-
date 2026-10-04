# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Build 922 regression canaries for clause boundaries and permanent irreducible recognition."""
from __future__ import annotations

import tempfile
from collections import deque

from concept_crystal import ConceptCrystalRegistry
from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form
from aurora_internal.aurora_representation_crystals import RepresentationCrystals
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger


def test_clause_boundary_patch_preserves_relation_without_assigning_meaning():
    cases = [
        ("If the battery dies, the motor stops.", "if", "fronted", 2),
        ("The motor starts after I charge the battery.", "after", "medial", 2),
        ("Before I leave, I charge the battery.", "before", "fronted", 2),
        ("The motor stops unless the battery runs.", "unless", "medial", 2),
        ("Because I bumped the table, the glass fell.", "because", "fronted", 2),
        ("The motor is fast but the battery is weak.", "but", "coordinated", 2),
    ]
    for text, connector, position, clauses in cases:
        form = extract_relational_form(text, parsed={}, feed_lexical_grounding=False)
        rels = form.get("clause_relations") or []
        assert rels and rels[0]["connector"] == connector and rels[0]["position"] == position
        assert len(form.get("clauses") or []) + 1 == clauses

    one = extract_relational_form("The motor is tired but happy.", parsed={}, feed_lexical_grounding=False)
    assert not one.get("clause_relations") and not one.get("clauses")

    q = extract_relational_form("What happens if the battery dies?", parsed={}, feed_lexical_grounding=False)
    assert q.get("question") and len(q.get("clauses") or []) == 0
    assert (q.get("clause_relations") or [])[0]["position"] == "constraint"


def _prepared_lexical_ledger():
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=2, lexical=True)
    ledger._lex._members[0] = {"hello", "hey", "hi"}
    ledger._lex._epochs[0] = 1
    ledger._lex_epochs = ledger._lex.epoch_vector()
    ledger._refresh_active()
    ledger._tables.setdefault("external_user", {})["L0>L0"] = {
        "ctx": {"0": [90, 10], "1": [5, 95]}, "null": {}, "marg": [95, 105]
    }
    return ledger


def test_earned_kernel_uses_epoch_identity_and_not_training_examples():
    ledger = _prepared_lexical_ledger()
    kernel = ledger.recognition_kernel("external_user", "L0>L0")
    assert kernel["identity_path"] == "L0@1>L0@1"
    assert kernel["path"] == "L0>L0"
    assert set(kernel["lexical"]["L0"]["members"]) == {"hello", "hey", "hi"}
    assert set(kernel) >= {"id", "path", "identity_path", "ctx", "marg", "lexical"}
    # No event text, episode IDs, or example list is copied into permanence.
    assert "examples" not in kernel and "events" not in kernel and "history" not in kernel


def test_slot_reuse_gets_a_new_identity_and_cannot_inherit_old_tables():
    ledger = _prepared_lexical_ledger()
    old = ledger._lex.epoch_vector()
    assert ledger.representation_identity("L0>L0") == "L0@1>L0@1"
    ledger._lex._members[0] = {"alpha", "beta", "gamma"}
    ledger._lex._epochs[0] += 1
    new = ledger._lex.epoch_vector()
    ledger._retire_reused_lexical_slots(old, new)
    assert ledger.representation_identity("L0>L0") == "L0@2>L0@2"
    assert "L0>L0" not in ledger._tables.get("external_user", {})


def test_dormant_kernel_can_recognize_without_live_lexical_slot():
    ledger = _prepared_lexical_ledger()
    exchange = AuroraRepresentationExchange(ledger, state_dir=tempfile.mkdtemp(), persist=False)
    kernel = ledger.recognition_kernel("external_user", "L0>L0")
    rep = {
        "id": "REPR:external_user:L0@1>L0@1", "subject": "external_user", "path": "L0>L0",
        "identity_path": "L0@1>L0@1", "target": "L0", "length": 2, "resolution": "REC_SHALLOW",
        "offered": 0, "accepted": 0, "first_seen": 0.0, "universal": {
            "n": 500.0, "gain": 250.0, "hits": 450.0, "blk_n": 0.0, "blk_sum": 0.0,
            "nb": 5.0, "bsum": 2.5, "bsq": 1.25,
        }, "domain": {}, "kernel": kernel, "words": {"hi": {}, "lo": {}}, "word_n": {"hi": 0, "lo": 0},
    }
    exchange._reps[rep["id"]] = rep
    # The developmental handle vanishes; the crystal recognizer remains.
    ledger._lex._members[0] = set()
    exchange._history["live"] = deque([{"bits": (0,) * 14, "tokens": ["hey"]}], maxlen=5)
    exp = exchange._kernel_expectation(rep, "live")
    assert exp and exp["dormant_reactivation"] is True and exp["target"] == "L0"


def test_kernel_round_trips_inside_representation_crystal():
    ledger = _prepared_lexical_ledger()
    kernel = ledger.recognition_kernel("external_user", "L0>L0")
    registry = ConceptCrystalRegistry()
    store = RepresentationCrystals(registry)
    record = {
        "v": 2, "id": "REPR:external_user:L0@1>L0@1", "subject": "external_user",
        "path": "L0>L0", "identity_path": "L0@1>L0@1", "target": "L0", "kernel": kernel,
        "uni": {"n": 500.0, "hits": 450.0, "gain": 250.0}, "lexc": {"L0": ledger.lexical_coordinate("L0")},
    }
    assert store.upsert(record, delta={"n": 0.0, "hits": 0.0, "gain": 0.0})
    restored = store.load_all()
    match = next(r for r in restored if r.get("id") == record["id"])
    assert match["kernel"]["identity_path"] == "L0@1>L0@1"
    assert set(match["kernel"]["lexical"]["L0"]["members"]) == {"hello", "hey", "hi"}
