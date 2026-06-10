#!/usr/bin/env python3
"""Compatibility wrapper for the renamed noncomp manifold compiler."""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from aurora_constraint_manifold_compiler import *  # noqa: F401,F403


if __name__ == "__main__":
    from aurora_constraint_manifold_compiler import main

    main()
