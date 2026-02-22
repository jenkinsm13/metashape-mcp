---
name: sky-artifact-prevention
description: Prevent and remove sky/tunnel mesh artifacts in road corridor photogrammetry. Covers five strategies from Metashape-side prevention (height field, region crop, point cloud classification, source selection) to post-mesh cleanup. The #1 quality problem for vehicle-mounted captures. Works through the Metashape MCP server.
user-invocable: false
---

# Sky Artifact Prevention for Road Corridors

## The Problem

Metashape's mesh generation creates "tunnel" or "dome" artifacts over road corridors. Even with proper sky masks:
- **Depth maps ignore masks** during mesh interpolation
- **Interpolation fills gaps** between opposite sides of the road, creating a closed surface overhead
- This produces tunnel effects, flashing artifacts, and enclosed environments where open sky should be

This is Metashape's most well-known limitation for road corridor captures. There is no single fix — use a combination of strategies.

## When to Use

- Building mesh from road corridor captures
- Any long linear capture where sky/overhead closure is a problem
- After mesh building, if tunnel artifacts are visible
- When planning the dense reconstruction strategy (choose BEFORE building)

## Strategy Overview

Five strategies, ordered by effectiveness for road corridors:

| # | Strategy | When to Apply | Effectiveness |
|---|----------|--------------|---------------|
| 1 | Point cloud source | Before mesh build | Best — avoids the problem entirely |
| 2 | Height field mode | Before mesh build | Good for flat terrain, loses vertical surfaces |
| 3 | Point cloud classification | Before mesh build | Good — requires classification step |
| 4 | Region cropping | Before mesh build | Moderate — simple but crude |
| 5 | Post-mesh cleanup | After mesh build | Fallback — fixes what got through |

**Recommended combination:** Strategy 1 + 3 + 5 (point cloud source, with ground classification, followed by cleanup).

## Strategy 1: Build Mesh from Point Cloud (Not Depth Maps)

**Why it works:** Point cloud generation DOES respect masks. If sky is masked, no points exist in the sky → no mesh in the sky. Depth map interpolation is what creates the tunnel — bypassing it avoids the problem.

```
# Step 1: Build point cloud with masks active
build_point_cloud(
    point_colors=True,
    point_confidence=True
)

# Step 2: Build mesh from point cloud
build_model(
    surface_type="arbitrary",
    source_data="point_cloud",
    interpolation="enabled",
    vertex_colors=True
)
```

**Trade-offs:**
- (+) Best preservation of open sky areas
- (+) Masks fully respected during point cloud generation
- (-) Point cloud mesh is slightly less detailed than depth map mesh
- (-) Still some interpolation at edges where point density drops

**When NOT to use:** When you need maximum mesh detail and will handle artifacts in post.

## Strategy 2: Height Field Surface Type

**Why it works:** Height field mode generates only the surface visible from directly above — it cannot create tunnels, domes, or enclosed spaces.

```
build_model(
    surface_type="height_field",
    source_data="depth_maps",
    interpolation="enabled",
    vertex_colors=True
)
```

**Trade-offs:**
- (+) Completely eliminates tunnel/dome artifacts
- (+) Perfect for terrain-only workflows (DEM generation)
- (-) Loses vertical surfaces: building facades, retaining walls, canyon rock faces
- (-) Not suitable when you need full 3D geometry

**Best for:** Terrain/ground extraction where vertical surfaces don't matter. NOT suitable for driving simulator environments where canyon walls are important.

## Strategy 3: Point Cloud Classification + Filtered Mesh

**Why it works:** Classify the point cloud to separate ground/building from vegetation/noise/sky, then build mesh from only the classes you want.

```
# Step 1: Build point cloud
build_point_cloud(
    point_colors=True,
    point_confidence=True
)

# Step 2: Classify ground
classify_ground_points(
    max_angle=15.0,
    max_distance=1.0,
    cell_size=50.0
)

# Step 3: Build mesh from ground + building classes only
build_model(
    surface_type="arbitrary",
    source_data="point_cloud",
    classes=[2, 6],              # 2=Ground, 6=Building
    interpolation="enabled",
    vertex_colors=True
)
```

**Point cloud classes (ASPRS LAS standard):**

| Class | Code | Include? |
|-------|------|----------|
| Created/never classified | 0 | Maybe — contains unclassified real geometry |
| Unclassified | 1 | Maybe — same as above |
| Ground | 2 | YES — always include |
| Low vegetation | 3 | Depends on needs |
| Medium vegetation | 4 | Depends on needs |
| High vegetation | 5 | Usually NO for road corridors |
| Building | 6 | YES — retaining walls, structures |
| Noise | 7 | NO — sky artifacts live here |

**Trade-offs:**
- (+) Precise control over what gets meshed
- (+) Removes sky noise AND vegetation noise
- (-) Classification can misclassify rock faces as buildings or vice versa
- (-) Extra processing step (classification takes time)
- (-) `classify_ground_points` is designed for aerial data — may not perfectly classify vehicle-level captures

**Tuning for road corridors:**
```
classify_ground_points(
    max_angle=25.0,     # Increase from 15 for steep canyon walls
    max_distance=2.0,   # Increase for rougher terrain
    cell_size=20.0      # Decrease for finer detail in narrow corridors
)
```

## Strategy 4: Region Cropping

**Why it works:** Limit the reconstruction volume so nothing above a certain height gets meshed.

```
# Get current bounds
get_chunk_bounds()

# Set tight region — limit vertical extent
set_region(
    center=[x, y, z],
    size=[width, length, limited_height]
)
```

**How to determine `limited_height`:**
- For a road canyon: tallest wall height + 2m margin
- For flat road: 5-10m above road surface
- For bridges/overpasses: height of the tallest structure + 2m

**Trade-offs:**
- (+) Simple, no extra processing
- (+) Works with any source (depth maps or point cloud)
- (-) Crude — a single height limit for the whole corridor
- (-) Clips tall features if the limit is too low
- (-) Requires manual coordinate inspection to set properly

**Region rotation for corridors:**
If the corridor isn't axis-aligned, rotate the region to match:
```
set_region_rotation(yaw=corridor_heading)
```

## Strategy 5: Post-Mesh Cleanup

**When to use:** After mesh is built, as a fallback for whatever got through.

### 5a: Component-based cleaning
```
clean_model(
    criterion="component_size",
    level=75
)
```
Removes disconnected mesh components smaller than the threshold. Sky artifacts are often disconnected from the main terrain mesh.

**Level guide:**
- `50`: Conservative — only removes small fragments
- `75`: Moderate — removes medium artifacts (good default)
- `90`: Aggressive — removes everything except the largest component

### 5b: Confidence-based filtering
If point confidence was enabled:
```
# Remove low-confidence points first, then rebuild mesh
filter_points_by_confidence(min_confidence=3)
```
Sky interpolation artifacts tend to have low confidence scores.

### 5c: Manual region deletion
For stubborn artifacts that automated cleaning misses:
1. Identify the region in Metashape GUI
2. Select faces manually and delete
3. Or use `execute_python` to delete faces by height/normal criteria

## Decision Tree

```
Building mesh for road corridor?
├── Need full 3D (walls, rock faces)?
│   ├── YES → Strategy 1 (point cloud source)
│   │         + Strategy 3 (classify, use classes [0,1,2,6])
│   │         + Strategy 5 (cleanup remaining artifacts)
│   └── NO (terrain only) → Strategy 2 (height field)
├── Have EXR masks?
│   ├── YES → Strategy 1 is especially effective (masks respected in point cloud)
│   └── NO → Strategy 3 + 4 + 5 (classify + region crop + cleanup)
└── Already built mesh with artifacts?
    └── Strategy 5 (cleanup) — then consider rebuilding with Strategy 1 or 3
```

## Recommended Pipeline for Decker Canyon-Style Corridors

This project needs full 3D (road + canyon walls), has EXR masks, and outputs to a driving simulator:

```
# 1. GPU off for dense operations
set_gpu_config(cpu_enable=False)

# 2. Build point cloud (masks respected here)
build_point_cloud(point_colors=True, point_confidence=True)

# 3. Classify ground — tuned for steep canyon
classify_ground_points(max_angle=25.0, max_distance=2.0, cell_size=20.0)

# 4. Build mesh from point cloud, ground + unclassified + building
build_model(
    surface_type="arbitrary",
    source_data="point_cloud",
    classes=[0, 1, 2, 6],
    interpolation="enabled",
    vertex_colors=True,
    vertex_confidence=True
)

# 5. Clean remaining artifacts
clean_model(criterion="component_size", level=75)

# 6. Verify — check for tunnel artifacts
get_model_stats()
capture_viewport()
```

If artifacts remain after step 5, increase `level` to 90 or apply region cropping before rebuilding.

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Building from depth maps with masks | Tunnel forms anyway — depth map interpolation ignores masks | Use `source_data="point_cloud"` instead |
| Height field on a canyon | Loses rock face walls | Use `surface_type="arbitrary"` with classification |
| Aggressive classification on vehicle data | Misclassifies walls as noise | Increase `max_angle` to 25-30 for steep terrain |
| Not cleaning after mesh build | Artifact fragments remain | Always run `clean_model` as final step |
| Region crop too tight | Clips legitimate tall features | Add 2-3m margin above tallest feature |
