import sys, os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
systems = boot_aurora(state_dir="aurora_state", verbose=False)
oets = systems.get("oets")
if oets:
    print(f"OETS Nodes: {len(oets.nodes)}")
    for word in ["see", "hear", "understand", "agency"]:
        node = oets.nodes.get(word)
        if node:
            print(f"Node '{word}': conf={getattr(node, 'comprehension_confidence', 0.0)}")
        else:
            print(f"Node '{word}' NOT FOUND")
else:
    print("NO OETS FOUND")
