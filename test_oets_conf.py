import sys, os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
systems = boot_aurora(state_dir="aurora_state", verbose=False)
oets = systems.get('perception').oets
if oets:
    for w in ["understand", "hear", "agency"]:
        node = oets.web.nodes.get(w)
        if node:
            print(f"Node '{w}': conf={getattr(node, 'comprehension_confidence', 0.0)} roles={getattr(node, 'role', 'N/A')}")
