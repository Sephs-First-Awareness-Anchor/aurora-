# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE: unresolved fields must remain unresolved. No subsystem this
pass may silently repin, reclassify, or convert a None field into an
inferred anchor value -- as_pinned_anchor() is the only, explicitly-named
way to alias sub_law_c/sub_law_d := nc_law_c/nc_dim, and it must never be
called implicitly by any of the code touched this pass.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUnresolvedRemainsNoneThroughLiveInterpret:
    def test_low_confidence_input_leaves_sub_and_col_fields_unresolved(self):
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory
        from aurora_representational_address import RepresentationalRef
        import tempfile
        import shutil

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        tmp = tempfile.mkdtemp(prefix="aurora_unresolved_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
            state = ri.interpret("hm")
            ref = RepresentationalRef.decode(state.representational_ref)
            # A D1-level fallback ref must leave nc_target/sub_*/col_* unresolved.
            assert ref.sub_law_c is None
            assert ref.sub_law_d is None
            assert ref.col_law_c is None
            assert ref.col_law_d is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_understood_input_c1_ref_still_leaves_sub_and_col_unresolved(self):
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory
        from aurora_representational_address import RepresentationalRef
        import tempfile
        import shutil

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        tmp = tempfile.mkdtemp(prefix="aurora_unresolved_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
            state = ri.interpret("I need to protect my boundaries here")
            ref = RepresentationalRef.decode(state.representational_ref)
            # This pass only ever builds C1-level (or D1) refs from live
            # interpret() -- it never resolves sub_law_c/sub_law_d/col_*
            # itself, since doing so would require deciding new semantics.
            assert ref.sub_law_c is None
            assert ref.sub_law_d is None
            assert ref.col_law_c is None
            assert ref.col_law_d is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestNoImplicitPinningInTouchedFiles:
    """as_pinned_anchor() must remain the only, explicitly-named alias
    mechanism -- none of this pass's touched files may call it implicitly
    (i.e. inside a helper that silently substitutes a default)."""

    def test_reflexive_interpreter_does_not_call_as_pinned_anchor(self):
        import aurora_reflexive_interpreter as ri
        src = inspect.getsource(ri)
        assert "as_pinned_anchor(" not in src

    def test_rcec_does_not_call_as_pinned_anchor(self):
        from aurora_internal import aurora_cognitive_experience_chamber as rcec
        src = inspect.getsource(rcec)
        assert "as_pinned_anchor(" not in src

    def test_understanding_sediment_does_not_call_as_pinned_anchor(self):
        import aurora_understanding_sediment as us
        src = inspect.getsource(us)
        assert "as_pinned_anchor(" not in src


class TestFieldKeysForRefDoesNotFabricateMissingData:
    def test_unknown_ref_returns_empty_list_not_a_guess(self):
        from aurora_understanding_sediment import UnderstandingSedimentOverlay
        import tempfile
        import shutil

        tmp = tempfile.mkdtemp(prefix="aurora_unresolved_overlay_")
        try:
            overlay = UnderstandingSedimentOverlay(state_dir=tmp)
            assert overlay.field_keys_for_ref("REF:NOT:A:REAL:REF:?:?:?") == []
            assert overlay.field_keys_for_ref("") == []
            assert overlay.field_keys_for_ref(None) == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_ref_for_missing_slot_returns_none_not_a_fabricated_ref(self):
        from aurora_understanding_sediment import UnderstandingSedimentOverlay
        import tempfile
        import shutil

        tmp = tempfile.mkdtemp(prefix="aurora_unresolved_overlay_")
        try:
            overlay = UnderstandingSedimentOverlay(state_dir=tmp)
            assert overlay.ref_for("nonexistent_field_key", "nonexistent_slot") is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSedimemoryPassthroughDoesNotFabricateWhenAbsent:
    def test_content_without_a_ref_key_has_no_ref_after_extraction(self):
        import aurora_sedimemory as sm
        filt = sm.NCStrainFilter()
        content = {"source": "test", "module": "test_mod"}
        sliced = filt._extract_slice(
            content, sm.Constraint.X, sm.NonCompDimension.OPERATOR, 0.9
        )
        assert "representational_ref" not in sliced

    def test_content_with_a_ref_key_passes_it_through_unmodified(self):
        import aurora_sedimemory as sm
        filt = sm.NCStrainFilter()
        ref = "REF:X:OPERATOR:X:?:?:?:?"
        content = {"source": "test", "representational_ref": ref}
        sliced = filt._extract_slice(
            content, sm.Constraint.X, sm.NonCompDimension.OPERATOR, 0.9
        )
        assert sliced.get("representational_ref") == ref
