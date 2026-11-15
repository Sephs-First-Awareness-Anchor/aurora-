# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Build plan P3: how far a crystal has grown, as degrees.  Isolated: reads plain numbers, touches no crystal, imports nothing from Aurora.

The spec's seven points are filled from what actually occurred, each as a degree (polarity as a signed direction), and a crystal's standing at each
level is a continuous membership in [0, 1].  Nothing is compared with a bar: a count becomes a degree through x / (x + k), where k is the spec's
reference value (the count at which the degree is one half), so more occurrences always mean slightly more and nothing flips.

  * `degree(x, k)`                    a count as a degree in [0, 1).
  * `points_from_evidence(...)`       associative, abstract, temporal, cognitive, recursive, polarity (signed), emotional (None = not wired).
  * `memberships(points)`             {level: membership}, nested (each level can be no more than the one below), level 1 always 1.0.
  * `expected_level(points)`          1 + the sum of the memberships: a continuous position between 1 and 4.
  * `standing_next` / `ready_to_grow` how far it belongs to the next level, and the one place that standing is read as a class (more in than out).

A point that is None is unknown and leaves the blend; a point that is 0.0 was looked for and found nothing, and holds the level down.
"""
from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional

# Reference counts from the Crystal AI spec (the count at which the degree is one half).  Starting references, never cut-offs.
REF_ASSOCIATIVE = {2: 5.0, 3: 10.0, 4: 12.0}
REF_ABSTRACT = 5.0        # distinct contexts the crystal has appeared in
REF_TEMPORAL = 3.0        # distinct sessions it has recurred across
REF_EMOTIONAL = 5.0       # counted occasions that carried a feeling (a tone other than neutral)
NEUTRAL_TONES = frozenset({"neutral", "none"})

POINTS = ("emotional", "polarity", "associative", "abstract", "temporal", "cognitive", "recursive")


def degree(x: float, k: float) -> float:
    """A count as a degree: 0 at 0, one half at k, approaching 1, rising for every further occurrence."""
    x = max(0.0, float(x))
    k = max(1e-12, float(k))
    return x / (x + k)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def points_from_evidence(*, association_strengths: Iterable[float] = (), contexts: int = 0, sessions: int = 0,
                         consequences_shown: float = 0.0, consequences_total: float = 0.0,
                         members_promoted: float = 0.0, members_total: float = 0.0,
                         axis_displacement: Optional[Iterable[float]] = None, emotional: Optional[float] = None,
                         level: int = 4) -> Dict[str, Optional[float]]:
    """Fill the points from what occurred.  `association_strengths` are the counted associations (each in [0,1]); their sum is how much association
    the crystal carries, so many weak ties and a few strong ones both count in proportion.  Cognitive is the share of consequences that were shown
    outside the system's own simulation (0.0 when none have been looked for).  Recursive is the share of members that are themselves promoted.
    Polarity is the signed net direction of the axis displacement (its sign is kept)."""
    assoc_sum = sum(_clamp(s) for s in association_strengths)
    cog = 0.0 if consequences_total <= 0 else _clamp(consequences_shown / consequences_total)
    rec = 0.0 if members_total <= 0 else _clamp(members_promoted / members_total)
    pol = None
    if axis_displacement is not None:
        d = [float(v) for v in axis_displacement]
        pol = _clamp(sum(d) / len(d), -1.0, 1.0) if d else None
    return {
        "emotional": None if emotional is None else _clamp(emotional),
        "polarity": pol,
        "associative": assoc_sum,                       # kept as the raw amount; turned into a degree per level in `memberships`
        "abstract": degree(contexts, REF_ABSTRACT),
        "temporal": degree(sessions, REF_TEMPORAL),
        "cognitive": cog,
        "recursive": rec,
    }


def _blend(parts: Iterable[Optional[float]]) -> float:
    """How well the requirements are met together: held by the weakest of them (any part at 0 brings it to 0) and lifted, up to double, by how well
    the rest are met, so every pressure shows in the result.  min x (1 + mean) / 2 is continuous in every part and moves no faster than the part
    that moved.  A part that is unknown (None) is left out; with nothing required it is 1.0."""
    known = [p for p in parts if p is not None]
    if not known:
        return 1.0
    return min(known) * (1.0 + sum(known) / len(known)) / 2.0


def memberships(points: Mapping[str, Optional[float]]) -> Dict[int, float]:
    """Standing at each level, nested.  Level 2 needs association; level 3 also abstraction, recurrence over time and demonstrated consequence;
    level 4 also that its members are themselves promoted.  Higher levels ask for more association (spec reference 5, 10, 12)."""
    assoc = points.get("associative")
    a = {lv: (None if assoc is None else degree(assoc, REF_ASSOCIATIVE[lv])) for lv in (2, 3, 4)}
    m2 = _blend([a[2]])
    m3 = min(m2, _blend([a[3], points.get("abstract"), points.get("temporal"), points.get("cognitive")]))
    m4 = min(m3, _blend([a[4], points.get("abstract"), points.get("temporal"), points.get("cognitive"), points.get("recursive")]))
    return {1: 1.0, 2: m2, 3: m3, 4: m4}


def expected_level(points: Mapping[str, Optional[float]]) -> float:
    return sum(memberships(points).values())


def standing_next(points: Mapping[str, Optional[float]], level: int) -> float:
    """How far the crystal already belongs to the level above `level`, in [0, 1]; 0.0 from the top level."""
    return memberships(points).get(int(level) + 1, 0.0)


def ready_to_grow(points: Mapping[str, Optional[float]], level: int) -> bool:
    """A crystal's level is an integer, so the continuous standing has to be read once as a class: it moves up when it belongs more to the next level than
    it falls short of it (`s > 1 - s`, the fuzzy-set reading of membership).  The standing itself, which is what everything else uses, stays a degree."""
    s = standing_next(points, level)
    return s > 1.0 - s
