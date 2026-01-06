  Current MCP Limitations

  1. Sketch Complexity

  Creating complex 2D profiles is tedious - I have to draw line-by-line, arc-by-arc. A real wrench has smooth, ergonomic curves that would require many spline points to define properly. There's no way to:
  - Import SVG/DXF profiles
  - Use reference images as underlays
  - Create complex curves interactively

  2. Organic Shape Transitions

  A real wrench has smooth, flowing transitions between the head and handle (think forged steel look). The current tools make it hard to:
  - Create smooth lofts between complex profiles
  - Blend surfaces organically
  - Add subtle tapers and contours

  3. Boolean Operations Workflow

  Notice my wrench has 2 separate bodies - combining them cleanly requires extra steps. For complex designs, managing body relationships gets cumbersome.

  4. Missing Features for Realism

  - No knurling/patterns: Real wrenches have grip textures
  - No emboss/deboss text: The emboss tool doesn't work via API (I tried noting this)
  - No shell tool exposed: Hollowing for weight reduction
  - No direct face manipulation: Push/pull faces to sculpt

  5. Iterative Design Challenge

  I can't "see" the model as I build - I have to take screenshots periodically. Real CAD work is visual and iterative.

  6. What Would Help

  Ideal additions:
  ├── Import SVG/DXF profiles
  ├── Working emboss for markings
  ├── Surface blending/patch tools
  ├── Pattern features (knurl, diamond, etc.)
  ├── Reference image support
  └── Better body combine workflow

  1. ~~No Emboss/Wrap on Curved Surfaces~~ PARTIALLY RESOLVED
  - ~~Can't wrap text or shapes onto cylindrical/curved geometry~~
  - Text engraving only works on flat planes, not conforming to curves
  - **NEW:** `wrap_sketch_to_surface()` tool implemented - wraps sketch curves onto curved faces
  - Still needed: Full emboss_on_face() for raised/recessed features on curves

  2. No Construction Plane Visibility Control
  - Can't hide/show construction planes programmatically
  - The golden HeartPlane is visible in screenshots
  - Needed: set_entity_visibility(entity_id, visible: bool) tool

  3. Limited Sketch-on-Face Capability
  - Creating sketches directly on curved body faces is unreliable
  - Had to use offset planes which don't follow the curve
  - Needed: create_sketch_on_face(face_id) with proper projection

  4. No "To Object" Extrude Option
  - Can only extrude by distance, not "to next" or "to body"
  - Makes cutting into curved surfaces imprecise
  - Needed: extrude(..., extent_type="to_object", target=body_id)

  5. ~~No Shell Feature~~ ✅ RESOLVED
  - ~~Had to create hollow mug via revolve profile~~
  - ~~Can't hollow out a solid body directly~~
  - **IMPLEMENTED:** `shell(body_id, face_ids, thickness, direction)` tool available

  6. Health State Errors Are Opaque
  - Features show "error" state but still work
  - No detailed error messages to diagnose issues
  - Needed: get_feature_errors(feature_id) returning specific messages

  7. No Undo/Rollback
  - Had to manually delete features to fix mistakes
  - Needed: undo() or rollback_to(timeline_index)

  8. ~~No Boolean Operations Between Bodies~~ ✅ RESOLVED
  - ~~Can't directly union/subtract/intersect existing bodies~~
  - ~~Only through extrude/sweep operations~~
  - **IMPLEMENTED:** `combine(target_body_id, tool_body_ids, operation)` tool available

  9. No Material/Appearance Assignment
  - Can't set colors or materials for visualization
  - Needed: set_appearance(body_id, color/material)

  10. No Export Capability
  - Can't export STL/STEP/3MF for 3D printing directly
  - Needed: export(body_ids, format="stl", file_path)

  Most Impactful Additions

  If I could add just 3 tools, they would be:
  1. ~~wrap_to_surface()~~ ✅ IMPLEMENTED as `wrap_sketch_to_surface()`
  2. export_stl() - Direct 3D print file generation
  3. ~~shell()~~ ✅ IMPLEMENTED

  These would cover the most common design-to-print workflow gaps.
