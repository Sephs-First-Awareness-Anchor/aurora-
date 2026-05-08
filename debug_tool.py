import sys
import os
sys.path.append('.')
from aurora import _select_tool, _classify_input_intent
from aurora_internal.tool_registry import call as _tool_call

user_text = 'search youtube for lofi hip hop radio'
intent = _classify_input_intent(user_text)
print(f"Intent: {intent}")
tname, tkwargs = _select_tool(user_text, intent, False, None, None)
print(f"Tool: {tname}")
if tname:
    res = _tool_call(tname, **tkwargs)
    print(f"Tool success: {res.success}")
    print(f"Tool data: {res.data}")
