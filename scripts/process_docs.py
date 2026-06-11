# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import re

input_file = "AURORA_COMPREHENSIVE_DOCUMENTATION.md"
output_file = "AURORA_HUMAN_READABLE_DOCUMENTATION.md"

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)

output = []
output.append("# Aurora Human-Readable Documentation\n\n")
output.append("This document provides a human-readable, zero-assumption overview of the Aurora system, its directories, modules, and files. It has been synthesized to remove raw AST/code boilerplate while preserving the exact purpose and means of every file.\n\n")

state = "NORMAL"
in_code_block = False
code_block_delimiter = ""

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Check if we are entering or leaving a code block
    if stripped.startswith("```"):
        if not in_code_block:
            in_code_block = True
            code_block_delimiter = stripped
        elif stripped == "```" or stripped.startswith(code_block_delimiter):
            # This handles cases where closing block is just ``` or matches opening
            in_code_block = False

    # Skip old title
    if "Aurora Comprehensive Documentation" in line and i < 10:
        continue
    if "This document provides a highly organized" in line and i < 10:
        continue
        
    if not in_code_block and line.startswith("## "):
        output.append("\n" + line)
        state = "NORMAL"
        continue
        
    if not in_code_block and line.startswith("### File:"):
        state = "IN_FILE_HEADER"
        output.append("\n" + line)
        continue
        
    if state == "IN_FILE_HEADER":
        # Check for AST elements
        if not in_code_block and (line.startswith("#### Class:") or line.startswith("#### Function:") or line.startswith("#### Method:") or line.startswith("#### Field:") or line.startswith("#### Decorator:") or line.startswith("#### Dependency:")):
            state = "SKIP_AST"
            continue
        else:
            output.append(line)
            
    elif state == "SKIP_AST":
        # If we hit another directory or file header, the above `if` blocks will catch it
        # Wait, the `if line.startswith("## ")` blocks are BEFORE this `elif`, so they WILL execute and change state!
        pass
    else:
        output.append(line)

# Clean up multiple consecutive newlines
final_text = "".join(output)
final_text = re.sub(r'\n{3,}', '\n\n', final_text)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(final_text)

print(f"Processed file. Lines in: {len(lines)}. Bytes out: {len(final_text)}")
