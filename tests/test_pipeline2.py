# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import json
sys.path.append('.')
from aurora import dual_question_pipeline

class MockSystems:
    def __init__(self):
        self.systems = {}
        self.systems['ExistenceMode'] = type('ExistenceMode', (), {'BOUNDED': 'BOUNDED'})()
        self.systems['aurora'] = type('MockAurora', (), {'gateway': type('MockGateway', (), {
            'inbound_log': [], 'response_log': [], 'total_received': 0, 'total_rejected': 0, 'total_accepted': 0, 'total_filtered': 0, 'total_responses': 0,
            '_validate': lambda *args, **kw: type('V', (), {'verdict': 'ACCEPTED', 'filtered_content': None})(),
            '_synthesize': lambda *args, **kw: type('S', (), {'assembly': type('A', (), {'conscious_frame': {}})()})(),
            '_express': lambda *args, **kw: None,
            '_integrate': lambda *args, **kw: None,
            '_exploration_queue': [],
            'quarantine': {}
        })()})()
        
        # Need Enum
        from enum import Enum
        class StreamType(Enum):
            USER_INPUT = "USER_INPUT"
        self.systems['StreamType'] = StreamType
        self.systems['perception'] = type('P', (), {'express': lambda *args, **kw: {}})()
        self.systems['working_memory'] = None
        self.systems['conversation_memory'] = None
        self.systems['core_identity'] = None
        self.systems['search_adapter'] = None

sys_mock = MockSystems()

try:
    respA, respB, offered = dual_question_pipeline(sys_mock.systems, "search youtube for lofi hip hop radio", sys_mock.systems['ExistenceMode'].BOUNDED, use_search=False)
    print("WINNER:", getattr(respA, 'src', None), getattr(respA, 'content', None))
except Exception as e:
    import traceback
    traceback.print_exc()

