#!/usr/bin/env python3
"""
run_corpus.py — Launch wrapper for aurora_core_ai/corpus_runner.py

Sets up sys.path so aurora_strata modules take priority over
aurora_core_ai copies (aurora_strata has the clean foundational_contract).

Usage:
  python3 run_corpus.py --corpus conversations.json --passes triple
  python3 run_corpus.py --corpus fast_corpus.json --passes observer
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
sys.path.append(os.path.join(_BASE, "aurora_core_ai"))

os.chdir(_BASE)

from aurora_core_ai.corpus_runner import main

if __name__ == "__main__":
    main()
