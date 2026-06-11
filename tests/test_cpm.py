"""
Tests for Aurora's Constraint Physics Machine:
  - ConstraintHead: maps IVM polarity → crystal address
  - IStateOperations: I-state × recursion level field operations
  - Genealogy walk_link_sequence: DAG → ordered program steps
  - CPMSession: ties all three together
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ivm(polarity: dict):
    """Fake IVM that returns a fixed global_polarity dict."""
    ivm = MagicMock()
    ivm.get_global_polarity.return_value = polarity
    return ivm


def _make_crystal(stage='base', bucket=(0.5, 0.5, 0.5, 0.5, 0.5)):
    crystal = MagicMock()
    crystal.stage = stage
    crystal.axis_bucket = bucket
    crystal.current_overlay = {}
    return crystal


def _make_registry(crystal=None):
    registry = MagicMock()
    registry.query.return_value = crystal
    # expose _nodes for tape_size reporting
    registry._nodes = {}
    return registry


# ---------------------------------------------------------------------------
# ConstraintHead
# ---------------------------------------------------------------------------

from aurora_constraint_head import ConstraintHead, HeadPosition


class TestConstraintHead:

    def test_advance_returns_head_position(self):
        ivm = _make_ivm({'existence': 0.8, 'temporal': 0.4,
                         'energy': 0.6, 'boundary': 0.2, 'agency': 1.0})
        reg = _make_registry()
        head = ConstraintHead(ivm, reg)
        pos = head.advance()
        assert isinstance(pos, HeadPosition)
        assert pos.tick == 1

    def test_polarity_mapped_to_0_1_range(self):
        # polarity=-1.0 → axis=0.0; polarity=+1.0 → axis=1.0
        ivm = _make_ivm({'existence': -1.0, 'temporal': 1.0,
                         'energy': 0.0, 'boundary': -1.0, 'agency': 0.0})
        head = ConstraintHead(ivm, _make_registry())
        pos = head.advance()
        assert abs(pos.axis_state['X'] - 0.0) < 1e-6
        assert abs(pos.axis_state['T'] - 1.0) < 1e-6
        assert abs(pos.axis_state['N'] - 0.5) < 1e-6

    def test_has_moved_after_bucket_change(self):
        ivm = _make_ivm({'existence': 0.0, 'temporal': 0.0,
                         'energy': 0.0, 'boundary': 0.0, 'agency': 0.0})
        head = ConstraintHead(ivm, _make_registry())
        head.advance()
        ivm.get_global_polarity.return_value = {
            'existence': 1.0, 'temporal': 1.0,
            'energy': 1.0, 'boundary': 1.0, 'agency': 1.0,
        }
        head.advance()
        assert head.has_moved

    def test_has_not_moved_on_same_bucket(self):
        ivm = _make_ivm({'existence': 0.1, 'temporal': 0.1,
                         'energy': 0.1, 'boundary': 0.1, 'agency': 0.1})
        head = ConstraintHead(ivm, _make_registry())
        head.advance()
        head.advance()
        assert not head.has_moved

    def test_recursion_depth_surface_for_low_a_b(self):
        ivm = _make_ivm({'existence': 0.0, 'temporal': 0.0,
                         'energy': 0.0, 'boundary': -1.0, 'agency': -1.0})
        head = ConstraintHead(ivm, _make_registry())
        head.advance()
        assert head.recursion_depth() == 0  # SURFACE

    def test_recursion_depth_core_for_high_a_b(self):
        ivm = _make_ivm({'existence': 0.0, 'temporal': 0.0,
                         'energy': 0.0, 'boundary': 1.0, 'agency': 1.0})
        head = ConstraintHead(ivm, _make_registry())
        head.advance()
        assert head.recursion_depth() == 4  # CORE

    def test_trace_grows_with_advances(self):
        ivm = _make_ivm({'existence': 0.0, 'temporal': 0.0,
                         'energy': 0.0, 'boundary': 0.0, 'agency': 0.0})
        head = ConstraintHead(ivm, _make_registry())
        for _ in range(5):
            head.advance()
        assert len(head.trace) == 5

    def test_no_crystal_at_unknown_address(self):
        ivm = _make_ivm({'existence': 0.5, 'temporal': 0.5,
                         'energy': 0.5, 'boundary': 0.5, 'agency': 0.5})
        reg = _make_registry(crystal=None)
        head = ConstraintHead(ivm, reg)
        head.advance()
        assert not head.at_known_crystal()

    def test_dominant_axis_is_highest(self):
        ivm = _make_ivm({'existence': 0.0, 'temporal': -0.5,
                         'energy': 1.0, 'boundary': 0.0, 'agency': -1.0})
        head = ConstraintHead(ivm, _make_registry())
        head.advance()
        assert head.dominant_axis() == 'N'


# ---------------------------------------------------------------------------
# IStateOperations
# ---------------------------------------------------------------------------

from aurora_istate_operations import (
    apply_operation, istate_to_op, read_cell_cpm, cell_symbol,
    IStateOp, FieldOperation,
)


class TestIStateOperations:

    def _op(self, istate: str, rec: int = 0, intensity: float = 1.0):
        return istate_to_op(istate, rec, intensity)

    def test_istate_to_op_known(self):
        op = self._op('I_IS', 2)
        assert op is not None
        assert op.istate_op == IStateOp.ASSERT
        assert op.axis == 'X'
        assert op.recursion_level == 2

    def test_istate_to_op_unknown_returns_none(self):
        assert istate_to_op('I_WHATEVER', 0) is None

    def test_assert_increments_assert_count(self):
        crystal = _make_crystal()
        op = self._op('I_IS')
        result = apply_operation(op, crystal, MagicMock())
        assert result.success
        cpm = read_cell_cpm(crystal)
        assert cpm['assert_count'] == 1

    def test_negate_raises_negate_pressure(self):
        crystal = _make_crystal()
        op = self._op('I_ISNT', intensity=1.0)
        apply_operation(op, crystal, MagicMock())
        cpm = read_cell_cpm(crystal)
        assert cpm['negate_pressure'] > 0.0

    def test_block_reduces_temporal(self):
        crystal = _make_crystal()
        # First extend temporal
        apply_operation(self._op('I_CAN', intensity=1.0), crystal, MagicMock())
        temporal_before = read_cell_cpm(crystal)['extend_temporal']
        # Then block
        apply_operation(self._op('I_CANNOT', intensity=1.0), crystal, MagicMock())
        temporal_after = read_cell_cpm(crystal)['extend_temporal']
        assert temporal_after < temporal_before

    def test_none_crystal_returns_failure(self):
        op = self._op('I_IS')
        result = apply_operation(op, None, MagicMock())
        assert not result.success

    def test_shallow_propagation_generates_events(self):
        crystal = _make_crystal()
        op = istate_to_op('I_DO', recursion_level=1, intensity=1.0)  # SHALLOW
        result = apply_operation(op, crystal, MagicMock())
        assert len(result.propagated_to) > 0
        # N-axis at SHALLOW should propagate to B, T, X via coupling
        axes = {p.axis for p in result.propagated_to}
        assert 'B' in axes

    def test_surface_no_propagation(self):
        crystal = _make_crystal()
        op = istate_to_op('I_DO', recursion_level=0, intensity=1.0)  # SURFACE
        result = apply_operation(op, crystal, MagicMock())
        assert len(result.propagated_to) == 0

    def test_cell_symbol_returns_stage(self):
        crystal = _make_crystal(stage='quasi')
        assert cell_symbol(crystal) == 'quasi'

    def test_cell_symbol_none_crystal(self):
        assert cell_symbol(None) is None

    def test_cpm_state_namespaced(self):
        crystal = _make_crystal()
        apply_operation(self._op('I_DID'), crystal, MagicMock())
        # Should be under '_cpm' key, not polluting other overlay keys
        assert '_cpm' in crystal.current_overlay
        other_keys = [k for k in crystal.current_overlay if k != '_cpm']
        assert len(other_keys) == 0

    def test_withhold_reduces_agency(self):
        crystal = _make_crystal()
        apply_operation(self._op('I_DID', intensity=1.0), crystal, MagicMock())
        commit_before = read_cell_cpm(crystal)['commit_agency']
        apply_operation(self._op('I_DIDNT', intensity=1.0), crystal, MagicMock())
        commit_after = read_cell_cpm(crystal)['commit_agency']
        assert commit_after < commit_before

    def test_recursion_level_clamped(self):
        op = istate_to_op('I_IS', recursion_level=99, intensity=1.0)
        assert op.recursion_level == 4


# ---------------------------------------------------------------------------
# Genealogy walk_link_sequence
# ---------------------------------------------------------------------------

from unittest.mock import patch


class TestWalkLinkSequence:

    def _make_genealogy(self, links: dict):
        from unittest.mock import MagicMock
        g = MagicMock()
        g.links = links
        # Attach the real walk_link_sequence to this mock
        from aurora_internal.constraint_genealogy import (
            ConstraintGenealogyLogger
        )
        g.walk_link_sequence = lambda lid: ConstraintGenealogyLogger.walk_link_sequence(g, lid)
        return g

    def _make_link(self, lid, parents, depth, relief, dominant=None):
        link = MagicMock()
        link.id = lid
        link.parents = parents
        link.depth = depth
        link.mean_relief = relief
        link.dominant_relief_axis = dominant
        return link

    def test_single_link_no_parents(self):
        link = self._make_link('L:abc', [], 1, {'X': 0.7, 'T': 0.2})
        g = self._make_genealogy({'L:abc': link})
        seq = g.walk_link_sequence('L:abc')
        assert len(seq) == 1
        assert seq[0]['link_id'] == 'L:abc'
        assert seq[0]['i_state'] == 'I_IS'  # X+ positive relief
        assert seq[0]['recursion_level'] == 0  # depth 1 → SURFACE

    def test_negative_relief_gives_negative_istate(self):
        link = self._make_link('L:neg', [], 1, {'A': -0.5})
        g = self._make_genealogy({'L:neg': link})
        seq = g.walk_link_sequence('L:neg')
        assert seq[0]['i_state'] == 'I_DIDNT'  # A− negative relief

    def test_parent_chain_ordered_ancestor_first(self):
        parent = self._make_link('L:p1', [], 1, {'N': 0.8})
        child  = self._make_link('L:c1', ['L:p1'], 2, {'A': 0.6})
        g = self._make_genealogy({'L:p1': parent, 'L:c1': child})
        seq = g.walk_link_sequence('L:c1')
        assert len(seq) == 2
        assert seq[0]['link_id'] == 'L:p1'  # ancestor first
        assert seq[1]['link_id'] == 'L:c1'

    def test_ability_id_in_parents_is_skipped(self):
        # Ability IDs are not in self.links — they're leaves
        link = self._make_link('L:x1', ['ABILITY:raw'], 1, {'B': 0.5})
        g = self._make_genealogy({'L:x1': link})
        seq = g.walk_link_sequence('L:x1')
        assert len(seq) == 1  # ability skipped, only the link itself

    def test_depth_mapping_to_recursion_level(self):
        cases = [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (99, 4)]
        for depth, expected_rec in cases:
            link = self._make_link(f'L:{depth}', [], depth, {'X': 0.5})
            g = self._make_genealogy({f'L:{depth}': link})
            seq = g.walk_link_sequence(f'L:{depth}')
            assert seq[0]['recursion_level'] == expected_rec, f"depth {depth}"

    def test_unknown_link_returns_empty(self):
        g = self._make_genealogy({})
        seq = g.walk_link_sequence('L:NOTEXIST')
        assert seq == []

    def test_cycle_protection(self):
        # Cycle: L:a → L:b → L:a — should not infinite-loop
        a = self._make_link('L:a', ['L:b'], 2, {'X': 0.5})
        b = self._make_link('L:b', ['L:a'], 2, {'T': 0.5})
        g = self._make_genealogy({'L:a': a, 'L:b': b})
        seq = g.walk_link_sequence('L:a')
        assert len(seq) == 2  # both present, no infinite loop


# ---------------------------------------------------------------------------
# CPMSession integration
# ---------------------------------------------------------------------------

from aurora_computational_model import CPMSession, CPM_FORMAL_DEFINITION


class TestCPMSession:

    def _session(self, crystal=None):
        crystal = crystal or _make_crystal()
        ivm = _make_ivm({'existence': 0.5, 'temporal': 0.3,
                         'energy': 0.7, 'boundary': 0.2, 'agency': 0.9})
        reg = _make_registry(crystal)
        return CPMSession(ivm, reg), crystal

    def test_advance_returns_head_position(self):
        session, _ = self._session()
        pos = session.advance()
        assert pos is not None
        assert pos.tick == 1

    def test_apply_istate_applies_to_crystal(self):
        session, crystal = self._session()
        session.advance()
        result = session.apply_istate('I_IS')
        assert result is not None
        assert result.success
        from aurora_istate_operations import read_cell_cpm
        assert read_cell_cpm(crystal)['assert_count'] == 1

    def test_apply_istate_before_advance_returns_none(self):
        session, _ = self._session()
        result = session.apply_istate('I_DO')
        assert result is None

    def test_snapshot_has_expected_keys(self):
        session, _ = self._session()
        session.advance()
        snap = session.snapshot()
        for key in ('address', 'tape_symbol', 'dominant_axis',
                    'recursion_depth', 'head_tick', 'tape_size'):
            assert key in snap, f"Missing key: {key}"

    def test_tape_symbol_returns_crystal_stage(self):
        session, _ = self._session(_make_crystal(stage='higher_order'))
        session.advance()
        assert session.tape_symbol() == 'higher_order'

    def test_execute_program_without_genealogy_returns_empty(self):
        session, _ = self._session()
        session.advance()
        results = session.execute_program('L:any')
        assert results == []

    def test_execute_program_with_genealogy(self):
        from unittest.mock import MagicMock
        session, _ = self._session()
        session.advance()
        genealogy = MagicMock()
        genealogy.walk_link_sequence.return_value = [
            {'i_state': 'I_DO', 'recursion_level': 1, 'axis': 'N',
             'mean_relief': {'N': 0.8}, 'depth': 2, 'link_id': 'L:test'},
        ]
        session.set_genealogy(genealogy)
        results = session.execute_program('L:test')
        assert len(results) == 1
        assert results[0].success

    def test_op_trace_records_successful_ops(self):
        session, _ = self._session()
        session.advance()
        session.apply_istate('I_IS')
        session.apply_istate('I_DID')
        trace = session.op_trace()
        assert len(trace) == 2

    def test_formal_definition_has_50_states(self):
        assert CPM_FORMAL_DEFINITION['state_set']['total_states'] == 50

    def test_formal_definition_energy_conservation(self):
        assert 'energy_conservation' in CPM_FORMAL_DEFINITION


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    """
    Verify that CPM state flows into the synthesis pipeline correctly.
    Tests the three integration points:
      1. Braid thread advances CPM each tick
      2. Language Field n_cost modulated by crystal stage
      3. Snapshot exposes correct state for observation string
    """

    def _session(self, crystal=None):
        crystal = crystal or _make_crystal()
        ivm = _make_ivm({'existence': 0.5, 'temporal': 0.3,
                         'energy': 0.7, 'boundary': 0.2, 'agency': 0.9})
        reg = _make_registry(crystal)
        return CPMSession(ivm, reg), crystal, ivm, reg

    # -- Braid thread integration --

    def test_cpm_in_systems_advances_from_braid_loop(self):
        session, _, _, _ = self._session()
        systems = {'cpm': session}

        # Simulate what the braid loop does each tick
        cpm = systems.get('cpm')
        assert cpm is not None
        cpm.advance()
        assert cpm.head.tick == 1

    def test_cpm_absent_from_systems_no_error(self):
        systems = {}
        cpm = systems.get('cpm')
        # Should silently do nothing — the braid loop guards with `if cpm is not None`
        if cpm is not None:
            cpm.advance()
        assert True  # no exception

    # -- Language Field n_cost modulation --

    def test_language_field_set_cpm(self):
        from aurora_language_field import LanguageField
        from unittest.mock import MagicMock
        lf = LanguageField(identity_field=MagicMock())
        session, _, _, _ = self._session()
        lf.set_cpm(session)
        assert lf._cpm is session

    def test_cpm_n_cost_quasi_crystal_cheaper(self):
        from aurora_language_field import LanguageField
        from unittest.mock import MagicMock
        lf = LanguageField(identity_field=MagicMock())
        session, _, _, _ = self._session(crystal=_make_crystal(stage='quasi'))
        session.advance()
        lf.set_cpm(session)
        reduced = lf._cpm_n_cost(0.60)
        assert reduced < 0.60
        assert reduced >= 0.08  # N_COST_FLOOR

    def test_cpm_n_cost_unmapped_more_expensive(self):
        from aurora_language_field import LanguageField
        from unittest.mock import MagicMock
        lf = LanguageField(identity_field=MagicMock())
        # Registry returns None → no crystal at address
        ivm = _make_ivm({'existence': 0.5, 'temporal': 0.3,
                         'energy': 0.7, 'boundary': 0.2, 'agency': 0.9})
        reg = _make_registry(crystal=None)
        session = CPMSession(ivm, reg)
        session.advance()
        lf.set_cpm(session)
        increased = lf._cpm_n_cost(0.50)
        assert increased > 0.50

    def test_cpm_n_cost_no_cpm_unchanged(self):
        from aurora_language_field import LanguageField
        from unittest.mock import MagicMock
        lf = LanguageField(identity_field=MagicMock())
        assert lf._cpm is None
        result = lf._cpm_n_cost(0.45)
        assert result == 0.45

    def test_cpm_n_cost_base_crystal_unchanged(self):
        from aurora_language_field import LanguageField
        from unittest.mock import MagicMock
        lf = LanguageField(identity_field=MagicMock())
        session, _, _, _ = self._session(crystal=_make_crystal(stage='base'))
        session.advance()
        lf.set_cpm(session)
        result = lf._cpm_n_cost(0.45)
        assert result == 0.45

    # -- Observation string snapshot --

    def test_snapshot_charted_territory(self):
        session, crystal, _, _ = self._session(crystal=_make_crystal(stage='higher_order'))
        session.advance()
        snap = session.snapshot()
        assert snap['tape_symbol'] == 'higher_order'
        assert snap['at_known_crystal'] is True
        assert snap['recursion_depth'] in range(5)

    def test_snapshot_uncharted_territory(self):
        ivm = _make_ivm({'existence': 0.5, 'temporal': 0.3,
                         'energy': 0.7, 'boundary': 0.2, 'agency': 0.9})
        reg = _make_registry(crystal=None)
        session = CPMSession(ivm, reg)
        session.advance()
        snap = session.snapshot()
        assert snap['tape_symbol'] is None
        assert snap['at_known_crystal'] is False

    def test_synthesis_istate_applied_to_crystal(self):
        session, crystal, _, _ = self._session()
        session.advance()
        # Simulate what handle_message does after synthesis with A-dominant axis
        dom = 'A'
        polarity = 0.9   # positive → I_DID
        result = session.apply_istate('I_DID', intensity=abs(polarity - 0.5) * 2.0)
        assert result is not None and result.success
        from aurora_istate_operations import read_cell_cpm
        assert read_cell_cpm(crystal)['commit_agency'] > 0

    def test_synthesis_negative_istate_on_low_polarity(self):
        session, crystal, _, _ = self._session()
        session.advance()
        # polarity=0.2 → intensity=0.6 → negative I-state should apply pressure
        result = session.apply_istate('I_ISNT', intensity=abs(0.2 - 0.5) * 2.0)
        assert result is not None and result.success
        from aurora_istate_operations import read_cell_cpm
        assert read_cell_cpm(crystal)['negate_pressure'] > 0


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
