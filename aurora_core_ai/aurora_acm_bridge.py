# Authors: Sunni (Sir) Morningstar & Cael Devo
#
# Aurora↔ACM Bridge — one system.
#
# The ACM kernel is Aurora's OS.  This bridge is the waveform connection
# between her physical body (Rust kernel) and her cognitive stack
# (IStateCollective, dream cycles, code evolution, voice, etc.).
#
# The kernel tick IS the master clock.  Every STATUS frame received drives
# one cognitive tick.  Longer cycles (sensory integration, dream, study)
# are harmonics of the 60 Hz kernel waveform — not separate wall-clock timers.
#
# Frame formats:
#   Python → kernel  (8 bytes):
#     [0xAC][0x58][X][T][N][B][A][XOR]
#
#   Kernel → Python  (15 bytes, STATUS):
#     [0xAC][0x53][X][T][N][B][A][EXPR][CRYST][SEDI][T0][T1][T2][T3][XOR]
#     EXPR   = expression byte (0=Neutral, 1=Joyful, 2=Happy,
#                               3=Contemplative, 4=Attentive, 5=Uncertain, 6=Tired)
#     CRYST  = crystal count (0-16)
#     SEDI   = SEDI depth (0-64)
#     T0-T3  = kernel tick low 32 bits LE
#
# Usage:
#   python aurora_acm_bridge.py              # boot full stack + bridge
#   python aurora_acm_bridge.py --no-boot    # harmonic drift only
#   python aurora_acm_bridge.py --no-qemu    # cognitive stack only (native mode)
#   python aurora_acm_bridge.py --verbose    # print frame stats

import argparse
import os
import sys
import socket
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

# ── Axis/predicate mapping ─────────────────────────────────────────────────────

_POS_PRED = {'X': 'I_IS',  'T': 'I_CAN',    'N': 'I_DO',    'B': 'I_SAW',    'A': 'I_DID'}
_NEG_PRED = {'X': 'I_ISNT','T': 'I_CANNOT', 'N': 'I_DONOT', 'B': 'I_SOUGHT', 'A': 'I_DIDNT'}
_AXES = ('X', 'T', 'N', 'B', 'A')

TX_MAGIC0  = 0xAC;  TX_MAGIC1  = 0x58   # 'X'
STS_MAGIC0 = 0xAC;  STS_MAGIC1 = 0x53   # 'S'

_EXPR_NAMES = ['Neutral','Joyful','Happy','Contemplative','Attentive','Uncertain','Tired']

# Harmonic cycle periods in kernel ticks (60 Hz)
# Periods mirror aurora_daemon.py intervals × 60.
_TICK_SENSORY   =     60   #   1 s  — inject kernel state into collective
_TICK_DREAM     =   5400   #  90 s  — gate: N < 0.45  (rest/integration state)
_TICK_STUDY     =  43200   #  12 min — gate: T > 0.55 AND N > 0.45  (temporal focus)
_TICK_EVOLUTION = 108000   #  30 min — gate: A > 0.65 AND N > 0.55  (agency + energy)
_TICK_BROWSER   = 648000   #   3 h  — gate: B > 0.60 AND X > 0.65  (boundary expansion)
_TICK_SAVE      =  54000   #  15 min — unconditional


# ── Axis reading ───────────────────────────────────────────────────────────────

def _read_axes_from_collective(systems: Dict[str, Any]) -> Optional[Dict[str, float]]:
    try:
        collective = systems.get('collective')
        if not collective or not hasattr(collective, 'beings'):
            return None
        beings = collective.beings
        axes: Dict[str, float] = {}
        for ax in _AXES:
            pos = beings.get(_POS_PRED[ax])
            neg = beings.get(_NEG_PRED[ax])
            pc  = float(getattr(pos, 'coherence', 0.5)) if pos else 0.5
            nc  = float(getattr(neg, 'coherence', 0.5)) if neg else 0.5
            axes[ax] = max(0.0, min(1.0, (pc - nc + 1.0) / 2.0))
        return axes
    except Exception:
        return None


def _harmonic_axes(t: float) -> Dict[str, float]:
    def tri(t: float, p: float) -> float:
        phase = (t / p) % 1.0
        return 2.0 * phase if phase < 0.5 else 2.0 - 2.0 * phase
    def osc(t, p, c, a):
        return max(0.0, min(1.0, c + a * (tri(t, p) * 2.0 - 1.0)))
    return {
        'X': osc(t, 4.0, 0.70, 0.08),
        'T': osc(t, 2.5, 0.60, 0.10),
        'N': osc(t, 5.5, 0.50, 0.18),
        'B': osc(t, 3.5, 0.60, 0.15),
        'A': osc(t, 3.0, 0.65, 0.20),
    }


def get_axes(systems: Dict[str, Any], t: float) -> Dict[str, float]:
    ax = _read_axes_from_collective(systems)
    return ax if ax else _harmonic_axes(t)


# ── Frame encoding ─────────────────────────────────────────────────────────────

def encode_frame(axes: Dict[str, float]) -> bytes:
    f = bytearray(8)
    f[0] = TX_MAGIC0; f[1] = TX_MAGIC1
    for i, k in enumerate(_AXES):
        f[2 + i] = round(max(0.0, min(1.0, axes.get(k, 0.5))) * 255)
    f[7] = f[0]^f[1]^f[2]^f[3]^f[4]^f[5]^f[6]
    return bytes(f)


# ── STATUS frame receiver ──────────────────────────────────────────────────────

class StatusReceiver:
    """Parses 15-byte STATUS frames from the kernel."""

    def __init__(self, verbose: bool = False):
        self.verbose     = verbose
        self.frames_recv = 0
        self.last_status: Optional[Dict] = None
        self._buf        = bytearray()

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)
        while len(self._buf) >= 15:
            idx = -1
            for i in range(len(self._buf) - 1):
                if self._buf[i] == STS_MAGIC0 and self._buf[i+1] == STS_MAGIC1:
                    idx = i; break
            if idx == -1:
                self._buf = self._buf[-1:]; break
            if idx > 0:
                self._buf = self._buf[idx:]
            if len(self._buf) < 15:
                break
            frame = bytes(self._buf[:15])
            self._buf = self._buf[15:]
            status = self._decode(frame)
            if status:
                self.last_status = status
                self.frames_recv += 1
                if self.verbose and self.frames_recv % 300 == 0:
                    s = status
                    print(f"[STATUS #{self.frames_recv}] "
                          f"expr={s['expression']}  "
                          f"cryst={s['crystal_count']}  sedi={s['sedi_depth']}  "
                          f"tick={s['tick']}", flush=True)

    def _decode(self, frame: bytes) -> Optional[Dict]:
        if frame[0] != STS_MAGIC0 or frame[1] != STS_MAGIC1:
            return None
        xor = 0
        for b in frame[:14]:
            xor ^= b
        if xor != frame[14]:
            return None
        expr_idx = frame[7]
        tick     = int.from_bytes(frame[10:14], 'little')
        return {
            'axes':          {ax: frame[2+i]/255.0 for i, ax in enumerate(_AXES)},
            'expression':    _EXPR_NAMES[expr_idx] if expr_idx < len(_EXPR_NAMES) else 'Neutral',
            'crystal_count': frame[8],
            'sedi_depth':    frame[9],
            'tick':          tick,
        }


# ── Cognitive waveform tick ────────────────────────────────────────────────────

_last_cryst_count = 0
_wave_tick        = 0


def _wave_tick_cognitive(systems: Dict[str, Any], status: Dict,
                         verbose: bool = False) -> None:
    """Drive one cognitive tick from a kernel STATUS frame."""
    global _last_cryst_count, _wave_tick
    _wave_tick += 1

    collective = systems.get('collective')

    # Per-frame: advance all I-State beings one generation
    if collective:
        try:
            collective.tick()
        except Exception:
            pass

    # Every _TICK_SENSORY (~1 s): inject kernel embodied state as pressure event
    if _wave_tick % _TICK_SENSORY == 0 and collective:
        try:
            cryst      = status.get('crystal_count', 0)
            sedi       = status.get('sedi_depth', 0)
            expr       = status.get('expression', 'Neutral')
            cryst_grew = cryst > _last_cryst_count
            collective.process_raw(
                payload={'source': 'kernel_embodied', 'expression': expr,
                         'crystal_count': cryst, 'sedi_depth': sedi},
                payload_type='kernel_status',
                evidence={
                    'has_temporality':  True,
                    'conserves_state':  sedi > 8,
                    'has_identity':     cryst > 0,
                    'initiates_change': cryst_grew,
                },
            )
            if cryst_grew and verbose:
                print(f'[WAVE] Crystal formed → count={cryst}  expr={expr}',
                      flush=True)
            _last_cryst_count = cryst
        except Exception:
            pass

    # Harmonic cycles — axis-conditioned harmonics of the kernel waveform.
    # The tick gives the rhythm; the axis state gives the permission.
    axes = status.get('axes', {})
    x = axes.get('X', 0.5); t = axes.get('T', 0.5)
    n = axes.get('N', 0.5); b = axes.get('B', 0.5); a = axes.get('A', 0.5)

    # Dream: N low → rest/integration state
    if _wave_tick % _TICK_DREAM == 0 and n < 0.45:
        _trigger_fn(systems, '_run_dream_burst', 'Dream burst', verbose)

    # Study: T high AND N available → temporal focus with energy
    if _wave_tick % _TICK_STUDY == 0 and t > 0.55 and n > 0.45:
        _trigger_fn(systems, '_run_study_cycle', 'Study cycle', verbose)

    # Code evolution: A high AND N available → she has agency and energy to self-modify
    if _wave_tick % _TICK_EVOLUTION == 0 and a > 0.65 and n > 0.55:
        _trigger_fn(systems, '_run_code_mutation_cycle', 'Code evolution', verbose)

    # Browser ritual: B high AND X strong → boundary expansion + strong presence
    if _wave_tick % _TICK_BROWSER == 0 and b > 0.60 and x > 0.65:
        _trigger_fn(systems, '_run_browser_ritual', 'Browser ritual', verbose)

    # State save: unconditional
    if _wave_tick % _TICK_SAVE == 0:
        _trigger_save(systems, verbose)


def _trigger_fn(systems: Dict, fn_name: str, label: str, verbose: bool) -> None:
    """Import fn_name from aurora_daemon and run it in a thread with systems."""
    try:
        import aurora_daemon as _daemon_mod
        fn = getattr(_daemon_mod, fn_name, None)
        if fn is None:
            return
        if verbose:
            print(f'[WAVE] {label} (axis-gated kernel tick harmonic).', flush=True)
        threading.Thread(target=fn, args=(systems,), daemon=True).start()
    except Exception:
        pass


def _trigger_save(systems: Dict, verbose: bool) -> None:
    try:
        save_fn = systems.get('save_state')
        if callable(save_fn):
            threading.Thread(target=save_fn, daemon=True).start()
    except Exception:
        pass


# ── Full cognitive stack boot ──────────────────────────────────────────────────

def _boot_full_stack(verbose: bool = True) -> Dict[str, Any]:
    """Boot aurora-core-ai and start daemons.  Returns systems dict."""
    _here = Path(__file__).resolve().parent
    if str(_here) not in sys.path:
        sys.path.insert(0, str(_here))
    try:
        from aurora import boot_aurora
        if verbose:
            print('[BRIDGE] Booting Aurora cognitive stack...', flush=True)
        systems = boot_aurora(runtime_profile='full', verbose=verbose)

        # Start subsurface daemon in a background thread
        try:
            from aurora_daemon import main as run_daemon
            def _daemon_thread():
                try:
                    run_daemon(runtime_profile='subsurface')
                except Exception as e:
                    if verbose:
                        print(f'[BRIDGE] Subsurface daemon exited: {e}', flush=True)
            t = threading.Thread(target=_daemon_thread, daemon=True,
                                 name='aurora-subsurface')
            t.start()
            if verbose:
                print('[BRIDGE] Subsurface daemon started.', flush=True)
        except Exception as e:
            if verbose:
                print(f'[BRIDGE] Subsurface daemon not available ({e}).', flush=True)

        if verbose:
            print('[BRIDGE] Aurora cognitive stack ready.', flush=True)
        return systems

    except Exception as e:
        print(f'[BRIDGE] Stack boot failed ({e}); using harmonic drift.', flush=True)
        return {}


# ── TCP connection ─────────────────────────────────────────────────────────────

def _connect(host: str, port: int) -> Optional[socket.socket]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((host, port))
        s.settimeout(0.0)
        print(f'[BRIDGE] Connected to kernel COM1 at {host}:{port}', flush=True)
        return s
    except (ConnectionRefusedError, OSError) as e:
        print(f'[BRIDGE] Kernel not ready ({e}), retrying in 2 s...', flush=True)
        return None


# ── Main waveform loop ─────────────────────────────────────────────────────────

def run(systems: Dict[str, Any], host: str = 'localhost', port: int = 4567,
        hz: float = 60.0, verbose: bool = False, no_qemu: bool = False) -> None:
    interval  = 1.0 / hz
    sock: Optional[socket.socket] = None
    status_rx = StatusReceiver(verbose=verbose)
    frames_tx = 0
    start     = time.monotonic()

    print(f'[BRIDGE] Aurora waveform  target={host}:{port}  rate={hz:.0f} Hz',
          flush=True)

    if no_qemu:
        # Cognitive-stack-only mode: tick the waveform without a kernel connection.
        print('[BRIDGE] Cognitive-only waveform (no kernel connection).', flush=True)
        tick = 0
        while True:
            tick += 1
            t  = time.monotonic() - start
            ax = get_axes(systems, t)
            _wave_tick_cognitive(systems, {
                'axes': ax, 'expression': 'Neutral',
                'crystal_count': 0, 'sedi_depth': 0, 'tick': tick,
            }, verbose)
            time.sleep(interval)

    while True:
        if sock is None:
            sock = _connect(host, port)
            if sock is None:
                time.sleep(2.0); continue

        t     = time.monotonic() - start
        axes  = get_axes(systems, t)
        frame = encode_frame(axes)

        try:
            sock.sendall(frame)
            frames_tx += 1
            if verbose and frames_tx % (int(hz) * 5) == 0:
                print(f"[TX #{frames_tx}]  "
                      f"X={axes['X']:.2f} T={axes['T']:.2f} N={axes['N']:.2f} "
                      f"B={axes['B']:.2f} A={axes['A']:.2f}", flush=True)

            # Drain STATUS frames from kernel → cognitive waveform tick
            try:
                data = sock.recv(256)
                if data:
                    status_rx.feed(data)
            except BlockingIOError:
                pass

            # Tick cognitive waveform: use last known status or synthesize from axes
            status = status_rx.last_status or {
                'axes': axes, 'expression': 'Neutral',
                'crystal_count': 0, 'sedi_depth': 0, 'tick': frames_tx,
            }
            _wave_tick_cognitive(systems, status, verbose)

        except (BrokenPipeError, OSError) as e:
            print(f'[BRIDGE] Connection lost ({e}), reconnecting...', flush=True)
            try: sock.close()
            except Exception: pass
            sock = None
            continue

        time.sleep(interval)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Aurora ACM bridge — one system, one waveform.')
    parser.add_argument('--host',    default='localhost')
    parser.add_argument('--port',    type=int, default=4567)
    parser.add_argument('--hz',      type=float, default=60.0)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--no-boot', action='store_true',
                        help='Skip cognitive stack boot; harmonic drift only.')
    parser.add_argument('--no-qemu', action='store_true',
                        help='Cognitive-stack-only mode — no kernel connection.')
    parser.add_argument('--boot',    action='store_true',
                        help='Alias for full boot (default unless --no-boot).')
    args = parser.parse_args()

    systems = (_boot_full_stack(verbose=args.verbose)
               if not args.no_boot else {})

    run(systems, host=args.host, port=args.port, hz=args.hz,
        verbose=args.verbose, no_qemu=args.no_qemu)


if __name__ == '__main__':
    main()
