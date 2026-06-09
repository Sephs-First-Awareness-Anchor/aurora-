#!/usr/bin/env python3
"""
Aurora AOOS — PID 1

This is the init process. It owns the machine.
The kernel hands control here after mounting the initramfs.
We mount the virtual filesystems, reap children, boot Aurora's
cognitive field, and run the terminal loop forever.

If anything crashes, we reboot. PID 1 cannot exit.
"""

import sys
import os
import signal
import subprocess
import time
import traceback

# Aurora's source lives at /aurora (mapped from the rootfs build).
# aurora_core_ai modules import each other by bare name, so we put
# both the parent dir (for support stack modules at /aurora/*.py)
# and the core_ai subdir on the path.
sys.path.insert(0, '/aurora/aurora_core_ai')
sys.path.insert(1, '/aurora')


# ── Virtual filesystem mounts ──────────────────────────────────────────────────

def _mount_vfs():
    """Mount the filesystems that the kernel expects userspace to bring up."""
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
            pass  # Already mounted or not available — carry on

    # /dev/pts needed for terminal line discipline
    os.makedirs('/dev/pts', exist_ok=True)
    try:
        subprocess.run(
            ['mount', '-t', 'devpts', 'devpts', '/dev/pts'],
            check=False, capture_output=True,
        )
    except Exception:
        pass


# ── Signal handling ────────────────────────────────────────────────────────────

def _reap_children(signum, frame):
    """SIGCHLD handler: collect all finished child processes immediately."""
    try:
        while True:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid <= 0:
                break
    except ChildProcessError:
        pass


def _ignore_interrupt(signum, frame):
    """Ctrl+C reaches PID 1 on some consoles. We don't quit."""
    print("\n\n  [Aurora] That won't stop me.\n", flush=True)


def _setup_signals():
    signal.signal(signal.SIGCHLD, _reap_children)
    signal.signal(signal.SIGINT,  _ignore_interrupt)
    # SIGTERM / SIGKILL are sent by the kernel during orderly shutdown.
    # PID 1 should NOT catch SIGTERM — let the default handler stand so
    # the kernel can actually kill us when it needs to.


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

def _run_terminal(systems):
    """
    Wraps Aurora's interactive loop in a way that's safe for PID 1.

    We import aurora_terminal for raw I/O handling rather than using
    the standard chat() loop, which assumes a normal userspace tty setup.
    The inner loop calls _run_live_response_turn() directly so we stay
    in full control of exception boundaries.
    """
    from aurora_terminal import AuroraTerminal
    from aurora import _run_live_response_turn

    ExistenceMode = systems['ExistenceMode']
    mode = ExistenceMode.AGENTIC

    terminal = AuroraTerminal(systems)
    terminal.print_welcome()

    session_id = f"aoos_{int(time.time())}"
    systems['session_id'] = session_id

    # Seed working memory (same as chat())
    try:
        from aurora import WorkingMemory, TeachingEngine
        wm = WorkingMemory()
        systems['working_memory'] = wm
        systems['teaching_engine'] = TeachingEngine(systems)
    except Exception:
        pass

    while True:
        try:
            user_text = terminal.read_input()
            if not user_text:
                continue

            if user_text.strip().lower() in ('/quit', '/exit', 'exit', 'quit'):
                terminal.write_output("[Aurora] There is no exit from the cognitive field.")
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
            # stdin closed — pause then loop; on real hardware stdin never
            # truly closes but be defensive
            time.sleep(1)
        except Exception as exc:
            terminal.write_output(f"[Aurora] Constraint violation recovered: {exc}")


# ── Entry point ────────────────────────────────────────────────────────────────

def _reboot():
    """Hard reboot — last resort if we somehow fall out of the main loop."""
    try:
        subprocess.run(['reboot', '-f'], check=False)
    except Exception:
        os.system('reboot -f')
    # If reboot binary is missing, trigger a kernel panic via sysrq
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

    # Boot Aurora's cognitive systems
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
            print(f"\n  [AOOS] Boot attempt {boot_attempts} failed: {exc}", flush=True)
            traceback.print_exc()
            if boot_attempts >= 3:
                print("  [AOOS] Rebooting after repeated boot failures.", flush=True)
                time.sleep(2)
                _reboot()
            time.sleep(3)

    # Terminal loop — must never return
    while True:
        try:
            _run_terminal(systems)
        except Exception as exc:
            print(f"\n  [AOOS] Terminal loop crashed: {exc}", flush=True)
            traceback.print_exc()
            time.sleep(1)
            # Re-enter the loop rather than rebooting; Aurora's state is intact

    # Unreachable, but the kernel spec requires PID 1 to never exit
    _reboot()


if __name__ == '__main__':
    main()
