# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os
sys.path.append('.')
from aurora_internal.aurora_language_faculty import validate_candidate

meaning_packet = {
    'intent': 'general',
    'draft': 'engine=youtube | query=lofi hip hop radio | url=https://www.youtube.com/results?search_query=lofi+hip+hop+radio | title=',
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
print(validate_candidate('engine=youtube | query=lofi hip hop radio | url=https://www.youtube.com/results?search_query=lofi+hip+hop+radio | title=', meaning_packet, aurora_context))
