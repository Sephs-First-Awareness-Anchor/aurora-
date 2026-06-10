# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os
sys.path.append('.')
from aurora_internal.aurora_language_faculty import score_feedback_bias
print(f"Bias for tool: {score_feedback_bias('general', 'tool')}")
print(f"Bias for comprehension: {score_feedback_bias('general', 'comprehension')}")
