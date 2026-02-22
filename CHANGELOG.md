# Changelog

All notable changes to the metashape-mcp plugin.

## [Unreleased]

### Added
- **3 new skills**: photo-import-setup, sky-artifact-prevention, texturing-pipeline
- **1 new agent**: texture-advisor — texture settings and artifact diagnosis
- **2 new hooks**: pre-flight time estimator (warns before long operations), post-QA reminder (suggests QA after processing steps)

### Changed
- **WORKFLOW_GUIDE.md**: Full rewrite — references all agents/skills, fixes outdated claims, shows agent-driven workflow
- **metashape-reconstruction skill**: Added sky artifact prevention section and texturing-pipeline cross-reference
- **project-planner agent**: Added Stage 0 (new project), expanded Stage 1 (setup sub-stages), video import awareness, updated pipeline checklist to 21 steps
- **handoff-coordinator agent**: Added Blender → Metashape re-texturing round-trip, mask transfer awareness

## [5e199cf] — 2026-02-22

### Added
- **5 new agents**: alignment-doctor, gcp-advisor, handoff-coordinator, terrain-processor, project-planner
- Subagent team design doc and implementation plan

## [f315c4d] — 2026-02-21

### Added
- **7 diagnostic tools** in `diagnostics.py`: camera spatial stats, per-region reprojection error, alignment continuity, DEM comparison, virtual checkpoints, corridor drift report
- **corridor-alignment-pipeline skill**: incremental batch alignment with drift QA gates
- Corridor drift detection design doc

## [55b6acc] — 2026-02-21

### Fixed
- 6 critical API bugs: `calculatePointNormals` location, `assignClass` params, `closeHoles` progress callback, `mergeChunks` param names, `refineMarkers` behavior, `exportMarkers` params

## [0553d20] — 2026-02-21

### Fixed
- 3 remaining API issues: `importMasks` source parameter, `captureView` method, `downscale` enum mapping

## [e24172d] — 2026-02-21

### Added
- **3 dev skills**: mcp-tool-scaffolding, metashape-api-lookup, metashape-reconstruction
- **metashape-api-verifier agent**: cross-references tools against API reference
- Code quality hooks (ruff format + lint)

## [6bad505] — 2026-02-21

### Added
- **Claude Code plugin**: `.claude-plugin/plugin.json`, `.mcp.json`
- **2 skills**: tile-export-pipeline, corridor-alignment-pipeline (initial)
- **1 agent**: photogrammetry-qa
- **3 safety hooks**: destructive op warnings, block .psx edits, block reference file edits

## [d6a450f] — 2026-02-20

### Added
- Initial MCP server with 106 tools across 15 modules
- 10 resources, 6 prompts
- Streamable HTTP transport on port 8765
- Full photogrammetry pipeline coverage: project → photos → alignment → dense → mesh → texture → survey → export
