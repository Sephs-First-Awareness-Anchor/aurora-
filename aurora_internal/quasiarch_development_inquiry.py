# Authors: Sunni (Sir) Morningstar & Cael Devo
"""QuasiArch diagnostics over developmental evidence (directive VIII, Stage F): investigative, never authoritative.

Answers the six questions the directive names, from what the genealogy actually recorded, and says what it cannot tell:

    1. dream_ancestry        which experiences supplied a dream's ancestral material
    2. new_relationships     what relationships emerged during the dream
    3. consequential_changes which changes were measurably consequential
    4. validation            which capabilities have internal validation, which have external validation
    5. uncertain             which conclusions remain hypothetical or uncertain

Rules this module keeps:
  * read-only -- it calls only the genealogy's read accessors and changes nothing (tests compare the whole state before and after);
  * no manufactured ancestry -- a dream's ancestral material is the union of what its representations carry; which ancestor
    supplied which combination is stated as not attributed, never guessed; a representation with no recorded ancestry is
    reported unattributed;
  * every answer carries `basis` (what it rests on), `unknown` (what could not be determined and why) and `authoritative: False`;
  * nothing here is fed back into cognition, speech or pressure: the answer goes to whoever asked.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

AXES = ("X", "T", "N", "B", "A")
_CAP = 50


def _reply(question: str, basis: List[str], unknown: List[str], **body: Any) -> Dict[str, Any]:
    return {"question": question, "authoritative": False, "basis": basis, "unknown": unknown, **body}


def _net(relief: Optional[Dict[str, float]]) -> float:
    return sum(float((relief or {}).get(a, 0.0) or 0.0) for a in AXES)


def resolve_episode(g: Any, episode: str) -> Dict[str, Any]:
    """An episode may be named by the input id or by its own name (a dream's lineage id, a turn id).  Nothing is guessed: an
    unknown name, or a name that matches more than one retained input, is reported as such."""
    ep = str(episode)
    ident = g.input_identity(ep)
    if ident is not None:
        return {"input": ep, "identity": ident, "how": "input id"}
    ids = g.find_inputs(ep)
    if len(ids) == 1:
        return {"input": ids[0], "identity": g.input_identity(ids[0]), "how": "episode name"}
    if len(ids) > 1:
        return {"input": None, "identity": None, "how": "ambiguous", "candidates": ids[:10]}
    credited = g.reps_credited_under(ep)["reps"] or g.pairs_credited_under(ep)["pairs"]
    if credited:
        return {"input": ep, "identity": None, "how": "input id (what it was is no longer retained)"}
    return {"input": None, "identity": None, "how": "not recorded"}


def _lived_ancestors(g: Any, lived_ids: Iterable[str]) -> List[Dict[str, Any]]:
    out = []
    for i in lived_ids:
        ident = g.input_identity(i)
        out.append({"input": i, "occurrence": (ident or {}).get("occurrence", "unknown"),
                    "name": (ident or {}).get("turn_id", "not retained")})
    return out


def dream_ancestry(g: Any, episode: str) -> Dict[str, Any]:
    q = "Which experiences supplied this dream's ancestral material?"
    res = resolve_episode(g, episode)
    if res["input"] is None:
        return _reply(q, [], [f"the episode is {res['how']}"], found=False, resolution=res)
    credited = g.reps_credited_under(res["input"])
    reps = sorted(credited["reps"])
    anc = g.ancestry_of(reps)
    if not reps:
        anc = dict(anc, status="unknown")                                          # nothing is listed for it; not "traced" or "none"
    per_rep = {r: {"kinds": credited["reps"][r], "ancestry": g.representation_evidence(r)["ancestry"],
                   "lived_ancestors": _lived_ancestors(g, g.representation_evidence(r)["lived_inputs"])} for r in reps[:_CAP]}
    unknown = ["which ancestor supplied which combination: a novel combination can arise from several representations whose "
               "interactions are not attributed (and are not assigned a one-to-one counterpart)"]
    if anc["unattributed"]:
        unknown.append(f"{len(anc['unattributed'])} representation(s) carry no recorded experiential ancestry (legacy or never "
                       f"credited by a lived input): {anc['unattributed'][:10]}")
    if credited["capped_rows"]:
        unknown.append(f"{credited['capped_rows']} ledger row(s) keep only their most recent inputs, so material they supplied "
                       "to this episode long ago may not be listed")
    if not reps:
        unknown.append("no representation's ledger lists this episode, so its ancestral material is not known")
    if res["identity"] is None:
        unknown.append("what the episode itself was is no longer retained")
    return _reply(q, ["representation ledger (per kind of occurrence)", "lived ancestors, most recent 8 per representation"], unknown,
                  found=True, resolution=res, status=anc["status"], representations=per_rep,
                  lived_ancestors=_lived_ancestors(g, anc["lived_inputs"][:_CAP]), unattributed=anc["unattributed"][:_CAP])


def new_relationships(g: Any, episode: str) -> Dict[str, Any]:
    q = "What new relationships emerged during this dream?"
    res = resolve_episode(g, episode)
    if res["input"] is None:
        return _reply(q, [], [f"the episode is {res['how']}"], found=False, resolution=res)
    credited = g.pairs_credited_under(res["input"])
    rows = []
    for (left, right), kinds in sorted(credited["pairs"].items())[:_CAP]:
        ev = g.pair_evidence(left, right)
        by = ev.get("by_kind", {}) if ev.get("ledger") == "recorded" else {}
        link_id = g._links_by_parents.get((left, right))
        link = g.links.get(link_id) if link_id else None
        rows.append({"pair": [left, right], "kinds": kinds,
                     "only_ever_dreamed_or_simulated": bool(by) and set(by) == {"hypothetical"},
                     "also_lived": "lived" in by, "promoted": bool(link),
                     "link_qualification": (link.evidence_qualification if link is not None else None),
                     "distinct_inputs_by_kind": {k: v.get("n_inputs") for k, v in by.items()}})
    unknown = ["whether a relationship that appears only in dreams would hold outside them: that needs an external test"]
    if credited["capped_rows"]:
        unknown.append(f"{credited['capped_rows']} pair row(s) keep only their most recent inputs")
    return _reply(q, ["pair ledger (per kind of occurrence)", "minted links' evidence qualification"], unknown,
                  found=True, resolution=res, relationships=rows)


def consequential_changes(g: Any, episode: str) -> Dict[str, Any]:
    q = "Which changes from this episode were genuinely consequential?"
    res = resolve_episode(g, episode)
    if res["input"] is None:
        return _reply(q, [], [f"the episode is {res['how']}"], found=False, resolution=res)
    rows = g.input_effects(res["input"])
    unknown: List[str] = []
    if not rows:
        unknown.append("this episode's own effect per representation is not held (the shadow is in memory and is not kept across "
                       "restarts); only totals over every dream/simulation input are held, which cannot be split out")
    changes = []
    for r in rows[:_CAP]:
        net = _net(r["relief"])
        changes.append({"representation": r["target"], "ticks": r["n"], "net_relief": round(net, 9),
                        "effect": "relieved pressure" if net > 0 else "loaded pressure" if net < 0 else "none measured",
                        "relief_by_axis": {a: round(float(r["relief"].get(a, 0.0)), 9) for a in AXES}})
    return _reply(q, ["per-input effect shadow (measured relief from the observation, not a judgement)"], unknown,
                  found=True, resolution=res, changes=changes,
                  consequential=[c["representation"] for c in changes if c["effect"] != "none measured"])


def validation(g: Any, rep_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    q = "Which capabilities have internal validation, and which have external validation?"
    ids = list(dict.fromkeys(str(r) for r in (rep_ids if rep_ids is not None else g._rep_ledger)))
    groups: Dict[str, List[str]] = {"internal_only": [], "external_supported": [], "external_contradicted": [],
                                    "external_mixed": [], "lived_not_externally_demonstrated": [], "none": []}
    internal: Dict[str, str] = {}
    for r in ids:
        ev = g.representation_evidence(r)
        app = ev["applicability"]
        by = ev["by_kind"]
        if app == "none" and "lived" in by:
            app = "lived_not_externally_demonstrated"
        groups.setdefault(app, []).append(r)
        hyp = by.get("hypothetical")
        if hyp and hyp["ticks"]:
            net = _net(hyp["relief"])
            internal[r] = "supported" if net > 0 else "contradicted" if net < 0 else "no measured effect"
    return _reply(q, ["representation ledger: kinds of occurrence and external ticks"],
                  ["external validation means an input she tested, acted on or perceived; hearing something is not that, and live "
                   "inputs are currently heard, so few or no capabilities can have external validation yet"] if not groups["external_supported"] else [],
                  counts={k: len(v) for k, v in groups.items()}, groups={k: v[:_CAP] for k, v in groups.items()},
                  internal_validation={r: internal[r] for r in list(internal)[:_CAP]}, n_examined=len(ids))


def uncertain(g: Any) -> Dict[str, Any]:
    q = "Which conclusions remain hypothetical or uncertain?"
    legacy = [r for r, a in g.abilities.items() if a.consequence_profile and r not in g._rep_ledger]
    capped = sum(1 for row in g._rep_ledger.values() for v in row["by"].values() if v["n_inputs"] > len(v["inputs"]))
    links = list(g.links.values())
    unqualified = [l.id for l in links if getattr(l, "evidence_qualification", None) is None]
    internal_links = [l.id for l in links if (getattr(l, "evidence_qualification", None) or {}).get("internal_only")]
    ev = {r: g.representation_evidence(r)["applicability"] for r in g._rep_ledger}
    items = {
        "capabilities_with_no_recorded_ancestry": {"n": len(legacy), "examples": legacy[:10]},
        "ledger_rows_keeping_only_recent_inputs": capped,
        "links_with_no_evidence_qualification": {"n": len(unqualified), "examples": unqualified[:10]},
        "links_resting_only_on_dreams_or_simulations": {"n": len(internal_links), "examples": internal_links[:10]},
        "capabilities_hypothetical_only": [r for r, a in ev.items() if a == "internal_only"][:_CAP],
        "capabilities_contradicted_or_mixed_externally": [r for r, a in ev.items() if a in ("external_contradicted", "external_mixed")][:_CAP],
        "evidence_not_yet_consolidated_from_the_surface": [x for x in g._applied.open_gaps()],
        "replays_not_counted_as_new_evidence": int(g._replays_skipped),
    }
    return _reply(q, ["genealogy's own ledgers and the journal's applied record"],
                  ["anything not listed here is not known to be certain, only not known to be uncertain"], items=items)


QUESTIONS = {"dream_ancestry": dream_ancestry, "new_relationships": new_relationships,
             "consequential_changes": consequential_changes, "validation": validation, "uncertain": uncertain}


def inquire(g: Any, question: str, **kw: Any) -> Dict[str, Any]:
    fn = QUESTIONS.get(str(question))
    if fn is None:
        return _reply(str(question), [], [f"unknown question; the ones answered are {sorted(QUESTIONS)}"], found=False)
    return fn(g, **kw)
