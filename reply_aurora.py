#!/usr/bin/env python3
"""Reply to a message Aurora left you (aurora_state/aurora_to_user.json). One
command from any terminal, no boot required -- Phase R2 of the Semantic
Plateau Remediation Directive (2026-07-15).

Usage: python3 reply_aurora.py <message_id> <reply text...>
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import time

from aurora_internal.aurora_correspondence_loop import _append_jsonl, _correspondence_dir

if len(sys.argv) < 3:
    print(__doc__)
    raise SystemExit(1)

message_id, text = sys.argv[1], " ".join(sys.argv[2:])
_append_jsonl(_correspondence_dir() / "from_sunni.jsonl", {
    "reply_to": message_id, "text": text, "time": time.time(),
})
print(f"Reply queued for {message_id!r}. Aurora will process it next time the correspondence loop runs.")
