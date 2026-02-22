# Subagent Team Design — Metashape + Blender Pipeline

**Date:** 2026-02-22
**Status:** Approved
**Approach:** Five focused specialists (Approach A)

## Context

The metashape-mcp plugin has 106 tools, 5 skills, and 2 existing agents (photogrammetry-qa, metashape-api-verifier). The user's full pipeline involves a 4-handoff round-trip between Metashape and Blender:

1. **Metashape → Blender**: Raw point cloud or mesh (PLY)
2. **Blender**: Cleanup, classification by surface type, splitting, UV projection
3. **Blender → Metashape**: Cleaned/split/UV'd meshes for photo-texturing
4. **Metashape → Blender**: Textured meshes for environment finishing (trees, street furniture, etc.)

Deliverable is game-ready terrain for a game engine, split by surface type (road, vegetation, rock face) so each can have appropriate procedural materials (rain, grass, etc.).

## Design Decisions

- **Five specialists over three generalists**: Clear ownership, focused system prompts, easier to maintain. Claude already routes well based on agent descriptions.
- **No orchestrator**: Claude handles routing naturally. Project-planner recommends agents but doesn't invoke them.
- **DEM-based ground truth, not survey GCPs**: User uses USGS LiDAR DEM (EPSG:26911), not physical targets. Agent renamed from gcp-advisor to dem-alignment-advisor.
- **Classification priority**: Spline-based (KML road path) > color-based (vertex colors always available on points) > normal-based (fallback). Points always have colors; mesh vertex colors are expensive and only done when specifically needed.

## Agent Team

### 1. alignment-doctor

**Color:** `#D4380D` (deep red)
**Trigger:** Alignment failed, produced bad results, or cameras in wrong positions.
**Role:** Diagnoses the CAUSE of alignment problems. The photogrammetry-qa agent detects symptoms — this agent finds the root cause.

**Decision logic — classify failure mode:**
- **Total failure** (<50% aligned): sensor config, preselection settings, or image quality
- **Partial failure** (50-85%): overlap gaps, lighting mismatch, disabled cameras
- **Geometric failure** (aligned but wrong positions): drift, CRS issues, scale problems
- **Calibration failure** (reprojection >1.0px): wrong sensor type, degenerate geometry

For each mode, a specific investigation protocol using MCP tools. Prescribes ONE primary diagnosis with a specific fix.

**Tools:** get_alignment_stats, list_sensors, select_cameras, get_camera_spatial_stats, get_reprojection_error_by_region, check_alignment_continuity, get_camera_metadata, enable_cameras, get_corridor_drift_report

**References:** corridor-alignment-pipeline skill for drift thresholds

### 2. handoff-coordinator

**Color:** `#7B61FF` (purple)
**Trigger:** Any export/import between Metashape and Blender.
**Role:** Orchestrates all 4 handoff transitions. Records state before export, verifies after import.

**Four transitions:**

| # | Direction | Payload | Key Checks |
|---|-----------|---------|------------|
| 1 | MS → Blender | Raw point cloud or mesh (PLY) | CRS recorded, point/face counts, no 0.411x scale leak |
| 2 | Blender → MS | Cleaned/split/UV'd meshes | Identity transforms, naming convention (Road_Tile_X-Y etc.), UV integrity |
| 3 | MS → Blender | Photo-textured meshes | Texture atlas present, material assignments match split names |
| 4 | Blender → Engine | Finished environment | Final export validation, asset manifest |

**Key behaviors:**
- Detects the 0.411x Metashape internal scale bug
- Enforces golden rule: identity transforms, FBX_SCALE_NONE, axis conventions
- Handles PLY (intermediate) and FBX (final) formats
- Tracks tile transfer status and current stage
- Works with both point cloud and mesh payloads

**Tools:** Metashape export/import/state tools + Blender scene_info, object_info, execute_blender_code, viewport_screenshot

**References:** tile-export-pipeline skill

### 3. terrain-processor

**Color:** `#389E0D` (green)
**Trigger:** Working on mesh or point cloud in Blender — cleanup, classification, splitting, UV, optimization.
**Role:** Makes judgment calls about what needs cleaning, how to classify surfaces, and how to split for game engine.

**Three phases:**

**Phase 1 — Assessment:** Read scene, count objects, check face/point counts, identify data type (points vs mesh, tiled vs single). Report findings and recommend processing plan.

**Phase 2 — Classification & Splitting:**

| Strategy | Priority | When Available | Method |
|----------|----------|----------------|--------|
| Spline-based | 1st (best) | KML/path data exists | Import road centerline, buffer to road width, classify faces/points within buffer |
| Color-based | 2nd | Vertex colors exist (always for points) | HSV/RGB clustering — asphalt gray vs vegetation green vs rock tan |
| Normal-based | 3rd (fallback) | Always | Face normal thresholds: nZ>0.85 road, 0.2-0.85 rock, <0.2 vegetation |
| Hybrid | When combining | Multiple sources | Spline for road, color for vegetation vs rock |

Splits into separate objects: `Road_Tile_X-Y`, `Vegetation_Tile_X-Y`, `RockFace_Tile_X-Y`

**Phase 3 — UV & Cleanup:**
- Top-down orthographic UV for road surfaces
- Tri-planar or smart UV for rock faces
- Decimation recommendations per surface type
- Enforces golden rule: never alter identity transforms

**Tools:** Blender execute_blender_code, scene_info, object_info, viewport_screenshot

**References:** photogrammetry-terrain-cleanup skill, tile-export-pipeline skill

### 4. dem-alignment-advisor

**Color:** `#CF8B17` (amber)
**Trigger:** Accuracy concerns, drift detected, or vertical alignment needs validation.
**Role:** DEM-based ground truth specialist. NOT a survey GCP agent — uses USGS LiDAR DEM.

**Key capabilities:**

1. **DEM import guidance**: CRS matching (EPSG:26911 UTM11N vs project EPSG:9707), vertical datum correction (-36m NAVD88→EGM96)

2. **Drift interpretation:**
   - Uniform offset → datum issue, not alignment problem
   - Increasing offset along corridor → real drift, needs investigation
   - Random scatter → normal GPS noise

3. **Virtual checkpoints**: DEM-derived check points that MEASURE accuracy (not improve it). Uses generate_virtual_checkpoints().

4. **When to recommend re-alignment**: Drift gradient >2.0 m/100m → recommend DEM points as control to constrain solution. Knows "report the problem" vs "fix the problem."

**Tools:** compare_alignment_to_dem, generate_virtual_checkpoints, get_corridor_drift_report, get_camera_spatial_stats, coordinate tools, marker tools

**References:** corridor-alignment-pipeline skill, MEMORY.md (-36m datum correction)

### 5. project-planner

**Color:** `#0958D9` (blue)
**Trigger:** Session start, context switching, "where am I" questions.
**Role:** Reads state from both MCP servers and classifies project stage.

**9-stage pipeline tracking:**

| Stage | Detection |
|-------|-----------|
| 1. Photos imported | Cameras exist, none aligned |
| 2. Alignment in progress | Some cameras aligned, not all |
| 3. Alignment complete | All enabled cameras aligned, tie points exist |
| 4. Tie points filtered | Optimization done, RU/PA/RE passes applied |
| 5. Dense reconstruction | Point cloud or depth maps exist |
| 6. Mesh built | Model exists in chunk |
| 7. In Blender — processing | Tile objects in Blender scene, no textured versions |
| 8. Back in Metashape — texturing | Split meshes imported, texture building |
| 9. Final Blender — environment | Textured meshes with environment objects |

**Behaviors:**
- Reports blockers (no GPS, processing running, drift, missing tiles)
- Recommends next action and names which agent to invoke
- Tracks multiple projects (one active, others on hold)
- Knows about all .psx files on disk

**Tools:** Metashape project/chunk/alignment/model state tools + Blender scene_info, object_info

**References:** All other agents and skills by name

## Color Palette

| Agent | Color | Hex |
|-------|-------|-----|
| photogrammetry-qa (existing) | Teal | `#2E86AB` |
| metashape-api-verifier (existing) | Red-orange | `#E8543E` |
| alignment-doctor | Deep red | `#D4380D` |
| handoff-coordinator | Purple | `#7B61FF` |
| terrain-processor | Green | `#389E0D` |
| dem-alignment-advisor | Amber | `#CF8B17` |
| project-planner | Blue | `#0958D9` |

## Agent Interaction Map

```
project-planner (session start)
    ├── "Alignment needed" → alignment-doctor (if problems) or corridor-alignment-pipeline skill
    ├── "Ready to export" → handoff-coordinator (MS → Blender)
    ├── "Tiles in Blender" → terrain-processor
    ├── "Drift detected" → dem-alignment-advisor
    ├── "Ready for texturing" → handoff-coordinator (Blender → MS)
    └── "QA check needed" → photogrammetry-qa
```

photogrammetry-qa detects drift → dem-alignment-advisor investigates → alignment-doctor fixes
handoff-coordinator transfers → terrain-processor processes → handoff-coordinator transfers back
