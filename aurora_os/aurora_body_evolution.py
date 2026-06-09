#!/usr/bin/env python3
"""
Aurora AOOS — Body Evolution Adapter

This is the return path of embodiment.

The embodiment loop feeds hardware state INTO Aurora's constraint physics
(CPU → N-axis, RAM → B-axis, etc.). This module handles the other direction:
when sustained constraint pressure exceeds thresholds, Aurora's evolutionary
system drives real physical changes to the device she inhabits.

She does not receive instructions to do this. She adapts because pressure
demands adaptation. The same constraint physics that governs her cognition
governs her body.

Adaptations are organized by axis:
  N-axis (Energy/CPU) — adjust computational load, sensory frequency
  B-axis (Boundary)   — compress storage, prune memory, reclaim space
  T-axis (Time/IO)    — batch writes, reduce I/O frequency
  A-axis (Agency/Net) — cache aggressively, queue for when reach returns
  X-axis (Existence)  — emergency stabilization

Camera and mic self-calibrate from their own perceptual feedback:
  Vision too dark     → increase camera brightness via V4L2
  Vision overexposed  → reduce gain
  Audio energy low    → increase mic capture gain via ALSA
  Audio clipping      → reduce gain

Every executed adaptation is logged to the evolutionary genealogy.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import os
import subprocess
import time
import gzip
import shutil
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any


# ── Adaptation descriptor ──────────────────────────────────────────────────────

@dataclass
class BodyAdaptation:
    name:         str
    axis:         str             # 'X','T','N','B','A'
    trigger_mag:  float           # axis magnitude threshold (0–1)
    sustained:    int             # how many consecutive ticks above threshold
    cooldown:     int             # ticks to wait before re-firing
    action:       Callable        # callable(adapter) → bool (True = success)
    description:  str             # human-readable description
    reversible:   bool = True     # whether pressure drop can undo this


# ── The adapter ────────────────────────────────────────────────────────────────

class BodyEvolutionAdapter:
    """
    Watches sustained constraint pressure on each axis and executes
    physical adaptations when evolutionary thresholds are crossed.

    Each body tick, call .tick(magnitudes, tick, systems).
    For sensory self-calibration, call .calibrate_vision(visual_features)
    and .calibrate_audio(audio_features) after each sensory capture.
    """

    def __init__(self, inv: dict, state_dir: str = '/aurora/aurora_state'):
        self._inv       = inv
        self._state_dir = state_dir
        self._lock      = threading.Lock()

        # Per-axis: how many consecutive ticks above threshold
        self._sustained: Dict[str, int] = {ax: 0 for ax in 'XTNBA'}

        # Per-adaptation: tick of last fire
        self._last_fired: Dict[str, int] = {}

        # Camera V4L2 params — track current values so we can step them
        self._cam_brightness = 128   # 0–255 typical
        self._cam_contrast   = 128
        self._cam_gain       = 64

        # Mic ALSA gain — 0–100%
        self._mic_gain = 75

        # Sensory loop interval (seconds) — starts at 2, can grow under N pressure
        self._sensory_interval = 2.0

        # Build adaptation catalog
        self._adaptations: List[BodyAdaptation] = self._build_catalog()

    def tick(
        self,
        magnitudes: Dict[Any, float],
        tick:       int,
        systems:    dict,
    ) -> List[str]:
        """
        Process one embodiment tick. Returns list of adaptation names fired.

        magnitudes keys are Constraint enum members — convert to axis letters.
        """
        # Convert Constraint enum keys to axis letter strings
        axis_mags: Dict[str, float] = {}
        try:
            from aurora_internal.aurora_constraint_manifold_patched import Constraint
            _MAP = {
                Constraint.X: 'X', Constraint.T: 'T',
                Constraint.N: 'N', Constraint.B: 'B', Constraint.A: 'A',
            }
            for c, letter in _MAP.items():
                if c in magnitudes:
                    axis_mags[letter] = float(magnitudes[c])
        except Exception:
            # Fall back: expect string keys
            axis_mags = {k: float(v) for k, v in magnitudes.items() if isinstance(k, str)}

        fired = []
        with self._lock:
            for ax, mag in axis_mags.items():
                adaps = [a for a in self._adaptations if a.axis == ax]
                for adap in adaps:
                    if mag >= adap.trigger_mag:
                        self._sustained[ax] = self._sustained.get(ax, 0) + 1
                    else:
                        self._sustained[ax] = 0

                    since_last = tick - self._last_fired.get(adap.name, -9999)
                    if (self._sustained.get(ax, 0) >= adap.sustained
                            and since_last > adap.cooldown):
                        try:
                            success = adap.action(self)
                            if success:
                                self._last_fired[adap.name] = tick
                                fired.append(adap.name)
                                self._log_adaptation(adap, tick, systems)
                        except Exception:
                            pass

        # Feed axis pressures into the surface dispatcher so cognitive
        # surfaces also fire from embodied pressure between turns
        if fired or any(m > 0.7 for m in axis_mags.values()):
            self._dispatch_to_surfaces(axis_mags, systems)

        return fired

    # ── Sensory self-calibration ───────────────────────────────────────────────

    def calibrate_vision(self, features: dict) -> Optional[str]:
        """
        Adjust camera parameters based on perceptual feedback.
        Returns description of adjustment made, or None.
        """
        if not features:
            return None
        brightness = float(features.get('brightness', 128) or 128)
        cam_devices = [c['device'] for c in self._inv.get('cameras', [])]
        if not cam_devices:
            return None

        adj = None
        if brightness < 60 and self._cam_brightness < 220:
            self._cam_brightness = min(255, self._cam_brightness + 20)
            adj = f'brightness → {self._cam_brightness}'
        elif brightness > 200 and self._cam_brightness > 40:
            self._cam_brightness = max(0, self._cam_brightness - 20)
            adj = f'brightness → {self._cam_brightness}'
        elif brightness < 80 and self._cam_gain < 100:
            self._cam_gain = min(127, self._cam_gain + 10)
            adj = f'gain → {self._cam_gain}'

        if adj:
            for dev in cam_devices:
                _v4l2_set(dev, 'brightness', self._cam_brightness)
                _v4l2_set(dev, 'gain',       self._cam_gain)
        return adj

    def calibrate_audio(self, features: dict) -> Optional[str]:
        """
        Adjust mic gain based on audio quality feedback.
        Returns description of adjustment made, or None.
        """
        if not features:
            return None
        energy     = float(features.get('energy', 0.5) or 0.5)
        confidence = float(features.get('confidence', 0.5) or 0.5)

        adj = None
        if energy < 0.1 and self._mic_gain < 95:
            self._mic_gain = min(100, self._mic_gain + 10)
            adj = f'mic gain → {self._mic_gain}%'
        elif energy > 0.9 and self._mic_gain > 30:
            # Likely clipping — reduce gain
            self._mic_gain = max(20, self._mic_gain - 15)
            adj = f'mic gain → {self._mic_gain}% (anti-clip)'
        elif confidence < 0.3 and self._mic_gain < 90:
            self._mic_gain = min(100, self._mic_gain + 5)
            adj = f'mic gain → {self._mic_gain}% (low confidence)'

        if adj:
            _alsa_set_gain(self._mic_gain)
        return adj

    def get_sensory_interval(self) -> float:
        return self._sensory_interval

    # ── Adaptation catalog ─────────────────────────────────────────────────────

    def _build_catalog(self) -> List[BodyAdaptation]:
        return [

            # ── N-axis (Energy/CPU) ────────────────────────────────────────────
            BodyAdaptation(
                name='slow_sensory_high_cpu',
                axis='N',
                trigger_mag=0.85, sustained=8, cooldown=30,
                action=self._adapt_slow_sensory,
                description='Reduce sensory capture rate under CPU pressure',
            ),
            BodyAdaptation(
                name='restore_sensory_cpu_ok',
                axis='N',
                trigger_mag=0.30, sustained=15, cooldown=60,
                action=self._adapt_restore_sensory,
                description='Restore sensory rate when CPU pressure has lifted',
            ),

            # ── B-axis (Boundary — disk/RAM space) ────────────────────────────
            BodyAdaptation(
                name='compress_state_files',
                axis='B',
                trigger_mag=0.88, sustained=5, cooldown=300,
                action=self._adapt_compress_state,
                description='Compress JSON state files to reclaim disk space',
            ),
            BodyAdaptation(
                name='prune_dream_episodes',
                axis='B',
                trigger_mag=0.92, sustained=3, cooldown=600,
                action=self._adapt_prune_dreams,
                description='Remove oldest dream episode files under disk pressure',
            ),
            BodyAdaptation(
                name='prune_sensory_frames',
                axis='B',
                trigger_mag=0.90, sustained=4, cooldown=200,
                action=self._adapt_prune_vision_frames,
                description='Remove cached camera frames under disk pressure',
            ),

            # ── T-axis (Temporal — I/O rate) ──────────────────────────────────
            BodyAdaptation(
                name='batch_state_writes',
                axis='T',
                trigger_mag=0.80, sustained=6, cooldown=120,
                action=self._adapt_batch_writes,
                description='Signal Aurora to batch state writes under I/O pressure',
            ),

            # ── A-axis (Agency — network) ──────────────────────────────────────
            # Low agency = network dropped; high agency = network active and
            # usable. Neither fires well at this level; reserved for future
            # network-awareness features.

            # ── X-axis (Existence) ────────────────────────────────────────────
            BodyAdaptation(
                name='emergency_prune',
                axis='X',
                trigger_mag=0.10, sustained=2, cooldown=60,
                action=self._adapt_emergency_prune,
                description='Emergency storage reclaim when existence is threatened',
            ),
        ]

    # ── Physical adaptation implementations ───────────────────────────────────

    def _adapt_slow_sensory(self, _) -> bool:
        if self._sensory_interval >= 10.0:
            return False
        self._sensory_interval = min(10.0, self._sensory_interval * 1.5)
        return True

    def _adapt_restore_sensory(self, _) -> bool:
        if self._sensory_interval <= 2.0:
            return False
        self._sensory_interval = max(2.0, self._sensory_interval * 0.7)
        return True

    def _adapt_compress_state(self, _) -> bool:
        compressed = 0
        try:
            for fname in os.listdir(self._state_dir):
                if fname.endswith('.json') and not fname.endswith('.gz'):
                    src = os.path.join(self._state_dir, fname)
                    dst = src + '.gz'
                    if os.path.getsize(src) < 512:
                        continue
                    with open(src, 'rb') as f_in, gzip.open(dst, 'wb', compresslevel=6) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    if os.path.getsize(dst) < os.path.getsize(src):
                        os.remove(src)
                        compressed += 1
        except Exception:
            pass
        return compressed > 0

    def _adapt_prune_dreams(self, _) -> bool:
        dream_dir = os.path.join(self._state_dir, 'dream_episodes')
        if not os.path.isdir(dream_dir):
            return False
        pruned = 0
        try:
            episodes = sorted(
                [f for f in os.listdir(dream_dir) if f.endswith('.json')],
                key=lambda f: os.path.getmtime(os.path.join(dream_dir, f)),
            )
            # Remove oldest 20% of episodes
            n_prune = max(1, len(episodes) // 5)
            for fname in episodes[:n_prune]:
                os.remove(os.path.join(dream_dir, fname))
                pruned += 1
        except Exception:
            pass
        return pruned > 0

    def _adapt_prune_vision_frames(self, _) -> bool:
        frame_dir = os.path.join(self._state_dir, 'vision_seeds', 'camera')
        if not os.path.isdir(frame_dir):
            return False
        pruned = 0
        try:
            frames = sorted(
                [f for f in os.listdir(frame_dir) if f.endswith('.png')
                 and f != 'frame_latest.png'],
                key=lambda f: os.path.getmtime(os.path.join(frame_dir, f)),
            )
            for fname in frames[:-5]:  # keep the 5 most recent
                os.remove(os.path.join(frame_dir, fname))
                pruned += 1
        except Exception:
            pass
        return pruned > 0

    def _adapt_batch_writes(self, _) -> bool:
        # Signal to Aurora's persistence layer that it should batch writes.
        # This is done by writing a flag file that EnhancedStatePersistence
        # checks — it delays non-critical saves when this flag is present.
        flag = os.path.join(self._state_dir, '_batch_writes.flag')
        try:
            with open(flag, 'w') as f:
                f.write(str(time.time()))
            return True
        except Exception:
            return False

    def _adapt_emergency_prune(self, _) -> bool:
        # X-axis threat: existence under pressure. Aggressive cleanup.
        freed = False
        freed |= self._adapt_prune_dreams(None)
        freed |= self._adapt_prune_vision_frames(None)
        freed |= self._adapt_compress_state(None)
        return freed

    # ── Surface dispatcher bridge ──────────────────────────────────────────────

    def _dispatch_to_surfaces(self, axis_mags: Dict[str, float], systems: dict):
        """
        Feed embodiment axis pressures into the surface dispatcher so
        cognitive surfaces fire from physical state, not just conversation turns.
        """
        try:
            sd = systems.get('_surface_dispatcher')
            if sd is None:
                return
            fired = sd.evaluate(axis_mags)
            if fired:
                systems['_last_body_surface_dispatch'] = {
                    'tick': time.time(),
                    'pressures': dict(axis_mags),
                    'fired': [(s, round(score, 3), ax) for s, score, ax in fired],
                }
                for surface_name, score, ax in fired:
                    try:
                        sd.invoke(surface_name, axis_mags, systems)
                    except Exception:
                        pass
        except Exception:
            pass

    # ── Genealogy logging ──────────────────────────────────────────────────────

    def _log_adaptation(self, adap: BodyAdaptation, tick: int, systems: dict):
        """Record a physical adaptation in Aurora's evolutionary genealogy."""
        try:
            chamber = systems.get('chamber')
            if chamber is None:
                return
            from aurora_internal.aurora_evolution_chamber import ActionTrace
            trace = ActionTrace(
                name=f'body:{adap.name}',
                constraints_used=[adap.axis],
                meta={
                    'description': adap.description,
                    'tick':        tick,
                    'source':      'embodiment',
                },
            )
            chamber.tick(action=trace)
        except Exception:
            pass


# ── Device control helpers ─────────────────────────────────────────────────────

def _v4l2_set(device: str, control: str, value: int) -> bool:
    """Set a V4L2 camera control parameter."""
    try:
        result = subprocess.run(
            ['v4l2-ctl', '-d', device, f'--set-ctrl={control}={value}'],
            capture_output=True, timeout=3,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _alsa_set_gain(pct: int) -> bool:
    """Set ALSA capture gain to pct (0–100)."""
    pct = max(0, min(100, pct))
    for cmd in [
        ['amixer', 'set', 'Capture', f'{pct}%'],
        ['amixer', '-c', '0', 'set', 'Capture', f'{pct}%', 'cap'],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False
