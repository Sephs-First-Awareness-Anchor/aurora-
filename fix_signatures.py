import os
import re

patterns = [
    (r'(\w+)\["lineage_signature"\] = self\.constraint_profile\(\)\.weighted_signature\(\)', 
     r'cp = self.constraint_profile()\n\1["lineage_signature"] = cp.weighted_signature() if hasattr(cp, "weighted_signature") else "XTNBA"'),
    
    (r'"lineage_signature":\s+self\.constraint_profile\(\)\.weighted_signature\(\),',
     r'"lineage_signature": (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA"),'),
     
    (r'(\w+)\["lineage_signature"\] = self\.constraint_profile\(\)\.weighted_signature\(\)',
     r'cp = self.constraint_profile(); \1["lineage_signature"] = cp.weighted_signature() if hasattr(cp, "weighted_signature") else "XTNBA"')
]

FILES = [
    "aurora_governance_persistence_gateway.py",
    "aurora_core_ai/aurora_sedimemory.py",
    "aurora_core_ai/aurora_simulation_engine.py",
    "aurora_core_ai/aurora_expression_perception.py",
    "aurora_core_ai/aurora_internal/aurora_sensory_crystal.py",
    "aurora_core_ai/aurora_behavioral_identity.py",
    "aurora_core_ai/aurora_consciousness_engine.py",
    "aurora_core_ai/aurora_dimensional_systems.py",
    "aurora_sedimemory.py",
    "aurora_simulation_engine.py",
    "aurora_expression_perception.py",
    "aurora_live_vision.py"
]

def fix_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Simpler approach for the common case
    new_content = content.replace('self.constraint_profile().weighted_signature()', 
                                 '(self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA")')
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

for f in FILES:
    fix_file(f)
