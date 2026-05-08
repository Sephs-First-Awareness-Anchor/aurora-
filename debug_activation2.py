import sys, os
from pprint import pprint
sys.path.insert(0, os.getcwd())

import aurora_internal.aurora_lineage_runtime_activation as activation

def my_resolve_target(systems, target, working_memory=None):
    if target == "systems":
        # Let's wrap systems in a dict subclass to track sets
        class TrackDict(dict):
            def __setitem__(self, k, v):
                if k == "genealogy":
                    print(f"!!! OVERWRITING systems['genealogy'] with {type(v)} !!!")
                    import traceback
                    traceback.print_stack()
                super().__setitem__(k, v)
        ts = TrackDict(systems)
        return ts
    return activation.orig_resolve(systems, target, working_memory)

activation.orig_resolve = activation._resolve_target
activation._resolve_target = my_resolve_target

from aurora import boot_aurora
boot_aurora(state_dir='aurora_state', verbose=False)
