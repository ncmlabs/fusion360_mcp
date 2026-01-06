# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Bug Fixes

- Remove accidental file and quote pip package spec

### Miscellaneous Tasks

- Remove accidental feedback files
- Remove accidental feedback files
## [0.1.1] - 2026-01-05

### Bug Fixes

- Use dynamic SERVER_VERSION in test instead of hardcoded value
- Auto-sync development branch after release
- Quote pip package spec to prevent shell redirect

### Documentation

- Add community governance files for open source release
- Add missing tools to API reference and expand README features

### Features

- Add demo GIF to README

### Miscellaneous Tasks

- Sync version to 0.1.1 on development branch
## [0.1.0] - 2026-01-05

### Bug Fixes

- Resolve Fusion 360 add-in import and event handler issues
- Add operations module to deploy script
- Correct Fusion 360 API usage for move, rotate, and delete operations
- Remove unused imports to pass ruff linting
- Include exceptions module in Server package
- Use isClosed property for closed splines instead of non-existent API
- Use correct Fusion 360 API for sketch text
- Correct Fusion 360 API usage for coincident and fix constraints
- Correct Fusion 360 API usage for pipe and mark coil as unsupported
- Correct Fusion 360 API usage for thread, thicken; mark emboss unsupported
- Inline unit conversion functions to avoid import issues in Fusion 360
- Correct Fusion 360 API usage for assembly operations
- Loft cut operation and update emboss documentation
- Implement working emboss feature using correct Fusion 360 API
- Remove base64 screenshot option, default to file output
- Use correct BooleanTypes.UnionBooleanType for combine join operation
- Use FeatureOperations enum for combine operation
- Disable non-working MODIFY tools pending debugging

### Features

- Phase 0 Foundation Infrastructure
- Phase 1 Query Layer Implementation
- Phase 2 Enhanced Creation Implementation
- Phase 3 Modification Layer Implementation
- Phase 4 Validation Layer Implementation
- Phase 6 Production Readiness Implementation
- Phase 7a Core Sketch Geometry Tools Implementation
- Phase 7b Sketch Patterns & Operations Implementation
- Phase 7c Sketch Constraints & Dimensions Implementation
- Phase 8a Advanced Feature Tools Implementation
- Phase 8b Feature Pattern Tools Implementation
- Phase 8c Specialized Feature Tools Implementation
- Standardize all serializer outputs to millimeters (mm)
- Add viewport snapshot and camera control tools
- Add construction plane creation tools
- Phase 5 Assembly Support Implementation
- Add MCP configuration for Claude Desktop integration
- Add SketchText support for emboss/deboss
- Add LLM prompt optimization documentation
- Add 7 MODIFY menu tools
- Add wrap_sketch_to_surface tool for projecting curves onto curved faces
- Add versioning and release automation

### Miscellaneous Tasks

- Prepare repository for open source release

