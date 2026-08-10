# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Restart/save/load conservation tests, per the AURORA ESTABLISHED
REPRESENTATIONAL SUBSTRATE FULL INTEGRATION DIRECTIVE, Sections 17 and 25:

    store(ref) -> restart -> retrieve(ref) -> same representation.

Covers both the raw address module (encode/decode across a process
boundary simulation) and the one real, narrowly-extended memory surface
(UnderstandingSedimentOverlay's now-optional representational_ref field).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_representational_address import RepresentationalRef, AXES, DIM_NAMES


class TestRawEncodeDecodeAcrossProcessBoundary:
    def test_encoded_ref_written_to_disk_and_reread_is_identical(self, tmp_path):
        """Simulates a process restart: write the encoded ref to a plain
        file, then read it back in a way that shares no in-memory state
        with the writer."""
        ref = RepresentationalRef.for_c2("X", "OPERATOR", "B", "T", "COST", "N", "MAGNITUDE")
        path = tmp_path / "ref.txt"
        path.write_text(ref.encode(), encoding="utf-8")

        reread_text = path.read_text(encoding="utf-8")
        recovered = RepresentationalRef.decode(reread_text)
        assert recovered == ref
        assert recovered.level() == ref.level()

    def test_dict_form_round_trips_through_json_like_a_real_state_file(self, tmp_path):
        ref = RepresentationalRef.for_m22("A", "DIFFERENCE", "N", "X", "T", "POLARITY")
        path = tmp_path / "ref.json"
        path.write_text(json.dumps(ref.to_dict()), encoding="utf-8")

        loaded = json.loads(path.read_text(encoding="utf-8"))
        recovered = RepresentationalRef.from_dict(loaded)
        assert recovered == ref

    def test_partial_ref_persists_its_unresolved_fields_as_unresolved(self, tmp_path):
        """A restart must not accidentally 'fill in' an unresolved field --
        confirms unresolved stays unresolved across the encode/decode
        boundary, not just in memory."""
        ref = RepresentationalRef.for_d1("B", "COST")
        encoded = ref.encode()
        recovered = RepresentationalRef.decode(encoded)
        assert recovered.nc_target is None
        assert recovered.sub_law_c is None
        assert recovered.unresolved_fields() == ref.unresolved_fields()


class TestUnderstandingSedimentOverlayPersistence:
    """The one real memory surface this pass extended. Simulates a real
    process restart: instance 1 deposits and is discarded; a brand new
    instance 2, constructed fresh with no shared Python state, must recover
    the exact same reference from disk."""

    def test_ref_survives_a_simulated_restart(self, tmp_path):
        from aurora_understanding_sediment import UnderstandingSedimentOverlay

        ref = RepresentationalRef.for_c1("X", "OPERATOR", "B")
        overlay1 = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
        overlay1.deposit("SomeNonComp", "X:OPERATOR|X:OPERATOR", 0.80, ref=ref.encode())
        overlay1.save()
        del overlay1  # simulate process exit -- no shared state survives

        overlay2 = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
        recovered_encoded = overlay2.ref_for("SomeNonComp", "X:OPERATOR|X:OPERATOR")
        assert recovered_encoded == ref.encode()
        assert RepresentationalRef.decode(recovered_encoded) == ref

    def test_deposit_without_a_ref_leaves_no_fabricated_ref_on_restart(self, tmp_path):
        """Backward-compatibility / no-silent-default guard: a deposit made
        without a ref (the pre-existing behavior, still fully supported)
        must not manufacture one on a later read."""
        from aurora_understanding_sediment import UnderstandingSedimentOverlay

        overlay1 = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
        overlay1.deposit("OtherNonComp", "T:COST|T:OPERATOR", 0.75)  # no ref= kwarg
        overlay1.save()
        del overlay1

        overlay2 = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
        assert overlay2.ref_for("OtherNonComp", "T:COST|T:OPERATOR") is None
        # The delta itself is still there -- only the ref is (correctly) absent.
        assert overlay2.delta("OtherNonComp", "T:COST|T:OPERATOR") > 0.0

    def test_old_on_disk_records_without_the_ref_field_still_load(self, tmp_path):
        """A record written by the PRE-EXTENSION schema (no
        representational_ref key at all) must still load without error --
        proves this pass's change is truly additive, not a breaking schema
        migration."""
        import time
        from aurora_understanding_sediment import UnderstandingSedimentOverlay, OVERLAY_FILENAME

        legacy_payload = {
            "version": 1,
            "entries": {
                "LegacyNonComp": {
                    "X:OPERATOR|X:OPERATOR": {
                        "delta": 0.12, "last_touch": time.time(),
                        "deposits": 3, "last_worth": 0.61,
                        # no "representational_ref" key -- exactly the old shape
                    }
                }
            },
        }
        path = os.path.join(str(tmp_path), OVERLAY_FILENAME)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(legacy_payload, f)

        overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
        assert overlay.delta("LegacyNonComp", "X:OPERATOR|X:OPERATOR") == pytest.approx(0.12, abs=0.01)
        assert overlay.ref_for("LegacyNonComp", "X:OPERATOR|X:OPERATOR") is None

    def test_real_interpret_call_deposits_a_recoverable_ref_across_restart(self, tmp_path):
        """Full, real, end-to-end path: ReflexiveInterpreter.interpret()
        (not a hand-built overlay call) -- then a fresh interpreter
        instance recovers the same reference."""
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory
        from aurora_understanding_sediment import slot_key

        manifold_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_manifold_directory")
        ri1 = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=str(tmp_path))
        state = ri1.interpret("I need to protect my boundaries here")
        assert state.is_understood is True
        del ri1

        ri2 = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=str(tmp_path))
        key = state.nc_name or f"{state.constraint}:{state.dimension}"
        slot = slot_key(state.constraint, state.dimension)
        ref_encoded = ri2._overlay.ref_for(key, slot)
        assert ref_encoded is not None
        ref = RepresentationalRef.decode(ref_encoded)
        assert ref.nc_law_c == state.constraint
        assert ref.nc_dim == state.dimension
        # This call site resolves a C1-level ref (nc_target known via the
        # directory) -- not a guess, and not silently promoted further.
        assert ref.level() in ("C1_125", "D1_25")
