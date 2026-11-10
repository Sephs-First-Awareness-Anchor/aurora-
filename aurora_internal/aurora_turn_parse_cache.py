"""Single live-turn utterance parse cache.

The response path asks the same stateless UtteranceParser about the same
source text from attention, observation, and synthesis. Avoid rerunning the
parser when the text is byte-for-byte unchanged. A genuinely rewritten
grounded utterance is reparsed. Every caller receives its own deep copy so
later enrichment cannot contaminate the following reader or the cache.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Dict, Optional


class TurnParseCache:
    def __init__(self, parse: Callable[[str], Dict[str, Any]]) -> None:
        self._parse = parse
        self._text: Optional[str] = None
        self._parsed: Optional[Dict[str, Any]] = None

    def parse(self, text: str) -> Dict[str, Any]:
        text = str(text or "")
        if self._parsed is None or self._text != text:
            parsed = dict(self._parse(text) or {})
            self._parsed = copy.deepcopy(parsed)
            self._text = text
        return copy.deepcopy(self._parsed)
