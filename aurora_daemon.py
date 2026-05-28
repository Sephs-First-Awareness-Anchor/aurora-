#!/usr/bin/env python3
"""
AURORA  Daemon Proxy
====================
Everything every platform should run off one whole system.
This file now proxies all logic to 'aurora_core_ai/aurora_daemon.py'.
"""

import sys
import os
from pathlib import Path

# Add the core engine directory to the front of the path
_HERE = Path(__file__).resolve().parent
_CORE_AI = _HERE / "aurora_core_ai"

if str(_CORE_AI) not in sys.path:
    sys.path.insert(0, str(_CORE_AI))

# Proxy all symbols from the core engine daemon
from aurora_daemon import *

if __name__ == '__main__':
    # Execute the core main entry point
    # We use args from CLI if provided
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="full")
    args, unknown = parser.parse_known_args()
    main(runtime_profile=args.profile)
