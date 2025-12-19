# Fusion 360 MCP Server User Guide

This guide explains how AI assistants can effectively use the Fusion 360 MCP Server to create and modify CAD designs.

## Getting Started

### Prerequisites

1. Fusion 360 installed and running
2. FusionMCP add-in loaded
3. MCP Server connected to your AI assistant

### Verifying Connection

Always start by checking the connection:

```
check_health()
```

Expected response:
```json
{
  "healthy": true,
  "server_status": "running",
  "addin_status": "healthy"
}
```

## Workflow Best Practices

### 1. Always Query First

Before creating or modifying anything, understand the current design state:

```
get_design_state()
```

This tells you:
- Design name and units
- How many bodies, sketches, and components exist
- Current timeline position

### 2. Use Entity IDs

Every entity (body, sketch, face, edge) has a unique ID. These IDs are:
- Stable across queries
- Required for modifications
- Returned by creation operations

Example workflow:
```python
# Create a box
result = create_box(width=100, depth=50, height=20, name="base_plate")
body_id = result["body_id"]  # Save this!

# Use the ID for modifications
move_body(body_id=body_id, x=10, y=0, z=0)
```

### 3. Verify After Changes

After creating or modifying geometry, verify the result:

```python
# After creating a box
body = get_body_by_id(body_id=body_id)
print(body["volume"])  # Should match expected volume

# After moving
properties = get_body_properties(body_id=body_id)
print(properties["center_of_mass"])  # Check new position
```

## Design Workflows

### Creating a Simple Part

**Goal:** Create a 100x50x10mm mounting plate with 4 holes.

```python
# 1. Check starting state
state = get_design_state()
assert state["bodies_count"] == 0

# 2. Create the base plate
plate = create_box(
    width=100, depth=50, height=10,
    name="mounting_plate"
)
plate_id = plate["body_id"]

# 3. Verify dimensions
props = get_body_properties(body_id=plate_id)
assert abs(props["volume"] - 50000) < 0.1  # 100*50*10

# 4. Get the top face for holes
body = get_body_by_id(body_id=plate_id, include_faces=True)
top_face = next(f for f in body["faces"] if f["type"] == "planar")

# 5. Create mounting holes at corners
hole_positions = [
    (15, 15),   # Bottom-left
    (85, 15),   # Bottom-right
    (15, 35),   # Top-left
    (85, 35),   # Top-right
]

for x, y in hole_positions:
    create_hole(
        diameter=6,  # M6 clearance
        depth=10,    # Through hole
        face_id=top_face["id"],
        x=x - 50,    # Relative to center
        y=y - 25,
    )

# 6. Final verification
state = get_design_state()
assert state["bodies_count"] == 1
```

### Creating Custom Shapes with Sketches

For shapes that aren't simple primitives:

```python
# 1. Create a sketch on the XY plane
sketch = create_sketch(plane="XY", name="bracket_profile")
sketch_id = sketch["sketch_id"]

# 2. Draw the profile
draw_rectangle(sketch_id=sketch_id, x1=0, y1=0, x2=50, y2=30)
draw_circle(sketch_id=sketch_id, center_x=25, center_y=15, radius=10)

# 3. Check sketch status
status = get_sketch_status(sketch_id=sketch_id)
print(f"Profiles available: {status['profiles_count']}")

# 4. Extrude to create solid
result = extrude(
    sketch_id=sketch_id,
    distance=5,
    operation="new_body",
    name="bracket"
)

# If you need the outer profile minus the circle:
result = extrude(
    sketch_id=sketch_id,
    distance=5,
    profile_index=0,  # Usually the outer profile
    operation="new_body"
)
```

### Adding Edge Features

```python
# 1. Get the body with edges
body = get_body_by_id(body_id=body_id, include_edges=True)

# 2. Find edges to fillet (e.g., all vertical edges)
vertical_edges = [
    e["id"] for e in body["edges"]
    if e["type"] == "linear" and abs(e["direction"]["z"]) > 0.9
]

# 3. Apply fillet
fillet(body_id=body_id, edge_ids=vertical_edges, radius=2.0)
```

### Assembly Operations

```python
# 1. Create components
comp1 = create_component(name="Housing")
comp2 = create_component(name="Cover")

# 2. Create geometry in each component
activate_component(component_id=comp1["component_id"])
create_box(width=100, depth=100, height=50, name="housing_body")

activate_component(component_id=comp2["component_id"])
create_box(width=100, depth=100, height=10, name="cover_body")

# 3. Position components
move_occurrence(
    occurrence_id=comp2["occurrence_id"],
    x=0, y=0, z=50
)

# 4. Create joint
create_joint(
    occurrence1_id=comp1["occurrence_id"],
    occurrence2_id=comp2["occurrence_id"],
    joint_type="rigid"
)
```

## Validation Techniques

### Dimensional Verification

```python
# Verify distance between holes
dist = measure_distance(entity1_id="hole_1", entity2_id="hole_2")
assert abs(dist["distance"] - 70) < 0.01  # Expected 70mm

# Verify perpendicularity
angle = measure_angle(entity1_id=face1_id, entity2_id=face2_id)
assert abs(angle["angle"] - 90) < 0.01
```

### Interference Checking

```python
# Check all bodies for collisions
result = check_interference()
if result["has_interference"]:
    for interference in result["interferences"]:
        print(f"Collision: {interference['body1_id']} and {interference['body2_id']}")
        print(f"Overlap volume: {interference['overlap_volume']} mm³")

# Check specific bodies only
result = check_interference(body_ids=[body1_id, body2_id])
```

### Property Verification

```python
props = get_body_properties(body_id=body_id)

# Check volume (expected 50,000 mm³)
assert abs(props["volume"] - 50000) < 1

# Check bounding box dimensions
dims = props["dimensions"]
assert dims["x"] == 100
assert dims["y"] == 50
assert dims["z"] == 10

# Check center of mass
com = props["center_of_mass"]
assert abs(com["z"] - 5) < 0.1  # Half of height
```

## Modification Patterns

### Parametric Changes

When you need to change a dimension:

```python
# Option 1: Modify the feature directly
modify_feature(
    feature_id=extrude_id,
    parameters={"distance": 30}  # Change height
)

# Option 2: Update a parameter (if defined)
update_parameter(name="height", expression="30 mm")
```

### Moving Geometry

```python
# Translate a body
move_body(body_id=body_id, x=10, y=20, z=0)

# Rotate around Z axis at origin
rotate_body(
    body_id=body_id,
    axis="Z",
    angle=45,
    origin_x=0, origin_y=0, origin_z=0
)

# Rotate around a body's center
props = get_body_properties(body_id=body_id)
com = props["center_of_mass"]
rotate_body(
    body_id=body_id,
    axis="Z",
    angle=45,
    origin_x=com["x"],
    origin_y=com["y"],
    origin_z=com["z"]
)
```

### Editing Sketches

```python
# Get sketch details
sketch = get_sketch_by_id(sketch_id=sketch_id)

# Modify a line's endpoint
edit_sketch(
    sketch_id=sketch_id,
    curve_id=line_id,
    properties={"end_x": 100, "end_y": 50}
)

# Modify a circle's radius
edit_sketch(
    sketch_id=sketch_id,
    curve_id=circle_id,
    properties={"radius": 15}
)
```

## Common Patterns

### Error Recovery

```python
try:
    result = create_hole(diameter=6, depth=10, x=50, y=50)
except EntityNotFoundError as e:
    # Face or body not found
    print(f"Entity not found. Available: {e.available_entities}")

except InvalidParameterError as e:
    # Bad parameter value
    print(f"Invalid {e.parameter_name}: {e.reason}")

except GeometryError as e:
    # Geometry operation failed
    print(f"Geometry error: {e.message}")
```

### Incremental Design

```python
def create_with_verification(create_fn, verify_fn, **kwargs):
    """Create geometry and verify result."""
    result = create_fn(**kwargs)

    # Allow Fusion to update
    state = get_design_state()

    # Verify
    if not verify_fn(result):
        # Rollback by deleting
        delete_body(body_id=result["body_id"])
        raise ValueError("Verification failed")

    return result
```

### Design Exploration

```python
# Save current state
initial_state = get_design_state()
initial_bodies = get_bodies()

# Try different approaches
for approach in approaches:
    # Apply approach
    apply_design(approach)

    # Check if valid
    if not check_interference()["has_interference"]:
        break

    # Rollback - delete new bodies
    current_bodies = get_bodies()
    for body in current_bodies:
        if body["id"] not in [b["id"] for b in initial_bodies]:
            delete_body(body_id=body["id"])
```

## Tips for AI Assistants

1. **Be methodical** - Query, create, verify in that order
2. **Track IDs** - Store entity IDs from creation operations
3. **Verify dimensions** - Use get_body_properties after creation
4. **Check interference** - Before finalizing multi-body designs
5. **Handle errors gracefully** - Use error context for recovery
6. **Use descriptive names** - Name bodies and features meaningfully
7. **Query topology when needed** - Only request faces/edges when required

## Example: Complete Bracket Design

```python
# Autonomous bracket design: 100x50x10mm plate with 4 M6 holes

# 1. Verify clean slate
state = get_design_state()
if state["bodies_count"] > 0:
    print("Warning: Design is not empty")

# 2. Create base plate
plate = create_box(
    width=100, depth=50, height=10,
    name="base_plate"
)
plate_id = plate["body_id"]

# 3. Verify dimensions
props = get_body_properties(body_id=plate_id)
expected_volume = 100 * 50 * 10
assert abs(props["volume"] - expected_volume) < 1, "Volume mismatch"

# 4. Get top face
body = get_body_by_id(body_id=plate_id, include_faces=True)
top_face = None
for face in body["faces"]:
    if face["type"] == "planar":
        # Check if normal points up (+Z)
        if face.get("normal", {}).get("z", 0) > 0.9:
            top_face = face
            break

# 5. Create holes at corners (15mm from edges)
hole_positions = [(-35, -10), (35, -10), (-35, 10), (35, 10)]
hole_ids = []

for i, (x, y) in enumerate(hole_positions):
    result = create_hole(
        diameter=6.6,  # M6 clearance
        depth=10,
        face_id=top_face["id"],
        x=x, y=y,
        name=f"hole_{i+1}"
    )
    hole_ids.append(result["feature_id"])

# 6. Verify hole spacing (should be 70mm horizontal)
dist = measure_distance(entity1_id=hole_ids[0], entity2_id=hole_ids[1])
assert abs(dist["distance"] - 70) < 0.1, f"Hole spacing: {dist['distance']}mm"

# 7. Check for interference (should be none)
interference = check_interference()
assert not interference["has_interference"], "Unexpected interference"

# 8. Final verification
state = get_design_state()
print(f"Design complete: {state['name']}")
print(f"Bodies: {state['bodies_count']}")
print(f"Features in timeline: {state['timeline_count']}")
```
