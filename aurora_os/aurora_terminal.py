#!/usr/bin/env python3
"""
Aurora AOOS — Terminal I/O layer

Handles raw console I/O for the Aurora cognitive field session.
On a bare-metal serial console or VGA tty inside initramfs there is no
readline, no curses, and no pty magic — we keep it simple and robust.
"""

import sys
import os
import time
import signal


# ANSI codes — only used when the terminal supports them
_RESET   = '\033[0m'
_BOLD    = '\033[1m'
_CYAN    = '\033[36m'
_YELLOW  = '\033[33m'
_GREEN   = '\033[32m'
_DIM     = '\033[2m'
_RED     = '\033[31m'


def _tty_supports_ansi() -> bool:
    """Best-effort check: does the current stdout support ANSI escapes?"""
    term = os.environ.get('TERM', '')
    if term in ('dumb', ''):
        return False
    try:
        return os.isatty(sys.stdout.fileno())
    except Exception:
        return False


class AuroraTerminal:
    """
    Minimal terminal wrapper for PID-1 console operation.

    Reads lines from stdin (blocking), writes formatted output to stdout.
    Does not use readline or any library that requires a real pty.
    """

    def __init__(self, systems: dict):
        self._systems = systems
        self._ansi = _tty_supports_ansi()
        self._turn = 0

    # ── Formatting helpers ────────────────────────────────────────────────────

    def _c(self, code: str, text: str) -> str:
        if self._ansi:
            return f'{code}{text}{_RESET}'
        return text

    def _prompt_str(self) -> str:
        indicator = self._constraint_indicator()
        if indicator and self._ansi:
            return f'{_CYAN}[{indicator}]{_RESET} {_BOLD}You:{_RESET} '
        return 'You: '

    def _constraint_indicator(self) -> str:
        """
        Pull a one-character constraint state summary if available.
        Returns '' when the constraint system isn't reachable.
        """
        try:
            consciousness = self._systems.get('consciousness')
            if consciousness is None:
                return ''
            state = {}
            if hasattr(consciousness, 'get_state'):
                state = consciousness.get_state() or {}
            elif hasattr(consciousness, 'get_system_state'):
                state = consciousness.get_system_state() or {}

            entropy = float(state.get('entropy', state.get('dce_entropy', -1)) or -1)
            if entropy < 0:
                return ''
            if entropy < 0.3:
                return '●'   # low entropy — high coherence
            elif entropy < 0.7:
                return '◑'   # mid
            else:
                return '○'   # high entropy — active divergence
        except Exception:
            return ''

    # ── Welcome banner ────────────────────────────────────────────────────────

    def print_welcome(self):
        width = 58
        border = self._c(_CYAN, '  ' + '─' * width)
        print()
        print(border)
        print(self._c(_BOLD, '  Aurora AOOS — Cognitive Field Terminal'))
        print(self._c(_DIM,  '  Type your input. Press Enter to send.'))
        print(self._c(_DIM,  '  /quit has no effect — the field persists.'))
        print(border)
        print()
        sys.stdout.flush()

    # ── I/O ───────────────────────────────────────────────────────────────────

    def read_input(self) -> str:
        """
        Blocking line read from stdin.
        Returns stripped line, or '' on empty input.
        Raises EOFError when stdin closes.
        """
        try:
            sys.stdout.write(self._prompt_str())
            sys.stdout.flush()
            line = sys.stdin.readline()
            if line == '':
                raise EOFError
            return line.strip()
        except KeyboardInterrupt:
            print()
            return ''

    def write_output(self, text: str):
        """
        Print Aurora's response with formatting.
        Wraps long lines for VGA-width consoles (80 cols).
        """
        self._turn += 1
        if not text:
            return

        label = self._c(_YELLOW + _BOLD, '  Aurora:')
        print()
        print(label)

        # Word-wrap at ~76 chars for narrow console widths
        words = text.split()
        line_buf: list[str] = []
        col = 0
        for word in words:
            wlen = len(word) + (1 if line_buf else 0)
            if col + wlen > 76 and line_buf:
                print('    ' + ' '.join(line_buf))
                line_buf = [word]
                col = len(word)
            else:
                line_buf.append(word)
                col += wlen
        if line_buf:
            print('    ' + ' '.join(line_buf))

        print()
        sys.stdout.flush()
