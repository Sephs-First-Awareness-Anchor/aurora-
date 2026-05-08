#!/usr/bin/env python3
"""
Local articulation layer for Aurora.

This module is not a responder. It can only smooth Aurora's already-selected
draft through local llama.cpp and returns the original text if preservation
checks fail.
"""

from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set


DEFAULT_MODEL = "Models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_BINARY = "/data/data/com.termux/files/usr/bin/llama-cli"
WORKER_SCRIPT = Path(__file__).with_name("aurora_llama_worker.py")
DECISION_LOG = Path("aurora_state") / "articulation_feedback.jsonl"
SUMMARY_FILE = Path("aurora_state") / "articulation_feedback_summary.json"
TRACE_FILE = Path("aurora_state") / "last_articulation_trace.json"
_PY_LLM = None
_PY_LLM_LOCK = threading.Lock()


@dataclass
class ArticulationDecision:
    original: str
    candidate: str
    selected: str
    accepted: bool
    reason: str
    original_score: float
    candidate_score: float
    original_pressure: float
    candidate_pressure: float
    pressure_relief: float
    safe: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


def _flag_disabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _binary_path() -> str:
    configured = os.environ.get("AURORA_ARTICULATOR_BIN", "").strip()
    if configured:
        return configured
    return shutil.which("llama-cli") or DEFAULT_BINARY


def _model_path() -> str:
    configured = os.environ.get("AURORA_ARTICULATOR_MODEL", "").strip()
    if configured:
        return configured
    return DEFAULT_MODEL


def available() -> bool:
    if _flag_disabled("AURORA_ARTICULATOR_DISABLED"):
        return False
    binary = _binary_path()
    model = _model_path()
    return bool(
        model and Path(model).exists() and (
            _isolated_llama_available() or Path(binary).exists() or _python_llama_available()
        )
    )


def _python_llama_available() -> bool:
    if _flag_disabled("AURORA_ARTICULATOR_PY_DISABLED"):
        return False
    if not _flag_enabled("AURORA_ARTICULATOR_PY_ENABLED"):
        return False
    try:
        import llama_cpp  # noqa: F401
        return True
    except Exception:
        return False


def _isolated_llama_available() -> bool:
    if _flag_disabled("AURORA_ARTICULATOR_ISOLATED_DISABLED"):
        return False
    if not _flag_enabled("AURORA_ARTICULATOR_ISOLATED_ENABLED"):
        return False
    return WORKER_SCRIPT.exists() and Path(_model_path()).exists()


def _server_url() -> str:
    return os.environ.get("AURORA_LOCAL_LLM_SERVER_URL", "").strip().rstrip("/")


def _guard_tokens(text: str) -> Set[str]:
    # Words to ignore when checking for proper noun preservation
    skip = {
        "I", "A", "An", "The", "This", "That", "These", "Those", "It", "If",
        "When", "Where", "What", "Why", "How", "Because", "And", "But", "So",
        "My", "Your", "Our", "Yes", "No", "Hello", "Hi", "Hey",
        "Please", "Thanks", "Thank", "Okay", "Ok", "Maybe", "Perhaps",
        "Well", "Now", "Actually", "Just",
    }
    tokens = {
        tok for tok in re.findall(r"\b[A-Z][A-Za-z0-9_\-]*\b", text or "")
        if tok not in skip
    }
    tokens.update(re.findall(r"[-+]?\d+(?:\.\d+)?", text or ""))
    tokens.update(re.findall(r"\b[A-Za-z0-9_.+-]+@[A-Za-z0-9_.+-]+\b", text or ""))
    return tokens


def _strip_llama_output(text: str) -> str:
    out = (text or "").strip()
    for marker in ("Revised:", "Revised message:", "Output:", "Message:", "Response:"):
        if marker in out:
            out = out.split(marker)[-1].strip()
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    # If the model gives multiple lines, prefer the longest one as it's likely the comprehensive one
    if len(lines) > 1:
        out = max(lines, key=len)
    return out.strip().strip('"').strip("'").strip()


def _get_python_llm():
    """Load and retain llama.cpp through llama_cpp for the current process."""
    global _PY_LLM
    if _PY_LLM is not None:
        return _PY_LLM
    if not _python_llama_available():
        return None
    with _PY_LLM_LOCK:
        if _PY_LLM is not None:
            return _PY_LLM
        from llama_cpp import Llama

        _PY_LLM = Llama(
            model_path=_model_path(),
            n_ctx=int(os.environ.get("AURORA_ARTICULATOR_CTX", "512") or 512),
            n_threads=int(os.environ.get("AURORA_ARTICULATOR_THREADS", "2") or 2),
            verbose=False,
        )
        return _PY_LLM


def _run_python_llama_candidate(draft_text: str, prompt: str, tone: str) -> str:
    llm = _get_python_llm()
    if llm is None:
        return ""
    resp = llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Aurora's local articulation layer only. "
                    "Do not answer the user directly. Do not add new facts or questions. "
                    "Smooth Aurora's draft to sound more human, comprehensive, and conversational. "
                    "Preserve core meaning, facts, and names."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "tone": tone,
                    "user_context": str(prompt or "")[:300],
                    "aurora_draft": draft_text,
                }, ensure_ascii=True),
            },
        ],
        temperature=float(os.environ.get("AURORA_ARTICULATOR_TEMP", "0.2") or 0.2),
        max_tokens=int(os.environ.get("AURORA_ARTICULATOR_PY_TOKENS", "512") or 512),
    )
    try:
        content = resp["choices"][0]["message"]["content"]
    except Exception:
        return ""
    return _strip_llama_output(str(content or ""))


def _run_isolated_llama_candidate(draft_text: str, prompt: str, tone: str, timeout_s: float) -> str:
    if not _isolated_llama_available():
        return ""
    request = {
        "task": "articulate",
        "draft": draft_text,
        "prompt": prompt,
        "tone": tone,
    }
    proc = subprocess.run(
        [sys.executable, str(WORKER_SCRIPT)],
        input=json.dumps(request, ensure_ascii=True),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads((proc.stdout or "").strip())
    except Exception:
        return ""
    if not isinstance(data, dict) or not data.get("ok"):
        return ""
    return _strip_llama_output(str(data.get("message", "") or ""))


def _run_server_llama_candidate(draft_text: str, prompt: str, tone: str, timeout_s: float) -> str:
    url = _server_url()
    if not url:
        return ""
    payload = json.dumps({
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Aurora's local articulation layer only. Do not answer the user. "
                    "Do not add facts, examples, questions, or advice. Only lightly smooth "
                    "Aurora's draft while preserving meaning. Return only the revised message."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "tone": tone,
                    "user_prompt_context": str(prompt or "")[:300],
                    "aurora_draft": draft_text[:900],
                }, ensure_ascii=True),
            },
        ],
        "max_tokens": int(os.environ.get("AURORA_ARTICULATOR_PY_TOKENS", "48") or 48),
        "temperature": float(os.environ.get("AURORA_ARTICULATOR_TEMP", "0.15") or 0.15),
    }, ensure_ascii=True).encode()
    req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode() or "{}")
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        return ""
    return _strip_llama_output(str(content or ""))


def _deterministic_candidate(draft_text: str) -> str:
    """
    Conservative cleanup for recurring Aurora-native phrasing.

    This is intentionally small and phrase-level. It gives the user a readable
    bridge when local llama.cpp is unavailable or too slow, without letting a
    general-purpose model invent a new answer.
    """
    text = re.sub(r"\s+", " ", str(draft_text or "")).strip()
    if not text:
        return ""

    replacements = (
        (r"\bThe meaning is whole, and I tell\.", "I am trying to tell the whole meaning."),
        (r"\bI will tell the alive question\.", "I will speak to the living question."),
        (r"\blike real heart\b", "with real feeling"),
        (r"\blike deep heart\b", "with deep feeling"),
        (r"\blike alive awareness\b", "with active awareness"),
        (r"\blike strange moment\b", "in an unfamiliar way"),
        (r"\bI grow this\b", "I am developing this"),
        (r"\bI hear this always\b", "I keep hearing this"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    return re.sub(r"\s+", " ", text).strip()


def _interpret_prompt_snapshot(prompt: str) -> Dict[str, Any]:
    raw = re.sub(r"\s+", " ", str(prompt or "")).strip()
    lower = raw.lower()
    terms = [
        w for w in re.findall(r"[a-zA-Z][a-zA-Z']{3,}", lower)
        if w not in {
            "what", "when", "where", "which", "about", "that", "this", "with",
            "from", "your", "tell", "something", "please", "could", "would",
        }
    ]
    entities = [
        tok for tok in re.findall(r"\b[A-Z][A-Za-z0-9_\-]{2,}\b", raw)
        if tok not in {"The", "This", "That", "Tell", "What", "When", "Where"}
    ]
    if "about yourself" in lower or "something about yourself" in lower:
        intent = "self_description_request"
    elif lower.endswith("?") or lower.startswith(("what", "why", "how", "when", "where", "do ", "does ", "can ")):
        intent = "question"
    elif any(word in lower for word in ("fix", "make", "build", "change", "add")):
        intent = "action_request"
    else:
        intent = "statement_or_context"

    return {
        "raw_prompt": raw[:240],
        "intent_hint": intent,
        "topic_terms": terms[:8],
        "entities": entities[:8],
    }


def _clarity_score(text: str) -> float:
    """Aurora-side heuristic for deciding whether articulation improved."""
    t = (text or "").strip()
    if not t:
        return 0.0

    words = re.findall(r"[A-Za-z']+", t)
    if not words:
        return 0.0

    lower_words = [w.lower() for w in words]
    unique_ratio = len(set(lower_words)) / max(1, len(lower_words))
    avg_word_len = sum(len(w) for w in words) / max(1, len(words))
    sentence_count = max(1, len(re.findall(r"[.!?]", t)) or 1)
    words_per_sentence = len(words) / sentence_count

    score = 0.45
    if 5 <= words_per_sentence <= 24:
        score += 0.18
    elif words_per_sentence > 36:
        score -= 0.12

    if 3.5 <= avg_word_len <= 8.0:
        score += 0.12
    if unique_ratio >= 0.72:
        score += 0.12

    if re.search(r"\b(\w+)\s+\1\b", " ".join(lower_words)):
        score -= 0.16
    if re.search(r"\b(something|interesting possibility|fragmented|word|answer)\b", t.lower()):
        score -= 0.06
    native_phrases = (
        "alive question", "meaning is whole", "and i tell", "like real heart",
        "like deep heart", "like alive awareness", "like strange moment",
    )
    if any(phrase in t.lower() for phrase in native_phrases):
        score -= 0.18
    if any(p in t for p in (".", "!", "?")):
        score += 0.05
    if len(t) > 260:
        score -= 0.06

    return max(0.0, min(1.0, round(score, 4)))


def _pressure_score(text: str, prompt: str = "") -> float:
    """
    Estimate articulation pressure: lower means easier for the user to receive.
    This is Aurora's decision signal, not the LLM's.
    """
    t = (text or "").strip()
    if not t:
        return 1.0

    words = re.findall(r"[A-Za-z']+", t)
    lower = t.lower()
    lower_words = [w.lower() for w in words]
    prompt_terms = {
        w for w in re.findall(r"[a-z]{4,}", (prompt or "").lower())
        if w not in {"what", "when", "where", "which", "about", "that", "this", "with", "from", "your"}
    }

    pressure = 0.18
    if len(words) < 3:
        pressure += 0.22
    if len(words) > 55:
        pressure += 0.18
    if words:
        sentence_count = max(1, len(re.findall(r"[.!?]", t)) or 1)
        words_per_sentence = len(words) / sentence_count
        if words_per_sentence > 30:
            pressure += 0.14
        if words_per_sentence < 4:
            pressure += 0.08

    abstract_markers = {
        "something", "interesting", "possibility", "fragmented", "perhaps",
        "maybe", "stuff", "thing", "things", "deeply", "strange", "quiet",
        "alive",
    }
    pressure += min(0.20, 0.035 * sum(1 for w in lower_words if w in abstract_markers))
    native_phrases = (
        "alive question", "meaning is whole", "and i tell", "like real heart",
        "like deep heart", "like alive awareness", "like strange moment",
    )
    if any(phrase in lower for phrase in native_phrases):
        pressure += 0.18

    if re.search(r"\b(\w+)\s+\1\b", " ".join(lower_words)):
        pressure += 0.16
    if not re.search(r"[.!?]$", t):
        pressure += 0.06
    if t.count(",") > 4:
        pressure += 0.05
    if any(marker in lower for marker in ("i cannot", "i don't know", "not sure")):
        pressure += 0.04

    if prompt_terms:
        response_terms = set(re.findall(r"[a-z]{4,}", lower))
        overlap = len(prompt_terms & response_terms) / max(1, len(prompt_terms))
        if overlap == 0:
            pressure += 0.12
        elif overlap < 0.25:
            pressure += 0.06

    clarity = _clarity_score(t)
    pressure += (1.0 - clarity) * 0.20
    return max(0.0, min(1.0, round(pressure, 4)))


def is_safe_revision(original: str, candidate: str) -> bool:
    original = (original or "").strip()
    candidate = (candidate or "").strip()
    if not original or not candidate or candidate == original:
        return False

    if len(candidate) > max(len(original) * 1.45, len(original) + 80):
        return False

    original_words = re.findall(r"[a-z]{3,}", original.lower())
    candidate_words = re.findall(r"[a-z]{3,}", candidate.lower())
    if len(candidate_words) > max(len(original_words) + 18, int(len(original_words) * 1.5)):
        return False

    orig_guards = _guard_tokens(original)
    cand_guards = _guard_tokens(candidate)
    if orig_guards:
        # Allow missing up to 20% of guard tokens for more natural phrasing
        # (e.g. if the model changes "The system" to "It")
        preserved = orig_guards.intersection(cand_guards)
        if len(preserved) / len(orig_guards) < 0.8:
            return False

    original_equations = set(re.findall(r"\d+\s*[\+\-\*/xX=]\s*\d+", original))
    candidate_equations = set(re.findall(r"\d+\s*[\+\-\*/xX=]\s*\d+", candidate))
    if original_equations and not original_equations.issubset(candidate_equations):
        return False

    if candidate.endswith("?") and not original.endswith("?"):
        return False

    original_set = set(original_words)
    candidate_set = set(candidate_words)
    if original_set:
        overlap = len(original_set & candidate_set) / max(1, len(original_set))
        if overlap < 0.25:
            return False

    return True


def _run_llama_candidate(draft_text: str, prompt: str, tone: str, timeout_s: float) -> str:
    prompt_text = (
        "You are Aurora's local articulation layer only.\n"
        "Do not answer the user. Do not add facts, examples, questions, or advice.\n"
        "Only provide a candidate smoothing of Aurora's draft.\n"
        "Aurora will decide whether your candidate is better.\n"
        "Preserve all names, numbers, equations, claims, tone, and meaning.\n"
        "Return only the candidate draft. If no improvement is needed, return the original draft.\n\n"
        f"Tone: {tone}\n"
        f"User prompt context, not to answer: {str(prompt or '')[:300]}\n"
        f"Aurora draft:\n{draft_text}\n"
    )

    command = [
        _binary_path(),
        "-m", _model_path(),
        "-p", prompt_text,
        "-n", os.environ.get("AURORA_ARTICULATOR_TOKENS", "24"),
        "--temp", os.environ.get("AURORA_ARTICULATOR_TEMP", "0.15"),
        "--no-display-prompt",
        "--simple-io",
        "-st",
    ]

    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s)
    if proc.returncode != 0:
        return ""
    return _strip_llama_output(proc.stdout)


def _failure_metadata(error: str = "", stderr: str = "") -> Dict[str, Any]:
    return {
        "error": str(error or "")[:240],
        "stderr_excerpt": str(stderr or "")[-600:],
    }


def decide_articulation(
    draft: str,
    candidate: str,
    *,
    prompt: str = "",
    tone: str = "neutral",
    source: str = "local_llama",
) -> ArticulationDecision:
    """Aurora chooses whether a smoothing candidate is better than her draft."""
    draft_text = (draft or "").strip()
    candidate_text = (candidate or "").strip()
    original_score = _clarity_score(draft_text)
    candidate_score = _clarity_score(candidate_text)
    original_pressure = _pressure_score(draft_text, prompt)
    candidate_pressure = _pressure_score(candidate_text, prompt)
    pressure_relief = round(original_pressure - candidate_pressure, 4)
    safe = is_safe_revision(draft_text, candidate_text)
    min_relief = float(os.environ.get("AURORA_ARTICULATOR_MIN_RELIEF", "0.035") or 0.035)

    accepted = bool(safe and pressure_relief >= min_relief)
    reason = "accepted_pressure_relief" if accepted else "kept_original"
    if not candidate_text:
        reason = "no_candidate"
    elif not safe:
        reason = "candidate_failed_preservation"
    elif pressure_relief < min_relief:
        reason = "candidate_did_not_relieve_pressure"

    return ArticulationDecision(
        original=draft_text,
        candidate=candidate_text,
        selected=candidate_text if accepted else draft_text,
        accepted=accepted,
        reason=reason,
        original_score=original_score,
        candidate_score=candidate_score,
        original_pressure=original_pressure,
        candidate_pressure=candidate_pressure,
        pressure_relief=pressure_relief,
        safe=safe,
        metadata={
            "prompt_excerpt": str(prompt or "")[:240],
            "input_interpretation": _interpret_prompt_snapshot(prompt),
            "tone": tone,
            "source": source,
            "model": _model_path(),
            "timestamp": time.time(),
        },
    )


def record_decision(decision: ArticulationDecision) -> None:
    """Persist Aurora's articulation choice as learning feedback."""
    try:
        DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DECISION_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(decision), ensure_ascii=True) + "\n")
        TRACE_FILE.write_text(json.dumps(asdict(decision), indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        return

    try:
        if SUMMARY_FILE.exists():
            summary = json.loads(SUMMARY_FILE.read_text(encoding="utf-8") or "{}")
        else:
            summary = {}
        total = int(summary.get("total", 0)) + 1
        accepted = int(summary.get("accepted", 0)) + (1 if decision.accepted else 0)
        rejected = total - accepted
        prev_gain = float(summary.get("avg_pressure_relief", 0.0) or 0.0)
        gain = decision.pressure_relief
        summary.update({
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": round(accepted / max(1, total), 4),
            "avg_pressure_relief": round(prev_gain + ((gain - prev_gain) / total), 4),
            "last_reason": decision.reason,
            "last_updated": time.time(),
        })
        SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        pass


def smooth_with_decision(
    draft: str,
    *,
    prompt: str = "",
    tone: str = "neutral",
    timeout: Optional[float] = None,
) -> ArticulationDecision:
    """
    Let local llama.cpp smooth/translate a draft only.

    The model is instructed not to answer the user. Safety checks enforce that
    names, numbers, equations, and core wording survive.
    """
    draft_text = (draft or "").strip()
    if not draft_text or not available():
        decision = decide_articulation(draft_text, "", prompt=prompt, tone=tone, source="unavailable")
        record_decision(decision)
        return decision

    timeout_s = float(timeout or os.environ.get("AURORA_ARTICULATOR_TIMEOUT", "90") or 90)
    candidate = ""
    failure: Dict[str, Any] = {}
    source = "isolated_llama_cpp"
    attempts: Dict[str, Any] = {}

    if _server_url():
        source = "llama_server"
        server_started = time.perf_counter()
        server_timeout = float(os.environ.get("AURORA_LOCAL_LLM_TIMEOUT", "45") or 45)
        try:
            candidate = _run_server_llama_candidate(draft_text, prompt, tone, server_timeout)
            attempts["llama_server"] = {
                "ok": bool(candidate),
                "elapsed_s": round(time.perf_counter() - server_started, 4),
            }
            if not candidate:
                failure = _failure_metadata("server_no_candidate")
        except Exception as exc:
            attempts["llama_server"] = {
                "ok": False,
                "elapsed_s": round(time.perf_counter() - server_started, 4),
                "error": f"exception:{type(exc).__name__}",
            }
            failure = _failure_metadata(f"server_exception:{type(exc).__name__}")

    if not candidate and _isolated_llama_available():
        source = "isolated_llama_cpp"
        iso_started = time.perf_counter()
        iso_timeout = float(os.environ.get("AURORA_ARTICULATOR_ISOLATED_TIMEOUT", "45") or 45)
        try:
            candidate = _run_isolated_llama_candidate(draft_text, prompt, tone, iso_timeout)
            attempts["isolated_llama_cpp"] = {
                "ok": bool(candidate),
                "elapsed_s": round(time.perf_counter() - iso_started, 4),
            }
            if not candidate:
                failure = _failure_metadata("isolated_no_candidate")
        except subprocess.TimeoutExpired as exc:
            attempts["isolated_llama_cpp"] = {
                "ok": False,
                "elapsed_s": round(time.perf_counter() - iso_started, 4),
                "error": f"timeout_after_{iso_timeout:g}s",
            }
            failure = _failure_metadata(f"isolated_timeout_after_{iso_timeout:g}s", getattr(exc, "stderr", "") or "")
        except Exception as exc:
            attempts["isolated_llama_cpp"] = {
                "ok": False,
                "elapsed_s": round(time.perf_counter() - iso_started, 4),
                "error": f"exception:{type(exc).__name__}",
            }
            failure = _failure_metadata(f"isolated_exception:{type(exc).__name__}")
    else:
        attempts["isolated_llama_cpp"] = {"ok": False, "disabled": True}

    if not candidate and _python_llama_available():
        source = "python_llama_cpp"
        py_started = time.perf_counter()
        try:
            candidate = _run_python_llama_candidate(draft_text, prompt, tone)
            source = "python_llama_cpp" if candidate else source
            attempts["python_llama_cpp"] = {
                "ok": bool(candidate),
                "elapsed_s": round(time.perf_counter() - py_started, 4),
            }
            if not candidate:
                failure = _failure_metadata("python_no_candidate")
        except Exception as exc:
            attempts["python_llama_cpp"] = {
                "ok": False,
                "elapsed_s": round(time.perf_counter() - py_started, 4),
                "error": f"exception:{type(exc).__name__}",
            }
            failure = _failure_metadata(f"python_exception:{type(exc).__name__}")
    else:
        attempts["python_llama_cpp"] = {"ok": False, "disabled": True}

    if not candidate:
        source = "deterministic_fallback"
        fallback_candidate = _deterministic_candidate(draft_text)
        if fallback_candidate and fallback_candidate != draft_text:
            candidate = fallback_candidate
            source = "deterministic_fallback"
            attempts["deterministic_fallback"] = {"ok": True}
            failure = failure or _failure_metadata("deterministic_fallback")

    use_cli_fallback = _flag_enabled("AURORA_ARTICULATOR_CLI_FALLBACK")
    if not candidate and use_cli_fallback and not _flag_disabled("AURORA_ARTICULATOR_CLI_DISABLED"):
        source = "llama_cli"
        cli_started = time.perf_counter()
        try:
            candidate = _run_llama_candidate(draft_text, prompt, tone, timeout_s)
            attempts["llama_cli"] = {
                "ok": bool(candidate),
                "elapsed_s": round(time.perf_counter() - cli_started, 4),
            }
            if not candidate and not failure:
                failure = _failure_metadata("llama_cli_no_candidate")
        except subprocess.TimeoutExpired as exc:
            attempts["llama_cli"] = {
                "ok": False,
                "elapsed_s": round(time.perf_counter() - cli_started, 4),
                "error": f"timeout_after_{timeout_s:g}s",
            }
            failure = _failure_metadata(f"timeout_after_{timeout_s:g}s", getattr(exc, "stderr", "") or "")
        except Exception as exc:
            attempts["llama_cli"] = {
                "ok": False,
                "elapsed_s": round(time.perf_counter() - cli_started, 4),
                "error": f"exception:{type(exc).__name__}",
            }
            failure = _failure_metadata(f"exception:{type(exc).__name__}")

    decision = decide_articulation(draft_text, candidate, prompt=prompt, tone=tone, source=source)
    decision.metadata["attempts"] = attempts
    if failure:
        decision.metadata["llama_error"] = failure["error"]
        if decision.reason == "accepted_pressure_relief":
            decision.reason = "accepted_deterministic_fallback" if source == "deterministic_fallback" else decision.reason
        elif failure["error"]:
            decision.reason = failure["error"]
        decision.metadata.update(failure)
    record_decision(decision)
    return decision


def smooth_response(
    draft: str,
    *,
    prompt: str = "",
    tone: str = "neutral",
    timeout: Optional[float] = None,
) -> str:
    return smooth_with_decision(draft, prompt=prompt, tone=tone, timeout=timeout).selected
