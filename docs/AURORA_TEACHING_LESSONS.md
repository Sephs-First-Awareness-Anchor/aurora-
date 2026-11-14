# Teaching her by saying it

Authors: Sunni (Sir) Morningstar & Cael Devo

**Rule (Sir, 2026-11-14):** if her knowledge is taught, it must be taught as if she
learned it: every relation and affect that learning touches, nothing recorded as
placed, nothing that could skew her development.

**How this holds.** A lesson is plain text, one utterance per line (`#` lines are the
teacher's notes and are never said). Replaying it is the same as typing it: each
line goes through the phone bridge's `handle_message`, unchanged, with real time
between lines. There is no seeding path, no marker, no special source. Everything a
live turn touches is touched, because a live turn happened.

**Run it on her real state, as the teacher.** Never on a copy you intend to commit.
- Laptop: `python scripts/teach_lesson.py lessons/feelings_names.txt --state-dir <her aurora_state>`
- Phone: bridge `teach_lesson(text, pace_seconds)` / `lesson_status()` (Hub wiring not built).
- Or simply type the lines to her.

**Measured (scratch copy, real `handle_message`):** two lines produced `aurora -feel-> curious`
and `aurora -feel-> calm`, spoken by sunni, as typed lines do. Her own code-lineage record
notes new source modules (as it does for every module added); no conversation, relation,
memory or genealogy record mentions a lesson. Not verified: a run on a device.
