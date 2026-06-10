#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TESTS = [
    ("greeting", "hello Aurora"),
    ("self_state", "Aurora, how are you feeling right now?"),
    ("pipeline", "Aurora, what are you feeling about your response pipeline right now?"),
    ("sensory", "Aurora, what is present around you right now?"),
    ("memory", "Aurora, what do you remember about my name?"),
    ("ambiguous", "that thing from before"),
    ("emotional", "I feel really overwhelmed and I need you with me."),
    ("tool", "what time is it"),
]


def _short(text: Any, limit: int = 220) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit] + ("..." if len(value) > limit else "")


def _has(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has(v) for v in value.values())
    if isinstance(value, list):
        return any(_has(v) for v in value)
    return bool(str(value or "").strip())


def run_turn(aurora: Any, prompt: str) -> Dict[str, Any]:
    systems = aurora.boot_aurora(
        state_dir="aurora_state",
        verbose=False,
        use_quasiarch=False,
        runtime_profile="diagnostic",
    )
    result = aurora.process_external_user_turn(
        systems,
        prompt,
        source_label="unified_regression",
        auto_search_enabled=False,
        record_exchange=False,
        update_interactive_state=False,
        track_evolutionary_trace=True,
        run_periodic_maintenance=False,
    )
    resp = result.get("resp_A")
    packet = systems.get("_last_unified_meaning_packet", {})
    thought = dict(packet.get("thought_state") or {})
    grounding = dict(packet.get("grounding") or {})
    projection = dict(packet.get("subsurface_projection") or {})
    final = str(getattr(resp, "content", "") or "")
    return {
        "prompt": prompt,
        "src": str(getattr(resp, "src", "") or ""),
        "final": final,
        "unified_packet_present": bool(packet),
        "thought_used": bool(thought.get("unified_interpretation") or thought.get("dominant_thread")),
        "grounding_used": bool(grounding.get("anchor_type") and grounding.get("anchor_type") != "unresolved"),
        "subsurface_guidance_used": bool(projection.get("surface_guidance")),
        "salad_score": aurora._candidate_word_salad_score(final, user_text=prompt),
        "coherent": aurora._coherent_candidate_text(final, user_text=prompt),
        "packet": packet,
        "systems": systems,
    }


def influence_checks(aurora: Any, baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
    packet = baseline["packet"]
    systems = baseline["systems"]
    base_text, _ = aurora._realize_unified_surface_response(
        systems,
        packet,
        mode=None,
        routing="audit",
        is_self_question=True,
    )
    changes = []

    mutations = {
        "ThoughtState.unified_interpretation": lambda p: p["thought_state"].update(
            {"unified_interpretation": "The turn is now centered on a deliberately altered integration claim about continuity and trust."}
        ),
        "ThoughtState.self_application": lambda p: p["thought_state"].update(
            {"self_application": "This applies to me as a boundary-and-trust calibration, not only a self-state report."}
        ),
        "ThoughtState.conflicts": lambda p: p["thought_state"].update(
            {"conflicts": [["memory", "trust"], ["language", "boundary"], ["prediction", "surface"]]}
        ),
        "grounding.content": lambda p: p["grounding"].update(
            {"anchor_type": "relational", "content": "grounded in the ongoing relationship thread and the user's requested truth-check", "grounding_source": "audit_mutation"}
        ),
        "subsurface_projection.surface_guidance": lambda p: p["subsurface_projection"].update(
            {"surface_guidance": "Surface should slow down and preserve relational trust while the deeper frame checks coherence."}
        ),
        "conscious_frame.root_thought": lambda p: p["conscious_frame"].update(
            {"root_thought": {"summary": "A changed predictive frame says the next answer should emphasize trust, continuity, and careful wording."}}
        ),
    }

    for label, mutate in mutations.items():
        altered = copy.deepcopy(packet)
        mutate(altered)
        text, _ = aurora._realize_unified_surface_response(
            systems,
            altered,
            mode=None,
            routing="audit",
            is_self_question=True,
        )
        changes.append({
            "field": label,
            "changed": text != base_text,
            "before": _short(base_text),
            "after": _short(text),
        })
    return changes


def main() -> int:
    import aurora

    rows = []
    influence = []
    baseline_for_influence = None
    for name, prompt in TESTS:
        row = run_turn(aurora, prompt)
        if name == "pipeline":
            baseline_for_influence = row
        rows.append({
            "case": name,
            "prompt": prompt,
            "src": row["src"],
            "unified_packet_present": row["unified_packet_present"],
            "thought_used": row["thought_used"],
            "grounding_used": row["grounding_used"],
            "subsurface_guidance_used": row["subsurface_guidance_used"],
            "salad_score": round(float(row["salad_score"]), 4),
            "coherent": bool(row["coherent"]),
            "final": _short(row["final"], 260),
        })

    if baseline_for_influence:
        influence = influence_checks(aurora, baseline_for_influence)

    payload = {
        "regression": rows,
        "influence_checks": influence,
        "all_influence_changed": all(item.get("changed") for item in influence),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0 if payload["all_influence_changed"] and all(row["coherent"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
