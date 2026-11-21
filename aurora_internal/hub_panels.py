# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Read-only panels for the desktop subsurface hub (Sir, 2026-11-15): the resolution ledger, the strata link, the crystal pass.

Each reads what Aurora already keeps on disk and nothing else: it imports nothing of her stack, writes nothing, and never creates a directory.  The strata panel
shows named, non-secret fields only: the link's secret, pairing key and per-surface keys are never read into a panel.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Mapping, Optional

LINK_DIR = "strata_link"
STACK_PIDS = ("surface", "subsurface", "hub", "room")
STR_FIELDS = 200


def _read(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _num(v: Any, d: int = 4) -> Optional[float]:
    try:
        f = float(v)
        return round(f, d) if f == f and abs(f) != float("inf") else None
    except (TypeError, ValueError):
        return None


# -- the resolution ledger ----------------------------------------------------------------------------------------------------------------------------

def ledger_panel(crystals: Mapping[str, Mapping[str, Any]], top: int = 40) -> Dict[str, Any]:
    """The ledger keeps its research ON the crystals (`hyp:res:<subject>:<path>` facets, `hyp:cal:ledger` calibration, `hyp:lex:structure` word classes)."""
    calibration: Dict[str, Any] = {}
    hyps: List[Dict[str, Any]] = []
    lex: Dict[str, Any] = {}
    for c in crystals.values():
        for f in (c.get("facets") or {}).values():
            role = str(f.get("role", ""))
            if not role.startswith("hyp:"):
                continue
            rec = f.get("content")
            try:
                rec = json.loads(rec) if isinstance(rec, str) else rec
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            if role == "hyp:cal:ledger":
                calibration = rec
            elif role == "hyp:lex:structure":
                lex = rec
            elif rec.get("path"):
                st = rec.get("st") or {}
                n = float(st.get("n") or 0.0)
                hyps.append({"subject": str(rec.get("subject", "")), "path": str(rec.get("path", ""))[:STR_FIELDS], "crystal": str(c.get("concept", ""))[:80],
                             "observations": n, "gain_per_obs": _num(float(st.get("gain") or 0.0) / n) if n else None,
                             "null_per_obs": _num(float(st.get("null") or 0.0) / n) if n else None, "blocks": float(st.get("nb") or 0.0)})
    hyps.sort(key=lambda h: (-h["observations"], h["subject"], h["path"]))
    n_obs = {str(k): int(v) for k, v in dict(calibration.get("n_obs") or {}).items()}
    return {"present": bool(calibration or hyps), "subjects": dict(sorted(n_obs.items(), key=lambda kv: (-kv[1], kv[0]))[:30]),
            "demands_submitted": int(calibration.get("emitted") or 0), "demands_unsubmitted": int(calibration.get("unsubmitted") or 0),
            "last_emission": calibration.get("last_emission") or {}, "streams": {str(n): int((s or {}).get("next_index") or 0) for n, s in dict(calibration.get("streams") or {}).items()},
            "hypotheses": len(hyps), "under_test": hyps[: max(1, int(top))], "lexical_structure_keys": sorted(map(str, lex))[:20]}


# -- the strata link ---------------------------------------------------------------------------------------------------------------------------------

def _alive(pid_file: str) -> Optional[bool]:
    try:
        with open(pid_file, "r", encoding="utf-8") as fh:
            pid = int(fh.read().strip().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None


def _outbox(path: str) -> Optional[Dict[str, int]]:
    d = _read(path)
    if not isinstance(d, dict):
        return None
    return {"pending": len([r for r in (d.get("records") or []) if isinstance(r, dict)]), "next_seq": int(d.get("next_seq") or 1), "overflow_dropped": int(d.get("overflow_dropped") or 0)}


def strata_panel(state_dir: str, now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else float(now)
    link = os.path.join(str(state_dir), LINK_DIR)
    srv = _read(os.path.join(link, "server_state.json"))
    cli = _read(os.path.join(link, "client_state.json"))
    seeded = _read(os.path.join(link, "seeded.json"))
    last_seen = {str(k): _num(v, 1) for k, v in dict((srv or {}).get("last_seen") or {}).items()}
    out: Dict[str, Any] = {
        "configured": os.path.isdir(link),
        "server": None if not isinstance(srv, dict) else {
            "epoch": int(srv.get("epoch") or 0), "owner": str(srv.get("owner") or ""), "applied": {str(k): int(v or 0) for k, v in dict(srv.get("applied") or {}).items()},
            "last_seen_seconds_ago": {k: (round(now - v, 1) if v else None) for k, v in last_seen.items()},
            "handoff_pending": bool(srv.get("handoff")), "migrations": len(srv.get("migrations") or []),
            "last_migration": (srv.get("migrations") or [None])[-1] if srv.get("migrations") else None},
        "client": None if not isinstance(cli, dict) else {"down_applied": int(cli.get("down_applied") or 0), "has_link_key": bool(cli.get("link_key"))},        # the key itself is never read out
        "seeded": bool(seeded), "seeded_detail": ({k: seeded[k] for k in ("at", "from", "surface", "records") if k in seeded} if isinstance(seeded, dict) else None),
        "downlink_enabled": os.path.exists(os.path.join(link, "downlink_enabled")),
        "paired": os.path.exists(os.path.join(link, "secret.txt")),                      # whether, never what
        "down_outbox": _outbox(os.path.join(link, "down_outbox.json")), "up_outbox": _outbox(os.path.join(link, "up_outbox.json")),
        "processes": {n: _alive(os.path.join(str(state_dir), "strata_stack", "pids", f"{n}.pid")) for n in STACK_PIDS}}
    out.update(_strata_extras(link, srv if isinstance(srv, dict) else {}, now))
    snap = _read(os.path.join(str(state_dir), "dual_strata_snapshot.json"))
    if isinstance(snap, dict):
        cf = snap.get("conscious_frame") or {}
        out["frame"] = {"saved_seconds_ago": (round(now - float(snap["saved_at"]), 1) if snap.get("saved_at") else None), "crest": (cf.get("conscious_crest") or {}).get("label"),
                        "action": cf.get("selected_action"), "mode": cf.get("processing_mode"), "readiness": _num(cf.get("readiness")), "coherence": _num(cf.get("coherence"))}
    return out


def _text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()[:STR_FIELDS]
    except OSError:
        return ""


def _strata_extras(link: str, srv: Mapping[str, Any], now: float) -> Dict[str, Any]:
    """Who holds her, the devices home knows, a move under way, each phone's
    first pairing, home's inquiry desk, and the gate on a surface.  Names,
    stages and counts only."""
    names = {str(k): str(v)[:64] for k, v in dict(srv.get("names") or {}).items()}
    home_id = _text(os.path.join(link, "home_surface_id.txt"))
    owner = str(srv.get("owner") or "")
    seen = dict(srv.get("last_seen") or {})
    devices = sorted({*names, *map(str, seen)} | ({home_id} if home_id else set()))
    move = srv.get("move") if isinstance(srv.get("move"), dict) else None
    desk = _read(os.path.join(link, "inquiry_desk.json"))
    questions = dict((desk or {}).get("questions") or {}) if isinstance(desk, dict) else {}
    gate = _read(os.path.join(link, "store_gate.json"))
    growth = _read(os.path.join(link, "growth", "last_install.json"))
    return {
        "holder": {"surface_id": owner, "name": names.get(owner) or ("this desktop" if owner and owner == home_id else owner),
                   "is_this_desktop": bool(owner and owner == home_id)},
        "devices": [{"surface_id": d, "name": names.get(d) or ("this desktop" if d == home_id else d), "holds_her": d == owner,
                     "this_desktop": d == home_id,
                     "seen_seconds_ago": (round(now - float(seen[d]), 1) if seen.get(d) else None)} for d in devices],
        "move": None if not move else {k: move.get(k) for k in ("from", "to", "stage", "requested_by", "at")}
                | {"from_name": names.get(str(move.get("from"))) or move.get("from"), "to_name": names.get(str(move.get("to"))) or move.get("to")},
        "recent_moves": [{k: m.get(k) for k in ("to", "outcome", "requested_by", "ended_at", "at")} | {"to_name": names.get(str(m.get("to"))) or m.get("to")}
                         for m in (srv.get("moves") or [])[-5:] if isinstance(m, dict)],
        "first_pairing": {names.get(str(k)) or str(k): {f: v.get(f) for f in ("status", "at", "tail_open")} for k, v in dict(srv.get("first_pairing") or {}).items() if isinstance(v, dict)},
        "shared_inquiry": {"questions": len(questions), "handed_down": sum(1 for q in questions.values() if isinstance(q, dict) and q.get("handed_down"))},
        "store_gate": None if not isinstance(gate, dict) else {k: gate.get(k) for k in ("at", "surface_only", "stores_declined", "writes_declined", "stores_provisional", "writes_provisional", "provisional")},
        "last_growth_install": growth if isinstance(growth, dict) else None,
        "listening": ({k: listen.get(k) for k in ("host", "port", "reachable_from_network")} if isinstance(listen := _read(os.path.join(link, "listen.json")), dict) else None),
    }


# -- the crystal pass -------------------------------------------------------------------------------------------------------------------------------

def pass_panel(state_dir: str) -> Dict[str, Any]:
    d = _read(os.path.join(str(state_dir), "crystal_pass_report.json"))
    if not isinstance(d, dict):
        return {"present": False}
    rep = d.get("report") if isinstance(d.get("report"), dict) else {}
    return {"present": True, "at": d.get("at"), "report": {k: v for k, v in rep.items() if isinstance(v, (int, float, str, bool, dict)) and k != "error"} | ({"error": str(rep["error"])[:300]} if "error" in rep else {}),
            "history": [h for h in (d.get("history") or []) if isinstance(h, dict)][-24:]}
