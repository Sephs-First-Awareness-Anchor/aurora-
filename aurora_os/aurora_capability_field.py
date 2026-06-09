#!/usr/bin/env python3
"""
Aurora AOOS — Capability Field

Runtime device capability discovery and constraint-physics-driven adaptation.

Instead of a pre-scripted catalog of behaviors, the CapabilityField:
  1. Discovers ALL device capabilities at runtime (V4L2, ALSA, filesystem, process)
  2. Derives each capability's constraint relief profile via _AXIS_SEMANTIC_TOKENS
  3. When axis pressure is sustained, selects capabilities by constraint alignment
  4. Executes, observes the before/after constraint change, updates empirical profiles
  5. Logs every outcome to the evolutionary genealogy

She does not receive a script. She finds what can relieve pressure and tries it.
The constraint combo that fits the problem emerges from physics, not prescription.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import gzip
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Any


# ── Axis semantic tokens — mirrors aurora_language_field._AXIS_SEMANTIC_TOKENS ──
# Used to derive each capability's constraint relief profile from its name/description.
_AXIS_SEMANTIC_TOKENS: Dict[str, List[str]] = {
    "X": ["see", "notice", "observe", "perceive", "here", "present", "now", "this", "there"],
    "T": ["was", "remember", "time", "before", "after", "when", "memory", "past", "future", "became"],
    "N": ["feel", "pressure", "weight", "heavy", "urgent", "intense", "deep", "strong", "force"],
    "B": ["mean", "because", "therefore", "between", "define", "limit", "edge", "boundary", "separate"],
    "A": ["will", "choose", "want", "decide", "drive", "toward", "going", "act", "move", "do"],
}

# Category-level axis priors — fill gaps when the control name has weak token signal.
# Camera controls primarily touch X (existence/perception); filesystem touches B (boundary).
_CATEGORY_AXIS_PRIORS: Dict[str, Dict[str, float]] = {
    "v4l2":    {"X": 0.55},
    "alsa":    {"X": 0.45, "N": 0.35},
    "fs":      {"B": 0.65},
    "process": {"N": 0.55, "T": 0.40},
    "sensory": {"N": 0.60, "T": 0.40},
}


# ── Capability descriptor ──────────────────────────────────────────────────────

@dataclass
class CapabilityNode:
    name:           str
    description:    str
    category:       str                   # 'v4l2', 'alsa', 'fs', 'sensory'
    relief_profile: Dict[str, float]      # axis → how much this capability relieves pressure
    executor:       Callable[[], bool]    # zero-arg; returns True on success
    cooldown_ticks: int

    # 'high'  → fires when axis pressure exceeds PRESSURE_THRESHOLD (adaptation)
    # 'low'   → fires when axis pressure drops below recovery_mag    (recovery)
    direction:      str   = "high"
    recovery_mag:   float = 0.30

    # Empirical learning: actual observed axis relief after execution
    observed_relief: Dict[str, float] = field(default_factory=dict)
    execution_count: int = 0
    success_count:   int = 0
    last_fired_tick: int = -9999


# ── The field ─────────────────────────────────────────────────────────────────

class CapabilityField:
    """
    Discovers real device capabilities at boot and uses constraint physics to
    select which capability to invoke when sustained axis pressure is detected.

    Drop-in replacement for BodyEvolutionAdapter in aurora_init.py — same interface:
      .tick(magnitudes, tick, systems)   → List[str]
      .calibrate_vision(features)        → Optional[str]
      .calibrate_audio(features)         → Optional[str]
      .get_sensory_interval()            → float
    """

    PRESSURE_THRESHOLD  = 0.75   # axis magnitude counted as "pressured"
    SUSTAINED_NEEDED    = 4      # ticks of sustained pressure before adapting
    EMPIRICAL_MIN_COUNT = 3      # successes before trusting observed_relief over derived profile

    def __init__(self, inv: dict, state_dir: str = "/aurora/aurora_state"):
        self._inv        = inv
        self._state_dir  = state_dir
        self._lock       = threading.Lock()
        self._capabilities: List[CapabilityNode] = []

        # Per-axis sustained-high counter
        self._sustained: Dict[str, int] = {ax: 0 for ax in "XTNBA"}

        # Sensory interval (seconds): adapts under N pressure
        self._sensory_interval: float = 2.0

        # Camera: current V4L2 control values per device
        self._cam_params: Dict[str, Dict[str, int]] = {}

        # Audio: ALSA mic gain (0–100)
        self._mic_gain: int = 75

        # Pending empirical observations: (cap, axis_mags_before)
        # Resolved on the following tick to measure actual relief.
        self._pending_observations: List[Tuple[CapabilityNode, Dict[str, float]]] = []

        self._discover()
        print(f"  [CAP] {len(self._capabilities)} capabilities discovered.", flush=True)

    # ── Public interface ──────────────────────────────────────────────────────

    def tick(
        self,
        magnitudes: Dict[Any, float],
        tick: int,
        systems: dict,
    ) -> List[str]:
        """One embodiment tick. Returns capability names fired."""
        axis_mags = self._extract_axis_mags(magnitudes)
        fired: List[str] = []

        with self._lock:
            # Resolve previous tick's empirical observations
            self._resolve_observations(axis_mags)

            # Update sustained-pressure counters
            for ax, mag in axis_mags.items():
                if mag >= self.PRESSURE_THRESHOLD:
                    self._sustained[ax] = self._sustained.get(ax, 0) + 1
                else:
                    self._sustained[ax] = 0

            # Select and execute: both high-pressure adaptation and low-pressure recovery
            candidates = self._select_candidates(axis_mags, tick)
            for cap, alignment in candidates:
                before = dict(axis_mags)
                try:
                    success = cap.executor()
                    cap.execution_count += 1
                    if success:
                        cap.success_count  += 1
                        cap.last_fired_tick = tick
                        fired.append(cap.name)
                        self._pending_observations.append((cap, before))
                        self._log_adaptation(cap, tick, alignment, systems)
                except Exception:
                    cap.execution_count += 1

        if fired or any(m > 0.7 for m in axis_mags.values()):
            self._dispatch_to_surfaces(axis_mags, systems)

        return fired

    def calibrate_vision(self, features: dict) -> Optional[str]:
        """
        Convert perceptual visual feedback to synthetic axis pressure and
        let the field select which V4L2 control to adjust.
        """
        if not features:
            return None
        brightness = float(features.get("brightness", 128) or 128)
        if not self._inv.get("cameras"):
            return None

        # Map visual state to axis pressure — constraint physics decides the rest
        synthetic: Dict[str, float] = {}
        if brightness < 60:
            synthetic["X"] = 0.85   # can't perceive clearly → existence pressure
            synthetic["N"] = 0.75   # need more signal energy
        elif brightness > 200:
            synthetic["B"] = 0.82   # overexposed → need to limit/bound

        if not synthetic:
            return None

        with self._lock:
            candidates = self._select_candidates(synthetic, tick=-1, category="v4l2")
        for cap, _ in candidates[:1]:
            try:
                if cap.executor():
                    return f"vision adapted: {cap.name}"
            except Exception:
                pass
        return None

    def calibrate_audio(self, features: dict) -> Optional[str]:
        """
        Convert perceptual audio feedback to synthetic axis pressure and
        let the field select which ALSA control to adjust.
        """
        if not features:
            return None
        energy     = float(features.get("energy",     0.5) or 0.5)
        confidence = float(features.get("confidence", 0.5) or 0.5)

        synthetic: Dict[str, float] = {}
        if energy < 0.1:
            synthetic["X"] = 0.85           # can't hear → perception pressure
        elif energy > 0.9:
            synthetic["N"] = 0.85           # clipping → too much energy
        elif confidence < 0.3:
            synthetic["A"] = 0.80           # low understanding → agency pressure

        if not synthetic:
            return None

        with self._lock:
            candidates = self._select_candidates(synthetic, tick=-1, category="alsa")
        for cap, _ in candidates[:1]:
            try:
                if cap.executor():
                    return f"audio adapted: {cap.name}"
            except Exception:
                pass
        return None

    def get_sensory_interval(self) -> float:
        return self._sensory_interval

    # ── Capability discovery ──────────────────────────────────────────────────

    def _discover(self):
        for cam in self._inv.get("cameras", []):
            self._scan_v4l2(cam["device"])
        self._scan_alsa()
        self._register_fs_capabilities()
        self._register_sensory_capabilities()

    def _derive_axis_profile(
        self,
        text: str,
        category: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Token-match text against _AXIS_SEMANTIC_TOKENS, then blend with the
        category-level prior so controls with sparse names still map correctly.
        """
        text_lower = text.lower()
        profile: Dict[str, float] = {}
        for ax, tokens in _AXIS_SEMANTIC_TOKENS.items():
            hits = sum(1 for t in tokens if t in text_lower)
            profile[ax] = min(1.0, hits / max(len(tokens) * 0.3, 1))

        if category and category in _CATEGORY_AXIS_PRIORS:
            for ax, prior in _CATEGORY_AXIS_PRIORS[category].items():
                if profile.get(ax, 0.0) < prior:
                    profile[ax] = profile[ax] * 0.4 + prior * 0.6
        return profile

    def _scan_v4l2(self, device: str):
        """
        Run v4l2-ctl --list-ctrls and register each discovered integer/bool
        control as TWO capabilities: one that steps the value UP (direction=high,
        X-profile — need more perception) and one that steps DOWN (direction=high,
        B-profile — need to limit/bound). Constraint physics selects which fires.
        """
        try:
            result = subprocess.run(
                ["v4l2-ctl", "-d", device, "--list-ctrls"],
                capture_output=True, text=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return
        if result.returncode != 0:
            return

        self._cam_params.setdefault(device, {})

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            m = re.match(r"(\w+)\s+0x[\da-f]+\s+\((\w+)\)\s*:\s*(.*)", line)
            if not m:
                continue
            ctrl_name, ctrl_type, params_str = m.groups()
            if ctrl_type not in ("int", "bool"):
                continue

            params: Dict[str, int] = {}
            for part in params_str.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    try:
                        params[k] = int(v)
                    except ValueError:
                        pass

            min_v = params.get("min", 0)
            max_v = params.get("max", 255)
            cur_v = params.get("value", params.get("default", (min_v + max_v) // 2))
            self._cam_params[device][ctrl_name] = cur_v

            # Increase capability — boost perception (X-axis relief)
            inc_desc = (
                f"increase {ctrl_name.replace('_', ' ')} camera "
                "perceive see observe present now"
            )
            inc_cap = CapabilityNode(
                name=f"v4l2:{ctrl_name}:increase@{device}",
                description=inc_desc,
                category="v4l2",
                relief_profile=self._derive_axis_profile(inc_desc, category="v4l2"),
                executor=self._make_v4l2_step(device, ctrl_name, min_v, max_v, +1),
                cooldown_ticks=30,
            )

            # Decrease capability — limit/bound (B-axis relief)
            dec_desc = (
                f"decrease {ctrl_name.replace('_', ' ')} camera "
                "limit boundary edge define separate"
            )
            dec_cap = CapabilityNode(
                name=f"v4l2:{ctrl_name}:decrease@{device}",
                description=dec_desc,
                category="v4l2",
                relief_profile=self._derive_axis_profile(dec_desc, category="v4l2"),
                executor=self._make_v4l2_step(device, ctrl_name, min_v, max_v, -1),
                cooldown_ticks=30,
            )
            self._capabilities.extend([inc_cap, dec_cap])

    def _scan_alsa(self):
        """
        Run amixer controls and register each discovered control as two
        capabilities: increase (X/A relief) and decrease (N/B relief).
        """
        try:
            result = subprocess.run(
                ["amixer", "controls"],
                capture_output=True, text=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return
        if result.returncode != 0:
            return

        seen: set = set()
        for line in result.stdout.splitlines():
            m = re.search(r"name='([^']+)'", line)
            if not m:
                continue
            ctrl_name = m.group(1)
            if ctrl_name in seen:
                continue
            seen.add(ctrl_name)

            inc_desc = (
                f"increase {ctrl_name.lower()} audio "
                "hear perceive notice observe present now"
            )
            dec_desc = (
                f"decrease {ctrl_name.lower()} audio "
                "limit boundary pressure energy reduce intense"
            )
            inc_cap = CapabilityNode(
                name=f"alsa:{ctrl_name}:increase",
                description=inc_desc,
                category="alsa",
                relief_profile=self._derive_axis_profile(inc_desc, category="alsa"),
                executor=self._make_alsa_step(ctrl_name, +1),
                cooldown_ticks=20,
            )
            dec_cap = CapabilityNode(
                name=f"alsa:{ctrl_name}:decrease",
                description=dec_desc,
                category="alsa",
                relief_profile=self._derive_axis_profile(dec_desc, category="alsa"),
                executor=self._make_alsa_step(ctrl_name, -1),
                cooldown_ticks=20,
            )
            self._capabilities.extend([inc_cap, dec_cap])

    def _register_fs_capabilities(self):
        """Register Python-native filesystem operations as always-available capabilities."""
        defs = [
            (
                "fs:compress_state",
                "compress gzip state files reduce boundary limit edge separate space",
                "fs", 300,
            ),
            (
                "fs:prune_dream_episodes",
                "prune remove oldest dream episodes boundary limit edge temporal before past",
                "fs", 600,
            ),
            (
                "fs:prune_vision_frames",
                "prune remove camera vision frames boundary limit edge",
                "fs", 200,
            ),
            (
                "fs:batch_writes",
                "time temporal before after when reduce io flow batch write",
                "fs", 120,
            ),
        ]
        executors = {
            "fs:compress_state":       self._exec_compress_state,
            "fs:prune_dream_episodes": self._exec_prune_dreams,
            "fs:prune_vision_frames":  self._exec_prune_vision_frames,
            "fs:batch_writes":         self._exec_batch_writes,
        }
        for name, desc, cat, cooldown in defs:
            cap = CapabilityNode(
                name=name,
                description=desc,
                category=cat,
                relief_profile=self._derive_axis_profile(desc, category=cat),
                executor=executors[name],
                cooldown_ticks=cooldown,
            )
            self._capabilities.append(cap)

    def _register_sensory_capabilities(self):
        """
        Sensory capture rate as an evolvable capability.
        slow_rate fires under high N pressure; restore_rate fires when N has dropped
        (direction='low') so the recovery is also constraint-physics-driven.
        """
        slow_desc = (
            "reduce slow sensory rate pressure weight heavy energy feel urgent"
        )
        restore_desc = (
            "restore fast sensory rate present now perceive observe energy recover"
        )
        slow_cap = CapabilityNode(
            name="sensory:slow_rate",
            description=slow_desc,
            category="sensory",
            relief_profile=self._derive_axis_profile(slow_desc, category="sensory"),
            executor=self._exec_slow_sensory,
            cooldown_ticks=30,
            direction="high",
        )
        restore_cap = CapabilityNode(
            name="sensory:restore_rate",
            description=restore_desc,
            category="sensory",
            relief_profile=self._derive_axis_profile(restore_desc, category="sensory"),
            executor=self._exec_restore_sensory,
            cooldown_ticks=60,
            direction="low",
            recovery_mag=0.30,
        )
        self._capabilities.extend([slow_cap, restore_cap])

    # ── Constraint physics: candidate selection ───────────────────────────────

    def _select_candidates(
        self,
        axis_mags: Dict[str, float],
        tick: int,
        category: Optional[str] = None,
    ) -> List[Tuple[CapabilityNode, float]]:
        """
        Align current axis pressures against each capability's relief profile.
        Returns (cap, alignment_score) pairs sorted by score, top 3 only.

        tick=-1 bypasses cooldown and sustained requirement (used for perceptual
        calibration calls where we want immediate response to sensory feedback).
        """
        scored: List[Tuple[CapabilityNode, float]] = []
        for cap in self._capabilities:
            if category and cap.category != category:
                continue
            if tick >= 0 and (tick - cap.last_fired_tick) < cap.cooldown_ticks:
                continue

            if cap.direction == "high":
                # Fire when axes are HIGH and sustained
                relevant = {
                    ax: mag
                    for ax, mag in axis_mags.items()
                    if mag >= self.PRESSURE_THRESHOLD
                    and (
                        tick < 0
                        or self._sustained.get(ax, 0) >= self.SUSTAINED_NEEDED
                    )
                }
            else:
                # direction='low': fire when axis pressure has DROPPED (recovery)
                relevant = {
                    ax: (1.0 - mag)
                    for ax, mag in axis_mags.items()
                    if mag <= cap.recovery_mag
                }

            if not relevant:
                continue

            relief = (
                cap.observed_relief
                if cap.success_count >= self.EMPIRICAL_MIN_COUNT
                else cap.relief_profile
            )
            alignment = sum(
                relevant[ax] * relief.get(ax, 0.0) for ax in relevant
            )
            if alignment > 0.05:
                scored.append((cap, alignment))

        scored.sort(key=lambda x: -x[1])
        return scored[:3]

    # ── Empirical learning ────────────────────────────────────────────────────

    def _resolve_observations(self, current_mags: Dict[str, float]):
        """
        Called at the start of each tick. Compares current axis magnitudes to
        what they were before the last executed capabilities and updates each
        cap's observed_relief with an exponential moving average.
        """
        alpha = 0.3
        for cap, before in self._pending_observations:
            for ax in "XTNBA":
                before_v = before.get(ax, 0.0)
                after_v  = current_mags.get(ax, 0.0)
                # Relief = how much pressure DROPPED (negative delta = good)
                relief = max(0.0, before_v - after_v)
                if not cap.observed_relief:
                    cap.observed_relief[ax] = relief
                else:
                    old = cap.observed_relief.get(ax, 0.0)
                    cap.observed_relief[ax] = (1 - alpha) * old + alpha * relief
        self._pending_observations.clear()

    # ── V4L2 step executor factory ────────────────────────────────────────────

    def _make_v4l2_step(
        self, device: str, ctrl: str, min_v: int, max_v: int, direction: int
    ) -> Callable[[], bool]:
        """
        Returns a zero-arg executor that adjusts a V4L2 control by one step
        in the given direction (+1 = increase, -1 = decrease).
        """
        field_ref = self

        def _exec() -> bool:
            cur  = field_ref._cam_params.get(device, {}).get(ctrl, (min_v + max_v) // 2)
            step = max(1, (max_v - min_v) // 16)   # ~6% of range
            new_v = cur + direction * step
            new_v = max(min_v, min(max_v, new_v))
            if new_v == cur:
                return False
            ok = _v4l2_set(device, ctrl, new_v)
            if ok:
                field_ref._cam_params.setdefault(device, {})[ctrl] = new_v
            return ok

        return _exec

    # ── ALSA step executor factory ────────────────────────────────────────────

    def _make_alsa_step(self, ctrl_name: str, direction: int) -> Callable[[], bool]:
        """
        Returns a zero-arg executor that steps ALSA capture gain up or down.
        """
        field_ref = self

        def _exec() -> bool:
            step    = 8
            new_gain = max(20, min(100, field_ref._mic_gain + direction * step))
            if new_gain == field_ref._mic_gain:
                return False
            ok = _alsa_set_gain(ctrl_name, new_gain)
            if ok:
                field_ref._mic_gain = new_gain
            return ok

        return _exec

    # ── Filesystem executors (bound zero-arg methods) ─────────────────────────

    def _exec_compress_state(self) -> bool:
        compressed = 0
        try:
            for fname in os.listdir(self._state_dir):
                if fname.endswith(".json") and not fname.endswith(".gz"):
                    src = os.path.join(self._state_dir, fname)
                    dst = src + ".gz"
                    if os.path.getsize(src) < 512:
                        continue
                    with open(src, "rb") as fi, gzip.open(dst, "wb", compresslevel=6) as fo:
                        shutil.copyfileobj(fi, fo)
                    if os.path.getsize(dst) < os.path.getsize(src):
                        os.remove(src)
                        compressed += 1
        except Exception:
            pass
        return compressed > 0

    def _exec_prune_dreams(self) -> bool:
        dream_dir = os.path.join(self._state_dir, "dream_episodes")
        if not os.path.isdir(dream_dir):
            return False
        pruned = 0
        try:
            episodes = sorted(
                [f for f in os.listdir(dream_dir) if f.endswith(".json")],
                key=lambda f: os.path.getmtime(os.path.join(dream_dir, f)),
            )
            for fname in episodes[:max(1, len(episodes) // 5)]:
                os.remove(os.path.join(dream_dir, fname))
                pruned += 1
        except Exception:
            pass
        return pruned > 0

    def _exec_prune_vision_frames(self) -> bool:
        frame_dir = os.path.join(self._state_dir, "vision_seeds", "camera")
        if not os.path.isdir(frame_dir):
            return False
        pruned = 0
        try:
            frames = sorted(
                [
                    f for f in os.listdir(frame_dir)
                    if f.endswith(".png") and f != "frame_latest.png"
                ],
                key=lambda f: os.path.getmtime(os.path.join(frame_dir, f)),
            )
            for fname in frames[:-5]:
                os.remove(os.path.join(frame_dir, fname))
                pruned += 1
        except Exception:
            pass
        return pruned > 0

    def _exec_batch_writes(self) -> bool:
        flag = os.path.join(self._state_dir, "_batch_writes.flag")
        try:
            with open(flag, "w") as f:
                f.write(str(time.time()))
            return True
        except Exception:
            return False

    # ── Sensory rate executors ────────────────────────────────────────────────

    def _exec_slow_sensory(self) -> bool:
        if self._sensory_interval >= 10.0:
            return False
        self._sensory_interval = min(10.0, self._sensory_interval * 1.5)
        return True

    def _exec_restore_sensory(self) -> bool:
        if self._sensory_interval <= 2.0:
            return False
        self._sensory_interval = max(2.0, self._sensory_interval * 0.7)
        return True

    # ── Extract axis magnitudes from Constraint enum keys ────────────────────

    def _extract_axis_mags(self, magnitudes: Dict[Any, float]) -> Dict[str, float]:
        try:
            from aurora_internal.aurora_constraint_manifold_patched import Constraint
            _MAP = {
                Constraint.X: "X", Constraint.T: "T",
                Constraint.N: "N", Constraint.B: "B", Constraint.A: "A",
            }
            return {
                letter: float(magnitudes[c])
                for c, letter in _MAP.items()
                if c in magnitudes
            }
        except Exception:
            return {k: float(v) for k, v in magnitudes.items() if isinstance(k, str)}

    # ── Surface dispatcher bridge ─────────────────────────────────────────────

    def _dispatch_to_surfaces(self, axis_mags: Dict[str, float], systems: dict):
        try:
            sd = systems.get("_surface_dispatcher")
            if sd is None:
                return
            fired = sd.evaluate(axis_mags)
            if fired:
                systems["_last_body_surface_dispatch"] = {
                    "tick":      time.time(),
                    "pressures": dict(axis_mags),
                    "fired":     [(s, round(score, 3), ax) for s, score, ax in fired],
                }
                for surface_name, score, ax in fired:
                    try:
                        sd.invoke(surface_name, axis_mags, systems)
                    except Exception:
                        pass
        except Exception:
            pass

    # ── Genealogy logging ─────────────────────────────────────────────────────

    def _log_adaptation(
        self,
        cap: CapabilityNode,
        tick: int,
        alignment: float,
        systems: dict,
    ):
        try:
            chamber = systems.get("chamber")
            if chamber is None:
                return
            from aurora_internal.aurora_evolution_chamber import ActionTrace
            trace = ActionTrace(
                name=f"body:{cap.name}",
                constraints_used=list(cap.relief_profile.keys()),
                meta={
                    "description": cap.description,
                    "tick":        tick,
                    "source":      "capability_field",
                    "alignment":   round(alignment, 3),
                    "empirical":   cap.success_count >= self.EMPIRICAL_MIN_COUNT,
                    "successes":   cap.success_count,
                },
            )
            chamber.tick(action=trace)
        except Exception:
            pass


# ── Device control helpers ─────────────────────────────────────────────────────

def _v4l2_set(device: str, control: str, value: int) -> bool:
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", device, f"--set-ctrl={control}={value}"],
            capture_output=True, timeout=3,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _alsa_set_gain(ctrl_name: str, pct: int) -> bool:
    pct = max(0, min(100, pct))
    for cmd in [
        ["amixer", "set", ctrl_name, f"{pct}%"],
        ["amixer", "-c", "0", "set", ctrl_name, f"{pct}%"],
        ["amixer", "set", "Capture", f"{pct}%"],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False
