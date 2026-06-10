# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys, os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
systems = boot_aurora(state_dir="aurora_state", verbose=False)
p = systems.get('perception')
oets = p.oets
if oets and hasattr(oets, 'web'):
    words = ["see", "hear", "understand", "agency"]
    for w in words:
        node = oets.web.nodes.get(w)
        if node:
            print(f"Node '{w}': roles={getattr(node, 'role', 'N/A')} depth={getattr(node, 'ontological_depth', 0)} axes={getattr(node, 'axis_polarities', 'N/A')}")
        else:
            print(f"Word '{w}' NOT IN OETS")
else:
    print("OETS OR WEB NOT FOUND")
