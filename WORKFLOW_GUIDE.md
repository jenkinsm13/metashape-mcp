# Metashape MCP - Road Corridor Capture Workflow Guide

A practical guide for using the Metashape MCP server for large-scale road corridor captures destined for driving simulator environments.

## Your Setup

- **Camera**: Full-frame with fisheye lens, vehicle-mounted
- **Format**: EXR with alpha channel (sky mask)
- **Scale**: 5,000 - 50,000+ photos per project, ~25 miles of road at the high end
- **GPS**: EXIF GPS extracted to CSV, supplemented with manually-placed GCPs at road markings
- **Output**: Textured mesh (FBX/OBJ/glTF) for driving simulator (Unreal, etc.)

---

## Phase 1: Project Setup & Import

Talk to Claude naturally:

> "I have 21k photos of Highway 101 from SLO to Pismo. EXR files in C:/captures/101_south/. GPS is in gps_data.csv. Set up the project."

What happens behind the scenes:
1. `create_project("C:/projects/101_south.psx")`
2. `add_photos(["C:/captures/101_south/"])`
3. `import_reference("C:/captures/101_south/gps_data.csv", columns="nxyz", delimiter=",")`
4. `analyze_images()` — flags blown/blurry frames from the drive

### Mask Import

Import your EXR alpha as masks in Metashape. The MCP doesn't currently automate mask import (Metashape's `importMasks()` method), but this can be done via Metashape's GUI or a one-liner in the console:

```python
chunk.importMasks(path="{filename}.exr", source=Metashape.MaskSourceAlpha)
```

---

## Phase 2: Alignment (Always Incremental)

Alignment is always done in batches of ~2000 photos max. Never try to align everything at once — it will fail on large corridor datasets.

Road captures have two travel directions (outbound and inbound) that overlap along the road centerline. You handle camera selection in one of two ways:

### Option A: Select cameras in the GUI

All photos are imported upfront. In Metashape's reference pane, select camera dots by GPS position and enable only the batch you want to align (~2000 at a time).

> "I've enabled the first 2000 outbound cameras. Align them."

### Option B: Separate outbound/inbound folders

Photos are organized into outbound and inbound folders. Tell the agent to add from the head of one direction and tail of the other to build up coverage incrementally.

> "Add the first 2000 from outbound/ and align."

### The alignment loop

1. Enable/add a batch of ~2000 cameras
2. The agent runs `match_photos` + `align_cameras(reset_alignment=False)`
3. Agent checks alignment rate and reports back
4. You decide: add the next batch, place GCPs, remove problem cameras, or adjust settings
5. Repeat until alignment is complete

The key is `reset_alignment=False` after the first batch — this builds on existing alignment instead of starting over.

> "Alignment rate is 94% on the first 2000. Enable the next batch."
> "Before we add more, I'm going to place GCPs at the first three intersections."

### Alignment Settings for Road Corridors

- **Downscale 1 (High)** — you need the accuracy for long linear sequences
- **Reference preselection = True** — essential for corridors, uses GPS to limit matching to nearby images
- **Keypoint limit 60,000+** — fisheye lenses produce more distortion, need more keypoints
- **Generic preselection = True** — helps bridge gaps in the sequence
- **Guided matching = True** — helps with the repetitive nature of road surfaces

---

## Phase 3: GCP Placement (Human Step)

This stays interactive — you know the road markings better than any AI.

> "Alignment looks good, I'm going to add GCPs now."

You place GCPs at road markings/intersections in the Metashape GUI. When done:

> "I've added 12 GCPs at intersections. Optimize and show me the errors."

The LLM calls:
1. `optimize_cameras(adaptive_fitting=True)`
2. `list_markers()` — shows error for each GCP
3. Flags outliers: "GCP 'Elm_Oak_intersection' has 2.3m error vs 0.15m average. Check projections."

### GCP Strategy for Road Corridors

- Place at intersections where road markings are clearly visible
- Every 500m-1km along the route minimum
- More at curves and elevation changes
- Road paint (stop bars, crosswalks) makes great natural GCPs
- After optimization, look for any GCP with >3x the average error — likely misprojected

---

## Phase 4: The Sky/Mesh Problem

### The Fundamental Issue

Metashape has a well-known problem with road corridor captures:
- **Masks are ignored** during mesh generation from depth maps
- **Interpolation fills gaps** regardless of mask settings — the sky gets "closed" into a tunnel
- This creates tunnel effects, flashing artifacts, and closed environments where you need open sky

### Mitigation Strategies

**Strategy A: Height Field Surface Type**
```
build_model(surface_type="height_field", source_data="depth_maps")
```
Height field mode only generates surface visible from above — eliminates the tunnel/dome problem entirely. Works well for road corridors where the ground surface is what you care about. Downside: loses vertical surfaces like building facades and walls.

**Strategy B: Aggressive Region Cropping**
Set a tight reconstruction region that cuts off everything above a certain height:
```
set_region(center=[x, y, z], size=[width, height, limited_depth])
```
Limit the vertical extent to just above the tallest feature you care about.

**Strategy C: Point Cloud Classification + Filtered Mesh**
1. `build_point_cloud(point_confidence=True)`
2. `classify_ground_points()` — separates ground from vegetation/buildings/sky noise
3. `build_model(source_data="point_cloud", classes=[2, 6])` — build mesh from only ground + building classes
4. This avoids the depth map interpolation problem entirely since you're building from classified points

**Strategy D: Depth Maps + Aggressive Cleaning**
1. Build mesh from depth maps (it will create the tunnel)
2. `clean_model(criterion="component_size", level=75)` — aggressively remove disconnected components
3. Manually clean remaining sky artifacts in the Metashape GUI or a 3D editor
4. This is tedious but sometimes necessary for quality

**Strategy E: Build from Point Cloud Instead of Depth Maps**
```
build_model(source_data="point_cloud", surface_type="arbitrary")
```
Point cloud source respects the data better — if there are no points in the sky (because masks worked during point cloud generation), there's less interpolation. Still not perfect but often better than depth maps.

**Recommended Combo:**
1. Import masks from EXR alpha
2. Build point cloud WITH masks (masks ARE respected during point cloud generation)
3. Classify ground points
4. Build mesh from point cloud, not depth maps
5. Use region cropping to limit vertical extent
6. Clean model to remove remaining artifacts

---

## Phase 5: Texture & Export for Sim Engine

> "Texture it and export as FBX for Unreal."

1. `build_uv(mapping_mode="generic", texture_size=8192)`
2. `build_texture(blending_mode="mosaic", texture_size=8192, ghosting_filter=True)`
3. `export_model("C:/exports/101_south.fbx", format="fbx", save_texture=True)`

### Export Tips for Driving Simulators

- **Face count**: Most sim engines want 2-10M faces per tile. Use `decimate_model()` if needed.
- **Texture size**: 8192x8192 is the sweet spot. Larger causes VRAM issues in engines.
- **FBX or glTF**: Both work well in Unreal/Unity. glTF is more modern.
- **Coordinate system**: Set CRS before export so the model is geo-located in the sim.
- **Split long corridors**: Export sections separately (2-5km each) to keep file sizes manageable.

---

## Monitoring & Diagnostics

Ask anytime:

> "How's my project looking?"

The LLM reads resources (`metashape://project/chunks`, `metashape://chunk/*/summary`) and gives you a status report.

> "Reprojection errors are high, what should I try?"

Uses the `diagnose_alignment` prompt to analyze and suggest fixes.

> "What settings should I use for 21k photos with 64GB RAM?"

Uses `optimize_quality_settings` to recommend parameters.

---

## Batch Processing

For processing multiple road segments with identical settings:

> "Process all four chunks with the same settings: medium quality depth maps, moderate filtering, arbitrary mesh at 5M faces, mosaic texture at 8192."

The LLM runs through each chunk sequentially, or submits to network processing:

```
network_connect("localhost")
network_submit_batch(["BuildDepthMaps", "BuildModel", "BuildUV", "BuildTexture"], [...params...])
```

Then you can check on progress:

> "How's the network batch doing?"

---

## Quick Reference: Your Recommended Settings

| Step | Setting | Value | Why |
|------|---------|-------|-----|
| Match | downscale | 1 | Accuracy for long corridors |
| Match | keypoint_limit | 60000 | Fisheye needs more keypoints |
| Match | reference_preselection | True | Essential for corridors |
| Align | adaptive_fitting | True | Handles fisheye distortion |
| Depth Maps | downscale | 4 (medium) | Balance for 20k+ photos |
| Depth Maps | filter_mode | moderate | Road surfaces need moderate |
| Model | source_data | point_cloud | Avoids sky tunnel problem |
| Model | surface_type | arbitrary | Preserves vertical surfaces |
| Clean | level | 50-75 | Remove sky artifacts |
| UV | texture_size | 8192 | Sim engine sweet spot |
| Texture | blending_mode | mosaic | Best for sharp road markings |
| Texture | ghosting_filter | True | Handles moving vehicles |
