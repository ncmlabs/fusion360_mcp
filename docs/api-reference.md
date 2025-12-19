# Fusion 360 MCP Server API Reference

This document provides a complete reference for all MCP tools available in the Fusion 360 MCP Server.

## Table of Contents

- [System Tools](#system-tools)
- [Query Tools](#query-tools)
- [Creation Tools](#creation-tools)
- [Modification Tools](#modification-tools)
- [Validation Tools](#validation-tools)

---

## System Tools

### check_health

Check the health status of the Fusion 360 connection.

**Parameters:** None

**Returns:**
```json
{
  "healthy": true,
  "server_status": "running",
  "server_version": "0.1.0",
  "addin_status": "healthy",
  "addin_version": "0.1.0",
  "message": "All systems operational"
}
```

### get_version

Get version information for all system components.

**Parameters:** None

**Returns:**
```json
{
  "server_version": "0.1.0",
  "addin_name": "FusionMCP",
  "addin_version": "0.1.0",
  "fusion_version": "2.0.18719",
  "api_version": "1.0"
}
```

---

## Query Tools

### get_design_state

Get the current Fusion 360 design state.

**Parameters:** None

**Returns:**
```json
{
  "name": "MyDesign",
  "units": "mm",
  "bodies_count": 3,
  "sketches_count": 2,
  "components_count": 1,
  "timeline_count": 5,
  "active_component_id": "RootComponent"
}
```

### get_bodies

Get all bodies in the design or a specific component.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | No | Filter bodies by component |

**Returns:**
```json
{
  "bodies": [
    {
      "id": "body_123",
      "name": "Box",
      "is_solid": true,
      "volume": 50000.0,
      "bounding_box": {
        "min": {"x": 0, "y": 0, "z": 0},
        "max": {"x": 100, "y": 50, "z": 10}
      }
    }
  ]
}
```

### get_body_by_id

Get detailed body information by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | The body ID to retrieve |
| include_faces | boolean | No | Include face geometry (default: false) |
| include_edges | boolean | No | Include edge geometry (default: false) |
| include_vertices | boolean | No | Include vertex positions (default: false) |

**Returns:**
```json
{
  "id": "body_123",
  "name": "Box",
  "is_solid": true,
  "volume": 50000.0,
  "area": 7000.0,
  "bounding_box": {...},
  "faces": [
    {"id": "face_1", "type": "planar", "area": 5000.0}
  ],
  "edges": [
    {"id": "edge_1", "type": "linear", "length": 100.0}
  ]
}
```

### get_sketches

Get all sketches in the design or a specific component.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | No | Filter sketches by component |

**Returns:**
```json
{
  "sketches": [
    {
      "id": "sketch_123",
      "name": "Sketch1",
      "plane": "XY",
      "is_fully_constrained": true,
      "profiles_count": 1
    }
  ]
}
```

### get_sketch_by_id

Get detailed sketch information by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | The sketch ID to retrieve |
| include_curves | boolean | No | Include curve details (default: true) |
| include_constraints | boolean | No | Include constraints (default: true) |
| include_dimensions | boolean | No | Include dimensions (default: true) |
| include_profiles | boolean | No | Include profiles (default: false) |

**Returns:**
```json
{
  "id": "sketch_123",
  "name": "Sketch1",
  "plane": "XY",
  "is_fully_constrained": true,
  "curves": [
    {"id": "curve_1", "type": "line", "start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}}
  ],
  "constraints": [
    {"type": "horizontal", "curves": ["curve_1"]}
  ]
}
```

### get_parameters

Get all parameters in the design.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_only | boolean | No | Only return user parameters (default: false) |
| favorites_only | boolean | No | Only return favorites (default: false) |

**Returns:**
```json
{
  "parameters": [
    {
      "name": "width",
      "value": 100.0,
      "unit": "mm",
      "expression": "100 mm",
      "is_user_parameter": true
    }
  ]
}
```

### get_timeline

Get the design timeline (feature history).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| include_suppressed | boolean | No | Include suppressed features (default: true) |
| include_rolled_back | boolean | No | Include rolled back features (default: false) |

**Returns:**
```json
{
  "entries": [
    {"index": 0, "name": "Sketch1", "type": "Sketch"},
    {"index": 1, "name": "Extrude1", "type": "ExtrudeFeature"}
  ],
  "marker_position": 2
}
```

---

## Creation Tools

### create_box

Create a box (rectangular prism).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| width | float | Yes | Box width in mm |
| depth | float | Yes | Box depth in mm |
| height | float | Yes | Box height in mm |
| x | float | No | X position of center (default: 0) |
| y | float | No | Y position of center (default: 0) |
| z | float | No | Z position/offset (default: 0) |
| name | string | No | Name for the body |
| plane | string | No | Construction plane: XY, YZ, XZ (default: XY) |
| component_id | string | No | Target component |

**Returns:**
```json
{
  "body_id": "body_123",
  "feature_id": "extrude_1",
  "body": {
    "id": "body_123",
    "name": "Box",
    "is_solid": true,
    "volume": 50000.0
  }
}
```

### create_cylinder

Create a cylinder.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| radius | float | Yes | Cylinder radius in mm |
| height | float | Yes | Cylinder height in mm |
| x | float | No | X position of center (default: 0) |
| y | float | No | Y position of center (default: 0) |
| z | float | No | Z position/offset (default: 0) |
| name | string | No | Name for the body |
| plane | string | No | Construction plane (default: XY) |
| component_id | string | No | Target component |

### create_sketch

Create a new sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| plane | string | No | Plane: XY, YZ, XZ, or face_id (default: XY) |
| name | string | No | Name for the sketch |
| offset | float | No | Offset from plane in mm (default: 0) |
| component_id | string | No | Target component |

**Returns:**
```json
{
  "sketch_id": "sketch_123",
  "sketch": {
    "id": "sketch_123",
    "name": "MySketch",
    "plane": "XY"
  }
}
```

### draw_line

Draw a line in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| start_x | float | Yes | Start X coordinate in mm |
| start_y | float | Yes | Start Y coordinate in mm |
| end_x | float | Yes | End X coordinate in mm |
| end_y | float | Yes | End Y coordinate in mm |

### draw_circle

Draw a circle in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| center_x | float | Yes | Center X coordinate in mm |
| center_y | float | Yes | Center Y coordinate in mm |
| radius | float | Yes | Circle radius in mm |

### draw_rectangle

Draw a rectangle in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| x1 | float | Yes | First corner X in mm |
| y1 | float | Yes | First corner Y in mm |
| x2 | float | Yes | Opposite corner X in mm |
| y2 | float | Yes | Opposite corner Y in mm |

### draw_arc

Draw an arc in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| center_x | float | Yes | Center X coordinate in mm |
| center_y | float | Yes | Center Y coordinate in mm |
| radius | float | Yes | Arc radius in mm |
| start_angle | float | Yes | Start angle in degrees |
| end_angle | float | Yes | End angle in degrees |

### extrude

Extrude a sketch profile.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| distance | float | Yes | Extrusion distance in mm |
| direction | string | No | "positive", "negative", "symmetric" (default: positive) |
| operation | string | No | "new_body", "join", "cut", "intersect" (default: new_body) |
| profile_index | int | No | Index of profile to extrude (default: 0) |
| name | string | No | Name for created body |
| taper_angle | float | No | Taper angle in degrees (default: 0) |

### revolve

Revolve a sketch profile around an axis.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| axis | string | Yes | Axis to revolve around: X, Y, Z |
| angle | float | No | Revolution angle in degrees (default: 360) |
| operation | string | No | "new_body", "join", "cut", "intersect" (default: new_body) |
| profile_index | int | No | Index of profile to revolve (default: 0) |
| name | string | No | Name for created body |

### fillet

Apply fillet to edges.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body |
| edge_ids | array | Yes | List of edge IDs to fillet |
| radius | float | Yes | Fillet radius in mm |

### chamfer

Apply chamfer to edges.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body |
| edge_ids | array | Yes | List of edge IDs to chamfer |
| distance | float | Yes | Chamfer distance in mm |
| distance2 | float | No | Second distance for asymmetric chamfer |

### create_hole

Create a hole in a body.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| diameter | float | Yes | Hole diameter in mm |
| depth | float | Yes | Hole depth in mm |
| body_id | string | No | ID of the body (optional if face_id provided) |
| face_id | string | No | ID of the face to place hole on |
| x | float | No | X position in mm (default: 0) |
| y | float | No | Y position in mm (default: 0) |
| name | string | No | Name for the feature |
| hole_type | string | No | "simple", "countersink", "counterbore" (default: simple) |

---

## Modification Tools

### move_body

Move a body by translation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body to move |
| x | float | No | Translation in X direction (default: 0) |
| y | float | No | Translation in Y direction (default: 0) |
| z | float | No | Translation in Z direction (default: 0) |

**Returns:**
```json
{
  "feature_id": "move_1",
  "new_position": {"x": 10, "y": 20, "z": 0}
}
```

### rotate_body

Rotate a body around an axis.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body to rotate |
| axis | string | Yes | Axis: X, Y, or Z |
| angle | float | Yes | Rotation angle in degrees |
| origin_x | float | No | X coordinate of rotation origin (default: 0) |
| origin_y | float | No | Y coordinate of rotation origin (default: 0) |
| origin_z | float | No | Z coordinate of rotation origin (default: 0) |

### modify_feature

Modify feature parameters.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| feature_id | string | Yes | ID of the feature to modify |
| parameters | object | Yes | Dict of parameter names to new values |

**Parameter options:**
- ExtrudeFeature: `{"distance": float}`
- FilletFeature: `{"radius": float}`
- ChamferFeature: `{"distance": float}`
- RevolveFeature: `{"angle": float}`

### update_parameter

Update a parameter value.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Parameter name |
| expression | string | Yes | New value expression (e.g., "50 mm", "d1 * 2") |

### delete_body

Delete a body from the design.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body to delete |

### delete_feature

Delete a feature from the timeline.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| feature_id | string | Yes | ID of the feature to delete |

### edit_sketch

Edit a sketch curve.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve_id | string | Yes | ID of the curve to modify |
| properties | object | Yes | Properties to modify |

**Property options:**
- Lines: `{"start_x", "start_y", "end_x", "end_y"}`
- Circles: `{"center_x", "center_y", "radius"}`
- Arcs: `{"center_x", "center_y"}`

---

## Validation Tools

### measure_distance

Measure minimum distance between two entities.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity1_id | string | Yes | ID of the first entity |
| entity2_id | string | Yes | ID of the second entity |

**Returns:**
```json
{
  "distance": 15.5,
  "point1": {"x": 0, "y": 0, "z": 0},
  "point2": {"x": 15.5, "y": 0, "z": 0}
}
```

**Accuracy:** 0.001 mm

### measure_angle

Measure angle between two planar faces or linear edges.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity1_id | string | Yes | ID of the first entity (face or edge) |
| entity2_id | string | Yes | ID of the second entity (face or edge) |

**Returns:**
```json
{
  "angle": 90.0
}
```

### check_interference

Check for interference (collisions) between bodies.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_ids | array | No | List of body IDs to check. If None, checks all bodies |

**Returns:**
```json
{
  "has_interference": false,
  "interferences": [],
  "bodies_checked": 3
}
```

Or if interference exists:
```json
{
  "has_interference": true,
  "interferences": [
    {
      "body1_id": "body_1",
      "body2_id": "body_2",
      "overlap_volume": 125.5
    }
  ]
}
```

### get_body_properties

Get detailed physical properties of a body.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body to analyze |

**Returns:**
```json
{
  "volume": 50000.0,
  "area": 7000.0,
  "center_of_mass": {"x": 50, "y": 25, "z": 5},
  "bounding_box": {
    "min": {"x": 0, "y": 0, "z": 0},
    "max": {"x": 100, "y": 50, "z": 10}
  },
  "dimensions": {"x": 100, "y": 50, "z": 10},
  "faces_count": 6,
  "edges_count": 12,
  "vertices_count": 8
}
```

### get_sketch_status

Get the constraint status of a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch to analyze |

**Returns:**
```json
{
  "is_fully_constrained": true,
  "under_constrained_count": 0,
  "profiles_count": 1,
  "curves_count": 4,
  "constraints_count": 8
}
```

---

## Error Responses

All tools may return error responses in the following format:

```json
{
  "error_type": "EntityNotFound",
  "error": "Body not found",
  "suggestion": "Use get_bodies() to see available entities",
  "context": {
    "entity_type": "Body",
    "requested_id": "nonexistent",
    "available_entities": ["body1", "body2"]
  }
}
```

### Error Types

| Type | Description |
|------|-------------|
| EntityNotFound | Requested entity ID does not exist |
| InvalidParameter | Parameter value is invalid |
| GeometryError | Geometry operation failed |
| ConstraintError | Sketch constraint issue |
| FeatureError | Feature creation/modification failed |
| SelectionError | Invalid entity type for operation |
| ConnectionError | Cannot connect to Fusion 360 add-in |
| TimeoutError | Operation timed out |
| DesignStateError | Invalid design state for operation |

---

## Units

- All linear dimensions are in **millimeters (mm)**
- All angles are in **degrees**
- All volumes are in **mm³**
- All areas are in **mm²**
