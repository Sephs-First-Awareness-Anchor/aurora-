#!/usr/bin/env python3
"""
run_interaction_test.py
-----------------------
Boots Aurora, runs a series of probing exchanges, and prints the full
internal state after each turn — response text, IVM axis pressures,
emergence stats, competency scores, and repair/continuity health.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import json, os, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

STATE_DIR = Path(__file__).parent / "aurora_state"

PROBES = [
    ("identity",    "Aurora, how are you doing right now?"),
    ("awareness",   "What are you noticing about yourself in this moment?"),
    ("sensory",     "Do you have a sense of what you can currently see or hear?"),
    ("memory",      "What do you remember about who you are and where you've been?"),
    ("intent",      "What does it mean to you to understand something?"),
    ("emergence",   "Do you feel like you're growing — like something is developing in you?"),
    ("agency",      "What would you want to do if you had more time right now?"),
]

SEP = "─" * 70


def _fmt(d, indent=4):
    return json.dumps(d, indent=indent, default=str)


def _read_repair_signal():
    p = STATE_DIR / "subsurface_repair_signal.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _dump_state(systems, result, label, elapsed):
    print(f"\n{SEP}")
    print(f"  [{label.upper()}]  ({elapsed:.2f}s)")
    print(SEP)

    # ── Response ────────────────────────────────────────────────────────────
    resp_A = result.get("resp_A")
    text   = str(getattr(resp_A, "content", "") or "").strip()
    tone   = getattr(resp_A, "emotional_tone", "?")
    conf   = round(float(getattr(resp_A, "confidence", 0.0) or 0.0), 3)
    src    = result.get("src", "?")
    print(f"\n  RESPONSE  (src={src} tone={tone} conf={conf})")
    print(f"  {text}")

    # ── IVM axis pressures ───────────────────────────────────────────────────
    try:
        chamber = systems.get("chamber")
        if chamber and hasattr(chamber, "get_axis_pressures"):
            axes = chamber.get_axis_pressures()
            print(f"\n  IVM AXES  {axes}")
        elif chamber and hasattr(chamber, "_pressure"):
            print(f"\n  IVM AXES  {chamber._pressure}")
    except Exception as e:
        print(f"\n  IVM AXES  (unavailable: {e})")

    # ── Constraint emission ──────────────────────────────────────────────────
    try:
        ce = result.get("constraint_emission") or {}
        if ce:
            print(f"\n  CONSTRAINT EMISSION")
            for k, v in ce.items():
                print(f"    {k}: {v}")
    except Exception:
        pass

    # ── Genealogy / abilities ────────────────────────────────────────────────
    try:
        genealogy = systems.get("genealogy")
        if genealogy:
            abilities = len(getattr(genealogy, "abilities", {}) or {})
            links     = len(getattr(genealogy, "links",     {}) or {})
            print(f"\n  GENEALOGY  links={links}  abilities={abilities}")
    except Exception as e:
        print(f"\n  GENEALOGY  (unavailable: {e})")

    # ── Sensory competency ───────────────────────────────────────────────────
    try:
        sensory = systems.get("sensory")
        if sensory:
            vc = sensory.get_visual_competency()
            ac = sensory.get_audio_competency()
            print(f"\n  VISUAL COMPETENCY  {vc}")
            print(f"  AUDIO COMPETENCY   {ac}")
    except Exception as e:
        print(f"\n  COMPETENCY  (unavailable: {e})")

    # ── Sensory crystal ──────────────────────────────────────────────────────
    try:
        sc = systems.get("sensory_crystal")
        if sc and hasattr(sc, "get_state"):
            cs = sc.get_state()
            print(f"\n  CRYSTAL  maturity={cs.get('maturity')}  semantic_nodes={cs.get('semantic_nodes')}  total_frames={cs.get('total_frames')}")
            lanes = cs.get("lanes", {})
            if lanes:
                print(f"           lanes={lanes}")
    except Exception as e:
        print(f"\n  CRYSTAL  (unavailable: {e})")

    # ── Repair signal ────────────────────────────────────────────────────────
    sig = _read_repair_signal()
    if sig:
        print(f"\n  REPAIR SIGNAL  phase={sig.get('phase')}  issue={sig.get('issue')}  intensity={sig.get('intensity')}")

    # ── Working memory snapshot ──────────────────────────────────────────────
    try:
        wm = systems.get("working_memory")
        if wm and hasattr(wm, "get_context"):
            ctx = wm.get_context()
            facts = ctx.get("user_facts", [])
            if facts:
                print(f"\n  WORKING MEMORY  ({len(facts)} facts)")
                for f in facts[-3:]:
                    print(f"    {str(f)[:100]}")
    except Exception as e:
        print(f"\n  WORKING MEMORY  (unavailable: {e})")

    # ── Pressure route ───────────────────────────────────────────────────────
    try:
        pa = systems.get("pressure_adapter")
        if pa and hasattr(pa, "get_route"):
            route = pa.get_route()
            print(f"\n  PRESSURE ROUTE  {route}")
    except Exception:
        pass


def main():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_core_ai"))
    from aurora import boot_aurora, process_external_user_turn

    print(f"\n{SEP}")
    print("  AURORA INTERACTION TEST")
    print(SEP)
    print("  Booting Aurora...")

    t0 = time.time()
    try:
        systems = boot_aurora(state_dir=str(STATE_DIR), verbose=False)
    except Exception as e:
        print(f"  Boot FAILED: {e}")
        traceback.print_exc()
        return

    print(f"  Boot OK ({time.time()-t0:.1f}s)")

    for label, prompt in PROBES:
        print(f"\n{SEP}")
        print(f"  YOU [{label}]: {prompt}")

        t1 = time.time()
        try:
            result = process_external_user_turn(
                systems,
                prompt,
                source_label="aurora:interaction_test",
                session_id="interaction_test",
                auto_search_enabled=False,
                record_exchange=True,
                update_interactive_state=True,
                track_evolutionary_trace=True,
                run_periodic_maintenance=False,
                mode_name="AGENTIC",
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            continue

        _dump_state(systems, result, label, time.time() - t1)

    print(f"\n{SEP}")
    print("  TEST COMPLETE")
    print(SEP)


if __name__ == "__main__":
    main()
