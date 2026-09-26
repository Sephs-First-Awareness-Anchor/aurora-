"""Regression tests for fix/canonical-noncomp-dimension.

aurora_constraint_engine.py used to define its own, independent
NonCompDimension(enum.Enum) with string values ("polarity", "magnitude",
...) -- a duplicate identity of the canonical NonCompDimension(IntEnum) in
aurora_internal/aurora_noncomp_registry.py (POLARITY=0, MAGNITUDE=1, ...).
Same five members, same declaration order, but a different class, so
isinstance/is/registry-returned-member comparisons against this module's
members could silently fail even when the enum "looked" the same.

This suite pins two things going forward:
  1. aurora_constraint_engine.NonCompDimension IS the canonical class from
     aurora_internal.aurora_noncomp_registry -- not merely equal-looking.
  2. Every external serialization that depended on the old enum's string
     .value ("SED:{axis}>{dimension}" sediment-basin IDs, "NC_{AXIS}_{DIM}"
     channel names) is byte-identical to what it was before the collapse,
     now produced via dimension.name.lower() instead of dimension.value.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pytest

import aurora_constraint_engine as ace
from aurora_internal.aurora_noncomp_registry import NonCompDimension as CanonicalDim
from aurora_internal.aurora_constraint_manifold_patched import ManifoldViolation


# ---------------------------------------------------------------------------
# 1. Canonical enum identity
# ---------------------------------------------------------------------------

def test_engine_noncomp_dimension_is_canonical_class():
    """Not just equal-looking -- the literal same class object."""
    assert ace.NonCompDimension is CanonicalDim


@pytest.mark.parametrize("member_name", [
    "POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE",
])
def test_engine_members_are_canonical_members(member_name):
    engine_member = getattr(ace.NonCompDimension, member_name)
    canonical_member = getattr(CanonicalDim, member_name)
    assert engine_member is canonical_member
    assert isinstance(engine_member, CanonicalDim)


def test_engine_noncomp_dimension_is_intenum_with_ordinal_values():
    """The canonical enum is an IntEnum (POLARITY=0 .. DIFFERENCE=4), not
    the old enum.Enum with string values -- confirms the collapse actually
    happened rather than aliasing two independent classes."""
    assert [int(m) for m in ace.NonCompDimension] == [0, 1, 2, 3, 4]
    assert [m.name for m in ace.NonCompDimension] == [
        "POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE",
    ]


def test_sediment_basin_accepts_canonical_member_constructed_elsewhere():
    """A NonCompDimension member built via the canonical module works
    directly as a SedimentBasin.dimension -- proof there is only one
    identity in play, not two enums that happen to compare equal."""
    basin = ace.SedimentBasin(axis="A", dimension=CanonicalDim.OPERATOR)
    assert basin.dimension is CanonicalDim.OPERATOR


# ---------------------------------------------------------------------------
# 2. Preservation of existing external serialization
# ---------------------------------------------------------------------------

def test_nc_channels_values_are_unchanged_lowercase_strings():
    """NC_CHANNELS values previously came from dim.value (the old enum's
    lowercase string). The canonical enum's .value is an int (0-4), so
    this must now be built from dim.name.lower() -- verify every one of
    the 25 entries still serializes to the pre-existing lowercase form."""
    expected_dims = ["polarity", "magnitude", "operator", "cost", "difference"]
    for ax in ("X", "T", "N", "B", "A"):
        for dim_name, dim_str in zip(
            ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE"),
            expected_dims,
        ):
            key = f"NC_{ax}_{dim_name}"
            assert ace.NC_CHANNELS[key] == f"SED:{ax}>{dim_str}"


def test_nc_channels_exact_pinned_values():
    """Same exact assertions as the module's own self-test (INV-05), kept
    here as an independent, pytest-collected regression guard."""
    assert ace.NC_CHANNELS["NC_X_POLARITY"] == "SED:X>polarity"
    assert ace.NC_CHANNELS["NC_B_MAGNITUDE"] == "SED:B>magnitude"
    assert ace.NC_CHANNELS["NC_A_DIFFERENCE"] == "SED:A>difference"
    assert ace.NC_CHANNELS["NC_T_OPERATOR"] == "SED:T>operator"
    assert ace.NC_CHANNELS["NC_N_COST"] == "SED:N>cost"


def test_nc_channels_has_all_25_atomic_channels():
    assert len(ace.NC_CHANNELS) == 25


def test_sediment_basin_id_uses_lowercase_name_not_int_value():
    """basin_id previously read self.dimension.value (the old enum's
    lowercase string); the canonical enum's .value is an int, so a naive
    aliasing would have produced 'SED:B>3' instead of 'SED:B>cost'."""
    basin = ace.SedimentBasin(axis="B", dimension=ace.NonCompDimension.COST)
    assert basin.basin_id == "SED:B>cost"
    assert "3" not in basin.basin_id


def test_sediment_basins_module_dict_exact_pinned_ids():
    """Same exact assertions as the module's own self-test (INV-05,
    MemorySubstrate section), kept here as an independent regression
    guard against the sediment-basin ID surface."""
    assert len(ace.SEDIMENT_BASINS) == 10
    for basin_id, basin in ace.SEDIMENT_BASINS.items():
        assert basin.axis in ("B", "A")
    assert "SED:B>polarity" in ace.SEDIMENT_BASINS
    assert "SED:B>difference" in ace.SEDIMENT_BASINS
    assert "SED:A>polarity" in ace.SEDIMENT_BASINS
    assert "SED:A>difference" in ace.SEDIMENT_BASINS
    # X, T, N have no deep basins (INV-05) -- unaffected by this fix, kept
    # here to pin the full expected key set alongside the ones that are.
    assert "SED:X>polarity" not in ace.SEDIMENT_BASINS
    assert "SED:T>cost" not in ace.SEDIMENT_BASINS
    assert "SED:N>operator" not in ace.SEDIMENT_BASINS


def test_sediment_basin_rejects_non_deep_axis():
    """Unrelated to the enum collapse, but shares the same construction
    path -- confirms the fix didn't loosen the axis guard."""
    with pytest.raises(ManifoldViolation):
        ace.SedimentBasin(axis="X", dimension=ace.NonCompDimension.POLARITY)
