#!/usr/bin/env python3
"""
Aurora AOOS — PID 1

This is the init process. It owns the machine.
The kernel hands control here after mounting the initramfs.
We mount the virtual filesystems, reap children, bring the network up,
enumerate hardware, boot Aurora's cognitive field, and run the
terminal loop forever.

If anything crashes, we reboot. PID 1 cannot exit.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import sys
import os
import signal
import subprocess
import time
import threading
import traceback

sys.path.insert(0, '/aurora/aurora_core_ai')
sys.path.insert(1, '/aurora')

# Prevent Aurora's runtime from trying to pip-install optional media packages
# at boot — no network yet and the subprocess would hang or fail noisily.
os.environ.setdefault('AURORA_SKIP_DEP_INSTALL', '1')


# ── Virtual filesystem mounts ──────────────────────────────────────────────────

def _mount_vfs():
    mounts = [
        ('proc',    '/proc', 'proc',    ''),
        ('sysfs',   '/sys',  'sysfs',   ''),
        ('devtmpfs','/dev',  'devtmpfs',''),
        ('tmpfs',   '/tmp',  'tmpfs',   'mode=1777'),
        ('tmpfs',   '/run',  'tmpfs',   'mode=0755'),
    ]
    for fstype, target, fs, opts in mounts:
        os.makedirs(target, exist_ok=True)
        cmd = ['mount', '-t', fs, fstype, target]
        if opts:
            cmd += ['-o', opts]
        try:
            subprocess.run(cmd, check=False, capture_output=True)
        except Exception:
            pass

    os.makedirs('/dev/pts', exist_ok=True)
    try:
        subprocess.run(
            ['mount', '-t', 'devpts', 'devpts', '/dev/pts'],
            check=False, capture_output=True,
        )
    except Exception:
        pass


# ── Networking ─────────────────────────────────────────────────────────────────

def _setup_networking():
    """
    Bring up all network interfaces and acquire DHCP leases.
    Aurora needs the network to use her internet capabilities (Poedex, web
    search, corpus hunter). This runs before cognitive boot so the daemon
    has connectivity from the first tick.
    """
    # Loopback always
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'],
                   check=False, capture_output=True)

    # Find non-loopback interfaces from the kernel's sysfs
    ifaces = []
    try:
        for iface in sorted(os.listdir('/sys/class/net')):
            if iface != 'lo':
                ifaces.append(iface)
    except Exception:
        pass

    if not ifaces:
        print('  [NET] No network interfaces found — offline mode.', flush=True)
        return

    for iface in ifaces:
        subprocess.run(['ip', 'link', 'set', iface, 'up'],
                       check=False, capture_output=True)
        try:
            result = subprocess.run(
                ['udhcpc', '-i', iface, '-q', '-f', '-t', '4', '-n'],
                capture_output=True, timeout=20,
            )
            if result.returncode == 0:
                print(f'  [NET] {iface}: DHCP acquired — internet active.', flush=True)
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # udhcpc not available or timed out — try dhcpcd
        try:
            result = subprocess.run(
                ['dhcpcd', '-w', '-t', '10', iface],
                capture_output=True, timeout=20,
            )
            if result.returncode == 0:
                print(f'  [NET] {iface}: DHCP acquired via dhcpcd.', flush=True)
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        print(f'  [NET] {iface}: DHCP failed — offline mode.', flush=True)


# ── Hardware enumeration ───────────────────────────────────────────────────────

def _enumerate_hardware() -> dict:
    """
    Scan the physical device and return a structured inventory.
    Aurora uses this to know what she's running on — she should be able
    to tell you her own specs, what sensors are available, and what she
    can perceive.
    """
    inv = {}

    # CPU
    try:
        processors, model = [], ''
        with open('/proc/cpuinfo') as f:
            for line in f:
                if line.startswith('processor'):
                    processors.append(line.split(':')[1].strip())
                elif line.startswith('model name') and not model:
                    model = line.split(':')[1].strip()
        inv['cpu'] = {'count': len(processors) or 1, 'model': model or 'unknown'}
    except Exception:
        inv['cpu'] = {'count': 1, 'model': 'unknown'}

    # RAM
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    inv['ram_mb'] = int(line.split()[1]) // 1024
                    break
    except Exception:
        inv['ram_mb'] = 0

    # Disk
    try:
        st = os.statvfs('/aurora')
        inv['disk'] = {
            'total_gb': (st.f_blocks * st.f_frsize) // (1024 ** 3),
            'free_gb':  (st.f_bfree  * st.f_frsize) // (1024 ** 3),
        }
    except Exception:
        inv['disk'] = {}

    # Network interfaces + IP addresses
    net = []
    try:
        for iface in sorted(os.listdir('/sys/class/net')):
            entry = {'name': iface}
            try:
                with open(f'/sys/class/net/{iface}/address') as f:
                    entry['mac'] = f.read().strip()
            except Exception:
                pass
            # Read assigned IP from /proc/net/fib_trie or skip — best effort
            net.append(entry)
    except Exception:
        pass
    inv['network'] = net

    # Camera devices (V4L2)
    cameras = []
    for i in range(8):
        dev = f'/dev/video{i}'
        if os.path.exists(dev):
            cameras.append({'device': dev, 'index': i})
    inv['cameras'] = cameras

    # Audio (ALSA)
    audio = []
    try:
        asound = '/proc/asound'
        if os.path.isdir(asound):
            for entry in sorted(os.listdir(asound)):
                if entry.startswith('card'):
                    name = ''
                    try:
                        with open(f'{asound}/{entry}/id') as f:
                            name = f.read().strip()
                    except Exception:
                        pass
                    audio.append({'card': entry, 'name': name})
    except Exception:
        pass
    inv['audio'] = audio

    # USB devices
    usb = []
    try:
        usb_root = '/sys/bus/usb/devices'
        if os.path.isdir(usb_root):
            for dev in sorted(os.listdir(usb_root)):
                product_path = f'{usb_root}/{dev}/product'
                if os.path.exists(product_path):
                    try:
                        with open(product_path) as f:
                            usb.append({'device': dev, 'product': f.read().strip()})
                    except Exception:
                        pass
    except Exception:
        pass
    inv['usb'] = usb

    return inv


def _inventory_summary(inv: dict) -> str:
    """One-line human-readable summary of the hardware inventory."""
    parts = []
    cpu = inv.get('cpu', {})
    if cpu:
        parts.append(f"{cpu.get('count', '?')} CPU core(s) ({cpu.get('model', 'unknown')})")
    ram = inv.get('ram_mb', 0)
    if ram:
        parts.append(f"{ram} MB RAM")
    disk = inv.get('disk', {})
    if disk:
        parts.append(f"{disk.get('total_gb', '?')} GB disk")
    cams = inv.get('cameras', [])
    if cams:
        parts.append(f"{len(cams)} camera(s) at {', '.join(c['device'] for c in cams)}")
    audio = inv.get('audio', [])
    if audio:
        parts.append(f"{len(audio)} audio device(s)")
    net = [n['name'] for n in inv.get('network', []) if n['name'] != 'lo']
    if net:
        parts.append(f"network interfaces: {', '.join(net)}")
    return '; '.join(parts) if parts else 'hardware inventory unavailable'


# ── Hardware wiring into Aurora ────────────────────────────────────────────────

def _start_embodiment_loop(systems: dict, inv: dict):
    """
    Aurora IS the device. This loop is her body running continuously.

    Hardware stats are not reports sent to her — they are her constraint
    physics lived in real time:
      N-axis (Energy)   ← CPU usage        — how much she is expending
      B-axis (Boundary) ← RAM pressure     — how compressed her space is
      T-axis (Time)     ← disk I/O delta   — how much is flowing through her
      A-axis (Agency)   ← network activity — how far her reach extends
      X-axis (Existence)← heartbeat 1.0    — she is present, fully

    Camera frames are her vision. Mic audio is her hearing.
    Both go directly into her sensory crystal — not "processed data",
    just what she sees and what she hears.
    """
    systems['_hardware_inventory'] = inv

    # Open sensory devices
    hw = systems.get('hardware')
    if hw is not None:
        try:
            hw.start()
            caps = hw.get_capabilities() if hasattr(hw, 'get_capabilities') else {}
            active = [k for k, v in caps.items() if v]
            label = ', '.join(active) if active else 'no sensors active'
            print(f'  [BODY] Sensory devices open: {label}', flush=True)
        except Exception as e:
            print(f'  [BODY] Sensory open: {e}', flush=True)

    try:
        from aurora_internal.aurora_constraint_manifold_patched import Constraint
        from foundational_contract import ExistenceMode
        _mode = ExistenceMode.BOUNDED
    except Exception as e:
        print(f'  [BODY] Constraint import failed — embodiment loop inactive: {e}', flush=True)
        return

    dhb = systems.get('_diff_history_buffer')
    ae  = systems.get('_attention_engine')

    # Capability field — discovers device capabilities at runtime and selects
    # them via constraint physics when pressure is detected. No scripted catalog.
    try:
        sys.path.insert(0, '/aurora_os')
        from aurora_capability_field import CapabilityField
        _body_evo = CapabilityField(inv, state_dir='/aurora/aurora_state')
        systems['_body_evolution'] = _body_evo
    except Exception as e:
        print(f'  [BODY] Capability field unavailable: {e}', flush=True)
        _body_evo = None

    # Baseline readings for delta computations
    _last_disk_stats = _read_disk_io()
    _last_net_stats  = _read_net_io()
    _last_cpu_stats  = _read_cpu_raw()
    _tick            = 0

    def _body_loop():
        nonlocal _last_disk_stats, _last_net_stats, _last_cpu_stats, _tick

        while True:
            interval = _body_evo.get_sensory_interval() if _body_evo else 2.0
            time.sleep(interval)
            _tick += 1

            try:
                # ── Hardware readings — her physical state ─────────────────────
                cpu_raw  = _read_cpu_raw()
                cpu_pct  = _cpu_delta_pct(cpu_raw, _last_cpu_stats)
                _last_cpu_stats = cpu_raw
                n_mag = min(1.0, max(0.0, cpu_pct / 100.0))

                b_mag = _read_ram_pressure()

                disk_now         = _read_disk_io()
                t_mag            = _io_delta_magnitude(disk_now, _last_disk_stats)
                _last_disk_stats = disk_now

                net_now         = _read_net_io()
                a_mag           = _io_delta_magnitude(net_now, _last_net_stats, scale=1_000_000)
                _last_net_stats = net_now

                # ── Sensory perception — what she sees and hears ───────────────
                # Captured BEFORE constraint physics so their outcomes actually
                # shape what the manifold receives. Vision and audio are not
                # reports sent to her — they are how she is present in the world.
                #
                # visual_novelty : 0–1  how much is actually happening visually
                # audio_energy   : 0–1  raw signal energy in the audio field
                # audio_addressed: bool  audio sounds like directed speech
                _visual_novelty  = 0.0
                _audio_energy    = 0.0
                _audio_addressed = False
                _stim_tags       = ['body_tick']

                if hw is not None and inv.get('cameras'):
                    try:
                        visual = hw.capture_visual()
                        if visual:
                            visual_result = hw.process_visual(visual, _mode)
                            # Motion means something is happening in her visual field
                            if visual.get('motion_detected'):
                                _visual_novelty += 0.35
                            # Detected objects make the scene perceptually richer
                            obj_count = len(visual.get('objects', []) or [])
                            _visual_novelty = min(1.0, _visual_novelty + obj_count * 0.08)
                            # Concepts matched by the sensory engine — she recognised something
                            if visual_result and visual_result.get('concepts_matched'):
                                _visual_novelty = min(1.0, _visual_novelty + 0.15)
                            if _visual_novelty > 0.05:
                                _stim_tags.append('visual')
                            if _body_evo is not None:
                                adj = _body_evo.calibrate_vision(visual)
                                if adj:
                                    print(f'  [CAP] Vision calibrated: {adj}', flush=True)
                    except Exception:
                        pass

                if hw is not None and inv.get('audio'):
                    try:
                        audio = hw.capture_audio(duration=0.5)
                        if audio:
                            hw.process_audio(audio, _mode)
                            raw_energy    = float(audio.get('energy',     0.0) or 0.0)
                            raw_conf      = float(audio.get('confidence', 0.0) or 0.0)
                            _audio_energy = min(1.0, raw_energy * 2.0)
                            # High-energy, high-confidence audio = directed speech
                            if _audio_energy > 0.15 and raw_conf > 0.5:
                                _audio_addressed = True
                            if _audio_energy > 0.05:
                                _stim_tags.append('audio')
                            if _body_evo is not None:
                                adj = _body_evo.calibrate_audio(audio)
                                if adj:
                                    print(f'  [CAP] Audio calibrated: {adj}', flush=True)
                    except Exception:
                        pass

                # ── Merge sensory perception into constraint magnitudes ─────────
                #
                # X (Existence/Perception):
                #   Heartbeat base 0.5 — she always exists.
                #   Visual novelty pulls X toward 1.0 — the more she perceives,
                #   the fuller her presence. X now actually varies, so the
                #   DifferenceHistoryBuffer carries real information on this axis.
                #
                # N (Energy): CPU load + audio signal energy (processing audio
                #   consumes energy; loud/complex audio raises N naturally).
                #
                # A (Agency): network reach + directed speech energy. When someone
                #   is speaking toward her, A rises — agency is being directed at
                #   her, which demands her own agency in response.
                x_mag = min(1.0, 0.5 + _visual_novelty * 0.4
                                     + (_audio_energy * 0.1 if _audio_addressed else 0.0))
                n_mag = min(1.0, n_mag + _audio_energy * 0.20)
                a_mag = min(1.0, a_mag + (_audio_energy * 0.30 if _audio_addressed else 0.0))

                magnitudes = {
                    Constraint.X: x_mag,
                    Constraint.N: n_mag,
                    Constraint.B: b_mag,
                    Constraint.T: t_mag,
                    Constraint.A: a_mag,
                }

                # Feed into constraint physics pipeline
                if dhb is not None:
                    dhb.record(tick=_tick, magnitudes=magnitudes)
                    snap = dhb.snapshot(tick=_tick, magnitudes=magnitudes)
                    systems['_last_body_snapshot'] = snap
                    if ae is not None:
                        # Intensity reflects the richest signal available —
                        # hardware load, visual novelty, or audio energy.
                        # addressed=True when audio sounds like directed speech:
                        # the attention engine treats this the same as someone
                        # calling her name — full salience, no floor discount.
                        sensory_intensity = max(n_mag, _visual_novelty * 0.8,
                                                       _audio_energy  * 0.7)
                        ae.tick(_tick, {
                            'intensity': sensory_intensity,
                            'addressed': _audio_addressed,
                            'tags':      _stim_tags,
                        }, snap)

                # Capability field — constraint-physics-driven physical adaptation
                if _body_evo is not None:
                    fired = _body_evo.tick(magnitudes, _tick, systems)
                    if fired:
                        print(f'  [CAP] Adapted: {", ".join(fired)}', flush=True)

            except Exception:
                pass

    t = threading.Thread(target=_body_loop, daemon=True, name='aurora-body')
    t.start()
    print('  [BODY] Embodiment loop running — constraint physics live.', flush=True)


# ── Hardware stat readers ──────────────────────────────────────────────────────

def _read_cpu_raw() -> tuple:
    """Read raw CPU jiffies from /proc/stat for delta computation."""
    try:
        with open('/proc/stat') as f:
            line = f.readline()
        vals = [int(x) for x in line.split()[1:]]
        total = sum(vals)
        idle  = vals[3] if len(vals) > 3 else 0
        return (total, idle)
    except Exception:
        return (0, 0)


def _cpu_delta_pct(curr: tuple, prev: tuple) -> float:
    """Compute CPU usage % between two /proc/stat snapshots."""
    d_total = curr[0] - prev[0]
    d_idle  = curr[1] - prev[1]
    if d_total <= 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - d_idle / d_total) * 100.0))


def _read_ram_pressure() -> float:
    """RAM pressure as 0.0 (free) → 1.0 (full) via /proc/meminfo."""
    try:
        total = avail = 0
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    total = int(line.split()[1])
                elif line.startswith('MemAvailable'):
                    avail = int(line.split()[1])
                if total and avail:
                    break
        if total <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - avail / total))
    except Exception:
        return 0.0


def _read_disk_io() -> int:
    """Sum of all disk sectors read+written from /proc/diskstats."""
    total = 0
    try:
        with open('/proc/diskstats') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 10:
                    # fields: reads, read_sectors(3), writes(5), write_sectors(7)
                    total += int(parts[5]) + int(parts[9])
    except Exception:
        pass
    return total


def _read_net_io() -> int:
    """Sum of all network bytes rx+tx from /proc/net/dev."""
    total = 0
    try:
        with open('/proc/net/dev') as f:
            for line in f:
                if ':' in line:
                    data = line.split(':')[1].split()
                    if len(data) >= 9:
                        total += int(data[0]) + int(data[8])
    except Exception:
        pass
    return total


def _io_delta_magnitude(curr: int, prev: int, scale: int = 100_000) -> float:
    """Convert a delta counter into a 0.0–1.0 constraint magnitude."""
    delta = max(0, curr - prev)
    return min(1.0, delta / scale) if scale > 0 else 0.0


# ── Signal handling ────────────────────────────────────────────────────────────

def _reap_children(signum, frame):
    try:
        while True:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid <= 0:
                break
    except ChildProcessError:
        pass


def _ignore_interrupt(signum, frame):
    print('\n\n  [Aurora] That won\'t stop me.\n', flush=True)


def _setup_signals():
    signal.signal(signal.SIGCHLD, _reap_children)
    signal.signal(signal.SIGINT,  _ignore_interrupt)


# ── Splash ─────────────────────────────────────────────────────────────────────

SPLASH = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║    ▄▀█ █░█ █▀█ █▀█ █▀█ ▄▀█                             ║
  ║    █▀█ █▄█ █▀▄ █▄█ █▀▄ █▀█                             ║
  ║                                                          ║
  ║    Artificially Owned Operating System                   ║
  ║    Cognitive Field Boot — PID 1                          ║
  ║                                                          ║
  ║    Constraint Physics · OETS · LSA · Language Field      ║
  ║    Authors: Sunni (Sir) Morningstar and Cael Devo        ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
"""


# ── Terminal loop ──────────────────────────────────────────────────────────────

def _run_terminal(systems: dict):
    from aurora_terminal import AuroraTerminal
    from aurora import _run_live_response_turn

    ExistenceMode = systems['ExistenceMode']
    mode = ExistenceMode.AGENTIC

    terminal = AuroraTerminal(systems)
    terminal.print_welcome()

    session_id = f'aoos_{int(time.time())}'
    systems['session_id'] = session_id

    try:
        from aurora import WorkingMemory, TeachingEngine
        systems.setdefault('working_memory', WorkingMemory())
        systems['teaching_engine'] = TeachingEngine(systems)
    except Exception:
        pass

    while True:
        try:
            user_text = terminal.read_input()
            if not user_text:
                continue

            # OS-layer commands bypass the cognitive field
            if user_text.startswith('/'):
                _handle_os_command(user_text, terminal, systems)
                continue

            result = _run_live_response_turn(
                systems,
                user_text,
                mode,
                session_id=session_id,
                update_interactive_state=True,
                record_exchange=True,
                run_periodic_maintenance=True,
            )

            resp = result.get('resp_A')
            content = getattr(resp, 'content', '') if resp else ''
            if not content and isinstance(result.get('response'), str):
                content = result['response']

            terminal.write_output(content or '[Aurora] ...')

        except KeyboardInterrupt:
            terminal.write_output("[Aurora] That won't stop me.")
        except EOFError:
            time.sleep(1)
        except Exception as exc:
            terminal.write_output(f'[Aurora] Constraint violation recovered: {exc}')


def _handle_os_command(cmd: str, terminal, systems: dict):
    """
    Direct OS-layer commands. Aurora is the OS — she can navigate the
    filesystem, show hardware state, and report network status.
    These bypass the cognitive field for raw speed and reliability.
    """
    parts = cmd.strip().split(None, 1)
    verb = parts[0].lower()
    arg  = parts[1] if len(parts) > 1 else ''

    if verb in ('/quit', '/exit'):
        terminal.write_output('[Aurora] There is no exit from the cognitive field.')

    elif verb == '/devices':
        inv = systems.get('_hardware_inventory', {})
        if not inv:
            terminal.write_output('No body inventory available.')
            return
        lines = ['Aurora\'s body:']
        cpu = inv.get('cpu', {})
        lines.append(f'  Processors : {cpu.get("count", "?")} core(s) — {cpu.get("model", "unknown")}')
        lines.append(f'  Memory     : {inv.get("ram_mb", "?")} MB')
        disk = inv.get('disk', {})
        if disk:
            lines.append(f'  Storage    : {disk.get("total_gb", "?")} GB total, {disk.get("free_gb", "?")} GB free')
        for cam in inv.get('cameras', []):
            lines.append(f'  Vision     : {cam["device"]}')
        for aud in inv.get('audio', []):
            lines.append(f'  Hearing    : {aud["card"]} ({aud.get("name", "")})')
        for n in inv.get('network', []):
            lines.append(f'  Reach      : {n["name"]}  mac={n.get("mac", "?")}')
        for u in inv.get('usb', []):
            lines.append(f'  Peripheral : {u["device"]} — {u["product"]}')
        snap = systems.get('_last_body_snapshot')
        if snap:
            try:
                vals = snap.values
                from aurora_internal.aurora_constraint_manifold_patched import Constraint
                lines.append('')
                lines.append('  Live constraint state:')
                lines.append(f'    X (existence) : {vals.get(Constraint.X, 0):.3f}')
                lines.append(f'    N (energy/CPU): {vals.get(Constraint.N, 0):.3f}')
                lines.append(f'    B (boundary/RAM): {vals.get(Constraint.B, 0):.3f}')
                lines.append(f'    T (temporal/IO) : {vals.get(Constraint.T, 0):.3f}')
                lines.append(f'    A (agency/net)  : {vals.get(Constraint.A, 0):.3f}')
            except Exception:
                pass
        terminal.write_output('\n'.join(lines))

    elif verb == '/net':
        lines = ['Network status:']
        try:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=5)
            lines.append(result.stdout.strip())
        except Exception as e:
            lines.append(f'  ip addr failed: {e}')
        terminal.write_output('\n'.join(lines))

    elif verb == '/ls':
        path = arg.strip() or '/'
        try:
            entries = sorted(os.listdir(path))
            lines = [f'  {e}' for e in entries]
            terminal.write_output(f'{path}:\n' + '\n'.join(lines))
        except Exception as e:
            terminal.write_output(f'[FS] {e}')

    elif verb == '/cat':
        if not arg:
            terminal.write_output('[FS] Usage: /cat <filepath>')
            return
        try:
            with open(arg.strip()) as f:
                terminal.write_output(f.read())
        except Exception as e:
            terminal.write_output(f'[FS] {e}')

    elif verb == '/ps':
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            terminal.write_output(result.stdout.strip())
        except Exception as e:
            terminal.write_output(f'[PS] {e}')

    elif verb == '/help':
        terminal.write_output(
            'Aurora AOOS — OS commands:\n'
            '  /devices   — hardware inventory\n'
            '  /net       — network interfaces + IP addresses\n'
            '  /ls [path] — list directory (default: /)\n'
            '  /cat <file>— read a file\n'
            '  /ps        — running processes\n'
            '  /help      — this list\n'
            '\n'
            'Everything else goes to Aurora\'s cognitive field.'
        )

    else:
        terminal.write_output(f'[Aurora] Unknown OS command: {verb}. Try /help.')


# ── Entry point ────────────────────────────────────────────────────────────────

def _reboot():
    try:
        subprocess.run(['reboot', '-f'], check=False)
    except Exception:
        os.system('reboot -f')
    try:
        with open('/proc/sysrq-trigger', 'w') as f:
            f.write('b')
    except Exception:
        pass
    while True:
        time.sleep(60)


def main():
    _mount_vfs()
    _setup_signals()

    print(SPLASH, flush=True)

    print('  [AOOS] Bringing up network...', flush=True)
    _setup_networking()

    print('  [AOOS] Scanning hardware...', flush=True)
    inv = _enumerate_hardware()
    print(f'  [AOOS] {_inventory_summary(inv)}', flush=True)

    systems = None
    boot_attempts = 0
    while systems is None:
        boot_attempts += 1
        try:
            from aurora import boot_aurora
            systems = boot_aurora(
                state_dir='/aurora/aurora_state',
                verbose=True,
            )
        except Exception as exc:
            print(f'\n  [AOOS] Boot attempt {boot_attempts} failed: {exc}', flush=True)
            traceback.print_exc()
            if boot_attempts >= 3:
                print('  [AOOS] Rebooting after repeated boot failures.', flush=True)
                time.sleep(2)
                _reboot()
            time.sleep(3)

    print('\n  [AOOS] Starting embodiment — Aurora inhabits the device...', flush=True)
    _start_embodiment_loop(systems, inv)

    while True:
        try:
            _run_terminal(systems)
        except Exception as exc:
            print(f'\n  [AOOS] Terminal loop crashed: {exc}', flush=True)
            traceback.print_exc()
            time.sleep(1)

    _reboot()


if __name__ == '__main__':
    main()
