#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Which words stand in for one another in what she has been told and has said, and which are the broadest.  READ-ONLY.

    python scripts/measure_crystal_substitutability.py --state-dir aurora_state [--top 15] [--word and --word but]

Feeds the conversation memory (what was said to her, and what she said) through `ContextProfiles`, sentence by sentence, then prints the broadest
words, the strongest classes and the substitutes of the words asked about.  Nothing is cut off; --top only limits what is printed.  Writes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.crystal_substitutability import ContextProfiles, exemplar_classes  # noqa: E402

WORD = re.compile(r"[a-z']+")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--word", action="append", default=["and", "or", "but", "that", "because"])
    a = ap.parse_args()
    mem = json.load(open(os.path.join(a.state_dir, "aurora_conversation_memory.json")))
    p, sentences = ContextProfiles(), 0
    for e in mem.get("entries") or []:
        for field in ("user_said", "aurora_said"):
            for sent in re.split(r"[.!?;\n]+", str(e.get(field) or "")):
                ws = WORD.findall(sent.lower())
                if ws:
                    sentences += bool(p.observe(ws))
    vocab = p.vocabulary()
    print(f"sentences: {sentences} | words: {len(vocab)} | seen at least 10 times: {sum(1 for w in vocab if p.count(w) >= 10)}")
    print("broadest and best seen:", [(w, round(p.function_likeness(w), 2)) for w in sorted(vocab, key=lambda w: -p.function_likeness(w))[:a.top]])
    for w in a.word:
        if p.count(w):
            print(f"  substitutes for {w!r} (seen {p.count(w)}):", [(x, round(s, 2)) for x, s in p.substitutes(w, top=6)])
        else:
            print(f"  {w!r}: never seen")
    well = [w for w in vocab if p.count(w) >= 5]
    print("strongest classes:")
    for h, d, m in exemplar_classes(p, well, top=6):
        print(f"  {h:<12} degree {d:.2f}  {[x for x, _ in sorted(m.items(), key=lambda kv: -kv[1])[:8]]}")


if __name__ == "__main__":
    main()
