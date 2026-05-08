import re

FILES = ['aurora.py', 'aurora_core_ai/aurora.py']

variables = [
    'recent_mentions',
    'semantic_frames',
    'recent_user_utterances',
    'recent_response_forms',
    'recent_claims',
    'claim_conflicts'
]

for filepath in FILES:
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        for var in variables:
            pattern = r'(\s+)self\.' + var + r'\.appendleft\('
            replacement = r'\1if not isinstance(self.' + var + r', deque):\n\1    self.' + var + r' = deque(list(self.' + var + r' or []), maxlen=40)\n\1self.' + var + r'.appendleft('
            content = re.sub(pattern, replacement, content)
            
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed {filepath}")
    except Exception as e:
        print(f"Error on {filepath}: {e}")
