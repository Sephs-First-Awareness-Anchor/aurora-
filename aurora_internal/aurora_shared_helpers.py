"""Small shared helpers with no Aurora dependencies.

Holds the one ``clamp`` that 19 modules each used to define for themselves,
and ``DictRecord``, the to_dict/from_dict pair that 11 flat dataclasses each
wrote by hand. This module imports only the standard library, so any module
can use it without pulling in another Aurora subsystem.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

__all__ = ["clamp", "DictRecord"]


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Bound v to [lo, hi]. Shared by every module that used its own _clamp copy."""
    return max(lo, min(hi, v))


class DictRecord:
    """Mixin for flat dataclasses: field-order to_dict and a from_dict that ignores unknown keys."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
