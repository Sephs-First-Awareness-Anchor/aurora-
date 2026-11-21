"""Desktop background experience belongs to the resident's one canonical organism.

Phone-only bridge tests are not evidence that the Windows resident starts
the same learning services. These checks execute the real desktop boot hook
with a substituted LearningProbe, without starting threads or a Praxis server.
"""
from types import SimpleNamespace
import sys

from aurora_internal.desktop.runtime import DesktopRuntime


def test_desktop_starts_one_weekly_learning_probe_against_shared_home(tmp_path, monkeypatch):
    created = []
    class Probe:
        def __init__(self, systems, *, state_dir, field_lock, live_idle):
            created.append(self)
            self.systems = systems
            self.state_dir = state_dir
            self.field_lock = field_lock
            self.live_idle = live_idle
            self.starts = 0
        def start(self):
            self.starts += 1
        def stop(self):
            return None
        def summary(self):
            return {"run_count": 0, "source": "desktop_test"}
    monkeypatch.setitem(sys.modules, "aurora_learning_probe", SimpleNamespace(LearningProbe=Probe))
    host = DesktopRuntime(tmp_path, boot=lambda **kw: {}, background=False)
    host.systems["organism"] = object()
    first = host._attach_learning_probe()
    second = host._attach_learning_probe()
    assert first is second
    assert first.systems is host.systems
    assert first.field_lock is host.field_lock
    assert first.live_idle.__self__ is host
    assert first.starts == 1
    assert host._workers.count(first) == 1
    host._update_diagnostics()
    assert host._diagnostics["learning_probe"]["source"] == "desktop_test"
    assert host._diagnostics["historical_experience"]["status"] == "baseline_not_present"


def test_missing_history_does_not_masquerade_as_missing_praxis(tmp_path):
    host = DesktopRuntime(tmp_path, boot=lambda **kw: {}, background=False)
    host.systems["praxis_bridge"] = SimpleNamespace(status=lambda: {"status": "unreachable",
                                            "online": False, "thread_alive": True})
    host.systems["praxis_messenger"] = SimpleNamespace(status=lambda: {"status": "idle"})
    host._update_diagnostics()
    assert host._diagnostics["praxis_bridge"]["thread_alive"] is True
    assert host._diagnostics["praxis_messenger"]["status"] == "idle"
    assert host._diagnostics["historical_experience"]["status"] == "baseline_not_present"
