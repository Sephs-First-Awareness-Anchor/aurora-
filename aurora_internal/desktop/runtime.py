"""One resident organism; UI lifetime is independent of cognitive continuity.

Boot, turns, developmental cycles and host actions use the same canonical organs
and field lock. HTTP/owner diagnostics remain on separate threads. This is host
orchestration, not another reasoning, learning or promotion implementation.
"""
from __future__ import annotations

import itertools
import os
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from .blueprints import BlueprintSpace
from .common import read_json, write_json
from .demonstrations import Demonstrations
from .policy import owner_action
from .services import HostServices, discover_host


class DesktopRuntime:
    def __init__(self, state_dir, *, boot=None, turn=None, provider=discover_host, adapter=None,
                 background=True):
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._boot, self._turn = boot, turn
        self._owns_canonical_engine = boot is None
        self.background = background
        self.systems = {}
        self.field_lock = threading.RLock()
        self._jobs_lock = threading.RLock()
        self._queue = queue.PriorityQueue(maxsize=64)
        self._serial = itertools.count()
        self._stop = threading.Event()
        self._thread = None
        self.stage = "stopped"
        self.errors = {}
        self.last_live = 0.0
        self.active_job = None
        self.jobs_path = self.state_dir / "desktop_jobs.json"
        self.jobs = read_json(self.jobs_path, {})
        for job in self.jobs.values():
            if job.get("status") in {"queued", "running"}:
                job.update(status="interrupted", error="resident_restarted; action was not replayed")
        self.services = HostServices(self.state_dir, self.systems, provider=provider, adapter=adapter,
                                     observer=self._observe)
        self.blueprints = BlueprintSpace(self.state_dir)
        self.demonstrations = Demonstrations(self.state_dir, self.services, self.systems)
        self._workers = []
        self._tasks = {}
        self._due = {}
        self._tick_origin = None
        self._kernel_time = None
        self._pending_kernel = None
        self._coalesced_kernel = 0
        self._kernel_lock = threading.Lock()
        self._axes = {a: 0.5 for a in "XTNBA"}
        self.link = None
        self.acm = None
        self.surface_id = "desktop"
        self._diagnostics = {}
        self.first_pairing_applied = None
        self.home_requests_seen = {}
        self.pending_moves = []
        self.inquiry_desk = None
        self._move_job = None

    def _persist_jobs(self):
        with self._jobs_lock:
            completed = [k for k, v in self.jobs.items() if v.get("status") not in {"queued", "running"}]
            for k in completed[:-200]:
                del self.jobs[k]
            write_json(self.jobs_path, self.jobs)

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self.stage = "booting"
        self._thread = threading.Thread(target=self._run, name="aurora-resident-field", daemon=True)
        self._thread.start()
        return True

    def live_idle(self):
        return not self._stop.is_set() and self._queue.empty() and not self.active_job and time.monotonic() - self.last_live > 3

    def surface_idle(self):
        return self.live_idle() and (self.link is None or self.link.surface_ready(self.surface_id))

    def submit(self, kind, payload=None, *, owner=False, job_id=None):
        if self.stage in {"boot_failed", "stopped"}:
            raise RuntimeError("resident_not_available; use the independent owner console")
        if kind == "turn":
            self.last_live = time.monotonic()
            from aurora_curiosity_engine import interrupt_curiosity_cycles
            interrupt_curiosity_cycles()
            from aurora_internal.dual_strata.strata_link import publish_raw_input
            publish_raw_input(self.state_dir, str((payload or {}).get("text") or ""))
        jid = str(job_id or uuid.uuid4().hex)
        with self._jobs_lock:
            if jid in self.jobs:
                return self.jobs[jid]
            job = {"id": jid, "kind": kind, "status": "queued", "at": time.time()}
            self.jobs[jid] = job
            try:
                self._queue.put_nowait((0 if kind == "turn" else 5, next(self._serial), jid, kind, payload or {}, owner))
            except queue.Full:
                del self.jobs[jid]
                raise RuntimeError("resident_queue_full")
            self._persist_jobs()
            return dict(job)

    def job(self, jid):
        with self._jobs_lock:
            return dict(self.jobs.get(jid) or {})

    def _boot_once(self):
        os.environ["AURORA_STATE_DIR"] = str(self.state_dir)
        os.environ["AURORA_SKIP_DEP_INSTALL"] = "1"
        from aurora_internal.aurora_state_context import set_active_state_dir
        set_active_state_dir(str(self.state_dir))
        # A first-pairing migration whose choices are all made is installed
        # here, cold: before her stores are open in this process.
        try:
            from aurora_internal.dual_strata.strata_migration import apply_pending_migration
            applied = apply_pending_migration(self.state_dir)
            if applied is not None:
                self.first_pairing_applied = {k: applied.get(k) for k in
                                              ("ok", "migration_id", "error", "installed", "moved")}
        except Exception as exc:
            self.errors["first_pairing"] = f"{type(exc).__name__}: {exc}"[:300]
        if self._boot is None:
            import aurora
            self._boot, self._turn = aurora.boot_aurora, aurora.process_external_user_turn
        self.systems.update(self._boot(state_dir=str(self.state_dir), verbose=False, runtime_profile="full"))
        self.systems.update({"_desktop_runtime": self, "host_services": self.services,
                             "blueprint_space": self.blueprints, "desktop_demonstrations": self.demonstrations,
                             "_field_lock": self.field_lock})
        self.systems["_desktop_should_yield"] = lambda: not self._queue.empty() or self._stop.is_set()
        self.services.policy.systems = self.systems
        if self._turn is None:
            from aurora import process_external_user_turn
            self._turn = process_external_user_turn
        self.services.refresh()
        self._install_tools()
        if self.background:
            self._attach_existing_engines()
        self.blueprints.import_real(self.systems, self.services)
        self.stage = "online"
        self._started = time.monotonic()
        self._update_diagnostics()

    def _install_tools(self):
        from aurora_internal.tool_registry import _reg, ToolResult
        def register(name, fn, description):
            def invoke(**params):
                systems = params.pop("systems", {})
                # Registry definitions are process-wide; resolve the owning
                # organism from the supplied systems rather than a captured one.
                runtime = systems.get("_desktop_runtime")
                if runtime is None:
                    return ToolResult(name, "", False, "desktop_runtime_unavailable")
                try:
                    import json
                    result = fn(runtime, params)
                    return ToolResult(name, json.dumps(result, default=str), True)
                except Exception as exc:
                    return ToolResult(name, "", False, str(exc))
            _reg(name, description, "BOUNDED", invoke, disables_search=True)
        register("host_inventory", lambda r, p: r.services.status(), "Inspect actual host devices and service access")
        register("host_probe", lambda r, p: r.services.execute("host_probe", p), "Attempt a real device operation")
        register("blueprint_query", lambda r, p: r.blueprints.view(**p), "Inspect real computational structures")
        register("blueprint_compose", lambda r, p: r.blueprints.compose(**p), "Compose structures; unresolved effects remain hypotheses")
        register("demonstration_query", lambda r, p: r.demonstrations.view(), "Inspect observed owner demonstrations and outcomes")
        register("demonstration_propose", lambda r, p: r.demonstrations.propose(**p), "Propose an independent plan to demonstrate understanding")

    def _attach_existing_engines(self):
        import aurora
        import aurora_daemon as daemon
        from aurora_internal.aurora_runtime_constraint_governor import RuntimeConstraintGovernor
        self.governor = RuntimeConstraintGovernor(str(self.state_dir))
        self.systems["runtime_governor"] = self.governor
        for key, interval, fn in (
            ("study", 720, daemon._run_study_cycle), ("dream", 5400, daemon._run_dream_burst),
            ("assimilation", 3600, daemon._run_assimilation_cycle), ("classroom", 1800, daemon._run_classroom_cycle),
            ("pressure_routing", 60, daemon._run_pressure_routing), ("distill", 3600, daemon._run_distillation_cycle),
            ("save", 900, lambda s: aurora._full_save(s, verbose=False)),
            ("sensory", 300, daemon._run_sensory_crystal_consolidation),
            ("continuity", 1, daemon._consume_surface_continuity_feed)):
            self._tasks[key] = (interval, fn)
            self._due[key] = interval
        self._tasks["evo_tick"] = (15, self._development_tick)
        self._due["evo_tick"] = 15
        self._tasks["sensing"] = (5, self._sensing_tick)
        self._due["sensing"] = 5
        self._tasks["home_requests"] = (3, self._home_requests_tick)
        self._tasks["move"] = (2, self._move_tick)
        self._due["home_requests"] = 3
        # Mutation remains governed by the organism's existing self-modification
        # boundary, not enabled merely by installing a desktop interface.
        autonomy = self.systems.get("autonomy")
        if getattr(getattr(autonomy, "boundaries", None), "can_modify_self", False):
            self._tasks["mutation"] = (1800, daemon._run_code_mutation_cycle)
            self._due["mutation"] = 1800
        from aurora_dream_trainer import SkillMemory
        skill = SkillMemory(str(self.state_dir))
        skill.load()
        self.systems["skill_memory"] = skill
        registry = self.systems.get("_concept_crystal_registry")
        if not self.systems.get("cpm") and registry is not None and self.systems.get("lattice") is not None:
            from aurora_computational_model import CPMSession
            self.systems["cpm"] = CPMSession(self.systems["lattice"], registry, self.systems.get("genealogy"))
        engine = aurora._get_or_create_curiosity_engine(self.systems)
        if engine is not None:
            self._tasks["curiosity"] = (90, lambda s: engine.run_curiosity_cycle())
            self._due["curiosity"] = 90
        self.systems["_clone_harvest_absorb"] = {"status": "waiting_for_idle"}
        self._start_clone_absorption()
        from aurora_internal.dual_strata.subsurface_presence_runtime import start_subsurface_presence_runtime
        presence = start_subsurface_presence_runtime(self.systems, state_dir=self.state_dir)
        if presence:
            self._workers.append(presence)
        self._start_component("scout", self._start_scout)
        from aurora_internal.dual_strata.strata_link import (StrataLinkServer, device_name, listen_host,
                                                              surface_identity)
        self.surface_id = surface_identity(self.state_dir)
        # Home listens where the home setup chose (scripts/aurora_home_setup.py
        # pair), so a paired phone on the home network can reach her.
        self.link = StrataLinkServer(self.state_dir, host=listen_host(self.state_dir),
                                    port=int(os.environ.get("AURORA_STRATA_LINK_PORT", "8791")), state_install_allowed=False)
        self.link.set_home_surface(self.surface_id)
        self.link.handle_sync({"surface_id": self.surface_id, "name": device_name(self.state_dir)})
        self.link.start()
        self.systems["_strata_link_server"] = self.link
        self.systems["_desktop_surface_id"] = self.surface_id
        from aurora_praxis_bridge import start_praxis_bridge
        from aurora_praxis_messenger import start_praxis_messenger
        endpoint = os.environ.get("AURORA_PRAXIS_URL", "http://127.0.0.1:8787")
        for name, start in (("praxis_bridge", start_praxis_bridge), ("praxis_messenger", start_praxis_messenger)):
            def attach(start=start, name=name):
                obj = start(self.systems, state_dir=str(self.state_dir), endpoint=endpoint,
                            field_lock=self.field_lock, live_idle=self.surface_idle if name == "praxis_messenger" else self.live_idle)
                self.systems[name] = obj
                if obj:
                    self._workers.append(obj)
            self._start_component(name, attach)
        # The phone already starts the weekly LearningProbe as part of
        # experiential background; home must carry that same organ, sharing
        # the canonical systems, field lock and idle admission, not a second
        # cognition runtime. The probe's first run remains delayed an hour.
        self._start_component("learning_probe", self._attach_learning_probe)
        archive = self.state_dir / "experiential_baseline_v1.zip"
        if archive.exists():
            def history():
                app_python = Path(__file__).resolve().parents[2] / "flutter_app/android/app/src/main/python"
                sys.path.insert(0, str(app_python))
                from aurora_historical_experience_environment import start_historical_experience_environment
                obj = start_historical_experience_environment(self.systems, state_dir=str(self.state_dir),
                    archive_path=str(archive), field_lock=self.field_lock, live_idle=self.live_idle, initial_delay_s=30)
                self.systems["historical_experience"] = obj
                self._workers.append(obj)
            self._start_component("historical_experience", history)
        if os.environ.get("AURORA_ACM_BRIDGE") == "1":
            from aurora_acm_bridge import HostedACMBridge
            self.acm = HostedACMBridge(lambda: dict(self._axes), self._accept_kernel,
                                      port=int(os.environ.get("AURORA_ACM_PORT", "4567")))
            self.acm.start()

    def _attach_learning_probe(self):
        """Start exactly one existing developmental learning probe at home."""
        if self.systems.get("learning_probe") is not None:
            return self.systems["learning_probe"]
        from aurora_learning_probe import LearningProbe
        probe = LearningProbe(self.systems, state_dir=str(self.state_dir),
                              field_lock=self.field_lock, live_idle=self.live_idle)
        probe.start()
        self.systems["learning_probe"] = probe
        self._workers.append(probe)
        return probe

    def _start_scout(self):
        # Reuse the same worker entry used by the app; it claims the existing
        # broker queue and writes existing evidence bindings.
        from aurora_scout_daemon import run
        self._scout_stop = threading.Event()
        thread = threading.Thread(target=run, kwargs={"state_dir": str(self.state_dir),
                                  "stop_event": self._scout_stop}, daemon=True, name="aurora-desktop-scout")
        thread.start()
        self._scout_thread = thread

    def _start_clone_absorption(self):
        if getattr(self, "_clone_thread", None) and self._clone_thread.is_alive():
            return {"status": "running"}
        def absorb():
            from aurora_internal.aurora_clone_harvest import absorb_harvest
            self.systems["_clone_harvest_absorb"] = {"status": "absorbing_idle_batches"}
            try:
                result = absorb_harvest(self.systems, state_dir=str(self.state_dir),
                    field_lock=self.field_lock, live_idle=self.live_idle, stop_event=self._stop)
            except Exception as exc:
                result = {"status": "error", "error": str(exc)}
            self.systems["_clone_harvest_absorb"] = result
        self._clone_thread = threading.Thread(target=absorb, daemon=True, name="aurora-clone-absorption")
        self._clone_thread.start()
        return {"status": "absorbing_idle_batches"}

    def _development_tick(self, systems):
        chamber = systems.get("chamber")
        if chamber is not None:
            chamber.tick()
        from aurora_internal.dual_strata.predictive_stager import PredictiveStager
        _, offset = PredictiveStager.stage_passes_for_tick(systems, systems.get("working_memory"),
                    systems.get("_live_conscious_frame"), perspective_offset=systems.get("_predictive_stager_offset", 0))
        systems["_predictive_stager_offset"] = offset
        from aurora_internal.dual_strata.activation_field import run_activation_cycle
        run_activation_cycle(systems)

    def _home_requests_tick(self, systems):
        """What her surface asked home for.  A request brings the next pass of
        that work forward; home's own schedule and governor still decide."""
        from aurora_internal.dual_strata.strata_link import link_dir, read_home_requests
        offset_path = link_dir(self.state_dir) / "home_requests.offset"
        try:
            offset = int(offset_path.read_text(encoding="utf-8").strip() or 0)
        except (OSError, ValueError):
            offset = 0
        requests, offset = read_home_requests(self.state_dir, offset)
        done = self.home_requests_seen
        for req in requests:
            kind = str(req.get("kind") or "")
            task = {"curiosity_cycle": "curiosity", "evo_cycle": "evo_tick"}.get(kind)
            if task and task in self._due:
                self._due[task] = 0
                done[kind] = done.get(kind, 0) + 1
            elif kind == "embodiment_move":
                self._embodiment_move_requested(req)
                done[kind] = done.get(kind, 0) + 1
            elif kind in ("inquiry", "inquiry_evidence"):
                self._inquiry_desk().take(req)
                done[kind] = done.get(kind, 0) + 1
            elif kind in ("screen_skill", "screen_skill_use"):
                # What she learned on the phone by being shown, kept here.
                from aurora_internal.aurora_screen_apprenticeship import HomeScreenSkills
                HomeScreenSkills(self.state_dir).take(req)
                done[kind] = done.get(kind, 0) + 1
            elif kind in ("hub_move", "hub_message") and req.get("from") == "hub":
                # Sir at the desktop hub, on this machine (hub_route).  A phone
                # cannot file these: its uplink carries only HOME_REQUEST_KINDS.
                self._hub_request(kind, dict(req.get("payload") or {}))
                done[kind] = done.get(kind, 0) + 1
            else:
                done["not_runnable_here"] = done.get("not_runnable_here", 0) + 1
        if requests:
            offset_path.write_text(str(offset), encoding="utf-8")
        desk = self._inquiry_desk()
        if desk.questions:
            desk.tick()
        return {"requests": len(requests)}

    def _inquiry_desk(self):
        """Questions her surface raised, worked here in the order of home's
        own felt pressure (inquiry_tiers)."""
        if self.inquiry_desk is None:
            from aurora_internal.dual_strata.inquiry_tiers import HomeInquiryDesk
            self.inquiry_desk = HomeInquiryDesk(self.state_dir, self.systems)
        return self.inquiry_desk

    def _embodiment_move_requested(self, req):
        """Her own request to move (3c): home files it and carries it out in
        its safe order.  Only the device that holds her may ask."""
        payload = dict(req.get("payload") or {})
        if self.link is None:
            result = {"ok": False, "error": "strata server is unavailable"}
        else:
            result = self.link.request_move(str(payload.get("to") or ""), requested_by="her",
                                            from_surface=str(req.get("from") or ""))
        self.pending_moves.append({"request": dict(req), "result": result, "at": time.time()})
        del self.pending_moves[:-20]
        return result

    def _hub_request(self, kind, payload):
        if kind == "hub_move":
            result = self.request_move_from_hub(str(payload.get("to") or ""))
            self.pending_moves.append({"request": {"kind": kind, "payload": payload, "from": "hub"},
                                       "result": result, "at": time.time()})
            del self.pending_moves[:-20]
            return result
        from aurora_internal.dual_strata.hub_route import record_reply, send_to_holder
        if self.link is None:
            result = {"ok": False, "error": "strata server is unavailable", "status": "not_sent"}
            if payload.get("message_id"):
                record_reply(self.state_dir, str(payload["message_id"]), {"at": time.time(), **result})
            return result
        return send_to_holder(self.link, payload)

    def request_move_from_hub(self, to):
        """Sir's Move button: the same request, filed for the holder."""
        if self.link is None:
            return {"ok": False, "error": "strata server is unavailable"}
        return self.link.request_move(str(to or ""), requested_by="hub")

    def _move_tick(self, systems):
        """The desktop's own surface takes its part in a move locally."""
        if self.link is None:
            return None
        order = self.link.local_move_order(self.surface_id)
        if not order:
            return None
        key = (order.get("move_id"), order.get("action"))
        if key == self._move_job:
            return None
        self._move_job = key
        if order.get("action") == "checkpoint":
            return self.submit("handoff_prepare", {"move_id": order.get("move_id")})
        if order.get("action") == "claim" and order.get("token"):
            return self.submit("handoff_claim", {"token": order["token"], "move_id": order.get("move_id")})
        return None

    def _sensing_tick(self, systems):
        if self.link and not self.link.surface_ready(self.surface_id):
            return
        for device, enabled in self.services.sensors.items():
            if enabled:
                self.services.execute("host_probe", {"device": device})

    def _start_component(self, name, fn):
        try:
            fn()
        except Exception as exc:
            self.errors[name] = f"{type(exc).__name__}: {exc}"

    def _observe(self, event):
        self.demonstrations.observe(event)
        # Operation execution already runs on the field worker. Inventory also
        # arrives during boot before the gateway exists, so retain it for later.
        self.systems["_host_observation"] = event
        gateway = getattr(self.systems.get("aurora"), "gateway", None)
        stream, mode = self.systems.get("StreamType"), self.systems.get("ExistenceMode")
        if gateway is not None and stream is not None and mode is not None:
            import json
            gateway.receive(content=json.dumps(event, default=str), stream_type=stream.SENSOR_DATA,
                source="desktop_host", mode=mode.BOUNDED,
                metadata={"provenance": "desktop_observation", "epistemic_status": event["epistemic_status"],
                          "autobiographical_status": "observed_owner_demonstration" if self.demonstrations.active
                          else "observed_host_operation", "event": event})

    def _accept_kernel(self, status):
        with self._kernel_lock:
            if self._pending_kernel is not None:
                self._coalesced_kernel += 1
            self._pending_kernel = status
            self._kernel_time = time.monotonic()

    def _clock(self):
        if self.acm and self._kernel_time and time.monotonic() - self._kernel_time < 3:
            tick = self.acm.status().get("unwrapped_tick", 0) / 60.0
            if self._tick_origin is None:
                self._tick_origin = tick - (time.monotonic() - self._started)
            return tick - self._tick_origin
        self._tick_origin = None
        return time.monotonic() - self._started

    def _schedule_once(self):
        if not self.background or not self.live_idle():
            return
        if not self.field_lock.acquire(blocking=False):
            return
        try:
            now = self._clock()
            raw = read_json(self.state_dir / "strata_link" / "raw_input.json", {})
            if raw.get("expires_at", 0) >= time.time():
                self.systems["_anticipatory_input"] = raw
            else:
                self.systems.pop("_anticipatory_input", None)
            from aurora_acm_bridge import _read_axes_from_collective
            self._axes = _read_axes_from_collective(self.systems) or self._axes
            with self._kernel_lock:
                status, self._pending_kernel = self._pending_kernel, None
            if status:
                self.systems["_acm_status"] = status
                # Latest measured state is an observation, not another clock
                # which spawns independent dream/study/save threads.
                cpm = self.systems.get("cpm")
                if cpm:
                    cpm.advance()
            for name, (period, fn) in self._tasks.items():
                if now < self._due[name]:
                    continue
                decision = self.governor.evaluate_task(name, self.systems,
                    quiet=(self.state_dir / "quiet_mode").exists(),
                    state_write_lock=(self.state_dir / ".state_write_lock").exists())
                if not decision.get("allowed"):
                    self._due[name] = now + max(1, float(decision.get("retry_in", 30)))
                    continue
                self._due[name] = now + period
                try:
                    fn(self.systems)
                    self.governor.note_task_run(name)
                except Exception as exc:
                    self.errors[name] = f"{type(exc).__name__}: {exc}"
                break  # foreground jobs are reconsidered between every cycle
            if time.time() - self.services.last_refresh > 30:
                self.services.refresh()
                self.blueprints.import_real(self.systems, self.services)
            self._update_diagnostics()
        finally:
            self.field_lock.release()

    def _perform(self, kind, payload):
        if kind == "turn":
            def response_fields(response):
                if response is None:
                    return None
                fields = ("content", "src", "emotional_tone", "confidence", "response_id", "timestamp")
                if isinstance(response, dict):
                    return {key: response[key] for key in fields if key in response}
                return {key: getattr(response, key) for key in fields if hasattr(response, key)}
            def surface_ready(response):
                primary = response_fields(response) or {}
                with self._jobs_lock:
                    job = self.jobs[self.active_job]
                    job.update(surface_response=str(primary.get("content") or ""), surface_ready_at=time.time(),
                               result={"resp_A": primary, "response_text": str(primary.get("content") or ""),
                                       "subsurface_continuing": True})
                    self._persist_jobs()
            result = self._turn(self.systems, str(payload.get("text") or ""),
                                source_label="desktop_hub", session_id="desktop_owner", auto_search_enabled=True,
                                on_surface_ready=surface_ready)
            primary = response_fields(result.get("resp_A"))
            # Same public response as the phone/CLI. B is an optional afterthought,
            # never a replacement for her already-decided conscious expression.
            return {"resp_A": primary, "resp_B": response_fields(result.get("resp_B")),
                    "response_text": str((primary or {}).get("content") or ""),
                    **{k: result[k] for k in ("trace_id", "turn_tick", "src", "is_question", "elapsed_A") if k in result}}
        if kind == "operation":
            return self.services.execute(payload["operation"], payload.get("parameters", {}))
        if kind == "compose":
            return self.blueprints.compose(**payload)
        if kind == "demo_begin":
            return self.demonstrations.begin(**payload)
        if kind == "demo_finish":
            return self.demonstrations.finish()
        if kind == "demo_verify":
            return self.demonstrations.verify(payload["id"])
        if kind == "refresh":
            result = self.services.refresh()
            self.blueprints.import_real(self.systems, self.services)
            return result
        if kind == "sensor_control":
            return self.services.sensor_control(**payload)
        if kind == "clone_absorb":
            return self._start_clone_absorption()
        if kind in {"handoff_prepare", "handoff_claim", "handoff_cancel"}:
            if self.link is None:
                raise ValueError("strata server is unavailable")
            from aurora_internal.dual_strata.strata_link import StrataLinkClient, link_dir
            from aurora_internal.dual_strata.surface_working_state import capture, restore
            client = StrataLinkClient(self.state_dir, endpoint=f"http://127.0.0.1:{self.link.port}", secret=self.link.secret)
            client.sync_once()
            if kind == "handoff_prepare":
                capture(self.systems, self.state_dir)
                return client.push_state("handoff")
            if kind == "handoff_cancel":
                return client.cancel_handoff(payload["token"])
            result = client.pull_handoff(payload["token"], restore_callback=lambda: restore(self.systems, self.state_dir))
            if result.get("ok"):
                (link_dir(self.state_dir) / "surface_frozen").unlink(missing_ok=True)
            return result
        if kind == "save":
            from aurora import _full_save
            # A checkpoint persists what she has learned. Starting a new
            # whole-store weave here made shutdown wait for fresh learning;
            # her normal idle save retains the existing developmental pass.
            _full_save(self.systems, verbose=False, weave=False)
            return {"ok": True}
        raise ValueError("unknown resident operation")

    def _run(self):
        self._started = time.monotonic()
        try:
            with self.field_lock:
                self._boot_once()
        except Exception as exc:
            self.stage = "boot_failed"
            self.errors["boot"] = f"{type(exc).__name__}: {exc}"
            for job in self.jobs.values():
                if job.get("status") == "queued":
                    job.update(status="failed", error=self.errors["boot"])
            self._persist_jobs()
            return
        while not self._stop.is_set():
            try:
                _, _, jid, kind, payload, owner = self._queue.get(timeout=0.15)
            except queue.Empty:
                self._schedule_once()
                continue
            self.active_job = jid
            with self._jobs_lock:
                self.jobs[jid]["status"] = "running"
                self._persist_jobs()
            try:
                with self.field_lock:
                    if owner:
                        with owner_action():
                            result = self._perform(kind, payload)
                    else:
                        result = self._perform(kind, payload)
                # Response dataclasses are flattened for the hub; no re-generation.
                import dataclasses
                def plain(value):
                    if dataclasses.is_dataclass(value):
                        return dataclasses.asdict(value)
                    if isinstance(value, dict):
                        return {str(k): plain(v) for k, v in value.items()}
                    if isinstance(value, (list, tuple)):
                        return [plain(v) for v in value]
                    return value
                self.jobs[jid].update(status="completed", result=plain(result), finished_at=time.time())
            except Exception as exc:
                self.jobs[jid].update(status="failed", error=f"{type(exc).__name__}: {exc}")
            finally:
                self.active_job = None
                self._persist_jobs()
                self._queue.task_done()
                self._update_diagnostics()
        for obj in self._workers:
            self._start_component("shutdown:" + type(obj).__name__, obj.stop)
        if hasattr(self, "_scout_stop"):
            self._scout_stop.set()
            self._scout_thread.join(3)
        if getattr(self, "_clone_thread", None):
            self._clone_thread.join()  # admitted learning drains before the final save
        if self.acm:
            self.acm.stop()
        if self.link:
            self.link.stop()
        if self._owns_canonical_engine:
            self._start_component("final_save", lambda: self._perform("save", {}))
        if self.systems.get("aurora") is not None:
            from aurora import shutdown_aurora
            shutdown_aurora(self.systems)
        from aurora_desktop_agent import close_agent
        self._start_component("browser_shutdown", close_agent)
        self.services.active = False
        self.stage = "stopped"

    def _update_diagnostics(self):
        snapshot = {}
        for name in ("praxis_bridge", "praxis_messenger", "historical_experience",
                     "learning_probe", "cpm", "runtime_governor"):
            obj = self.systems.get(name)
            if obj is not None:
                try:
                    snapshot[name] = (obj.status() if hasattr(obj, "status")
                                      else obj.summary() if hasattr(obj, "summary")
                                      else obj.snapshot())
                except Exception as exc:
                    snapshot[name] = {"error": str(exc)}
        if self.systems.get("historical_experience") is None and not (
                self.state_dir / "experiential_baseline_v1.zip").exists():
            snapshot["historical_experience"] = {
                "status": "baseline_not_present",
                "archive": "experiential_baseline_v1.zip",
                "effect": "history replay not started; live cognition/Praxis unaffected",
            }
        self._diagnostics = snapshot

    def _first_pairing_status(self):
        """A phone's first pairing as home sees it: waiting for Sir's choices,
        ready to apply at the next start, or applied."""
        try:
            from aurora_internal.dual_strata.strata_migration import load_pending
            pending = load_pending(self.state_dir)
        except Exception as exc:
            return {"status": "unreadable", "error": str(exc)[:200]}
        if not pending:
            return {"status": "none"}
        report = pending.get("report") or {}
        return {"status": pending.get("status"), "migration_id": pending.get("migration_id"),
                "choices_needed": len(report.get("choices_needed") or []),
                "choices_made": len(pending.get("choices") or {}),
                "applied_this_start": self.first_pairing_applied, "error": pending.get("error")}

    def status(self):
        return {"stage": self.stage, "active_job": self.active_job, "queued": self._queue.qsize(),
                "errors": dict(self.errors), "organs": dict(self._diagnostics),
                "hardware": self.services.status(), "clone_harvest": self.systems.get("_clone_harvest_absorb"),
                "strata": self.link.status() if self.link else {"status": "not_started"},
                "first_pairing": self._first_pairing_status(),
                "home_requests": dict(self.home_requests_seen),
                "moving": self.link.move_status() if self.link else None,
                "shared_inquiry": self.inquiry_desk.status() if self.inquiry_desk is not None else None,
                "acm": {**self.acm.status(), "coalesced_observations": self._coalesced_kernel} if self.acm else {"status": "not_configured"},
                "surface": "local" if not self.link or self.link.surface_ready(self.surface_id) else "standby",
                "owner_console": "available", "at": time.time()}

    def stop(self, timeout=10):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)
        return not (self._thread and self._thread.is_alive())
