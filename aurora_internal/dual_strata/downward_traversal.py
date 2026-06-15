# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Downward traversal — the ONLY supported path from the surface layer into
subsurface mechanism. No language module may dict-walk _subsurface_detail
directly; they must call expand_crest instead.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

# Mapping: subsurface crest labels → which keys in _subsurface_detail
# are relevant at each depth
_CREST_DETAIL_MAP: Dict[str, Dict[int, list]] = {
    "comfort_bias":       {1: ["contract_signals", "recalled_fragments"], 2: ["candidate_interpretations"], 3: ["salience_weights"]},
    "caution":            {1: ["contract_signals", "instability_markers"], 2: ["candidate_interpretations"], 3: ["pressure_map"]},
    "warmth":             {1: ["contract_signals"], 2: ["candidate_interpretations"], 3: ["salience_weights"]},
    "hesitation":         {1: ["contract_signals", "instability_markers"], 2: ["candidate_interpretations"], 3: []},
    "neutral_affect":     {1: ["contract_signals"], 2: [], 3: []},
    "familiar":           {1: ["recalled_fragments", "contract_signals"], 2: ["candidate_interpretations"], 3: []},
    "unfamiliar":         {1: ["recalled_fragments"], 2: ["candidate_interpretations"], 3: []},
    "continuity_pull":    {1: ["recalled_fragments", "contract_signals"], 2: ["candidate_interpretations"], 3: []},
    "continuity_stable":  {1: ["recalled_fragments"], 2: [], 3: []},
    "resonant_recall":    {1: ["recalled_fragments", "contract_signals"], 2: ["candidate_interpretations"], 3: []},
    "thread_holds":       {1: ["contract_signals"], 2: ["recalled_fragments"], 3: []},
    "thread_slipping":    {1: ["contract_signals", "instability_markers"], 2: ["recalled_fragments"], 3: []},
    "new_thread":         {1: ["contract_signals"], 2: [], 3: []},
    "context_drag":       {1: ["contract_signals", "instability_markers"], 2: ["recalled_fragments"], 3: []},
    "strain":             {1: ["instability_markers"], 2: ["action_bias_candidates"], 3: []},
    "limitation":         {1: ["instability_markers"], 2: [], 3: []},
    "capacity":           {1: ["instability_markers"], 2: ["action_bias_candidates"], 3: []},
    "steady_envelope":    {1: [], 2: [], 3: []},
    "reframe_needed":     {1: ["instability_markers", "prediction_signal"], 2: ["candidate_interpretations"], 3: []},
    "surprise":           {1: ["prediction_signal", "instability_markers"], 2: ["candidate_interpretations"], 3: []},
    "low_certainty":      {1: ["prediction_signal"], 2: [], 3: []},
    "expectation":        {1: ["prediction_signal"], 2: [], 3: []},
    "steady_continuation":{1: [], 2: [], 3: []},
    "resonance":          {1: ["law_bindings"], 2: ["candidate_interpretations"], 3: []},
    "contradiction":      {1: ["instability_markers", "law_bindings"], 2: ["candidate_interpretations"], 3: []},
    "novelty":            {1: ["candidate_interpretations"], 2: [], 3: []},
    "alignment":          {1: ["law_bindings"], 2: [], 3: []},
    "urgency":            {1: ["instability_markers", "action_bias_candidates"], 2: ["pressure_map"], 3: []},
    "discomfort":         {1: ["instability_markers"], 2: ["action_bias_candidates"], 3: []},
    "tension":            {1: ["instability_markers"], 2: [], 3: []},
    "calm":               {1: [], 2: [], 3: []},
    "explain":            {1: ["contract_signals", "recalled_fragments"], 2: ["candidate_interpretations"], 3: []},
    "clarify":            {1: ["contract_signals", "instability_markers"], 2: ["candidate_interpretations"], 3: []},
    "comfort":            {1: ["contract_signals", "recalled_fragments"], 2: ["candidate_interpretations"], 3: []},
    "hold":               {1: ["instability_markers"], 2: [], 3: []},
    "contextualize":      {1: ["contract_signals", "recalled_fragments"], 2: ["candidate_interpretations"], 3: []},
    "reframe":            {1: ["instability_markers", "contract_signals"], 2: ["candidate_interpretations"], 3: []},
    "attend":             {1: ["contract_signals"], 2: [], 3: []},
}

_DEFAULT_DEPTH_KEYS = {
    1: ["contract_signals", "instability_markers", "recalled_fragments"],
    2: ["candidate_interpretations", "action_bias_candidates", "prediction_signal"],
    3: ["salience_weights", "pressure_map", "law_bindings", "comparison_channels", "origin_systems"],
}


def expand_crest(state_dir: Path, crest_label: str, depth: int = 1) -> dict:
    """When consciousness needs to elaborate, read subsurface_detail.json and
    return only the slice relevant to the named crest at the requested depth.

    depth=1: the sub-crests that produced this crest
    depth=2: the raw subsystem inputs behind those sub-crests
    depth=3: the underlying numeric mechanism (rarely needed for language)
    """
    detail_path = Path(state_dir) / "subsurface_detail.json"
    if not detail_path.exists():
        return {}
    try:
        detail = json.loads(detail_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(detail, dict):
        return {}

    depth = max(1, min(3, int(depth or 1)))
    label = str(crest_label or "").strip().lower()

    crest_map = _CREST_DETAIL_MAP.get(label, {})
    keys_at_depth = crest_map.get(depth, _DEFAULT_DEPTH_KEYS.get(depth, []))

    result = {"crest_label": label, "depth": depth}
    for key in keys_at_depth:
        val = detail.get(key)
        if val is not None:
            result[key] = val

    # Depth 1 always includes sub_crests if available
    if depth == 1 and "sub_crests" in detail:
        result["sub_crests"] = detail["sub_crests"]

    # micro_reasoning hypotheses (FIX-A009) are interpretation-level signals
    # not tied to any one crest label -- always surface them when present,
    # at any depth, the same way sub_crests is always surfaced at depth 1.
    if "micro_reasoning" in detail:
        result["micro_reasoning"] = detail["micro_reasoning"]

    return result
