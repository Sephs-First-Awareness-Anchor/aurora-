# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The concept web: search, lookup and neighbourhood over the one crystal store; the read-only server."""
import ast
import json
import threading
import urllib.error
import urllib.request

import pytest

from aurora_internal import crystal_web as W
from aurora_internal import crystal_web_server as S


def cr(cid, concept, level=1, conns=None, facets=None, usage=0, **extra):
    d = {"crystal_id": cid, "concept": concept, "level": level, "facets": facets or {}, "connections": conns or {}, "usage_count": usage}
    d.update(extra)
    return d


def store():
    return {
        "a": cr("a", "apple", 2, {"b": 0.9, "c": 0.3}, usage=5, facets={"f1": {"role": "fk:relation", "confidence": 0.8, "content": {"entries": [{"key": "is_a|fruit", "content": {"type": "is_a"}, "degree": 0.8, "contexts": 3}]}},
                                                                          "f2": {"role": "provenance:learned:apple", "confidence": 0.1, "content": {"source": "learned"}}}),
        "b": cr("b", "fruit", 3, {"a": 0.5}, usage=9),
        "c": cr("c", "pear", 1),
        "d": cr("d", "learned:pear", 1),
        "e": cr("e", "island", 1),
    }


def test_search_ranks_exact_then_word_then_prefix_then_contains_and_is_deterministic():
    w = W.ConceptWeb(store())
    names = [r["concept"] for r in w.search("pear")]
    assert names[0] == "pear" and "learned:pear" in names
    assert [r["match"] for r in w.search("pear")][0] == "exact"
    assert [r["concept"] for r in w.search("is")] == ["island"]                  # prefix beats contains
    assert w.search("") == [] and w.search("zzz") == []
    assert w.search("pear") == w.search("pear")


def test_a_labelled_name_resolves_to_its_word():
    w = W.ConceptWeb(store())
    assert w.resolve("learned:apple") == "a" and w.resolve("APPLE") == "a" and w.resolve("nothing") is None


def test_ties_are_as_strong_as_the_stronger_side_and_work_both_ways():
    w = W.ConceptWeb(store())
    card = w.lookup("apple")
    assert [(t["concept"], t["strength"]) for t in card["ties"]] == [("fruit", 0.9), ("pear", 0.3)]
    assert w.lookup("pear")["ties"][0]["concept"] == "apple" and w.lookup("fruit")["ties"][0]["strength"] == 0.9


def test_lookup_groups_what_a_crystal_holds():
    card = W.ConceptWeb(store()).lookup("apple")
    assert card["level_name"] == "COMPOSITE" and card["usage"] == 5
    assert card["evidence"][0]["kind"] == "relation" and card["evidence"][0]["degree"] == 0.8
    assert "provenance" in card["facets"] and "evidence" not in card["facets"]


def test_neighborhood_is_bounded_and_carries_the_ties_among_its_nodes():
    w = W.ConceptWeb(store())
    g = w.neighborhood("apple", depth=1)
    assert {n["concept"] for n in g["nodes"]} == {"apple", "fruit", "pear"} and len(g["edges"]) == 2
    assert w.neighborhood("apple", depth=1, max_nodes=2)["truncated"] and len(w.neighborhood("apple", max_nodes=2)["nodes"]) == 2
    assert w.neighborhood("nothing") is None


def test_it_never_writes_and_imports_nothing_of_the_stack():
    allowed = {"aurora_internal.crystal_web", "aurora_internal.crystal_store", "aurora_internal.crystal_web_page", "aurora_internal.crystal_maturity"}
    for mod in (W, S):
        src = open(mod.__file__).read()
        mods = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module)
            elif isinstance(n, ast.Import):
                mods.update(a.name for a in n.names)
        assert {m for m in mods if m.startswith("aurora")} <= allowed
        opens = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "open"]
        assert all(len(c.args) > 1 and getattr(c.args[1], "value", None) == "r" for c in opens)                 # every open() is explicitly a read
        assert not any(w in src for w in ("write_text", "os.remove", "os.rename", "atomic_write", ".write_bytes"))


def serve(tmp_path, token=""):
    (tmp_path / "dps_crystals.json").write_text(json.dumps({"crystals": store()}))
    srv = S.serve(str(tmp_path), "127.0.0.1", 0, token)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def get(port, path):
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}{path}").read())


def test_the_server_answers_reads_and_refuses_everything_else(tmp_path):
    srv, port = serve(tmp_path)
    try:
        assert get(port, "/api/search?q=apple")["results"][0]["concept"] == "apple"
        assert get(port, "/api/concept?name=apple")["tie_count"] == 2 and len(get(port, "/api/web?name=apple")["nodes"]) == 3
        assert get(port, "/api/overview")["crystals"] == 5
        with pytest.raises(urllib.error.HTTPError) as e:
            get(port, "/api/concept?name=zzz")
        assert e.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/search", method="POST"))
        assert e.value.code == 405
    finally:
        srv.shutdown()


def test_it_reloads_when_the_store_changes(tmp_path):
    srv, port = serve(tmp_path)
    try:
        assert get(port, "/api/overview")["crystals"] == 5
        more = store()
        more["z"] = cr("z", "zebra")
        (tmp_path / "dps_crystals.json").write_text(json.dumps({"crystals": more}) + " ")
        assert get(port, "/api/overview")["crystals"] == 6
    finally:
        srv.shutdown()


def test_beyond_loopback_needs_a_token_and_every_request_carries_it(tmp_path):
    with pytest.raises(SystemExit):
        S.serve(str(tmp_path), "0.0.0.0", 0, "")
    srv, port = serve(tmp_path, token="s3cret")
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            get(port, "/api/overview")
        assert e.value.code == 403
        assert get(port, "/api/overview?t=s3cret")["crystals"] == 5
    finally:
        srv.shutdown()
