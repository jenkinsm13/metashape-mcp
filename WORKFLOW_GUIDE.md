# Metashape MCP — Road Corridor Workflow Guide

A practical guide for using the Metashape MCP server with AI agents for large-scale road corridor captures destined for driving simulator environments.

## Your Setup

- **Camera**: Full-frame with fisheye lens, vehicle-mounted
- **Format**: EXR with alpha channel (sky mask)
- **Scale**: 5,000–50,000+ photos per project, ~25 miles of road at the high end
- **GPS**: EXIF GPS or extracted CSV, supplemented with manually-placed GCPs at road markings
- **Output**: Textured mesh (FBX) for driving simulator (Unreal, etc.)

## Agent Team

Seven specialized agents handle different aspects of the pipeline:

| Agent | Role | When Invoked |
|-------|------|-------------|
| **project-planner** | Status overview, stage detection, next-step routing | Session start, "where am I?", context switching |
| **alignment-doctor** | Diagnoses alignment failures, prescribes fixes | Alignment rate low, cameras in wrong positions, drift |
| **gcp-advisor** | GCP strategy, marker errors, virtual checkpoints | Drift detected, planning GCP placement, marker errors high |
| **handoff-coordinator** | Metashape ↔ Blender export/import/verification | Exporting tiles, importing into Blender, verifying transfers |
| **terrain-processor** | Blender mesh cleanup, classification, UV, game-ready | Canopy removal, surface splitting, UV projection |
| **texture-advisor** | Texture atlas, blending mode, artifact diagnosis | Choosing texture settings, diagnosing seams/blur/ghosting |
| **photogrammetry-qa** | Post-processing QA checks | After alignment, dense recon, mesh building |

Plus **metashape-api-verifier** for tool development/auditing.

## Skills Reference

| Skill | Coverage |
|-------|---------|
| **photo-import-setup** | Import photos, GPS, sensors, masks, quality check |
| **corridor-alignment-pipeline** | Incremental batch alignment with drift detection |
| **sky-artifact-prevention** | 5 strategies to prevent/fix tunnel mesh artifacts |
| **metashape-reconstruction** | Depth maps, point cloud, mesh, texture, DEM |
| **texturing-pipeline** | UV mapping, texture atlas, color calibration |
| **tile-export-pipeline** | Blender → game-ready FBX export |
| **photogrammetry-terrain-cleanup** | Blender-side canopy removal, classification, UV |

---

## Phase 1: Project Setup & Import

> "I have 21k photos of Highway 101 from SLO to Pismo. EXR files in C:/captures/101_south/. GPS is in gps_data.csv. Set up the project."

**Skill:** `photo-import-setup`

What happens:
1. `create_project("C:/projects/101_south.psx")`
2. `add_photos(["C:/captures/101_south/"])`
3. `import_reference("C:/captures/101_south/gps_data.csv", columns="nxyz", delimiter=",")`
4. `set_sensor(sensor_index=0, sensor_type="fisheye")` — **CRITICAL for fisheye lenses**
5. `import_masks(method="alpha", path="{filename}")` — imports EXR alpha as sky masks
6. `analyze_images()` — flags blown/blurry frames
7. `enable_cameras(labels=[...low_quality...], enable=False)` — disables bad frames

### Sensor Configuration

This is the #1 cause of total alignment failure. If you have a fisheye lens, you MUST set the sensor type:

```
set_sensor(sensor_index=0, sensor_type="fisheye")
```

The **alignment-doctor** agent exists largely because of this mistake.

### Mask Import

EXR files with alpha channel are imported as masks:
```
import_masks(method="alpha", path="{filename}")
```

Masks are critical for preventing sky reconstruction artifacts. See Phase 4 and the `sky-artifact-prevention` skill.

---

## Phase 2: Alignment (Always Incremental)

> "I've enabled the first 2000 outbound cameras. Align them."

**Skill:** `corridor-alignment-pipeline`

Alignment is always done in batches of ~200 cameras. Never align everything at once — it fails on large corridor datasets.

### The Alignment Loop

For each batch:
1. Enable batch cameras
2. `match_photos(keep_keypoints=True, reference_preselection=True, guided_matching=True)`
3. `align_cameras(reset_alignment=False)`
4. **Check drift** — `get_camera_spatial_stats()`
5. **Check continuity** — `check_alignment_continuity(new_camera_labels=...)`
6. If PASS → next batch. If WARN → consider GCPs. If FAIL → STOP.

### Drift Thresholds

| Gradient | Assessment | Action |
|----------|------------|--------|
| < 0.5 m/100m | PASS | Continue |
| 0.5–2.0 m/100m | WARN | Alert user, suggest GCPs |
| > 2.0 m/100m | FAIL | STOP — do not continue |

### Alignment Settings for Road Corridors

| Setting | Value | Why |
|---------|-------|-----|
| downscale | 1 (High) | Accuracy for long corridors |
| keypoint_limit | 60,000+ | Fisheye needs more keypoints |
| reference_preselection | True | Essential for corridors |
| generic_preselection | True | Bridges gaps in sequence |
| guided_matching | True | Handles repetitive road surfaces |
| keep_keypoints | True | Required for incremental alignment |
| reset_alignment | False | After first batch — builds on existing |

### GPU Config for Alignment
```
set_gpu_config(cpu_enable=True)   # CPU ON for alignment only
```

---

## Phase 3: GCP Placement (Human Step)

> "Alignment looks good, I'm going to add GCPs now."

**Agent:** `gcp-advisor`

GCP placement is interactive — you know the road markings. The agent advises on strategy.

### After Placing GCPs

1. `optimize_cameras(adaptive_fitting=True)`
2. `list_markers()` — shows per-marker error
3. Agent flags outliers: "GCP 'Elm_Oak_intersection' has 2.3m error vs 0.15m average."

### GCP Strategy

- Place at both ends of the corridor (non-negotiable for >500m)
- Every 500m–1km minimum
- More at curves and elevation changes
- Road paint (stop bars, crosswalks) makes great natural targets

### Tie Point Filtering (USGS Workflow)

After GCPs and optimization:
```
filter_tie_points(criterion="reconstruction_uncertainty", threshold=10)
optimize_cameras(adaptive_fitting=True)
filter_tie_points(criterion="projection_accuracy", threshold=3)
optimize_cameras(adaptive_fitting=True)
filter_tie_points(criterion="reprojection_error", threshold=0.3)
optimize_cameras(adaptive_fitting=True)
```

NEVER remove more than 50% of tie points in one pass — the tool enforces this automatically.

---

## Phase 4: Dense Reconstruction & Sky Artifact Prevention

> "Build the mesh. Make sure we don't get the tunnel effect."

**Skills:** `metashape-reconstruction` + `sky-artifact-prevention`

### The Sky/Tunnel Problem

Metashape's depth map mesh generation ignores masks — interpolation closes the sky into a tunnel. This is the #1 quality issue for road corridors.

### Recommended Strategy (Full 3D with Canyon Walls)

```
# GPU off for dense operations
set_gpu_config(cpu_enable=False)

# Build point cloud — masks ARE respected here
build_point_cloud(point_colors=True, point_confidence=True)

# Classify ground (tuned for steep canyons)
classify_ground_points(max_angle=25.0, max_distance=2.0, cell_size=20.0)

# Build mesh from point cloud — NOT depth maps
build_model(
    surface_type="arbitrary",
    source_data="point_cloud",
    classes=[0, 1, 2, 6],
    interpolation="enabled",
    vertex_colors=True,
    vertex_confidence=True
)

# Clean remaining artifacts
clean_model(criterion="component_size", level=75)
```

### Alternative Strategies

See the `sky-artifact-prevention` skill for all 5 strategies and the decision tree for choosing between them.

| Strategy | Best For |
|----------|---------|
| Point cloud source | Full 3D with masks (recommended) |
| Height field | Terrain-only, no vertical surfaces needed |
| Classification + filtering | When you need precise control |
| Region cropping | Quick and dirty, simple scenes |
| Post-mesh cleanup | Fallback for remaining artifacts |

### After Building

Run QA: invoke the **photogrammetry-qa** agent to check model statistics and verify no major artifacts remain.

---

## Phase 5: Texture

> "Texture it for the driving sim."

**Skill:** `texturing-pipeline`

```
build_uv(mapping_mode="generic", texture_size=8192)
build_texture(
    blending_mode="mosaic",
    texture_size=8192,
    ghosting_filter=True
    # optional: anti_aliasing=1, source_model_key=<key>, transfer_texture=True,
    # source_data="model" when transferring a texture from another mesh
)
```

### Texture Settings for Road Corridors

| Setting | Road Corridor Value | Why |
|---------|-------------------|-----|
| mapping_mode | generic | Best for arbitrary geometry |
| texture_size | 8192 | Sim engine sweet spot |
| blending_mode | mosaic | Sharpest road markings |
| ghosting_filter | True | Removes moving vehicles |

- **mosaic** blending: Sharpest detail per patch, best for road markings and text. May have visible seams.
- **natural** blending: Smoother seams, slightly less sharp. Better for organic surfaces.

If texture artifacts appear (seams, blur, ghosting), invoke the **texture-advisor** agent.

---

## Phase 6: Export to Blender

> "Export tiles for Blender processing."

**Agent:** `handoff-coordinator`

### PLY Tile Export
```
export_model(
    path="E:\\DeckerCanyon\\BlockModel\\Tile_5-3.ply",
    format="ply",
    save_normals=True,
    save_colors=True,
    binary=True
)
```

The handoff-coordinator:
1. Records CRS and face counts before export
2. Verifies after import into Blender
3. Checks for the 0.411x scale bug (Metashape internal scale leaking into exports)
4. Enforces identity transforms in Blender

### Coordinate System Notes
- Exported PLY vertices are in the chunk CRS (real-world meters)
- Blender has no CRS — 1 unit = 1 meter by convention
- The approximate UTM offset (E=327225, N=3773379) is stripped during export for Blender compatibility

---

## Phase 7: Blender Processing

> "Clean up the tiles, classify surfaces, project UVs."

**Agent:** `terrain-processor`
**Skill:** `photogrammetry-terrain-cleanup`

### Processing Pipeline

1. **Assessment** — scan all tiles, identify canopy percentage
2. **Basic cleanup** — separate loose parts, threshold canopy removal, re-separate
3. **Envelope cleanup** — raycasting-based removal for trouble tiles only
4. **Surface classification** — vertex groups by face normal (Road, Rock Face, Vegetation)
5. **UV projection** — top-down orthographic
6. **Game-ready export** — FBX per tile

### Golden Rules in Blender
- **NEVER alter object-level transforms** (Location/Rotation/Scale must stay at identity)
- **NEVER remove upward-facing faces** (normal Z >= 0 is terrain)
- Save after every tile modification
- Process 1-10 tiles per execute_blender_code call (not all 80)

---

## Phase 8: Final Export

> "Export to FBX for Unreal."

**Skill:** `tile-export-pipeline`

```python
bpy.ops.export_scene.fbx(
    filepath="E:\\DeckerCanyon\\BlockModel\\GameReady\\Tile_5-3.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z',
    axis_up='Y'
)
```

Export each tile individually. The handoff-coordinator verifies the full manifest.

---

## Monitoring & Diagnostics

### Project Status Check
> "How's my project looking?"

**Agent:** `project-planner` reads state from both MCP servers and reports stage, blockers, and next step.

### Drift Check
> "Is there drift?"

**Agent:** `gcp-advisor` or diagnostics tools directly:
```
get_corridor_drift_report(num_segments=10)
```

### Alignment Problems
> "Reprojection errors are high."

**Agent:** `alignment-doctor` investigates root cause and prescribes specific fix.

### QA After Processing
> "Run QA on the mesh."

**Agent:** `photogrammetry-qa` checks alignment rates, reprojection errors, model stats.

---

## Quick Reference: Recommended Settings

| Step | Setting | Value | Why |
|------|---------|-------|-----|
| Match | downscale | 1 | Accuracy for long corridors |
| Match | keypoint_limit | 60000 | Fisheye needs more keypoints |
| Match | reference_preselection | True | Essential for corridors |
| Match | keep_keypoints | True | Required for incremental |
| Align | adaptive_fitting | True | Handles fisheye distortion |
| Dense | GPU cpu_enable | False | CPU slows GPU operations |
| Depth Maps | downscale | 2–4 | Balance for 20k+ photos |
| Depth Maps | filter_mode | mild | Road surfaces need mild |
| Model | source_data | point_cloud | Avoids sky tunnel problem |
| Model | surface_type | arbitrary | Preserves vertical surfaces |
| Model | classes | [0,1,2,6] | Ground + unclassified + building |
| Clean | level | 75 | Remove sky artifacts |
| UV | texture_size | 8192 | Sim engine sweet spot |
| Texture | blending_mode | mosaic | Best for sharp road markings |
| Texture | ghosting_filter | True | Handles moving vehicles |
| FBX | scale | FBX_SCALE_NONE | No scale transform |
| FBX | axis_forward | -Z | Unreal convention |
| FBX | axis_up | Y | Unreal convention |
