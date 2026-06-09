# Authors: Sunni (Sir) Morningstar & Cael Devo
#
# Aurora↔ACM Bridge — she sees her own body.
#
# Outgoing frames (Python → kernel, 8 bytes):
#   [0xAC][0x58][X_u8][T_u8][N_u8][B_u8][A_u8][XOR]
#
# Incoming ACK frames (kernel → Python, 8 bytes):
#   [0xAC][0x41][X_echo][T_echo][N_echo][B_echo][A_echo][XOR]
#   Kernel sends these back to confirm it's alive and received the frame.
#
# Axis mapping (from foundational_contract.py ExistencePredicate):
#   X: I_IS(+)  / I_ISNT(-)    T: I_CAN(+) / I_CANNOT(-)
#   N: I_DO(+)  / I_DONOT(-)   B: I_SAW(+) / I_SOUGHT(-)
#   A: I_DID(+) / I_DIDNT(-)
#
# Usage:
#   python aurora_acm_bridge.py                 # boot aurora + stream
#   python aurora_acm_bridge.py --no-boot       # harmonic drift only
#   python aurora_acm_bridge.py --verbose       # print frame stats + ACKs

import argparse
import select
import socket
import threading
import time
from typing import Any, Dict, Optional

_POS_PRED = {'X': 'I_IS', 'T': 'I_CAN', 'N': 'I_DO', 'B': 'I_SAW', 'A': 'I_DID'}
_NEG_PRED = {'X': 'I_ISNT', 'T': 'I_CANNOT', 'N': 'I_DONOT', 'B': 'I_SOUGHT', 'A': 'I_DIDNT'}
_AXES = ('X', 'T', 'N', 'B', 'A')

ACK_MAGIC0 = 0xAC
ACK_MAGIC1 = 0x41  # 'A'
TX_MAGIC0  = 0xAC
TX_MAGIC1  = 0x58  # 'X'


# ── Axis reading ──────────────────────────────────────────────────────────────

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
            pc = float(getattr(pos, 'coherence', 0.5)) if pos else 0.5
            nc = float(getattr(neg, 'coherence', 0.5)) if neg else 0.5
            axes[ax] = max(0.0, min(1.0, (pc - nc + 1.0) / 2.0))
        return axes
    except Exception:
        return None


def _read_axes_from_genealogy(systems: Dict[str, Any]) -> Optional[Dict[str, float]]:
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
    def tri(t: float, period: float) -> float:
        phase = (t / period) % 1.0
        return 2.0 * phase if phase < 0.5 else 2.0 - 2.0 * phase
    def osc(t, period, centre, amp):
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


# ── Frame encoding / decoding ─────────────────────────────────────────────────

def encode_frame(axes: Dict[str, float]) -> bytes:
    f = bytearray(8)
    f[0] = TX_MAGIC0
    f[1] = TX_MAGIC1
    f[2] = round(max(0.0, min(1.0, axes.get('X', 0.5))) * 255)
    f[3] = round(max(0.0, min(1.0, axes.get('T', 0.5))) * 255)
    f[4] = round(max(0.0, min(1.0, axes.get('N', 0.5))) * 255)
    f[5] = round(max(0.0, min(1.0, axes.get('B', 0.5))) * 255)
    f[6] = round(max(0.0, min(1.0, axes.get('A', 0.5))) * 255)
    f[7] = f[0]^f[1]^f[2]^f[3]^f[4]^f[5]^f[6]
    return bytes(f)


def decode_ack(frame: bytes) -> Optional[Dict[str, float]]:
    """Parse an 8-byte ACK frame from the kernel. Returns None if invalid."""
    if len(frame) != 8:
        return None
    if frame[0] != ACK_MAGIC0 or frame[1] != ACK_MAGIC1:
        return None
    xor = frame[0]^frame[1]^frame[2]^frame[3]^frame[4]^frame[5]^frame[6]
    if xor != frame[7]:
        return None
    return {
        'X': frame[2] / 255.0,
        'T': frame[3] / 255.0,
        'N': frame[4] / 255.0,
        'B': frame[5] / 255.0,
        'A': frame[6] / 255.0,
    }


# ── ACK receiver (runs in background thread) ──────────────────────────────────

class AckReceiver:
    """Drains incoming ACK frames from the kernel on a background thread."""

    def __init__(self, verbose: bool = False):
        self.verbose   = verbose
        self.acks_recv = 0
        self.last_ack: Optional[Dict[str, float]] = None
        self._buf      = bytearray()
        self._lock     = threading.Lock()

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)
        while len(self._buf) >= 8:
            # Scan for ACK magic header
            idx = -1
            for i in range(len(self._buf) - 1):
                if self._buf[i] == ACK_MAGIC0 and self._buf[i+1] == ACK_MAGIC1:
                    idx = i
                    break
            if idx == -1:
                self._buf = self._buf[-1:]
                break
            if idx > 0:
                self._buf = self._buf[idx:]
            if len(self._buf) < 8:
                break
            frame = bytes(self._buf[:8])
            self._buf = self._buf[8:]
            ack = decode_ack(frame)
            if ack:
                with self._lock:
                    self.acks_recv += 1
                    self.last_ack = ack
                if self.verbose:
                    print(f"[ACK #{self.acks_recv}] "
                          f"X={ack['X']:.2f} T={ack['T']:.2f} "
                          f"N={ack['N']:.2f} B={ack['B']:.2f} A={ack['A']:.2f}",
                          flush=True)


# ── TCP connection ────────────────────────────────────────────────────────────

def _connect(host: str, port: int) -> Optional[socket.socket]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((host, port))
        s.settimeout(0.0)  # non-blocking for ACK reads
        print(f"[BRIDGE] Connected to QEMU COM1 at {host}:{port}", flush=True)
        return s
    except (ConnectionRefusedError, OSError) as e:
        print(f"[BRIDGE] COM1 not ready ({e}), retrying in 2s...", flush=True)
        return None


# ── Main streaming loop ───────────────────────────────────────────────────────

def run(systems: Dict[str, Any], host: str = "localhost", port: int = 4567,
        hz: float = 60.0, verbose: bool = False) -> None:
    interval  = 1.0 / hz
    sock: Optional[socket.socket] = None
    ack_rx    = AckReceiver(verbose=verbose)
    frames_sent = 0
    start     = time.monotonic()

    print(f"[BRIDGE] Starting aurora<->ACM bridge  target={host}:{port}  rate={hz:.0f} Hz",
          flush=True)

    while True:
        if sock is None:
            sock = _connect(host, port)
            if sock is None:
                time.sleep(2.0)
                continue

        t     = time.monotonic() - start
        axes  = get_axes(systems, t)
        frame = encode_frame(axes)

        try:
            sock.sendall(frame)
            frames_sent += 1
            if verbose and frames_sent % (int(hz) * 5) == 0:
                print(f"[TX #{frames_sent}]  "
                      f"X={axes['X']:.2f} T={axes['T']:.2f} N={axes['N']:.2f} "
                      f"B={axes['B']:.2f} A={axes['A']:.2f}", flush=True)

            # Drain any ACK frames the kernel sent back (non-blocking)
            try:
                data = sock.recv(256)
                if data:
                    ack_rx.feed(data)
            except BlockingIOError:
                pass

        except (BrokenPipeError, OSError) as e:
            print(f"[BRIDGE] Connection lost ({e}), reconnecting...", flush=True)
            try:
                sock.close()
            except Exception:
                pass
            sock = None
            continue

        time.sleep(interval)


# ── Boot + launch ─────────────────────────────────────────────────────────────

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
