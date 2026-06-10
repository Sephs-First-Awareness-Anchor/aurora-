# Authors: Sunni (Sir) Morningstar & Cael Devo
import re

with open('corpus_runner.py', 'r') as f:
    content = f.read()

# Remove Consolidation ritual
content = re.sub(
    r'# Consolidation ritual.*?try:\n\s*if False:\n\s*pass\n\s*_msg = generate_message\(systems\).*?except Exception as _e:\n\s*if verbose:\n\s*print\(f"  \[RITUAL\] Unavailable: \{_e\}"\)',
    '# Consolidation ritual removed.',
    content,
    flags=re.DOTALL
)

# Remove Post-session outreach
content = re.sub(
    r'# ── Post-session outreach: reward or punishment ───────────────────────────.*?try:\n\s*if False:\n\s*pass\n\s*# Compute session net improvement.*?except Exception as _e:\n\s*if verbose:\n\s*print\(f"  \[SESSION_OUTREACH\] Unavailable: \{_e\}"\)',
    '# ── Post-session outreach removed.',
    content,
    flags=re.DOTALL
)

with open('corpus_runner.py', 'w') as f:
    f.write(content)
