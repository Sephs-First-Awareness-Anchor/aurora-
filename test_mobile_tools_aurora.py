
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append("/storage/emulated/0/aurora_strata/aurora--main/aurora--main")

from aurora_internal.tool_registry import call

def test_mobile():
    print("Testing Mobile Battery Tool...")
    res = call("mobile_battery_status")
    print(f"Result: {res.success}")
    print(f"Data: {res.data}")
    
    print("\nTesting Mobile Notification Tool...")
    res = call("mobile_notification", title="Aurora Test", message="Mobile tools are functional.")
    print(f"Result: {res.success}")

if __name__ == "__main__":
    test_mobile()
