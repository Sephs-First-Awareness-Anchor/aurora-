#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
import json
import subprocess
import time
import os

def get_stats():
    try:
        with open('aurora_state/lexicon.json', 'r') as f:
            lex = json.load(f)
        with open('aurora_state/aurora_oets_web.json', 'r') as f:
            oets = json.load(f)
        with open('aurora_state/aurora_state.json', 'r') as f:
            state = json.load(f)
        traits = state.get('traits', {})
        return {
            "vocab": len(lex.get("entries", {})),
            "nodes": len(oets.get("nodes", {})),
            "introspection": traits.get("introspection", 0),
            "curiosity": traits.get("curiosity", 0),
            "generation": state.get("generation", 0)
        }
    except Exception as e:
        return {"error": str(e)}

def run_interval(index, start_offset, size=5000):
    print(f"\n{'='*60}")
    print(f" STARTING TRAINING INTERVAL {index+1} (Messages {start_offset} to {start_offset+size})")
    print(f"{'='*60}")
    
    # 1. Extract Slice
    print(f"  [1/3] Extracting {size} messages...")
    extract_cmd = f"""python3 -c '
import json
with open("conversations.json", "r", encoding="utf-8") as f:
    data = json.load(f)
flat_data = []
keys = list(data.keys())[{start_offset}:{start_offset + size}]
for k in keys:
    content = data[k].get("content", [])
    for i in range(0, len(content) - 1, 2):
        u = content[i].get("message", "")
        a = content[i+1].get("message", "")
        if u and a:
            flat_data.append({{"user": u, "assistant": a}})
with open("interval_corpus.json", "w", encoding="utf-8") as f:
    json.dump(flat_data, f, indent=2)
'"""
    subprocess.run(extract_cmd, shell=True)

    # 2. Run Training
    print(f"  [2/3] Executing intensive training...")
    train_cmd = "python3 corpus_runner.py --corpus interval_corpus.json --passes observer --warmup 0 --quiet"
    subprocess.run(train_cmd, shell=True)

    # 3. Test & Stats
    print(f"  [3/3] Analyzing improvement...")
    stats = get_stats()
    print(f"\n  [INTERVAL {index+1} COMPLETE]")
    print(f"  > Vocab Size: {stats.get('vocab')}")
    print(f"  > OETS Nodes: {stats.get('nodes')}")
    print(f"  > Introspection: {stats.get('introspection'):.4f}")
    print(f"  > Curiosity: {stats.get('curiosity'):.4f}")
    print(f"  > System Generation: {stats.get('generation')}")
    
    print("\n  [LIVE TEST INTERACTION]")
    test_cmd = "python3 test_conversation_desktop.py"
    subprocess.run(test_cmd, shell=True)

if __name__ == "__main__":
    for i in range(3):
        run_interval(i, start_offset=i*5000)
    print("\n[ALL INTERVALS COMPLETE]")
