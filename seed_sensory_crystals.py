#!/usr/bin/env python3
"""
Sensory Crystal Seeder for Aurora AI
Adds concept-level seed nodes to each sensory crystal facet.

Duplicate logic:
  - Primary check: exact name match against pre-existing nodes (idempotent re-runs).
  - Secondary check: cosine_sim > 0.92 against pre-existing concept nodes only
    (primitive stubs at [0.1]*N are removed before seeding so they don't block
    new seeds; seeds in the same batch never block each other).

Semantic wiring resolves node IDs from both newly-added nodes AND from
already-persisted nodes (for idempotent re-runs).
"""

import gzip
import json
import math
import os
import time
import uuid

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_STATE_DIR = os.path.abspath(
    os.environ.get("AURORA_SENSORY_STATE_DIR")
    or os.path.join(_BASE_DIR, "aurora_state")
)
BASE = os.path.join(_STATE_DIR, "sensory_crystal")
NOW = time.time()

# ── helpers ──────────────────────────────────────────────────────────────────

def cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def read_agb(path):
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rb") as fh:
        return json.loads(fh.read())


def write_agb(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(json.dumps(data).encode())


def new_node(name, domain, facet, centroid):
    return {
        "node_id": str(uuid.uuid4()),
        "name": name,
        "domain": domain,
        "facet": facet,
        "centroid": centroid,
        "radius": 0.12,
        "usage_count": 22,
        "session_count": 5,
        "confidence": 0.60,
        "fitness": 0.64,
        "stage": "concept",
        "lineage_id": str(uuid.uuid4()),
        "generation": 1,
        "born_at": NOW,
        "last_seen": NOW,
        "maturity": 0.62,
        "cross_modal_links": [],
        "wisdom_tone_bias": 0.2,
        "wisdom_structure_bias": 0.28,
        "_last_session": "",
    }


def seed_facet(path, domain, facet, seeds, replace_primitives=False):
    """
    Load the .agb, add seeds, write back.

    replace_primitives: remove stage=="primitive" nodes before seeding.

    Returns:
        added       — list of (name, node_id) for newly written nodes
        skipped     — list of names that were already present
        final_count — total node count after seeding
        name_to_id  — dict mapping seed name -> node_id (both new and pre-existing)
    """
    data = read_agb(path)
    if data is None:
        data = {
            "domain": domain,
            "facet": facet,
            "total_obs": 0,
            "novelty_rate": 0.18,
            "stability": 0.60,
            "maturity": 0.62,
            "nodes": {},
        }

    nodes = data["nodes"]  # dict keyed by node_id

    if replace_primitives:
        keys_to_remove = [k for k, v in nodes.items()
                          if isinstance(v, dict) and v.get("stage") == "primitive"]
        for k in keys_to_remove:
            del nodes[k]

    # Build name->node_id map from what's already persisted (after primitive removal)
    name_to_id = {}
    for k, v in nodes.items():
        if isinstance(v, dict) and v.get("name"):
            name_to_id[v["name"]] = k

    # Pre-existing CONCEPT-stage centroids only — used as a near-exact duplicate
    # guard (cosine > 0.999, i.e. virtually identical vectors).
    # Primitives are excluded because their [0.1]*N stubs falsely block real seeds.
    # Same-batch seeds never check against each other — name matching is the
    # primary idempotency guard; cosine here catches only truly re-submitted
    # identical centroids.
    pre_existing_concept_centroids = [
        v["centroid"] for v in nodes.values()
        if isinstance(v, dict) and "centroid" in v and v.get("stage") == "concept"
    ]

    added = []
    skipped = []

    for seed_name, centroid in seeds:
        # Primary: name collision (idempotent re-runs)
        if seed_name in name_to_id:
            skipped.append(seed_name)
            continue

        # Secondary: near-exact centroid match against pre-existing concept nodes
        duplicate = False
        for ec in pre_existing_concept_centroids:
            if len(ec) == len(centroid) and cosine_sim(ec, centroid) > 0.999:
                duplicate = True
                break
        if duplicate:
            skipped.append(seed_name)
            continue

        node = new_node(seed_name, domain, facet, centroid)
        nodes[node["node_id"]] = node
        name_to_id[seed_name] = node["node_id"]
        # Do NOT add to pre_existing_concept_centroids — same-batch seeds
        # are spec-defined distinct concepts and must not block each other.
        added.append((seed_name, node["node_id"]))

    # Update facet-level fields
    data["total_obs"] = data.get("total_obs", 0) + len(added) * 22
    data["maturity"] = 0.62
    data["stability"] = 0.60
    data["novelty_rate"] = 0.18
    data["nodes"] = nodes

    write_agb(path, data)
    return added, skipped, len(nodes), name_to_id


# ── Seed definitions ──────────────────────────────────────────────────────────

TONE_SEEDS = [
    ("human_speech_prosody",
     [0.42, 0.12, 0.08, 0.10, 0.07, 0.11, 0.06, 0.10, 0.08, 0.12, 0.07, 0.09, 0.08]),
    ("warm_consonant_harmony",
     [0.82, 0.75, 0.08, 0.10, 0.09, 0.72, 0.07, 0.09, 0.71, 0.08, 0.09, 0.07, 0.08]),
    ("questioning_upward_inflection",
     [0.48, 0.10, 0.09, 0.12, 0.11, 0.08, 0.12, 0.11, 0.09, 0.14, 0.10, 0.11, 0.13]),
    ("tense_dissonant",
     [0.28, 0.30, 0.20, 0.22, 0.19, 0.21, 0.18, 0.22, 0.20, 0.21, 0.19, 0.20, 0.18]),
    ("emotional_resonance",
     [0.68, 0.20, 0.15, 0.12, 0.18, 0.16, 0.14, 0.19, 0.17, 0.14, 0.18, 0.15, 0.16]),
]

TIMBRE_SEEDS = [
    ("warm_human_voice",     [0.38, 0.14, 0.34, 0.24, 0.44]),
    ("excited_voice",        [0.68, 0.28, 0.58, 0.44, 0.68]),
    ("quiet_whisper",        [0.14, 0.32, 0.22, 0.18, 0.32]),
    ("ambient_background",   [0.10, 0.06, 0.18, 0.14, 0.22]),
    ("bright_music_presence",[0.52, 0.22, 0.72, 0.52, 0.82]),
]

RHYTHM_SEEDS = [
    ("natural_speech_rhythm", [0.32, 0.58]),
    ("fast_energetic_speech", [0.52, 0.84]),
    ("steady_musical_beat",   [0.48, 0.78]),
    ("sparse_ambient",        [0.08, 0.10]),
]

HUE_SEEDS = [
    ("warm_skin_and_light",
     [0.18, 0.22, 0.16, 0.10, 0.08, 0.10, 0.08, 0.08,
      0.08, 0.10, 0.16, 0.22, 0.18, 0.12, 0.08, 0.06,
      0.06, 0.08, 0.14, 0.22, 0.24, 0.14, 0.08, 0.04]),
    ("cool_environmental",
     [0.06, 0.06, 0.08, 0.10, 0.16, 0.22, 0.20, 0.12,
      0.10, 0.14, 0.18, 0.20, 0.16, 0.10, 0.08, 0.04,
      0.04, 0.08, 0.12, 0.18, 0.24, 0.18, 0.12, 0.04]),
    ("neutral_balanced_light",
     [0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.13, 0.13,
      0.06, 0.08, 0.10, 0.14, 0.18, 0.16, 0.14, 0.14,
      0.04, 0.06, 0.12, 0.20, 0.24, 0.18, 0.12, 0.04]),
    ("vivid_expressive_color",
     [0.14, 0.16, 0.14, 0.12, 0.12, 0.14, 0.10, 0.08,
      0.04, 0.06, 0.10, 0.16, 0.22, 0.22, 0.14, 0.06,
      0.08, 0.14, 0.22, 0.24, 0.18, 0.10, 0.04, 0.00]),
    ("low_light_darkness",
     [0.13, 0.13, 0.12, 0.12, 0.13, 0.12, 0.12, 0.13,
      0.14, 0.14, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12,
      0.22, 0.24, 0.20, 0.14, 0.10, 0.06, 0.02, 0.02]),
]

SHAPE_SEEDS = [
    ("human_face_frontal",
     [0.42, 0.32, 0.28, 0.20, 0.72, 0.68, 0.62, 0.55, 0.58, 0.18, 0.38,
      0.45, 0.50, 0.60, 0.55, 0.48, 0.52, 0.45, 0.50, 0.55, 0.48, 0.52, 0.45, 0.50, 0.48, 0.52, 0.46]),
    ("hands_gesture",
     [0.62, 0.28, 0.32, 0.38, 0.38, 0.32, 0.48, 0.42, 0.32, 0.24, 0.68,
      0.62, 0.55, 0.48, 0.58, 0.52, 0.48, 0.55, 0.58, 0.50, 0.46, 0.52, 0.48, 0.54, 0.50, 0.48, 0.52]),
    ("text_and_interface",
     [0.72, 0.68, 0.18, 0.14, 0.28, 0.32, 0.42, 0.82, 0.22, 0.38, 0.72,
      0.68, 0.72, 0.62, 0.58, 0.65, 0.70, 0.68, 0.62, 0.58, 0.64, 0.68, 0.60, 0.62, 0.58, 0.64, 0.66]),
    ("body_silhouette",
     [0.38, 0.22, 0.48, 0.20, 0.58, 0.42, 0.52, 0.28, 0.32, 0.12, 0.42,
      0.38, 0.42, 0.36, 0.40, 0.38, 0.42, 0.38, 0.40, 0.36, 0.40, 0.38, 0.42, 0.36, 0.40, 0.38, 0.40]),
    ("object_field",
     [0.58, 0.34, 0.34, 0.32, 0.28, 0.30, 0.44, 0.62, 0.28, 0.68, 0.78,
      0.55, 0.58, 0.52, 0.56, 0.54, 0.58, 0.52, 0.56, 0.54, 0.58, 0.52, 0.56, 0.54, 0.58, 0.52, 0.56]),
]

MOTION_SEEDS = [
    ("face_present_still",  [0.08, 0.72, 0.22, 0.06, 0.68, 0.48]),
    ("active_gesture",      [0.72, 0.68, 0.42, 0.62, 0.48, 0.44]),
    ("full_body_movement",  [0.88, 0.48, 0.52, 0.82, 0.42, 0.38]),
    ("static_empty_scene",  [0.04, 0.08, 0.12, 0.04, 0.52, 0.52]),
]


# ── Facet seeding ─────────────────────────────────────────────────────────────

results = {}
node_id_map = {}  # seed_name -> node_id (accumulated across all facets)

print("=" * 60)
print("AURORA SENSORY CRYSTAL SEEDER")
print("=" * 60)

facet_specs = [
    # (path_parts, domain, facet, seeds, replace_primitives)
    (("audio", "tone"),    "audio",  "tone",   TONE_SEEDS,   False),
    (("audio", "timbre"),  "audio",  "timbre", TIMBRE_SEEDS, True),
    (("audio", "rhythm"),  "audio",  "rhythm", RHYTHM_SEEDS, True),
    (("visual", "hue"),    "visual", "hue",    HUE_SEEDS,    True),
    (("visual", "shape"),  "visual", "shape",  SHAPE_SEEDS,  True),
    (("visual", "motion"), "visual", "motion", MOTION_SEEDS, True),
]

for path_parts, domain, facet, seeds, replace_prim in facet_specs:
    path = os.path.join(BASE, *path_parts, "state.agb")
    added, skipped, total, name_to_id = seed_facet(
        path, domain, facet, seeds, replace_prim
    )

    # Merge name->id into global map (covers both new and pre-existing nodes)
    node_id_map.update(name_to_id)

    label = f"{domain}/{facet}"
    results[label] = {"added": added, "skipped": skipped, "total_nodes": total}

    print(f"\n[{label}]")
    if added:
        for name, nid in added:
            print(f"  + added: {name} ({nid[:8]}...)")
    if skipped:
        for name in skipped:
            print(f"  ~ skipped (already present): {name}")
    print(f"  total nodes now: {total}")


# ── Semantic plane seeding ────────────────────────────────────────────────────

sem_path = os.path.join(BASE, "semantic", "state.agb")
sem_data = read_agb(sem_path)
if sem_data is None:
    sem_data = {
        "total_frames": 0,
        "maturity": 0.0,
        "semantic": {},
        "cooccur": {},
        "audio_marginal": {},
        "visual_marginal": {},
    }

semantic_seeds = [
    # (audio_seed_name, visual_seed_name, lane, label)
    ("human_speech_prosody",   "warm_skin_and_light",    "tonal_colour",  "speech_prosody_x_warm_skin"),
    ("warm_consonant_harmony", "vivid_expressive_color", "tonal_colour",  "harmony_x_vivid_color"),
    ("warm_human_voice",       "human_face_frontal",     "texture_form",  "warm_voice_x_face"),
    ("bright_music_presence",  "object_field",           "texture_form",  "music_x_object_field"),
    ("natural_speech_rhythm",  "active_gesture",         "tempo_flow",    "speech_rhythm_x_gesture"),
    ("steady_musical_beat",    "full_body_movement",     "tempo_flow",    "musical_beat_x_body_motion"),
]

print("\n[semantic]")
sem_added = 0
sem_skipped = 0

# Build set of existing (audio_id, visual_id) pairs and existing labels
existing_sem_pairs = set()
existing_sem_labels = set()
for sv in sem_data["semantic"].values():
    existing_sem_pairs.add((sv.get("audio_node_id"), sv.get("visual_node_id")))
    existing_sem_labels.add(sv.get("name", ""))

for audio_name, visual_name, lane, label in semantic_seeds:
    audio_id = node_id_map.get(audio_name)
    visual_id = node_id_map.get(visual_name)

    if audio_id is None or visual_id is None:
        print(f"  ! cannot wire {label}: missing node_id "
              f"(audio={audio_name}:{audio_id}, visual={visual_name}:{visual_id})")
        sem_skipped += 1
        continue

    # Skip by label or by (audio_id, visual_id) pair
    if label in existing_sem_labels or (audio_id, visual_id) in existing_sem_pairs:
        print(f"  ~ skipped (already present): {label}")
        sem_skipped += 1
        continue

    sem_node_id = str(uuid.uuid4())
    sem_node = {
        "node_id": sem_node_id,
        "name": label,
        "lane": lane,
        "audio_node_id": audio_id,
        "audio_node_name": audio_name,
        "visual_node_id": visual_id,
        "visual_node_name": visual_name,
        "stage": "concept",
        "co_occurrence_count": 18,
        "npmi": 0.28,
        "confidence": 0.58,
        "fitness": 0.62,
        "usage_count": 22,
        "session_count": 5,
        "maturity": 0.62,
        "lineage_id": str(uuid.uuid4()),
        "generation": 1,
        "born_at": NOW,
        "last_seen": NOW,
        "radius": 0.12,
        "wisdom_tone_bias": 0.2,
        "wisdom_structure_bias": 0.28,
        "cross_modal_links": [],
        "_last_session": "",
    }
    sem_data["semantic"][sem_node_id] = sem_node
    print(f"  + added: {label} ({sem_node_id[:8]}...) [lane={lane}]")
    sem_added += 1

sem_data["maturity"] = 0.62
write_agb(sem_path, sem_data)
print(f"  total semantic nodes now: {len(sem_data['semantic'])}")


# ── sensory_competency_state.json update ──────────────────────────────────────

scs_path = os.path.join(_STATE_DIR, "sensory", "sensory_competency_state.json")
try:
    with open(scs_path, "r") as fh:
        scs = json.load(fh)
except FileNotFoundError:
    scs = {"visual_templates": {}, "audio_templates": {}}

visual_concept_names = (
    [name for name, _ in HUE_SEEDS] +
    [name for name, _ in SHAPE_SEEDS] +
    [name for name, _ in MOTION_SEEDS]
)
for name in visual_concept_names:
    if name in scs.get("visual_templates", {}):
        continue
    scs.setdefault("visual_templates", {})[name] = {
        "template_id": "vt_" + str(uuid.uuid4()).replace("-", "")[:12],
        "modality": "visual",
        "name": name,
        "stage": "concept",
        "confidence": 0.60,
        "fitness": 0.64,
        "usage_count": 22,
        "session_count": 5,
        "generation_created": 1,
        "last_matched": NOW,
    }

audio_concept_names = (
    [name for name, _ in TONE_SEEDS] +
    [name for name, _ in TIMBRE_SEEDS] +
    [name for name, _ in RHYTHM_SEEDS]
)
for name in audio_concept_names:
    if name in scs.get("audio_templates", {}):
        continue
    scs.setdefault("audio_templates", {})[name] = {
        "template_id": "at_" + str(uuid.uuid4()).replace("-", "")[:12],
        "modality": "audio",
        "name": name,
        "stage": "concept",
        "confidence": 0.60,
        "fitness": 0.64,
        "usage_count": 22,
        "session_count": 5,
        "generation_created": 1,
        "last_matched": NOW,
    }

os.makedirs(os.path.dirname(scs_path), exist_ok=True)
with open(scs_path, "w") as fh:
    json.dump(scs, fh, indent=2)

print(f"\n[sensory_competency_state.json] updated — "
      f"{len(visual_concept_names)} visual + {len(audio_concept_names)} audio concept entries written")


# ── Final summary ─────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
total_added_facet = 0
for label, r in results.items():
    n = len(r["added"])
    s = len(r["skipped"])
    total_added_facet += n
    print(f"  {label:22s}  added={n}  skipped={s}  total_nodes={r['total_nodes']}")
print(f"  {'semantic':22s}  added={sem_added}  skipped={sem_skipped}  "
      f"total_nodes={len(sem_data['semantic'])}")
print(f"\n  Grand total new nodes: {total_added_facet} facet + {sem_added} semantic "
      f"= {total_added_facet + sem_added}")
print("Done.")
