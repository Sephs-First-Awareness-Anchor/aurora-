# Authors: Sunni (Sir) Morningstar & Cael Devo
import json

axes = ["X", "T", "N", "B", "A"]
roles = {"P": "presence", "G": "formation", "N": "energy", "F": "frame", "O": "operation"}
axis_names = {"X": "existence", "T": "time", "N": "energy", "B": "boundary", "A": "agency"}
# Effect laws
# A generic logic for off-diagonal cells
cells = {}

for c in axes:
    for r_k, r_v in roles.items():
        for l in axes:
            if c == l:
                continue # Phase A handles this
            
            key = f"{c}.{r_k}[{l}]"
            desc = f"{axis_names[c].capitalize()} as {r_v} through {axis_names[l]} — the {axis_names[l]} aspect of {axis_names[c]}'s {r_v}."
            indicators = [f"{l}_polarity modulating {c}_weight", f"{c} and {l} interact"]
            effect = f"HIGH: {axis_names[c]} {r_v} is amplified by {axis_names[l]}; LOW: {axis_names[c]} {r_v} lacks {axis_names[l]} grounding; STRAINED: conflict between {axis_names[c]} and {axis_names[l]}"
            
            cells[key] = {
                "slot_description": desc,
                "runtime_indicators": indicators,
                "effect_law": effect
            }

code = "MANIFOLD_FIRST_LAYER_PHASE_B: dict = {\n"
for k, v in cells.items():
    code += f'    "{k}": {{\n'
    code += f'        "slot_description": "{v["slot_description"]}",\n'
    code += f'        "runtime_indicators": {json.dumps(v["runtime_indicators"])},\n'
    code += f'        "effect_law": "{v["effect_law"]}",\n'
    code += f'    }},\n'
code += "}\n"

with open("phase_b_cells.txt", "w") as f:
    f.write(code)
