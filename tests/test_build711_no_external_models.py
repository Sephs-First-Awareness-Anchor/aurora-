#!/usr/bin/env python3
"""Build 711 hard boundary: Aurora may retrieve evidence, never delegate cognition to an outside AI model."""
from pathlib import Path


def test_scout_backend_registry_contains_no_model_backend_classes():
    import aurora_internal.scouting.backends as backends

    forbidden = {
        "GeminiRestBackend", "RemoteModelBackend", "OpenAIBackend",
        "AnthropicBackend", "ClaudeBackend", "LlamaBackend",
    }
    for name in forbidden:
        assert not hasattr(backends, name), name

    resolved = backends.resolve_backend_chain([
        "gemini_rest", "remote_model", "openai", "anthropic", "claude", "llama",
        "public_human_dialogue", "local_human_dialogue", "public_web", "local_lessons",
    ])
    assert [backend.name for backend in resolved] == [
        "public_human_dialogue", "local_human_dialogue", "public_web", "local_lessons",
    ]


def test_scout_report_contract_cannot_carry_scout_authored_cognitive_labels():
    from aurora_internal.scouting.contracts import ScoutReport

    report = ScoutReport(
        request_id="r", turn_id="t", status="ok",
        evidence_items=[{"text": "observed evidence", "final_response": "do not pass"}],
        response_relationships=["explain"],
        fit_rationales=["because"],
        contradictions=["something"],
        confidence=0.9,
    )
    assert report.response_relationships == []
    assert report.fit_rationales == []
    assert report.contradictions == []
    assert report.evidence_items[0].get("final_response") is None
    assert report.evidence_items[0]["emittable"] is False


def test_legacy_local_llm_boundary_is_hard_disabled():
    import aurora_internal.aurora_local_llm_bridge as bridge

    assert bridge.MODEL_FREE_ARCHITECTURE is True
    assert bridge._enabled() is False
    result = bridge.interpret_input("hello")
    assert not result.get("ok", False)
    assert result.get("error") == "model_use_forbidden_by_architecture"


def test_mobile_tool_registry_blocks_external_ai_apps_and_urls(monkeypatch):
    import aurora_internal.tool_registry as tr

    monkeypatch.setattr(tr, "_is_chaquopy_android", lambda: False)
    monkeypatch.setattr(tr, "_is_termux", lambda: True)
    # Direct package IDs stay blocked even though friendly aliases were removed.
    for package in (
        "com.openai.chatgpt", "com.anthropic.claude", "com.google.android.apps.bard",
    ):
        result = tr._mobile_launch_app(package)
        assert result.success is False
        assert result.note == "external_ai_model_use_forbidden_by_architecture"

    for url in (
        "https://chatgpt.com/", "https://claude.ai/", "https://gemini.google.com/",
        "https://api.openai.com/v1/responses", "https://api.anthropic.com/v1/messages",
    ):
        result = tr._mobile_open_url(url)
        assert result.success is False
        assert result.note == "external_ai_model_use_forbidden_by_architecture"


def test_runtime_python_contains_no_external_model_api_configuration():
    root = Path(__file__).resolve().parents[1]
    runtime_files = [root / "aurora.py", root / "aurora_daemon.py", root / "flutter_app/android/app/src/main/python/aurora_bridge.py"]
    runtime_files.extend((root / "aurora_internal").rglob("*.py"))
    forbidden = (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "generateContent",
        "api.openai.com", "api.anthropic.com", "claude-sonnet", "gemini-2",
    )
    for path in runtime_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            assert token not in text, f"{token} found in runtime file {path.relative_to(root)}"


def test_source_tree_contains_no_live_external_model_api_endpoint_or_sdk_dependency():
    root = Path(__file__).resolve().parents[1]
    excluded_roots = {root / "aurora_state", root / "tests"}
    extensions = {".py", ".kt", ".java", ".js", ".jsx", ".html"}
    forbidden = (
        "api.anthropic.com/v1/messages",
        "api.openai.com/v1",
        "generativelanguage.googleapis.com",
        "generateContent",
        "claude-sonnet-",
    )
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if any(parent == path or parent in path.parents for parent in excluded_roots):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            assert token not in text, f"{token} found in {path.relative_to(root)}"

    requirements = (root / "current_requirements.txt").read_text(encoding="utf-8", errors="ignore").lower()
    assert "anthropic==" not in requirements
    assert "openai==" not in requirements
