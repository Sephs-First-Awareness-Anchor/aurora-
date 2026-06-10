# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
sys.path.append('.')
from aurora_internal.aurora_utterance_parser import UtteranceParser
up = UtteranceParser()
p = up.parse('search youtube for lofi hip hop radio')
print(p.get('query_type'))
