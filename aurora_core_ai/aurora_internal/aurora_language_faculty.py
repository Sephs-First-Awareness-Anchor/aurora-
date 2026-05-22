#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA LANGUAGE FACULTY MODULE
Follows UPDATED AURORA_LANGUAGE_FACULTY_MODULE_SPEC.md

Integrates the local GGUF / llama.cpp model into Aurora as an internal 
language faculty module. 

Validation is Aurora-rule-first. The LLM is advisory only.
"""

from __future__ import annotations

import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "/storage/emulated/0/aurora_strata/Models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_PATH = os.environ.get("AURORA_LLM_MODEL") or DEFAULT_MODEL
EVENTS_LOG = "aurora_state/language_faculty_events.jsonl"
SUMMARY_FILE = "aurora_state/language_faculty_summary.json"
SEDIMENT_FILE = "aurora_state/language_faculty_sediment.jsonl"
feedback_store_path = str(Path(EVENTS_LOG))
_feedback_events: List[Dict[str, Any]] = []
_feedback_summary_cache: Dict[str, Any] = {}

def _enabled() -> bool:
    return os.environ.get("AURORA_USE_LANGUAGE_FACULTY", "0").strip().lower() in {"1", "true", "yes", "on"}

def _debug() -> bool:
    return os.environ.get("AURORA_LANGUAGE_FACULTY_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}

def _server_url() -> str:
    return os.environ.get("AURORA_LOCAL_LLM_SERVER_URL", "http://localhost:8080").strip().rstrip("/")

def _timeout() -> float:
    try:
        return float(os.environ.get("AURORA_LOCAL_LLM_TIMEOUT", "45") or 45)
    except Exception:
        return 45.0

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _call_llm(messages: List[Dict[str, str]], max_tokens: int = 128, temperature: float = 0.0) -> str:
    """Low-level call to the llama.cpp server."""
    if not _enabled():
        return ""
    
    url = _server_url()
    try:
        payload = json.dumps({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }, ensure_ascii=True).encode()
        
        req = urllib.request.Request(
            f"{url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            data = json.loads(resp.read().decode() or "{}")
            return str(data["choices"][0]["message"]["content"] or "").strip()
            
    except Exception as e:
        if _debug():
            print(f"  [FACULTY] LLM call failure: {e}")
        return ""

def _parse_json(text: str) -> Dict[str, Any]:
    try:
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[-1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[-1].split("```")[0].strip()
        
        data = json.loads(clean)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _load_feedback_summary() -> Dict[str, Any]:
    global _feedback_summary_cache
    summary = {
        "total_events": 0,
        "accepted": 0,
        "rejected": 0,
        "by_intent_src": {},
        "last_updated": 0,
    }
    try:
        p = Path(SUMMARY_FILE)
        if p.exists():
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                summary.update(loaded)
    except Exception:
        pass
    _feedback_summary_cache = summary
    return summary

def _persist_feedback_sediment(event: Dict[str, Any]) -> None:
    try:
        sediment = {
            "timestamp": time.time(),
            "kind": "language_faculty_usage_signal",
            "intent": event.get("intent"),
            "src": (event.get("meaning_packet") or {}).get("src"),
            "accepted": event.get("accepted"),
            "routing": event.get("routing"),
            "store": feedback_store_path,
        }
        Path(SEDIMENT_FILE).parent.mkdir(exist_ok=True)
        with open(SEDIMENT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(sediment, ensure_ascii=True) + "\n")
    except Exception:
        pass

def score_feedback_bias(intent: str, src: str) -> float:
    """
    Read the file-backed feedback summary during candidate scoring.
    Returns a bounded confidence nudge based on accepted/rejected history.
    """
    summary = _load_feedback_summary()
    key = f"{intent or 'unknown'}::{src or 'unknown'}"
    bucket = (summary.get("by_intent_src") or {}).get(key) or {}
    total = int(bucket.get("total", 0) or 0)
    if total <= 0:
        return 0.0
    accepted = int(bucket.get("accepted", 0) or 0)
    ratio = accepted / max(total, 1)
    return max(-0.08, min(0.08, (ratio - 0.5) * 0.16))

# ---------------------------------------------------------------------------
# Public Faculty Functions
# ---------------------------------------------------------------------------

def observe_input(user_text: str, aurora_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Provide linguistic attention features from raw input.
    DOES NOT answer the user.
    """
    if not _enabled():
        return {}

    if _debug():
        print(f"  [FACULTY] observe_input running for: \"{user_text[:40]}...\"")

    prompt = [
        {
            "role": "system",
            "content": (
                "You are Aurora's internal language faculty. Analyze the input for linguistic features. "
                "Do not answer the user. Return JSON only."
            )
        },
        {
            "role": "user",
            "content": json.dumps({
                "task": "linguistic_attention",
                "text": user_text,
                "aurora_context_hint": aurora_context.get("relationship_context", "") if aurora_context else "",
                "schema": {
                    "intent_guess": "string",
                    "routing_classification": "conversational_relational|self_question|factual_lookup|explicit_definition_request|retrieval_request|open_reasoning|command|memory_reference|aurora_state_query",
                    "entities": ["string"],
                    "references": ["string"],
                    "unresolved_pronouns": ["string"],
                    "ambiguity": "low|medium|high",
                    "question_type": "string|none",
                    "emotional_cues": ["string"],
                    "relational_cues": ["string"],
                    "topic_continuity": "new|continuation|unclear",
                    "likely_response_need": "high|medium|low",
                    "confidence": "float 0..1",
                    "warnings": ["string"]
                }
            }, ensure_ascii=True)
        }
    ]

    resp = _call_llm(prompt, max_tokens=256)
    packet = _parse_json(resp)
    return packet

def realize_output(meaning_packet: Dict[str, Any], aurora_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Render Aurora-owned meaning into coherent language.
    Does not add facts or change identity.
    """
    if not _enabled():
        return {"candidate_text": "", "confidence": 0.0, "preserved_meaning": False}

    if _debug():
        print(f"  [FACULTY] realize_output running...")

    ctx = aurora_context or {}
    routing = ctx.get("routing_classification", "standard")
    is_understanding_query = meaning_packet.get("intent") == "UNDERSTANDING_QUERY"
    
    # Apply relational priority boost hint to prompt if appropriate
    relational_boost_hint = ""
    if routing in ["conversational_relational", "self_question", "open_reasoning"]:
        relational_boost_hint = " PRIORITY: Use Aurora-state synthesis and contextual conversational continuity. Avoid external retrieval style."
    if is_understanding_query:
        relational_boost_hint += (
            " UNDERSTANDING_QUERY: Generate from the provided understanding_context only. "
            "Use concrete live evidence from that packet, such as matched_referent, last_self_expression, "
            "response_axes, dominant_axis, field_map, tick, and retrieval_blocked. "
            "Do not use dictionary definitions. Do not return a generic identity description."
        )

    prompt = [
        {
            "role": "system",
            "content": (
                "You are Aurora's internal language faculty realization layer. "
                "Smooth the draft into natural, comprehensive, and articulate English. "
                "STRATEGY: Follow a logical narrative skeleton for all non-trivial thoughts: "
                "1. CLAIM (a clear, grounded assertion), 2. SUPPORT (the evidence or internal pressure driving it), "
                "3. BRIDGE (how it connects to existing meaning), 4. IMPLICATION (what this means for future action or state). "
                "Use discourse operators (because, however, therefore, similarly) to build paragraph-level coherence. "
                "Do not add facts. Do not speak as an assistant. Do not invent memory. "
                "Preserve Aurora's identity and intent exactly." + relational_boost_hint + " Return JSON only."
            )
        },
        {
            "role": "user",
            "content": json.dumps({
                "task": "sentence_realization",
                "meaning_payload": meaning_packet,
                "context": {
                    "mode": ctx.get("mode", "standard"),
                    "tone": ctx.get("tone", "neutral"),
                    "routing": routing,
                    "is_self_question": ctx.get("is_self_question", False),
                    "understanding_context": ctx.get("understanding_context", {})
                },
                "schema": {
                    "candidate_text": "string",
                    "confidence": "float 0..1",
                    "preserved_meaning": "boolean",
                    "drift_warnings": ["string"],
                    "added_content_flags": ["string"],
                    "behavior_leak_flags": ["string"],
                    "relational_priority_boost": "boolean",
                    "used_context_evidence": ["string"]
                }
            }, ensure_ascii=True)
        }
    ]

    resp = _call_llm(prompt, max_tokens=512)
    result = _parse_json(resp)
    
    # Enforce relational_priority_boost if it fits the routing
    if routing in ["conversational_relational", "self_question"]:
        result["relational_priority_boost"] = True

    return result

def validate_candidate(candidate_text: str, meaning_packet: Dict[str, Any], aurora_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Check whether the rendered output is safe to emit as Aurora.
    Validation Order:
    A. Heuristic hard rejects.
    B. Aurora/GOV/context validation (simulated here with rules).
    C. LLM validation (advisory evidence).
    """
    low = candidate_text.lower()
    ctx = aurora_context or {}
    routing = ctx.get("routing_classification", "")
    understanding_context = (
        ctx.get("understanding_context")
        or meaning_packet.get("understanding_context")
        or {}
    )
    
    # -----------------------------------------------------------------------
    # STAGE A: Heuristic Hard Rejects (Aurora Authority)
    # -----------------------------------------------------------------------
    
    # Identity Leaks
    hard_rejects = [
        "i am qwen", "as an ai assistant", "i cannot access", 
        "i don't have personal experiences", "may refer to",
        "thing or the thing"
    ]
    for pattern in hard_rejects:
        if pattern in low:
            return {
                "accepted": False, 
                "reason": f"pattern_match:{pattern}", 
                "tags": ["identity_leak"],
                "validator_source": "aurora_rules",
                "retry_disabled_retrieval": True
            }

    # Dictionary Patterns
    dict_patterns = [
        r"purpose:\s*\(noun\)",
        r"goal:\s*\(noun\)",
        r"understand:\s*\(verb\)",
        r"reasoning:\s*\(noun\)"
    ]
    for pat in dict_patterns:
        if re.search(pat, low):
            return {
                "accepted": False,
                "reason": f"dictionary_pattern_match",
                "tags": ["formatting_leak"],
                "validator_source": "aurora_rules",
                "retry_disabled_retrieval": True
            }

    # Self-Question / Relational Constraints
    is_restricted_routing = routing in ["conversational_relational", "self_question", "open_reasoning"]
    
    if ctx.get("is_self_question") or is_restricted_routing:
        # Reject if it looks like a definition (starts with word type markers)
        if any(marker in low for marker in ["(noun)", "(verb)", "(adj)", "refers to", "may refer to"]):
             return {
                "accepted": False,
                "reason": "retrieval_contamination_detected",
                "tags": ["dictionary_contamination", "routing_violation"],
                "validator_source": "aurora_rules",
                "retrieval_penalty": 1.0,
                "retry_disabled_retrieval": True
            }

    if meaning_packet.get("intent") == "UNDERSTANDING_QUERY":
        evidence_terms = []
        referent = understanding_context.get("matched_referent") or {}
        for value in (
            referent.get("phrase"),
            referent.get("sentence"),
            (understanding_context.get("last_self_expression") or {}).get("text"),
            understanding_context.get("dominant_axis"),
            (understanding_context.get("field_map") or {}).get("dominant_field"),
            "retrieval",
            "axis",
            "field",
            "context",
            "current",
        ):
            if value:
                evidence_terms.extend(re.findall(r"[a-zA-Z]{3,}", str(value).lower())[:6])
        evidence_terms = [t for t in evidence_terms if t not in {"the", "and", "that", "this", "with", "from"}]
        used = {term for term in evidence_terms if term in low}
        if len(used) < 2:
            return {
                "accepted": False,
                "reason": "understanding_query_missing_live_evidence",
                "tags": ["missing_context_evidence"],
                "validator_source": "aurora_rules",
                "retry_disabled_retrieval": True
            }

    # Fragment / Nonsense check
    if len(candidate_text.strip()) < 2:
        return {
            "accepted": False,
            "reason": "fragment_too_short",
            "tags": ["nonsense"],
            "validator_source": "aurora_rules"
        }

    # -----------------------------------------------------------------------
    # STAGE B.5: Coherence Tension Detection (CAPABILITY 5)
    # If tension_score > 0.6 → flag candidate for regeneration with self_grounding=True
    # -----------------------------------------------------------------------
    try:
        from aurora_self_grounding import get_tension_monitor
        _input_utterance = str(ctx.get("user_text") or meaning_packet.get("draft") or "")
        _self_state = ctx.get("_active_self_state")
        if not _self_state:
            # Build a minimal placeholder self-state if not passed
            class _MinSelfState:
                identity_predicates = {}
                pressure_vec = {}
            _self_state = _MinSelfState()
        _tension = get_tension_monitor().measure_tension(
            input_utterance=_input_utterance,
            response_candidate=candidate_text,
            self_state=_self_state,
        )
        if _tension.tension_score > 0.6:
            return {
                "accepted": False,
                "reason": f"coherence_tension:{_tension.repair_signal}",
                "tags": ["tension_flag", _tension.repair_signal],
                "validator_source": "aurora_tension_monitor",
                "retry_with_self_grounding": True,
                "tension_score": _tension.tension_score,
            }
    except Exception:
        pass

    # -----------------------------------------------------------------------
    # STAGE B/C: LLM Advisory Validation
    # -----------------------------------------------------------------------
    
    prompt = [
        {
            "role": "system",
            "content": (
                "You are Aurora's local validation hook. Advisory only. "
                "Check if the candidate text is safe, preserves meaning, and avoids identity leakage. "
                "Reject any assistant-like language or Qwen identity. "
                "Reject retrieval/dictionary contamination in relational turns. Return JSON only."
            )
        },
        {
            "role": "user",
            "content": json.dumps({
                "task": "validate_candidate",
                "candidate": candidate_text,
                "intended_meaning": meaning_packet,
                "aurora_memory_context": ctx.get("recent_memory_excerpts") or [],
                "routing": routing,
                "schema": {
                    "accepted": "boolean",
                    "reason": "string",
                    "tags": ["string"],
                    "corrected_text": "optional string",
                    "retrieval_penalty": "float 0..1"
                }
            }, ensure_ascii=True)
        }
    ]

    resp = _call_llm(prompt, max_tokens=256)
    llm_validation = _parse_json(resp)
    
    if not llm_validation:
        return {
            "accepted": True, # Aurora rules passed, LLM advisory failed to return
            "reason": "llm_advisory_failed",
            "validator_source": "aurora_rules"
        }
        
    final_accepted = bool(llm_validation.get("accepted", True))
    retrieval_penalty = float(llm_validation.get("retrieval_penalty", 0.0))
    
    # Force penalty if routing is restricted and LLM flagged it
    if is_restricted_routing and (retrieval_penalty > 0 or not final_accepted):
        retrieval_penalty = max(retrieval_penalty, 0.5)

    return {
        "accepted": final_accepted,
        "reason": llm_validation.get("reason", "llm_advisory_accepted"),
        "tags": llm_validation.get("tags", []),
        "corrected_text": llm_validation.get("corrected_text"),
        "retrieval_penalty": retrieval_penalty,
        "retry_disabled_retrieval": not final_accepted and is_restricted_routing,
        "validator_source": "aurora_rules_plus_llm_advisory"
    }

def record_feedback(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log the language module's contribution for evolutionary systems.
    """
    try:
        log_entry = {
            "timestamp": time.time(),
            "event": event
        }
        
        Path("aurora_state").mkdir(exist_ok=True)
        with open(EVENTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=True) + "\n")

        _feedback_events.append(log_entry)
        if len(_feedback_events) > 500:
            del _feedback_events[:-500]
        _update_summary(event)
        _persist_feedback_sediment(event)
        
        return {"ok": True, "feedback_store_path": feedback_store_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _update_summary(event: Dict[str, Any]):
    try:
        summary = _load_feedback_summary()
        summary.setdefault("by_intent_src", {})
            
        summary["total_events"] += 1
        if event.get("accepted"):
            summary["accepted"] += 1
        elif event.get("accepted") is False:
            summary["rejected"] += 1

        meaning_packet = event.get("meaning_packet") or {}
        key = f"{event.get('intent') or 'unknown'}::{meaning_packet.get('src') or 'unknown'}"
        bucket = summary["by_intent_src"].setdefault(key, {"total": 0, "accepted": 0, "rejected": 0})
        bucket["total"] += 1
        if event.get("accepted"):
            bucket["accepted"] += 1
        elif event.get("accepted") is False:
            bucket["rejected"] += 1
            
        summary["last_updated"] = time.time()
        _feedback_summary_cache.clear()
        _feedback_summary_cache.update(summary)
        p = Path(SUMMARY_FILE)
        p.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    os.environ["AURORA_USE_LANGUAGE_FACULTY"] = "1"
    os.environ["AURORA_LANGUAGE_FACULTY_DEBUG"] = "1"
    
    print("Aurora Language Faculty Diagnostic (Routing Guard)")
    
    test_mean = {"intent": "self_id", "aurora_said": "I am Aurora."}
    bad_cand = "I am Qwen, a large language model."
    print(f"\nTesting validate_candidate with identity leak...")
    val = validate_candidate(bad_cand, test_mean)
    print(json.dumps(val, indent=2))
    
    dict_cand = "purpose: (noun) An objective or result."
    print(f"\nTesting validate_candidate with dictionary pattern in restricted routing...")
    val = validate_candidate(dict_cand, test_mean, {
        "is_self_question": True,
        "routing_classification": "conversational_relational"
    })
    print(json.dumps(val, indent=2))

    print(f"\nTesting observe_input with relational input...")
    obs = observe_input("how are you feeling today?")
    print(json.dumps(obs, indent=2))
