import re

files = [
    "aurora_core_ai/aurora_internal/dual_strata/dce_bridge.py",
    "aurora_core_ai/aurora_surface_daemon.py",
    "aurora_surface_daemon.py"
]

for path in files:
    try:
        with open(path, "r") as f:
            content = f.read()
        
        if "dce_bridge.py" in path:
            # We want to replace the root_thought dictionary construction
            content = re.sub(
                r'root_thought = \{\n\s*"summary": root_summary,\n\s*"seed": root_seed,',
                'root_thought = {\n            "law_bindings": getattr(assembly_result, "law_bindings", []),\n            "diagonal_anchor": getattr(assembly_result, "diagonal_anchor", ""),',
                content
            )
            # Remove the huge block of string building if possible, but it's safer just to change the dict assignment 
            # and let the strings be garbage collected, to avoid breaking syntax.
            pass
            
        if "aurora_surface_daemon.py" in path:
            content = re.sub(
                r'root_thought = \{\n\s*"summary": guidance or interpretation or "Surface is holding the present converged frame.",\n\s*"seed": guidance or interpretation or "",',
                'root_thought = {\n            "law_bindings": dict(projection.get("law_bindings") or {}) or [],\n            "diagonal_anchor": str(projection.get("diagonal_anchor") or ""),',
                content
            )
            content = re.sub(
                r'root_thought\["summary"\] = str\(root_thought\.get\("summary", ""\) or guidance or interpretation or ""\)',
                '# English summary assignment removed.',
                content
            )
            
        with open(path, "w") as f:
            f.write(content)
        print(f"Refactored {path}")
    except FileNotFoundError:
        print(f"File not found: {path}")

