"""Phone Hub telemetry must not monopolize Aurora's shared Python bridge.

Flutter keeps Hub mounted under IndexedStack even when the user is chatting.
These source-level checks pin the visibility / in-flight guard because Dart
is only compiled in Android CI, not executed by Python unit tests.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HUB = ROOT / "flutter_app/lib/screens/hub_screen.dart"
SHELL = ROOT / "flutter_app/lib/main.dart"


def test_hidden_hub_stops_repeated_full_telemetry_read():
    hub = HUB.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    assert "HubScreen(active: _foreground && _tab == 3)" in shell
    assert "final bool active;" in hub
    assert "_timer?.cancel();\n    _gauntletTimer?.cancel();\n    if (!widget.active) return;" in hub
    assert "Duration(seconds: 10)" in hub
    assert "Duration(seconds: 4)" not in hub


def test_monitor_cannot_queue_overlapping_python_diagnostic_sweeps():
    hub = HUB.read_text(encoding="utf-8")
    assert "if (_refreshInFlight || !mounted || !widget.active) return;" in hub
    assert "_refreshInFlight = true;" in hub
    assert "finally {\n      _refreshInFlight = false;\n    }" in hub


def test_monitor_refreshes_on_return_without_unmounting_cognition():
    hub = HUB.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    assert "if (oldWidget.active != widget.active) _syncPolling();" in hub
    assert "IndexedStack(index: _tab" in shell
    assert "const HomeScreen()" in shell
