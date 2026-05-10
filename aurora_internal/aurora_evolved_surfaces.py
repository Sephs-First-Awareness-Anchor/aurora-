#!/usr/bin/env python3
"""
AURORA EVOLVED SURFACES
=======================
Generated from developmental lineage state.
Do not hand-edit generated methods; regenerate through the code autoevolver.
"""

from __future__ import annotations

import importlib
import inspect
import os
import time
from typing import Any, Dict, List, Optional


_SURFACE_REGISTRY: Dict[str, Dict[str, Any]] = {'reflect_aurora_consciousness_engine_consciousnessengine_tick': {'constraints': ['boundary'],
                                                                  'effect_modes': ['interface_boundary_change'],
                                                                  'effect_phrases': ['legacy '
                                                                                     'evolved-surface '
                                                                                     'binding '
                                                                                     'preserved '
                                                                                     'across '
                                                                                     'promotion'],
                                                                  'kind': 'compatibility_alias',
                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                  'op_id': 'reflect_aurora_consciousness_engine_consciousnessengine_tick',
                                                                  'origin_chain': [],
                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                  'surface_score': 0.0},
 'reflect_aurora_dimensional_systems_dimensionalsystems_current_pressure_vec': {'constraints': ['boundary'],
                                                                                'effect_modes': ['interface_boundary_change'],
                                                                                'effect_phrases': ['legacy '
                                                                                                   'evolved-surface '
                                                                                                   'binding '
                                                                                                   'preserved '
                                                                                                   'across '
                                                                                                   'promotion'],
                                                                                'kind': 'compatibility_alias',
                                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                'op_id': 'reflect_aurora_dimensional_systems_dimensionalsystems_current_pressure_vec',
                                                                                'origin_chain': [],
                                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                'surface_score': 0.0},
 'reflect_aurora_dimensional_systems_energyregulatorsystem_tick': {'constraints': ['boundary'],
                                                                   'effect_modes': ['interface_boundary_change'],
                                                                   'effect_phrases': ['legacy '
                                                                                      'evolved-surface '
                                                                                      'binding '
                                                                                      'preserved '
                                                                                      'across '
                                                                                      'promotion'],
                                                                   'kind': 'compatibility_alias',
                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                   'op_id': 'reflect_aurora_dimensional_systems_energyregulatorsystem_tick',
                                                                   'origin_chain': [],
                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                   'surface_score': 0.0},
 'reflect_aurora_dimensional_systems_energyregulatorsystem_update_links_for_facet': {'constraints': ['boundary'],
                                                                                     'effect_modes': ['interface_boundary_change'],
                                                                                     'effect_phrases': ['legacy '
                                                                                                        'evolved-surface '
                                                                                                        'binding '
                                                                                                        'preserved '
                                                                                                        'across '
                                                                                                        'promotion'],
                                                                                     'kind': 'compatibility_alias',
                                                                                     'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                     'op_id': 'reflect_aurora_dimensional_systems_energyregulatorsystem_update_links_for_facet',
                                                                                     'origin_chain': [],
                                                                                     'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                     'surface_score': 0.0},
 'reflect_aurora_dimensional_systems_poolview_inject': {'constraints': ['boundary'],
                                                        'effect_modes': ['interface_boundary_change'],
                                                        'effect_phrases': ['legacy evolved-surface '
                                                                           'binding preserved '
                                                                           'across promotion'],
                                                        'kind': 'compatibility_alias',
                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                        'op_id': 'reflect_aurora_dimensional_systems_poolview_inject',
                                                        'origin_chain': [],
                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                        'surface_score': 0.0},
 'reflect_aurora_expression_perception_sensoryconceptmemory_cluster_and_promote': {'constraints': ['boundary'],
                                                                                   'effect_modes': ['interface_boundary_change'],
                                                                                   'effect_phrases': ['legacy '
                                                                                                      'evolved-surface '
                                                                                                      'binding '
                                                                                                      'preserved '
                                                                                                      'across '
                                                                                                      'promotion'],
                                                                                   'kind': 'compatibility_alias',
                                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                   'op_id': 'reflect_aurora_expression_perception_sensoryconceptmemory_cluster_and_promote',
                                                                                   'origin_chain': [],
                                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                   'surface_score': 0.0},
 'reflect_aurora_expression_perception_visuallinguisticmapper_learn_association': {'constraints': ['boundary'],
                                                                                   'effect_modes': ['interface_boundary_change'],
                                                                                   'effect_phrases': ['legacy '
                                                                                                      'evolved-surface '
                                                                                                      'binding '
                                                                                                      'preserved '
                                                                                                      'across '
                                                                                                      'promotion'],
                                                                                   'kind': 'compatibility_alias',
                                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                   'op_id': 'reflect_aurora_expression_perception_visuallinguisticmapper_learn_association',
                                                                                   'origin_chain': [],
                                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                   'surface_score': 0.0},
 'reflect_aurora_expression_perception_webimagedownloader_download_for_concept': {'constraints': ['boundary'],
                                                                                  'effect_modes': ['interface_boundary_change'],
                                                                                  'effect_phrases': ['legacy '
                                                                                                     'evolved-surface '
                                                                                                     'binding '
                                                                                                     'preserved '
                                                                                                     'across '
                                                                                                     'promotion'],
                                                                                  'kind': 'compatibility_alias',
                                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                  'op_id': 'reflect_aurora_expression_perception_webimagedownloader_download_for_concept',
                                                                                  'origin_chain': [],
                                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                  'surface_score': 0.0},
 'reflect_aurora_expression_perception_webimagedownloader_download_seed_batch': {'constraints': ['boundary'],
                                                                                 'effect_modes': ['interface_boundary_change'],
                                                                                 'effect_phrases': ['legacy '
                                                                                                    'evolved-surface '
                                                                                                    'binding '
                                                                                                    'preserved '
                                                                                                    'across '
                                                                                                    'promotion'],
                                                                                 'kind': 'compatibility_alias',
                                                                                 'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                 'op_id': 'reflect_aurora_expression_perception_webimagedownloader_download_seed_batch',
                                                                                 'origin_chain': [],
                                                                                 'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                 'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_actionlog': {'constraints': ['boundary'],
                                                             'effect_modes': ['interface_boundary_change'],
                                                             'effect_phrases': ['legacy '
                                                                                'evolved-surface '
                                                                                'binding preserved '
                                                                                'across promotion'],
                                                             'kind': 'compatibility_alias',
                                                             'module': 'aurora_internal.aurora_evolved_surfaces',
                                                             'op_id': 'reflect_aurora_governance_persistence_gateway_actionlog',
                                                             'origin_chain': [],
                                                             'representation_kind': 'legacy_surface_compatibility_alias',
                                                             'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_actionlog_get_by_type': {'constraints': ['boundary'],
                                                                         'effect_modes': ['interface_boundary_change'],
                                                                         'effect_phrases': ['legacy '
                                                                                            'evolved-surface '
                                                                                            'binding '
                                                                                            'preserved '
                                                                                            'across '
                                                                                            'promotion'],
                                                                         'kind': 'compatibility_alias',
                                                                         'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                         'op_id': 'reflect_aurora_governance_persistence_gateway_actionlog_get_by_type',
                                                                         'origin_chain': [],
                                                                         'representation_kind': 'legacy_surface_compatibility_alias',
                                                                         'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_actionlog_get_recent': {'constraints': ['boundary'],
                                                                        'effect_modes': ['interface_boundary_change'],
                                                                        'effect_phrases': ['legacy '
                                                                                           'evolved-surface '
                                                                                           'binding '
                                                                                           'preserved '
                                                                                           'across '
                                                                                           'promotion'],
                                                                        'kind': 'compatibility_alias',
                                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                        'op_id': 'reflect_aurora_governance_persistence_gateway_actionlog_get_recent',
                                                                        'origin_chain': [],
                                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                                        'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_actionlog_init': {'constraints': ['boundary'],
                                                                  'effect_modes': ['interface_boundary_change'],
                                                                  'effect_phrases': ['legacy '
                                                                                     'evolved-surface '
                                                                                     'binding '
                                                                                     'preserved '
                                                                                     'across '
                                                                                     'promotion'],
                                                                  'kind': 'compatibility_alias',
                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                  'op_id': 'reflect_aurora_governance_persistence_gateway_actionlog_init',
                                                                  'origin_chain': [],
                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                  'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_actionlog_log': {'constraints': ['boundary'],
                                                                 'effect_modes': ['interface_boundary_change'],
                                                                 'effect_phrases': ['legacy '
                                                                                    'evolved-surface '
                                                                                    'binding '
                                                                                    'preserved '
                                                                                    'across '
                                                                                    'promotion'],
                                                                 'kind': 'compatibility_alias',
                                                                 'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                 'op_id': 'reflect_aurora_governance_persistence_gateway_actionlog_log',
                                                                 'origin_chain': [],
                                                                 'representation_kind': 'legacy_surface_compatibility_alias',
                                                                 'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_atomicwriter_append_jsonl': {'constraints': ['boundary'],
                                                                             'effect_modes': ['interface_boundary_change'],
                                                                             'effect_phrases': ['legacy '
                                                                                                'evolved-surface '
                                                                                                'binding '
                                                                                                'preserved '
                                                                                                'across '
                                                                                                'promotion'],
                                                                             'kind': 'compatibility_alias',
                                                                             'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                             'op_id': 'reflect_aurora_governance_persistence_gateway_atomicwriter_append_jsonl',
                                                                             'origin_chain': [],
                                                                             'representation_kind': 'legacy_surface_compatibility_alias',
                                                                             'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_aurorastatesnapshot': {'constraints': ['boundary'],
                                                                       'effect_modes': ['interface_boundary_change'],
                                                                       'effect_phrases': ['legacy '
                                                                                          'evolved-surface '
                                                                                          'binding '
                                                                                          'preserved '
                                                                                          'across '
                                                                                          'promotion'],
                                                                       'kind': 'compatibility_alias',
                                                                       'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                       'op_id': 'reflect_aurora_governance_persistence_gateway_aurorastatesnapshot',
                                                                       'origin_chain': [],
                                                                       'representation_kind': 'legacy_surface_compatibility_alias',
                                                                       'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_autonomousaction': {'constraints': ['boundary'],
                                                                    'effect_modes': ['interface_boundary_change'],
                                                                    'effect_phrases': ['legacy '
                                                                                       'evolved-surface '
                                                                                       'binding '
                                                                                       'preserved '
                                                                                       'across '
                                                                                       'promotion'],
                                                                    'kind': 'compatibility_alias',
                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_autonomousaction',
                                                                    'origin_chain': [],
                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_autonomyengine_get_recent_actions': {'constraints': ['boundary'],
                                                                                     'effect_modes': ['interface_boundary_change'],
                                                                                     'effect_phrases': ['legacy '
                                                                                                        'evolved-surface '
                                                                                                        'binding '
                                                                                                        'preserved '
                                                                                                        'across '
                                                                                                        'promotion'],
                                                                                     'kind': 'compatibility_alias',
                                                                                     'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                     'op_id': 'reflect_aurora_governance_persistence_gateway_autonomyengine_get_recent_actions',
                                                                                     'origin_chain': [],
                                                                                     'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                     'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_autonomyengine_get_status': {'constraints': ['boundary'],
                                                                             'effect_modes': ['interface_boundary_change'],
                                                                             'effect_phrases': ['legacy '
                                                                                                'evolved-surface '
                                                                                                'binding '
                                                                                                'preserved '
                                                                                                'across '
                                                                                                'promotion'],
                                                                             'kind': 'compatibility_alias',
                                                                             'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                             'op_id': 'reflect_aurora_governance_persistence_gateway_autonomyengine_get_status',
                                                                             'origin_chain': [],
                                                                             'representation_kind': 'legacy_surface_compatibility_alias',
                                                                             'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_autonomyengine_search_files': {'constraints': ['boundary'],
                                                                               'effect_modes': ['interface_boundary_change'],
                                                                               'effect_phrases': ['legacy '
                                                                                                  'evolved-surface '
                                                                                                  'binding '
                                                                                                  'preserved '
                                                                                                  'across '
                                                                                                  'promotion'],
                                                                               'kind': 'compatibility_alias',
                                                                               'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                               'op_id': 'reflect_aurora_governance_persistence_gateway_autonomyengine_search_files',
                                                                               'origin_chain': [],
                                                                               'representation_kind': 'legacy_surface_compatibility_alias',
                                                                               'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_checkpointmanager_signal_handler': {'constraints': ['boundary'],
                                                                                    'effect_modes': ['interface_boundary_change'],
                                                                                    'effect_phrases': ['legacy '
                                                                                                       'evolved-surface '
                                                                                                       'binding '
                                                                                                       'preserved '
                                                                                                       'across '
                                                                                                       'promotion'],
                                                                                    'kind': 'compatibility_alias',
                                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_checkpointmanager_signal_handler',
                                                                                    'origin_chain': [],
                                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_corpuscursor': {'constraints': ['boundary'],
                                                                'effect_modes': ['interface_boundary_change'],
                                                                'effect_phrases': ['legacy '
                                                                                   'evolved-surface '
                                                                                   'binding '
                                                                                   'preserved '
                                                                                   'across '
                                                                                   'promotion'],
                                                                'kind': 'compatibility_alias',
                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                'op_id': 'reflect_aurora_governance_persistence_gateway_corpuscursor',
                                                                'origin_chain': [],
                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_dailyquotas': {'constraints': ['boundary'],
                                                               'effect_modes': ['interface_boundary_change'],
                                                               'effect_phrases': ['legacy '
                                                                                  'evolved-surface '
                                                                                  'binding '
                                                                                  'preserved '
                                                                                  'across '
                                                                                  'promotion'],
                                                               'kind': 'compatibility_alias',
                                                               'module': 'aurora_internal.aurora_evolved_surfaces',
                                                               'op_id': 'reflect_aurora_governance_persistence_gateway_dailyquotas',
                                                               'origin_chain': [],
                                                               'representation_kind': 'legacy_surface_compatibility_alias',
                                                               'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_dailyquotas_reset_if_new_day': {'constraints': ['boundary'],
                                                                                'effect_modes': ['interface_boundary_change'],
                                                                                'effect_phrases': ['legacy '
                                                                                                   'evolved-surface '
                                                                                                   'binding '
                                                                                                   'preserved '
                                                                                                   'across '
                                                                                                   'promotion'],
                                                                                'kind': 'compatibility_alias',
                                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                'op_id': 'reflect_aurora_governance_persistence_gateway_dailyquotas_reset_if_new_day',
                                                                                'origin_chain': [],
                                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_dailyquotas_to_dict': {'constraints': ['boundary'],
                                                                       'effect_modes': ['interface_boundary_change'],
                                                                       'effect_phrases': ['legacy '
                                                                                          'evolved-surface '
                                                                                          'binding '
                                                                                          'preserved '
                                                                                          'across '
                                                                                          'promotion'],
                                                                       'kind': 'compatibility_alias',
                                                                       'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                       'op_id': 'reflect_aurora_governance_persistence_gateway_dailyquotas_to_dict',
                                                                       'origin_chain': [],
                                                                       'representation_kind': 'legacy_surface_compatibility_alias',
                                                                       'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_deviceawareness': {'constraints': ['boundary'],
                                                                   'effect_modes': ['interface_boundary_change'],
                                                                   'effect_phrases': ['legacy '
                                                                                      'evolved-surface '
                                                                                      'binding '
                                                                                      'preserved '
                                                                                      'across '
                                                                                      'promotion'],
                                                                   'kind': 'compatibility_alias',
                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                   'op_id': 'reflect_aurora_governance_persistence_gateway_deviceawareness',
                                                                   'origin_chain': [],
                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                   'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_devicerecord': {'constraints': ['boundary'],
                                                                'effect_modes': ['interface_boundary_change'],
                                                                'effect_phrases': ['legacy '
                                                                                   'evolved-surface '
                                                                                   'binding '
                                                                                   'preserved '
                                                                                   'across '
                                                                                   'promotion'],
                                                                'kind': 'compatibility_alias',
                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                'op_id': 'reflect_aurora_governance_persistence_gateway_devicerecord',
                                                                'origin_chain': [],
                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_drivesync': {'constraints': ['boundary'],
                                                             'effect_modes': ['interface_boundary_change'],
                                                             'effect_phrases': ['legacy '
                                                                                'evolved-surface '
                                                                                'binding preserved '
                                                                                'across promotion'],
                                                             'kind': 'compatibility_alias',
                                                             'module': 'aurora_internal.aurora_evolved_surfaces',
                                                             'op_id': 'reflect_aurora_governance_persistence_gateway_drivesync',
                                                             'origin_chain': [],
                                                             'representation_kind': 'legacy_surface_compatibility_alias',
                                                             'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_drivesync_status': {'constraints': ['boundary'],
                                                                    'effect_modes': ['interface_boundary_change'],
                                                                    'effect_phrases': ['legacy '
                                                                                       'evolved-surface '
                                                                                       'binding '
                                                                                       'preserved '
                                                                                       'across '
                                                                                       'promotion'],
                                                                    'kind': 'compatibility_alias',
                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_drivesync_status',
                                                                    'origin_chain': [],
                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_drivesync_stop': {'constraints': ['boundary'],
                                                                  'effect_modes': ['interface_boundary_change'],
                                                                  'effect_phrases': ['legacy '
                                                                                     'evolved-surface '
                                                                                     'binding '
                                                                                     'preserved '
                                                                                     'across '
                                                                                     'promotion'],
                                                                  'kind': 'compatibility_alias',
                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                  'op_id': 'reflect_aurora_governance_persistence_gateway_drivesync_stop',
                                                                  'origin_chain': [],
                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                  'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_drivesync_switch_message': {'constraints': ['boundary'],
                                                                            'effect_modes': ['interface_boundary_change'],
                                                                            'effect_phrases': ['legacy '
                                                                                               'evolved-surface '
                                                                                               'binding '
                                                                                               'preserved '
                                                                                               'across '
                                                                                               'promotion'],
                                                                            'kind': 'compatibility_alias',
                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                            'op_id': 'reflect_aurora_governance_persistence_gateway_drivesync_switch_message',
                                                                            'origin_chain': [],
                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                            'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_gatewayresponse': {'constraints': ['boundary'],
                                                                   'effect_modes': ['interface_boundary_change'],
                                                                   'effect_phrases': ['legacy '
                                                                                      'evolved-surface '
                                                                                      'binding '
                                                                                      'preserved '
                                                                                      'across '
                                                                                      'promotion'],
                                                                   'kind': 'compatibility_alias',
                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                   'op_id': 'reflect_aurora_governance_persistence_gateway_gatewayresponse',
                                                                   'origin_chain': [],
                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                   'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_gatewayverdict': {'constraints': ['boundary'],
                                                                  'effect_modes': ['interface_boundary_change'],
                                                                  'effect_phrases': ['legacy '
                                                                                     'evolved-surface '
                                                                                     'binding '
                                                                                     'preserved '
                                                                                     'across '
                                                                                     'promotion'],
                                                                  'kind': 'compatibility_alias',
                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                  'op_id': 'reflect_aurora_governance_persistence_gateway_gatewayverdict',
                                                                  'origin_chain': [],
                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                  'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw': {'constraints': ['boundary'],
                                                                            'effect_modes': ['interface_boundary_change'],
                                                                            'effect_phrases': ['legacy '
                                                                                               'evolved-surface '
                                                                                               'binding '
                                                                                               'preserved '
                                                                                               'across '
                                                                                               'promotion'],
                                                                            'kind': 'compatibility_alias',
                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                            'op_id': 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw',
                                                                            'origin_chain': [],
                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                            'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_compute_tension': {'constraints': ['boundary'],
                                                                                            'effect_modes': ['interface_boundary_change'],
                                                                                            'effect_phrases': ['legacy '
                                                                                                               'evolved-surface '
                                                                                                               'binding '
                                                                                                               'preserved '
                                                                                                               'across '
                                                                                                               'promotion'],
                                                                                            'kind': 'compatibility_alias',
                                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                            'op_id': 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_compute_tension',
                                                                                            'origin_chain': [],
                                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                            'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_init': {'constraints': ['boundary'],
                                                                                 'effect_modes': ['interface_boundary_change'],
                                                                                 'effect_phrases': ['legacy '
                                                                                                    'evolved-surface '
                                                                                                    'binding '
                                                                                                    'preserved '
                                                                                                    'across '
                                                                                                    'promotion'],
                                                                                 'kind': 'compatibility_alias',
                                                                                 'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                 'op_id': 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_init',
                                                                                 'origin_chain': [],
                                                                                 'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                 'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_shift_toward_stable': {'constraints': ['boundary'],
                                                                                                'effect_modes': ['interface_boundary_change'],
                                                                                                'effect_phrases': ['legacy '
                                                                                                                   'evolved-surface '
                                                                                                                   'binding '
                                                                                                                   'preserved '
                                                                                                                   'across '
                                                                                                                   'promotion'],
                                                                                                'kind': 'compatibility_alias',
                                                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                                'op_id': 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_shift_toward_stable',
                                                                                                'origin_chain': [],
                                                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                                'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationaltension': {'constraints': ['boundary'],
                                                                       'effect_modes': ['interface_boundary_change'],
                                                                       'effect_phrases': ['legacy '
                                                                                          'evolved-surface '
                                                                                          'binding '
                                                                                          'preserved '
                                                                                          'across '
                                                                                          'promotion'],
                                                                       'kind': 'compatibility_alias',
                                                                       'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                       'op_id': 'reflect_aurora_governance_persistence_gateway_generationaltension',
                                                                       'origin_chain': [],
                                                                       'representation_kind': 'legacy_surface_compatibility_alias',
                                                                       'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationaltension_total': {'constraints': ['boundary'],
                                                                             'effect_modes': ['interface_boundary_change'],
                                                                             'effect_phrases': ['legacy '
                                                                                                'evolved-surface '
                                                                                                'binding '
                                                                                                'preserved '
                                                                                                'across '
                                                                                                'promotion'],
                                                                             'kind': 'compatibility_alias',
                                                                             'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                             'op_id': 'reflect_aurora_governance_persistence_gateway_generationaltension_total',
                                                                             'origin_chain': [],
                                                                             'representation_kind': 'legacy_surface_compatibility_alias',
                                                                             'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_generationrole': {'constraints': ['boundary'],
                                                                  'effect_modes': ['interface_boundary_change'],
                                                                  'effect_phrases': ['legacy '
                                                                                     'evolved-surface '
                                                                                     'binding '
                                                                                     'preserved '
                                                                                     'across '
                                                                                     'promotion'],
                                                                  'kind': 'compatibility_alias',
                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                  'op_id': 'reflect_aurora_governance_persistence_gateway_generationrole',
                                                                  'origin_chain': [],
                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                  'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governanceengine': {'constraints': ['boundary'],
                                                                    'effect_modes': ['interface_boundary_change'],
                                                                    'effect_phrases': ['legacy '
                                                                                       'evolved-surface '
                                                                                       'binding '
                                                                                       'preserved '
                                                                                       'across '
                                                                                       'promotion'],
                                                                    'kind': 'compatibility_alias',
                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_governanceengine',
                                                                    'origin_chain': [],
                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governanceengine_promote': {'constraints': ['boundary'],
                                                                            'effect_modes': ['interface_boundary_change'],
                                                                            'effect_phrases': ['legacy '
                                                                                               'evolved-surface '
                                                                                               'binding '
                                                                                               'preserved '
                                                                                               'across '
                                                                                               'promotion'],
                                                                            'kind': 'compatibility_alias',
                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                            'op_id': 'reflect_aurora_governance_persistence_gateway_governanceengine_promote',
                                                                            'origin_chain': [],
                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                            'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governanceengine_resolve_conflict': {'constraints': ['boundary'],
                                                                                     'effect_modes': ['interface_boundary_change'],
                                                                                     'effect_phrases': ['legacy '
                                                                                                        'evolved-surface '
                                                                                                        'binding '
                                                                                                        'preserved '
                                                                                                        'across '
                                                                                                        'promotion'],
                                                                                     'kind': 'compatibility_alias',
                                                                                     'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                     'op_id': 'reflect_aurora_governance_persistence_gateway_governanceengine_resolve_conflict',
                                                                                     'origin_chain': [],
                                                                                     'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                     'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governancepersistencegateway_load_state': {'constraints': ['boundary'],
                                                                                           'effect_modes': ['interface_boundary_change'],
                                                                                           'effect_phrases': ['legacy '
                                                                                                              'evolved-surface '
                                                                                                              'binding '
                                                                                                              'preserved '
                                                                                                              'across '
                                                                                                              'promotion'],
                                                                                           'kind': 'compatibility_alias',
                                                                                           'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                           'op_id': 'reflect_aurora_governance_persistence_gateway_governancepersistencegateway_load_state',
                                                                                           'origin_chain': [],
                                                                                           'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                           'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governanceviolation': {'constraints': ['boundary'],
                                                                       'effect_modes': ['interface_boundary_change'],
                                                                       'effect_phrases': ['legacy '
                                                                                          'evolved-surface '
                                                                                          'binding '
                                                                                          'preserved '
                                                                                          'across '
                                                                                          'promotion'],
                                                                       'kind': 'compatibility_alias',
                                                                       'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                       'op_id': 'reflect_aurora_governance_persistence_gateway_governanceviolation',
                                                                       'origin_chain': [],
                                                                       'representation_kind': 'legacy_surface_compatibility_alias',
                                                                       'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governedcoordinate': {'constraints': ['boundary'],
                                                                      'effect_modes': ['interface_boundary_change'],
                                                                      'effect_phrases': ['legacy '
                                                                                         'evolved-surface '
                                                                                         'binding '
                                                                                         'preserved '
                                                                                         'across '
                                                                                         'promotion'],
                                                                      'kind': 'compatibility_alias',
                                                                      'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                      'op_id': 'reflect_aurora_governance_persistence_gateway_governedcoordinate',
                                                                      'origin_chain': [],
                                                                      'representation_kind': 'legacy_surface_compatibility_alias',
                                                                      'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governedcoordinate_agency_weight': {'constraints': ['boundary'],
                                                                                    'effect_modes': ['interface_boundary_change'],
                                                                                    'effect_phrases': ['legacy '
                                                                                                       'evolved-surface '
                                                                                                       'binding '
                                                                                                       'preserved '
                                                                                                       'across '
                                                                                                       'promotion'],
                                                                                    'kind': 'compatibility_alias',
                                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_governedcoordinate_agency_weight',
                                                                                    'origin_chain': [],
                                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governedcoordinate_boundary_weight': {'constraints': ['boundary'],
                                                                                      'effect_modes': ['interface_boundary_change'],
                                                                                      'effect_phrases': ['legacy '
                                                                                                         'evolved-surface '
                                                                                                         'binding '
                                                                                                         'preserved '
                                                                                                         'across '
                                                                                                         'promotion'],
                                                                                      'kind': 'compatibility_alias',
                                                                                      'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                      'op_id': 'reflect_aurora_governance_persistence_gateway_governedcoordinate_boundary_weight',
                                                                                      'origin_chain': [],
                                                                                      'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                      'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_governednode': {'constraints': ['boundary'],
                                                                'effect_modes': ['interface_boundary_change'],
                                                                'effect_phrases': ['legacy '
                                                                                   'evolved-surface '
                                                                                   'binding '
                                                                                   'preserved '
                                                                                   'across '
                                                                                   'promotion'],
                                                                'kind': 'compatibility_alias',
                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                'op_id': 'reflect_aurora_governance_persistence_gateway_governednode',
                                                                'origin_chain': [],
                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_nspacegateway_express': {'constraints': ['boundary'],
                                                                         'effect_modes': ['interface_boundary_change'],
                                                                         'effect_phrases': ['legacy '
                                                                                            'evolved-surface '
                                                                                            'binding '
                                                                                            'preserved '
                                                                                            'across '
                                                                                            'promotion'],
                                                                         'kind': 'compatibility_alias',
                                                                         'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                         'op_id': 'reflect_aurora_governance_persistence_gateway_nspacegateway_express',
                                                                         'origin_chain': [],
                                                                         'representation_kind': 'legacy_surface_compatibility_alias',
                                                                         'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_nspacegateway_needs_articulation_bridge': {'constraints': ['boundary'],
                                                                                           'effect_modes': ['interface_boundary_change'],
                                                                                           'effect_phrases': ['legacy '
                                                                                                              'evolved-surface '
                                                                                                              'binding '
                                                                                                              'preserved '
                                                                                                              'across '
                                                                                                              'promotion'],
                                                                                           'kind': 'compatibility_alias',
                                                                                           'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                           'op_id': 'reflect_aurora_governance_persistence_gateway_nspacegateway_needs_articulation_bridge',
                                                                                           'origin_chain': [],
                                                                                           'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                           'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_nspacegateway_receive': {'constraints': ['boundary'],
                                                                         'effect_modes': ['interface_boundary_change'],
                                                                         'effect_phrases': ['legacy '
                                                                                            'evolved-surface '
                                                                                            'binding '
                                                                                            'preserved '
                                                                                            'across '
                                                                                            'promotion'],
                                                                         'kind': 'compatibility_alias',
                                                                         'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                         'op_id': 'reflect_aurora_governance_persistence_gateway_nspacegateway_receive',
                                                                         'origin_chain': [],
                                                                         'representation_kind': 'legacy_surface_compatibility_alias',
                                                                         'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_proactivetrigger': {'constraints': ['boundary'],
                                                                    'effect_modes': ['interface_boundary_change'],
                                                                    'effect_phrases': ['legacy '
                                                                                       'evolved-surface '
                                                                                       'binding '
                                                                                       'preserved '
                                                                                       'across '
                                                                                       'promotion'],
                                                                    'kind': 'compatibility_alias',
                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_proactivetrigger',
                                                                    'origin_chain': [],
                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_ratelimitedsearch': {'constraints': ['boundary'],
                                                                     'effect_modes': ['interface_boundary_change'],
                                                                     'effect_phrases': ['legacy '
                                                                                        'evolved-surface '
                                                                                        'binding '
                                                                                        'preserved '
                                                                                        'across '
                                                                                        'promotion'],
                                                                     'kind': 'compatibility_alias',
                                                                     'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                     'op_id': 'reflect_aurora_governance_persistence_gateway_ratelimitedsearch',
                                                                     'origin_chain': [],
                                                                     'representation_kind': 'legacy_surface_compatibility_alias',
                                                                     'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface': {'constraints': ['boundary'],
                                                                   'effect_modes': ['interface_boundary_change'],
                                                                   'effect_phrases': ['legacy '
                                                                                      'evolved-surface '
                                                                                      'binding '
                                                                                      'preserved '
                                                                                      'across '
                                                                                      'promotion'],
                                                                   'kind': 'compatibility_alias',
                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                   'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface',
                                                                   'origin_chain': [],
                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                   'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_check_newer_remote': {'constraints': ['boundary'],
                                                                                      'effect_modes': ['interface_boundary_change'],
                                                                                      'effect_phrases': ['legacy '
                                                                                                         'evolved-surface '
                                                                                                         'binding '
                                                                                                         'preserved '
                                                                                                         'across '
                                                                                                         'promotion'],
                                                                                      'kind': 'compatibility_alias',
                                                                                      'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                      'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_check_newer_remote',
                                                                                      'origin_chain': [],
                                                                                      'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                      'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_find_rclone': {'constraints': ['boundary'],
                                                                               'effect_modes': ['interface_boundary_change'],
                                                                               'effect_phrases': ['legacy '
                                                                                                  'evolved-surface '
                                                                                                  'binding '
                                                                                                  'preserved '
                                                                                                  'across '
                                                                                                  'promotion'],
                                                                               'kind': 'compatibility_alias',
                                                                               'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                               'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_find_rclone',
                                                                               'origin_chain': [],
                                                                               'representation_kind': 'legacy_surface_compatibility_alias',
                                                                               'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_init': {'constraints': ['boundary'],
                                                                        'effect_modes': ['interface_boundary_change'],
                                                                        'effect_phrases': ['legacy '
                                                                                           'evolved-surface '
                                                                                           'binding '
                                                                                           'preserved '
                                                                                           'across '
                                                                                           'promotion'],
                                                                        'kind': 'compatibility_alias',
                                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                        'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_init',
                                                                        'origin_chain': [],
                                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                                        'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_is_available': {'constraints': ['boundary'],
                                                                                'effect_modes': ['interface_boundary_change'],
                                                                                'effect_phrases': ['legacy '
                                                                                                   'evolved-surface '
                                                                                                   'binding '
                                                                                                   'preserved '
                                                                                                   'across '
                                                                                                   'promotion'],
                                                                                'kind': 'compatibility_alias',
                                                                                'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_is_available',
                                                                                'origin_chain': [],
                                                                                'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_remote_full': {'constraints': ['boundary'],
                                                                               'effect_modes': ['interface_boundary_change'],
                                                                               'effect_phrases': ['legacy '
                                                                                                  'evolved-surface '
                                                                                                  'binding '
                                                                                                  'preserved '
                                                                                                  'across '
                                                                                                  'promotion'],
                                                                               'kind': 'compatibility_alias',
                                                                               'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                               'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_remote_full',
                                                                               'origin_chain': [],
                                                                               'representation_kind': 'legacy_surface_compatibility_alias',
                                                                               'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_run_sync': {'constraints': ['boundary'],
                                                                            'effect_modes': ['interface_boundary_change'],
                                                                            'effect_phrases': ['legacy '
                                                                                               'evolved-surface '
                                                                                               'binding '
                                                                                               'preserved '
                                                                                               'across '
                                                                                               'promotion'],
                                                                            'kind': 'compatibility_alias',
                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                            'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_run_sync',
                                                                            'origin_chain': [],
                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                            'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_down': {'constraints': ['boundary'],
                                                                             'effect_modes': ['interface_boundary_change'],
                                                                             'effect_phrases': ['legacy '
                                                                                                'evolved-surface '
                                                                                                'binding '
                                                                                                'preserved '
                                                                                                'across '
                                                                                                'promotion'],
                                                                             'kind': 'compatibility_alias',
                                                                             'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                             'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_down',
                                                                             'origin_chain': [],
                                                                             'representation_kind': 'legacy_surface_compatibility_alias',
                                                                             'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_up': {'constraints': ['boundary'],
                                                                           'effect_modes': ['interface_boundary_change'],
                                                                           'effect_phrases': ['legacy '
                                                                                              'evolved-surface '
                                                                                              'binding '
                                                                                              'preserved '
                                                                                              'across '
                                                                                              'promotion'],
                                                                           'kind': 'compatibility_alias',
                                                                           'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                           'op_id': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_up',
                                                                           'origin_chain': [],
                                                                           'representation_kind': 'legacy_surface_compatibility_alias',
                                                                           'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_streamtype': {'constraints': ['boundary'],
                                                              'effect_modes': ['interface_boundary_change'],
                                                              'effect_phrases': ['legacy '
                                                                                 'evolved-surface '
                                                                                 'binding '
                                                                                 'preserved across '
                                                                                 'promotion'],
                                                              'kind': 'compatibility_alias',
                                                              'module': 'aurora_internal.aurora_evolved_surfaces',
                                                              'op_id': 'reflect_aurora_governance_persistence_gateway_streamtype',
                                                              'origin_chain': [],
                                                              'representation_kind': 'legacy_surface_compatibility_alias',
                                                              'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_studyscheduler': {'constraints': ['boundary'],
                                                                  'effect_modes': ['interface_boundary_change'],
                                                                  'effect_phrases': ['legacy '
                                                                                     'evolved-surface '
                                                                                     'binding '
                                                                                     'preserved '
                                                                                     'across '
                                                                                     'promotion'],
                                                                  'kind': 'compatibility_alias',
                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                  'op_id': 'reflect_aurora_governance_persistence_gateway_studyscheduler',
                                                                  'origin_chain': [],
                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                  'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_validationresult': {'constraints': ['boundary'],
                                                                    'effect_modes': ['interface_boundary_change'],
                                                                    'effect_phrases': ['legacy '
                                                                                       'evolved-surface '
                                                                                       'binding '
                                                                                       'preserved '
                                                                                       'across '
                                                                                       'promotion'],
                                                                    'kind': 'compatibility_alias',
                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                    'op_id': 'reflect_aurora_governance_persistence_gateway_validationresult',
                                                                    'origin_chain': [],
                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                    'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_votingauthority': {'constraints': ['boundary'],
                                                                   'effect_modes': ['interface_boundary_change'],
                                                                   'effect_phrases': ['legacy '
                                                                                      'evolved-surface '
                                                                                      'binding '
                                                                                      'preserved '
                                                                                      'across '
                                                                                      'promotion'],
                                                                   'kind': 'compatibility_alias',
                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                   'op_id': 'reflect_aurora_governance_persistence_gateway_votingauthority',
                                                                   'origin_chain': [],
                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                   'surface_score': 0.0},
 'reflect_aurora_governance_persistence_gateway_writeresult': {'constraints': ['boundary'],
                                                               'effect_modes': ['interface_boundary_change'],
                                                               'effect_phrases': ['legacy '
                                                                                  'evolved-surface '
                                                                                  'binding '
                                                                                  'preserved '
                                                                                  'across '
                                                                                  'promotion'],
                                                               'kind': 'compatibility_alias',
                                                               'module': 'aurora_internal.aurora_evolved_surfaces',
                                                               'op_id': 'reflect_aurora_governance_persistence_gateway_writeresult',
                                                               'origin_chain': [],
                                                               'representation_kind': 'legacy_surface_compatibility_alias',
                                                               'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_cross_dim_amplifier': {'constraints': ['boundary'],
                                                                        'effect_modes': ['interface_boundary_change'],
                                                                        'effect_phrases': ['legacy '
                                                                                           'evolved-surface '
                                                                                           'binding '
                                                                                           'preserved '
                                                                                           'across '
                                                                                           'promotion'],
                                                                        'kind': 'compatibility_alias',
                                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                        'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_cross_dim_amplifier',
                                                                        'origin_chain': [],
                                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                                        'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_derive_pressure_weights': {'constraints': ['boundary'],
                                                                            'effect_modes': ['interface_boundary_change'],
                                                                            'effect_phrases': ['legacy '
                                                                                               'evolved-surface '
                                                                                               'binding '
                                                                                               'preserved '
                                                                                               'across '
                                                                                               'promotion'],
                                                                            'kind': 'compatibility_alias',
                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                            'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_derive_pressure_weights',
                                                                            'origin_chain': [],
                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                            'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_dominant_pressure_axis': {'constraints': ['boundary'],
                                                                           'effect_modes': ['interface_boundary_change'],
                                                                           'effect_phrases': ['legacy '
                                                                                              'evolved-surface '
                                                                                              'binding '
                                                                                              'preserved '
                                                                                              'across '
                                                                                              'promotion'],
                                                                           'kind': 'compatibility_alias',
                                                                           'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                           'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_dominant_pressure_axis',
                                                                           'origin_chain': [],
                                                                           'representation_kind': 'legacy_surface_compatibility_alias',
                                                                           'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_k_efficiency_ratio': {'constraints': ['boundary'],
                                                                       'effect_modes': ['interface_boundary_change'],
                                                                       'effect_phrases': ['legacy '
                                                                                          'evolved-surface '
                                                                                          'binding '
                                                                                          'preserved '
                                                                                          'across '
                                                                                          'promotion'],
                                                                       'kind': 'compatibility_alias',
                                                                       'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                       'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_k_efficiency_ratio',
                                                                       'origin_chain': [],
                                                                       'representation_kind': 'legacy_surface_compatibility_alias',
                                                                       'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_per_operator_pressure': {'constraints': ['boundary'],
                                                                          'effect_modes': ['interface_boundary_change'],
                                                                          'effect_phrases': ['legacy '
                                                                                             'evolved-surface '
                                                                                             'binding '
                                                                                             'preserved '
                                                                                             'across '
                                                                                             'promotion'],
                                                                          'kind': 'compatibility_alias',
                                                                          'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                          'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_per_operator_pressure',
                                                                          'origin_chain': [],
                                                                          'representation_kind': 'legacy_surface_compatibility_alias',
                                                                          'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_pressure_description': {'constraints': ['boundary'],
                                                                         'effect_modes': ['interface_boundary_change'],
                                                                         'effect_phrases': ['legacy '
                                                                                            'evolved-surface '
                                                                                            'binding '
                                                                                            'preserved '
                                                                                            'across '
                                                                                            'promotion'],
                                                                         'kind': 'compatibility_alias',
                                                                         'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                         'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_pressure_description',
                                                                         'origin_chain': [],
                                                                         'representation_kind': 'legacy_surface_compatibility_alias',
                                                                         'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_reactive_pressure_score': {'constraints': ['boundary'],
                                                                            'effect_modes': ['interface_boundary_change'],
                                                                            'effect_phrases': ['legacy '
                                                                                               'evolved-surface '
                                                                                               'binding '
                                                                                               'preserved '
                                                                                               'across '
                                                                                               'promotion'],
                                                                            'kind': 'compatibility_alias',
                                                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                            'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_reactive_pressure_score',
                                                                            'origin_chain': [],
                                                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                                                            'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_score_for_variant_moral_weight': {'constraints': ['boundary'],
                                                                                   'effect_modes': ['interface_boundary_change'],
                                                                                   'effect_phrases': ['legacy '
                                                                                                      'evolved-surface '
                                                                                                      'binding '
                                                                                                      'preserved '
                                                                                                      'across '
                                                                                                      'promotion'],
                                                                                   'kind': 'compatibility_alias',
                                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                   'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_score_for_variant_moral_weight',
                                                                                   'origin_chain': [],
                                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                   'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_score_from_cost': {'constraints': ['boundary'],
                                                                    'effect_modes': ['interface_boundary_change'],
                                                                    'effect_phrases': ['legacy '
                                                                                       'evolved-surface '
                                                                                       'binding '
                                                                                       'preserved '
                                                                                       'across '
                                                                                       'promotion'],
                                                                    'kind': 'compatibility_alias',
                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                    'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_score_from_cost',
                                                                    'origin_chain': [],
                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                    'surface_score': 0.0},
 'reflect_aurora_internal_aurora_cost_diff_score_verify_cost_diff_score': {'constraints': ['boundary'],
                                                                           'effect_modes': ['interface_boundary_change'],
                                                                           'effect_phrases': ['legacy '
                                                                                              'evolved-surface '
                                                                                              'binding '
                                                                                              'preserved '
                                                                                              'across '
                                                                                              'promotion'],
                                                                           'kind': 'compatibility_alias',
                                                                           'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                           'op_id': 'reflect_aurora_internal_aurora_cost_diff_score_verify_cost_diff_score',
                                                                           'origin_chain': [],
                                                                           'representation_kind': 'legacy_surface_compatibility_alias',
                                                                           'surface_score': 0.0},
 'reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint': {'constraints': ['boundary'],
                                                                        'effect_modes': ['interface_boundary_change'],
                                                                        'effect_phrases': ['legacy '
                                                                                           'evolved-surface '
                                                                                           'binding '
                                                                                           'preserved '
                                                                                           'across '
                                                                                           'promotion'],
                                                                        'kind': 'compatibility_alias',
                                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                        'op_id': 'reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint',
                                                                        'origin_chain': [],
                                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                                        'surface_score': 0.0},
 'reflect_aurora_internal_aurora_entropy_detector_entropysaturationdetector_project_critical_tick': {'constraints': ['boundary'],
                                                                                                     'effect_modes': ['interface_boundary_change'],
                                                                                                     'effect_phrases': ['legacy '
                                                                                                                        'evolved-surface '
                                                                                                                        'binding '
                                                                                                                        'preserved '
                                                                                                                        'across '
                                                                                                                        'promotion'],
                                                                                                     'kind': 'compatibility_alias',
                                                                                                     'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                                     'op_id': 'reflect_aurora_internal_aurora_entropy_detector_entropysaturationdetector_project_critical_tick',
                                                                                                     'origin_chain': [],
                                                                                                     'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                                     'surface_score': 0.0},
 'reflect_aurora_internal_aurora_entropy_detector_saturationsignal_urgency_ticks': {'constraints': ['boundary'],
                                                                                    'effect_modes': ['interface_boundary_change'],
                                                                                    'effect_phrases': ['legacy '
                                                                                                       'evolved-surface '
                                                                                                       'binding '
                                                                                                       'preserved '
                                                                                                       'across '
                                                                                                       'promotion'],
                                                                                    'kind': 'compatibility_alias',
                                                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                    'op_id': 'reflect_aurora_internal_aurora_entropy_detector_saturationsignal_urgency_ticks',
                                                                                    'origin_chain': [],
                                                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                    'surface_score': 0.0},
 'reflect_aurora_internal_aurora_intake_metabolism_intakerecord_ticks_remaining': {'constraints': ['boundary'],
                                                                                   'effect_modes': ['interface_boundary_change'],
                                                                                   'effect_phrases': ['legacy '
                                                                                                      'evolved-surface '
                                                                                                      'binding '
                                                                                                      'preserved '
                                                                                                      'across '
                                                                                                      'promotion'],
                                                                                   'kind': 'compatibility_alias',
                                                                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                   'op_id': 'reflect_aurora_internal_aurora_intake_metabolism_intakerecord_ticks_remaining',
                                                                                   'origin_chain': [],
                                                                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                   'surface_score': 0.0},
 'reflect_aurora_internal_aurora_leverage_scalar_phasenudge_apply_to': {'constraints': ['boundary'],
                                                                        'effect_modes': ['interface_boundary_change'],
                                                                        'effect_phrases': ['legacy '
                                                                                           'evolved-surface '
                                                                                           'binding '
                                                                                           'preserved '
                                                                                           'across '
                                                                                           'promotion'],
                                                                        'kind': 'compatibility_alias',
                                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                        'op_id': 'reflect_aurora_internal_aurora_leverage_scalar_phasenudge_apply_to',
                                                                        'origin_chain': [],
                                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                                        'surface_score': 0.0},
 'reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_init': {'constraints': ['boundary'],
                                                                              'effect_modes': ['interface_boundary_change'],
                                                                              'effect_phrases': ['legacy '
                                                                                                 'evolved-surface '
                                                                                                 'binding '
                                                                                                 'preserved '
                                                                                                 'across '
                                                                                                 'promotion'],
                                                                              'kind': 'compatibility_alias',
                                                                              'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                              'op_id': 'reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_init',
                                                                              'origin_chain': [],
                                                                              'representation_kind': 'legacy_surface_compatibility_alias',
                                                                              'surface_score': 0.0},
 'reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_summary': {'constraints': ['boundary'],
                                                                                 'effect_modes': ['interface_boundary_change'],
                                                                                 'effect_phrases': ['legacy '
                                                                                                    'evolved-surface '
                                                                                                    'binding '
                                                                                                    'preserved '
                                                                                                    'across '
                                                                                                    'promotion'],
                                                                                 'kind': 'compatibility_alias',
                                                                                 'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                 'op_id': 'reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_summary',
                                                                                 'origin_chain': [],
                                                                                 'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                 'surface_score': 0.0},
 'reflect_aurora_internal_aurora_primitive_extractor_primitiveextractor_chains': {'constraints': ['boundary'],
                                                                                  'effect_modes': ['interface_boundary_change'],
                                                                                  'effect_phrases': ['legacy '
                                                                                                     'evolved-surface '
                                                                                                     'binding '
                                                                                                     'preserved '
                                                                                                     'across '
                                                                                                     'promotion'],
                                                                                  'kind': 'compatibility_alias',
                                                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                  'op_id': 'reflect_aurora_internal_aurora_primitive_extractor_primitiveextractor_chains',
                                                                                  'origin_chain': [],
                                                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                  'surface_score': 0.0},
 'reflect_aurora_internal_constraint_genealogy_augment_ability_profile_with_origin': {'constraints': ['boundary'],
                                                                                      'effect_modes': ['interface_boundary_change'],
                                                                                      'effect_phrases': ['legacy '
                                                                                                         'evolved-surface '
                                                                                                         'binding '
                                                                                                         'preserved '
                                                                                                         'across '
                                                                                                         'promotion'],
                                                                                      'kind': 'compatibility_alias',
                                                                                      'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                                      'op_id': 'reflect_aurora_internal_constraint_genealogy_augment_ability_profile_with_origin',
                                                                                      'origin_chain': [],
                                                                                      'representation_kind': 'legacy_surface_compatibility_alias',
                                                                                      'surface_score': 0.0},
 'reflect_aurora_internal_constraint_genealogy_bred_child_generation': {'constraints': ['boundary'],
                                                                        'effect_modes': ['interface_boundary_change'],
                                                                        'effect_phrases': ['legacy '
                                                                                           'evolved-surface '
                                                                                           'binding '
                                                                                           'preserved '
                                                                                           'across '
                                                                                           'promotion'],
                                                                        'kind': 'compatibility_alias',
                                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                                        'op_id': 'reflect_aurora_internal_constraint_genealogy_bred_child_generation',
                                                                        'origin_chain': [],
                                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                                        'surface_score': 0.0},
 'reflect_aurora_internal_constraint_genealogy_pressurevec': {'constraints': ['boundary'],
                                                              'effect_modes': ['interface_boundary_change'],
                                                              'effect_phrases': ['legacy '
                                                                                 'evolved-surface '
                                                                                 'binding '
                                                                                 'preserved across '
                                                                                 'promotion'],
                                                              'kind': 'compatibility_alias',
                                                              'module': 'aurora_internal.aurora_evolved_surfaces',
                                                              'op_id': 'reflect_aurora_internal_constraint_genealogy_pressurevec',
                                                              'origin_chain': [],
                                                              'representation_kind': 'legacy_surface_compatibility_alias',
                                                              'surface_score': 0.0},
 'reflect_aurora_internal_constraint_genealogy_reliefrecord': {'constraints': ['boundary'],
                                                               'effect_modes': ['interface_boundary_change'],
                                                               'effect_phrases': ['legacy '
                                                                                  'evolved-surface '
                                                                                  'binding '
                                                                                  'preserved '
                                                                                  'across '
                                                                                  'promotion'],
                                                               'kind': 'compatibility_alias',
                                                               'module': 'aurora_internal.aurora_evolved_surfaces',
                                                               'op_id': 'reflect_aurora_internal_constraint_genealogy_reliefrecord',
                                                               'origin_chain': [],
                                                               'representation_kind': 'legacy_surface_compatibility_alias',
                                                               'surface_score': 0.0},
 'reflect_aurora_simulation_engine_avatarpersonality': {'constraints': ['boundary'],
                                                        'effect_modes': ['interface_boundary_change'],
                                                        'effect_phrases': ['legacy evolved-surface '
                                                                           'binding preserved '
                                                                           'across promotion'],
                                                        'kind': 'compatibility_alias',
                                                        'module': 'aurora_internal.aurora_evolved_surfaces',
                                                        'op_id': 'reflect_aurora_simulation_engine_avatarpersonality',
                                                        'origin_chain': [],
                                                        'representation_kind': 'legacy_surface_compatibility_alias',
                                                        'surface_score': 0.0},
 'reflect_aurora_simulation_engine_clamp': {'constraints': ['boundary'],
                                            'effect_modes': ['interface_boundary_change'],
                                            'effect_phrases': ['legacy evolved-surface binding '
                                                               'preserved across promotion'],
                                            'kind': 'compatibility_alias',
                                            'module': 'aurora_internal.aurora_evolved_surfaces',
                                            'op_id': 'reflect_aurora_simulation_engine_clamp',
                                            'origin_chain': [],
                                            'representation_kind': 'legacy_surface_compatibility_alias',
                                            'surface_score': 0.0},
 'reflect_aurora_simulation_engine_conceptualresponse': {'constraints': ['boundary'],
                                                         'effect_modes': ['interface_boundary_change'],
                                                         'effect_phrases': ['legacy '
                                                                            'evolved-surface '
                                                                            'binding preserved '
                                                                            'across promotion'],
                                                         'kind': 'compatibility_alias',
                                                         'module': 'aurora_internal.aurora_evolved_surfaces',
                                                         'op_id': 'reflect_aurora_simulation_engine_conceptualresponse',
                                                         'origin_chain': [],
                                                         'representation_kind': 'legacy_surface_compatibility_alias',
                                                         'surface_score': 0.0},
 'reflect_aurora_simulation_engine_consciouslearner': {'constraints': ['boundary'],
                                                       'effect_modes': ['interface_boundary_change'],
                                                       'effect_phrases': ['legacy evolved-surface '
                                                                          'binding preserved '
                                                                          'across promotion'],
                                                       'kind': 'compatibility_alias',
                                                       'module': 'aurora_internal.aurora_evolved_surfaces',
                                                       'op_id': 'reflect_aurora_simulation_engine_consciouslearner',
                                                       'origin_chain': [],
                                                       'representation_kind': 'legacy_surface_compatibility_alias',
                                                       'surface_score': 0.0},
 'reflect_aurora_simulation_engine_generate_id': {'constraints': ['boundary'],
                                                  'effect_modes': ['interface_boundary_change'],
                                                  'effect_phrases': ['legacy evolved-surface '
                                                                     'binding preserved across '
                                                                     'promotion'],
                                                  'kind': 'compatibility_alias',
                                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                                  'op_id': 'reflect_aurora_simulation_engine_generate_id',
                                                  'origin_chain': [],
                                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                                  'surface_score': 0.0},
 'reflect_aurora_simulation_engine_stabilitystate': {'constraints': ['boundary'],
                                                     'effect_modes': ['interface_boundary_change'],
                                                     'effect_phrases': ['legacy evolved-surface '
                                                                        'binding preserved across '
                                                                        'promotion'],
                                                     'kind': 'compatibility_alias',
                                                     'module': 'aurora_internal.aurora_evolved_surfaces',
                                                     'op_id': 'reflect_aurora_simulation_engine_stabilitystate',
                                                     'origin_chain': [],
                                                     'representation_kind': 'legacy_surface_compatibility_alias',
                                                     'surface_score': 0.0},
 'reflect_aurora_simulation_engine_timedilationgovernor': {'constraints': ['boundary'],
                                                           'effect_modes': ['interface_boundary_change'],
                                                           'effect_phrases': ['legacy '
                                                                              'evolved-surface '
                                                                              'binding preserved '
                                                                              'across promotion'],
                                                           'kind': 'compatibility_alias',
                                                           'module': 'aurora_internal.aurora_evolved_surfaces',
                                                           'op_id': 'reflect_aurora_simulation_engine_timedilationgovernor',
                                                           'origin_chain': [],
                                                           'representation_kind': 'legacy_surface_compatibility_alias',
                                                           'surface_score': 0.0},
 'reflect_aurora_simulation_engine_verify_layer7': {'constraints': ['boundary'],
                                                    'effect_modes': ['interface_boundary_change'],
                                                    'effect_phrases': ['legacy evolved-surface '
                                                                       'binding preserved across '
                                                                       'promotion'],
                                                    'kind': 'compatibility_alias',
                                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                                    'op_id': 'reflect_aurora_simulation_engine_verify_layer7',
                                                    'origin_chain': [],
                                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                                    'surface_score': 0.0},
 'reflect_run_chain_ability_axes': {'constraints': ['boundary'],
                                    'effect_modes': ['interface_boundary_change'],
                                    'effect_phrases': ['legacy evolved-surface binding preserved '
                                                       'across promotion'],
                                    'kind': 'compatibility_alias',
                                    'module': 'aurora_internal.aurora_evolved_surfaces',
                                    'op_id': 'reflect_run_chain_ability_axes',
                                    'origin_chain': [],
                                    'representation_kind': 'legacy_surface_compatibility_alias',
                                    'surface_score': 0.0},
 'reflect_run_chain_main': {'constraints': ['boundary'],
                            'effect_modes': ['interface_boundary_change'],
                            'effect_phrases': ['legacy evolved-surface binding preserved across '
                                               'promotion'],
                            'kind': 'compatibility_alias',
                            'module': 'aurora_internal.aurora_evolved_surfaces',
                            'op_id': 'reflect_run_chain_main',
                            'origin_chain': [],
                            'representation_kind': 'legacy_surface_compatibility_alias',
                            'surface_score': 0.0},
 'reflect_run_chain_make_run_id': {'constraints': ['boundary'],
                                   'effect_modes': ['interface_boundary_change'],
                                   'effect_phrases': ['legacy evolved-surface binding preserved '
                                                      'across promotion'],
                                   'kind': 'compatibility_alias',
                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                   'op_id': 'reflect_run_chain_make_run_id',
                                   'origin_chain': [],
                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                   'surface_score': 0.0},
 'reflect_run_chain_mode_burn': {'constraints': ['boundary'],
                                 'effect_modes': ['interface_boundary_change'],
                                 'effect_phrases': ['legacy evolved-surface binding preserved '
                                                    'across promotion'],
                                 'kind': 'compatibility_alias',
                                 'module': 'aurora_internal.aurora_evolved_surfaces',
                                 'op_id': 'reflect_run_chain_mode_burn',
                                 'origin_chain': [],
                                 'representation_kind': 'legacy_surface_compatibility_alias',
                                 'surface_score': 0.0},
 'reflect_run_chain_mode_test': {'constraints': ['boundary'],
                                 'effect_modes': ['interface_boundary_change'],
                                 'effect_phrases': ['legacy evolved-surface binding preserved '
                                                    'across promotion'],
                                 'kind': 'compatibility_alias',
                                 'module': 'aurora_internal.aurora_evolved_surfaces',
                                 'op_id': 'reflect_run_chain_mode_test',
                                 'origin_chain': [],
                                 'representation_kind': 'legacy_surface_compatibility_alias',
                                 'surface_score': 0.0},
 'reflect_run_chain_mode_watch': {'constraints': ['boundary'],
                                  'effect_modes': ['interface_boundary_change'],
                                  'effect_phrases': ['legacy evolved-surface binding preserved '
                                                     'across promotion'],
                                  'kind': 'compatibility_alias',
                                  'module': 'aurora_internal.aurora_evolved_surfaces',
                                  'op_id': 'reflect_run_chain_mode_watch',
                                  'origin_chain': [],
                                  'representation_kind': 'legacy_surface_compatibility_alias',
                                  'surface_score': 0.0},
 'reflect_run_chain_print_final': {'constraints': ['boundary'],
                                   'effect_modes': ['interface_boundary_change'],
                                   'effect_phrases': ['legacy evolved-surface binding preserved '
                                                      'across promotion'],
                                   'kind': 'compatibility_alias',
                                   'module': 'aurora_internal.aurora_evolved_surfaces',
                                   'op_id': 'reflect_run_chain_print_final',
                                   'origin_chain': [],
                                   'representation_kind': 'legacy_surface_compatibility_alias',
                                   'surface_score': 0.0}}
_SURFACE_MANIFEST: Dict[str, Any] = {'latent_methods': {}, 'method_count': 105, 'reflection_methods': {}}


class AuroraEvolvedSurfaceEngine:
    def __init__(self, systems: Any = None, state_dir: Optional[str] = None):
        self.systems = systems
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.state_dir = os.path.abspath(state_dir or os.path.join(repo_root, "aurora_state"))
        self._registry = dict(_SURFACE_REGISTRY)
        self._events: List[Dict[str, Any]] = []
        self._surface_state: Dict[str, Any] = {"activations": [], "reflections": []}

    def list_capabilities(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for name in sorted(self._registry.keys()):
            meta = dict(self._registry.get(name, {}) or {})
            out.append({
                "name": name,
                "kind": str(meta.get("kind", "") or ""),
                "constraints": list(meta.get("constraints", []) or []),
                "op_id": str(meta.get("op_id", "") or ""),
                "representation_kind": str(meta.get("representation_kind", "") or ""),
                "surface_score": float(meta.get("surface_score", 0.0) or 0.0),
            })
        return out

    def describe_capability(self, name: str) -> Dict[str, Any]:
        return dict(self._registry.get(str(name), {}) or {})

    def capability_report(self) -> Dict[str, Any]:
        latent = 0
        reflection = 0
        for meta in self._registry.values():
            kind = str((meta or {}).get("kind", "") or "")
            if kind == "latent":
                latent += 1
            elif kind == "reflection":
                reflection += 1
        return {
            "available": bool(self._registry),
            "surface_count": int(len(self._registry)),
            "latent_count": int(latent),
            "reflection_count": int(reflection),
            "recent_events": list(self._events[-10:]),
        }

    def lineage_manifest(self) -> Dict[str, Any]:
        return dict(_SURFACE_MANIFEST)

    def _system_summary(self) -> Dict[str, Any]:
        systems = self.systems
        if systems is None:
            return {"available": False, "active_components": [], "axis_pressure": {}}
        active: List[str] = []
        for name in (
            "contract", "lattice", "dimensional", "perception", "identity", "simulation",
            "chamber", "genealogy", "checkpoint", "aurora", "autonomy", "drive_sync",
        ):
            if getattr(systems, name, None) is not None:
                active.append(name)
        axis_pressure: Dict[str, float] = {}
        chamber = getattr(systems, "chamber", None)
        if chamber is not None:
            try:
                st = chamber.status()
                axis_pressure = {
                    ax: float(v)
                    for ax, v in (st.get("intent_pressure", {}) or {}).items()
                }
            except Exception:
                pass
        return {"available": True, "active_components": active, "axis_pressure": axis_pressure}

    def _resolve_origin(self, meta: Dict[str, Any]) -> Any:
        module_name = str(meta.get("module", "") or "").strip()
        chain = list(meta.get("origin_chain") or meta.get("op_chain") or [])
        if not module_name:
            return None
        try:
            module = importlib.import_module(module_name)
        except Exception:
            return None
        target: Any = module
        for attr in chain:
            if not attr or not hasattr(target, attr):
                return None
            target = getattr(target, attr)
        return target

    def _invoke_origin(self, origin: Any, payload: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        if not callable(origin):
            return {"called": False, "reason": "origin_not_callable"}
        try:
            sig = inspect.signature(origin)
        except Exception:
            sig = None
        try:
            if sig is None:
                if payload is not None:
                    return {"called": True, "result": origin(payload, **kwargs)}
                return {"called": True, "result": origin(**kwargs)}
            params = list(sig.parameters.values())
            accepts_var = any(p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD) for p in params)
            positional = [p for p in params if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            required = [p for p in positional if p.default is inspect._empty]
            if not params:
                return {"called": True, "result": origin()}
            if payload is not None and (accepts_var or positional):
                return {"called": True, "result": origin(payload, **kwargs)}
            if not required:
                return {"called": True, "result": origin(**kwargs)}
        except Exception as exc:
            return {"called": False, "reason": f"origin_error: {exc}"}
        return {"called": False, "reason": "origin_signature_not_satisfied"}

    def _record_event(self, event: Dict[str, Any]) -> None:
        self._events.append(dict(event))
        if len(self._events) > 64:
            self._events = self._events[-64:]

    def _log_pressure_event(self, record: Dict[str, Any]) -> None:
        """Append a compact pressure record to surface_pressure_log.jsonl."""
        try:
            import json as _json
            log_path = os.path.join(self.state_dir, "surface_pressure_log.jsonl")
            entry = {
                "surface":        str(record.get("method", "") or ""),
                "op_id":          str(record.get("op_id", "") or ""),
                "kind":           str(record.get("kind", "") or ""),
                "signature":      str(record.get("signature", "") or ""),
                "expected_axes":  list(record.get("expected_axes", []) or []),
                "effect_modes":   list(record.get("effect_modes", []) or []),
                "effect_phrases": list(record.get("effect_phrases", []) or []),
                "surface_score":  float(record.get("surface_score", 0.0) or 0.0),
                "genealogy_pressure": float(record.get("genealogy_pressure", 0.0) or 0.0),
                "axis_pressure":  dict(record.get("axis_pressure_snapshot", {}) or {}),
                "timestamp":      float(record.get("timestamp", 0.0) or 0.0),
            }
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(_json.dumps(entry) + "\n")
            try:
                if os.path.getsize(log_path) > 32 * 1024 * 1024:
                    with open(log_path, "rb") as _src:
                        _src.seek(-8 * 1024 * 1024, os.SEEK_END)
                        _src.readline()
                        _tail = _src.read()
                    with open(log_path, "wb") as _dst:
                        _dst.write(_tail)
            except Exception:
                pass
        except Exception:
            pass

    def _activation_record(self, method_name: str, meta: Dict[str, Any], payload: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        summary = self._system_summary()
        _CONSTRAINT_AXIS = {"existence": "X", "temporal": "T", "energy": "N", "boundary": "B", "agency": "A"}
        expected_axes = list(dict.fromkeys(
            _CONSTRAINT_AXIS.get(str(c).strip().lower(), "")
            for c in (meta.get("constraints", []) or [])
            if _CONSTRAINT_AXIS.get(str(c).strip().lower())
        ))
        return {
            "method": method_name,
            "kind": str(meta.get("kind", "") or ""),
            "op_id": str(meta.get("op_id", "") or ""),
            "signature": str(meta.get("signature", "") or ""),
            "constraints": list(meta.get("constraints", []) or []),
            "expected_axes": expected_axes,
            "contract_profile": dict(meta.get("contract_profile", {}) or {}),
            "effect_modes": list(meta.get("effect_modes", []) or []),
            "effect_phrases": list(meta.get("effect_phrases", []) or []),
            "surface_score": float(meta.get("surface_score", 0.0) or 0.0),
            "genealogy_pressure": float(meta.get("genealogy_pressure", 0.0) or 0.0),
            "timestamp": float(time.time()),
            "payload_present": payload is not None,
            "kwargs_keys": sorted(kwargs.keys()),
            "system_summary": summary,
            "axis_pressure_snapshot": dict(summary.get("axis_pressure", {}) or {}),
        }

    def _activate_surface(self, method_name: str, meta: Dict[str, Any], payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        record = self._activation_record(method_name, meta, payload, dict(kwargs))
        record["latent_reason"] = str(meta.get("latent_reason", "") or "")
        record["effect_phrases"] = list(meta.get("effect_phrases", []) or [])
        origin = self._resolve_origin(meta)
        invocation = self._invoke_origin(origin, payload, dict(kwargs))
        record["origin"] = {
            "module": str(meta.get("module", "") or ""),
            "op_id": str(meta.get("origin_op_id", "") or ""),
            "resolved": origin is not None,
            **invocation,
        }
        effects = set(str(x) for x in (meta.get("effect_modes", []) or []))
        if "state_schema_change" in effects:
            self._surface_state["last_state_change"] = {"method": method_name, "at": record["timestamp"]}
        if "gateway_surface" in effects or "latent_route_surface" in effects:
            routed = list(self._surface_state.get("routed_packets", []) or [])
            routed.append({"method": method_name, "payload": payload, "at": record["timestamp"]})
            self._surface_state["routed_packets"] = routed[-32:]
        if "lineage_surface" in effects and getattr(self.systems, "genealogy", None) is not None:
            genealogy = getattr(self.systems, "genealogy")
            record["genealogy_state"] = {
                "abilities": int(len(getattr(genealogy, "abilities", {}) or {})),
                "links": int(len(getattr(genealogy, "links", {}) or {})),
            }
        activations = list(self._surface_state.get("activations", []) or [])
        activations.append(record)
        self._surface_state["activations"] = activations[-64:]
        self._record_event({"type": "activation", "method": method_name, "timestamp": record["timestamp"]})
        self._log_pressure_event(record)
        return record

    def _reflect_surface(self, method_name: str, meta: Dict[str, Any], payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        record = self._activation_record(method_name, meta, payload, dict(kwargs))
        origin = self._resolve_origin(meta)
        record["origin"] = {
            "module": str(meta.get("module", "") or ""),
            "op_id": str(meta.get("op_id", "") or ""),
            "resolved": origin is not None,
            "callable": bool(callable(origin)),
        }
        if bool(kwargs.pop("call_origin", False)):
            record["origin_call"] = self._invoke_origin(origin, payload, dict(kwargs))
        reflections = list(self._surface_state.get("reflections", []) or [])
        reflections.append(record)
        self._surface_state["reflections"] = reflections[-64:]
        self._record_event({"type": "reflection", "method": method_name, "timestamp": record["timestamp"]})
        self._log_pressure_event(record)
        return record

    def __getattr__(self, name: str):
        # Fallback for any evolved surface method that was renamed or dropped by a mutation.
        # Prevents AttributeError from crashing callers — degrades gracefully instead.
        if name.startswith('__'):
            raise AttributeError(name)
        # Try partial-name match: find the closest surviving reflect_ method
        _all_methods = [m for m in vars(type(self)) if m.startswith('reflect_')]
        candidates = [m for m in _all_methods if m.startswith(name) or name.startswith(m)]
        if candidates:
            best = max(candidates, key=len)
            return object.__getattribute__(self, best)
        def _unavailable(payload=None, **kwargs):
            return {'available': False, 'reason': f'evolved_surface_method_renamed: {name}',
                    'op_id': name, 'kind': 'reflection'}
        return _unavailable

    def reflect_aurora_consciousness_engine_consciousnessengine_tick(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_consciousness_engine_consciousnessengine_tick', {}) or {})
        return self._reflect_surface('reflect_aurora_consciousness_engine_consciousnessengine_tick', meta, payload=payload, **kwargs)

    def reflect_aurora_dimensional_systems_dimensionalsystems_current_pressure_vec(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_dimensional_systems_dimensionalsystems_current_pressure_vec', {}) or {})
        return self._reflect_surface('reflect_aurora_dimensional_systems_dimensionalsystems_current_pressure_vec', meta, payload=payload, **kwargs)

    def reflect_aurora_dimensional_systems_energyregulatorsystem_tick(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_dimensional_systems_energyregulatorsystem_tick', {}) or {})
        return self._reflect_surface('reflect_aurora_dimensional_systems_energyregulatorsystem_tick', meta, payload=payload, **kwargs)

    def reflect_aurora_dimensional_systems_energyregulatorsystem_update_links_for_facet(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_dimensional_systems_energyregulatorsystem_update_links_for_facet', {}) or {})
        return self._reflect_surface('reflect_aurora_dimensional_systems_energyregulatorsystem_update_links_for_facet', meta, payload=payload, **kwargs)

    def reflect_aurora_dimensional_systems_poolview_inject(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_dimensional_systems_poolview_inject', {}) or {})
        return self._reflect_surface('reflect_aurora_dimensional_systems_poolview_inject', meta, payload=payload, **kwargs)

    def reflect_aurora_expression_perception_sensoryconceptmemory_cluster_and_promote(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_expression_perception_sensoryconceptmemory_cluster_and_promote', {}) or {})
        return self._reflect_surface('reflect_aurora_expression_perception_sensoryconceptmemory_cluster_and_promote', meta, payload=payload, **kwargs)

    def reflect_aurora_expression_perception_visuallinguisticmapper_learn_association(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_expression_perception_visuallinguisticmapper_learn_association', {}) or {})
        return self._reflect_surface('reflect_aurora_expression_perception_visuallinguisticmapper_learn_association', meta, payload=payload, **kwargs)

    def reflect_aurora_expression_perception_webimagedownloader_download_for_concept(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_expression_perception_webimagedownloader_download_for_concept', {}) or {})
        return self._reflect_surface('reflect_aurora_expression_perception_webimagedownloader_download_for_concept', meta, payload=payload, **kwargs)

    def reflect_aurora_expression_perception_webimagedownloader_download_seed_batch(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_expression_perception_webimagedownloader_download_seed_batch', {}) or {})
        return self._reflect_surface('reflect_aurora_expression_perception_webimagedownloader_download_seed_batch', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_actionlog(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_actionlog', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_actionlog', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_actionlog_get_by_type(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_actionlog_get_by_type', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_actionlog_get_by_type', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_actionlog_get_recent(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_actionlog_get_recent', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_actionlog_get_recent', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_actionlog_init(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_actionlog_init', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_actionlog_init', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_actionlog_log(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_actionlog_log', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_actionlog_log', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_atomicwriter_append_jsonl(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_atomicwriter_append_jsonl', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_atomicwriter_append_jsonl', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_aurorastatesnapshot(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_aurorastatesnapshot', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_aurorastatesnapshot', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_autonomousaction(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_autonomousaction', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_autonomousaction', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_autonomyengine_get_recent_actions(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_autonomyengine_get_recent_actions', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_autonomyengine_get_recent_actions', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_autonomyengine_get_status(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_autonomyengine_get_status', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_autonomyengine_get_status', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_autonomyengine_search_files(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_autonomyengine_search_files', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_autonomyengine_search_files', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_checkpointmanager_signal_handler(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_checkpointmanager_signal_handler', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_checkpointmanager_signal_handler', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_corpuscursor(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_corpuscursor', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_corpuscursor', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_dailyquotas(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_dailyquotas', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_dailyquotas', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_dailyquotas_reset_if_new_day(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_dailyquotas_reset_if_new_day', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_dailyquotas_reset_if_new_day', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_dailyquotas_to_dict(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_dailyquotas_to_dict', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_dailyquotas_to_dict', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_deviceawareness(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_deviceawareness', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_deviceawareness', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_devicerecord(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_devicerecord', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_devicerecord', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_drivesync(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_drivesync', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_drivesync', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_drivesync_status(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_drivesync_status', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_drivesync_status', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_drivesync_stop(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_drivesync_stop', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_drivesync_stop', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_drivesync_switch_message(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_drivesync_switch_message', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_drivesync_switch_message', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_gatewayresponse(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_gatewayresponse', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_gatewayresponse', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_gatewayverdict(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_gatewayverdict', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_gatewayverdict', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationalalignmentlaw(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_compute_tension(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_compute_tension', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_compute_tension', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_init(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_init', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_init', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_shift_toward_stable(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_shift_toward_stable', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_shift_toward_stable', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationaltension(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationaltension', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationaltension', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationaltension_total(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationaltension_total', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationaltension_total', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_generationrole(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_generationrole', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_generationrole', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governanceengine(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governanceengine', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governanceengine', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governanceengine_promote(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governanceengine_promote', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governanceengine_promote', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governanceengine_resolve_conflict(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governanceengine_resolve_conflict', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governanceengine_resolve_conflict', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governancepersistencegateway_load_state(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governancepersistencegateway_load_state', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governancepersistencegateway_load_state', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governanceviolation(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governanceviolation', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governanceviolation', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governedcoordinate(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governedcoordinate', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governedcoordinate', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governedcoordinate_agency_weight(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governedcoordinate_agency_weight', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governedcoordinate_agency_weight', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governedcoordinate_boundary_weight(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governedcoordinate_boundary_weight', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governedcoordinate_boundary_weight', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_governednode(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_governednode', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_governednode', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_nspacegateway_express(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_nspacegateway_express', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_nspacegateway_express', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_nspacegateway_needs_articulation_bridge(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_nspacegateway_needs_articulation_bridge', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_nspacegateway_needs_articulation_bridge', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_nspacegateway_receive(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_nspacegateway_receive', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_nspacegateway_receive', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_proactivetrigger(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_proactivetrigger', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_proactivetrigger', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_ratelimitedsearch(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_ratelimitedsearch', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_ratelimitedsearch', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_check_newer_remote(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_check_newer_remote', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_check_newer_remote', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_find_rclone(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_find_rclone', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_find_rclone', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_init(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_init', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_init', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_is_available(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_is_available', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_is_available', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_remote_full(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_remote_full', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_remote_full', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_run_sync(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_run_sync', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_run_sync', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_down(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_down', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_down', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_up(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_up', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_up', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_streamtype(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_streamtype', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_streamtype', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_studyscheduler(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_studyscheduler', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_studyscheduler', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_validationresult(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_validationresult', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_validationresult', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_votingauthority(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_votingauthority', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_votingauthority', meta, payload=payload, **kwargs)

    def reflect_aurora_governance_persistence_gateway_writeresult(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_governance_persistence_gateway_writeresult', {}) or {})
        return self._reflect_surface('reflect_aurora_governance_persistence_gateway_writeresult', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_cross_dim_amplifier(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_cross_dim_amplifier', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_cross_dim_amplifier', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_derive_pressure_weights(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_derive_pressure_weights', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_derive_pressure_weights', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_dominant_pressure_axis(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_dominant_pressure_axis', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_dominant_pressure_axis', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_k_efficiency_ratio(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_k_efficiency_ratio', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_k_efficiency_ratio', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_per_operator_pressure(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_per_operator_pressure', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_per_operator_pressure', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_pressure_description(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_pressure_description', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_pressure_description', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_reactive_pressure_score(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_reactive_pressure_score', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_reactive_pressure_score', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_score_for_variant_moral_weight(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_score_for_variant_moral_weight', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_score_for_variant_moral_weight', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_score_from_cost(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_score_from_cost', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_score_from_cost', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_cost_diff_score_verify_cost_diff_score(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_cost_diff_score_verify_cost_diff_score', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_cost_diff_score_verify_cost_diff_score', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_entropy_detector_entropysaturationdetector_project_critical_tick(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_entropy_detector_entropysaturationdetector_project_critical_tick', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_entropy_detector_entropysaturationdetector_project_critical_tick', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_entropy_detector_saturationsignal_urgency_ticks(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_entropy_detector_saturationsignal_urgency_ticks', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_entropy_detector_saturationsignal_urgency_ticks', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_intake_metabolism_intakerecord_ticks_remaining(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_intake_metabolism_intakerecord_ticks_remaining', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_intake_metabolism_intakerecord_ticks_remaining', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_leverage_scalar_phasenudge_apply_to(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_leverage_scalar_phasenudge_apply_to', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_leverage_scalar_phasenudge_apply_to', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_init(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_init', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_init', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_summary(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_summary', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_summary', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_aurora_primitive_extractor_primitiveextractor_chains(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_aurora_primitive_extractor_primitiveextractor_chains', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_aurora_primitive_extractor_primitiveextractor_chains', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_constraint_genealogy_augment_ability_profile_with_origin(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_constraint_genealogy_augment_ability_profile_with_origin', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_constraint_genealogy_augment_ability_profile_with_origin', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_constraint_genealogy_bred_child_generation(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_constraint_genealogy_bred_child_generation', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_constraint_genealogy_bred_child_generation', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_constraint_genealogy_pressurevec(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_constraint_genealogy_pressurevec', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_constraint_genealogy_pressurevec', meta, payload=payload, **kwargs)

    def reflect_aurora_internal_constraint_genealogy_reliefrecord(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_internal_constraint_genealogy_reliefrecord', {}) or {})
        return self._reflect_surface('reflect_aurora_internal_constraint_genealogy_reliefrecord', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_avatarpersonality(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_avatarpersonality', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_avatarpersonality', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_clamp(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_clamp', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_clamp', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_conceptualresponse(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_conceptualresponse', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_conceptualresponse', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_consciouslearner(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_consciouslearner', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_consciouslearner', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_generate_id(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_generate_id', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_generate_id', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_stabilitystate(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_stabilitystate', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_stabilitystate', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_timedilationgovernor(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_timedilationgovernor', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_timedilationgovernor', meta, payload=payload, **kwargs)

    def reflect_aurora_simulation_engine_verify_layer7(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_aurora_simulation_engine_verify_layer7', {}) or {})
        return self._reflect_surface('reflect_aurora_simulation_engine_verify_layer7', meta, payload=payload, **kwargs)

    def reflect_run_chain_ability_axes(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_ability_axes', {}) or {})
        return self._reflect_surface('reflect_run_chain_ability_axes', meta, payload=payload, **kwargs)

    def reflect_run_chain_main(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_main', {}) or {})
        return self._reflect_surface('reflect_run_chain_main', meta, payload=payload, **kwargs)

    def reflect_run_chain_make_run_id(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_make_run_id', {}) or {})
        return self._reflect_surface('reflect_run_chain_make_run_id', meta, payload=payload, **kwargs)

    def reflect_run_chain_mode_burn(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_mode_burn', {}) or {})
        return self._reflect_surface('reflect_run_chain_mode_burn', meta, payload=payload, **kwargs)

    def reflect_run_chain_mode_test(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_mode_test', {}) or {})
        return self._reflect_surface('reflect_run_chain_mode_test', meta, payload=payload, **kwargs)

    def reflect_run_chain_mode_watch(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_mode_watch', {}) or {})
        return self._reflect_surface('reflect_run_chain_mode_watch', meta, payload=payload, **kwargs)

    def reflect_run_chain_print_final(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        meta = dict(self._registry.get('reflect_run_chain_print_final', {}) or {})
        return self._reflect_surface('reflect_run_chain_print_final', meta, payload=payload, **kwargs)


__all__ = ["AuroraEvolvedSurfaceEngine"]
