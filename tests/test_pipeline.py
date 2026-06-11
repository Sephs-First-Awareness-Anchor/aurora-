# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import json
sys.path.append('.')
from aurora import _select_tool
from aurora_internal.tool_registry import call as _tool_call

tname, kwargs = _select_tool('search youtube for lofi hip hop radio', 'general', False, None, None)
print(f"Tool selected: {tname}, {kwargs}")
if tname:
    res = _tool_call(tname, **kwargs)
    print(f"Success: {res.success}")
    print(f"Data: {res.data}")
    print(f"Note: {res.note}")
