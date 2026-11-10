"""Turn-local utterance parsing through Aurora's shared computation graph.

Every reader receives a private copy of the same derived parse. When text
changes due to a grounded rewrite or intervening action, the source revision
changes and the graph automatically recalculates that stage. Unchanged text
never triggers another parser pass, even if its readers run at different
moments within the same turn.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from aurora_internal.aurora_turn_compute_graph import TurnComputeGraph


class TurnParseCache:
    def __init__(
        self,
        parse: Callable[[str], Dict[str, Any]],
        *,
        graph: Optional[TurnComputeGraph] = None,
    ) -> None:
        self._parse = parse
        # The live path injects TurnLedger.computations, not a second cache.
        # The optional standalone graph keeps isolated tests usable.
        self._graph = graph if graph is not None else TurnComputeGraph()

    def parse(self, text: str) -> Dict[str, Any]:
        self._graph.publish("utterance:text", str(text or ""))
        return self._graph.derive(
            "utterance:parsed",
            ("utterance:text",),
            lambda sources: dict(self._parse(sources["utterance:text"]) or {}),
        )
