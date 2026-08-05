#!/usr/bin/env python3
"""
Manual code lineage assimilation.

Hand-written code changes should not sit outside Aurora's lineage system.
This module watches the source tree, detects manual file changes, derives a
constraint-native signature for the changed file, and then tries to attach that
change to an existing code-evolution family before creating a new lineage
branch.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import hashlib
import json
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_internal.lineage_canonical import constraints_for_operation

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
LABEL_TO_AXIS = {
    "existence": "X",
    "temporal": "T",
    "energy": "N",
    "boundary": "B",
    "agency": "A",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "aurora_state",
    "aurora_runtime_output",
    "runs",
    "aurora_browser_profile",
    "aurora_genealogy",
    "aurora_geneology",
    "aurora_state_goal",
    ".mypy_cache",
    ".pytest_cache",
}


def _system_get(systems: Any, key: str, default: Any = None) -> Any:
    if isinstance(systems, dict):
        return systems.get(key, default)
    return getattr(systems, key, default)


def _purpose_lane_for_axis(axis: str) -> str:
    return {
        "X": "admissibility_grounding",
        "T": "continuity_memory",
        "N": "load_uncertainty",
        "B": "distinction_branching",
        "A": "repair_commitment",
    }.get(str(axis or "X").strip().upper(), "admissibility_grounding")


def _rewrite_profile_for_module(module_name: str) -> str:
    module = str(module_name or "").strip()
    if module == "aurora_internal.constraint_genealogy":
        return "constraint_genealogy"
    if module == "aurora_governance_persistence_gateway":
        return "governance_gateway"
    if module == "aurora_expression_perception":
        return "perception_synthesis"
    if module == "aurora_dimensional_systems":
        return "dimensional_balancing"
    return "generic"


def _axis_signature(constraints: Iterable[str]) -> str:
    counts = {axis: 0 for axis in AXES}
    for raw in (constraints or []):
        axis = LABEL_TO_AXIS.get(str(raw or "").strip().lower())
        if axis:
            counts[axis] += 1
    if not any(counts.values()):
        counts["X"] = 1
    parts: List[str] = []
    for axis in AXES:
        value = int(counts.get(axis, 0) or 0)
        if value > 0:
            parts.append(f"{axis}^{value}")
    return "*".join(parts) if parts else "X^1"


def _signature_counts(signature: str) -> Dict[str, int]:
    counts = {axis: 0 for axis in AXES}
    for raw in str(signature or "").split("*"):
        token = raw.strip()
        if not token:
            continue
        if "^" in token:
            axis, value = token.split("^", 1)
        else:
            axis, value = token, "1"
        axis = str(axis or "").strip().upper()
        if axis not in counts:
            continue
        try:
            counts[axis] += max(0, int(float(str(value or "0").strip())))
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:110",
                exc=_aurora_boundary_exc,
                context={"function": "_signature_counts", "handler_line": 110, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            continue
    return counts


def _signature_similarity(left: str, right: str) -> float:
    l_counts = _signature_counts(left)
    r_counts = _signature_counts(right)
    overlap = 0.0
    total = 0.0
    for axis in AXES:
        lv = float(max(0, int(l_counts.get(axis, 0) or 0)))
        rv = float(max(0, int(r_counts.get(axis, 0) or 0)))
        overlap += min(lv, rv)
        total += max(lv, rv)
    return 0.0 if total <= 0.0 else overlap / total


class ManualCodeLineageAssimilator:
    def __init__(self, repo_root: str, state_dir: str = _STATE_ROOT) -> None:
        self.repo_root = os.path.abspath(repo_root)
        self.state_dir = os.path.abspath(state_dir)
        self.state_path = os.path.join(self.state_dir, "manual_code_lineage_state.json")
        self._state: Dict[str, Any] = {
            "initialized": False,
            "manifest": {},
            "history": [],
        }
        self._descriptor_cache: Dict[str, Any] = {
            "path": "",
            "mtime_ns": 0,
            "size": 0,
            "operations": [],
        }
        self._load_state()

    def _load_state(self) -> None:
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as fh:
                raw = dict(json.load(fh) or {})
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:152",
                exc=_aurora_boundary_exc,
                context={"function": "_load_state", "handler_line": 152, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            return
        self._state = {
            "initialized": bool(raw.get("initialized", False)),
            "manifest": dict(raw.get("manifest", {}) or {}),
            "history": list(raw.get("history", []) or [])[-240:],
            "last_run_at": float(raw.get("last_run_at", 0.0) or 0.0),
        }

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
            stamp = float(time.time())
            self._state["last_run_at"] = stamp
            payload = dict(self._state)
            payload["last_run_at"] = stamp
            with open(self.state_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=True, indent=2, sort_keys=True)
            return True
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:171",
                exc=_aurora_boundary_exc,
                context={"function": "save", "handler_line": 171, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            return False

    def status(self) -> Dict[str, Any]:
        return {
            "initialized": bool(self._state.get("initialized", False)),
            "manifest_count": int(len(dict(self._state.get("manifest", {}) or {}))),
            "history_count": int(len(list(self._state.get("history", []) or []))),
            "last_run_at": float(self._state.get("last_run_at", 0.0) or 0.0),
            "state_path": self.state_path,
        }

    def _iter_python_files(self) -> Iterable[str]:
        for root, dirs, files in os.walk(self.repo_root):
            rel_dir = os.path.relpath(root, self.repo_root)
            parts = set() if rel_dir in (".", "") else set(rel_dir.replace("\\", "/").split("/"))
            if parts & SKIP_DIRS or any(part.startswith("reset_full_backup_") for part in parts):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("reset_full_backup_")]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                yield os.path.relpath(path, self.repo_root).replace("\\", "/")

    def _file_sha1(self, rel_path: str) -> str:
        path = os.path.join(self.repo_root, rel_path)
        digest = hashlib.sha1()
        try:
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(131072), b""):
                    digest.update(chunk)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:204",
                exc=_aurora_boundary_exc,
                context={"function": "_file_sha1", "handler_line": 204, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            return ""
        return digest.hexdigest()

    def _scan_manifest(self) -> Dict[str, Dict[str, Any]]:
        # Content hash is the actual change signal. mtime_ns/size are kept only
        # as a fast-path cache key: when both are unchanged from the previous
        # scan we reuse the previously computed sha1 instead of re-hashing, so
        # a checkout/clone that resets mtimes on every file (but not content)
        # still ends up re-hashing everything once and then finding no real
        # changes, rather than reporting a false "modified" for nearly the
        # whole tree the way pure mtime/size comparison did.
        previous = dict(self._state.get("manifest", {}) or {})
        manifest: Dict[str, Dict[str, Any]] = {}
        for rel_path in self._iter_python_files():
            path = os.path.join(self.repo_root, rel_path)
            try:
                st = os.stat(path)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:214",
                    exc=_aurora_boundary_exc,
                    context={"function": "_scan_manifest", "handler_line": 214, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
                )
                continue
            mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
            size = int(st.st_size)
            prev_entry = dict(previous.get(rel_path, {}) or {})
            if (
                str(prev_entry.get("sha1", "") or "")
                and int(prev_entry.get("mtime_ns", -1) or -1) == mtime_ns
                and int(prev_entry.get("size", -1) or -1) == size
            ):
                sha1 = str(prev_entry.get("sha1", "") or "")
            else:
                sha1 = self._file_sha1(rel_path)
            manifest[rel_path] = {
                "mtime_ns": mtime_ns,
                "size": size,
                "sha1": sha1,
            }
        return manifest

    def _detect_changes(self, current_manifest: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        previous = dict(self._state.get("manifest", {}) or {})
        if not previous:
            return []
        changes: List[Dict[str, Any]] = []
        all_paths = sorted(set(previous.keys()) | set(current_manifest.keys()))
        for rel_path in all_paths:
            prev = dict(previous.get(rel_path, {}) or {})
            cur = dict(current_manifest.get(rel_path, {}) or {})
            prev_sha1 = str(prev.get("sha1", "") or "")
            cur_sha1 = str(cur.get("sha1", "") or "")
            if prev and cur:
                if prev_sha1 and cur_sha1:
                    if prev_sha1 == cur_sha1:
                        continue
                else:
                    # Migration path: this manifest entry was persisted by a
                    # pre-content-hash version of this module (mtime_ns/size
                    # only, no sha1 -- every entry written before this fix).
                    # An mtime_ns/size fallback here was tried and found
                    # NOT SAFE: this environment resets mtime_ns on every
                    # file on session/checkout start (the exact mechanism
                    # Bug Report 1 already established), so a fallback that
                    # trusts mtime_ns reintroduces the identical false-storm
                    # bug for this one migration boot -- confirmed live
                    # against the real repo's own persisted manifest (434
                    # old-format entries, every single one's mtime_ns had
                    # already changed from what was recorded, so the
                    # mtime-fallback also reported all 468 files modified).
                    # There is no reliable signal at all for "did this file
                    # change since an old-format snapshot that never
                    # recorded content" -- mtime is proven unreliable, and
                    # there is no prior hash to compare against. The honest,
                    # conservative choice is the same one already used for a
                    # brand-new/uninitialized manifest: treat "no prior hash
                    # to compare against" as "no change signal," not as
                    # "changed." This one-time migration boot cannot detect
                    # genuine changes made before this fix existed (those
                    # are fundamentally undetectable without a hash-bearing
                    # prior snapshot) but it seeds a real sha1 for every
                    # file below, so every boot from here on compares
                    # correctly.
                    continue
                kind = "modified"
            elif not prev and cur:
                kind = "added"
            elif prev and not cur:
                kind = "deleted"
            else:
                continue
            change_id = hashlib.sha1(
                f"{rel_path}:{kind}:{cur_sha1}".encode("utf-8")
            ).hexdigest()[:12]
            changes.append({
                "change_id": f"MC:{change_id}",
                "file": rel_path,
                "kind": kind,
                "sha1": cur_sha1,
            })
        return changes

    def _descriptor_operations(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.state_dir, "operation_descriptors.json")
        try:
            st = os.stat(path)
            mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
            size = int(st.st_size)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:256",
                exc=_aurora_boundary_exc,
                context={"function": "_descriptor_operations", "handler_line": 256, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            return []
        cache = dict(self._descriptor_cache or {})
        if (
            str(cache.get("path", "")) == path
            and int(cache.get("mtime_ns", 0) or 0) == mtime_ns
            and int(cache.get("size", 0) or 0) == size
        ):
            return list(cache.get("operations", []) or [])
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = dict(json.load(fh) or {})
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:268",
                exc=_aurora_boundary_exc,
                context={"function": "_descriptor_operations", "handler_line": 268, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            return []
        ops = [dict(row) for row in (raw.get("operations", []) or []) if isinstance(row, dict)]
        self._descriptor_cache = {
            "path": path,
            "mtime_ns": mtime_ns,
            "size": size,
            "operations": ops,
        }
        return ops

    def _constraints_for_file(self, rel_path: str) -> Dict[str, Any]:
        cleaned = str(rel_path or "").replace("\\", "/").strip()
        module_name = cleaned[:-3].replace("/", ".") if cleaned.endswith(".py") else cleaned.replace("/", ".")
        rows = [row for row in self._descriptor_operations() if str(row.get("file", "") or "").replace("\\", "/").strip() == cleaned]
        labels: List[str] = []
        for row in rows:
            op_id = str(row.get("op_id", "") or "")
            axis = str(row.get("axis", "") or "")
            requires = list(row.get("requires", []) or [])
            effect_tags = list(row.get("effect_tags", []) or [])
            labels.extend(constraints_for_operation(op_id, axis=axis, requires=requires, effect_tags=effect_tags))
        if not labels:
            labels = list(constraints_for_operation(module_name))
        unique_labels: List[str] = []
        for label in labels:
            token = str(label or "").strip().lower()
            if token and token not in unique_labels:
                unique_labels.append(token)
        axis_weights = {axis: 0.0 for axis in AXES}
        for label in unique_labels:
            axis = LABEL_TO_AXIS.get(label)
            if axis:
                axis_weights[axis] += 1.0
        if not any(axis_weights.values()):
            axis_weights["X"] = 1.0
        dominant_axis = max(axis_weights, key=axis_weights.get)
        return {
            "module_name": module_name,
            "constraints": unique_labels,
            "axis_signature": _axis_signature(unique_labels),
            "dominant_axis": dominant_axis,
            "purpose_lane": _purpose_lane_for_axis(dominant_axis),
            "rewrite_profile": _rewrite_profile_for_module(module_name),
            "descriptor_rows": len(rows),
        }

    def _code_ability_records(self, genealogy: Any) -> List[Dict[str, Any]]:
        abilities = dict(getattr(genealogy, "abilities", {}) or {}) if genealogy is not None else {}
        rows: List[Dict[str, Any]] = []
        for aid, profile in abilities.items():
            tags = [str(x) for x in (getattr(profile, "effect_tags", ()) or ())]
            if "code_evolution" not in tags and "manual_code_lineage" not in tags:
                continue
            modules = [tag.split(":", 1)[1] for tag in tags if tag.startswith("mutation_module:")]
            signatures = [tag.split(":", 1)[1] for tag in tags if tag.startswith("origin_signature:")]
            rewrite_profiles = [tag.split(":", 1)[1] for tag in tags if tag.startswith("rewrite_profile:")]
            rows.append({
                "ability_id": str(aid or ""),
                "axis": str(getattr(profile, "axis", "X") or "X"),
                "modules": modules,
                "signatures": signatures,
                "rewrite_profiles": rewrite_profiles,
                "notes": str(getattr(profile, "notes", "") or ""),
            })
        return rows

    def _score_family(self, change_meta: Dict[str, Any], family: Dict[str, Any]) -> float:
        score = 0.0
        module_name = str(change_meta.get("module_name", "") or "")
        module_parts = module_name.split(".")
        modules = [str(item or "") for item in (family.get("modules", []) or []) if str(item or "")]
        if module_name in modules:
            score += 1.0
        else:
            for mod in modules:
                if mod and module_name.startswith(mod + "."):
                    score = max(score, 0.72)
                elif mod and mod.startswith(module_name + "."):
                    score = max(score, 0.58)
                elif module_parts and mod.split(".")[:2] == module_parts[:2]:
                    score = max(score, 0.42)
        if str(family.get("axis", "") or "") == str(change_meta.get("dominant_axis", "") or ""):
            score += 0.22
        change_sig = str(change_meta.get("axis_signature", "") or "")
        best_sig = 0.0
        for sig in (family.get("signatures", []) or []):
            best_sig = max(best_sig, _signature_similarity(change_sig, str(sig or "")))
        score += 0.28 * best_sig
        rewrite_profile = str(change_meta.get("rewrite_profile", "") or "")
        if rewrite_profile and rewrite_profile in list(family.get("rewrite_profiles", []) or []):
            score += 0.16
        return round(float(max(0.0, min(1.0, score))), 6)

    def _best_family(self, genealogy: Any, change_meta: Dict[str, Any]) -> Dict[str, Any]:
        best: Dict[str, Any] = {"score": 0.0}
        for family in self._code_ability_records(genealogy):
            score = self._score_family(change_meta, family)
            if score > float(best.get("score", 0.0) or 0.0):
                best = {**family, "score": score}
        return best

    def _record_journal_event(self, systems: Any, event: Dict[str, Any]) -> None:
        journal = _system_get(systems, "lineage_emergence_journal")
        if journal is None:
            return
        try:
            if hasattr(journal, "record_event"):
                journal.record_event(event)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:377",
                exc=_aurora_boundary_exc,
                context={"function": "_record_journal_event", "handler_line": 377, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
            )
            pass

    def assimilate(self, systems: Any, *, source: str = "runtime.boot", force: bool = False) -> List[Dict[str, Any]]:
        current_manifest = self._scan_manifest()
        if not bool(self._state.get("initialized", False)) and not force:
            self._state["initialized"] = True
            self._state["manifest"] = current_manifest
            self.save()
            return []

        changes = self._detect_changes(current_manifest) if not force else [
            {
                "change_id": f"MC:{hashlib.sha1(rel.encode('utf-8')).hexdigest()[:12]}",
                "file": rel,
                "kind": "modified",
                "sha1": str(current_manifest.get(rel, {}).get("sha1", "") or ""),
            }
            for rel in sorted(current_manifest.keys())
        ]
        if not changes:
            self._state["initialized"] = True
            self._state["manifest"] = current_manifest
            self.save()
            return []

        genealogy = _system_get(systems, "genealogy")
        results: List[Dict[str, Any]] = []
        for change in changes:
            if str(change.get("kind", "") or "") == "deleted":
                continue
            meta = self._constraints_for_file(str(change.get("file", "") or ""))
            family = self._best_family(genealogy, meta)
            matched_ability_id = str(family.get("ability_id", "") or "") if float(family.get("score", 0.0) or 0.0) >= 0.82 else ""
            payload = {
                "change_id": str(change.get("change_id", "") or ""),
                "source": str(source or "runtime.boot"),
                "target_files": [str(change.get("file", "") or "")],
                "target_modules": [str(meta.get("module_name", "") or "")],
                "constraints": list(meta.get("constraints", []) or []),
                "axis_signature": str(meta.get("axis_signature", "") or ""),
                "dominant_axis": str(meta.get("dominant_axis", "") or "X"),
                "purpose_lane": str(meta.get("purpose_lane", "") or _purpose_lane_for_axis("X")),
                "rewrite_profile": str(meta.get("rewrite_profile", "") or "generic"),
                "matched_ability_id": matched_ability_id,
                "matched_score": float(family.get("score", 0.0) or 0.0),
                "change_kind": str(change.get("kind", "modified") or "modified"),
                "sha1": str(change.get("sha1", "") or ""),
            }
            reg = {"registered": False, "ability_id": ""}
            if genealogy is not None and hasattr(genealogy, "register_manual_code_assimilation"):
                try:
                    # flush=False: this is one file out of a whole assimilation
                    # batch. Genealogy mutations accumulate in memory across
                    # every change in this loop; the batch is persisted with a
                    # single flush_files() call after the loop, not once per
                    # file (per-file flush() was the multi-hundred-file hang).
                    reg = dict(genealogy.register_manual_code_assimilation(payload, flush=False) or {})
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:430",
                        exc=_aurora_boundary_exc,
                        context={"function": "assimilate", "handler_line": 430, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
                    )
                    reg = {"registered": False, "ability_id": matched_ability_id}
            result = {
                "change_id": payload["change_id"],
                "file": payload["target_files"][0],
                "module_name": payload["target_modules"][0],
                "dominant_axis": payload["dominant_axis"],
                "axis_signature": payload["axis_signature"],
                "purpose_lane": payload["purpose_lane"],
                "matched_ability_id": matched_ability_id,
                "matched_score": float(payload["matched_score"]),
                "registered_ability_id": str(reg.get("ability_id", "") or ""),
                "mode": str(reg.get("mode", "") or ("attached_existing_family" if matched_ability_id else "created_manual_branch")),
                "source": payload["source"],
                "timestamp": float(time.time()),
            }
            results.append(result)
            self._record_journal_event(
                systems,
                {
                    "timestamp": result["timestamp"],
                    "source": source,
                    "kind": "manual_code_assimilation",
                    "id": result["registered_ability_id"] or result["change_id"],
                    "axis": result["dominant_axis"],
                    "summary": (
                        f"Manual code change in {result['file']} "
                        f"{'attached to' if matched_ability_id else 'formed'} "
                        f"{result['registered_ability_id'] or result['matched_ability_id'] or 'a new lineage branch'}"
                    ),
                },
            )
            # Confess genuinely NEW structure (a newly-added file with no
            # existing genealogy family) to the warp field — the universal
            # accommodation engine — so that "new for her code" is recognized
            # the same way understanding-level gaps are. Restricted to added
            # files: a modified-but-unmatched file is not new structure, and
            # confessing every one of them floods the field on a stale manifest.
            # Code with no organ/family alignment routes to SURFACE_EMERGENCE
            # (architecture-level recognition + record); the demand carries the
            # structure's dominant constraint axis so the field can classify
            # and (later) accommodate it.
            if not matched_ability_id and str(change.get("kind", "")) == "added":
                try:
                    from aurora_warp_protocol import warp_guard as _warp_guard, WarpTrigger as _WT
                    _dom = str(meta.get("dominant_axis", "X") or "X").upper()
                    _profile = {ax: (0.80 if ax == _dom else 0.10) for ax in "XTNBA"}
                    _warp_guard(
                        source="manual_code_lineage",
                        layer="code",
                        trigger=_WT.NO_ORGAN_ALIGNMENT,
                        unresolved_text=str(payload["target_modules"][0]
                                            or payload["target_files"][0] or ""),
                        profile=_profile,
                        severity=0.6 if str(change.get("kind", "")) == "added" else 0.45,
                        persistence_key=str(payload["target_modules"][0] or "")[:48],
                    )
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:487",
                        exc=_aurora_boundary_exc,
                        context={"function": "assimilate", "handler_line": 487, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
                    )
                    pass

        if results:
            function_lineage = _system_get(systems, "function_lineage")
            if function_lineage is not None and hasattr(function_lineage, "rebuild"):
                try:
                    lineage_status = dict(function_lineage.rebuild() or {})
                    if genealogy is not None and hasattr(function_lineage, "attach_genealogy"):
                        function_lineage.attach_genealogy(genealogy)
                    for result in results:
                        result["function_lineage_rebuilt"] = True
                        result["function_lineage_count"] = int(lineage_status.get("function_count", 0) or 0)
                        result["function_lineage_coverage"] = float(lineage_status.get("coverage_rate", 0.0) or 0.0)
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="manual_code_lineage:rebuild_universal_function_lineage",
                        exc=_aurora_boundary_exc,
                        context={"function": "assimilate", "source_file": __file__},
                    )

        if results and genealogy is not None and hasattr(genealogy, "flush_files"):
            try:
                genealogy.flush_files()
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_manual_code_lineage.py:561",
                    exc=_aurora_boundary_exc,
                    context={"function": "assimilate", "handler_line": 561, "source_file": "aurora_internal/aurora_manual_code_lineage.py"},
                )

        history = list(self._state.get("history", []) or [])
        history.extend(results)
        self._state["history"] = history[-240:]
        self._state["manifest"] = current_manifest
        self._state["initialized"] = True
        self.save()
        return results
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
