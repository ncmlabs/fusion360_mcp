# Fusion 360 MCP Server - Complete Rewrite Specification

## Executive Summary

**Purpose**: Enable fully autonomous AI-assisted CAD design in Fusion 360 with zero human intervention.

**Core Problem**: The current implementation makes the AI "blind" - it can create geometry but cannot see what exists, verify results, or make corrections. This breaks the design feedback loop.

**Solution**: Implement a complete Query → Create → Verify → Modify cycle that allows an AI agent to:
1. **See** the current design state (what bodies exist, their dimensions, positions)
2. **Create** geometry with explicit references (IDs) for later use
3. **Verify** that created geometry matches intent (measure, check interference)
4. **Modify** existing geometry when corrections are needed
5. **Iterate** until the design meets requirements

**End Goal**: An AI designer can receive a specification like "Create a mounting bracket with 4 holes for M6 bolts" and autonomously:
- Create the base plate
- Query to verify dimensions
- Add holes at correct positions
- Measure hole spacing to verify
- Adjust if needed
- Complete without human intervention

---

## Current Implementation (What Exists)

### Architecture
```
MCP Client (Claude) → MCP Server (Python/FastMCP) → HTTP → Fusion Add-in → Fusion API
```

### Current Files
- `MCP/MCP.py` - Fusion 360 Add-in (~1800 lines, monolithic)
- `Server/MCP_Server.py` - MCP Server using FastMCP

### Current Limitations
| Issue | Impact |
|-------|--------|
| AI is "blind" | Cannot query what exists in design |
| No entity references | Uses "last body" magic instead of IDs |
| Create-only | No modification or deletion of existing geometry |
| No verification | Cannot measure or check results |
| No error context | Errors don't tell AI how to fix them |
| Monolithic code | 1800 lines in one file, hard to maintain |

---

## API Research Findings

### Supported Languages
| Language | Status | Notes |
|----------|--------|-------|
| **Python** | Recommended | Cross-platform, most samples, easier debugging |
| **C++** | Supported | Requires separate Win/Mac compilation |
| JavaScript | Discontinued | Was supported, now removed |

**Decision: Use Python** - Same capabilities as C++, cross-platform, 90% of community samples are Python.

### Architecture Constraint
**No external REST API exists for Fusion 360 CAD.** Must run add-in inside Fusion 360.

Current architecture (add-in with HTTP server) is correct and the only viable approach:
```
MCP Client → MCP Server → HTTP → Fusion Add-in → Fusion API
```

### What the API CAN Do

| Category | Capabilities |
|----------|-------------|
| **Query** | Full design hierarchy: Application → Documents → Design → Components → Bodies/Sketches/Features |
| **Query** | BRepBody: faces, edges, vertices, bounding boxes, volume, area |
| **Query** | Sketches: curves, constraints, profiles, dimensions |
| **Query** | Parameters: all user/model parameters with values and expressions |
| **Query** | Timeline: feature history, suppression state |
| **Create** | All features: extrude, revolve, sweep, loft, fillet, chamfer, etc. |
| **Create** | Sketches and all sketch entities (lines, circles, arcs, splines) |
| **Create** | Components, occurrences, joints |
| **Modify** | Feature parameters via Definition objects |
| **Modify** | Move/rotate bodies via MoveFeature (Translate/Rotate types preserve params) |
| **Modify** | Sketch curve editing |
| **Modify** | Parameter values and expressions |
| **Delete** | All deletable objects support `deleteMe()` method |
| **Validate** | Evaluators for geometric queries (normals, parametric coords) |
| **Validate** | `isValid` to check object references |
| **Validate** | MeshManager for triangular representations |

### API Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Scripts block UI (main thread) | Use `adsk.doEvents()` for long operations | Keep operations atomic |
| Free Move doesn't preserve params | Use Translate/Rotate move types instead | Enforce specific move types |
| Custom Features in preview | May change before release | Avoid for now |
| No external REST API | Must run inside Fusion | HTTP server in add-in (current approach) |
| Arrays return "vector" not list | Need conversion for iteration | Use `list(vector)` |

### Key API Patterns

**Collections for access and creation:**
```python
bodies = component.bRepBodies  # Access all bodies
body = bodies.item(0)          # By index
body = bodies.itemByName("plate")  # By name
```

**Input objects for creation:**
```python
extInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(1.0))
extrude = extrudes.add(extInput)  # Returns ExtrudeFeature
```

**Definition objects for modification:**
```python
extDef = extrude.extentDefinition
# Modify via parameter objects
```

**Move bodies:**
```python
moveInput = moveFeats.createInput2(objectCollection)
moveInput.defineAsTranslate(vector)  # NOT defineAsFreeMove - preserves params
moveFeats.add(moveInput)
```

### Documentation Sources
- [Fusion API Reference Manual](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ReferenceManual_UM.htm)
- [Getting Started with Fusion's API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BasicConcepts_UM.htm)
- [Python Specific Issues](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonSpecific_UM.htm)
- [B-Rep and Geometry](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepGeometry_UM.htm)
- [Components and Proxies](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ComponentsProxies_UM.htm)

---

## New Architecture

### Current vs New

| Current | New |
|---------|-----|
| AI is "blind" - creates but can't see | Full design state queries |
| Create-only operations | Create + Modify + Delete |
| Magic "last body" references | Explicit entity IDs |
| Monolithic 1800-line file | Modular handler pattern |
| No constraint support | Sketch constraints |
| Single body only | Components + Assemblies |

### New File Structure

```
Autodesk-Fusion-360-MCP-Server/
├── Server/                        # MCP Server
│   ├── main.py                   # FastMCP entry point
│   ├── config.py
│   ├── models/                   # Pydantic data models
│   │   ├── geometry.py          # Point3D, BoundingBox, etc.
│   │   ├── body.py              # Body, Face, Edge
│   │   ├── sketch.py            # Sketch, Curve, Constraint
│   │   ├── feature.py           # Feature, Parameter
│   │   └── design_state.py      # Complete state
│   ├── tools/                    # MCP Tools by category
│   │   ├── query_tools.py
│   │   ├── creation_tools.py
│   │   ├── modification_tools.py
│   │   ├── validation_tools.py
│   │   └── assembly_tools.py
│   └── services/
│       └── fusion_client.py     # HTTP client
│
├── FusionAddin/                  # Fusion 360 Add-in
│   ├── FusionMCP.py             # Entry point
│   ├── core/
│   │   ├── event_manager.py     # Event handling
│   │   ├── task_queue.py        # Thread-safe queue
│   │   └── http_server.py       # HTTP server
│   ├── handlers/                 # Request handlers
│   │   ├── query_handlers.py
│   │   ├── creation_handlers.py
│   │   └── modification_handlers.py
│   ├── operations/               # Fusion API operations
│   │   ├── body_ops.py
│   │   ├── sketch_ops.py
│   │   └── feature_ops.py
│   └── serializers/              # Fusion → JSON
│       ├── body_serializer.py
│       └── sketch_serializer.py
│
└── shared/                       # Shared schemas
    └── api_schema.py
```

---

## Tool Categories

### 1. Query Tools (NEW - Critical for Feedback Loop)
| Tool | Purpose |
|------|---------|
| `get_design_state` | Full snapshot of design |
| `get_bodies` | List all bodies with dimensions, positions |
| `get_body_by_id` | Get specific body details |
| `get_sketches` | List all sketches with profiles |
| `get_timeline` | Feature history |
| `get_parameters` | All parameters |

### 2. Creation Tools (Enhanced with IDs)
| Tool | Returns |
|------|---------|
| `create_box` | Body ID + Feature ID + dimensions |
| `create_cylinder` | Body ID + Feature ID |
| `create_sketch` | Sketch ID |
| `create_hole` | Feature ID |
| `extrude` | Body ID + Feature ID |
| All tools return **references** for later use |

### 3. Modification Tools (NEW)
| Tool | Purpose |
|------|---------|
| `modify_feature` | Change feature parameters |
| `move_body` | Translate body by ID |
| `rotate_body` | Rotate body by ID |
| `edit_sketch` | Modify sketch curves |
| `delete_body` | Remove specific body |
| `delete_feature` | Remove feature from timeline |
| `update_parameter` | Change parameter value |

### 4. Validation Tools (NEW)
| Tool | Purpose |
|------|---------|
| `measure_distance` | Distance between entities |
| `check_interference` | Detect collisions |
| `get_body_properties` | Volume, area, center of mass |

### 5. Assembly Tools (NEW)
| Tool | Purpose |
|------|---------|
| `create_component` | New component |
| `create_joint` | Joint between components |
| `move_occurrence` | Position component |

---

## Autonomous AI Design Workflow (The Feedback Loop)

The core innovation is enabling a complete feedback loop. Here's how an AI designer operates:

### The Design Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    AI DESIGN LOOP                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. QUERY STATE                                             │
│     ├── get_design_state() → What exists now?               │
│     ├── get_bodies() → List all bodies with dimensions      │
│     └── get_parameters() → What parameters exist?           │
│                    ↓                                        │
│  2. PLAN                                                    │
│     └── AI decides what to create/modify based on state     │
│                    ↓                                        │
│  3. EXECUTE                                                 │
│     ├── create_box(name="base_plate", ...)                  │
│     │   → Returns: body_id, feature_id, bounding_box        │
│     └── Store references for later use                      │
│                    ↓                                        │
│  4. VERIFY                                                  │
│     ├── get_body_by_id("base_plate") → Check dimensions     │
│     ├── measure_distance(entity1, entity2) → Check spacing  │
│     └── check_interference() → No collisions?               │
│                    ↓                                        │
│  5. CORRECT (if needed)                                     │
│     ├── move_body("base_plate", x=5) → Adjust position      │
│     ├── modify_feature("extrude1", height=20) → Fix dims    │
│     └── delete_body("wrong_part") → Remove mistakes         │
│                    ↓                                        │
│  6. LOOP BACK TO STEP 1 until design complete               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Example: Autonomous Bracket Design

**User Request**: "Create a mounting bracket: 100x50x10mm plate with 4 M6 mounting holes at corners, 15mm from edges"

**AI Execution (No Human Intervention)**:

```
Step 1: Query current state
→ get_design_state()
→ Response: {"bodies": [], "sketches": [], "components": 1}
→ AI knows: Empty design, ready to start

Step 2: Create base plate
→ create_box(width=100, depth=50, height=10, name="base_plate")
→ Response: {
    "body_id": "base_plate",
    "feature_id": "Extrude1",
    "bounding_box": {"min": [0,0,0], "max": [100,50,10]}
  }

Step 3: Verify base plate
→ get_body_by_id("base_plate")
→ Response confirms: 100x50x10mm ✓

Step 4: Calculate hole positions
→ AI calculates: corners at 15mm from edges
  - Hole 1: (15, 15)
  - Hole 2: (85, 15)
  - Hole 3: (15, 35)
  - Hole 4: (85, 35)

Step 5: Create holes
→ create_hole(body_id="base_plate", x=15, y=15, diameter=6.5, depth=10, name="hole_1")
→ create_hole(body_id="base_plate", x=85, y=15, diameter=6.5, depth=10, name="hole_2")
→ create_hole(body_id="base_plate", x=15, y=35, diameter=6.5, depth=10, name="hole_3")
→ create_hole(body_id="base_plate", x=85, y=35, diameter=6.5, depth=10, name="hole_4")

Step 6: Verify hole spacing
→ measure_distance("hole_1", "hole_2")
→ Response: 70mm (85-15=70) ✓
→ measure_distance("hole_1", "hole_3")
→ Response: 20mm (35-15=20) ✓

Step 7: Final verification
→ get_design_state()
→ Response: {
    "bodies": [{"name": "base_plate", "volume": 48400, ...}],
    "features": ["Extrude1", "Hole1", "Hole2", "Hole3", "Hole4"]
  }

Step 8: Complete
→ AI reports: "Bracket created with 4 M6 holes at 15mm from edges"
```

---

## Detailed Tool Specifications

### Query Tools

#### `get_design_state`
**Purpose**: Get complete snapshot of current design
**Parameters**: None
**Returns**:
```json
{
  "success": true,
  "design": {
    "name": "MyDesign",
    "units": "mm",
    "bodies_count": 3,
    "sketches_count": 2,
    "components_count": 1,
    "parameters_count": 15
  },
  "root_component": {
    "name": "Root",
    "bodies": ["body_001", "body_002", "body_003"],
    "sketches": ["sketch_001", "sketch_002"]
  }
}
```

#### `get_bodies`
**Purpose**: List all bodies with full geometric information
**Parameters**:
- `component_id` (optional): Filter to specific component
**Returns**:
```json
{
  "success": true,
  "bodies": [
    {
      "id": "body_001",
      "name": "base_plate",
      "is_solid": true,
      "bounding_box": {
        "min": {"x": 0, "y": 0, "z": 0},
        "max": {"x": 100, "y": 50, "z": 10}
      },
      "dimensions": {"width": 100, "depth": 50, "height": 10},
      "volume": 50000.0,
      "area": 13000.0,
      "center_of_mass": {"x": 50, "y": 25, "z": 5},
      "faces_count": 6,
      "edges_count": 12,
      "vertices_count": 8
    }
  ]
}
```

#### `get_body_by_id`
**Purpose**: Get detailed information about a specific body
**Parameters**:
- `body_id` (required): The body identifier
- `include_faces` (optional, default false): Include face details
- `include_edges` (optional, default false): Include edge details
**Returns**:
```json
{
  "success": true,
  "body": {
    "id": "body_001",
    "name": "base_plate",
    "bounding_box": {...},
    "volume": 50000.0,
    "faces": [
      {"id": "face_001", "area": 5000.0, "normal": {"x": 0, "y": 0, "z": 1}},
      ...
    ]
  }
}
```

#### `get_sketches`
**Purpose**: List all sketches with profile information
**Parameters**:
- `component_id` (optional): Filter to specific component
**Returns**:
```json
{
  "success": true,
  "sketches": [
    {
      "id": "sketch_001",
      "name": "Sketch1",
      "plane": "XY",
      "origin": {"x": 0, "y": 0, "z": 0},
      "is_fully_constrained": true,
      "profiles_count": 1,
      "curves_count": 4
    }
  ]
}
```

#### `get_parameters`
**Purpose**: Get all design parameters
**Parameters**: None
**Returns**:
```json
{
  "success": true,
  "parameters": [
    {
      "name": "plate_width",
      "expression": "100 mm",
      "value": 100.0,
      "unit": "mm",
      "is_user_parameter": true
    },
    {
      "name": "d1",
      "expression": "plate_width / 2",
      "value": 50.0,
      "unit": "mm",
      "is_user_parameter": false
    }
  ]
}
```

#### `get_timeline`
**Purpose**: Get feature history
**Parameters**: None
**Returns**:
```json
{
  "success": true,
  "timeline": [
    {"index": 0, "name": "Sketch1", "type": "Sketch", "is_suppressed": false},
    {"index": 1, "name": "Extrude1", "type": "ExtrudeFeature", "is_suppressed": false},
    {"index": 2, "name": "Fillet1", "type": "FilletFeature", "is_suppressed": false}
  ]
}
```

### Creation Tools

#### `create_box`
**Purpose**: Create a box/rectangular prism
**Parameters**:
- `width` (required): X dimension in mm
- `depth` (required): Y dimension in mm
- `height` (required): Z dimension in mm
- `x`, `y`, `z` (optional): Center position, default (0,0,0)
- `name` (optional): Name for the body
- `plane` (optional): "XY", "YZ", "XZ", default "XY"
**Returns**:
```json
{
  "success": true,
  "body": {
    "id": "body_001",
    "name": "base_plate",
    "bounding_box": {"min": [-50,-25,0], "max": [50,25,10]}
  },
  "feature": {
    "id": "Extrude1",
    "type": "ExtrudeFeature"
  }
}
```

#### `create_cylinder`
**Purpose**: Create a cylinder
**Parameters**:
- `radius` (required): Cylinder radius in mm
- `height` (required): Cylinder height in mm
- `x`, `y`, `z` (optional): Center of base position
- `name` (optional): Name for the body
- `plane` (optional): Orientation plane
**Returns**: Same format as create_box

#### `create_sketch`
**Purpose**: Create a new sketch
**Parameters**:
- `plane` (required): "XY", "YZ", "XZ" or face_id
- `name` (optional): Sketch name
**Returns**:
```json
{
  "success": true,
  "sketch": {
    "id": "sketch_001",
    "name": "Sketch1",
    "plane": "XY"
  }
}
```

#### `create_hole`
**Purpose**: Create a hole in an existing body
**Parameters**:
- `body_id` or `face_id` (required): Target for hole
- `x`, `y` (required): Position on face in mm
- `diameter` (required): Hole diameter in mm
- `depth` (required): Hole depth in mm
- `name` (optional): Feature name
- `hole_type` (optional): "simple", "counterbore", "countersink"
**Returns**:
```json
{
  "success": true,
  "feature": {
    "id": "Hole1",
    "type": "HoleFeature",
    "diameter": 6.5,
    "depth": 10
  }
}
```

#### `extrude`
**Purpose**: Extrude a sketch profile
**Parameters**:
- `sketch_id` (required): Source sketch
- `profile_index` (optional): Which profile, default 0
- `distance` (required): Extrusion distance in mm
- `direction` (optional): "positive", "negative", "symmetric"
- `operation` (optional): "new_body", "join", "cut", "intersect"
- `name` (optional): Feature name
**Returns**: Same format as create_box

### Modification Tools

#### `move_body`
**Purpose**: Translate a body
**Parameters**:
- `body_id` (required): Body to move
- `x`, `y`, `z` (required): Translation vector in mm
**Returns**:
```json
{
  "success": true,
  "feature": {"id": "Move1", "type": "MoveFeature"},
  "new_position": {
    "bounding_box": {"min": [10,0,0], "max": [110,50,10]}
  }
}
```

#### `rotate_body`
**Purpose**: Rotate a body
**Parameters**:
- `body_id` (required): Body to rotate
- `axis` (required): "X", "Y", "Z" or axis definition
- `angle` (required): Rotation angle in degrees
- `origin` (optional): Rotation center point
**Returns**: Similar to move_body

#### `modify_feature`
**Purpose**: Change feature parameters
**Parameters**:
- `feature_id` (required): Feature to modify
- `parameters` (required): Dict of parameter changes
**Returns**:
```json
{
  "success": true,
  "feature": {"id": "Extrude1"},
  "changes": {"distance": {"old": 10, "new": 20}}
}
```

#### `update_parameter`
**Purpose**: Change a parameter value
**Parameters**:
- `name` (required): Parameter name
- `expression` (required): New expression (e.g., "50 mm" or "d1 * 2")
**Returns**:
```json
{
  "success": true,
  "parameter": {
    "name": "plate_width",
    "old_value": 100.0,
    "new_value": 150.0,
    "expression": "150 mm"
  }
}
```

#### `delete_body`
**Purpose**: Delete a body
**Parameters**:
- `body_id` (required): Body to delete
**Returns**:
```json
{
  "success": true,
  "deleted": {"id": "body_001", "name": "old_part"}
}
```

#### `delete_feature`
**Purpose**: Delete a feature from timeline
**Parameters**:
- `feature_id` (required): Feature to delete
**Returns**: Similar to delete_body

### Validation Tools

#### `measure_distance`
**Purpose**: Measure minimum distance between entities
**Parameters**:
- `entity1_id` (required): First entity (body, face, edge, or point)
- `entity2_id` (required): Second entity
**Returns**:
```json
{
  "success": true,
  "distance": 25.5,
  "point1": {"x": 10, "y": 0, "z": 5},
  "point2": {"x": 35.5, "y": 0, "z": 5}
}
```

#### `check_interference`
**Purpose**: Check for body collisions
**Parameters**:
- `body_ids` (optional): List of bodies to check, default all
**Returns**:
```json
{
  "success": true,
  "has_interference": true,
  "interferences": [
    {
      "body1": "body_001",
      "body2": "body_002",
      "volume": 125.5
    }
  ]
}
```

#### `get_body_properties`
**Purpose**: Get physical properties of a body
**Parameters**:
- `body_id` (required): Body to analyze
**Returns**:
```json
{
  "success": true,
  "properties": {
    "volume": 50000.0,
    "area": 13000.0,
    "center_of_mass": {"x": 50, "y": 25, "z": 5},
    "bounding_box": {...}
  }
}
```

### Assembly Tools

#### `create_component`
**Purpose**: Create a new component
**Parameters**:
- `name` (required): Component name
- `transform` (optional): Initial position/orientation
**Returns**:
```json
{
  "success": true,
  "component": {"id": "comp_001", "name": "Bracket"},
  "occurrence": {"id": "occ_001"}
}
```

#### `create_joint`
**Purpose**: Create a joint between components
**Parameters**:
- `geometry1` (required): First joint geometry (face/edge/point)
- `geometry2` (required): Second joint geometry
- `joint_type` (optional): "rigid", "revolute", "slider", etc.
**Returns**:
```json
{
  "success": true,
  "joint": {
    "id": "joint_001",
    "type": "RigidJoint",
    "component1": "comp_001",
    "component2": "comp_002"
  }
}
```

---

## Entity Reference System

Every created entity returns a stable ID that can be used for subsequent operations:

```python
# Create returns ID
result = create_box(width=10, height=5, name="base")
# Returns: {"body_id": "body_001", "feature_id": "ext_001"}

# Use ID in queries
body = get_body_by_id("body_001")
# Returns: dimensions, position, faces, etc.

# Use ID in modifications
move_body("body_001", x=10, y=0, z=0)

# Use ID in measurements
measure_distance("body_001", "body_002")
```

---

## Response Format

### Success Response
```json
{
  "success": true,
  "body": {
    "id": "body_001",
    "name": "plate",
    "bounding_box": {"min": [0,0,0], "max": [100,50,10]},
    "volume": 50000.0
  },
  "feature": {"id": "ext_001", "type": "extrude"}
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "type": "EntityNotFound",
    "message": "Body 'body_999' does not exist",
    "context": {
      "requested_id": "body_999",
      "available_bodies": ["body_001", "body_002", "plate"]
    },
    "suggestion": "Use get_bodies() to see available bodies"
  }
}
```

---

## Error Handling Requirements

All errors must be informative and actionable:

### Error Types
| Type | When | Context Provided |
|------|------|------------------|
| `EntityNotFound` | Referenced ID doesn't exist | List of available entities |
| `InvalidParameter` | Parameter value out of range | Valid range, current value |
| `GeometryError` | Operation would create invalid geometry | What went wrong |
| `ConstraintError` | Sketch is over/under-constrained | Missing constraints |
| `FeatureError` | Feature creation failed | Fusion error message |
| `SelectionError` | Invalid selection for operation | Valid selection types |

### Error Example
```json
{
  "success": false,
  "error": {
    "type": "EntityNotFound",
    "message": "Body 'body_999' does not exist",
    "context": {
      "requested_id": "body_999",
      "available_bodies": ["body_001", "body_002", "plate"]
    },
    "suggestion": "Use get_bodies() to see available bodies"
  }
}
```

---

## Implementation Phases

### Phase 1: Foundation + Query Layer
**Goal**: AI can see current design state

Tasks:
1. Restructure into modular architecture (new folder structure)
2. Implement Pydantic data models for geometry, bodies, sketches
3. Query handlers in add-in:
   - `get_design_state`: `app.activeProduct` → Design → Components
   - `get_bodies`: `component.bRepBodies` collection + BoundingBox via evaluator
   - `get_sketches`: `component.sketches` collection + profiles
   - `get_timeline`: `design.timeline` + features
   - `get_parameters`: `design.allParameters` collection
4. Serializers: Convert Fusion API objects to JSON-safe dicts

**API calls used**:
```python
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
bodies = rootComp.bRepBodies
body.boundingBox.minPoint, body.boundingBox.maxPoint
body.volume, body.area
sketches = rootComp.sketches
timeline = design.timeline
params = design.allParameters
```

### Phase 2: Enhanced Creation
**Goal**: Creation with entity IDs and references

Tasks:
1. Refactor all creation tools to return body/feature IDs
2. Implement entity naming: `body.name = "plate"`, `feature.name = "extrude1"`
3. Unified PlaneSpec handling across all sketch/feature creation
4. Return bounding box and key properties with each creation

**API pattern**:
```python
extrude = extrudes.add(extInput)
return {
    "body_id": extrude.bodies.item(0).name,
    "feature_id": extrude.name,
    "bounding_box": serialize_bbox(body.boundingBox)
}
```

### Phase 3: Modification Layer
**Goal**: AI can modify existing geometry

Tasks:
1. `move_body`: Use `MoveFeatures.createInput2()` + `defineAsTranslate()`
2. `rotate_body`: Use `MoveFeatures.createInput2()` + `defineAsRotate()`
3. `modify_feature`: Access via `feature.extentDefinition` or similar
4. `update_parameter`: `param.expression = "new_value"`
5. `delete_body`: `body.deleteMe()`
6. `delete_feature`: `feature.deleteMe()`

**API pattern for move**:
```python
moveFeats = rootComp.features.moveFeatures
collection = adsk.core.ObjectCollection.create()
collection.add(body)
moveInput = moveFeats.createInput2(collection)
vector = adsk.core.Vector3D.create(x, y, z)
moveInput.defineAsTranslate(vector)
moveFeats.add(moveInput)
```

### Phase 4: Validation
**Goal**: AI can verify designs

Tasks:
1. `measure_distance`: Use `MeasureManager.measureMinimumDistance()`
2. `get_body_properties`: Volume, area, center of mass
3. `check_interference`: Use `InterferenceFeatures.analyzeInterference()`
4. Bounding box comparisons for dimension validation

**API calls**:
```python
measureMgr = app.measureManager
result = measureMgr.measureMinimumDistance(entity1, entity2)
interference = rootComp.features.interferenceFeatures.analyzeInterference(bodies)
```

### Phase 5: Assembly
**Goal**: Multi-component designs

Tasks:
1. `create_component`: `rootComp.occurrences.addNewComponent()`
2. `create_joint`: `joints.createInput()` + `joints.add()`
3. `move_occurrence`: Occurrence transform manipulation
4. Component isolation/activation

**API pattern**:
```python
occurrence = rootComp.occurrences.addNewComponent(transform)
component = occurrence.component
jointInput = joints.createInput(jointGeometry1, jointGeometry2)
joint = joints.add(jointInput)
```

### Phase 6: Polish
**Goal**: Production-ready system

Tasks:
1. Performance optimization (batch operations, reduce round-trips)
2. Comprehensive error handling with helpful messages
3. Integration tests with actual Fusion 360
4. Documentation and examples

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `Server/models/*.py` | Create - Data models |
| `Server/tools/*.py` | Create - MCP tool definitions |
| `Server/services/fusion_client.py` | Create - HTTP client |
| `FusionAddin/core/*.py` | Create - Infrastructure |
| `FusionAddin/handlers/*.py` | Create - Request handlers |
| `FusionAddin/serializers/*.py` | Create - JSON conversion |
| `MCP/MCP.py` | Delete - Replace with new structure |
| `Server/MCP_Server.py` | Delete - Replace with new structure |

---

## Key Design Decisions

1. **Entity IDs over magic references**: No more "last body" - explicit IDs everywhere
2. **Rich return values**: Every operation returns what was created with full context
3. **Modular handlers**: Each handler category in its own file
4. **Pydantic models**: Type-safe data structures with validation
5. **Serialization layer**: Clean separation between Fusion API and JSON
6. **Unified plane handling**: Single PlaneSpec class used everywhere

---

## Critical Success Criteria

The rewrite is successful when:

1. **AI can query design state**: `get_design_state()` returns complete snapshot
2. **AI can verify dimensions**: Query body → get exact bounding box
3. **AI can measure**: `measure_distance()` returns precise measurements
4. **AI can modify**: Change feature parameters, move/rotate bodies
5. **AI can correct mistakes**: Delete and recreate entities
6. **AI can work without human**: Complete design loop autonomously
7. **Errors are actionable**: Every error tells AI how to fix it

### Test Scenario
Given prompt: "Create a 100x50x10mm plate with 4 corner holes, 10mm from edges, 5mm diameter"

AI must be able to:
- Create plate
- Verify dimensions match (100x50x10)
- Create 4 holes at calculated positions
- Verify hole positions are 10mm from edges
- If wrong, correct without human help
