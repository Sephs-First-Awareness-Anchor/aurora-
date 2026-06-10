# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os
sys.path.append('.')
from aurora_internal.aurora_language_faculty import realize_output
from aurora_internal.tool_registry import call as _tool_call

res = _tool_call('desktop_search', query='lofi hip hop radio', engine='youtube')
print(f"Tool Success: {res.success}")
print(f"Tool Data: {res.data}")

meaning_packet = {
    'intent': 'general',
    'draft': res.data,
    'tone': 'informative',
    'src': 'tool'
}
aurora_context = {
    'mode': 'BOUNDED',
    'tone': 'informative',
    'is_self_question': False,
    'routing_classification': None,
    'recent_memory_excerpts': []
}
print(realize_output(meaning_packet, aurora_context))
