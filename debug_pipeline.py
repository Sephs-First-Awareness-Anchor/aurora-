# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os
import json
sys.path.append('.')

# Mock systems for dual_question_pipeline
from enum import Enum
class StreamType(Enum):
    USER_INPUT = "USER_INPUT"

def mock_validate(*args, **kw):
    class V:
        def __init__(self):
            self.verdict = "ACCEPTED"
            self.filtered_content = None
    return V()

def mock_synthesize(*args, **kw):
    class S:
        def __init__(self):
            self.assembly = type('A', (), {'conscious_frame': {}, 'dominant_axis': 'X', 'paradoxes': [], 'thought_killed': False, 'quality': 1.0, 'entropy_state': {}})()
    return S()

systems = {
    'ExistenceMode': type('EM', (), {'BOUNDED': 'BOUNDED'})(),
    'StreamType': StreamType,
    'aurora': type('Aurora', (), {'gateway': type('Gateway', (), {
        'inbound_log': [], 'response_log': [], 'total_received': 0, 'total_rejected': 0, 'total_accepted': 0, 'total_filtered': 0, 'total_responses': 0,
        '_validate': mock_validate,
        '_synthesize': mock_synthesize,
        '_express': lambda *args, **kw: None,
        '_integrate': lambda *args, **kw: None,
        '_exploration_queue': [],
        'quarantine': {}
    })()})(),
    'perception': type('P', (), {'express': lambda *args, **kw: {}})(),
    'working_memory': None,
    'conversation_memory': None,
    'core_identity': None,
    'search_adapter': None,
    'dimensional': None
}

from aurora import dual_question_pipeline

user_text = "open youtube"
print(f"Testing input: {user_text}")
respA, respB, offered = dual_question_pipeline(systems, user_text, systems['ExistenceMode'].BOUNDED, use_search=False)

print(f"Winner SRC: {getattr(respA, 'src', 'unknown')}")
print(f"Winner Content: {respA.content}")
print(f"Winner Confidence: {respA.confidence}")

# Also check candidates
if "_last_surface_candidates" in systems:
    print("\nCandidates:")
    for c in systems["_last_surface_candidates"]:
        print(f"  - {c['src']}: {c['confidence']} (draft: {c['draft'][:50]}...)")
