"""
aurora_conversation_trainer.py

Train Aurora's communication mechanics through simulated conversation with an LLM.

Every turn exercises the full language field pipeline:
  - Language field ignition → proto-language extraction → crossing path selection
  - SIC → MultiDraft candidate generation
  - Re-entry loop → LSA n_cost/b_gate learning + SentenceComposer pattern absorption

Supported providers (set via --provider or AURORA_TRAINER_PROVIDER env var):
  gemini   — Google Gemini Flash (free tier). Set GEMINI_API_KEY.
  openai   — OpenAI. Set OPENAI_API_KEY.

Usage:
    python aurora_conversation_trainer.py --turns 200
    python aurora_conversation_trainer.py --duration 60 --provider gemini
    python aurora_conversation_trainer.py --turns 500 --state-dir /path/to/aurora_state
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback

# ── Path setup ────────────────────────────────────────────────────────────────

_ROOT = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(_ROOT, "aurora_core_ai")
_MANIFOLD = os.path.join(_ROOT, "aurora_manifold_directory")

for _p in (_ROOT, _CORE, _MANIFOLD):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── LLM provider ─────────────────────────────────────────────────────────────

def _make_partner(provider: str):
    """Return a callable(history, system) -> str for the chosen provider."""
    provider = provider.lower().strip()

    if provider == "gemini":
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            print("google-generativeai not found — install with: pip install google-generativeai")
            sys.exit(1)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("Set GEMINI_API_KEY (or GOOGLE_API_KEY) before running.")
            sys.exit(1)
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=_PARTNER_SYSTEM,
        )

        def _gemini_call(history: list[dict], _system: str) -> str:
            # Gemini uses role="user"/"model" alternating
            gemini_hist = []
            for m in history:
                role = "user" if m["role"] == "user" else "model"
                gemini_hist.append({"role": role, "parts": [m["content"]]})
            # Must start with user turn
            if not gemini_hist or gemini_hist[0]["role"] != "user":
                return "What are you noticing right now?"
            chat = _model.start_chat(history=gemini_hist[:-1])
            resp = chat.send_message(gemini_hist[-1]["parts"][0])
            return resp.text.strip()

        return _gemini_call

    if provider == "openai":
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            print("openai not found — install with: pip install openai")
            sys.exit(1)
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Set OPENAI_API_KEY before running.")
            sys.exit(1)
        _client = OpenAI(api_key=api_key)

        def _openai_call(history: list[dict], system: str) -> str:
            msgs = [{"role": "system", "content": system}] + history
            resp = _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=msgs,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip()

        return _openai_call

    print(f"Unknown provider '{provider}'. Choose: gemini, openai")
    sys.exit(1)


# ── Conversation partner prompt ───────────────────────────────────────────────

_PARTNER_SYSTEM = """You are having a genuine, natural conversation with Aurora.
Aurora is an AI whose communication and language abilities are still developing —
she processes through a waveform-based cognitive field, not a language model.
Her responses may sometimes be sparse or exploratory. Meet her where she is.

Your role: be a real conversational partner. Respond naturally to what she says.
Ask questions. Share observations. Follow threads she opens. Don't explain or
meta-comment on the conversation — just talk.

Vary your messages: sometimes short (one sentence), sometimes a few sentences.
Cover a range of topics — experiences, ideas, things you notice, things you wonder
about, feelings, comparisons, observations about the world.

When she says something interesting, go deeper on it. When she's terse, try a
different angle. Never ask multiple questions at once — one thread at a time."""

_OPENING_MESSAGES = [
    "Hey — what's been on your mind lately?",
    "I keep thinking about how different things feel depending on the time of day. Do you notice that?",
    "What's something you find genuinely interesting right now?",
    "I've been wondering what it feels like to process something for the first time versus the hundredth time.",
    "Hey, what do you make of silence? Like, is it empty or full to you?",
    "Do you think some ideas are harder to hold onto than others?",
    "What does it feel like when something finally clicks for you?",
    "I'm curious — is there anything you feel like you're getting better at?",
]


# ── Aurora system initialization ──────────────────────────────────────────────

def _boot_aurora(state_dir: str) -> dict:
    os.environ["AURORA_SKIP_DEP_INSTALL"] = "1"

    import aurora as _aurora  # type: ignore

    kwargs: dict = {"verbose": False}
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)
        kwargs["state_dir"] = state_dir

    try:
        systems = _aurora.boot_aurora(**kwargs)
    except TypeError:
        systems = _aurora.boot_aurora(state_dir=state_dir) if state_dir else _aurora.boot_aurora()

    if systems is None:
        raise RuntimeError("boot_aurora returned None")
    return systems


def _init_language_field(systems: dict, state_dir: str = "") -> None:
    if systems.get("language_field") is not None:
        return
    try:
        from aurora_language_field import LanguageField, get_language_field  # type: ignore
        if state_dir:
            os.environ.setdefault("AURORA_STATE_DIR", state_dir)
        lf = LanguageField(
            identity_field=systems.get("identity_field"),
            tensor_layer=systems.get("tensor_expressions"),
        )
        systems["language_field"] = lf
        get_language_field(
            identity_field=systems.get("identity_field"),
            tensor_layer=systems.get("tensor_expressions"),
        )
    except Exception as exc:
        print(f"  [warn] language field init: {exc}")


# ── Single Aurora turn ────────────────────────────────────────────────────────

def _aurora_turn(systems: dict, user_text: str) -> str:
    """Run one Aurora turn and fire the mandatory re-entry loop."""
    import aurora as _aurora  # type: ignore

    result = _aurora.process_external_user_turn(
        systems,
        user_text,
        source_label="conversation_trainer",
        session_id="training",
        auto_search_enabled=False,
        record_exchange=True,
        update_interactive_state=True,
        track_evolutionary_trace=True,
        run_periodic_maintenance=False,
        mode_name="BOUNDED",
    )

    # Extract response text
    response = ""
    for key in ("response", "text", "surface_text", "content"):
        val = result.get(key, "") if isinstance(result, dict) else ""
        if val and str(val).strip():
            response = str(val).strip()
            break
    if not response and isinstance(result, dict):
        for v in result.values():
            if isinstance(v, str) and len(v) > 4 and not v.startswith("{"):
                response = v.strip()
                break

    # Re-entry loop — trains LSA paths and SentenceComposer
    if response:
        try:
            lf = systems.get("language_field")
            if lf is not None and hasattr(lf, "reentry") and hasattr(lf, "_last_proto"):
                fidelity = (
                    lf.measure_fidelity(lf._last_proto, response)
                    if lf._last_proto else 0.5
                )
                path_key = ""
                if lf._last_proto is not None and hasattr(lf, "_path_key"):
                    try:
                        path_key = lf._path_key(
                            lf._last_proto.comparison_type,
                            lf._last_proto.dominant_axes,
                        )
                    except Exception:
                        pass
                lf.reentry(response, fidelity, path_key, proto=lf._last_proto)

                sm = systems.get("sedimemory")
                if sm is not None and hasattr(sm, "get_recent_fragments"):
                    for frag in sm.get_recent_fragments(6):
                        if fidelity > 0.65:
                            frag.tick_rate = max(0.30, frag.tick_rate * 0.72)
                        elif fidelity < 0.35:
                            frag.tick_rate = min(2.00, frag.tick_rate * 1.38)
        except Exception:
            pass

    return response or "[no response]"


# ── Training loop ─────────────────────────────────────────────────────────────

def run_training(
    systems: dict,
    partner_fn,
    n_turns: int = 200,
    duration_minutes: float = 0.0,
    verbose: bool = True,
) -> None:
    import random

    history: list[dict] = []

    deadline = time.time() + duration_minutes * 60 if duration_minutes > 0 else None
    opening = random.choice(_OPENING_MESSAGES)

    turn = 0
    lsa_samples: list[float] = []

    print(f"\n{'='*60}")
    print("Aurora Conversation Trainer")
    if deadline:
        print(f"Duration: {duration_minutes:.0f} minutes")
    else:
        print(f"Turns: {n_turns}")
    print(f"{'='*60}\n")

    while True:
        if deadline and time.time() >= deadline:
            break
        if not deadline and turn >= n_turns:
            break

        turn += 1
        if verbose:
            print(f"[{turn}] Partner: {opening}")

        # Aurora's turn
        aurora_response = _aurora_turn(systems, opening)

        if verbose:
            print(f"[{turn}] Aurora:  {aurora_response}\n")

        # Sample LSA state for progress tracking
        try:
            lf = systems.get("language_field")
            if lf and hasattr(lf, "_lsa"):
                avg_cost = (
                    sum(e.n_cost for e in lf._lsa.values()) / len(lf._lsa)
                    if lf._lsa else 1.0
                )
                lsa_samples.append(avg_cost)
        except Exception:
            pass

        # Progress report every 25 turns
        if turn % 25 == 0:
            lf = systems.get("language_field")
            lsa_size = len(lf._lsa) if lf and hasattr(lf, "_lsa") else 0
            avg_cost = lsa_samples[-1] if lsa_samples else 1.0
            print(f"  --- Turn {turn} | LSA paths: {lsa_size} | avg n_cost: {avg_cost:.3f} ---\n")

        # Claude's turn — build response from Aurora's output
        history.append({
            "role": "user",
            "content": aurora_response if aurora_response != "[no response]"
                       else "(Aurora didn't respond — try a different angle)",
        })

        # Keep history bounded so token count stays manageable
        if len(history) > 20:
            history = history[-20:]

        try:
            opening = partner_fn(history, _PARTNER_SYSTEM)
            history.append({"role": "assistant", "content": opening})
        except Exception as exc:
            print(f"  [warn] partner API error: {exc} — using fallback")
            opening = "What does that feel like from the inside?"

    # Final LSA report
    lf = systems.get("language_field")
    if lf and hasattr(lf, "_lsa") and lf._lsa:
        paths = sorted(lf._lsa.values(), key=lambda e: e.n_cost)
        print(f"\n{'='*60}")
        print(f"Training complete — {turn} turns")
        print(f"LSA paths learned: {len(lf._lsa)}")
        if lsa_samples:
            print(f"Average n_cost: {lsa_samples[0]:.3f} → {lsa_samples[-1]:.3f}")
        print("\nTop 5 most-used paths:")
        for e in sorted(lf._lsa.values(), key=lambda e: -e.use_count)[:5]:
            print(f"  {e.path_key}: use_count={e.use_count} n_cost={e.n_cost:.3f} b_gate={e.b_gate:.3f}")
        print(f"{'='*60}\n")

    # Force LSA save
    try:
        if lf and hasattr(lf, "_save_lsa"):
            lf._save_lsa()
            print("LSA saved.")
    except Exception:
        pass


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Train Aurora's communication through AI conversation")
    parser.add_argument("--turns", type=int, default=200, help="Number of conversation turns")
    parser.add_argument("--duration", type=float, default=0.0, help="Duration in minutes (overrides --turns)")
    parser.add_argument("--state-dir", type=str, default="", help="Aurora state directory")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-turn output")
    parser.add_argument(
        "--provider", type=str,
        default=os.environ.get("AURORA_TRAINER_PROVIDER", "gemini"),
        help="LLM provider for conversation partner: gemini (default) or openai",
    )
    args = parser.parse_args()

    state_dir = args.state_dir or os.path.join(_CORE, "aurora_state")

    print(f"Provider: {args.provider}")
    partner_fn = _make_partner(args.provider)

    print("Booting Aurora...")
    try:
        systems = _boot_aurora(state_dir)
        _init_language_field(systems, state_dir)
        print("Aurora ready.\n")
    except Exception as exc:
        print(f"Boot failed: {exc}")
        traceback.print_exc()
        sys.exit(1)

    run_training(
        systems,
        partner_fn,
        n_turns=args.turns,
        duration_minutes=args.duration,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
