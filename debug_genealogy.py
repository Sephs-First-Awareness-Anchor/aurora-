import sys, os
from pprint import pprint
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
systems = boot_aurora(state_dir="aurora_state", verbose=False)
gen = systems.get("genealogy")
if gen:
    print("Type of gen:", type(gen))
    print("Has abilities:", hasattr(gen, "abilities"))
    if hasattr(gen, "abilities"):
        print("Type of abilities:", type(gen.abilities))
        if isinstance(gen.abilities, dict):
            print("Num abilities:", len(gen.abilities))
        else:
            print("abilities is not a dict")
    print("Has links:", hasattr(gen, "links"))
    if hasattr(gen, "links"):
        if isinstance(gen.links, dict):
            print("Num links:", len(gen.links))
else:
    print("No genealogy in systems")
