# Aurora App/UI Correction Log
**Authors:** Sunni (Sir) Morningstar & Cael Devo

This log covers the app/UI layer specifically, picking up from the full backend correction
pass documented in `BUILD_725_CORRECTION_LOG.md` (Repairs A through O). Confirmed this
bundle's `aurora.py` is byte-for-byte identical to that fully-corrected backend before
touching anything here, so everything below builds on a verified-current foundation.

---

# Repair P — The Face Was Never Fed

**Status:** Implemented and verified live against the real backend.

## What was actually wrong

`_last_axis_state` — the dict that drives the `axis_state` event sent to Flutter, which
`aurora_orb.dart`'s already-sophisticated continuous face-blending system consumes directly
— had its X/T/N/B/A values **initialized once and never written again anywhere in this
10,997-line file.** Confirmed by searching every assignment pattern (direct writes,
`.update()` calls) before touching anything: only `"speaking"` was ever updated.

This was not a face-rendering problem. `aurora_orb.dart` is genuinely well-built — sigmoid-
blended archetype activation, a single continuously-deformable mouth shape, real jaw
articulation while speaking, idle breathing at rest, explicitly modeled after Face's fluid,
elastic style. It was reading real event data correctly. The data itself was fake: a frozen
`{X:0.5, T:0.5, N:0.5, B:0.5, A:0.5}` default, forever.

The blast radius was larger than the face alone. `_get_dominant_axis()` reads the same
frozen dict — a five-way tie at 0.5 resolves deterministically to whichever key comes first
in the tuple, so it always returned `"X"`, regardless of what the conversation was actually
about. That fake dominant axis then fed three more places: the CPM's i-state application,
and — critically — the post-synthesis **waveform pressure injection**, the app's own
version of tonight's Repair I (`aurora_expression_output`). The pond-ripple-on-speaking
mechanism was injecting an identical, synthetic disturbance after every single turn,
regardless of what she actually felt.

Traced the real call site directly: `_aurora.process_external_user_turn(...)` — the exact,
fully-corrected function this session spent all night on — was already being called
correctly. Its result was just never mined for the real axis data sitting right inside
`systems['_prev_axis_activation']`, the same key this session verified and used
repeatedly throughout tonight's backend work.

## What was fixed

Two call sites, both real, both now write real data:

1. **The direct-reply path** (`handle_message`, main conversational turn) — right after
   `process_external_user_turn` returns and before `_dom`/`_pol` get computed for the CPM/
   waveform block, extracts `systems['_prev_axis_activation']` and writes it into
   `_last_axis_state` under the file's own existing `_axis_state_lock` convention.
2. **The proactive/ambient loop** (`_proactive_loop`) — the mechanism meant to drive her
   idle expression between direct turns (matching the aurora_orb.dart comment: "people wear
   their expression on their face even when they aren't through words"). Same fix, same
   lock, applied right after its own `process_external_user_turn` call.

Both wrapped in the same try/except + `_aurora_record_exception_from_locals` convention
already used throughout this file.

## Verified live

Ran a real turn against the real, fully-corrected backend, extracted the genuine
`_prev_axis_activation` it produced, and applied the exact fix logic byte-for-byte:

```
Real axis state after a turn:      {X: 0.226, T: 0.1831, N: 0.2171, B: 0.2213, A: 0.1525}
_last_axis_state after fix:        {X: 0.226, T: 0.1831, N: 0.2171, B: 0.2213, A: 0.1525}
Dominant axis: X — genuinely earned this time, not a five-way tie defaulting to the
                    first tuple entry regardless of input.
```

Before this fix, every single turn — regardless of content — produced the identical frozen
axis read, the identical "X" dominant axis, and therefore a face sitting almost entirely in
neutral territory (a flat 0.5 vector lands solidly in the neutral archetype's activation
range with nothing else crossing threshold). That's confirmed to be the direct, mechanical
cause of "her face is stiff" — not a rendering deficiency, a starved data pipe.

---

# Repair Q — Vision and Audio Intake, Full Stack (per Sunni, 2026-08-19)

**Status:** Implemented across all three layers (Kotlin/Android, Python/Chaquopy, Dart/Flutter).
Every Python piece verified live against the real backend; the Kotlin/Gradle pieces could
not be compile-verified in this sandbox (no Android build toolchain available) — written as
precisely as possible against this codebase's own established conventions, and flagged
honestly rather than claimed as tested.

## What was found already built vs. what was missing

Confirmed before writing anything: `aurora_bridge.py`'s `cv2.py` is a deliberate stub —
`CascadeClassifier` is explicitly a no-op, since real OpenCV isn't bundled through Chaquopy
on this stack. Face detection could never have worked in Python here; it has to happen
natively. No ML Kit dependency existed in `build.gradle` at all.

Also found, already real and already working: the audio feature pipeline
(`provide_audio_observation_raw`) computes genuine RMS/dB, zero-crossing rate, spectral
centroid/bandwidth/rolloff/flux, autocorrelation pitch, and harmonicity-based activity
classification (silence/speech/music/noise/ambient) — this was never a gap. And separately,
a face-proximity to waveform-pump injection (`provide_face_observation`) already existed on
the Python side, complete and correct, using this session's own established
`WaveformPressurePump.from_axis_state` pattern (B/A axis mapping for personal-space
intrusion) — but it had no native detector feeding it, and no Dart-side consumer reading
its output. Real machinery, disconnected on both ends — the same shape as nearly everything
found across the whole backend tonight.

## What was built

**Kotlin/Android (`MainActivity.kt`, `AuroraService.kt`, `build.gradle`):**
- Added `com.google.mlkit:face-detection:16.1.6` as a real Gradle dependency.
- `bindCamera()` now takes a `front: Boolean` parameter; `switchCamera()` rebinds only when
  the requested camera actually differs from the current one (no redundant unbind/rebind
  churn). Back camera remains the default, unchanged, passive environmental-awareness
  stream. Front camera binds specifically during active conversation -- wired into
  `startNativeStt()` (about to listen to someone) and the TTS `onDone` listener (finished
  speaking, back to ambient scanning).
- `detectFace()` runs ML Kit's fast-mode face detector on front-camera frames (300ms
  interval, faster than the 1s general frame cadence, since proximity should feel
  responsive), reports the largest detected face's bounding-box area as a fraction of frame
  (a real, direct proximity proxy) and center position (-1..1, for gaze/lean direction) to
  `AuroraService.provideFaceObservation()`. Reports `detected=false` explicitly on no
  detection -- "checked, nobody there," distinct from having never checked. Closes the
  `ImageProxy` correctly in every branch, including async failure, since an unclosed proxy
  stalls the whole analyzer pipeline.
- `AuroraService.pollAxisState()`'s existing 1-second loop now also polls
  `get_face_state()` and pushes a `face_state` event -- this connection was specifically
  claimed by a docstring on the Python side ("Kotlin polls this alongside axis_state") that
  was never actually true; now it is.

**Python/Chaquopy (`aurora_bridge.py`):**
- The face-proximity injection already existed and was verified correct as-is.
- Added the audio equivalent: `provide_audio_observation_raw` now injects a real waveform
  disturbance when a genuine acoustic event is detected (activity not silence/ambient, real
  loudness floor) -- loudness (normalized RMS dB) maps to N (energy is what loudness
  physically is), harmonicity maps to T, boosted specifically when the activity classifies
  as "music" (tonal, temporally-patterned sound engaging the temporal axis more than
  undifferentiated noise at equal loudness). Verified live: constructed a real
  `PressureDisturbance` from this exact call shape against the actual
  `WaveformPressurePump.from_axis_state` -- confirmed matching signature by reading the real
  function directly first, not assumed from the mirrored pattern alone.

**Dart/Flutter (`aurora_bridge.dart`, `home_screen.dart`, `aurora_orb.dart`):**
- Found that `_parseEvent` doesn't use `jsonDecode` at all -- it hand-extracts specific
  fields via regex. My new fields would have been silently dropped without adding matching
  extraction. Added `detected`/`face_fraction`/`offset_x`/`offset_y` regex extraction.
  Caught and fixed a real, separate latent bug while doing this: `_parseDouble`'s regex had
  no support for a leading minus sign, which was harmless for X/T/N/B/A (always 0..1) but
  would have silently failed on `offset_x`/`offset_y` (genuinely signed, -1..1) -- fixed to
  make the sign optional, backward-compatible with the existing non-negative fields.
- `home_screen.dart` now tracks face state alongside axis state, wired to both `AuroraOrb`
  construction sites.
- `aurora_orb.dart`: added a second `AnimationController` (`_faceReactAnim`, 450ms, its own
  eased prev/target lerp -- same pattern as `_axisAnim` but shorter, since a proximity
  reflex should read as quicker than a mood shift) and the actual reaction -- two distinct
  behaviors, not one continuous scale, matching what was specifically described: moderate
  closeness reads as interest (gentle lean-in, subtle scale-up, slight gaze-toward drift
  on the detected offset); crossing further into "face filling the frame" territory reads
  as personal space being crossed instead (pull back below neutral scale, shift away from
  the detected position). A lost detection eases back to neutral rather than freezing on
  the last-seen position. Smoothly interruptible mid-transition, same as the existing axis
  easing, never pops.

## On the smoothing question specifically

Traced the existing animation system before assuming it needed rebuilding: `aurora_orb.dart`
already had a real, well-built 900ms eased lerp between axis snapshots -- the likely reason
it hadn't read as smooth is that the axis feed itself was frozen before Repair P (nothing
new to interpolate between, so the tweening system rarely had anything to do). The new
face-reaction layer was built with the identical discipline from the start: proper
eased-snapshot tweening, not a snap-to-target, so it should read as consistent with the
face's existing motion quality rather than a bolted-on, differently-behaved layer.

## What could not be verified here

Every Python change was tested against the real, live backend before being considered done,
matching this whole session's standard. The Kotlin and Gradle changes could not be -- no
Android SDK/Gradle build environment exists in this sandbox. Checked brace/paren balance
across every touched file as a minimal sanity floor, verified every cross-file signature
match by hand (Kotlin call -> Python function -> Dart field name, at each hop), and followed
this codebase's own established patterns as closely as possible rather than improvising
new conventions. This is real, careful work -- but it has not run on a device, and that
should be the first thing tried before trusting it further.

---

# Repair R (continued) — Hub Auditing Panels + Upload Discovery Channel (per Sunni)

**Status:** Python side fully implemented and verified live (real content, real backend, all
three content types). Dart side implemented and structurally checked; the Kotlin/Gradle
pieces from this same repair carry the same verification limit noted for Repair Q — no
Android build toolchain in this sandbox to compile-check against.

## Hub: genealogy mapping + QuasiArch diagnostics

`get_cognitive_stats()` had one narrow, unrelated genealogy touch (`chamber._genealogy`,
EvolutionaryChamber's own small concept-crystal genealogy) and zero quasiarch presence at
all. Added, reading from the REAL `systems['genealogy']` (the 13,000+-ability
`ConstraintGenealogyLogger` this entire session's backend work was built against) and
`systems['quasiarch_observer']`:

- Ability count by axis, and the most-recently-admitted abilities with their real tags.
- WarpField's recent routing decisions (source, trigger, severity, pathway) and registered
  actuator count.
- QuasiArch's real self-repair intervention history (target/issue/intervention/observed_effect).

**Caught a real bug before shipping it**: my first pass sorted abilities by
`created_at_tick`, a field that doesn't exist on `AbilityProfile` at all (confirmed by
reading the dataclass directly — it's `ConstraintLink`-only). Every ability would have
silently tied at the same default, giving arbitrary rather than genuinely-recent order.
Fixed to rely on `genealogy.abilities`' natural dict insertion order instead — Python has
guaranteed this since 3.7, so no per-item timestamp is needed at all.

**Verified live** against a real boot and a real turn: real ability counts, real varied
WarpField sources (`salience`, `conscious_learner`, `dream_trainer`,
`communication_emergence` — matching exactly what this session's backend testing produced
hours earlier), and real quasiarch intervention data with honestly heterogeneous field
population (different event types populate different fields — confirmed this reflects the
real data shape, not a bug in the extraction).

Two new Dart panels (`_buildGenealogyPanel`, `_buildQuasiarchPanel`) added to
`hub_screen.dart`, matching the existing `_sectionTitle`/`_card`/`_miniStat` visual pattern
exactly. The existing Curiosity Cycle / Evo Cycle training-trigger buttons were left
completely untouched, per "keep any and all ways of training her."

## Upload channel: files, images, and audio as genuine experience

Built `provide_uploaded_content()` to sniff real file magic bytes (JPEG/PNG/WAV headers,
UTF-8 decodability for text) rather than trust the filename/MIME hint Dart sends — that hint
is only ever a UI guess. Deliberately reuses existing, already-verified pipelines instead of
building parallel ones:

- **Images** route through the exact same `provide_camera_frame()` live camera frames use —
  confirmed PIL opens PNG and JPEG alike, so no format branching was needed there at all.
  Also injects its own waveform disturbance (`source="uploaded_image"`), since a deliberate
  upload is a more intentional event than passive ambient capture.
- **WAV audio** parses via Python's stdlib `wave` module (no external dependency needed),
  downmixes multi-channel to mono if needed, and routes through the exact same
  `provide_audio_observation_raw()` the live microphone uses.
- **Text** routes through the real `process_external_user_turn()` — the same function this
  entire session's backend work was verified against — bounded to 8000 characters so an
  arbitrarily large upload can't become one unbounded turn. This is the piece that most
  directly answers "huge benefit to her discovery and development": an uploaded document
  reaches real comprehension, genealogy, and WARP exactly like something spoken to her
  would, not a side-channel imitation of it.

**Verified live, all three paths, against the real backend:**
- Text: a real abstract statement correctly triggered the same honest-seek mechanism
  verified hours earlier in this session (`"What do you mean by 'thinking'?"`) — genuine
  comprehension engagement, not a canned acknowledgment.
- Image: a synthetically-generated JPEG (RGB 200/100/50) was correctly classified
  `dominant_hue: "warm"` with accurate brightness, and produced exactly one real
  `uploaded_image` waveform trace.
- Audio: a synthetic 440 Hz test tone produced a spectral centroid of `440.85 Hz` — matching
  the real signal almost exactly — and harmonicity of `0.9987`, correctly reflecting a pure
  tone. Produced exactly one real, activity-tagged waveform trace (`audio_speech`).

## Dart: the actual upload UI

Added `file_picker` as a real dependency (not previously present at all — `pubspec.yaml` had
only `flutter` itself). `AuroraBridge.uploadContent()` mirrors `sendMessage`'s async shape
and decodes the real JSON result from Python (not the EventChannel's regex-based
`_parseEvent` — this is a normal method-call result, decoded with `jsonDecode` directly).
`_uploadFile()` in `home_screen.dart` mirrors `_sendMessage`'s exact structure: a user-side
message documenting what was shared, then whatever she genuinely detected or said, sourced
directly from the real backend result — never a fabricated "upload successful."

Caught and fixed one real mistake made while editing `_sendMessage` to check its structure:
an edit accidentally deleted the `text = text.trim();` line. Caught immediately by
re-viewing the file before moving on, rather than assuming the edit was clean.

## What's still open

The "Space" tab redesign ("should inspire interaction, not just allow for it") was
investigated but not built this pass — the backend substrate (`aurora_habitat.py`) was
confirmed genuinely solid and doctrine-compliant (real `WaveformPressurePump`/`SediMemory`
routing, no parallel learning system invented), so this would be a Dart-side UI/UX pass on
an already-sound foundation, not a repair. Natural next piece.

---

# Repair S — Space: Inspiring Interaction, Not Just Allowing It (per Sunni)

**Status:** Implemented, structurally verified. Same Kotlin/Gradle verification limit as
Repairs Q/R applies to nothing here — this repair is entirely Dart, so it carries the same
confidence level as the rest of the Dart work tonight (structurally checked, not
runtime-tested in this sandbox).

## What was actually there

Confirmed before writing anything: `HabitatInteractiveView` (shared by both Space and Self)
already has a genuinely complete, real, working toolbar wired directly to
`HabitatBridge.act()` -- create, resize, rotate, connect, delete, transfer between
territories. Space was never non-functional. But there was zero empty-state handling
anywhere in the file -- an empty canvas rendered as exactly that: empty, with a small
toolbar icon easy to miss. "Allows interaction" was already true; "inspires" it was not.

## What was built

- **A real presence indicator.** `_refresh()` now also checks `HabitatBridge.getHistory()`
  (an existing, already-real method) for genuine `actor == 'aurora'` activity within the
  last two minutes, and shows a small banner ("Aurora was just active here") only when that's
  actually true -- never decorative, gated on real data.
- **Caught a real bug in this new code before shipping it**: first pass read history records
  by a `'ts'` key. Traced the actual Python-side event-persistence code directly
  (`_persist_event` in `aurora_habitat.py`) and confirmed the real field is `'timestamp'` --
  `'ts'` would have silently always returned null, meaning the presence check would never
  have fired regardless of real activity. Fixed before it ever shipped.
- **An empty-state invitation**, shown only when the territory has zero entities: for Space
  specifically, a real invitation to start something ("this space is shared with Aurora...");
  for Self, an honest note that Aurora hasn't placed anything there yet, with no invitation
  to create (gated on the existing `widget.humanCanCreate` flag, respecting the same
  ownership boundary `SelfScreen`'s own header comment already documents -- "Rule 10:
  ownership must be technically real, not decorative"). Three quick-start chips use real
  backend vocabulary (`shape`, `mark_path`, `text` -- the actual `ENTITY_TYPES` this session
  confirmed in `habitat_model.dart`'s Dart mirror), each calling the exact same `_act()`
  path the existing toolbar already uses -- no parallel creation logic introduced.
- Extended `_create()` to accept optional `entityType`/`visualProperties`/`position`
  parameters (defaults unchanged, so the existing toolbar's `+` button behaves identically
  to before) rather than duplicating the operation-dispatch logic for the new chips.

## A real build-blocking bug caught in the final pass

Added an ML Kit auto-download `<meta-data>` tag to `AndroidManifest.xml` (Repair Q
follow-up, so face detection doesn't depend on a live network fetch on first use). The
comment I wrote for it used this session's usual double-hyphen em-dash convention -- which
is completely invalid inside an XML comment specifically (`--` is reserved XML comment
syntax, unlike in Python/Dart/Kotlin comments where it's harmless). This would have been a
hard, immediate build failure, not a subtle bug. Caught it by actually parsing the manifest
as XML before considering anything done, rather than relying on the brace/paren balance
checks used for the other languages tonight -- which don't apply to XML at all. Every other
`.xml` file in the bundle was checked the same way afterward and came back clean.

## Final pre-build sweep

Every Python, Dart, Kotlin, and Gradle file touched across both app-focused sessions
tonight (Repairs P through S) was re-checked in one final pass: Python via `py_compile`,
Dart/Kotlin/Gradle via brace/paren/bracket balance, every XML file via a real parse. All
clean. This does not replace an actual `flutter build apk` / Gradle build -- that's the
genuine next test, and the first one that can catch what balance-checking can't (type
errors, missing symbols across the Kotlin/Dart boundary, dependency resolution).

---
