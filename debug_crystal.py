# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
systems = boot_aurora(state_dir="aurora_state", verbose=False)
sc = systems.get("sensory_crystal")
print("SC TYPE:", type(sc))
print("GET_STATE TYPE:", type(sc.get_state))
cp = sc.constraint_profile()
print("CP TYPE:", type(cp))
