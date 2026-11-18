"""Observed teaching episodes and independently proposed, verified re-execution.

This journal is environmental evidence. SkillMemory remains the procedure store;
no method here grants crystal maturity, changes thresholds or imports a clone.
"""
from __future__ import annotations

import copy
import time
import uuid
from pathlib import Path

from .common import digest, read_json, write_json


class Demonstrations:
    def __init__(self, state_dir, services, systems):
        self.path = Path(state_dir) / "desktop_demonstrations.json"
        self.services, self.systems = services, systems
        self.episodes = read_json(self.path, {})
        self.active = None

    def _save(self):
        write_json(self.path, self.episodes)

    def begin(self, intent, gap=""):
        if self.active:
            raise ValueError("finish the current demonstration first")
        if not str(intent).strip():
            raise ValueError("intent required")
        eid = uuid.uuid4().hex
        self.episodes[eid] = {"id": eid, "intent": str(intent), "gap": str(gap), "steps": [],
                              "created_at": time.time(), "status": "observing", "attempts": [],
                              "basis": "owner_demonstration", "dependency_version": self.services.inventory.get("version")}
        self.active = eid
        self._save()
        return self.episodes[eid]

    def observe(self, event):
        if self.active and event.get("kind") == "host_operation":
            episode = self.episodes[self.active]
            episode["steps"].append(copy.deepcopy(event))
            self._save()

    def finish(self):
        if not self.active:
            raise ValueError("no active demonstration")
        episode = self.episodes[self.active]
        episode["status"] = "awaiting_aurora_proposal"
        self.active = None
        self._save()
        return episode

    def propose(self, eid, steps, explanation):
        episode = self.episodes[eid]
        if episode["status"] == "observing" or not steps or len(steps) > 64:
            raise ValueError("finished demonstration and 1-64 proposed steps required")
        # Only the runtime's tool pathway supplies proposals. The owner route has
        # a separate verify operation; it cannot assert that Aurora understood.
        for step in steps:
            if step.get("operation") not in {"desktop_file_manager", "desktop_launch_app", "host_probe"}:
                raise ValueError("proposal operation has no bounded verification contract")
            if not isinstance(step.get("parameters"), dict):
                raise ValueError("parameters required")
        episode["proposal"] = {"steps": copy.deepcopy(steps), "explanation": str(explanation),
                               "basis": "aurora_proposed", "at": time.time()}
        episode["status"] = "awaiting_verification"
        self._save()
        return episode

    def verify(self, eid):
        episode = self.episodes[eid]
        proposal = episode.get("proposal")
        if not proposal:
            return {"ok": False, "error": "Aurora has not proposed an independent plan"}
        for step in episode["steps"]:
            if step.get("dependency_version") != self.services.dependency_version(step["operation"], step["parameters"]):
                return {"ok": False, "error": "operation_dependencies_changed; demonstrate or review again"}
        # A concrete held-out outcome is required. Replaying the original clicks
        # or a successful API return alone cannot verify understanding.
        expected = [s for s in episode["steps"] if "sha256" in s.get("after", {})]
        target_steps = [s for s in proposal["steps"] if s["operation"] == "desktop_file_manager"]
        if not expected or not target_steps:
            return {"ok": False, "error": "no_independent_observable_outcome_contract"}
        original_paths = {s["parameters"].get("path") for s in expected}
        if any(s["parameters"].get("path") in original_paths for s in target_steps):
            return {"ok": False, "error": "verification_requires_a_different_target"}
        outcomes = []
        for step in proposal["steps"]:
            result = self.services.execute(step["operation"], step["parameters"])
            outcomes.append(result)
            if not result.get("ok"):
                break
        actual = [r["observation"]["after"] for r in outcomes if "observation" in r
                  and "sha256" in r["observation"]["after"]]
        required = [{k: v for k, v in s["after"].items() if k in {"exists", "directory", "size", "sha256"}}
                    for s in expected]
        verified = (len(outcomes) == len(proposal["steps"]) and all(r.get("ok") for r in outcomes)
                    and bool(actual) and actual[-1] == required[-1] and bool(actual[-1].get("sha256")))
        attempt = {"at": time.time(), "verified": verified, "outcomes": outcomes,
                   "basis": "observed_independent_reexecution"}
        episode["attempts"].append(attempt)
        episode["status"] = "verified_procedure" if verified else "verification_failed"
        if verified:
            skill = self.systems.get("skill_memory")
            if skill is not None and any(s.get("sensory_context", {}).get("demonstration_id") == eid
                                         for s in getattr(skill, "_skills", [])):
                episode["skill_recorded"] = True
            if skill is not None and not episode.get("skill_recorded"):
                # A bounded procedural record, not a semantic promotion.
                procedure = "Execute the verified procedure: " + str(proposal["steps"])
                episode["skill_recorded"] = bool(skill.record_skill(
                    episode["intent"], procedure, source="desktop_verified_reexecution",
                    sensory_context={"demonstration_id": eid, "outcome_digest": digest(actual),
                                     "basis": "observed_independent_reexecution"}))
        self._save()
        return {"ok": verified, "episode": episode, "understanding_claim": "bounded_procedural_verification"}

    def view(self):
        return {"active": self.active, "episodes": list(self.episodes.values())[-100:]}
