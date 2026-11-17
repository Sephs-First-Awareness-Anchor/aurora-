"""Offline checks for the desktop embodiment discovery contract."""
import json
from unittest.mock import patch
from aurora_internal.desktop_embodiment import discovery

def test_snapshot_has_explicit_uncertainty():
    with patch.object(discovery.platform, "system", return_value="Windows"), \
         patch.object(discovery, "_windows_devices", return_value=[
             {"kind": "processor", "name": "CPU", "status": "OK"}
         ]):
        result = discovery.discover()
    assert result["records"][0]["name"] == "CPU"
    assert result["semantics"]["operational_access"] == "not yet verified"
    assert result["semantics"]["authorization"] == "not inferred"

def test_non_windows_does_not_claim_inventory():
    with patch.object(discovery.platform, "system", return_value="Linux"):
        result = discovery.discover()
    assert result["discovery_status"] == "unsupported_host"
    assert result["records"] == []

def test_atomic_snapshot(tmp_path):
    target = tmp_path / "inventory.json"
    with patch.object(discovery, "discover", return_value={"records": []}):
        discovery.write_snapshot(target)
    assert json.loads(target.read_text()) == {"records": []}
