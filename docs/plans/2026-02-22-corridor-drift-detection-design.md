# Corridor Alignment Drift Detection & Prevention

**Date**: 2026-02-22
**Problem**: Long road corridor scans diverge over distance during incremental alignment. Drift isn't detected until the full corridor is aligned, wasting hours of processing time.

## Phase A: Drift Detection Tools (New MCP Tools)

### Tool 1: `get_camera_spatial_stats`

Returns spatial quality metrics for aligned cameras, focusing on GPS deviation and positional continuity.

**Implementation** (in `tools/alignment.py` or new `tools/diagnostics.py`):

```python
def get_camera_spatial_stats(
    label_pattern: str | None = None,
) -> dict:
```

**What it computes:**
- For each aligned camera with a GPS reference (`cam.reference.location`):
  - Estimated position: `chunk.crs.project(chunk.transform.matrix.mulp(cam.center))`
  - GPS reference position: `cam.reference.location`
  - Error vector: estimated - reference (in CRS units, typically meters for UTM)
- Aggregates:
  - `mean_error_xy`: mean horizontal GPS deviation (meters)
  - `max_error_xy`: worst horizontal deviation
  - `mean_error_z`: mean vertical deviation
  - `max_error_z`: worst vertical deviation
  - `error_gradient`: slope of error magnitude along the corridor (meters drift per 100m of corridor length). This is the KEY drift indicator — a high gradient means the alignment is diverging.
  - `camera_count`: total aligned cameras in the selection
  - `worst_cameras`: list of top 5 cameras with highest error (label + error)

**Corridor direction detection**: Sort cameras by their reference position projected onto the dominant axis (longest extent of the bounding box). This gives "distance along corridor" for gradient computation.

**GPS deviation vs drift**: Uniform GPS error (all cameras off by ~3m) is normal GPS noise. *Increasing* error along the corridor is drift. The gradient distinguishes these.

### Tool 2: `get_reprojection_error_by_region`

Returns per-camera reprojection errors with spatial coordinates, binned into corridor segments.

```python
def get_reprojection_error_by_region(
    num_segments: int = 10,
) -> dict:
```

**What it computes:**
- Sort aligned cameras along corridor axis (same as above)
- Divide into `num_segments` equal-length bins
- For each bin: mean/max reprojection error, camera count, GPS deviation stats
- Returns list of segments with spatial bounds and quality metrics

**Why segments**: A single global reprojection error hides local problems. Drift shows up as error increasing in later segments.

### Tool 3: `check_alignment_continuity`

Compare newly aligned cameras against previously aligned ones to detect discontinuities.

```python
def check_alignment_continuity(
    new_camera_labels: list[str],
    max_position_jump: float = 5.0,
    max_rotation_jump: float = 15.0,
) -> dict:
```

**What it computes:**
- Find cameras from `new_camera_labels` that are spatially adjacent to previously-aligned cameras (by GPS reference proximity)
- For each pair of adjacent cameras (one new, one old):
  - Position difference between estimated positions
  - Rotation difference (angular)
- Flag pairs where position jump > `max_position_jump` meters or rotation jump > `max_rotation_jump` degrees
- Returns: `continuous` (bool), `discontinuities` (list of flagged pairs with details)

**When to use**: Call after each `align_cameras()` batch to verify the new batch connected smoothly to the existing alignment.

---

## Phase B: Automated Alignment Pipeline with QA Gates (Skill)

### Skill: `corridor-alignment-pipeline`

An agent-invocable skill that orchestrates incremental alignment with automatic drift checks.

**Location**: `skills/corridor-alignment-pipeline/SKILL.md`

**Workflow the skill teaches the agent:**

```
1. User provides: camera labels (or folder), batch size, GPS reference
2. For each batch of N cameras:
   a. enable_cameras(labels=batch)
   b. set_gpu_config(cpu_enable=True)
   c. match_photos(keep_keypoints=True, reference_preselection=True)
   d. align_cameras(reset_alignment=False)  # True only for first batch
   e. save_project()
   f. get_camera_spatial_stats()  ← NEW
   g. check_alignment_continuity(new_camera_labels=batch)  ← NEW
   h. DECISION POINT:
      - error_gradient < 0.5m/100m AND continuous → proceed to next batch
      - error_gradient 0.5-2.0m/100m → WARN user, suggest GCP placement
      - error_gradient > 2.0m/100m OR discontinuity → STOP, report problem
3. After all batches: get_reprojection_error_by_region() for full-corridor overview
4. Proceed to USGS filtering if quality passes
```

**Key thresholds** (configurable in skill):
- `max_gradient`: 2.0 m/100m (stop threshold)
- `warn_gradient`: 0.5 m/100m (warning threshold)
- `max_position_jump`: 5.0m
- `max_rotation_jump`: 15.0 degrees

---

## Phase C: Reference-Anchored Alignment (DEM Integration Tools)

### Tool 4: `compare_alignment_to_dem`

Compare camera vertical positions against the imported DEM/elevation data.

```python
def compare_alignment_to_dem(
    label_pattern: str | None = None,
    camera_height_offset: float = 2.0,
) -> dict:
```

**What it computes:**
- For each aligned camera, get its estimated position in CRS coordinates
- Sample the chunk's DEM (elevation model) at that XY position
- Expected camera Z = DEM elevation + `camera_height_offset` (vehicle roof height)
- Compute difference: estimated Z - expected Z
- Return per-camera and aggregate statistics, plus drift gradient

**Why `camera_height_offset`**: Vehicle-mounted cameras are ~2m above ground. Drone cameras would use ~50-120m.

**Prerequisite**: Chunk must have an elevation model (DEM) — either built from the alignment itself or imported from external LiDAR.

### Tool 5: `generate_virtual_checkpoints`

Generate evenly-spaced checkpoint positions along the corridor from the DEM, for use as check points (not control points) to validate alignment.

```python
def generate_virtual_checkpoints(
    spacing_meters: float = 200.0,
    camera_height_offset: float = 2.0,
    create_markers: bool = True,
    marker_prefix: str = "VCP",
) -> dict:
```

**What it computes:**
- Get all camera reference positions, sort along corridor axis
- Sample positions every `spacing_meters` along the corridor centerline
- At each sample: query DEM elevation, add `camera_height_offset`
- If `create_markers=True`: create markers at these positions (labeled VCP_001, VCP_002, ...)
- These markers are "check points" — enabled for error reporting but NOT for optimization (so they don't bias the alignment, they just measure it)

**Output**: List of virtual checkpoint positions with DEM-derived elevations.

### Tool 6: `get_corridor_drift_report`

All-in-one diagnostic combining tools 1-5 into a comprehensive corridor health report.

```python
def get_corridor_drift_report(
    num_segments: int = 10,
    camera_height_offset: float = 2.0,
) -> dict:
```

**Returns:**
- GPS deviation stats (from tool 1)
- Per-segment reprojection errors (from tool 2)
- DEM comparison if elevation model exists (from tool 4)
- Overall drift gradient and health assessment: PASS / WARN / FAIL
- Recommended actions based on findings

---

## Implementation Plan

### Phase A (implement first): 3 new tools
1. Create `src/metashape_mcp/tools/diagnostics.py` — new module for QA/diagnostic tools
2. Implement `get_camera_spatial_stats`
3. Implement `get_reprojection_error_by_region`
4. Implement `check_alignment_continuity`
5. Register module in `tools/__init__.py`
6. Run API verifier agent against new tools

### Phase B (implement second): 1 skill
7. Create `skills/corridor-alignment-pipeline/SKILL.md`
8. Update `metashape-alignment` skill to reference drift checks
9. Update `photogrammetry-qa` agent to use new diagnostic tools

### Phase C (implement third): 3 new tools + 1 report tool
10. Add `compare_alignment_to_dem` to diagnostics.py
11. Add `generate_virtual_checkpoints` to diagnostics.py
12. Add `get_corridor_drift_report` to diagnostics.py
13. Run API verifier agent against all new tools

### Dependencies
- Phase A: No dependencies. Uses existing camera.center, camera.reference, chunk.crs, chunk.transform
- Phase B: Depends on Phase A tools existing
- Phase C: Depends on chunk having an elevation model (DEM). Uses chunk.elevation for sampling.
  - Need to verify: does `chunk.elevation` expose a method to sample elevation at arbitrary XY? If not, we may need `execute_python` to access the raster directly.

### API Risk Areas
- DEM sampling: Need to verify how to query elevation at a point. May require `chunk.elevation.altitude(point)` or similar — must check API reference.
- Corridor axis detection: Assumes cameras have GPS reference and the corridor is roughly linear. Curved roads work fine (we use distance-along-track, not straight-line distance).
