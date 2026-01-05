# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-05

### Features

Initial release of Fusion 360 MCP Server - enabling AI assistants to interact with Autodesk Fusion 360 for CAD design.

#### Query Tools
- **get_design_state** - Get current design context (name, units, counts)
- **get_bodies** - List all bodies in the design or component
- **get_body_by_id** - Get detailed body information with faces/edges
- **get_sketches** - List all sketches
- **get_sketch_by_id** - Get detailed sketch geometry and constraints
- **get_parameters** - List design parameters
- **get_timeline** - Get feature history
- **get_components** - List design components
- **get_component_by_id** - Get component details
- **get_component_bodies** - Get bodies within a component
- **get_occurrences** - List component occurrences
- **get_joints** - List assembly joints
- **get_joint_by_id** - Get joint details

#### Creation Tools
- **create_box** - Create rectangular prism
- **create_cylinder** - Create cylinder
- **create_sphere** - Create sphere
- **create_torus** - Create torus/ring shape
- **create_sketch** - Create new sketch on plane
- **create_hole** - Create cylindrical hole
- **create_component** - Create new component
- **create_joint** - Create assembly joint
- **create_joint_between_occurrences** - Create joint between occurrence origins
- **create_offset_plane** - Create construction plane offset from base
- **create_angle_plane** - Create construction plane at angle from edge
- **create_three_point_plane** - Create construction plane through 3 points
- **create_midplane** - Create construction plane between two parallel planes
- **create_pipe** - Create hollow pipe along path
- **create_thread** - Add threads to cylindrical face

#### Sketch Tools
- **draw_line** - Draw line segment
- **draw_circle** - Draw circle
- **draw_rectangle** - Draw rectangle
- **draw_arc** - Draw arc
- **draw_polygon** - Draw regular polygon
- **draw_ellipse** - Draw ellipse
- **draw_slot** - Draw slot shape
- **draw_spline** - Draw spline through points
- **draw_point** - Draw point
- **add_sketch_text** - Add text to sketch
- **sketch_mirror** - Mirror sketch curves
- **sketch_circular_pattern** - Create circular pattern of curves
- **sketch_rectangular_pattern** - Create rectangular pattern of curves
- **project_geometry** - Project edges/faces onto sketch
- **wrap_sketch_to_surface** - Project sketch curves onto curved surfaces

#### Sketch Constraints
- **add_constraint_horizontal** - Constrain line to horizontal
- **add_constraint_vertical** - Constrain line to vertical
- **add_constraint_coincident** - Make points coincident
- **add_constraint_perpendicular** - Make lines perpendicular
- **add_constraint_parallel** - Make lines parallel
- **add_constraint_tangent** - Make curves tangent
- **add_constraint_equal** - Make curves equal size
- **add_constraint_concentric** - Make circles concentric
- **add_constraint_fix** - Fix entity in place
- **add_dimension** - Add dimensional constraint

#### Feature Tools
- **extrude** - Extrude sketch profile
- **revolve** - Revolve sketch profile around axis
- **fillet** - Round edges
- **chamfer** - Bevel edges
- **sweep** - Sweep profile along path
- **loft** - Create shape between multiple profiles
- **shell** - Create hollow shell from solid
- **combine** - Boolean combine bodies
- **split_body** - Split body with plane
- **thicken** - Add thickness to surface

#### Pattern Tools
- **rectangular_pattern** - Create rectangular pattern of bodies/features
- **circular_pattern** - Create circular pattern of bodies/features
- **mirror_feature** - Mirror bodies/features across plane

#### Modification Tools
- **move_body** - Translate body
- **rotate_body** - Rotate body around axis
- **move_occurrence** - Move component occurrence
- **modify_feature** - Change feature parameters
- **update_parameter** - Update design parameter
- **delete_body** - Delete body
- **delete_feature** - Delete timeline feature
- **edit_sketch** - Edit sketch curve properties

#### Validation Tools
- **measure_distance** - Measure distance between entities
- **measure_angle** - Measure angle between entities
- **check_interference** - Detect body collisions
- **get_body_properties** - Get physical properties (volume, area, etc.)
- **get_sketch_status** - Get sketch constraint status

#### Viewport Tools
- **take_screenshot** - Capture viewport as PNG
- **set_camera** - Set camera position and orientation
- **get_camera** - Get current camera state
- **set_view** - Set standard view (front, top, isometric, etc.)
- **fit_view** - Fit view to entities or all geometry

#### System Tools
- **check_health** - Check connection health
- **get_version** - Get version information

### Architecture
- MCP Server (Python) for AI assistant integration
- Fusion 360 Add-in for Fusion 360 API access
- HTTP communication between server and add-in
- Task queue for thread-safe Fusion 360 operations
- Structured logging with structlog

[0.1.0]: https://github.com/ncmlabs/fusion360_mcp/releases/tag/v0.1.0
