"""Small Windows/POSIX advisory lock; the OS releases it after a crash."""
from __future__ import annotations

import os
import threading
from pathlib import Path


class ProcessLock:
    def __init__(self, path, *, blocking=True):
        self.path = Path(path)
        self.blocking = blocking
        self._guard = threading.RLock()
        self._handle = None
        self._depth = 0

    def __enter__(self):
        self._guard.acquire()
        try:
            if self._depth:
                self._depth += 1
                return self
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(self.path, "a+b")
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0, 2)
                    if not handle.tell():
                        handle.write(b"\0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if self.blocking else msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (0 if self.blocking else fcntl.LOCK_NB))
            except Exception:
                handle.close()
                raise
            self._handle, self._depth = handle, 1
            return self
        except Exception:
            self._guard.release()
            raise

    def __exit__(self, *exc):
        try:
            self._depth -= 1
            if not self._depth:
                handle, self._handle = self._handle, None
                try:
                    if os.name == "nt":
                        import msvcrt
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                finally:
                    handle.close()
        finally:
            self._guard.release()
