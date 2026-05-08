#!/usr/bin/env python3
"""
run_gauntlet.py — Aurora Evolution Gauntlet
===========================================

Default flow: learning arc

  Stage 0 : Stop daemon
  Stage 1 : Corpus trainer run (default: 1,000 messages)
  Stage 2 : Study
  Stage 3 : Sensory grounding
  Stage 4 : Socialization
  Stage 5 : Dream
  Stage 6 : Restart daemon

Legacy flow is still available with `--flow legacy`:

  Stage 0 : Stop daemon
  Stage 1 : Corpus observer pass
  Stage 2 : Chain burn (light)
  Stage 3 : Corpus triple pass
  Stage 4 : Assimilation cycle
  Stage 5 : Chain burn (deep)
  Stage 6 : Code mutation
  Stage 7 : Restart daemon

Each stage waits for the previous to complete. Progress is logged with
timestamps to gauntlet_run.log and stdout.

Usage:
  python3 run_gauntlet.py
  python3 run_gauntlet.py --flow learning_arc --batch-size 1000
  python3 run_gauntlet.py --flow legacy
  python3 run_gauntlet.py --no-restart
  python3 run_gauntlet.py --stages 1,2,3,4

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import sys
import time
import signal
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent.resolve()
STATE_DIR   = BASE_DIR / "aurora_state"
GENEAL_DIR  = STATE_DIR / "genealogy"
LOG_FILE    = BASE_DIR / "gauntlet_run.log"
DEFAULT_CORPUS_NAME = "conversations.json"
CORPUS_FILE = BASE_DIR / DEFAULT_CORPUS_NAME
DAEMON_LOG  = STATE_DIR / "daemon.log"

DAEMON_CMD  = ["python3", "-u", "aurora_daemon.py"]

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_CHAIN_SEED_TICKS  = 20_000   # Legacy stage 2: light seed burn
DEFAULT_CHAIN_DEEP_TICKS  = 80_000   # Legacy stage 5: deep post-corpus burn
DEFAULT_CHAIN_K_MIN       = 2
DEFAULT_CHAIN_BOOTSTRAP   = 0.4

DEFAULT_CORPUS_BATCH_SIZE = 1_000
DEFAULT_CORPUS_PASSES     = "triple"
DEFAULT_OBSERVER_BATCH    = 15
DEFAULT_STUDY_CYCLES      = 1
DEFAULT_SENSORY_CONCEPTS  = 6
DEFAULT_SOCIAL_TURNS      = 8
DEFAULT_DREAM_EPISODES    = 4

# ── Logging ───────────────────────────────────────────────────────────────────
_log_fh = None

def _log(msg: str, also_print: bool = True):
    global _log_fh
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    if also_print:
        print(line, flush=True)
    if _log_fh:
        _log_fh.write(line + "\n")
        _log_fh.flush()


def _section(title: str):
    bar = "─" * 60
    _log(f"\n{bar}")
    _log(f"  {title}")
    _log(bar)

# ── Daemon control ────────────────────────────────────────────────────────────
def _find_daemon_pid() -> int | None:
    """Return PID of running aurora_daemon.py, or None."""
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "aurora_daemon.py"], text=True
        ).strip()
        pids = [int(p) for p in out.splitlines() if p.strip()]
        return pids[0] if pids else None
    except subprocess.CalledProcessError:
        return None


def _stop_daemon(timeout: int = 30) -> bool:
    pid = _find_daemon_pid()
    if pid is None:
        _log("  Daemon not running — nothing to stop.")
        return True
    _log(f"  Sending SIGTERM to daemon PID {pid}...")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1)
        if _find_daemon_pid() is None:
            _log("  Daemon stopped.")
            return True
    _log(f"  Daemon still running after {timeout}s — sending SIGKILL.")
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    time.sleep(2)
    return _find_daemon_pid() is None


def _start_daemon():
    _log("  Starting daemon (nohup)...")
    log_out = open(str(DAEMON_LOG), "a")
    proc = subprocess.Popen(
        DAEMON_CMD,
        cwd=str(BASE_DIR),
        stdout=log_out,
        stderr=log_out,
        start_new_session=True,
    )
    _log(f"  Daemon launched (PID {proc.pid}). Waiting 15s for boot...")
    time.sleep(15)
    if _find_daemon_pid():
        _log("  Daemon is running.")
    else:
        _log("  WARNING: Daemon PID not found after launch. Check daemon.log.")

# ── Stage helpers ─────────────────────────────────────────────────────────────
def _run_corpus(
    passes: str,
    corpus_file: Path,
    *,
    batch_size: int = DEFAULT_CORPUS_BATCH_SIZE,
    fast: bool = False,
    observer_batch: int = DEFAULT_OBSERVER_BATCH,
    quiet: bool = True,
) -> bool:
    _log(
        f"  Running corpus_runner --passes {passes} "
        f"--batch-size {batch_size:,}" +
        (" --fast" if fast else "")
    )
    t0 = time.time()
    cmd = [
        sys.executable, str(BASE_DIR / "corpus_runner.py"),
        "--corpus", str(corpus_file),
        "--passes", passes,
        "--batch-size", str(batch_size),
        "--batches", "1",
    ]
    if quiet:
        cmd.append("--quiet")
    if fast:
        cmd.append("--fast")
    if observer_batch > 0:
        cmd.extend(["--observer-batch", str(observer_batch)])
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    elapsed = time.time() - t0
    if result.returncode == 0:
        _log(f"  corpus_runner ({passes}) done in {elapsed/60:.1f}min.")
        return True
    else:
        _log(f"  corpus_runner ({passes}) FAILED (exit {result.returncode}).")
        return False


def _run_study(cycles: int) -> bool:
    _log(f"  Running study cycle(s): {cycles}")
    t0 = time.time()
    script = f"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from aurora import boot_aurora, study

state_dir = {json.dumps(str(STATE_DIR))}
systems = boot_aurora(state_dir=state_dir, verbose=False)
study(systems, cycles={int(cycles)}, verbose=False)

perception = systems.get("perception")
oets = getattr(perception, "oets", None) if perception else None
stats = oets.get_stats() if oets else {{}}
web = stats.get("web", {{}}) if isinstance(stats, dict) else {{}}
print(json.dumps({{
    "study_cycles": {int(cycles)},
    "oets_nodes": int(web.get("total_nodes", 0) or 0),
    "oets_relations": int(web.get("total_relations", 0) or 0),
}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    if result.returncode == 0:
        summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if summary:
            _log(f"  Study summary: {summary}")
        _log(f"  Study done in {elapsed:.1f}s.")
        return True
    _log(f"  Study FAILED (exit {result.returncode}).")
    if result.stderr.strip():
        _log(f"  Study stderr: {result.stderr.strip()[:400]}")
    return False


def _run_sensory_grounding(max_concepts: int) -> bool:
    _log(f"  Running sensory grounding (up to {max_concepts} concept image(s))")
    t0 = time.time()
    script = f"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from aurora import boot_aurora
from aurora_concept_imager import run_concept_image_cycle

state_dir = {json.dumps(str(STATE_DIR))}
systems = boot_aurora(state_dir=state_dir, verbose=False)

perception = systems.get("perception")
oets = getattr(perception, "oets", None) if perception else None
if oets is None:
    raise SystemExit("oets unavailable for sensory grounding")

hardware = systems.get("hardware")
sensory_crystal = systems.get("sensory_crystal")
vision_bootstrap = systems.get("vision_bootstrap")
sensory_integration = systems.get("sensory_integration")

before = vision_bootstrap.status() if vision_bootstrap and hasattr(vision_bootstrap, "status") else {{}}
grounded = int(
    run_concept_image_cycle(
        oets=oets,
        hardware=hardware,
        sensory_crystal=sensory_crystal,
        state_dir=state_dir,
        max_per_run={int(max_concepts)},
    ) or 0
)

ingest_result = {{}}
seed_dir = str(Path(state_dir) / "vision_seeds")
if vision_bootstrap and hasattr(vision_bootstrap, "ingest_folder"):
    ingest_result = dict(vision_bootstrap.ingest_folder(seed_dir) or {{}})

after = vision_bootstrap.status() if vision_bootstrap and hasattr(vision_bootstrap, "status") else {{}}
sensory_stats = sensory_integration.get_stats() if sensory_integration and hasattr(sensory_integration, "get_stats") else {{}}
crystal_state = sensory_crystal.get_state() if sensory_crystal and hasattr(sensory_crystal, "get_state") else {{}}

if sensory_crystal and hasattr(sensory_crystal, "save"):
    try:
        sensory_crystal.save()
    except Exception:
        pass

print(json.dumps({{
    "concept_images_grounded": grounded,
    "vision_before": {{
        "vectors": int(before.get("vectors_indexed", 0) or 0),
        "clusters": int(before.get("clusters", 0) or 0),
        "named_clusters": int(before.get("named_clusters", 0) or 0),
    }},
    "vision_ingest": ingest_result,
    "vision_after": {{
        "vectors": int(after.get("vectors_indexed", 0) or 0),
        "clusters": int(after.get("clusters", 0) or 0),
        "named_clusters": int(after.get("named_clusters", 0) or 0),
    }},
    "sensory_events_processed": int(sensory_stats.get("events_processed", 0) or 0),
    "sensory_visual_concepts": int(((crystal_state.get("recognitions") or {{}}).get("visual_total", 0)) or 0),
    "sensory_audio_concepts": int(((crystal_state.get("recognitions") or {{}}).get("audio_total", 0)) or 0),
}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    if result.returncode == 0:
        summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if summary:
            _log(f"  Sensory summary: {summary}")
        _log(f"  Sensory grounding done in {elapsed:.1f}s.")
        return True
    _log(f"  Sensory grounding FAILED (exit {result.returncode}).")
    if result.stderr.strip():
        _log(f"  Sensory stderr: {result.stderr.strip()[:400]}")
    if result.stdout.strip():
        _log(f"  Sensory stdout: {result.stdout.strip()[:400]}")
    return False


def _run_socialize(turns: int, topic: str | None = None) -> bool:
    _log(f"  Running socialization session ({turns} turns" + (f", topic={topic}" if topic else "") + ")")
    t0 = time.time()
    script = f"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from aurora import boot_aurora, process_external_user_turn
from aurora_gpt_learning_session import run_learning_session
from aurora_daemon import _document_session_learnings

state_dir = {json.dumps(str(STATE_DIR))}
topic = {topic!r}
systems = boot_aurora(state_dir=state_dir, verbose=False)

def _gen(prompt_text, source="gauntlet_social"):
    if not prompt_text or len(str(prompt_text).split()) < 3:
        return None
    result = process_external_user_turn(
        systems,
        str(prompt_text),
        source_label=f"aurora:{{source}}",
        session_id="gauntlet_social",
        auto_search_enabled=False,
        record_exchange=False,
        update_interactive_state=False,
        track_evolutionary_trace=True,
        run_periodic_maintenance=True,
        mode_name="AGENTIC",
    )
    return result.get("resp_A")

systems["_generate_fn"] = _gen
try:
    exchanges = run_learning_session(
        systems,
        n_turns={int(turns)},
        topic=topic,
        verbose=False,
    )
    _document_session_learnings(systems, exchanges or [], topic=topic)
finally:
    systems.pop("_generate_fn", None)

if not exchanges:
    raise SystemExit("socialization produced 0 exchanges")

dt = systems.get("dream_trainer")
top_fails = []
if dt is not None and hasattr(dt, "ledger"):
    try:
        top_fails = list(dt.ledger.get_top_fails(3) or [])
    except Exception:
        top_fails = []

print(json.dumps({{
    "exchanges": len(exchanges),
    "top_fails": top_fails,
}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    if result.returncode == 0:
        summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if summary:
            _log(f"  Social summary: {summary}")
        _log(f"  Socialization done in {elapsed:.1f}s.")
        return True
    _log(f"  Socialization FAILED (exit {result.returncode}).")
    if result.stderr.strip():
        _log(f"  Socialization stderr: {result.stderr.strip()[:400]}")
    if result.stdout.strip():
        _log(f"  Socialization stdout: {result.stdout.strip()[:400]}")
    return False


def _run_dream(episodes: int) -> bool:
    _log(f"  Running dream burst ({episodes} episode(s))")
    t0 = time.time()
    script = f"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from aurora import boot_aurora
from corpus_runner import simulation_burst

state_dir = {json.dumps(str(STATE_DIR))}
systems = boot_aurora(state_dir=state_dir, verbose=False)
result = simulation_burst(systems, episodes={int(episodes)}, verbose=False)
print(json.dumps({{
    "avg_fitness": float(result.get("avg_fitness", 0.0) or 0.0),
    "learner_shards": int(result.get("learner_shards", 0) or 0),
    "response_pressure_specs": int(result.get("response_pressure_specs", 0) or 0),
}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    if result.returncode == 0:
        summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if summary:
            _log(f"  Dream summary: {summary}")
        _log(f"  Dream burst done in {elapsed:.1f}s.")
        return True
    _log(f"  Dream burst FAILED (exit {result.returncode}).")
    if result.stderr.strip():
        _log(f"  Dream stderr: {result.stderr.strip()[:400]}")
    return False


def _run_chain(ticks: int, label: str) -> bool:
    _log(f"  Running run_chain burn ({label}, ticks={ticks:,}) ...")
    t0 = time.time()
    result = subprocess.run(
        [
            sys.executable, str(BASE_DIR / "run_chain.py"),
            "--mode", "burn",
            "--ticks", str(ticks),
            "--out", str(GENEAL_DIR),
            "--k-min", str(DEFAULT_CHAIN_K_MIN),
            "--stagnation-bootstrap-ratio", str(DEFAULT_CHAIN_BOOTSTRAP),
            "--quiet",
        ],
        cwd=str(BASE_DIR),
    )
    elapsed = time.time() - t0
    _log_chain_stats()
    if result.returncode == 0:
        _log(f"  run_chain ({label}) done in {elapsed/60:.1f}min.")
        return True
    else:
        _log(f"  run_chain ({label}) FAILED (exit {result.returncode}).")
        return False


def _log_chain_stats():
    try:
        links_path = GENEAL_DIR / "links.json"
        ab_path    = GENEAL_DIR / "abilities.json"
        ts_path    = GENEAL_DIR / "tick_state.json"
        n_links    = len(json.loads(links_path.read_text())) if links_path.exists() else "?"
        n_ab       = len(json.loads(ab_path.read_text())) if ab_path.exists() else "?"
        ts         = json.loads(ts_path.read_text()) if ts_path.exists() else {}
        ticks      = ts.get("tick_count", "?")
        _log(f"  Genealogy: {n_links} links | {n_ab} abilities | {ticks} ticks total")
    except Exception:
        pass


def _log_competency_snapshot(label: str = ""):
    """Boot Aurora briefly in a subprocess and log all four competency dimensions."""
    tag = f" [{label}]" if label else ""
    script = f"""
import json, os, sys
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora

state_dir = {json.dumps(str(STATE_DIR))}
try:
    systems = boot_aurora(state_dir=state_dir, verbose=False)
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    sys.exit(0)

sensory          = systems.get("sensory")
sensory_crystal  = systems.get("sensory_crystal")
sensory_integ    = systems.get("sensory_integration")

visual_comp = {{}}
try:
    visual_comp = dict(sensory.get_visual_competency() or {{}}) if sensory else {{}}
except Exception:
    pass

audio_comp = {{}}
try:
    audio_comp = dict(sensory.get_audio_competency() or {{}}) if sensory else {{}}
except Exception:
    pass

intent_comp = {{}}
try:
    cs = sensory_crystal.get_state() if sensory_crystal and hasattr(sensory_crystal, "get_state") else {{}}
    intent_comp = {{
        "maturity":            round(float(cs.get("maturity", 0.0) or 0.0), 3),
        "semantic_nodes":      int(cs.get("semantic_nodes", 0) or 0),
        "audio_promoted":      sum(int((v or {{}}).get("promoted", 0) or 0)
                                    for v in (cs.get("audio") or {{}}).values()),
        "visual_promoted":     sum(int((v or {{}}).get("promoted", 0) or 0)
                                    for v in (cs.get("visual") or {{}}).values()),
        "cross_modal_promoted": sum(int((v or {{}}).get("promoted", 0) or 0)
                                    for v in (cs.get("lanes") or {{}}).values()),
    }}
except Exception:
    pass

integration_comp = {{}}
try:
    si = sensory_integ.get_stats() if sensory_integ and hasattr(sensory_integ, "get_stats") else {{}}
    integration_comp = {{
        "visual_processed":  int(si.get("visual_processed", 0) or 0),
        "audio_processed":   int(si.get("audio_processed", 0) or 0),
        "concepts_grounded": int(si.get("concepts_grounded", 0) or 0),
        "speech_transcribed": int(si.get("speech_transcribed", 0) or 0),
    }}
except Exception:
    pass

print(json.dumps({{
    "visual_competency":   visual_comp,
    "audio_competency":    audio_comp,
    "intent_competency":   intent_comp,
    "integration_competency": integration_comp,
}}))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        _log(f"  Competency snapshot{tag}: timed out.")
        return

    if not result.stdout.strip():
        _log(f"  Competency snapshot{tag}: no output (exit {result.returncode}).")
        if result.stderr.strip():
            _log(f"    stderr: {result.stderr.strip()[:300]}")
        return

    last_line = result.stdout.strip().splitlines()[-1]
    try:
        snap = json.loads(last_line)
    except Exception:
        _log(f"  Competency snapshot{tag}: parse error — {last_line[:200]}")
        return

    if "error" in snap:
        _log(f"  Competency snapshot{tag}: boot error — {snap['error'][:200]}")
        return

    def _fmt(d: dict, keys: list) -> str:
        parts = []
        for k in keys:
            v = d.get(k)
            if v is None:
                parts.append(f"{k}=?")
            else:
                try:
                    parts.append(f"{k}={float(v):.3f}")
                except (TypeError, ValueError):
                    parts.append(f"{k}={v}")
        return "  ".join(parts)

    vc = snap.get("visual_competency") or {}
    ac = snap.get("audio_competency") or {}
    ic = snap.get("intent_competency") or {}
    gc = snap.get("integration_competency") or {}

    _log(f"  ── Competency snapshot{tag} ──────────────────────────────────")
    if vc:
        _log(f"  Visual competency   : {_fmt(vc, ['focus','motion_sensitivity','recognition_threshold','detail_orientation'])}")
    if ac:
        _log(f"  Audio competency    : {_fmt(ac, ['sensitivity','voice_isolation','emotion_detection'])}")
    if ic:
        _log(f"  Intent competency   : maturity={ic.get('maturity','?')}  "
             f"semantic_nodes={ic.get('semantic_nodes','?')}  "
             f"cross_modal_promoted={ic.get('cross_modal_promoted','?')}  "
             f"audio_promoted={ic.get('audio_promoted','?')}  "
             f"visual_promoted={ic.get('visual_promoted','?')}")
    if gc:
        _log(f"  Integration competency: visual_processed={gc.get('visual_processed','?')}  "
             f"audio_processed={gc.get('audio_processed','?')}  "
             f"concepts_grounded={gc.get('concepts_grounded','?')}  "
             f"speech_transcribed={gc.get('speech_transcribed','?')}")
    _log(f"  ─────────────────────────────────────────────────────────────")


def _run_assimilation() -> bool:
    _log("  Running assimilation cycle (CapabilityAssimilator + SecondGenInjector)...")
    t0 = time.time()
    script = """
import sys, os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
from aurora_internal.aurora_capability_assimilator import CapabilityAssimilator

systems = boot_aurora(state_dir=str(STATE_DIR), verbose=False)
genealogy = systems.get("genealogy")
if genealogy is None:
    print("  [ASSIM] No genealogy — skipped.")
    sys.exit(1)

assim = CapabilityAssimilator(os.getcwd())
dt = systems.get("dream_trainer")
ledger = getattr(dt, "ledger", None) if dt else None
result = assim.assimilate_all(genealogy, fail_ledger=ledger)
new   = result.get("total_new", 0)
total = result.get("total_assimilated", 0)
print(f"  [ASSIM] {new} new | {total} total assimilated")

# Flush genealogy
chamber = systems.get("chamber")
if chamber and hasattr(chamber, "_genealogy"):
    chamber._genealogy.flush_files()
if dt:
    dt.ledger.save()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BASE_DIR),
    )
    elapsed = time.time() - t0
    if result.returncode == 0:
        _log(f"  Assimilation done in {elapsed:.1f}s.")
        return True
    else:
        _log(f"  Assimilation FAILED (exit {result.returncode}).")
        return False


def _run_code_mutation() -> bool:
    _log("  Running code mutation (latent_promotion)...")
    t0 = time.time()
    script = """
import sys, os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
from aurora_internal.aurora_code_autoevolver import CodeAutoEvolver
from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
import py_compile

systems = boot_aurora(state_dir=str(STATE_DIR), verbose=False)
genealogy = systems.get("genealogy")
if genealogy is None:
    print("  [MUTATE] No genealogy — skipped.")
    sys.exit(1)

links = len(getattr(genealogy, "links", {}) or {})
print(f"  [MUTATE] {links} links available for mutation signal.")

autoevolver = CodeAutoEvolver(os.getcwd())
target = "aurora_internal/aurora_evolved_surfaces.py"
chamber = systems.get("code_evolution_chamber")
if chamber is None:
    chamber = CodeEvolutionChamber(repo_root=os.getcwd())
    systems["code_evolution_chamber"] = chamber

before = None
try:
    before = chamber.snapshot(target_files=[target])
except Exception as _before_e:
    print(f"  [MUTATE] Chamber pre-snapshot unavailable: {_before_e}")

result = autoevolver.apply_operator(operator_key="latent_promotion", target_files=[target])
changed_files = list(result.get("changed_files", []) or []) if isinstance(result, dict) else []
backups = dict(result.get("backups", {}) or {}) if isinstance(result, dict) else {}
after = None
trace = None
if changed_files:
    try:
        after = chamber.snapshot(target_files=changed_files)
    except Exception as _after_e:
        print(f"  [MUTATE] Chamber post-snapshot unavailable: {_after_e}")
    try:
        trace = chamber.propose_mutation(
            name="autoevolver:latent_promotion",
            constraints_used=["temporal", "agency"],
            target_files=changed_files,
            meta={
                "operator_key": "latent_promotion",
                "source": "run_gauntlet",
                "changed_files": list(changed_files),
                "backups": list(backups.keys()),
                "file_timings": list(result.get("file_timings", []) or []),
                "manifest": dict(result.get("manifest", {}) or {}),
            },
        )
    except Exception as _trace_e:
        print(f"  [MUTATE] Chamber trace unavailable: {_trace_e}")

compile_ok = True
for path in changed_files:
    if not str(path).endswith(".py"):
        continue
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as ce:
        print(f"  [MUTATE] Compile FAILED on {path}: {ce} — rolling back.")
        compile_ok = False
        break

if trace is not None and before is not None and after is not None:
    try:
        chamber.observe_mutation(
            trace=trace,
            before=before,
            after=after,
            checks_passed=bool(compile_ok),
            notes={
                "source": "run_gauntlet",
                "operator_key": "latent_promotion",
                "changed_files": list(changed_files),
                "compile_ok": bool(compile_ok),
                "file_timings": list(result.get("file_timings", []) or []),
                "manifest": dict(result.get("manifest", {}) or {}),
            },
        )
    except Exception as _observe_e:
        print(f"  [MUTATE] Chamber observation unavailable: {_observe_e}")

if not compile_ok:
    if backups:
        autoevolver.rollback(backups)
    sys.exit(1)

changed = len(changed_files)
if changed:
    print(f"  [MUTATE] Surfaces updated ({changed} file(s) changed).")
else:
    print("  [MUTATE] No changes produced — operator had nothing new to surface.")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BASE_DIR),
    )
    elapsed = time.time() - t0
    if result.returncode == 0:
        _log(f"  Code mutation done in {elapsed:.1f}s.")
        return True
    else:
        _log(f"  Code mutation FAILED (exit {result.returncode}).")
        return False

# ── Trim pressure log (prevent slow boots) ───────────────────────────────────
def _trim_pressure_log(keep_lines: int = 20_000):
    p = STATE_DIR / "surface_pressure_log.jsonl"
    if not p.exists():
        return
    size_mb = p.stat().st_size / 1_048_576
    if size_mb < 20:
        return
    _log(f"  Trimming surface_pressure_log.jsonl ({size_mb:.0f}MB → last {keep_lines:,} lines)...")
    import subprocess as sp
    tmp = str(p) + ".trim"
    sp.run(f"tail -n {keep_lines} '{p}' > '{tmp}' && mv '{tmp}' '{p}'", shell=True, check=True)
    new_mb = p.stat().st_size / 1_048_576
    _log(f"  Trimmed to {new_mb:.1f}MB.")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="Aurora Evolution Gauntlet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Default flow (`--flow learning_arc`):
  0  Stop daemon
  1  Corpus trainer run
  2  Study
  3  Sensory grounding
  4  Socialization
  5  Dream
  6  Restart daemon

Legacy flow (`--flow legacy`):
  0  Stop daemon
  1  Corpus observer pass
  2  Chain burn — light seed
  3  Corpus triple pass
  4  Assimilation cycle
  5  Chain burn — deep
  6  Code mutation
  7  Restart daemon
""",
    )
    ap.add_argument("--flow", type=str, default="learning_arc",
                    choices=("learning_arc", "legacy"),
                    help="Gauntlet sequence to run (default: learning_arc)")
    ap.add_argument("--corpus-file", type=str, default=None,
                    help="Override corpus file path for corpus stages")
    ap.add_argument("--skip-corpus",    action="store_true",
                    help="Skip both corpus passes (use if corpus was run recently)")
    ap.add_argument("--skip-observer",  action="store_true",
                    help="Skip legacy stage 1 observer pass only")
    ap.add_argument("--corpus-passes", type=str, default=DEFAULT_CORPUS_PASSES,
                    help="Pass mode for learning_arc corpus stage (default: triple)")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_CORPUS_BATCH_SIZE,
                    help="Messages to process in learning_arc corpus stage (default: 1000)")
    ap.add_argument("--observer-batch", type=int, default=DEFAULT_OBSERVER_BATCH,
                    help="Observer batch size for fast corpus mode (default: 15)")
    ap.add_argument("--study-cycles", type=int, default=DEFAULT_STUDY_CYCLES,
                    help="Study cycles after corpus in learning_arc flow")
    ap.add_argument("--sensory-concepts", type=int, default=DEFAULT_SENSORY_CONCEPTS,
                    help="Max concept images to ground during the sensory stage")
    ap.add_argument("--social-turns", type=int, default=DEFAULT_SOCIAL_TURNS,
                    help="GPT social turns in learning_arc flow")
    ap.add_argument("--social-topic", type=str, default=None,
                    help="Optional topic for the learning_arc social stage")
    ap.add_argument("--dream-episodes", type=int, default=DEFAULT_DREAM_EPISODES,
                    help="Dream episodes in learning_arc flow")
    ap.add_argument("--chain-seed-ticks", type=int, default=DEFAULT_CHAIN_SEED_TICKS,
                    help=f"Ticks for legacy light seed burn (default {DEFAULT_CHAIN_SEED_TICKS:,})")
    ap.add_argument("--chain-deep-ticks", type=int, default=DEFAULT_CHAIN_DEEP_TICKS,
                    help=f"Ticks for legacy deep post-corpus burn (default {DEFAULT_CHAIN_DEEP_TICKS:,})")
    ap.add_argument("--no-restart",     action="store_true",
                    help="Leave daemon stopped after gauntlet")
    ap.add_argument("--stages",         type=str, default=None,
                    help="Comma-separated list of stage numbers to run (e.g. 3,4,5)")
    args = ap.parse_args()

    corpus_file = Path(args.corpus_file).expanduser() if args.corpus_file else (BASE_DIR / DEFAULT_CORPUS_NAME)

    # Parse stage filter
    only_stages = None
    if args.stages:
        only_stages = {int(s.strip()) for s in args.stages.split(",")}

    def _should_run(n: int) -> bool:
        return only_stages is None or n in only_stages

    # Open log
    global _log_fh
    _log_fh = open(str(LOG_FILE), "a")

    _section("AURORA EVOLUTION GAUNTLET")
    _log(f"  Base dir : {BASE_DIR}")
    _log(f"  Flow     : {args.flow}")
    _log(f"  Corpus   : {corpus_file} ({corpus_file.stat().st_size // 1_048_576}MB)" if corpus_file.exists() else f"  Corpus   : NOT FOUND ({corpus_file})")
    if args.flow == "legacy":
        _log(f"  Chain    : seed={args.chain_seed_ticks:,}  deep={args.chain_deep_ticks:,}")
    else:
        _log(
            f"  Learning : passes={args.corpus_passes} batch={args.batch_size:,} "
            f"study={args.study_cycles} sensory={args.sensory_concepts} "
            f"social={args.social_turns} dream={args.dream_episodes}"
        )
    _log(f"  Stages   : {args.stages or 'all'}")

    results = {}
    t_total = time.time()

    if args.flow == "legacy":
        # ── Stage 0: Stop daemon ──────────────────────────────────────────────
        if _should_run(0):
            _section("Stage 0 — Stop Daemon")
            results[0] = _stop_daemon()

        # ── Stage 1: Corpus observer pass ─────────────────────────────────────
        if _should_run(1) and not args.skip_corpus and not args.skip_observer:
            _section("Stage 1 — Corpus Observer Pass")
            if not corpus_file.exists():
                _log("  SKIPPED — corpus file not found.")
                results[1] = False
            else:
                results[1] = _run_corpus("observer", corpus_file, quiet=True)

        # ── Stage 2: Chain burn — light seed ──────────────────────────────────
        if _should_run(2):
            _section("Stage 2 — Chain Burn (light seed)")
            results[2] = _run_chain(args.chain_seed_ticks, "seed")

        # ── Stage 3: Corpus triple pass ───────────────────────────────────────
        if _should_run(3) and not args.skip_corpus:
            _section("Stage 3 — Corpus Triple Pass (observer → responder → reverse)")
            if not corpus_file.exists():
                _log("  SKIPPED — corpus file not found.")
                results[3] = False
            else:
                results[3] = _run_corpus("triple", corpus_file, quiet=True)

        # ── Stage 4: Assimilation ─────────────────────────────────────────────
        if _should_run(4):
            _section("Stage 4 — Assimilation Cycle")
            results[4] = _run_assimilation()

        # ── Stage 5: Chain burn — deep ────────────────────────────────────────
        if _should_run(5):
            _section("Stage 5 — Chain Burn (deep post-corpus)")
            results[5] = _run_chain(args.chain_deep_ticks, "deep")

        # ── Stage 6: Code mutation ────────────────────────────────────────────
        if _should_run(6):
            _section("Stage 6 — Code Mutation (latent_promotion)")
            results[6] = _run_code_mutation()

        _trim_pressure_log()

        # ── Stage 7: Restart daemon ───────────────────────────────────────────
        if _should_run(7) and not args.no_restart:
            _section("Stage 7 — Restart Daemon")
            _start_daemon()
    else:
        # ── Stage 0: Stop daemon ──────────────────────────────────────────────
        if _should_run(0):
            _section("Stage 0 — Stop Daemon")
            results[0] = _stop_daemon()

        # ── Stage 1: Corpus trainer run ───────────────────────────────────────
        if _should_run(1) and not args.skip_corpus:
            _section("Stage 1 — Corpus Trainer Run")
            if not corpus_file.exists():
                _log("  SKIPPED — corpus file not found.")
                results[1] = False
            else:
                results[1] = _run_corpus(
                    args.corpus_passes,
                    corpus_file,
                    batch_size=max(0, int(args.batch_size)),
                    fast=True,
                    observer_batch=max(0, int(args.observer_batch)),
                    quiet=False,
                )

        # ── Stage 2: Study ────────────────────────────────────────────────────
        if _should_run(2):
            _section("Stage 2 — Study")
            results[2] = _run_study(max(1, int(args.study_cycles)))

        # ── Stage 3: Sensory grounding ────────────────────────────────────────
        if _should_run(3):
            _section("Stage 3 — Sensory Grounding")
            results[3] = _run_sensory_grounding(max(1, int(args.sensory_concepts)))

        # ── Stage 4: Socialization ────────────────────────────────────────────
        if _should_run(4):
            _section("Stage 4 — Socialization")
            results[4] = _run_socialize(
                max(1, int(args.social_turns)),
                topic=args.social_topic,
            )

        # ── Stage 5: Dream ────────────────────────────────────────────────────
        if _should_run(5):
            _section("Stage 5 — Dream")
            results[5] = _run_dream(max(1, int(args.dream_episodes)))

        _trim_pressure_log()

        # ── Stage 6: Restart daemon ───────────────────────────────────────────
        if _should_run(6) and not args.no_restart:
            _section("Stage 6 — Restart Daemon")
            _start_daemon()

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed_total = time.time() - t_total
    _section(f"GAUNTLET COMPLETE  ({elapsed_total/60:.1f} min total)")
    for stage, ok in sorted(results.items()):
        status = "OK" if ok else "FAILED"
        _log(f"  Stage {stage}: {status}")
    _log_chain_stats()
    _log_competency_snapshot()
    _log(f"\n  Full log: {LOG_FILE}")

    if _log_fh:
        _log_fh.close()


if __name__ == "__main__":
    main()
