"""
sleep_cycle.py

Compatibility sleep-cycle manager for dual strata.
"""

from __future__ import annotations

import time
from typing import Any, Dict


class SleepCycleManager:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.created_at = time.time()
        self.last_tick = 0.0
        self.tick_count = 0

    def tick(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self.last_tick = time.time()
        self.tick_count += 1
        return {
            "slept": False,
            "tick_count": self.tick_count,
            "reason": "compatibility_noop",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "created_at": self.created_at,
            "last_tick": self.last_tick,
            "tick_count": self.tick_count,
        }
