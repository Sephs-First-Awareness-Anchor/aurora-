import sys
import re

with open('aurora.py', 'r') as f:
    content = f.read()

# 1. Force Tool Result to ALWAYS win if success
# 2. Add debug logging to a file we can track

debug_code = """
    # DEBUG LOG
    with open('aurora_debug.log', 'a') as f_log:
        f_log.write(f"\\n--- TURN: {user_text[:50]} ---\\n")
        f_log.write(f"Intent: {intent}\\n")
        f_log.write(f"Tool Result: {bool(_tool_result)}\\n")
        if _tool_result: f_log.write(f"Tool Success: {_tool_result.success}\\n")
"""

# Insert debug code after intent classification
content = content.replace(
    "intent = _classify_input_intent(user_text)",
    "intent = _classify_input_intent(user_text)" + debug_code
)

# Insert priority boost for tool results
content = content.replace(
    '        tool_cand = _MiniResp(_display_text, "informative", 0.92)',
    '        tool_cand = _MiniResp(_display_text, "informative", 0.99) # FORCED WINNER'
)

with open('aurora.py', 'w') as f:
    f.write(content)

print("Aurora.py updated with debug logging and forced tool priority.")
