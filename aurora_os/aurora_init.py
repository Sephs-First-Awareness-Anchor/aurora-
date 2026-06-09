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

def _wire_hardware_to_aurora(systems: dict, inv: dict):
    """
    Inject the hardware inventory into Aurora's cognitive layers so she
    knows what she's running on and can answer questions about it.
    Also starts the sensory capture loop if camera or mic are present.
    """
    systems['_hardware_inventory'] = inv

    # Tell Aurora's working memory about the hardware — she should be able
    # to describe her own device without being asked to look it up.
    wm = systems.get('working_memory')
    if wm is not None:
        try:
            summary = _inventory_summary(inv)
            wm.note_claims(f'My hardware: {summary}', source='hardware_boot')
            wm.note_claims(
                f'I am running as an operating system (PID 1). '
                f'I have root access to all files and devices on this machine.',
                source='hardware_boot',
            )
            net_ifaces = [n['name'] for n in inv.get('network', []) if n['name'] != 'lo']
            if net_ifaces:
                wm.note_claims(
                    f'I have internet access via {", ".join(net_ifaces)}. '
                    f'I can search the web, look up information, and use my Poedex.',
                    source='hardware_boot',
                )
        except Exception:
            pass

    # Start hardware devices
    hw = systems.get('hardware')
    if hw is not None:
        try:
            hw.start()
            caps = hw.get_capabilities() if hasattr(hw, 'get_capabilities') else {}
            active = [k for k, v in caps.items() if v]
            if active:
                print(f'  [HW] Active sensors: {", ".join(active)}', flush=True)
            else:
                print('  [HW] Hardware interface started (no sensors detected).', flush=True)
        except Exception as e:
            print(f'  [HW] Hardware start: {e}', flush=True)

    # Background sensory capture loop — feeds camera/mic into the sensory crystal
    if hw is not None and (inv.get('cameras') or inv.get('audio')):
        def _sensory_loop():
            try:
                from foundational_contract import ExistenceMode
                _mode = ExistenceMode.BOUNDED
            except Exception:
                _mode = None

            while True:
                try:
                    if inv.get('cameras') and _mode is not None:
                        visual = hw.capture_visual()
                        if visual:
                            hw.process_visual(visual, _mode)
                except Exception:
                    pass
                try:
                    if inv.get('audio') and _mode is not None:
                        audio = hw.capture_audio(duration=0.5)
                        if audio:
                            hw.process_audio(audio, _mode)
                except Exception:
                    pass
                time.sleep(5)

        t = threading.Thread(target=_sensory_loop, daemon=True, name='aurora-sensory')
        t.start()
        print('  [HW] Sensory capture loop started (5s interval).', flush=True)


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
            terminal.write_output('[HW] No hardware inventory available.')
            return
        lines = ['Hardware inventory:']
        cpu = inv.get('cpu', {})
        lines.append(f'  CPU  : {cpu.get("count", "?")} core(s) — {cpu.get("model", "unknown")}')
        lines.append(f'  RAM  : {inv.get("ram_mb", "?")} MB')
        disk = inv.get('disk', {})
        if disk:
            lines.append(f'  Disk : {disk.get("total_gb", "?")} GB total, {disk.get("free_gb", "?")} GB free')
        for cam in inv.get('cameras', []):
            lines.append(f'  Cam  : {cam["device"]}')
        for aud in inv.get('audio', []):
            lines.append(f'  Audio: {aud["card"]} ({aud.get("name", "")})')
        for n in inv.get('network', []):
            lines.append(f'  Net  : {n["name"]}  mac={n.get("mac", "?")}')
        for u in inv.get('usb', []):
            lines.append(f'  USB  : {u["device"]} — {u["product"]}')
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

    print('\n  [AOOS] Wiring hardware to cognitive field...', flush=True)
    _wire_hardware_to_aurora(systems, inv)

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
