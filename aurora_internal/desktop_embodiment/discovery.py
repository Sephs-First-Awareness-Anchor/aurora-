"""Read-only desktop embodiment discovery for Aurora's host environment.

Produces observed capability records, not inferred permission or competence.
No background polling, networking, installs, or device mutations.
"""
from __future__ import annotations
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_WINDOWS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$classes = @(
  @{ kind='processor'; class='Win32_Processor' },
  @{ kind='memory'; class='Win32_PhysicalMemory' },
  @{ kind='storage'; class='Win32_DiskDrive' },
  @{ kind='graphics'; class='Win32_VideoController' },
  @{ kind='network'; class='Win32_NetworkAdapter' },
  @{ kind='audio'; class='Win32_SoundDevice' },
  @{ kind='usb'; class='Win32_USBController' },
  @{ kind='camera'; class='Win32_PnPEntity' }
)
$results = @()
foreach ($entry in $classes) {
  try {
    $items = @(Get-CimInstance -ClassName $entry.class -ErrorAction Stop)
    foreach ($item in $items) {
      if ($entry.kind -eq 'camera' -and $item.PNPClass -ne 'Camera' -and $item.PNPClass -ne 'Image') { continue }
      $results += [pscustomobject]@{
        kind=$entry.kind; name=[string]$item.Name
        device_id=[string]$item.DeviceID; status=[string]$item.Status
        pnp_class=[string]$item.PNPClass
      }
    }
  } catch {
    $results += [pscustomobject]@{ kind=$entry.kind; error=$_.Exception.Message }
  }
}
ConvertTo-Json -InputObject @($results) -Depth 4 -Compress
"""

def _windows_devices(timeout: int = 20) -> list[dict]:
    exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not exe:
        return [{"kind": "discovery", "error": "PowerShell unavailable"}]
    try:
        run = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", _WINDOWS_SCRIPT],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [{"kind": "discovery", "error": type(exc).__name__}]
    if run.returncode:
        return [{"kind": "discovery", "error": "PowerShell inventory failed",
                 "returncode": run.returncode}]
    try:
        parsed = json.loads(run.stdout)
        return parsed if isinstance(parsed, list) else [parsed]
    except (ValueError, TypeError):
        return [{"kind": "discovery", "error": "Invalid inventory response"}]

def discover() -> dict:
    """Capture observed host capabilities without claiming operability."""
    system = platform.system()
    records = _windows_devices() if system == "Windows" else []
    return {
        "schema": "aurora.desktop.embodiment.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "host": {"os": system, "release": platform.release(),
                 "machine": platform.machine()},
        "records": records,
        "discovery_status": "windows_cim" if system == "Windows" else "unsupported_host",
        "semantics": {
            "record": "observed hardware metadata only",
            "capability": "not yet verified",
            "authorization": "not inferred",
            "operational_access": "not yet verified",
        },
    }

def write_snapshot(path: str | Path) -> dict:
    """Write an atomic diagnostic snapshot; never change device configuration."""
    snapshot = discover()
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name + ".tmp")
    temp.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(dest)
    return snapshot

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Aurora desktop embodiment inventory")
    parser.add_argument("--output", default="aurora_state/desktop_embodiment.json")
    args = parser.parse_args()
    result = write_snapshot(args.output)
    print(json.dumps({"path": args.output, "records": len(result["records"]),
                      "status": result["discovery_status"]}))
