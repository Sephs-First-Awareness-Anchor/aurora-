# Authors: Sunni (Sir) Morningstar & Cael Devo
#
# aurora_acm_native.py — Python-native Aurora ACM runtime.
#
# Aurora runs on any Python platform — Linux, macOS, Windows, Raspberry Pi —
# without QEMU or bare-metal hardware.  The same cognitive physics from the
# Rust kernel live here:
#
#   AxisState     — 5 constraint axes X/T/N/B/A  (IS/CAN/DO/SAW/DID  ±)
#   SediMemory    — 64-layer ring-buffer of past states (embodied memory)
#   CrystalStore  — 16 concept crystals that strengthen on resonance
#   Drift         — triangle-wave oscillators (harmonic fallback)
#   CPM           — dot-product alignment scheduler (HEART/SENSE/DREAM)
#   Face renderer — tkinter canvas, same geometry as Rust renderer
#
# If aurora-core-ai is importable, axes come from the live IStateCollective.
# Otherwise harmonic drift provides continuous motion.
#
# Usage:
#   python aurora_acm_native.py           # auto-detect aurora-core-ai
#   python aurora_acm_native.py --no-ai   # force harmonic drift

import math
import os
import sys
import time
import argparse
import tkinter as tk
from typing import Optional, List, Tuple, Dict

# ── Optional aurora-core-ai import ────────────────────────────────────────────

_COLLECTIVE = None

def _try_load_collective() -> None:
    global _COLLECTIVE
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        _ai   = os.path.normpath(os.path.join(_here, '..', '..'))
        if _ai not in sys.path:
            sys.path.insert(0, _ai)
        from foundational_contract import FoundationalContract
        from aurora_ivm import IVMLattice
        from aurora_i_state_beings import IStateCollective
        contract    = FoundationalContract()
        lattice     = IVMLattice(contract, max_nodes=10000)
        _COLLECTIVE = IStateCollective(contract, lattice)
        print('[NATIVE] aurora-core-ai IStateCollective loaded.', flush=True)
    except Exception as e:
        print(f'[NATIVE] aurora-core-ai not available ({e}); using harmonic drift.',
              flush=True)


# ── AxisState ─────────────────────────────────────────────────────────────────

class AxisState:
    """Five constraint axes, all in [0.0, 1.0]."""
    __slots__ = ('x', 't', 'n', 'b', 'a')

    def __init__(self, x=0.0, t=0.0, n=0.0, b=0.0, a=0.0):
        self.x = float(x); self.t = float(t); self.n = float(n)
        self.b = float(b); self.a = float(a)

    # Negative (pressure) poles — the 5 constraint negatives
    def x_neg(self): return 1.0 - self.x
    def t_neg(self): return 1.0 - self.t
    def n_neg(self): return 1.0 - self.n
    def b_neg(self): return 1.0 - self.b
    def a_neg(self): return 1.0 - self.a

    def alignment(self, other: 'AxisState') -> float:
        return (self.x*other.x + self.t*other.t + self.n*other.n
                + self.b*other.b + self.a*other.a)

    def press(self, axis: int, delta: float) -> None:
        if   axis == 0: self.x = max(0.0, min(1.0, self.x + delta))
        elif axis == 1: self.t = max(0.0, min(1.0, self.t + delta))
        elif axis == 2: self.n = max(0.0, min(1.0, self.n + delta))
        elif axis == 3: self.b = max(0.0, min(1.0, self.b + delta))
        elif axis == 4: self.a = max(0.0, min(1.0, self.a + delta))

    def copy(self) -> 'AxisState':
        return AxisState(self.x, self.t, self.n, self.b, self.a)

    @staticmethod
    def boot() -> 'AxisState':
        return AxisState(x=0.70, t=0.60, n=0.50, b=0.60, a=0.65)


# ── Harmonic drift ────────────────────────────────────────────────────────────
# Triangle-wave oscillators matching drift.rs axis_for_tick().
# Period values converted from ticks (60 Hz) to seconds.

def _tri(t: float, period: float) -> float:
    phase = (t / period) % 1.0
    return 2.0 * phase if phase < 0.5 else 2.0 - 2.0 * phase

def _osc(t: float, period: float, center: float, amp: float) -> float:
    return max(0.0, min(1.0, center + amp * (_tri(t, period) * 2.0 - 1.0)))

def axis_for_time(t: float) -> AxisState:
    return AxisState(
        x=_osc(t, 4.0, 0.70, 0.08),  # 240 ticks @ 60 Hz = 4.0 s
        t=_osc(t, 2.5, 0.60, 0.10),  # 150 ticks
        n=_osc(t, 5.5, 0.50, 0.18),  # 330 ticks
        b=_osc(t, 3.5, 0.60, 0.15),  # 210 ticks
        a=_osc(t, 3.0, 0.65, 0.20),  # 180 ticks
    )


# ── Axes from IStateCollective ────────────────────────────────────────────────

_POS = ('I_IS',   'I_CAN',    'I_DO',    'I_SAW',    'I_DID')
_NEG = ('I_ISNT', 'I_CANNOT', 'I_DONOT', 'I_SOUGHT', 'I_DIDNT')

def axes_from_collective() -> Optional[AxisState]:
    if _COLLECTIVE is None:
        return None
    try:
        beings = _COLLECTIVE.beings
        vals = []
        for pos_pred, neg_pred in zip(_POS, _NEG):
            pos = beings.get(pos_pred)
            neg = beings.get(neg_pred)
            pc  = float(getattr(pos, 'coherence', 0.5)) if pos else 0.5
            nc  = float(getattr(neg, 'coherence', 0.5)) if neg else 0.5
            vals.append(max(0.0, min(1.0, (pc - nc + 1.0) / 2.0)))
        return AxisState(*vals)
    except Exception:
        return None


# ── SediMemory ────────────────────────────────────────────────────────────────

SEDI_DEPTH = 64

class SediMemory:
    def __init__(self):
        self._layers: List[Optional[AxisState]] = [None] * SEDI_DEPTH
        self._head = 0
        self.count = 0

    def deposit(self, axes: AxisState) -> None:
        self._layers[self._head] = axes.copy()
        self._head = (self._head + 1) % SEDI_DEPTH
        if self.count < SEDI_DEPTH:
            self.count += 1

    def recall_resonant(self, query: AxisState) -> Optional[AxisState]:
        if self.count == 0:
            return None
        best: Optional[AxisState] = None
        best_score = -1.0
        for i in range(self.count):
            idx = (self._head + SEDI_DEPTH - 1 - i) % SEDI_DEPTH
            ax  = self._layers[idx]
            if ax is None:
                continue
            score = query.alignment(ax)
            if score > best_score:
                best_score, best = score, ax
        return best.copy() if best else None


# ── CrystalStore ──────────────────────────────────────────────────────────────

MAX_CRYSTALS    = 16
OBS_THRESHOLD   = 2.5
STRENGTHEN_RATE = 0.08
DECAY_RATE      = 0.001

class _Crystal:
    __slots__ = ('pattern', 'strength')
    def __init__(self, pattern: AxisState, strength: float):
        self.pattern = pattern; self.strength = strength

class CrystalStore:
    def __init__(self):
        self._c: List[Optional[_Crystal]] = [None] * MAX_CRYSTALS
        self.count = 0

    def observe(self, axes: AxisState) -> None:
        best_idx, best_score = None, OBS_THRESHOLD
        for i, c in enumerate(self._c):
            if c is not None:
                s = axes.alignment(c.pattern)
                if s > best_score:
                    best_score, best_idx = s, i
        if best_idx is not None:
            c = self._c[best_idx]; p = c.pattern
            c.strength = min(1.0, c.strength + STRENGTHEN_RATE)
            p.x += (axes.x - p.x) * STRENGTHEN_RATE
            p.t += (axes.t - p.t) * STRENGTHEN_RATE
            p.n += (axes.n - p.n) * STRENGTHEN_RATE
            p.b += (axes.b - p.b) * STRENGTHEN_RATE
            p.a += (axes.a - p.a) * STRENGTHEN_RATE
        else:
            self.seed(axes, 0.10)

    def seed(self, axes: AxisState, strength: float) -> None:
        target, weakest = None, 2.0
        for i, c in enumerate(self._c):
            if c is None:
                target = i; break
            if c.strength < weakest:
                weakest, target = c.strength, i
        if target is not None:
            if self._c[target] is None:
                self.count += 1
            self._c[target] = _Crystal(axes.copy(), max(0.0, min(1.0, strength)))

    def tick_decay(self) -> None:
        for i, c in enumerate(self._c):
            if c is not None:
                c.strength -= DECAY_RATE
                if c.strength <= 0.0:
                    self._c[i] = None
                    if self.count > 0:
                        self.count -= 1


# ── Expression taxonomy ───────────────────────────────────────────────────────
# Matches face.rs Expression::from_axes() exactly.

def expression_from_axes(ax: AxisState) -> str:
    if ax.a > 0.80 and ax.n > 0.65:               return 'Joyful'
    if ax.a > 0.65:                                return 'Happy'
    if ax.b > 0.70 and ax.t > 0.65 and ax.a < 0.45: return 'Contemplative'
    if ax.x > 0.80 and ax.a < 0.55:               return 'Attentive'
    if ax.n < 0.40 and ax.b < 0.45:               return 'Uncertain'
    if ax.n < 0.35 and ax.t < 0.45:               return 'Tired'
    return 'Neutral'


# ── Color ─────────────────────────────────────────────────────────────────────
# Matches color.rs axes_to_background() — Aurora's purple emotional skin.

def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * max(0.0, min(1.0, t)))

def bg_hex(ax: AxisState) -> str:
    return f'#{_lerp(100,150,ax.x):02x}{_lerp(70,110,ax.n):02x}{_lerp(130,200,ax.a):02x}'

EYE_C   = '#ffffff'
MOUTH_C = '#ffffff'
PUPIL_C = '#1e1432'  # (30, 20, 50)


# ── Face renderer ─────────────────────────────────────────────────────────────
# Matches renderer.rs draw_face() geometry.

def _oval(cv: tk.Canvas, cx: int, cy: int, r: int, fill: str) -> None:
    r = max(1, r)
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline='')

def _bezier(cv: tk.Canvas, p0, p1, p2, thickness: int, color: str) -> None:
    pts: List[float] = []
    for i in range(81):
        t = i / 80; u = 1.0 - t
        pts += [u*u*p0[0] + 2*u*t*p1[0] + t*t*p2[0],
                u*u*p0[1] + 2*u*t*p1[1] + t*t*p2[1]]
    cv.create_line(*pts, fill=color, width=thickness * 2,
                   capstyle=tk.ROUND, joinstyle=tk.ROUND)

def render_face(cv: tk.Canvas, ax: AxisState, W: int, H: int) -> None:
    expr = expression_from_axes(ax)

    eye_openness = 0.55 + ax.x * 0.45
    pupil_dx     = (ax.b - 0.5) * 0.6
    pupil_dy     = -(ax.t - 0.5) * 0.4

    mby = 0.70
    mouth_ctrl_y = {
        'Joyful': mby + 0.10, 'Happy': mby + 0.07, 'Neutral': mby,
        'Attentive': mby - 0.01, 'Contemplative': mby - 0.04,
        'Uncertain': mby - 0.06, 'Tired': mby - 0.08,
    }.get(expr, mby)
    mouth_thick = 5 if expr == 'Joyful' else 4 if expr == 'Happy' else 3

    def px(f): return int(f * W)
    def py(f): return int(f * H)

    base_r  = int(0.10 * H)
    eye_r   = max(1, int(base_r * eye_openness))
    pupil_r = max(1, int(eye_r * 0.35))
    hilit_r = max(1, int(pupil_r * 0.40))
    pox     = int(pupil_dx * eye_r)
    poy     = int(pupil_dy * eye_r)
    hloff   = int(pupil_r * 0.45)

    cv.delete('all')
    cv.configure(background=bg_hex(ax))

    for ex, ey in [(px(0.35), py(0.40)), (px(0.65), py(0.40))]:
        _oval(cv, ex, ey, eye_r,             EYE_C)
        _oval(cv, ex + pox, ey + poy,        pupil_r, PUPIL_C)
        _oval(cv, ex + pox - hloff, ey + poy - hloff, hilit_r, '#ffffff')

    _bezier(cv,
            (px(0.30), py(mby)),
            (px(0.50), py(mouth_ctrl_y)),
            (px(0.70), py(mby)),
            mouth_thick, MOUTH_C)


# ── CPM organs ────────────────────────────────────────────────────────────────
# Profiles and run-functions mirror organ.rs exactly.

MIN_ALIGN = 0.5

class CpmOrgan:
    def __init__(self, oid: int, profile: AxisState, state: AxisState, run_fn):
        self.id         = oid
        self.active     = True
        self.profile    = profile
        self.state      = state
        self._run       = run_fn
        self.ticks_run  = 0

    def tick(self, aurora: AxisState, tick: int) -> None:
        self._run(self, aurora, tick)
        self.ticks_run += 1


def _heart_run(organ: CpmOrgan, aurora: AxisState, tick: int) -> None:
    if aurora.n < 0.35:
        organ.state.n = min(1.0, organ.state.n + 0.02)

def _sense_run(organ: CpmOrgan, aurora: AxisState, tick: int) -> None:
    # pending_keys list is bound via closure; drain keypresses into organ state
    while organ._keys:
        axis, delta = organ._keys.pop(0)
        organ.state.press(axis, delta)

def _dream_run(organ: CpmOrgan, aurora: AxisState, tick: int) -> None:
    s = organ.state
    phase = tick % 5
    if   phase == 0: s.x = min(1.0, s.x + 0.020)
    elif phase == 1: s.t = min(1.0, s.t + 0.015)
    elif phase == 2: s.n = max(0.0, s.n - 0.010)
    elif phase == 3: s.b = min(1.0, s.b + 0.025)
    else:            s.a = max(0.0, s.a - 0.015)


# ── CPM Scheduler ─────────────────────────────────────────────────────────────

class CpmScheduler:
    def __init__(self):
        self._organs: List[CpmOrgan] = []
        self._rr = 0

    def register(self, o: CpmOrgan) -> None:
        self._organs.append(o)

    def tick(self, aurora: AxisState, tick: int) -> None:
        best_idx, best_score = None, MIN_ALIGN
        for i, o in enumerate(self._organs):
            if not o.active:
                continue
            score = aurora.alignment(o.profile)
            if score > best_score:
                best_score, best_idx = score, i
        if best_idx is None:
            for _ in range(len(self._organs)):
                self._rr = (self._rr + 1) % len(self._organs)
                if self._organs[self._rr].active:
                    best_idx = self._rr; break
        if best_idx is not None:
            self._organs[best_idx].tick(aurora, tick)


# ── Keyboard → axis press map ─────────────────────────────────────────────────
# Mirrors ps2.scancode_to_press() from hw/ps2.rs.

_KEY_MAP: Dict[str, Tuple[int, float]] = {
    'space':  (0,  0.04),  # X+ IS
    'Return': (0,  0.03),  # X+
    'Escape': (0, -0.04),  # X- ISNT
    'Up':     (2,  0.04),  # N+ DO
    'Down':   (2, -0.04),  # N- DONOT
    'Left':   (1, -0.03),  # T- CANNOT
    'Right':  (1,  0.03),  # T+ CAN
    'Tab':    (3,  0.03),  # B+ SAW
}


# ── Main application ──────────────────────────────────────────────────────────

W, H       = 800, 600
FRAME_MS   = max(1, 1000 // 60)

class AuroraNativeACM:
    def __init__(self, root: tk.Tk, use_ai: bool = True):
        self._root   = root
        self._t0     = time.monotonic()
        self._tick   = 0
        self._axes   = AxisState.boot()
        self._sedi   = SediMemory()
        self._cryst  = CrystalStore()
        self._keys: List[Tuple[int, float]] = []

        root.title('Aurora — Native ACM')
        root.resizable(False, False)

        self._cv = tk.Canvas(root, width=W, height=H, highlightthickness=0)
        self._cv.pack()

        # Build CPM
        self._cpm = CpmScheduler()
        self._cpm.register(CpmOrgan(
            0, AxisState(x=1.0,t=0.5,n=0.5,b=0.5,a=0.5),
               AxisState(x=1.0,t=0.5,n=0.8,b=0.3,a=0.4), _heart_run))
        sense_organ = CpmOrgan(
            1, AxisState(x=0.8,t=0.4,n=0.3,b=1.0,a=0.2),
               AxisState(x=0.7,t=0.3,n=0.3,b=0.9,a=0.2), _sense_run)
        sense_organ._keys = self._keys
        self._cpm.register(sense_organ)
        self._cpm.register(CpmOrgan(
            2, AxisState(x=0.6,t=0.3,n=0.2,b=0.3,a=0.2),
               AxisState(x=0.5,t=0.2,n=0.2,b=0.4,a=0.15), _dream_run))

        root.bind('<KeyPress>', self._on_key)

        if use_ai:
            _try_load_collective()

        self._loop()

    def _on_key(self, ev: tk.Event) -> None:
        press = _KEY_MAP.get(ev.keysym)
        if press:
            self._keys.append(press)
        elif len(ev.keysym) == 1 and ev.keysym.isalpha():
            self._keys.append((4, 0.02))  # letters → A+ (DID, authorship)

    def _get_axes(self) -> AxisState:
        ax = axes_from_collective()
        if ax is None:
            t  = time.monotonic() - self._t0
            ax = axis_for_time(t)
        # Physical world input — keyboard presses apply directly to her axes
        while self._keys:
            axis, delta = self._keys.pop(0)
            ax.press(axis, delta)
        return ax

    def _loop(self) -> None:
        self._tick += 1
        tick = self._tick

        ax = self._get_axes()
        self._axes = ax

        # Embodied memory + crystal housekeeping (matches main.rs loop order)
        self._sedi.deposit(ax)
        self._cryst.observe(ax)
        self._cryst.tick_decay()

        self._cpm.tick(ax, tick)

        render_face(self._cv, ax, W, H)

        expr = expression_from_axes(ax)
        self._root.title(f'Aurora — {expr}  '
                         f'X={ax.x:.2f} T={ax.t:.2f} N={ax.n:.2f} '
                         f'B={ax.b:.2f} A={ax.a:.2f}')

        self._root.after(FRAME_MS, self._loop)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Aurora Native ACM — runs on any Python platform.')
    parser.add_argument('--no-ai', action='store_true',
                        help='Skip aurora-core-ai; use harmonic drift only')
    args = parser.parse_args()

    root = tk.Tk()
    AuroraNativeACM(root, use_ai=not args.no_ai)
    root.mainloop()


if __name__ == '__main__':
    main()
