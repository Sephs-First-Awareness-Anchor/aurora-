# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys, os
from pprint import pprint
sys.path.insert(0, os.getcwd())

import aurora_internal.aurora_lineage_runtime_activation as activation
orig_apply = activation.apply_selected_lineage_runtime_activation

def hooked_apply(systems, *args, **kwargs):
    gen = systems.get('genealogy')
    print(f"BEFORE: type={type(gen)}")
    if isinstance(gen, dict):
        print(f"  keys: {list(gen.keys())}")
    elif hasattr(gen, "abilities"):
        print(f"  abilities: {len(getattr(gen, 'abilities', {}))}")
        
    res = orig_apply(systems, *args, **kwargs)
    
    gen = systems.get('genealogy')
    print(f"AFTER: type={type(gen)}")
    if isinstance(gen, dict):
        print(f"  keys: {list(gen.keys())}")
    elif hasattr(gen, "abilities"):
        print(f"  abilities: {len(getattr(gen, 'abilities', {}))}")
        
    return res

activation.apply_selected_lineage_runtime_activation = hooked_apply

from aurora import boot_aurora
boot_aurora(state_dir='aurora_state', verbose=False)
