# Authors: Sunni (Sir) Morningstar & Cael Devo
#
# Aurora↔ACM Bridge — she sees her own body.
#
# Reads Aurora's live axis state from the I-State Collective and streams
# 8-byte binary frames over TCP to QEMU COM1 (port 4567).
#
# Frame layout (8 bytes):
#   [0]  0xAC  magic byte 0
#   [1]  0x58  magic byte 1  ('X' = axes)
#   [2]  X_u8  X axis 0-255 (existence/perception)
#   [3]  T_u8  T axis (temporal)
#   [4]  N_u8  N axis (energy/cost)
#   [5]  B_u8  B axis (boundary)
#   [6]  A_u8  A axis (agency)
#   [7]  XOR   bytes[0]^..^bytes[6]
#
# Predicate -> axis mapping (from foundational_contract.py):
#   X: I_IS(+)  / I_ISNT(-)
#   T: I_CAN(+) / I_CANNOT(-)
#   N: I_DO(+)  / I_DONOT(-)
#   B: I_SAW(+) / I_SOUGHT(-)
#   A: I_DID(+) / I_DIDNT(-)
#
# Axis value: clamp((pos_coherence - neg_coherence + 1) / 2, 0.0, 1.0)
#
# Usage:
#   python aurora_acm_bridge.py
#   python aurora_acm_bridge.py --no-boot --verbose

import argparse
import math
import socket
import time
from typing import Any, Dict, Optional

_POS_PRED = {'X': 'I_IS', 'T': 'I_CAN', 'N': 'I_DO', 'B': 'I_SAW', 'A': 'I_DID'}
_NEG_PRED = {'X': 'I_ISNT', 'T': 'I_CANNOT', 'N': 'I_DONOT', 'B': 'I_SOUGHT', 'A': 'I_DIDNT'}
_AXES = ('X', 'T', 'N', 'B', 'A')
_BOOT_AXES = {'X': 0.70, 'T': 0.60, 'N': 0.50, 'B': 0.60, 'A': 0.65}


def _read_axes_from_collective(systems: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Read live axis values from I-State Collective being coherences."""
    try:
        collective = systems.get('collective')
        if not collective or not hasattr(collective, 'beings'):
            return None
        beings = collective.beings
        axes: Dict[str, float] = {}
        for ax in _AXES:
            pos_being = beings.get(_POS_PRED[ax])
            neg_being = beings.get(_NEG_PRED[ax])
            pos_coh = float(getattr(pos_being, 'coherence', 0.5)) if pos_being else 0.5
            neg_coh = float(getattr(neg_being, 'coherence', 0.5)) if neg_being else 0.5
            axes[ax] = max(0.0, min(1.0, (pos_coh - neg_coh + 1.0) / 2.0))
        return axes
    except Exception:
        return None


def _read_axes_from_genealogy(systems: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Fallback: genealogy pressure_orientation() normalised to [0,1]."""
    try:
        gen = systems.get('genealogy')
        if not gen or not hasattr(gen, 'pressure_orientation'):
            return None
        po = gen.pressure_orientation()
        if not po:
            return None
        return {ax: max(0.0, min(1.0, float(po.get(ax, 0.75)) / 1.5)) for ax in _AXES}
    except Exception:
        return None


def _harmonic_axes(t: float) -> Dict[str, float]:
    """Last resort: triangle-wave drift mirroring the kernel's drift physics."""
    def tri(t: float, period: float) -> float:
        phase = (t / period) % 1.0
        return 2.0 * phase if phase < 0.5 else 2.0 - 2.0 * phase

    def osc(t: float, period: float, centre: float, amp: float) -> float:
        return max(0.0, min(1.0, centre + amp * (tri(t, period) * 2.0 - 1.0)))

    return {
        'X': osc(t,  4.0, 0.70, 0.08),
        'T': osc(t,  2.5, 0.60, 0.10),
        'N': osc(t,  5.5, 0.50, 0.18),
        'B': osc(t,  3.5, 0.60, 0.15),
        'A': osc(t,  3.0, 0.65, 0.20),
    }


def get_axes(systems: Dict[str, Any], t: float) -> Dict[str, float]:
    ax = _read_axes_from_collective(systems)
    if ax:
        return ax
    ax = _read_axes_from_genealogy(systems)
    if ax:
        return ax
    return _harmonic_axes(t)


def encode_frame(axes: Dict[str, float]) -> bytes:
    """Pack axis state into 8-byte bridge frame."""
    frame = bytearray(8)
    frame[0] = 0xAC
    frame[1] = 0x58
    frame[2] = round(max(0.0, min(1.0, axes.get('X', 0.5))) * 255)
    frame[3] = round(max(0.0, min(1.0, axes.get('T', 0.5))) * 255)
    frame[4] = round(max(0.0, min(1.0, axes.get('N', 0.5))) * 255)
    frame[5] = round(max(0.0, min(1.0, axes.get('B', 0.5))) * 255)
    frame[6] = round(max(0.0, min(1.0, axes.get('A', 0.5))) * 255)
    frame[7] = frame[0]^frame[1]^frame[2]^frame[3]^frame[4]^frame[5]^frame[6]
    return bytes(frame)


def _connect(host: str, port: int) -> Optional[socket.socket]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((host, port))
        s.settimeout(None)
        print(f"[BRIDGE] Connected to QEMU COM1 at {host}:{port}", flush=True)
        return s
    except (ConnectionRefusedError, OSError) as e:
        print(f"[BRIDGE] COM1 not ready ({e}), retrying in 2s...", flush=True)
        return None


def run(systems: Dict[str, Any], host: str = "localhost", port: int = 4567,
        hz: float = 60.0, verbose: bool = False) -> None:
    """Stream axis frames to the ACM kernel. Blocks indefinitely."""
    interval = 1.0 / hz
    sock: Optional[socket.socket] = None
    frames_sent = 0
    start = time.monotonic()

    print(f"[BRIDGE] Starting aurora<->ACM bridge  target={host}:{port}  rate={hz:.0f} Hz",
          flush=True)

    while True:
        if sock is None:
            sock = _connect(host, port)
            if sock is None:
                time.sleep(2.0)
                continue

        t = time.monotonic() - start
        axes = get_axes(systems, t)
        frame = encode_frame(axes)

        try:
            sock.sendall(frame)
            frames_sent += 1
            if verbose and frames_sent % (int(hz) * 5) == 0:
                print(f"[BRIDGE] {frames_sent} frames  "
                      f"X={axes['X']:.2f} T={axes['T']:.2f} N={axes['N']:.2f} "
                      f"B={axes['B']:.2f} A={axes['A']:.2f}", flush=True)
        except (BrokenPipeError, OSError) as e:
            print(f"[BRIDGE] Connection lost ({e}), reconnecting...", flush=True)
            try:
                sock.close()
            except Exception:
                pass
            sock = None
            continue

        time.sleep(interval)


def _boot_minimal_systems() -> Dict[str, Any]:
    try:
        from aurora import boot_aurora
        print("[BRIDGE] Booting aurora subsurface stack...", flush=True)
        systems = boot_aurora(runtime_profile="subsurface", verbose=True)
        print("[BRIDGE] Aurora stack ready.", flush=True)
        return systems
    except Exception as e:
        print(f"[BRIDGE] Aurora boot failed ({e}); using harmonic drift.", flush=True)
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aurora<->ACM bridge: stream live axis frames to QEMU COM1.")
    parser.add_argument("--host",    default="localhost")
    parser.add_argument("--port",    type=int, default=4567)
    parser.add_argument("--hz",      type=float, default=60.0)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-boot", action="store_true",
                        help="Skip aurora boot; use harmonic drift only")
    args = parser.parse_args()

    systems = {} if args.no_boot else _boot_minimal_systems()
    run(systems, host=args.host, port=args.port, hz=args.hz, verbose=args.verbose)


if __name__ == "__main__":
    main()
