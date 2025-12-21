# Fusion 360 MCP - LLM Reference Guide

This guide helps LLMs quickly identify the right tools and workflows when working with Fusion 360 MCP Server.

---

## 1. Tool Categories Quick Reference

### Query Tools (7 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_design_state()` | Get current design overview | None |
| `get_bodies(component_id?)` | List all bodies | Optional component filter |
| `get_body_by_id(body_id, include_faces?, include_edges?)` | Get body details | Set flags for topology |
| `get_sketches(component_id?)` | List all sketches | Optional component filter |
| `get_sketch_by_id(sketch_id, ...)` | Get sketch details | include_curves, include_profiles |
| `get_parameters(user_only?)` | List design parameters | Filter to user params |
| `get_timeline()` | Get feature history | None |

### Creation Tools - Primitives (5 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_box(width, depth, height, x?, y?, z?)` | Create rectangular prism | Dimensions in mm |
| `create_cylinder(radius, height, x?, y?, z?)` | Create cylinder | Radius, height in mm |
| `create_sphere(radius, x?, y?, z?)` | Create sphere | Radius in mm |
| `create_torus(major_radius, minor_radius, ...)` | Create donut shape | minor < major |
| `create_coil(...)` | Create helix/spring | **NOT SUPPORTED** - API limitation |

### Creation Tools - Sketches (12 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_sketch(plane?, offset?)` | Create new sketch | "XY", "YZ", "XZ" or face_id |
| `draw_line(sketch_id, start_x, start_y, end_x, end_y)` | Draw line | Coordinates in mm |
| `draw_circle(sketch_id, center_x, center_y, radius)` | Draw circle | Creates closed profile |
| `draw_rectangle(sketch_id, x1, y1, x2, y2)` | Draw rectangle | Two corners |
| `draw_arc(sketch_id, center_x, center_y, radius, start_angle, end_angle)` | Draw arc | Angles in degrees |
| `draw_polygon(sketch_id, radius, sides, ...)` | Draw regular polygon | 3-64 sides |
| `draw_ellipse(sketch_id, major_radius, minor_radius, ...)` | Draw ellipse | minor ≤ major |
| `draw_slot(sketch_id, length, width, ...)` | Draw slot/oblong | Rounded ends |
| `draw_spline(sketch_id, points, is_closed?)` | Draw smooth curve | List of {x, y} points |
| `draw_point(sketch_id, x, y)` | Draw reference point | For constraints |
| `add_sketch_text(sketch_id, text, height, ...)` | Add text | **Note: No extrude profiles** |
| `project_geometry(sketch_id, entity_ids, ...)` | Project 3D edges | For reference curves |

### Creation Tools - Features (10 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `extrude(sketch_id, distance, direction?, operation?)` | Extrude profile | "new_body", "join", "cut" |
| `revolve(sketch_id, axis, angle?, operation?)` | Revolve profile | Axis: "X", "Y", "Z" |
| `sweep(profile_sketch_id, path_sketch_id, ...)` | Sweep along path | Profile + path sketches |
| `loft(sketch_ids, operation?, target_body_id?)` | Blend profiles | **Requires target_body_id for cut/join** |
| `create_pipe(path_sketch_id, outer_diameter, wall_thickness)` | Create hollow tube | wall < diameter/2 |
| `fillet(body_id, edge_ids, radius)` | Round edges | Get edges with include_edges=True |
| `chamfer(body_id, edge_ids, distance, distance2?)` | Bevel edges | Symmetric or asymmetric |
| `create_hole(diameter, depth, body_id?, face_id?, x?, y?)` | Create hole | Position on face |
| `thicken(face_ids, thickness, direction?)` | Add thickness to surface | For sheet metal |
| `emboss(sketch_id, face_id, depth, is_emboss?)` | Raise/recess profile | True=emboss, False=deboss |

### Creation Tools - Patterns (6 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `sketch_mirror(sketch_id, curve_ids, mirror_line_id)` | Mirror sketch curves | Across a line |
| `sketch_circular_pattern(sketch_id, curve_ids, count, ...)` | Circular array in sketch | 2-360 instances |
| `sketch_rectangular_pattern(sketch_id, curve_ids, x_count, y_count, x_spacing, y_spacing)` | Grid array in sketch | Spacing in mm |
| `rectangular_pattern(entity_ids, entity_type, x_count, x_spacing, ...)` | Pattern bodies/features | 3D rectangular array |
| `circular_pattern(entity_ids, entity_type, axis, count, ...)` | Pattern bodies/features | 3D circular array |
| `mirror_feature(entity_ids, entity_type, mirror_plane)` | Mirror bodies/features | "XY", "YZ", "XZ" |

### Creation Tools - Constraints (10 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `add_constraint_horizontal(sketch_id, curve_id)` | Make line horizontal | Line only |
| `add_constraint_vertical(sketch_id, curve_id)` | Make line vertical | Line only |
| `add_constraint_coincident(sketch_id, entity1_id, entity2_id)` | Connect points | Points or curves |
| `add_constraint_perpendicular(sketch_id, curve1_id, curve2_id)` | 90° between lines | Two lines |
| `add_constraint_parallel(sketch_id, curve1_id, curve2_id)` | Parallel lines | Two lines |
| `add_constraint_tangent(sketch_id, curve1_id, curve2_id)` | Smooth transition | Line to arc/circle |
| `add_constraint_equal(sketch_id, curve1_id, curve2_id)` | Same size | Same type curves |
| `add_constraint_concentric(sketch_id, curve1_id, curve2_id)` | Same center | Circles/arcs |
| `add_constraint_fix(sketch_id, entity_id)` | Lock position | Any entity |
| `add_dimension(sketch_id, dimension_type, entity1_id, value, ...)` | Add dimension | "distance", "radius", "diameter", "angle" |

### Creation Tools - Construction Planes (4 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_offset_plane(base_plane, offset)` | Parallel plane | Offset in mm |
| `create_angle_plane(base_plane, edge_id, angle)` | Angled plane | Angle in degrees |
| `create_three_point_plane(point1, point2, point3)` | Plane through 3 points | {x, y, z} dicts |
| `create_midplane(plane1, plane2)` | Plane between two | Must be parallel |

### Creation Tools - Advanced (2 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_thread(face_id, thread_type, thread_size, ...)` | Add threads | Cylindrical face |
| `create_coil(...)` | **NOT SUPPORTED** | Use sweep workaround |

### Modification Tools (10 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `move_body(body_id, x?, y?, z?)` | Translate body | Offset in mm |
| `rotate_body(body_id, axis, angle, origin_x?, ...)` | Rotate body | Axis: "X", "Y", "Z" |
| `modify_feature(feature_id, parameters)` | Change feature params | {"distance": 20} |
| `update_parameter(name, expression)` | Update parameter | "50 mm", "d1 * 2" |
| `delete_body(body_id)` | Remove body | Creates Remove feature |
| `delete_feature(feature_id)` | Remove from timeline | May affect dependents |
| `edit_sketch(sketch_id, curve_id, properties)` | Modify curve | {"radius": 25} |
| `combine(target_body_id, tool_body_ids, operation?, keep_tools?)` | Boolean combine | "join", "cut", "intersect" |
| `split_body(body_id, splitting_tool, extend?)` | Split into parts | "XY"/"YZ"/"XZ" or face_id |
| `shell(body_id, face_ids, thickness, direction?)` | Create hollow shell | Remove faces, add walls |

### Validation Tools (5 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `measure_distance(entity1_id, entity2_id)` | Minimum distance | Returns mm |
| `measure_angle(entity1_id, entity2_id)` | Angle between | Returns degrees |
| `check_interference(body_ids?)` | Find collisions | All bodies if omitted |
| `get_body_properties(body_id)` | Volume, area, etc. | Full physical props |
| `get_sketch_status(sketch_id)` | Constraint status | profiles_count important |

### System Tools (2 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `check_health()` | Verify connection | None |
| `get_version()` | Get version info | None |

### Viewport Tools (5 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `take_screenshot(file_path, view?, width?, height?)` | Capture image | Saves to file |
| `set_camera(eye_x, eye_y, eye_z, ...)` | Position camera | Coordinates in mm |
| `get_camera()` | Get camera state | None |
| `set_view(view)` | Standard view | "isometric", "top", etc. |
| `fit_view(entity_ids?)` | Fit to geometry | None = all |

### Assembly Tools (11 tools)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `create_component(name)` | Create component | Descriptive name |
| `get_components()` | List components | None |
| `get_component_by_id(component_id)` | Component details | Include body/sketch IDs |
| `activate_component(component_id)` | Set active | New geometry goes here |
| `get_component_bodies(component_id)` | Bodies in component | For assembly ops |
| `get_occurrences(component_id?)` | List instances | Filter by component |
| `move_occurrence(occurrence_id, x?, y?, z?)` | Position instance | Relative move |
| `create_joint(geometry1_id, geometry2_id, joint_type?)` | Connect by geometry | Face/edge IDs |
| `create_joint_between_occurrences(occ1_id, occ2_id, joint_type?)` | Connect at origins | Simpler joint creation |
| `get_joints()` | List all joints | None |
| `get_joint_by_id(joint_id)` | Joint details | Full info |

---

## 2. Decision Trees

### What Tool Do I Need?

```
What is your goal?
│
├── [Understand the design]
│   ├── Overview? → get_design_state()
│   ├── What bodies exist? → get_bodies()
│   ├── Body details? → get_body_by_id(include_faces=True)
│   ├── What sketches exist? → get_sketches()
│   └── Design history? → get_timeline()
│
├── [Create geometry]
│   ├── Simple primitive?
│   │   ├── Box → create_box()
│   │   ├── Cylinder → create_cylinder()
│   │   ├── Sphere → create_sphere()
│   │   └── Donut → create_torus()
│   │
│   ├── Custom 2D→3D?
│   │   └── create_sketch() → draw_*() → extrude()/revolve()
│   │
│   ├── Along a path?
│   │   ├── Solid → sweep()
│   │   └── Hollow → create_pipe()
│   │
│   ├── Between profiles?
│   │   └── loft() [requires target_body_id for cut/join]
│   │
│   └── Pattern/Array?
│       ├── In sketch → sketch_circular/rectangular_pattern()
│       └── 3D bodies → circular/rectangular_pattern()
│
├── [Modify geometry]
│   ├── Move/position → move_body() or move_occurrence()
│   ├── Rotate → rotate_body()
│   ├── Round edges → fillet()
│   ├── Bevel edges → chamfer()
│   ├── Change dimension → modify_feature() or update_parameter()
│   ├── Delete → delete_body() or delete_feature()
│   ├── Boolean combine bodies → combine() with "join"/"cut"/"intersect"
│   ├── Split body in half → split_body()
│   ├── Make hollow shell → shell()
│   ├── Add mold draft → draft()
│   ├── Resize/scale → scale()
│   ├── Push/pull faces → offset_face()
│   └── Split face → split_face()
│
├── [Validate design]
│   ├── Check spacing → measure_distance()
│   ├── Check angle → measure_angle()
│   ├── Check collisions → check_interference()
│   └── Verify dimensions → get_body_properties()
│
├── [Visualize]
│   ├── Capture image → take_screenshot()
│   ├── Change view → set_view("isometric")
│   └── Fit to see all → fit_view()
│
└── [Assembly]
    ├── Create part → create_component() → activate_component()
    ├── Position part → move_occurrence()
    └── Connect parts → create_joint() or create_joint_between_occurrences()
```

### How to Create a Custom Shape?

```
Starting from scratch:
│
├── 1. Create sketch
│   └── create_sketch(plane="XY")
│
├── 2. Draw geometry (one or more)
│   ├── draw_circle()      → Closed profile ✓
│   ├── draw_rectangle()   → Closed profile ✓
│   ├── draw_polygon()     → Closed profile ✓
│   ├── draw_ellipse()     → Closed profile ✓
│   └── draw_line() × 4    → Close manually for profile
│
├── 3. Verify profiles
│   └── get_sketch_status() → Check profiles_count > 0
│
└── 4. Create 3D body
    ├── Straight → extrude(distance=X)
    ├── Around axis → revolve(axis="Y")
    ├── Along path → sweep(path_sketch_id=...)
    └── Between shapes → loft(sketch_ids=[...])
```

---

## 3. Recipe Patterns

### Recipe 1: Box with Rounded Edges

```
Goal: Create a 100×50×10mm box with 3mm filleted edges

1. Create box
   create_box(width=100, depth=50, height=10)
   → Returns: body_id

2. Get edge IDs
   get_body_by_id(body_id, include_edges=True)
   → Returns: edges array with IDs

3. Apply fillet
   fillet(body_id, edge_ids=[...], radius=3)
```

### Recipe 2: Custom Extruded Shape with Hole

```
Goal: Create an L-bracket with a mounting hole

1. Create sketch
   create_sketch(plane="XY")
   → Returns: sketch_id

2. Draw L-shape (3 lines to form L)
   draw_line(sketch_id, start_x=0, start_y=0, end_x=40, end_y=0)
   draw_line(sketch_id, start_x=40, start_y=0, end_x=40, end_y=10)
   draw_line(sketch_id, start_x=40, start_y=10, end_x=10, end_y=10)
   draw_line(sketch_id, start_x=10, start_y=10, end_x=10, end_y=30)
   draw_line(sketch_id, start_x=10, start_y=30, end_x=0, end_y=30)
   draw_line(sketch_id, start_x=0, start_y=30, end_x=0, end_y=0)

3. Verify closed profile
   get_sketch_status(sketch_id)
   → Check: profiles_count >= 1

4. Extrude
   extrude(sketch_id, distance=5)
   → Returns: body_id

5. Add hole
   create_hole(body_id=body_id, diameter=6, depth=5, x=5, y=5)
```

### Recipe 3: Pipe Along Curved Path

```
Goal: Create a 90° elbow pipe with 20mm OD, 2mm wall

1. Create path sketch
   create_sketch(plane="XZ")
   → Returns: path_sketch_id

2. Draw arc for path
   draw_arc(path_sketch_id, center_x=0, center_y=0, radius=50,
            start_angle=0, end_angle=90)

3. Create pipe
   create_pipe(path_sketch_id, outer_diameter=20, wall_thickness=2)
```

### Recipe 4: Loft Between Shapes (Hollow)

```
Goal: Create hollow tapered container (square bottom to circle top)

1. Create bottom sketch
   create_sketch(plane="XY", offset=0)
   → Returns: bottom_sketch_id
   draw_rectangle(bottom_sketch_id, x1=-25, y1=-25, x2=25, y2=25)

2. Create top sketch
   create_sketch(plane="XY", offset=50)
   → Returns: top_sketch_id
   draw_circle(top_sketch_id, center_x=0, center_y=0, radius=15)

3. Create outer loft (solid)
   loft(sketch_ids=[bottom_sketch_id, top_sketch_id])
   → Returns: outer_body_id

4. Create inner sketches (smaller)
   create_sketch(plane="XY", offset=0)
   → Returns: inner_bottom_id
   draw_rectangle(inner_bottom_id, x1=-22, y1=-22, x2=22, y2=22)

   create_sketch(plane="XY", offset=50)
   → Returns: inner_top_id
   draw_circle(inner_top_id, center_x=0, center_y=0, radius=12)

5. Cut inner loft (REQUIRES target_body_id)
   loft(sketch_ids=[inner_bottom_id, inner_top_id],
        operation="cut",
        target_body_id=outer_body_id)
```

### Recipe 5: Circular Pattern of Holes

```
Goal: Create 6 mounting holes in circular pattern

1. Create base plate
   create_cylinder(radius=50, height=10)
   → Returns: body_id

2. Create first hole
   create_hole(body_id=body_id, diameter=5, depth=10, x=35, y=0)
   → Returns: feature_id

3. Pattern the hole
   circular_pattern(
       entity_ids=[feature_id],
       entity_type="features",
       axis="Z",
       count=6
   )
   → Creates 6 evenly spaced holes
```

---

## 4. Common Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| "No profiles found" for extrude | Sketch curves not closed | Close all curves to form loop |
| Loft cut doesn't work | Missing `target_body_id` | Add `target_body_id=<body_id>` for cut/join/intersect |
| Text won't extrude | `add_sketch_text` creates SketchText, not profiles | Use shapes instead, or use emboss for text |
| Fillet fails | Radius too large for edge | Reduce radius to ≤ half of smallest face |
| Can't find edges for fillet | Didn't request edge data | Use `get_body_by_id(include_edges=True)` |
| create_coil fails | API not supported | Use sweep with helical path instead |
| emboss fails | SketchText has no profiles | Create text outlines manually or use alternative |
| Torus creation fails | `minor_radius >= major_radius` | Ensure minor_radius < major_radius |
| Pipe fails | `wall_thickness >= outer_diameter/2` | Reduce wall thickness |
| Pattern creates single instance | Count < 2 | Set count >= 2 |

---

## 5. Unit Conventions

| Measurement | Unit | Minimum | Notes |
|-------------|------|---------|-------|
| All distances | mm | > 0.001 | Precision: 0.001mm (1 micron) |
| Angles | degrees | - | 0-360 for full revolution |
| Radius/Diameter | mm | > 0.001 | Must be positive |
| Spacing | mm | > 0.001 | Pattern spacing |

### Coordinate System
- **X**: Right (+) / Left (-)
- **Y**: Forward (+) / Back (-)
- **Z**: Up (+) / Down (-)
- **Origin**: (0, 0, 0) at center

---

## 6. ID Naming Conventions

| Entity Type | ID Format | Example |
|-------------|-----------|---------|
| Body | `body_N` or custom name | `body_0`, `base_plate` |
| Sketch | `SketchN` | `Sketch1`, `Sketch2` |
| Sketch Curve | `{sketch_id}_{type}_{index}` | `Sketch1_line_0`, `Sketch1_circle_0` |
| Face | `{body_id}_face_{index}` | `body_0_face_0` |
| Edge | `{body_id}_edge_{index}` | `body_0_edge_0` |
| Feature | Feature name from timeline | `Extrude1`, `Fillet1` |
| Component | Component name | `Bracket`, `Housing` |
| Occurrence | `{ComponentName}:{index}` | `Bracket:1`, `Bolt:3` |
| Joint | `{JointType}{index}` | `Rigid1`, `Revolute1` |

---

## 7. Workflow Checklist

### Before Creating Geometry
- [ ] Called `get_design_state()` to understand context
- [ ] Checked existing bodies with `get_bodies()`
- [ ] Know what component is active

### Before Extruding/Revolving
- [ ] Sketch has closed profiles (`profiles_count > 0`)
- [ ] Used `get_sketch_status()` to verify

### Before Fillet/Chamfer
- [ ] Got edge IDs with `get_body_by_id(include_edges=True)`
- [ ] Radius is appropriate for edge size

### Before Loft Cut/Join
- [ ] Set `operation="cut"` or `"join"`
- [ ] Provided `target_body_id` parameter

### Before Pattern
- [ ] Have correct entity_ids (body IDs or feature IDs)
- [ ] Set `entity_type` correctly ("bodies" or "features")
- [ ] Count >= 2

### After Any Modification
- [ ] Verify with `get_body_properties()` if needed
- [ ] Use `take_screenshot()` to visualize
- [ ] Check for interferences if multiple bodies

---

## 8. Error Recovery

### Problem: Operation Failed

```
1. Read error message carefully
2. Check parameter constraints (see Gotchas table)
3. Verify entity IDs exist:
   - get_bodies() for body IDs
   - get_sketches() for sketch IDs
   - get_body_by_id(include_faces=True) for face IDs
4. Try simpler parameters first
```

### Problem: Design in Bad State

```
1. Check timeline health:
   get_timeline()
   → Look for health_state: "error"

2. Try deleting problematic feature:
   delete_feature(feature_id)

3. Or start fresh with new primitive
```

### Problem: Can't Find Geometry

```
1. Query current state:
   get_design_state()

2. List all bodies:
   get_bodies()

3. For specific body topology:
   get_body_by_id(body_id, include_faces=True, include_edges=True)

4. Visualize:
   set_view("isometric")
   take_screenshot()
```

### Problem: Fusion 360 Connection Issues

```
1. Check health:
   check_health()

2. Verify versions:
   get_version()

3. If unhealthy, restart Fusion 360 add-in
```

---

## Quick Reference Card

### Most Common Operations

| Task | Tool | Critical Parameters |
|------|------|---------------------|
| Create box | `create_box` | width, depth, height |
| Create cylinder | `create_cylinder` | radius, height |
| Make sketch | `create_sketch` | plane="XY"/"YZ"/"XZ" |
| Draw circle | `draw_circle` | sketch_id, radius |
| Extrude | `extrude` | sketch_id, distance |
| Round edges | `fillet` | body_id, edge_ids, radius |
| Check dimensions | `get_body_properties` | body_id |
| Take picture | `take_screenshot` | file_path, view="isometric" |

### Critical Constraints

| Operation | Constraint |
|-----------|------------|
| All dimensions | > 0.001 mm |
| Torus | minor_radius < major_radius |
| Pipe | wall_thickness < outer_diameter/2 |
| Loft cut/join | **requires target_body_id** |
| Polygon sides | 3-64 |
| Extrude/Revolve | Sketch needs closed profiles |
| Fillet radius | ≤ half smallest adjacent face |
