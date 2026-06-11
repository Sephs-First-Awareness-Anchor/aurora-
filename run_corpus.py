#!/usr/bin/env python3
"""
run_corpus.py — Launch wrapper for corpus_runner.py

Sets up sys.path so aurora_strata modules take priority over
root-level copies (aurora_strata has the clean foundational_contract).

Usage:
  python3 run_corpus.py --corpus conversations.json --passes triple
  python3 run_corpus.py --corpus fast_corpus.json --passes observer
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)

os.chdir(_BASE)

from corpus_runner import main

if __name__ == "__main__":
    main()
