#!/usr/bin/env python3
"""
Pressure Release Distillation Runner for Aurora.

Distillation moves oversized temporal residue out of the live stack and into
reversible archive rounds. Structural summaries stay attached to Aurora,
while the raw purged details are packed into a restoreable archive folder.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional


_BASE_DIR = Path(__file__).parent
_STATE_DIR = _BASE_DIR / "aurora_state"
_DISTILL_DIR = _STATE_DIR / "distillation"
_ARCHIVES_DIR = _DISTILL_DIR / "archives"
_CRYSTALS_FILE = _STATE_DIR / "distillation_crystals.json"
_MICRO_FILE = _STATE_DIR / "distillation_micro_residuals.json"
_RUNS_FILE = _STATE_DIR / "distillation_runs.json"
_METRICS_FILE = _STATE_DIR / "distillation_metrics.json"
_LINEAGE_FILE = _STATE_DIR / "live_lineage_journal.json"


class CoherenceShape(str, Enum):
    WAVE = "wave"
    VORTEX = "vortex"
    KNOT = "knot"
    DRIFT = "drift"


@dataclass(frozen=True)
class ResidueConfig:
    name: str
    path: Path
    max_bytes: int
    keep_tail_lines: int
    parser: str = "jsonl"


@dataclass
class PressureAggregate:
    source: str
    signature: str
    count: int = 0
    worth_total: float = 0.0
    coherence_total: float = 0.0
    axis_counts: Counter = field(default_factory=Counter)
    tag_counts: Counter = field(default_factory=Counter)
    first_ts: float = 0.0
    last_ts: float = 0.0
    examples: List[str] = field(default_factory=list)
    raw_bytes: int = 0

    def ingest(self, worth: float, coherence: float, axes: Iterable[str],
               tags: Iterable[str], timestamp: float, summary: str,
               raw_bytes: int) -> None:
        self.count += 1
        self.worth_total += worth
        self.coherence_total += coherence
        self.raw_bytes += raw_bytes
        for axis in axes:
            if axis:
                self.axis_counts[str(axis)] += 1
        for tag in tags:
            if tag:
                self.tag_counts[str(tag)] += 1
        if timestamp:
            if self.first_ts == 0.0 or timestamp < self.first_ts:
                self.first_ts = timestamp
            if timestamp > self.last_ts:
                self.last_ts = timestamp
        if summary and len(self.examples) < 3:
            self.examples.append(summary[:240])

    @property
    def avg_worth(self) -> float:
        return self.worth_total / max(1, self.count)

    @property
    def avg_coherence(self) -> float:
        return self.coherence_total / max(1, self.count)

    @property
    def axes(self) -> List[str]:
        return [axis for axis, _ in self.axis_counts.most_common(4)]

    @property
    def tags(self) -> List[str]:
        return [tag for tag, _ in self.tag_counts.most_common(6)]


class CoherenceAnalyzer:
    """Turns raw temporal records into structural features."""

    _AXES = ("X", "T", "N", "B", "A")

    def extract(self, source: str, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            signature = self._signature_from_dict(source, payload)
            axes = self._axes_from_payload(payload)
            tags = self._tags_from_payload(payload)
            timestamp = self._timestamp_from_payload(payload)
            worth = self._worth_from_payload(source, payload, axes)
            coherence = self._coherence_from_payload(payload, axes, tags)
            summary = self._summary_from_payload(source, payload)
            return {
                "source": source,
                "signature": signature,
                "axes": axes,
                "tags": tags,
                "timestamp": timestamp,
                "worth": worth,
                "coherence": coherence,
                "summary": summary,
            }

        text = str(payload or "").strip()
        signature = self._hash(f"{source}:{text[:160]}")
        tag = self._tag_from_log_line(text)
        worth = 0.22
        coherence = 0.18
        if tag in {"study", "dream", "social", "distill", "restore"}:
            worth += 0.24
            coherence += 0.18
        if "error" in text.lower():
            worth += 0.08
        return {
            "source": source,
            "signature": signature,
            "axes": [],
            "tags": [tag] if tag else [],
            "timestamp": 0.0,
            "worth": self._clamp(worth),
            "coherence": self._clamp(coherence),
            "summary": text[:240],
        }

    def classify(self, aggregate: PressureAggregate) -> CoherenceShape:
        axes = aggregate.axes
        tags = aggregate.tags
        if aggregate.count >= 2 and len(axes) >= 2:
            return CoherenceShape.KNOT
        if aggregate.count >= 4:
            return CoherenceShape.VORTEX
        if aggregate.avg_worth < 0.35 and aggregate.avg_coherence < 0.30:
            return CoherenceShape.DRIFT
        if "coherent_structure" in tags and axes:
            return CoherenceShape.KNOT
        return CoherenceShape.WAVE

    def _signature_from_dict(self, source: str, payload: Dict[str, Any]) -> str:
        for key in (
            "op_id", "surface", "id", "experience_id", "anchor",
            "mutation_id", "target", "word", "topic", "kind", "source"
        ):
            val = payload.get(key)
            if val:
                return self._hash(f"{source}:{key}:{val}")
        return self._hash(f"{source}:{json.dumps(payload, sort_keys=True)[:256]}")

    def _axes_from_payload(self, payload: Dict[str, Any]) -> List[str]:
        axes: List[str] = []
        expected = payload.get("expected_axes")
        if isinstance(expected, list):
            axes.extend(str(a) for a in expected if str(a) in self._AXES)
        axis_pressure = payload.get("axis_pressure")
        if isinstance(axis_pressure, dict):
            axes.extend(
                str(a) for a, v in axis_pressure.items()
                if a in self._AXES and float(v or 0.0) > 0.0
            )
        axis = payload.get("axis")
        if axis in self._AXES:
            axes.append(str(axis))
        return sorted(set(axes))

    def _tags_from_payload(self, payload: Dict[str, Any]) -> List[str]:
        tags: List[str] = []
        for key in ("kind", "source", "role", "topic"):
            value = payload.get(key)
            if value:
                tags.append(str(value))
        for key in ("tags", "effect_modes"):
            values = payload.get(key)
            if isinstance(values, list):
                tags.extend(str(v) for v in values if v)
        return sorted(set(tags))

    def _timestamp_from_payload(self, payload: Dict[str, Any]) -> float:
        for key in ("timestamp", "updated_at", "create_time"):
            value = payload.get(key)
            try:
                if value:
                    return float(value)
            except Exception:
                pass
        return 0.0

    def _worth_from_payload(self, source: str, payload: Dict[str, Any],
                            axes: List[str]) -> float:
        scores: List[float] = []
        for key in ("surface_score", "genealogy_pressure", "confidence"):
            value = payload.get(key)
            try:
                if value is not None:
                    scores.append(float(value))
            except Exception:
                pass

        consequence = payload.get("consequence")
        if isinstance(consequence, dict):
            try:
                scores.append(min(1.0, float(consequence.get("tension", 0.0) or 0.0)))
            except Exception:
                pass

        outcome = payload.get("outcome")
        if isinstance(outcome, dict) and outcome.get("resolved") is False:
            scores.append(0.56)

        if "genealogy" in str(payload.get("source", "")).lower():
            scores.append(0.68)
        if "lineage" in source:
            scores.append(0.62)
        if len(axes) >= 2:
            scores.append(0.74)
        if not scores:
            scores.append(0.30 if source == "daemon_log" else 0.42)
        return self._clamp(sum(scores) / len(scores))

    def _coherence_from_payload(self, payload: Dict[str, Any], axes: List[str],
                                tags: List[str]) -> float:
        score = 0.10
        if axes:
            score += min(0.42, 0.18 * len(axes))
        if tags:
            score += min(0.24, 0.04 * len(tags))
        if payload.get("anchor") and payload.get("meaning"):
            score += 0.18
        if payload.get("effect_modes"):
            score += 0.12
        if isinstance(payload.get("outcome"), dict):
            score += 0.08
        return self._clamp(score)

    def _summary_from_payload(self, source: str, payload: Dict[str, Any]) -> str:
        for key in (
            "summary", "meaning", "causal_action", "text", "surface",
            "op_id", "anchor", "topic", "lesson_summary"
        ):
            value = payload.get(key)
            if value:
                return f"{source}: {str(value)[:220]}"
        return f"{source}: structural residue"

    def _tag_from_log_line(self, line: str) -> str:
        lo = line.lower()
        if "[study]" in lo:
            return "study"
        if "[dream]" in lo:
            return "dream"
        if "[social]" in lo or "[browser]" in lo:
            return "social"
        if "[distill]" in lo:
            return "distill"
        if "[restore]" in lo:
            return "restore"
        if "error" in lo:
            return "error"
        return "log"

    def _hash(self, value: str) -> str:
        return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))


class TemporalCompressor:
    """Trims temporal residue while emitting structural summaries."""

    def __init__(self, analyzer: Optional[CoherenceAnalyzer] = None):
        self.analyzer = analyzer or CoherenceAnalyzer()

    def compress(self, config: ResidueConfig, *, force: bool = False,
                 archive_dir: Optional[Path] = None) -> Dict[str, Any]:
        path = config.path
        if not path.exists():
            return self._empty_result(config, "missing")

        size = path.stat().st_size
        if not force and size <= config.max_bytes:
            return self._empty_result(config, "under_threshold", current_bytes=size)

        if config.parser in {"jsonl", "log"}:
            return self._compress_line_file(config, size, archive_dir=archive_dir)
        return self._empty_result(config, "unsupported", current_bytes=size)

    def _compress_line_file(self, config: ResidueConfig, size: int,
                            *, archive_dir: Optional[Path]) -> Dict[str, Any]:
        keep: deque[str] = deque()
        aggregates: Dict[str, PressureAggregate] = {}
        bytes_purged = 0
        records_purged = 0
        archive_file = archive_dir / f"{config.name}.purged" if archive_dir else None
        archive_handle = None

        if archive_file is not None:
            archive_file.parent.mkdir(parents=True, exist_ok=True)
            archive_handle = open(archive_file, "w", encoding="utf-8")

        try:
            with open(config.path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if len(keep) < config.keep_tail_lines:
                        keep.append(line)
                        continue
                    old_line = keep.popleft()
                    keep.append(line)
                    if archive_handle is not None:
                        archive_handle.write(old_line)
                    self._ingest_purged_line(
                        source=config.name,
                        parser=config.parser,
                        line=old_line,
                        aggregates=aggregates,
                    )
                    bytes_purged += len(old_line.encode("utf-8", errors="ignore"))
                    records_purged += 1
        finally:
            if archive_handle is not None:
                archive_handle.close()

        if records_purged == 0:
            if archive_file and archive_file.exists():
                archive_file.unlink(missing_ok=True)
            return self._empty_result(config, "tail_only", current_bytes=size)

        tmp = config.path.with_suffix(config.path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.writelines(list(keep))
        os.replace(tmp, config.path)

        crystals: List[Dict[str, Any]] = []
        micro_residuals: List[Dict[str, Any]] = []
        shape_counts: Counter = Counter()
        for aggregate in sorted(
            aggregates.values(),
            key=lambda item: (item.count * item.avg_worth * item.avg_coherence),
            reverse=True,
        ):
            shape = self.analyzer.classify(aggregate)
            shape_counts[shape.value] += 1
            record = {
                "id": f"DISTILL:{shape.value}:{aggregate.signature}",
                "signature": aggregate.signature,
                "source": aggregate.source,
                "shape": shape.value,
                "count": aggregate.count,
                "avg_worth": round(aggregate.avg_worth, 4),
                "avg_coherence": round(aggregate.avg_coherence, 4),
                "axes": aggregate.axes,
                "axis_counts": {k: int(v) for k, v in aggregate.axis_counts.items()},
                "tags": aggregate.tags,
                "tag_counts": {k: int(v) for k, v in aggregate.tag_counts.items()},
                "first_ts": aggregate.first_ts,
                "last_ts": aggregate.last_ts,
                "raw_bytes": aggregate.raw_bytes,
                "examples": aggregate.examples,
            }
            if shape in {CoherenceShape.KNOT, CoherenceShape.VORTEX}:
                crystals.append(record)
            elif aggregate.avg_worth >= 0.45 or aggregate.avg_coherence >= 0.40:
                micro_residuals.append(record)

        return {
            "source": config.name,
            "path": str(config.path),
            "parser": config.parser,
            "status": "distilled",
            "current_bytes": size,
            "bytes_purged": bytes_purged,
            "records_purged": records_purged,
            "archive_file": str(archive_file) if archive_file else "",
            "crystals": crystals,
            "micro_residuals": micro_residuals,
            "shape_counts": dict(shape_counts),
        }

    def _ingest_purged_line(self, *, source: str, parser: str, line: str,
                            aggregates: Dict[str, PressureAggregate]) -> None:
        stripped = line.strip()
        if not stripped:
            return
        if parser == "jsonl":
            try:
                payload: Any = json.loads(stripped)
            except Exception:
                payload = {"raw_line": stripped[:240]}
        else:
            payload = stripped[:240]
        features = self.analyzer.extract(source, payload)
        signature = str(features["signature"])
        agg = aggregates.get(signature)
        if agg is None:
            agg = PressureAggregate(source=source, signature=signature)
            aggregates[signature] = agg
        agg.ingest(
            worth=float(features["worth"]),
            coherence=float(features["coherence"]),
            axes=list(features["axes"]),
            tags=list(features["tags"]),
            timestamp=float(features["timestamp"]),
            summary=str(features["summary"]),
            raw_bytes=len(line.encode("utf-8", errors="ignore")),
        )

    def _empty_result(self, config: ResidueConfig, status: str,
                      current_bytes: int = 0) -> Dict[str, Any]:
        return {
            "source": config.name,
            "path": str(config.path),
            "parser": config.parser,
            "status": status,
            "current_bytes": current_bytes,
            "bytes_purged": 0,
            "records_purged": 0,
            "archive_file": "",
            "crystals": [],
            "micro_residuals": [],
            "shape_counts": {},
        }


class MetabolicDistiller:
    """Coherence-aware pressure release runner."""

    def __init__(self, state_dir: Path = _STATE_DIR,
                 logger: Optional[Callable[[str], None]] = None):
        self.state_dir = state_dir
        self.logger = logger or (lambda _msg: None)
        self.analyzer = CoherenceAnalyzer()
        self.compressor = TemporalCompressor(self.analyzer)
        self.archive_retention_runs = max(
            1,
            int(os.environ.get("AURORA_DISTILL_ARCHIVE_RETENTION", "24") or 24),
        )
        self.residue_configs = [
            ResidueConfig(
                name="surface_pressure",
                path=self.state_dir / "surface_pressure_log.jsonl",
                max_bytes=64 * 1024 * 1024,
                keep_tail_lines=18000,
                parser="jsonl",
            ),
            ResidueConfig(
                name="pressure_experiences",
                path=self.state_dir / "pressure_experiences.jsonl",
                max_bytes=12 * 1024 * 1024,
                keep_tail_lines=10000,
                parser="jsonl",
            ),
            ResidueConfig(
                name="daemon_log",
                path=self.state_dir / "daemon.log",
                max_bytes=512 * 1024,
                keep_tail_lines=2500,
                parser="log",
            ),
            ResidueConfig(
                name="articulation_feedback",
                path=self.state_dir / "articulation_feedback.jsonl",
                max_bytes=2 * 1024 * 1024,
                keep_tail_lines=500,
                parser="jsonl",
            ),
        ]

    def trigger_snapshot(self) -> Dict[str, Any]:
        sizes = {
            cfg.name: cfg.path.stat().st_size if cfg.path.exists() else 0
            for cfg in self.residue_configs
        }
        low_worth_density = self._estimate_low_worth_density()
        genealogy_backlog = int(_LINEAGE_FILE.stat().st_size) if _LINEAGE_FILE.exists() else 0
        total_state_bytes = 0
        try:
            total_state_bytes = sum(
                p.stat().st_size for p in self.state_dir.iterdir() if p.is_file()
            )
        except Exception:
            total_state_bytes = 0

        der_load = self._estimate_der_load()
        quiet_window = self._in_quiet_window()
        latest_run = self._latest_restorable_run_id()
        triggers = {
            "log_size_threshold_exceeded": any(
                sizes[cfg.name] > cfg.max_bytes for cfg in self.residue_configs
            ),
            "high_low_worth_density": low_worth_density >= 0.58,
            "genealogy_backlog": genealogy_backlog >= 3 * 1024 * 1024,
            "memory_saturation": total_state_bytes >= 300 * 1024 * 1024,
            "der_load_increase": der_load >= 0.55,
            "coherence_instability": low_worth_density >= 0.42,
            "quiet_window": quiet_window,
        }
        return {
            "sizes": sizes,
            "total_state_bytes": total_state_bytes,
            "low_worth_density": round(low_worth_density, 4),
            "der_load": round(der_load, 4),
            "latest_restorable_run_id": latest_run,
            "triggers": triggers,
        }

    def should_run(self, *, force: bool = False) -> Dict[str, Any]:
        snapshot = self.trigger_snapshot()
        triggers = snapshot["triggers"]
        snapshot["should_run"] = force or bool(
            triggers["log_size_threshold_exceeded"]
            or triggers["high_low_worth_density"]
            or triggers["memory_saturation"]
            or (triggers["quiet_window"] and (triggers["coherence_instability"] or triggers["genealogy_backlog"]))
            or triggers["der_load_increase"]
        )
        return snapshot

    def run(self, *, force: bool = False) -> Dict[str, Any]:
        snapshot = self.should_run(force=force)
        if not snapshot["should_run"]:
            telemetry = self._build_idle_telemetry(snapshot)
            self._write_metrics(telemetry)
            return telemetry

        run_id = self._new_run_id()
        archive_dir = _ARCHIVES_DIR / run_id
        archive_dir.mkdir(parents=True, exist_ok=True)

        self.logger(f"  [DISTILL] Pressure release distillation started. run={run_id}")
        results = [
            self.compressor.compress(cfg, force=force, archive_dir=archive_dir)
            for cfg in self.residue_configs
        ]
        crystals: List[Dict[str, Any]] = []
        micro_residuals: List[Dict[str, Any]] = []
        bytes_purged = 0
        for result in results:
            crystals.extend(result["crystals"])
            micro_residuals.extend(result["micro_residuals"])
            bytes_purged += int(result["bytes_purged"] or 0)

        crystals = self._merge_records(_CRYSTALS_FILE, crystals, keep=400, sort_key="last_ts")
        micro_residuals = self._merge_records(_MICRO_FILE, micro_residuals, keep=600, sort_key="last_ts")
        links_promoted = self._promote_lineage(crystals)
        manifest = self._write_archive_manifest(
            run_id=run_id,
            archive_dir=archive_dir,
            snapshot=snapshot,
            results=results,
        )

        telemetry = self._build_distill_telemetry(
            run_id=run_id,
            snapshot=snapshot,
            results=results,
            bytes_purged=bytes_purged,
            crystals=crystals,
            micro_residuals=micro_residuals,
            links_promoted=links_promoted,
            archive_dir=archive_dir,
        )
        self._append_run(telemetry)
        pruned = self._prune_archive_runs()
        if pruned:
            self.logger(f"  [DISTILL] Pruned {pruned} old archive rounds")
        self._write_metrics(telemetry)
        self.logger(
            "  [DISTILL] Completed: "
            f"run={run_id} purged={self._human_bytes(bytes_purged)} "
            f"crystals={telemetry['crystals_formed']} coherence={telemetry['coherence_ratio']:.2f}"
        )
        if manifest.get("restorable"):
            self.logger(f"  [DISTILL] Archive packed at {archive_dir}")
        return telemetry

    def restore(self, *, run_id: Optional[str] = None) -> Dict[str, Any]:
        run_entry = self._resolve_run(run_id)
        if not run_entry:
            telemetry = {
                "timestamp": time.time(),
                "timestamp_str": self._now_str(),
                "status": "restore_missing",
                "summary": "no restorable distillation round found",
                "restored_run_id": "",
                "distillation_status": "restore_missing",
            }
            self._write_metrics(telemetry)
            return telemetry

        archive_dir = Path(str(run_entry.get("archive_dir") or ""))
        manifest_path = archive_dir / "manifest.json"
        if not manifest_path.exists():
            telemetry = {
                "timestamp": time.time(),
                "timestamp_str": self._now_str(),
                "status": "restore_missing",
                "summary": f"manifest missing for {run_entry.get('run_id', '')}",
                "restored_run_id": str(run_entry.get("run_id", "")),
                "distillation_status": "restore_missing",
            }
            self._write_metrics(telemetry)
            return telemetry

        manifest = json.loads(manifest_path.read_text())
        if manifest.get("restored_at"):
            telemetry = {
                "timestamp": time.time(),
                "timestamp_str": self._now_str(),
                "status": "restore_skipped",
                "summary": f"run {manifest.get('run_id', '')} already restored",
                "restored_run_id": str(manifest.get("run_id", "")),
                "distillation_status": f"restored {manifest.get('run_id', '')}",
            }
            self._write_metrics(telemetry)
            return telemetry

        restored_sources = 0
        restored_bytes = 0
        for result in manifest.get("results", []):
            target_path = Path(str(result.get("path") or ""))
            archive_file = Path(str(result.get("archive_file") or ""))
            if not target_path.exists() or not archive_file.exists():
                continue
            restored_bytes += self._restore_file(target_path, archive_file)
            restored_sources += 1

        restored_at = self._now_str()
        manifest["restored_at"] = restored_at
        self._write_json_atomic(manifest_path, manifest)
        self._mark_run_restored(str(manifest.get("run_id", "")), restored_at)

        telemetry = {
            "timestamp": time.time(),
            "timestamp_str": restored_at,
            "status": "restored",
            "summary": f"restored {manifest.get('run_id', '')} from archive",
            "restored_run_id": str(manifest.get("run_id", "")),
            "restored_sources": restored_sources,
            "restored_bytes": restored_bytes,
            "distillation_status": f"restored {manifest.get('run_id', '')}",
        }
        self._write_metrics(telemetry)
        self.logger(
            "  [RESTORE] Restored distillation round "
            f"{manifest.get('run_id', '')} ({restored_sources} source files)"
        )
        return telemetry

    def _write_archive_manifest(self, *, run_id: str, archive_dir: Path,
                                snapshot: Dict[str, Any],
                                results: List[Dict[str, Any]]) -> Dict[str, Any]:
        manifest = {
            "run_id": run_id,
            "timestamp": time.time(),
            "timestamp_str": self._now_str(),
            "restored_at": "",
            "archive_dir": str(archive_dir),
            "snapshot": snapshot,
            "results": [
                {
                    "source": result.get("source", ""),
                    "path": result.get("path", ""),
                    "parser": result.get("parser", "jsonl"),
                    "bytes_purged": int(result.get("bytes_purged", 0) or 0),
                    "records_purged": int(result.get("records_purged", 0) or 0),
                    "archive_file": result.get("archive_file", ""),
                    "status": result.get("status", ""),
                }
                for result in results
                if int(result.get("bytes_purged", 0) or 0) > 0
            ],
        }
        manifest["restorable"] = bool(manifest["results"])
        self._write_json_atomic(archive_dir / "manifest.json", manifest)
        return manifest

    def _build_idle_telemetry(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "timestamp_str": self._now_str(),
            "status": "idle",
            "summary": "idle",
            "trigger_snapshot": snapshot,
            "bytes_purged": 0,
            "links_promoted": 0,
            "crystals_formed": 0,
            "micro_residuals_preserved": 0,
            "coherence_ratio": 1.0,
            "vortex_count": 0,
            "knot_count": 0,
            "wave_count": 0,
            "drift_count": 0,
            "results": [],
            "archive_dir": "",
            "run_id": "",
            "restorable": bool(snapshot.get("latest_restorable_run_id")),
            "latest_restorable_run_id": snapshot.get("latest_restorable_run_id", ""),
            "distillation_status": "idle",
        }

    def _build_distill_telemetry(self, *, run_id: str, snapshot: Dict[str, Any],
                                 results: List[Dict[str, Any]], bytes_purged: int,
                                 crystals: List[Dict[str, Any]],
                                 micro_residuals: List[Dict[str, Any]],
                                 links_promoted: int, archive_dir: Path) -> Dict[str, Any]:
        knot_count = sum(1 for item in crystals if item.get("shape") == "knot")
        vortex_count = sum(1 for item in crystals if item.get("shape") == "vortex")
        drift_count = sum(int(result.get("shape_counts", {}).get("drift", 0) or 0) for result in results)
        wave_count = sum(int(result.get("shape_counts", {}).get("wave", 0) or 0) for result in results)
        coherent = knot_count + vortex_count + wave_count
        total = coherent + drift_count
        coherence_ratio = coherent / total if total else 1.0
        summary = (
            f"run {run_id} | {self._human_bytes(bytes_purged)} purged | "
            f"{len(crystals)} crystals"
        )
        return {
            "timestamp": time.time(),
            "timestamp_str": self._now_str(),
            "status": "distilled",
            "summary": summary,
            "trigger_snapshot": snapshot,
            "bytes_purged": bytes_purged,
            "links_promoted": links_promoted,
            "crystals_formed": len(crystals),
            "micro_residuals_preserved": len(micro_residuals),
            "coherence_ratio": round(coherence_ratio, 4),
            "vortex_count": vortex_count,
            "knot_count": knot_count,
            "wave_count": wave_count,
            "drift_count": drift_count,
            "results": results,
            "archive_dir": str(archive_dir),
            "run_id": run_id,
            "restorable": True,
            "latest_restorable_run_id": run_id,
            "distillation_status": f"{run_id} ready",
        }

    def _append_run(self, telemetry: Dict[str, Any]) -> None:
        runs = self._read_json_list(_RUNS_FILE)
        runs.append({
            "run_id": telemetry.get("run_id", ""),
            "timestamp": telemetry["timestamp"],
            "timestamp_str": telemetry["timestamp_str"],
            "status": telemetry["status"],
            "bytes_purged": telemetry.get("bytes_purged", 0),
            "links_promoted": telemetry.get("links_promoted", 0),
            "crystals_formed": telemetry.get("crystals_formed", 0),
            "coherence_ratio": telemetry.get("coherence_ratio", 1.0),
            "vortex_count": telemetry.get("vortex_count", 0),
            "knot_count": telemetry.get("knot_count", 0),
            "summary": telemetry.get("summary", ""),
            "archive_dir": telemetry.get("archive_dir", ""),
            "restorable": bool(telemetry.get("restorable", False)),
            "restored_at": "",
        })
        self._write_json_atomic(_RUNS_FILE, runs[-120:])

    def _prune_archive_runs(self) -> int:
        """
        Keep only the most recent archive runs on disk.

        The run ledger remains as historical metadata, but archive folders for
        older distillation rounds are deleted so the system cannot accumulate an
        unbounded number of restoreable copies.
        """
        runs = self._read_json_list(_RUNS_FILE)
        if len(runs) <= self.archive_retention_runs:
            return 0

        # Sort oldest first so pruning preserves the newest restore points.
        ordered = sorted(
            runs,
            key=lambda item: float(item.get("timestamp", 0.0) or 0.0),
        )
        keep_ids = {
            str(item.get("run_id", ""))
            for item in ordered[-self.archive_retention_runs:]
            if item.get("run_id")
        }

        pruned = 0
        for run in ordered:
            run_id = str(run.get("run_id", "") or "")
            if not run_id or run_id in keep_ids:
                continue
            archive_dir = Path(str(run.get("archive_dir", "") or ""))
            if archive_dir.exists():
                shutil.rmtree(archive_dir, ignore_errors=True)
            run["status"] = "pruned"
            run["restorable"] = False
            run["pruned_at"] = self._now_str()
            pruned += 1

        if pruned:
            self._write_json_atomic(_RUNS_FILE, ordered[-120:])
        return pruned

    def _mark_run_restored(self, run_id: str, restored_at: str) -> None:
        runs = self._read_json_list(_RUNS_FILE)
        for run in runs:
            if str(run.get("run_id", "")) == run_id:
                run["restored_at"] = restored_at
                run["status"] = "restored"
                run["restorable"] = False
                break
        self._write_json_atomic(_RUNS_FILE, runs[-120:])

    def _latest_restorable_run_id(self) -> str:
        runs = self._read_json_list(_RUNS_FILE)
        for run in reversed(runs):
            if run.get("status") == "distilled" and not run.get("restored_at"):
                return str(run.get("run_id", ""))
        return ""

    def _resolve_run(self, run_id: Optional[str]) -> Optional[Dict[str, Any]]:
        runs = self._read_json_list(_RUNS_FILE)
        if run_id:
            for run in runs:
                if str(run.get("run_id", "")) == run_id:
                    return run
            return None
        for run in reversed(runs):
            if run.get("status") == "distilled" and not run.get("restored_at"):
                return run
        return None

    def _restore_file(self, target_path: Path, archive_file: Path) -> int:
        tmp = target_path.with_suffix(target_path.suffix + ".restore.tmp")
        with open(tmp, "w", encoding="utf-8") as out:
            with open(archive_file, "r", encoding="utf-8", errors="replace") as handle:
                shutil.copyfileobj(handle, out)
            with open(target_path, "r", encoding="utf-8", errors="replace") as handle:
                shutil.copyfileobj(handle, out)
        restored_bytes = archive_file.stat().st_size
        os.replace(tmp, target_path)
        return int(restored_bytes)

    def _new_run_id(self) -> str:
        return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    def _empty_axis_map(self) -> Dict[str, float]:
        return {axis: 0.0 for axis in ("X", "T", "N", "B", "A")}

    def _raw_axis_counts(self, crystal: Dict[str, Any]) -> Dict[str, float]:
        counts = self._empty_axis_map()
        raw = dict(crystal.get("axis_counts", {}) or {})
        for axis in counts:
            try:
                counts[axis] = float(raw.get(axis, 0.0) or 0.0)
            except Exception:
                counts[axis] = 0.0
        if sum(counts.values()) <= 0.0:
            for axis in list(crystal.get("axes", []) or []):
                if axis in counts:
                    counts[axis] += 1.0
        return counts

    def _normalize_axis_map(self, weights: Dict[str, float]) -> Dict[str, float]:
        total = sum(max(0.0, float(v or 0.0)) for v in weights.values())
        if total <= 0.0:
            return self._empty_axis_map()
        return {
            axis: round(max(0.0, float(weights.get(axis, 0.0) or 0.0)) / total, 4)
            for axis in ("X", "T", "N", "B", "A")
        }

    def _round_axis_map(self, weights: Dict[str, float]) -> Dict[str, float]:
        return {
            axis: round(max(0.0, float(weights.get(axis, 0.0) or 0.0)), 4)
            for axis in ("X", "T", "N", "B", "A")
        }

    def _cost_weighted_axis_magnitudes(self, axis_weights: Dict[str, float]) -> Dict[str, float]:
        from aurora_internal.aurora_noncomp_registry import REGISTRY, Constraint

        axis_map = {
            "X": Constraint.X,
            "T": Constraint.T,
            "N": Constraint.N,
            "B": Constraint.B,
            "A": Constraint.A,
        }
        weighted = {}
        for axis, constraint in axis_map.items():
            weighted[axis] = float(axis_weights.get(axis, 0.0) or 0.0) * float(REGISTRY.cost(constraint).shift_cost_coeff)
        return self._round_axis_map(weighted)

    def _operator_weighted_axis_magnitudes(self, axis_weights: Dict[str, float]) -> Dict[str, float]:
        from aurora_internal.aurora_cost_diff_score import OPPOSED_OPERATOR_SCALES, TICK_PARTICIPATION_WEIGHTS
        from aurora_internal.aurora_noncomp_registry import Constraint

        axis_map = {
            "X": Constraint.X,
            "T": Constraint.T,
            "N": Constraint.N,
            "B": Constraint.B,
            "A": Constraint.A,
        }
        weighted = {}
        for axis, constraint in axis_map.items():
            participation = float(TICK_PARTICIPATION_WEIGHTS.get(constraint, 0.0) or 0.0)
            operator_scale = abs(float(OPPOSED_OPERATOR_SCALES.get(constraint, 0.0) or 0.0))
            weighted[axis] = float(axis_weights.get(axis, 0.0) or 0.0) * participation * operator_scale
        return self._round_axis_map(weighted)

    def _dominant_axis(self, constraint_axes: Dict[str, float]) -> str:
        ordered = [axis for axis in ("X", "T", "N", "B", "A")]
        return max(ordered, key=lambda axis: float(constraint_axes.get(axis, 0.0) or 0.0)) if ordered else "X"

    def _lineage_marker_payload(self, crystal: Dict[str, Any]) -> Dict[str, Any]:
        from aurora_internal.lineage_canonical import operator_action_for_axis

        raw_counts = self._raw_axis_counts(crystal)
        constraint_axes = self._normalize_axis_map(raw_counts)
        dominant_axis = self._dominant_axis(constraint_axes)
        cost_weighted_axis_magnitudes = self._cost_weighted_axis_magnitudes(raw_counts)
        operator_weighted_axis_magnitudes = self._operator_weighted_axis_magnitudes(raw_counts)
        cost_weighted_axes = self._normalize_axis_map(cost_weighted_axis_magnitudes)
        operator_weighted_axes = self._normalize_axis_map(operator_weighted_axis_magnitudes)
        return {
            "constraint_axes": constraint_axes,
            "dominant_axis": dominant_axis,
            "axis_signature": [axis for axis, value in constraint_axes.items() if float(value) > 0.0],
            "raw_axis_counts": {axis: round(value, 4) for axis, value in raw_counts.items() if value > 0.0},
            "cost_weighted_axes": cost_weighted_axes,
            "cost_weighted_axis_magnitudes": cost_weighted_axis_magnitudes,
            "cost_weight_total": round(sum(cost_weighted_axis_magnitudes.values()), 4),
            "operator_weighted_axes": operator_weighted_axes,
            "operator_weighted_axis_magnitudes": operator_weighted_axis_magnitudes,
            "operator_weight_total": round(sum(operator_weighted_axis_magnitudes.values()), 4),
            "operator_action": operator_action_for_axis(dominant_axis),
            "worth_signal": round(float(crystal.get("avg_worth", 0.0) or 0.0), 4),
            "coherence_signal": round(float(crystal.get("avg_coherence", 0.0) or 0.0), 4),
            "recurrence_count": int(crystal.get("count", 0) or 0),
            "distillation_shape": str(crystal.get("shape", "wave") or "wave"),
            "distillation_source": str(crystal.get("source", "") or ""),
        }

    def refresh_lineage_marker_values(self) -> int:
        if not _LINEAGE_FILE.exists() or not _CRYSTALS_FILE.exists():
            return 0
        try:
            data = json.loads(_LINEAGE_FILE.read_text())
        except Exception:
            return 0
        if not isinstance(data, dict):
            return 0
        events = data.get("events")
        if not isinstance(events, list):
            return 0
        crystal_index = {
            str(item.get("id")): item
            for item in self._read_json_list(_CRYSTALS_FILE)
            if isinstance(item, dict) and item.get("id")
        }
        changed = 0
        for event in events:
            if not isinstance(event, dict) or str(event.get("source", "")) != "metabolic_distiller":
                continue
            event_id = str(event.get("id", ""))
            crystal_id = event_id[:-8] if event_id.endswith(":lineage") else event_id
            crystal = crystal_index.get(crystal_id)
            if crystal is None:
                continue
            payload = self._lineage_marker_payload(crystal)
            payload["axis"] = payload["dominant_axis"]
            updated = False
            for key, value in payload.items():
                if event.get(key) != value:
                    event[key] = value
                    updated = True
            if updated:
                changed += 1
        if changed:
            data["updated_at"] = time.time()
            self._write_json_atomic(_LINEAGE_FILE, data)
        return changed

    def _merge_records(self, path: Path, records: List[Dict[str, Any]], *,
                       keep: int, sort_key: str) -> List[Dict[str, Any]]:
        existing: List[Dict[str, Any]] = self._read_json_list(path)
        merged: Dict[str, Dict[str, Any]] = {
            str(item.get("id")): item for item in existing if isinstance(item, dict) and item.get("id")
        }
        for record in records:
            rid = str(record.get("id"))
            previous = merged.get(rid, {})
            if previous:
                record["count"] = int(previous.get("count", 0) or 0) + int(record.get("count", 0) or 0)
                record["raw_bytes"] = int(previous.get("raw_bytes", 0) or 0) + int(record.get("raw_bytes", 0) or 0)
                record["first_ts"] = min(
                    float(previous.get("first_ts", 0) or 0),
                    float(record.get("first_ts", 0) or 0),
                ) or float(record.get("first_ts", 0) or 0)
                record["last_ts"] = max(
                    float(previous.get("last_ts", 0) or 0),
                    float(record.get("last_ts", 0) or 0),
                )
                prev_axis_counts = dict(previous.get("axis_counts", {}) or {})
                curr_axis_counts = dict(record.get("axis_counts", {}) or {})
                merged_axis_counts = {}
                for axis in ("X", "T", "N", "B", "A"):
                    merged_axis_counts[axis] = int(prev_axis_counts.get(axis, 0) or 0) + int(curr_axis_counts.get(axis, 0) or 0)
                record["axis_counts"] = {k: v for k, v in merged_axis_counts.items() if v > 0}
                prev_tag_counts = dict(previous.get("tag_counts", {}) or {})
                curr_tag_counts = dict(record.get("tag_counts", {}) or {})
                merged_tag_counts = {}
                for key in set(prev_tag_counts) | set(curr_tag_counts):
                    merged_tag_counts[str(key)] = int(prev_tag_counts.get(key, 0) or 0) + int(curr_tag_counts.get(key, 0) or 0)
                record["tag_counts"] = {k: v for k, v in merged_tag_counts.items() if v > 0}
                examples = list(previous.get("examples", [])) + list(record.get("examples", []))
                deduped: List[str] = []
                for example in examples:
                    if example and example not in deduped:
                        deduped.append(str(example))
                record["examples"] = deduped[:4]
            merged[rid] = record
        ordered = sorted(
            merged.values(),
            key=lambda item: float(item.get(sort_key, 0) or 0),
            reverse=True,
        )[:keep]
        self._write_json_atomic(path, ordered)
        return ordered

    def _promote_lineage(self, crystals: List[Dict[str, Any]]) -> int:
        if not _LINEAGE_FILE.exists():
            return 0
        try:
            data = json.loads(_LINEAGE_FILE.read_text())
        except Exception:
            return 0
        if not isinstance(data, dict):
            return 0
        events = data.get("events")
        if not isinstance(events, list):
            events = []
            data["events"] = events

        existing_ids = {str(evt.get("id")) for evt in events if isinstance(evt, dict)}
        promoted = 0
        crystal_index = {
            str(item.get("id")): item
            for item in self._read_json_list(_CRYSTALS_FILE)
            if isinstance(item, dict) and item.get("id")
        }
        for crystal in crystals:
            if crystal.get("id"):
                crystal_index[str(crystal.get("id"))] = crystal
        for crystal in crystals[:8]:
            if crystal.get("shape") not in {"knot", "vortex"}:
                continue
            event_id = f"{crystal['id']}:lineage"
            payload = self._lineage_marker_payload(crystal)
            if event_id in existing_ids:
                continue
            events.append({
                "timestamp": time.time(),
                "source": "metabolic_distiller",
                "kind": "coherent_structure",
                "id": event_id,
                "axis": payload["dominant_axis"],
                **payload,
                "tags": [
                    "distillation",
                    f"shape:{crystal.get('shape', 'wave')}",
                    f"count:{crystal.get('count', 0)}",
                    f"dominant_axis:{payload['dominant_axis']}",
                    f"operator_action:{payload['operator_action']}",
                ],
                "summary": f"Distilled {crystal.get('shape')} from {crystal.get('source')} with "
                           f"{crystal.get('count', 0)} recurrence(s).",
            })
            existing_ids.add(event_id)
            promoted += 1

        changed = 0
        for event in events:
            if not isinstance(event, dict) or str(event.get("source", "")) != "metabolic_distiller":
                continue
            event_id = str(event.get("id", ""))
            crystal_id = event_id[:-8] if event_id.endswith(":lineage") else event_id
            crystal = crystal_index.get(crystal_id)
            if crystal is None:
                continue
            payload = self._lineage_marker_payload(crystal)
            payload["axis"] = payload["dominant_axis"]
            for key, value in payload.items():
                if event.get(key) != value:
                    event[key] = value
                    changed += 1
            tags = list(event.get("tags", []) or [])
            wanted = [
                f"dominant_axis:{payload['dominant_axis']}",
                f"operator_action:{payload['operator_action']}",
            ]
            for item in wanted:
                if item not in tags:
                    tags.append(item)
                    changed += 1
            event["tags"] = tags

        if promoted or changed:
            data["updated_at"] = time.time()
            self._write_json_atomic(_LINEAGE_FILE, data)
        return promoted

    def _write_metrics(self, telemetry: Dict[str, Any]) -> None:
        _DISTILL_DIR.mkdir(parents=True, exist_ok=True)
        self._write_json_atomic(_METRICS_FILE, telemetry)

    def _read_json_list(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
        except Exception:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def _write_json_atomic(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(tmp, path)

    def _estimate_low_worth_density(self) -> float:
        path = self.state_dir / "pressure_experiences.jsonl"
        if not path.exists():
            return 0.0
        tail = self._tail_lines(path, 160)
        if not tail:
            return 0.0
        low = 0
        total = 0
        for line in tail:
            try:
                payload = json.loads(line)
            except Exception:
                continue
            features = self.analyzer.extract("pressure_experiences", payload)
            total += 1
            if float(features["worth"]) < 0.38:
                low += 1
        return low / max(1, total)

    def _estimate_der_load(self) -> float:
        fail_points = self.state_dir / "fail_points.json"
        if fail_points.exists():
            try:
                payload = json.loads(fail_points.read_text())
                records = payload.get("records", {})
                if isinstance(records, dict) and records:
                    severities = []
                    for item in records.values():
                        fails = float(item.get("fail_count", 0) or 0)
                        sev_sum = float(item.get("severity_sum", 0) or 0)
                        if fails > 0:
                            severities.append(min(1.0, sev_sum / fails))
                    if severities:
                        return sum(severities) / len(severities)
            except Exception:
                pass
        return self._estimate_low_worth_density()

    def _tail_lines(self, path: Path, count: int) -> List[str]:
        lines: deque[str] = deque(maxlen=count)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                lines.append(line.rstrip("\n"))
        return list(lines)

    def _in_quiet_window(self) -> bool:
        hour = _dt.datetime.now().hour
        return hour >= 22 or hour < 8

    def _human_bytes(self, value: int) -> str:
        units = ["B", "KB", "MB", "GB"]
        size = float(max(0, value))
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
            size /= 1024.0
        return f"{int(size)}B"

    def _now_str(self) -> str:
        return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_distillation_cycle(*, force: bool = False,
                           logger: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    return MetabolicDistiller(logger=logger).run(force=force)


def restore_distillation_cycle(*, run_id: Optional[str] = None,
                               logger: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    return MetabolicDistiller(logger=logger).restore(run_id=run_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aurora pressure release distillation runner")
    parser.add_argument("--force", action="store_true", help="Run even if no trigger is active")
    parser.add_argument("--status", action="store_true", help="Print trigger snapshot and exit")
    parser.add_argument("--restore", action="store_true", help="Restore the latest or specified distillation round")
    parser.add_argument("--run-id", type=str, default="", help="Specific distillation round id")
    args = parser.parse_args()

    runner = MetabolicDistiller(logger=print)
    if args.status:
        print(json.dumps(runner.should_run(force=args.force), indent=2))
        return
    if args.restore:
        print(json.dumps(runner.restore(run_id=args.run_id or None), indent=2))
        return
    print(json.dumps(runner.run(force=args.force), indent=2))


if __name__ == "__main__":
    main()
