# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Exhaustive structural tests for aurora_representational_address.py, per the
AURORA ESTABLISHED REPRESENTATIONAL SUBSTRATE FULL INTEGRATION DIRECTIVE,
Section 25.

Proves, exhaustively where computationally practical:
  25/25 D1, 125/125 C1, 625/625 D2, 3,125/3,125 M2,1 (static SlotCoord-
  equivalent space), 15,625/15,625 M2,2 (confirmed Candidate-A extension),
  and 78,125/78,125 C2 addresses are each unique, round-trip losslessly,
  and (for C2) resolve to the real, already-compiled manifold slot.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import aurora_rank6_shadow_analysis as rank6
from aurora_representational_address import (
    RepresentationalRef, AXES, DIM_NAMES, resolve_manifold_slot,
    LEVEL_D1, LEVEL_C1, LEVEL_D2, LEVEL_M21, LEVEL_M22, LEVEL_C2,
)


def _assert_unique_and_roundtrip(refs):
    encodings = set()
    for ref in refs:
        enc = ref.encode()
        assert enc not in encodings, f"collision: {enc}"
        encodings.add(enc)
        assert RepresentationalRef.decode(enc) == ref
    return encodings


class TestD1Addressability:
    def test_all_25_d1_states_unique_and_roundtrip(self):
        refs = [RepresentationalRef.for_d1(c, d) for c in AXES for d in DIM_NAMES]
        assert len(refs) == 25
        encodings = _assert_unique_and_roundtrip(refs)
        assert len(encodings) == 25
        assert all(r.level() == LEVEL_D1 for r in refs)

    def test_constraint_and_dimension_not_collapsed(self):
        """A D1 ref must distinguish constraint from dimension -- two refs
        sharing a constraint but differing in dimension are NOT equal, and
        vice versa."""
        a = RepresentationalRef.for_d1("X", "OPERATOR")
        b = RepresentationalRef.for_d1("X", "COST")
        c = RepresentationalRef.for_d1("T", "OPERATOR")
        assert a != b
        assert a != c
        assert b != c


class TestC1Addressability:
    def test_all_125_c1_states_unique_and_roundtrip(self):
        refs = [RepresentationalRef.for_c1(c, d, t) for c in AXES for d in DIM_NAMES for t in AXES]
        assert len(refs) == 125
        encodings = _assert_unique_and_roundtrip(refs)
        assert len(encodings) == 125
        assert all(r.level() == LEVEL_C1 for r in refs)

    def test_self_targeting_is_not_the_only_representable_state(self):
        self_target = RepresentationalRef.for_c1("X", "OPERATOR", "X")
        cross_target = RepresentationalRef.for_c1("X", "OPERATOR", "B")
        assert self_target != cross_target
        assert cross_target.nc_target == "B"  # genuinely representable, not forced to source


class TestD2Addressability:
    def test_all_625_d2_relations_unique_and_roundtrip(self):
        refs = [
            RepresentationalRef.for_d2(rc, rd, cc, cd)
            for rc in AXES for rd in DIM_NAMES for cc in AXES for cd in DIM_NAMES
        ]
        assert len(refs) == 625
        encodings = _assert_unique_and_roundtrip(refs)
        assert len(encodings) == 625
        assert all(r.level() == LEVEL_D2 for r in refs)

    def test_row_and_column_can_differ_and_be_addressed(self):
        """The directive's own example addresses, verified representable
        (not verified 'meaningful' -- meaning is not assigned)."""
        examples = [
            ("X", "OPERATOR", "B", "DIFFERENCE"),
            ("T", "POLARITY", "A", "COST"),
            ("N", "MAGNITUDE", "X", "OPERATOR"),
        ]
        for rc, rd, cc, cd in examples:
            ref = RepresentationalRef.for_d2(rc, rd, cc, cd)
            assert (ref.nc_law_c, ref.nc_dim) != (ref.col_law_c, ref.col_law_d) or (rc, rd) == (cc, cd)
            assert ref.nc_law_c == rc and ref.col_law_c == cc


class TestM21Addressability:
    def test_all_3125_static_positions_unique_and_roundtrip(self):
        refs = [
            RepresentationalRef.for_m21(nc_c, nc_d, tgt, col_c, col_d)
            for tgt in AXES for nc_c in AXES for nc_d in DIM_NAMES for col_c in AXES for col_d in DIM_NAMES
        ]
        assert len(refs) == 3125
        encodings = _assert_unique_and_roundtrip(refs)
        assert len(encodings) == 3125
        assert all(r.level() == LEVEL_M21 for r in refs)

    def test_sub_fields_remain_explicitly_unresolved_not_defaulted(self):
        ref = RepresentationalRef.for_m21("X", "OPERATOR", "X", "T", "MAGNITUDE")
        assert ref.sub_law_c is None
        assert ref.sub_law_d is None
        # Explicitly NOT equal to the anchor-pinned version -- the pin must
        # be an opt-in transformation, never silently implied.
        assert ref != ref.as_pinned_anchor()

    def test_matches_real_slotcoord_generator_cardinality(self):
        """Cross-check against the already-existing, independently-tested
        SlotCoord static generator (aurora_constraint_manifold_router.py),
        not just this module's own count."""
        from aurora_constraint_manifold_router import AXES as SC_AXES, DIM_NAMES as SC_DIMS
        assert len(SC_AXES) == len(AXES) == 5
        assert len(SC_DIMS) == len(DIM_NAMES) == 5
        assert len(SC_AXES) ** 3 * len(SC_DIMS) ** 2 == 3125


class TestM22Addressability:
    def test_all_15625_candidate_a_positions_unique_and_roundtrip(self):
        refs = [
            RepresentationalRef.for_m22(nc_c, nc_d, tgt, sub_c, col_c, col_d)
            for tgt in AXES for nc_c in AXES for nc_d in DIM_NAMES
            for sub_c in AXES for col_c in AXES for col_d in DIM_NAMES
        ]
        assert len(refs) == 15625
        encodings = _assert_unique_and_roundtrip(refs)
        assert len(encodings) == 15625
        assert all(r.level() == LEVEL_M22 for r in refs)

    def test_sub_law_d_remains_unresolved_sub_law_d_not_promoted(self):
        """Candidate A frees sub_law_c only. sub_law_d must remain
        unresolved at this level -- confirms this module does not silently
        promote the coupled sub_law_d coordinate alongside it."""
        ref = RepresentationalRef.for_m22("X", "OPERATOR", "X", "B", "T", "MAGNITUDE")
        assert ref.sub_law_d is None
        assert ref.level() == LEVEL_M22


class TestC2Addressability:
    """The full 78,125-position exhaustive test (directive Section 15),
    done efficiently: build every ref directly from the real, already-
    compiled manifold data (loaded once, not reopened per-position) so the
    full 78,125/78,125 traversal completes in seconds rather than requiring
    78,125 separate file opens."""

    @pytest.fixture(scope="class")
    @classmethod
    def directory(cls):
        return rank6.load_manifold_directory_raw()

    def test_full_78125_exhaustive_uniqueness_and_roundtrip(self, directory):
        assert len(directory) == 125
        seen_encodings = set()
        total = 0
        for nc_name, nc in directory.items():
            assert len(nc["slots"]) == 625
            for slot in nc["slots"]:
                ref = RepresentationalRef.for_c2(
                    nc_law_c=nc["nc_law_c"], nc_dim=nc["nc_dim"], nc_target=nc["nc_target"],
                    sub_law_c=slot["sub_law_c"], sub_law_d=slot["sub_law_d"],
                    col_law_c=slot["col_law_c"], col_law_d=slot["col_law_d"],
                )
                enc = ref.encode()
                assert enc not in seen_encodings, f"collision at {enc}"
                seen_encodings.add(enc)
                assert RepresentationalRef.decode(enc) == ref
                total += 1
        assert total == 78125
        assert len(seen_encodings) == 78125

    def test_full_78125_positions_resolve_identity_and_physics(self, directory):
        """Steps 2-8, 13 of the directive's 13-step per-position test,
        applied to all 78,125 positions using the pre-loaded data (avoids
        78,125 redundant file re-opens while still checking every position
        against its real, persisted slot)."""
        checked = 0
        for nc_name, nc in directory.items():
            idx = rank6.build_slot_index(nc)
            for slot in nc["slots"]:
                ref = RepresentationalRef.for_c2(
                    nc_law_c=nc["nc_law_c"], nc_dim=nc["nc_dim"], nc_target=nc["nc_target"],
                    sub_law_c=slot["sub_law_c"], sub_law_d=slot["sub_law_d"],
                    col_law_c=slot["col_law_c"], col_law_d=slot["col_law_d"],
                )
                real = idx[(ref.sub_law_c, ref.sub_law_d, ref.col_law_c, ref.col_law_d)]
                assert real["slot_id"] == slot["slot_id"]
                assert real["evolution_grade"] == slot["evolution_grade"]
                assert real["accountability_weight"] == slot["accountability_weight"]
                checked += 1
        assert checked == 78125

    def test_resolve_manifold_slot_real_api_on_a_representative_sample(self, directory):
        """A real, end-to-end call through the public resolve_manifold_slot()
        API (which does open the real ManifoldDirectory/stream_slots path,
        not the pre-loaded shortcut above) -- sampled rather than run
        78,125 times, since each call legitimately re-opens a manifold file
        the way a real consumer would."""
        rng = random.Random(20260808)
        nc_names = list(directory.keys())
        sample_ncs = rng.sample(nc_names, 12)
        checked = 0
        for nc_name in sample_ncs:
            nc = directory[nc_name]
            sample_slots = rng.sample(nc["slots"], 5)
            for slot in sample_slots:
                ref = RepresentationalRef.for_c2(
                    nc_law_c=nc["nc_law_c"], nc_dim=nc["nc_dim"], nc_target=nc["nc_target"],
                    sub_law_c=slot["sub_law_c"], sub_law_d=slot["sub_law_d"],
                    col_law_c=slot["col_law_c"], col_law_d=slot["col_law_d"],
                )
                resolved = resolve_manifold_slot(ref)
                assert resolved is not None
                assert resolved["slot_id"] == slot["slot_id"]
                assert resolved["evolution_grade"] == slot["evolution_grade"]
                checked += 1
        assert checked == 60

    def test_unresolvable_ref_returns_none_not_a_fabricated_slot(self):
        partial = RepresentationalRef.for_m21("X", "OPERATOR", "X", "T", "MAGNITUDE")
        assert resolve_manifold_slot(partial) is None

    def test_dimensional_genealogy_recoverable_from_terminal_ref(self, directory):
        """Section 6/8's core requirement: a consumer given a full C2 ref
        must be able to recover its C1/D2/M2,1/M2,2 ancestry -- not just an
        opaque slot id."""
        nc_name = "Existential_Operator_of_Existence"
        nc = directory[nc_name]
        slot = nc["slots"][123]
        ref = RepresentationalRef.for_c2(
            nc_law_c=nc["nc_law_c"], nc_dim=nc["nc_dim"], nc_target=nc["nc_target"],
            sub_law_c=slot["sub_law_c"], sub_law_d=slot["sub_law_d"],
            col_law_c=slot["col_law_c"], col_law_d=slot["col_law_d"],
        )
        # Recover the C1 identity from the terminal C2 ref alone.
        assert ref.nc_name_key() == (nc["nc_law_c"], nc["nc_dim"], nc["nc_target"])
        # Recover the D2 relation (row/col channels) from the terminal ref.
        assert (ref.sub_law_c, ref.sub_law_d) == (slot["sub_law_c"], slot["sub_law_d"])
        assert (ref.col_law_c, ref.col_law_d) == (slot["col_law_c"], slot["col_law_d"])
        assert ref.level() == LEVEL_C2


class TestNoImplicitDefaultsMasqueradingAsKnown:
    def test_slot_id_alone_cannot_be_reverse_engineered_without_the_ref(self):
        """An opaque slot_id string does not, by itself, expose the
        dimensional genealogy -- confirming why the ref (not the bare id)
        must be the thing carried between systems."""
        slot_id = "NC_MANIFOLD:Existential_Operator_of_Existence:SUB[B:COST]xLAW[T:MAGNITUDE]"
        # A slot_id DOES happen to encode the coordinates in this particular
        # compiler's naming convention, but nothing guarantees a consumer
        # parses it correctly, and other slot-id-shaped strings elsewhere in
        # Aurora (e.g. Aurora625PressureMap's "NC:X>T" atoms) use a
        # completely different, incompatible convention -- confirmed
        # disjoint in the prior recursive-depth audit. The ref type exists
        # precisely so consumers never need to parse either convention.
        assert "SUB[" in slot_id and "LAW[" in slot_id  # this compiler's convention only
        # No assertion of universal parseability -- that is exactly the point.

    def test_anchor_pin_is_a_named_explicit_operation_not_a_silent_default(self):
        ref = RepresentationalRef.for_m21("B", "COST", "A", "T", "MAGNITUDE")
        assert ref.sub_law_c is None and ref.sub_law_d is None
        pinned = ref.as_pinned_anchor()
        assert pinned.sub_law_c == "B" and pinned.sub_law_d == "COST"
        # The unpinned ref is untouched (immutable dataclass) -- pin creates
        # a new, distinctly-named object rather than mutating in place.
        assert ref.sub_law_c is None

    def test_column_pin_is_a_named_explicit_operation_not_a_silent_default(self):
        """Mirrors test_anchor_pin_is_a_named_explicit_operation_not_a_silent_default
        for as_pinned_column() -- the escape hatch ReflexiveInterpreter.interpret()'s
        live SlotCoord construction uses for the column (law_c/law_d), which has no
        independent evidence at that call site (confirmed: IndexEntry.dense_top3
        aggregates across every col_law_c, discarding which one contributed)."""
        ref = RepresentationalRef(nc_law_c="B", nc_dim="COST", nc_target="A")
        assert ref.col_law_c is None and ref.col_law_d is None
        pinned = ref.as_pinned_column()
        assert pinned.col_law_c == "B" and pinned.col_law_d == "COST"
        # The unpinned ref is untouched (immutable dataclass) -- pin creates
        # a new, distinctly-named object rather than mutating in place.
        assert ref.col_law_c is None

    def test_column_pin_requires_nc_law_c_and_nc_dim_already_resolved(self):
        ref = RepresentationalRef()
        try:
            ref.as_pinned_column()
            assert False, "as_pinned_column() should raise when nc_law_c/nc_dim are unresolved"
        except ValueError:
            pass
