# Fusion 360 MCP Server API Reference

This document provides a complete reference for all MCP tools available in the Fusion 360 MCP Server.

## Table of Contents

- [System Tools](#system-tools)
- [Query Tools](#query-tools)
- [Creation Tools](#creation-tools)
  - [Primitives](#primitives)
  - [Sketches](#sketches)
  - [Basic Features](#basic-features)
  - [Advanced Sketch Drawing](#advanced-sketch-drawing)
  - [Sketch Constraints](#sketch-constraints)
  - [Sketch Dimensions](#sketch-dimensions)
  - [Sketch Patterns & Operations](#sketch-patterns--operations)
  - [Sketch Annotations](#sketch-annotations)
  - [Advanced Features](#advanced-features)
  - [Construction Planes](#construction-planes)
  - [Body Patterns](#body-patterns)
  - [Body Operations](#body-operations)
- [Modification Tools](#modification-tools)
- [Validation Tools](#validation-tools)
- [Viewport Tools](#viewport-tools)
- [Assembly Tools](#assembly-tools)

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

### Primitives

#### create_box

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

#### create_cylinder

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

### Sketches

#### create_sketch

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

### Basic Features

#### draw_line

Draw a line in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| start_x | float | Yes | Start X coordinate in mm |
| start_y | float | Yes | Start Y coordinate in mm |
| end_x | float | Yes | End X coordinate in mm |
| end_y | float | Yes | End Y coordinate in mm |

#### draw_circle

Draw a circle in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| center_x | float | Yes | Center X coordinate in mm |
| center_y | float | Yes | Center Y coordinate in mm |
| radius | float | Yes | Circle radius in mm |

#### draw_rectangle

Draw a rectangle in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| x1 | float | Yes | First corner X in mm |
| y1 | float | Yes | First corner Y in mm |
| x2 | float | Yes | Opposite corner X in mm |
| y2 | float | Yes | Opposite corner Y in mm |

#### draw_arc

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

#### extrude

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

#### revolve

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

#### fillet

Apply fillet to edges.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body |
| edge_ids | array | Yes | List of edge IDs to fillet |
| radius | float | Yes | Fillet radius in mm |

#### chamfer

Apply chamfer to edges.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body |
| edge_ids | array | Yes | List of edge IDs to chamfer |
| distance | float | Yes | Chamfer distance in mm |
| distance2 | float | No | Second distance for asymmetric chamfer |

#### create_hole

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

### Advanced Sketch Drawing

#### draw_polygon

Draw a regular polygon in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| radius | float | Yes | Circumscribed circle radius in mm |
| sides | int | Yes | Number of sides (3-64) |
| center_x | float | No | Center X coordinate (default: 0) |
| center_y | float | No | Center Y coordinate (default: 0) |
| rotation_angle | float | No | Rotation angle in degrees (default: 0) |

#### draw_ellipse

Draw an ellipse in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| major_radius | float | Yes | Major axis radius in mm |
| minor_radius | float | Yes | Minor axis radius in mm |
| center_x | float | No | Center X coordinate (default: 0) |
| center_y | float | No | Center Y coordinate (default: 0) |
| rotation_angle | float | No | Rotation of major axis in degrees (default: 0) |

#### draw_slot

Draw a slot shape (rounded rectangle/oblong) in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| length | float | Yes | Slot length in mm |
| width | float | Yes | Slot width in mm (diameter of rounded ends) |
| center_x | float | No | Center X coordinate (default: 0) |
| center_y | float | No | Center Y coordinate (default: 0) |
| slot_type | string | No | "overall" or "center_to_center" (default: overall) |
| rotation_angle | float | No | Rotation angle in degrees (default: 0) |

#### draw_spline

Draw a spline (smooth curve) through control points.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| points | array | Yes | List of point dicts with 'x' and 'y' coordinates |
| is_closed | boolean | No | Create closed spline loop (default: false) |

**Example points format:**
```json
[{"x": 0, "y": 0}, {"x": 20, "y": 15}, {"x": 40, "y": -10}]
```

#### draw_point

Draw a point in a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| x | float | Yes | X coordinate in mm |
| y | float | Yes | Y coordinate in mm |
| is_construction | boolean | No | Mark as construction geometry (default: false) |

### Sketch Constraints

#### add_constraint_horizontal

Constrain a line to be horizontal.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve_id | string | Yes | ID of the line to constrain |

#### add_constraint_vertical

Constrain a line to be vertical.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve_id | string | Yes | ID of the line to constrain |

#### add_constraint_coincident

Make two points coincident or place a point on a curve.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| entity1_id | string | Yes | ID of first entity (point or curve) |
| entity2_id | string | Yes | ID of second entity (point or curve) |

#### add_constraint_perpendicular

Make two lines perpendicular (90 degrees).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve1_id | string | Yes | ID of the first line |
| curve2_id | string | Yes | ID of the second line |

#### add_constraint_parallel

Make two lines parallel.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve1_id | string | Yes | ID of the first line |
| curve2_id | string | Yes | ID of the second line |

#### add_constraint_tangent

Make two curves tangent at their connection point.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve1_id | string | Yes | ID of the first curve |
| curve2_id | string | Yes | ID of the second curve |

#### add_constraint_equal

Make two curves equal in size (length for lines, radius for circles).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve1_id | string | Yes | ID of the first curve |
| curve2_id | string | Yes | ID of the second curve |

#### add_constraint_concentric

Make two circles or arcs share the same center.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve1_id | string | Yes | ID of the first circle/arc |
| curve2_id | string | Yes | ID of the second circle/arc |

#### add_constraint_fix

Fix an entity at its current position.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| entity_id | string | Yes | ID of the point or curve to fix |

### Sketch Dimensions

#### add_dimension

Add a dimensional constraint to a sketch.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| dimension_type | string | Yes | "distance", "radius", "diameter", or "angle" |
| entity1_id | string | Yes | ID of the first entity |
| value | float | Yes | Dimension value (mm or degrees) |
| entity2_id | string | No | ID of second entity (for distance between entities, angle) |
| text_position_x | float | No | X position for dimension text |
| text_position_y | float | No | Y position for dimension text |

### Sketch Patterns & Operations

#### sketch_mirror

Mirror sketch entities across a line.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve_ids | array | Yes | List of curve IDs to mirror |
| mirror_line_id | string | Yes | ID of the line to mirror across |

#### sketch_circular_pattern

Create a circular pattern of sketch entities.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve_ids | array | Yes | List of curve IDs to pattern |
| count | int | Yes | Total number of instances (2-360) |
| center_x | float | No | Pattern center X in mm (default: 0) |
| center_y | float | No | Pattern center Y in mm (default: 0) |
| total_angle | float | No | Total angle span in degrees (default: 360) |

#### sketch_rectangular_pattern

Create a rectangular pattern of sketch entities.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| curve_ids | array | Yes | List of curve IDs to pattern |
| x_count | int | Yes | Number of columns |
| y_count | int | Yes | Number of rows |
| x_spacing | float | Yes | Column spacing in mm |
| y_spacing | float | Yes | Row spacing in mm |

#### project_geometry

Project 3D geometry onto a sketch plane.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the target sketch |
| entity_ids | array | Yes | List of entity IDs to project (edges, faces, bodies) |
| project_type | string | No | "standard" or "cut_edges" (default: standard) |

### Sketch Annotations

#### add_sketch_text

Add text to a sketch for engraving or embossing.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch |
| text | string | Yes | Text content |
| height | float | Yes | Text height in mm |
| x | float | No | X position in mm (default: 0) |
| y | float | No | Y position in mm (default: 0) |
| font_name | string | No | Font name (default: system default) |
| is_bold | boolean | No | Make text bold (default: false) |
| is_italic | boolean | No | Make text italic (default: false) |

#### wrap_sketch_to_surface

Project sketch curves onto a curved surface.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the source sketch |
| face_id | string | Yes | ID of the target curved face |
| projection_type | string | No | "closest_point" or "along_vector" (default: closest_point) |
| direction_axis | string | No | Axis for "along_vector": X, Y, Z |
| create_new_sketch | boolean | No | Create new sketch for result (default: true) |

### Advanced Features

#### sweep

Sweep a 2D profile along a path to create 3D geometry.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| profile_sketch_id | string | Yes | ID of sketch with profile |
| path_sketch_id | string | Yes | ID of sketch with path |
| profile_index | int | No | Profile index (default: 0) |
| operation | string | No | "new_body", "join", "cut", "intersect" (default: new_body) |
| orientation | string | No | "perpendicular" or "parallel" (default: perpendicular) |
| name | string | No | Name for the body |

#### loft

Create a smooth shape by blending between multiple profiles.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_ids | array | Yes | List of sketch IDs in order |
| profile_indices | array | No | Profile indices for each sketch |
| operation | string | No | "new_body", "join", "cut", "intersect" (default: new_body) |
| is_solid | boolean | No | Create solid body (default: true) |
| is_closed | boolean | No | Close loft ends (default: false) |
| name | string | No | Name for the body |
| target_body_id | string | No | **Required** for join/cut/intersect operations |

#### create_sphere

Create a solid sphere.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| radius | float | Yes | Sphere radius in mm |
| x | float | No | Center X position (default: 0) |
| y | float | No | Center Y position (default: 0) |
| z | float | No | Center Z position (default: 0) |
| name | string | No | Name for the body |
| component_id | string | No | Target component |

#### create_torus

Create a torus (donut/ring shape).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| major_radius | float | Yes | Distance from center to tube center in mm |
| minor_radius | float | Yes | Tube radius in mm (must be < major_radius) |
| x | float | No | Center X position (default: 0) |
| y | float | No | Center Y position (default: 0) |
| z | float | No | Center Z position (default: 0) |
| name | string | No | Name for the body |
| component_id | string | No | Target component |

#### create_coil

Create a helix/spring shape.

> **Note:** This tool is **NOT SUPPORTED** due to Fusion 360 API limitations. Use `sweep()` with a helical path as a workaround.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| diameter | float | Yes | Coil diameter in mm |
| pitch | float | Yes | Distance between coils in mm |
| revolutions | float | Yes | Number of turns |
| section_size | float | Yes | Wire/section diameter in mm |
| section_type | string | No | "circular" or "square" (default: circular) |

#### create_pipe

Create a hollow tubular shape along a path.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| path_sketch_id | string | Yes | ID of sketch with path |
| outer_diameter | float | Yes | Outer diameter in mm |
| wall_thickness | float | Yes | Wall thickness in mm (must be < outer_diameter/2) |
| operation | string | No | "new_body", "join", "cut", "intersect" (default: new_body) |
| name | string | No | Name for the body |

#### create_thread

Add threads to a cylindrical face.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| face_id | string | Yes | ID of the cylindrical face |
| thread_type | string | Yes | Thread standard (e.g., "ISO Metric profile") |
| thread_size | string | Yes | Thread size (e.g., "M8x1.25") |
| is_internal | boolean | No | Internal threads (default: false) |
| is_full_length | boolean | No | Thread entire length (default: true) |
| thread_length | float | No | Custom thread length in mm |
| is_modeled | boolean | No | Create 3D geometry (default: false) |

### Construction Planes

#### create_offset_plane

Create a construction plane offset from an existing plane.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| base_plane | string | Yes | Base plane: XY, YZ, XZ, face_id, or plane_id |
| offset | float | Yes | Offset distance in mm |
| name | string | No | Name for the plane |
| component_id | string | No | Target component |

#### create_angle_plane

Create a construction plane at an angle from a plane along an edge.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| base_plane | string | Yes | Base plane reference |
| edge_id | string | Yes | ID of edge to rotate around |
| angle | float | Yes | Rotation angle in degrees |
| name | string | No | Name for the plane |
| component_id | string | No | Target component |

#### create_three_point_plane

Create a construction plane through three points.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| point1 | object | Yes | First point {x, y, z} - becomes origin |
| point2 | object | Yes | Second point {x, y, z} |
| point3 | object | Yes | Third point {x, y, z} |
| name | string | No | Name for the plane |
| component_id | string | No | Target component |

#### create_midplane

Create a construction plane midway between two parallel planes.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| plane1 | string | Yes | First plane reference |
| plane2 | string | Yes | Second plane reference (must be parallel) |
| name | string | No | Name for the plane |
| component_id | string | No | Target component |

### Body Patterns

#### rectangular_pattern

Create a rectangular pattern of bodies or features.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_ids | array | Yes | List of body or feature IDs |
| entity_type | string | Yes | "bodies" or "features" |
| x_count | int | Yes | Number of columns (≥2) |
| x_spacing | float | Yes | Column spacing in mm |
| x_axis | string | No | Direction: X, Y, Z, or edge_id (default: X) |
| y_count | int | No | Number of rows (default: 1) |
| y_spacing | float | No | Row spacing in mm |
| y_axis | string | No | Second direction |

#### circular_pattern

Create a circular pattern of bodies or features.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_ids | array | Yes | List of body or feature IDs |
| entity_type | string | Yes | "bodies" or "features" |
| axis | string | Yes | Rotation axis: X, Y, Z, or axis_id |
| count | int | Yes | Total instances (≥2) |
| total_angle | float | No | Angle span in degrees (default: 360) |
| is_symmetric | boolean | No | Distribute evenly (default: true) |

#### mirror_feature

Mirror bodies or features across a plane.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_ids | array | Yes | List of body or feature IDs |
| entity_type | string | Yes | "bodies" or "features" |
| mirror_plane | string | Yes | Symmetry plane: XY, YZ, XZ, plane_id, or face_id |

### Body Operations

#### combine

Combine multiple bodies using boolean operations.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| target_body_id | string | Yes | ID of the body to modify |
| tool_body_ids | array | Yes | List of body IDs to combine with |
| operation | string | No | "join", "cut", "intersect" (default: join) |
| keep_tools | boolean | No | Keep tool bodies after operation (default: false) |

#### split_body

Split a body using a plane or face.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body to split |
| splitting_tool | string | Yes | XY, YZ, XZ, face_id, or plane_id |
| extend_splitting_tool | boolean | No | Extend surface to split completely (default: true) |

#### shell

Create a hollow shell from a solid body.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| body_id | string | Yes | ID of the body to shell |
| face_ids | array | Yes | List of face IDs to remove (become openings) |
| thickness | float | Yes | Wall thickness in mm |
| direction | string | No | "inside" or "outside" (default: inside) |

#### thicken

Add thickness to surface faces to create solid bodies.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| face_ids | array | Yes | List of face IDs to thicken |
| thickness | float | Yes | Thickness in mm |
| direction | string | No | "both", "positive", "negative" (default: both) |
| operation | string | No | "new_body", "join", "cut", "intersect" (default: new_body) |
| is_chain | boolean | No | Include tangent faces (default: true) |

#### emboss

Create raised (emboss) or recessed (deboss) features.

> **Note:** This tool is **NOT SUPPORTED** due to Fusion 360 API limitations. Use `extrude()` with join/cut operations as a workaround.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sketch_id | string | Yes | ID of the sketch with profile |
| face_id | string | Yes | ID of the face to emboss onto |
| depth | float | Yes | Emboss depth in mm |
| is_emboss | boolean | No | True for raised, False for recessed (default: true) |
| profile_index | int | No | Profile index (default: 0) |
| taper_angle | float | No | Side taper in degrees (default: 0) |

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

## Viewport Tools

### take_screenshot

Capture the current Fusion 360 viewport as a PNG image.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file_path | string | Yes | Path to save the image file |
| view | string | No | View to capture: "current", "front", "back", "top", "bottom", "left", "right", "isometric", "trimetric", "home" (default: current) |
| width | int | No | Image width in pixels (default: 1920, max: 8192) |
| height | int | No | Image height in pixels (default: 1080, max: 8192) |

**Returns:**
```json
{
  "format": "png",
  "dimensions": {"width": 1920, "height": 1080},
  "view": "isometric",
  "file_path": "/path/to/design.png"
}
```

### set_camera

Set the viewport camera position and orientation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| eye_x | float | Yes | Camera eye X position in mm |
| eye_y | float | Yes | Camera eye Y position in mm |
| eye_z | float | Yes | Camera eye Z position in mm |
| target_x | float | No | Look-at X position (default: 0) |
| target_y | float | No | Look-at Y position (default: 0) |
| target_z | float | No | Look-at Z position (default: 0) |
| up_x | float | No | Up vector X (default: 0) |
| up_y | float | No | Up vector Y (default: 0) |
| up_z | float | No | Up vector Z (default: 1) |
| smooth_transition | boolean | No | Animate camera movement (default: true) |

**Returns:**
```json
{
  "camera": {
    "eye": {"x": 0, "y": -500, "z": 200},
    "target": {"x": 0, "y": 0, "z": 0},
    "up_vector": {"x": 0, "y": 0, "z": 1},
    "view_extents": 50.0,
    "is_perspective": true
  }
}
```

### get_camera

Get the current viewport camera state.

**Parameters:** None

**Returns:**
```json
{
  "camera": {
    "eye": {"x": 0, "y": -500, "z": 200},
    "target": {"x": 0, "y": 0, "z": 0},
    "up_vector": {"x": 0, "y": 0, "z": 1},
    "view_extents": 50.0,
    "is_perspective": true
  }
}
```

### set_view

Set the viewport to a standard named view.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| view | string | Yes | Named view: "front", "back", "top", "bottom", "left", "right", "isometric", "trimetric", "home" |
| smooth_transition | boolean | No | Animate view change (default: true) |

**Returns:**
```json
{
  "view": "isometric",
  "camera": {
    "eye": {"x": 100, "y": -100, "z": 100},
    "target": {"x": 0, "y": 0, "z": 0}
  }
}
```

### fit_view

Fit the viewport to show specific entities or all geometry.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_ids | array | No | List of body/component/occurrence IDs. If not provided, fits all visible geometry |
| smooth_transition | boolean | No | Animate zoom change (default: true) |

**Returns:**
```json
{
  "fitted_to": "all",
  "camera": {
    "eye": {"x": 150, "y": -150, "z": 100},
    "target": {"x": 50, "y": 25, "z": 5}
  }
}
```

---

## Assembly Tools

### Component Tools

#### create_component

Create a new component in the design.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Name for the new component |

**Returns:**
```json
{
  "success": true,
  "component": {
    "id": "Bracket",
    "name": "Bracket",
    "is_root": false
  },
  "occurrence": {
    "id": "Bracket:1",
    "transform": [...]
  },
  "component_id": "Bracket",
  "occurrence_id": "Bracket:1"
}
```

#### get_components

Get all components in the design.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "components": [
    {
      "id": "RootComponent",
      "name": "Root",
      "is_root": true,
      "is_active": false,
      "bodies_count": 0,
      "sketches_count": 0,
      "occurrences_count": 2
    },
    {
      "id": "Bracket",
      "name": "Bracket",
      "is_root": false,
      "is_active": true,
      "bodies_count": 1,
      "sketches_count": 1,
      "occurrences_count": 0
    }
  ],
  "total": 2
}
```

#### get_component_by_id

Get detailed information about a specific component.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | Yes | ID of the component |

**Returns:**
```json
{
  "success": true,
  "component": {
    "id": "Bracket",
    "name": "Bracket",
    "is_root": false,
    "is_active": true,
    "bodies_count": 1,
    "sketches_count": 1,
    "features_count": 2,
    "body_ids": ["body_0"],
    "sketch_ids": ["Sketch1"],
    "occurrence_ids": ["Bracket:1"],
    "bounding_box": {
      "min": {"x": 0, "y": 0, "z": 0},
      "max": {"x": 50, "y": 10, "z": 30}
    }
  }
}
```

#### activate_component

Activate a component for editing.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | Yes | ID of the component to activate. Use "RootComponent" for top level |

**Returns:**
```json
{
  "success": true,
  "active_component": {
    "id": "Bracket",
    "name": "Bracket"
  },
  "component_id": "Bracket"
}
```

#### get_component_bodies

Get all bodies within a specific component.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | Yes | ID of the component |

**Returns:**
```json
{
  "success": true,
  "bodies": [
    {
      "id": "body_0",
      "name": "Body1",
      "is_solid": true,
      "volume": 15000.0
    }
  ],
  "total": 1,
  "component_id": "Bracket"
}
```

### Occurrence Tools

#### get_occurrences

Get all occurrences in the design or within a component.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| component_id | string | No | Filter occurrences by component |

**Returns:**
```json
{
  "success": true,
  "occurrences": [
    {
      "id": "Bracket:1",
      "name": "Bracket:1",
      "component_id": "Bracket",
      "transform": [...],
      "is_visible": true,
      "is_grounded": false
    }
  ],
  "total": 1
}
```

#### move_occurrence

Move an occurrence to a new position (relative translation).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| occurrence_id | string | Yes | ID of the occurrence to move |
| x | float | No | X translation in mm (default: 0) |
| y | float | No | Y translation in mm (default: 0) |
| z | float | No | Z translation in mm (default: 0) |

**Returns:**
```json
{
  "success": true,
  "occurrence": {
    "id": "Bracket:1",
    "transform": [...]
  },
  "occurrence_id": "Bracket:1",
  "translation": {"x": 100, "y": 0, "z": 0}
}
```

### Joint Tools

#### create_joint

Create a joint between two geometry entities.

**Joint Types:**
- `rigid`: No relative motion (parts fixed together)
- `revolute`: Rotation around one axis (hinge)
- `slider`: Translation along one axis (drawer)
- `cylindrical`: Rotation + translation along same axis (piston)
- `pin_slot`: Rotation + perpendicular translation
- `planar`: Motion in a plane (2D freedom)
- `ball`: Rotation in all directions (ball joint)

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| geometry1_id | string | Yes | First geometry entity ID (face, edge, or vertex) |
| geometry2_id | string | Yes | Second geometry entity ID from different occurrence |
| joint_type | string | No | Type of joint (default: rigid) |

**Returns:**
```json
{
  "success": true,
  "joint": {
    "id": "Rigid1",
    "type": "rigid",
    "occurrence1_id": "Part1:1",
    "occurrence2_id": "Part2:1"
  },
  "joint_id": "Rigid1"
}
```

#### create_joint_between_occurrences

Create a joint between two occurrences at their origins.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| occurrence1_id | string | Yes | First occurrence ID |
| occurrence2_id | string | Yes | Second occurrence ID |
| joint_type | string | No | Type of joint (default: rigid) |

**Returns:**
```json
{
  "success": true,
  "joint": {
    "id": "Rigid1",
    "type": "rigid",
    "occurrence1_id": "Part1:1",
    "occurrence2_id": "Part2:1"
  },
  "joint_id": "Rigid1"
}
```

#### get_joints

Get all joints in the design.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "joints": [
    {
      "id": "Rigid1",
      "name": "Rigid1",
      "joint_type": "rigid",
      "occurrence1_id": "Part1:1",
      "occurrence2_id": "Part2:1",
      "is_suppressed": false
    }
  ],
  "total": 1
}
```

#### get_joint_by_id

Get detailed information about a specific joint.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| joint_id | string | Yes | ID of the joint |

**Returns:**
```json
{
  "success": true,
  "joint": {
    "id": "Rigid1",
    "name": "Rigid1",
    "joint_type": "rigid",
    "occurrence1_id": "Part1:1",
    "occurrence2_id": "Part2:1",
    "is_suppressed": false
  }
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
