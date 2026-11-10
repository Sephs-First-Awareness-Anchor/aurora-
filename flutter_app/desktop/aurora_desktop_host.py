"""Stdio transport for the Flutter desktop runner and the existing app bridge."""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import traceback


ENGINE = Path(__file__).resolve().parents[2]
ANDROID = ENGINE / "flutter_app" / "android" / "app" / "src" / "main"

# Match the Android method channel's app operations. Hardware calls stay in
# MainActivity; the desktop host has no network listener or dynamic dispatch.
METHODS = {
    "sendMessage": ("handle_message", ("text",)),
    "getSelfModel": ("get_self_model", ()),
    "getCognitiveStats": ("get_cognitive_stats", ()),
    "getLiveTurnDiagnostics": ("get_live_turn_diagnostics", ()),
    "getRoomState": ("get_room_state", ()),
    "provideRoomCommand": ("provide_room_command", ("cmd",)),
    "getPraxisStatus": ("get_praxis_status", ()),
    "pausePraxis": ("pause_praxis", ()),
    "resumePraxis": ("resume_praxis", ()),
    "startGauntlet": ("start_gauntlet", ()),
    "stopGauntlet": ("stop_gauntlet", ()),
    "getGauntletStatus": ("get_gauntlet_status", ()),
    "triggerCuriosityCycle": ("trigger_curiosity_cycle", ("n",)),
    "triggerEvoCycle": ("trigger_evo_cycle", ("ticks",)),
    "habitatGetAffordances": ("habitat_get_affordances", ()),
    "habitatGetState": ("habitat_get_state", ("params",)),
    "habitatGetEntity": ("habitat_get_entity", ("params",)),
    "habitatGetHistory": ("habitat_get_history", ("params",)),
    "habitatGetLineage": ("habitat_get_lineage", ("entityId",)),
    "habitatAct": ("habitat_act", ("actionJson",)),
    "habitatIntegrityReport": ("habitat_integrity_report", ()),
    "habitatBackup": ("habitat_backup", ()),
    "habitatRestore": ("habitat_restore", ("backupPath",)),
    "habitatIsolateCorrupt": ("habitat_isolate_corrupt", ()),
    "habitatReset": ("habitat_reset", ()),
}


def _lock_state(handle) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        raise RuntimeError("Aurora is already using this state directory") from exc


def _serve(state: Path, emit) -> int:
    sys.path.insert(0, str(ENGINE))
    # Search installed packages first, especially the real desktop cv2.
    sys.path.append(str(ANDROID / "python"))
    os.chdir(state)
    os.environ["AURORA_STATE_DIR"] = str(state)

    baseline = state / "experiential_baseline_v1.zip"
    bundled = ANDROID / "assets" / "aurora_experiential_baseline_v1.zip"
    if bundled.is_file() and (not baseline.exists() or baseline.stat().st_size == 0):
        temporary = baseline.with_suffix(".tmp")
        shutil.copyfile(bundled, temporary)
        temporary.replace(baseline)

    import aurora_bridge as bridge

    status = bridge.initialize(str(state), android=False)
    if status.startswith("error"):
        emit(event={"type": "error", "text": status})
        return 1
    emit(event={"type": "ready", "text": status,
                "health": json.loads(bridge.record_boot_health())})

    stopping = threading.Event()

    def forward_events() -> None:
        while not stopping.wait(3):
            try:
                axes = json.loads(bridge.get_axis_state())
                emit(event={**axes, "type": "axis_state"})
                for read in (bridge.get_pending_report, bridge.get_proactive_expression,
                             bridge.get_late_surface_response):
                    text = read()
                    if text:
                        emit(event={"type": "proactive", "text": text})
            except BrokenPipeError:
                return
            except Exception:
                traceback.print_exc()

    def reply(request: dict) -> None:
        request_id = request["id"]
        try:
            method = request["method"]
            args = request.get("args") or {}
            if method == "uploadContent":
                value = bridge.provide_uploaded_content(
                    base64.b64decode(args["bytes"], validate=True),
                    args["filename"], args["contentType"],
                )
            else:
                name, keys = METHODS[method]
                value = getattr(bridge, name)(*(args[key] for key in keys))
        except Exception as exc:
            emit(id=request_id, error=f"{type(exc).__name__}: {exc}")
        else:
            emit(id=request_id, value=value)

    threading.Thread(target=forward_events, daemon=True).start()
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="aurora-turn") as turns:
            for line in sys.stdin:
                request = json.loads(line)
                if request["method"] in {"sendMessage", "uploadContent"}:
                    turns.submit(reply, request)
                else:
                    reply(request)
    finally:
        stopping.set()
    return 0


def main() -> int:
    # Third-party modules and Aurora write progress to stdout. Reserve its
    # original pipe for JSON, including when a native module prints directly.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    output_lock = threading.Lock()

    def emit(**message) -> None:
        with output_lock:
            protocol.write(json.dumps(message, ensure_ascii=False) + "\n")
            protocol.flush()

    try:
        state = Path(sys.argv[1]).resolve()
        state.mkdir(parents=True, exist_ok=True)
        with (state / ".desktop.lock").open("a+b") as handle:
            _lock_state(handle)
            return _serve(state, emit)
    except BrokenPipeError:
        return 0
    except Exception as exc:
        traceback.print_exc()
        emit(event={"type": "error", "text": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
