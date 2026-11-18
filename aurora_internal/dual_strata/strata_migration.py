#!/usr/bin/env python3
"""
strata_migration.py -- the first pairing of a phone that has lived as a whole
mind (surface restructure 3d, Sir's tightening 1).

Until a phone is paired it runs every organ on its own copy, so it may hold
memories home never lived.  Pairing must not throw that away, and nothing may
merge two histories by overwriting one.  So the first pairing is its own
procedure, and every step can be undone until the last one:

  1. The phone snapshots its state and keeps running on the full profile.
  2. The snapshot goes to a staging area at home (offer, chunk, commit under
     the purpose "migrate"), every file verified against its hash.  Home's
     live state does not change.
  3. Home compares each store in the two copies by its class:
       history        append-only logs: merged as a union, keyed by each
                      record's own id or by its content hash.  Nothing from
                      either side is dropped.
       developmental  single-snapshot stores (the crystal store, lexicon,
                      memory, grounding, ledgers): never merged byte for byte
                      and never overwritten automatically.  The report says
                      which side has lived more; Sir picks, store by store.
                      The other side's copy is archived at home, labelled.
       present        her present frame and habitat: the phone's.
       cache          indexes, locks, temporary files: not moved.
  4. With every choice made, the merge is built in a copy, verified against
     its manifest and installed cold (before the resident boots), with a
     backup of everything it replaces.
  5. Home writes a receipt: what moved, what merged, what Sir chose, where the
     archive is, and the digest of what was installed.
  6. The phone checks the receipt against its own snapshot.  Only then does it
     go surface-only (aurora_store_ownership).  Its pre-migration copy stays
     on the phone, untouched, until Sir clears it.  If any step fails, the
     phone stays a whole mind and home is unchanged.

What the phone lived after its snapshot, while it waited, is not lost: its
continuity stays in the outbox and home integrates it, once, after the
receipt (strata_link's first-pairing tail).

Nothing here decides what she learns or which side is "right": the report
measures, Sir chooses.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from aurora_internal.aurora_store_ownership import (
    CACHE,
    JOURNAL,
    SURFACE_PRESENT,
    MOVES_WITH_HER,
    classify,
)

RECEIPT_FILENAME = "migration_receipt.json"
PENDING_FILENAME = "pending.json"
MIGRATION_DIRNAME = "migration"

HISTORY = "history"
DEVELOPMENTAL = "developmental"
PRESENT = "present"
SKIP = "cache"

PHONE = "phone"
HOME = "home"

# Append-only records of what happened: union-merged.  Named here, in one
# place; anything else that is line-per-record JSON is treated the same.
_HISTORY_NAMES = ("developmental_timeline.jsonl", "study_log.jsonl", "pressure_experiences.jsonl",
                  "habitat_events.jsonl", "entity_lineage.jsonl")
_RECORD_ID_KEYS = ("id", "event_id", "record_id", "turn_id", "uid", "packet_id")
_TIME_KEYS = ("at", "ts", "timestamp", "time", "created_at")


def _link_dir(state_dir: Any) -> Path:
    from aurora_internal.dual_strata.strata_link import link_dir
    return link_dir(state_dir)


def migration_root(state_dir: Any) -> Path:
    root = _link_dir(state_dir) / MIGRATION_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    os.replace(str(tmp), str(path))


# ---------------------------------------------------------------------------
# Classes and measurements
# ---------------------------------------------------------------------------

def migration_class(rel_path: str) -> str:
    rel = str(rel_path).replace(os.sep, "/")
    owner = classify(rel)
    if owner == CACHE:
        return SKIP
    import fnmatch
    if any(fnmatch.fnmatchcase(rel, p) for p in MOVES_WITH_HER):
        return PRESENT
    if owner == SURFACE_PRESENT:
        return SKIP          # this device's own traces; each side keeps its own
    name = rel.rsplit("/", 1)[-1]
    if owner == JOURNAL or name in _HISTORY_NAMES or name.endswith(".jsonl"):
        return HISTORY
    return DEVELOPMENTAL


def _jsonl_records(path: Path) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return [line.rstrip("\n") for line in handle if line.strip()]
    except (OSError, UnicodeDecodeError):
        return []


def _record_count(path: Path) -> int:
    """How much has been lived into a store, by its own records."""
    if not path.is_file():
        return 0
    if path.name.endswith(".jsonl"):
        return len(_jsonl_records(path))
    data = _read(path, None)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("entries", "nodes", "records", "crystals", "items", "motifs"):
            if isinstance(data.get(key), (dict, list)):
                return len(data[key])
        return len(data)
    return 0


def _measure(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    from aurora_internal.dual_strata.strata_state_transfer import file_sha256
    stat = path.stat()
    return {"exists": True, "size": stat.st_size, "records": _record_count(path),
            "changed_at": stat.st_mtime, "sha256": file_sha256(path)}


def _suggest(phone: Mapping[str, Any], home: Mapping[str, Any]) -> str:
    """Which side has lived more, by records, then size.  A suggestion for
    Sir to read; never applied without his word."""
    if not home.get("exists"):
        return PHONE
    if not phone.get("exists"):
        return HOME
    if int(phone.get("records", 0)) != int(home.get("records", 0)):
        return PHONE if int(phone["records"]) > int(home["records"]) else HOME
    return PHONE if int(phone.get("size", 0)) >= int(home.get("size", 0)) else HOME


def divergence_report(home_dir: Any, phone_files: Any, manifest: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Each store the phone sent, measured against home's copy."""
    home_root, phone_root = Path(str(home_dir)), Path(str(phone_files))
    stores: Dict[str, Dict[str, Any]] = {}
    counts = {HISTORY: 0, DEVELOPMENTAL: 0, PRESENT: 0, SKIP: 0, "identical": 0}
    for row in manifest:
        rel = str(row["path"])
        cls = migration_class(rel)
        home = _measure(home_root / rel)
        if home.get("sha256") == row["sha256"]:
            counts["identical"] += 1
            continue
        counts[cls] += 1
        if cls == SKIP:
            continue
        phone = _measure(phone_root / rel)
        entry: Dict[str, Any] = {"class": cls, "phone": phone, "home": home}
        if cls == DEVELOPMENTAL:
            entry["suggested"] = _suggest(phone, home)
            entry["needs_choice"] = bool(home.get("exists"))
        stores[rel] = entry
    return {"stores": stores, "counts": counts,
            "choices_needed": sorted(k for k, v in stores.items() if v.get("needs_choice"))}


# ---------------------------------------------------------------------------
# Home: staging, choices, cold apply
# ---------------------------------------------------------------------------

def stage_received(state_dir: Any, transfer_root: Path, migration_id: str, *,
                   meta: Mapping[str, Any], manifest: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A verified migrate transfer has fully arrived: keep it in the migration
    area and write the divergence report.  Home's live state is untouched."""
    root = migration_root(state_dir) / migration_id
    if root.exists():
        shutil.rmtree(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    os.replace(str(transfer_root), str(root))
    report = divergence_report(state_dir, root / "files", manifest)
    pending = {"migration_id": migration_id, "from": meta.get("from"), "at": time.time(),
               "source_digest": meta.get("digest"), "lived_seq": int(meta.get("lived_seq", 0) or 0),
               "status": "awaiting_choice" if report["choices_needed"] else "ready",
               "choices": {}, "report": report}
    _write(migration_root(state_dir) / PENDING_FILENAME, pending)
    return {"migration_id": migration_id, "status": pending["status"],
            "choices_needed": len(report["choices_needed"]), "counts": report["counts"]}


def load_pending(state_dir: Any) -> Optional[Dict[str, Any]]:
    pending = _read(migration_root(state_dir) / PENDING_FILENAME, None)
    return pending if isinstance(pending, dict) else None


def choose(state_dir: Any, choices: Mapping[str, str], *, accept_suggested: bool = False) -> Dict[str, Any]:
    """Record Sir's choice for each developmental store (phone or home)."""
    pending = load_pending(state_dir)
    if not pending or pending.get("status") not in ("awaiting_choice", "ready"):
        return {"ok": False, "error": "no_migration_waiting"}
    stores = pending["report"]["stores"]
    chosen = dict(pending.get("choices") or {})
    for rel, side in dict(choices).items():
        if rel not in stores or stores[rel].get("class") != DEVELOPMENTAL:
            return {"ok": False, "error": f"not a store that needs a choice: {rel}"}
        if side not in (PHONE, HOME):
            return {"ok": False, "error": f"side must be phone or home: {rel}"}
        chosen[rel] = side
    if accept_suggested:
        for rel in pending["report"]["choices_needed"]:
            chosen.setdefault(rel, stores[rel]["suggested"])
    pending["choices"] = chosen
    missing = [r for r in pending["report"]["choices_needed"] if r not in chosen]
    pending["status"] = "awaiting_choice" if missing else "ready"
    _write(migration_root(state_dir) / PENDING_FILENAME, pending)
    return {"ok": True, "status": pending["status"], "missing": missing}


def _record_key(line: str) -> str:
    try:
        rec = json.loads(line)
    except ValueError:
        rec = None
    if isinstance(rec, dict):
        for key in _RECORD_ID_KEYS:
            if rec.get(key) not in (None, ""):
                return f"{key}:{rec[key]}"
    return "sha:" + hashlib.sha256(line.encode("utf-8")).hexdigest()


def _record_time(line: str) -> float:
    try:
        rec = json.loads(line)
    except ValueError:
        return 0.0
    if isinstance(rec, dict):
        for key in _TIME_KEYS:
            try:
                return float(rec[key])
            except (KeyError, TypeError, ValueError):
                continue
    return 0.0


def union_history(home_path: Path, phone_path: Path, out_path: Path) -> Dict[str, int]:
    """Every record from both sides, once.  Home's order is kept; the phone's
    records home never had are placed by their own time where they carry one,
    otherwise after home's."""
    home_lines, phone_lines = _jsonl_records(home_path), _jsonl_records(phone_path)
    seen = {_record_key(line) for line in home_lines}
    extra = [line for line in phone_lines if _record_key(line) not in seen]
    merged = list(home_lines)
    if extra and all(_record_time(l) for l in home_lines + extra):
        merged = sorted(home_lines + extra, key=_record_time)
    else:
        merged.extend(extra)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        for line in merged:
            handle.write(line + "\n")
    return {"home": len(home_lines), "phone": len(phone_lines), "added_from_phone": len(extra)}


def apply_pending_migration(state_dir: Any) -> Optional[Dict[str, Any]]:
    """Install a migration whose choices are all made.  Call only cold:
    before the resident boots.  Returns the receipt, or None when nothing is
    ready.  A failure leaves home's live state as it was and says why."""
    from aurora_internal.dual_strata import strata_state_transfer as st
    pending = load_pending(state_dir)
    if not pending or pending.get("status") != "ready":
        return None
    home = Path(str(state_dir))
    mid = str(pending["migration_id"])
    area = migration_root(home) / mid
    phone_files = area / "files"
    merged = area / "merged"
    archive = area / "archive"
    shutil.rmtree(merged, ignore_errors=True)
    moved, unioned, chosen_rows = [], [], {}
    try:
        staged = st.IncomingTransfer(migration_root(home), mid)
        if staged.verify_all():
            raise st.TransferError("staged snapshot no longer matches its manifest")
        for rel, entry in pending["report"]["stores"].items():
            cls = entry["class"]
            src = phone_files / rel
            if cls == PRESENT:
                st.safe_join(merged, rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, merged / rel)
                moved.append(rel)
            elif cls == HISTORY:
                unioned.append({"path": rel, **union_history(home / rel, src, st.safe_join(merged, rel))})
            elif cls == DEVELOPMENTAL:
                if not entry.get("needs_choice"):
                    side = PHONE            # only the phone has lived it
                    moved.append(rel)
                else:
                    side = pending["choices"].get(rel)
                    if side not in (PHONE, HOME):
                        raise st.TransferError(f"no choice recorded for {rel}")
                    chosen_rows[rel] = side
                if side == PHONE:
                    st.safe_join(merged, rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, merged / rel)
                    if (home / rel).is_file():
                        keep = st.safe_join(archive / "home", rel)
                        keep.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(home / rel, keep)
                else:
                    keep = st.safe_join(archive / "phone", rel)
                    keep.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, keep)
        rel_paths = sorted(str(p.relative_to(merged).as_posix())
                           for p in merged.rglob("*") if p.is_file()) if merged.exists() else []
        manifest = st.build_manifest(merged, rel_paths)
        installed = st.install_verified(merged, manifest, home, area / "backup") if manifest else \
            {"installed": 0, "unchanged": 0, "backed_up": 0}
        after = st.build_manifest(home, rel_paths)
        if st.manifest_digest(after) != st.manifest_digest(manifest):
            raise st.TransferError("installed files do not match the merged manifest")
    except Exception as exc:
        pending["status"] = "failed"
        pending["error"] = f"{type(exc).__name__}: {exc}"[:300]
        _write(migration_root(home) / PENDING_FILENAME, pending)
        return {"ok": False, "migration_id": mid, "error": pending["error"]}
    receipt = {"ok": True, "verified": True, "migration_id": mid, "from": pending.get("from"),
               "source_digest": pending.get("source_digest"), "lived_seq": pending.get("lived_seq", 0),
               "applied_at": time.time(), "moved": moved, "merged": unioned, "chosen": chosen_rows,
               "archive": str(archive.relative_to(home).as_posix()),
               "installed_digest": st.manifest_digest(manifest), **installed}
    _write(_link_dir(home) / RECEIPT_FILENAME, receipt)
    pending["status"] = "applied"
    pending["receipt"] = receipt
    _write(migration_root(home) / PENDING_FILENAME, pending)
    shutil.rmtree(merged, ignore_errors=True)
    return receipt


def status_for(state_dir: Any, surface_id: str) -> Dict[str, Any]:
    """What the phone may know about its own migration: never another
    device's, never home's file contents."""
    pending = load_pending(state_dir)
    if not pending or pending.get("from") != surface_id:
        return {"status": "none"}
    out = {"migration_id": pending.get("migration_id"), "status": pending.get("status"),
           "choices_needed": len(pending.get("report", {}).get("choices_needed", [])),
           "choices_made": len(pending.get("choices") or {})}
    if pending.get("status") == "applied":
        out["receipt"] = pending.get("receipt")
    if pending.get("error"):
        out["error"] = pending["error"]
    return out


# ---------------------------------------------------------------------------
# Phone: the receipt that lets it become a surface
# ---------------------------------------------------------------------------

def load_receipt(state_dir: Any) -> Optional[Dict[str, Any]]:
    receipt = _read(_link_dir(state_dir) / RECEIPT_FILENAME, None)
    return receipt if isinstance(receipt, dict) else None


def accept_receipt(state_dir: Any, receipt: Mapping[str, Any], *, migration_id: str,
                   source_digest: str) -> Dict[str, Any]:
    """The phone checks home's receipt against the snapshot it sent.  Only a
    matching receipt is kept, and only a kept receipt makes it a surface."""
    if not receipt or not receipt.get("verified"):
        return {"ok": False, "error": "receipt_not_verified"}
    if receipt.get("migration_id") != migration_id or receipt.get("source_digest") != source_digest:
        return {"ok": False, "error": "receipt_does_not_match_this_snapshot"}
    kept = dict(receipt)
    kept["accepted_at"] = time.time()
    _write(_link_dir(state_dir) / RECEIPT_FILENAME, kept)
    return {"ok": True, "migration_id": migration_id}


def surface_only_ready(state_dir: Any) -> bool:
    """A paired phone whose first pairing was received and verified at home
    runs as a surface.  An unpaired phone, or one still migrating, stays the
    whole mind (it is then the only copy of her)."""
    from aurora_internal.dual_strata.strata_link import load_surface_config
    if load_surface_config(state_dir) is None:
        return False
    receipt = load_receipt(state_dir)
    return bool(receipt and receipt.get("verified") and receipt.get("accepted_at"))


# ---------------------------------------------------------------------------
# Command line (home): read the report, record choices, apply cold
# ---------------------------------------------------------------------------

def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="First pairing: move a whole-mind phone home.")
    parser.add_argument("command", choices=("report", "choose", "apply"))
    parser.add_argument("--state-dir", default=os.environ.get("AURORA_STATE_DIR", "aurora_state"))
    parser.add_argument("--side", action="append", default=[],
                        help="store=phone or store=home, once per store")
    parser.add_argument("--accept-suggested", action="store_true",
                        help="take the side that has lived more for every store not chosen")
    args = parser.parse_args(argv)
    if args.command == "report":
        pending = load_pending(args.state_dir)
        if not pending:
            _print({"status": "none"})
            return 0
        rows = []
        for rel, entry in sorted(pending["report"]["stores"].items()):
            if entry["class"] != DEVELOPMENTAL or not entry.get("needs_choice"):
                continue
            rows.append({"store": rel, "suggested": entry["suggested"],
                         "chosen": pending.get("choices", {}).get(rel),
                         "phone_records": entry["phone"].get("records"),
                         "home_records": entry["home"].get("records")})
        _print({"migration_id": pending["migration_id"], "status": pending["status"],
                "counts": pending["report"]["counts"], "choices": rows})
        return 0
    if args.command == "choose":
        sides = dict(s.split("=", 1) for s in args.side if "=" in s)
        result = choose(args.state_dir, sides, accept_suggested=args.accept_suggested)
        _print(result)
        return 0 if result.get("ok") else 1
    result = apply_pending_migration(args.state_dir)
    _print(result or {"status": "nothing_ready"})
    return 0 if (result is None or result.get("ok")) else 1


if __name__ == "__main__":
    sys.exit(main())
