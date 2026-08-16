// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Dart mirror of aurora_habitat.py's HabitatEntity/EnvironmentAction/
// EnvironmentConsequence. Plain data classes only -- no rendering, no
// gesture handling, no interpretation of what any field means. Space
// and Self both build on these same classes (spec section 4: one
// shared substrate, not two independent implementations).
import 'dart:convert';

const List<String> kHabitatTerritories = ['space', 'self'];
const List<String> kHabitatOwners = ['aurora', 'human', 'shared'];
const List<String> kHabitatEntityTypes = ['shape', 'text', 'mark_path', 'connector', 'group'];
const List<String> kHabitatOperations = [
  'create', 'duplicate', 'delete', 'restore',
  'move', 'resize', 'rotate', 'recolor',
  'connect', 'disconnect', 'group', 'ungroup',
  'transfer', 'grant_permission', 'revoke_permission',
];

class HabitatEntity {
  final String id;
  final String entityType;
  final String creator;
  final String owner;
  final String territory;
  final double createdAt;
  final double modifiedAt;
  final List<double> position;   // [x, y] normalized 0..1
  final List<double> dimensions; // [width, height] normalized 0..1
  final double orientation;      // degrees
  final int layer;
  final Map<String, dynamic> visualProperties;
  final Map<String, dynamic> temporalProperties;
  final List<String> links;
  final String? groupMembership;
  final Map<String, dynamic> content;
  final Map<String, dynamic> interactionPermissions;
  final Map<String, dynamic> lineage;
  final bool deleted;
  final int revisionCount;

  const HabitatEntity({
    required this.id,
    required this.entityType,
    required this.creator,
    required this.owner,
    required this.territory,
    required this.createdAt,
    required this.modifiedAt,
    required this.position,
    required this.dimensions,
    required this.orientation,
    required this.layer,
    required this.visualProperties,
    required this.temporalProperties,
    required this.links,
    required this.groupMembership,
    required this.content,
    required this.interactionPermissions,
    required this.lineage,
    required this.deleted,
    required this.revisionCount,
  });

  factory HabitatEntity.fromJson(Map<String, dynamic> j) {
    List<double> _pair(dynamic v, List<double> fallback) {
      if (v is List && v.length >= 2) {
        return [(v[0] as num).toDouble(), (v[1] as num).toDouble()];
      }
      return fallback;
    }

    return HabitatEntity(
      id: j['id'] as String? ?? '',
      entityType: j['entity_type'] as String? ?? 'shape',
      creator: j['creator'] as String? ?? 'human',
      owner: j['owner'] as String? ?? 'shared',
      territory: j['territory'] as String? ?? 'space',
      createdAt: (j['created_at'] as num?)?.toDouble() ?? 0.0,
      modifiedAt: (j['modified_at'] as num?)?.toDouble() ?? 0.0,
      position: _pair(j['position'], const [0.5, 0.5]),
      dimensions: _pair(j['dimensions'], const [0.1, 0.1]),
      orientation: (j['orientation'] as num?)?.toDouble() ?? 0.0,
      layer: (j['layer'] as num?)?.toInt() ?? 0,
      visualProperties: Map<String, dynamic>.from(j['visual_properties'] as Map? ?? {}),
      temporalProperties: Map<String, dynamic>.from(j['temporal_properties'] as Map? ?? {}),
      links: List<String>.from((j['links'] as List?) ?? const []),
      groupMembership: j['group_membership'] as String?,
      content: Map<String, dynamic>.from(j['content'] as Map? ?? {}),
      interactionPermissions: Map<String, dynamic>.from(j['interaction_permissions'] as Map? ?? {}),
      lineage: Map<String, dynamic>.from(j['lineage'] as Map? ?? {}),
      deleted: j['deleted'] as bool? ?? false,
      revisionCount: (j['revision_count'] as num?)?.toInt() ?? 0,
    );
  }

  bool permission(String key) => interactionPermissions[key] == true;

  /// Deliberately generic pass-through of whatever the environment
  /// action stored. Never derives a meaning; only surfaces the fact.
  dynamic visual(String key) => visualProperties[key];
}

class HabitatState {
  final String territory;
  final int entityCount;
  final List<HabitatEntity> entities;
  final double asOf;

  const HabitatState({
    required this.territory,
    required this.entityCount,
    required this.entities,
    required this.asOf,
  });

  factory HabitatState.fromJson(Map<String, dynamic> j) {
    final rawEntities = (j['entities'] as List?) ?? const [];
    return HabitatState(
      territory: j['territory'] as String? ?? 'all',
      entityCount: (j['entity_count'] as num?)?.toInt() ?? 0,
      entities: rawEntities
          .whereType<Map>()
          .map((e) => HabitatEntity.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      asOf: (j['as_of'] as num?)?.toDouble() ?? 0.0,
    );
  }

  factory HabitatState.empty(String territory) =>
      HabitatState(territory: territory, entityCount: 0, entities: const [], asOf: 0.0);
}

class HabitatConsequence {
  final String actionId;
  final bool success;
  final String actor;
  final String operation;
  final List<String> affectedEntities;
  final String permissionResult;
  final String rejectedReason;
  final Map<String, dynamic> resultingState;

  const HabitatConsequence({
    required this.actionId,
    required this.success,
    required this.actor,
    required this.operation,
    required this.affectedEntities,
    required this.permissionResult,
    required this.rejectedReason,
    required this.resultingState,
  });

  factory HabitatConsequence.fromJson(Map<String, dynamic> j) => HabitatConsequence(
        actionId: j['action_id'] as String? ?? '',
        success: j['success'] as bool? ?? false,
        actor: j['actor'] as String? ?? '',
        operation: j['operation'] as String? ?? '',
        affectedEntities: List<String>.from((j['affected_entities'] as List?) ?? const []),
        permissionResult: j['permission_result'] as String? ?? 'n/a',
        rejectedReason: j['rejected_reason'] as String? ?? '',
        resultingState: Map<String, dynamic>.from(j['resulting_state'] as Map? ?? {}),
      );

  factory HabitatConsequence.error(String reason) => HabitatConsequence(
        actionId: '', success: false, actor: '', operation: '',
        affectedEntities: const [], permissionResult: 'denied:$reason',
        rejectedReason: reason, resultingState: const {},
      );
}

/// Safe JSON decode helper shared by the Habitat Dart files -- returns
/// an empty map rather than throwing on a malformed/error payload, so
/// a bridge hiccup degrades the UI instead of crashing it.
Map<String, dynamic> decodeHabitatJson(String raw) {
  try {
    final decoded = jsonDecode(raw);
    if (decoded is Map) return Map<String, dynamic>.from(decoded);
  } catch (_) {}
  return {};
}
